---
tags: [decision, model-viewer, ui]
date: 2026-04-05
---

# Per-run graphics state and screenshot persistence

## Context

The Model Viewer shows validation runs with configurable Graphics Settings Bar (visibility toggles, colors, opacity). When switching between runs, the previous run's settings were bleeding into the next run's view. Additionally, the validation run tiles in the bottom strip had no visual preview.

## Decision

1. **Per-run graphics state** — each run's Graphics Settings Bar state (9 values) is saved before switching and restored when selecting a run. Stored in `localStorage` under `dg_run_gfx_{project}`.

2. **Automatic screenshots** — the 3D viewport is captured as a 160×80 JPEG thumbnail via `viewer.screenshot()` before each navigation event (run switch or page leave). Stored in `localStorage` under `dg_run_screenshots_{project}`.

3. **Restore on load** — when viewer becomes ready, saved graphics state is restored for the active run.

## Alternatives Considered

- **Server-side storage** — rejected; adds API complexity for a UX feature, no shared state needed between users
- **Session-only storage** — rejected; users expect to see thumbnails and settings across browser sessions
- **Full-size screenshots** — rejected; 160×80 JPEG at 0.7 quality keeps each thumbnail ~3-5KB, avoiding localStorage quota issues

## Consequences

- localStorage usage grows with number of runs × projects (~4KB per run for screenshot + settings)
- No automatic pruning yet — may need cleanup of old project data in future
