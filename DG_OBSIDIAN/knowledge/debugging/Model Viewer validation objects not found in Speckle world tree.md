---
tags: [debugging, model-viewer, speckle, coloring]
date: 2026-07-08
---

# Model Viewer validation objects not found in Speckle world tree

## Symptoms
- Fail/pass/base visibility toggles in Model Viewer toolbar have no effect
- Colors (failColor/passColor) don't apply to objects
- The model always shows grey regardless of toggle state
- "All off" should hide the model completely but it stays visible

## Root Cause Hypothesis

`collectValidationObjects()` (in `SpeckleViewport.jsx:22-67`) walks the Speckle world tree looking for nodes whose raw payload matches all three conditions:

```javascript
raw.validationRunId === runId && raw.dgProject === project && raw.dgEntityId
```

If **no nodes match**, `entityMap` stays empty, `allValidationObjectIds` stays empty, and every filtering operation (`hideObjects`, `isolateObjects`, `setUserObjectColors`, `setMaterial`) receives zero object IDs → noop.

Three fallback modes exist:
1. Primary: `validationRunId + dgProject + dgEntityId`
2. Fallback: `dgProject + dgEntityId` (without runId — some historical data)
3. Final: `validationRunId + dgEntityId` (without project)

## Key Questions

1. **Does the validation Speckle resource (`validationResourceUrl`) contain objects with `dgEntityId` in their raw data?** — Check against the actual Speckle stream's object properties.

2. **What does the legacy viewer (`graph-viewer/model-viewer/src/App.jsx`) do differently?** It uses the same `collectValidationObjects` function and loading sequence. If it worked, the Speckle objects had the right properties.

3. **Does `view.validationResourceUrl` return the correct URL?** — Check the data-service `/validation/view/` endpoint response.

4. **Are the `failedEntityIdList`/`passedEntityIdList` props populated?** — They come from `view.objectSets.failed[].dgEntityId` / `view.objectSets.passed[].dgEntityId`. These are the entity IDs we're trying to find in Speckle.

## Investigation Plan

1. **Check data-service `/validation/view/{project}/{runId}` response** — Does the `validationResourceUrl` field exist? Is the URL accessible?

2. **Add a debug log** inside `collectValidationObjects` to see how many nodes match each search mode (port from legacy viewer's `console.log("[DG-Debug] ...")` pattern).

3. **Check Speckle object properties** — Load `validationResourceUrl` separately and inspect raw object data for `dgEntityId`/`validationRunId`/`dgProject`.

4. **Verify entity list props** — Log `failedEntityIdList` and `passedEntityIdList` in the filtering effect.

## Related Files

- [SpeckleViewport.jsx](ui-v2/src/components/speckle/SpeckleViewport.jsx) — lines 22-67 collectValidationObjects, lines 253-361 filtering effect
- [ModelScreen.jsx](ui-v2/src/screens/ModelScreen.jsx) — lines 339-341 entity ID lists, line 483 resourceUrls
- [modelApi.js](ui-v2/src/lib/modelApi.js) — `fetchValidationView` response shape
- [Legacy viewer](../../graph-viewer/model-viewer/src/App.jsx) — working reference implementation

## Why the fix (commit 34f26dd) didn't help

The commit fixed a SECONDARY issue: when `entityMap` IS populated, multiple FilteringExtension calls with different stateKeys silently wipe each other. But the PRIMARY issue is that `entityMap` is empty — no matching nodes found in the world tree.

## RESOLVED 2026-07-08 (audit-fix F-01)

**Root cause was NOT in the viewer.** The Speckle validation elements carried correct `dgEntityId`/`dgProject`/`validationRunId` — but **`displayValue: []`** (no geometry). With no meshes, the world tree had no renderable nodes for the validation entities, so hide/isolate/color operations had nothing to act on.

The geometry was dropped server-side of the viewer, in the C# pipeline:
`DesignStateBindingService.CreateBindings()` built each binding's `ElementRef` with only `DgEntityId` + `DisplayName`, never copying `objState.Geometry`. Every DesignState-pipeline publish (v7.0+) therefore sent null geometry → `speckle_validation.py build_display_value(None)` → empty `displayValue`. The v2.0-era TestA runs worked in the legacy viewer because the old pipeline attached geometry (verified: TestA validation elements have 6 meshes each in `displayValue`).

**Fix:** `DG/src/DG.Core/Services/DesignStateBindingService.cs` — `Geometry = objState.Geometry` in the ElementRef (commit `0b15ce0`, regression test added). Requires rebuilding the GH plugin and republishing runs; all runs published before the fix have no geometry and will stay grey/untoggleable.

**Verified live:** republished a geometry-carrying run via `test/publish_validation_run_with_geometry.py` (commit for F-02) — primary world-tree search matched 9/9 nodes, entityMap 9 entities / 18 objectIds, fail-toggle hides 8 ids, base-off isolates 18, all-off applies the sentinel isolate, and renderer material overrides resolve 2 render views per entity with correct color+opacity.

Debug logging was also restored in `SpeckleViewport.jsx` (`[DG-Debug]` + `window.__dgSpeckleDebug`, commit for F-03).

## Evidence

- [[sessions/2026-07-08 Model Viewer filter/coloring regression]]
