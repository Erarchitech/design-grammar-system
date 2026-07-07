import React from "react";

export default function Dialog({ title, open = true, onClose, footer, children, style }) {
  if (!open) return null;
  return (
    <div
      style={{
        width: 380,
        boxSizing: "border-box",
        background: "var(--frost-bg)",
        backdropFilter: "blur(var(--frost-blur))",
        WebkitBackdropFilter: "blur(var(--frost-blur))",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-cards)",
        boxShadow: "var(--shadow-panel)",
        overflow: "hidden",
        ...style
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 20px",
          borderBottom: "1px solid var(--color-hairline)"
        }}
      >
        <span style={{ font: "600 15px/1.2 var(--font-sans)", color: "var(--color-ink)" }}>{title}</span>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              border: "none",
              background: "transparent",
              cursor: "pointer",
              color: "var(--text-muted)",
              font: "400 16px/1 var(--font-sans)",
              padding: 4
            }}
          >
            ×
          </button>
        )}
      </div>
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>{children}</div>
      {footer && (
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
            padding: "14px 20px",
            borderTop: "1px solid var(--color-hairline)"
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
}
