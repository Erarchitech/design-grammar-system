import React from "react";
import ScreenHeader from "../shell/ScreenHeader.jsx";

// Graph Viewer screen — the live Neo4j datascape lands here in Phase 23.
export default function GraphScreen({ onBack, project }) {
  return (
    <div className="dg-blueprint" style={{ position: "absolute", inset: 0 }}>
      <ScreenHeader
        title="Graph Viewer"
        subtitle={`${project || "No project"} · bolt://neo4j:7687`}
        onBack={onBack}
      />
      <div
        className="dg-annotation dg-annotation--muted"
        style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", fontSize: 11 }}
      >
        Datascape pending · phase 23
      </div>
    </div>
  );
}
