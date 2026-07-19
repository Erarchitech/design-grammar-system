// Maps the live Neo4j graph onto the datascape's orbital model:
// one ring layer per `graph` property value, three orbits per layer
// grouped by node label. Same-layer relationships become ring edges;
// relationships spanning layers become labelled cross edges.

// Fixed layer order (mockup order); only layers present in the data render.
// KnowledgeGraph is pre-v7 data that may coexist with SpecGraph.
const LAYER_ORDER = ["OntoGraph", "Metagraph", "KnowledgeGraph", "SpecGraph", "Computgraph", "ValidGraph"];

// Orbit assignment per layer: label → orbit index. Unlisted labels fall to
// the outer orbit. Orbit display names derive from the labels actually seen.
const ORBITS = {
  OntoGraph: { Class: 0, ObjectProperty: 1, DatatypeProperty: 2 },
  Metagraph: { Rule: 0, Atom: 1, Var: 2, Literal: 2, Builtin: 2 },
  KnowledgeGraph: { KnowledgeClass: 0, KnowledgeNote: 1, KnowledgeTag: 2, KnowledgeSession: 2 },
  SpecGraph: { SpecClass: 0, SpecNote: 1, SpecTag: 2, SpecSession: 2 },
  Computgraph: { Object: 0, Behavior: 0, Algorithm: 0, Procedure: 1, Pattern: 1, Parameter: 2, Interface: 2 },
  ValidGraph: { ValidationRun: 0, Run: 0, DesignState: 1, ValidationEntity: 2, IntegrationConfig: 2 }
};

// Display caption per label (from the legacy viewer's config.template.js).
const CAPTIONS = {
  Rule: ["Rule_Id"],
  Atom: ["SWRL_label", "Atom_Id"],
  Class: ["label"],
  DatatypeProperty: ["SWRL_label", "label"],
  ObjectProperty: ["label"],
  Builtin: ["label"],
  Var: ["name"],
  Literal: ["lex"],
  DesignState: ["StateId"],
  Run: ["Run_Id", "runId"],
  ValidationRun: ["runId"],
  ValidationEntity: ["displayName", "dgEntityId", "objRefName"],
  IntegrationConfig: ["project"],
  KnowledgeClass: ["label", "name"],
  KnowledgeNote: ["title"],
  KnowledgeTag: ["name"],
  KnowledgeSession: ["mode"],
  DesignRuleSession: ["mode", "id"],
  SpecNote: ["title"],
  SpecTag: ["name"],
  SpecSession: ["mode"],
  SpecClass: ["label"],
  Object: ["objectName"],
  Behavior: ["definitionId"],
  Algorithm: ["algorithmName"],
  Procedure: ["procedureName"],
  Pattern: ["patternName"],
  Parameter: ["parameterName"],
  Interface: ["interfaceName"]
};

const TAU = 6.283185307;

function primaryLabel(labels) {
  return labels.find((l) => CAPTIONS[l]) || labels[0] || "Node";
}

function captionOf(label, props) {
  for (const key of CAPTIONS[label] || []) {
    if (props[key] != null && props[key] !== "") return String(props[key]);
  }
  return props.label || props.name || props.id || label;
}

export default function buildRings({ nodes, rels }) {
  // group nodes by layer (graph property; untagged nodes are skipped —
  // they are orphans pending the post-ingest tagging pass)
  const byLayer = new Map();
  const nodeInfo = new Map(); // neo4j id → {layerKey, ...}
  for (const n of nodes) {
    const layer = n.props.graph;
    if (!layer) continue;
    if (!byLayer.has(layer)) byLayer.set(layer, []);
    byLayer.get(layer).push(n);
  }

  const layerKeys = [...byLayer.keys()].sort((a, b) => {
    const ia = LAYER_ORDER.indexOf(a),
      ib = LAYER_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });

  const rings = layerKeys.map((layerKey, g) => {
    const orbitMap = ORBITS[layerKey] || {};
    const raw = byLayer.get(layerKey);
    const buckets = [[], [], []];
    const orbitLabels = [new Set(), new Set(), new Set()];
    for (const n of raw) {
      const label = primaryLabel(n.labels);
      const o = orbitMap[label] != null ? orbitMap[label] : 2;
      buckets[o].push({ neoId: n.id, kind: label, label: captionOf(label, n.props), props: Object.entries(n.props) });
      orbitLabels[o].add(label);
    }
    // deterministic order within an orbit → stable angles across reloads
    buckets.forEach((arr) => arr.sort((a, b) => a.label.localeCompare(b.label)));
    let nodesFlat = [];
    const ob = [];
    buckets.forEach((arr, o) => {
      const start = nodesFlat.length;
      arr.forEach((n) => {
        n.orbit = o;
      });
      nodesFlat = nodesFlat.concat(arr);
      ob.push([start, nodesFlat.length]);
    });
    nodesFlat.forEach((n, i) => {
      n.ring = g;
      n.idx = i;
      n.deg = 0;
      nodeInfo.set(n.neoId, { g, i });
    });
    ob.forEach((rng, o) => {
      const c = Math.max(1, rng[1] - rng[0]);
      for (let i = rng[0]; i < rng[1]; i++) nodesFlat[i].ang = ((i - rng[0]) / c) * TAU + o * 0.26;
    });
    const orbits = orbitLabels.map((s, o) => ([...s].join(" / ") || ["Core", "Mid", "Outer"][o]));
    return { key: layerKey, name: layerKey, orbits, nodes: nodesFlat, edges: [], ob };
  });

  // relationships → ring edges / cross edges
  const cross = [];
  const xmap = {};
  const seen = new Set();
  for (const r of rels) {
    const a = nodeInfo.get(r.source),
      b = nodeInfo.get(r.target);
    if (!a || !b) continue;
    if (a.g === b.g) {
      if (a.i === b.i) continue;
      const key = a.g + ":" + (a.i < b.i ? a.i + "_" + b.i : b.i + "_" + a.i);
      if (seen.has(key)) continue;
      seen.add(key);
      const rg = rings[a.g];
      rg.edges.push([a.i, b.i, r.type]);
      rg.nodes[a.i].deg++;
      rg.nodes[b.i].deg++;
    } else {
      cross.push({ r1: a.g, i1: a.i, r2: b.g, i2: b.i, label: r.type });
      (xmap[a.g + ":" + a.i] = xmap[a.g + ":" + a.i] || []).push({ r: b.g, i: b.i, label: r.type });
      (xmap[b.g + ":" + b.i] = xmap[b.g + ":" + b.i] || []).push({ r: a.g, i: a.i, label: r.type });
      rings[a.g].nodes[a.i].deg++;
      rings[b.g].nodes[b.i].deg++;
    }
  }
  const xPerRing = rings.map(() => 0);
  cross.forEach((x) => {
    xPerRing[x.r1]++;
    xPerRing[x.r2]++;
  });

  return { rings, cross, xmap, xPerRing };
}
