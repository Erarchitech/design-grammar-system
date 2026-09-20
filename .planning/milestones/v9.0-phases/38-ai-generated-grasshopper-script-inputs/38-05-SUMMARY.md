---
phase: 38-ai-generated-grasshopper-script-inputs
plan: 05
subsystem: api
tags: [computgraph, neo4j, validgraph, designstate, data-service, dg-core]

# Dependency graph
requires:
  - phase: 38-01
    provides: "spec/DATABASE.md's amended two-writer / Run-less-DesignState invariants and the normative ParamState node shape this plan writes to"
  - phase: 38-04
    provides: "cg_input_sampler.validate_candidate, the candidates[] shape (parameters[]/provenance/statePayload) this plan persists"
provides:
  - "data-service/cg_paramstate_store.py: accept_candidate() -- the first :DesignState writer in the repository, and the only write path for AI-generated candidates"
  - "POST /computgraph/candidates/accept route with all three documented error codes"
  - "fetch_generated_param_states() -- the GHIN-03 SC4 'queryable in the graph' read"
  - "Neo4jValidGraphRepository.StandaloneStatesQuery -- the additive second read that closes finding F1, making a standalone accepted ParamState visible to VALIDATION GRAPH"
affects: [38-06, 38-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Accept-time server-side re-validation: re-read live published :Parameter domains and re-run the SAME validate_candidate() the generation path uses, never trusting a client round-trip (T-38-17)"
    - "Deterministic content-hashed StateId (compute_param_state_id) instead of the per-request generation-time candidateId, so MERGE-by-StateId re-accepting is genuinely idempotent"
    - "Degrade-not-abort additive read: a second Cypher query on the same session, wrapped so a failure (older graph, missing property) falls back to the pre-existing behavior rather than breaking the whole read"

key-files:
  created:
    - data-service/cg_paramstate_store.py
    - data-service/tests/test_cg_paramstate_store.py
  modified:
    - data-service/app.py
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
    - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs

key-decisions:
  - "cg_paramstate_store.py re-implements its own _list_published_parameters read rather than importing cg_input_generation's private helper -- keeps the persistence module's first-party dependency surface limited to cg_input_bindings and cg_input_sampler only (D-22), matching the module docstring's stated boundary"
  - "compute_param_state_id hashes sorted (parameterId, value) pairs + provenance.sourceRuleId, deliberately NOT the generation-time candidateId (c0/c1/...), which is per-request and would break MERGE idempotency across two independent accept calls for identical content"
  - "The written statePayloadJson envelope uses DesignStateParameter's own camelCase property names (numberValue/integerValue/booleanValue) rather than DesignStatePayloadV2Serializer's private condensed {type,value} DTO shape -- the latter is understood only by that class's own Serialize/Deserialize pair, not by the generic JsonSerializer.Deserialize<DesignState> path Neo4jValidGraphRepository.TryParseDesignState actually uses"
  - "StandaloneStatesQuery's failure mode is degrade-not-abort (try/catch around the second read only) rather than a shared try/catch with the runs read -- an older graph or a missing property must never break VALIDATION GRAPH's pre-existing behavior (T-38-21)"

requirements-completed: [GHIN-02, GHIN-03, GHIN-04]

coverage:
  - id: D1
    description: "accept_candidate() persists an architect-accepted candidate as a standalone, Run-less :DesignState {kind:'ParamState'} node, MERGE'd by StateId+project, after re-validating every parameter against the LIVE published domains -- never trusting the client round-trip"
    requirement: GHIN-03
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_paramstate_store.py (7 tests: valid-write with all 11 provenance props, DS_-prefixed deterministic StateId, out-of-domain rejection with zero writes, missing-provenance rejection with zero writes, narrowed-live-domain rejection with zero writes, fetch_generated_param_states rule/model/timestamp + rule_id filter, every captured query parameterized)"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /computgraph/candidates/accept is a thin route with definitionId required (no resolution fallback) and all three documented error codes mapped from real exception paths"
    requirement: GHIN-02
    verification:
      - kind: other
        ref: "grep-based acceptance criteria on data-service/app.py: 1 route decorator, 3 unique COMPUTGRAPH_ACCEPT_CANDIDATE_* codes; python -m pytest data-service/tests/test_cg_paramstate_store.py data-service/tests/test_error_responses.py -q (11/11 pass, no regression to the shipped structured-error contract)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Neo4jValidGraphRepository gains an additive second read for standalone :DesignState nodes (StandaloneStatesQuery), closing finding F1 -- a candidate accepted via the new route is now visible to VALIDATION GRAPH, and the component degrades gracefully rather than breaking when the query cannot run"
    requirement: GHIN-03
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs (18 tests, 3 new: StandaloneStatesQuery shape assertion, a literal statePayloadJson fixture matching the Python writer's envelope verbatim parsing with a matching StateId/parameter, run-derived+standalone dedup-by-StateId yielding exactly one entry); dotnet build ./DG/DG.sln -c Release exits 0 on both net7.0 and net9.0"
        status: pass
    human_judgment: false
  - id: D4
    description: "The generation/application separation survives the introduction of a writer -- cg_input_generation still never imports cg_paramstate_store, and the generate-inputs route still performs zero writes"
    requirement: GHIN-04
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_input_boundary.py -q (4/4 pass, unchanged from plan 38-04)"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 05: Accepted-Candidate Persistence and the Standalone-DesignState Read Summary

**The first `:DesignState` writer in the repository (`cg_paramstate_store.accept_candidate`, wired through `POST /computgraph/candidates/accept`) plus the additive `Neo4jValidGraphRepository` read that closes finding F1 -- an architect-accepted AI-generated candidate is now written idempotently after live-domain re-validation, and visible to VALIDATION GRAPH.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 4
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `data-service/cg_paramstate_store.py` (new): `accept_candidate(session, project, definition_id, rule_id, candidate)` re-reads the live published `:Parameter` rows for `definition_id`, rebuilds `bound_params` through `cg_input_bindings.select_parameters`, and re-runs `cg_input_sampler.validate_candidate` -- raising `CandidateDomainViolation` (carrying the violation list) or `CandidateRequestInvalid` (malformed request/incomplete provenance) with **zero writes** on either path. On success it writes a single parameterized `MERGE (ds:DesignState {StateId: $stateId, project: $project})` / `SET` carrying `kind='ParamState'`, `graph='ValidGraph'`, a v2 `statePayloadJson` envelope, and all eleven provenance properties (`source`, `sourceRuleId`, `provider`, `model`, `confidence`, `definitionId`, `publishedAt`, `strategy`, `determinabilityClass`, `generatedAt`, `acceptedAt`). `compute_param_state_id` derives a deterministic `DS_`-prefixed id from a sorted `(parameterId, value)` hash plus `sourceRuleId` -- re-accepting the identical candidate content is genuinely idempotent. `fetch_generated_param_states` is the GHIN-03 SC4 read.
- `POST /computgraph/candidates/accept` added to `app.py`: `ComputgraphAcceptCandidateRequest` (`definitionId` required, no resolution fallback -- documented asymmetry vs. `generate-inputs`), thin route mapping `CandidateDomainViolation` -> 422 with a hint naming the offending parameters, `CandidateRequestInvalid`/`ValueError` -> 422 request-invalid, bare `Exception` -> 502.
- `Neo4jValidGraphRepository.cs` gained `StandaloneStatesQuery` (matches `kind:'ParamState'`, `graph:'ValidGraph'`, `$project`, ordered deterministically) and `GetStandaloneStatesQueryForTesting()`. `GetRunsAsync` runs it as a second read on the **same session** after the runs cursor is fully consumed, appending parsed states to `allStates` before the existing StateId dedup block; `Runs`/`StatusList` stay untouched and index-matched; the read is wrapped in a degrade-not-abort try/catch (T-38-21) and opens no second session (`AsyncSession` still occurs exactly once in the file).
- Two Rule 1 bug fixes surfaced while proving the cross-language round-trip (Task 4 test 9): `TryParseDesignState`'s v2 branch was silently returning a `DesignState` with **empty** `ParamStates[].Parameters` for any real parameter list -- `DesignStateParameter.Type`'s enum needed a `JsonStringEnumConverter`, and `ParamState.Parameters`'s getter-only `Collection<T>` needed a manual per-item backfill pass (`JsonObjectCreationHandling.Populate` is .NET 8+ only and DG.Core multi-targets net7.0 for the actual Grasshopper runtime, so it could not be used). The Python writer's `_build_state_payload_json` was also fixed to emit `DesignStateParameter`'s own camelCase shape (`numberValue`/`integerValue`/`booleanValue`) instead of `DesignStatePayloadV2Serializer`'s private condensed `{type, value}` DTO shape, which only that class's own Serialize/Deserialize pair understands.
- Test suites: `test_cg_paramstate_store.py` (7 tests, written with Task 1 since Task 1's own `<verify>` step depends on it -- mirrors plan 38-04's precedent), and 3 new `Neo4jValidGraphRepositoryTests.cs` tests (18 total, additions only).

## Task Commits

Each task was committed atomically:

1. **Task 1: Accepted-candidate persistence with server-side re-validation** - `012c0dd` (feat) -- includes `test_cg_paramstate_store.py`, written early to satisfy this task's own `<verify>` step (see Deviations)
2. **Task 2: The candidates/accept route** - `fc929ed` (feat)
3. **Task 3: Additive standalone-DesignState read in the C# repository** - `0ede403` (feat)
4. **Task 4: Persistence, provenance-query and read-path tests** - `9181e1f` (test) -- also carries the two Rule 1 fixes below

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `data-service/cg_paramstate_store.py` - `accept_candidate`, `compute_param_state_id`, `fetch_generated_param_states`, `CandidateDomainViolation`, `CandidateRequestInvalid`
- `data-service/tests/test_cg_paramstate_store.py` - 7 tests, fake-session style
- `data-service/app.py` - `ComputgraphAcceptCandidateRequest` + `POST /computgraph/candidates/accept`
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` - `StandaloneStatesQuery`, `GetStandaloneStatesQueryForTesting`, additive second read in `GetRunsAsync`, `TryParseDesignState` enum + collection-population fixes
- `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` - 3 new tests (additions only)

## Decisions Made

- `cg_paramstate_store.py`'s first-party import surface is limited to `cg_input_bindings` and `cg_input_sampler` -- it re-implements its own published-parameter read rather than importing `cg_input_generation`'s private helper, keeping the module's own dependency graph as narrow as the boundary test enforces on the generation side.
- `compute_param_state_id` hashes candidate content (sorted parameter pairs + `sourceRuleId`), never the per-request `candidateId` -- this is what makes re-accepting the identical candidate produce the identical node rather than a duplicate.
- The accept-time `statePayloadJson` envelope mirrors `DesignStateParameter`'s own CLR property names verbatim, not `DesignStatePayloadV2Serializer`'s internal DTO shape -- the two are different contracts for different call paths, and only one of them is what `Neo4jValidGraphRepository.TryParseDesignState`'s generic-deserialize path actually reads.
- `StandaloneStatesQuery`'s try/catch wraps only the second read, not the whole method -- a standalone-read failure degrades to run-derived states alone; it must never take down the pre-existing runs read.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `test_cg_paramstate_store.py` written during Task 1, not deferred to Task 4**
- **Found during:** Task 1, attempting to run its own `<verify>` command
- **Issue:** Task 1's `<verify>` step is `python -m pytest data-service/tests/test_cg_paramstate_store.py -q`, but that file is listed under Task 4's `<files>`, not Task 1's -- the command as written cannot pass until a later task exists. Same sequencing gap plan 38-04 hit and documented.
- **Fix:** Wrote the full 7-test `test_cg_paramstate_store.py` as part of Task 1's own commit. Task 4 then only needed to extend `Neo4jValidGraphRepositoryTests.cs`.
- **Files modified:** `data-service/tests/test_cg_paramstate_store.py`
- **Commit:** `012c0dd` (Task 1)

**2. [Rule 1 - Bug] `TryParseDesignState`'s v2 branch silently dropped every ParamState parameter**
- **Found during:** Task 4, building test 9's round-trip fixture
- **Issue:** Two independent, compounding defects in the pre-existing v2-deserialize branch (never previously exercised with a populated Parameters list, confirmed by isolating the failure with a throwaway console harness): (a) `DesignStateParameter.Type` is a C# enum, and `System.Text.Json`'s default enum handling only accepts an integer, not a lowercase string, without an explicit `JsonStringEnumConverter`; (b) `ParamState.Parameters` is exposed via a getter-only `Collection<T>` (by design, so callers cannot replace the instance), and `System.Text.Json`'s default object-creation handling silently SKIPS populating a getter-only collection member rather than throwing -- so the whole method returned a non-null `DesignState` with a correctly-parsed `ParamStates` list whose nested `Parameters` was always empty, with no exception anywhere.
- **Fix:** Registered `new JsonStringEnumConverter(JsonNamingPolicy.CamelCase)` on the local `JsonSerializerOptions`, and added a manual backfill pass that re-walks the raw `JsonDocument`'s `paramStates[].parameters[]` arrays and `Add()`s each deserialized `DesignStateParameter` onto the corresponding `ParamState.Parameters` collection. Deliberately did NOT use `JsonObjectCreationHandling.Populate` (the one-line .NET 8+ fix) because DG.Core multi-targets `net7.0` -- the actual Grasshopper plugin runtime -- and that API is unavailable there (confirmed via a failed net7.0 build before reverting to the manual-backfill approach).
- **Files modified:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs`
- **Verification:** New test 9 passes; `dotnet build ./DG/DG.sln -c Release` exits 0 on both `net7.0` and `net9.0`; full `dotnet test ./DG/tests/DG.Tests/` (412 tests) green.
- **Commit:** `9181e1f` (Task 4)

**3. [Rule 1 - Bug] Python writer emitted the wrong parameter JSON shape for the C# reader**
- **Found during:** Task 4, same round-trip fixture work as fix #2
- **Issue:** `cg_paramstate_store.py`'s `_build_state_payload_json` initially wrote each parameter as `{parameterId, displayName, type, value}` -- the condensed shape `DesignStatePayloadV2Serializer`'s PRIVATE `ParameterDto` uses, understood only by that class's own `Serialize()`/`Deserialize()` pair. `Neo4jValidGraphRepository.TryParseDesignState`'s v2 branch instead deserializes directly onto `DG.Core.Models.DesignStateParameter`, which has no generic `value` property at all -- only `numberValue`/`integerValue`/`booleanValue`.
- **Fix:** Rewrote `_build_state_payload_json` to emit `numberValue`/`integerValue`/`booleanValue` (with the two non-applicable ones explicitly `null`), matching `DesignStateParameter`'s own camelCase shape.
- **Files modified:** `data-service/cg_paramstate_store.py`
- **Verification:** `python -m pytest data-service/tests/test_cg_paramstate_store.py -q` (7/7 pass); C# test 9 round-trips the corrected fixture successfully.
- **Commit:** `9181e1f` (Task 4)

---

**Total deviations:** 3 auto-fixed (1 sequencing, 2 bugs in the cross-language round-trip)
**Impact on plan:** Fixes #2 and #3 are exactly what makes this plan's stated purpose (SC2's round-trip: written by Python, read by C#) actually reachable rather than aspirational -- both were latent defects in code paths that had never been exercised with a real, non-empty ParamState before this plan built the first writer that produces one. No scope creep beyond making the plan's own success criteria true.

## Issues Encountered

None beyond the auto-fixed items above -- both cross-language bugs were caught by this plan's own Task 4 test 9 before its commit, exactly as the deviation protocol intends. Diagnosed the getter-only-collection defect with a disposable throwaway console harness (outside the repo, in the session scratchpad, deleted after use) rather than guessing at the fix.

## User Setup Required

None - no external service configuration required. All verification ran locally: Python tests against a fake Neo4j session (no live Neo4j), C# tests via `dotnet test`/`dotnet build` against both `net7.0` and `net9.0` targets. Live-Neo4j-dependent integration tests elsewhere in the data-service suite (`test_dg_context.py`, `test_cg_structure_checks.py`, `test_computgraph_consult.py`) fail without a running Neo4j container, exactly as documented for this environment -- pre-existing, unrelated to any file this plan touched, confirmed via `grep` finding zero references to `cg_paramstate_store`/`candidates/accept` in those files.

## Next Phase Readiness

- Plan 38-06 (the review panel) can now read `fetch_generated_param_states()` for the "queryable in the graph" list and rely on `POST /computgraph/candidates/accept`'s documented response shape (`project`, `stateId`, `kind`, `acceptedAt`, `parameterCount`, `provenance`) being real and tested.
- Plan 38-07's UAT can exercise the full SC2 round-trip end to end: generate -> accept -> read via the additive `StandaloneStatesQuery` -> apply through the unchanged `PARAMETER REINSTATE` component -- the cross-language envelope contract that round-trip depends on is now proven by an automated test, not assumed.
- `test_cg_input_boundary.py` still passes unchanged: `cg_input_generation` does not import `cg_paramstate_store`, and `POST /computgraph/generate-inputs` still performs zero writes -- the generation/application separation survived the introduction of the first writer.
- No blockers.

## Self-Check: PASSED

All 6 files (cg_paramstate_store.py, test_cg_paramstate_store.py, app.py, Neo4jValidGraphRepository.cs, Neo4jValidGraphRepositoryTests.cs, this SUMMARY.md) verified present on disk via direct file checks, and all 4 task commit hashes (012c0dd, fc929ed, 0ede403, 9181e1f) verified present via `git log --oneline --all`.

---
*Phase: 38-ai-generated-grasshopper-script-inputs*
*Completed: 2026-07-27*
