import React from "react";
import { Button, Select } from "../components/index.js";
import {
  listConnectors,
  listMyGrants,
  requestGrant,
  requestConnectorAccess,
  listProjectConnectorAccess,
  issueConnectorAccess,
  revokeConnectorAccess,
  DEGRAM_CONNECTOR_ID
} from "../lib/connectorsApi.js";
import { listProjectMembers } from "../lib/memberApi.js";
import { ApiError } from "../lib/apiClient.js";
import { isDegramHost } from "../lib/hostMode.js";
import { describeError, formatDate } from "../i18n/index.js";
import { useT } from "../i18n/LanguageProvider.jsx";
import DegramGrantsPanel from "./DegramGrantsPanel.jsx";
import HostedConnectorsTable from "./HostedConnectorsTable.jsx";

const muted = { font: "400 14px/1.5 var(--font-sans)", color: "var(--text-muted)" };
const errorStyle = { font: "400 12px/1.4 var(--font-sans)", color: "var(--status-fail)" };
const rowStyle = { display: "flex", alignItems: "center", gap: 8, padding: "7px 10px", borderBottom: "1px solid var(--color-hairline)", font: "400 13px/1.3 var(--font-sans)" };
const sectionHeading = { font: "500 11px/1 var(--font-sans)", color: "var(--text-muted)", padding: "8px 10px 2px" };
const SECTION_EYEBROW = { font: "500 11px/1 var(--font-sans)", letterSpacing: "1.5px", textTransform: "uppercase", color: "var(--text-muted)", margin: "32px 0 12px" };

// A grant for another connector, or an inactive grant, cannot exclude a member.
export function eligibleGrantMembers(members, grants, connectorId) {
  const granted = new Set(grants.filter((g) => g.connector_id === connectorId && g.active).map((g) => g.username?.toLowerCase()));
  return members.filter((m) => (m.role === "editor" || m.role === "viewer") && !granted.has(m.username?.toLowerCase()));
}

// The normal Web UI uses ink/gray; the hosted table deliberately uses green/red.
function StatusDot({ status }) {
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: status === "active" ? "var(--status-pass)" : "var(--status-base)", opacity: status === "never_connected" ? 0.35 : 1, flex: "none" }} />;
}

function SignInCount({ count, tp }) {
  return <div>{tp("{n} live sign-ins", count ?? 0)}</div>;
}

function AccessLine({ access, canAdminister, t }) {
  if (canAdminister) return <div>{t("Access: included with your role")}</div>;
  if (access === "available") return <div>{t("Access: granted")}</div>;
  if (access === "pending") return <div>{t("Access: requested")}</div>;
  return <div>{t("Access: not granted")}</div>;
}

function GrantToMemberForm({ members, grants, connectorId, busy, onGrant, t }) {
  const [username, setUsername] = React.useState("");
  const eligible = eligibleGrantMembers(members, grants, connectorId);
  const selected = eligible.some((m) => m.username === username) ? username : "";
  if (eligible.length === 0) return <p style={{ ...muted, margin: "8px 10px" }}>{t("All editors and viewers already have access.")}</p>;
  return (
    <form onSubmit={(event) => { event.preventDefault(); if (selected && !busy) { onGrant(connectorId, selected); setUsername(""); } }} style={{ padding: "8px 10px", display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}>
      <div style={{ minWidth: 180 }}>
        <span style={{ ...muted, fontSize: 12 }}>{t("Member")}</span>
        <Select aria-label={t("Member")} value={selected} onChange={(event) => setUsername(event.target.value)} options={[{ value: "", label: t("Select a member") }, ...eligible.map((m) => ({ value: m.username, label: m.username }))]} />
      </div>
      <Button size="sm" type="submit" disabled={busy || !selected}>{t("Grant access")}</Button>
    </form>
  );
}

function ConnectorAccessAdmin({ connectorId, requests, grants, members, busy, onGrant, onRevoke, t }) {
  const issued = grants.filter((g) => g.active);
  return (
    <div data-testid="connector-access-admin">
      <div style={sectionHeading}>{t("Access requests")}</div>
      {requests.map((r) => (
        <div key={r.request_id} style={rowStyle}>
          <span style={{ flex: 1 }}>{r.username} · {r.note || "—"} · {formatDate(r.created_at)}</span>
          <Button size="sm" disabled={busy} onClick={() => onGrant(connectorId, r.username)}>{t("Grant access")}</Button>
        </div>
      ))}
      <div style={sectionHeading}>{t("Granted access")}</div>
      {issued.length === 0 && <p style={{ ...muted, margin: "8px 10px" }}>{t("No access has been granted yet.")}</p>}
      {issued.map((g) => (
        <div key={g.access_id} style={rowStyle}>
          <span style={{ flex: 1 }}>{g.username} · {formatDate(g.created_at)}</span>
          <Button size="sm" variant="destructive" disabled={busy} onClick={() => onRevoke(connectorId, g.access_id)}>{t("Revoke access")}</Button>
        </div>
      ))}
      <div style={sectionHeading}>{t("Grant access to a member")}</div>
      <GrantToMemberForm members={members} grants={grants} connectorId={connectorId} busy={busy} onGrant={onGrant} t={t} />
    </div>
  );
}

function RequestAccessForm({ connectorId, busy, onRequest, t }) {
  const [note, setNote] = React.useState("");
  return (
    <form onSubmit={(event) => { event.preventDefault(); if (!busy) onRequest(connectorId, note.trim()); }} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", padding: "8px 10px" }}>
      <input aria-label={t("Note (optional)")} placeholder={t("Note (optional)")} maxLength={200} value={note} onChange={(event) => setNote(event.target.value)} style={{ height: 28, border: "1px solid var(--color-hairline)", borderRadius: "var(--radius-inputs)", padding: "0 10px", background: "var(--surface-input)", color: "var(--color-ink)" }} />
      <Button size="sm" type="submit" disabled={busy}>{t("Request access")}</Button>
    </form>
  );
}

function ConnectorCard({ connector, expanded, onToggle, project, user, active, canAdminister, adminReady, accessData, members, busy, error, onGrant, onRevoke, onRequest, t, tp }) {
  const isDegram = connector.id === DEGRAM_CONNECTOR_ID;
  return (
    <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", boxShadow: "var(--shadow-panel)", marginBottom: 10, overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "14px 18px", cursor: "pointer", userSelect: "none" }} onClick={() => onToggle(connector.id)}>
        <StatusDot status={connector.status} />
        <span style={{ font: "500 15px/1 var(--font-sans)", color: "var(--color-ink)", flex: 1 }}>{connector.name}</span>
        <span style={{ font: "400 12px/1 var(--font-sans)", color: "var(--text-muted)" }}>{connector.status === "active" ? t("On") : t("Off")}</span>
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: expanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform var(--duration-fast) var(--ease-out)", color: "var(--text-muted)" }}><path d="m6 9 6 6 6-6" /></svg>
      </div>
      {expanded && (isDegram ? <DegramGrantsPanel project={project} user={user} active={active} /> : (
        <div style={{ borderTop: "1px solid var(--color-hairline)" }}>
          <div style={{ ...muted, display: "grid", gap: 4, padding: "14px 18px" }}>
            <div>{connector.status === "active" ? t("On") : t("Off")} · {connector.last_connection ? t("Last sign-in {date}", { date: formatDate(connector.last_connection) }) : t("Never signed in")}</div>
            <SignInCount count={connector.active_sessions} tp={tp} />
            <AccessLine access={connector.access} canAdminister={canAdminister} t={t} />
            <div>{t("Sign in from {connector} with your DG account. No token is needed.", { connector: connector.name })}</div>
          </div>
          {canAdminister && project && adminReady ? (
            <ConnectorAccessAdmin connectorId={connector.id} requests={accessData.requests.filter((r) => r.connector_id === connector.id)} grants={accessData.grants.filter((g) => g.connector_id === connector.id)} members={members} busy={busy} onGrant={onGrant} onRevoke={onRevoke} t={t} />
          ) : project && connector.access === "requestable" ? (
            <RequestAccessForm connectorId={connector.id} busy={busy} onRequest={onRequest} t={t} />
          ) : null}
          {error && <p role="alert" style={{ ...errorStyle, margin: "8px 18px" }}>{describeError(error, t("Could not complete the request. Try again."))}</p>}
        </div>
      ))}
    </div>
  );
}

export default function ConnectorsScreen({ active, onBack, project, user }) {
  const hosted = isDegramHost();
  const { t, tp } = useT();
  const [categories, setCategories] = React.useState([]);
  const [connectors, setConnectors] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [loadErr, setLoadErr] = React.useState(null);
  const [expanded, setExpanded] = React.useState({});
  const [busy, setBusy] = React.useState({});
  const [errors, setErrors] = React.useState({});
  const [accessData, setAccessData] = React.useState({ grants: [], requests: [] });
  const [members, setMembers] = React.useState([]);
  const [myGrants, setMyGrants] = React.useState(null);
  const [loadedProject, setLoadedProject] = React.useState(null);
  const [adminLoaded, setAdminLoaded] = React.useState(false);
  const activeRole = user?.memberships?.find((m) => m.project === project)?.role;
  const canAdminister = activeRole === "owner" || !!user?.isAdmin;
  const loadSeq = React.useRef(0);
  const busyRef = React.useRef(false);
  const currentProject = React.useRef(project);
  currentProject.current = project;

  const load = React.useCallback(() => {
    const seq = ++loadSeq.current;
    setLoading(true);
    setLoadErr(null);
    setLoadedProject(null);
    setAdminLoaded(false);
    // The registry must be scoped to the selected project even outside DeGram.
    const registry = listConnectors(project);
    const extra = hosted ? listMyGrants().catch(() => null)
      : canAdminister && project ? listProjectConnectorAccess(project) : Promise.resolve(null);
    const people = !hosted && canAdminister && project ? listProjectMembers(project) : Promise.resolve(null);
    Promise.all([registry, extra, people]).then(([data, more, memberData]) => {
      if (seq !== loadSeq.current) return;
      setCategories(data.categories || []);
      setConnectors(data.connectors || []);
      setLoadedProject(project);
      setAdminLoaded(!canAdminister || hosted || (!!more && !!memberData));
      if (hosted) setMyGrants(more);
      else {
        setAccessData({ grants: more?.grants || [], requests: more?.requests || [] });
        setMembers(memberData?.members || []);
      }
    }).catch((err) => {
      if (seq === loadSeq.current) setLoadErr(err);
    }).finally(() => {
      if (seq === loadSeq.current) setLoading(false);
    });
  }, [hosted, project, canAdminister]);

  React.useEffect(() => {
    setErrors({});
    setExpanded({});
  }, [project]);

  React.useEffect(() => {
    if (active && project) load();
    return () => { loadSeq.current += 1; };
  }, [active, project, load]);

  const projectReady = !!project && project === loadedProject && !loadErr;
  const adminReady = projectReady && adminLoaded;
  const visibleConnectors = projectReady ? connectors : [];
  const visibleCategories = projectReady ? categories : [];

  const setError = (id, err) => setErrors((prev) => ({ ...prev, [id]: err }));
  const actOn = async (id, action) => {
    if (busyRef.current || !projectReady) return;
    const actionProject = project;
    const actionSeq = loadSeq.current;
    busyRef.current = true;
    setBusy((prev) => ({ ...prev, [id]: true }));
    setError(id, null);
    try { await action(); if (currentProject.current === actionProject && loadSeq.current === actionSeq) load(); }
    catch (err) { if (currentProject.current === actionProject && loadSeq.current === actionSeq) setError(id, err); }
    finally { busyRef.current = false; setBusy((prev) => ({ ...prev, [id]: false })); }
  };
  const grantAccess = (connectorId, username) => actOn(connectorId, () => issueConnectorAccess(project, { username, connectorId }));
  const revokeAccess = (connectorId, accessId) => {
    if (globalThis.confirm(t("Revoke this connector access?"))) actOn(connectorId, () => revokeConnectorAccess(project, accessId));
  };
  const requestAccess = (connectorId, note) => actOn(connectorId, async () => {
    try { await requestConnectorAccess(project, connectorId, note); }
    catch (err) { if (!(err instanceof ApiError && err.status === 409 && err.code === "ACCESS_EXISTS")) throw err; }
  });
  const hostedRequestDegram = (note) => actOn(DEGRAM_CONNECTOR_ID, async () => {
    try { await requestGrant(project, note); }
    catch (err) { if (!(err instanceof ApiError && err.status === 409 && err.code === "GRANT_EXISTS")) throw err; }
  });

  if (hosted) return (
    <HostedConnectorsTable connectors={visibleConnectors} project={project} myGrants={projectReady ? myGrants : null} loading={loading} error={loadErr ? describeError(loadErr, t("Connectors unavailable.")) : ""} busy={busy} errors={Object.fromEntries(Object.entries(errors).map(([id, err]) => [id, err ? describeError(err, t("Could not complete the request. Try again.")) : ""]))} onRefresh={load} onRequestAccess={requestAccess} onRequestDegram={hostedRequestDegram} />
  );

  const grouped = visibleCategories.map((category) => ({ category, items: visibleConnectors.filter((c) => c.category === category) })).filter((group) => group.items.length);
  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)", overflow: "auto" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 40px 60px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>&larr; {t("Back")}</Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>{t("Region · Connectors")}</div>
            <div style={{ font: "400 30px/1.1 var(--font-display)", letterSpacing: "var(--tracking-screen-title)", textTransform: "uppercase" }}>{t("Connectors")}</div>
          </div>
          <div style={{ marginLeft: "auto" }}><Button size="sm" variant="secondary" onClick={load} disabled={loading}>{loading ? t("Refreshing...") : t("Refresh")}</Button></div>
        </div>
        <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 26, boxShadow: "var(--shadow-panel)", ...muted }}>
          {t("Connectors let external applications access your project. Sign in from each add-in with your DG account.")}
        </div>
        {loadErr && <p role="alert" style={errorStyle}>{t("Connectors unavailable.")} {describeError(loadErr, "")} <Button size="sm" variant="secondary" onClick={load}>{t("Retry")}</Button></p>}
        {loading && visibleConnectors.length === 0 && <div className="dg-annotation dg-annotation--muted">{t("Loading connectors...")}</div>}
        {!loading && !loadErr && visibleConnectors.length === 0 && <div className="dg-annotation dg-annotation--muted">{t("No connector data · data-service may be unreachable")}</div>}
        {grouped.map(({ category, items }) => <div key={category}>
          <div style={SECTION_EYEBROW}>{category}</div>
          {items.map((connector) => <ConnectorCard key={connector.id} connector={connector} expanded={expanded[connector.id]} onToggle={(id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }))} project={project} user={user} active={active} canAdminister={canAdminister} adminReady={adminReady} accessData={accessData} members={members} busy={!!busy[connector.id]} error={errors[connector.id]} onGrant={grantAccess} onRevoke={revokeAccess} onRequest={requestAccess} t={t} tp={tp} />)}
        </div>)}
      </div>
    </div>
  );
}
