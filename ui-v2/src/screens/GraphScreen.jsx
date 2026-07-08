import React from "react";
import ScreenHeader from "../shell/ScreenHeader.jsx";
import GraphEngine from "../graph/graphEngine.js";
import buildRings from "../graph/buildRings.js";
import { fetchGraph, ingestRules, queryGraph, tagProjectNodes, getConfig, fetchDrSessions, saveDrSession } from "../lib/graphApi.js";
import {
  Badge,
  Button,
  Chip,
  Collapsible,
  Input,
  Progress,
  PropertiesTable,
  SearchField,
  Select,
  Tabs
} from "../components/index.js";

const MODES = ["Ingest", "Query"];
const STEPS = {
  0: ["Parsing intent", "Reasoning over ontology", "Encoding SWRL / Cypher", "Committing to metagraph"],
  1: ["Parsing query", "Traversing graph", "Ranking matches"]
};

const frost = (extra) => ({
  borderRadius: "var(--radius-nested)",
  padding: 8,
  boxShadow: "var(--shadow-panel)",
  display: "flex",
  flexDirection: "column",
  gap: 1,
  flex: "none",
  ...extra
});

// Extract the nodes a rule-ingest Cypher statement creates, so the session
// turn can list them (rule first, then atoms, vars, literals, builtins).
const NODE_DISPLAY_KEYS = ["Rule_Id", "SWRL_label", "Atom_Id", "label", "name", "lex", "iri"];
const NODE_ORDER = { Rule: 0, Atom: 1, Var: 2, Literal: 3, Builtin: 4 };
function parseCreatedNodes(cypher) {
  if (!cypher) return [];
  const nodes = [];
  const seen = new Set();
  const re = /(?:CREATE|MERGE)\s*\(\s*[\w`]*\s*:\s*`?(\w+)`?\s*(\{[^}]*\})?/gi;
  let m;
  while ((m = re.exec(cypher))) {
    const label = m[1];
    const propsText = m[2] || "";
    let display = "";
    for (const key of NODE_DISPLAY_KEYS) {
      const pm = propsText.match(new RegExp(key + "\\s*:\\s*(?:'([^']*)'|\"([^\"]*)\")"));
      if (pm) {
        display = pm[1] ?? pm[2] ?? "";
        if (display) break;
      }
    }
    const id = label + "·" + display;
    if (seen.has(id)) continue;
    seen.add(id);
    nodes.push({ label, display });
  }
  nodes.sort((a, b) => (NODE_ORDER[a.label] ?? 9) - (NODE_ORDER[b.label] ?? 9));
  return nodes;
}

function clockNow() {
  try {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

// The live Neo4j datascape: ring layers from the project metagraph, node
// selection with divergence callout + details panel, n8n prompt console,
// and node search (right-click popover + persistent property-scoped bar).
export default function GraphScreen({ active, onBack, project }) {
  const canvasRef = React.useRef(null);
  const mapRef = React.useRef(null);
  const zoomRef = React.useRef(null);
  const hoverPanelRef = React.useRef(null);
  const selPanelRef = React.useRef(null);
  const searchPopRef = React.useRef(null);
  const sessionScrollRef = React.useRef(null);
  const engineRef = React.useRef(null);

  const [data, setData] = React.useState(null); // {rings, cross, ...}
  const [loadErr, setLoadErr] = React.useState("");
  const [type, setType] = React.useState(0);
  const [sel, setSel] = React.useState(null); // {r, i}
  const [selBig, setSelBig] = React.useState(false);
  const [hover, setHover] = React.useState(null);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [searchProp, setSearchProp] = React.useState("*");
  const [filterOn, setFilterOn] = React.useState(false);
  const [filterQ, setFilterQ] = React.useState("");
  const [matchCount, setMatchCount] = React.useState(0);
  const [matchList, setMatchList] = React.useState([]);
  const [mode, setMode] = React.useState(0);
  const [promptVal, setPromptVal] = React.useState("");
  const [session, setSession] = React.useState([]);
  const [sessionOpen, setSessionOpen] = React.useState(false);
  const [busy, setBusy] = React.useState(false);

  const cfg = React.useMemo(() => getConfig(), []);

  const loadGraph = React.useCallback(async () => {
    setLoadErr("");
    try {
      const raw = await fetchGraph(project);
      const built = buildRings(raw);
      setData(built);
      if (engineRef.current) engineRef.current.setData(built);
    } catch (err) {
      setLoadErr(err.message || "Could not reach Neo4j.");
    }
  }, [project]);

  // engine lifecycle
  React.useEffect(() => {
    const engine = new GraphEngine(
      {
        canvas: canvasRef.current,
        map: mapRef.current,
        zoomLabel: zoomRef.current,
        hoverPanel: hoverPanelRef.current,
        selPanel: selPanelRef.current
      },
      {
        onHover: (hit) => setHover(hit),
        onSelect: (hit, big) => {
          setSel(hit);
          setSelBig(big);
          setHover(null);
          setSearchOpen(false);
          setType(hit.r);
        },
        onClearSel: () => {
          setSel(null);
          setSelBig(false);
        },
        onTypeChange: (i) => {
          setType(i);
          setSel(null);
          setSelBig(false);
          setFilterOn(false);
          setFilterQ("");
          setQ("");
          setSearchProp("*");
        },
        onContextSearch: (x, y) => {
          const sp = searchPopRef.current;
          if (sp) {
            sp.style.left = Math.min(x, window.innerWidth - 420) + "px";
            sp.style.top = Math.min(y, window.innerHeight - 70) + "px";
          }
          setSearchOpen(true);
          setHover(null);
          setTimeout(() => {
            const inp = sp && sp.querySelector("input");
            if (inp) inp.focus();
          }, 80);
        },
        onCloseSearch: () => setSearchOpen(false)
      }
    );
    engineRef.current = engine;
    if (import.meta.env.DEV) window.__dgg = engine;
    engine.start();
    return () => engine.stop();
  }, []);

  React.useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  React.useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    if (active) engine.setVisible(true);
    else {
      const t = setTimeout(() => engine.setVisible(false), 620);
      return () => clearTimeout(t);
    }
  }, [active]);

  React.useEffect(() => {
    const engine = engineRef.current;
    if (engine) engine.searchOpen = searchOpen;
  }, [searchOpen]);

  // Escape precedence while this screen is active: close search → clear
  // selection → (unhandled) App returns to landing. Capture phase so this
  // runs before the App-level bubble listener.
  React.useEffect(() => {
    if (!active) return;
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      if (searchOpen) {
        setSearchOpen(false);
        e.stopPropagation();
      } else if (sel) {
        engineRef.current?.clearSel();
        e.stopPropagation();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [active, searchOpen, sel]);

  // search matching → engine live/filter sets + popover result list
  React.useEffect(() => {
    const engine = engineRef.current;
    if (!engine || !data) return;
    const rings = data.rings;
    if (!q) {
      engine.liveSet = null;
      if (!filterOn) engine.filterSet = null;
      setMatchCount(0);
      setMatchList([]);
      return;
    }
    const m = engine.computeMatches(q, type, searchProp);
    engine.liveSet = m;
    if (filterOn) engine.filterSet = m;
    setMatchCount(m.size);
    setMatchList(
      [...m].slice(0, 8).map((i) => ({ i, label: rings[type]?.nodes[i]?.label || "" }))
    );
  }, [q, searchProp, type, filterOn, data]);

  const jumpTo = (i) => {
    engineRef.current?.selectNode(type, i, false);
    setSearchOpen(false);
  };

  const clearFilter = () => {
    setFilterOn(false);
    setFilterQ("");
    setQ("");
    const engine = engineRef.current;
    if (engine) {
      engine.filterSet = null;
      engine.liveSet = null;
    }
  };

  /* -------- session history (data-service DesignRuleSession nodes) -------- */
  React.useEffect(() => {
    let gone = false;
    setSession([]);
    fetchDrSessions(project)
      .then((rows) => {
        if (gone) return;
        // API returns newest-first; the console renders oldest-first
        const hist = rows
          .slice()
          .reverse()
          .map((s) => {
            const result = s.result || "";
            const ix = result.indexOf("\n\n// Cypher\n");
            const cypher = ix >= 0 ? result.slice(ix + 12) : "";
            return {
              id: s.sessionId,
              modeLabel: s.mode === "query" ? "Query" : s.mode === "edit" ? "Edit" : "Ingest",
              text: s.prompt || "",
              steps: [],
              progress: 100,
              status: "done",
              response: ix >= 0 ? result.slice(0, ix) : result,
              cypher,
              createdNodes: parseCreatedNodes(cypher),
              cypherOpen: false,
              meta: "History · " + String(s.createdAt || "").slice(0, 10),
              clock: String(s.createdAt || "").slice(11, 19),
              history: true
            };
          });
        if (hist.length) setSession(hist);
      })
      .catch(() => {
        // data-service unreachable — console starts empty, live turns still work
      });
    return () => {
      gone = true;
    };
  }, [project]);

  /* -------- prompt console (rules-ingest / graph-query webhooks) -------- */
  const patchTurn = (id, patch) =>
    setSession((s) => s.map((t) => (t.id !== id ? t : { ...t, ...(typeof patch === "function" ? patch(t) : patch) })));

  const autoScroll = () =>
    requestAnimationFrame(() => {
      const el = sessionScrollRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });

  const sendPrompt = async () => {
    const txt = promptVal.trim();
    if (!txt || busy) return;
    const id = "t" + Date.now();
    const steps = STEPS[mode];
    setSession((s) =>
      s.concat([
        {
          id,
          modeLabel: MODES[mode],
          text: txt,
          steps: steps.map((l) => ({ label: l, active: false, time: "" })),
          progress: 5,
          status: "processing",
          response: "",
          meta: "",
          clock: ""
        }
      ])
    );
    setSessionOpen(true);
    setPromptVal("");
    setBusy(true);
    autoScroll();

    // advance the step display while the workflow runs (capped at the last step)
    let step = 0;
    const t0 = Date.now();
    const timer = setInterval(() => {
      if (step < steps.length - 1) step++;
      patchTurn(id, (t) => ({
        progress: Math.min(90, Math.round(((step + 0.5) / steps.length) * 100)),
        steps: t.steps.map((x, i) => ({
          ...x,
          active: i === step,
          time: i < step ? x.time || ((Date.now() - t0) / 1000 / steps.length).toFixed(1) + "s" : x.time
        }))
      }));
    }, 1400);

    try {
      const payload =
        mode === 0 ? await ingestRules(txt, project) : await queryGraph(txt, project);
      clearInterval(timer);
      const secs = ((Date.now() - t0) / 1000).toFixed(1);
      let response, meta, cypher = "", createdNodes = [];
      if (mode === 0) {
        cypher = Array.isArray(payload.cypher) ? payload.cypher.join("\n\n") : payload.cypher || "";
        createdNodes = parseCreatedNodes(cypher);
        response = "Rule ingested into the metagraph.";
        meta = "Committed → Metagraph · " + secs + "s";
        await tagProjectNodes(project); // legacy-parity post-ingest project claim
        await loadGraph(); // the datascape reflects the new rule
      } else {
        response = payload.answer || payload.response || "(empty answer)";
        meta = "Query · " + (project || "all projects") + " · " + secs + "s";
      }
      patchTurn(id, (t) => ({
        status: "done",
        progress: 100,
        steps: t.steps.map((x) => ({ ...x, active: false, time: x.time || "·" })),
        response,
        cypher,
        createdNodes,
        cypherOpen: false,
        meta,
        clock: clockNow()
      }));
      // persist the turn so it survives reloads (legacy saveDrSession parity)
      void saveDrSession(
        project,
        mode === 0 ? "ingest" : "query",
        txt,
        response + (cypher ? "\n\n// Cypher\n" + cypher : "")
      );
    } catch (err) {
      clearInterval(timer);
      patchTurn(id, (t) => ({
        status: "done",
        progress: 100,
        steps: t.steps.map((x) => ({ ...x, active: false })),
        response: "ERROR — " + (err.message || "workflow failed"),
        meta: "Failed",
        clock: clockNow()
      }));
    } finally {
      setBusy(false);
      autoScroll();
    }
  };

  /* -------- derived render data -------- */
  const rings = data?.rings || [];
  const ringN = rings[type] || null;
  const nodeOf = (h) => (h && rings[h.r] ? rings[h.r].nodes[h.i] : null);
  const hv = nodeOf(hover);
  const se = nodeOf(sel);
  const rowsOf = (n, max) => (n ? n.props.slice(0, max).map((p) => ({ key: p[0], value: String(p[1]) })) : []);
  const conns = [];
  if (se && sel) {
    for (const e of rings[sel.r].edges) {
      const j = e[0] === sel.i ? e[1] : e[1] === sel.i ? e[0] : -1;
      if (j >= 0) conns.push({ label: rings[sel.r].nodes[j].label, ring: rings[sel.r].name, r: sel.r, i: j });
    }
    for (const p of data.xmap[sel.r + ":" + sel.i] || []) {
      conns.push({ label: rings[p.r].nodes[p.i].label, ring: rings[p.r].name, r: p.r, i: p.i });
    }
  }
  const searchProps = ringN
    ? [{ value: "*", label: "Any field" }, { value: "__label", label: "Label" }].concat(
        [...new Set([].concat(...ringN.nodes.map((n) => n.props.map((p) => p[0]))))].map((k) => ({ value: k, label: k }))
      )
    : [{ value: "*", label: "Any field" }];

  return (
    <div style={{ position: "absolute", inset: 0, background: "var(--color-canvas)" }}>
      <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", touchAction: "none" }} />

      <ScreenHeader title="Graph Viewer" subtitle={`${project || "All projects"} · ${cfg.neo4jUri || "bolt://neo4j:7687"}`} onBack={onBack} />

      {loadErr && (
        <div
          className="dg-annotation dg-annotation--muted"
          style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", fontSize: 11, display: "flex", flexDirection: "column", alignItems: "center", gap: 12, zIndex: 4 }}
        >
          <span style={{ color: "var(--color-signal)" }}>Graph unavailable · {loadErr}</span>
          <Button variant="outline" size="sm" onClick={loadGraph}>
            Retry
          </Button>
        </div>
      )}
      {!loadErr && data && rings.length === 0 && (
        <div className="dg-annotation dg-annotation--muted" style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", fontSize: 11, zIndex: 4 }}>
          No graph data · ingest a rule to begin
        </div>
      )}

      {filterOn && (
        <div style={{ position: "absolute", left: "50%", top: 24, transform: "translateX(-50%)", zIndex: 5 }}>
          <Chip selected onRemove={clearFilter}>
            {(searchProp === "*" ? "any" : searchProp === "__label" ? "label" : searchProp) + ' ~ "' + filterQ + '" · ' + matchCount + " nodes"}
          </Chip>
        </div>
      )}

      {/* left column: layers + orbit legend */}
      {rings.length > 0 && (
        <div style={{ position: "absolute", left: 20, top: 94, zIndex: 5, width: 224, display: "flex", flexDirection: "column", gap: 10, maxHeight: "calc(100vh - 132px)", overflow: "auto" }}>
          <div className="dg-frost" style={frost()}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", padding: "2px 6px 6px" }}>
              <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
                Graph Layers
              </span>
              <span style={{ font: "400 9px/1.3 var(--font-annotation)", letterSpacing: "1.2px", textTransform: "uppercase", color: "var(--text-muted)" }}>
                Grouped · {rings.length}×3
              </span>
            </div>
            {rings.map((rg, r) => {
              const on = r === type;
              return (
                <div
                  key={rg.key}
                  onClick={() => engineRef.current?.setType(r)}
                  style={{ display: "flex", alignItems: "center", gap: 9, padding: 6, borderRadius: 8, cursor: "pointer" }}
                >
                  <span style={{ width: 12, textAlign: "right", font: "500 10px/1.4 var(--font-mono)", color: on ? "var(--color-signal)" : "var(--text-muted)" }}>
                    {r + 1}
                  </span>
                  <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 1 }}>
                    <span style={{ fontSize: 12, letterSpacing: "0.2px", color: on ? "var(--color-ink)" : "var(--text-muted)", fontWeight: on ? 600 : 400, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {rg.name}
                    </span>
                    <span style={{ font: "400 10px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>
                      {rg.nodes.length + " nodes" + (on ? " · " + (rg.edges.length + (data.xPerRing[r] || 0)) + " edges" : "")}
                    </span>
                    {on && (
                      <span style={{ font: "400 9px/1.4 var(--font-annotation)", letterSpacing: "0.6px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {rg.orbits.join(" · ")}
                      </span>
                    )}
                  </div>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", flex: "none", background: on ? "var(--color-signal)" : "transparent" }} />
                </div>
              );
            })}
            <div style={{ marginTop: 5, padding: "7px 6px 2px", borderTop: "1px solid var(--color-hairline)" }}>
              <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 9.5, lineHeight: 1.5 }}>
                Drag to rotate · click to align · double-click to inspect · right-click to search
              </div>
            </div>
          </div>

          {ringN && (
            <div className="dg-frost" style={frost()}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", padding: "2px 6px 6px" }}>
                <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10 }}>
                  Orbits
                </span>
                <span style={{ font: "400 9px/1.3 var(--font-annotation)", letterSpacing: "1.2px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 118 }}>
                  {ringN.name}
                </span>
              </div>
              {ringN.orbits.map((nm, o) => {
                const rng = ringN.ob[o] || [0, 0];
                const on = (k) => (k === o ? "var(--color-signal)" : "var(--ink-a16)");
                return (
                  <div key={o} style={{ display: "flex", alignItems: "center", gap: 11, padding: "5px 6px" }}>
                    <span style={{ position: "relative", width: 24, height: 24, flex: "none" }}>
                      <span style={{ position: "absolute", left: "50%", top: "50%", width: 22, height: 22, margin: "-11px 0 0 -11px", borderRadius: "50%", border: `1.5px solid ${on(2)}` }} />
                      <span style={{ position: "absolute", left: "50%", top: "50%", width: 13, height: 13, margin: "-6.5px 0 0 -6.5px", borderRadius: "50%", border: `1.5px solid ${on(1)}` }} />
                      <span style={{ position: "absolute", left: "50%", top: "50%", width: 5, height: 5, margin: "-2.5px 0 0 -2.5px", borderRadius: "50%", background: on(0) }} />
                    </span>
                    <span style={{ display: "flex", flexDirection: "column", gap: 1, minWidth: 0 }}>
                      <span style={{ font: "600 11px/1.3 var(--font-sans)", letterSpacing: "0.1px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{nm}</span>
                      <span style={{ font: "400 9px/1.4 var(--font-annotation)", letterSpacing: "0.8px", textTransform: "uppercase", color: "var(--text-muted)" }}>
                        {rng[1] - rng[0]} nodes
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* hover panel (engine-positioned) */}
      <div ref={hoverPanelRef} style={{ position: "absolute", left: 0, top: 0, width: 280, zIndex: 6, opacity: 0, pointerEvents: "none", transition: "opacity 140ms" }}>
        {hv && (
          <div className="dg-frost" style={{ borderRadius: "var(--radius-nested)", padding: 12, boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Chip>{hv.kind}</Chip>
              <span style={{ font: "500 12px/1.3 var(--font-mono)" }}>{hv.label}</span>
            </div>
            <PropertiesTable rows={rowsOf(hv, 6)} editable={false} />
          </div>
        )}
      </div>

      {/* selection detail panel (engine-positioned, double-click) */}
      <div ref={selPanelRef} style={{ position: "absolute", left: 0, top: 0, width: 360, zIndex: 7, opacity: 0, pointerEvents: "none", transition: "opacity 160ms" }}>
        {se && selBig && (
          <div className="dg-frost" style={{ borderRadius: "var(--radius-cards)", padding: 18, boxShadow: "var(--shadow-panel)", height: "70vh", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 12, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <Chip selected>{se.kind}</Chip>
              <div onClick={() => engineRef.current?.clearSel()} style={{ cursor: "pointer", fontSize: 15, color: "var(--text-muted)", lineHeight: 1, padding: 4 }}>
                ✕
              </div>
            </div>
            <div style={{ font: "500 15px/1.3 var(--font-mono)", letterSpacing: "-0.2px" }}>{se.label}</div>
            <div style={{ flex: "1 1 auto", overflow: "auto", minHeight: 0, display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                  Properties
                </div>
                <PropertiesTable rows={rowsOf(se, 24)} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div className="dg-annotation dg-annotation--muted" style={{ fontSize: 11 }}>
                  Edges · {conns.length}
                </div>
                {conns.map((c, k) => (
                  <div
                    key={k}
                    onClick={() => engineRef.current?.selectNode(c.r, c.i, true)}
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, padding: "7px 4px", borderBottom: "1px solid var(--color-hairline)", cursor: "pointer" }}
                  >
                    <span style={{ font: "400 12px/1.3 var(--font-mono)" }}>{c.label}</span>
                    <span style={{ font: "400 11px/1.3 var(--font-sans)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>{c.ring}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* right-click search popover with jump-to results */}
      <div ref={searchPopRef} style={{ position: "absolute", left: 0, top: 0, zIndex: 8 }}>
        {searchOpen && (
          <div className="dg-frost" style={{ borderRadius: "var(--radius-nested)", padding: 6, boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", gap: 6, width: 330 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <SearchField
                placeholder={"Search " + (ringN ? ringN.name : "") + "…"}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && matchList.length) jumpTo(matchList[0].i);
                }}
                style={{ flex: 1 }}
              />
              <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10, whiteSpace: "nowrap" }}>
                {q ? matchCount + " MATCH" + (matchCount === 1 ? "" : "ES") : "TYPE TO SEARCH"}
              </span>
            </div>
            {matchList.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", maxHeight: 220, overflow: "auto" }}>
                {matchList.map((m) => (
                  <div
                    key={m.i}
                    onClick={() => jumpTo(m.i)}
                    style={{ padding: "7px 8px", font: "400 12px/1.3 var(--font-mono)", cursor: "pointer", borderBottom: "1px solid var(--color-hairline)" }}
                  >
                    {m.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* bottom: session + prompt bar + property search */}
      <div style={{ position: "absolute", left: "50%", bottom: 22, transform: "translateX(-50%)", zIndex: 6, display: "flex", alignItems: "flex-end", gap: 12, maxWidth: "96vw" }}>
        <div style={{ width: "min(560px, 56vw)", display: "flex", flexDirection: "column", alignItems: "stretch", gap: 8 }}>
          {sessionOpen && (
            <div className="dg-frost" style={{ width: "100%", boxSizing: "border-box", borderRadius: "var(--radius-nested)", boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderBottom: "1px solid var(--color-hairline)" }}>
                <span style={{ font: "500 10px/1 var(--font-annotation)", letterSpacing: "1.4px", textTransform: "uppercase", color: "var(--text-muted)" }}>Session</span>
                <Badge variant="outline">{session.length}</Badge>
                <span style={{ flex: 1 }} />
                <span
                  onClick={() => setSession([])}
                  style={{ cursor: "pointer", font: "400 10px/1 var(--font-annotation)", letterSpacing: "1.1px", textTransform: "uppercase", color: "var(--text-muted)", padding: "3px 5px" }}
                >
                  Clear
                </span>
                <div onClick={() => setSessionOpen(false)} title="Collapse session" style={{ cursor: "pointer", width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 6, color: "var(--text-secondary)" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </div>
              </div>
              <div ref={sessionScrollRef} style={{ maxHeight: "min(46vh, 340px)", overflowY: "auto", display: "flex", flexDirection: "column" }}>
                {session.map((turn) => (
                  <div key={turn.id} style={{ padding: "11px 12px", borderBottom: "1px solid var(--color-hairline)", display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <span style={{ flex: "none", font: "500 9px/1.5 var(--font-annotation)", letterSpacing: "1px", textTransform: "uppercase", color: "var(--text-secondary)", border: "1px solid var(--color-hairline)", borderRadius: 5, padding: "2px 6px" }}>
                        {turn.modeLabel}
                      </span>
                      <span style={{ flex: 1, font: "400 12px/1.5 var(--font-mono)", overflowWrap: "anywhere" }}>{turn.text}</span>
                    </div>
                    {turn.status === "processing" && <Progress value={turn.progress} steps={turn.steps} />}
                    {turn.status === "done" && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingLeft: 10, borderLeft: "2px solid var(--color-hairline)" }}>
                        <span style={{ font: "500 9px/1 var(--font-annotation)", letterSpacing: "1.2px", textTransform: "uppercase", color: "var(--text-muted)" }}>Response</span>
                        <pre style={{ margin: 0, font: "400 11px/1.6 var(--font-mono)", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{turn.response}</pre>
                        {turn.createdNodes && turn.createdNodes.length > 0 && (
                          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                            <span style={{ font: "500 9px/1 var(--font-annotation)", letterSpacing: "1.2px", textTransform: "uppercase", color: "var(--text-muted)" }}>
                              Created nodes · {turn.createdNodes.length}
                            </span>
                            {turn.createdNodes.map((n, k) => (
                              <div key={k} style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                                <span style={{ flex: "none", font: "500 9px/1.5 var(--font-annotation)", letterSpacing: "0.8px", textTransform: "uppercase", color: n.label === "Rule" ? "var(--color-signal-ink)" : "var(--text-secondary)", border: "1px solid var(--color-hairline)", borderRadius: 5, padding: "1px 6px", minWidth: 44, textAlign: "center" }}>
                                  {n.label}
                                </span>
                                <span style={{ font: "400 11px/1.5 var(--font-mono)", overflowWrap: "anywhere" }}>{n.display || "—"}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {turn.cypher && (
                          <Collapsible
                            label="Cypher"
                            open={!!turn.cypherOpen}
                            onToggle={() => patchTurn(turn.id, (t) => ({ cypherOpen: !t.cypherOpen }))}
                          >
                            <pre style={{ margin: 0, padding: "8px 12px", font: "400 10.5px/1.6 var(--font-mono)", whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 220, overflowY: "auto" }}>
                              {turn.cypher}
                            </pre>
                          </Collapsible>
                        )}
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, paddingTop: 2 }}>
                          <span style={{ font: "500 9px/1 var(--font-annotation)", letterSpacing: "1px", textTransform: "uppercase", color: "var(--color-signal)" }}>{turn.meta}</span>
                          <span style={{ font: "400 10px/1 var(--font-mono)", color: "var(--text-muted)" }}>{turn.clock}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="dg-frost" style={{ width: "100%", boxSizing: "border-box", borderRadius: "var(--radius-buttons)", padding: 6, boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0 2px" }}>
              <Tabs tabs={MODES} active={mode} onChange={setMode} style={{ height: 30, width: 170, flex: "none" }} />
              <span style={{ flex: 1, minWidth: 0, textAlign: "right", font: "500 9px/1.3 var(--font-annotation)", letterSpacing: "1.1px", textTransform: "uppercase", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {ringN ? ringN.name + " · text" : "No data"}
              </span>
              {!sessionOpen && session.length > 0 && (
                <div onClick={() => setSessionOpen(true)} title="Show session" style={{ cursor: "pointer", width: 24, height: 24, flex: "none", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 6, color: "var(--text-secondary)" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m18 15-6-6-6 6" />
                  </svg>
                </div>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Input
                mono
                placeholder={mode === 0 ? "Encode a design rule…" : "Ask the graph a question…"}
                value={promptVal}
                onChange={(e) => setPromptVal(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") sendPrompt();
                }}
                style={{ flex: "1 1 auto", minWidth: 60 }}
              />
              <Button size="sm" onClick={sendPrompt} disabled={busy}>
                {mode === 0 ? "Ingest" : "Query"}
              </Button>
            </div>
          </div>
        </div>

        <div className="dg-frost" style={{ boxSizing: "border-box", borderRadius: "var(--radius-buttons)", padding: 6, boxShadow: "var(--shadow-panel)", display: "flex", alignItems: "center", gap: 6, flex: "none" }}>
          <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9, paddingLeft: 4, whiteSpace: "nowrap" }}>
            Search by
          </span>
          <Select
            value={searchProp}
            options={searchProps}
            onChange={(e) => {
              setSearchProp(e.target.value);
              setFilterOn(!!q);
              setFilterQ(q);
            }}
            style={{ height: 32, width: 136, fontSize: 12, padding: "0 30px 0 12px" }}
          />
          <SearchField
            placeholder={"filter by " + (searchProp === "*" ? "any field" : searchProp === "__label" ? "label" : searchProp) + "…"}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setFilterOn(!!e.target.value);
              setFilterQ(e.target.value);
            }}
            style={{ width: 184 }}
          />
          <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 10, whiteSpace: "nowrap", minWidth: 48, textAlign: "right", paddingRight: 4 }}>
            {q ? matchCount + " / " + (ringN ? ringN.nodes.length : 0) : ""}
          </span>
        </div>
      </div>

      {/* minimap */}
      {rings.length > 0 && (
        <div style={{ position: "absolute", right: 20, top: 64, zIndex: 6 }}>
          <div className="dg-frost" style={{ borderRadius: "var(--radius-nested)", padding: 8, boxShadow: "var(--shadow-panel)", display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "0 2px" }}>
              <span className="dg-annotation dg-annotation--muted" style={{ fontSize: 9 }}>
                Overview
              </span>
              <span ref={zoomRef} style={{ font: "500 9px/1.3 var(--font-mono)", color: "var(--text-muted)" }}>
                1.0×
              </span>
            </div>
            <canvas ref={mapRef} width="150" height="150" style={{ width: 150, height: 150, display: "block", borderRadius: 6, cursor: "crosshair" }} />
          </div>
        </div>
      )}
    </div>
  );
}
