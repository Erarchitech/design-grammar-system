---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 11
subsystem: grasshopper-plugin
tags: [csharp, grasshopper, error-messages, input-validation, tdd, dg-core]

# Dependency graph
requires:
  - phase: 1202 (plan 06)
    provides: DesignStateIdGenerator.ComputeObjectStateIdFromRef (D-04's converged ObjState minting) — untouched by this plan
provides:
  - ObjStateGuard.IsObjectListLengthMismatch — pure DG.Core predicate for the Object-vs-Geometry list-length contract
  - ErrorMessageTemplates.ObjStateMismatchedObjectListLength — dedicated Object-side error template
  - Object-vs-Geometry hard guard wired into ObjectStateComponent.SolveInstance, closing REVIEW CR-02
affects: [1202-REVIEW.md CR-02, 1202-VERIFICATION.md gap 2, ALGN12-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SDK-independent guard predicates factored into DG.Core as pure static functions so GRASSHOPPER_SDK-gated components can be logic-tested without the Rhino SDK"

key-files:
  created:
    - DG/src/DG.Core/Services/ObjStateGuard.cs
  modified:
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
    - DG/tests/DG.Tests/ObjStateModelTests.cs

key-decisions:
  - "A dedicated Object-side error template was required, not a reuse of the existing Label-worded ObjStateMismatchedListLengths — that template hardcodes the word 'Label' in its message body and its second parameter is literally named labelCount, so passing an Object count through it would actively mislead a user about which input is mis-wired."
  - "The guard predicate lives in DG.Core (new ObjStateGuard static class) rather than as a private method on the component, because ObjectStateComponent.cs is entirely #if GRASSHOPPER_SDK-gated and DG.Tests (net9.0, DG.Core-only) cannot reach it directly."
  - "The new guard is placed after the existing Label guard and before broadcastClassIri, preserving Label-first error precedence on a wiring that is mismatched on both inputs simultaneously — no currently-observable error message changes for existing failure modes."

requirements-completed: [ALGN12-08]

coverage:
  - id: D1
    description: "ObjStateGuard.IsObjectListLengthMismatch pure predicate exempts objectCount in {0, 1, geometryCount} and flags every other count as a mismatch"
    requirement: "ALGN12-08"
    verification:
      - kind: unit
        ref: "DG.Tests/ErrorMessageTemplateTests.cs#ObjStateGuard_IsObjectListLengthMismatch_MatchesExpectedShape"
        status: pass
      - kind: unit
        ref: "DG.Tests/ObjStateModelTests.cs#ObjStateGuard_MismatchCasesAreExactlyTheCasesThatWouldMintADegradedObjState"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dedicated Object-side error template names the Object input, includes both counts, and never says Label; the existing Label template is byte-for-byte unchanged"
    requirement: "ALGN12-08"
    verification:
      - kind: unit
        ref: "DG.Tests/ErrorMessageTemplateTests.cs#ObjStateMismatchedObjectListLength_NamesObjectNotLabel"
        status: pass
      - kind: unit
        ref: "DG.Tests/ErrorMessageTemplateTests.cs#ObjStateMismatchedListLengths_UnchangedByThisPlan_StillLabelWorded"
        status: pass
    human_judgment: false
  - id: D3
    description: "ObjectStateComponent.SolveInstance raises GH_RuntimeMessageLevel.Error and emits no ObjStates on an Object-vs-Geometry length mismatch, placed after the Label guard and before broadcastClassIri, delegating to the shared DG.Core predicate rather than re-expressing the condition inline"
    requirement: "ALGN12-08"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (Rhino 8 SDK present, GRASSHOPPER_SDK branch compiled, 0 warnings/errors)"
        status: pass
      - kind: other
        ref: "grep -c 'ObjStateMismatchedListLengths' DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs == 1"
        status: pass
      - kind: other
        ref: "grep -n 'GH_RuntimeMessageLevel.Error' DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs — 2 sites"
        status: pass
    human_judgment: true
    rationale: "The plan's own design_decision states no acceptance criterion asserts runtime Grasshopper canvas behavior — nothing in this repo executes the GH canvas headlessly. Compilation + grep prove the call site is correct and uses the new template, but the actual on-canvas Error balloon and no-ObjStates-emitted behavior is only confirmable by loading the rebuilt plugin in Rhino 8, which is an optional human-check per the plan, not performed this session."

# Metrics
duration: ~20min
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 11: Object-vs-Geometry List-Length Guard Summary

**Closed REVIEW CR-02 by adding a pure DG.Core predicate (`ObjStateGuard.IsObjectListLengthMismatch`) and a dedicated Object-side error template, then wiring both into `ObjectStateComponent.SolveInstance` so a mismatched Object list now hard-errors instead of silently minting `OS_`-prefixed identities with `ClassIri = null`.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3/3
- **Files modified:** 4 (1 new, 3 modified)

## Accomplishments

- Added `ObjStateGuard.IsObjectListLengthMismatch(geometryCount, objectCount)` in `DG.Core.Services` — a pure, SDK-independent predicate exempting `objectCount` of `0` (no Object wired, registered Optional), `1` (ontology-class broadcast), and `== geometryCount` (matched per-instance), flagging every other count including over-supply.
- Added `ErrorMessageTemplates.ObjStateMismatchedObjectListLength(geometryCount, objectCount)` — a dedicated Object-side template that names the Object input explicitly, states the three legal wirings, and never uses the word "Label". The existing `ObjStateMismatchedListLengths` (Label-side) is byte-for-byte unchanged, now pinned by a new regression Fact.
- Wired the guard into `ObjectStateComponent.SolveInstance`, positioned after the existing Label-vs-Geometry guard and before the `broadcastClassIri` assignment — preserving Label-first error precedence for wirings that are mismatched on both inputs. On a mismatch it raises `GH_RuntimeMessageLevel.Error`, sets output to null, and returns — emitting no ObjStates.
- Updated the component's class-level doc-comment to state the Object input's length contract now enforced.
- Added 10 Theory cases (`ErrorMessageTemplateTests`) covering every exempt/non-exempt shape of the predicate, 2 template Facts (Object-side wording + Label-side byte-pin), and a cross-referencing consequence Fact + SDK-testability-boundary comment block in `ObjStateModelTests.cs`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the pure length-guard predicate and the dedicated Object-side error template to DG.Core** - `8e13586` (feat)
2. **Task 2: Wire the Object-vs-Geometry guard into ObjectStateComponent.SolveInstance** - `68a160d` (feat)
3. **Task 3: Pin the guard's decision surface and record the SDK testability boundary** - `b310a7f` (test)

**Plan metadata:** committed as part of this SUMMARY's closing commit.

## Files Created/Modified

- `DG/src/DG.Core/Services/ObjStateGuard.cs` - New static class; `IsObjectListLengthMismatch` pure predicate, doc-commented with the three exempt cases and CR-02 provenance
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` - Added `ObjStateMismatchedObjectListLength`; existing `ObjStateMismatchedListLengths` untouched
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` - New guard block in `SolveInstance` between the Label guard and `broadcastClassIri`; class doc-comment gained one line on the Object input's length contract
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` - 10-case Theory for the predicate + 2 template Facts (new wording, old wording unchanged)
- `DG/tests/DG.Tests/ObjStateModelTests.cs` - Consequence-pinning Fact + SDK-testability-boundary comment block, cross-referencing Task 1's Facts by name

## Decisions Made

- **Dedicated template, not reuse:** verified on disk (per the plan's `design_decision`) that `ObjStateMismatchedListLengths` hardcodes "Label" in its message body and names its parameter `labelCount` — reuse would mislead a user with a mis-wired Object input into thinking their Label input is wrong. A new template was mandatory, not a judgment call.
- **Predicate location:** placed in a new `ObjStateGuard` static class in `DG.Core.Services` (sibling to `DesignStateIdGenerator`) rather than bolting it onto an unrelated existing service — keeps the guard's single responsibility clear and matches the plan's suggested placement options.
- **Guard ordering:** the new guard sits strictly after the Label guard and before `broadcastClassIri`, per the plan's explicit ordering requirement — this means a canvas wiring mismatched on both Label and Object still reports the Label error first, unchanged from pre-plan behavior.
- No architectural deviations. No Rule 4 triggers. No auto-fixes needed (Rules 1-3 not invoked) — the plan's design was fully specified and executed as written.

## Deviations from Plan

None — plan executed exactly as written. All four `files_modified` entries in the plan's frontmatter were touched exactly as scoped; no file outside that list was modified.

## Issues Encountered

None. The Rhino 8 SDK was present on this build machine (`C:\Program Files\Rhino 8\System\RhinoCommon.dll` and the Grasshopper/GH_IO DLLs all resolved), so `dotnet build DG/DG.sln -c Release` compiled the `GRASSHOPPER_SDK` branch and the new guard's call site type-checked for real — this was not the "Rhino absent" fallback scenario.

## SDK Testability Boundary (stated per plan's design_decision)

`ObjectStateComponent.SolveInstance` cannot be unit-tested directly from `DG.Tests`: the component is entirely inside `#if GRASSHOPPER_SDK`, `DG.Grasshopper` targets `net7.0-windows` and requires the Rhino SDK, and `DG.Tests` targets `net9.0` and references `DG.Core` only (no `DG.Grasshopper` `ProjectReference` was added — this is explicitly prohibited by the plan). What is proven automatically:

1. The guard predicate — 100% unit-tested across all exempt/non-exempt shapes (`ErrorMessageTemplateTests` Theory + `ObjStateModelTests` consequence Fact).
2. The error message text — both the new Object-side template and byte-identical confirmation of the unchanged Label-side template.
3. `dotnet build DG/DG.sln -c Release` — compiled the `GRASSHOPPER_SDK` branch cleanly (Rhino 8 SDK present on this machine), proving the guard's call site type-checks.
4. Targeted greps — confirm the component calls the shared predicate (not an inline re-expression) and uses the new template (Label template still referenced exactly once; two `GH_RuntimeMessageLevel.Error` sites exist).

What is NOT claimed: no assertion of actual Grasshopper canvas runtime behavior (the red Error balloon appearing, ObjStates genuinely not being emitted at runtime). The plan's Task 3 `<human-check>` (load the rebuilt plugin in Rhino 8, wire 5 geometry + 3 per-instance Objects, confirm the Error balloon and 0 ObjStates; then confirm broadcast and no-Object cases still work) is **optional and non-blocking per the plan** and was **not performed this session** — build-machine automation (compile + unit tests + greps) is the full extent of what was run.

## Test Results

- `dotnet build DG/src/DG.Core/DG.Core.csproj -c Release` — success, 0 warnings, 0 errors.
- `dotnet build DG/DG.sln -c Release` — success, 0 warnings, 0 errors. Rhino 8 SDK was present; the `GRASSHOPPER_SDK` conditional-compilation branch actually compiled (not the SDK-absent fallback).
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ErrorMessageTemplate"` — 43/43 passing (33 pre-existing + 10 new Theory cases + 2 new template Facts, all pre-existing Facts still pass unchanged).
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~ObjState"` — 27/27 passing.
- `dotnet test DG/tests/DG.Tests/` (full suite) — **556/556 passing, 0 failed, 0 skipped**. The Neo4j Docker container was up during this run, so the 4 `DesignStateValidationFlowTests` that normally fail fast when Neo4j is unreachable ran and passed too (not merely excluded) — no regression outside or within that known-environment-dependent set.
- `git diff --numstat fixtures/golden/` — empty (frozen golden trio untouched).
- `git diff DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — empty (D-04's converged minting untouched).
- `grep -c 'ObjStateMismatchedListLengths' DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` — `1`.
- `grep -n 'GH_RuntimeMessageLevel.Error' DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` — 2 sites (Label guard line 97, Object guard line 115).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

This was plan 11 of 11 in Phase 1202 (design-state-replay-and-per-object-verdict-closure). All 11 plans now have SUMMARY.md files. REVIEW CR-02 is closed; the guard's condition is a single pure `DG.Core` function called by the component (no drift risk between tested and shipped logic), and ALGN12-08's "stable per-object identity" half now holds under a list-length mismatch — the mismatch is loud, not silently absorbed into a degraded identity. The optional in-Rhino canvas human-check from Task 3 remains available for a future `/gsd-verify-work 1202` pass if live confirmation is desired, but does not block phase completion per the plan's own design_decision.

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-22*

## Self-Check: PASSED

All 5 created/modified source files confirmed present on disk (`ObjStateGuard.cs`, `ErrorMessageTemplates.cs`, `ObjectStateComponent.cs`, `ErrorMessageTemplateTests.cs`, `ObjStateModelTests.cs`), plus this SUMMARY.md itself. All 3 task commits (`8e13586`, `68a160d`, `b310a7f`) confirmed present in `git log`.
