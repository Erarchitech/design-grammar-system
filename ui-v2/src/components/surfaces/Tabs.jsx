import React from "react";

export default function Tabs({ tabs = [], active = 0, onChange, style }) {
  return (
    <div
      style={{
        display: "flex",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-nested)",
        overflow: "hidden",
        background: "var(--color-canvas)",
        ...style
      }}
    >
      {tabs.map((t, i) => (
        <button
          key={i}
          onClick={() => onChange && onChange(i)}
          style={{
            flex: 1,
            height: 36,
            border: "none",
            cursor: "pointer",
            borderRight: i < tabs.length - 1 ? "1px solid var(--color-hairline)" : "none",
            background: i === active ? "var(--color-paper)" : "transparent",
            color: i === active ? "var(--color-ink)" : "var(--text-muted)",
            font: `${i === active ? 600 : 400} 13px/1 var(--font-sans)`,
            transition: "background var(--duration-fast) var(--ease-out)"
          }}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
