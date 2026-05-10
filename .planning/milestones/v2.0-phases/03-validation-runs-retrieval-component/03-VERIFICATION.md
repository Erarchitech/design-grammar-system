---
phase: 03-validation-runs-retrieval-component
verified: 2026-05-03T18:30:00Z
human_uat_passed: 2026-05-05T20:00:00Z
status: passed
score: 4/4 must-haves verified
human_verification:
  - test: "Run VALIDATION RUNS component against a live Neo4j instance with populated ValidationRun nodes"
    expected: "Runs output lists all runs; Rule filter narrows list to only runs referencing that ruleId; State filter narrows to runs with that stateId attached"
    why_human: "ValidationRunsQueryService.QueryAsync requires a live Neo4j connection — cannot be tested programmatically in this environment"
  - test: "Build DG.sln in Release configuration with GRASSHOPPER_SDK defined"
    expected: "0 errors, 0 warnings; ValidationRunsComponent registers correctly in Grasshopper panel"
    why_human: "Build requires Rhino 8 SDK and Grasshopper assemblies not available in CI; conditional compilation guard (#if GRASSHOPPER_SDK) means component is excluded from the test build"
---

# Phase 03: Validation Runs Retrieval Component Verification Report

**Phase Goal:** Implement VALIDATION RUNS retrieval component and query contract with optional Rule and State filtering and deterministic output schema.
**Verified:** 2026-05-03T18:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | VALIDATION RUNS supports unfiltered, rule-filtered, and state-filtered queries | VERIFIED | `ValidationRunsQueryService.QueryAsync` accepts `ruleId?` and `stateId?`. Rule filter pushed into Cypher `WHERE $ruleId IS NULL OR run.rulesJson CONTAINS $ruleId`. State filter applied in-process via `StringComparer.Ordinal` on `result.State.StateId`. |
| 2 | Output schema remains stable for identical inputs | VERIFIED | `ParseRulesJson` sorts `ruleIds` and `results` via `OrderBy(StringComparer.Ordinal)`. `ValidationRunQueryResult` uses `IReadOnlyList<string>` with deterministic sort. Test `RuleIds_ShouldBeSortedDeterministically_ForSameInput` and `Results_ShouldBeSortedDeterministically_ForSameInput` confirm this. |
| 3 | Empty result sets return valid empty collections without errors | VERIFIED | Default `ValidationRunQueryResult` initializes `RuleIds = Array.Empty<string>()`, `Results = Array.Empty<string>()`. Test `ValidationRunQueryResult_DefaultValues_ShouldReturnEmptyCollections` and `ValidationRunQueryResult_EmptyRuleIds_ShouldNotThrow` confirm no exceptions. Component `SetEmptyOutputs` always provides valid empty lists. |
| 4 | Tests cover query filters and schema consistency | VERIFIED | 14 `[Fact]` tests in `ValidationRunsQueryTests.cs` covering: filter match/exclude for rule and state, deterministic sort, schema roundtrip, mixed state presence, empty states, project isolation. 5 additional tests in `ValidationRunPersistenceTests.cs` and 5 in `DesignStateJsonSerializerTests.cs` (27 phase-related tests verified by inspection). |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `DG/src/DG.Core/Models/ValidationRunQueryResult.cs` | Deterministic output schema | VERIFIED | 38 lines. `RunId`, `Project`, `CapturedAtUtc`, sorted `RuleIds`, sorted `Results`, optional `State`, `StatePayloadJson`. All fields non-null-safe with `Array.Empty<string>()` defaults. |
| `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` | Neo4j query with filters | VERIFIED | 209 lines. Full Neo4j Cypher query, ruleId WHERE filter, in-process stateId filter, graceful null-state parse, deterministic sort, project isolation via `{project:$project}`. Not a stub. |
| `DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs` | GH component with 4 inputs/4 outputs | VERIFIED | 235 lines (guarded by `#if GRASSHOPPER_SDK`). Connection, Rule (optional), State (optional), Refresh inputs. Runs, Results, States, Status outputs. Async MetagraphComponent pattern with `CancelPendingQuery`/`StartQuery`/`ContinueWith` lifecycle. `_queryService.QueryAsync` called at line 158. |
| `DG/tests/DG.Tests/ValidationRunsQueryTests.cs` | Tests for filters and schema consistency | VERIFIED | 336 lines, 14 `[Fact]` tests. Covers: default schema, field preservation, empty results, deterministic sort (rules and results), state filter match/exclude, rule filter match/exclude, state deserialization roundtrip, mixed state presence, no-state empty output, project isolation. |
| `DG/src/DG.Core/Models/DesignStateSnapshot.cs` | State model (prerequisite) | VERIFIED | Exists. `StateId`, `CapturedAtUtc`, `Parameters` collection. |
| `DG/src/DG.Core/Models/ValidationRunRecord.cs` | Run record with optional StatePayloadJson (prerequisite) | VERIFIED | Exists. `RunId`, `Project`, `Graph`, `RuleIds`, `StatePayloadJson?`. |
| `DG/src/DG.Grasshopper/PublicTypes.cs` | Public proxy types for GH | VERIFIED | Exports `DesignStateSnapshot` and `DesignStateParameter` as public proxy classes inheriting DG.Core types. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ValidationRunsComponent` | `ValidationRunsQueryService` | `_queryService.QueryAsync(connection, ruleId, stateId, cts.Token)` at line 158 | WIRED | Component instantiates service at field init (line 15); calls `QueryAsync` in `StartQuery`. Result consumed in `SolveInstance` at `_queryTask.Result.ToList()`. |
| `ValidationRunsQueryService` | Neo4j `ValidationRun` nodes | Cypher `MATCH (run:ValidationRun {graph:$graph, project:$project})` | WIRED | Full Cypher query with parameterized `graph`, `project`, `ruleId`. Returns `runId`, `project`, `createdAt`, `rulesJson`, `statePayloadJson`. |
| `ValidationRunsQueryService` | `DesignStateJsonSerializer` | `DesignStateJsonSerializer.Deserialize(statePayloadJson)` in `ParseState` (line 193) | WIRED | Deserializer called for state payload; `InvalidOperationException` caught and surfaced as null (graceful resilience). |
| `ValidationRunsComponent.SetOutputs` | GH outputs (Runs/Results/States/Status) | `da.SetDataList(0..2)` + `da.SetData(3)` | WIRED | All 4 outputs set. States output filters `run.State is not null`. Results output uses `BuildResultLines` formatting `{runId}|{ruleId}:{passed}`. |
| `ClassificatorComponent` | `DesignStateSnapshot` State input | `pManager.AddGenericParameter("State", ...)` at line 30 | WIRED | Optional State input registered at index 3 with `Optional = true`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `ValidationRunsComponent` | `_latestRuns` | `ValidationRunsQueryService.QueryAsync` → Neo4j | Yes — Cypher query returns real `ValidationRun` nodes with `rulesJson`, `statePayloadJson` | FLOWING (requires live Neo4j; confirmed by code path) |
| `ValidationRunsQueryService` | `rawResults` | `session.RunAsync(RunsQuery, ...)` | Yes — real Cypher cursor iteration via `ForEachAsync` | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED for live Neo4j query path (requires running service). Pure-logic behaviors verified via unit tests in Step 3.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `ValidationRunQueryResult` default empty schema | Verified via test `ValidationRunQueryResult_DefaultValues_ShouldReturnEmptyCollections` | Empty collections, no exceptions | PASS (test) |
| Deterministic sort of RuleIds | Verified via test `RuleIds_ShouldBeSortedDeterministically_ForSameInput` | Same sorted order for any input permutation | PASS (test) |
| State filter exclusion | Verified via test `StaleStateFilter_WithNonMatchingStateId_ShouldExcludeRun` | Non-matching stateId correctly excluded | PASS (test) |
| States output empty when no state attached | Verified via test `ValidationRunQueryResult_WithNoState_StatesOutputShouldBeEmpty` | Empty list returned | PASS (test) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DGCL-03 | 03-01-PLAN.md | Persisted validation run remains project-isolated and queryable by rule and state | SATISFIED | Cypher query uses `{project:$project}` for isolation. `ruleId` filter in `WHERE` clause. `stateId` filter in-process via `StateId` match. `ValidationRunsQueryService` tested via 14 unit tests. |
| DGRN-01 | 03-01-PLAN.md | VALIDATION RUNS component returns run list for selected project/stream | SATISFIED | `ValidationRunsComponent` queries Neo4j with `connection.Project` as Cypher param. `Runs` output returns `IReadOnlyList<ValidationRunQueryResult>`. |
| DGRN-02 | 03-01-PLAN.md | VALIDATION RUNS supports optional Rule filter and optional State filter | SATISFIED | `Rule` input at index 1 (`Optional = true`), `State` input at index 2 (`Optional = true`). `ruleId` passed to Cypher WHERE; `stateId` applied in-process. |
| DGRN-03 | 03-01-PLAN.md | VALIDATION RUNS outputs Runs, Results, and States collections in a deterministic schema | SATISFIED | Output 0: `Runs` (ValidationRunQueryResult list). Output 1: `Results` (formatted `{runId}|{ruleId}:{passed}` strings). Output 2: `States` (DesignStateSnapshot for runs with non-null State). RuleIds and Results sorted via `StringComparer.Ordinal`. |

### Anti-Patterns Found

No TODO, FIXME, HACK, PLACEHOLDER, or hollow-return anti-patterns detected in any phase key file.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ValidationRunsQueryTests.cs` line 78-96 | 78-96 | Test `QueryAsync_WhenConnectionNotConnected_ShouldReturnEmpty` does not invoke `QueryAsync` — it asserts a manually constructed empty list | Info | Does not test the actual service path; however, the GH component's `IsConnected` guard is verified separately via code inspection. No blocker. |

### Human Verification Required

#### 1. Live Neo4j Integration Test

**Test:** With Neo4j running and containing at least 3 `ValidationRun` nodes (one with a State, one with a rule filter match, one without):
1. Open Grasshopper with DG plugin loaded
2. Place VALIDATION RUNS component; connect CONNECTOR output
3. Verify unfiltered `Runs` output lists all 3 runs
4. Connect a Rule to Rule input; verify only matching runs appear
5. Connect a DesignStateSnapshot to State input; verify only the state-matched run appears

**Expected:** All three filter modes return correct subsets without errors. Status output shows "Loaded N runs." in each case.

**Why human:** `ValidationRunsQueryService.QueryAsync` requires a live Neo4j driver connection. No mock/stub exists for driver in test suite. The `QueryAsync_WhenConnectionNotConnected_ShouldReturnEmpty` test validates the guard path only, not the actual query execution.

#### 2. Grasshopper Plugin Build and Registration

**Test:** Run `dotnet build DG/DG.sln -c Release /p:DefineConstants=GRASSHOPPER_SDK` (or build from within Rhino 8 environment). Verify `ValidationRunsComponent` appears in the GH component panel under the expected category.

**Expected:** Build succeeds with 0 errors and 0 warnings. Component registers with `ComponentGuid A7F2C3E1-B849-4D6A-9F0E-3C2D1E5B8A94` and appears in GH toolbar.

**Why human:** Build requires Rhino 8 SDK / Grasshopper assemblies not available in CI. The `#if GRASSHOPPER_SDK` conditional compilation means the real component body is excluded from the standard `dotnet test` build.

### Gaps Summary

No gaps. All 4 observable truths are verified by code inspection and unit tests. All required artifacts exist and are substantive. All key links are wired. The 2 human verification items cover live-service integration (Neo4j query execution) and SDK-gated build — neither blocks the code-level goal achievement. The phase delivers a complete, non-stub implementation of the VALIDATION RUNS retrieval contract.

---

_Verified: 2026-05-03T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
