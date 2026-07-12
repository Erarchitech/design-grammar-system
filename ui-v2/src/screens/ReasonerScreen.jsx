import React from "react";
import { Button, Badge } from "../components/index.js";
import {
  getReasonerSettings,
  selectReasoner,
  runConsistencyCheck,
} from "../lib/reasonerApi.js";

// Lifted verbatim from SessionHistory.jsx L27-40 (module-private there) —
// the one relative-time convention in this codebase; do not write a second one.
function formatRelativeDate(isoString) {
  if (!isoString) return "";
  const then = new Date(isoString).getTime();
  if (Number.isNaN(then)) return "";
  const diffMs = Date.now() - then;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return diffMin + "m ago";
  if (diffHr < 24) return diffHr + "h ago";
  if (diffDay < 7) return diffDay + "d ago";
  return String(isoString).slice(0, 10);
}

// Reasoner region — ontology reasoner selector for the Validation Graph.
// HermiT is the one live/integrated engine (Phase 822) — its card runs a real
// schema-consistency check. Pellet remains a clearly-labeled placeholder
// ("integration pending" — selection persists server-side but does not yet
// drive validation). Selection survives revisits (Phase 814: REAS-01..03).
export default function ReasonerScreen({ active, onBack, project }) {
  const [reasoners, setReasoners] = React.useState([]);
  const [selected, setSelected] = React.useState(null);

  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState("");

  const [saving, setSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState("");

  // ── Consistency-check run-state machine (HermiT card, D-01/D-07/D-08/D-09/D-11) ──
  const [runState, setRunState] = React.useState("idle");
  const [runError, setRunError] = React.useState("");
  const [runResult, setRunResult] = React.useState(null);
  const [lastCheckedAt, setLastCheckedAt] = React.useState(null);
  const [elapsedSec, setElapsedSec] = React.useState(0);
  const abortRef = React.useRef(null);

  // ── Load settings when screen becomes active ──
  React.useEffect(() => {
    if (!active) return;
    setLoading(true);
    setLoadError("");
    setSaveError("");
    getReasonerSettings()
      .then((s) => {
        setReasoners(s.reasoners || []);
        setSelected(s.selected || null);
      })
      .catch((err) => setLoadError(err.message || "Failed to load settings"))
      .finally(() => setLoading(false));
  }, [active]);

  // ── Select a reasoner ──
  const handleSelect = async (id) => {
    if (id === selected) return; // already selected
    setSaving(true);
    setSaveError("");
    try {
      const result = await selectReasoner(id);
      setSelected(result.selected || null);
    } catch (err) {
      setSaveError(err.message || "Failed to save selection");
    } finally {
      setSaving(false);
    }
  };

  // ── Retry load ──
  const handleRetry = () => {
    setLoading(true);
    setLoadError("");
    getReasonerSettings()
      .then((s) => {
        setReasoners(s.reasoners || []);
        setSelected(s.selected || null);
      })
      .catch((err) => setLoadError(err.message || "Failed to load settings"))
      .finally(() => setLoading(false));
  };

  // ── Run a schema-consistency check (HermiT card only, D-04/D-05) ──
  const handleRunCheck = async () => {
    const controller = new AbortController();
    abortRef.current = controller;
    setRunState("running");
    setRunError("");
    setElapsedSec(0);
    const t0 = Date.now();
    const timer = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - t0) / 1000));
    }, 1000);
    try {
      const result = await runConsistencyCheck(project, {
        signal: controller.signal,
      });
      const body = result.body || {};
      // RESEARCH Pitfall 1 — 504 is ambiguous; branch on body shape, not status.
      if (body.error === "timeout" && "consistent" in body) {
        // Genuine sidecar semantic timeout — Unknown/Inconclusive (D-08).
        setRunResult(body);
        setRunState("unknown");
        setLastCheckedAt(new Date().toISOString());
      } else if (!result.ok) {
        // Transport/hard error — distinct error line, never folded into Unknown (D-09).
        setRunError(body?.detail?.error || "Reasoner unavailable");
        setRunState("error");
      } else {
        setRunResult(body);
        setRunState(body.consistent ? "consistent" : "inconsistent");
        setLastCheckedAt(new Date().toISOString());
      }
    } catch (err) {
      if (err.name === "AbortError") {
        setRunState("cancelled"); // D-07 — kept distinct from Unknown
      } else {
        setRunError(err.message || "Reasoner unavailable");
        setRunState("error");
      }
    } finally {
      clearInterval(timer);
      abortRef.current = null;
    }
  };

  // ── Cancel the in-flight check (client-side abort only, D-07) ──
  const handleCancel = () => {
    abortRef.current?.abort();
  };

  // ── Render ──
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "var(--surface-canvas)",
        overflow: "auto",
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "28px 40px 60px",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          gap: 28,
        }}
      >
        {/* ── Header ── */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← Back
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
              Region · Reasoner
            </div>
            <div style={{ font: "600 34px/1.1 var(--font-sans)", letterSpacing: "-1.2px" }}>
              Reasoner.
            </div>
          </div>
        </div>

        {/* ── Loading state ── */}
        {loading && (
          <div
            className="dg-frost"
            style={{
              borderRadius: "var(--radius-cards)",
              padding: 26,
              boxShadow: "var(--shadow-panel)",
            }}
          >
            <div style={{ font: "400 14px/1.5 var(--font-sans)", color: "var(--text-muted)" }}>
              Loading reasoner settings…
            </div>
          </div>
        )}

        {/* ── Load error state ── */}
        {loadError && (
          <div
            className="dg-frost"
            style={{
              borderRadius: "var(--radius-cards)",
              padding: 26,
              boxShadow: "var(--shadow-panel)",
            }}
          >
            <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>
              Settings unavailable · {loadError}{" "}
              <span
                onClick={handleRetry}
                style={{ cursor: "pointer", textDecoration: "underline" }}
              >
                Retry
              </span>
            </div>
          </div>
        )}

        {/* ── Screen-level note ── */}
        {!loading && !loadError && (
          <div
            className="dg-frost"
            style={{
              borderRadius: "var(--radius-cards)",
              padding: 26,
              boxShadow: "var(--shadow-panel)",
            }}
          >
            <div
              style={{
                font: "400 14px/1.5 var(--font-sans)",
                color: "var(--text-muted)",
              }}
            >
              Select the ontology reasoner used to evaluate design rules against the
              Validation Graph. Selection persists across sessions but does{" "}
              <strong>not</strong> yet change validation behavior — both reasoners are
              shown as placeholders until their integration is elaborated.
            </div>
          </div>
        )}

        {/* ── Reasoner cards ── */}
        {!loading && !loadError && (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {reasoners.map((r) => {
                const isActive = selected === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => handleSelect(r.id)}
                    style={{
                      borderRadius: "var(--radius-cards)",
                      padding: 24,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      boxShadow: isActive
                        ? "var(--shadow-panel), 0 0 0 1.5px var(--accent-selection)"
                        : "var(--shadow-panel), 0 0 0 1px var(--color-hairline)",
                      background: isActive
                        ? "var(--accent-selection-bg)"
                        : "var(--surface-card)",
                      opacity: saving ? 0.7 : 1,
                      pointerEvents: saving ? "none" : "auto",
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") handleSelect(r.id);
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        marginBottom: 10,
                      }}
                    >
                      <div
                        style={{
                          font: "600 18px/1.3 var(--font-sans)",
                          color: "var(--color-ink)",
                          letterSpacing: "-0.3px",
                        }}
                      >
                        {r.name}
                      </div>
                      {isActive && (
                        <Badge variant="solid">Active</Badge>
                      )}
                      {r.status === "placeholder" && (
                        <Badge variant="outline">Integration pending</Badge>
                      )}
                    </div>
                    <div
                      style={{
                        font: "400 13px/1.5 var(--font-sans)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {r.description}
                    </div>
                    {r.status === "integrated" ? (
                      <div
                        style={{
                          marginTop: 16,
                          display: "flex",
                          flexDirection: "column",
                          gap: 12,
                        }}
                      >
                        <div
                          style={{
                            font: "400 12px/1.33 var(--font-sans)",
                            color: "var(--text-muted)",
                          }}
                        >
                          Schema-consistency check — verifies the ontology's logical
                          structure, not design compliance.
                        </div>

                        {runState === "idle" && (
                          <>
                            <div
                              style={{
                                font: "400 13px/1.5 var(--font-sans)",
                                color: "var(--text-secondary)",
                              }}
                            >
                              No check run yet. Run a schema-consistency check against
                              the active project.
                            </div>
                            <div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRunCheck();
                                }}
                              >
                                Run check
                              </Button>
                            </div>
                          </>
                        )}

                        {runState === "running" && (
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 12,
                            }}
                          >
                            <style>{`@keyframes dg-reasoner-spin { to { transform: rotate(360deg); } }`}</style>
                            <div
                              style={{
                                width: 12,
                                height: 12,
                                borderRadius: "50%",
                                border: "2px solid var(--color-hairline)",
                                borderTopColor: "var(--text-muted)",
                                animation: "dg-reasoner-spin 0.8s linear infinite",
                              }}
                            />
                            <div
                              style={{
                                font: "400 12px/1.33 var(--font-sans)",
                                color: "var(--text-muted)",
                              }}
                            >
                              Running… {elapsedSec}s
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCancel();
                              }}
                            >
                              Cancel
                            </Button>
                            <Button variant="outline" size="sm" disabled>
                              Run check
                            </Button>
                          </div>
                        )}

                        {runState === "consistent" && (
                          <>
                            <div
                              style={{ display: "flex", alignItems: "center", gap: 8 }}
                            >
                              <div
                                style={{
                                  font: "600 13px/1.5 var(--font-sans)",
                                  color: "var(--color-ink)",
                                }}
                              >
                                ✓ Schema consistent — no unsatisfiable classes found.
                              </div>
                              <Badge variant="solid">Consistent</Badge>
                            </div>
                            {lastCheckedAt && (
                              <div
                                style={{
                                  font: "400 12px/1.33 var(--font-sans)",
                                  color: "var(--text-muted)",
                                }}
                              >
                                Last checked {formatRelativeDate(lastCheckedAt)}
                              </div>
                            )}
                            <div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRunCheck();
                                }}
                              >
                                Run check
                              </Button>
                            </div>
                          </>
                        )}

                        {runState === "inconsistent" &&
                          (() => {
                            const list = runResult?.unsatisfiable_classes || [];
                            const n = list.length;
                            return (
                              <>
                                <div
                                  style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: 8,
                                    padding: 12,
                                    borderRadius: "var(--radius-cards)",
                                    background: "var(--color-signal-soft)",
                                  }}
                                >
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 8,
                                    }}
                                  >
                                    <div
                                      style={{
                                        font: "600 13px/1.5 var(--font-sans)",
                                        color: "var(--color-signal)",
                                      }}
                                    >
                                      Schema inconsistent — {n} unsatisfiable class
                                      {n === 1 ? "" : "es"}.
                                    </div>
                                    <Badge variant="signal">Inconsistent</Badge>
                                  </div>
                                  {n > 0 && (
                                    <ul
                                      style={{
                                        margin: 0,
                                        paddingLeft: 20,
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: 8,
                                      }}
                                    >
                                      {list.map((entry, i) => (
                                        <li
                                          key={i}
                                          style={{
                                            font: "400 13px/1.5 var(--font-sans)",
                                            color: "var(--color-signal)",
                                          }}
                                        >
                                          {entry.label}
                                        </li>
                                      ))}
                                    </ul>
                                  )}
                                </div>
                                {lastCheckedAt && (
                                  <div
                                    style={{
                                      font: "400 12px/1.33 var(--font-sans)",
                                      color: "var(--text-muted)",
                                    }}
                                  >
                                    Last checked {formatRelativeDate(lastCheckedAt)}
                                  </div>
                                )}
                                <div>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleRunCheck();
                                    }}
                                  >
                                    Run check
                                  </Button>
                                </div>
                              </>
                            );
                          })()}

                        {runState === "unknown" && (
                          <>
                            <div
                              style={{ display: "flex", alignItems: "center", gap: 8 }}
                            >
                              <div
                                style={{
                                  font: "400 13px/1.5 var(--font-sans)",
                                  color: "var(--text-muted)",
                                }}
                              >
                                – Inconclusive — the reasoner timed out before
                                finishing. Try again.
                              </div>
                              <Badge variant="outline">Inconclusive</Badge>
                            </div>
                            {lastCheckedAt && (
                              <div
                                style={{
                                  font: "400 12px/1.33 var(--font-sans)",
                                  color: "var(--text-muted)",
                                }}
                              >
                                Last checked {formatRelativeDate(lastCheckedAt)}
                              </div>
                            )}
                            <div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRunCheck();
                                }}
                              >
                                Run check
                              </Button>
                            </div>
                          </>
                        )}

                        {runState === "cancelled" && (
                          <>
                            <div
                              style={{
                                font: "400 13px/1.5 var(--font-sans)",
                                color: "var(--ink-a56)",
                              }}
                            >
                              × Run cancelled — no result.
                            </div>
                            <div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRunCheck();
                                }}
                              >
                                Run check
                              </Button>
                            </div>
                          </>
                        )}

                        {runState === "error" && (
                          <div
                            style={{
                              font: "400 13px/1.4 var(--font-sans)",
                              color: "var(--color-signal-ink)",
                            }}
                          >
                            Reasoner unavailable · {runError}{" "}
                            <span
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRunCheck();
                              }}
                              style={{ cursor: "pointer", textDecoration: "underline" }}
                            >
                              Retry
                            </span>
                          </div>
                        )}
                      </div>
                    ) : (
                      isActive && (
                        <div
                          style={{
                            marginTop: 14,
                            font: "400 12px/1.33 var(--font-sans)",
                            color: "var(--accent-selection)",
                          }}
                        >
                          Selected — will be used when integration is complete.
                        </div>
                      )
                    )}
                  </div>
                );
              })}
            </div>

            {/* ── Save error ── */}
            {saveError && (
              <div
                style={{
                  font: "400 13px/1.4 var(--font-sans)",
                  color: "var(--color-signal)",
                }}
              >
                {saveError}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
