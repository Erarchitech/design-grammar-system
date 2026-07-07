import React from "react";

export default function Select({ label, options = [], value, onChange, style, ...rest }) {
  const field = (
    <div style={{ position: "relative" }}>
      <select
        value={value}
        onChange={onChange}
        style={{
          width: "100%",
          boxSizing: "border-box",
          height: 36,
          appearance: "none",
          WebkitAppearance: "none",
          background: "var(--surface-input)",
          color: "var(--color-ink)",
          border: "1px solid transparent",
          borderRadius: "var(--radius-inputs)",
          padding: "0 36px 0 14px",
          outline: "none",
          cursor: "pointer",
          font: "400 14px/1.43 var(--font-sans)",
          ...style
        }}
        onFocus={(e) => {
          e.target.style.borderColor = "var(--color-hairline-strong)";
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "transparent";
        }}
        {...rest}
      >
        {options.map((o) => {
          const opt = typeof o === "string" ? { value: o, label: o } : o;
          return (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          );
        })}
      </select>
      <svg
        viewBox="0 0 24 24"
        width="14"
        height="14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          position: "absolute",
          right: 14,
          top: "50%",
          transform: "translateY(-50%)",
          pointerEvents: "none",
          color: "var(--text-muted)"
        }}
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </div>
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
