---
phase: 18-rules-and-validator-rework
plan: 05
subsystem: validator
tags: grasshopper, ghost-document, csharp, fastapi, validation, ghvl-03, ghvl-05

requires:
  - phase: 18-01
    provides: DesignStateBindingService for binding resolution from Rule + DesignState
  - phase: 16
    provides: DesignStatePayloadV2Serializer for v2 state JSON serialization
  - phase: 17
    provides: Neo4jValidGraphRepository for v1+v2 payload reads

provides:
  - Rewritten ValidatorComponent with 4-input/8-output contract using DesignStateBindingService
  - Extended ValidationPublishClient with v2 serialization and ValidStatus passthrough
  - Extended ValidationPublishContract with ValidStatus field
  - Extended data-service store_validation_run to accept passed validStatus

affects:
  - Phase 19: model-viewer grouping by stateId from statePayloadJson

tech-stack:
  added: []
  patterns:
    - DesignStateBindingService replaces CLASSIFICATOR for variable binding resolution
    - ValidStatus computed per-D-01/D-02: index-matched to ObjStates, non-matching excluded from AND
    - v2 DesignState payload serialization via DesignStatePayloadV2Serializer
    - Python-side backward compat guard: valid_status_param is not None

key-files:
  created: []
  modified:
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs (rewritten)
    - DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs (extended)
    - DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs (extended)
    - DG/src/DG.Core/Services/ValidationRunPersistenceService.cs (extended)
    - data-service/app.py (extended)

key-decisions:
  - "ValidationPublishClient.Publish replaces ParamState? parameter with DesignState? + List<bool>? pair"
  - "ValidStatus property on ValidationPublishRequest set to { get; set; } (not init) — assigned after BuildRequest"
  - "DesignState aliased as CoreDesignState in ValidationPublishClient to resolve DG.DesignState ambiguity"

requirements-completed: [GHVL-03, GHVL-05]

duration: 12min
completed: 2026-07-05
status: complete
---

# Phase 18 Plan 05: Validator Rewrite — DesignState-driven contract with v2 publish path

**VALIDATOR accepts Rule + DesignState + SendValid + DataServiceUrl, produces per-ObjState ValidStatus via DesignStateBindingService, publishes with statePayloadJson v2 on SendValid=true**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-05T13:05:00Z
- **Completed:** 2026-07-05T13:17:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Rewrote ValidatorComponent to accept single Rule + DesignState + SendValid + DataServiceUrl (4 inputs, 8 outputs) per GHVL-03
- ValidStatus computed per D-01/D-02: index-matched to DesignState.ObjStates order; non-matching ObjStates (ClassIri mismatch per D-05) set to false but excluded from overall pass AND
- Uses DesignStateBindingService.BuildBindings for variable binding resolution (replaces CLASSIFICATOR)
- Extended ValidationPublishContract with ValidStatus (List<bool>?) field
- Extended ValidationPublishClient.Publish with DesignState? + List<bool>? parameters, v2 serialization via DesignStatePayloadV2Serializer
- Extended data-service app.py: validStatus field on ValidationPublishRequest, store_validation_run accepts valid_status_param with backward compat fallback, publish_validation handler passes it through
- Extended ValidationRunPersistenceService with AttachDesignStateV2 and ValidateDesignStatePayload (auto-detects v1 vs v2)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite ValidatorComponent with new contract** - `87ca9e1` (feat)
2. **Task 2: Extend publish path — ValidationPublishClient, Contract, data-service** - `dba7041` (feat)
3. **Task 3: Extend ValidationRunPersistenceService for v2 DesignState** - `8b60073` (feat)

## Files Modified

- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` — Complete rewrite: 4 inputs (Rule, DesignState, SendValid, DataServiceUrl), 8 outputs (ValidStatus, RuleName, RuleDescription, Report, FailingBindings, SendStatus, ValidationRunId, ModelViewerUrl), uses DesignStateBindingService + RuleEvaluator
- `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` — Added ValidStatus (List<bool>?) to ValidationPublishRequest
- `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` — New Publish signature with DesignState? + List<bool>?, v2 serialization using DesignStatePayloadV2Serializer
- `DG/src/DG.Core/Services/ValidationRunPersistenceService.cs` — Added AttachDesignStateV2 and ValidateDesignStatePayload (auto-detect v1/v2)
- `data-service/app.py` — Added validStatus field to request model, modified store_validation_run and publish_validation handler

## Decisions Made

- **DesignState aliased as CoreDesignState** in ValidationPublishClient to resolve namespace collision between DG.Core.Models.DesignState and DG.DesignState (public Grasshopper wrapper)
- **ValidStatus property set to { get; set; }** on ValidationPublishRequest (not { get; init; }) because it is assigned after the BuildRequest object is constructed — matches runtime-assignment pattern
- **Backward compat for Python**: store_validation_run checks `valid_status_param is not None` — pre-v7.0 clients without the field still work via entity-based computation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] DesignState namespace ambiguity in ValidationPublishClient**
- **Found during:** Task 2 (build verification)
- **Issue:** `DesignState` in ValidationPublishClient resolved to `DG.DesignState` (public Grasshopper wrapper) instead of `DG.Core.Models.DesignState`, causing CS1503 conversion error
- **Fix:** Added `using CoreDesignState = DG.Core.Models.DesignState;` alias and used `CoreDesignState?` in method parameters
- **Files modified:** `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs`
- **Verification:** dotnet build succeeds after fix
- **Committed in:** dba7041 (Task 2 commit)

**2. [Rule 3 - Blocking] ValidStatus init-only property assigned after construction**
- **Found during:** Task 2 (build verification)
- **Issue:** `request.ValidStatus = validStatus;` failed with CS8852 because `ValidStatus` was declared `{ get; init; }`
- **Fix:** Changed to `{ get; set; }` — matches post-construction assignment pattern
- **Files modified:** `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs`
- **Verification:** dotnet build succeeds after fix
- **Committed in:** dba7041 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking)
**Impact on plan:** Both fixes necessary for compilation. No scope creep.

## Issues Encountered

- None beyond the auto-fixed compilation issues documented above. All plan tasks executed as specified.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- ValidatorComponent fully rewritten with new DesignState-driven contract
- Publish path sends v2 statePayloadJson with index-matched ValidStatus
- DATA-SERVICE has Python-side backward-compatible validStatus handling (pre-v7.0 clients fall back to entity computation)
- Ready for Phase 19 (model-viewer grouping by stateId from statePayloadJson)
- Integration test coverage (Neo4j-based E2E) requires live database — 4 pre-existing Neo4j E2E tests failed as expected in this environment; all 179 unit tests pass

## Self-Check: PASSED

- Commits verified: 87ca9e1, dba7041, 8b60073 exist in git log
- Build verified: `dotnet build DG/DG.sln --no-restore` succeeds (0 errors, 0 warnings)
- No `using DG.Core.Classification` in any modified file
- All 179 unit tests pass (4 Neo4j E2E tests fail due to environment — pre-existing)
- All modified files exist and contain expected changes

---
*Phase: 18-rules-and-validator-rework*
*Completed: 2026-07-05*
