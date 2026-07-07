import React from "react";

export function Collapsible({ label, count, open = false, onToggle, signal = false, children, style }) {
  return (
    <div
      style={{
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-nested)",
        overflow: "hidden",
        ...style
      }}
    >
      <button
        onClick={onToggle}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          boxSizing: "border-box",
          padding: "9px 12px",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          background: "var(--color-surface-alt)",
          font: "500 13px/1 var(--font-sans)",
          color: "var(--color-ink)"
        }}
      >
        <svg
          viewBox="0 0 24 24"
          width="13"
          height="13"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transform: open ? "rotate(0deg)" : "rotate(-90deg)",
            transition: "transform var(--duration-fast) var(--ease-out)",
            color: "var(--text-muted)",
            flex: "none"
          }}
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
        <span style={{ flex: 1 }}>{label}</span>
        {count != null && (
          <span
            style={{
              font: "500 12px/1 var(--font-mono)",
              padding: "2px 7px",
              borderRadius: "var(--radius-full)",
              background: signal ? "var(--color-signal-soft)" : "var(--color-paper)",
              color: signal ? "var(--color-signal-ink)" : "var(--text-muted)",
              border: signal ? "1px solid transparent" : "1px solid var(--color-hairline)"
            }}
          >
            {count}
          </span>
        )}
      </button>
      {open && (
        <div style={{ borderTop: "1px solid var(--color-hairline)", background: "var(--color-paper)" }}>
          {children}
        </div>
      )}
    </div>
  );
}

export function CollapsibleItem({ primary, secondary, selected = false, onClick, style }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        padding: "8px 12px",
        cursor: onClick ? "pointer" : "default",
        borderBottom: "1px solid var(--color-hairline)",
        background: selected ? "var(--accent-selection-bg)" : "transparent",
        boxShadow: selected ? "inset 2px 0 0 var(--color-signal)" : "none",
        ...style
      }}
    >
      <span
        style={{
          font: "400 13px/1.3 var(--font-mono)",
          color: selected ? "var(--color-signal-ink)" : "var(--color-ink)"
        }}
      >
        {primary}
      </span>
      {secondary && (
        <span style={{ font: "400 11px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>{secondary}</span>
      )}
    </div>
  );
}

export default Collapsible;
