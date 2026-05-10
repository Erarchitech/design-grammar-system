---
tags: [session, phase-05, model-viewer, grouping, react, vitest, speckle, resize]
date: 2026-05-10
---

# Session: 2026-05-10 — Phase 05 model-viewer grouping execution

## Goal

Execute Phase 05 of the v2.0 milestone (`model-viewer-grouping-by-rule-state`) end-to-end via `/gsd-execute-phase 5`:

- **Plan 05-01** — extend the data-service `/validation/runs/{project}` endpoint so each run carries a `state: { stateId, capturedAtUtc, parameterCount }` projection (or `null`).
- **Plan 05-02** — replace inline Validation Runs strip JSX with a `ValidationRunsStrip` component that adds a Group by switch (Rule | Design State), persists per-project state in localStorage, and ships through Vitest.

## What Was Done

### Wave 1: 05-01 (data-service)

- Added `_project_state_summary` helper above `list_validation_runs` in `data-service/app.py`.
- Cypher RETURN clause extended to fetch `run.statePayloadJson`.
- Each run dict now carries a `"state"` key (object or `null`).
- 9 pytest cases in `data-service/tests/test_validation_runs_state.py` covering: present, absent, malformed JSON, deeply nested brackets, recursive structures.
- Caught `RecursionError` in helper for Python 3.11 (container) compat — Python 3.14 (host) does not raise it on the same input.
- Container rebuilt and verified 20/20 tests pass.
- Commits: `477a1f1`, `e3771c4`, `29e3146`.

### Wave 2: 05-02 (model-viewer frontend)

Initial bringup landed via worktree but was reapplied directly to master after a worktree-base mishap (see Issues below). Final commits on master:

- `bd0eb4f` — `feat(05-02): ValidationRunsStrip with grouping switch + tests` (consolidated bringup of vitest scaffold, useValidationRunsGrouping pure adapter with 9 test cases, ValidationRunsStrip component, App.jsx wire-up).
- `2025cf2` — `feat(05-02): vertical scroll + draggable resize for ValidationRunsStrip` (post-UAT).
- `d86c1d7` — `fix(05-02): resize Speckle viewer canvas when strip height changes` (ResizeObserver on viewer host).
- `c73825a` — `fix(05-02): constrain page layout so strip resize shrinks viewport above` (grid + flex overflow guards).
- `e0a1250`, `29c2d4c` — SUMMARY.md updates for the post-UAT additions.

### Verification

- Backend: 9/9 pytest pass in container.
- Frontend: 9/9 vitest pass for `useValidationRunsGrouping`.
- Production bundle at `http://localhost:8080/model-viewer/` confirmed to contain `Group by`, `dg_run_grouping_`, `mv-strip-resize-handle`, `ResizeObserver`, error/empty copy.
- `gsd-verifier` ran goal-backward against `MVGP-01/02/03`: **5/5 must-haves passed**.
- Schema drift check: clean (no schema files touched).
- User UAT: all 13 points approved.

## Decisions Made

- **ResizeObserver on viewer host** drives `viewer.resize()` + `requestRender(RENDER | SHADOWS)` whenever the host's box changes. Cleanup on unmount via `observer.disconnect()`. Centralizing on the host element (rather than wiring an `onHeightChange` callback through the strip) handles every container resize, not just strip-driven ones. See [[ResizeObserver wires Speckle viewer.resize on host element]].
- **Resize handle at top edge of strip** with drag-up-grows semantics. Pointer events update inline `style.height` via React state. Persisted in the existing `dg_run_grouping_${project}` localStorage entry alongside `mode` and `collapsed`. Height clamped to `[120px, 0.8 × innerHeight]`, re-clamped on `window.resize`. Keyboard support: ArrowUp/Down (16px), Home (reset).
- **Layout overflow guards** are required when introducing a flex child with explicit dynamic height. Without them the child overflows the viewport rather than displacing siblings. See [[Layout overflow guards required for resizable flex children]].
- **Pure grouping adapter** (`useValidationRunsGrouping`) is a plain function despite `useFoo` naming — easier to unit-test and to call inside `React.useMemo`. 9 vitest cases written RED-then-GREEN.
- **Default grouping mode = `"rule"`** to preserve the existing visual mental model (tiles already showed ruleId first; defaulting to State would surprise existing users).
- **Filter context preservation by construction** — all filter state (sliders, toggles, isolation, selection) lives in `App.jsx`; the strip only owns `mode` and `collapsed`. Switching mode cannot touch filter state because it has no reference to it.

## Issues Encountered

- **Worktree branch base mishap (Windows)** — Wave 2's executor agent ran inside a worktree (`agent-ac3274cb17d07fe47`). Its 4 atomic task commits (`e8cc560`, `5464f4c`, `9794a40`, `53897de`) ended up containing **spurious deletions** of Phase 1-4 source files (`DG/src/DG.Core/Models/*`, `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs`, `DG/tests/DG.Tests/*`, `data-service/tests/test_validation_runs_state.py`, etc.). The worktree branch's parent was correct (`29e3146`) but the commits' deltas were corrupt, suggesting the agent's working tree got reset to an older base before staging. A naive `git merge worktree-agent-...` would have wiped 4,695 lines of Phase 1-4 work. See [[Worktree branch commits with spurious deletions]].
- **Recovery path** — reset master to before the orphan SUMMARY commit, attempted `git merge --ff-only` which failed with the same deletion warning. After that the merge state lingered (`MERGE_HEAD` present) and corrupted the working tree with conflict markers in `ValidationRunsStrip.jsx` and reverted Phase 2-4 source files. Fix: `rm .git/MERGE_HEAD .git/MERGE_MSG`, `git reset HEAD`, `git restore` to clean working tree, then `git checkout 26eb5f1 -- graph-viewer/model-viewer/...` to pull only the model-viewer files from the worktree branch onto master. Committed as one consolidated commit (`bd0eb4f`).
- **Bottom strip exceeded viewport** — original UAT exposed that with many groups, the fixed-200px strip clipped tile rows. Resolved by adding `.mv-strip-content` wrapper with `overflow-y: auto` and a draggable resize handle.
- **3D viewport stayed at old size when strip resized** — the Speckle Viewer measures its host pixel dimensions once at `init()` and keeps the WebGL canvas at that size. Adding a `ResizeObserver` on `viewerHostRef` that calls `viewer.resize()` fixed this.
- **Resize handle visually pinned, only inner scrollbar reacted** — second-round UAT issue. Root cause: `.mv-page` grid had no explicit row sizing and `.mv-right-col` had no overflow guard. The strip grew DOWN past the viewport instead of pushing the canvas above to shrink. Fix: `.mv-page { grid-template-rows: 100%; overflow: hidden }`, `.mv-right-col { min-height: 0; overflow: hidden }`. With these guards the canvas-wrap (`flex: 1`) is forced to shrink, the strip's top edge moves up tracking the cursor, and the ResizeObserver keeps the WebGL canvas in sync.

## Next Steps

- Phase 06 (`End-to-End Hardening and Verification`) — INTG-01/02/03. Discuss → plan → execute.
- Stale worktree branches (`worktree-agent-ad5e6e4c912c4e78e`, `worktree-agent-ac3274cb17d07fe47`) are still locked by their agent processes (pid 9484). Delete them after the agent runtime exits.
- `commit_docs: false` is set in `.planning/config.json` — `STATE.md`, `ROADMAP.md`, `05-VERIFICATION.md` updates remain in the working tree pending manual commit.

## Related Notes

- [[ResizeObserver wires Speckle viewer.resize on host element]]
- [[Layout overflow guards required for resizable flex children]]
- [[Worktree branch commits with spurious deletions]]
- [[ValidationRunsStrip component with per-project localStorage persistence]]
- [[Pure grouping adapter testable as plain function]]
- [[sessions/2026-04-07 Phase 05 UI mode restructuring execution|2026-04-07 Phase 05 (v1.1) execution]]
