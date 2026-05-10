---
phase: 06-end-to-end-hardening-and-verification
plan: 02
subsystem: error-handling
tags: [python, fastapi, pytest, react, error-responses]

requires:
  - phase: 05-model-viewer-grouping-by-rule-state
    provides: Model-viewer fetch infrastructure and runsError pattern
provides:
  - Structured {error, hint, code} JSON error responses from validation endpoints
  - Pytest test coverage for error response shape
  - Model-viewer extractErrorMessage reads structured hint/error fields
affects: [06-03, model-viewer-error-handling]

tech-stack:
  added: []
  patterns: [Structured error response helper _structured_error_response]

key-files:
  created:
    - data-service/tests/test_error_responses.py
  modified:
    - data-service/app.py
    - graph-viewer/model-viewer/src/App.jsx

key-decisions:
  - "Used mock-based tests (patch Neo4j calls) so pytest works without Docker stack"
  - "extractErrorMessage prefers hint over error for user-facing display"

patterns-established:
  - "Structured error pattern: _structured_error_response(error, hint, code, status_code) for all validation endpoints"

requirements-completed: [INTG-03]

duration: 6min
completed: 2026-05-09
---

# Phase 06 Plan 02: Data-Service Structured Errors + Model-Viewer Error Handling Summary

**Structured {error, hint, code} JSON error responses from 8 validation endpoint error paths, with 3 pytest tests and model-viewer hint extraction**

## What Was Built

1. **`_structured_error_response` helper** in `data-service/app.py` — returns HTTPException with `{error, hint, code}` dict detail
2. **8 validation endpoint error paths** updated to use structured responses:
   - POST `/validation/publish`: SPECKLE_CONFIG_MISSING, SPECKLE_TOKEN_MISSING, PUBLISH_VALIDATION_ERROR, PUBLISH_INTERNAL_ERROR
   - DELETE `/validation/run/{project}/{run_id}`: RUN_NOT_FOUND, SPECKLE_TOKEN_MISSING, SPECKLE_IDS_MISSING, DELETE_VALIDATION_ERROR, DELETE_INTERNAL_ERROR
3. **3 pytest tests** verifying structured error body shape with mocked Neo4j
4. **`extractErrorMessage` in App.jsx** updated to read `hint` or `error` from object-typed `detail` responses

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | c709b9a | feat(06-02): add structured error responses to data-service validation endpoints |
| 2 | b55e0a1 | feat(06-02): add pytest for structured errors + model-viewer hint extraction |

## Verification

- `python -m pytest tests/test_error_responses.py -v` — 3 passed, 0 failed
- `_structured_error_response('test', 'hint', 'CODE', 400)` returns correct structured detail

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Neo4j not available in local test environment**
- **Found during:** Task 2
- **Issue:** Publish and delete endpoints hit Neo4j to check configs/runs; TestClient without Docker stack gets 500 before reaching the config-not-found path
- **Fix:** Used `unittest.mock.patch` to mock `get_integration_config` and `get_validation_run`
- **Files modified:** data-service/tests/test_error_responses.py

## Self-Check: PASSED
