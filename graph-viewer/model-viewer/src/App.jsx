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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return response.json();
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

function flattenObjectIds(entityMap, entityIds) {
  const objectIds = [];
  for (const entityId of entityIds || []) {
    const mapped = entityMap.get(entityId) || [];
    objectIds.push(...mapped);
  }
  return Array.from(new Set(objectIds));
}

export default function App() {
  const [project] = React.useState(initialProject);
  const [runId, setRunId] = React.useState(initialRunId);
  const [manifest, setManifest] = React.useState(null);
  const [selectedRuleId, setSelectedRuleId] = React.useState(initialRuleId);
  const [objectSets, setObjectSets] = React.useState({ failed: [], passed: [] });
  const [showFailed, setShowFailed] = React.useState(true);
  const [showPassed, setShowPassed] = React.useState(true);
  const [status, setStatus] = React.useState("Loading validation viewer...");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(true);

  const viewerHostRef = React.useRef(null);
  const viewerRef = React.useRef(null);
  const filteringRef = React.useRef(null);
  const entityMapRef = React.useRef(new Map());
  const allValidationObjectIdsRef = React.useRef([]);
  const loadedRunIdRef = React.useRef("");

  const loadManifest = React.useCallback(async () => {
    if (!project) {
      setLoading(false);
      setError("Project query parameter is required.");
      return;
    }

    const dataServiceUrl = normalizeUrl(config.dataServiceUrl || "/data-service");
    const manifestUrl = runId
      ? `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}/${encodeURIComponent(runId)}`
      : `${dataServiceUrl}/validation/view/${encodeURIComponent(project)}`;

    try {
      setLoading(true);
      setError("");
      const response = await fetchJson(manifestUrl);
      setManifest(response);
      setRunId(response.runId || "");
      if (!selectedRuleId) {
        const firstRule = (response.rules || [])[0];
        if (firstRule?.ruleId) {
          setSelectedRuleId(firstRule.ruleId);
        }
      }
      setStatus("Validation manifest loaded.");
    } catch (err) {
      setError(err.message || "Failed to load validation manifest.");
      setStatus("Validation manifest is unavailable.");
    } finally {
      setLoading(false);
    }
  }, [project, runId, selectedRuleId]);

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

    const dataServiceUrl = normalizeUrl(config.dataServiceUrl || "/data-service");
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
  }, [manifest, project, selectedRuleId]);

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

  const rules = manifest?.rules || [];
  const selectedRule = rules.find((rule) => rule.ruleId === selectedRuleId) || null;
  const noSetup = !loading && !error && !manifest;
  const noMappedGeometry = manifest && selectedRuleId && (objectSets.failed.length + objectSets.passed.length === 0);

  return (
    <div className="mv-page">
      <aside className="mv-sidebar">
        <div className="mv-header">
          <a className="mv-back" href="/">
            Back To DG
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
                <span>Run</span>
                <strong>{manifest.runId}</strong>
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
              <div className="mv-counts">
                <div>Failing: {(objectSets.failed || []).length}</div>
                <div>Passing: {(objectSets.passed || []).length}</div>
              </div>
              {noMappedGeometry ? (
                <div className="mv-note">
                  No mapped geometry was published for the selected rule in this validation run.
                </div>
              ) : null}
            </div>
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
