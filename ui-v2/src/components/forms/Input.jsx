import React from "react";

export default function Input({ label, hint, mono = false, invalid = false, style, ...rest }) {
  const field = (
    <input
      style={{
        width: "100%",
        boxSizing: "border-box",
        height: 36,
        background: "var(--surface-input)",
        color: "var(--color-ink)",
        border: "1px solid transparent",
        borderRadius: "var(--radius-inputs)",
        padding: "8px 14px",
        outline: "none",
        font: `400 14px/1.43 ${mono ? "var(--font-mono)" : "var(--font-sans)"}`,
        transition: "border-color var(--duration-fast) var(--ease-out)",
        ...(invalid ? { borderColor: "var(--color-signal)" } : null),
        ...style
      }}
      onFocus={(e) => {
        if (!invalid) e.target.style.borderColor = "var(--color-hairline-strong)";
      }}
      onBlur={(e) => {
        if (!invalid) e.target.style.borderColor = "transparent";
      }}
      {...rest}
    />
  );
  if (!label && !hint) return field;
  return (
    <label style={{ display: "block" }}>
      {label && (
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
      )}
      {field}
      {hint && (
        <span
          style={{
            display: "block",
            font: "400 12px/1.33 var(--font-sans)",
            color: "var(--text-muted)",
            marginTop: 6
          }}
        >
          {hint}
        </span>
      )}
    </label>
  );
}
