import React from "react";

export function KVRow({ label, value, mono = true, style }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        gap: 12,
        padding: "5px 0",
        ...style
      }}
    >
      <span style={{ font: "400 12px/1.4 var(--font-sans)", color: "var(--text-muted)", flex: "none" }}>
        {label}
      </span>
      <span
        style={{
          font: `400 12px/1.4 ${mono ? "var(--font-mono)" : "var(--font-sans)"}`,
          color: "var(--color-ink)",
          textAlign: "right",
          overflowWrap: "anywhere",
          minWidth: 0
        }}
      >
        {value}
      </span>
    </div>
  );
}

export function StatBlock({ label, value, signal = false, style }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, ...style }}>
      <span
        style={{
          font: "500 12px/1.33 var(--font-sans)",
          letterSpacing: "var(--tracking-caption)",
          textTransform: "uppercase",
          color: "var(--text-muted)"
        }}
      >
        {label}
      </span>
      <span
        style={{
          font: "600 30px/1.2 var(--font-sans)",
          letterSpacing: "var(--tracking-heading)",
          color: signal ? "var(--color-signal-ink)" : "var(--color-ink)"
        }}
      >
        {value}
      </span>
    </div>
  );
}

export default KVRow;
