---
phase: 27-speckle-3d-embed
fixed_at: 2026-07-08T12:00:00Z
review_path: .planning/phases/27-speckle-3d-embed/27-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 27: Code Review Fix Report

**Fixed at:** 2026-07-08T12:00:00Z
**Source review:** .planning/phases/27-speckle-3d-embed/27-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (1 critical, 3 warnings)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Inline callback functions cause Speckle viewer re-creation on every parent render

**Files modified:** `ui-v2/src/components/speckle/SpeckleViewport.jsx`
**Commit:** a84bd40

**Applied fix (Part A -- ref-based approach):**
Stored `onEntityClick`, `onReady`, and `onError` callbacks in refs (`onEntityClickRef`, `onReadyRef`, `onErrorRef`) and updated them before the viewer lifecycle effect. The effect now reads from these refs instead of closure-captured props, and the dependency array was reduced to only stable props (`[resourceUrls, readToken, project, runId]`). This prevents the Speckle viewer from being disposed and re-created when the parent passes inline arrow functions that create new references on every render.

Changes applied to SpeckleViewport.jsx:
- Added `onEntityClickRef`, `onReadyRef`, `onErrorRef` refs initialized from props
- Added ref synchronization before the effect (runs every render)
- Replaced `onError?.()`, `onEntityClick`, `onReady?.()` calls with their ref equivalents inside the effect
- Changed effect dependency array from `[resourceUrls, readToken, project, runId, onEntityClick, onReady, onError]` to `[resourceUrls, readToken, project, runId]` with an `eslint-disable-next-line react-hooks/exhaustive-deps` comment

This approach follows the pattern used in the legacy viewer (`graph-viewer/model-viewer/src/App.jsx`) which separates viewer lifecycle from callback dependencies.

### WR-01: Race window during async viewer initialization before viewerRef assignment

**Files modified:** `ui-v2/src/components/speckle/SpeckleViewport.jsx`
**Commit:** f71ca08

**Applied fix:**
Added a `.catch()` chain to the `void initViewer()` call inside the viewer lifecycle effect. The catch handler checks the `disposed` flag before routing errors through `onErrorRef.current?.()`. This ensures that any unhandled promise rejections during the async initialization race window (when `viewerRef.current` may not yet be assigned but the cleanup has already run) are caught and reported rather than silently swallowed.

The existing internal try/catch in `initViewer` already handles most errors, but the top-level `.catch()` acts as a safety net matching the pattern used in the legacy viewer.

### WR-02: No retry mechanism for 3D view after initialization failure

**Files modified:** `ui-v2/src/screens/ModelScreen.jsx`
**Commit:** c38d589

**Applied fix:**
Added a `retry3d()` function that clears `speckleError` state and switches `viewMode` to `"3d"`. The 3D button was updated:
- Removed the `disabled` prop so the button is always clickable
- `onClick` now checks `speckleError` -- if set, calls `retry3d()`; otherwise calls `setViewMode("3d")`
- Label shows "Retry 3D" when `speckleError` is truthy, "3D" otherwise

This allows users to recover from transient initialization failures (e.g., temporary network glitch) without a full page reload.

### WR-03: `fetchValidationView` not in useEffect dependency array (stale closure)

**Files modified:** `ui-v2/src/screens/ModelScreen.jsx`
**Commit:** abe2378

**Applied fix:**
Added the three imported API functions to their respective useEffect dependency arrays:
- `fetchValidationView` added to the run-view loading effect: `[runId, project, fetchValidationView]`
- `fetchRuleDetails` added to the rule details effect: `[ruleId, project, fetchRuleDetails]`
- `fetchEntityStatuses` added to the per-entity statuses effect: `[picked, runId, project, fetchEntityStatuses]`

These are stable module-level imports, so adding them to dependency arrays satisfies the `react-hooks/exhaustive-deps` rule without causing unnecessary effect re-runs in production.

---

_Fixed: 2026-07-08T12:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
