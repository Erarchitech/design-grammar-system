---
phase: 1303-pravilo-gh-obekt
plan: "24"
subsystem: property-calculator-acceptance-fixes
tags: [d-66, d-67, d-68, d-69, dgopn-05, dgopn-06, no-data, run-property-check, sendvalid, regenerate-retired, derived-edges]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-22 (participants), 1303-23 (stack at f0e27a1, live acts 1-4 and the findings this plan fixes)"
provides:
  - "D-66: validate_function refuses a zero returned from an `is None` branch; prompt rule; shell report `nodata=`; EVIDENCE-CONTRACT D-05 example"
  - "D-67: data-service sends run_property_check once (503 CANVAS_BUSY, 409 SEND_VALID_ARMED, poll on solutionsEnded); listener 60 s hand-off, cancelled late hand-off, no canvas read behind a long solution, solutionsEnded counters; SendValidGuard one-shot"
  - "D-68: POST /scripts/property-calculators/regenerate (member, editor) and the Mapping panel button for a retired copy"
  - "D-69: dashed derived Class -> Class edges from ObjectProperty domain/range in the Graph Viewer"
affects: [1303-18, 1303-23]
key-files:
  modified:
    - data-service/property_calculator_llm.py
    - data-service/property_calculators/calculator_shell.py.tmpl
    - data-service/property_calculator_store.py
    - data-service/app.py
    - data-service/route_policy.py
    - DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs
    - DG/src/DG.Core/Bridge/CanvasUiWait.cs
    - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
    - ui-v2/src/lib/mappingApi.js
    - ui-v2/src/screens/MappingPanel.jsx
    - ui-v2/src/graph/buildRings.js
    - ui-v2/src/graph/graphEngine.js
    - spec/EVIDENCE-CONTRACT.md
    - spec/DATABASE.md
    - spec/SECURITY-BOUNDARY.md
  created:
    - DG/src/DG.Core/Bridge/SendValidGuard.cs
    - data-service/tests/test_property_check_run.py
    - DG/tests/DG.Tests/CanvasUiWaitTests.cs
    - DG/tests/DG.Tests/SendValidGuardTests.cs
    - ui-v2/tests/graph-derived-edges.test.mjs
    - test/str-openings-01/evidence/stack-rollout-1303-24.json
key-decisions:
  - "The no-zero rule is syntactic and narrow (a constant zero returned inside `if <name> is None`): counts that return 0 for 'no hits' stay valid, and the semantic part rests on the prompt. A stored source with the old pattern now fails verify_stored_source (integrity), so it can no longer be promoted or reused; it is regenerated through the confirmed, paid flow."
  - "SendValid is one-shot for every solution end, not only for listener-armed runs. A publish that needs SendValid on across several solutions is not supported by design."
  - "A late UI hand-off is cancelled only for run_property_check (cancelOnTimeout); other writes keep the documented 'may still run later' behaviour."
  - "Executed without DSH workers: the hub was unreachable (mode hub, hub_reachable false); the owner chose 'implement myself, TDD'."
requirements-completed: []
requirements_partial: [DGOPN-05, DGOPN-06]
completed: 2026-10-25
status: complete-offline-live-acceptance-open
---

# Plan 1303-24 summary

## What was done (one commit per task, base 2447295)

| Task | Commit | Result |
|---|---|---|
| plan | ae008c3 | PLAN.md |
| 1 D-66 | 6d0df1f | `validate_function` refuses `return 0/0.0/-0.0` inside `if x is None`; CONTEXT_API tells the model to return None for a distance, clearance or size with nothing to measure against and 0 only for counts; shell report line `n=%d nodata=%d min=%s max=%s`; prompt pin re-pinned on purpose (1419 -> 1627 characters) |
| 2 D-67 data-service | 34db9e7 | `_run_check_retrying_busy` removed; `_guard_canvas_ready`, `_start_check`, `_await_check_end`; 8 new tests |
| 3 D-67 plugin | e3e08d5 | `CanvasRunUiTimeoutMs` 60 s, `CanvasUiWait.Await(..., onTimeout)`, cancelled late hand-off, `finished=false` answers without a canvas read, `solutionsEnded`/`solutionsEndedBefore`, `SendValidGuard` with loop flag in the status, solution counter also subscribed by the status read |
| 4 D-68 backend | c9fe4a8 | `store.regenerate`, route, policy row (member, editor), `CALCULATOR_NOT_RETIRED`, SECURITY-BOUNDARY and DATABASE.md rows |
| 5 D-68/D-69 UI | 23ed720 | "Regenerate with DG" on a retired card, dashed derived edges (`buildRings` 4th edge element, engine dash) |
| 6 rollout | 414a7ab | images and DG.gha from `git archive 23ed720`, rollback kept, install script, evidence `stack-rollout-1303-24.json` |

## Verification (offline, from the committed state)

- data-service full: 4 failed, 6533 passed, 25 errors, the same names as the 1303-18/23 baseline; de01: the same 1 baseline failure; DG.Tests Release: 822 passed, the same 5 environmental failures; ui-v2: 381/381; ui build exit 0.
- Stack runs `dg-mapping-data-service:23ed720` and `dg-mapping-ui:23ed720`; served code equals the archive; anonymous candidates and regenerate answer 401.

## Not proven offline (owner acts)

1. DG.gha `96796214...` is built but not installed (owner, Rhino and Revit closed, `D:\dgb\mapping-release-23ed720\install-dg-gha.ps1`).
2. That a `None` item in the calculator's output list keeps the positional pairing with OBJECT STATE, so VALIDATOR reports `unknown` for exactly those boxes and not for a shifted set. Proof: regenerate the calculator, run the check, read per-box statuses.
3. That switching SendValid off at the end of the solution does not cut the asynchronous VALIDATOR upload of a hand-started publish (the listener one-shot did not, 2026-10-21/22).
4. Regeneration of `hasMinProjectionClearanceMm` costs one paid LLM call: needs the owner's explicit yes.

## Deviations

- No DSH workers (hub unreachable); every task was done by the controller with red-then-green tests.
- `_reset_check_toggles` in `app.py` has no caller; left in place.
- ValidationRun nodes and Speckle versions of 2026-10-25 (50 each) were counted and kept (owner decision), not deleted.
