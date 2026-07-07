import React from "react";

export default function Panel({ title, frost = false, children, style }) {
  return (
    <section
      style={{
        background: frost ? "var(--frost-bg)" : "var(--surface-card)",
        backdropFilter: frost ? "blur(var(--frost-blur))" : undefined,
        WebkitBackdropFilter: frost ? "blur(var(--frost-blur))" : undefined,
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-cards)",
        boxShadow: "var(--shadow-subtle)",
        padding: "var(--card-padding)",
        ...style
      }}
    >
      {title && (
        <h4
          style={{
            margin: "0 0 12px",
            font: "500 12px/1.33 var(--font-sans)",
            letterSpacing: "var(--tracking-caption)",
            textTransform: "uppercase",
            color: "var(--text-muted)"
          }}
        >
          {title}
        </h4>
      )}
      {children}
    </section>
  );
}
