---
phase: 05-model-viewer-grouping-by-rule-state
plan: 01
subsystem: data-service
tags: [api, validation-runs, state-projection, pytest, tdd]
dependency_graph:
  requires:
    - "Phase 03 Plan 01: statePayloadJson persistence path confirmed (ValidationRun node property)"
  provides:
    - "GET /validation/runs/{project} now returns 'state' field per run with stateId, capturedAtUtc, parameterCount"
    - "_project_state_summary helper: defensive JSON parser for statePayloadJson"
  affects:
    - "data-service/app.py list_validation_runs"
    - "Phase 05 Plan 02 frontend grouping: can now group by run.state.stateId"
tech_stack:
  added: []
  patterns:
    - "Defensive JSON projection: never raise on absent/malformed/deep-nested payloads"
    - "TDD: tests written as RED before implementation (GREEN)"
key_files:
  modified:
    - data-service/app.py
  created:
    - data-service/tests/test_validation_runs_state.py
decisions:
  - "RecursionError caught alongside JSONDecodeError: Python 3.11 (container) raises RecursionError on '[' * 1000; Python 3.14 (local dev) does not. Both runtimes must be covered."
  - "parameterCount included in projection: lets frontend label 'No parameters' buckets without re-fetching the full statePayloadJson"
  - "state appended as last key in run dict: preserves existing key order to avoid breaking other consumers"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-07T13:45:00Z"
  tasks_completed: 3
  files_changed: 2
requirements:
  - MVGP-02
---

# Phase 05 Plan 01: State Projection for Validation Runs Summary

**One-liner:** Defensive `statePayloadJson` projection adding `{stateId, capturedAtUtc, parameterCount}` to every run returned by `GET /validation/runs/{project}`, with `null` for absent or malformed payloads.

## What Was Built

Extended `data-service/app.py` so the `list_validation_runs` function:

1. Fetches `run.statePayloadJson` from Neo4j via an additional Cypher RETURN clause
2. Passes it through `_project_state_summary`, a private helper that defensively parses the JSON and returns a compact dict or `None`
3. Appends `"state": ...` as the final key of each run dict, preserving all existing key order

### Projection Shape Added

```json
"state": {
  "stateId": "8E3237433258150D",
  "capturedAtUtc": "2026-05-06T11:03:59.8516141Z",
  "parameterCount": 10
}
```

Or `"state": null` when the run has no state.

### Why parameterCount Is Included

The frontend (Plan 05-02) groups runs by `stateId`. Within a group it needs to label buckets — e.g., "10 parameters captured" vs "No parameters". Including `parameterCount` in the list projection avoids a second round-trip to fetch the full `statePayloadJson` just to count parameters.

### Defensive Parsing Strategy

`_project_state_summary` catches all of:
- `None` / empty string: early return `None`
- `json.JSONDecodeError`, `ValueError`, `TypeError`: malformed JSON
- `RecursionError`: Python 3.11 (the container runtime) raises this for deeply nested structures like `"[" * 1000` that Python 3.14 (local dev) handles silently

Any non-`dict` JSON value (array, string, number) also returns `None`. The function is declared to **never raise** under any input.

### MVGP-02 Frontend Unblock

Plan 05-02 requires a stable `stateId` per run to group the validation strip by Design State. That field is now available on every run in the `/validation/runs/{project}` response. Plan 05-02 can proceed without any further data-service changes.

## Test Coverage

9 pytest cases in `data-service/tests/test_validation_runs_state.py`:

| Test | Scenario |
|------|----------|
| `test_state_projection_valid_full_payload` | Full valid JSON → correct stateId, capturedAtUtc, parameterCount |
| `test_state_projection_none_returns_none` | `None` input → `None` |
| `test_state_projection_empty_string_returns_none` | `""` input → `None` |
| `test_state_projection_malformed_json_returns_none` | `"not-valid-json"` → `None` |
| `test_state_projection_non_object_json_returns_none` | Array/string/number JSON → `None` |
| `test_state_projection_missing_stateid_uses_empty_string` | Missing `stateId` → `""` (frontend treats as "No State" bucket) |
| `test_state_projection_missing_parameters_yields_zero_count` | Missing `parameters` key → `parameterCount: 0` |
| `test_state_projection_parameters_not_a_list_yields_zero_count` | `parameters` is string → `parameterCount: 0` |
| `test_state_projection_does_not_raise_on_garbage_input` | Garbage strings including deeply nested brackets → no exception |

All 20 tests pass in both local (Python 3.14) and container (Python 3.11) environments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Caught RecursionError for Python 3.11 container compatibility**
- **Found during:** Task 3 (container test run)
- **Issue:** `_project_state_summary` only caught `json.JSONDecodeError, ValueError, TypeError`. Python 3.11 raises `RecursionError` on `"[" * 1000` (1000 nested open brackets), which Python 3.14 silently handles. The garbage-input test failed inside the container.
- **Fix:** Added `RecursionError` to the exception tuple in the `except` clause
- **Files modified:** `data-service/app.py` (one character change)
- **Commit:** e3771c4

## Live Endpoint Verification

```
GET /validation/runs/TestA
count=18
run=9e485d1f state={'stateId': '8E3237433258150D', 'capturedAtUtc': '2026-05-06T11:03:59.8516141Z', 'parameterCount': 10}
run=43f8c162 state={'stateId': '8E3237433258150D', 'capturedAtUtc': '2026-05-06T06:02:31.2983738Z', 'parameterCount': 10}
run=a1d85abb state=None
OK
```

18 real runs returned — some with state, some without. All have the `state` key. Shape is correct.

## Commits

| Hash | Description |
|------|-------------|
| 477a1f1 | feat(05-01): add state projection to list_validation_runs (MVGP-02) |
| e3771c4 | fix(05-01): catch RecursionError in _project_state_summary for Python 3.11 |

## Self-Check: PASSED
