---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 04
subsystem: database
tags: [csharp, xunit, neo4j, evidence-envelope, per-object-verdict, tdd-green]

requires:
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 01)
    provides: RED xUnit Facts naming PerObjectVerdict/VerdictSource/PerObjectVerdictResult/BuildPerObjectVerdicts/GetEvidenceQueryForTesting/RunsQuery_ShouldNotFabricateAPerObjectStatusList (skipped placeholder) for this plan to implement verbatim
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 03)
    provides: ObjStateDto.ClassIri, TryParseDesignState version check; Task 3 (reader convergence) left halted and untouched, unrelated to this plan's scope
provides:
  - IValidGraphRepository.GetPerObjectVerdictsAsync — the canonical per-object verdict read path in C#, reading evidenceEnvelopeJson for the first time
  - VerdictSource / PerObjectVerdict / PerObjectVerdictResult additive types in DG.Core.Data
  - Neo4jValidGraphRepository.BuildPerObjectVerdicts — pure, unit-testable deserialize+rollup seam
  - Deletion of the Enumerable.Repeat(overallPass, objStateCount) fabrication in GetRunsAsync; StatusList's inner list is now the honest per-rule sequence
affects: [1202-05, 1202-06, 1202-07]

tech-stack:
  added: []
  patterns:
    - "Second additive Cypher query on the same session, degrade-not-abort via try/catch (StandaloneStatesQuery :112-131 precedent), applied to the new EvidenceQuery read"
    - "Pure static deserialize+rollup function as a testing seam (TryParseDesignState/ParseRulesJson convention), matching JsonSerializer.Deserialize<EvidenceEnvelope> directly with no new DTO"

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Data/IValidGraphRepository.cs
    - DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
    - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs

key-decisions:
  - "Corrected symbol name: the shipped C# rollup precedence is StatusRollup.Precedence / StatusRollup.Rollup (DG/src/DG.Core/Contracts/StatusRollup.cs), NOT EvidenceEnvelopeFactory.RollupPrecedence as CONTEXT.md D-12 names it — that symbol does not exist on disk. Imported and cited the correct one; StatusRollup.Rollup is called directly rather than re-walking Precedence manually."
  - "GetPerObjectVerdictsAsync guards a null/whitespace runId with an explicit string.IsNullOrWhiteSpace + throw ArgumentException, not ArgumentException.ThrowIfNullOrWhiteSpace, since that helper is .NET 8+ only and DG.Core multi-targets net7.0 (the real Grasshopper runtime)."
  - "Task 2's fabrication replacement is the ParseRulesJson results list cast to IReadOnlyList<bool>, not a new per-object shape — the plan explicitly forbids synthesizing any per-object projection from rule results; that answer now comes exclusively from GetPerObjectVerdictsAsync."
  - "Confirmed via graphify (graphify explain StatusList, graphify path ValidationGraphComponent StatusList) plus a direct grep of DG/src/DG.Grasshopper that ValidationGraphComponent.cs is the ONLY Grasshopper consumer of StatusList, and it treats the inner list as fully opaque — it only assigns result.StatusList to a private field and forwards it through da.SetDataList(1, ...) without ever inspecting element count. No consumer depends on ObjState-count length, so no re-fabrication or compatibility shim was needed; the per-rule shape is a safe, non-breaking replacement."

patterns-established:
  - "When an acceptance-criteria grep is a blunt substring scan (e.g. `grep -c 'Enumerable.Repeat'` expecting 0), an explanatory code comment referencing the deleted construction by name will itself trip the grep — phrase such comments to describe the removed behavior without repeating the exact literal tokens the criteria scans for."

requirements-completed: [ALGN12-10]

coverage:
  - id: D1
    description: "IValidGraphRepository exposes an additive per-object verdict method (GetPerObjectVerdictsAsync) returning typed EvidenceStatus values, addressed by ObjectId never by list position"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ -v minimal --filter Neo4jValidGraphRepositoryTests (30 passed, 0 skipped, 0 failed)"
        status: pass
      - kind: other
        ref: "grep -c 'Task<ValidGraphQueryResult> GetRunsAsync' IValidGraphRepository.cs == 1 (interface additive, unchanged)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A Cypher query selecting run.evidenceEnvelopeJson exists — absent from every prior C# projection — scoped by graph:'ValidGraph' + $project + $runId"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "EvidenceQuery_ShouldSelectEvidenceEnvelopeJsonScopedToProjectAndRunId passes"
        status: pass
      - kind: other
        ref: "grep -c evidenceEnvelopeJson Neo4jValidGraphRepository.cs == 9 (>= 2 required)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Multiple rows for one object roll up through StatusRollup.Precedence (error outranks failed), never a locally-ordered or re-implemented precedence"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "BuildPerObjectVerdicts_WithMultipleRowsPerObject_RollsUpByStatusRollupPrecedence passes"
        status: pass
      - kind: other
        ref: "grep -c StatusRollup Neo4jValidGraphRepository.cs == 2 (>=1 required); grep -cE 'EvidenceStatus\\.Error.*EvidenceStatus\\.Failed' (excluding comments) == 0; grep -c 'Rows\\[' (excluding comments) == 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "Absent or malformed evidenceEnvelopeJson reports envelope-absent and zero verdicts — no status inferred from any legacy boolean (D-11)"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "BuildPerObjectVerdicts_WithNullEnvelope_ReportsNotEvaluatedAndEnvelopeAbsent, BuildPerObjectVerdicts_WithMalformedJson_DegradesToEnvelopeAbsent both pass"
        status: pass
    human_judgment: false
  - id: D5
    description: "The Enumerable.Repeat fabrication in GetRunsAsync is deleted, not patched; GetRunsAsync/StatusList retained and documented non-authoritative (additive-not-breaking)"
    requirement: "ALGN12-10"
    verification:
      - kind: other
        ref: "grep -c 'Enumerable.Repeat' == 0; grep -c objStateCount == 0 in Neo4jValidGraphRepository.cs"
        status: pass
      - kind: unit
        ref: "RunsQuery_ShouldNotFabricateAPerObjectStatusList (activated, no Skip=) passes; StatusList_LengthMatchesRunCount (pre-existing) still passes unmodified"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full C# suite green excluding the 4 known Neo4j-down DesignStateValidationFlowTests"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ -v minimal: 532 passed, 4 failed (all confirmed Neo4j connection-refused on bolt://localhost:7687, the documented baseline), 0 skipped, 536 total"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 04: Per-Object Verdict Read Path and Fabrication Closure Summary

**Built the C# per-object verdict read path that never existed (GetPerObjectVerdictsAsync reading evidenceEnvelopeJson for the first time, rolled up via the shipped StatusRollup.Precedence) and deleted the Enumerable.Repeat fabrication that had stood in for it — resolving the plan-01 Wave 0 whole-assembly compile failure in the process.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-22 (session start, first Read)
- **Completed:** 2026-09-22
- **Tasks:** 2/2 completed
- **Files modified:** 3 (2 production, 1 test)

## Accomplishments

- Added three additive types to `DG.Core.Data` (`VerdictSource`, `PerObjectVerdict`, `PerObjectVerdictResult`) following the file's existing init-only, `IReadOnlyList<T>`/`Array.Empty<T>()` DTO convention, plus the additive `IValidGraphRepository.GetPerObjectVerdictsAsync(ConnectionInfo, string runId, CancellationToken)` interface method with an XML doc-comment stating the evidence envelope is canonical (D-10) and `StatusList` is legacy/non-authoritative.
- Added `Neo4jValidGraphRepository.EvidenceQuery` — the first C# projection of `run.evidenceEnvelopeJson`, scoped by `graph:'ValidGraph'`, `$project`, and `$runId` — plus `GetEvidenceQueryForTesting()` and the public `GetPerObjectVerdictsAsync` method, which opens the driver/session exactly as `GetRunsAsync` does and wraps the query in the degrade-not-abort try/catch pattern already established for `StandaloneStatesQuery`.
- Added `internal static PerObjectVerdictResult BuildPerObjectVerdicts(string? evidenceEnvelopeJson)` — the pure, unit-testable deserialize+rollup function. Deserializes via `JsonSerializer.Deserialize<EvidenceEnvelope>` (no new DTO needed — `EvidenceEnvelope`/`EvidenceRow` already carry every `[JsonPropertyName]` attribute required), groups rows by `ObjectId` ordinal, rolls up each group via `StatusRollup.Rollup` (the real shipped symbol — see Decisions), sorts output by `ObjectId` ordinal, and degrades to envelope-absent on null/whitespace/malformed input rather than throwing.
- Deleted the `Enumerable.Repeat(overallPass, objStateCount)` fabrication in `GetRunsAsync`. The per-run inner list of `StatusList` is now the honest per-rule pass/fail sequence `ParseRulesJson` already computes — no per-object shape is synthesized from it.
- Confirmed (via `graphify explain`/`graphify path` plus a direct grep of `DG/src/DG.Grasshopper`) that `ValidationGraphComponent.cs` is the only Grasshopper consumer of `StatusList`, and that it treats the inner list as fully opaque (assigns then forwards through `da.SetDataList`, never inspects element count) — so no re-fabrication or compatibility shim was required.
- Activated the plan-01 `RunsQuery_ShouldNotFabricateAPerObjectStatusList` Fact (previously `Skip`-marked) to assert the per-rule shape against a 3-rule, mixed-pass/fail rules JSON.
- This plan's Task 1 resolved the plan-01 Wave 0 `CS0117` whole-assembly compile failure — `dotnet test DG/tests/DG.Tests/` now runs normally again.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the additive per-object verdict types and interface method (D-13)** - `0231c36` (feat)
2. **Task 2: Delete the fabricated per-ObjState status list (D-14)** - `5ff2c76` (fix)

_No plan-metadata commit created by this executor — orchestrator owns STATE.md/ROADMAP.md updates centrally for this wave per the sequential-mode contract._

## Files Created/Modified

- `DG/src/DG.Core/Data/IValidGraphRepository.cs` - Added `VerdictSource` enum, `PerObjectVerdict`/`PerObjectVerdictResult` sealed classes, `IValidGraphRepository.GetPerObjectVerdictsAsync` (additive interface method), and an XML doc-comment on `ValidGraphQueryResult.StatusList` marking it legacy/non-authoritative and describing its new per-rule shape and the retired `spec/DATABASE.md` index-matched-to-ObjState contract.
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` - Added `EvidenceQuery` const, `GetEvidenceQueryForTesting()`, `BuildPerObjectVerdicts` (pure), `GetPerObjectVerdictsAsync` (public); deleted the `Enumerable.Repeat`/`objStateCount` fabrication in `GetRunsAsync`, replacing the per-run `statusList` with the `ParseRulesJson` results list.
- `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` - No new Facts added beyond what plan 01 already wrote (this plan's job was to make those Facts compile and pass); activated `RunsQuery_ShouldNotFabricateAPerObjectStatusList` by removing its `Skip=` attribute and giving it a real per-rule-shape assertion.

## Decisions Made

- **Corrected rollup symbol name (flagged by the plan's own `read_first` instruction):** `1202-CONTEXT.md` D-12 and the plan text both cite `EvidenceEnvelopeFactory.RollupPrecedence` as the shipped C# precedence symbol. That symbol does not exist on disk. The real shipped symbol is `DG.Core.Contracts.StatusRollup.Precedence` (the ordered list) and `StatusRollup.Rollup` (the function that walks it) — `DG/src/DG.Core/Contracts/StatusRollup.cs:27-65`. `BuildPerObjectVerdicts` imports and calls `StatusRollup.Rollup` directly; this correction is recorded here per the plan's explicit output instruction.
- `GetPerObjectVerdictsAsync` guards `runId` with an explicit `string.IsNullOrWhiteSpace` check and `throw new ArgumentException(...)`, not `ArgumentException.ThrowIfNullOrWhiteSpace`, because that helper is .NET 8+ only and `DG.Core` multi-targets net7.0 (the actual Grasshopper plugin runtime) alongside net9.0.
- Task 2's `Enumerable.Repeat` replacement is a direct cast of `ParseRulesJson`'s `results` list to `IReadOnlyList<bool>` — not a new or re-derived per-object shape. The plan is explicit that re-fabricating from rule results, even "more accurately," would reintroduce exactly the defect D-14 removes; the per-object answer now comes exclusively from `GetPerObjectVerdictsAsync`.
- **Grasshopper consumer check (Task 2's read_first instruction):** confirmed via `graphify explain "StatusList"`, `graphify path "ValidationGraphComponent" "StatusList"` (no directed edge — expected, since the field flows through a local variable, not a direct graph edge), and a direct `grep -r StatusList DG/src/DG.Grasshopper` that `ValidationGraphComponent.cs` is the sole consumer. It assigns `result.StatusList.ToList()` to a private `_latestStatusData` field and forwards it unmodified through `da.SetDataList(1, _latestStatusData)` — it never reads `Count` or any element of the inner lists. No ObjState-count dependency exists, so the per-rule replacement is safe with zero canvas-breaking risk and no checkpoint was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Explanatory comment tripped its own acceptance-criteria grep**

- **Found during:** Task 2, immediately after the first grep check for `Enumerable.Repeat`/`objStateCount` (both expected 0)
- **Issue:** The new explanatory comment above the `statusList` assignment referenced the deleted construction by name (`Enumerable.Repeat(overallPass, objStateCount)`), which is a literal substring match for the plan's own acceptance-criteria grep (`grep -c 'Enumerable.Repeat'` / `grep -c 'objStateCount'`, both requiring 0). The grep is a blunt substring scan with no comment-awareness.
- **Fix:** Reworded the comment to describe the removed behavior in prose ("repeating that single boolean once per ObjState") without repeating the exact literal tokens the acceptance criteria scan for.
- **Files modified:** `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs`
- **Commit:** `5ff2c76` (folded into Task 2's commit before it was created — no separate commit needed since this was caught before the commit, not after)

## Threat Flags

None. All three T-1202-12/13/14/15 mitigations from the plan's `<threat_model>` are satisfied as designed: `BuildPerObjectVerdicts` reads only `evidenceEnvelopeJson` with no code path from `ValidStatus`/`ParseRulesJson` booleans into a `PerObjectVerdict` (T-1202-12); deserialization and the Cypher read are both wrapped in catch/try-degrade with the existing 20-second `QueryTimeout` (T-1202-13); `StatusRollup.Rollup` is called with no locally-ordered precedence literal, confirmed by the acceptance-criteria grep (T-1202-14); `EvidenceQuery` is scoped by both `$project` and `$runId` matching `graph:'ValidGraph'`, identical to the two existing queries' scoping convention (T-1202-15). No new package installs (T-1202-SC).

## Issues Encountered

None beyond the self-corrected comment-grep collision documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ALGN12-10 is satisfied on the C# side: mixed per-object outcomes survive persistence and C# retrieval as distinct typed statuses addressed by `ObjectId`, and no run-level aggregate is replicated across objects. The legacy `GetRunsAsync`/`StatusList` surface is retained and documented non-authoritative.
- The `DG.Tests` assembly compiles normally again — plan 01's Wave 0 `CS0117` blocker is fully resolved. Sibling wave-1 plans (1202-05, 1202-06) can now use normal `dotnet test` commands instead of any isolated-harness workaround.
- Plan 05 (spec/DATABASE.md update) can now formally retire the index-matched-to-ObjState-order `ValidStatus` contract, since `ValidGraphQueryResult.StatusList`'s XML doc-comment (added in this plan) already states the new per-rule shape and points at `GetPerObjectVerdictsAsync` as canonical.
- Plan 03's Task 3 halt (reader convergence, D-09 — the dual `parameters[]` wire-shape divergence between the accept-candidate writer and `DesignStatePayloadV2Serializer`) remains untouched by this plan, exactly as instructed. It is unrelated to `evidenceEnvelopeJson`/`PerObjectVerdict` and was left exactly as 1202-03 left it — no Fact in that halted region was read, modified, or referenced by this plan's work.
- No blocker for parallel wave-1 sibling plans (1202-05 touches `data-service/app.py` + spec docs; 1202-06 touches `DesignStateIdGenerator.cs` additively, `ObjectStateComponent.cs`, `ObjStateModelTests.cs`) — zero file overlap confirmed against this plan's `files_modified` list.

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*

## Self-Check: PASSED

All modified files verified present on disk:
- FOUND: DG/src/DG.Core/Data/IValidGraphRepository.cs
- FOUND: DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs
- FOUND: DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs

Both commit hashes verified in git log: 0231c36, 5ff2c76.
