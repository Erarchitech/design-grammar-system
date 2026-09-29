import React from "react";
import { Badge, Button, Input, Panel, Select, Tile } from "../components/index.js";
import { fetchProjects } from "../lib/graphApi.js";
import { apiFetch, dataServiceBase, ApiError } from "../lib/apiClient.js";

const ROLE_OPTIONS = [
  { value: "viewer", label: "Viewer" },
  { value: "editor", label: "Editor" },
  { value: "owner", label: "Owner" }
];

function projectUrl(project, suffix) {
  return `${dataServiceBase()}/projects/${encodeURIComponent(project)}${suffix}`;
}

const ERR_STYLE = { font: "400 13px/1.4 var(--font-sans)", color: "var(--color-signal)" };

// Projects are membership-scoped (phase 1205, D-02/D-05): the tile grid lists
// only the caller's projects with their role; opening one scopes every Graph /
// Model Viewer request to it (PROJ-01/02). Owners administer members here.
export default function ProjectsScreen({ active, onBack, project, onProject, user }) {
  const [projects, setProjects] = React.useState([]);
  const [loadErr, setLoadErr] = React.useState("");
  const [creating, setCreating] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [createErr, setCreateErr] = React.useState("");
  const [shots, setShots] = React.useState({});

  // Owner members panel state. The invite code lives only in this component
  // state (rendered once, never written to browser storage).
  const [members, setMembers] = React.useState([]);
  const [membersErr, setMembersErr] = React.useState("");
  const [inviteUser, setInviteUser] = React.useState("");
  const [inviteRole, setInviteRole] = React.useState("viewer");
  const [inviteErr, setInviteErr] = React.useState("");
  const [inviteNote, setInviteNote] = React.useState("");
  const [invite, setInvite] = React.useState(null);
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
    setLoadErr("");
    fetchProjects()
      .then(setProjects)
      .catch((err) => setLoadErr(err.message || "Projects unreachable"));
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
    setCreateErr("");
    try {
      await apiFetch(`${dataServiceBase()}/projects`, { method: "POST", body: { project: name } });
    } catch (err) {
      setCreateErr(
        err instanceof ApiError && err.status === 409
          ? "That project name is unavailable."
          : err.message || "Could not create the project."
      );
      return;
    }
    setCreating(false);
    setNewName("");
    open(name); // nodes appear under this scope on first rule ingest
  };

  const loadMembers = React.useCallback(() => {
    if (!project || !canAdminister) return;
    setMembersErr("");
    apiFetch(projectUrl(project, "/members"))
      .then((body) => setMembers(Array.isArray(body?.members) ? body.members : []))
      .catch((err) => setMembersErr(err.message || "Members unavailable."));
  }, [project, canAdminister]);

  // Switching project (or losing owner rights) discards the panel state,
  // including any invite code still on screen.
  React.useEffect(() => {
    setMembers([]);
    setInvite(null);
    setInviteNote("");
    setInviteErr("");
    setMembersErr("");
    if (active) loadMembers();
  }, [active, loadMembers]);

  const sendInvite = async () => {
    const username = inviteUser.trim();
    if (!username) return setInviteErr("Enter a username.");
    setInviteErr("");
    setInviteNote("");
    setInvite(null);
    try {
      const res = await apiFetch(`${dataServiceBase()}/auth/invites`, {
        method: "POST",
        body: { username, project, role: inviteRole }
      });
      if (res?.status === "invited") {
        setInvite({ code: res.inviteCode, expiresAt: res.expiresAt });
      } else if (res?.status === "member-added") {
        setInviteNote(`${username} was added to ${project} as ${inviteRole}.`);
      }
      setInviteUser("");
      loadMembers();
    } catch (err) {
      setInviteErr(err.message || "Could not send the invitation.");
    }
  };

  const removeMember = async (username) => {
    setMembersErr("");
    try {
      await apiFetch(projectUrl(project, `/members/${encodeURIComponent(username)}`), { method: "DELETE" });
      loadMembers();
    } catch (err) {
      // 409 LAST_OWNER and the rest arrive with the server's own message
      setMembersErr(err.message || "Could not remove the member.");
    }
  };

  const copyInvite = () => {
    if (invite?.code && navigator.clipboard) navigator.clipboard.writeText(invite.code).catch(() => {});
  };

  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--surface-canvas)", overflow: "auto" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 40px 60px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← Back
          </Button>
          <div style={{ font: "600 34px/1.1 var(--font-sans)", letterSpacing: "-1.2px" }}>Projects.</div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            {creating && (
              <>
                <Input
                  placeholder="Project name"
                  value={newName}
                  autoFocus
                  onChange={(e) => {
                    setNewName(e.target.value);
                    setCreateErr("");
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") createProject();
                    if (e.key === "Escape") setCreating(false);
                  }}
                  style={{ width: 220 }}
                />
                <Button size="sm" onClick={createProject}>
                  Create
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setCreating(false)}>
                  Cancel
                </Button>
              </>
            )}
            {!creating && (
              <Button size="sm" onClick={() => setCreating(true)}>
                New Project
              </Button>
            )}
          </div>
        </div>

        {createErr && <div style={ERR_STYLE}>{createErr}</div>}

        {loadErr && (
          <div style={ERR_STYLE}>
            Projects unavailable · {loadErr}{" "}
            <span onClick={load} style={{ cursor: "pointer", textDecoration: "underline" }}>
              Retry
            </span>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
          {projects.map((p) => (
            <Tile
              key={p.project}
              title={p.project}
              description={`${p.role || "member"} · ${p.nodes} node${p.nodes === 1 ? "" : "s"} in graph${p.project === project ? " · active" : ""}`}
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
            No projects yet · create one with New Project, or ask an owner for an invitation
          </div>
        )}

        {canAdminister && (
          <Panel title={`Members · ${project}`} style={{ userSelect: "text" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {membersErr && <div style={ERR_STYLE}>{membersErr}</div>}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {members.map((m) => (
                  <div key={m.username} style={{ display: "flex", alignItems: "center", gap: 10, font: "400 14px/1.4 var(--font-sans)" }}>
                    <span style={{ flex: 1 }}>{m.username}</span>
                    <Badge variant={m.role === "owner" ? "signal" : "soft"}>{m.role}</Badge>
                    <Button variant="secondary" size="sm" onClick={() => removeMember(m.username)}>
                      Remove
                    </Button>
                  </div>
                ))}
                {!membersErr && members.length === 0 && (
                  <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                    No members listed
                  </div>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <Input
                  placeholder="Username to invite"
                  value={inviteUser}
                  autoComplete="off"
                  onChange={(e) => {
                    setInviteUser(e.target.value);
                    setInviteErr("");
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") sendInvite();
                  }}
                  style={{ width: 240 }}
                />
                <Select options={ROLE_OPTIONS} value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} style={{ width: 130 }} />
                <Button size="sm" onClick={sendInvite}>
                  Invite
                </Button>
              </div>
              {inviteErr && <div style={ERR_STYLE}>{inviteErr}</div>}
              {inviteNote && <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>{inviteNote}</div>}
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
                      Copy
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => setInvite(null)}>
                      Dismiss
                    </Button>
                  </div>
                  <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                    Share this code with the invitee; it is shown once and expires in 72 hours.
                  </div>
                </div>
              )}
            </div>
          </Panel>
        )}

        <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
          {projects.length} project{projects.length === 1 ? "" : "s"}
        </div>
      </div>
    </div>
  );
}
