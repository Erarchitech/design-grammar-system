---
phase: 1303-pravilo-gh-obekt
plan: "25"
subsystem: property-check-verdict-and-presentation
tags: [d-70, d-71, d-72, dgopn-05, dgopn-06, one-shot, verdict-gate, no-verdict, bbox-helpers]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-24 (D-66 None for no data, D-67 one-shot SendValid) and its live check of 2026-10-25 afternoon"
provides:
  - "D-70: VerdictGate (DG.Core); listener one-shot released by the solution that produced the verdict (3 solution ends / 120 s bound), oneShotPending in the status; data-service waits for it and re-reads the status after the published runs are found"
  - "D-71: VALIDATOR Status output (canonical status per ObjState); highlighter red/grey/green from Status; objectSets.unknown; Model Viewer draws and lists objects without a verdict apart; EVIDENCE-CONTRACT §5.0"
  - "D-72: ctx.near, ctx.host_floors, ctx.plan_gap_mm in the calculator shell; CONTEXT_API names them (prompt pin 2297 characters, sha256 60405fd9...)"
affects: [1303-18, 1303-23, 1303-24]
key-files:
  created:
    - DG/src/DG.Core/Bridge/VerdictGate.cs
    - DG/tests/DG.Tests/VerdictGateTests.cs
    - ui-v2/src/lib/objectSets.js
    - ui-v2/tests/model-unknown-set.test.mjs
  modified:
    - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
    - DG/src/DG.Core/Services/ValidStatusMapper.cs
    - DG/tests/DG.Tests/ValidStatusMapperTests.cs
    - data-service/app.py
    - data-service/property_scripts.py
    - data-service/property_calculator_llm.py
    - data-service/property_calculators/highlighter.py.tmpl
    - data-service/property_calculators/calculator_shell.py.tmpl
    - data-service/tests/test_property_check_run.py
    - data-service/tests/test_property_scripts.py
    - data-service/tests/test_property_calculator_llm.py
    - data-service/tests/test_validation_entity_rollup.py
    - ui-v2/src/screens/ModelScreen.jsx
    - ui-v2/src/i18n/dict/model.js
    - ui-v2/tests/i18n-swept/model.json
    - spec/EVIDENCE-CONTRACT.md
requirements-completed: []
requirements_partial: [DGOPN-05, DGOPN-06]
completed: 2026-10-25
status: complete-live-accepted
---

# Plan 1303-25 summary

## What was done (one commit per task, base 917a30b)

| Task | Commit | Result |
|---|---|---|
| plan + live evidence | 917a30b | PLAN.md, `live-check-1303-24.json`, image 25297dd added to `stack-rollout-1303-24.json` |
| 1 D-70 | 770a612 | `VerdictGate` + 7 xUnit tests; listener arms the one-shot for every non-clear run and releases it on the verdict; `oneShotPending`; data-service waits for it and re-reads the status after publishing (2 new pytest) |
| 2 D-71 plugin | f7c7575 | `ValidStatusMapper.PerObjStateStatus` + 2 tests; VALIDATOR output `Status` appended (index 8) |
| 3 D-71 data-service | e776774 | highlighter `verdicts()` (red failed/error, grey non-verdict, green passed; ValidStatus fallback), Status input and wire; `objectSets.unknown`; two 1202-era rollup assertions changed on purpose; EVIDENCE-CONTRACT §5.0 |
| 4 D-71 UI | dc52c2a | `lib/objectSets.js` + 5 node tests; ModelScreen neutral colour, "Items without a verdict", NO VERDICT; ru strings; i18n manifest |
| 5 D-72 | 9d95481 | `near`, `plan_gap_mm`, `host_floors` in ModelContext + 2 tests on the fake Revit DB; CONTEXT_API lines; prompt pin re-pinned |

## Verification (offline)

- DG.Tests Release (worktree, sources equal to 9d95481): 831 passed, 5 failed = the 1303-24 environmental baseline (FrameAblatedCorpusEmitter golden files; DesignStateValidationFlowTests x4).
- ui-v2: 386/386; build exit 0.
- data-service focused property/run/rollup set: 264 passed; full suite: see "Gate".
- de01: 1 failure, the baseline `test_de01_runner_against_golden_fixture_has_zero_silent_disagreements`.
- DG.sln Release build from `git archive 9d95481`: 0 errors, 38 warnings; DG.gha sha256 `0def946488cb4e55770fb13a4625c70fff2c8fb9761c16a745fcff0d2c04a16d`, DG.Core.dll `980225c108dcebe6663b74722ad6730fe719bc50e652e81f478530adbf16cd2f`.

## Gate

data-service full (worktree, 468 s): 4 failed, 6544 passed, 35 skipped, 8 deselected, 25 errors. The 4 failures are the 1303-18/23/24 baseline names (tests/test_dg_context.py: test_post_assemble_returns_200_for_valid_type, test_get_debug_matches_post_assemble_body, test_repeated_assemble_calls_are_byte_identical, test_get_debug_and_post_assemble_are_equal_for_graph_query); the 25 errors are the DNS failures for neo4j:7687 (test_cg_structure_checks 20, test_computgraph_consult 5). No new failure name; 11 more tests pass than in the 1303-24 gate (6533).

## Live acceptance (2026-10-25 evening, evidence `test/str-openings-01/evidence/live-check-1303-25.json`)

Rollout 9d95481 (data-service, UI), DG.gha installed by the owner (hash checked). Three follow-up fixes found live, each red-then-green and rolled out with the owner's yes:

| Commit | Finding | Fix |
|---|---|---|
| 12b5d76 | Run check right after placing a newly generated calculator answered 503: the pre-run read met the placement's own solution | after a placement only the status read is repeated (up to 90 s); the run is still sent once |
| 72846b4 | the Model Viewer listed 4 boxes without data as passed: legacy ValidationEntity rows come from passedRuleIds | objectSets and picked-object statuses read the run's evidence envelope; ValidationEntity rows unchanged (pinned contract) |
| c0b81f6 | painting opened Revit's modal "group changed outside group edit mode" warning, which held the solution and the one-shot | a grouped box is only coloured; DG_Violation is not written into it |

Results: one paid regeneration gave `calc_gen_e5c9bd4c09` (bce2dcf4..., pending) using host_floors/near/plan_gap_mm: n=309, nodata=4. One Run check after a fresh placement published 5 of 5 runs (200); after the dialog was closed the one-shot released itself, no further publish. Envelope R_STR: 188 failed, 121 passed, 4 unknown; R1-R4 unchanged (boxes 214, 217, 0/1/2/157) — this closes the 1303-24 ObjState-pairing proof. With c0b81f6 the view equals the envelope for all 5 rules.

## Still open

1. Grey colouring in Revit was not inspected visually; c0b81f6 (no parameter in grouped boxes) not yet exercised live.
2. The calculator is pending: confirming it into the UAT-A catalogue is act 5 of plan 1303-18.

## Deviations

- `VerdictGate` is a new class next to `SendValidGuard` (the plan named only SendValidGuard): the guard keeps counting disarms and loops, the gate decides when to release.
- Model Viewer strings went to `i18n/dict/model.js` (where the neighbouring Model strings live), not `screens.js`; `lib/objectSets.js` added to the i18n manifest.
- The full DG.Tests and data-service suites cannot run from the `git archive` folder (spec/ and fixtures/ are not exported); they ran in the worktree, whose tested trees had no uncommitted change.
