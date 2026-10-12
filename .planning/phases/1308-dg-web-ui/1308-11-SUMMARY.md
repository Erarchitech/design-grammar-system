---
phase: 1308-dg-web-ui
plan: "11"
subsystem: ui
tags: [landing, summaries, react, i18n]
requires:
  - phase: 1308-02
    provides: Project-scoped summary route
  - phase: 1308-05
    provides: EN/RU translation infrastructure
  - phase: 1308-23
    provides: Translated landing labels
provides:
  - Project-scoped landing summaries for five modules
  - Shared Model Viewer run grouping
  - Failure-tolerant, independently loaded summary sources
  - Russian summary labels
  - Offline landing summary tests
  - Project summary API client
  - No interval polling
  - Current-project response guard
  - Monochrome second-line summary styling
  - Host-only Graph and Model summary loading
  - Connector names capped at two plus count
  - LLM model value truncation with full-value tooltip
affects: [1308-19, 1308-20, landing, model-viewer]
tech-stack:
  added: []
  patterns: [per-source status envelope, shared pure grouping function]
key-files:
  created: [ui-v2/src/lib/summaryApi.js, ui-v2/src/lib/runGroups.js, ui-v2/src/lib/landingSummary.js, ui-v2/tests/landing-summary.test.mjs, ui-v2/tests/i18n-swept/landing.json]
  modified: [ui-v2/src/landing/LandingLayer.jsx, ui-v2/src/landing/landing.css, ui-v2/src/screens/ModelScreen.jsx, ui-v2/src/i18n/dict/landing.js]
key-decisions:
  - "A response carrying another project id is ignored rather than displayed."
  - "Each source loads independently on signed-in landing activation and project change; cleanup ignores stale results."
patterns-established:
  - "Landing source states are loading, ok or error; no polling or failure toast."
requirements-completed: [WEBUI-05, WEBUI-02]
coverage:
  - id: D1
    description: "Graph, Model, LLM, Reasoner and Connector summaries follow the current-project and host-mode contracts."
    requirement: WEBUI-05
    verification:
      - kind: unit
        ref: "ui-v2/tests/landing-summary.test.mjs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Russian labels and summaries remain within the landing ring and viewport at 1280px and 1920px in both themes."
    requirement: WEBUI-02
    verification: []
    human_judgment: true
    rationale: "A visual browser layout check at the required viewport sizes and themes was not performed."
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 11: Landing Summaries

**Five signed-in landing regions now show project-scoped or system-wide summaries without delaying the hero.**

## Accomplishments

- Added the authenticated summary client and pure builder, with a guard against another project's summary or runs and no rendering of LLM credential fields.
- Extracted Model Viewer's run grouping into a shared module; the landing's Design State count uses that same function.
- Added independently loaded, failure-tolerant second lines, RU translations, capped connector names and a model tooltip.

## Task Commits

1. Task 1, Graph Viewer tracer: `4f145d6`
2. Task 2, remaining summaries and shared grouping: `9bde930`

## Verification

- Task 1: `node --test ui-v2/tests/landing-summary.test.mjs ui-v2/tests/i18n.test.mjs` — 31 passed; `npm --prefix ui-v2 run build` — passed.
- Task 2 and final plan run: `node --test ui-v2/tests/*.test.mjs` — 283 passed, 0 failed; `npm --prefix ui-v2 run build` — passed (pre-existing chunk-size warning).
- Acceptance searches passed: summary CSS/render, no `setInterval`, grouping import/use in both modules, no local `NO_STATE` in ModelScreen, no `Keys issued` in UI source, `Grants issued` in builder.
- `graphify update .` completed. No live Docker, Rhino, paid inference or service write performed.
- Visual backstop at 1280px/1920px light/dark remains unverified; it must not be reported as a pass.

## Deviations from Plan

- Added a defensive current-project response check for both summary and validation runs; this is necessary to avoid cross-project counts on rapid project switches. No new package or surface was added.
- The whole-repository `git diff --check` encountered pre-existing whitespace in unrelated planning and generated files; scoped changed-file check passed.

## Next Phase Readiness

Plan 11 is code-complete and offline-verified. The required visual backstop and phase-level live acceptance remain open. The rest of wave 4 must proceed in dependency order.

## Self-Check: PASSED

Created modules and test manifest exist; both production task commits exist; task acceptance and plan-level offline verification passed. Visual backstop explicitly remains pending.
