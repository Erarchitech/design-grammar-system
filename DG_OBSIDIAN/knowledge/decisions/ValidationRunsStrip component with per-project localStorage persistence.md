---
tags: [decision, model-viewer, react, ui, localStorage, grouping]
date: 2026-05-10
---

# ValidationRunsStrip Component with Per-Project localStorage Persistence

## Context

Phase 05 introduced grouping (Rule | Design State) for the bottom Validation Runs strip in the Model Viewer. Group collapse state, the selected mode, and the user's preferred strip height all need to persist across reloads — but must NOT leak between projects (different validation history → different group keys → no point sharing collapse maps).

## Decision

Single localStorage key per project: `dg_run_grouping_${project}`.

```js
{
  "mode": "rule" | "state",
  "collapsed": { "<groupKey>": true, ... },
  "height": <number>
}
```

- **Reload triggers re-read** — `loadPersistedState(project)` is called in `useMemo` for initial state and again in a `useEffect` whenever the `project` prop changes. Switching projects swaps the entire entry.
- **Defaults** — `mode: "rule"`, `collapsed: {}`, `height: 200`. `mode: "rule"` preserves the existing visual mental model (tiles already show ruleId first; defaulting to State would surprise existing users).
- **Height is clamped** to `[120px, floor(window.innerHeight × 0.8)]` on read AND on every change. Re-clamped on `window.resize` so the strip can't outgrow a shrinking viewport.
- **Filter context preservation by construction** — all filter state (`showFailed`, `isolatedIds`, `selectedEntityIds`, sliders, etc.) lives in `App.jsx`. The strip only owns `mode`, `collapsed`, and `height`. Switching mode physically cannot touch filter state because it has no reference to it.

## Pure Grouping Adapter

`useValidationRunsGrouping(runs, mode)` is a plain function (despite the `useFoo` naming). Returns `[{ groupKey, groupLabel, runs }, ...]`:

- Rule mode: key = `run.ruleIds[0]` or `"__no_rule__"` bucket (always last).
- State mode: key = `run.state.stateId` or `"__no_state__"` bucket (always last).
- Group order: `localeCompare` ascending; null buckets last.
- Run order within group: `createdAt` DESC, `runId` ASC tiebreak.
- Defensive: `null`/`undefined`/empty input returns `[]`; unknown mode falls back to `"rule"`.

This shape is unit-testable without React, runs inside `React.useMemo` for cheap re-renders, and was driven by 9 vitest cases written RED before GREEN.

## Resize Handle

6px tall handle absolutely positioned at the strip's top edge (`top: 0; left: 0; right: 0; cursor: ns-resize`). Pointer drag updates inline `style.height` via React state. Drag UP grows the strip (handle is at the top, intuitively the strip grows toward the cursor). Keyboard accessibility: `tabIndex={0}` with `role="separator"`; ArrowUp/ArrowDown step 16px; Home resets to 200px.

## Why Not

- **Single global key** — would mix collapse maps across projects and confuse users.
- **Server-side persistence** — overkill; this is per-user, per-device UI preference, not shared state.
- **Separate keys per field** — three calls per change instead of one; harder to reason about migration.

## Related

- [[ResizeObserver wires Speckle viewer.resize on host element]]
- [[Layout overflow guards required for resizable flex children]]
- [[Pure grouping adapter testable as plain function]]
- [[Per-run graphics state and screenshot persistence]] — same per-project pattern, different concern.
