import React from "react";
import ScreenHeader from "../shell/ScreenHeader.jsx";

// Projects screen — live project tile grid lands here in Phase 25.
export default function ProjectsScreen({ onBack, project }) {
  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)" }}>
      <ScreenHeader
        title="Projects"
        subtitle={`${project || "No project selected"} · neo4j project index`}
        onBack={onBack}
      />
      <div
        className="dg-annotation dg-annotation--muted"
        style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", fontSize: 11 }}
      >
        Project tiles pending · phase 25
      </div>
    </div>
  );
}
