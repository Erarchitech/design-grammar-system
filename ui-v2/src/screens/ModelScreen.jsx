import React from "react";
import {
  Badge,
  Button,
  CandidateTable,
  Checkbox,
  Chip,
  CodeBlock,
  Collapsible,
  CollapsibleItem,
  Input,
  KVRow,
  Panel,
  RunTile,
  SearchField,
  Slider,
  StatBlock
} from "../components/index.js";
import { fetchValidationRuns, fetchValidationView, fetchRuleDetails, fetchEntityStatuses } from "../lib/modelApi.js";
import { groupRunsByState, NO_STATE } from "../lib/runGroups.js";
import { classifyObjectSets } from "../lib/objectSets.js";
import { generateInputs, acceptCandidate, fetchAcceptedCandidates } from "../lib/inputGenApi.js";
import SpeckleViewport from "../components/speckle/SpeckleViewport.jsx";
import { useT } from "../i18n/LanguageProvider.jsx";
import { describeError } from "../i18n/index.js";
import useModelPanels from "./useModelPanels.js";

// ---- deterministic synthetic massing: degraded-mode fallback only. When
// Speckle is unavailable (no viewer resources or init error) the viewport renders
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

// v2: thumbnails captured before the background fill were black where the
// (transparent) viewer canvas showed the page — drop them rather than show them.
// Phase 1303-25 (D-71): objects without a verdict (no data) are drawn neutral, never in the fail colour.
const NO_VERDICT_COLOR = "#94A3B8";
const RUN_SHOTS_KEY = "dgv2_run_shots_v2";
const LEGACY_RUN_SHOTS_KEY = "dgv2_run_shots";
const PROJECT_SHOTS_KEY = "dgv2_project_shots";
// v2: { [project]: [propIri…] } — the old global list named a fixed urban
// catalogue (Height, GFA, …) that no real project's PropStates matched.
const TILE_PROPS_KEY = "dgv2_tile_props_v2";
const LEGACY_TILE_PROPS_KEY = "dgv2_tile_props";
const DEFAULT_TILE_PROP_COUNT = 3;
const CAMERA_KEY = "dgv2_model_camera"; // { [project]: { position, target } }
// Model context of a check (walls, columns, beams of the rule's classes): neutral and see-through by default.
const DEFAULT_CONTEXT_COLOR = "#a3a3a3";
const DEFAULT_CONTEXT_OPACITY = 35;

// "ex:hasTotalHeightM" → "Total Height M": local name, a leading "has" dropped,
// camelCase split. The full iri stays visible in the tile-properties menu.
function propLabel(iri) {
  const local = String(iri).replace(/^.*[:#/]/, "").replace(/^has(?=[A-Z])/, "");
  return local.replace(/([a-z0-9])([A-Z])/g, "$1 $2") || String(iri);
}

// The tile-property catalogue is the set of PropState properties the project's
// design states actually carry (their projected props), never a fixed list.
function propCatalogue(states) {
  const byIri = new Map();
  for (const state of states) {
    for (const p of state?.props || []) {
      if (p?.iri && !byIri.has(p.iri)) byIri.set(p.iri, { iri: p.iri, label: propLabel(p.iri) });
    }
  }
  return [...byIri.values()].sort((a, b) => a.label.localeCompare(b.label));
}

function formatNumber(n) {
  return String(Number(n.toFixed(3)));
}

// Summarise one property over a design state: a PropState usually holds one
// value per object, so numbers show as a min – max range (a single value when
// they agree) and text as the value or a count of distinct values. Returns null
// when the state carries no such property (caller renders an em dash).
function propSummary(state, iri, t) {
  const values = (state?.props || []).filter((p) => p?.iri === iri).map((p) => p.value);
  if (values.length === 0) return null;
  const nums = values.map((v) => Number(v));
  if (nums.every((n) => Number.isFinite(n))) {
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    return min === max ? formatNumber(min) : formatNumber(min) + " – " + formatNumber(max);
  }
  const distinct = new Set(values.map(String));
  return distinct.size === 1 ? String(values[0]) : t("{n} values", { n: distinct.size });
}

function readShotStore(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "{}");
  } catch {
    return {};
  }
}

// Downscale a viewer screenshot to a small JPEG thumbnail so the
// localStorage stores stay within quota (legacy viewer pattern). The Speckle
// canvas clears to transparent, and JPEG has no alpha — so paint the
// viewport's own background first, or the empty sky turns black.
function downscaleThumb(dataUrl, tw, th, background) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = tw;
      canvas.height = th;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = background || "#ffffff";
      ctx.fillRect(0, 0, tw, th);
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
  const { t } = useT();
  const ref = React.useRef(null);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span
        onClick={() => ref.current?.click()}
        title={t("{label} colour", { label })}
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
  const { t, tc, tp } = useT();
  const validationStatusLabel = (status) => {
    switch (status) {
      case "passed": return t("Passed");
      case "failed": return tc("validation", "Failed");
      case "unknown": return t("Unknown");
      case "not_evaluated": return t("Not evaluated");
      case "no_population": return t("No population");
      case "unsupported": return t("Unsupported");
      case "indeterminate": return t("Indeterminate");
      case "error": return t("Error");
      default: return status || t("Unknown");
    }
  };
  const [runs, setRuns] = React.useState([]);
  const [loadErr, setLoadErr] = React.useState(null); // { err, fallback: "runs" | "view" }
  const [stateKey, setStateKey] = React.useState(null); // design-state group filter
  const [runId, setRunId] = React.useState(null);
  const [view, setView] = React.useState(null); // validation view payload
  const [rule, setRule] = React.useState(null); // {ruleId, name, description, swrl}
  const [ruleId, setRuleId] = React.useState(null);

  /* ---- AI input candidates (Phase 38, D-20/GHIN-04) ----
     ruleForGen defaults to the screen's selected ruleId but is independently
     overridable, so switching the AI-panel's target does not disturb the
     rule the architect is inspecting validation results for. */
  const [ruleForGen, setRuleForGen] = React.useState(null);
  const [candidateCount, setCandidateCount] = React.useState(4);
  const [paramOverrides, setParamOverrides] = React.useState("");
  const [candidates, setCandidates] = React.useState(null); // full generate-inputs response, or null
  const [genErr, setGenErr] = React.useState(null); // error object; translated on render
  const [genBusy, setGenBusy] = React.useState(false);
  const [acceptedStates, setAcceptedStates] = React.useState([]); // [{candidateId, stateId}]
  const [busyCandidateId, setBusyCandidateId] = React.useState(null);
  const [propMode, setPropMode] = React.useState("run");
  const [picked, setPicked] = React.useState(null); // dgEntityId
  const [pickedStatuses, setPickedStatuses] = React.useState([]);
  const [mvFail, setMvFail] = React.useState(true);
  const [mvPass, setMvPass] = React.useState(true);
  const [aFail, setAFail] = React.useState(85);
  const [aPass, setAPass] = React.useState(55);
  const [failColor, setFailColor] = React.useState("#e7000b");
  const [passColor, setPassColor] = React.useState("#737373");
  const [contextColor, setContextColor] = React.useState(DEFAULT_CONTEXT_COLOR);
  const [aContext, setAContext] = React.useState(DEFAULT_CONTEXT_OPACITY);
  const [failOpen, setFailOpen] = React.useState(true);
  const [passOpen, setPassOpen] = React.useState(false);
  const [unknownOpen, setUnknownOpen] = React.useState(false);
  const [shaclViolationOpen, setShaclViolationOpen] = React.useState(true);
  const [shaclWarningOpen, setShaclWarningOpen] = React.useState(false);
  const [shaclInfoOpen, setShaclInfoOpen] = React.useState(false);
  const [isolate, setIsolate] = React.useState(false);
  const [hidden, setHidden] = React.useState([]);
  const [selById, setSelById] = React.useState("");
  const [tilePropSel, setTilePropSel] = React.useState(() => readShotStore(TILE_PROPS_KEY)); // { [project]: [propIri…] } tiles show
  const [dsSettingsOpen, setDsSettingsOpen] = React.useState(false);
  const [viewMode, setViewMode] = React.useState("3d");
  const [sceneTick, setSceneTick] = React.useState(0); // bumps each time the 3D scene finishes loading
  const [speckleError, setSpeckleError] = React.useState(null);
  const [viewBox, setViewBox] = React.useState({ x: 0, y: 0, w: 880, h: 440 });
  const rootRef = React.useRef(null);
  const panels = useModelPanels(rootRef);
  const svgRef = React.useRef(null);
  const mapRef = React.useRef(null);
  const panRef = React.useRef(null);
  const worldRef = React.useRef({ w: 880, h: 440 });
  const speckleApiRef = React.useRef(null);

  /* ---- automatic viewport screenshots (tiles) ---- */
  const [runShots, setRunShots] = React.useState(() => readShotStore(RUN_SHOTS_KEY));
  React.useEffect(() => {
    try {
      localStorage.removeItem(LEGACY_RUN_SHOTS_KEY);
    } catch {
      // storage unavailable — nothing to clean up
    }
  }, []);
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
      localStorage.setItem(TILE_PROPS_KEY, JSON.stringify(tilePropSel));
      localStorage.removeItem(LEGACY_TILE_PROPS_KEY);
    } catch {
      // quota exceeded — selection stays in-memory only
    }
  }, [tilePropSel]);

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
    setAFail(saved.aFail);
    setAPass(saved.aPass);
    setFailColor(saved.failColor);
    setPassColor(saved.passColor);
    setContextColor(saved.contextColor ?? DEFAULT_CONTEXT_COLOR); // runs saved before the context control
    setAContext(saved.aContext ?? DEFAULT_CONTEXT_OPACITY);
    // The Design State filter is navigation, not a run setting: restoring a
    // run's stale saved filter jumped the selection to another Design State.
    if (saved.ruleId !== undefined) setRuleId(saved.ruleId);
  }, [runId]);
  // save settings for the active run whenever they change (not on run switch)
  React.useEffect(() => {
    if (!runId) return;
    if (skipGfxSaveRef.current) {
      skipGfxSaveRef.current = false;
      return;
    }
    setRunGfx((prev) => ({
      ...prev,
      [runId]: { mvFail, mvPass, aFail, aPass, failColor, passColor, contextColor, aContext, ruleId }
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mvFail, mvPass, aFail, aPass, failColor, passColor, contextColor, aContext, ruleId]);

  // The thumbnail is filed under the run the scene actually shows (not the run
  // just clicked, whose geometry may still be loading).
  const captureShot = React.useCallback(async () => {
    const api = speckleApiRef.current;
    const shotRunId = api?.sceneRunId?.();
    if (!api || !shotRunId) return;
    try {
      const dataUrl = await api.screenshot();
      if (!dataUrl) return;
      const background = rootRef.current ? getComputedStyle(rootRef.current).backgroundColor : "";
      const thumb = await downscaleThumb(dataUrl, 320, 180, background);
      if (!thumb) return;
      setRunShots((prev) => ({ ...prev, [shotRunId]: thumb }));
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
  }, [project]);

  // One debounced capture for every trigger (scene loaded, graphics change,
  // camera settled), so the progressive render has finished before the shot.
  const shotTimerRef = React.useRef(null);
  const scheduleShot = React.useCallback(() => {
    clearTimeout(shotTimerRef.current);
    shotTimerRef.current = setTimeout(() => void captureShot(), 1200);
  }, [captureShot]);
  React.useEffect(() => () => clearTimeout(shotTimerRef.current), []);

  const load = React.useCallback(async () => {
    setLoadErr(null);
    try {
      const data = await fetchValidationRuns(project);
      const list = data.runs || [];
      setRuns(list);
      // keep the current run only if it still exists under this project scope
      setRunId((prev) => (prev && list.some((r) => r.runId === prev) ? prev : list[0]?.runId || null));
    } catch (err) {
      setLoadErr({ err, fallback: "runs" });
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
      return;
    }
    let gone = false;
    fetchValidationView(project, runId)
      .then((v) => {
        if (gone) return;
        setView(v);
        setSpeckleError(null);
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
      .catch((err) => !gone && setLoadErr({ err, fallback: "view" }));
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

  // AI input candidates: default the generation target to the selected rule
  // and clear any stale candidate set when the architect switches rules.
  // This effect only sets local state — it performs no generation and no
  // acceptance call of any kind (GHIN-04/D-19: those happen only on an
  // explicit button click, never on mount or on rule selection).
  React.useEffect(() => {
    setRuleForGen(ruleId);
    setCandidates(null);
    setGenErr(null);
    // CR-02: candidateId is only unique within one generate-inputs
    // response (c0..cN-1, reused verbatim by the next response) — clear
    // acceptedStates alongside candidates so an unrelated future candidate
    // never inherits a stale "already accepted" badge.
    setAcceptedStates([]);
  }, [ruleId]);

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
  const groups = React.useMemo(() => groupRunsByState(runs), [runs]);

  /* ---- tile properties: this project's PropState properties ---- */
  const propCatalogueList = React.useMemo(() => propCatalogue(groups.map((g) => g.state)), [groups]);
  const tilePropKey = project || "default-project";
  // a project never configured shows its first few properties
  const tileProps = (tilePropSel[tilePropKey] || propCatalogueList.slice(0, DEFAULT_TILE_PROP_COUNT).map((p) => p.iri)).filter(
    (iri) => propCatalogueList.some((p) => p.iri === iri)
  );
  const toggleTileProp = (iri) => {
    const next = tileProps.indexOf(iri) >= 0 ? tileProps.filter((k) => k !== iri) : tileProps.concat([iri]);
    setTilePropSel((prev) => ({ ...prev, [tilePropKey]: next }));
  };

  const visibleRuns = stateKey ? runs.filter((r) => (r.state?.stateId || NO_STATE) === stateKey) : runs;

  /* ---- entities and map items ---- */
  // Phase 1303-25 (D-71): objects without a verdict (objectSets.unknown, e.g. no data) are neither failing nor passing.
  const sets = React.useMemo(() => classifyObjectSets(view?.objectSets), [view]);
  const failedIds = React.useMemo(() => new Set(sets.failedIds), [sets]);
  const failedEntityIdList = sets.failedIds;
  const passedEntityIdList = sets.passedIds;
  const entities = sets.entities;
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
    const open = !fail && sets.statusOf(b.id) === "unknown";
    if ((fail && !mvFail) || (!fail && !mvPass) || hiddenSet.has(b.id) || (isolate && picked !== b.id)) continue;
    const selB = picked === b.id;
    items.push({
      id: b.id,
      d: boxPath(b),
      fill: selB ? "var(--color-signal-soft)" : fail ? "var(--color-signal-soft)" : "transparent",
      stroke: selB ? "var(--color-signal)" : fail ? failColor : open ? NO_VERDICT_COLOR : passColor,
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
        status: fail ? t("FAILING · {rule}", { rule: (ruleId || "").toUpperCase() }) : open ? t("NO VERDICT") : t("PASSING")
      };
    }
  }

  const pick = React.useCallback((id) => {
    setPicked(id);
    setPropMode("instance");
  }, []);

  // Auto-capture: each time the scene finishes loading, and again (debounced)
  // whenever the graphics settings change, refresh the run/state/project
  // thumbnails. Camera moves schedule a shot through onViewChanged.
  React.useEffect(() => {
    if (!sceneTick) return;
    scheduleShot();
  }, [sceneTick, mvFail, mvPass, aFail, aPass, failColor, passColor, viewMode, hidden, isolate, scheduleShot]);

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
      ctx.fillStyle = fail ? failColor : sets.statusOf(b.id) === "unknown" ? NO_VERDICT_COLOR : passColor;
      ctx.fillRect(ox + b.x * sc, oy + (b.y - b.h) * sc, Math.max(2, b.w * sc), Math.max(2, b.h * sc));
    }
    ctx.strokeStyle = failColor;
    ctx.lineWidth = 1;
    ctx.strokeRect(ox + viewBox.x * sc, oy + viewBox.y * sc, viewBox.w * sc, viewBox.h * sc);
  }, [boxes, viewBox, failedIds, sets, failColor, passColor]);

  const onMapClick = (e) => {
    const rect = mapRef.current.getBoundingClientRect();
    const world = worldRef.current;
    const sc = (150 - 10) / Math.max(world.w, world.h);
    const wx = (e.clientX - rect.left - 5) / sc;
    const wy = (e.clientY - rect.top - 5) / sc;
    setViewBox((vb) => ({ ...vb, x: wx - vb.w / 2, y: wy - vb.h / 2 }));
  };

  const { failItems, passItems, unknownItems } = sets;
  const pickedEntity = entities.find((e) => e.dgEntityId === picked);
  const pickedFailing = picked ? failedIds.has(picked) : false;
  const pickedOpen = picked ? sets.statusOf(picked) === "unknown" : false;
  const zoomPct = worldRef.current.w / viewBox.w;

  // The viewer shows only the run's validation model; the base model is never
  // loaded (it was context geometry, often another project's). resolve_view_resources
  // (data-service/speckle_proxy.py) lists the base model's URL first and the
  // validation model's second, skipping a model whose id or version is missing —
  // so the payload's ids say which URL is the validation model.
  const sceneResourceUrls = React.useMemo(() => {
    const all = Array.isArray(view?.viewerResources) ? view.viewerResources.filter(Boolean) : [];
    const hasBase = Boolean(view?.baseModelId && view?.baseVersionId);
    const hasValidation = Boolean(view?.validationModelId && view?.validationVersionId);
    if (!hasValidation) return [];
    return hasBase && all.length === 2 ? all.slice(1) : all.slice(-1);
  }, [view]);
  const handleSpeckleReady = React.useCallback(() => setSceneTick((t) => t + 1), []);
  // The 3D viewpoint is remembered per project, so reopening the Model Viewer
  // (or reloading the page) returns to where the architect left it.
  const savedCamera = project ? readShotStore(CAMERA_KEY)[project] || null : null;
  const handleCameraChange = React.useCallback(
    (cam) => {
      if (!project) return;
      try {
        const all = readShotStore(CAMERA_KEY);
        all[project] = cam;
        localStorage.setItem(CAMERA_KEY, JSON.stringify(all));
      } catch {
        // storage unavailable — the viewpoint lasts only for this session
      }
    },
    [project]
  );
  const handleSpeckleError = React.useCallback((msg) => setSpeckleError(msg), []);

  return (
    <div ref={rootRef} style={{ position: "absolute", inset: 0, display: "flex", background: "var(--color-canvas)" }}>
      {/* ===== left: design states + runs ===== */}
      <div style={{ position: "relative", display: "flex", minWidth: 0, flex: "none", width: panels.widths.left }}>
      <div {...panels.handle("left")} aria-label={t("Resize design states panel")} data-testid="model-states-resize" />
      <aside style={{ width: "100%", minWidth: 0, overflowWrap: "anywhere", flex: "none", boxSizing: "border-box", background: "var(--surface-sidebar)", borderRight: "1px solid var(--color-hairline)", overflow: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingBottom: 12, borderBottom: "1px solid var(--color-hairline)" }}>
          <Button variant="outline" size="sm" onClick={onBack}>
            {t("← Back")}
          </Button>
        </div>
        <div>
          <h3 style={{ margin: 0, font: "400 20px/1.2 var(--font-display)", letterSpacing: "var(--tracking-screen-title)", textTransform: "uppercase" }}>{t("Model Viewer")}</h3>
          <span style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>
            {project || "default-project"}
          </span>
        </div>
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
          <span style={{ font: "500 11px/1.33 var(--font-sans)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>{t("Design States")}</span>
          <Badge variant="outline">{groups.length}</Badge>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9 }}>
              {t("{selected} / {total} props", { selected: tileProps.length, total: propCatalogueList.length })}
            </span>
            <div
              onClick={() => setDsSettingsOpen((v) => !v)}
              title={t("Configure tile properties")}
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
              <div className="dg-frost" style={{ position: "absolute", right: 0, top: 38, zIndex: 15, width: 288, boxSizing: "border-box", borderRadius: "var(--radius-nested)", boxShadow: "var(--shadow-panel)", padding: 12, display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 3, padding: "0 4px 8px", borderBottom: "1px solid var(--color-hairline)" }}>
                  <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>{t("Tile Properties")}</span>
                  <span style={{ font: "400 9px/1.4 var(--font-mono)", color: "var(--text-muted)" }}>{t("PropState values in {project}", { project: tilePropKey })}</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 1, paddingTop: 4 }}>
                  {propCatalogueList.length === 0 && (
                    <span style={{ padding: "6px 4px", font: "400 12px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>
                      {t("No PropState values in this project's design states")}
                    </span>
                  )}
                  {propCatalogueList.map((p) => {
                    const on = tileProps.indexOf(p.iri) >= 0;
                    return (
                      <div
                        key={p.iri}
                        onClick={() => toggleTileProp(p.iri)}
                        style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 4px", borderRadius: 8, cursor: "pointer" }}
                      >
                        <span style={{ width: 15, height: 15, flex: "none", border: `1px solid ${on ? "var(--color-ink)" : "var(--color-hairline)"}`, background: on ? "var(--color-ink)" : "transparent", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center", font: "600 9px/1 var(--font-sans)", color: "var(--surface-card)" }}>
                          {on ? "✓" : ""}
                        </span>
                        <span style={{ flex: 1, minWidth: 0, font: "500 12px/1.3 var(--font-sans)", color: on ? "var(--text-primary)" : "var(--text-muted)" }}>{p.label}</span>
                        <span title={p.iri} style={{ maxWidth: "48%", overflow: "hidden", textOverflow: "ellipsis", font: "400 9px/1.3 var(--font-mono)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>{p.iri}</span>
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
            {describeError(loadErr.err, loadErr.fallback === "runs" ? t("data-service unreachable") : t("Could not load validation run."))}{" "}
            <span onClick={load} style={{ cursor: "pointer", textDecoration: "underline" }}>
              {t("Retry")}
            </span>
          </div>
        )}
        {!loadErr && runs.length === 0 && (
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
            {t("No validation runs · publish from Grasshopper")}
          </div>
        )}
        {groups.map((g) => {
          const on = stateKey === g.key;
          const latest = g.runs[0];
          const fails = g.runs.reduce((s, r) => s + (r.failedRuleCount || 0), 0);
          const rules = g.runs.reduce((s, r) => s + (r.ruleCount || 0), 0);
          // the run on screen first, so the tile follows what was just captured
          const stateThumb =
            (g.runs.some((r) => r.runId === runId) && runShots[runId]) || g.runs.map((r) => runShots[r.runId]).find(Boolean);
          const propRows = propCatalogueList.filter((p) => tileProps.indexOf(p.iri) >= 0).map((entry) => ({
            key: entry.iri,
            label: entry.label,
            value: propSummary(g.state, entry.iri, t)
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
                  {g.key === NO_STATE ? t("No design state") : (g.state?.label || g.key)}
                </span>
                <span style={{ font: "400 9px/1.3 var(--font-annotation)", letterSpacing: "1px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                  {tp("{n} run", g.runs.length)}
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
                  <span style={{ font: "400 10px/1.4 var(--font-annotation)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>{t("Captured")}</span>
                  <span style={{ font: "500 11px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>
                    {g.state?.capturedAtUtc ? String(g.state.capturedAtUtc).slice(0, 16).replace("T", " ") : "—"}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ font: "400 10px/1.4 var(--font-annotation)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>{t("States")}</span>
                  <span style={{ font: "500 11px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>{g.state?.parameterCount ?? "—"}</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingTop: 8, borderTop: "1px solid var(--color-hairline)" }}>
                <span style={{ font: "400 10px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>
                  {latest?.createdAt ? String(latest.createdAt).slice(0, 10) : ""}
                </span>
                <span style={{ font: "500 10px/1.3 var(--font-mono)", color: fails ? "var(--color-signal-ink)" : "var(--text-secondary)" }}>
                  {t("{passed} / {total} pass", { passed: rules - fails, total: rules })}
                </span>
              </div>
            </div>
          );
        })}
      </aside>
      </div>

      {/* ===== centre: toolbar + map + runs strip ===== */}
      <main style={{ flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "10px 16px", background: "var(--surface-card)", borderBottom: "1px solid var(--color-hairline)" }}>
          <Checkbox label={t("Failing")} checked={mvFail} onChange={setMvFail} />
          <Checkbox label={t("Passing")} checked={mvPass} onChange={setMvPass} />
          <span style={{ width: 1, height: 20, background: "var(--color-hairline)" }} />
          <ColorSwatch label={t("Fail")} color={failColor} onChange={setFailColor} />
          <Slider label={t("Fail α")} value={aFail} onChange={setAFail} style={{ width: 210 }} />
          <ColorSwatch label={t("Pass")} color={passColor} onChange={setPassColor} />
          <Slider label={t("Pass α")} value={aPass} onChange={setAPass} style={{ width: 210 }} />
          <ColorSwatch label={t("Context")} color={contextColor} onChange={setContextColor} />
          <Slider label={t("Context α")} value={aContext} onChange={setAContext} style={{ width: 210 }} />
          <span style={{ width: 1, height: 20, background: "var(--color-hairline)" }} />
          <SearchField
            placeholder={t("Select by Id…")}
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
              {speckleError ? t("Retry 3D") : "3D"}
            </Button>
            <Button variant="outline" size="sm" selected={viewMode === "map"} onClick={() => setViewMode("map")}>
              {t("Map")}
            </Button>
          </div>
          <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
            <Button variant="outline" size="sm" selected={isolate} onClick={() => setIsolate((v) => !v)}>
              {t("Isolate")}
            </Button>
            <Button variant="outline" size="sm" onClick={() => picked && setHidden((h) => [...h, picked])}>
              {t("Hide")}
            </Button>
            {hidden.length > 0 && (
              <Button variant="secondary" size="sm" onClick={() => setHidden([])}>
                {t("Show all")}
              </Button>
            )}
          </div>
        </div>

        <div style={{ flex: "1 1 auto", minHeight: 0, display: "flex", position: "relative" }}>
          {!speckleError && sceneResourceUrls.length > 0 ? (
            <SpeckleViewport
              viewMode={viewMode}
              resourceUrls={sceneResourceUrls}
              project={project}
              runId={view?.runId}
              failedEntityIds={failedEntityIdList}
              passedEntityIds={passedEntityIdList}
              showFailed={mvFail}
              showPassed={mvPass}
              failColor={failColor}
              passColor={passColor}
              failOpacity={aFail}
              passOpacity={aPass}
              contextColor={contextColor}
              contextOpacity={aContext}
              hiddenIds={hidden}
              isolateEntityId={isolate && picked ? picked : null}
              onEntityClick={pick}
              onReady={handleSpeckleReady}
              onViewChanged={scheduleShot}
              initialCamera={savedCamera}
              onCameraChange={handleCameraChange}
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
                    <text x={callout.tx} y={callout.ty1} fontFamily="Tektur, sans-serif" fontSize="13" letterSpacing="1.4" fill="var(--color-ink)">
                      {callout.name}
                    </text>
                    <text x={callout.tx} y={callout.ty2} fontFamily="Tektur, sans-serif" fontSize="10" letterSpacing="1.2" fill="var(--color-mid-gray)">
                      {callout.status}
                    </text>
                  </g>
                )}
                {entities.length === 0 && (
                  <text x={viewBox.x + viewBox.w / 2} y={viewBox.y + viewBox.h / 2} textAnchor="middle" fontFamily="Tektur, sans-serif" fontSize="12" letterSpacing="1.4" fill="var(--color-mid-gray)">
                    {runId ? t("NO ENTITIES IN THIS RUN") : t("SELECT A VALIDATION RUN")}
                  </text>
                )}
              </svg>

              {/* minimap — only in map mode */}
              <div style={{ position: "absolute", right: 14, top: 14 }}>
                <div className="dg-frost" style={{ borderRadius: "var(--radius-nested)", padding: 8, boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "0 2px" }}>
                    <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9 }}>
                      {t("Overview")}
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
            <span style={{ font: "500 11px/1.33 var(--font-sans)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)" }}>{t("Validation runs")}</span>
            <Badge variant="outline">{visibleRuns.length}</Badge>
          </div>
          <div style={{ display: "flex", gap: 10, overflowX: "auto" }}>
            {visibleRuns.map((r) => (
              <RunTile
                key={r.runId}
                ruleId={r.ruleIds?.[0] ? r.ruleIds[0] + (r.ruleCount > 1 ? " +" + (r.ruleCount - 1) : "") : r.runId}
                date={r.createdAt ? String(r.createdAt).slice(0, 10) : ""}
                kind={r.failedRuleCount ? tp("{n} failing", r.failedRuleCount) : t("All pass")}
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
      <div style={{ position: "relative", display: "flex", minWidth: 0, flex: "none", width: panels.widths.right }}>
      <div {...panels.handle("right")} aria-label={t("Resize properties panel")} data-testid="model-properties-resize" />
      <aside style={{ width: "100%", minWidth: 0, overflowWrap: "anywhere", flex: "none", boxSizing: "border-box", background: "var(--surface-sidebar)", borderLeft: "1px solid var(--color-hairline)", overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: 12, borderBottom: "1px solid var(--color-hairline)" }}>
          <span style={{ font: "600 15px/1.2 var(--font-sans)", letterSpacing: "-0.2px" }}>{t("Properties")}</span>
          <span style={{ marginLeft: "auto", font: "400 9px/1.3 var(--font-annotation)", letterSpacing: "1.2px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
            {propMode === "run" ? t("Validation run") : t("Geometry instance")}
          </span>
        </div>

        {propMode === "run" && view && (
          <>
            <Panel title={t("Validation run")}>
              <KVRow label={t("Run Id")} value={view.runId} />
              <KVRow label={t("Date Created")} value={view.createdAt ? String(view.createdAt).slice(0, 19).replace("T", " ") : "—"} />
              <KVRow label={t("Base Model")} value={view.baseModelId || "—"} />
              <KVRow label={t("Validation Model")} value={view.validationModelId || "—"} />
              <div style={{ display: "grid", gridTemplateColumns: `repeat(${unknownItems.length > 0 ? 3 : 2}, minmax(0, 1fr))`, gap: 12, marginTop: 10 }}>
                <StatBlock label={t("Failing")} value={String(failItems.length)} signal={failItems.length > 0} />
                <StatBlock label={t("Passing")} value={String(passItems.length)} />
                {unknownItems.length > 0 && <StatBlock label={t("No verdict")} value={String(unknownItems.length)} />}
              </div>
            </Panel>
            {(() => {
              // SHACL Data Integrity — four states keyed on results.length,
              // NEVER on a conforms boolean (allow_infos/allow_warnings means
              // conforms stays true with only info/warning findings). shapeId
              // is present on each finding but must never be rendered here.
              const shaclReport = view.shaclReport;
              if (!shaclReport) {
                return (
                  <Panel title={t("SHACL Data Integrity")}>
                    <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>{t("Not checked")}</div>
                    <div style={{ font: "400 11px/1.3 var(--font-sans)", color: "var(--text-muted)", marginTop: 2 }}>
                      {t("This run predates SHACL validation.")}
                    </div>
                  </Panel>
                );
              }
              if (shaclReport.status === "unavailable" || shaclReport.status === "timeout") {
                return (
                  <Panel title={t("SHACL Data Integrity")}>
                    <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>{t("Not evaluated")}</div>
                    <div style={{ font: "400 11px/1.3 var(--font-sans)", color: "var(--text-muted)", marginTop: 2 }}>
                      {shaclReport.status === "timeout"
                        ? t("SHACL validation timed out when this run published.")
                        : t("SHACL validator was unreachable when this run published.")}
                    </div>
                  </Panel>
                );
              }
              const shaclResults = shaclReport.results || [];
              if (shaclResults.length === 0) {
                return (
                  <Panel title={t("SHACL Data Integrity")}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                      <span style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--color-ink)" }}>{t("Conforms")}</span>
                    </div>
                    <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)", marginTop: 4 }}>
                      {t("No data-integrity issues found in this run.")}
                    </div>
                  </Panel>
                );
              }
              const bySeverity = { violation: [], warning: [], info: [] };
              shaclResults.forEach((f) => {
                (bySeverity[f.severity] || bySeverity.violation).push(f);
              });
              const chipDefs = [
                { severity: "violation", variant: "violation", singular: t("Violation"), plural: t("Violations") },
                { severity: "warning", variant: "warning", singular: t("Warning"), plural: t("Warnings") },
                { severity: "info", variant: "info", singular: t("Info"), plural: t("Info") }
              ];
              const chips = chipDefs
                .map((d) => ({ ...d, n: bySeverity[d.severity].length }))
                .filter((d) => d.n > 0);
              const findingCard = (f, i, isLast) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    padding: "8px 12px",
                    borderBottom: isLast ? "none" : "1px solid var(--color-hairline)"
                  }}
                >
                  <span style={{ font: "500 12px/1.3 var(--font-mono)", color: "var(--color-ink)" }}>{f.focusLabel || "—"}</span>
                  <span style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-secondary)" }}>{f.what || "—"}</span>
                  <span style={{ font: "400 11px/1.3 var(--font-sans)", color: "var(--text-muted)" }}>{t("Where: {value}", { value: f.where || "—" })}</span>
                  <span style={{ font: "400 11px/1.3 var(--font-sans)", color: "var(--text-muted)" }}>{t("Fix: {value}", { value: f.howToFix || "—" })}</span>
                </div>
              );
              const severityGroup = (label, tone, items, open, setOpen) =>
                items.length > 0 && (
                  <Collapsible key={label} label={label} tone={tone} count={items.length} open={open} onToggle={() => setOpen((v) => !v)}>
                    {items.map((f, i) => findingCard(f, i, i === items.length - 1))}
                  </Collapsible>
                );
              return (
                <Panel title={t("SHACL Data Integrity")}>
                  <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    {chips.map((c, i) => (
                      <React.Fragment key={c.severity}>
                        {i > 0 && <span style={{ font: "400 12px/1 var(--font-sans)", color: "var(--text-muted)" }}>·</span>}
                        <Badge variant={c.variant}>
                          {c.n} {c.n === 1 ? c.singular : c.plural}
                        </Badge>
                      </React.Fragment>
                    ))}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
                    {severityGroup(t("Violations"), "violation", bySeverity.violation, shaclViolationOpen, setShaclViolationOpen)}
                    {severityGroup(t("Warnings"), "warning", bySeverity.warning, shaclWarningOpen, setShaclWarningOpen)}
                    {severityGroup(t("Info"), "info", bySeverity.info, shaclInfoOpen, setShaclInfoOpen)}
                  </div>
                </Panel>
              );
            })()}
            <Collapsible label={t("Failing items")} count={failItems.length} signal={failItems.length > 0} open={failOpen} onToggle={() => setFailOpen((v) => !v)}>
              {failItems.map((it) => (
                <CollapsibleItem key={it.id} primary={it.primary} secondary={it.secondary} selected={picked === it.id} onClick={() => pick(it.id)} />
              ))}
            </Collapsible>
            <Collapsible label={t("Passing items")} count={passItems.length} open={passOpen} onToggle={() => setPassOpen((v) => !v)}>
              {passItems.map((it) => (
                <CollapsibleItem key={it.id} primary={it.primary} secondary={it.secondary} selected={picked === it.id} onClick={() => pick(it.id)} />
              ))}
            </Collapsible>
            {unknownItems.length > 0 && (
              <Collapsible label={t("Items without a verdict")} count={unknownItems.length} open={unknownOpen} onToggle={() => setUnknownOpen((v) => !v)}>
                {unknownItems.map((it) => (
                  <CollapsibleItem key={it.id} primary={it.primary} secondary={it.secondary} selected={picked === it.id} onClick={() => pick(it.id)} />
                ))}
              </Collapsible>
            )}
            <Panel title={t("Rule")}>
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
              <KVRow label={t("Name")} value={rule?.name || "—"} mono={false} />
              <KVRow label={t("Description")} value={rule?.description || "—"} mono={false} />
              <div style={{ marginTop: 10 }}>
                <CodeBlock label={t("SWRL Expression")}>{rule?.swrl || "—"}</CodeBlock>
              </div>
            </Panel>

            {/* AI input candidates (D-20, GHIN-04): a panel on this existing
                Model screen, reusing Panel/Badge/Callout/Button/Input only —
                not a new screen, not the Graph screen. Generation and
                acceptance are strictly separated: generateInputs runs only
                on the Generate button click below, and acceptCandidate runs
                only inside CandidateTable's onAccept click handler further
                down — neither is ever called from an effect, on mount, or
                on rule selection (SC3). Rejecting a candidate is a local
                dismissal only (D-19) — CandidateTable issues no request for
                it. */}
            <Panel title={t("AI input candidates")}>
              {!ruleId && (
                <div style={{ font: "400 13px/1.4 var(--font-sans)", color: "var(--text-muted)" }}>
                  {t("Select a rule first to generate candidate inputs for it.")}
                </div>
              )}
              {ruleId && (
                <>
                  <KVRow label={t("Target rule")} value={ruleForGen || ruleId} />
                  <div style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 8, flexWrap: "wrap" }}>
                    <Input
                      label={t("Candidate count (1–8)")}
                      type="number"
                      min={1}
                      max={8}
                      value={candidateCount}
                      onChange={(e) => {
                        const n = Math.round(Number(e.target.value));
                        const clamped = Number.isFinite(n) ? Math.max(1, Math.min(8, n)) : 4;
                        setCandidateCount(clamped);
                      }}
                      style={{ width: 110 }}
                    />
                    <Input
                      label={t("Parameter overrides (optional, comma-separated)")}
                      value={paramOverrides}
                      onChange={(e) => setParamOverrides(e.target.value)}
                      style={{ minWidth: 240 }}
                    />
                    <Button
                      size="sm"
                      disabled={genBusy}
                      onClick={async () => {
                        setGenErr(null);
                        setGenBusy(true);
                        // CR-02: a fresh response reuses the same c0..cN-1
                        // candidateId values as any prior response — reset
                        // acceptedStates so a new, never-accepted candidate
                        // never renders as falsely already-accepted.
                        setAcceptedStates([]);
                        try {
                          const overridesArr = paramOverrides
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean);
                          const result = await generateInputs(
                            project,
                            null,
                            ruleForGen || ruleId,
                            candidateCount,
                            overridesArr
                          );
                          setCandidates(result);
                        } catch (err) {
                          setGenErr(err);
                        } finally {
                          setGenBusy(false);
                        }
                      }}
                    >
                      {genBusy ? t("Generating…") : t("Generate")}
                    </Button>
                  </div>
                  {genErr && (
                    <div style={{ font: "400 12px/1.4 var(--font-sans)", color: "var(--color-signal-ink)", marginTop: 8 }}>
                      {describeError(genErr, t("Candidate request failed."))}
                    </div>
                  )}
                  {candidates && (
                    <div style={{ marginTop: 12 }}>
                      <CandidateTable
                        candidates={candidates.candidates}
                        boundParameters={candidates.boundParameters}
                        determinabilityClass={candidates.determinabilityClass}
                        ruleLimit={candidates.ruleLimit}
                        acceptedStateIds={acceptedStates.map((a) => a.candidateId)}
                        busyCandidateId={busyCandidateId}
                        onAccept={async (candidate) => {
                          // The only call site of acceptCandidate in this file
                          // — inside this click-triggered handler, never in
                          // an effect (GHIN-04/D-19/SC3).
                          setBusyCandidateId(candidate.candidateId);
                          setGenErr(null);
                          try {
                            const res = await acceptCandidate(
                              project,
                              candidates.definitionId,
                              candidates.ruleId,
                              candidate
                            );
                            setAcceptedStates((prev) =>
                              prev.concat([{ candidateId: candidate.candidateId, stateId: res.stateId }])
                            );
                            // Refresh from the graph so the panel reflects
                            // what was actually persisted, not only local
                            // optimism.
                            await fetchAcceptedCandidates(project, candidates.ruleId).catch(() => null);
                          } catch (err) {
                            setGenErr(err);
                          } finally {
                            setBusyCandidateId(null);
                          }
                        }}
                        onReject={(candidate) => {
                          // Local dismissal only — issues no request (D-19).
                          setCandidates((prev) =>
                            prev
                              ? { ...prev, candidates: prev.candidates.filter((c) => c.candidateId !== candidate.candidateId) }
                              : prev
                          );
                        }}
                      />
                    </div>
                  )}
                </>
              )}
            </Panel>
          </>
        )}
        {propMode === "run" && !view && (
          <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
            {runs.length ? t("Loading run…") : t("No validation run selected")}
          </div>
        )}

        {propMode === "instance" && (
          <>
            <div
              onClick={() => setPropMode("run")}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, alignSelf: "flex-start", cursor: "pointer", font: "500 11px/1.2 var(--font-annotation)", letterSpacing: "1px", textTransform: "uppercase", color: "var(--text-muted)" }}
            >
              {t("← Validation run")}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Chip selected>{pickedFailing ? t("Failing") : pickedOpen ? t("No verdict") : t("Passing")}</Chip>
              <span style={{ font: "500 13px/1.3 var(--font-mono)", letterSpacing: "-0.2px" }}>{picked}</span>
            </div>
            <Panel title={t("Instance properties")}>
              <KVRow label={t("Id")} value={picked || "—"} />
              <KVRow label={t("Display name")} value={pickedEntity?.displayName || picked || "—"} />
              <KVRow label={t("Source model")} value={view?.source?.model || "—"} />
              <KVRow label={t("Platform")} value={view?.source?.platform || "—"} />
              <KVRow label={t("Id in model")} value={(picked && view?.nativeIds?.[picked]) || "—"} />
              <KVRow label={t("Run")} value={view?.runId || "—"} />
            </Panel>
            <Panel title={t("Validation")}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8, paddingBottom: 8, borderBottom: "1px solid var(--color-hairline)" }}>
                <span style={{ font: "400 12px/1.3 var(--font-sans)", color: "var(--text-muted)" }}>{t("Status")}</span>
                <span style={{ font: "600 12px/1.3 var(--font-mono)", color: pickedFailing ? "var(--color-signal)" : "var(--text-secondary)" }}>
                  {pickedFailing ? t("FAIL") : pickedOpen ? t("NO VERDICT") : t("PASS")}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 1, marginTop: 6 }}>
                {pickedStatuses.map((r) => (
                  <div key={r.ruleId} style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8, padding: "5px 0" }}>
                    <span style={{ font: "400 12px/1.3 var(--font-mono)", color: "var(--text-secondary)" }}>{r.ruleId}</span>
                    <span style={{ font: "500 11px/1.3 var(--font-mono)", color: r.status === "failed" ? "var(--color-signal)" : "var(--text-secondary)" }}>
                      {validationStatusLabel(r.status)}
                    </span>
                  </div>
                ))}
                {pickedStatuses.length === 0 && (
                  <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9, paddingTop: 6 }}>
                    {t("No per-rule records")}
                  </span>
                )}
              </div>
            </Panel>
          </>
        )}
      </aside>
      </div>
    </div>
  );
}
