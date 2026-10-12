import React from "react";
import { currentUser, login, logout, clearTenantBrowserData } from "../lib/auth.js";
import Input from "../components/forms/Input.jsx";
import { AUTH_EXPIRED_EVENT } from "../lib/apiClient.js";
import { fetchProjects, fetchGraph } from "../lib/graphApi.js";
import Button from "../components/forms/Button.jsx";
import ReadOnlyGraph from "./ReadOnlyGraph.jsx";
import { inspectionGraph } from "./inspection.js";
import { useT } from "../i18n/LanguageProvider.jsx";
import "./degram.css";

function statusText(status, t) {
  switch (status) {
    case "checking": return t("Checking session…");
    case "expired": return t("Sign in to DeGram — session expired.");
    case "signed-out": return t("Sign in to DeGram");
    case "select-project": return t("Select a project");
    case "no-projects": return t("No accessible projects. Ask your project owner for access.");
    case "access-denied": return t("Access denied. Refresh access or ask your project owner.");
    case "service-unavailable": return t("Service unavailable. Try again.");
    case "loading-graph": return t("Loading graph…");
    case "empty-graph": return t("This project has no graph nodes.");
    case "graph-unavailable": return t("Graph unavailable. Try again.");
    case "signing-in": return t("Signing in…");
    case "sign-in-failed": return t("Sign in failed. Check your account and try again.");
    case "signing-out": return t("Signing out…");
    case "sign-out-failed": return t("Read context cleared. Server sign-out unavailable; retry sign-out.");
    default: return status;
  }
}

export default function DeGramWorkspace() {
  const { t } = useT();
  const [user, setUser] = React.useState(null);
  const [projects, setProjects] = React.useState([]);
  const [project, setProject] = React.useState(null);
  const [graph, setGraph] = React.useState(null);
  const [status, setStatus] = React.useState("checking");
  const [signingOut, setSigningOut] = React.useState(false);
  const [logoutFailed, setLogoutFailed] = React.useState(false);
  const scope = React.useRef(0);
  const clearContext = React.useCallback((message, signedOut = false) => {
    ++scope.current;
    setProjects([]); setProject(null); setGraph(null);
    if (signedOut) setUser(null);
    clearTenantBrowserData(); setStatus(message);
  }, []);
  React.useEffect(() => {
    const expired = () => clearContext("expired", true);
    window.addEventListener(AUTH_EXPIRED_EVENT, expired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expired);
  }, [clearContext]);
  const refreshAccess = React.useCallback(async () => {
    const request = ++scope.current;
    setProjects([]); setProject(null); setGraph(null); setStatus("checking");
    try {
      const fresh = await currentUser();
      if (request !== scope.current) return;
      setUser(fresh);
      if (!fresh) { setStatus("signed-out"); return; }
      const available = await fetchProjects();
      if (request !== scope.current) return;
      setProjects(available);
      setStatus(available.length ? "select-project" : "no-projects");
    } catch (error) {
      if (request !== scope.current) return;
      if (error.status === 403) clearContext("access-denied");
      else setStatus("service-unavailable");
    }
  }, [clearContext]);
  React.useEffect(() => { refreshAccess(); return () => { ++scope.current; }; }, [refreshAccess]);
  React.useEffect(() => {
    if (!user || signingOut || logoutFailed) return;
    const recheck = () => { if (document.visibilityState !== "hidden") refreshAccess(); };
    window.addEventListener("focus", recheck);
    return () => window.removeEventListener("focus", recheck);
  }, [user, signingOut, logoutFailed, refreshAccess]);
  const select = async name => {
    const request = ++scope.current;
    setProject(name); setGraph(null); setStatus("loading-graph");
    try {
      const data = await fetchGraph(name);
      if (request === scope.current) {
        setGraph(data.nodes.length ? inspectionGraph(data) : null);
        setStatus(data.nodes.length ? "" : "empty-graph");
      }
    } catch (error) {
      if (request !== scope.current) return;
      if (error.status === 403) clearContext("access-denied");
      else setStatus("graph-unavailable");
    }
  };
  const signIn = async event => {
    event.preventDefault();
    if (status === "signing-in") return;
    const form = event.currentTarget;
    const username = form.elements.username.value;
    const password = form.elements.password.value;
    form.reset();
    const request = ++scope.current;
    setStatus("signing-in");
    try {
      const fresh = await login(username, password);
      if (request !== scope.current) return;
      setUser(fresh);
      const available = await fetchProjects();
      if (request !== scope.current) return;
      setProjects(available);
      setStatus(available.length ? "select-project" : "no-projects");
    } catch (error) {
      if (request !== scope.current) return;
      if (error.status === 403) clearContext("access-denied");
      else setStatus("sign-in-failed");
    }
  };
  const signOut = async () => {
    clearContext("signing-out", true);
    setSigningOut(true); setLogoutFailed(false);
    try {
      await logout();
      setStatus("signed-out");
    } catch {
      setLogoutFailed(true);
      setStatus("sign-out-failed");
    } finally { setSigningOut(false); }
  };
  return <main className="degram-workspace">
    <header className="degram-header"><h1>DeGram</h1><span>{t("Read-only workspace")}</span><span>{user?.name}</span>
      {!signingOut && !logoutFailed && <Button variant="outline" onClick={refreshAccess}>{t("Refresh access")}</Button>}
      {logoutFailed && <Button variant="outline" onClick={signOut}>{t("Retry sign-out")}</Button>}
      {user && <Button variant="outline" onClick={signOut}>{t("Sign out")}</Button>}
    </header>
    <nav className="degram-panel degram-projects" aria-label={t("Projects")}>
      <h2>{t("Projects")}</h2>
      {projects.map(p => <Button key={p.project} variant="outline" selected={project === p.project} onClick={() => select(p.project)}>{p.project}</Button>)}
    </nav>
    {status && <p className="degram-status" role="status">{statusText(status, t)}</p>}
    {!user && !signingOut && !logoutFailed && status !== "checking" && <form className="degram-status" onSubmit={signIn}>
      <Input label={t("Username")} name="username" autoComplete="username" required />
      <Input label={t("Password")} name="password" type="password" autoComplete="current-password" required />
      <Button type="submit" disabled={status === "signing-in"}>{t("Sign in")}</Button>
    </form>}
    {graph && <ReadOnlyGraph key={project} graph={graph} />}
  </main>;
}
