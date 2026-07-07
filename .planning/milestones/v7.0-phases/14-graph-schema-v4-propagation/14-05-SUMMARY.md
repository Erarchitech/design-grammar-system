---
phase: 14-graph-schema-v4-propagation
plan: 05
subsystem: api, database
tags: validation-run, valid-status, send-status, validgraph, schema-v4
requires:
  - phase: 13-ontology-v7-and-contract-investigation
    provides: D-01 Run validation model (ValidStatus/SendStatus), D-14 ValidGraph layer literal
provides:
  - ValidStatus/SendStatus as schema-present properties on ValidationRun in data-service
  - ValidGraph as the canonical runtime layer literal across all code
affects:
  - 14-06 (data migration of 1169 live nodes to ValidGraph)
  - Phase 18 (full per-ObjState ValidStatus population)

tech-stack:
  added: []
  patterns:
    - "Schema-present properties added alongside existing job-lifecycle status (run.status='completed' untouched)"
    - "Best-effort ValidStatus computation from existing entities data, not full index-matched binding"

key-files:
  created: []
  modified:
    - data-service/app.py
    - DG/src/DG.Core/Services/ValidationRunsQueryService.cs
    - DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs

key-decisions:
  - "ValidStatus added as best-effort per-entity Boolean list; full per-ObjState index-matched population deferred to Phase 18 (GHVL-05)"
  - "SendStatus set true on successful publish (directly knowable today)"
  - "run.status='completed' left untouched — it tracks publish-job lifecycle, distinct from the removed Run.Status pass/fail text field"
  - "VALIDATION_GRAPH constant VALUE renamed to ValidGraph; constant identifier names (C# ValidationGraph, Python VALIDATION_GRAPH) left unchanged per plan scope"

patterns-established:
  - "Schema presence first: add properties as schema-proven placeholders before full binding logic lands in later phases"

requirements-completed: [SCHM-12]

coverage:
  - id: D1
    description: "ValidStatus/SendStatus properties added to data-service validation run CRUD (store, get, list)"
    requirement: SCHM-12
    verification:
      - kind: other
        ref: "grep -q 'ValidStatus' data-service/app.py && grep -q 'SendStatus' data-service/app.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "run.status='completed' untouched (not conflated with removed Run.Status text field)"
    requirement: SCHM-12
    verification:
      - kind: other
        ref: "grep -q \"run.status = 'completed'\" data-service/app.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Runtime layer literal renamed from ValidationGraph to ValidGraph in all code: app.py, ValidationRunsQueryService.cs, E2E tests"
    requirement: SCHM-12
    verification:
      - kind: other
        ref: "grep -rn 'ValidGraph' data-service/app.py DG/src/DG.Core/Services/ValidationRunsQueryService.cs DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs"
        status: pass
      - kind: other
        ref: "DG.Core + DG.Tests build clean (Release, 0 warnings/errors)"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-07-03
status: complete
---

# Phase 14 Plan 05: ValidStatus/SendStatus Schema Presence + ValidGraph Literal Rename (D-14 code half)

**ValidStatus and SendStatus added as schema-present properties on ValidationRun in data-service, and the runtime layer literal renamed from ValidationGraph to ValidGraph across all three code files (app.py, C# service, E2E tests), ready for 14-06 to migrate the 1169 live data nodes.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-03T13:10:00Z
- **Completed:** 2026-07-03T13:28:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `run.ValidStatus` (best-effort per-entity Boolean list computed from existing failed/passed data) and `run.SendStatus` (Boolean, true on successful publish) to `store_validation_run` MERGE/SET in `app.py`; left `run.status='completed'` untouched (job lifecycle, distinct from the removed Run.Status pass/fail text field)
- Added `run.ValidStatus AS validStatus, run.SendStatus AS sendStatus` to RETURN clauses of `get_validation_run` and `list_validation_runs`
- Updated v3-era comment vocabulary references to v4 kind names (DefState→ParamState, ObjectState→ObjState) in `app.py`
- Renamed the runtime layer literal from `"ValidationGraph"` to `"ValidGraph"` in all three code locations: `app.py` VALIDATION_GRAPH constant, `ValidationRunsQueryService.cs` constant value, and 5 hardcoded occurrences in `DesignStateValidationFlowTests.cs`
- DG.Core and DG.Tests both build clean (Release, 0 warnings, 0 errors)
- Full per-ObjState index-matched ValidStatus population explicitly deferred to Phase 18 (GHVL-05); 1169 live-node data migration deferred to 14-06

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ValidStatus/SendStatus to data-service Run write and reads (SCHM-12)** - `6c4cd90` (feat)
2. **Task 2: Rename the runtime layer literal to ValidGraph in code (D-14 code half)** - `1dc6135` (feat)

## Files Created/Modified

- `data-service/app.py` - Added ValidStatus/SendStatus write (store_validation_run) and reads (get_validation_run, list_validation_runs); updated comment vocabulary to v4 kind names; renamed VALIDATION_GRAPH constant value to "ValidGraph"
- `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` - Renamed constant value from "ValidationGraph" to "ValidGraph"
- `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` - Updated 5 hardcoded `graph: 'ValidationGraph'` occurrences to `graph: 'ValidGraph'`

## Decisions Made

- **ValidStatus best-effort computation:** Computed as per-entity Boolean list from already-available `failedRuleIds` data in `store_validation_run`; this is schema-presence-only placeholder logic — full per-ObjState index-matched population is Phase 18 (GHVL-05) work
- **SendStatus directly knowable:** Set to `true` on successful publish call, reflecting the synchronous publish path
- **run.status='completed' preserved:** Confirmed semantically distinct from the removed Run.Status pass/fail text field (RESEARCH Pitfall 4)
- **Constant names unchanged:** Only the string VALUE changed to "ValidGraph"; the C# identifier `ValidationGraph` and Python `VALIDATION_GRAPH` constant names remain as-is per plan scope

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Code is ready for 14-06 (data migration of 1169 live nodes from ValidationGraph to ValidGraph graph property value)
- Phase 18 (GHVL-05) owns the full per-ObjState index-matched ValidStatus population logic

## Self-Check: PASSED

- [x] All 3 modified files exist
- [x] Task 1 commit `6c4cd90` found
- [x] Task 2 commit `1dc6135` found
- [x] ValidStatus/SendStatus present in app.py; run.status='completed' intact
- [x] Layer literal renamed to ValidGraph across all 3 code files

---
*Phase: 14-graph-schema-v4-propagation*
*Completed: 2026-07-03*
