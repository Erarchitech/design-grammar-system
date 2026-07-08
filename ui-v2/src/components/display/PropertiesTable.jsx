import React from "react";

// Key/value property table. When `onEdit(key, rawValue)` is provided (and
// `editable`), values can be edited inline: click the ✎ (or double-click the
// value), Enter commits, Escape cancels — the legacy SPA's editing pattern.
export default function PropertiesTable({ rows = [], editable = true, onEdit, style }) {
  const [editingKey, setEditingKey] = React.useState(null);
  const [draft, setDraft] = React.useState("");
  const canEdit = editable && typeof onEdit === "function";

  const begin = (r) => {
    if (!canEdit || String(r.key).startsWith("<")) return;
    setEditingKey(r.key);
    setDraft(String(r.value ?? ""));
  };
  const cancel = () => {
    setEditingKey(null);
    setDraft("");
  };
  const commit = () => {
    if (editingKey != null) onEdit(editingKey, draft);
    cancel();
  };

  const cell = {
    padding: "10px 8px",
    font: "400 13px/1.4 var(--font-sans)",
    verticalAlign: "top"
  };
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", ...style }}>
      <thead>
        <tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
          <th style={{ ...cell, width: 118, textAlign: "left", fontWeight: 600, color: "var(--text-muted)" }}>
            Key
          </th>
          <th style={{ ...cell, textAlign: "left", fontWeight: 600, color: "var(--text-muted)" }}>Value</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
            <td style={{ ...cell, color: "var(--color-ink)" }}>
              <span style={{ display: "inline-flex", gap: 4, alignItems: "baseline" }}>
                {editable && !String(r.key).startsWith("<") && (
                  <span
                    onClick={() => begin(r)}
                    title={canEdit ? "Edit value" : undefined}
                    style={{ color: "var(--ink-a32)", fontSize: 12, cursor: canEdit ? "pointer" : "default" }}
                  >
                    ✎
                  </span>
                )}
                {r.key}
              </span>
            </td>
            <td
              onDoubleClick={() => begin(r)}
              style={{
                ...cell,
                fontFamily: "var(--font-mono)",
                color: "var(--color-ink)",
                overflowWrap: "anywhere"
              }}
            >
              {editingKey === r.key ? (
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commit();
                    if (e.key === "Escape") cancel();
                  }}
                  onBlur={cancel}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    font: "400 12px/1.4 var(--font-mono)",
                    color: "var(--color-ink)",
                    background: "var(--surface-input)",
                    border: "1px solid var(--color-hairline-strong)",
                    borderRadius: 5,
                    padding: "4px 6px",
                    outline: "none"
                  }}
                />
              ) : (
                r.value
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
