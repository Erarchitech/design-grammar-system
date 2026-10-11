import React from "react";
import LandingLayer from "./landing/LandingLayer.jsx";
import GraphScreen from "./screens/GraphScreen.jsx";
import ModelScreen from "./screens/ModelScreen.jsx";
import ProjectsScreen from "./screens/ProjectsScreen.jsx";
import AiEngineScreen from "./screens/AiEngineScreen.jsx";
import ConnectorsScreen from "./screens/ConnectorsScreen.jsx";
import ReasonerScreen from "./screens/ReasonerScreen.jsx";
import ApiDocsScreen from "./screens/ApiDocsScreen.jsx";
import SpecimenPage from "./specimen/SpecimenPage.jsx";
import { currentUser, purgeLegacyLocalAuth, clearTenantBrowserData, OWNER_KEY } from "./lib/auth.js";
import { AUTH_EXPIRED_EVENT } from "./lib/apiClient.js";
import { announceProject, isRegionAllowed } from "./lib/hostMode.js";

const EASE = "cubic-bezier(0.2, 0, 0, 1)";

// One of the screen layers. All stay mounted; the active one is scaled
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
  // D-01: identity is resolved asynchronously from GET /auth/me (session cookie).
  const [user, setUser] = React.useState(null);
  const [project, setProject] = React.useState(() => localStorage.getItem("dgv2_project") || null);
  const [theme, setTheme] = React.useState(() => (localStorage.getItem("dgv2_theme") === "dark" ? "dark" : "light"));
  const landingLayerRef = React.useRef(null);

  // Theme: stamp <html data-theme> for the CSS token overrides and notify
  // the canvas engines (they listen for "dg-theme" to swap palettes).
  React.useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("dgv2_theme", theme);
    } catch {
      // storage unavailable — theme resets on reload
    }
    window.dispatchEvent(new CustomEvent("dg-theme", { detail: theme }));
  }, [theme]);

  React.useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Resolve the signed-in user from the server; drop the legacy browser
  // accounts (D-05); return to the signed-out state whenever any call 401s.
  React.useEffect(() => {
    let cancelled = false;
    purgeLegacyLocalAuth();
    currentUser()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        // server unreachable — stay signed out; the login card reports errors
      });
    const onExpired = () => setUser(null);
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => {
      cancelled = true;
      window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
    };
  }, []);

  // WR-09: tenant data must not outlive the session that loaded it. Sign-out
  // and session expiry (user -> null) wipe the tenant keys and the project
  // scope; a sign-in as a DIFFERENT account than the browser's last owner
  // does the same, so the next user never inherits the previous user's data.
  const prevUserRef = React.useRef(null);
  React.useEffect(() => {
    const prev = prevUserRef.current;
    prevUserRef.current = user ? user.email : null;
    if (prev && !user) {
      clearTenantBrowserData();
      setProject(null);
    }
  }, [user]);
  React.useEffect(() => {
    if (!user) return;
    try {
      const owner = localStorage.getItem(OWNER_KEY);
      if (owner && owner !== user.email) {
        clearTenantBrowserData();
        setProject(null);
      }
      localStorage.setItem(OWNER_KEY, user.email);
    } catch {
      // storage unavailable — nothing persisted to protect
    }
  }, [user?.email]);

  // A remembered project the user is not a member of is forgotten (admins
  // keep it), together with any tenant data cached for it. The server denies
  // access anyway; this avoids a stale scope.
  React.useEffect(() => {
    if (!user || user.isAdmin || !project) return;
    if (!user.memberships.some((m) => m.project === project)) {
      clearTenantBrowserData();
      try {
        localStorage.setItem(OWNER_KEY, user.email);
      } catch {
        // storage unavailable
      }
      setProject(null);
    }
  }, [user, project]);

  // Selecting a project first refreshes memberships so a project created or
  // joined a moment ago is not mistaken for a stale one by the effect above.
  const selectProject = React.useCallback(async (name) => {
    if (name) {
      try {
        const fresh = await currentUser();
        if (fresh) setUser(fresh);
      } catch {
        // keep the previous memberships
      }
    }
    setProject(name);
    announceProject(name);
  }, []);

  React.useEffect(() => {
    if (project) localStorage.setItem("dgv2_project", project);
    else localStorage.removeItem("dgv2_project");
  }, [project]);

  // fly(region, originPoint): when leaving the landing via a region callout,
  // the landing layer zooms toward the callout's ring point.
  const fly = React.useCallback((next, origin) => {
    if (!isRegionAllowed(next)) return;
    if (origin && landingLayerRef.current) {
      landingLayerRef.current.style.transformOrigin = origin[0] + "px " + origin[1] + "px";
    }
    setRegion(next);
  }, []);
  const goLanding = React.useCallback(() => setRegion("landing"), []);

  React.useEffect(() => {
    if (!isRegionAllowed(region)) setRegion("landing");
  }, [region]);

  React.useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape" && region !== "landing") setRegion("landing");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [region]);

  if (import.meta.env.DEV && hash === "#specimen") return <SpecimenPage />;

  // WR-09: the screen layers are keyed on the signed-in identity so a sign-out
  // or account change discards their in-memory graph, run and token state.
  const screenKey = user ? user.email : "anon";

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
        <GraphScreen key={screenKey} active={region === "graph"} onBack={goLanding} project={project} />
      </Layer>
      <Layer active={region === "model"}>
        <ModelScreen key={screenKey} active={region === "model"} onBack={goLanding} project={project} />
      </Layer>
      <Layer active={region === "projects"}>
        <ProjectsScreen key={screenKey} active={region === "projects"} onBack={goLanding} project={project} onProject={selectProject} user={user} />
      </Layer>
      <Layer active={region === "aiengine"}>
        <AiEngineScreen key={screenKey} active={region === "aiengine"} onBack={goLanding} project={project} />
      </Layer>
      <Layer active={region === "connectors"}>
        <ConnectorsScreen key={screenKey} active={region === "connectors"} onBack={goLanding} project={project} user={user} />
      </Layer>
      <Layer active={region === "reasoner"}>
        <ReasonerScreen key={screenKey} active={region === "reasoner"} onBack={goLanding} project={project} />
      </Layer>
      <Layer active={region === "apidocs"}>
        <ApiDocsScreen key={screenKey} active={region === "apidocs"} onBack={goLanding} project={project} />
      </Layer>

      {/* dark / light toggle — global, floats above every layer */}
      <div
        className="dg-frost"
        onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        style={{
          position: "absolute",
          right: 18,
          bottom: 18,
          zIndex: 50,
          width: 36,
          height: 36,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: "var(--shadow-panel)",
          color: "var(--text-secondary)"
        }}
      >
        {theme === "dark" ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </div>
    </div>
  );
}
