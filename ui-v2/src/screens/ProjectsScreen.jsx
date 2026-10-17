import React from "react";
import { Button, Checkbox, Input, Panel, Select, Tile } from "../components/index.js";
import { fetchProjects } from "../lib/graphApi.js";
import { apiFetch, dataServiceBase, ApiError } from "../lib/apiClient.js";
import { changeMemberRole } from "../lib/memberApi.js";
import { isSoleOwner, needsSelfDemotionConfirm } from "../lib/memberRoles.js";
import { getDegramPolicy, policyPatch, setDegramPolicy, shouldShowProjectSettings } from "../lib/projectSettingsApi.js";
import { describeError } from "../i18n/index.js";
import { ROLE_VALUES, roleLabel } from "../i18n/enums.js";
import { useT } from "../i18n/LanguageProvider.jsx";
import MappingPanel from "./MappingPanel.jsx";

function roleOptions() {
  return ROLE_VALUES.map((value) => ({ value, label: roleLabel(value) }));
}

function projectUrl(project, suffix) {
  return `${dataServiceBase()}/projects/${encodeURIComponent(project)}${suffix}`;
}

const ERR_STYLE = { font: "400 12px/1.33 var(--font-sans)", color: "var(--color-signal)" };

// Screen-reader-only text (live regions and aria-describedby targets).
const VISUALLY_HIDDEN = {
  position: "absolute",
  width: 1,
  height: 1,
  overflow: "hidden",
  clip: "rect(0 0 0 0)",
  whiteSpace: "nowrap"
};

// Role Select of one member (D-16). Dumb: value, disabled state and the sole-owner hint come from MemberRow.
function MemberRoleSelect({ username, value, disabled, soleOwner, soleOwnerText, noteId, onChange }) {
  const { t } = useT();
  return (
    <>
      <Select
        options={roleOptions()}
        value={value}
        disabled={disabled}
        onChange={onChange}
        aria-label={t("Role of {username}", { username })}
        aria-describedby={soleOwner ? noteId : undefined}
        title={soleOwner ? soleOwnerText : undefined}
        style={{ minWidth: 130, width: "auto", opacity: disabled ? 0.45 : 1, cursor: disabled ? "default" : "pointer" }}
      />
      {soleOwner && (
        <span id={noteId} style={VISUALLY_HIDDEN}>
          {soleOwnerText}
        </span>
      )}
    </>
  );
}

// One Members row: optimistic role change with rollback and a mapped inline error (D-16, D-09). A non-admin owner
// lowering their own role confirms first because the panel disappears after the change. `scopeRef` is the screen's
// panelScope race guard: a reply that lands after the project switched is dropped.
function MemberRow({ member, members, user, project, scopeRef, onRoleChanged, onRemove }) {
  const { t } = useT();
  const [pending, setPending] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [confirm, setConfirm] = React.useState(null);
  const [saved, setSaved] = React.useState(false);
  const noteId = React.useId();
  const soleOwner = isSoleOwner(members, member.username);
  const busy = pending !== null;

  const commit = async (next) => {
    const scope = scopeRef.current;
    setConfirm(null);
    setError(null);
    setSaved(false);
    setPending(next);
    try {
      await changeMemberRole(project, member.username, next);
      if (scope !== scopeRef.current) return;
      setPending(null);
      setSaved(true);
      onRoleChanged(member.username, next);
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setPending(null); // roll back to the server's value
      setError(err);
    }
  };

  const onChange = (event) => {
    const next = event.target.value;
    if (busy || next === member.role) return;
    setError(null);
    setSaved(false);
    if (needsSelfDemotionConfirm({ user, username: member.username, from: member.role, to: next })) {
      setConfirm(next);
      return;
    }
    commit(next);
  };

  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: 4 }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && confirm) setConfirm(null);
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, font: "400 14px/1.43 var(--font-sans)" }}>
        <span style={{ flex: 1, minWidth: 0 }}>{member.username}</span>
        <MemberRoleSelect
          username={member.username}
          value={pending ?? member.role}
          disabled={busy || soleOwner}
          soleOwner={soleOwner}
          soleOwnerText={t("A project must keep at least one owner. Promote another member first.")}
          noteId={noteId}
          onChange={onChange}
        />
        <Button variant="secondary" size="sm" onClick={() => onRemove(member.username)}>
          {t("Remove member")}
        </Button>
      </div>
      {confirm && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", font: "400 14px/1.43 var(--font-sans)" }}>
          <span>{t("You will no longer be able to manage members of this project.")}</span>
          <Button size="sm" onClick={() => commit(confirm)}>
            {t("Change role")}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setConfirm(null)}>
            {t("Keep my role")}
          </Button>
        </div>
      )}
      {error && <div style={ERR_STYLE}>{describeError(error, t("Could not change the role. Try again."))}</div>}
      <span aria-live="polite" style={VISUALLY_HIDDEN}>
        {saved ? t("Role updated for {username}", { username: member.username }) : ""}
      </span>
    </div>
  );
}

// One export-policy toggle (D-17): Checkbox row with a 12px helper below (4px gap). The primitive has no input element,
// so the wrapper carries role="checkbox", focus and the Space/Enter keys. While `confirm` is set (enabling
// whole-definition export) the helper is replaced by the inline confirm, and Escape picks the safe answer.
function PolicyRow({ label, helper, checked, busy, onToggle, error, confirm }) {
  const labelId = React.useId();
  const helperId = React.useId();
  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: 4 }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && confirm) confirm.onKeep();
      }}
    >
      <div
        role="checkbox"
        tabIndex={0}
        aria-checked={checked}
        aria-disabled={busy}
        aria-labelledby={labelId}
        aria-describedby={helperId}
        onKeyDown={(event) => {
          if (event.key !== " " && event.key !== "Enter") return;
          event.preventDefault();
          if (!busy) onToggle(!checked);
        }}
        style={{ alignSelf: "flex-start", opacity: busy ? 0.45 : 1, pointerEvents: busy ? "none" : undefined }}
      >
        <Checkbox
          checked={checked}
          onChange={(next) => {
            if (!busy) onToggle(next);
          }}
          label={
            <span id={labelId} style={{ font: "400 14px/1.43 var(--font-sans)" }}>
              {label}
            </span>
          }
        />
      </div>
      {confirm ? (
        <div id={helperId} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ font: "400 14px/1.43 var(--font-sans)" }}>{confirm.text}</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button size="sm" onClick={confirm.onAllow}>
              {confirm.allowLabel}
            </Button>
            <Button variant="outline" size="sm" onClick={confirm.onKeep}>
              {confirm.keepLabel}
            </Button>
          </div>
        </div>
      ) : (
        <div id={helperId} style={{ font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)" }}>
          {helper}
        </div>
      )}
      {error && <div style={ERR_STYLE}>{error}</div>}
    </div>
  );
}

function readPolicy(body, fallback) {
  const ok = body && typeof body.providerExportAllowed === "boolean" && typeof body.wholeDefinitionAllowed === "boolean";
  if (ok) return { providerExportAllowed: body.providerExportAllowed, wholeDefinitionAllowed: body.wholeDefinitionAllowed };
  return fallback;
}

// DG-admin-only export policy for one project (D-02, D-17). Only the changed flag is sent. Enabling whole-definition
// export needs an inline confirm; the checkbox stays off until it is confirmed. A 403 ADMIN_REQUIRED reloads the panel.
function ProjectSettingsPanel({ project, active }) {
  const { t, tc } = useT();
  const [policy, setPolicy] = React.useState(null);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [failure, setFailure] = React.useState(null);
  const [confirming, setConfirming] = React.useState(false);
  const [saved, setSaved] = React.useState(false);
  const scopeRef = React.useRef(0);

  const load = React.useCallback(() => {
    const scope = scopeRef.current;
    setLoadFailed(false);
    getDegramPolicy(project)
      .then((body) => {
        const read = readPolicy(body, null);
        if (scope !== scopeRef.current) return;
        if (read) setPolicy(read);
        else setLoadFailed(true); // fail closed: never guess a flag
      })
      .catch(() => {
        if (scope === scopeRef.current) setLoadFailed(true);
      });
  }, [project]);

  // Switching project (or leaving the screen) discards the panel state; late replies of the old scope are dropped.
  React.useEffect(() => {
    setPolicy(null);
    setLoadFailed(false);
    setBusy(false);
    setFailure(null);
    setConfirming(false);
    setSaved(false);
    if (active) load();
    return () => {
      scopeRef.current += 1;
    };
  }, [active, load]);

  const apply = async (flag, value) => {
    if (!policy || busy) return;
    const next = { ...policy, [flag]: value };
    const patch = policyPatch(policy, next);
    if (Object.keys(patch).length === 0) return;
    const scope = scopeRef.current;
    setFailure(null);
    setSaved(false);
    setConfirming(false);
    setBusy(true);
    setPolicy(next);
    try {
      const body = await setDegramPolicy(project, patch);
      if (scope !== scopeRef.current) return;
      setPolicy(readPolicy(body, next));
      setBusy(false);
      setSaved(true);
    } catch (err) {
      if (scope !== scopeRef.current) return;
      setBusy(false);
      setFailure({ flag, err });
      if (err?.code === "ADMIN_REQUIRED") {
        setPolicy(null); // back to server truth: reload the panel
        load();
      } else {
        setPolicy(policy); // roll back
      }
    }
  };

  const onWholeToggle = (value) => {
    setFailure(null);
    setSaved(false);
    if (value) setConfirming(true); // the checkbox stays off until confirmed
    else {
      setConfirming(false);
      apply("wholeDefinitionAllowed", false);
    }
  };

  const failureText = failure ? describeError(failure.err, t("Could not save the setting. Try again.")) : "";
  const rowError = (flag) => (failure && failure.flag === flag ? failureText : "");

  let body;
  if (policy) {
    body = (
      <>
        <PolicyRow
          label={t("Allow provider export")}
          helper={t("DeGram may send this project's data to the LLM provider. On by default.")}
          checked={policy.providerExportAllowed}
          busy={busy}
          onToggle={(value) => apply("providerExportAllowed", value)}
          error={rowError("providerExportAllowed")}
        />
        <PolicyRow
          label={t("Allow whole-definition export")}
          helper={t("Lets DeGram request the complete Grasshopper definition. Each request still needs its own consent. Off by default.")}
          checked={policy.wholeDefinitionAllowed}
          busy={busy}
          onToggle={onWholeToggle}
          error={rowError("wholeDefinitionAllowed")}
          confirm={
            confirming
              ? {
                  text: t("Allow whole-definition export for {project}? DeGram will be able to request the entire definition, each time with your consent.", { project }),
                  allowLabel: tc("confirm", "Allow whole-definition export"),
                  keepLabel: t("Keep export off"),
                  onAllow: () => apply("wholeDefinitionAllowed", true),
                  onKeep: () => setConfirming(false)
                }
              : null
          }
        />
      </>
    );
  } else if (loadFailed) {
    body = (
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span style={ERR_STYLE}>{t("Could not load project settings.")}</span>
        <Button variant="outline" size="sm" onClick={load}>
          {t("Retry loading settings")}
        </Button>
      </div>
    );
  } else {
    body = <div style={{ font: "400 14px/1.43 var(--font-sans)", color: "var(--text-muted)" }}>{t("Loading settings…")}</div>;
  }

  return (
    <Panel title={t("Project settings · {project}", { project })} style={{ marginTop: 24, userSelect: "text" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)" }}>{t("Visible to DG admins only.")}</div>
        {!policy && failureText && <div style={ERR_STYLE}>{failureText}</div>}
        {body}
        <span aria-live="polite" style={VISUALLY_HIDDEN}>
          {saved ? t("Project settings saved") : ""}
        </span>
      </div>
    </Panel>
  );
}

// Projects are membership-scoped (phase 1205, D-02/D-05): the tile grid lists
// only the caller's projects with their role; opening one scopes every Graph /
// Model Viewer request to it (PROJ-01/02). Owners administer members here.
export default function ProjectsScreen({ active, onBack, project, onProject, user }) {
  const { t, tp } = useT();
  const [projects, setProjects] = React.useState([]);
  const [loadErr, setLoadErr] = React.useState(null);
  const [creating, setCreating] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [createErr, setCreateErr] = React.useState(null);
  const [shots, setShots] = React.useState({});

  // Owner members panel state. The invite code lives only in this component
  // state (rendered once, never written to browser storage).
  const [members, setMembers] = React.useState([]);
  const [membersErr, setMembersErr] = React.useState(null);
  const [inviteUser, setInviteUser] = React.useState("");
  const [inviteRole, setInviteRole] = React.useState("viewer");
  const [inviteErr, setInviteErr] = React.useState(null);
  const [inviteNote, setInviteNote] = React.useState(null);
  const [invite, setInvite] = React.useState(null);
  const panelScope = React.useRef(0);
  const activeRole = projects.find((p) => p.project === project)?.role;
  const canAdminister = !!project && (activeRole === "owner" || !!user?.isAdmin);

  // Viewport thumbnails captured by the Model Viewer (per project)
  React.useEffect(() => {
    if (!active) return;
    try {
      setShots(JSON.parse(localStorage.getItem("dgv2_project_shots") || "{}"));
    } catch {
      setShots({});
    }
  }, [active]);

  const load = React.useCallback(() => {
    setLoadErr(null);
    fetchProjects()
      .then(setProjects)
      .catch(setLoadErr);
  }, []);

  React.useEffect(() => {
    if (active) load();
  }, [active, load]);

  const open = (name) => {
    onProject(name);
    onBack(); // mockup behaviour: picking a project returns to the landing
  };

  const createProject = async () => {
    const name = newName.trim();
    if (!name) return;
    setCreateErr(null);
    try {
      await apiFetch(`${dataServiceBase()}/projects`, { method: "POST", body: { project: name } });
    } catch (err) {
      setCreateErr(err instanceof ApiError && err.status === 409 ? { unavailable: true } : err);
      return;
    }
    setCreating(false);
    setNewName("");
    open(name); // nodes appear under this scope on first rule ingest
  };

  const loadMembers = React.useCallback(() => {
    if (!project || !canAdminister) return;
    const scope = panelScope.current;
    setMembersErr(null);
    apiFetch(projectUrl(project, "/members"))
      .then((body) => {
        if (scope === panelScope.current) setMembers(Array.isArray(body?.members) ? body.members : []);
      })
      .catch((err) => {
        if (scope === panelScope.current) setMembersErr({ err, kind: "load" });
      });
  }, [project, canAdminister]);

  // Switching project (or losing owner rights) discards the panel state,
  // including any invite code still on screen.
  React.useEffect(() => {
    setMembers([]);
    setInvite(null);
    setInviteNote(null);
    setInviteErr(null);
    setMembersErr(null);
    if (active) loadMembers();
    // Late reads from a previous project/owner scope must not refill this panel.
    return () => { panelScope.current += 1; };
  }, [active, loadMembers]);

  const sendInvite = async () => {
    const username = inviteUser.trim();
    if (!username) return setInviteErr({ missing: true });
    setInviteErr(null);
    setInviteNote(null);
    setInvite(null);
    const scope = panelScope.current;
    try {
      const res = await apiFetch(`${dataServiceBase()}/auth/invites`, {
        method: "POST",
        body: { username, project, role: inviteRole }
      });
      if (scope !== panelScope.current) return;
      if (res?.status === "invited") {
        setInvite({ code: res.inviteCode, expiresAt: res.expiresAt });
      } else if (res?.status === "member-added") {
        setInviteNote({ username, project, role: inviteRole });
      }
      setInviteUser("");
      loadMembers();
    } catch (err) {
      if (scope === panelScope.current) setInviteErr(err);
    }
  };

  const removeMember = async (username) => {
    const scope = panelScope.current;
    setMembersErr(null);
    try {
      await apiFetch(projectUrl(project, `/members/${encodeURIComponent(username)}`), { method: "DELETE" });
      if (scope === panelScope.current) loadMembers();
    } catch (err) {
      // 409 LAST_OWNER and the rest are mapped by code (describeError)
      if (scope === panelScope.current) setMembersErr({ err, kind: "remove" });
    }
  };

  // A role change succeeded: show it at once, then take the server's list (guarded by panelScope inside loadMembers).
  const onRoleChanged = (username, role) => {
    setMembers((list) => list.map((m) => (m.username === username ? { ...m, role } : m)));
    loadMembers();
  };

  const copyInvite = () => {
    if (invite?.code && navigator.clipboard) navigator.clipboard.writeText(invite.code).catch(() => {});
  };

  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)", overflow: "auto" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 40px 60px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← {t("Back")}
          </Button>
          <div style={{ font: "400 30px/1.1 var(--font-display)", letterSpacing: "var(--tracking-screen-title)", textTransform: "uppercase" }}>{t("Projects")}</div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            {creating && (
              <>
                <Input
                  placeholder={t("Project name")}
                  value={newName}
                  autoFocus
                  onChange={(e) => {
                    setNewName(e.target.value);
                    setCreateErr(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") createProject();
                    if (e.key === "Escape") setCreating(false);
                  }}
                  style={{ width: 220 }}
                />
                <Button size="sm" onClick={createProject}>
                  {t("Create")}
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setCreating(false)}>
                  {t("Cancel")}
                </Button>
              </>
            )}
            {!creating && (
              <Button size="sm" onClick={() => setCreating(true)}>
                {t("New Project")}
              </Button>
            )}
          </div>
        </div>

        {createErr && (
          <div style={ERR_STYLE}>
            {createErr.unavailable ? t("That project name is unavailable.") : describeError(createErr, t("Could not create the project."))}
          </div>
        )}

        {loadErr && (
          <div style={ERR_STYLE}>
            {t("Projects unavailable · {reason}", { reason: describeError(loadErr, t("Projects unreachable")) })}{" "}
            <span onClick={load} style={{ cursor: "pointer", textDecoration: "underline" }}>
              {t("Retry")}
            </span>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
          {projects.map((p) => (
            <Tile
              key={p.project}
              title={p.project}
              description={`${p.role ? roleLabel(p.role) : t("member")} · ${tp("{n} node in graph", p.nodes)}${p.project === project ? ` · ${t("active")}` : ""}`}
              thumbnail={
                shots[p.project] ? (
                  <img src={shots[p.project]} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
                ) : undefined
              }
              onClick={() => open(p.project)}
            />
          ))}
        </div>
        {!loadErr && projects.length === 0 && (
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
            {t("No projects yet · create one with New Project, or ask an owner for an invitation")}
          </div>
        )}

        {canAdminister && (
          <div>
            <Panel title={t("Members · {project}", { project })} style={{ userSelect: "text" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {membersErr && (
                <div style={ERR_STYLE}>
                  {describeError(membersErr.err, membersErr.kind === "remove" ? t("Could not remove the member.") : t("Members unavailable."))}
                </div>
              )}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {members.map((m) => (
                    <MemberRow
                      key={m.username}
                      member={m}
                      members={members}
                      user={user}
                      project={project}
                      scopeRef={panelScope}
                      onRoleChanged={onRoleChanged}
                      onRemove={removeMember}
                    />
                  ))}
                  {!membersErr && members.length === 0 && (
                    <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                      {t("No members listed")}
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <Input
                    placeholder={t("Username to invite")}
                    value={inviteUser}
                    autoComplete="off"
                    onChange={(e) => {
                      setInviteUser(e.target.value);
                      setInviteErr(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") sendInvite();
                    }}
                    style={{ width: 240 }}
                  />
                  <Select options={roleOptions()} value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} style={{ width: 130 }} />
                  <Button size="sm" onClick={sendInvite}>
                    {t("Send invitation")}
                  </Button>
                </div>
                {inviteErr && (
                <div style={ERR_STYLE}>
                  {inviteErr.missing ? t("Enter a username.") : describeError(inviteErr, t("Could not send the invitation."))}
                </div>
              )}
                {inviteNote && (
                <div style={{ font: "400 12px/1.33 var(--font-sans)", color: "var(--text-muted)" }}>
                  {t("{username} was added to {project} as {role}.", {
                    username: inviteNote.username,
                    project: inviteNote.project,
                    role: roleLabel(inviteNote.role)
                  })}
                </div>
              )}
                {invite && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Input
                        mono
                        readOnly
                        value={invite.code}
                        onFocus={(e) => e.target.select()}
                        style={{ width: 360, userSelect: "text" }}
                      />
                      <Button variant="secondary" size="sm" onClick={copyInvite}>
                        {t("Copy invite code")}
                      </Button>
                      <Button variant="secondary" size="sm" onClick={() => setInvite(null)}>
                        {t("Hide invite code")}
                      </Button>
                    </div>
                    <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                      {t("Share this code with the invitee; it is shown once and expires in 72 hours.")}
                    </div>
                  </div>
                )}
              </div>
            </Panel>
            {shouldShowProjectSettings(user, project) && (
              <ProjectSettingsPanel project={project} active={active} />
            )}
            {project && <MappingPanel key={project} project={project} active={active} />}
          </div>
        )}

        <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
          {tp("{n} project", projects.length)}
        </div>
      </div>
    </div>
  );
}
