---
phase: 24-model-viewer
plan: "24-01"
status: complete
completed: 2026-07-07
commits:
  - c082021 feat(24-01) Model Viewer screen + modelApi
  - 92309ab feat(24-01) seed fixture + pending migration + ring mapping
  - c21497d feat(25-01) (includes model viewer project-switch reset fix)
duration: ~1h
---

# Summary 24-01: Model Viewer

## What shipped

MVIEW-01 (runs from data-service with KV rows + failing/passing collapsibles), MVIEW-02 (instance mode with selection panel + per-rule breakdown), MVIEW-03 (iso map with Signal-Red failing / ink passing / gray base colouring, wheel zoom, minimap), MVIEW-04 (SWRL rule panel verbatim in mono from the metagraph `Rule.SWRL`; orbit-glyph legend).

## Decisions / deviations

- **Synthetic isometric massing** from entity-id hashes — the spec's stylised-map approach; stable across reloads; true 3D deferred per REQUIREMENTS.
- **Rule SWRL from Neo4j**, not data-service — `rulesJson` summaries carry no SWRL; the metagraph is the natural source (schema v4 `Rule.SWRL`).
- **Design-state tiles show real summary fields only** (stateId, capturedAtUtc, parameterCount, run count, pass ratio) — the mockup's rich per-state property rows (height/GFA/…) have no live data source; the PropState tile-settings popover was dropped with them.
- **"Re-run checks" button dropped** — validation runs publish from Grasshopper; the web UI cannot re-run.
- **Bugs fixed during verification**: project switch now resets run/view/instance state (stale-run 404 observed live); `gone:` label typo in an effect cleanup.

## Verification results

All four MVIEW criteria verified against the live stack with the `v8-ui-smoke` seed fixture (see PLAN). Build clean.

## Blocked / pending

- Real v2.0-era validation runs stay invisible until the user approves `migrations/2026-07-07_validationgraph_to_validgraph.cypher`.
