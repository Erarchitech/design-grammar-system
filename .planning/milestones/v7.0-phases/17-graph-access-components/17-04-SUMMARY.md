---
phase: 17-graph-access-components
plan: 04
subsystem: DG Grasshopper Plugin
tags:
  - graph-access
  - valid-graph
  - repository
  - component
  - async-load
  - validation-runs
  - v1-v2-compat
requires:
  - 17-01 (ValidGraphHandle, PublicTypes base, ValidationGraph24 icon)
  - 17-CONTEXT (D-03: Run.Status 1:1 paired, D-04: DesignState deduplication, D-05: Status per-ObjState, D-06: per-layer repository)
provides:
  - ValidGraph read access for downstream VALIDATOR run loading
  - Old VALIDATION RUNS GUID fully purged
affects:
  - DG/src/DG.Core/Data/
  - DG/src/DG.Grasshopper/Components/
  - DG/tests/DG.Tests/
tech-stack:
  added:
    - IValidGraphRepository interface (GetRunsAsync returning Run/Status/DesignState)
    - Neo4jValidGraphRepository (Cypher query targeting graph='ValidGraph', v1/v2 compat deserialization)
    - ValidationGraphComponent (async GH component with 3 outputs)
    - ValidGraph repository tests (15 xunit tests)
  patterns:
    - repository: single-async-method, ConnectionInfo + CancellationToken, result object return
    - component: async-load with ContinueWith + ScheduleSolution (MetagraphComponent pattern)
    - tests: internal accessor-based query validation (no reflection needed)
key-files:
  created:
    - DG/src/DG.Core/Data/IValidGraphRepository.cs
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
    - DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs
    - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs
  modified:
    - DG/src/DG.Core/Data/IValidGraphRepository.cs (RunInfo unsealed for public wrapper inheritance)
    - DG/src/DG.Grasshopper/PublicTypes.cs (added RunInfo public wrapper)
    - DG/src/DG.Grasshopper/DgIcons.cs (ValidationRuns24 removed)
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs (ParseRulesJson nullability fix)
  deleted:
    - DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs
    - DG/src/DG.Grasshopper/Properties/ValidationRuns24.png
decisions:
  - Neo4jValidGraphRepository is a NEW parallel class, not a modification of ValidationRunsQueryService (preserved for Phase 18 removal)
  - v1/v2 payload heuristic: check root JSON for stateKind/objStates keys to detect v2; fall back to DesignStateJsonSerializer for v1
  - Status constructed as per-ObjState Boolean list (overall AND of all rules per ObjState), single-element for v1
  - New GUID 95fc9d32-307e-41fd-a158-bfae49a3dc2a assigned to ValidationGraphComponent (replaces old A7F2C3E1)
  - RunInfo unsealed in Core (matching DesignState/ParamState/ObjState/PropState pattern) for public wrapper inheritance
  - Old VALIDATION RUNS GUID (A7F2C3E1) fully purged — zero remaining references across all .cs files
metrics:
  duration: "4m 30s"
  completed_date: "2026-07-04"
  tasks: 4
  files_created: 4
  files_modified: 4
  files_deleted: 2
  tests_added: 15
status: complete
---

# Phase 17 Plan 04: VALIDATION GRAPH Component and Repository

## One-liner

Created the VALIDATION GRAPH component and its backing repository (IValidGraphRepository + Neo4jValidGraphRepository) reading Run/Status/DesignState from the ValidGraph layer with v1/v2 payload compat, delivered 15 unit tests, and fully purged the old VALIDATION RUNS component (GUID A7F2C3E1, icon, PNG) from the plugin.

## Tasks Executed

### Task 1: Create IValidGraphRepository and Neo4jValidGraphRepository
- **Commit:** 03d4ecc
- **Files:**
  - `DG/src/DG.Core/Data/IValidGraphRepository.cs` — interface + ValidGraphQueryResult + RunInfo
  - `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` — sealed implementation with RunsQuery Cypher
- **Key details:**
  - RunsQuery targets `graph:'ValidGraph'` with `$project` parameterized isolation (T-17-09 mitigated)
  - TryParseDesignState handles v1 (ParamState-only) and v2 (3-part ObjState+ParamState+PropState) payloads with key-detection heuristic
  - Status constructed per-ObjState: `Enumerable.Repeat(overallPass, objStateCount)` for v2, single-element list for v1
  - DesignState deduplication by StateId across all runs (D-04) using HashSet
  - Try-catch around all JSON deserialization (T-17-10 mitigated)
  - QueryTimeout 20s from established pattern (T-17-12 accepted)
  - Internal accessors (TryParseDesignState, ParseRulesJson, ParseTimestamp, GetRunsQueryForTesting) exposed for testability via InternalsVisibleTo

### Task 2: Create ValidationGraphComponent (new GUID, async-load pattern, 3 outputs)
- **Commit:** 30682c3
- **Files:**
  - `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs` — full async component
  - `DG/src/DG.Core/Data/IValidGraphRepository.cs` — RunInfo unsealed for public wrapper
  - `DG/src/DG.Grasshopper/PublicTypes.cs` — added RunInfo : DG.Core.Data.RunInfo
- **Key details:**
  - Inputs: ValidGraphHandle (generic, from GRAPH DECONSTRUCT), Refresh (Boolean trigger)
  - Outputs: Run (RunInfo list), Status (Boolean list per-ObjState, generic), DesignState (deduplicated, generic)
  - GUID: 95fc9d32-307e-41fd-a158-bfae49a3dc2a (new, replaces old VALIDATION RUNS GUID)
  - Follows MetagraphComponent async pattern exactly: CancelPendingQuery, BuildRequestKey, edge-triggered refresh, ContinueWith + ScheduleSolution
  - Public wrapper mapping: ToPublicRunInfo, ToPublicDesignState with recursive ToPublicObjState/ToPublicParamState/ToPublicPropState
  - Graceful error handling: disconnected handle, refresh=false, fault/cancelation states

### Task 3: Create unit tests for VALIDATION GRAPH repository
- **Commit:** 372fefb
- **Files:**
  - `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` — 15 test methods
- **Key details:**
  - v1 payload returns ParamState-only DesignState
  - v2 payload via stateKind key returns full DesignState
  - v2 payload via objStates key (alternative heuristic path) returns DesignState with populated ObjStates
  - Null, empty, malformed JSON all return null gracefully
  - Dedup by StateId: 3 states (2 duplicates) -> 2 distinct
  - Status/Run 1:1 index matching (D-03)
  - RunQuery constant validation: graph='ValidGraph', $project, ORDER BY
  - ParseRulesJson: empty array, valid array with sorted results, null input
  - ParseTimestamp: valid ISO 8601, null, empty string
  - No live Neo4j required — all tests use internal static accessors

### Task 4: Remove ValidationRunsComponent.cs, DgIcons.ValidationRuns24, and stale PNG
- **Commit:** fa3a72d
- **Files:**
  - Deleted: `DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs` (old GUID A7F2C3E1)
  - Deleted: `DG/src/DG.Grasshopper/Properties/ValidationRuns24.png`
  - Modified: `DG/src/DG.Grasshopper/DgIcons.cs` (ValidationRuns24 entry removed)
  - Modified: `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` (ParseRulesJson nullability fix)
- **Key details:**
  - Old GUID A7F2C3E1 fully purged — zero remaining references across DG/ directory
  - ValidationRunsQueryService NOT modified (preserved for Phase 18 removal)
  - Build succeeds with 0 errors, 0 warnings after cleanup

## Success Criteria Check

| Criterion | Status |
|-----------|--------|
| GHGA-05: VALIDATION GRAPH outputs Run / Status / DesignState from ValidGraph | Done |
| Run-Status 1:1 index-matched parallel lists (D-03) | Verified in test and implementation |
| DesignState deduplicated by StateId across all runs (D-04) | Verified (HashSet<string> in repository + test) |
| Status[i] = IReadOnlyList&lt;bool&gt; per-ObjState (D-05) | Verified (Enumerable.Repeat for v2, single-element for v1) |
| v1 ParamState-only payloads parsed gracefully into DesignState | Tested (v1 heuristic + DesignStateJsonSerializer fallback) |
| New GUID replaces old VALIDATION RUNS GUID | Verified (95fc9d32 new, A7F2C3E1 zero refs) |
| ValidationRunsComponent.cs deleted, DgIcons.ValidationRuns24 removed | Done |
| Build succeeds (0 errors, 0 warnings) | Verified |
| Full test suite passes (176/176) | Verified |

## Verification

- `dotnet build DG/DG.sln` — passes (0 warnings, 0 errors)
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ValidGraphRepository"` — 15/15 passed
- `dotnet test DG/tests/DG.Tests/` — 176/176 passed (full suite)

## Deviations

### Auto-fixed Issues

**1. [Rule 2 - Missing Functionality] RunInfo sealed in Core blocked public wrapper inheritance**
- **Found during:** Task 2 build validation
- **Issue:** `RunInfo` was declared `sealed` in `DG.Core.Data`, preventing `DG.Grasshopper` from creating a public wrapper (error CS0509)
- **Fix:** Unsealed `RunInfo` in `DG/src/DG.Core/Data/IValidGraphRepository.cs` to match the pattern of `DesignState`, `ParamState`, `ObjState`, `PropState` (all unsealed in Core for public wrapper inheritance)
- **Files modified:** `DG/src/DG.Core/Data/IValidGraphRepository.cs`

**2. [Rule 2 - Missing Functionality] ParseRulesJson parameter not nullable despite handling null**
- **Found during:** Test compilation warning
- **Issue:** `ParseRulesJson(string rulesJson)` accepted non-nullable string but the implementation checked for null internally; tests passed `null` producing CS8625 warning
- **Fix:** Changed parameter type to `string?` to match implementation's null-handling contract
- **Files modified:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs`

## Threat Surface

No new threat surface beyond the planned STRIDE register:

| Threat ID | Category | Disposition | Status |
|-----------|----------|-------------|--------|
| T-17-09 | Tampering | mitigate (parameterized $project) | All queries use $project parameter |
| T-17-10 | Tampering | mitigate (try-catch on JSON) | TryParseDesignState catches JsonException + InvalidOperationException |
| T-17-11 | Information Disclosure | accept — validation results | Same sensitivity as old VALIDATION RUNS |
| T-17-12 | Denial of Service | accept — QueryTimeout 20s | Implemented on GetRunsAsync |

## Known Stubs

None. The v1/v2 payload heuristic gracefully handles Phase 17's v1-only data environment. Phase 18 will write v2 payloads, and the heuristic will detect them automatically.

## Artifacts

| Symbol | Kind | File |
|--------|------|------|
| `IValidGraphRepository` | interface (NEW) | DG/src/DG.Core/Data/IValidGraphRepository.cs |
| `ValidGraphQueryResult` | sealed class (NEW) | DG/src/DG.Core/Data/IValidGraphRepository.cs |
| `RunInfo` | class (NEW, unsealed) | DG/src/DG.Core/Data/IValidGraphRepository.cs |
| `IValidGraphRepository.GetRunsAsync` | method (NEW) | DG/src/DG.Core/Data/IValidGraphRepository.cs |
| `Neo4jValidGraphRepository` | sealed class (NEW) | DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs |
| `Neo4jValidGraphRepository.RunsQuery` | private const string (NEW Cypher) | DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs |
| `Neo4jValidGraphRepository.TryParseDesignState` | internal static method (NEW) | DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs |
| `DG.Grasshopper.Components.ValidationGraphComponent` | class (NEW GH component) | DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs |
| VALIDATION GRAPH ComponentGuid | `95fc9d32-307e-41fd-a158-bfae49a3dc2a` | DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs |
| `ValidationRunsComponent.cs` | file DELETED | DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs |
| `DgIcons.ValidationRuns24` | icon entry REMOVED | DG/src/DG.Grasshopper/DgIcons.cs |
| `ValidationRuns24.png` | file DELETED | DG/src/DG.Grasshopper/Properties/ValidationRuns24.png |

## Self-Check

- [x] All task commits verified in git log (4 commits for this plan)
- [x] Build succeeded (0 errors, 0 warnings)
- [x] Full test suite passed (176/176)
- [x] All created files exist on disk
- [x] ValidationRunsComponent.cs and stale PNG confirmed deleted
- [x] Old GUID A7F2C3E1 zero remaining references
- [x] No unexpected file deletions detected
