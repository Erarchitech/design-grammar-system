import React from "react";
import Select from "../forms/Select.jsx";

// Legacy graph-viewer "Session History" panel, reskinned for V2. A collapsible,
// filterable list of persisted workflow turns (design-rule ingest/query/edit or
// knowledge insert/query/update). Each row shows a mode badge, the prompt text,
// a relative timestamp and a Restore action; clicking a row expands the full
// prompt / result / time. Paginates in +50 chunks via "Show more".

// Per-mode badge palettes (mirrors the legacy .session-badge-* rules).
const BADGE_STYLES = {
  ingest: { background: "#6da7ff", color: "#0c1018" },
  edit: { background: "#c6b5ff", color: "#1a1030" },
  insert: { background: "#4ecdc4", color: "#0c1018" },
  update: { background: "#ffb66f", color: "#20160f" },
  query: { background: "#5fd0ff", color: "#0c1018" }
};

const BADGE_TEXT = {
  ingest: "ING",
  edit: "EDT",
  insert: "INS",
  update: "UPD",
  query: "QRY"
};

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

/**
 * @param sessions         array of {sessionId, mode, prompt, result, createdAt}
 * @param filters           filter <select> options, e.g. [{value:"all",label:"All"},…]
 * @param open              controlled expanded/collapsed state of the whole panel
 * @param onToggle          () => void — toggle panel open/closed
 * @param onRestore         (session) => void — reuse the turn's prompt in the bar
 * @param onRestorePoint    (session) => void — rewind the graph to before this turn
 * @param onRepeat          (session) => void — re-run the turn (shown after restore)
 * @param restorePointIds   Set of sessionIds that have a captured graph snapshot
 * @param restoredSessionId sessionId currently rewound to (enables its Repeat)
 * @param busy              when true, Repeat is disabled (a turn is running)
 * @param emptyLabel        copy shown when there are no sessions at all
 */
export default function SessionHistory({
  sessions = [],
  filters = [{ value: "all", label: "All" }],
  open = false,
  onToggle,
  onRestore,
  onRestorePoint,
  onRepeat,
  restorePointIds,
  restoredSessionId = null,
  busy = false,
  emptyLabel = "No sessions yet"
}) {
  const hasPoint = (id) => !!(restorePointIds && restorePointIds.has(id) && onRestorePoint);
  const [filter, setFilter] = React.useState("all");
  const [displayCount, setDisplayCount] = React.useState(50);
  const [expandedId, setExpandedId] = React.useState(null);

  const filtered = filter === "all" ? sessions : sessions.filter((s) => s.mode === filter);
  const displayed = filtered.slice(0, displayCount);

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {/* header: chevron + title + count + filter */}
      <div
        role="button"
        aria-expanded={open}
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={(ev) => {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            onToggle && onToggle();
          }
        }}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          height: 34,
          padding: "0 8px",
          borderRadius: "var(--radius-nested)",
          cursor: "pointer"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", whiteSpace: "nowrap", minWidth: 0, flex: "1 1 auto", gap: 6 }}>
          <svg
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            style={{ flex: "0 0 auto", color: "var(--text-muted)", transform: open ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 140ms" }}
          >
            <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span style={{ font: "600 12px/1.3 var(--font-sans)", letterSpacing: "0.1px", color: "var(--color-ink)" }}>Session History</span>
          <span style={{ font: "400 11px/1.3 var(--font-sans)", color: "var(--text-muted)" }}>({filtered.length})</span>
        </div>
        <div onClick={(ev) => ev.stopPropagation()} style={{ flex: "0 0 auto" }}>
          <Select
            value={filter}
            options={filters}
            onChange={(ev) => {
              setFilter(ev.target.value);
              setDisplayCount(50);
            }}
            style={{ height: 24, width: 82, fontSize: 11, padding: "0 26px 0 8px" }}
          />
        </div>
      </div>

      {open && (
        <div style={{ maxHeight: 300, overflowY: "auto", padding: "4px 0", display: "flex", flexDirection: "column" }}>
          {displayed.length === 0 && (
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11, padding: "12px 0", textAlign: "center" }}>
              {sessions.length === 0 ? emptyLabel : "No sessions match this filter"}
            </div>
          )}

          {displayed.map((session) => {
            const mode = session.mode || "query";
            const badge = BADGE_STYLES[mode] || BADGE_STYLES.query;
            const badgeText = BADGE_TEXT[mode] || "QRY";
            const isExpanded = expandedId === session.sessionId;
            return (
              <React.Fragment key={session.sessionId}>
                <div
                  onClick={() => setExpandedId((prev) => (prev === session.sessionId ? null : session.sessionId))}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    width: "100%",
                    padding: "8px 4px",
                    borderBottom: "1px solid var(--color-hairline)",
                    cursor: "pointer"
                  }}
                >
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      height: 18,
                      padding: "0 7px",
                      borderRadius: 999,
                      font: "600 10px/1 var(--font-annotation)",
                      letterSpacing: "0.6px",
                      flex: "0 0 auto",
                      ...badge
                    }}
                  >
                    {badgeText}
                  </span>
                  <span
                    style={{
                      flex: 1,
                      minWidth: 0,
                      font: "400 12px/1.4 var(--font-mono)",
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis"
                    }}
                  >
                    {session.prompt || ""}
                  </span>
                  <span style={{ flex: "0 0 auto", font: "400 10px/1.3 var(--font-sans)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                    {formatRelativeDate(session.createdAt)}
                  </span>
                  {hasPoint(session.sessionId) && (
                    <button
                      type="button"
                      title="Rewind the graph to how it looked before this turn"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        onRestorePoint(session);
                      }}
                      style={{
                        flex: "0 0 auto",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 3,
                        background: "transparent",
                        border: "1px solid var(--color-hairline)",
                        borderRadius: 6,
                        color: "var(--color-signal-ink)",
                        font: "500 10px/1 var(--font-sans)",
                        padding: "3px 6px",
                        cursor: "pointer"
                      }}
                      onMouseOver={(ev) => (ev.currentTarget.style.borderColor = "var(--color-signal)")}
                      onMouseOut={(ev) => (ev.currentTarget.style.borderColor = "var(--color-hairline)")}
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                        <path d="M3 3v5h5" />
                      </svg>
                      Restore
                    </button>
                  )}
                  <button
                    type="button"
                    title="Load this prompt back into the prompt bar to edit or re-run"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      onRestore && onRestore(session);
                    }}
                    style={{
                      flex: "0 0 auto",
                      background: "transparent",
                      border: "none",
                      color: "var(--text-secondary)",
                      font: "500 11px/1 var(--font-sans)",
                      padding: "3px 6px",
                      cursor: "pointer"
                    }}
                    onMouseOver={(ev) => (ev.currentTarget.style.textDecoration = "underline")}
                    onMouseOut={(ev) => (ev.currentTarget.style.textDecoration = "none")}
                  >
                    Reuse
                  </button>
                </div>

                {isExpanded && (
                  <div
                    style={{
                      background: "var(--color-canvas)",
                      border: "1px solid var(--color-hairline)",
                      borderRadius: "var(--radius-nested)",
                      padding: 12,
                      margin: "4px 0 8px 0",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4
                    }}
                  >
                    <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>Prompt</span>
                    <div style={{ font: "400 12px/1.5 var(--font-mono)", color: "var(--color-ink)", whiteSpace: "pre-wrap", overflowWrap: "anywhere", marginBottom: 8 }}>{session.prompt || ""}</div>
                    <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>Result</span>
                    <div style={{ font: "400 12px/1.5 var(--font-mono)", color: "var(--text-secondary)", whiteSpace: "pre-wrap", overflowWrap: "anywhere", marginBottom: 8, maxHeight: 160, overflowY: "auto" }}>{session.result || ""}</div>
                    <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>Time</span>
                    <div style={{ font: "400 11px/1.4 var(--font-mono)", color: "var(--text-muted)" }}>
                      {session.createdAt ? String(session.createdAt).replace("T", " ").slice(0, 16) : ""}
                    </div>
                  </div>
                )}
              </React.Fragment>
            );
          })}

          {filtered.length > displayCount && (
            <button
              type="button"
              onClick={() => setDisplayCount((prev) => prev + 50)}
              style={{
                width: "100%",
                marginTop: 8,
                padding: "6px 0",
                background: "transparent",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-nested)",
                color: "var(--text-secondary)",
                font: "500 11px/1 var(--font-sans)",
                cursor: "pointer",
                textAlign: "center"
              }}
            >
              Show more
            </button>
          )}
        </div>
      )}
    </div>
  );
}
