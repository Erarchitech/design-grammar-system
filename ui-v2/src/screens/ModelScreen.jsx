import React from "react";
import {
  Badge,
  Button,
  Checkbox,
  Chip,
  CodeBlock,
  Collapsible,
  CollapsibleItem,
  KVRow,
  Panel,
  RunTile,
  SearchField,
  Slider,
  StatBlock
} from "../components/index.js";
import { fetchValidationRuns, fetchValidationView, fetchRuleDetails, fetchEntityStatuses } from "../lib/modelApi.js";

// ---- deterministic synthetic massing: the V2 spec renders the validation
// viewport as a stylised isometric map (true 3D Speckle embed is deferred);
// box geometry derives from entity ids so layouts are stable across loads.
function hashOf(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return h >>> 0;
}
function layoutEntities(ids) {
  const perRow = 7;
  return ids.map((id, k) => {
    const h = hashOf(id);
    const row = Math.floor(k / perRow),
      col = k % perRow;
    return {
      id,
      x: 60 + col * 115 + (row % 2) * 40,
      y: 340 + row * 170,
      w: 56 + (h % 28),
      d: 28 + ((h >> 4) % 12),
      h: 52 + ((h >> 8) % 138)
    };
  });
}
function boxPath(b) {
  const iso = (dx, dy, dz) => [b.x + dx - dy * 0.6, b.y - dz - dy * 0.32];
  const p = (a) => a.join(",");
  const A = iso(0, 0, 0),
    B = iso(b.w, 0, 0),
    C = iso(b.w, b.d, 0),
    D2 = iso(0, 0, b.h),
    B2 = iso(b.w, 0, b.h),
    C2 = iso(b.w, b.d, b.h),
    E2 = iso(0, b.d, b.h);
  return (
    "M" + p(A) + " L" + p(B) + " L" + p(B2) + " L" + p(D2) + " Z M" + p(B) + " L" + p(C) + " L" + p(C2) +
    " L" + p(B2) + " Z M" + p(D2) + " L" + p(B2) + " L" + p(C2) + " L" + p(E2) + " Z"
  );
}

const NO_STATE = "__no_state__";

// Validation results in the V2 skin: run browsing with failing/passing
// breakdowns (MVIEW-01), instance inspection (MVIEW-02), map canvas with
// validation colouring + minimap + zoom (MVIEW-03), SWRL rule panel and
// orbit-glyph status legend (MVIEW-04).
export default function ModelScreen({ active, onBack, project }) {
  const [runs, setRuns] = React.useState([]);
  const [loadErr, setLoadErr] = React.useState("");
  const [stateKey, setStateKey] = React.useState(null); // design-state group filter
  const [runId, setRunId] = React.useState(null);
  const [view, setView] = React.useState(null); // validation view payload
  const [rule, setRule] = React.useState(null); // {ruleId, name, description, swrl}
  const [ruleId, setRuleId] = React.useState(null);
  const [propMode, setPropMode] = React.useState("run");
  const [picked, setPicked] = React.useState(null); // dgEntityId
  const [pickedStatuses, setPickedStatuses] = React.useState([]);
  const [mvFail, setMvFail] = React.useState(true);
  const [mvPass, setMvPass] = React.useState(true);
  const [mvBase, setMvBase] = React.useState(true);
  const [aFail, setAFail] = React.useState(85);
  const [aPass, setAPass] = React.useState(55);
  const [failOpen, setFailOpen] = React.useState(true);
  const [passOpen, setPassOpen] = React.useState(false);
  const [isolate, setIsolate] = React.useState(false);
  const [hidden, setHidden] = React.useState([]);
  const [selById, setSelById] = React.useState("");
  const [viewBox, setViewBox] = React.useState({ x: 0, y: 0, w: 880, h: 440 });
  const svgRef = React.useRef(null);
  const mapRef = React.useRef(null);
  const panRef = React.useRef(null);
  const worldRef = React.useRef({ w: 880, h: 440 });

  const load = React.useCallback(async () => {
    setLoadErr("");
    try {
      const data = await fetchValidationRuns(project);
      const list = data.runs || [];
      setRuns(list);
      // keep the current run only if it still exists under this project scope
      setRunId((prev) => (prev && list.some((r) => r.runId === prev) ? prev : list[0]?.runId || null));
    } catch (err) {
      setLoadErr(err.message || "data-service unreachable");
    }
  }, [project]);

  // project switch invalidates every run-scoped bit of state
  React.useEffect(() => {
    setRuns([]);
    setRunId(null);
    setView(null);
    setStateKey(null);
    setPicked(null);
    setPropMode("run");
  }, [project]);

  React.useEffect(() => {
    if (active) load();
  }, [active, load]);

  // load the selected run's view (rules + entity sets)
  React.useEffect(() => {
    if (!runId) {
      setView(null);
      return;
    }
    let gone = false;
    fetchValidationView(project, runId)
      .then((v) => {
        if (gone) return;
        setView(v);
        const firstFail = (v.rules || []).find((r) => !r.passed) || (v.rules || [])[0];
        setRuleId(firstFail ? firstFail.ruleId : null);
        setPicked(null);
        setPropMode("run");
        setHidden([]);
        setIsolate(false);
      })
      .catch((err) => !gone && setLoadErr(err.message));
    return () => {
      gone = true;
    };
  }, [runId, project]);

  // rule details (SWRL from the metagraph)
  React.useEffect(() => {
    if (!ruleId) {
      setRule(null);
      return;
    }
    let gone = false;
    fetchRuleDetails(ruleId, project)
      .then((r) => !gone && setRule(r ? { ruleId, ...r } : { ruleId, swrl: "", name: "", description: "" }))
      .catch(() => !gone && setRule({ ruleId, swrl: "", name: "", description: "" }));
    return () => {
      gone = true;
    };
  }, [ruleId, project]);

  // per-rule statuses for the picked instance
  React.useEffect(() => {
    if (!picked || !runId) {
      setPickedStatuses([]);
      return;
    }
    let gone = false;
    fetchEntityStatuses(project, runId, picked)
      .then((s) => !gone && setPickedStatuses(s))
      .catch(() => !gone && setPickedStatuses([]));
    return () => {
      gone = true;
    };
  }, [picked, runId, project]);

  /* ---- design-state grouping (stateId from statePayloadJson summaries) ---- */
  const groups = React.useMemo(() => {
    const buckets = new Map();
    for (const r of runs) {
      const key = r.state?.stateId || NO_STATE;
      if (!buckets.has(key)) buckets.set(key, { key, state: r.state, runs: [] });
      buckets.get(key).runs.push(r);
    }
    const arr = [...buckets.values()];
    arr.sort((a, b) => (a.key === NO_STATE) - (b.key === NO_STATE) || a.key.localeCompare(b.key));
    return arr;
  }, [runs]);

  const visibleRuns = stateKey ? runs.filter((r) => (r.state?.stateId || NO_STATE) === stateKey) : runs;

  /* ---- entities and map items ---- */
  const failedIds = React.useMemo(() => new Set((view?.objectSets?.failed || []).map((e) => e.dgEntityId)), [view]);
  const entities = React.useMemo(() => {
    const all = [...(view?.objectSets?.failed || []), ...(view?.objectSets?.passed || [])];
    all.sort((a, b) => a.dgEntityId.localeCompare(b.dgEntityId));
    return all;
  }, [view]);
  const boxes = React.useMemo(() => layoutEntities(entities.map((e) => e.dgEntityId)), [entities]);

  React.useEffect(() => {
    // fit world + viewBox to content
    const rows = Math.max(1, Math.ceil(boxes.length / 7));
    const w = 880,
      h = Math.max(440, 260 + rows * 170);
    worldRef.current = { w, h };
    setViewBox({ x: 0, y: 0, w, h });
  }, [boxes.length]);

  const hiddenSet = new Set(hidden);
  const items = [];
  let callout = null;
  for (const b of boxes) {
    const fail = failedIds.has(b.id);
    if ((fail && !mvFail) || (!fail && !mvPass) || hiddenSet.has(b.id) || (isolate && picked !== b.id)) continue;
    const selB = picked === b.id;
    items.push({
      id: b.id,
      d: boxPath(b),
      fill: selB ? "var(--color-signal-soft)" : fail ? "var(--color-signal-soft)" : "transparent",
      stroke: selB ? "var(--color-signal)" : fail ? "var(--status-fail)" : "var(--ink-a32)",
      sw: selB || fail ? 1.5 : 1,
      op: (fail ? aFail : aPass) / 100
    });
    if (selB) {
      callout = {
        d: `M${b.x + b.w / 2} ${b.y - b.h - 12} L ${b.x + b.w / 2} ${b.y - b.h - 42} L ${b.x + b.w / 2 + 16} ${b.y - b.h - 42}`,
        tx: b.x + b.w / 2 + 22,
        ty1: b.y - b.h - 48,
        ty2: b.y - b.h - 34,
        name: b.id.toUpperCase(),
        status: fail ? "FAILING · " + (ruleId || "").toUpperCase() : "PASSING"
      };
    }
  }

  const pick = (id) => {
    setPicked(id);
    setPropMode("instance");
  };

  /* ---- map zoom / pan / minimap ---- */
  const onWheel = (e) => {
    e.preventDefault();
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const vb = viewBox;
    const mx = vb.x + ((e.clientX - rect.left) / rect.width) * vb.w;
    const my = vb.y + ((e.clientY - rect.top) / rect.height) * vb.h;
    const f = Math.exp(e.deltaY * 0.0012);
    const world = worldRef.current;
    const w = Math.max(world.w * 0.15, Math.min(world.w * 1.6, vb.w * f));
    const h = (w / vb.w) * vb.h;
    setViewBox({ x: mx - ((mx - vb.x) / vb.w) * w, y: my - ((my - vb.y) / vb.h) * h, w, h });
  };
  const onPointerDown = (e) => {
    if (e.button !== 0) return;
    panRef.current = { x: e.clientX, y: e.clientY, vb: { ...viewBox }, moved: 0 };
  };
  const onPointerMove = (e) => {
    const p = panRef.current;
    if (!p || !(e.buttons & 1)) return;
    const svg = svgRef.current;
    const rect = svg.getBoundingClientRect();
    const dx = ((e.clientX - p.x) / rect.width) * p.vb.w;
    const dy = ((e.clientY - p.y) / rect.height) * p.vb.h;
    p.moved += Math.abs(e.movementX || 0) + Math.abs(e.movementY || 0);
    setViewBox({ x: p.vb.x - dx, y: p.vb.y - dy, w: p.vb.w, h: p.vb.h });
  };
  const onPointerUp = () => {
    panRef.current = null;
  };

  React.useEffect(() => {
    const ctx = mapRef.current?.getContext("2d");
    if (!ctx) return;
    const S = 150;
    const world = worldRef.current;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    mapRef.current.width = S * dpr;
    mapRef.current.height = S * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, S, S);
    const sc = (S - 10) / Math.max(world.w, world.h);
    const ox = 5,
      oy = 5;
    for (const b of boxes) {
      const fail = failedIds.has(b.id);
      ctx.fillStyle = fail ? "#e7000b" : "rgba(10,10,10,0.4)";
      ctx.fillRect(ox + b.x * sc, oy + (b.y - b.h) * sc, Math.max(2, b.w * sc), Math.max(2, b.h * sc));
    }
    ctx.strokeStyle = "#e7000b";
    ctx.lineWidth = 1;
    ctx.strokeRect(ox + viewBox.x * sc, oy + viewBox.y * sc, viewBox.w * sc, viewBox.h * sc);
  }, [boxes, viewBox, failedIds]);

  const onMapClick = (e) => {
    const rect = mapRef.current.getBoundingClientRect();
    const world = worldRef.current;
    const sc = (150 - 10) / Math.max(world.w, world.h);
    const wx = (e.clientX - rect.left - 5) / sc;
    const wy = (e.clientY - rect.top - 5) / sc;
    setViewBox((vb) => ({ ...vb, x: wx - vb.w / 2, y: wy - vb.h / 2 }));
  };

  const failItems = (view?.objectSets?.failed || []).map((e) => ({
    id: e.dgEntityId,
    primary: e.displayName || e.dgEntityId,
    secondary: "id: " + e.dgEntityId
  }));
  const passItems = (view?.objectSets?.passed || []).map((e) => ({
    id: e.dgEntityId,
    primary: e.displayName || e.dgEntityId,
    secondary: "id: " + e.dgEntityId
  }));
  const pickedEntity = entities.find((e) => e.dgEntityId === picked);
  const pickedFailing = picked ? failedIds.has(picked) : false;
  const zoomPct = worldRef.current.w / viewBox.w;

  const legendRows = [
    { name: "Failing", color: "var(--color-signal)", count: failItems.length },
    { name: "Passing", color: "var(--color-ink)", count: passItems.length },
    { name: "Base model", color: "var(--color-mid-gray)", count: mvBase ? "on" : "off" }
  ];

  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", background: "var(--color-canvas)" }}>
      {/* ===== left: design states + runs ===== */}
      <aside style={{ width: 320, flex: "none", boxSizing: "border-box", background: "var(--surface-sidebar)", borderRight: "1px solid var(--color-hairline)", overflow: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingBottom: 12, borderBottom: "1px solid var(--color-hairline)" }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            ← Back
          </Button>
        </div>
        <div>
          <h3 style={{ margin: 0, font: "600 20px/1.2 var(--font-sans)", letterSpacing: "-0.5px" }}>Model Viewer</h3>
          <span style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>
            {project || "default-project"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
          <span style={{ font: "500 11px/1.33 var(--font-sans)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>Design States</span>
          <Badge variant="outline">{groups.length}</Badge>
        </div>
        {loadErr && (
          <div style={{ font: "400 12px/1.4 var(--font-sans)", color: "var(--color-signal)" }}>
            {loadErr}{" "}
            <span onClick={load} style={{ cursor: "pointer", textDecoration: "underline" }}>
              Retry
            </span>
          </div>
        )}
        {!loadErr && runs.length === 0 && (
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
            No validation runs · publish from Grasshopper
          </div>
        )}
        {groups.map((g) => {
          const on = stateKey === g.key;
          const latest = g.runs[0];
          const fails = g.runs.reduce((s, r) => s + (r.failedRuleCount || 0), 0);
          const rules = g.runs.reduce((s, r) => s + (r.ruleCount || 0), 0);
          return (
            <div
              key={g.key}
              onClick={() => setStateKey(on ? null : g.key)}
              style={{
                border: on ? "1px solid var(--color-signal)" : "1px solid var(--color-hairline)",
                background: on ? "var(--accent-selection-bg)" : "var(--surface-card)",
                borderRadius: "var(--radius-nested)",
                padding: 12,
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: 9
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ font: "600 13px/1.2 var(--font-mono)", letterSpacing: "-0.1px", color: on ? "var(--color-signal-ink)" : "var(--color-ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {g.key === NO_STATE ? "No design state" : (g.state?.label || g.key)}
                </span>
                <span style={{ font: "400 9px/1.3 var(--font-annotation)", letterSpacing: "1px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                  {g.runs.length} run{g.runs.length === 1 ? "" : "s"}
                </span>
              </div>
              {g.state?.label && g.key !== NO_STATE && (
                <div style={{ font: "400 10px/1.3 var(--font-mono)", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {g.key}
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ font: "400 10px/1.4 var(--font-annotation)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>Captured</span>
                  <span style={{ font: "500 11px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>
                    {g.state?.capturedAtUtc ? String(g.state.capturedAtUtc).slice(0, 16).replace("T", " ") : "—"}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ font: "400 10px/1.4 var(--font-annotation)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>States</span>
                  <span style={{ font: "500 11px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>{g.state?.parameterCount ?? "—"}</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingTop: 8, borderTop: "1px solid var(--color-hairline)" }}>
                <span style={{ font: "400 10px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>
                  {latest?.createdAt ? String(latest.createdAt).slice(0, 10) : ""}
                </span>
                <span style={{ font: "500 10px/1.3 var(--font-mono)", color: fails ? "var(--color-signal-ink)" : "var(--text-secondary)" }}>
                  {rules - fails} / {rules} pass
                </span>
              </div>
            </div>
          );
        })}

        {/* orbit-glyph status legend (per spec) */}
        <div className="dg-frost" style={{ borderRadius: "var(--radius-nested)", padding: 8, display: "flex", flexDirection: "column", gap: 1, marginTop: "auto" }}>
          <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10, padding: "2px 6px 6px" }}>
            Legend
          </span>
          {legendRows.map((row, o) => (
            <div key={row.name} style={{ display: "flex", alignItems: "center", gap: 11, padding: "5px 6px" }}>
              <span style={{ position: "relative", width: 24, height: 24, flex: "none" }}>
                <span style={{ position: "absolute", left: "50%", top: "50%", width: 22, height: 22, margin: "-11px 0 0 -11px", borderRadius: "50%", border: `1.5px solid ${o === 2 ? row.color : "var(--ink-a16)"}` }} />
                <span style={{ position: "absolute", left: "50%", top: "50%", width: 13, height: 13, margin: "-6.5px 0 0 -6.5px", borderRadius: "50%", border: `1.5px solid ${o === 1 ? row.color : "var(--ink-a16)"}` }} />
                <span style={{ position: "absolute", left: "50%", top: "50%", width: 5, height: 5, margin: "-2.5px 0 0 -2.5px", borderRadius: "50%", background: o === 0 ? row.color : "var(--ink-a16)" }} />
              </span>
              <span style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <span style={{ font: "600 11px/1.3 var(--font-sans)" }}>{row.name}</span>
                <span style={{ font: "400 9px/1.4 var(--font-annotation)", letterSpacing: "0.8px", textTransform: "uppercase", color: "var(--text-muted)" }}>{row.count}</span>
              </span>
            </div>
          ))}
        </div>
      </aside>

      {/* ===== centre: toolbar + map + runs strip ===== */}
      <main style={{ flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "10px 16px", background: "var(--surface-card)", borderBottom: "1px solid var(--color-hairline)" }}>
          <Checkbox label="Failing" checked={mvFail} onChange={setMvFail} />
          <Checkbox label="Passing" checked={mvPass} onChange={setMvPass} />
          <Checkbox label="Base model" checked={mvBase} onChange={setMvBase} />
          <span style={{ width: 1, height: 20, background: "var(--color-hairline)" }} />
          <Slider label="Fail α" value={aFail} onChange={setAFail} style={{ width: 150 }} />
          <Slider label="Pass α" value={aPass} onChange={setAPass} style={{ width: 150 }} />
          <span style={{ width: 1, height: 20, background: "var(--color-hairline)" }} />
          <SearchField
            placeholder="Select by Id…"
            value={selById}
            style={{ width: 170 }}
            onChange={(e) => {
              setSelById(e.target.value);
              const hit = entities.find((x) => x.dgEntityId.toLowerCase().includes(e.target.value.toLowerCase()));
              if (e.target.value && hit) pick(hit.dgEntityId);
            }}
          />
          <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
            <Button variant="outline" size="sm" selected={isolate} onClick={() => setIsolate((v) => !v)}>
              Isolate
            </Button>
            <Button variant="outline" size="sm" onClick={() => picked && setHidden((h) => [...h, picked])}>
              Hide
            </Button>
            {hidden.length > 0 && (
              <Button variant="secondary" size="sm" onClick={() => setHidden([])}>
                Show all
              </Button>
            )}
          </div>
        </div>

        <div style={{ flex: "1 1 auto", minHeight: 0, display: "flex", position: "relative" }}>
          <div className="dg-blueprint" style={{ flex: "1 1 auto", minWidth: 0, position: "relative" }}>
            <svg
              ref={svgRef}
              width="100%"
              height="100%"
              viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
              preserveAspectRatio="xMidYMid meet"
              style={{ display: "block", position: "absolute", inset: 0, touchAction: "none", cursor: "grab" }}
              onWheel={onWheel}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
            >
              {mvBase && <path d={`M30 ${worldRef.current.h - 80} L ${worldRef.current.w - 30} ${worldRef.current.h - 80} M60 ${worldRef.current.h - 50} L ${worldRef.current.w} ${worldRef.current.h - 50}`} stroke="var(--ink-a08)" strokeWidth="1" fill="none" />}
              {items.map((b) => (
                <path
                  key={b.id}
                  d={b.d}
                  fill={b.fill}
                  stroke={b.stroke}
                  strokeWidth={b.sw}
                  opacity={b.op}
                  onClick={() => {
                    if (!panRef.current || panRef.current.moved < 5) pick(b.id);
                  }}
                  style={{ cursor: "pointer" }}
                />
              ))}
              {callout && (
                <g>
                  <path d={callout.d} stroke="var(--ink-a32)" strokeWidth="1" fill="none" />
                  <text x={callout.tx} y={callout.ty1} fontFamily="Oswald, sans-serif" fontSize="13" letterSpacing="1.4" fill="var(--color-ink)">
                    {callout.name}
                  </text>
                  <text x={callout.tx} y={callout.ty2} fontFamily="Oswald, sans-serif" fontSize="10" letterSpacing="1.2" fill="var(--color-mid-gray)">
                    {callout.status}
                  </text>
                </g>
              )}
              {entities.length === 0 && (
                <text x={viewBox.x + viewBox.w / 2} y={viewBox.y + viewBox.h / 2} textAnchor="middle" fontFamily="Oswald, sans-serif" fontSize="12" letterSpacing="1.4" fill="var(--color-mid-gray)">
                  {runId ? "NO ENTITIES IN THIS RUN" : "SELECT A VALIDATION RUN"}
                </text>
              )}
            </svg>

            {/* minimap */}
            <div style={{ position: "absolute", right: 14, top: 14 }}>
              <div className="dg-frost" style={{ borderRadius: "var(--radius-nested)", padding: 8, boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "0 2px" }}>
                  <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9 }}>
                    Overview
                  </span>
                  <span style={{ font: "500 9px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>{zoomPct.toFixed(1)}×</span>
                </div>
                <canvas ref={mapRef} style={{ width: 150, height: 150, display: "block", borderRadius: 6, cursor: "crosshair" }} onClick={onMapClick} />
              </div>
            </div>
          </div>
        </div>

        <div style={{ background: "var(--surface-card)", borderTop: "1px solid var(--color-hairline)", padding: "10px 16px 14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <span style={{ font: "500 11px/1.33 var(--font-sans)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>Validation runs</span>
            <Badge variant="outline">{visibleRuns.length}</Badge>
          </div>
          <div style={{ display: "flex", gap: 10, overflowX: "auto" }}>
            {visibleRuns.map((r) => (
              <RunTile
                key={r.runId}
                ruleId={r.ruleIds?.[0] ? r.ruleIds[0] + (r.ruleCount > 1 ? " +" + (r.ruleCount - 1) : "") : r.runId}
                date={r.createdAt ? String(r.createdAt).slice(0, 10) : ""}
                kind={r.failedRuleCount ? r.failedRuleCount + " failing" : "All pass"}
                active={r.runId === runId}
                onSelect={() => setRunId(r.runId)}
              />
            ))}
          </div>
        </div>
      </main>

      {/* ===== right: properties sidebar ===== */}
      <aside style={{ width: 344, flex: "none", boxSizing: "border-box", background: "var(--surface-sidebar)", borderLeft: "1px solid var(--color-hairline)", overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: 12, borderBottom: "1px solid var(--color-hairline)" }}>
          <span style={{ font: "600 15px/1.2 var(--font-sans)", letterSpacing: "-0.2px" }}>Properties</span>
          <span style={{ marginLeft: "auto", font: "400 9px/1.3 var(--font-annotation)", letterSpacing: "1.2px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
            {propMode === "run" ? "Validation run" : "Geometry instance"}
          </span>
        </div>

        {propMode === "run" && view && (
          <>
            <Panel title="Validation run">
              <KVRow label="Run Id" value={view.runId} />
              <KVRow label="Date Created" value={view.createdAt ? String(view.createdAt).slice(0, 19).replace("T", " ") : "—"} />
              <KVRow label="Base Model" value={view.baseModelId || "—"} />
              <KVRow label="Validation Model" value={view.validationModelId || "—"} />
              <div style={{ display: "flex", gap: 28, marginTop: 10 }}>
                <StatBlock label="Failing" value={String(failItems.length)} signal={failItems.length > 0} />
                <StatBlock label="Passing" value={String(passItems.length)} />
              </div>
            </Panel>
            <Collapsible label="Failing items" count={failItems.length} signal={failItems.length > 0} open={failOpen} onToggle={() => setFailOpen((v) => !v)}>
              {failItems.map((it) => (
                <CollapsibleItem key={it.id} primary={it.primary} secondary={it.secondary} selected={picked === it.id} onClick={() => pick(it.id)} />
              ))}
            </Collapsible>
            <Collapsible label="Passing items" count={passItems.length} open={passOpen} onToggle={() => setPassOpen((v) => !v)}>
              {passItems.map((it) => (
                <CollapsibleItem key={it.id} primary={it.primary} secondary={it.secondary} selected={picked === it.id} onClick={() => pick(it.id)} />
              ))}
            </Collapsible>
            <Panel title="Rule">
              {(view.rules || []).length > 1 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                  {view.rules.map((r) => (
                    <Chip key={r.ruleId} selected={r.ruleId === ruleId} style={{ cursor: "pointer" }}>
                      <span onClick={() => setRuleId(r.ruleId)}>{r.ruleId}</span>
                    </Chip>
                  ))}
                </div>
              )}
              <KVRow label="Rule_Id" value={ruleId || "—"} />
              <KVRow label="Name" value={rule?.name || "—"} mono={false} />
              <KVRow label="Description" value={rule?.description || "—"} mono={false} />
              <div style={{ marginTop: 10 }}>
                <CodeBlock label="SWRL Expression">{rule?.swrl || "—"}</CodeBlock>
              </div>
            </Panel>
          </>
        )}
        {propMode === "run" && !view && (
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
            {runs.length ? "Loading run…" : "No validation run selected"}
          </div>
        )}

        {propMode === "instance" && (
          <>
            <div
              onClick={() => setPropMode("run")}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, alignSelf: "flex-start", cursor: "pointer", font: "500 11px/1.2 var(--font-annotation)", letterSpacing: "1px", textTransform: "uppercase", color: "var(--text-muted)" }}
            >
              ← Validation run
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Chip selected>{pickedFailing ? "Failing" : "Passing"}</Chip>
              <span style={{ font: "500 13px/1.3 var(--font-mono)", letterSpacing: "-0.2px" }}>{picked}</span>
            </div>
            <Panel title="Instance properties">
              <KVRow label="Id" value={picked || "—"} />
              <KVRow label="Display name" value={pickedEntity?.displayName || picked || "—"} />
              <KVRow label="Run" value={view?.runId || "—"} />
            </Panel>
            <Panel title="Validation">
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8, paddingBottom: 8, borderBottom: "1px solid var(--color-hairline)" }}>
                <span style={{ font: "400 12px/1.3 var(--font-sans)", color: "var(--text-muted)" }}>Status</span>
                <span style={{ font: "600 12px/1.3 var(--font-mono)", color: pickedFailing ? "var(--color-signal)" : "var(--text-secondary)" }}>
                  {pickedFailing ? "FAIL" : "PASS"}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 1, marginTop: 6 }}>
                {pickedStatuses.map((r) => (
                  <div key={r.ruleId} style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8, padding: "5px 0" }}>
                    <span style={{ font: "400 12px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>{r.ruleId}</span>
                    <span style={{ font: "500 11px/1.3 var(--font-mono)", color: r.status === "failed" ? "var(--color-signal)" : "var(--text-secondary)" }}>
                      {r.status === "failed" ? "Fail" : "Pass"}
                    </span>
                  </div>
                ))}
                {pickedStatuses.length === 0 && (
                  <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9, paddingTop: 6 }}>
                    No per-rule records
                  </span>
                )}
              </div>
            </Panel>
          </>
        )}
      </aside>
    </div>
  );
}
