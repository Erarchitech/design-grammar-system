---
phase: 18-rules-and-validator-rework
plan: 01
subsystem: DG.Core
tags:
  - binding-service
  - class-iri-matching
  - design-state-binding
  - objstate
requires:
  - DG.Core.VariableTypeInferrer
  - DG.Core.Models
requires_artifacts:
  - DG/src/DG.Core/Parsing/VariableTypeInferrer.cs
  - DG/src/DG.Core/Models/BindingRow.cs
provides:
  - DesignStateBindingService
  - ObjState.ClassIri
  - ObjectStateComponent.Class input port
  - ErrorMessageTemplates.RuleVariableUnclassified
  - ErrorMessageTemplates.BindingServiceNoObjectBindings
affects:
  - DG.Grasshopper (ObjectStateComponent port change)
tech-stack:
  added: []
  patterns:
    - Static service class with Rule + DesignState -> List<BindingRow> contract
    - TDD: RED -> GREEN cycles with xUnit Facts
key-files:
  created:
    - DG/src/DG.Core/Services/DesignStateBindingService.cs
    - DG/tests/DG.Tests/DesignStateBindingServiceTests.cs
  modified:
    - DG/src/DG.Core/Models/ObjState.cs
    - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
decisions:
  - Builtin-only variables excluded from binding rows (D-07) rather than throwing or producing empty rows
  - Multiple Object variables resolve independently per matching ObjState ClassIri
  - Property values apply to ALL existing rows (not per-ObjState), matching VALIDATOR contract
  - PropValue resolution uses NumberValue/IntegerValue/BooleanValue precedence per DesignStateParameter model
metrics:
  duration: 9m
  completed_date: 2026-07-05
  tasks_completed: 4
  tests_written: 9
  build_targets: DG.Core + DG.Grasshopper
status: complete
---

# Phase 18 Plan 01: ObjState ClassIri + DesignStateBindingService

## One-liner

Added `ClassIri` property to `ObjState` for ontology class discrimination, created `DesignStateBindingService.BuildBindings(Rule, DesignState) -> List<BindingRow>` with Class IRI matching per D-05, and extended `ErrorMessageTemplates` with unclassified-variable and no-ObjState error messages. 9/9 tests pass.

## Tasks Completed

| # | Name | Type | Commit(s) | Files |
|---|------|------|-----------|-------|
| 1 | Add ClassIri to ObjState model and update ObjectStateComponent | auto | 683dee9 | ObjState.cs, ObjectStateComponent.cs, ErrorMessageTemplates.cs |
| 2 | Create DesignStateBindingService.cs with BuildBindings method | auto (tdd) | 7a0f870 (RED), d95f297 (GREEN) | DesignStateBindingService.cs, DesignStateBindingServiceTests.cs |
| 3 | Extend ErrorMessageTemplates with new methods | auto | 9050e2b | ErrorMessageTemplates.cs |
| 4 | Create DesignStateBindingServiceTests covering all scenarios | tdd | 7a0f870 + d95f297 | DesignStateBindingServiceTests.cs |

## Key Features

### ObjState.ClassIri (D-05)
- New `string? ClassIri` property on `ObjState` with default `null` for backward compatibility
- XML doc comment explaining purpose: Class IRI matching for `DesignStateBindingService`

### ObjectStateComponent Class Input
- New optional "Class" text input port (index 3) for Class IRI passthrough from METAGRAPH Objects
- Empty/unset values produce `null` ClassIri (backward compatible with existing canvases)
- Index-mismatch guard extended to 4-list check

### DesignStateBindingService.BuildBindings
- Classifies variables via `VariableTypeInferrer.Infer()` -- not `VariableBinder`
- **Class IRI matching (D-05):** Only `ObjState`s with `ClassIri` matching a rule Object variable's `ClassAtom.PredicateIri` produce binding rows. Non-matching and null-ClassIri ObjStates are skipped.
- **Property resolution:** `PropState` values matched by `RuleIri` + `DataPropertyIri` applied to all existing rows
- **Builtin-only exclusion (D-07):** Variables appearing only in `BuiltinAtom` args excluded from bindings
- **Unclassified variable error (D-06):** Variables with `null` from Infer() that are not Builtin-only throw `InvalidOperationException`
- **Empty-ObjState guard:** Rules with Object variables but zero ObjStates throw descriptive error
- **Property-only rules:** Single row created from PropStates when no Object variables exist
- Preserves input ObjState list ordering for index-matched ValidStatus

### ErrorMessageTemplates Extensions
- `RuleVariableUnclassified(string, string)` -- What+Where+How-to-fix for D-06 unclassified variables
- `BindingServiceNoObjectBindings(string)` -- actionable error for zero-ObjState with Object variables

## Test Coverage (9 tests)

| Test | What it Verifies |
|------|-----------------|
| `BuildBindings_ObjectVarsMatchByClassIri` | 3 ObjStates, 2 matching ClassIri -> 2 rows (D-05) |
| `BuildBindings_PropertyVarMatchByDataPropertyIri` | PropState with matching DataPropertyIri -> value on row |
| `BuildBindings_BuiltinOnlyVariableExcluded` | Builtin-only variable excluded from bindings (D-07) |
| `BuildBindings_UnclassifiedVariableThrows` | Non-Builtin variable with no ClassAtom -> InvalidOperationException (D-06) |
| `BuildBindings_NoObjStatesWithObjectVarsThrows` | Empty ObjStates with Object vars -> throw |
| `BuildBindings_PropertyOnlyRuleCreatesSingleRow` | No Object vars, matching PropState -> 1 row |
| `BuildBindings_ClassIriMatchingPreservesIndexOrder` | Matching at indices 1,3 -> rows in order B1,B2 |
| `BuildBindings_NullClassIriSkipped` | Null ClassIri ObjState -> no row produced |
| `BuildBindings_ZeroMatchingObjStatesReturnsEmpty` | 2 non-matching ObjStates -> empty result |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ObjStateMismatchedListLengths signature extended**
- **Found during:** Task 1 (ObjectStateComponent update)
- **Issue:** Adding the Class input required extending the index-mismatch guard from 3-list to 4-list comparison
- **Fix:** Updated `ObjStateMismatchedListLengths` to accept 4 parameters with updated error message
- **Files modified:** `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`
- **Commit:** 683dee9

## Threat Flags

None. No new trust boundaries or network surfaces introduced. DesignStateBindingService is an in-process service called by the VALIDATOR component on the Grasshopper solve thread.

## Known Stubs

None. Zero-matching-ObjState and empty-ObjState cases both produce correct behavior (empty result or throw).

## Verification Results

- `dotnet build DG/src/DG.Core/ --no-restore` -- PASSED
- `dotnet build DG/src/DG.Grasshopper/ --no-restore` -- PASSED
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DesignStateBindingService"` -- PASSED (9/9)
- No `using DG.Core.Classification` in any new/modified file -- PASSED
- ObjState.ClassIri property exists (string?, default null) -- PASSED
- ObjectStateComponent has Class input port -- PASSED
- ErrorMessageTemplates has both new methods -- PASSED

## Self-Check: PASSED

```
FOUND: DG/src/DG.Core/Models/ObjState.cs
FOUND: DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
FOUND: DG/src/DG.Core/Services/DesignStateBindingService.cs
FOUND: DG/src/DG.Core/Services/ErrorMessageTemplates.cs
FOUND: DG/tests/DG.Tests/DesignStateBindingServiceTests.cs
FOUND: 683dee9
FOUND: 9050e2b
FOUND: 7a0f870
FOUND: d95f297
```
