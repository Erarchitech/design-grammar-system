import React from "react";
import {
  CameraController,
  DefaultViewerParams,
  FilteringExtension,
  SelectionExtension,
  SpeckleLoader,
  UpdateFlags,
  UrlHelper,
  Viewer
} from "@speckle/viewer";
import ValidationRunsStrip from "./ValidationRunsStrip.jsx";

const config = window.GRAPH_CONFIG || {};
const query = new URLSearchParams(window.location.search);
const initialProject = query.get("project") || "";
const initialRunId = query.get("runId") || "";
const initialRuleId = query.get("ruleId") || "";

function normalizeUrl(url) {
  return (url || "").replace(/\/+$/, "");
}

function parseJsonSafely(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function extractErrorMessage(text, status) {
  const parsed = parseJsonSafely(text);
  if (parsed && typeof parsed.detail === "string" && parsed.detail) {
    return parsed.detail;
  }
  return text || `Request failed with ${status}`;
}

async function fetchJson(url, init) {
  const response = await fetch(url, init);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(extractErrorMessage(text, response.status));
  }

  if (!text) {
    return null;
  }

  return parseJsonSafely(text) || text;
}

function collectAllDescendantIds(node) {
  const ids = [];
  node.walk((child) => {
    if (child.model?.id) {
      ids.push(child.model.id);
    }
    return true;
  });
  return ids;
}

function collectValidationObjects(worldTree, runId) {
  const entityMap = new Map();
  const allValidationObjectIds = [];

  // Debug: sample some tree nodes to see their structure
  let sampleCount = 0;
  worldTree.walk((node) => {
    if (sampleCount < 10 && node.model?.raw && Object.keys(node.model.raw).length > 2) {
      console.log("[DG-Debug] Sample tree node:", node.model.id, Object.keys(node.model.raw));
      sampleCount++;
    }
    return true;
  });

  // Primary search: exact match on validationRunId + dgEntityId
  let nodes = worldTree.findAll((node) => {
    const raw = node.model?.raw;
    return raw && raw.validationRunId === runId && raw.dgEntityId;
  });

  console.log("[DG-Debug] collectValidationObjects: runId =", runId, "matched nodes =", nodes.length);

  // Fallback: if no nodes matched, try finding any node with dgEntityId regardless of runId
  if (nodes.length === 0) {
    nodes = worldTree.findAll((node) => {
      const raw = node.model?.raw;
      return raw && raw.dgEntityId;
    });
    console.log("[DG-Debug] Fallback search (dgEntityId only): matched nodes =", nodes.length);
  }

  for (const node of nodes) {
    const dgEntityId = node.model.raw.dgEntityId;
    const objectId = node.model.id;
    if (!dgEntityId || !objectId) {
      continue;
    }

    // Collect this node's ID plus all its descendant IDs (mesh/geometry nodes)
    const allIds = collectAllDescendantIds(node);
    if (allIds.length === 0) {
      allIds.push(objectId);
    }

    allValidationObjectIds.push(...allIds);
    if (!entityMap.has(dgEntityId)) {
      entityMap.set(dgEntityId, []);
    }
    entityMap.get(dgEntityId).push(...allIds);
  }

  console.log("[DG-Debug] entityMap size:", entityMap.size, "total objectIds:", allValidationObjectIds.length);
  if (entityMap.size > 0) {
    const first = entityMap.entries().next().value;
    console.log("[DG-Debug] Sample entity:", first[0], "→", first[1].length, "objectIds:", first[1].slice(0, 3));
  }

  return {
    entityMap,
    allValidationObjectIds: Array.from(new Set(allValidationObjectIds))
  };
}

// Normalize an entity item — API may return plain string or {dgEntityId, displayName}
function entityId(item) {
  if (!item) return "";
  if (typeof item === "string") return item;
  return item.dgEntityId || "";
}

function entityLabel(item) {
  if (!item) return "Unknown";
  if (typeof item === "string") return item;
  return item.displayName || item.dgEntityId || "Unknown";
}

function entityIds(items) {
  return (items || []).map(entityId);
}

function flattenObjectIds(entityMap, ids) {
  const objectIds = [];
  for (const id of ids || []) {
    const mapped = entityMap.get(id) || [];
    objectIds.push(...mapped);
  }
  return Array.from(new Set(objectIds));
}

function shortId(value) {
  if (!value) {
    return "Unknown";
  }
  if (value.length <= 16) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function formatTimestamp(value) {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export default function App() {
  const dataServiceUrl = normalizeUrl(config.dataServiceUrl || "/data-service");
  const [project] = React.useState(initialProject);
  const [runId, setRunId] = React.useState(initialRunId);
  const [manifest, setManifest] = React.useState(null);
  const [validationRuns, setValidationRuns] = React.useState([]);
  const [selectedRuleId, setSelectedRuleId] = React.useState(initialRuleId);
  const [objectSets, setObjectSets] = React.useState({ failed: [], passed: [] });
  const [showFailed, setShowFailed] = React.useState(true);
  const [showPassed, setShowPassed] = React.useState(true);
  const [showBase, setShowBase] = React.useState(true);
  const [failColor, setFailColor] = React.useState("#ff4d4f");
  const [passColor, setPassColor] = React.useState("#2fb16f");
  const [baseColor, setBaseColor] = React.useState("#5a6a88");
  const [failOpacity, setFailOpacity] = React.useState(80);
  const [passOpacity, setPassOpacity] = React.useState(60);
  const [baseOpacity, setBaseOpacity] = React.useState(30);
  const [selectById, setSelectById] = React.useState("");
  const [isolatedIds, setIsolatedIds] = React.useState(null);
  const [hiddenIds, setHiddenIds] = React.useState(new Set());
  const [expandFailing, setExpandFailing] = React.useState(true);
  const [expandPassing, setExpandPassing] = React.useState(false);
  const [selectedEntityIds, setSelectedEntityIds] = React.useState(new Set());
  const [viewerReady, setViewerReady] = React.useState(false);
  const [status, setStatus] = React.useState("Loading validation viewer...");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [runsLoading, setRunsLoading] = React.useState(true);
  const [runsError, setRunsError] = React.useState(null);
  const [deletingRunId, setDeletingRunId] = React.useState("");
  const [speckleConfig, setSpeckleConfig] = React.useState({
    speckleProjectId: "",
    baseModelId: "",
    baseModelName: "",
    validationModelId: ""
  });
  const [speckleConfigStatus, setSpeckleConfigStatus] = React.useState("Load Speckle project mapping.");
  const [loadingSpeckleConfig, setLoadingSpeckleConfig] = React.useState(false);
  const [expandSpeckleConnector, setExpandSpeckleConnector] = React.useState(false);
  const [expandSpeckleSettings, setExpandSpeckleSettings] = React.useState(false);
  const [speckleSettings, setSpeckleSettings] = React.useState({ baseUrl: "http://localhost:8090", writeToken: "", readToken: "" });
  const [speckleSettingsMeta, setSpeckleSettingsMeta] = React.useState({
    writeTokenConfigured: false,
    readTokenConfigured: false,
    writeTokenPreview: "",
    readTokenPreview: ""
  });
  const [speckleSettingsStatus, setSpeckleSettingsStatus] = React.useState("");
  const [loadingSpeckleSettings, setLoadingSpeckleSettings] = React.useState(false);

  // Screenshot thumbnails per run — persisted in localStorage
  const screenshotStorageKey = `dg_run_screenshots_${project}`;
  const [runScreenshots, setRunScreenshots] = React.useState(() => {
    try {
      return JSON.parse(localStorage.getItem(screenshotStorageKey) || "{}");
    } catch {
      return {};
    }
  });

  // Per-run graphics settings — persisted in localStorage
  const gfxStorageKey = `dg_run_gfx_${project}`;
  const [runGfxMap, setRunGfxMap] = React.useState(() => {
    try {
      return JSON.parse(localStorage.getItem(gfxStorageKey) || "{}");
    } catch {
      return {};
    }
  });
  const runGfxMapRef = React.useRef(runGfxMap);
  runGfxMapRef.current = runGfxMap;


  const failColorRef = React.useRef(null);
  const passColorRef = React.useRef(null);
  const baseColorRef = React.useRef(null);
  const viewerHostRef = React.useRef(null);
  const viewerRef = React.useRef(null);
  const filteringRef = React.useRef(null);
  const entityMapRef = React.useRef(new Map());
  const allValidationObjectIdsRef = React.useRef([]);
  const manifestRef = React.useRef(null);
  manifestRef.current = manifest;
  const manifestRunId = manifest?.runId || "";
  const activeRunId = runId || manifestRunId;
  const activeRunIdRef = React.useRef(activeRunId);
  activeRunIdRef.current = activeRunId;
  const runScreenshotsRef = React.useRef(runScreenshots);
  runScreenshotsRef.current = runScreenshots;

  // Persist screenshots to localStorage whenever they change
  React.useEffect(() => {
    try {
      localStorage.setItem(screenshotStorageKey, JSON.stringify(runScreenshots));
    } catch {
      // localStorage quota exceeded — silently skip
    }
  }, [runScreenshots, screenshotStorageKey]);

  // Persist per-run graphics settings to localStorage
  React.useEffect(() => {
    try {
      localStorage.setItem(gfxStorageKey, JSON.stringify(runGfxMap));
    } catch {
      // localStorage quota exceeded — silently skip
    }
  }, [runGfxMap, gfxStorageKey]);

  const defaultGfx = {
    showFailed: true, showPassed: true, showBase: true,
    failColor: "#ff4d4f", passColor: "#2fb16f", baseColor: "#5a6a88",
    failOpacity: 80, passOpacity: 60, baseOpacity: 30
  };

  // Save current graphics state for the active run
  const saveGfxState = React.useCallback((targetRunId) => {
    const rid = targetRunId || activeRunIdRef.current;
    if (!rid) return;
    setRunGfxMap((prev) => ({
      ...prev,
      [rid]: { showFailed, showPassed, showBase, failColor, passColor, baseColor, failOpacity, passOpacity, baseOpacity }
    }));
  }, [showFailed, showPassed, showBase, failColor, passColor, baseColor, failOpacity, passOpacity, baseOpacity]);

  // Restore graphics state for a given run (or apply defaults)
  const restoreGfxState = React.useCallback((targetRunId) => {
    const saved = runGfxMapRef.current[targetRunId] || defaultGfx;
    setShowFailed(saved.showFailed);
    setShowPassed(saved.showPassed);
    setShowBase(saved.showBase);
    setFailColor(saved.failColor);
    setPassColor(saved.passColor);
    setBaseColor(saved.baseColor);
    setFailOpacity(saved.failOpacity);
    setPassOpacity(saved.passOpacity);
    setBaseOpacity(saved.baseOpacity);
  }, []);


  // Capture a screenshot of the current 3D viewport and store it for the active run
  const captureScreenshot = React.useCallback(async () => {
    const viewer = viewerRef.current;
    const currentRunId = activeRunIdRef.current;
    if (!viewer || !currentRunId) return;
    try {
      const dataUrl = await viewer.screenshot();
      // Downscale to a small thumbnail to save localStorage space
      const thumb = await new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement("canvas");
          const tw = 160, th = 80;
          canvas.width = tw;
          canvas.height = th;
          const ctx = canvas.getContext("2d");
          const sr = img.width / img.height;
          const tr = tw / th;
          let sw, sh, sx, sy;
          if (sr > tr) { sh = img.height; sw = sh * tr; sx = (img.width - sw) / 2; sy = 0; }
          else { sw = img.width; sh = sw / tr; sx = 0; sy = (img.height - sh) / 2; }
          ctx.drawImage(img, sx, sy, sw, sh, 0, 0, tw, th);
          resolve(canvas.toDataURL("image/jpeg", 0.7));
        };
        img.onerror = () => resolve(null);
        img.src = dataUrl;
      });
      if (thumb) {
        setRunScreenshots((prev) => ({ ...prev, [currentRunId]: thumb }));
      }
    } catch (err) {
      console.warn("[DG] Failed to capture screenshot:", err.message);
    }
  }, []);

  const loadRuns = React.useCallback(async () => {
    if (!project) {
      setValidationRuns([]);
      setRunsLoading(false);
      return [];
    }

    const runsUrl = `${dataServiceUrl}/validation/runs/${encodeURIComponent(project)}`;

    try {
      setRunsLoading(true);
      setRunsError(null);
      const response = await fetchJson(runsUrl);
      const runs = Array.isArray(response?.runs) ? response.runs : [];
      setValidationRuns(runs);
      return runs;
    } catch (err) {
      setValidationRuns([]);
      setRunsError(err.message || "Could not load grouped runs. Try again.");
      setError(err.message || "Failed to load validation runs.");
      return [];
    } finally {
      setRunsLoading(false);
    }
  }, [dataServiceUrl, project]);

  const loadSpeckleConfig = React.useCallback(async () => {
    if (!project) {
      setSpeckleConfigStatus("Project is required to configure Speckle connector.");
      return;
    }

    setLoadingSpeckleConfig(true);
    try {
      const response = await fetch(`${dataServiceUrl}/integration/speckle/project/${encodeURIComponent(project)}`);
      if (response.status === 404) {
        setSpeckleConfig({
          speckleProjectId: "",
          baseModelId: "",
          baseModelName: "",
          validationModelId: ""
        });
        setSpeckleConfigStatus("No Speckle model link saved for this DG project yet.");
        return;
      }
      if (!response.ok) {
        throw new Error(await response.text() || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setSpeckleConfig({
        speckleProjectId: data.speckleProjectId || "",
        baseModelId: data.baseModelId || "",
        baseModelName: data.baseModelName || "",
        validationModelId: data.validationModelId || ""
      });
      setSpeckleConfigStatus("Speckle model link loaded.");
    } catch (err) {
      setSpeckleConfigStatus(`Failed to load Speckle config: ${err.message}`);
    } finally {
      setLoadingSpeckleConfig(false);
    }
  }, [dataServiceUrl, project]);

  const saveSpeckleConfig = React.useCallback(async () => {
    if (!project) {
      setSpeckleConfigStatus("Project is required to configure Speckle connector.");
      return;
    }

    setLoadingSpeckleConfig(true);
    try {
      const response = await fetch(`${dataServiceUrl}/integration/speckle/project/${encodeURIComponent(project)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          speckleProjectId: (speckleConfig.speckleProjectId || "").trim(),
          baseModelId: (speckleConfig.baseModelId || "").trim(),
          baseModelName: (speckleConfig.baseModelName || "").trim() || null,
          validationModelId: (speckleConfig.validationModelId || "").trim() || null
        })
      });

      const rawText = await response.text();
      const data = rawText ? (parseJsonSafely(rawText) || null) : null;
      if (!response.ok) {
        throw new Error(data?.detail || rawText || `HTTP ${response.status}`);
      }

      setSpeckleConfig({
        speckleProjectId: data?.speckleProjectId || "",
        baseModelId: data?.baseModelId || "",
        baseModelName: data?.baseModelName || "",
        validationModelId: data?.validationModelId || ""
      });
      setSpeckleConfigStatus("Speckle model link saved.");
    } catch (err) {
      setSpeckleConfigStatus(`Failed to save Speckle config: ${err.message}`);
    } finally {
      setLoadingSpeckleConfig(false);
    }
  }, [dataServiceUrl, project, speckleConfig]);

  const loadSpeckleSettings = React.useCallback(async () => {
    setLoadingSpeckleSettings(true);
    try {
      const response = await fetch(`${dataServiceUrl}/settings/speckle`);
      if (!response.ok) {
        throw new Error(await response.text() || `HTTP ${response.status}`);
      }
      const data = await response.json();
      setSpeckleSettings((current) => ({
        baseUrl: data.baseUrl || current.baseUrl || "http://localhost:8090",
        writeToken: "",
        readToken: ""
      }));
      setSpeckleSettingsMeta({
        writeTokenConfigured: !!data.writeTokenConfigured,
        readTokenConfigured: !!data.readTokenConfigured,
        writeTokenPreview: data.writeTokenPreview || "",
        readTokenPreview: data.readTokenPreview || ""
      });
      setSpeckleSettingsStatus(
        data.writeTokenConfigured
          ? "Stored in data-service."
          : "No stored Speckle write token yet."
      );
    } catch (err) {
      setSpeckleSettingsStatus(`Failed to load Speckle settings: ${err.message}`);
    } finally {
      setLoadingSpeckleSettings(false);
    }
  }, [dataServiceUrl]);

  const saveSpeckleSettings = React.useCallback(async () => {
    setLoadingSpeckleSettings(true);
    try {
      const response = await fetch(`${dataServiceUrl}/settings/speckle`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          baseUrl: (speckleSettings.baseUrl || "").trim() || "http://localhost:8090",
          writeToken: (speckleSettings.writeToken || "").trim(),
          readToken: (speckleSettings.readToken || "").trim()
        })
      });
      const rawText = await response.text();
      const data = rawText ? (parseJsonSafely(rawText) || null) : null;
      if (!response.ok) {
        throw new Error(data?.detail || rawText || `HTTP ${response.status}`);
      }
      setSpeckleSettings({
        baseUrl: data?.baseUrl || speckleSettings.baseUrl || "http://localhost:8090",
        writeToken: "",
        readToken: ""
      });
      setSpeckleSettingsMeta({
        writeTokenConfigured: !!data?.writeTokenConfigured,
        readTokenConfigured: !!data?.readTokenConfigured,
        writeTokenPreview: data?.writeTokenPreview || "",
        readTokenPreview: data?.readTokenPreview || ""
      });
      setSpeckleSettingsStatus("Speckle settings saved.");
    } catch (err) {
      setSpeckleSettingsStatus(`Failed to save: ${err.message}`);
    } finally {
      setLoadingSpeckleSettings(false);
    }
  }, [dataServiceUrl, speckleSettings]);

  const loadManifest = React.useCallback(async (signal) => {
    if (!project) {
      setLoading(false);
      setError("Project query parameter is required.");
      return;
    }

    const targetRunId = runId || "";

    // Skip re-fetch if we already have a manifest for this exact run
    const current = manifestRef.current;
    if (current && current.runId === targetRunId) {
      setLoading(false);
      return;
    }

    // If no runId is specified and runs haven't loaded yet, wait
    if (!targetRunId && runsLoading) {
      return;
    }

    // If no runId and no runs available, show empty state
    if (!targetRunId && !runsLoading && validationRuns.length === 0) {
      if (!current) {
        setManifest(null);
        setObjectSets({ failed: [], passed: [] });
        setSelectedRuleId("");
        setLoading(false);
        setError("");
        setStatus("No validation runs found for this project.");
      }
      return;
    }

    const manifestUrl = targetRunId
      ? `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}/${encodeURIComponent(targetRunId)}`
      : `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}`;

    try {
      setLoading(true);
      setError("");
      const response = await fetchJson(manifestUrl);
      if (signal?.aborted) return;
      setManifest(response);
      setRunId(response.runId || "");
      setSelectedRuleId((currentRuleId) => {
        const nextRules = response.rules || [];
        if (currentRuleId && nextRules.some((rule) => rule.ruleId === currentRuleId)) {
          return currentRuleId;
        }
        return nextRules[0]?.ruleId || "";
      });
      setStatus("Validation manifest loaded.");
    } catch (err) {
      if (signal?.aborted) return;
      const message = err.message || "Failed to load validation manifest.";
      if (message.includes("No validation run found") || message.includes("Validation run not found")) {
        setManifest(null);
        setObjectSets({ failed: [], passed: [] });
        setSelectedRuleId("");
        setError("");
        setStatus("No validation manifest found for this project.");
      } else {
        setError(message);
        setStatus("Validation manifest is unavailable.");
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [dataServiceUrl, project, runId, runsLoading, validationRuns.length]);

  React.useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  React.useEffect(() => {
    void loadSpeckleConfig();
  }, [loadSpeckleConfig]);

  React.useEffect(() => {
    void loadSpeckleSettings();
  }, [loadSpeckleSettings]);

  React.useEffect(() => {
    const ac = new AbortController();
    void loadManifest(ac.signal);
    return () => ac.abort();
  }, [loadManifest]);

  // Viewer init — keyed on manifestRunId (string) to prevent re-init on same run
  React.useEffect(() => {
    console.log("[DG-Debug] Viewer init effect: manifestRunId =", manifestRunId, "host =", !!viewerHostRef.current);
    if (!manifestRunId || !viewerHostRef.current) {
      return undefined;
    }

    let disposed = false;

    const initViewer = async () => {
      const m = manifestRef.current;
      if (!m) return;

      // Dispose any previous viewer and clear the host to prevent stacking
      if (viewerRef.current) {
        viewerRef.current.dispose();
        viewerRef.current = null;
        filteringRef.current = null;
      }
      const host = viewerHostRef.current;
      while (host && host.firstChild) {
        host.removeChild(host.firstChild);
      }

      setViewerReady(false);
      setStatus("Initializing Speckle viewer...");

      const viewer = new Viewer(host, {
        ...DefaultViewerParams,
        verbose: false,
        showStats: false
      });
      await viewer.init();

      if (disposed) {
        viewer.dispose();
        return;
      }

      viewer.createExtension(CameraController);
      viewer.createExtension(SelectionExtension);
      const filtering = viewer.createExtension(FilteringExtension);
      viewerRef.current = viewer;
      filteringRef.current = filtering;

      const resourceUrls = [m.baseResourceUrl, m.validationResourceUrl].filter(Boolean);
      for (const resourceUrl of resourceUrls) {
        if (disposed) return;
        const urls = await UrlHelper.getResourceUrls(resourceUrl);
        for (const url of urls) {
          if (disposed) return;
          const loader = new SpeckleLoader(
            viewer.getWorldTree(),
            url,
            m.readToken || config.speckleReadToken || undefined
          );
          await viewer.loadObject(loader, true);
        }
      }

      if (disposed) {
        return;
      }

      const collected = collectValidationObjects(viewer.getWorldTree(), m.runId);
      entityMapRef.current = collected.entityMap;
      allValidationObjectIdsRef.current = collected.allValidationObjectIds;
      setViewerReady(true);
      setStatus("Viewer ready.");
    };

    void initViewer().catch((err) => {
      if (!disposed) {
        setError(err.message || "Failed to initialize the Speckle viewer.");
        setStatus("Viewer initialization failed.");
      }
    });

    return () => {
      disposed = true;
      setViewerReady(false);
      if (viewerRef.current) {
        viewerRef.current.dispose();
        viewerRef.current = null;
      }
      filteringRef.current = null;
      entityMapRef.current = new Map();
      allValidationObjectIdsRef.current = [];
    };
  }, [manifestRunId]);

  // Load rule-specific object sets
  React.useEffect(() => {
    if (!manifest?.runId || !selectedRuleId) {
      return undefined;
    }

    const url = `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}/${encodeURIComponent(manifest.runId)}/${encodeURIComponent(selectedRuleId)}`;
    let cancelled = false;

    const loadRuleObjectSets = async () => {
      try {
        const response = await fetchJson(url);
        if (!cancelled) {
          setObjectSets(response.objectSets || { failed: [], passed: [] });
          const nextQuery = new URLSearchParams(window.location.search);
          nextQuery.set("project", project);
          nextQuery.set("runId", manifest.runId);
          nextQuery.set("ruleId", selectedRuleId);
          window.history.replaceState({}, "", `${window.location.pathname}?${nextQuery.toString()}`);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load rule object sets.");
        }
      }
    };

    void loadRuleObjectSets();
    return () => {
      cancelled = true;
    };
  }, [dataServiceUrl, manifest, project, selectedRuleId]);

  // Filtering effect — applies visibility, isolation, hiding, and coloring
  React.useEffect(() => {
    const filtering = filteringRef.current;
    if (!filtering || !viewerReady || !selectedRuleId) {
      return;
    }

    filtering.resetFilters();
    const entityMap = entityMapRef.current;
    const allValidationObjectIds = allValidationObjectIdsRef.current;
    const failedObjectIds = showFailed ? flattenObjectIds(entityMap, entityIds(objectSets.failed)) : [];
    const passedObjectIds = showPassed ? flattenObjectIds(entityMap, entityIds(objectSets.passed)) : [];
    const visibleObjectIds = [...failedObjectIds, ...passedObjectIds];

    // If user has isolated specific IDs via the search bar, apply isolation
    if (isolatedIds) {
      const isoObjectIds = flattenObjectIds(entityMap, Array.from(isolatedIds));
      if (isoObjectIds.length > 0) {
        filtering.isolateObjects(isoObjectIds, "dg-isolate", true, true);
      }
    } else {
      // Hide validation objects not in the visible set
      const visibleSet = new Set(visibleObjectIds);
      const hiddenValidationIds = allValidationObjectIds.filter((id) => !visibleSet.has(id));
      if (hiddenValidationIds.length > 0) {
        filtering.hideObjects(hiddenValidationIds, "dg-validation", true, false);
      }

      // When base model toggle is off, isolate only the validation objects
      if (!showBase && visibleObjectIds.length > 0) {
        filtering.isolateObjects(visibleObjectIds, "dg-base", true, false);
      }

      // Hide specific entity IDs from the Hide button
      if (hiddenIds.size > 0) {
        const hideObjectIds = flattenObjectIds(entityMap, Array.from(hiddenIds));
        if (hideObjectIds.length > 0) {
          filtering.hideObjects(hideObjectIds, "dg-hide", true, false);
        }
      }
    }

    // Apply colours + opacity from the graphics bar settings
    const colorGroups = [];
    if (failedObjectIds.length > 0) {
      colorGroups.push({ objectIds: failedObjectIds, color: failColor });
    }
    if (passedObjectIds.length > 0) {
      colorGroups.push({ objectIds: passedObjectIds, color: passColor });
    }

    console.log("[DG-Debug] Filtering effect:", {
      viewerReady,
      selectedRuleId,
      showFailed,
      showPassed,
      showBase,
      failedEntityCount: (objectSets.failed || []).length,
      passedEntityCount: (objectSets.passed || []).length,
      failedObjectIds: failedObjectIds.length,
      passedObjectIds: passedObjectIds.length,
      entityMapSize: entityMap.size,
      allValidationObjectIds: allValidationObjectIds.length,
      colorGroups: colorGroups.length
    });

    if (colorGroups.length > 0) {
      filtering.setUserObjectColors(colorGroups);
    }

    // Apply per-group opacity via renderer material overrides.
    // setUserObjectColors only handles RGB (Speckle ramp texture has no alpha),
    // so we resolve each group's objectIds to NodeRenderViews and call
    // renderer.setMaterial with a RenderMaterial that includes opacity.
    const viewer = viewerRef.current;
    if (viewer) {
      const renderer = viewer.getRenderer();
      const worldTree = viewer.getWorldTree();
      const renderTree = worldTree.getRenderTree();

      const applyGroupMaterial = (objectIds, hexColor, opacityPercent) => {
        if (objectIds.length === 0) return;
        const rvs = [];
        for (const id of objectIds) {
          const nodes = worldTree.findId(id);
          if (nodes) {
            for (const node of nodes) {
              const views = renderTree.getRenderViewsForNode(node);
              if (views) rvs.push(...views);
            }
          }
        }
        if (rvs.length === 0) return;
        const colorInt = parseInt(hexColor.slice(1), 16);
        renderer.setMaterial(rvs, {
          id: `dg-${hexColor}-${opacityPercent}`,
          color: colorInt,
          emissive: 0,
          opacity: opacityPercent / 100,
          roughness: 0.6,
          metalness: 0,
          vertexColors: false,
          lineWeight: 1,
        });
      };

      applyGroupMaterial(failedObjectIds, failColor, failOpacity);
      applyGroupMaterial(passedObjectIds, passColor, passOpacity);

      viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
    }
  }, [viewerReady, objectSets, selectedRuleId, showFailed, showPassed, showBase,
      failColor, passColor, failOpacity, passOpacity, baseColor, baseOpacity, isolatedIds, hiddenIds]);

  // Restore graphics state + capture screenshot when viewer becomes ready
  React.useEffect(() => {
    if (!viewerReady || !activeRunId) return;
    // Restore saved graphics state for this run (on initial load)
    if (runGfxMapRef.current[activeRunId]) {
      restoreGfxState(activeRunId);
    }
    // Small delay to let the filtering/coloring effect render first
    const timer = setTimeout(() => void captureScreenshot(), 600);
    return () => clearTimeout(timer);
  }, [viewerReady, activeRunId, captureScreenshot, restoreGfxState]);

  const handleSelectRun = React.useCallback(async (nextRunId) => {
    if (!nextRunId || nextRunId === manifest?.runId) {
      return;
    }

    // Save current graphics state + capture screenshot before switching
    saveGfxState();
    await captureScreenshot();

    // Restore graphics state for the target run
    restoreGfxState(nextRunId);

    setError("");
    setStatus("Loading validation run...");
    setObjectSets({ failed: [], passed: [] });
    setRunId(nextRunId);
  }, [manifest?.runId, captureScreenshot, saveGfxState, restoreGfxState]);

  // Handle back navigation — save state + capture screenshot before leaving
  const handleBackClick = React.useCallback(async (e) => {
    e.preventDefault();
    saveGfxState();
    await captureScreenshot();
    const href = project ? `/?project=${encodeURIComponent(project)}` : "/";
    window.location.href = href;
  }, [captureScreenshot, saveGfxState, project]);

  const handleDeleteRun = React.useCallback(async (targetRunId) => {
    if (!project || !targetRunId) {
      return;
    }

    // Remove screenshot and graphics state for deleted run
    setRunScreenshots((prev) => {
      const next = { ...prev };
      delete next[targetRunId];
      return next;
    });
    setRunGfxMap((prev) => {
      const next = { ...prev };
      delete next[targetRunId];
      return next;
    });

    const confirmed = window.confirm(
      `Delete validation run ${shortId(targetRunId)} from both Design Grammars and Speckle?`
    );
    if (!confirmed) {
      return;
    }

    try {
      setDeletingRunId(targetRunId);
      setError("");
      setStatus("Deleting validation run...");
      await fetchJson(
        `${dataServiceUrl}/validation/run/${encodeURIComponent(project)}/${encodeURIComponent(targetRunId)}`,
        { method: "DELETE" }
      );

      const nextRuns = await loadRuns();
      if (activeRunId === targetRunId) {
        const fallbackRunId = nextRuns[0]?.runId || "";
        setManifest(null);
        setObjectSets({ failed: [], passed: [] });
        setSelectedRuleId("");
        setRunId(fallbackRunId);
        if (fallbackRunId) {
          setStatus("Validation run deleted. Loading the next available run...");
        } else {
          setStatus("Validation run deleted. No runs remain for this project.");
        }
      } else {
        setStatus("Validation run deleted.");
      }
    } catch (err) {
      setError(err.message || "Failed to delete the validation run.");
      setStatus("Validation delete failed.");
    } finally {
      setDeletingRunId("");
    }
  }, [activeRunId, dataServiceUrl, loadRuns, project]);

  const handleIsolate = React.useCallback(() => {
    const ids = new Set(selectedEntityIds);
    if (selectById.trim()) ids.add(selectById.trim());
    if (ids.size === 0) return;
    setIsolatedIds(ids);
    setHiddenIds(new Set());
  }, [selectById, selectedEntityIds]);

  const handleHide = React.useCallback(() => {
    const ids = new Set(selectedEntityIds);
    if (selectById.trim()) ids.add(selectById.trim());
    if (ids.size === 0) return;
    setHiddenIds((prev) => {
      const next = new Set(prev);
      for (const id of ids) next.add(id);
      return next;
    });
    setIsolatedIds(null);
  }, [selectById, selectedEntityIds]);

  const handleSelectByIdKeyDown = React.useCallback((event) => {
    if (event.key === "Enter") {
      handleIsolate();
    }
  }, [handleIsolate]);

  const toggleEntitySelection = React.useCallback((entityId) => {
    setSelectedEntityIds((prev) => {
      const next = new Set(prev);
      if (next.has(entityId)) next.delete(entityId);
      else next.add(entityId);
      return next;
    });
  }, []);

  const rules = manifest?.rules || [];
  const selectedRule = rules.find((rule) => rule.ruleId === selectedRuleId) || null;
  const noSetup = !loading && !error && !manifest;

  return (
    <div className="mv-page">
      <aside className="mv-sidebar">
        <div className="mv-header">
          <div className="mv-header-row">
            <a className="mv-back" href={project ? `/?project=${encodeURIComponent(project)}` : "/"} onClick={handleBackClick}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
              Project
            </a>
            <button type="button" className="mv-back mv-header-connector" onClick={() => setExpandSpeckleConnector(!expandSpeckleConnector)}>
              <span>Speckle connector</span>
              <svg className={`mv-chevron ${expandSpeckleConnector ? "is-open" : ""}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
            </button>
          </div>
          <div className="mv-title">Model Viewer</div>
          <div className="mv-project">{project || "No project selected"}</div>
          {expandSpeckleConnector ? (
            <div className="mv-speckle-panel">
              <div className="mv-speckle-form">
                <label className="mv-speckle-label">Speckle Project Id or URL</label>
                <input
                  className="mv-speckle-input"
                  value={speckleConfig.speckleProjectId}
                  placeholder="Project id or full project URL"
                  onChange={(ev) => setSpeckleConfig((current) => ({ ...current, speckleProjectId: ev.target.value }))}
                />

                <label className="mv-speckle-label">Base Model Id or URL</label>
                <input
                  className="mv-speckle-input"
                  value={speckleConfig.baseModelId}
                  placeholder="Model id or full model URL"
                  onChange={(ev) => setSpeckleConfig((current) => ({ ...current, baseModelId: ev.target.value }))}
                />

                <label className="mv-speckle-label">Base Model Name</label>
                <input
                  className="mv-speckle-input"
                  value={speckleConfig.baseModelName}
                  placeholder="Optional display name"
                  onChange={(ev) => setSpeckleConfig((current) => ({ ...current, baseModelName: ev.target.value }))}
                />

                <label className="mv-speckle-label">Validation Model Id or URL</label>
                <input
                  className="mv-speckle-input"
                  value={speckleConfig.validationModelId}
                  placeholder="Optional id or URL, backend will create if blank"
                  onChange={(ev) => setSpeckleConfig((current) => ({ ...current, validationModelId: ev.target.value }))}
                />

                <div className="mv-speckle-actions">
                  <button type="button" className="mv-speckle-btn" onClick={() => void saveSpeckleConfig()} disabled={loadingSpeckleConfig}>
                    {loadingSpeckleConfig ? "Saving..." : "Save Speckle Link"}
                  </button>
                  <button type="button" className="mv-speckle-btn is-secondary" onClick={() => void loadSpeckleConfig()} disabled={loadingSpeckleConfig}>
                    Reload
                  </button>
                </div>

                <div className="mv-speckle-status">{speckleConfigStatus}</div>

                <div className="mv-speckle-footer">
                  <button type="button" className="mv-speckle-gear" onClick={() => setExpandSpeckleSettings(!expandSpeckleSettings)} title="Speckle settings">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
                    </svg>
                  </button>
                </div>

                {expandSpeckleSettings ? (
                  <div className="mv-speckle-settings">
                    <div className="mv-speckle-settings-title">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="3" />
                        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
                      </svg>
                      Speckle settings
                    </div>
                    <div className="mv-speckle-settings-divider" />

                    <label className="mv-speckle-label">Speckle Base URL</label>
                    <input
                      className="mv-speckle-input"
                      value={speckleSettings.baseUrl}
                      placeholder="http://localhost:8090"
                      onChange={(ev) => setSpeckleSettings((c) => ({ ...c, baseUrl: ev.target.value }))}
                    />

                    <label className="mv-speckle-label">Write Token</label>
                    <input
                      className="mv-speckle-input"
                      type="password"
                      value={speckleSettings.writeToken}
                      placeholder={speckleSettingsMeta.writeTokenConfigured ? "Leave blank to keep stored token" : "Paste Speckle write token"}
                      onChange={(ev) => setSpeckleSettings((c) => ({ ...c, writeToken: ev.target.value }))}
                    />
                    {speckleSettingsMeta.writeTokenConfigured ? (
                      <div className="mv-speckle-token-hint is-ok">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#2fb16f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
                        Stored write token: {speckleSettingsMeta.writeTokenPreview}
                      </div>
                    ) : (
                      <div className="mv-speckle-token-hint">No write token stored yet.</div>
                    )}

                    <label className="mv-speckle-label">Read Token (optional)</label>
                    <input
                      className="mv-speckle-input"
                      type="password"
                      value={speckleSettings.readToken}
                      placeholder={speckleSettingsMeta.readTokenConfigured ? "Leave blank to keep stored token" : "Leave blank to use write token"}
                      onChange={(ev) => setSpeckleSettings((c) => ({ ...c, readToken: ev.target.value }))}
                    />
                    {speckleSettingsMeta.readTokenConfigured ? (
                      <div className="mv-speckle-token-hint is-ok">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#2fb16f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
                        Stored read token: {speckleSettingsMeta.readTokenPreview}
                      </div>
                    ) : (
                      <div className="mv-speckle-token-hint">No separate read token. Viewer uses write token.</div>
                    )}

                    <div className="mv-speckle-settings-divider" />
                    <div className="mv-speckle-actions">
                      <button type="button" className="mv-speckle-btn" onClick={() => void saveSpeckleSettings()} disabled={loadingSpeckleSettings}>
                        {loadingSpeckleSettings ? "Saving..." : "Save Settings"}
                      </button>
                      <button type="button" className="mv-speckle-btn is-secondary" onClick={() => void loadSpeckleSettings()} disabled={loadingSpeckleSettings}>
                        Reload
                      </button>
                    </div>
                    {speckleSettingsStatus ? <div className="mv-speckle-status">{speckleSettingsStatus}</div> : null}
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>

        {error ? <div className="mv-error">{error}</div> : null}
        {loading ? <div className="mv-status">{status}</div> : null}
        {noSetup ? <div className="mv-status">No validation manifest found for this project.</div> : null}

        {manifest ? (
          <>
            <div className="mv-panel">
              <div className="mv-panel-title">Validation Run</div>
              <div className="mv-kv">
                <span>Run Id</span>
                <strong>{manifest.runId}</strong>
              </div>
              <div className="mv-kv">
                <span>Date Created</span>
                <strong>{formatTimestamp(manifest.createdAt)}</strong>
              </div>
              <div className="mv-kv">
                <span>Base Model</span>
                <strong>{manifest.baseModelId}</strong>
              </div>
              <div className="mv-kv">
                <span>Validation Model</span>
                <strong>{manifest.validationModelId}</strong>
              </div>

              <div className="mv-counts-row">
                <div className="mv-count-block">
                  <span className="mv-count-label">Failing</span>
                  <span className="mv-count-value is-fail">{(objectSets.failed || []).length}</span>
                </div>
                <div className="mv-count-block">
                  <span className="mv-count-label">Passing</span>
                  <span className="mv-count-value is-pass">{(objectSets.passed || []).length}</span>
                </div>
              </div>

              <div className={`mv-dropdown ${expandFailing ? "is-open" : ""} is-fail-border`}>
                <button type="button" className="mv-dropdown-header" onClick={() => setExpandFailing(!expandFailing)}>
                  <svg className={`mv-chevron ${expandFailing ? "is-open" : ""}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ff4d4f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
                  <span className="mv-dropdown-label is-fail">Failing items ({(objectSets.failed || []).length})</span>
                </button>
                {expandFailing ? (
                  <div className="mv-dropdown-list">
                    {(objectSets.failed || []).length === 0 ? (
                      <div className="mv-dropdown-empty">No failing items</div>
                    ) : (objectSets.failed || []).map((item, index) => {
                      const id = entityId(item);
                      const label = entityLabel(item);
                      return (
                        <div key={id || index} className={`mv-dropdown-item ${selectedEntityIds.has(id) ? "is-selected" : ""}`} onClick={() => toggleEntitySelection(id)} style={{ cursor: "pointer" }}>
                          <div className="mv-dropdown-item-name">{label}</div>
                          <div className="mv-dropdown-item-id">id: {id}</div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>

              <div className={`mv-dropdown ${expandPassing ? "is-open" : ""} is-pass-border`}>
                <button type="button" className="mv-dropdown-header" onClick={() => setExpandPassing(!expandPassing)}>
                  <svg className={`mv-chevron ${expandPassing ? "is-open" : ""}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2fb16f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6" /></svg>
                  <span className="mv-dropdown-label is-pass">Passing items ({(objectSets.passed || []).length})</span>
                </button>
                {expandPassing ? (
                  <div className="mv-dropdown-list">
                    {(objectSets.passed || []).length === 0 ? (
                      <div className="mv-dropdown-empty">No passing items</div>
                    ) : (objectSets.passed || []).map((item, index) => {
                      const id = entityId(item);
                      const label = entityLabel(item);
                      return (
                        <div key={id || index} className={`mv-dropdown-item ${selectedEntityIds.has(id) ? "is-selected" : ""}`} onClick={() => toggleEntitySelection(id)} style={{ cursor: "pointer" }}>
                          <div className="mv-dropdown-item-name">{label}</div>
                          <div className="mv-dropdown-item-id">id: {id}</div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="mv-panel">
              <div className="mv-panel-title">Rule</div>
              {selectedRule ? (
                <>
                  <div className="mv-kv">
                    <span>Rule_Id</span>
                    <strong className="mv-rule-id-value">{selectedRule.ruleId}</strong>
                  </div>
                  <div className="mv-kv">
                    <span>Description</span>
                    <strong className="mv-rule-desc-value">{selectedRule.ruleDescription || "No description"}</strong>
                  </div>
                  {selectedRule.swrlExpression ? (
                    <div className="mv-kv">
                      <span>SWRL Expression</span>
                      <div className="mv-swrl-block">{selectedRule.swrlExpression}</div>
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="mv-empty-copy">Select a validation run to see rule details.</div>
              )}
            </div>
          </>
        ) : null}

      </aside>

      <div className="mv-right-col">
        <div className="mv-gfx-bar">
          <div className="mv-gfx-group">
            <label className="mv-filter-toggle" onClick={() => setShowFailed(!showFailed)}>
              <span className="mv-checkbox" style={{ background: showFailed ? failColor : "transparent", borderColor: failColor }}>
                {showFailed ? <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg> : null}
              </span>
              <span>Failing</span>
            </label>
            <label className="mv-filter-toggle" onClick={() => setShowPassed(!showPassed)}>
              <span className="mv-checkbox" style={{ background: showPassed ? passColor : "transparent", borderColor: passColor }}>
                {showPassed ? <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg> : null}
              </span>
              <span>Passing</span>
            </label>
            <label className="mv-filter-toggle" onClick={() => setShowBase(!showBase)}>
              <span className="mv-checkbox" style={{ background: showBase ? baseColor : "transparent", borderColor: baseColor }}>
                {showBase ? <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg> : null}
              </span>
              <span>Base model</span>
            </label>
          </div>

          <div className="mv-gfx-sep" />

          <div className="mv-gfx-group">
            <div className="mv-colour-swatch" style={{ background: failColor }} onClick={() => failColorRef.current?.click()} />
            <input ref={failColorRef} type="color" value={failColor} onChange={(e) => setFailColor(e.target.value)} style={{ display: "none" }} />
            <span className="mv-gfx-label">Fail</span>
            <div className="mv-colour-swatch" style={{ background: passColor }} onClick={() => passColorRef.current?.click()} />
            <input ref={passColorRef} type="color" value={passColor} onChange={(e) => setPassColor(e.target.value)} style={{ display: "none" }} />
            <span className="mv-gfx-label">Pass</span>
            <div className="mv-colour-swatch" style={{ background: baseColor }} onClick={() => baseColorRef.current?.click()} />
            <input ref={baseColorRef} type="color" value={baseColor} onChange={(e) => setBaseColor(e.target.value)} style={{ display: "none" }} />
            <span className="mv-gfx-label">Base</span>
          </div>

          <div className="mv-gfx-sep" />

          <div className="mv-gfx-group">
            <span className="mv-gfx-label">Fail α</span>
            <input type="range" className="mv-opacity-slider" min="0" max="100" value={failOpacity} onChange={(e) => setFailOpacity(Number(e.target.value))} style={{ accentColor: failColor }} />
            <span className="mv-gfx-value">{failOpacity}%</span>

            <span className="mv-gfx-label">Pass α</span>
            <input type="range" className="mv-opacity-slider" min="0" max="100" value={passOpacity} onChange={(e) => setPassOpacity(Number(e.target.value))} style={{ accentColor: passColor }} />
            <span className="mv-gfx-value">{passOpacity}%</span>

            <span className="mv-gfx-label">Base α</span>
            <input type="range" className="mv-opacity-slider" min="0" max="100" value={baseOpacity} onChange={(e) => setBaseOpacity(Number(e.target.value))} style={{ accentColor: baseColor }} />
            <span className="mv-gfx-value">{baseOpacity}%</span>
          </div>

          <div className="mv-gfx-sep" />

          <div className="mv-search-bar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#98a4bd" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /></svg>
            <input
              type="text"
              className="mv-search-input"
              placeholder="Select by Id..."
              value={selectById}
              onChange={(e) => setSelectById(e.target.value)}
              onKeyDown={handleSelectByIdKeyDown}
            />
          </div>
        </div>

        <div className="mv-actions-bar">
          <button type="button" className="mv-action-btn is-isolate" onClick={handleIsolate}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>
            Isolate
          </button>
          <button type="button" className="mv-action-btn is-hide" onClick={handleHide}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94" /><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
            Hide
          </button>
          {(isolatedIds || hiddenIds.size > 0) ? (
            <button type="button" className="mv-action-btn is-reset" onClick={() => { setIsolatedIds(null); setHiddenIds(new Set()); }}>
              Reset View
            </button>
          ) : null}
        </div>

        <main className="mv-canvas-wrap">
          <div ref={viewerHostRef} className="mv-canvas" />
          {!manifest && !loading ? (
            <div className="mv-empty-state">
              <div className="mv-empty-title">Viewer unavailable</div>
              <div className="mv-empty-copy">
                Configure the project Speckle link in Design Grammars and publish a validation run first.
              </div>
            </div>
          ) : null}
        </main>

        <ValidationRunsStrip
          project={project}
          validationRuns={validationRuns}
          runsLoading={runsLoading}
          error={runsError}
          onRetry={loadRuns}
          activeRunId={activeRunId}
          deletingRunId={deletingRunId}
          runScreenshots={runScreenshots}
          onSelectRun={handleSelectRun}
          onDeleteRun={handleDeleteRun}
        />
      </div>
    </div>
  );
}
