// Colours of the mapping view of a model snapshot (Phase 1303-26, D-82). Classes mode: every OntoGraph class of the
// view has its own colour, and a class keeps its colour from load to load (its iri picks a palette slot; a clash
// within the view moves to the next free slot). Status mode: the five mapping states in the shared D-50 palette
// (MappingPanel tokens, Revit connector palette.STATE_COLOURS). Legend rows hide and show their elements.

import { MAPPING_STATES } from "./mappingApi.js";

export const STATE_COLOURS = Object.freeze({
  confirmed: "#2E7D32",
  auto: "#1565C0",
  suggested: "#F9A825",
  ambiguous: "#E65100",
  unmapped: "#9E9E9E"
});

// Distinguishable colours that are none of the state colours and not the fail red (#E7000B).
export const CLASS_PALETTE = Object.freeze([
  "#4E79A7", "#F28E2B", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1",
  "#FF9DA7", "#9C755F", "#17BECF", "#BCBD22", "#7F3C8D", "#E377C2"
]);

export const NO_CLASS = "__no_class__";

function hashOf(text) {
  let h = 5381;
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
  return h >>> 0;
}

function hslHex(h, s, l) {
  const a = s * Math.min(l, 1 - l);
  const f = (n) => {
    const k = (n + h / 30) % 12;
    const c = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(c * 255).toString(16).padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`.toUpperCase();
}

// iri -> colour for the classes of one view; distinct within the view.
export function classColours(iris) {
  const sorted = [...new Set((iris || []).filter(Boolean))].sort();
  const n = CLASS_PALETTE.length;
  const used = new Set();
  const out = new Map();
  let extra = 0;
  for (const iri of sorted) {
    if (used.size >= n) {
      out.set(iri, hslHex((hashOf(iri) % 360 + extra * 137.508) % 360, 0.55, 0.5));
      extra += 1;
      continue;
    }
    let slot = hashOf(iri) % n;
    while (used.has(slot)) slot = (slot + 1) % n;
    used.add(slot);
    out.set(iri, CLASS_PALETTE[slot]);
  }
  return out;
}

const classKeys = (element) => (element.classIris || []).length ? [...element.classIris] : [NO_CLASS];

export function elementColour(element, mode, colours) {
  if (mode === "status") return STATE_COLOURS[element.state] || STATE_COLOURS.unmapped;
  const first = [...(element.classIris || [])].sort()[0];
  return (first && colours.get(first)) || STATE_COLOURS.unmapped;
}

function elementHidden(element, mode, hidden) {
  if (mode === "status") return hidden.has(element.state || "unmapped");
  return classKeys(element).every((key) => hidden.has(key));
}

// Legend rows of a mode: classes by count (largest first, then label), the no-class row last; or the five states.
export function legendRows(elements, mode, colours, hidden) {
  const off = hidden || new Set();
  if (mode === "status") {
    const counts = Object.fromEntries(MAPPING_STATES.map((s) => [s, 0]));
    for (const e of elements || []) counts[e.state in counts ? e.state : "unmapped"] += 1;
    return MAPPING_STATES.map((s) => ({ key: s, label: s, colour: STATE_COLOURS[s], count: counts[s], hidden: off.has(s) }));
  }
  const rows = new Map();
  let none = 0;
  for (const e of elements || []) {
    const iris = e.classIris || [];
    if (iris.length === 0) none += 1;
    iris.forEach((iri, k) => {
      const row = rows.get(iri) || { key: iri, label: (e.classLabels || [])[k] || iri, colour: colours.get(iri), count: 0 };
      row.count += 1;
      rows.set(iri, row);
    });
  }
  const out = [...rows.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  if (none > 0) out.push({ key: NO_CLASS, label: "", colour: STATE_COLOURS.unmapped, count: none });
  return out.map((r) => ({ ...r, hidden: off.has(r.key) }));
}

// What the viewport draws: colour groups of the visible elements and the UniqueIds of the hidden ones.
export function viewGroups(elements, mode, colours, hidden) {
  const off = hidden || new Set();
  const byColour = new Map();
  const hiddenNativeIds = [];
  for (const e of elements || []) {
    if (elementHidden(e, mode, off)) {
      hiddenNativeIds.push(e.nativeId);
      continue;
    }
    const colour = elementColour(e, mode, colours);
    if (!byColour.has(colour)) byColour.set(colour, []);
    byColour.get(colour).push(e.nativeId);
  }
  return { colorGroups: [...byColour.entries()].map(([color, nativeIds]) => ({ color, nativeIds })), hiddenNativeIds };
}
