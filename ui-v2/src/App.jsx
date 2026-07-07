import React from "react";
import SpecimenPage from "./specimen/SpecimenPage.jsx";

// Dev-only specimen route (open /#specimen while running `npm run dev`).
// The real app shell — landing / graph / model / projects layers — arrives
// in Phase 22; until then the root renders a minimal blueprint placeholder.
export default function App() {
  const [hash, setHash] = React.useState(window.location.hash);
  React.useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (import.meta.env.DEV && hash === "#specimen") return <SpecimenPage />;

  return (
    <div
      className="dg-blueprint"
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 10
      }}
    >
      <div
        style={{
          font: "600 clamp(32px, 5vw, 64px)/1.06 var(--font-annotation)",
          textTransform: "uppercase",
          letterSpacing: "1px",
          color: "var(--text-primary)"
        }}
      >
        Design Grammars.
      </div>
      <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
        System pending · shell arrives in phase 22
      </div>
    </div>
  );
}
