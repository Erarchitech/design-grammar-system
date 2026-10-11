import React from "react";
import { Button } from "../components/index.js";
import { apiFetch, dataServiceBase, ApiError } from "../lib/apiClient.js";
import { issueGrant, listMyGrants, listProjectGrants, requestGrant, revokeGrant } from "../lib/connectorsApi.js";

const fieldStyle = {
  minHeight: 32,
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-inputs)",
  padding: "4px 10px",
  background: "var(--surface-input)",
  color: "var(--color-ink)",
  font: "400 13px/1.3 var(--font-sans)"
};
const muted = { color: "var(--text-muted)", font: "400 12px/1.4 var(--font-sans)" };
const errorStyle = { color: "var(--status-fail)", font: "400 12px/1.4 var(--font-sans)" };

function date(iso) {
  return iso ? new Date(iso).toLocaleDateString() : "—";
}

export default function DegramGrantsPanel({ project, user, trimmed = false, active = true }) {
  const activeRole = user?.memberships?.find((m) => m.project === project)?.role;
  const canAdminister = activeRole === "owner" || !!user?.isAdmin;
  const administer = !trimmed && canAdminister;
  const ru = trimmed && new URLSearchParams(globalThis.location?.search || "").get("lang") === "ru";
  const words = ru ? {
    title: "Доступ DeGram", request: "Запросить новый токен", pending: "Запрос отправлен",
    exists: "Доступ уже выдан", note: "Примечание (необязательно)", grants: "Мой доступ",
    none: "Доступ пока не выдан", refresh: "Обновить"
  } : {
    title: "DeGram access", request: "Request a new token", pending: "Request sent",
    exists: "Access already granted", note: "Note (optional)", grants: "My access",
    none: "No access granted yet", refresh: "Refresh"
  };
  const [grants, setGrants] = React.useState([]);
  const [requests, setRequests] = React.useState([]);
  const [members, setMembers] = React.useState([]);
  const [username, setUsername] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [purpose, setPurpose] = React.useState("");
  const [note, setNote] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [requestState, setRequestState] = React.useState("");
  const scope = React.useRef(0);

  const refresh = React.useCallback(async () => {
    if (!active || !project || !user) return;
    const generation = scope.current;
    setLoading(true);
    setError("");
    try {
      if (administer) {
        const [records, people] = await Promise.all([
          listProjectGrants(project),
          apiFetch(`${dataServiceBase()}/projects/${encodeURIComponent(project)}/members`)
        ]);
        if (generation !== scope.current) return;
        setGrants(records.grants || []);
        setRequests(records.requests || []);
        setMembers(people.members || []);
      } else {
        const mine = await listMyGrants();
        if (generation !== scope.current) return;
        setGrants((mine.grants || []).filter((g) => g.project === project));
        setRequests((mine.requests || []).filter((r) => r.project === project));
      }
    } catch (err) {
      if (generation === scope.current) {
        setGrants([]);
        setRequests([]);
        setMembers([]);
        setError(err.message || "DeGram access unavailable.");
      }
    } finally {
      if (generation === scope.current) setLoading(false);
    }
  }, [active, administer, project, user]);

  React.useEffect(() => {
    scope.current += 1;
    setGrants([]);
    setRequests([]);
    setMembers([]);
    setUsername("");
    setLabel("");
    setPurpose("");
    setNote("");
    setRequestState("");
    setError("");
    refresh();
    return () => { scope.current += 1; };
  }, [refresh]);

  const grant = async (target, name, reason) => {
    if (!target || !name.trim() || !reason.trim() || busy) return;
    const generation = scope.current;
    setBusy(true);
    setError("");
    try {
      await issueGrant(project, { username: target, label: name.trim(), purpose: reason.trim() });
      if (generation !== scope.current) return;
      setLabel("");
      setPurpose("");
      await refresh();
    } catch (err) {
      if (generation === scope.current) setError(err.message || "Could not grant access.");
    } finally {
      if (generation === scope.current) setBusy(false);
    }
  };

  const revoke = async (grantId) => {
    if (busy || !globalThis.confirm("Revoke this DeGram grant?")) return;
    const generation = scope.current;
    setBusy(true);
    setError("");
    try {
      await revokeGrant(project, grantId);
      if (generation === scope.current) await refresh();
    } catch (err) {
      if (generation === scope.current) setError(err.message || "Could not revoke access.");
    } finally {
      if (generation === scope.current) setBusy(false);
    }
  };

  const request = async (event) => {
    event.preventDefault();
    if (busy) return;
    const generation = scope.current;
    setBusy(true);
    setError("");
    try {
      await requestGrant(project, note.trim());
      if (generation !== scope.current) return;
      setRequestState("pending");
      await refresh();
    } catch (err) {
      if (generation === scope.current) {
        if (err instanceof ApiError && err.status === 409 && err.code === "GRANT_EXISTS") setRequestState("exists");
        else setError(err.message || "Could not request access.");
      }
    } finally {
      if (generation === scope.current) setBusy(false);
    }
  };

  if (!project) return <p style={muted}>Select a project to manage DeGram access.</p>;
  if (!user) return <p style={muted}>Sign in to view DeGram access.</p>;

  const hasRequest = requestState === "pending" || requests.some((r) => !r.status || r.status === "pending");
  const visible = grants.filter((g) => g.active);

  return (
    <section data-testid="degram-grants" style={{ padding: "16px 18px", display: "grid", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <strong style={{ font: "500 15px/1.3 var(--font-sans)" }}>{words.title}</strong>
        <Button size="sm" variant="secondary" onClick={refresh} disabled={loading || busy} style={{ marginLeft: "auto" }}>
          {words.refresh}
        </Button>
      </div>
      {error && <p role="alert" style={errorStyle}>{error}</p>}
      {loading && <p style={muted}>Loading...</p>}
      {administer ? (
        <>
          <form onSubmit={(event) => { event.preventDefault(); grant(username, label, purpose); }} style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <select aria-label="Member" value={username} onChange={(event) => setUsername(event.target.value)} required style={fieldStyle}>
              <option value="">Select member</option>
              {members.map((member) => <option key={member.username} value={member.username}>{member.username}</option>)}
            </select>
            <input aria-label="Name" placeholder="Name" maxLength={120} required value={label} onChange={(event) => setLabel(event.target.value)} style={fieldStyle} />
            <input aria-label="Purpose" placeholder="Purpose" maxLength={200} required value={purpose} onChange={(event) => setPurpose(event.target.value)} style={fieldStyle} />
            <Button size="sm" type="submit" disabled={busy || loading}>Grant access</Button>
          </form>
          <div>
            <strong>Issued grants</strong>
            {visible.length === 0 && <p style={muted}>No active grants.</p>}
            {visible.map((g) => (
              <div key={g.grant_id} style={{ borderBottom: "1px solid var(--color-hairline)", padding: "8px 0", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <span>{g.username} · {g.label} · {g.purpose}</span>
                <span style={muted}>Created {date(g.created_at)} · Last used {date(g.last_used)}</span>
                <Button size="sm" variant="destructive" disabled={busy} onClick={() => revoke(g.grant_id)}>Revoke</Button>
              </div>
            ))}
          </div>
          {requests.length > 0 && <div>
            <strong>Pending requests</strong>
            {requests.map((r) => <div key={r.request_id} style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", padding: "8px 0" }}>
              <span>{r.username} · {r.note || "—"} · {date(r.created_at)}</span>
              <Button size="sm" disabled={busy} onClick={() => grant(r.username, (r.note?.trim() || "DeGram access").slice(0, 120), r.note?.trim() || "Requested access")}>Grant</Button>
            </div>)}
          </div>}
        </>
      ) : (
        <>
          <div><strong>{words.grants}</strong>
            {visible.length === 0 && <p style={muted}>{words.none}</p>}
            {visible.map((g) => <p key={`${g.project}-${g.created_at}`} style={muted}>{g.label} · {g.purpose} · {date(g.created_at)} · Last used {date(g.last_used)}</p>)}
          </div>
          {requestState === "exists" ? <p role="status">{words.exists}</p> :
            hasRequest ? <p role="status">{words.pending}</p> :
            <form onSubmit={request} style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <input aria-label={words.note} placeholder={words.note} maxLength={200} value={note} onChange={(event) => setNote(event.target.value)} style={fieldStyle} />
              <Button size="sm" type="submit" disabled={busy || loading}>{words.request}</Button>
            </form>}
        </>
      )}
    </section>
  );
}
