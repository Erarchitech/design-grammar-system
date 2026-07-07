import React from "react";
import ScreenHeader from "../shell/ScreenHeader.jsx";

// Model Viewer screen — validation runs UI lands here in Phase 24.
export default function ModelScreen({ onBack, project }) {
  return (
    <div className="dg-blueprint" style={{ position: "absolute", inset: 0 }}>
      <ScreenHeader
        title="Model Viewer"
        subtitle={`${project || "No project"} · data-service /validation`}
        onBack={onBack}
      />
      <div
        className="dg-annotation dg-annotation--muted"
        style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", fontSize: 11 }}
      >
        Validation viewport pending · phase 24
      </div>
    </div>
  );
}
