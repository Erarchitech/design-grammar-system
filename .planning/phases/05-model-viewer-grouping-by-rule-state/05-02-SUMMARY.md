---
phase: 05-model-viewer-grouping-by-rule-state
plan: 02
subsystem: model-viewer
tags: [react, vite, vitest, tdd, grouping, ui, localStorage]
dependency_graph:
  requires:
    - "Phase 05 Plan 01: state projection adds run.state.stateId to /validation/runs/{project} response"
  provides:
    - "ValidationRunsStrip component: Group by switch (Rule | Design State) in validation runs strip"
    - "useValidationRunsGrouping hook: pure grouping adapter returning ordered groups[]"
    - "localStorage persistence: dg_run_grouping_${project} survives page reload"
    - "Error state: Could not load grouped runs. Try again. with retry affordance"
  affects:
    - "graph-viewer/model-viewer/src/App.jsx: inline strip removed, delegates to ValidationRunsStrip"
    - "graph-viewer/model-viewer/src/styles.css: new .mv-group-switch, .mv-run-group-header, .mv-error-retry, .mv-strip-content, .mv-strip-resize-handle classes"
    - "Production bundle at http://localhost:8080/model-viewer/"
    - "Post-UAT addition: vertical scroll inside strip + draggable resize handle at top edge"
tech_stack:
  added:
    - "vitest ^2.1.8 (devDependency): test runner for pure JS logic in model-viewer"
  patterns:
    - "Pure grouping adapter: useValidationRunsGrouping is a plain function, not a React hook, despite useFoo naming"
    - "localStorage persistence per project: separate key per project prevents cross-project collapse state leakage"
    - "Filter context preservation by construction: all filter state lives in App.jsx; strip only owns mode + collapsed"
    - "TDD: 9 test cases written RED before implementation GREEN"
key_files:
  created:
    - graph-viewer/model-viewer/src/useValidationRunsGrouping.js
    - graph-viewer/model-viewer/src/useValidationRunsGrouping.test.js
    - graph-viewer/model-viewer/src/ValidationRunsStrip.jsx
  modified:
    - graph-viewer/model-viewer/src/App.jsx
    - graph-viewer/model-viewer/src/styles.css
    - graph-viewer/model-viewer/package.json
    - graph-viewer/model-viewer/vite.config.js
    - graph-viewer/model-viewer/package-lock.json
decisions:
  - "Default grouping mode = 'rule': preserves existing visual mental model; tiles already show ruleId first"
  - "localStorage key dg_run_grouping_${project}: separate key per project; stores {mode, collapsed}; survives reload"
  - "Flat src/ layout retained: no components/ or hooks/ subdirs — matches existing App.jsx-only convention"
  - "Vitest added as devDependency: Vite already present; lockfile regenerated for Docker npm ci"
  - "Task 5 (Docker rebuild + smoke) kept in same plan: tight build pipeline with no orphan plan"
  - "runsError state separate from general error state: strip needs its own error string for the retry affordance"
  - "Files copied to main repo before Docker rebuild: worktree build context not accessible from main docker-compose.yml"
  - "Strip resizing via pointer events + inline style.height: avoids re-layout thrash and keeps the height a per-project user preference"
  - "Resize handle at top edge: drag-up grows the strip (intuitive — it grows toward where the user's pointer is moving)"
  - "Height clamped to [120px, 80vh] and re-clamped on window resize: prevents the strip from eating the entire viewport on small screens"
  - "Existing dg_run_grouping_${project} localStorage entry extended with height field rather than a separate key: keeps related strip prefs together"
metrics:
  duration_minutes: 50
  completed_date: "2026-05-07T18:55:00Z"
  tasks_completed: 6
  files_changed: 9
requirements:
  - MVGP-01
  - MVGP-02
  - MVGP-03
---

# Phase 05 Plan 02: Validation Runs Grouping Strip (Frontend)

**One-liner:** `ValidationRunsStrip` component with Rule/Design-State group-by switch, collapsible groups, localStorage persistence, and error-retry state — wired into App.jsx replacing ~45 lines of inline tile JSX.

## What Was Built

### useValidationRunsGrouping.js (pure adapter)

A plain function (despite the `useFoo` name) that takes `runs[]` and `mode` and returns `groups[]`:

```javascript
[
  { groupKey: "R_URB_HEIGHT_MAX_75_V", groupLabel: "R_URB_HEIGHT_MAX_75_V", runs: [...] },
  { groupKey: "__no_rule__", groupLabel: "No Rule", runs: [...] }
]
```

- Rule mode: key = `run.ruleIds[0]` or `"__no_rule__"` bucket (always last)
- State mode: key = `run.state.stateId` or `"__no_state__"` bucket (always last)
- Group order: `localeCompare` ascending; null buckets last
- Run order within group: `createdAt` DESC, `runId` ASC tiebreak
- Defensive: `null`/`undefined`/empty input returns `[]`; unknown mode falls back to `"rule"`

### useValidationRunsGrouping.test.js (9 Vitest cases)

| Test | Covers |
|------|--------|
| empty input | null, undefined, [] all return [] |
| rule grouping | first ruleId used as key; multiple runs under same rule |
| __no_rule__ last | runs with empty ruleIds in last bucket |
| state grouping | state.stateId used as key |
| __no_state__ last | null state + empty stateId both go to last bucket |
| run ordering | createdAt DESC with runId ASC tiebreak |
| unknown mode fallback | "garbage" → rule mode |
| invalid createdAt | non-date sorts as epoch 0 (last among reals) |
| stability | repeated calls produce identical JSON |

All 9 pass.

### ValidationRunsStrip.jsx (component)

Replaces the inline `<div className="mv-bottom-strip">` block in App.jsx. Key behaviors:

- `Group by` radiogroup with `Rule` and `Design State` buttons (`role=radio`, `aria-checked`)
- Calls `useValidationRunsGrouping` via `React.useMemo`
- Collapsible group headers with `aria-expanded` and SVG chevron
- Tile rendering (identical structure to former inline JSX)
- **Error state:** when `error` prop is non-empty → renders `"Could not load grouped runs. Try again."` + `Try again` button invoking `onRetry`
- **Empty state:** when no runs → `"No validation runs match current filters."`
- **localStorage persistence:** `dg_run_grouping_${project}` stores `{mode, collapsed}` per project; reloaded when `project` prop changes

### App.jsx changes

- Added `import ValidationRunsStrip from "./ValidationRunsStrip.jsx"`
- Added `const [runsError, setRunsError] = React.useState(null)` alongside `runsLoading`
- `loadRuns`: `setRunsError(null)` at start; `setRunsError(message)` in catch branch
- Replaced the entire `<div className="mv-bottom-strip">...</div>` block (~45 lines) with `<ValidationRunsStrip ... />`

### Error-state wiring path

```
loadRuns catch → setRunsError(message)
  → App.jsx state: runsError
  → ValidationRunsStrip prop: error={runsError}
  → renders "Could not load grouped runs. Try again."
  → "Try again" button → onRetry={loadRuns}
  → loadRuns called → setRunsError(null) at start → error cleared
```

### CSS additions (styles.css)

New classes appended to end of file:
- `.mv-group-switch`, `.mv-group-switch-label`, `.mv-group-switch-opt`, `.mv-group-switch-opt.is-active`
- `.mv-run-group`, `.mv-run-group-header`, `.mv-run-group-label`, `.mv-run-group-count`
- `.mv-chevron`, `.mv-chevron.is-open` (rotation transition)
- `.mv-error-copy`, `.mv-error-retry`

`.mv-strip-header` already had `display: flex; align-items: center` — no change needed.

### Production bundle verification

Bundle `assets/index-CVlIRKJs.js` served at `http://localhost:8080/model-viewer/` contains:
- `"Group by"`: 2 matches
- `"dg_run_grouping_"`: 1 match
- `"Could not load grouped runs"`: 2 matches
- `"No validation runs match current filters"`: 1 match

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Files copied to main repo before Docker rebuild**
- **Found during:** Task 5
- **Issue:** The worktree has its own git branch with the new files. `docker compose build` in the main repo uses `./graph-viewer` as context — the main repo's directory which does not yet have the new files (they're on the worktree branch). The build produced a stale image.
- **Fix:** Copied all 9 modified/new files from the worktree `graph-viewer/model-viewer/` to the main repo's `graph-viewer/model-viewer/` before running `docker compose build --no-cache design-grammars` from the main repo dir.
- **Files modified:** main repo graph-viewer/model-viewer/{src/App.jsx, src/styles.css, src/ValidationRunsStrip.jsx, src/useValidationRunsGrouping.js, src/useValidationRunsGrouping.test.js, package.json, package-lock.json, vite.config.js}
- **Impact:** None on correctness — the files in main repo now match the worktree exactly. The worktree commits remain canonical.

**2. [Rule 2 - Missing] runsError state separate from general error state**
- **Found during:** Task 4
- **Issue:** App.jsx had a general `error` state used for viewer-level errors (not just run-loading). Passing that to the strip would incorrectly surface viewer errors as "Could not load grouped runs" and clear run-error on any other state change.
- **Fix:** Added `runsError` as a dedicated state. `loadRuns` clears it on success and sets it on failure. The general `error` state is preserved for other error cases.
- **Files modified:** graph-viewer/model-viewer/src/App.jsx

## Known Stubs

None. The grouping adapter is fully implemented and wired. The strip renders real data from the existing `validationRuns` array.

## Commits

| Hash | Description |
|------|-------------|
| e8cc560 | chore(05-02): add Vitest to model-viewer + scaffold grouping stub files |
| 5464f4c | feat(05-02): implement pure grouping adapter with 9 Vitest cases (TDD) |
| 9794a40 | feat(05-02): build ValidationRunsStrip with grouping switch, error state, localStorage persistence |
| 53897de | feat(05-02): wire ValidationRunsStrip into App.jsx, replace inline strip (MVGP-03) |

## Post-UAT Addition: Vertical scroll + draggable resize

Triggered by user feedback during UAT: "Bottom Validation Runs Strip now exceeds the size of window and tiles don't fit the window. So add scroller updown for the strip and add control to extend the strip up and down by the user if needed."

Made directly on master (worktree branch reapplied to master per user direction during this session).

### Changes
- **`.mv-strip-content` wrapper** added inside `.mv-bottom-strip` below the header. `overflow-y: auto`, `min-height: 0`, `flex: 1` — vertical scroll for the group list while the header stays pinned. Custom 8px scrollbar styled to match the accent palette.
- **Resize handle** at the strip's top edge: 6px tall, `cursor: ns-resize`, with a small visible grab indicator (32×2px bar centered).
- **Pointer-driven drag** on the handle updates inline `style.height` via React state. Drag UP grows the strip (handle is at the top), drag DOWN shrinks it.
- **Keyboard accessibility:** the handle is `tabIndex=0` with `role="separator"`. ArrowUp/ArrowDown change height by 16px. Home resets to 200px.
- **Height clamp:** `[120px, floor(window.innerHeight × 0.8)]`. Re-clamped on `window.resize` so the strip can't outgrow a shrinking viewport.
- **Persistence:** the existing `dg_run_grouping_${project}` localStorage entry now stores `{mode, collapsed, height}`. Height survives reload and is per-project.

### Commits
| Hash | Description |
|------|-------------|
| bd0eb4f | feat(05-02): ValidationRunsStrip with grouping switch + tests (MVGP-01/02/03) — consolidated bringup directly on master |
| 2025cf2 | feat(05-02): vertical scroll + draggable resize for ValidationRunsStrip |
| e0a1250 | docs(05-02): document scroll + resize, updated UAT checklist |
| d86c1d7 | fix(05-02): resize Speckle viewer canvas when strip height changes (ResizeObserver on host) |
| c73825a | fix(05-02): constrain page layout so strip resize shrinks viewport above (mv-page grid-template-rows: 100% + overflow: hidden, mv-right-col min-height: 0 + overflow: hidden) |

### Follow-up fixes from second-round UAT
- **Viewport stays at old size when strip resizes** → added `ResizeObserver` on `viewerHostRef` that calls `viewer.resize()` + re-requests render (commit d86c1d7).
- **Resize handle pinned, only inner scrollbar reacts** → grid+flex layout had no overflow guard, so the strip overflowed past the viewport rather than shrinking the canvas above. Locked grid row to 100% and gave `.mv-right-col` `min-height: 0; overflow: hidden` (commit c73825a). Strip top edge (and handle) now tracks the cursor; canvas-wrap shrinks to compensate; ResizeObserver keeps the WebGL canvas in sync.

## Awaiting

**Task 6 (checkpoint:human-verify):** Human UAT — verify grouping UX end-to-end.

Visit `http://localhost:8080/model-viewer/?project=<project-with-runs>` and verify:
1. "Group by" label visible with Rule (active) and Design State buttons
2. Rule mode groups tiles by ruleId; empty-rule runs in "No Rule" (last)
3. Design State mode groups tiles by stateId; no-state runs in "No State" (last)
4. Switching mode preserves: filters, sliders, isolated entities, selected run
5. Collapse a group, hard-refresh → mode and collapsed state persist (localStorage)
6. Empty project → "No validation runs match current filters."
7. Stop data-service → "Could not load grouped runs. Try again." → restart → Try again works
8. Keyboard: Tab to Group by buttons and group headers; Space/Enter activates
9. **Vertical scroll:** load a project with many groups → group list scrolls vertically inside the strip without clipping the header
10. **Resize handle:** hover the top edge of the strip → cursor becomes ns-resize and a small grab bar lights up
11. **Drag resize:** drag the handle UP → strip grows; drag DOWN → strip shrinks. Min 120px, max 80% of viewport
12. **Resize persistence:** resize the strip, hard-refresh → height restored
13. **Keyboard resize:** Tab to the handle, ArrowUp/Down adjusts in 16px steps, Home resets to 200px

## Self-Check: PASSED

| Item | Status |
|------|--------|
| useValidationRunsGrouping.js exists in worktree | FOUND |
| useValidationRunsGrouping.test.js exists in worktree | FOUND |
| ValidationRunsStrip.jsx exists in worktree | FOUND |
| commit e8cc560 exists | FOUND |
| commit 5464f4c exists | FOUND |
| commit 9794a40 exists | FOUND |
| commit 53897de exists | FOUND |
| "Group by" in production bundle | FOUND |
| "dg_run_grouping_" in production bundle | FOUND |
| "Could not load grouped runs" in production bundle | FOUND |
