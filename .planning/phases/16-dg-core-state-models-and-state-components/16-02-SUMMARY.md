---
phase: 16-dg-core-state-models-and-state-components
plan: 02
subsystem: DG.Core
tags: [state-models, id-generator, deterministic-hash, sha256, tdd, dg-core, csharp, xunit]

requires:
  - plan: 16-01
    provides: [ObjState, ParamState, PropState, DesignState models]

provides:
  - ComputeParamStateId (renamed from ComputeDefStateId, same DS_ prefix, same logic)
  - ComputePropStateId (PS_ prefix, SHA-256 hash over ruleIri|dataPropertyIri|propValueLex)
  - ComputeDesignStateId (DS_ prefix, SHA-256 hash over sorted member StateIds)
  - ComputeObjectStateId preserved unchanged (OS_ prefix)
  - ComputeObjectInstanceId removed (OI_ prefix constant removed)
  - IdRefPrefix constant preserved unchanged
  - 11 unit tests: 2 ComputeParamStateId, 3 ComputeObjectStateId, 3 ComputePropStateId, 3 ComputeDesignStateId

affects: [16-03, 16-05-state-components, 16-06-designstate-component, future Phase 18 validator]

tech-stack:
  added: []
  patterns:
    - SHA-256 content-addressed IDs with 16-char hex prefixes
    - Deterministic sorting for order-independent hashing
    - Type-specific value formatting (Number "R" round-trip, Integer/Boolean invariant)

key-files:
  modified:
    - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
    - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs

decisions:
  - ParamStatePrefix reuses "DS_" literal; DesignStatePrefix also "DS_" — different hash input domains disambiguate (Research Finding 6)
  - PropStatePrefix = "PS_" per D-11
  - OI_ prefix and ComputeObjectInstanceId removed entirely (zero call sites)
  - ComputeObjectStateId (OS_) and IdRefPrefix (IDR_) preserved unchanged

metrics:
  duration: ~15m
  completed_date: "2026-07-04"

status: complete
---

# Phase 16 Plan 02: DesignStateIdGenerator Update — Summary

Updated DesignStateIdGenerator to support Phase 16 state models: renamed `ComputeDefStateId` to `ComputeParamStateId`, added `ComputePropStateId` (PS_ prefix) and `ComputeDesignStateId` (DS_ prefix, sorted-member aggregate hash), removed `ComputeObjectInstanceId` and the OI_ prefix constant. Executed via TDD (RED/GREEN per task). Build succeeds, 11/11 tests pass.

## Tasks Executed

| Task | Name | Type | Status | Commits |
|------|------|------|--------|---------|
| 1 | Update DesignStateIdGenerator with Phase 16 methods | auto, tdd | complete | `4a6a2f5` (RED test), `b3153c3` (GREEN feat) |
| 2 | Update DesignStateIdGeneratorTests for Phase 16 methods | auto, tdd | complete | `4a6a2f5` (test changes committed in Task 1 RED) |

## TDD Gate Compliance

| Gate | Status | Evidence |
|------|--------|----------|
| RED (test) | passed | `4a6a2f5` — build failed with 16 CS0117 errors (methods not found) |
| GREEN (feat) | passed | `b3153c3` — build succeeds, all 11 tests pass |

## File Changes

### DesignStateIdGenerator.cs — Changes

- **Constant renames/additions/removals:**
  - `DefStatePrefix` (`"DS_"`) renamed to `ParamStatePrefix`
  - `ObjectInstancePrefix` (`"OI_"`) removed entirely
  - `PropStatePrefix` (`"PS_"`) added — new prefix for PropState IDs
  - `DesignStatePrefix` (`"DS_"`) added — aggregate prefix for DesignState IDs
  - `ObjectStatePrefix` (`"OS_"`) preserved unchanged
  - `IdRefPrefix` (`"IDR_"`) preserved unchanged

- **Method changes:**
  - `ComputeDefStateId(IEnumerable<DesignStateParameter>)` renamed to `ComputeParamStateId(...)` — same body, same DS_ prefix via ParamStatePrefix
  - `ComputePropStateId(string ruleIri, string dataPropertyIri, DesignStateParameter propValue)` added — PS_ prefix, hash input = `$"{ruleIri}|{dataPropertyIri}|{lex}"` where lex is type-switched (Number "R", Integer invariant, Boolean invariant, null → "null")
  - `ComputeDesignStateId(IEnumerable<string> memberStateIds)` added — DS_ prefix, sorts via StringComparer.Ordinal, concatenates without separator (fixed-length prefixes are self-delimiting)
  - `ComputeObjectInstanceId(string projectId, string variableName, string seed)` removed — no call sites per D-15
  - `ComputeObjectStateId` preserved unchanged

- **Updated XML doc comments** on all methods to reference current model names

### DesignStateIdGeneratorTests.cs — Changes

- **Renamed tests:**
  - `ComputeDefStateId_ShouldBeDeterministic_RegardlessOfInputOrder` → `ComputeParamStateId_ShouldBeDeterministic_RegardlessOfInputOrder`
  - `ComputeDefStateId_ShouldChange_WhenParameterIsAdded` → `ComputeParamStateId_ShouldChange_WhenParameterIsAdded`

- **Removed test:**
  - `ComputeObjectInstanceId_ShouldProduceOiPrefixedString`

- **Preserved tests (3 unchanged):**
  - `ComputeObjectStateId_ShouldBeDeterministic_ForSameInputs`
  - `ComputeObjectStateId_ShouldHaveExactlyThreeStringParameters_ProvingCrossRuleIdentity`
  - `ComputeObjectStateId_ShouldChange_WhenObjectInstanceIdChanges`

- **New tests for ComputePropStateId (3):**
  - `ComputePropStateId_ShouldBeDeterministic_ForSameInputs` — same inputs → equal ID, Assert.StartsWith("PS_")
  - `ComputePropStateId_ShouldChange_WhenRuleIriChanges` — different ruleIri → NotEqual
  - `ComputePropStateId_ShouldChange_WhenValueChanges` — different propValue → NotEqual

- **New tests for ComputeDesignStateId (3):**
  - `ComputeDesignStateId_ShouldBeDeterministic_ForSameMemberIds` — same list → equal ID, Assert.StartsWith("DS_")
  - `ComputeDesignStateId_ShouldBeDeterministic_RegardlessOfOrder` — ordered vs reversed → equal (proves sorting)
  - `ComputeDesignStateId_ShouldChange_WhenMembersChange` — different members → NotEqual

## Verification Results

- `dotnet build DG/DG.sln` succeeds — 0 errors, 0 warnings
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DesignStateIdGenerator"` — 11 passed, 0 failed, 54 ms

### Source file grep checks

| Pattern | Expected | Actual |
|---------|----------|--------|
| `ComputeDefStateId` | 0 | 0 |
| `ComputeParamStateId` | 1 | 1 |
| `ComputePropStateId` | 1 | 1 |
| `ComputeDesignStateId` | 1 | 1 |
| `ComputeObjectInstanceId` | 0 | 0 |
| `ObjectInstancePrefix\|OI_` | 0 | 0 |
| `PropStatePrefix.*PS_` | 1 | 1 |
| `DesignStatePrefix.*DS_` | 1 | 1 |

### Test file grep checks

| Pattern | Expected | Actual |
|---------|----------|--------|
| `ComputeDefStateId` | 0 | 0 |
| `ComputeParamStateId` | ≥2 | 6 |
| `ComputeObjectInstanceId` | 0 | 0 |
| `ComputePropStateId` | ≥3 | 9 |
| `ComputeDesignStateId` | ≥3 | 9 |

## Key Design Decisions

1. **DS_ prefix collision is safe by design**: Both `ParamStatePrefix` and `DesignStatePrefix` use the literal `"DS_"`. Research Finding 6 confirmed this is correct because the hash input domains are entirely different (sorted parameter ID+value pairs vs. sorted member StateIds). The two methods produce distinct IDs by construction.

2. **OI_ prefix removed entirely**: Per D-15 and the research recommendation to avoid dead constant confusion. All call sites confirmed as zero across the codebase before removal.

3. **Deterministic ordering**: `ComputeParamStateId` uses `OrderBy(ParameterId, StringComparer.Ordinal)` (existing behavior). `ComputeDesignStateId` uses `OrderBy(x => x, StringComparer.Ordinal)` on member StateIds. Both ensure identical input sets produce identical IDs regardless of input order.

4. **No separator between concatenated StateIds**: The fixed-length prefixes (`DS_`, `OS_`, `PS_`, each 3 chars) make adjacent IDs self-delimiting. Adding a separator would change the hash without improving correctness.

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes, architectural changes, or blocking issues encountered.

## Self-Check: PASSED

- Commits `4a6a2f5` and `b3153c3` confirmed in git log
- Build succeeds (0 errors, 0 warnings)
- 11/11 tests pass
- All grep criteria satisfied
- No untracked or uncommitted files
