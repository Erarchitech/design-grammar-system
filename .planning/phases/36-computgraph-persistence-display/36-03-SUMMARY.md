---
phase: 36-computgraph-persistence-display
plan: 03
subsystem: ui-v2
tags:
  - computgraph
  - ui-wiring
  - display-layer
  - display-only
requires:
  - Phase 36 UI-SPEC (locked binding contract)
  - buildRings.js existing layer table structure
  - GraphScreen.jsx existing rowsOf mapper
provides:
  - Fixes "Computgraph" casing parity with graph property value
  - Computgraph layer orbit routing (7 labels / 3 orbits)
  - Display property captions for 6 of 7 labels
  - 200-char value truncation guard for large node properties
affects:
  - ui-v2/src/graph/buildRings.js
  - ui-v2/src/screens/GraphScreen.jsx
tech-stack:
  added: []
  patterns:
    - buildRings.js LAYER_ORDER / ORBITS / CAPTIONS table-driven layer wiring
    - Single-function rowsOf guard pattern (one point of change for both hover and detail panels)
key-files:
  created: []
  modified:
    - ui-v2/src/graph/buildRings.js
    - ui-v2/src/screens/GraphScreen.jsx
decisions:
  - Behavior node intentionally excluded from CAPTIONS — falls through to captionOf() generic fallback, renders literal "Behavior" string
  - No new accent color for Computgraph layer — renders in TH.ink/TH.dim monochrome like all others
  - Truncation guard lives in rowsOf (single function), not in PropertiesTable component — keeps the guard generic without component changes
  - No "view full JSON" modal or copy button added this phase — truncation alone satisfies "panel does not break"
metrics:
  duration: null
  completed_date: 2026-07-19
status: complete
---

# Phase 36 Plan 03: ui-v2 Computgraph Layer Display

Wired the 7 Computgraph labels into the ui-v2 orbital datascape's buildRings.js tables and added a 200-character truncation guard to the GraphScreen.jsx properties panel. Two production files edited, Vite build clean.

## Task Execution

### Task 1: buildRings.js — Computgraph layer key, orbits, captions

**Files modified:** `ui-v2/src/graph/buildRings.js`
**Commit:** `6ccebd1`

Three atomic changes to the existing layer table files:

1. **LAYER_ORDER casing fix** (line 8): Changed `"ComputGraph"` to `"Computgraph"` — the exact casing required to match the `graph:'Computgraph'` property that CGPD-01 persists. Without this fix, Computgraph nodes would fall through the `ia<0?99:ia` catch-all sort and render as an unlabeled misplaced layer after ValidGraph.

2. **ORBITS replacement** (line 17): Removed the stale placeholder `ComputGraph: { Pattern: 0, Parameter: 1, Interface: 2 }` and replaced it with the full 7-label / 3-orbit map:
   - Orbit 0 (identity chain): `Object, Behavior, Algorithm`
   - Orbit 1 (structural decomposition): `Procedure, Pattern`
   - Orbit 2 (leaf entities): `Parameter, Interface`

3. **CAPTIONS entries** (lines 45-52): Added 6 display-property mappings:
   - `Object → ["objectName"]`
   - `Algorithm → ["algorithmName"]`
   - `Procedure → ["procedureName"]`
   - `Pattern → ["patternName"]`
   - `Parameter → ["parameterName"]`
   - `Interface → ["interfaceName"]`
   
   `Behavior` intentionally has no caption entry — it falls through to the existing `captionOf()` generic fallback (`props.label || props.name || props.id || label`) and renders the literal string `"Behavior"`.

**Verification:** `node -e` grep gate: confirmed no stale `ComputGraph` casing, `Computgraph` key present, all 6 caption property name strings present.

### Task 2: GraphScreen.jsx — rowsOf 200-char truncation guard

**Files modified:** `ui-v2/src/screens/GraphScreen.jsx`
**Commit:** `ee907c9`

Single-line change inside the existing `rowsOf` function (line 690): any property value whose string length exceeds 200 characters now renders as `String(p[1]).slice(0, 200) + "…"`. Both call sites (`rowsOf(hv, 6)` for the hover panel and `rowsOf(se, 24)` for the detail panel) inherit this guard automatically since they share the same function.

This prevents a multi-KB `contextJson` property on `Algorithm` nodes from breaking the frosted detail panel's `70vh` height constraint.

**Verification:** `npm --prefix ui-v2 run build` — Vite production build completed successfully (947 modules transformed, ✓ built in 7.66s, no errors).

## Deviations from Plan

None — plan executed exactly as written.

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The threat model (T-36-06 information disclosure, mitigated by React text escaping and the 200-char truncation guard; T-36-07 tampering on inline-edit of provenance fields, accepted per UI-SPEC) is unchanged.

## Self-Check: PASSED

- File check: `ui-v2/src/graph/buildRings.js` — exists, verified by grep gate
- File check: `ui-v2/src/screens/GraphScreen.jsx` — exists, verified by Vite build
- Commit check: `6ccebd1` — verified via `git log`
- Commit check: `ee907c9` — verified via `git log`
