import React from "react";

export default function RunTile({ ruleId, date, kind = "Constraint", thumb, active = false, onSelect, onDelete, style }) {
  return (
    <div
      onClick={onSelect}
      style={{
        width: 178,
        flex: "none",
        boxSizing: "border-box",
        background: "var(--surface-card)",
        border: active ? "1px solid var(--color-signal)" : "1px solid var(--color-hairline)",
        boxShadow: active ? "0 0 0 1px var(--color-signal-mid)" : "var(--shadow-subtle)",
        borderRadius: "var(--radius-nested)",
        overflow: "hidden",
        cursor: onSelect ? "pointer" : "default",
        ...style
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 6,
          padding: "7px 10px",
          borderBottom: "1px solid var(--color-hairline)"
        }}
      >
        <span
          style={{
            font: "500 12px/1.2 var(--font-mono)",
            color: active ? "var(--color-signal-ink)" : "var(--color-ink)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap"
          }}
        >
          {ruleId}
        </span>
        {onDelete && (
          <span
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            title="Delete run"
            style={{ color: "var(--ink-a32)", cursor: "pointer", font: "400 13px/1 var(--font-sans)", flex: "none" }}
          >
            ×
          </span>
        )}
      </div>
      {thumb ? (
        <img src={thumb} alt="" style={{ width: "100%", height: 64, objectFit: "cover", display: "block" }} />
      ) : (
        <div
          style={{
            height: 64,
            background: "var(--color-canvas)",
            backgroundImage:
              "linear-gradient(var(--ink-a04) 1px, transparent 1px), linear-gradient(90deg, var(--ink-a04) 1px, transparent 1px)",
            backgroundSize: "16px 16px"
          }}
        />
      )}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 6,
          padding: "7px 10px",
          borderTop: "1px solid var(--color-hairline)"
        }}
      >
        <span style={{ font: "400 11px/1.2 var(--font-sans)", color: "var(--text-muted)" }}>{date}</span>
        <span
          style={{
            font: "500 10px/1.2 var(--font-sans)",
            padding: "2px 7px",
            borderRadius: "var(--radius-full)",
            background: "var(--color-canvas)",
            color: "var(--color-ink-soft)"
          }}
        >
          {kind}
        </span>
      </div>
    </div>
  );
}
