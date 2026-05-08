---
phase: 06-end-to-end-hardening-and-verification
plan: 01
subsystem: error-handling
tags: [csharp, grasshopper, error-messages, enum, xunit]

requires:
  - phase: 04-reinstatement-component
    provides: ReinstatementStatus enum and reinstatement service patterns
provides:
  - SerializationError enum with 4 values for state capture failures
  - ErrorMessageTemplates static class with 5 methods following What+Where+How-to-fix format
  - All GH components wired to use standardized error messages
affects: [06-03, model-viewer-error-handling]

tech-stack:
  added: []
  patterns: [What+Where+How-to-fix error message pattern via static template class]

key-files:
  created:
    - DG/src/DG.Core/Models/SerializationError.cs
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
  modified:
    - DG/src/DG.Grasshopper/Components/DesignStateComponent.cs
    - DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
    - DG/src/DG.Grasshopper/Components/ReinstateComponent.cs

key-decisions:
  - "ErrorMessageTemplates as static class in DG.Core.Services — accessible from both DG.Core and DG.Grasshopper"
  - "Each method returns a complete sentence ending with period, containing What+Where+How-to-fix"

patterns-established:
  - "Error template pattern: ErrorMessageTemplates.MethodName(context, error) returns formatted string"
  - "GH components use ErrorMessageTemplates for all AddRuntimeMessage calls"

requirements-completed: [INTG-03]

duration: 8min
completed: 2026-05-08
---

# Phase 06 Plan 01: C# Error Message Templates Summary

**SerializationError enum + ErrorMessageTemplates class with 5 methods providing What+Where+How-to-fix error messages across all 4 GH components, backed by 12 unit tests**

## What Was Built

1. **SerializationError enum** (`DG.Core.Models`) — 4 values: `NoStateProvided`, `MalformedStatePayload`, `MissingParameterId`, `TimestampMissing`
2. **ErrorMessageTemplates static class** (`DG.Core.Services`) — 5 methods:
   - `SerializationFailed(parameterId, error)` — maps each enum value to actionable message
   - `ReinstatementBlocked(parameterId, status, detail)` — wraps reinstatement errors with fix hints per status
   - `ValidationInputMissing(inputName)` — standardized missing input message
   - `PublishFailed(project, errorDetail)` — publish failure with troubleshooting guidance
   - `DesignStateTypeUnsupported(parameterName, typeName)` — unsupported type capture skip
3. **12 unit tests** verifying format compliance: contains parameterId, contains `: ` separator, ends with `.`
4. **GH component updates** — DesignStateComponent, ClassificatorComponent, ValidatorComponent, ReinstateComponent all wired to ErrorMessageTemplates

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | edd10cc | feat(06-01): create SerializationError enum + ErrorMessageTemplates + unit tests |
| 2 | 96b6733 | feat(06-01): update GH components to use ErrorMessageTemplates |

## Verification

- `dotnet build DG/DG.sln -c Release` — 0 errors, 0 warnings
- `dotnet test DG/tests/DG.Tests/ -c Release` — 61 tests passed, 0 failed

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
