---
tags: [debugging, ui-v2, model-viewer, speckle, fixed]
date: 2026-10-08
status: fixed
---

# Model Viewer camera reset and Design State jump on run switch

Owner reports after the F18–F22 fixes: the camera still reset to default on reopen, and switching runs inside a selected Design State sometimes jumped to the next Design State.

## Causes

1. **No Stationary event.** `@speckle/viewer` 2.31.14 `CameraController.on(CameraEvent.Stationary)` never fires after a move (only `dynamic` does), so the camera was never saved after an orbit. The saved value was the zoom-to-fit of the first load.
2. **Re-frame on every run switch.** The resource sync unloads the old validation model before loading the new one; judging "first load" by an empty scene made every switch call `loadObject(loader, true)` (zoom to fit).
3. **Design State persisted per run.** `runGfx` stored `stateKey` with each run; clicking a Design State saved it under the run on screen, and switching to a run restored its stale filter.

## Fixes (`ui-v2/src/components/speckle/SpeckleViewport.jsx`, `ui-v2/src/screens/ModelScreen.jsx`)

- Camera polled every 600 ms: reported once it holds still for a tick and differs from the last report; also on `pagehide` and unmount; never while a run is swapping or in map mode. Stored per project in `dgv2_model_camera`, restored via `setCameraView({position, target}, false)` on the viewer's first load.
- `hasLoadedRef` decides the one-time framing, not the scene's emptiness.
- `stateKey` removed from the per-run graphics save and restore.

## Verified

Live in the signed-in browser: restore after reload exact; V4 held through four run switches; camera held across a completed switch. Polling save not yet seen in a foreground tab (background tab throttled).

## Related

- [[knowledge/debugging/Model Viewer shows a foreign base model and a hard-coded tile property catalogue]]
- [[sessions/2026-10-08 Model Viewer fixes, landing motion redesign and DeGram 0.1.5]]
