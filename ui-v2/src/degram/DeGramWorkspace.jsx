import React from "react";
import { currentUser, login, logout, clearTenantBrowserData } from "../lib/auth.js";
import Input from "../components/forms/Input.jsx";
import { AUTH_EXPIRED_EVENT } from "../lib/apiClient.js";
import { fetchProjects, fetchGraph } from "../lib/graphApi.js";
import Button from "../components/forms/Button.jsx";
import ReadOnlyGraph from "./ReadOnlyGraph.jsx";
import { inspectionGraph } from "./inspection.js";
import "./degram.css";

export default function DeGramWorkspace() {
  const [user, setUser] = React.useState(null);
  const [projects, setProjects] = React.useState([]);
  const [project, setProject] = React.useState(null);
  const [graph, setGraph] = React.useState(null);
  const [status, setStatus] = React.useState("Checking session…");
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
    const expired = () => clearContext("Sign in to DeGram — session expired.", true);
    window.addEventListener(AUTH_EXPIRED_EVENT, expired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expired);
  }, [clearContext]);
  const refreshAccess = React.useCallback(async () => {
    const request = ++scope.current;
    setProjects([]); setProject(null); setGraph(null); setStatus("Checking session…");
    try {
      const fresh = await currentUser();
      if (request !== scope.current) return;
      setUser(fresh);
      if (!fresh) { setStatus("Sign in to DeGram"); return; }
      const available = await fetchProjects();
      if (request !== scope.current) return;
      setProjects(available);
      setStatus(available.length ? "Select a project" : "No accessible projects. Ask your project owner for access.");
    } catch (error) {
      if (request !== scope.current) return;
      if (error.status === 403) clearContext("Access denied. Refresh access or ask your project owner.");
      else setStatus("Service unavailable. Try again.");
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
    setProject(name); setGraph(null); setStatus("Loading graph…");
    try {
      const data = await fetchGraph(name);
      if (request === scope.current) {
        setGraph(data.nodes.length ? inspectionGraph(data) : null);
        setStatus(data.nodes.length ? "" : "This project has no graph nodes.");
      }
    } catch (error) {
      if (request !== scope.current) return;
      if (error.status === 403) clearContext("Access denied. Refresh access or ask your project owner.");
      else setStatus("Graph unavailable. Try again.");
    }
  };
  const signIn = async event => {
    event.preventDefault();
    if (status === "Signing in…") return;
    const form = event.currentTarget;
    const username = form.elements.username.value;
    const password = form.elements.password.value;
    form.reset();
    const request = ++scope.current;
    setStatus("Signing in…");
    try {
      const fresh = await login(username, password);
      if (request !== scope.current) return;
      setUser(fresh);
      const available = await fetchProjects();
      if (request !== scope.current) return;
      setProjects(available);
      setStatus(available.length ? "Select a project" : "No accessible projects. Ask your project owner for access.");
    } catch (error) {
      if (request !== scope.current) return;
      if (error.status === 403) clearContext("Access denied. Refresh access or ask your project owner.");
      else setStatus("Sign in failed. Check your account and try again.");
    }
  };
  const signOut = async () => {
    clearContext("Signing out…", true);
    setSigningOut(true); setLogoutFailed(false);
    try {
      await logout();
      setStatus("Sign in to DeGram");
    } catch {
      setLogoutFailed(true);
      setStatus("Read context cleared. Server sign-out unavailable; retry sign-out.");
    } finally { setSigningOut(false); }
  };
  return <main className="degram-workspace">
    <header className="degram-header"><h1>DeGram</h1><span>Read-only workspace</span><span>{user?.name}</span>
      {!signingOut && !logoutFailed && <Button variant="outline" onClick={refreshAccess}>Refresh access</Button>}
      {logoutFailed && <Button variant="outline" onClick={signOut}>Retry sign-out</Button>}
      {user && <Button variant="outline" onClick={signOut}>Sign out</Button>}
    </header>
    <nav className="degram-panel degram-projects" aria-label="Projects">
      <h2>Projects</h2>
      {projects.map(p => <Button key={p.project} variant="outline" selected={project === p.project} onClick={() => select(p.project)}>{p.project}</Button>)}
    </nav>
    {status && <p className="degram-status" role="status">{status}</p>}
    {!user && !signingOut && !logoutFailed && status !== "Checking session…" && <form className="degram-status" onSubmit={signIn}>
      <Input label="Username" name="username" autoComplete="username" required />
      <Input label="Password" name="password" type="password" autoComplete="current-password" required />
      <Button type="submit" disabled={status === "Signing in…"}>Sign in</Button>
    </form>}
    {graph && <ReadOnlyGraph key={project} graph={graph} />}
  </main>;
}
