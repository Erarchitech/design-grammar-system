---
phase: 19-deconstruct-and-reinstate-components
plan: 02
subsystem: DG.Grasshopper
tags:
  - gh-component
  - deconstruct
  - design-state
  - obj-state
  - object-deconstruct
  - passive
  - synchronous
requires: []
provides:
  - DesignStateDeconstructComponent
  - ObjectDeconstructComponent
affects: []
tech-stack:
  added:
    - C# GH_Component (sealed, pure synchronous pattern)
    - xUnit tests for Core-model level verification
  patterns:
    - DesignStateDeconstruct: TryDesignState → SetDataList x3
    - ObjectDeconstruct: TryObjState → SetData x3 (Text/Generic/Text)
    - SetEmptyOutputs with Remark + cache clearing
    - D-07 Warning level (not Error) for missing/null input
key-files:
  created:
    - DG/src/DG.Grasshopper/Components/DesignStateDeconstructComponent.cs
    - DG/src/DG.Grasshopper/Components/ObjectDeconstructComponent.cs
    - DG/tests/DG.Tests/DesignStateDeconstructComponentTests.cs
    - DG/tests/DG.Tests/ObjectDeconstructComponentTests.cs
  modified: []
decisions:
  - Namespace-resolved Core model types via CoreObjState/CoreParamState/CorePropState aliases to avoid DG. wrapper type conflict in Grasshopper project context
  - SetEmptyOutputs uses Remark (GH_RuntimeMessageLevel.Remark) for status, while missing-input emits Warning — matching the pattern of Warning to alert + Remark to inform
metrics:
  duration: ~3m
  completed_date: "2026-07-05"
  tasks_total: 2
  tasks_completed: 2
  tests_passing: 200 (non-E2E), 6 new
status: complete
---

# Phase 19 Plan 02: DesignStateDeconstruct + ObjectDeconstruct Components

**One-liner:** Two passive deconstruction GH_Component files following the pure synchronous passthrough pattern — DESIGN STATE DECONSTRUCT splits a DesignState into three typed lists (ObjState/ParamState/PropState), OBJECT DECONSTRUCT splits an ObjState into ObjectRef/Geometry/Label — with 6 matching test cases across two test files.

## Tasks

### Task 1: DesignStateDeconstructComponent + Tests (373ca4c)

**Files created:**
- `DG/src/DG.Grasshopper/Components/DesignStateDeconstructComponent.cs`
- `DG/tests/DG.Tests/DesignStateDeconstructComponentTests.cs`

**Class:** `DesignStateDeconstructComponent : GH_Component`
- Guid: `6D7B8C9D-0E1F-4A2B-8C3D-4E5F6A7B8C9D`
- Input: Generic item (DesignState) -> Outputs: 3 Generic lists (ObjState/ParamState/PropState)
- SolveInstance: GetData → TryDesignState → SetDataList x3 + Message count summary
- D-07: Warning (not Error) for null/missing input; no warning for empty bags
- Internal cached fields (`_latestObjStates`/`_latestParamStates`/`_latestPropStates`) for re-solve stability
- GRASSHOPPER_SDK guard with #else stub

**Tests (3):**
1. `DesignStateWithItems_ExposesThreeLists` — 2 ObjStates, 1 ParamState, 3 PropStates
2. `EmptyBagPassthrough_ProducesEmptyLists` — default DesignState, verifies empty lists
3. `DesignState_MissingInput_WarningPattern` — error template strings contain "DESIGN STATE DECONSTRUCT", "DesignState input", "required"

### Task 2: ObjectDeconstructComponent + Tests (00d8ce4)

**Files created:**
- `DG/src/DG.Grasshopper/Components/ObjectDeconstructComponent.cs`
- `DG/tests/DG.Tests/ObjectDeconstructComponentTests.cs`

**Class:** `ObjectDeconstructComponent : GH_Component`
- Guid: `7E8C9D0A-1B2C-4D3E-8F4A-5B6C7D8E9F0A`
- Input: Generic item (ObjState) -> Outputs: Text(Object)/Generic(Geometry)/Text(Label)
- SolveInstance: GetData → TryObjState → SetData x3 + Message = ObjectRef
- SetEmptyOutputs: string.Empty for TextParameter outputs, null for GenericParameter
- D-07: Warning for null/missing input; default ObjState (empty ObjectRef) valid passthrough
- Internal cached fields for re-solve stability
- GRASSHOPPER_SDK guard with #else stub

**Tests (3):**
1. `ObjStateWithValues_ReturnsObjectRefGeometryLabel` — ObjectRef="building-42", Geometry="rhino-guid-abc", Label="Main Building"
2. `ObjStateWithNullGeometryAndLabel_ReturnsEmptyStrings` — ObjectRef set, Geometry/Label null
3. `ObjectDeconstruct_WarningPattern` — error template strings contain "OBJECT DECONSTRUCT", "input is required", "Could not unwrap"

## Verification

| Check | Result |
|-------|--------|
| `dotnet build DG/DG.sln` | Passed — 0 errors, 0 warnings |
| `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~DesignStateDeconstruct\|FullyQualifiedName~ObjectDeconstruct"` | 10/10 passed (6 new + 4 overlapping ErrorMessageTemplate tests) |
| `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName!~E2E"` | 200/200 passed (non-E2E) |
| Grep for GH_RuntimeMessageLevel.Warning in both components | Confirmed — 2 Warning sites per component, 0 Error sites |
| ComponentGuid uniqueness | Both new GUIDs are unique within the project (verified no duplicates) |

## Deviations from Plan

None. The plan was executed exactly as written.

**Minor fix applied (Rule 1 — auto-fix):** The `SetEmptyOutputs` method in DesignStateDeconstructComponent used `new List<ObjState>()` which resolved to `List<DG.ObjState>` (public wrapper) instead of `List<DG.Core.Models.ObjState>` (core model). Fixed by using the `CoreObjState`/`CoreParamState`/`CorePropState` aliases (consistent with the pattern already used in `GhCastingHelpers`). Also fixed an xUnit analyzer warning: `Assert.Equal(1, …)` → `Assert.Single(…)`.

## Key Decisions

1. **Core model type aliasing:** In the Grasshopper project context, `ObjState` resolves to `DG.ObjState` (public wrapper inheriting from `DG.Core.Models.ObjState`). To reference core model types in component code, `CoreObjState`, `CoreParamState`, `CorePropState` aliases are used — matching the pattern established by `GhCastingHelpers`.

2. **SetEmptyOutputs Remark pattern:** When input is null/missing, the component first emits a Warning (D-07) via `AddRuntimeMessage(Warning, …)`, then calls `SetEmptyOutputs` which sets empty lists/values and adds a Remark. The Remark is informational only — the Warning carries the actionable guidance.

3. **D-07 passthrough semantics:** Empty bags (DesignState with no items) are valid output — no warning emitted. Default ObjState (empty ObjectRef string) is valid passthrough for OBJECT DECONSTRUCT — no warning emitted.

## Known Stubs

None. Both components output real data from model properties directly.

## Threat Flags

None. Both components are pure synchronous in-process transformations with no network, DB, or external I/O.

## Self-Check: PASSED

- [x] `DG/src/DG.Grasshopper/Components/DesignStateDeconstructComponent.cs` created
- [x] `DG/src/DG.Grasshopper/Components/ObjectDeconstructComponent.cs` created
- [x] `DG/tests/DG.Tests/DesignStateDeconstructComponentTests.cs` created
- [x] `DG/tests/DG.Tests/ObjectDeconstructComponentTests.cs` created
- [x] Commit 373ca4c verified
- [x] Commit 00d8ce4 verified
- [x] Build succeeds (0 errors, 0 warnings)
- [x] All 200 non-E2E tests pass
- [x] D-07 Warning level confirmed in both components
