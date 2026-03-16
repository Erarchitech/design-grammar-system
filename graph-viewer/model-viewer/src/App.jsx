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

function hexWithAlpha(hex, opacityPercent) {
  const alpha = Math.round((opacityPercent / 100) * 255);
  return hex + alpha.toString(16).padStart(2, "0");
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
  const [deletingRunId, setDeletingRunId] = React.useState("");

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

  const loadRuns = React.useCallback(async () => {
    if (!project) {
      setValidationRuns([]);
      setRunsLoading(false);
      return [];
    }

    const runsUrl = `${dataServiceUrl}/validation/runs/${encodeURIComponent(project)}`;

    try {
      setRunsLoading(true);
      const response = await fetchJson(runsUrl);
      const runs = Array.isArray(response?.runs) ? response.runs : [];
      setValidationRuns(runs);
      return runs;
    } catch (err) {
      setValidationRuns([]);
      setError(err.message || "Failed to load validation runs.");
      return [];
    } finally {
      setRunsLoading(false);
    }
  }, [dataServiceUrl, project]);

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
      colorGroups.push({ objectIds: failedObjectIds, color: hexWithAlpha(failColor, failOpacity) });
    }
    if (passedObjectIds.length > 0) {
      colorGroups.push({ objectIds: passedObjectIds, color: hexWithAlpha(passColor, passOpacity) });
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

    // Force the viewer to re-render after filter changes
    const viewer = viewerRef.current;
    if (viewer) {
      viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
    }
  }, [viewerReady, objectSets, selectedRuleId, showFailed, showPassed, showBase,
      failColor, passColor, failOpacity, passOpacity, baseOpacity, isolatedIds, hiddenIds]);

  const handleSelectRun = React.useCallback((nextRunId) => {
    if (!nextRunId || nextRunId === manifest?.runId) {
      return;
    }

    setError("");
    setStatus("Loading validation run...");
    setObjectSets({ failed: [], passed: [] });
    setRunId(nextRunId);
  }, [manifest?.runId]);

  const handleDeleteRun = React.useCallback(async (targetRunId) => {
    if (!project || !targetRunId) {
      return;
    }

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
          <a className="mv-back" href={project ? `/?project=${encodeURIComponent(project)}` : "/"}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5" /><path d="M12 19l-7-7 7-7" /></svg>
            Project
          </a>
          <div className="mv-title">Model Viewer</div>
          <div className="mv-project">{project || "No project selected"}</div>
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

        <div className="mv-bottom-strip">
          <div className="mv-strip-header">
            <span className="mv-strip-title">VALIDATION RUNS</span>
            <span className="mv-strip-badge">{validationRuns.length}</span>
          </div>
          {runsLoading ? <div className="mv-empty-copy">Loading...</div> : null}
          {!runsLoading && validationRuns.length === 0 ? (
            <div className="mv-empty-copy">No validation runs yet.</div>
          ) : null}
          <div className="mv-tile-strip">
            {validationRuns.map((run) => {
              const isActive = run.runId === activeRunId;
              const isDeleting = deletingRunId === run.runId;
              return (
                <div key={run.runId} className={`mv-tile ${isActive ? "is-active" : ""}`}>
                  <div className="mv-tile-header">
                    <button
                      type="button"
                      className="mv-tile-rule-id"
                      onClick={() => handleSelectRun(run.runId)}
                      disabled={isDeleting}
                    >
                      {run.ruleIds?.[0] || shortId(run.runId)}
                    </button>
                    <button
                      type="button"
                      className="mv-tile-delete"
                      onClick={() => void handleDeleteRun(run.runId)}
                      disabled={isDeleting}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                    </button>
                  </div>
                  <div className="mv-tile-thumb" onClick={() => handleSelectRun(run.runId)} />
                  <div className="mv-tile-footer">
                    <div className="mv-tile-date">{formatTimestamp(run.createdAt)}</div>
                    <div className={`mv-tile-kind ${run.failedRuleCount > 0 ? "is-fail" : "is-pass"}`}>
                      {run.failedRuleCount > 0 ? "Constraint" : "Requirement"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
