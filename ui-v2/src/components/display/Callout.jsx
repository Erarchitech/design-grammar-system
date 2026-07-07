import React from "react";

// Divergence callout — the signature datascape annotation device:
// optional hexagon marker, hairline left rule, condensed uppercase captions.
export default function Callout({ date, title, subtitle, detail, signal = false, marker = false, style }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "flex-start", gap: 14, ...style }}>
      {marker && (
        <svg width="34" height="34" viewBox="0 0 34 34" style={{ flex: "none", marginTop: 2 }}>
          <polygon
            points="17,3 29,10 29,24 17,31 5,24 5,10"
            fill="none"
            stroke={signal ? "var(--color-signal)" : "var(--ink-a32)"}
            strokeWidth="1"
          />
          <circle cx="17" cy="17" r="2.5" fill={signal ? "var(--color-signal)" : "var(--color-ink)"} />
        </svg>
      )}
      <div
        style={{
          borderLeft: `1px solid ${signal ? "var(--color-signal)" : "var(--ink-a32)"}`,
          paddingLeft: 12,
          display: "flex",
          flexDirection: "column",
          gap: 1
        }}
      >
        {date && (
          <span
            style={{
              font: "400 12px/1.4 var(--font-annotation)",
              letterSpacing: "1.2px",
              color: "var(--text-muted)"
            }}
          >
            {date}
          </span>
        )}
        <span
          style={{
            font: "500 18px/1.2 var(--font-annotation)",
            letterSpacing: "var(--tracking-annotation-lg)",
            textTransform: "uppercase",
            color: "var(--color-ink)"
          }}
        >
          {title}
          {subtitle && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}> : {subtitle}</span>}
        </span>
        {detail && (
          <span
            style={{
              font: "400 12px/1.5 var(--font-annotation)",
              letterSpacing: "1.4px",
              textTransform: "uppercase",
              color: signal ? "var(--color-signal-ink)" : "var(--color-ink-soft)"
            }}
          >
            {detail}
          </span>
        )}
      </div>
    </div>
  );
}
