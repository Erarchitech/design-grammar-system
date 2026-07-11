import React from "react";
import { Button } from "../components/index.js";

// Reasoner region — skeletal shell (Phase 810). Phase 814 fills it with the
// ontology reasoner selector (HermiT / Pellet placeholders), persisted.
export default function ReasonerScreen({ active, onBack, project }) {
  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)", overflow: "auto" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 40px 60px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← Back
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
              Region · Reasoner
            </div>
            <div style={{ font: "600 34px/1.1 var(--font-sans)", letterSpacing: "-1.2px" }}>Reasoner.</div>
          </div>
        </div>

        <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}>
          <div style={{ font: "400 14px/1.5 var(--font-sans)", color: "var(--text-muted)" }}>
            Select the ontology reasoner (HermiT, Pellet) used to evaluate design rules; the choice persists across sessions.
          </div>
        </div>
      </div>
    </div>
  );
}
