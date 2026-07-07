import React from "react";

export default function Slider({ label, value = 50, onChange, showValue = true, unit = "%", style }) {
  const pct = Math.max(0, Math.min(100, value));
  const track = (e) => {
    if (!onChange) return;
    const r = e.currentTarget.getBoundingClientRect();
    onChange(Math.round(((e.clientX - r.left) / r.width) * 100));
  };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, ...style }}>
      {label && (
        <span style={{ font: "400 12px/1 var(--font-sans)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
          {label}
        </span>
      )}
      <div
        onMouseDown={(e) => {
          track(e);
          const mv = (ev) => track(ev);
          const up = () => {
            window.removeEventListener("mousemove", mv);
            window.removeEventListener("mouseup", up);
          };
          window.addEventListener("mousemove", mv);
          window.addEventListener("mouseup", up);
        }}
        style={{
          position: "relative",
          flex: 1,
          minWidth: 60,
          height: 14,
          cursor: "pointer",
          display: "flex",
          alignItems: "center"
        }}
      >
        <div
          style={{
            width: "100%",
            height: 3,
            borderRadius: "var(--radius-full)",
            background: "var(--ink-a08)"
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 0,
            width: pct + "%",
            height: 3,
            borderRadius: "var(--radius-full)",
            background: "var(--color-ink)"
          }}
        />
        <div
          style={{
            position: "absolute",
            left: `calc(${pct}% - 6px)`,
            width: 12,
            height: 12,
            boxSizing: "border-box",
            borderRadius: "var(--radius-full)",
            background: "var(--color-paper)",
            border: "1px solid var(--color-ink)"
          }}
        />
      </div>
      {showValue && (
        <span
          style={{
            font: "400 12px/1 var(--font-mono)",
            color: "var(--color-ink)",
            minWidth: 34,
            textAlign: "right"
          }}
        >
          {pct}
          {unit}
        </span>
      )}
    </div>
  );
}
