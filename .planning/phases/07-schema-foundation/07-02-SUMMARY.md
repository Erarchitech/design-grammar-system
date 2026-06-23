---
phase: 07-schema-foundation
plan: 02
subsystem: api
tags: [csharp, dotnet, sha256, ontology, dg-core]

# Dependency graph
requires:
  - phase: 07-01
    provides: VariableKind enum and VariableTypeInferrer (no direct code dependency, but establishes the same DG.Core static-utility / flat-model convention this plan follows)
provides:
  - DefState, ObjectState, ObjectInstance flat sibling model classes in DG.Core.Models
  - DesignStateIdGenerator static class in DG.Core.Services — ComputeDefStateId, ComputeObjectStateId, ComputeObjectInstanceId, IdRefPrefix constant
affects: [07-03 (Neo4j Cypher for :DesignState{kind} nodes), Phase 9 (OBJECT STATE / DESIGN STATE components consume these models and ID methods, IdRef production wiring)]

# Tech tracking
tech-stack:
  added: []
  patterns: [SHA256 deterministic ID generation relocated from GH-coupled component into DG.Core static service, mirroring ErrorMessageTemplates static-class convention]

key-files:
  created:
    - DG/src/DG.Core/Models/DefState.cs
    - DG/src/DG.Core/Models/ObjectState.cs
    - DG/src/DG.Core/Models/ObjectInstance.cs
    - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
    - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs
  modified: []

key-decisions:
  - "DefState/ObjectState/ObjectInstance are flat sibling classes with no shared base class or interface — matches the Neo4j single :DesignState{kind} label decision (no concrete parent node) and the existing flat DG.Core.Models convention (Rule, Atom, Variable)"
  - "ComputeObjectStateId takes exactly 3 string parameters (projectId, objectInstanceId, variableName) — no ruleId — proving cross-rule identity per CMPST-07; verified by both a grep check and a reflection-based unit test on the method signature"
  - "DesignStateSnapshot.cs and DesignStateParameter.cs were left untouched — DefState is additive, not a replacement, per CONTEXT.md's 'no Grasshopper component behavior changes' boundary for this phase"
  - "IDR_ prefix declared as a const string only (no ComputeIdRefId method, no IdRef model class) — IdRef = DefState.StateId reused per CMPST-08; full production wiring deferred to Phase 9 when the DESIGN STATE component exists"

patterns-established:
  - "SHA256 deterministic ID generation centralized in DG.Core.Services.DesignStateIdGenerator (static class, no instance state) — relocates the previously GH-coupled DesignStateComponent.ComputeStateId pattern into testable pure logic, reusable by future Neo4j repository code"

requirements-completed: [SCHM-01, SCHM-03]

# Metrics
duration: 25min
completed: 2026-06-23
status: complete
---

# Phase 7 Plan 02: DefState/ObjectState/ObjectInstance Models and DS_/OS_/OI_/IDR_ ID Generation Summary

**DefState/ObjectState/ObjectInstance flat model classes plus a DG.Core DesignStateIdGenerator producing deterministic DS_/OS_/OI_-prefixed SHA256 IDs (cross-rule ObjectState, no ruleId), with the IDR_ prefix declared and IdRef production deferred to Phase 9**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-23T00:25:00Z
- **Completed:** 2026-06-23T00:50:22Z
- **Tasks:** 2 completed
- **Files modified:** 5 (5 created, 0 modified)

## Accomplishments
- `DefState`, `ObjectState`, `ObjectInstance` model classes added to `DG.Core.Models`, all flat sibling classes with `init`-only scalar properties and `Collection<T>` getter-only list properties, matching the established `DesignStateSnapshot`/`Rule`/`Atom` convention
- `DesignStateIdGenerator` static class added to `DG.Core.Services`, relocating the SHA256-based ID hashing logic out of the `#if GRASSHOPPER_SDK`-guarded `DesignStateComponent.ComputeStateId` into pure, unit-testable `DG.Core` logic
- `ComputeObjectStateId` proven cross-rule via both a grep check (`ruleId` count = 0) and a reflection-based unit test asserting exactly 3 string parameters with no parameter named `ruleId`
- `IdRefPrefix` constant (`"IDR_"`) declared alongside `DS_`/`OS_`/`OI_`, completing the full v3.0 ID-prefix vocabulary lock without adding a compute method or model class for IdRef (correctly deferred to Phase 9 per CMPST-08)
- 6 unit tests cover: DefState determinism/order-independence, DefState change-on-parameter-add (Pitfall 5 guard), ObjectState determinism, ObjectState 3-parameter signature, ObjectState sensitivity to objectInstanceId, ObjectInstance OI_ prefix

## Task Commits

Each task was committed atomically:

1. **Task 1: DefState, ObjectState, ObjectInstance model classes** - `4027749` (feat)
2. **Task 2: DesignStateIdGenerator — DS_/OS_/OI_ deterministic ID computation** - `6bfb659` (test, RED) + `379bb40` (feat, GREEN)

**Plan metadata:** (this commit)

_Note: Task 2 used the TDD test→feat commit split per the plan's `tdd="true"` marker. RED was confirmed via a genuine compile failure (CS0103/CS0246 — `DesignStateIdGenerator` did not exist), not a logic-only failure._

## Files Created/Modified
- `DG/src/DG.Core/Models/DefState.cs` - flat class: `StateId`, `CapturedAtUtc`, `Parameters` (Collection<DesignStateParameter>), mirrors `DesignStateSnapshot.cs` exactly
- `DG/src/DG.Core/Models/ObjectState.cs` - flat class: `StateId`, `ObjectInstanceId`, `VariableName`, `ObjectRef`, `GeoRefs` (Collection<string>), `CapturedAtUtc`
- `DG/src/DG.Core/Models/ObjectInstance.cs` - flat class: `InstanceId`, `ProjectId`, `VariableName`, `CreatedAtUtc` — new cross-rule identity anchor concept, no prior C# analog
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` - static class: `ComputeDefStateId`, `ComputeObjectStateId`, `ComputeObjectInstanceId`, `IdRefPrefix` const
- `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` - 6 xUnit tests covering determinism, sensitivity, prefix correctness, and the cross-rule signature guarantee

## Decisions Made
- Kept `DesignStateSnapshot.cs`/`DesignStateParameter.cs` unmodified — `DefState` is additive per the plan's explicit instruction; no renaming/retiring in this phase
- Used the identical `SHA256.HashData` + `Convert.ToHexString(hash)[..16]` pattern from `DesignStateComponent.ComputeStateId` for all three ID methods, factored into a private `HashToHex16` helper to avoid duplicating the hash-and-truncate logic three times
- `ComputeObjectInstanceId(projectId, variableName, seed)` signature chosen exactly as the plan suggested — `seed` lets the future Phase 9 call site supply a stable disambiguator (e.g. ObjectRef) since no other natural uniqueness key exists for `ObjectInstance` at this phase

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed the literal substring "ruleId" from a doc comment to satisfy the plan's done-criteria grep**
- **Found during:** Task 2 verification (`grep -c "ruleId" DesignStateIdGenerator.cs` returned 1, expected 0)
- **Issue:** The XML doc comment on `ComputeObjectStateId` explained the cross-rule design by writing "no ruleId parameter" — correct in meaning, but the literal substring `ruleId` made the plan's exact-match grep check fail even though no `ruleId` parameter exists in the actual method signature (confirmed separately by the reflection-based unit test)
- **Fix:** Reworded the comment to "no rule-scoping input" — same meaning, doesn't trip the grep
- **Files modified:** DG/src/DG.Core/Services/DesignStateIdGenerator.cs
- **Verification:** Rebuilt (0 errors), re-ran `DesignStateIdGeneratorTests` (6/6 pass), re-ran the grep (now 0)
- **Committed in:** 379bb40 (part of Task 2 GREEN commit — the edit was made before the commit, so no separate commit was needed)

---

**Total deviations:** 1 auto-fixed (1 bug-class wording fix)
**Impact on plan:** Cosmetic only — no behavior change, no scope creep.

## Issues Encountered
None. The .NET SDK (10.0.109) was available in this environment as noted in the execution context, so all build/test verification used real `dotnet build`/`dotnet test` commands rather than manual tracing — resolving the blocker carried forward from 07-01.

Full test suite run after Task 2: 73 passed, 4 failed — the 4 failures are pre-existing `DG.Tests.E2E.DesignStateValidationFlowTests` cases requiring a live Neo4j at `bolt://localhost:7687` (Docker stack not running in this environment), unrelated to this plan's changes, consistent with the environment note. No regressions introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `DefState`, `ObjectState`, `ObjectInstance`, and `DesignStateIdGenerator` are ready for `07-03-PLAN.md` to wire Neo4j Cypher around the `:DesignState{kind}` node shape (DS_/OS_ prefixes) and for Phase 9 to consume `ComputeObjectInstanceId`/`ComputeObjectStateId` from the OBJECT STATE / DESIGN STATE components.
- The 07-01 blocker (manual-trace-only verification, no .NET SDK) is now resolved for this plan — real `dotnet build`/`dotnet test` were used throughout. Recommend re-running `dotnet test DG/tests/DG.Tests/DG.Tests.csproj --filter VariableTypeInferrerTests` (07-01's code) on this same machine to close out that earlier blocker, since the SDK is now confirmed available.
- SCHM-03 is only partially complete by design: DS_/OS_/OI_ fully implemented and tested; IDR_ is a declared constant only, with IdRef's actual production logic intentionally deferred to Phase 9 per CMPST-08.

---
*Phase: 07-schema-foundation*
*Completed: 2026-06-23*
