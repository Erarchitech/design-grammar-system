---
tags: [session, ui-v2, model-viewer, landing, degram, phase-1301]
date: 2026-10-08
---

# Session: 2026-10-07/08 — Model Viewer fixes, landing motion redesign and DeGram 0.1.5

## Goal

Fix the Model Viewer remarks from the v12 façade test (F18–F22), redesign the motion of the Design Grammars main window, and replace the red DEGRAM lettering of a new DeGram session with an animated logo, then build DeGram 0.1.5.

## What Was Done

- **Model Viewer (ui-v2, deployed and checked live):**
  - **F18 + F19:** the Base model checkbox is removed and the base model is never loaded, so the foreign Urban-Block geometry and its baked ground shadow are gone. The Speckle shadowcatcher is baked at load and re-baked only on unload; filtering left the shadow behind.
  - **F20:** run tile thumbnails were black because the transparent WebGL canvas became JPEG. They now get the viewport background first, and shots are filed under the run actually on screen (`sceneRunId`). The store key moved to `dgv2_run_shots_v2`.
  - **F21:** the viewer is created once and run switches load/unload only the validation model; the camera is saved per project (`dgv2_model_camera`) and restored on reopen. See [[knowledge/debugging/Model Viewer camera reset and Design State jump on run switch]].
  - **F22:** tile properties are built from the project's PropState values (`propCatalogue`), shown as min–max ranges, selection saved per project (`dgv2_tile_props_v2`); the hard-coded urban catalogue and `bolt://dg-meta:7687` caption are gone.
  - Design State selection no longer jumps on run switch (it was persisted per run).
- **Main window (ui-v2 landing, deployed, checked in real-time headless Chrome, 55–60 fps):** owner-tuned in a preview artifact. Opening sequence: a current runs once round the ring clockwise from the top (1 s), the ring lights up behind it, nodes pop in with the Graph Viewer arrival impulse, leader lines draw, labels fade in; hero words fade in by opacity only. Ring: 26,000 dots packed into narrow peaks, brightness contrast, breathing peaks, per-frame envelope lookup table. Michroma (self-hosted, OFL) for hero and region labels, Geist Mono for captions. See [[knowledge/decisions/Landing opening sequence and Michroma display face]].
- **DeGram (component `apps/degram`):** `DegramAnimatedMark` draws the 91-dot halftone hexagon live and pulses it (owner-tuned: pulse 3.6 s, ring delay 0.32 s, stretch 0.09, swell 1.35 − 0.04/ring). Component commits `ac65e101` + `2da8a2aa` (0.1.5), pushed by the owner; framework gitlink `a2cacb5`; build `5a86019` documented in `1301-BUILD.md`.
- **DeGram 0.1.5 built:** `DeGram-Setup-0.1.5.exe`, 490,510,493 bytes, SHA-256 `9081563b…a348`, exe 0.1.5; the packaged renderer CSS carries the tuned mark. Not launched.
- Two preview artifacts for owner tuning: DeGram Mark Tuner and Design Grammars Landing Tuner.

## Decisions Made

- [[knowledge/decisions/Model Viewer shows only the validation model]]: base model removed from the viewer (owner request).
- [[knowledge/decisions/Landing opening sequence and Michroma display face]].
- New-session DeGram mark replaces the Wordmark in variant degram only; variant hermes keeps the upstream lettering.

## Issues Encountered

- `@speckle/viewer` 2.31.14 never emits `CameraEvent.Stationary`; camera saving now polls the controls' goal position.
- The first resource-sync version re-framed the camera on every run switch (it judged "first load" by an empty scene after unloading).
- The browser bridge tab stays hidden behind VS Code, so Chrome pauses rAF; canvas verification used a CDP script on headless Chrome in real time (`--experimental-websocket` on Node 20).
- Pushing to the public fork was blocked by the permission classifier; the owner pushed.
- DeGram build run 1 failed on read-only `__pycache__` files of the previous payload (known 0.1.3 obstacle); flag cleared, run 2 exit 0.

## Next Steps

- Owner: run 0.1.5 `win-unpacked\DeGram.exe`, check the breathing mark on a new session.
- Owner: hard-refresh the Web UI and check the landing opening and the Model Viewer camera restore in a visible tab (polling save not yet seen live in a foreground tab).
- `/gsd-execute-phase 1301` → plan 16 (DGCL live checklist on PC1), unchanged.
- Optional: sphere and current strands exist in the tuner but are off in the shipped landing; re-enable only on owner request.

## Related Notes

- [[knowledge/debugging/Model Viewer shows a foreign base model and a hard-coded tile property catalogue]]
- [[knowledge/debugging/Model Viewer camera reset and Design State jump on run switch]]
- [[sessions/2026-10-07 Phase 1301 DeGram pairing connector, rules read fix, 490 MB installer and no Hermes name]]
