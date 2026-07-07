import React from "react";
import LandingLayer from "./landing/LandingLayer.jsx";
import GraphScreen from "./screens/GraphScreen.jsx";
import ModelScreen from "./screens/ModelScreen.jsx";
import ProjectsScreen from "./screens/ProjectsScreen.jsx";
import SpecimenPage from "./specimen/SpecimenPage.jsx";
import { currentUser } from "./lib/auth.js";

const EASE = "cubic-bezier(0.2, 0, 0, 1)";

// One of the four screen layers. All stay mounted; the active one is scaled
// to 1 / opaque, the rest fade with the spec's 520ms scale+opacity transition.
// Landing scales UP (1.6) when it recedes — it zooms toward the clicked
// region callout via transform-origin set in fly().
function Layer({ active, isLanding = false, layerRef, children }) {
  return (
    <div
      ref={layerRef}
      style={{
        position: "absolute",
        inset: 0,
        opacity: active ? 1 : 0,
        pointerEvents: active ? "auto" : "none",
        transform: active ? "scale(1)" : isLanding ? "scale(1.6)" : "scale(0.965)",
        transition: `opacity 520ms ${EASE}, transform 520ms ${EASE}`,
        willChange: "transform, opacity"
      }}
    >
      {children}
    </div>
  );
}

export default function App() {
  const [hash, setHash] = React.useState(window.location.hash);
  const [region, setRegion] = React.useState("landing");
  const [user, setUser] = React.useState(() => currentUser());
  const [project, setProject] = React.useState(() => localStorage.getItem("dgv2_project") || null);
  const landingLayerRef = React.useRef(null);

  React.useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  React.useEffect(() => {
    if (project) localStorage.setItem("dgv2_project", project);
    else localStorage.removeItem("dgv2_project");
  }, [project]);

  // fly(region, originPoint): when leaving the landing via a region callout,
  // the landing layer zooms toward the callout's ring point.
  const fly = React.useCallback((next, origin) => {
    if (origin && landingLayerRef.current) {
      landingLayerRef.current.style.transformOrigin = origin[0] + "px " + origin[1] + "px";
    }
    setRegion(next);
  }, []);
  const goLanding = React.useCallback(() => setRegion("landing"), []);

  React.useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && region !== "landing") setRegion("landing");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [region]);

  if (import.meta.env.DEV && hash === "#specimen") return <SpecimenPage />;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--color-canvas)",
        overflow: "hidden",
        fontFamily: "var(--font-sans)",
        color: "var(--text-primary)",
        userSelect: "none"
      }}
    >
      <Layer active={region === "landing"} isLanding layerRef={landingLayerRef}>
        <LandingLayer
          active={region === "landing"}
          onFly={fly}
          user={user}
          project={project}
          onUser={setUser}
        />
      </Layer>
      <Layer active={region === "graph"}>
        <GraphScreen onBack={goLanding} project={project} />
      </Layer>
      <Layer active={region === "model"}>
        <ModelScreen onBack={goLanding} project={project} />
      </Layer>
      <Layer active={region === "projects"}>
        <ProjectsScreen onBack={goLanding} project={project} onProject={setProject} />
      </Layer>
    </div>
  );
}
