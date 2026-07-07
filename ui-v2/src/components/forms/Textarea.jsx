import React from "react";

export default function Textarea({ label, mono = true, rows = 5, style, ...rest }) {
  const field = (
    <textarea
      rows={rows}
      style={{
        width: "100%",
        boxSizing: "border-box",
        resize: "vertical",
        background: "var(--surface-input)",
        color: "var(--color-ink)",
        border: "1px solid transparent",
        borderRadius: "var(--radius-nested)",
        padding: "12px 14px",
        outline: "none",
        font: `400 13px/1.55 ${mono ? "var(--font-mono)" : "var(--font-sans)"}`,
        transition: "border-color var(--duration-fast) var(--ease-out)",
        ...style
      }}
      onFocus={(e) => {
        e.target.style.borderColor = "var(--color-hairline-strong)";
      }}
      onBlur={(e) => {
        e.target.style.borderColor = "transparent";
      }}
      {...rest}
    />
  );
  if (!label) return field;
  return (
    <label style={{ display: "block" }}>
      <span
        style={{
          display: "block",
          font: "400 13px/1.4 var(--font-sans)",
          color: "var(--text-muted)",
          marginBottom: 8
        }}
      >
        {label}
      </span>
      {field}
    </label>
  );
}
