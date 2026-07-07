import React from "react";

export default function SearchField({
  placeholder = "Search projects...",
  shortcut,
  value,
  onChange,
  style,
  ...rest
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        height: 36,
        boxSizing: "border-box",
        background: "var(--surface-input)",
        borderRadius: "var(--radius-inputs)",
        padding: "0 14px",
        ...style
      }}
    >
      <svg
        viewBox="0 0 24 24"
        width="14"
        height="14"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ color: "var(--text-muted)", flex: "none" }}
      >
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        style={{
          flex: 1,
          minWidth: 0,
          background: "transparent",
          border: "none",
          outline: "none",
          color: "var(--color-ink)",
          font: "400 14px/1 var(--font-sans)"
        }}
        {...rest}
      />
      {shortcut && (
        <kbd
          style={{
            font: "400 11px/1 var(--font-mono)",
            color: "var(--text-muted)",
            border: "1px solid var(--color-hairline)",
            borderRadius: 6,
            padding: "3px 5px",
            background: "var(--color-paper)"
          }}
        >
          {shortcut}
        </kbd>
      )}
    </div>
  );
}
