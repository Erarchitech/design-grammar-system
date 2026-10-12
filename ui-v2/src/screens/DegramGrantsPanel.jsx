import React from "react";
import { Button } from "../components/index.js";
import { apiFetch, dataServiceBase, ApiError } from "../lib/apiClient.js";
import { issueGrant, listMyGrants, listProjectGrants, requestGrant, revokeGrant } from "../lib/connectorsApi.js";
import { describeError, formatDate } from "../i18n/index.js";
import { useT } from "../i18n/LanguageProvider.jsx";

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

// Dates follow the resolved language; formatDate answers a dash for an empty or invalid value.
function date(iso) {
  return formatDate(iso, { dateStyle: "medium" });
}

export default function DegramGrantsPanel({ project, user, trimmed = false, active = true }) {
  const activeRole = user?.memberships?.find((m) => m.project === project)?.role;
  const canAdminister = activeRole === "owner" || !!user?.isAdmin;
  const administer = !trimmed && canAdminister;
  const { t, tc } = useT();
  const [grants, setGrants] = React.useState([]);
  const [requests, setRequests] = React.useState([]);
  const [members, setMembers] = React.useState([]);
  const [username, setUsername] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [purpose, setPurpose] = React.useState("");
  const [note, setNote] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null); // { err, kind }: described at render so the text follows the language
  const [requestState, setRequestState] = React.useState("");
  const scope = React.useRef(0);

  const refresh = React.useCallback(async () => {
    if (!active || !project || !user) return;
    const generation = scope.current;
    setLoading(true);
    setError(null);
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
        setError({ err, kind: "load" });
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
    setError(null);
    refresh();
    return () => { scope.current += 1; };
  }, [refresh]);

  const grant = async (target, name, reason) => {
    if (!target || !name.trim() || !reason.trim() || busy) return;
    const generation = scope.current;
    setBusy(true);
    setError(null);
    try {
      await issueGrant(project, { username: target, label: name.trim(), purpose: reason.trim() });
      if (generation !== scope.current) return;
      setLabel("");
      setPurpose("");
      await refresh();
    } catch (err) {
      if (generation === scope.current) setError({ err, kind: "grant" });
    } finally {
      if (generation === scope.current) setBusy(false);
    }
  };

  const revoke = async (grantId) => {
    if (busy || !globalThis.confirm(t("Revoke this DeGram grant?"))) return;
    const generation = scope.current;
    setBusy(true);
    setError(null);
    try {
      await revokeGrant(project, grantId);
      if (generation === scope.current) await refresh();
    } catch (err) {
      if (generation === scope.current) setError({ err, kind: "revoke" });
    } finally {
      if (generation === scope.current) setBusy(false);
    }
  };

  const request = async (event) => {
    event.preventDefault();
    if (busy) return;
    const generation = scope.current;
    setBusy(true);
    setError(null);
    try {
      await requestGrant(project, note.trim());
      if (generation !== scope.current) return;
      setRequestState("pending");
      await refresh();
    } catch (err) {
      if (generation === scope.current) {
        if (err instanceof ApiError && err.status === 409 && err.code === "GRANT_EXISTS") setRequestState("exists");
        else setError({ err, kind: "request" });
      }
    } finally {
      if (generation === scope.current) setBusy(false);
    }
  };

  if (!project) return <p style={muted}>{t("Select a project to manage DeGram access.")}</p>;
  if (!user) return <p style={muted}>{t("Sign in to view DeGram access.")}</p>;

  let errorText = "";
  if (error) {
    const failure = error.err || new Error("");
    if (error.kind === "load") errorText = describeError(failure, t("DeGram access unavailable."));
    else if (error.kind === "grant") errorText = describeError(failure, t("Could not grant access."));
    else if (error.kind === "revoke") errorText = describeError(failure, t("Could not revoke access."));
    else errorText = describeError(failure, t("Could not request access."));
  }

  const hasRequest = requestState === "pending" || requests.some((r) => !r.status || r.status === "pending");
  const visible = grants.filter((g) => g.active);

  // Built outside the JSX so the request state reads as plain branches.
  let requestForm;
  if (requestState === "exists") requestForm = <p role="status">{t("Access already granted")}</p>;
  else if (hasRequest) requestForm = <p role="status">{t("Request sent")}</p>;
  else {
    requestForm = (
      <form onSubmit={request} style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <input aria-label={t("Note (optional)")} placeholder={t("Note (optional)")} maxLength={200} value={note} onChange={(event) => setNote(event.target.value)} style={fieldStyle} />
        <Button size="sm" type="submit" disabled={busy || loading}>{t("Request access")}</Button>
      </form>
    );
  }

  return (
    <section data-testid="degram-grants" style={{ padding: "16px 18px", display: "grid", gap: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <strong style={{ font: "500 15px/1.3 var(--font-sans)" }}>{t("DeGram access")}</strong>
        <Button size="sm" variant="secondary" onClick={refresh} disabled={loading || busy} style={{ marginLeft: "auto" }}>
          {t("Refresh")}
        </Button>
      </div>
      {error && <p role="alert" style={errorStyle}>{errorText}</p>}
      {loading && <p style={muted}>{t("Loading...")}</p>}
      {administer ? (
        <>
          <form onSubmit={(event) => { event.preventDefault(); grant(username, label, purpose); }} style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <select aria-label={t("Member")} value={username} onChange={(event) => setUsername(event.target.value)} required style={fieldStyle}>
              <option value="">{t("Select member")}</option>
              {members.map((member) => <option key={member.username} value={member.username}>{member.username}</option>)}
            </select>
            <input aria-label={tc("grant", "Name")} placeholder={tc("grant", "Name")} maxLength={120} required value={label} onChange={(event) => setLabel(event.target.value)} style={fieldStyle} />
            <input aria-label={t("Purpose")} placeholder={t("Purpose")} maxLength={200} required value={purpose} onChange={(event) => setPurpose(event.target.value)} style={fieldStyle} />
            <Button size="sm" type="submit" disabled={busy || loading}>{t("Grant access")}</Button>
          </form>
          <div>
            <strong>{t("Issued grants")}</strong>
            {visible.length === 0 && <p style={muted}>{t("No active grants.")}</p>}
            {visible.map((g) => (
              <div key={g.grant_id} style={{ borderBottom: "1px solid var(--color-hairline)", padding: "8px 0", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <span>{g.username} · {g.label} · {g.purpose}</span>
                <span style={muted}>{t("Created {date}", { date: date(g.created_at) })} · {t("Last used {date}", { date: date(g.last_used) })}</span>
                <Button size="sm" variant="destructive" disabled={busy} onClick={() => revoke(g.grant_id)}>{t("Revoke")}</Button>
              </div>
            ))}
          </div>
          {requests.length > 0 && <div>
            <strong>{t("Pending requests")}</strong>
            {requests.map((r) => <div key={r.request_id} style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", padding: "8px 0" }}>
              <span>{r.username} · {r.note || "—"} · {date(r.created_at)}</span>
              <Button size="sm" disabled={busy} onClick={() => grant(r.username, (r.note?.trim() || "DeGram access").slice(0, 120), r.note?.trim() || "Requested access")}>{t("Grant")}</Button>
            </div>)}
          </div>}
        </>
      ) : (
        <>
          <div><strong>{t("My access")}</strong>
            {visible.length === 0 && <p style={muted}>{t("No access granted yet")}</p>}
            {visible.map((g) => <p key={`${g.project}-${g.created_at}`} style={muted}>{g.label} · {g.purpose} · {date(g.created_at)} · {t("Last used {date}", { date: date(g.last_used) })}</p>)}
          </div>
          {requestForm}
        </>
      )}
    </section>
  );
}
