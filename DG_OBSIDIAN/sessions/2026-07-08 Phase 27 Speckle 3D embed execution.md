---
tags: [session]
date: 2026-07-08
---

# Phase 27: Speckle 3D Embed — Execution

**Model:** deepseek-v4-flash (orchestrator), sonnet (executor/verifier/reviewer)
**Date:** 2026-07-08
**Changed files:** 7 (4 UI source + 3 planning artifacts)

## What was done

Executed Phase 27 (Speckle 3D Embed) — 1 plan, wave 1/1, via `/gsd-execute-phase 27`.

### Task 1: SpeckleViewport component
- Created `ui-v2/src/components/speckle/SpeckleViewport.jsx` — React wrapper around `@speckle/viewer` Viewer
- Added `@speckle/viewer@^2.31.14` to `ui-v2/package.json`
- Full viewer lifecycle: create on resource change → dispose on unmount/run change
- Entity mapping: world tree walk for `dgEntityId` → Speckle objectId
- Click handler: routes Speckle object click to `onEntityClick(dgEntityId)`
- ResizeObserver for responsive canvas

### Task 2: ModelScreen integration
- Modified `ui-v2/src/screens/ModelScreen.jsx` — 3D/Map toggle in toolbar
- Conditional rendering: SpeckleViewport (3D mode) or SVG map (Map mode)
- Entity click wiring: Speckle click → `pick(id)` → Properties sidebar instance mode
- Auto-fallback to SVG map on initialization error
- SVG map code preserved verbatim

### Code review (standard depth)
**7 findings:**
- **CR-01** (critical): Inline callbacks in `useEffect` dep array → viewer re-created on every render → FIXED: store callbacks in refs
- **WR-01** (warning): Race window during async `initViewer()` → FIXED: `.catch()` chain
- **WR-02** (warning): No retry after 3D init failure → FIXED: `retry3d()` + "Retry 3D" button
- **WR-03** (warning): Missing `fetch*` functions in dep arrays → FIXED: added to deps
- 3 info findings (keyboard a11y, component size, effect separation)

### Verification
- **PASSED** — 6/6 must-haves verified
- MVIEW3D-01 (3D viewport): ✓
- MVIEW3D-02 (validation colors): ✓ (server-side)
- MVIEW3D-03 (SVG map fallback): ✓
- Build passes (931 modules, 5.40s)
- 217/219 tests pass (2 pre-existing E2E failures requiring live Neo4j)

### Commits

```
fe70510 feat(27-speckle-3d-embed): create SpeckleViewport component
5dc6bf6 feat(27-speckle-3d-embed): integrate SpeckleViewport into ModelScreen
13c678b docs(27-speckle-3d-embed): complete 27-01 plan
d2f14a1 docs(27): add code review report
223e7e1 docs(27): add verification report
30ebd17 docs(27): complete phase 27
a84bd40 fix(27): CR-01 stabilize callback refs
f71ca08 fix(27): WR-01 add init catch chain
c38d589 fix(27): WR-02 add retry mechanism
abe2378 fix(27): WR-03 add fetch functions to deps
c4faaee docs(27): add code review fix report
```

## Results

- Phase 27 complete — 1/1 plans, all 3 requirements satisfied
- Speckle 3D viewer now embedded in V2 ModelScreen as the primary viewport
- SVG map preserved as toggle fallback (3D/Map toggle in toolbar)
- Entity click in either mode opens instance mode in Properties sidebar
- All 4 code review fixes applied (all Critical + Warning resolved)

## Next steps

- Verify Phase 27 in live Docker: rebuild `design-grammars` container with `--no-cache`, reload http://localhost:8080, select `v8-ui-smoke` project, check that Speckle renders geometry
- v8.0 now fully complete with all phases (21-27) done
- Next: v4.0 BOT Ontology Bridge or resume v9.0 Phase 01 UAT
