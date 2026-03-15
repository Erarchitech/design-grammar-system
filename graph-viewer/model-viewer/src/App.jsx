import React from "react";
import {
  CameraController,
  DefaultViewerParams,
  FilteringExtension,
  SelectionExtension,
  SpeckleLoader,
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

function collectValidationObjects(worldTree, runId) {
  const entityMap = new Map();
  const allValidationObjectIds = [];
  const nodes = worldTree.findAll((node) => {
    const raw = node.model?.raw;
    return raw && raw.validationRunId === runId && raw.dgEntityId;
  });

  for (const node of nodes) {
    const dgEntityId = node.model.raw.dgEntityId;
    const objectId = node.model.id;
    if (!dgEntityId || !objectId) {
      continue;
    }

    allValidationObjectIds.push(objectId);
    if (!entityMap.has(dgEntityId)) {
      entityMap.set(dgEntityId, []);
    }
    entityMap.get(dgEntityId).push(objectId);
  }

  return {
    entityMap,
    allValidationObjectIds: Array.from(new Set(allValidationObjectIds))
  };
}

function extractEntityId(entry) {
  if (typeof entry === "string") {
    return entry;
  }
  return entry?.dgEntityId || "";
}

function extractEntityIds(entries) {
  return (entries || []).map(extractEntityId).filter(Boolean);
}

function flattenObjectIds(entityMap, entries) {
  const objectIds = [];
  for (const entry of entries || []) {
    const entityId = extractEntityId(entry);
    if (!entityId) {
      continue;
    }
    const mapped = entityMap.get(entityId) || [];
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
  const [status, setStatus] = React.useState("Loading validation viewer...");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [runsLoading, setRunsLoading] = React.useState(true);
  const [deletingRunId, setDeletingRunId] = React.useState("");
  const [failedExpanded, setFailedExpanded] = React.useState(true);
  const [passedExpanded, setPassedExpanded] = React.useState(true);

  const viewerHostRef = React.useRef(null);
  const viewerRef = React.useRef(null);
  const filteringRef = React.useRef(null);
  const entityMapRef = React.useRef(new Map());
  const allValidationObjectIdsRef = React.useRef([]);
  const loadedRunIdRef = React.useRef("");
  const activeRunId = runId || manifest?.runId || "";

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

  const loadManifest = React.useCallback(async () => {
    if (!project) {
      setLoading(false);
      setError("Project query parameter is required.");
      return;
    }

    if (!runId && !runsLoading && validationRuns.length === 0) {
      setManifest(null);
      setObjectSets({ failed: [], passed: [] });
      setSelectedRuleId("");
      setLoading(false);
      setError("");
      setStatus("No validation runs found for this project.");
      return;
    }

    const manifestUrl = runId
      ? `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}/${encodeURIComponent(runId)}`
      : `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}`;

    try {
      setLoading(true);
      setError("");
      setObjectSets({ failed: [], passed: [] });
      const response = await fetchJson(manifestUrl);
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
      setLoading(false);
    }
  }, [dataServiceUrl, project, runId, runsLoading, validationRuns.length]);

  React.useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  React.useEffect(() => {
    void loadManifest();
  }, [loadManifest]);

  React.useEffect(() => {
    if (!manifest || !viewerHostRef.current || loadedRunIdRef.current === manifest.runId) {
      return undefined;
    }

    let disposed = false;

    const initViewer = async () => {
      setStatus("Initializing Speckle viewer...");
      const viewer = new Viewer(viewerHostRef.current, {
        ...DefaultViewerParams,
        verbose: false,
        showStats: false
      });
      await viewer.init();
      viewer.createExtension(CameraController);
      viewer.createExtension(SelectionExtension);
      const filtering = viewer.createExtension(FilteringExtension);
      viewerRef.current = viewer;
      filteringRef.current = filtering;

      const resourceUrls = [manifest.baseResourceUrl, manifest.validationResourceUrl].filter(Boolean);
      for (const resourceUrl of resourceUrls) {
        const urls = await UrlHelper.getResourceUrls(resourceUrl);
        for (const url of urls) {
          const loader = new SpeckleLoader(
            viewer.getWorldTree(),
            url,
            manifest.readToken || config.speckleReadToken || undefined
          );
          await viewer.loadObject(loader, true);
        }
      }

      if (disposed) {
        return;
      }

      const collected = collectValidationObjects(viewer.getWorldTree(), manifest.runId);
      entityMapRef.current = collected.entityMap;
      allValidationObjectIdsRef.current = collected.allValidationObjectIds;
      loadedRunIdRef.current = manifest.runId;
      setStatus("Viewer ready.");
    };

    void initViewer().catch((err) => {
      setError(err.message || "Failed to initialize the Speckle viewer.");
      setStatus("Viewer initialization failed.");
    });

    return () => {
      disposed = true;
      if (viewerRef.current) {
        viewerRef.current.dispose();
        viewerRef.current = null;
      }
      filteringRef.current = null;
      entityMapRef.current = new Map();
      allValidationObjectIdsRef.current = [];
      loadedRunIdRef.current = "";
    };
  }, [manifest]);

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

  React.useEffect(() => {
    const filtering = filteringRef.current;
    if (!filtering || !selectedRuleId) {
      return;
    }

    filtering.resetFilters();
    const entityMap = entityMapRef.current;
    const allValidationObjectIds = allValidationObjectIdsRef.current;
    const failedObjectIds = showFailed ? flattenObjectIds(entityMap, objectSets.failed) : [];
    const passedObjectIds = showPassed ? flattenObjectIds(entityMap, objectSets.passed) : [];
    const visibleObjectIds = new Set([...failedObjectIds, ...passedObjectIds]);
    const hiddenObjectIds = allValidationObjectIds.filter((id) => !visibleObjectIds.has(id));

    if (hiddenObjectIds.length > 0) {
      filtering.hideObjects(hiddenObjectIds, "dg-validation", true, false);
    }

    const colorGroups = [];
    if (failedObjectIds.length > 0) {
      colorGroups.push({
        objectIds: failedObjectIds,
        color: "#ff4d4f"
      });
    }
    if (passedObjectIds.length > 0) {
      colorGroups.push({
        objectIds: passedObjectIds,
        color: "#2fb16f"
      });
    }
    if (colorGroups.length > 0) {
      filtering.setUserObjectColors(colorGroups);
    }
  }, [objectSets, selectedRuleId, showFailed, showPassed]);

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

  const rules = manifest?.rules || [];
  const selectedRule = rules.find((rule) => rule.ruleId === selectedRuleId) || null;
  const noSetup = !loading && !error && !manifest;
  const noMappedGeometry = manifest && selectedRuleId && (objectSets.failed.length + objectSets.passed.length === 0);

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

        <div className="mv-panel">
          <div className="mv-panel-header">
            <div className="mv-panel-title">Validation Runs</div>
            <div className="mv-panel-meta">{validationRuns.length}</div>
          </div>
          {runsLoading ? <div className="mv-empty-copy">Loading validation runs...</div> : null}
          {!runsLoading && validationRuns.length === 0 ? (
            <div className="mv-empty-copy">No validation runs have been published for this project yet.</div>
          ) : null}
          {!runsLoading && validationRuns.length > 0 ? (
            <div className="mv-runs-list">
              {validationRuns.map((run) => {
                const isActive = run.runId === activeRunId;
                const isDeleting = deletingRunId === run.runId;
                return (
                  <div key={run.runId} className={`mv-run-row ${isActive ? "is-active" : ""}`}>
                    <button
                      type="button"
                      className="mv-run-button"
                      onClick={() => handleSelectRun(run.runId)}
                      disabled={isDeleting}
                    >
                      <div className="mv-run-id">{shortId(run.runId)}</div>
                      <div className="mv-run-meta">{formatTimestamp(run.createdAt)}</div>
                      <div className="mv-run-meta">
                        {run.entityCount} mapped entities • {run.failedRuleCount}/{run.ruleCount} failing rules
                      </div>
                    </button>
                    <button
                      type="button"
                      className="mv-delete-button"
                      onClick={() => void handleDeleteRun(run.runId)}
                      disabled={isDeleting}
                    >
                      {isDeleting ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>

        {manifest ? (
          <>
            <div className="mv-panel">
              <div className="mv-panel-title">Validation Run</div>
              <div className="mv-kv">
                <span>Run</span>
                <strong>{manifest.runId}</strong>
              </div>
              <div className="mv-kv">
                <span>Created</span>
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
            </div>

            <div className="mv-panel">
              <div className="mv-panel-title">Rule</div>
              <select
                className="mv-select"
                value={selectedRuleId}
                onChange={(event) => setSelectedRuleId(event.target.value)}
              >
                {rules.map((rule) => (
                  <option key={rule.ruleId} value={rule.ruleId}>
                    {rule.ruleId}
                  </option>
                ))}
              </select>
              {selectedRule ? (
                <div className="mv-rule-summary">
                  <div className={`mv-badge ${selectedRule.passed ? "is-pass" : "is-fail"}`}>
                    {selectedRule.passed ? "Pass" : "Fail"}
                  </div>
                  <div className="mv-rule-name">{selectedRule.ruleName || selectedRule.ruleId}</div>
                  <div className="mv-rule-description">{selectedRule.ruleDescription || "No description"}</div>
                </div>
              ) : null}
            </div>

            <div className="mv-panel">
              <div className="mv-panel-title">Overlay</div>
              <label className="mv-toggle">
                <input type="checkbox" checked={showFailed} onChange={(event) => setShowFailed(event.target.checked)} />
                <span>Show failing elements</span>
              </label>
              <label className="mv-toggle">
                <input type="checkbox" checked={showPassed} onChange={(event) => setShowPassed(event.target.checked)} />
                <span>Show passing elements</span>
              </label>
              {noMappedGeometry ? (
                <div className="mv-note">
                  No mapped geometry was published for the selected rule in this validation run.
                </div>
              ) : null}
            </div>

            {(objectSets.failed || []).length > 0 ? (
              <div className="mv-panel mv-entity-list is-fail">
                <button
                  type="button"
                  className="mv-entity-list-header"
                  onClick={() => setFailedExpanded((prev) => !prev)}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ff4d4f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: failedExpanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.15s" }}><path d="M6 9l6 6 6-6" /></svg>
                  <span className="mv-entity-list-label is-fail">Failing items ({(objectSets.failed || []).length})</span>
                </button>
                {failedExpanded ? (
                  <div className="mv-entity-items">
                    {(objectSets.failed || []).map((entry) => {
                      const entityId = extractEntityId(entry);
                      const displayName = (typeof entry === "object" && entry?.displayName) || entityId;
                      return (
                        <div key={entityId} className="mv-entity-item">
                          <div className="mv-entity-name">{displayName}</div>
                          <div className="mv-entity-id">id: {entityId}</div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            ) : null}

            {(objectSets.passed || []).length > 0 ? (
              <div className="mv-panel mv-entity-list is-pass">
                <button
                  type="button"
                  className="mv-entity-list-header"
                  onClick={() => setPassedExpanded((prev) => !prev)}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2fb16f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: passedExpanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.15s" }}><path d="M6 9l6 6 6-6" /></svg>
                  <span className="mv-entity-list-label is-pass">Passing items ({(objectSets.passed || []).length})</span>
                </button>
                {passedExpanded ? (
                  <div className="mv-entity-items">
                    {(objectSets.passed || []).map((entry) => {
                      const entityId = extractEntityId(entry);
                      const displayName = (typeof entry === "object" && entry?.displayName) || entityId;
                      return (
                        <div key={entityId} className="mv-entity-item">
                          <div className="mv-entity-name">{displayName}</div>
                          <div className="mv-entity-id">id: {entityId}</div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            ) : null}
          </>
        ) : null}
      </aside>

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
    </div>
  );
}
