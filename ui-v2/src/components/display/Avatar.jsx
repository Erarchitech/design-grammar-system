import React from "react";

export default function Avatar({ initials = "JD", size = 32, style }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        borderRadius: "var(--radius-full)",
        background: "var(--color-ink-soft)",
        color: "var(--text-inverse)",
        font: `600 ${Math.round(size * 0.38)}px/1 var(--font-sans)`,
        letterSpacing: "0.02em",
        flex: "none",
        ...style
      }}
    >
      {initials}
    </span>
  );
}
