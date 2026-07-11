import React from "react";
import { Button, Badge } from "../components/index.js";
import { getReasonerSettings, selectReasoner } from "../lib/reasonerApi.js";

// Reasoner region — ontology reasoner selector for the Validation Graph.
// HermiT and Pellet ship as clearly-labeled placeholders ("integration pending" —
// selection is persisted server-side but does not yet drive validation).
// Selection survives revisits (Phase 814: REAS-01..03).
export default function ReasonerScreen({ active, onBack, project }) {
  const [reasoners, setReasoners] = React.useState([]);
  const [selected, setSelected] = React.useState(null);

  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState("");

  const [saving, setSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState("");

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
                        ? "var(--shadow-panel), 0 0 0 1.5px var(--color-accent)"
                        : "var(--shadow-panel), 0 0 0 1px var(--color-hairline)",
                      background: isActive
                        ? "var(--surface-focus)"
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
                    {isActive && (
                      <div
                        style={{
                          marginTop: 14,
                          font: "400 12px/1.33 var(--font-sans)",
                          color: "var(--color-accent)",
                        }}
                      >
                        Selected — will be used when integration is complete.
                      </div>
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
