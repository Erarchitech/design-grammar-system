import React from "react";
import LandingEngine from "./landingEngine.js";
import { Button, Input } from "../components/index.js";
import * as auth from "../lib/auth.js";
import "./landing.css";
import { isDegramHost } from "../lib/hostMode.js";
import HostCentre from "./HostCentre.jsx";
import AssembleText from "./AssembleText.jsx";
import { useT } from "../i18n/LanguageProvider.jsx";
import { describeError, PRODUCT_NAME } from "../i18n/index.js";
import { getProjectSummary } from "../lib/summaryApi.js";
import { buildLandingSummaries } from "../lib/landingSummary.js";
import { fetchValidationRuns } from "../lib/modelApi.js";
import { getSettings } from "../lib/llmApi.js";
import { getReasonerSettings } from "../lib/reasonerApi.js";
import { listConnectors } from "../lib/connectorsApi.js";

// Client-side auth messages are stored as a code and translated at render, so a live language switch retranslates
// them (D-52). Server errors are stored as the error object and mapped by describeError.
function authMessage(t, e) {
  if (!e) return "";
  if (e.err) return describeError(e.err, t("Authentication failed."));
  switch (e.key) {
    case "invite-code":
      return t("Enter your invite code.");
    case "password-length":
      return t("Password must be at least 12 characters.");
    case "choose-username":
      return t("Choose a username.");
    case "password-mismatch":
      return t("The passwords do not match.");
    case "enter-username":
      return t("Enter your username.");
    case "enter-password":
      return t("Enter your password.");
    default:
      return t("Authentication failed.");
  }
}

// The landing experience: particle ring, materialising hero title, region
// callouts, and the inline auth card that rises through the particles.
// `active` gates canvas drawing; `onFly(region, originPoint)` navigates.
export default function LandingLayer({ active, onFly, user, project, onUser, hostState = "idle" }) {
  const { t } = useT();
  const degramHost = isDegramHost();
  const canvasRef = React.useRef(null);
  const heroTitleRef = React.useRef(null);
  const sphereRef = React.useRef(null);
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
  const [authCode, setAuthCode] = React.useState("");
  const [authUser, setAuthUser] = React.useState("");
  const [authPass, setAuthPass] = React.useState("");
  const [authPass2, setAuthPass2] = React.useState("");
  const [authErr, setAuthErr] = React.useState(null);
  // Register is offered only when the server says so; any failure hides it.
  const [canRegister, setCanRegister] = React.useState(false);
  const [sources, setSources] = React.useState({});
  const [sourceScope, setSourceScope] = React.useState(null);

  React.useEffect(() => {
    if (!active || !user) return;
    let stale = false;
    const loading = { status: "loading", data: null };
    setSourceScope({ project, username: user.name });
    setSources({ summary: loading, runs: loading, llm: loading, reasoner: loading, connectors: loading });
    const load = (key, request) => request()
      .then(data => { if (!stale) setSources(prev => ({ ...prev, [key]: { status: "ok", data } })); })
      .catch(() => { if (!stale) setSources(prev => ({ ...prev, [key]: { status: "error", data: null } })); });
    if (project) {
      load("summary", () => getProjectSummary(project));
      load("runs", () => fetchValidationRuns(project));
      if (!degramHost) load("connectors", () => listConnectors(project));
    }
    if (!degramHost) {
      load("llm", getSettings);
      load("reasoner", getReasonerSettings);
    }
    return () => { stale = true; };
  }, [active, user?.name, project, degramHost]);

  const scoped = sourceScope?.project === project && sourceScope?.username === user?.name ? sources : {};
  const summaries = buildLandingSummaries({ project, hostMode: degramHost, ...scoped });

  const refreshAuthOptions = React.useCallback(() => {
    auth
      .authOptions()
      .then((o) => setCanRegister(o.selfRegistration === true))
      .catch(() => setCanRegister(false));
  }, [degramHost]);
  React.useEffect(() => {
    refreshAuthOptions();
  }, [refreshAuthOptions]);

  React.useEffect(() => {
    const engine = new LandingEngine(
      {
        canvas: canvasRef.current,
        sphere: sphereRef.current,
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
      }
    , degramHost ? [
      { key: "graph", ang: Math.PI * 1.06, amp: 0.95, sig: 0.3, out: 62 },
      { key: "model", ang: -0.2, amp: 1.0, sig: 0.26, out: 62 },
      { key: "projects", ang: Math.PI * 0.62, amp: 0.72, sig: 0.22, out: 54 }
    ] : undefined);
    engineRef.current = engine;
    if (import.meta.env.DEV) window.__dgl = engine;
    engine.start();
    return () => engine.stop();
  }, [degramHost]);

  // Draw while the layer is on screen; keep drawing 620ms into a fly-away
  // so the ring is visible through the scale transition.
  React.useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    if (active) {
      engine.setVisible(true);
      if (engine.fontsReady && engine.heroPh === "hidden" && !authOpen && (!degramHost || hostState !== "connecting")) engine.setHeroPhase("forming");
    } else {
      const timer = setTimeout(() => engine.setVisible(false), 620);
      return () => clearTimeout(timer);
    }
  }, [active, authOpen, degramHost, hostState]);

  React.useEffect(() => {
    if (!degramHost) return;
    const engine = engineRef.current;
    if (!engine) return;
    engine.setHostConnecting(hostState === "connecting");
    if (hostState === "connecting") engine.setHeroPhase("dissolving");
    else if (!authOpen && engine.fontsReady) engine.setHeroPhase("forming");
  }, [degramHost, hostState, authOpen]);

  React.useEffect(() => {
    const engine = engineRef.current;
    if (engine) engine.setAuthOpen(authOpen);
    if (authOpen) {
      const timer = setTimeout(() => {
        const inp = document.querySelector("#dgl-hero-form-card input");
        if (inp) inp.focus();
      }, 620);
      return () => clearTimeout(timer);
    }
  }, [authOpen]);

  const openAuth = () => {
    engineRef.current?.setHeroPhase("dissolving");
    setAuthMode("login");
    setAuthErr(null);
    refreshAuthOptions();
    setAuthOpen(true);
  };
  const cancelAuth = () => {
    setAuthOpen(false);
    setAuthErr(null);
    engineRef.current?.setHeroPhase("forming");
  };
  const goAuthMode = (next) => {
    setAuthMode(next);
    setAuthErr(null);
    setAuthPass("");
    setAuthPass2("");
  };
  // A Register mode left selected after the server turned it off falls back to login.
  const mode = authMode === "register" && !canRegister ? "login" : authMode;
  const submitAuth = async () => {
    const invite = mode === "invite";
    const register = mode === "register";
    const username = authUser.trim();
    const code = authCode.trim();
    if (invite) {
      if (!code) return setAuthErr({ key: "invite-code" });
      // Client-side floor only; the server enforces the password policy.
      if (authPass.length < 12) return setAuthErr({ key: "password-length" });
    } else if (register) {
      if (!username) return setAuthErr({ key: "choose-username" });
      if (authPass.length < 12) return setAuthErr({ key: "password-length" });
      if (authPass !== authPass2) return setAuthErr({ key: "password-mismatch" });
    } else {
      if (!username) return setAuthErr({ key: "enter-username" });
      if (!authPass) return setAuthErr({ key: "enter-password" });
    }
    try {
      const u = invite
        ? await auth.acceptInvite(code, authPass)
        : register
          ? await auth.register(username, authPass)
          : await auth.login(username, authPass);
      onUser(u);
      setAuthOpen(false);
      setAuthErr(null);
      setAuthPass("");
      setAuthPass2("");
      setAuthCode("");
      engineRef.current?.setHeroPhase("forming");
    } catch (err) {
      setAuthErr({ err });
    }
  };
  const signOut = async () => {
    try {
      await auth.logout();
    } catch {
      // the local state is cleared either way; a live session expires server-side
    }
    onUser(null);
  };

  const fly = (region) => onFly(region, engineRef.current?.pk?.[region]);
  const reg = mode === "invite";
  const signUp = mode === "register";

  const cardStyle = authOpen
    ? { transitionDelay: "260ms", opacity: 1, transform: "translateY(0)", filter: "blur(0px)", pointerEvents: "auto" }
    : { transitionDelay: "0ms", opacity: 0, transform: "translateY(18px)", filter: "blur(9px)", pointerEvents: "none" };

  // One row per figure; every word rises out of its own mask in reading order once the engine marks the
  // label shown (data-on, landing.css .dgl-w).
  const renderSummary = (parts) => {
    if (parts === null) return null;
    let n = 0;
    const word = (text, key, valueStyle, title) => (
      <span key={key} className="dgl-w" style={{ "--d": `${(n++ * 0.07).toFixed(2)}s` }}>
        <span style={valueStyle} title={title}>{text}</span>
      </span>
    );
    const rows = parts === "—" ? [<span key="dash" className="dgl-sum-row">{word("—", "w")}</span>] : parts.map(({ label, value, title }) => (
      <span key={label} className="dgl-sum-row">
        {String(label).split(" ").map((w, i, all) => (
          <React.Fragment key={i}>{i > 0 && " "}{word(i === all.length - 1 ? `${w}:` : w, `l${i}`)}</React.Fragment>
        ))}
        {" "}
        {word(value, "v", title
          ? { color: "var(--text-primary)", maxWidth: "24ch", overflow: "hidden", textOverflow: "ellipsis", display: "inline-block", verticalAlign: "bottom" }
          : { color: "var(--text-primary)" }, title)}
      </span>
    ));
    return <span className="dgl-region-summary">{rows}</span>;
  };

  return (
    <>
      <canvas ref={canvasRef} className="dgl-canvas" />
      <img ref={sphereRef} className="dgl-think" alt="" aria-hidden="true" />

      <div ref={heroTitleRef} className="dgl-hero-title">
        <div ref={heroL1Ref} className="dgl-hero-l1">
          <AssembleText text={PRODUCT_NAME} tracking={0.3} />
        </div>
        <div ref={heroL2Ref} className="dgl-hero-l2">
          <AssembleText text={t("Encode Design Grammars")} tracking={0.3} />
        </div>
      </div>

      {degramHost && <HostCentre hostState={hostState} mode="connecting" />}

      <div ref={heroBeneathRef} className="dgl-hero-beneath">
        {!user && !authOpen && (
          <div style={{ pointerEvents: "auto" }}>
            <Button variant="outline" size="lg" onClick={openAuth}>
              {t("Log in")}
            </Button>
          </div>
        )}
        {user && !authOpen && (
          <div style={{ pointerEvents: "auto", display: "flex", flexDirection: "column", alignItems: "center", gap: 9 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--color-signal)", flex: "none" }} />
              <span className="dgl-user">
                {user.name}
              </span>
            </div>
            <div className="dgl-sys">
              {t("System initiated")} ·{" "}
              <span style={{ color: project ? "var(--color-signal)" : "var(--text-muted)" }}>
                {project || t("Select the project")}
              </span>
            </div>
            <div className="dgl-signout" onClick={signOut}>
              {t("Sign out")}
            </div>
            {degramHost && <HostCentre hostState={hostState} mode="pill" />}
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
              {reg ? t("Invitation") : signUp ? t("Register") : t("Access")}
            </div>
            <div style={{ font: "600 20px/1.15 var(--font-sans)", letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--text-primary)" }}>
              {reg ? t("Accept your invite") : signUp ? t("Create your account") : t("Welcome back")}
            </div>
            <div style={{ font: "400 13px/1.45 var(--font-sans)", color: "var(--text-muted)" }}>
              {reg
                ? t("Enter the code from your project owner and choose a password.")
                : signUp
                  ? t("Choose a username and a password of at least 12 characters. You can create your own projects afterwards.")
                  : t("Enter your credentials to access {product}.", { product: PRODUCT_NAME })}
            </div>
          </div>
          {reg ? (
            <Input placeholder={t("Invite code")} value={authCode} autoComplete="off" onChange={(e) => { setAuthCode(e.target.value); setAuthErr(null); }} />
          ) : (
            <Input placeholder={t("Username")} value={authUser} autoComplete="username" onChange={(e) => { setAuthUser(e.target.value); setAuthErr(null); }} />
          )}
          <Input
            type="password"
            placeholder={reg || signUp ? t("New password (12+ characters)") : t("Password")}
            autoComplete={reg || signUp ? "new-password" : "current-password"}
            value={authPass}
            onChange={(e) => { setAuthPass(e.target.value); setAuthErr(null); }}
            onKeyDown={(e) => { if (e.key === "Enter") submitAuth(); }}
          />
          {signUp && (
            <Input
              type="password"
              placeholder={t("Confirm password")}
              autoComplete="new-password"
              value={authPass2}
              onChange={(e) => { setAuthPass2(e.target.value); setAuthErr(null); }}
              onKeyDown={(e) => { if (e.key === "Enter") submitAuth(); }}
            />
          )}
          {authErr && <div style={{ font: "400 12px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>{authMessage(t, authErr)}</div>}
          <Button size="lg" style={{ width: "100%" }} onClick={submitAuth}>
            {reg ? t("Accept invite") : signUp ? t("Register") : t("Log in")}
          </Button>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 2 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {mode !== "login" && (
                <div className="dgl-auth-switch" onClick={() => goAuthMode("login")}>
                  {t("Have an account? Log in")}
                </div>
              )}
              {mode !== "invite" && (
                <div className="dgl-auth-switch" onClick={() => goAuthMode("invite")}>
                  {t("Have an invite code? Accept invite")}
                </div>
              )}
              {canRegister && mode !== "register" && (
                <div className="dgl-auth-switch" onClick={() => goAuthMode("register")}>
                  {t("New here? Register")}
                </div>
              )}
            </div>
            <div className="dgl-auth-cancel" onClick={cancelAuth}>
              {t("Cancel")}
            </div>
          </div>
        </div>
      </div>

      <div ref={labelGraphRef} className="dgl-region-label" onClick={() => fly("graph")}>
        {t("Graph Viewer")}
        {user && renderSummary(summaries.graph)}
      </div>
      <div ref={labelModelRef} className="dgl-region-label" onClick={() => fly("model")}>
        {t("Model Viewer")}
        {user && renderSummary(summaries.model)}
      </div>
      <div ref={labelProjectsRef} className="dgl-region-label" onClick={() => fly("projects")}>
        {t("Projects")}
      </div>
{!degramHost && <>
        <div ref={labelAiEngineRef} className="dgl-region-label" onClick={() => fly("aiengine")}>
          {t("LLM model")}
          {user && renderSummary(summaries.aiengine)}
        </div>
        <div ref={labelConnectorsRef} className="dgl-region-label" onClick={() => fly("connectors")}>
          {t("Connectors")}
          {user && renderSummary(summaries.connectors)}
        </div>
        <div ref={labelReasonerRef} className="dgl-region-label" onClick={() => fly("reasoner")}>
          {t("Reasoner")}
          {user && renderSummary(summaries.reasoner)}
        </div>
        <div ref={labelApiDocsRef} className="dgl-region-label" onClick={() => fly("apidocs")}>
          {t("DG API Docs")}
        </div>
      </>}
      <div ref={hintRef} className="dgl-hint">
        {t("Select a region")}
      </div>
    </>
  );
}
