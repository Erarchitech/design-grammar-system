---
phase: 18-rules-and-validator-rework
plan: 02
subsystem: DG.Grasshopper
tags:
  - rule-deconstruct
  - variable-partitioning
  - variable-type-inferrer
  - builtin-exclusion
requires:
  - DG.Core.VariableTypeInferrer
  - DG.Core.Models
requires_artifacts:
  - DG/src/DG.Core/Parsing/VariableTypeInferrer.cs
  - DG/src/DG.Core/Models/Variable.cs
provides:
  - RuleDeconstructComponent.Objects output
  - RuleDeconstructComponent.DataProperties output
  - D-06 unclassified variable error handling
  - D-07 builtin-only variable exclusion
affects:
  - DG.Grasshopper (RULE DECONSTRUCT port names, partition output)
tech-stack:
  added: []
  patterns:
    - Variable partitioning via VariableTypeInferrer.Infer() with builtin detection
    - Conditional compilation (#if GRASSHOPPER_SDK) for GH-dependent code
key-files:
  created: []
  modified:
    - DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs
decisions:
  - Builtin-only variables excluded from both Objects and DataProperties outputs per D-07
  - Unclassifiable variables (in regular atoms but no REFERS_TO link) produce runtime error per D-06
  - VariableTypeInferrer stays unchanged in DG.Core.Parsing per D-08
  - Objects and DataProperties outputs use Param_GenericObject (carry DG.Variable objects)
  - Same 6-element output count preserved (no canvas layout crash)
metrics:
  duration: 8m
  completed_date: 2026-07-05
  tasks_completed: 2
  build_targets: DG.Grasshopper
status: complete
---

# Phase 18 Plan 02: RULE DECONSTRUCT Extension — Objects/DataProperties Partition

## One-liner

Extended RULE DECONSTRUCT to partition rule variables into Objects and DataProperties outputs using VariableTypeInferrer.Infer(), replacing the old flat Variables/VariableName list with a type-aware split that excludes builtin-only variables per D-07 and reports unclassifiable variables per D-06.

## Tasks Completed

| # | Name | Type | Commit(s) | Files |
|---|------|------|-----------|-------|
| 1 | Update ExpectedOutputNames and output registration to Objects/DataProperties | auto | 9fe4f41 | RuleDeconstructComponent.cs |
| 2 | Add variable partitioning logic in SolveInstance | auto | a116fd2 | RuleDeconstructComponent.cs |

## Key Features

### Output Names Changed (Task 1)
- **ExpectedOutputNames**: `"Variables"` → `"Objects"`, `"VariableName"` → `"DataProperties"`
- **Length preserved**: 6 elements — same count as before, so `HasExpectedOutputLayout` still passes on existing canvases, preventing layout crashes
- **Output types**: Both Objects and DataProperties use `Param_GenericObject` (carry `DG.Variable` objects), replacing the old `Variables` (Generic) and `VariableName` (Text) outputs

### Variable Partitioning (Task 2)
- **Classification**: Each variable classified via `VariableTypeInferrer.Infer(rule, variable.Name)` per D-08
- **VariableKind.Object** → Objects output (maps to ObjState downstream)
- **VariableKind.Property** → DataProperties output (maps to PropState downstream)
- **Builtin-only (D-07)**: Variables that appear only in `BuiltinAtom` args (no `ClassAtom`/`ObjectPropertyAtom`/`DataPropertyAtom` presence) are excluded from both outputs
- **Unclassifiable (D-06)**: Variables found in regular atoms but returning `null` from Infer() produce a runtime error message at `GH_RuntimeMessageLevel.Error`
- **Component Message**: Shows partition counts — `"2 obj, 3 prop"`, appends `", 1 unclassified"` when applicable

### Edge Cases Handled
- Empty rule with no variables → empty lists for both outputs, `"0 obj, 0 prop"` message
- All-Builtin rule → all variables excluded, `"0 obj, 0 prop"` message (D-07)
- Mixed builtin + regular variables → builtins excluded, regular variables partitioned correctly
- Malformed rule where variable appears in regular atom at non-classifying position → D-06 error

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `dotnet build DG/src/DG.Grasshopper/ --no-restore` — PASSED (0 warnings, 0 errors)
- `dotnet test DG/tests/DG.Tests/` — PASSED (181/185 passed, 4 Neo4j-dependent E2E skipped — Docker not running)
- ExpectedOutputNames = `["Rule","Objects","DataProperties","SWRL","RuleName","RuleDescription"]` — PASSED (6 elements)
- No `"Variables"` or `"VariableName"` in ExpectedOutputNames or RegisterOutputParams — PASSED
- SolveInstance uses `VariableTypeInferrer.Infer()` for partitioning — PASSED
- D-06: unclassifiable vars produce error message — PASSED
- D-07: Builtin-only vars excluded from both outputs — PASSED
- VariableTypeInferrer unchanged (D-08) — PASSED

## Threat Flags

None. No new trust boundaries or network surfaces introduced. Variable partitioning is pure in-process logic operating on the Rule object already held by the component.

## Known Stubs

None.

## Self-Check: PASSED

```
FOUND: DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs
FOUND: 9fe4f41
FOUND: a116fd2
```
