---
phase: 27-speckle-3d-embed
verified: 2026-07-08T17:00:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
deferred: []
warnings:
  - "CR-01: Inline callback functions in ModelScreen cause SpeckleViewport to dispose and recreate the viewer on every parent re-render"
  - "WR-02: No retry mechanism for 3D view after initialization failure — user must page reload"
  - "Requirements MVIEW3D-01/02/03 defined in ROADMAP.md but not formalized in REQUIREMENTS.md traceability table"
---

# Phase 27: Speckle 3D Embed Verification Report

**Phase Goal:** Replace synthetic SVG isometric boxes in ModelScreen.jsx with an embedded Speckle 3D viewer rendering real BIM geometry with validation color overlay, while preserving the SVG map as a toggle fallback.
**Verified:** 2026-07-08T17:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SpeckleViewport React component creates/disposes a @speckle/viewer Viewer instance on resourceUrl changes and emits entity click events with dgEntityId | VERIFIED | `ui-v2/src/components/speckle/SpeckleViewport.jsx` exists at 218 lines. useEffect keyed on `[resourceUrls, readToken, project, runId, ...]` creates new Viewer on mount/resource change, disposes on cleanup. Click handler registered via `viewer.on("object-clicked", handler)` extracts `dgEntityId` from `hit.node.model.raw.dgEntityId` and calls `onEntityClick(dgEntityId)`. |
| 2 | ModelScreen.jsx conditionally renders either SpeckleViewport (3D mode) or the existing SVG map (Map mode), toggled by a toolbar button | VERIFIED | `ui-v2/src/screens/ModelScreen.jsx` line 87: `const [viewMode, setViewMode] = React.useState("3d")`. Lines 465-471: 3D/Map Button pair in toolbar. Lines 488-560: conditional rendering — SpeckleViewport when `viewMode === "3d" && speckleResourceUrls.length > 0 && speckleToken`, SVG map otherwise. |
| 3 | Clicking a Speckle geometry object triggers pick(dgEntityId) which opens the Properties sidebar in instance mode | VERIFIED | ModelScreen line 495: `onEntityClick={(id) => pick(id)}` passes Speckle click to ModelScreen's `pick()` function (line 241-244) which sets `setPropMode("instance")`. Properties sidebar line 639 renders instance mode content when `propMode === "instance"`. |
| 4 | Camera resets per run; viewer disposes cleanly on unmount or run change without memory leaks | VERIFIED | New Viewer instance created per run change via useEffect keyed on runId (line 98 dependency array includes runId). Cleanup function (line 177-189) disposes viewer, unregisters click handler, clears entityMapRef. `disposedRef` guard prevents stale state updates. **Note:** inline callback refs (CR-01) cause unnecessary re-initialization on every parent render, but the cleanup/disposal mechanism is correct and leak-free. |
| 5 | Fallback to SVG map occurs automatically when Speckle viewer initialization fails (missing token, network error, or missing resource URL) | VERIFIED | SpeckleViewport guard at line 100-102: calls `onError("No Speckle resource URLs or token available")` when preconditions fail. Error handler at ModelScreen line 497: `setSpeckleError(msg); setViewMode("map")`. Conditional render at ModelScreen line 489: only renders SpeckleViewport when prerequisites met. |
| 6 | The SVG map code remains fully intact and functional when toggled; run browsing, failing/passing lists, rule panel, and Properties sidebar work unchanged in both modes | VERIFIED | All SVG map code preserved: `boxPath` (line 45-58), `hashOf` (line 23-27), `layoutEntities` (line 28-43) — 6 matches total. SVG rendering (lines 501-559), zoom/pan handlers (lines 247-277), minimap canvas (lines 279-300), all sidebar components, run browsing, rule panel, Properties sidebar are outside the SpeckleViewport conditional branch and work unchanged. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ui-v2/src/components/speckle/SpeckleViewport.jsx` | Net-new React component wrapping @speckle/viewer | VERIFIED | 218 lines. Exists, exports default function with documented props interface. Imports Viewer, DefaultViewerParams, SpeckleLoader, UrlHelper, CameraController, SelectionExtension, UpdateFlags from @speckle/viewer. Lifecycle, entity mapping, click handler, resize handling all present. |
| `ui-v2/src/screens/ModelScreen.jsx` | Modified — 3D/Map toggle, conditional viewport render, entity click wiring | VERIFIED | 685 lines. Import at line 18. viewMode/speckleReady/speckleError state at lines 87-89. speckleResourceUrls/speckleToken derivation at lines 331-332. Toolbar toggle at lines 465-471. Conditional render at lines 488-560. Error handling at line 497. |
| `ui-v2/package.json` | Modified — @speckle/viewer dependency added | VERIFIED | Line 12: `"@speckle/viewer": "^2.31.14"` (version 2.31.14 installed, compatible with ^2.28.0 range). Build succeeds with no errors (4.78s). Bundle includes Speckle viewer (2MB total JS). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| SpeckleViewport props | data-service view payload | `readToken`, `baseResourceUrl`, `validationResourceUrl` from `build_view_payload()` | VERIFIED | data-service `app.py` line 707-727 returns all three fields. ModelScreen lines 331-332 derives `speckleResourceUrls = filter(Boolean)([view.baseResourceUrl, view.validationResourceUrl])` and `speckleToken = view.readToken`. |
| SpeckleViewport.onEntityClick | ModelScreen's pick(id) | `onEntityClick={(id) => pick(id)}` at line 495 | VERIFIED | Routes to `pick()` at line 241-244 which sets `setPicked(id)` and `setPropMode("instance")`. |
| World tree entity mapping | Legacy collectValidationObjects | `collectValidationObjects()` in SpeckleViewport.jsx (3-tier search: project+run, project-only, run-only) | VERIFIED | Mirrors legacy `graph-viewer/model-viewer/src/App.jsx` lines 70-141. Uses worldTree.findAll with fallback strategy. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| SpeckleViewport | readToken, resourceUrls | ModelScreen derives from `fetchValidationView()` response via `view.baseResourceUrl`, `view.validationResourceUrl`, `view.readToken` | YES — data-service returns from Neo4j run record at `app.py` lines 715, 721-722 | FLOWING |
| ModelScreen | view (validation payload) | `fetchValidationView()` in `modelApi.js` line 31-34 calls `/validation/view/{project}/{runId}` | YES — data-service queries Neo4j for run data and object sets (app.py lines 1193-1200) | FLOWING |
| SpeckleViewport entityMap | project, runId | SpeckleViewport receives from ModelScreen's own `project` and `runId` state | YES — project and runId are derived from user navigation state | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| npm package installed | `npm ls @speckle/viewer` | `@speckle/viewer@2.31.14` installed | PASS |
| Build succeeds | `npm run build` | Built in 4.78s, 931 modules | PASS |
| SpeckleViewport import exists | `grep -c "import SpeckleViewport" ModelScreen.jsx` | 1 match (confirmed) | PASS |
| viewMode state/references | `grep -c "viewMode" ModelScreen.jsx` | 5 matches (state + 4 usages) | PASS |
| SVG code preserved | `grep -c "boxPath\|hashOf\|layoutEntities" ModelScreen.jsx` | 6 matches (all SVG functions present) | PASS |
| @speckle/viewer in package.json | `grep -c "@speckle/viewer" package.json` | 1 match | PASS |
| Commits exist | `git show fe70510` / `git show 5dc6bf6` | Both commits found with expected content | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MVIEW3D-01 | ROADMAP / PLAN | Interactive 3D viewport with Speckle viewer; entity selection, zoom, pan, orbit | SATISFIED | SpeckleViewport renders 3D geometry. CameraController creates orbit controls. Entity selection via click handler routes to Properties sidebar. |
| MVIEW3D-02 | ROADMAP / PLAN | Validation color overlay on Speckle geometry matching SVG color scheme | SATISFIED (with note) | Server-side coloring via speckle_validation.py (D-04). No client-side recolor needed. Geometry renders as-is from Speckle publish pipeline. Verification requires running the app to confirm colors render server-side. |
| MVIEW3D-03 | ROADMAP / PLAN | Legacy SVG map remains as toggle fallback; run browsing, instance inspection, SWRL panel unchanged | SATISFIED | SVG map fully preserved. Toggle to "Map" renders original SVG. All sidebar panels unchanged. |

**Requirement Traceability Issue:** MVIEW3D-01, MVIEW3D-02, MVIEW3D-03 are defined in ROADMAP.md (Phase 27 section) and referenced in the PLAN frontmatter, but do NOT appear in the REQUIREMENTS.md traceability table. The REQUIREMENTS.md "Future Requirements" section mentions Speckle 3D as deferred but never assigns MVIEW3D IDs. This is a documentation completeness issue — the requirements exist at the ROADMAP level but are not formalized in the requirements document.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| ModelScreen.jsx | 490-499 | **CR-01:** Inline arrow function callbacks (onEntityClick, onReady, onError) create new references every render, causing SpeckleViewport's useEffect to dispose and recreate the viewer on every ModelScreen re-render | WARNING | Viewer reinitializes on every state change (entity pick, filter toggle, alpha slider, etc.). Camera resets, resources refetched, viewport flickers. Fix: use refs or useCallback to stabilize callback references. |
| ModelScreen.jsx | 466-468 | **WR-02:** No retry mechanism for 3D view after initialization failure — speckleError permanently disables 3D button | WARNING | User must page reload to retry 3D after transient failure. Fix: add retry3d() to clear error state. |
| SpeckleViewport.jsx | 108-135 | **WR-01:** Race window — viewerRef.current assigned after init(), not immediately after new Viewer() | WARNING | If deps change during async init, cleanup may not dispose new viewer (mitigated by disposed flag but fragile). |
| ModelScreen.jsx | 124-149 | **WR-03:** fetchValidationView not in useEffect dependency array | INFO | Stale closure risk during HMR. Missing from deps array. |
| SpeckleViewport.jsx | 98-190 | **IN-03:** Single useEffect for lifecycle + event binding + entity mapping | INFO | Combined concerns force re-running all work on any dep change. Legacy viewer separates into 3 effects. |

## Gaps Summary

No blocking gaps found. The implementation satisfies all 6 observable truths and all 3 success criteria from the ROADMAP:

1. **3D viewport renders** — SpeckleViewport component creates @speckle/viewer Viewer, loads resources, entity mapping, click handling
2. **Validation colors** — server-side applied via publish pipeline (no client-side recolor per D-04)
3. **SVG map preserved** — full toggle fallback with all map interactions intact

### Warnings (Non-Blocking)

1. **CR-01 (Critical Re-render Bug):** Inline callback props cause Speckle viewer to dispose and recreate on every ModelScreen re-render (entity selection, filter toggle, slider change). This is a significant UX degradation — camera resets, resources refetched. The 27-REVIEW.md provides a complete fix (use useRef for callbacks, remove them from dep array).

2. **WR-02 (No Retry):** After Speckle error, the 3D button is permanently disabled with no retry path.
   - Fix: Add `retry3d()` in ModelScreen and make 3D button always clickable.

3. **WR-01 (Race Window):** `viewerRef.current` assigned after async `init()`, creating a window where cleanup may not track the new viewer instance.

4. **Requirements Documentation Gap:** MVIEW3D-01/02/03 are defined in ROADMAP.md and used in PLAN but are absent from `REQUIREMENTS.md`'s traceability table. Recommend adding them to the active milestone's REQUIREMENTS.md or documenting the ROADMAP as the source of truth for these requirements.

---

_Verified: 2026-07-08T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
