---
phase: 823-shacl-validation-layer
plan: 05
subsystem: grasshopper-plugin
tags: [shacl, csharp, grasshopper, dotnet, dto, error-messages]

# Dependency graph
requires:
  - phase: 823-02
    provides: "Canonical SHACL envelope {conforms, results:[{severity,what,where,howToFix,focusLabel,shapeId}], counts:{violation,warning,info}} from dg-reasoner's POST /shacl/validate"
  - phase: 823-03
    provides: "data-service publish response carries top-level shacl key mirroring the canonical envelope (or null when unavailable/pre-823)"
provides:
  - "ErrorMessageTemplates.ShaclViolation(severity, what, where, howToFix) -> string — What+Where+How-to-fix house style formatter for SHACL findings"
  - "ShaclReportPayload/ShaclCountsPayload/ShaclFindingPayload (DG.Core.Validation, public) — camelCase-matching DTOs for the shacl publish-response block"
  - "ValidationPublishResponse.Shacl (DG.Grasshopper.Validation) — nullable typed access to the deserialized shacl block"
  - "ValidatorComponent SHACL surfacing — Report output lines + Warning/Remark runtime messages, never Error, for every SHACL finding on a successful publish"
affects: [823-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SHACL DTOs live in DG.Core.Validation (public), not DG.Grasshopper.Validation (internal) — DG.Tests (net9.0) cannot ProjectReference DG.Grasshopper (net7.0-windows7.0, NU1201 TFM incompatibility); placing camelCase-contract DTOs in DG.Core keeps the round-trip deserialization test runnable"
    - "GH_RuntimeMessageLevel severity cap: violation/warning -> Warning, info -> Remark, never Error, for any SHACL finding — Error stays reserved for true component failures (existing publish-exception catch block)"
    - "Report output list mutated and re-set via a second da.SetDataList(3, ...) call after the publish block enriches it with SHACL lines — GH allows multiple SetDataList calls on the same output within one SolveInstance, last call wins"

key-files:
  created:
    - DG/src/DG.Core/Validation/ShaclReportPayload.cs
    - DG/tests/DG.Tests/ValidationPublishResponseShaclTests.cs
  modified:
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
    - DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs
    - DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs

key-decisions:
  - "ShaclReportPayload/ShaclCountsPayload/ShaclFindingPayload defined as public types in DG.Core.Validation instead of internal sealed types inside ValidationPublishContract.cs (DG.Grasshopper) as the plan's <action> literally specified — probed via a throwaway ProjectReference + dotnet restore and confirmed NU1201 ('Project DG.Grasshopper is not compatible with net9.0 ... supports: net7.0-windows7.0'); DG.Tests has no route to reference DG.Grasshopper's internal types at all. Placing the DTOs in DG.Core preserves the exact camelCase contract and keeps it unit-testable; ValidationPublishResponse.Shacl (DG.Grasshopper) references the DG.Core type directly"
  - "Fixed a latent bug in ValidationPublishClient's stateWarning-override branch (Rule 1): the existing manual ValidationPublishResponse reconstruction there did not copy the new Shacl field, which would have silently dropped SHACL data whenever DesignState serialization emitted a warning"
  - "Report output line list is built once, then optionally re-set via a second da.SetDataList(3, ...) call after SHACL findings are appended post-publish, since Report is set at output-assembly time (before SendValid publish) but SHACL data only exists after a successful publish call"
  - "Verified real (non-stub) GRASSHOPPER_SDK code paths compile clean via direct `dotnet build DG/src/DG.Grasshopper/DG.Grasshopper.csproj` — Rhino 8 SDK is present on this machine, so DG.Grasshopper builds its real implementation (not the #else stub) even though DG.Tests can't reference it"

patterns-established:
  - "When a DTO must be both internal-to-a-GH-SDK-gated-assembly AND unit-testable, and the test project can't cross-reference that assembly (TFM/visibility), define the DTO in the shared DG.Core library as public and have the GH-side type reference it — avoids adding a ProjectReference that fails NU1201"

requirements-completed: [SHCL-02]

coverage:
  - id: D1
    description: "ErrorMessageTemplates.ShaclViolation produces a What+Where+How-to-fix string in the established house style, covering severity, what, where, and howToFix content"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ErrorMessageTemplateTests.cs::ShaclViolation_EachSeverity_ProducesHouseStyleMessage (3 InlineData cases), ShaclViolation_HowToFixAlreadyEndingInPeriod_DoesNotDoublePunctuate"
        status: pass
    human_judgment: false
  - id: D2
    description: "The publish response's shacl block round-trips into typed C# with every field populated (camelCase contract verified, no silent nulls)"
    requirement: "SHCL-02"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ValidationPublishResponseShaclTests.cs::Deserialize_PopulatedShaclBlock_YieldsAllFieldsNonEmpty, Deserialize_ViolationFinding_MapsEveryCamelCaseFieldExactly"
        status: pass
    human_judgment: false
  - id: D3
    description: "ValidatorComponent surfaces SHACL findings in Report + runtime messages, capped at Warning/Remark, never Error"
    requirement: "SHCL-02"
    verification:
      - kind: source-assertion
        ref: "grep confirms GH_RuntimeMessageLevel.Error appears only in the pre-existing publish-exception catch block, never inside the SHACL-finding surfacing loop"
        status: pass
      - kind: build
        ref: "dotnet build DG/src/DG.Grasshopper/DG.Grasshopper.csproj (GRASSHOPPER_SDK defined, Rhino 8 present) — 0 warnings, 0 errors"
        status: pass
      - kind: manual
        ref: "Live GH-canvas verification (publish a run, inspect Report + runtime levels) tracked as manual-only in 823-VALIDATION.md — ValidatorComponent is GRASSHOPPER_SDK-gated, not unit-testable outside a live host"
        status: deferred
    human_judgment: true

# Metrics
duration: ~35min
completed: 2026-07-12
status: complete
---

# Phase 823 Plan 05: SHACL Grasshopper Surfacing Summary

**SHACL findings now surface on the VALIDATOR component via a new `ErrorMessageTemplates.ShaclViolation` house-style formatter and typed `ValidationPublishResponse.Shacl` DTOs — Report lines plus runtime messages capped at Warning/Remark, never Error, so a data-integrity finding never renders the component as failed.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3 complete
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `ErrorMessageTemplates.ShaclViolation(severity, what, where, howToFix)` added to DG.Core, following the class's existing `{Context}: {what happened}. {how to fix}.` house style (`"SHACL {severity}: {what} at {where}. {howToFix}."`), with defensive trailing-period trimming so a caller-supplied `howToFix` that already ends in "." doesn't double-punctuate. Covered by 4 new theory/fact tests.
- `ShaclReportPayload` / `ShaclCountsPayload` / `ShaclFindingPayload` DTOs added as public types in `DG.Core.Validation`, camelCase-matching the canonical envelope (`status`/`conforms`/`counts`/`results`, and per-finding `severity`/`what`/`where`/`howToFix`/`focusLabel`/`shapeId`) established by Plans 823-02/823-03. Round-trip deserialization test proves every field populates non-empty — no silent nulls from a naming mismatch.
- `ValidationPublishResponse.Shacl` (nullable `ShaclReportPayload?`) added, so the publish response's `shacl` block deserializes into typed C#.
- `ValidatorComponent.SolveInstance` extended: after a successful publish, each `response.Shacl.Results` finding is formatted via `ShaclViolation` and appended to the Report output; runtime message severity is capped at Warning (violation/warning) or Remark (info) — never Error. `shacl.Status` of `"unavailable"`/`"timeout"` surfaces a single non-alarming Remark.
- Full non-E2E test suite: 222/222 passing, zero regressions. Direct `DG.Grasshopper` build (Rhino 8 SDK present, real `GRASSHOPPER_SDK` code path, not the stub) compiles clean with 0 warnings/0 errors.

## Task Commits

1. **Task 1 (RED):** `5a761c2` - test(823-05): add ShaclViolation theory tests
2. **Task 1 (GREEN):** `a1c86ba` - feat(823-05): implement ErrorMessageTemplates.ShaclViolation
3. **Task 2 (RED):** `22ce1d6` - test(823-05): add ShaclReportPayload round-trip deserialization test
4. **Task 2 (GREEN):** `e76b333` - feat(823-05): implement ShaclReportPayload DTOs + wire ValidationPublishResponse.Shacl
5. **Task 3:** `d16d93c` - feat(823-05): surface SHACL findings on VALIDATOR component (D-15)

**Plan metadata:** committed together with this SUMMARY (see final commit below)

## Files Created/Modified

- `DG/src/DG.Core/Validation/ShaclReportPayload.cs` (new) - `ShaclReportPayload`, `ShaclCountsPayload`, `ShaclFindingPayload` public DTOs
- `DG/tests/DG.Tests/ValidationPublishResponseShaclTests.cs` (new) - round-trip deserialization tests
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` - `ShaclViolation` method
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` - theory/fact tests for `ShaclViolation`
- `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` - `ValidationPublishResponse.Shacl` property
- `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` - `Shacl` field copied in the stateWarning-override reconstruction (bug fix)
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` - SHACL surfacing block in `SolveInstance`

## Decisions Made

- SHACL DTOs placed in `DG.Core.Validation` (public) rather than `DG.Grasshopper.Validation` (internal, as the plan's `<action>` literally specified) — a throwaway `ProjectReference` + `dotnet restore` probe confirmed `NU1201: Project DG.Grasshopper is not compatible with net9.0 ... supports: net7.0-windows7.0`, so `DG.Tests` (net9.0) has no way to reference `DG.Grasshopper`'s internal types. This preserves the exact camelCase contract while keeping it genuinely unit-testable; `ValidationPublishResponse.Shacl` (DG.Grasshopper) references the DG.Core type directly, and a direct `DG.Grasshopper` build (Rhino 8 SDK present) confirms the real, non-stub wiring compiles.
- Fixed `ValidationPublishClient`'s `stateWarning`-override branch to copy the new `Shacl` field (Rule 1: this existing manual reconstruction would otherwise silently drop SHACL data whenever DesignState serialization emits a warning).
- Report output list is built once at the normal output-assembly point, then re-set via a second `da.SetDataList(3, ...)` call after SHACL findings are appended inside the post-publish block — Grasshopper permits multiple `SetDataList` calls on the same output within one `SolveInstance`; the last call wins.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] SHACL DTOs relocated from DG.Grasshopper.Validation to DG.Core.Validation**
- **Found during:** Task 2
- **Issue:** The plan's `<action>` specified adding `ShaclReportPayload`/`ShaclFindingPayload` as `internal sealed` classes inside `ValidationPublishContract.cs` (DG.Grasshopper) and writing a round-trip deserialization test for them in `DG.Tests`. `DG.Tests` targets `net9.0` and only `ProjectReference`s `DG.Core`; it has no reference to `DG.Grasshopper` (`net7.0-windows7.0`) and the DTOs are `internal` with no `InternalsVisibleTo` for `DG.Tests`.
- **Fix:** Probed the blocker directly (temporary `ProjectReference` + `dotnet restore`), confirmed `NU1201` TFM incompatibility, then defined the three DTOs as `public sealed` types in a new file `DG/src/DG.Core/Validation/ShaclReportPayload.cs` and had `ValidationPublishResponse.Shacl` (DG.Grasshopper) reference them directly. The round-trip test targets these DG.Core types — the exact same types the response wraps — so the camelCase contract is still verified end-to-end.
- **Files modified:** `DG/src/DG.Core/Validation/ShaclReportPayload.cs` (new), `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs`
- **Commits:** `22ce1d6`, `e76b333`

**2. [Rule 1 - Bug] ValidationPublishClient dropped Shacl in stateWarning-override branch**
- **Found during:** Task 2
- **Issue:** `ValidationPublishClient.Publish` manually reconstructs `ValidationPublishResponse` when a DesignState-serialization warning occurs, copying each field explicitly. Adding `Shacl` to the response class without updating this reconstruction would silently drop SHACL data on that code path.
- **Fix:** Added `Shacl = parsed.Shacl` to the reconstruction.
- **Files modified:** `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs`
- **Commit:** `e76b333`

**3. [Rule 1 - Bug] Nullable-reference warning on finding fields**
- **Found during:** Task 3
- **Issue:** `dotnet build` flagged CS8604 (possible null reference) passing `finding.Severity` etc. to `ShaclViolation`'s non-nullable string parameters — a legitimate runtime concern, since `System.Text.Json` can assign `null` to a non-nullable string property when the JSON explicitly contains a null value, bypassing the C# initializer.
- **Fix:** Null-coalesced each finding field (`finding.Severity ?? string.Empty`, etc.) before use.
- **Files modified:** `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs`
- **Commit:** `d16d93c`

## Issues Encountered

None beyond the three auto-fixed items above. Full non-E2E test suite (222/222) confirmed no regression across all three tasks; the 3 pre-existing E2E test failures (`DesignStateValidationFlowTests`, requiring live Neo4j/data-service on `localhost`) are out of scope per the scope-boundary rule — unrelated to this plan's changes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `ValidationPublishResponse.Shacl` and `ErrorMessageTemplates.ShaclViolation` are the exact typed contract Plan 823-06 (UI rendering, if it also touches Grasshopper-adjacent surfaces) or any future GH-side consumer needs.
- Live GH-canvas verification (publish a run from a real canvas, inspect Report lines + runtime message levels) was not performed in this sequential session — deferred to `823-VALIDATION.md` as a manual-only check, consistent with the plan's own acceptance criteria (`ValidatorComponent is GRASSHOPPER_SDK-gated, not unit-testable outside a live host`).
- No blockers identified for downstream plans.

---
*Phase: 823-shacl-validation-layer*
*Completed: 2026-07-12*

## Self-Check: PASSED

- FOUND: DG/src/DG.Core/Validation/ShaclReportPayload.cs
- FOUND: DG/tests/DG.Tests/ValidationPublishResponseShaclTests.cs
- FOUND: DG/src/DG.Core/Services/ErrorMessageTemplates.cs (ShaclViolation method present)
- FOUND: DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs (Shacl property present)
- FOUND: DG/src/DG.Grasshopper/Components/ValidatorComponent.cs (SHACL surfacing block present)
- FOUND commit: 5a761c2
- FOUND commit: a1c86ba
- FOUND commit: 22ce1d6
- FOUND commit: e76b333
- FOUND commit: d16d93c
