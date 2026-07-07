import React from "react";

export default function Chip({ selected = false, onRemove, children, style }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        height: 26,
        boxSizing: "border-box",
        borderRadius: "var(--radius-full)",
        padding: "0 12px",
        font: "500 13px/1 var(--font-sans)",
        background: selected ? "var(--accent-selection-bg)" : "var(--color-paper)",
        color: selected ? "var(--color-signal-ink)" : "var(--color-ink)",
        border: selected ? "1px solid var(--color-signal)" : "1px solid var(--color-hairline)",
        ...style
      }}
    >
      {children}
      {onRemove && (
        <span
          onClick={onRemove}
          style={{ cursor: "pointer", color: "inherit", opacity: 0.6, font: "400 13px/1 var(--font-sans)" }}
        >
          ×
        </span>
      )}
    </span>
  );
}
