---
phase: 03-validation-runs-retrieval-component
plan: 01
subsystem: grasshopper-plugin
tags: [csharp, neo4j, grasshopper, design-state, validation-runs, xunit]

# Dependency graph
requires:
  - phase: 02-classificator-state-input-and-run-persistence
    provides: ValidationRunRecord model, ClassificatorComponent optional State input
  - phase: 01-design-state-contract-and-serialization
    provides: DesignStateSnapshot, DesignStateParameter, DesignStateJsonSerializer
provides:
  - ValidationRunQueryResult deterministic output schema
  - ValidationRunsQueryService with optional ruleId/stateId filtering against Neo4j
  - ValidationRunsComponent GH component (Connection, Rule, State, Refresh inputs; Runs, Results, States, Status outputs)
  - 39 total passing tests (14 new + 25 existing)
affects:
  - 04-reinstatement-component
  - 05-model-viewer-grouping-by-rule-state

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Async GH component with CancelPendingQuery/StartQuery lifecycle (mirrors MetagraphComponent)
    - Deterministic output ordering via StringComparer.Ordinal on RuleIds and Results
    - Graceful state deserialization (malformed JSON returns null state, not exception)
    - In-process stateId filter after retrieval (ruleId filter pushed into Cypher WHERE clause)

key-files:
  created:
    - DG/src/DG.Core/Models/DesignStateParameter.cs
    - DG/src/DG.Core/Models/DesignStateSnapshot.cs
    - DG/src/DG.Core/Models/ValidationRunRecord.cs
    - DG/src/DG.Core/Models/ValidationRunQueryResult.cs
    - DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs
    - DG/src/DG.Core/Services/ValidationRunPersistenceService.cs
    - DG/src/DG.Core/Services/ValidationRunsQueryService.cs
    - DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs
    - DG/tests/DG.Tests/DesignStateJsonSerializerTests.cs
    - DG/tests/DG.Tests/ValidationRunPersistenceTests.cs
    - DG/tests/DG.Tests/ValidationRunsQueryTests.cs
  modified:
    - DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs
    - DG/src/DG.Grasshopper/PublicTypes.cs

key-decisions:
  - "ValidationRunQueryResult.RuleIds and Results sorted by StringComparer.Ordinal for stable downstream grouping"
  - "stateId filter applied in-process (not Cypher) to enable deserialization-based matching without SWRL schema changes"
  - "ruleId filter pushed into Cypher WHERE clause via CONTAINS on rulesJson string — fast for string filter, sufficient for this data volume"
  - "Malformed statePayloadJson surfaces null state without throwing — resilient to partial data from legacy runs"
  - "ValidationRunsComponent follows MetagraphComponent async pattern exactly for consistency"

patterns-established:
  - "GH async component: cancel-on-restart with _queryCts/CancelPendingQuery/StartQuery pattern"
  - "Results output format: '{runId}|{ruleId}:{passed}' — one line per rule per run"
  - "States output: only populated for runs with non-null State (empty list when none)"

requirements-completed:
  - DGCL-03
  - DGRN-01
  - DGRN-02
  - DGRN-03

# Metrics
duration: 35min
completed: 2026-05-03
---

# Phase 03 Plan 01: Validation Runs Retrieval Component Summary

**VALIDATION RUNS GH component querying Neo4j ValidationRun nodes with optional Rule/State filters, deterministic Runs/Results/States output schema, and 39 passing tests**

## Performance

- **Duration:** 35 min
- **Started:** 2026-05-03T17:30:00Z
- **Completed:** 2026-05-03T18:05:00Z
- **Tasks:** 5 commits (prerequisite models + 4 main tasks)
- **Files modified:** 13

## Accomplishments

- Full DesignState type system: DesignStateParameter, DesignStateSnapshot, ValidationRunRecord, and round-trip JSON serializer
- ValidationRunPersistenceService stores design state alongside run metadata; Classificator gains optional State input
- ValidationRunQueryResult provides deterministic output schema (RuleIds + Results sorted by Ordinal, stable across identical inputs)
- ValidationRunsQueryService queries Neo4j with ruleId Cypher filter + in-process stateId filter; graceful null on malformed state
- ValidationRunsComponent GH component with 4 inputs / 4 outputs following MetagraphComponent async lifecycle pattern
- 39 tests all passing (build: 0 warnings, 0 errors)

## Task Commits

Each task was committed atomically:

1. **Task 1: DesignState models + JSON serializer** - `5435853` (feat)
2. **Task 2: ValidationRunPersistenceService + Classificator State input** - `219559d` (feat)
3. **Task 3: ValidationRunQueryResult model + ValidationRunsQueryService** - `582e2d8` (feat)
4. **Task 4: ValidationRunsComponent GH component** - `dd8ddac` (feat)
5. **Task 5: ValidationRunsQueryTests** - `faf3f33` (test)

## Files Created/Modified

- `DG/src/DG.Core/Models/DesignStateParameter.cs` — Number/Integer/Boolean typed value fields with DesignStateParameterType enum
- `DG/src/DG.Core/Models/DesignStateSnapshot.cs` — StateId, CapturedAtUtc, Parameters collection
- `DG/src/DG.Core/Models/ValidationRunRecord.cs` — RunId, Project, Graph, RuleIds list, optional StatePayloadJson
- `DG/src/DG.Core/Models/ValidationRunQueryResult.cs` — Deterministic output schema for downstream reinstatement and UI grouping
- `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs` — Round-trip serialization with camelCase JSON and parameter type validation
- `DG/src/DG.Core/Services/ValidationRunPersistenceService.cs` — AttachDesignState + ValidateRunRecord with clear error messages
- `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` — Neo4j query with ruleId WHERE filter, in-process stateId filter, graceful state parse
- `DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs` — GH component (async, cancel-on-restart, 4 inputs, 4 outputs)
- `DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs` — Added optional State input at index 3
- `DG/src/DG.Grasshopper/PublicTypes.cs` — Added DesignStateSnapshot and DesignStateParameter public proxy types
- `DG/tests/DG.Tests/DesignStateJsonSerializerTests.cs` — Serialize/deserialize roundtrip for all parameter types
- `DG/tests/DG.Tests/ValidationRunPersistenceTests.cs` — State-present and state-absent persistence paths
- `DG/tests/DG.Tests/ValidationRunsQueryTests.cs` — Query filters, schema consistency, empty results, project isolation

## Decisions Made

- **Deterministic ordering**: RuleIds and Results sorted with StringComparer.Ordinal — essential for downstream grouping in Model Viewer
- **stateId filter in-process**: Neo4j doesn't know the state ID (it's embedded in statePayloadJson JSON field); filtering after retrieval avoids complex JSON parsing in Cypher while keeping the service pure-C#
- **ruleId filter in Cypher**: CONTAINS on rulesJson string is simple and fast enough for this data volume; avoids bringing all runs to the application layer
- **Graceful state deserialization**: Malformed or legacy statePayloadJson returns null state without throwing — old runs without state field stay usable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added prerequisite phase 01 and 02 artifacts**
- **Found during:** Task setup (model directory inspection)
- **Issue:** Phase 03-01 depended on DesignState models and Serializer (phase 01) and PersistenceService + Classificator (phase 02), but these were never committed to the worktree branch
- **Fix:** Copied and committed all prerequisite files from the main working directory to the worktree, staged in two additional commits before the phase 03 work
- **Files modified:** All DG.Core models, Serialization, Services, Grasshopper PublicTypes and ClassificatorComponent, phase 01/02 tests
- **Verification:** Build passes with 0 warnings; all 39 tests green

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing prerequisite artifacts)
**Impact on plan:** Essential prerequisite — phase 03 cannot compile without phase 01/02 types. No scope creep.

## Issues Encountered

- Worktree branch was missing phases 01 and 02 artifacts (only existed as untracked files in the main working directory). Resolved by copying files from main to worktree before committing.

## User Setup Required

None - no external service configuration required. The VALIDATION RUNS component requires a live Neo4j connection to query `ValidationRun` nodes.

## Next Phase Readiness

- Phase 04 (REINSTATE component) can consume the `States` output from VALIDATION RUNS directly
- ValidationRunQueryResult.StatePayloadJson carries the full serialized state for reinstatement without re-serialization
- Phase 05 (Model Viewer grouping) can use the `Results` output format (`{runId}|{ruleId}:{passed}`) for group-by-rule logic

---
*Phase: 03-validation-runs-retrieval-component*
*Completed: 2026-05-03*
