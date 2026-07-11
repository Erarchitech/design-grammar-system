import React from "react";
import { Button } from "../components/index.js";

// AI Engine region — skeletal shell (Phase 810). Phase 811 fills it with
// LLM provider/model/API-key setup over the data-service gateway.
export default function AiEngineScreen({ active, onBack, project }) {
  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)", overflow: "auto" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 40px 60px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← Back
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
              Region · AI Engine
            </div>
            <div style={{ font: "600 34px/1.1 var(--font-sans)", letterSpacing: "-1.2px" }}>AI Engine.</div>
          </div>
        </div>

        <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)" }}>
          <div style={{ font: "400 14px/1.5 var(--font-sans)", color: "var(--text-muted)" }}>
            Configure the platform LLM — provider, model, and API key — that powers rule ingestion and graph queries.
          </div>
        </div>
      </div>
    </div>
  );
}
