import React from "react";
import { Button, Input, Tile } from "../components/index.js";
import { fetchProjects, getConfig } from "../lib/graphApi.js";

// Projects are first-class: the tile grid lists real projects present in
// Neo4j; opening one scopes every Graph/Model Viewer query to it (PROJ-01/02).
export default function ProjectsScreen({ active, onBack, project, onProject }) {
  const [projects, setProjects] = React.useState([]);
  const [loadErr, setLoadErr] = React.useState("");
  const [creating, setCreating] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [shots, setShots] = React.useState({});
  const cfg = React.useMemo(() => getConfig(), []);

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
      .catch((err) => setLoadErr(err.message || "Neo4j unreachable"));
  }, []);

  React.useEffect(() => {
    if (active) load();
  }, [active, load]);

  const open = (name) => {
    onProject(name);
    onBack(); // mockup behaviour: picking a project returns to the landing
  };
  const createProject = () => {
    const name = newName.trim();
    if (!name) return;
    setCreating(false);
    setNewName("");
    open(name); // nodes appear under this scope on first rule ingest
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
                  onChange={(e) => setNewName(e.target.value)}
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

        {loadErr && (
          <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>
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
              description={`${p.nodes} node${p.nodes === 1 ? "" : "s"} in graph${p.project === project ? " · active" : ""}`}
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
            No projects yet · ingest a rule to create one
          </div>
        )}

        <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
          {projects.length} project{projects.length === 1 ? "" : "s"} · Neo4j connected · {cfg.neo4jUri || "bolt://neo4j:7687"}
        </div>
      </div>
    </div>
  );
}
