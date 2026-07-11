import React from "react";
import LandingEngine from "./landingEngine.js";
import { Button, Input } from "../components/index.js";
import * as auth from "../lib/auth.js";
import "./landing.css";

// The landing experience: particle ring, materialising hero title, region
// callouts, and the inline auth card that rises through the particles.
// `active` gates canvas drawing; `onFly(region, originPoint)` navigates.
export default function LandingLayer({ active, onFly, user, project, onUser }) {
  const canvasRef = React.useRef(null);
  const heroTitleRef = React.useRef(null);
  const heroL1Ref = React.useRef(null);
  const heroL2Ref = React.useRef(null);
  const heroBeneathRef = React.useRef(null);
  const heroFormRef = React.useRef(null);
  const labelGraphRef = React.useRef(null);
  const labelModelRef = React.useRef(null);
  const labelProjectsRef = React.useRef(null);
  const labelAiEngineRef = React.useRef(null);
  const labelConnectorsRef = React.useRef(null);
  const labelReasonerRef = React.useRef(null);
  const labelApiDocsRef = React.useRef(null);
  const hintRef = React.useRef(null);
  const engineRef = React.useRef(null);

  const [authOpen, setAuthOpen] = React.useState(false);
  const [authMode, setAuthMode] = React.useState("login");
  const [authName, setAuthName] = React.useState("");
  const [authEmail, setAuthEmail] = React.useState("");
  const [authPass, setAuthPass] = React.useState("");
  const [authErr, setAuthErr] = React.useState("");

  React.useEffect(() => {
    const engine = new LandingEngine(
      {
        canvas: canvasRef.current,
        heroTitle: heroTitleRef.current,
        heroL1: heroL1Ref.current,
        heroL2: heroL2Ref.current,
        heroBeneath: heroBeneathRef.current,
        heroForm: heroFormRef.current,
        labels: {
          graph: labelGraphRef.current,
          model: labelModelRef.current,
          projects: labelProjectsRef.current,
          aiengine: labelAiEngineRef.current,
          connectors: labelConnectorsRef.current,
          reasoner: labelReasonerRef.current,
          apidocs: labelApiDocsRef.current
        },
        hint: hintRef.current
      },
      { density: 2 }
    );
    engineRef.current = engine;
    if (import.meta.env.DEV) window.__dgl = engine;
    engine.start();
    return () => engine.stop();
  }, []);

  // Draw while the layer is on screen; keep drawing 620ms into a fly-away
  // so the ring is visible through the scale transition.
  React.useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    if (active) {
      engine.setVisible(true);
      if (engine.fontsReady && engine.heroPh === "hidden" && !authOpen) engine.setHeroPhase("forming");
    } else {
      const t = setTimeout(() => engine.setVisible(false), 620);
      return () => clearTimeout(t);
    }
  }, [active, authOpen]);

  React.useEffect(() => {
    const engine = engineRef.current;
    if (engine) engine.setAuthOpen(authOpen);
    if (authOpen) {
      const t = setTimeout(() => {
        const inp = document.querySelector("#dgl-hero-form-card input");
        if (inp) inp.focus();
      }, 620);
      return () => clearTimeout(t);
    }
  }, [authOpen]);

  const openAuth = () => {
    engineRef.current?.setHeroPhase("dissolving");
    setAuthMode("login");
    setAuthErr("");
    setAuthOpen(true);
  };
  const cancelAuth = () => {
    setAuthOpen(false);
    setAuthErr("");
    engineRef.current?.setHeroPhase("forming");
  };
  const switchAuthMode = () => {
    setAuthMode((m) => (m === "login" ? "register" : "login"));
    setAuthErr("");
  };
  const submitAuth = async () => {
    const email = authEmail.trim();
    const reg = authMode === "register";
    if (reg && !authName.trim()) return setAuthErr("Enter your name.");
    if (!email || email.indexOf("@") < 1) return setAuthErr("Enter a valid email.");
    if (authPass.length < 4) return setAuthErr("Password must be at least 4 characters.");
    try {
      const u = reg ? await auth.register(authName, email, authPass) : await auth.login(email, authPass);
      onUser(u);
      setAuthOpen(false);
      setAuthErr("");
      setAuthPass("");
      engineRef.current?.setHeroPhase("forming");
    } catch (err) {
      setAuthErr(err.message || "Authentication failed.");
    }
  };
  const signOut = () => {
    auth.signOut();
    onUser(null);
  };

  const fly = (region) => onFly(region, engineRef.current?.pk?.[region]);
  const reg = authMode === "register";

  const cardStyle = authOpen
    ? { transitionDelay: "260ms", opacity: 1, transform: "translateY(0)", filter: "blur(0px)", pointerEvents: "auto" }
    : { transitionDelay: "0ms", opacity: 0, transform: "translateY(18px)", filter: "blur(9px)", pointerEvents: "none" };

  return (
    <>
      <canvas ref={canvasRef} className="dgl-canvas" />

      <div ref={heroTitleRef} className="dgl-hero-title">
        <div ref={heroL1Ref} className="dgl-hero-l1">
          Design Grammars.
        </div>
        <div ref={heroL2Ref} className="dgl-hero-l2">
          Encode your design intent.
        </div>
      </div>

      <div ref={heroBeneathRef} className="dgl-hero-beneath">
        {!user && !authOpen && (
          <div style={{ pointerEvents: "auto" }}>
            <Button variant="outline" size="lg" onClick={openAuth}>
              Login / Register
            </Button>
          </div>
        )}
        {user && !authOpen && (
          <div style={{ pointerEvents: "auto", display: "flex", flexDirection: "column", alignItems: "center", gap: 9 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--color-signal)", flex: "none" }} />
              <span style={{ font: "600 21px/1.1 var(--font-sans)", letterSpacing: "-0.5px", color: "var(--text-primary)" }}>
                {user.name}
              </span>
            </div>
            <div className="dg-annotation" style={{ fontSize: 11, letterSpacing: "1.4px", color: "var(--text-muted)" }}>
              System initiated ·{" "}
              <span style={{ color: project ? "var(--color-signal)" : "var(--text-muted)" }}>
                {project || "Select the project"}
              </span>
            </div>
            <div className="dgl-signout" onClick={signOut}>
              Sign out
            </div>
          </div>
        )}
      </div>

      <div ref={heroFormRef} className="dgl-hero-form">
        <div
          id="dgl-hero-form-card"
          className="dg-frost"
          style={{
            width: "min(372px, 86vw)",
            boxSizing: "border-box",
            borderRadius: "var(--radius-cards)",
            padding: "26px 26px 22px",
            boxShadow: "var(--shadow-panel)",
            display: "flex",
            flexDirection: "column",
            gap: 15,
            transition:
              "opacity 500ms cubic-bezier(0.2,0,0,1), transform 560ms cubic-bezier(0.2,0,0,1), filter 500ms cubic-bezier(0.2,0,0,1)",
            ...cardStyle
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
              {reg ? "New account" : "Access"}
            </div>
            <div style={{ font: "600 22px/1.15 var(--font-sans)", letterSpacing: "-0.6px", color: "var(--text-primary)" }}>
              {reg ? "Create your account" : "Welcome back"}
            </div>
            <div style={{ font: "400 13px/1.45 var(--font-sans)", color: "var(--text-muted)" }}>
              {reg ? "Register to start encoding design intent." : "Enter your credentials to access Design Grammars."}
            </div>
          </div>
          {reg && <Input placeholder="Full name" value={authName} onChange={(e) => { setAuthName(e.target.value); setAuthErr(""); }} />}
          <Input type="email" placeholder="Email" value={authEmail} onChange={(e) => { setAuthEmail(e.target.value); setAuthErr(""); }} />
          <Input
            type="password"
            placeholder="Password"
            value={authPass}
            onChange={(e) => { setAuthPass(e.target.value); setAuthErr(""); }}
            onKeyDown={(e) => { if (e.key === "Enter") submitAuth(); }}
          />
          {authErr && <div style={{ font: "400 12px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>{authErr}</div>}
          <Button size="lg" style={{ width: "100%" }} onClick={submitAuth}>
            {reg ? "Register" : "Log in"}
          </Button>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 2 }}>
            <div className="dgl-auth-switch" onClick={switchAuthMode}>
              {reg ? "Have an account? Log in" : "Need an account? Register"}
            </div>
            <div className="dgl-auth-cancel" onClick={cancelAuth}>
              Cancel
            </div>
          </div>
        </div>
      </div>

      <div ref={labelGraphRef} className="dgl-region-label" onClick={() => fly("graph")}>
        Graph Viewer
      </div>
      <div ref={labelModelRef} className="dgl-region-label" onClick={() => fly("model")}>
        Model Viewer
      </div>
      <div ref={labelProjectsRef} className="dgl-region-label" onClick={() => fly("projects")}>
        Projects.
      </div>
      <div ref={labelAiEngineRef} className="dgl-region-label" onClick={() => fly("aiengine")}>
        AI Engine
      </div>
      <div ref={labelConnectorsRef} className="dgl-region-label" onClick={() => fly("connectors")}>
        Connectors
      </div>
      <div ref={labelReasonerRef} className="dgl-region-label" onClick={() => fly("reasoner")}>
        Reasoner
      </div>
      <div ref={labelApiDocsRef} className="dgl-region-label" onClick={() => fly("apidocs")}>
        DG API Docs
      </div>
      <div ref={hintRef} className="dg-annotation dg-annotation--muted dgl-hint">
        Select a region
      </div>
    </>
  );
}
