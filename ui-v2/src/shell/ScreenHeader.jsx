import React from "react";
import { Button } from "../components/index.js";

// Global chrome (NAV-02): Back pill + screen title + mono connection subtitle,
// rendered top-left on every non-landing screen.
export default function ScreenHeader({ title, subtitle, onBack, style }) {
  return (
    <div style={{ position: "absolute", left: 20, top: 20, display: "flex", alignItems: "center", gap: 14, zIndex: 5, ...style }}>
      <Button variant="outline" size="sm" onClick={onBack}>
        ← Back
      </Button>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div style={{ font: "600 16px/1.2 var(--font-sans)", letterSpacing: "-0.3px" }}>{title}</div>
        <div style={{ font: "400 11px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>{subtitle}</div>
      </div>
    </div>
  );
}
