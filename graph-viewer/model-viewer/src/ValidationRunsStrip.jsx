import React from "react";
import { useValidationRunsGrouping } from "./useValidationRunsGrouping.js";

const STORAGE_KEY_PREFIX = "dg_run_grouping_";
const DEFAULT_MODE = "rule";
const DEFAULT_HEIGHT = 200;
const MIN_HEIGHT = 120;
const MAX_HEIGHT_RATIO = 0.8;

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

function clampHeight(value) {
  const max = typeof window !== "undefined" ? Math.floor(window.innerHeight * MAX_HEIGHT_RATIO) : 800;
  if (typeof value !== "number" || Number.isNaN(value)) return DEFAULT_HEIGHT;
  return Math.max(MIN_HEIGHT, Math.min(max, value));
}

function loadPersistedState(project) {
  if (!project) return { mode: DEFAULT_MODE, collapsed: {}, height: DEFAULT_HEIGHT };
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${project}`);
    if (!raw) return { mode: DEFAULT_MODE, collapsed: {}, height: DEFAULT_HEIGHT };
    const parsed = JSON.parse(raw);
    const mode = parsed && (parsed.mode === "state" || parsed.mode === "rule") ? parsed.mode : DEFAULT_MODE;
    const collapsed = parsed && typeof parsed.collapsed === "object" && parsed.collapsed !== null ? parsed.collapsed : {};
    const height = parsed && typeof parsed.height === "number" ? clampHeight(parsed.height) : DEFAULT_HEIGHT;
    return { mode, collapsed, height };
  } catch {
    return { mode: DEFAULT_MODE, collapsed: {}, height: DEFAULT_HEIGHT };
  }
}

function persistState(project, mode, collapsed, height) {
  if (!project) return;
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}${project}`, JSON.stringify({ mode, collapsed, height }));
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
  const [height, setHeight] = React.useState(initial.height);
  const dragRef = React.useRef(null);

  // Reload persisted state whenever project changes (different localStorage key).
  React.useEffect(() => {
    const next = loadPersistedState(project);
    setMode(next.mode);
    setCollapsed(next.collapsed);
    setHeight(next.height);
  }, [project]);

  // Persist on any change.
  React.useEffect(() => {
    persistState(project, mode, collapsed, height);
  }, [project, mode, collapsed, height]);

  // Re-clamp height on window resize so MAX_HEIGHT_RATIO stays honored.
  React.useEffect(() => {
    const handleResize = () => setHeight((h) => clampHeight(h));
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleResizeStart = (event) => {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = height;
    dragRef.current = { startY, startHeight };

    const onMove = (e) => {
      if (!dragRef.current) return;
      // Drag UP increases strip height (handle at top); drag DOWN decreases.
      const delta = dragRef.current.startY - e.clientY;
      setHeight(clampHeight(dragRef.current.startHeight + delta));
    };
    const onUp = () => {
      dragRef.current = null;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "ns-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const handleResizeKey = (event) => {
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setHeight((h) => clampHeight(h + 16));
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setHeight((h) => clampHeight(h - 16));
    } else if (event.key === "Home") {
      event.preventDefault();
      setHeight(DEFAULT_HEIGHT);
    }
  };

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
    <div className="mv-bottom-strip" style={{ height: `${height}px` }}>
      <div
        className="mv-strip-resize-handle"
        role="separator"
        aria-label="Resize validation runs strip"
        aria-orientation="horizontal"
        aria-valuenow={height}
        aria-valuemin={MIN_HEIGHT}
        tabIndex={0}
        onPointerDown={handleResizeStart}
        onKeyDown={handleResizeKey}
        title="Drag to resize. Arrow keys to adjust. Home to reset."
      />
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

      <div className="mv-strip-content">
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
    </div>
  );
}
