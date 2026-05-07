import React from "react";
import { useValidationRunsGrouping } from "./useValidationRunsGrouping.js";

const STORAGE_KEY_PREFIX = "dg_run_grouping_";
const DEFAULT_MODE = "rule";

function shortId(value) {
  if (!value) return "Unknown";
  if (value.length <= 16) return value;
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function formatTimestamp(value) {
  if (!value) return "Unknown time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function loadPersistedState(project) {
  if (!project) return { mode: DEFAULT_MODE, collapsed: {} };
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${project}`);
    if (!raw) return { mode: DEFAULT_MODE, collapsed: {} };
    const parsed = JSON.parse(raw);
    const mode = parsed && (parsed.mode === "state" || parsed.mode === "rule") ? parsed.mode : DEFAULT_MODE;
    const collapsed = parsed && typeof parsed.collapsed === "object" && parsed.collapsed !== null ? parsed.collapsed : {};
    return { mode, collapsed };
  } catch {
    return { mode: DEFAULT_MODE, collapsed: {} };
  }
}

function persistState(project, mode, collapsed) {
  if (!project) return;
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}${project}`, JSON.stringify({ mode, collapsed }));
  } catch {
    // localStorage quota / disabled — silent
  }
}

export default function ValidationRunsStrip({
  project,
  validationRuns,
  runsLoading,
  error,
  onRetry,
  activeRunId,
  deletingRunId,
  runScreenshots,
  onSelectRun,
  onDeleteRun,
}) {
  const initial = React.useMemo(() => loadPersistedState(project), [project]);
  const [mode, setMode] = React.useState(initial.mode);
  const [collapsed, setCollapsed] = React.useState(initial.collapsed);

  // Reload persisted state whenever project changes (different localStorage key).
  React.useEffect(() => {
    const next = loadPersistedState(project);
    setMode(next.mode);
    setCollapsed(next.collapsed);
  }, [project]);

  // Persist on any change.
  React.useEffect(() => {
    persistState(project, mode, collapsed);
  }, [project, mode, collapsed]);

  const groups = React.useMemo(
    () => useValidationRunsGrouping(validationRuns, mode),
    [validationRuns, mode]
  );

  const handleModeChange = (next) => {
    setMode(next);
    // Filter context (showFailed, isolatedIds, selectedEntityIds, etc.) lives in App.jsx
    // and is NOT touched here — by construction, switching grouping preserves it.
  };

  const toggleCollapse = (groupKey) => {
    setCollapsed((prev) => {
      const next = { ...prev };
      if (next[groupKey]) delete next[groupKey];
      else next[groupKey] = true;
      return next;
    });
  };

  const totalRuns = Array.isArray(validationRuns) ? validationRuns.length : 0;
  const hasError = typeof error === "string" && error.length > 0;

  return (
    <div className="mv-bottom-strip">
      <div className="mv-strip-header">
        <span className="mv-strip-title">VALIDATION RUNS</span>
        <span className="mv-strip-badge">{totalRuns}</span>
        <div
          className="mv-group-switch"
          role="radiogroup"
          aria-label="Group by"
        >
          <span className="mv-group-switch-label">Group by</span>
          <button
            type="button"
            role="radio"
            aria-checked={mode === "rule"}
            className={`mv-group-switch-opt ${mode === "rule" ? "is-active" : ""}`}
            onClick={() => handleModeChange("rule")}
          >
            Rule
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={mode === "state"}
            className={`mv-group-switch-opt ${mode === "state" ? "is-active" : ""}`}
            onClick={() => handleModeChange("state")}
          >
            Design State
          </button>
        </div>
      </div>

      {hasError ? (
        <div className="mv-error-copy" role="alert">
          <span>Could not load grouped runs. Try again.</span>
          <button
            type="button"
            className="mv-error-retry"
            onClick={() => { if (typeof onRetry === "function") onRetry(); }}
          >
            Try again
          </button>
        </div>
      ) : null}

      {!hasError && runsLoading ? <div className="mv-empty-copy">Loading...</div> : null}
      {!hasError && !runsLoading && totalRuns === 0 ? (
        <div className="mv-empty-copy">No validation runs match current filters.</div>
      ) : null}

      {!hasError && !runsLoading && totalRuns > 0
        ? groups.map((group) => {
            const isCollapsed = !!collapsed[group.groupKey];
            const headerId = `mv-group-${encodeURIComponent(group.groupKey)}`;
            return (
              <div key={group.groupKey} className="mv-run-group">
                <button
                  type="button"
                  id={headerId}
                  className={`mv-run-group-header ${isCollapsed ? "is-collapsed" : ""}`}
                  onClick={() => toggleCollapse(group.groupKey)}
                  aria-expanded={!isCollapsed}
                >
                  <svg
                    className={`mv-chevron ${isCollapsed ? "" : "is-open"}`}
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                  <span className="mv-run-group-label">{group.groupLabel}</span>
                  <span className="mv-run-group-count">{group.runs.length}</span>
                </button>
                {!isCollapsed ? (
                  <div className="mv-tile-strip" role="group" aria-labelledby={headerId}>
                    {group.runs.map((run) => {
                      const isActive = run.runId === activeRunId;
                      const isDeleting = deletingRunId === run.runId;
                      return (
                        <div
                          key={run.runId}
                          className={`mv-tile ${isActive ? "is-active" : ""}`}
                        >
                          <div className="mv-tile-header">
                            <button
                              type="button"
                              className="mv-tile-rule-id"
                              onClick={() => onSelectRun(run.runId)}
                              disabled={isDeleting}
                            >
                              {run.ruleIds?.[0] || shortId(run.runId)}
                            </button>
                            <button
                              type="button"
                              className="mv-tile-delete"
                              onClick={() => void onDeleteRun(run.runId)}
                              disabled={isDeleting}
                              aria-label="Delete run"
                            >
                              <svg
                                width="12"
                                height="12"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <line x1="18" y1="6" x2="6" y2="18" />
                                <line x1="6" y1="6" x2="18" y2="18" />
                              </svg>
                            </button>
                          </div>
                          <div
                            className="mv-tile-thumb"
                            onClick={() => onSelectRun(run.runId)}
                            style={
                              runScreenshots[run.runId]
                                ? {
                                    backgroundImage: `url(${runScreenshots[run.runId]})`,
                                    backgroundSize: "cover",
                                    backgroundPosition: "center",
                                  }
                                : undefined
                            }
                          />
                          <div className="mv-tile-footer">
                            <div className="mv-tile-date">{formatTimestamp(run.createdAt)}</div>
                            <div
                              className={`mv-tile-kind ${run.failedRuleCount > 0 ? "is-fail" : "is-pass"}`}
                            >
                              {run.failedRuleCount > 0 ? "Constraint" : "Requirement"}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })
        : null}
    </div>
  );
}
