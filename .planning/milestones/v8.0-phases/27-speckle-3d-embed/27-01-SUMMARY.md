---
phase: 27-speckle-3d-embed
plan: "27-01"
subsystem: "V2 UI Model Viewer"
tags:
  - speckle
  - viewer
  - 3d
  - model-viewer
  - v2-ui
requires:
  - "27-CONTEXT.md"
provides:
  - "SpeckleViewport React component"
  - "3D/Map toggle in ModelScreen"
affects:
  - ui-v2/package.json
  - ui-v2/src/screens/ModelScreen.jsx
  - ui-v2/src/components/speckle/SpeckleViewport.jsx
tech-stack:
  added:
    - "@speckle/viewer@^2.28.0"
  patterns:
    - React controlled wrapper around imperative `@speckle/viewer` Viewer API
    - collectValidationObjects entity mapping (3-tier search: project+run, project-only, run-only)
    - Speckle world tree walk for dgEntityId discovery
    - Viewer lifecycle: create on resource change, dispose on unmount/run change
    - ResizeObserver for responsive canvas
key-files:
  created:
    - ui-v2/src/components/speckle/SpeckleViewport.jsx
  modified:
    - ui-v2/package.json
    - ui-v2/package-lock.json
    - ui-v2/src/screens/ModelScreen.jsx
decisions:
  - "D-01: Use @speckle/viewer npm package directly (not iframe)"
  - "D-02: Viewer instance created per run, disposed on run change/unmount"
  - "D-03: Read token from view payload, not UI env vars"
  - "D-04: No FilteringExtension — server-side coloring via Speckle publish"
  - "D-05: Speckle object click routes to same pick(id) as SVG map"
  - "D-06: 3D/Map toggle in toolbar; auto-fallback to map on error"
metrics:
  duration: "~18m"
  completed_date: "2026-07-08"
status: complete
---

# Phase 27 Plan 01: Speckle 3D Embed — Summary

Embed a Speckle 3D viewer into the V2 ModelScreen, replacing the synthetic SVG isometric boxes with real BIM geometry rendered by the `@speckle/viewer` library, while preserving the SVG map as a toggle fallback.

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-01 | Use `@speckle/viewer` npm package directly | Native React integration enables event handling and avoids iframe complexity |
| D-02 | Viewer created per run, disposed on change | Camera resets per run; no stale selection state |
| D-03 | Read token from view payload | Token circulates server-to-SPA via data-service; not in UI env vars |
| D-04 | No client-side FilteringExtension | Server-side publish pipeline already colors geometry (Signal Red fail, ink pass) |
| D-05 | Speckle click -> pick(id) | Consistent entity selection flow in both 3D and Map modes |
| D-06 | 3D/Map toggle + auto-fallback | Degraded gracefully: missing resource URLs or init errors switch to SVG map |

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | `npm ls @speckle/viewer` | `@speckle/viewer@2.31.14` installed |
| 2 | `grep import SpeckleViewport` | 1 match (import present) |
| 3 | `grep viewMode` | 5 matches (state declaration + 4 usages) |
| 4 | `grep boxPath\|hashOf\|layoutEntities` | 6 matches (SVG code preserved) |
| 5 | `npm run build` | Build succeeds (931 modules, 4.54s) |

## Threat Flags

None. The threat register items T-27-01 (read token in view payload) and T-27-02 (npm dependency) follow the same patterns as the legacy model-viewer.

## Self-Check: PASSED

All created files exist, all commits exist.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `fe70510` | Create SpeckleViewport component and add @speckle/viewer dependency |
| 2 | `5dc6bf6` | Integrate SpeckleViewport into ModelScreen with 3D/Map toggle |
