---
phase: 18-rules-and-validator-rework
plan: 03
subsystem: DG.Core, DG.Grasshopper, DG.Tests
tags:
  - deletion
  - classification
  - classificator
  - clean-up
requires: []
provides: []
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - DG/src/DG.Grasshopper/DgIcons.cs
    - DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
  deleted:
    - DG/src/DG.Core/Classification/VariableBinder.cs
    - DG/src/DG.Core/Classification/ClassificationResult.cs
    - DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs
    - DG/src/DG.Grasshopper/Properties/Classificator24.png
    - DG/tests/DG.Tests/VariableBinderTests.cs
decisions: []
metrics:
  duration: "~3m"
  completed_date: "2026-07-05"
status: complete
---

# Phase 18 Plan 03: Delete CLASSIFICATOR Component and Associated Code

Full purge of the CLASSIFICATOR component, DG.Core.Classification namespace, its icon, its tests, and all references. The new DesignStateBindingService (Plan 18-01) replaces VariableBinder.BuildBindings. 5 files deleted, 3 files modified. Solution builds cleanly with zero Classificator/Classification references remaining.

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Delete DG.Core.Classification namespace — VariableBinder.cs and ClassificationResult.cs | `cc438c3` | DG/src/DG.Core/Classification/VariableBinder.cs, DG/src/DG.Core/Classification/ClassificationResult.cs |
| 2 | Delete ClassificatorComponent.cs, remove Classificator24 from DgIcons, delete Classificator24.png | `678a952` | DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs, DG/src/DG.Grasshopper/Properties/Classificator24.png, DG/src/DG.Grasshopper/DgIcons.cs |
| 3 | Delete VariableBinderTests.cs, clean up ParameterStateComponent comments, verify no using references remain | `e9c9b57` | DG/tests/DG.Tests/VariableBinderTests.cs, DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs, DG/src/DG.Grasshopper/Components/ValidatorComponent.cs |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Stale reference] Classificator references in ValidatorComponent.cs**

- **Found during:** Task 3 (grep check across DG/src/ for Classificator references)
- **Issue:** `ValidatorComponent.cs` had two stale CLASSIFICATOR references: line 27 `"Binding rows from CLASSIFICATOR"` and line 31 `"(or Classificator.State output)"` in parameter descriptions. These referenced the now-deleted component.
- **Fix:** Updated line 27 to `"Binding rows from RULE DECONSTRUCT (partitioned variables)"` and line 31 to reference `"DESIGN STATE composition"` and `"VALIDATION GRAPH"` instead.
- **Files modified:** `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs`
- **Commit:** `e9c9b57`

### Scope Boundary Exemptions

No out-of-scope issues found.

### Fix Attempt Limit

Not reached.

## Verification

1. All 5 files deleted — confirmed by file-not-exists checks
2. `grep -rn "Classificator\|DG\.Core\.Classification" DG/src/` — zero results
3. `dotnet build DG/DG.sln --no-restore` — Build succeeded. 0 Warning(s), 0 Error(s)
4. BindingRow.cs at `DG/src/DG.Core/Models/` — intact
5. VariableTypeInferrer.cs at `DG/src/DG.Core/Parsing/` — intact

## Deleted Files

| File | Purpose |
|------|---------|
| `DG/src/DG.Core/Classification/VariableBinder.cs` | Variable binding logic (replaced by DesignStateBindingService) |
| `DG/src/DG.Core/Classification/ClassificationResult.cs` | Binding result model |
| `DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs` | GH component (114 lines) |
| `DG/src/DG.Grasshopper/Properties/Classificator24.png` | Component icon |
| `DG/tests/DG.Tests/VariableBinderTests.cs` | Unit tests for deleted code |

## Deleted Symbols

- `DG.Core.Classification.VariableBinder` (static class)
- `DG.Core.Classification.ClassificationResult` (sealed class)
- `DG.Core.Classification` (namespace, entirely removed)
- `DG.Grasshopper.Components.ClassificatorComponent` (GH component)
- `DG.Grasshopper.DgIcons.Classificator24` (Bitmap property)

## Modified Files

| File | Change |
|------|--------|
| `DG/src/DG.Grasshopper/DgIcons.cs` | Classificator24 line removed (line 15) |
| `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs` | XML doc comments updated — Classificator references replaced |
| `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` | Parameter descriptions updated — CLASSIFICATOR references removed |

## Threat Flags

No threat flags — pure deletion plan, no new trust boundaries introduced.

## Known Stubs

None.

## Self-Check: PASSED

- `cc438c3`: `git log --oneline | grep -q cc438c3` — FOUND
- `678a952`: `git log --oneline | grep -q 678a952` — FOUND
- `e9c9b57`: `git log --oneline | grep -q e9c9b57` — FOUND
- `Dotnet build`: Succeeded (3.28s, 0 warnings, 0 errors)
