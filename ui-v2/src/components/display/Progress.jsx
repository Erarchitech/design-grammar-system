import React from "react";

export default function Progress({ value = 0, steps = [], style }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, ...style }}>
      <div
        style={{
          height: 10,
          boxSizing: "border-box",
          borderRadius: "var(--radius-full)",
          background: "var(--color-paper)",
          border: "1px solid var(--color-hairline)",
          overflow: "hidden"
        }}
      >
        <div
          style={{
            width: `${Math.max(0, Math.min(100, value))}%`,
            height: "100%",
            background: "var(--color-ink)",
            borderRadius: "var(--radius-full)",
            transition: "width var(--duration-base) var(--ease-out)"
          }}
        />
      </div>
      {steps.length > 0 && (
        <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 3 }}>
          {steps.map((s, i) => {
            const st = typeof s === "string" ? { label: s } : s;
            const done = !!st.time;
            return (
              <li
                key={i}
                style={{
                  font: "400 12px/1.4 var(--font-mono)",
                  color: st.active
                    ? "var(--color-signal-ink)"
                    : done
                      ? "var(--color-ink)"
                      : "var(--text-muted)",
                  display: "flex",
                  gap: 8,
                  alignItems: "baseline"
                }}
              >
                <span style={{ flex: "none" }}>{done ? "■" : st.active ? "▶" : "□"}</span>
                <span>
                  {st.label}
                  {st.time ? ` (${st.time})` : ""}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
