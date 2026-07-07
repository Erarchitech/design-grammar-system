---
phase: 19-deconstruct-and-reinstate-components
plan: 03
subsystem: grasshopper-components
tags: ["param-reinstate", "reinstatement", "rising-edge", "wire-traversal", "assembly-mismatch"]
requires:
  - phase: 19-01
    provides: ErrorMessageTemplates.FormatStatus/FormatMessage, ParameterReinstate24 icon
  - phase: 19-02
    provides: DesignStateDeconstruct + ObjectDeconstruct patterns
provides:
  - ParameterReinstateComponent replacing old ReinstateComponent with new GUID
  - 3-input / 3-output contract: ParamState + Target (REQUIRED) + Reinstate → Parameters + StateStatus + Status
  - Wire-traversal searching Input 1 (Target) only per D-02
  - Rising-edge trigger with _lastApplyInput = true (prevents first-solve auto-fire)
affects: [phase 20-e2e-validation, grasshopper-canvas-migration]
tech-stack:
  added: []
  patterns:
    - Rising-edge trigger with true-initialized guard field
    - Deferred value write via ScheduleSolution (carried forward)
    - Assembly-mismatch fallback (ReconstructSnapshot/ReconstructParameter via reflection)
    - Index-matched output contract (Parameters list ↔ StateStatus list)
key-files:
  created:
    - DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs
    - DG/tests/DG.Tests/ParameterReinstateComponentTests.cs
  modified: []
  deleted:
    - DG/src/DG.Grasshopper/Components/ReinstateComponent.cs
key-decisions:
  - "_lastApplyInput initialized to true (not default false) — prevents first-solve auto-fire while preserving rising-edge behavior"
  - "Wire-traversal restricted to Input 1 (Target) only — no fallback to Input 0 per D-02"
  - "Parameters output always returns ALL params from ParamState (D-05), StateStatus index-matched (D-04)"
requirements-completed: [GHST-07]
duration: 8min
completed: 2026-07-05
status: complete
---

# Phase 19 Plan 03: PARAMETER REINSTATE Component

**Old REINSTATE component rewritten as PARAMETER REINSTATE with new GUID, required Target input, 3-output contract (Parameters + StateStatus + Status), and rising-edge trigger with true-initialized guard**

## Performance

- **Duration:** 8 min
- **Tasks:** 2
- **Files created:** 2
- **Files deleted:** 1

## Accomplishments

- Created `ParameterReinstateComponent.cs` adapting all wire-traversal, deferred write, and assembly-mismatch fallback patterns from old `ReinstateComponent.cs`
- 3 inputs: ParamState (generic item), Target (generic item, REQUIRED — no Optional flag), Reinstate (Boolean item, default false)
- 3 outputs: Parameters (generic list — ALL params per D-05), StateStatus (generic list — index-matched per D-04), Status (text item — per D-06)
- Wire-traversal searches Input 1 (Target) ONLY — no fallback to Input 0 (D-02)
- `_lastApplyInput` initialized to `true` (previously default `false`) to prevent first-solve auto-fire
- `FormatStatus`/`FormatMessage` called from `ErrorMessageTemplates` (not local methods — moved in Plan 01)
- Old `ReinstateComponent.cs` deleted (GUID `D4E2F8A1` and class name fully purged)
- 7 new tests pass: Parameters output contract, StateStatus index-matching, enum contract, null guard, assembly-mismatch round-trip, error template contracts, FormatStatus/FormatMessage branches
- 10 existing ReinstatementServiceTests pass (no regression)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ParameterReinstateComponent.cs replacing ReinstateComponent.cs** - `51a64b5` (feat)
2. **Task 2: Create ParameterReinstateComponentTests** - `9b1fefc` (test)

## Files Created/Deleted

### Created
- `DG/src/DG.Grasshopper/Components/ParameterReinstateComponent.cs` — New PARAMETER REINSTATE component (sealed, GH_Component, GUID `8F9D0A1B`)
- `DG/tests/DG.Tests/ParameterReinstateComponentTests.cs` — 7 test cases (sealed, xUnit)

### Deleted
- `DG/src/DG.Grasshopper/Components/ReinstateComponent.cs` — Old REINSTATE component (GUID `D4E2F8A1`), removed with `git rm`

## Decisions Made

- **`_lastApplyInput = true` initialization**: Under the old default (`false`), the first solve with `Reinstate=true` would auto-fire because `applyInput && !_lastApplyInput` evaluates to `true && !false = true`. Initializing to `true` means the rising edge only fires on the *transition* from false to true, which is the intended UX — the user must explicitly toggle the trigger.

- **Wire-traversal restricted to Input 1 (Target) only**: Per D-02, the new component does NOT fall back to searching Input 0 (ParamState) for the upstream PARAMETER STATE component. This makes the Target input semantically required and eliminates ambiguity.

- **Full carry-forward of assembly-mismatch fallback**: `UnwrapSnapshot`/`ReconstructSnapshot`/`ReconstructParameter`/`DiagnoseInputType` preserve the same reflection-based cross-assembly reconstruction that the old component used — necessary because Grasshopper may load a different copy of DG.Core.dll at runtime.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- **CS0019 on null-conditional with LINQ extensions**: `_latestParamState?.Parameters.ToList() ?? new List<DesignStateParameter>()` fails on `net7.0-windows` (the Grasshopper target framework) because the null-conditional with extension methods produces both sides as the same non-nullable type. Fixed with explicit ternary: `_latestParamState is not null ? _latestParamState.Parameters.ToList() : new List<DesignStateParameter>()`.

## Verification Summary

- [x] `dotnet build DG/DG.sln -c Release` — Build succeeded (0 errors, 0 warnings)
- [x] `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ParameterReinstate"` — 7/7 passed
- [x] `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ReinstatementService"` — 10/10 passed (no regression)
- [x] GUID `D4E2F8A1` purged from all source (`grep -c` returns 0)
- [x] Class name `ReinstateComponent` purged from all source (`grep -c` returns 0)
- [x] `ComponentGuid` is `8F9D0A1B-2C3D-4E4F-5A5B-6C7D8E9F0A1B`
- [x] All 3 inputs registered: ParamState (0), Target (1, REQUIRED), Reinstate (2, Boolean default false)
- [x] All 3 outputs: Parameters (list), StateStatus (list), Status (text)
- [x] `_lastApplyInput` initialized to `true`
- [x] Wire-traversal searches Input 1 (Target) only — no fallback to Input 0
- [x] 207 unit tests pass, 4 Neo4j-dependent E2E tests fail (pre-existing, environment)
- [x] No FormatStatus/FormatMessage local methods (calls ErrorMessageTemplates)

## Next Phase Readiness

- PARAMETER REINSTATE is ready for canvas migration and E2E validation testing
- Wire-traversal, deferred write, and assembly-mismatch patterns are consistent with the old component
- Rising-edge trigger with `_lastApplyInput = true` is the standard pattern for all trigger-based reinstatement components

---
*Phase: 19-deconstruct-and-reinstate-components / Plan 03*
*Completed: 2026-07-05*
