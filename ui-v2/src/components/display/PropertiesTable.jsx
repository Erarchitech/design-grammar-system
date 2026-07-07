import React from "react";

export default function PropertiesTable({ rows = [], editable = true, style }) {
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
                  <span style={{ color: "var(--ink-a32)", fontSize: 12 }}>✎</span>
                )}
                {r.key}
              </span>
            </td>
            <td
              style={{
                ...cell,
                fontFamily: "var(--font-mono)",
                color: "var(--color-ink)",
                overflowWrap: "anywhere"
              }}
            >
              {r.value}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
