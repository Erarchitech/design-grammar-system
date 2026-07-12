---
phase: 810-ring-extension-and-screen-shell
plan: "810-01"
subsystem: ui-v2
tags: [landing, particle-ring, screens, navigation]
requires: []
provides:
  - "Ring anchors + callouts for aiengine/connectors/reasoner/apidocs"
  - "Skeletal screens: AiEngineScreen, ConnectorsScreen, ReasonerScreen, ApiDocsScreen"
  - "App.jsx Layer registration for the four new regions"
affects: [811, 813, 814, 815]
tech-stack:
  added: []
  patterns: ["engine-owned styling (classes in JSX, per-frame styles in engine)", "ProjectsScreen chrome pattern for skeleton screens"]
key-files:
  created:
    - ui-v2/src/screens/AiEngineScreen.jsx
    - ui-v2/src/screens/ConnectorsScreen.jsx
    - ui-v2/src/screens/ReasonerScreen.jsx
    - ui-v2/src/screens/ApiDocsScreen.jsx
  modified:
    - ui-v2/src/landing/landingEngine.js
    - ui-v2/src/landing/LandingLayer.jsx
    - ui-v2/src/App.jsx
decisions:
  - "Ring angles: aiengine -pi*0.45 (top, slightly right), connectors pi*0.30 (lower-right), reasoner -pi*0.78 (top-left), apidocs pi*0.86 (left, below center) — free arcs between the three primary anchors"
  - "New peaks use amp 0.60-0.68 / sig 0.20-0.24 so they read as secondary to graph/model/projects"
metrics:
  duration: "~6 min"
  completed: "2026-07-11"
status: complete
---

# Phase 810 Plan 01: Ring Extension & Screen Shell Summary

Four new setup-region callouts (AI Engine, Connectors, Reasoner, DG API Docs) on the landing particle ring, each flying into its own skeletal screen layer with standard 520ms transition and back navigation.

## What Changed

### Task 1 — Engine anchors (commit a495d87)
- `ANCH` in `landingEngine.js` extended with `aiengine` (-π·0.45), `connectors` (π·0.30), `reasoner` (-π·0.78), `apidocs` (π·0.86); amp 0.60–0.68, sig 0.20–0.24 (secondary to the three primaries)
- `layoutLanding()` cfg map extended with the four regions (`out: 54`), so leader lines, `pk[key]` fly-origins, and label transforms are produced for all 7 callouts
- `setNavLabels()` now iterates `Object.values(labels)` generically plus the hint

### Task 2 — LandingLayer callouts (commit e66e4fe)
- Four new refs + `.dgl-region-label` divs (`AI Engine`, `Connectors`, `Reasoner`, `DG API Docs`), each `onClick={() => fly("<key>")}`
- Refs passed to the engine in the `labels` record; no React style props on engine-managed elements (classes only, per the engine-owned styling contract)

### Task 3 — Skeleton screens + App layers (commit 81edb7d)
- `AiEngineScreen.jsx`, `ConnectorsScreen.jsx`, `ReasonerScreen.jsx`, `ApiDocsScreen.jsx`: full-viewport container, ProjectsScreen-style chrome header with `← Back`, `dg-annotation` region eyebrow, screen title, `dg-frost` placeholder card with one-sentence purpose
- `App.jsx`: four new `<Layer>` entries keyed `aiengine` / `connectors` / `reasoner` / `apidocs` per the fixed contract, props `active` / `onBack` / `project`
- Escape-to-landing verified: the handler is generic on `region !== "landing"` so it covers the new regions with no change

## Fixed contract compliance

- Region keys: `aiengine`, `connectors`, `reasoner`, `apidocs` — exact
- Screen files: `AiEngineScreen.jsx`, `ConnectorsScreen.jsx`, `ReasonerScreen.jsx`, `ApiDocsScreen.jsx` — exact
- Label texts: `AI Engine`, `Connectors`, `Reasoner`, `DG API Docs` — exact

## Verification

- `npm --prefix ui-v2 run build` — passed (`✓ built in 4.89s`; pre-existing >500 kB chunk warning only, unrelated)
- Dev-server visual check: not run (optional per execution constraints); angle choices computed to keep all 7 labels clear of the hero (center, vh·0.44), hint (bottom center), and each other — left-side labels stack at y ≈ cy−0.64R (reasoner), cy−0.19R (graph), cy+0.43R (apidocs), cy+0.93R (projects); right side at cy−0.99R (aiengine), cy−0.20R (model), cy+0.81R (connectors)
- Existing regions untouched: graph/model/projects anchors, hero, and auth code paths unchanged

## Deviations from Plan

None — plan executed as written. (Three per-task commits were made instead of the suggested one-or-two; each is atomic and scoped to its task.)

## Known Stubs

The four screens are intentionally skeletal placeholder cards — this is the plan's stated deliverable; phases 811/813/814/815 fill them.

## Self-Check: PASSED

- ui-v2/src/screens/AiEngineScreen.jsx — FOUND
- ui-v2/src/screens/ConnectorsScreen.jsx — FOUND
- ui-v2/src/screens/ReasonerScreen.jsx — FOUND
- ui-v2/src/screens/ApiDocsScreen.jsx — FOUND
- Commits a495d87, e66e4fe, 81edb7d — FOUND
