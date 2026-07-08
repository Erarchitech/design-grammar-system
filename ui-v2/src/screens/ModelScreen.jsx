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
import SpeckleViewport from "../components/speckle/SpeckleViewport.jsx";

// ---- deterministic synthetic massing: degraded-mode fallback only. When
// Speckle is unavailable (no token/urls or init error) the viewport renders
// these stylised isometric boxes; box geometry derives from entity ids so
// layouts are stable across loads. With Speckle healthy, both 3D and Map
// modes show the real model (Map = top-down orthographic).
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

const RUN_SHOTS_KEY = "dgv2_run_shots";
const PROJECT_SHOTS_KEY = "dgv2_project_shots";
const TILE_PROPS_KEY = "dgv2_tile_props";

// PropState ⊑ DesignState — the fixed catalogue of design-grammar properties the
// tiles can surface (owl:subClassOf DesignState in the metagraph). Each entry maps
// a display row to the real PropState values published from Grasshopper: `match`
// keywords are tested against a run state's projected props (iri + displayName).
const PROPSTATES = [
  { key: "height", label: "Height", iri: "dg:HeightState", match: ["height"] },
  { key: "gfa", label: "GFA", iri: "dg:GFAState", match: ["gfa", "floor area", "grossfloor"] },
  { key: "units", label: "Units", iri: "dg:UnitCountState", match: ["unit"] },
  { key: "storeys", label: "Storeys", iri: "dg:StoreyState", match: ["storey", "story", "floor count"] },
  { key: "coverage", label: "Site coverage", iri: "dg:CoverageState", match: ["coverage", "site cover"] },
  { key: "setback", label: "Setback", iri: "dg:SetbackState", match: ["setback"] },
  { key: "glazing", label: "Glazing ratio", iri: "dg:GlazingState", match: ["glazing", "glaz"] },
  { key: "daylight", label: "Daylight factor", iri: "dg:DaylightState", match: ["daylight"] },
  { key: "parking", label: "Parking ratio", iri: "dg:ParkingState", match: ["parking"] }
];
const DEFAULT_TILE_PROPS = ["height", "gfa", "units"];

function readTileProps() {
  try {
    const raw = JSON.parse(localStorage.getItem(TILE_PROPS_KEY) || "null");
    if (Array.isArray(raw)) return raw.filter((k) => PROPSTATES.some((p) => p.key === k));
  } catch {
    /* fall through to default */
  }
  return DEFAULT_TILE_PROPS;
}

// Resolve a catalogue entry to a real value for a design-state group, matching the
// state's projected props by keyword. Returns null when the state carries no such
// property (caller renders an em dash).
function propValueFor(state, entry) {
  const props = state?.props;
  if (!Array.isArray(props)) return null;
  for (const p of props) {
    const hay = ((p.label || "") + " " + (p.iri || "")).toLowerCase();
    if (entry.match.some((m) => hay.includes(m))) return p.value || null;
  }
  return null;
}

function readShotStore(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "{}");
  } catch {
    return {};
  }
}

// Downscale a viewer screenshot to a small JPEG thumbnail so the
// localStorage stores stay within quota (legacy viewer pattern).
function downscaleThumb(dataUrl, tw, th) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = tw;
      canvas.height = th;
      const ctx = canvas.getContext("2d");
      const sr = img.width / img.height;
      const tr = tw / th;
      let sw, sh, sx, sy;
      if (sr > tr) {
        sh = img.height;
        sw = sh * tr;
        sx = (img.width - sw) / 2;
        sy = 0;
      } else {
        sw = img.width;
        sh = sw / tr;
        sx = 0;
        sy = (img.height - sh) / 2;
      }
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, tw, th);
      resolve(canvas.toDataURL("image/jpeg", 0.7));
    };
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}

// Clickable colour swatch backed by a hidden <input type="color"> —
// same pattern as the legacy viewer's graphics bar.
function ColorSwatch({ label, color, onChange }) {
  const ref = React.useRef(null);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span
        onClick={() => ref.current?.click()}
        title={label + " colour"}
        style={{
          width: 18,
          height: 18,
          borderRadius: 5,
          background: color,
          border: "1px solid var(--color-hairline-strong)",
          cursor: "pointer",
          flex: "none"
        }}
      />
      <input ref={ref} type="color" value={color} onChange={(e) => onChange(e.target.value)} style={{ display: "none" }} />
    </span>
  );
}

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
  const [failColor, setFailColor] = React.useState("#e7000b");
  const [passColor, setPassColor] = React.useState("#737373");
  const [failOpen, setFailOpen] = React.useState(true);
  const [passOpen, setPassOpen] = React.useState(false);
  const [isolate, setIsolate] = React.useState(false);
  const [hidden, setHidden] = React.useState([]);
  const [selById, setSelById] = React.useState("");
  const [tileProps, setTileProps] = React.useState(readTileProps); // which PropState rows tiles show
  const [dsSettingsOpen, setDsSettingsOpen] = React.useState(false);
  const [viewMode, setViewMode] = React.useState("3d");
  const [speckleReady, setSpeckleReady] = React.useState(false);
  const [speckleError, setSpeckleError] = React.useState(null);
  const [viewBox, setViewBox] = React.useState({ x: 0, y: 0, w: 880, h: 440 });
  const svgRef = React.useRef(null);
  const mapRef = React.useRef(null);
  const panRef = React.useRef(null);
  const worldRef = React.useRef({ w: 880, h: 440 });
  const speckleApiRef = React.useRef(null);

  /* ---- automatic viewport screenshots (tiles) ---- */
  const [runShots, setRunShots] = React.useState(() => readShotStore(RUN_SHOTS_KEY));
  React.useEffect(() => {
    try {
      localStorage.setItem(RUN_SHOTS_KEY, JSON.stringify(runShots));
    } catch {
      // quota exceeded — thumbnails stay in-memory only
    }
  }, [runShots]);

  /* ---- tile-properties selection persistence ---- */
  React.useEffect(() => {
    try {
      localStorage.setItem(TILE_PROPS_KEY, JSON.stringify(tileProps));
    } catch {
      // quota exceeded — selection stays in-memory only
    }
  }, [tileProps]);
  const toggleTileProp = React.useCallback((key) => {
    setTileProps((prev) => (prev.indexOf(key) >= 0 ? prev.filter((k) => k !== key) : prev.concat([key])));
  }, []);

  /* ---- per-run graphics state (legacy runGfxMap session persistence) ---- */
  const [runGfx, setRunGfx] = React.useState(() => readShotStore("dgv2_run_gfx"));
  const runGfxRef = React.useRef(runGfx);
  runGfxRef.current = runGfx;
  const skipGfxSaveRef = React.useRef(false);
  React.useEffect(() => {
    try {
      localStorage.setItem("dgv2_run_gfx", JSON.stringify(runGfx));
    } catch {
      // quota exceeded — settings stay in-memory only
    }
  }, [runGfx]);
  // restore saved settings when switching runs
  React.useEffect(() => {
    if (!runId) return;
    const saved = runGfxRef.current[runId];
    if (!saved) return;
    skipGfxSaveRef.current = true;
    setMvFail(saved.mvFail);
    setMvPass(saved.mvPass);
    setMvBase(saved.mvBase);
    setAFail(saved.aFail);
    setAPass(saved.aPass);
    setFailColor(saved.failColor);
    setPassColor(saved.passColor);
    if (saved.stateKey !== undefined) setStateKey(saved.stateKey);
    if (saved.ruleId !== undefined) setRuleId(saved.ruleId);
  }, [runId]);
  // save settings for the active run whenever they change (not on run switch)
  React.useEffect(() => {
    if (!runId) return;
    if (skipGfxSaveRef.current) {
      skipGfxSaveRef.current = false;
      return;
    }
    setRunGfx((prev) => ({ ...prev, [runId]: { mvFail, mvPass, mvBase, aFail, aPass, failColor, passColor, stateKey, ruleId } }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mvFail, mvPass, mvBase, aFail, aPass, failColor, passColor, stateKey, ruleId]);

  const captureShot = React.useCallback(async () => {
    const api = speckleApiRef.current;
    if (!api || !runId) return;
    try {
      const dataUrl = await api.screenshot();
      if (!dataUrl) return;
      const thumb = await downscaleThumb(dataUrl, 320, 180);
      if (!thumb) return;
      setRunShots((prev) => ({ ...prev, [runId]: thumb }));
      if (project) {
        try {
          const shots = readShotStore(PROJECT_SHOTS_KEY);
          shots[project] = thumb;
          localStorage.setItem(PROJECT_SHOTS_KEY, JSON.stringify(shots));
        } catch {
          // quota exceeded — skip project thumbnail
        }
      }
    } catch {
      // screenshot unsupported / viewer busy — tile keeps its last thumbnail
    }
  }, [runId, project]);

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
      setSpeckleError(null);
      setSpeckleReady(false);
      return;
    }
    let gone = false;
    fetchValidationView(project, runId)
      .then((v) => {
        if (gone) return;
        setView(v);
        setSpeckleError(null);
        setSpeckleReady(false);
        // restore saved ruleId if available, otherwise use first failing rule
        const saved = runGfxRef.current[runId];
        const savedRuleId = saved?.ruleId;
        const hasValidRule = savedRuleId && (v.rules || []).some((r) => r.ruleId === savedRuleId);
        const firstFail = (v.rules || []).find((r) => !r.passed) || (v.rules || [])[0];
        skipGfxSaveRef.current = true;
        setRuleId(hasValidRule ? savedRuleId : (firstFail ? firstFail.ruleId : null));
        setPicked(null);
        setPropMode("run");
        setHidden([]);
        setIsolate(false);
      })
      .catch((err) => !gone && setLoadErr(err.message));
    return () => {
      gone = true;
    };
  }, [runId, project, fetchValidationView]);

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
  }, [ruleId, project, fetchRuleDetails]);

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
  }, [picked, runId, project, fetchEntityStatuses]);

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
  const failedEntityIdList = React.useMemo(() => (view?.objectSets?.failed || []).map((e) => e.dgEntityId), [view]);
  const passedEntityIdList = React.useMemo(() => (view?.objectSets?.passed || []).map((e) => e.dgEntityId), [view]);
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
      stroke: selB ? "var(--color-signal)" : fail ? failColor : passColor,
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

  const pick = React.useCallback((id) => {
    setPicked(id);
    setPropMode("instance");
  }, []);

  // Auto-capture: once the viewer is ready, and again (debounced) whenever
  // the graphics settings change, refresh the run/state/project thumbnails.
  React.useEffect(() => {
    if (!speckleReady) return;
    const t = setTimeout(() => void captureShot(), 1200);
    return () => clearTimeout(t);
  }, [speckleReady, mvFail, mvPass, mvBase, aFail, aPass, failColor, passColor, viewMode, captureShot]);

  const retry3d = () => {
    setSpeckleError(null);
    setViewMode("3d");
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
      ctx.fillStyle = fail ? failColor : passColor;
      ctx.fillRect(ox + b.x * sc, oy + (b.y - b.h) * sc, Math.max(2, b.w * sc), Math.max(2, b.h * sc));
    }
    ctx.strokeStyle = failColor;
    ctx.lineWidth = 1;
    ctx.strokeRect(ox + viewBox.x * sc, oy + viewBox.y * sc, viewBox.w * sc, viewBox.h * sc);
  }, [boxes, viewBox, failedIds, failColor, passColor]);

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

  const speckleResourceUrls = React.useMemo(
    () => (view ? [view.baseResourceUrl, view.validationResourceUrl].filter(Boolean) : []),
    [view]
  );
  const speckleToken = view?.readToken || null;
  const handleSpeckleReady = React.useCallback(() => setSpeckleReady(true), []);
  const handleSpeckleError = React.useCallback((msg) => setSpeckleError(msg), []);

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
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
          <span style={{ font: "500 11px/1.33 var(--font-sans)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>Design States</span>
          <Badge variant="outline">{groups.length}</Badge>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9 }}>
              {tileProps.length} / {PROPSTATES.length} props
            </span>
            <div
              onClick={() => setDsSettingsOpen((v) => !v)}
              title="Configure tile properties"
              style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 30, height: 30, border: "1px solid var(--color-hairline)", borderRadius: "var(--radius-buttons)", cursor: "pointer", color: "var(--text-secondary)", background: "var(--surface-card)" }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <line x1="21" y1="4" x2="14" y2="4" />
                <line x1="10" y1="4" x2="3" y2="4" />
                <line x1="21" y1="12" x2="12" y2="12" />
                <line x1="8" y1="12" x2="3" y2="12" />
                <line x1="21" y1="20" x2="16" y2="20" />
                <line x1="12" y1="20" x2="3" y2="20" />
                <line x1="14" y1="2" x2="14" y2="6" />
                <line x1="8" y1="10" x2="8" y2="14" />
                <line x1="16" y1="18" x2="16" y2="22" />
              </svg>
            </div>
          </div>
          {dsSettingsOpen && (
            <>
              <div onClick={() => setDsSettingsOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 14 }} />
              <div className="dg-frost" style={{ position: "absolute", right: 0, top: 38, zIndex: 15, width: 250, borderRadius: "var(--radius-nested)", boxShadow: "var(--shadow-panel)", padding: 12, display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 3, padding: "0 4px 8px", borderBottom: "1px solid var(--color-hairline)" }}>
                  <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>Tile Properties</span>
                  <span style={{ font: "400 9px/1.4 var(--font-mono)", color: "var(--text-muted)" }}>PropState ⊑ DesignState · bolt://dg-meta:7687</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 1, paddingTop: 4 }}>
                  {PROPSTATES.map((p) => {
                    const on = tileProps.indexOf(p.key) >= 0;
                    return (
                      <div
                        key={p.key}
                        onClick={() => toggleTileProp(p.key)}
                        style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 4px", borderRadius: 8, cursor: "pointer" }}
                      >
                        <span style={{ width: 15, height: 15, flex: "none", border: `1px solid ${on ? "var(--color-ink)" : "var(--color-hairline)"}`, background: on ? "var(--color-ink)" : "transparent", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center", font: "600 9px/1 var(--font-sans)", color: "var(--surface-card)" }}>
                          {on ? "✓" : ""}
                        </span>
                        <span style={{ flex: 1, font: "500 12px/1.3 var(--font-sans)", color: on ? "var(--text-primary)" : "var(--text-muted)" }}>{p.label}</span>
                        <span style={{ font: "400 9px/1.3 var(--font-mono)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>{p.iri}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}
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
          const stateThumb = g.runs.map((r) => runShots[r.runId]).find(Boolean);
          const propRows = PROPSTATES.filter((p) => tileProps.indexOf(p.key) >= 0).map((entry) => ({
            key: entry.key,
            label: entry.label,
            value: propValueFor(g.state, entry)
          }));
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
              {stateThumb && (
                <img
                  src={stateThumb}
                  alt=""
                  style={{ width: "100%", height: 74, objectFit: "cover", display: "block", borderRadius: 6, border: "1px solid var(--color-hairline)" }}
                />
              )}
              {propRows.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  {propRows.map((r) => (
                    <div key={r.key} style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
                      <span style={{ font: "400 10px/1.4 var(--font-annotation)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>{r.label}</span>
                      <span style={{ font: "500 11px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>{r.value ?? "—"}</span>
                    </div>
                  ))}
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
      </aside>

      {/* ===== centre: toolbar + map + runs strip ===== */}
      <main style={{ flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "10px 16px", background: "var(--surface-card)", borderBottom: "1px solid var(--color-hairline)" }}>
          <Checkbox label="Failing" checked={mvFail} onChange={setMvFail} />
          <Checkbox label="Passing" checked={mvPass} onChange={setMvPass} />
          <Checkbox label="Base model" checked={mvBase} onChange={setMvBase} />
          <span style={{ width: 1, height: 20, background: "var(--color-hairline)" }} />
          <ColorSwatch label="Fail" color={failColor} onChange={setFailColor} />
          <Slider label="Fail α" value={aFail} onChange={setAFail} style={{ width: 150 }} />
          <ColorSwatch label="Pass" color={passColor} onChange={setPassColor} />
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
          <span style={{ width: 1, height: 20, background: "var(--color-hairline)" }} />
          <div style={{ display: "flex", gap: 4 }}>
            <Button variant="outline" size="sm" selected={viewMode === "3d"} onClick={() => { if (speckleError) retry3d(); else setViewMode("3d"); }}>
              {speckleError ? "Retry 3D" : "3D"}
            </Button>
            <Button variant="outline" size="sm" selected={viewMode === "map"} onClick={() => setViewMode("map")}>
              Map
            </Button>
          </div>
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
          {!speckleError && speckleResourceUrls.length > 0 && speckleToken ? (
            <SpeckleViewport
              viewMode={viewMode}
              readToken={speckleToken}
              resourceUrls={speckleResourceUrls}
              project={project}
              runId={runId}
              failedEntityIds={failedEntityIdList}
              passedEntityIds={passedEntityIdList}
              showFailed={mvFail}
              showPassed={mvPass}
              showBase={mvBase}
              failColor={failColor}
              passColor={passColor}
              failOpacity={aFail}
              passOpacity={aPass}
              hiddenIds={hidden}
              isolateEntityId={isolate && picked ? picked : null}
              onEntityClick={pick}
              onReady={handleSpeckleReady}
              onError={handleSpeckleError}
              apiRef={speckleApiRef}
              style={{ position: "absolute", inset: 0 }}
            />
          ) : (
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

              {/* minimap — only in map mode */}
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
          )}
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
                thumb={runShots[r.runId]}
                active={r.runId === runId}
                onSelect={() => {
                  void captureShot(); // snapshot the outgoing run before switching
                  setRunId(r.runId);
                }}
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
