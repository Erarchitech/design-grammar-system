import React from "react";

export default function Tile({ title, description, thumbnail, onClick, style }) {
  return (
    <div
      onClick={onClick}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "var(--color-hairline-strong)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--color-hairline)";
      }}
      style={{
        background: "var(--surface-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-cards)",
        boxShadow: "var(--shadow-subtle)",
        overflow: "hidden",
        cursor: onClick ? "pointer" : "default",
        transition: "border-color var(--duration-fast) var(--ease-out)",
        ...style
      }}
    >
      <div
        style={{
          aspectRatio: "16 / 9",
          background: "var(--color-canvas)",
          backgroundImage:
            "linear-gradient(var(--ink-a04) 1px, transparent 1px), linear-gradient(90deg, var(--ink-a04) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: "1px solid var(--color-hairline)"
        }}
      >
        {thumbnail || (
          <svg width="40" height="40" viewBox="0 0 40 40">
            <circle cx="20" cy="12" r="3.5" fill="none" stroke="var(--ink-a32)" strokeWidth="1" />
            <circle cx="10" cy="28" r="3.5" fill="none" stroke="var(--ink-a32)" strokeWidth="1" />
            <circle cx="30" cy="28" r="3.5" fill="var(--color-ink)" />
            <path d="M18 15 12 25 M22 15 28 25 M13.5 28 26.5 28" stroke="var(--ink-a32)" strokeWidth="1" />
          </svg>
        )}
      </div>
      <div style={{ padding: "14px 16px 16px", display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ font: "600 15px/1.3 var(--font-sans)", color: "var(--color-ink)" }}>{title}</span>
        {description && (
          <span style={{ font: "400 13px/1.45 var(--font-sans)", color: "var(--text-muted)" }}>{description}</span>
        )}
      </div>
    </div>
  );
}
