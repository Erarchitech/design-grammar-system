---
phase: 18-rules-and-validator-rework
plan: 04
subsystem: data-service
type: execute
tags:
  - model-viewer
  - state-payload
  - backward-compat
  - v2-envelope
depends_on: []
requires: []
affects:
  - data-service/app.py
  - data-service/tests/test_validation_runs_state.py
tech-stack:
  added: []
  patterns:
    - version-field envelope detection
key-files:
  modified:
    - data-service/app.py
    - data-service/tests/test_validation_runs_state.py
decisions:
  - "Return shape identical for v1 and v2: only {stateId, capturedAtUtc, parameterCount} — no stateKind field (deviates from RESEARCH.md prototype which included stateKind)"
metrics:
  duration: 6m
  tasks_completed: 2
  tests_added: 5
  tests_total: 14
status: complete
---

# Phase 18 Plan 04: Model Viewer Read-Side v2 Adaptation

Adapt the Model Viewer read-side (`_project_state_summary`) to handle v2 statePayloadJson envelopes while preserving v1 backward compatibility. The function detects the payload version via the root `version` field and counts elements from the appropriate arrays.

## Summary

The `_project_state_summary` function in `data-service/app.py` now checks `parsed.get("version") == "2"` to detect v2 envelopes. For v2 payloads, it counts elements from `objStates + paramStates + propStates` arrays instead of the v1 `parameters` array. The return shape is identical for both versions (`{stateId, capturedAtUtc, parameterCount}`), ensuring no JS changes are needed in the Model Viewer's `useValidationRunsGrouping.js` or `ValidationRunsStrip.jsx`.

Five new test functions cover: all three state kinds, empty arrays, missing arrays defaulting to zero, v1 fallback with no version field, and incompatible version ("1") falling back to parameters array. All 14 tests pass.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Adapt `_project_state_summary` for v2 envelope detection | `c4b17e7` | `data-service/app.py` |
| 2 | Extend Python tests with v2 envelope test cases | `4ef838f` | `data-service/tests/test_validation_runs_state.py` |

## Verification

- All 9 existing tests continue to pass (no regressions)
- All 5 new v2-specific tests pass
- `_project_state_summary` never raises on any input (tested with garbage, null, empty, arrays, non-object JSON)
- Return shape is identical for v1 and v2: both produce `{stateId, capturedAtUtc, parameterCount}`

## Deviations from Plan

### Specified Return Shape (Intentional Choice)

The `_project_state_summary` function does NOT include a `stateKind` field in the return dict, despite the RESEARCH.md showing one. This is intentional: the PLAN.md explicitly specifies that the return shape must be identical for v1 and v2 (same three keys only), and the UI-SPEC confirms this contract. The plan requirements take precedence over the research prototype.

## Threat Surface Scan

No new threat surface introduced. The existing try/except guards for `JSONDecodeError`, `ValueError`, `TypeError`, and `RecursionError` remain in place. The version-detection logic introduces no new network endpoints, auth paths, or file access patterns.

## Self-Check

- [x] `data-service/app.py` exists and modified with version-aware logic
- [x] `data-service/tests/test_validation_runs_state.py` exists with 14 test functions
- [x] Commit `c4b17e7` exists
- [x] Commit `4ef838f` exists
- [x] All 14 tests pass: `pytest tests/test_validation_runs_state.py -v`

## Self-Check: PASSED
