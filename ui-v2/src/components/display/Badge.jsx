import React from "react";

export default function Badge({ variant = "soft", children, style }) {
  const variants = {
    solid: {
      background: "var(--color-ink-soft)",
      color: "var(--text-inverse)",
      border: "1px solid transparent"
    },
    soft: {
      background: "var(--color-canvas)",
      color: "var(--color-ink-soft)",
      border: "1px solid transparent"
    },
    outline: {
      background: "transparent",
      color: "var(--color-ink)",
      border: "1px solid var(--color-hairline)"
    },
    signal: {
      background: "var(--color-signal-soft)",
      color: "var(--color-signal-ink)",
      border: "1px solid transparent"
    },
    violation: {
      background: "var(--color-signal-soft)",
      color: "var(--color-signal-ink)",
      border: "1px solid transparent"
    },
    warning: {
      background: "var(--color-warning-soft)",
      color: "var(--color-warning-ink)",
      border: "1px solid transparent"
    },
    info: {
      background: "var(--color-info-soft)",
      color: "var(--color-info-ink)",
      border: "1px solid transparent"
    }
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        borderRadius: "var(--radius-badges)",
        padding: "2px 8px",
        font: "500 12px/1.33 var(--font-sans)",
        ...(variants[variant] || variants.soft),
        ...style
      }}
    >
      {children}
    </span>
  );
}
