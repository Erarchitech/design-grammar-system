import React from "react";

export default function Button({
  variant = "primary",
  size = "md",
  selected = false,
  disabled = false,
  children,
  style,
  ...rest
}) {
  const heights = { sm: 28, md: 36, lg: 40 };
  const h = heights[size] || 36;
  const variants = {
    primary: {
      background: "var(--color-ink)",
      color: "var(--text-inverse)",
      border: "1px solid transparent"
    },
    secondary: {
      background: "var(--color-canvas)",
      color: "var(--color-ink)",
      border: "1px solid transparent"
    },
    outline: {
      background: "transparent",
      color: "var(--color-ink)",
      border: "1px solid var(--color-hairline)"
    },
    destructive: {
      background: "transparent",
      color: "var(--color-signal-ink)",
      border: "1px solid var(--color-signal-mid)"
    }
  };
  const v = variants[variant] || variants.primary;
  const sel = selected
    ? {
        boxShadow: "var(--focus-ring-selected)",
        background: "var(--accent-selection-bg)",
        color: "var(--color-signal-ink)",
        border: "1px solid transparent"
      }
    : null;
  return (
    <button
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        height: h,
        padding: size === "sm" ? "0 12px" : "0 16px",
        borderRadius: "var(--radius-buttons)",
        font: `500 ${size === "sm" ? 13 : 14}px/1 var(--font-sans)`,
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.45 : 1,
        transition:
          "background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out)",
        ...v,
        ...sel,
        ...style
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
