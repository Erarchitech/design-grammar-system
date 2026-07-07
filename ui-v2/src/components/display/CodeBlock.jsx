import React from "react";

export default function CodeBlock({ children, label, style }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, ...style }}>
      {label && (
        <span style={{ font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)" }}>{label}</span>
      )}
      <pre
        style={{
          margin: 0,
          background: "var(--color-canvas)",
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-nested)",
          padding: "12px 14px",
          font: "400 12px/1.6 var(--font-mono)",
          color: "var(--color-ink)",
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere"
        }}
      >
        {children}
      </pre>
    </div>
  );
}
