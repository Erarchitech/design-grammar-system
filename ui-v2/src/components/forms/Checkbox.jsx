import React from "react";

export default function Checkbox({ label, checked = false, onChange, style }) {
  const toggle = () => onChange && onChange(!checked);
  return (
    <label
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        cursor: "pointer",
        userSelect: "none",
        ...style
      }}
    >
      <span
        onClick={toggle}
        style={{
          width: 16,
          height: 16,
          boxSizing: "border-box",
          borderRadius: "var(--radius-small)",
          border: checked
            ? "1px solid var(--color-ink)"
            : "1px solid var(--color-hairline-strong)",
          background: checked ? "var(--color-ink)" : "var(--color-paper)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "background var(--duration-fast) var(--ease-out)",
          flex: "none"
        }}
      >
        {checked && (
          <svg
            viewBox="0 0 24 24"
            width="11"
            height="11"
            fill="none"
            stroke="#fafafa"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 6 9 17l-5-5" />
          </svg>
        )}
      </span>
      {label && (
        <span onClick={toggle} style={{ font: "400 13px/1 var(--font-sans)", color: "var(--color-ink)" }}>
          {label}
        </span>
      )}
    </label>
  );
}
