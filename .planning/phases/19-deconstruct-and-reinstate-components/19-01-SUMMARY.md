---
phase: 19-deconstruct-and-reinstate-components
plan: 01
subsystem: grasshopper-plugin
tags:
  - error-messages
  - icons
  - infrastructure
  - csharp
  - grasshopper

# Dependency graph
requires:
  - phase: 16-dg-core-state-models-and-state-components
    provides: ReinstatementResult, ReinstatementStatus, ReinstatementParameterReport models
provides:
  - 8 new ErrorMessageTemplates methods (deconstruct/reinstate/warning templates + FormatStatus/FormatMessage)
  - 3 new DgIcons icon properties (DesignStateDeconstruct24, ObjectDeconstruct24, ParameterReinstate24)
  - 3 new PNG icon files
  - 15 new ErrorMessageTemplateTests
affects:
  - 19-02 (DECONSTRUCT components)
  - 19-03 (PARAMETER REINSTATE rework)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ErrorMessageTemplates What+Where+How-to-fix pattern extended for deconstruct/reinstate surfaces"
    - "DgIcons.Load fallback guarantee (new Bitmap(24,24)) for safe compilation without real artwork"
    - "FormatStatus/FormatMessage as pure static functions on ReinstatementResult (testable from DG.Tests)"

key-files:
  created:
    - DG/src/DG.Grasshopper/Properties/DesignStateDeconstruct24.png
    - DG/src/DG.Grasshopper/Properties/ObjectDeconstruct24.png
    - DG/src/DG.Grasshopper/Properties/ParameterReinstate24.png
  modified:
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/src/DG.Grasshopper/DgIcons.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs

key-decisions:
  - "FormatStatus/FormatMessage moved from old ReinstateComponent into ErrorMessageTemplates (DG.Core) so Plans 2/3 can access them without DG.Grasshopper dependency"
  - "Deconstruct warning templates use Warning-level tone: 'is required'/'Could not unwrap' per D-07 convention"
  - "Reinstate templates describe Target wire setup in What+Where+How-to-fix structure"
  - "PNG icons are minimal solid-color placeholders — DgIcons.Load fallback to new Bitmap(24,24) guarantees compilation succeeds regardless of artwork quality"

patterns-established:
  - "FormatStatus: Applied {N} parameters / Aborted: {N} blocked / Unchanged (same state) / Idle"
  - "FormatMessage: Applied {N} / Aborted / Unchanged / Idle (shorter variant for component Message property)"

requirements-completed: []

coverage:
  - id: D1
    description: "ErrorMessageTemplates has 8 new public static methods: 6 deconstruct/reinstate templates + FormatStatus + FormatMessage"
    requirement: ""
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ErrorMessageTemplateTests.cs#AllNewMethods_ReturnNonEmpty"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 6 deconstruct/reinstate template methods produce correctly formatted What+Where+How-to-fix messages with proper component names and fix instructions"
    requirement: ""
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ErrorMessageTemplateTests.cs#DesignStateDeconstructInputMissing_IncludesComponentAndActionAndFix"
        status: pass
    human_judgment: false
  - id: D3
    description: "FormatStatus and FormatMessage produce correct output for all 4 branches (Applied, Aborted, Unchanged, Idle)"
    requirement: ""
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ErrorMessageTemplateTests.cs#FormatStatus_AppliedWithCount_ReturnsAppliedSummary"
        status: pass
    human_judgment: false
  - id: D4
    description: "DgIcons has 3 new static Bitmap properties (DesignStateDeconstruct24, ObjectDeconstruct24, ParameterReinstate24)"
    requirement: ""
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release"
        status: pass
    human_judgment: false
  - id: D5
    description: "3 PNG icon files exist in Properties/ and are embedded via .csproj wildcard"
    requirement: ""
    verification:
      - kind: other
        ref: "ls Properties/*Deconstruct*.png Properties/*Reinstate*.png"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-05
status: complete
---

# Phase 19 Plan 01: Shared Infrastructure for Deconstruct and Reinstate Components

**ErrorMessageTemplates extended with 6 deconstruct/reinstate warning methods + FormatStatus/FormatMessage helpers; DgIcons extended with 3 new icon properties and PNG files; 15 new tests all passing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-05T15:31:00Z
- **Completed:** 2026-07-05T15:43:17Z
- **Tasks:** 2 of 2
- **Files modified:** 7 (2 created, 3 existing modified)

## Accomplishments
- Extended ErrorMessageTemplates.cs with 8 new public static methods (6 deconstruct/reinstate template methods + FormatStatus + FormatMessage)
- Extended DgIcons.cs with 3 new icon properties alphabetically placed (DesignStateDeconstruct24, ObjectDeconstruct24, ParameterReinstate24)
- Created 3 minimal 24x24 PNG icon files in DG/src/DG.Grasshopper/Properties/
- Added 15 new tests to ErrorMessageTemplateTests.cs covering all new methods
- Built successfully with 0 warnings, 0 errors
- All 27 ErrorMessageTemplate tests pass (12 original + 15 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend ErrorMessageTemplates + tests** - `885791b` (feat)
2. **Task 2: Add DgIcons icon properties + PNG files** - `f18ea1b` (feat)

## Files Created/Modified

### Created
- `DG/src/DG.Grasshopper/Properties/DesignStateDeconstruct24.png` - 24x24 icon for DESIGN STATE DECONSTRUCT
- `DG/src/DG.Grasshopper/Properties/ObjectDeconstruct24.png` - 24x24 icon for OBJECT DECONSTRUCT
- `DG/src/DG.Grasshopper/Properties/ParameterReinstate24.png` - 24x24 icon for PARAMETER REINSTATE

### Modified
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` - Added 8 new public static methods
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` - Added 15 new tests
- `DG/src/DG.Grasshopper/DgIcons.cs` - Added 3 icon properties

## Decisions Made
- **FormatStatus/FormatMessage in DG.Core:** Moved from old ReinstateComponent into ErrorMessageTemplates so Plans 2/3 can call them without DG.Grasshopper dependency. DG.Tests can test them directly (pure functions on ReinstatementResult).
- **Deconstruct warning wording:** Follows D-07 convention — uses "is required" for missing input and "Could not unwrap" for cast failures. Both include the fix instruction with component names.
- **Reinstate template wording:** TargetRequired says "Wire the 'State' output of a PARAMETER STATE component" — helps the user understand the wire source explicitly. SourceNotFound says "Could not find a PARAMETER STATE component upstream" — guides the user to check their wiring.
- **Minimal PNG icons:** Solid-color placeholders are sufficient because DgIcons.Load already has a `new Bitmap(24,24)` fallback when the embedded resource is missing. The build succeeds regardless.

## Deviations from Plan

None - plan executed exactly as written.

### Auto-fixed Issues

None - no bugs, missing functionality, or blocking issues encountered during execution.

## Issues Encountered

None - both tasks completed cleanly on first attempt. Build and tests green.

## User Setup Required

None - no external service configuration required. All files are in-project C#/PNG assets.

## Next Phase Readiness

- **ErrorMessageTemplates** ready for Plans 19-02 (DESIGN STATE DECONSTRUCT uses DesignStateDeconstructInputMissing, DesignStateDeconstructCastFailed; OBJECT DECONSTRUCT uses ObjectDeconstructInputMissing, ObjectDeconstructCastFailed) and 19-03 (PARAMETER REINSTATE uses ReinstateTargetRequired, ReinstateSourceNotFound, FormatStatus, FormatMessage)
- **DgIcons** ready — Plan 19-02 uses DesignStateDeconstruct24 + ObjectDeconstruct24; Plan 19-03 uses ParameterReinstate24
- **3 PNG files** present in Properties/ with .csproj wildcard embedding already configured

## Self-Check: PASSED

- All 3 PNG files exist and are tracked in git
- Both task commits verified (885791b, f18ea1b)
- `dotnet build DG/DG.sln -c Release` succeeds with 0 errors
- `dotnet test --filter "~ErrorMessageTemplate"` passes 27/27

---
*Phase: 19-deconstruct-and-reinstate-components*
*Completed: 2026-07-05*
