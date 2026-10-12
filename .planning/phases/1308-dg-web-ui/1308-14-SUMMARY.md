---
phase: 1308-dg-web-ui
plan: "14"
subsystem: ui
tags: [model-viewer, i18n, react, speckle]
requires:
  - phase: 1308-05
    provides: EN/RU translation layer, coded error mapping, raw-text guard
  - phase: 1308-11
    provides: Shared Model Viewer run grouping
provides:
  - Translated Model Viewer chrome and shared display components
  - Russian Model dictionary and nine-file coverage manifest
  - Render-time error translation without language-triggered validation refetch
  - One-to-one display labels for eight validation statuses
  - Translated local Speckle proxy refusal messages
  - Unchanged model data, error codes and project-authorized proxy routes
affects: [1308-19, 1308-20, model-viewer]
tech-stack:
  added: []
  patterns: [render-time error translation, useT for shared React components]
key-files:
  created: []
  modified: [ui-v2/src/screens/ModelScreen.jsx, ui-v2/src/components/display/SessionHistory.jsx, ui-v2/src/components/display/CandidateTable.jsx, ui-v2/src/components/display/PropertiesTable.jsx, ui-v2/src/components/speckle/SpeckleViewport.jsx, ui-v2/src/components/surfaces/RunTile.jsx, ui-v2/src/lib/speckleProxy.js, ui-v2/src/i18n/dict/model.js, ui-v2/tests/i18n-swept/model.json]
key-decisions:
  - "API modules without authored user-facing messages remain unchanged; server text and codes stay data."
  - "Errors are translated on render so language changes do not reload a run or repeat candidate actions."
patterns-established:
  - "Store the original error and apply describeError at render for language-responsive display."
requirements-completed: [WEBUI-02]
coverage:
  - id: D1
    description: "Model Viewer labels and status/kind displays switch between English and Russian without translating model data."
    requirement: WEBUI-02
    verification:
      - kind: unit
        ref: "node --test ui-v2/tests/*.test.mjs"
        status: pass
    human_judgment: true
    rationale: "A browser RU/EN visual and interaction pass has not been performed; static coverage and offline tests do not prove layout or live language switching."
  - id: D2
    description: "Model area literal keys have Russian entries and all nine files are registered in the raw-text coverage manifest."
    requirement: WEBUI-02
    verification:
      - kind: unit
        ref: "node --test ui-v2/tests/i18n.test.mjs ui-v2/tests/landing-summary.test.mjs"
        status: pass
    human_judgment: false
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 14: Model Viewer Translation

**Model Viewer chrome, shared displays and proxy refusal messages follow the EN/RU layer while model-owned text stays unchanged.**

## Accomplishments

- Translated screen chrome, NO_STATE bucket and eight validation display statuses without changing codes or shared run grouping.
- Translated SessionHistory, CandidateTable, PropertiesTable, RunTile and SpeckleViewport presentation strings. Speckle proxy refusal messages now use the active language; path checks and credential boundary were unchanged.
- Error objects retain codes and are translated on render. Language changes no longer enter validation fetch effect dependencies or repeat candidate generation/acceptance.
- Registered all nine planned source paths in `tests/i18n-swept/model.json`. `modelApi.js` has no authored UI message; `inputGenApi.js` forwards server-authored hint/message and retains code/status, so neither needed an artificial translation.

## Task Commits

1. Task 1, ModelScreen tracer: `a3a73c6`.
2. Task 2, shared components and API messages: `5afd5da`.

## Verification

- Final source: `node --test ui-v2/tests/*.test.mjs` — 283 passed, 0 failed; `npm --prefix ui-v2 run build` — passed with existing chunk-size warning.
- `node --test ui-v2/tests/i18n.test.mjs ui-v2/tests/landing-summary.test.mjs` — 36 passed, including nine-file raw-text guard, dictionary/placeholder checks and shared grouping.
- Scoped `git diff --check` and staged diff check passed. The manifest lists all nine plan files; ModelScreen retains the `groupRunsByState` import and useMemo.
- No browser RU/EN visual pass, live geometry load, Docker rollout or candidate service acceptance was run. These are not claimed as verified.

## Deviations from Plan

- The two API modules without authored UI strings were left unchanged, although named in `files_modified`; their server-authored text must not be translated as model data.
- Corrected language-dependent fetch closures in ModelScreen and stored candidate error objects so changing language changes presentation only. No route or payload contract changed.

## Issues Encountered

The shared working tree has unrelated dirty planning and evidence files; only plan-owned source was staged for the task commits. The DSH hub was unavailable, so this two-task plan ran inline in the current tree without a worktree, as the owner requested.

## Next Phase Readiness

Offline acceptance is complete. The Russian layout and live language-switch behavior require the later browser/human backstop; phase-level rollout remains open. Continue other plans in dependency order, including 1308-24 before 1308-15.

## Self-Check: PASSED

Both task commits exist; the planned manifest and dictionary are present, the nine-file guard and all current UI node tests pass, and the production build succeeds. Human visual acceptance remains explicitly pending.
