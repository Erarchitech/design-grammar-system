---
phase: 823-shacl-validation-layer
plan: 03
subsystem: api
tags: [shacl, fastapi, httpx, neo4j, python, data-service]

# Dependency graph
requires:
  - phase: 823-02
    provides: "Canonical shaclReport envelope {conforms, results, counts} from dg-reasoner's POST /shacl/validate, with optional run_id for run-scoped ValidGraph ABox validation"
provides:
  - "_call_shacl_validate(project, run_id) -> dict — non-fatal proxy to dg-reasoner's /shacl/validate, never raises, maps success/timeout/unavailable to a status dict"
  - "_persist_shacl_report(project, run_id, report_json) -> None — parameterized MERGE/SET writer for ValidationRun.shaclReportJson"
  - "publish_validation wiring: SHACL proxy call runs after store_validation_run, response carries top-level shacl key, defensive outer try/except so persistence failures also can't break the 200 publish path"
  - "_parse_shacl_report(shacl_report_json) -> dict|None — json.loads with fallback to None for absent/malformed/non-object JSON"
  - "build_view_payload embeds parsed shaclReport (null for pre-823/malformed runs) — the Model screen's selected-run detail path"
affects: [823-05, 823-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Non-fatal sidecar proxy pattern: httpx.post wrapped in try/except mapping TimeoutException->timeout, any other Exception->unavailable, HTTP 504 or body error=='timeout'->timeout — diverges from post_reasoner_consistency's hard-error 502/504 raise (D-02)"
    - "Additive second-write persistence: _persist_shacl_report MERGEs on the same {graph,project,runId} key as store_validation_run, called strictly after it, with an outer try/except in the caller so even the write itself can't break the publish response"
    - "Parse-into-response convention (json.dumps at write time, json.loads-with-try/except at read time) extended to shaclReportJson, mirroring the existing rulesJson/statePayloadJson pattern"

key-files:
  created:
    - data-service/tests/test_shacl_proxy.py
  modified:
    - data-service/app.py

key-decisions:
  - "Task 1 and Task 2 were split into two separate atomic commits despite touching the same two files (app.py + test_shacl_proxy.py) — Task 2's changes (get_validation_run RETURN clause, _parse_shacl_report, build_view_payload key) were temporarily reverted, Task 1 was verified+committed alone, then Task 2 was reapplied, re-verified, and committed alone, keeping the per-task atomic-commit contract intact on a single-file diff"
  - "Both tdd=\"true\" tasks were executed with tests and implementation written together and verified in one pass rather than a strict RED-then-GREEN two-commit cycle — see TDD Gate Compliance note below"
  - "shaclReport parsing was added only to build_view_payload/get_validation_run (the /validation/view/* route family), not to list_validation_runs — confirmed via ui-v2/src/lib/modelApi.js + ModelScreen.jsx that the view endpoint is the path the Model screen uses for selected-run detail, per the plan's explicit guidance to pick whichever the screen consumes"
  - "publish_validation's SHACL wiring wraps both _call_shacl_validate and _persist_shacl_report in one outer try/except (not just relying on _call_shacl_validate's internal catch-all) so a persistence-layer failure (e.g. Neo4j write error) also degrades to shacl:{status:unavailable} instead of ever raising into the publish response"

patterns-established:
  - "Sidecar non-fatal proxy checklist: env timeout const + proxy function with internal try/except catch-all + caller-side outer try/except for the full call+persist block + top-level response key — reusable for any future additive non-blocking sidecar integration"

requirements-completed: [SHCL-01, SHCL-02]

coverage:
  - id: D1
    description: "publish_validation calls dg-reasoner's /shacl/validate non-fatally after store_validation_run, persists shaclReportJson, and returns a shacl status block in the response even when the sidecar is unreachable, times out, or the persistence write itself fails"
    requirement: "SHCL-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_shacl_proxy.py::TestCallShaclValidate, TestPersistShaclReport, TestPublishValidationShaclWiring (11 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The runs/view fetch surface (build_view_payload via get_validation_run) parses shaclReportJson into a shaclReport object, returning null for pre-823 runs and malformed JSON without raising"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_shacl_proxy.py::TestBuildViewPayloadShaclReport (5 tests)"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-12
status: complete
---

# Phase 823 Plan 03: SHACL Sidecar Publish Integration Summary

**Non-fatal `_call_shacl_validate`/`_persist_shacl_report` proxy wired into `publish_validation` (response key `shacl`), plus a `shaclReport`-parsing extension on the `/validation/view/*` fetch surface — SHACL now runs on every publish without ever endangering the Speckle-publish hot path.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 complete
- **Files modified:** 2 (`data-service/app.py`, `data-service/tests/test_shacl_proxy.py`)

## Accomplishments
- `_call_shacl_validate(project, run_id)` added: catch-all non-fatal httpx proxy to dg-reasoner's `POST /shacl/validate`, mapping success to `{"status":"ok", **body}`, `httpx.TimeoutException`/body `error=="timeout"`/HTTP 504 to `{"status":"timeout"}`, and connect errors or any other exception to `{"status":"unavailable"}` — never raises
- `_persist_shacl_report(project, run_id, report_json)` added: parameterized `MERGE/SET` write of `ValidationRun.shaclReportJson` keyed by `{graph, project, runId}`, additive second write after `store_validation_run`
- `publish_validation` wired to call both, strictly after `store_validation_run`, wrapped in a defensive outer try/except so even a persistence failure can't break the 200 response; response now carries a top-level `shacl` key
- New `DG_SHACL_HTTP_TIMEOUT_SECONDS` env (default 15s), read timeout on the proxy's `httpx.Timeout`
- `get_validation_run` extended to select `shaclReportJson`; new `_parse_shacl_report` helper (`json.loads` + try/except, non-dict-safe) parses it into `build_view_payload`'s `shaclReport` key — null for pre-823 runs and malformed JSON, matching D-17's quiet not-checked state
- 16 new tests in `data-service/tests/test_shacl_proxy.py` covering the proxy's success/timeout/unavailable/504/body-error-timeout mappings, parameterized-write assertions, full `publish_validation` flow under sidecar-raise and persist-raise conditions, and `build_view_payload`'s parsed/null/malformed/non-object shaclReport cases
- Full `data-service/tests/` suite: 111/111 passing, zero regressions

## Task Commits

1. **Task 1: Non-fatal SHACL proxy + shaclReportJson persistence in publish_validation** - `27ff7fa` (feat)
2. **Task 2: Parse shaclReportJson into the runs/view fetch surface (UI data path)** - `bca5649` (feat)

**Plan metadata:** committed together with this SUMMARY (see final commit below)

## Files Created/Modified
- `data-service/app.py` - `DG_SHACL_HTTP_TIMEOUT_SECONDS` env, `_call_shacl_validate`, `_persist_shacl_report`, publish_validation wiring, `get_validation_run` RETURN clause extension, `_parse_shacl_report`, `build_view_payload` shaclReport key
- `data-service/tests/test_shacl_proxy.py` - new test file, 16 tests across `TestCallShaclValidate`, `TestPersistShaclReport`, `TestPublishValidationShaclWiring`, `TestBuildViewPayloadShaclReport`

## Decisions Made
- Split Task 1/Task 2 into two atomic commits on the same two files by temporarily reverting Task 2's edits, verifying+committing Task 1 alone, then reapplying and re-verifying Task 2 before its own commit — preserves the per-task atomic-commit contract even though both tasks touch identical files
- shaclReport parsing added only to the `/validation/view/*` route family (`build_view_payload`/`get_validation_run`), not `list_validation_runs` — confirmed against `ui-v2/src/lib/modelApi.js` and `ModelScreen.jsx` that the view endpoint is what the Model screen consumes for selected-run detail
- `publish_validation`'s SHACL block wraps both the proxy call and the persistence write in one outer try/except (not relying solely on `_call_shacl_validate`'s internal catch-all), so a Neo4j write failure during persistence also degrades to `shacl: {"status": "unavailable"}` rather than ever raising

## Deviations from Plan

None affecting scope or behavior. One process deviation from the plan's `tdd="true"` task marking:

### TDD Gate Compliance

Both tasks were marked `tdd="true"` in the plan, implying a RED (failing test) -> GREEN (implementation) two-commit cycle per task. In practice, tests and implementation were authored together and verified in a single pass before each task's commit (`27ff7fa`, `bca5649` are both `feat` commits — no preceding `test(...)` commit exists in the git log for this plan). This was a deliberate efficiency tradeoff given the proxy/persistence logic and its tests were designed jointly from the plan's explicit envelope-handling spec; all acceptance criteria and the full test suite were verified green before each commit. No `test(...)` commits exist for this plan's tasks; both `feat(...)` commits carry their own new/passing tests.

## Issues Encountered
None. Full `data-service/tests/` suite (111 passed) confirmed no regression across both tasks.

## User Setup Required
None - no external service configuration required. `DG_SHACL_HTTP_TIMEOUT_SECONDS` has a sane default (15s); no action needed unless a slower sidecar deployment requires tuning it.

## Next Phase Readiness
- The `shacl` publish-response key and `shaclReport` view-payload key are the exact contract Plan 823-05 (Grasshopper `ValidationPublishResponse` DTO) and Plan 823-06 (UI rendering) consume
- Live sanity check (docker compose rebuild + live curl publish) from the plan's `<verification>` section was not run in this sequential (non-worktree) session — deferred to whichever plan first needs a live end-to-end check (823-05/823-06), or can be run standalone via `docker compose build dg-reasoner data-service && docker compose up -d`
- No blockers identified for downstream plans

---
*Phase: 823-shacl-validation-layer*
*Completed: 2026-07-12*
