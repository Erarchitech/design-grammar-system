---
phase: 32-computgraph-serialization-core
plan: 05
subsystem: testing
tags: [csharp, dotnet, xunit, fixture, computgraph, acceptance-test]

# Dependency graph
requires:
  - phase: 32-computgraph-serialization-core plan 01
    provides: "GH-free Computgraph object model (CgContext, RawCanvas, Cg* entities)"
  - phase: 32-computgraph-serialization-core plan 02
    provides: "CanvasAnnotationParser.Parse(RawCanvas) : CgContext"
  - phase: 32-computgraph-serialization-core plan 03
    provides: "ComputgraphContextSerializer.Serialize/Deserialize"
provides:
  - "Checked-in Frame RawCanvas fixture (DG/tests/DG.Tests/Fixtures/frame-cg-context.json) pinned to the OWL named individuals"
  - "FrameFixtureTests -- xUnit integration test exercising parse -> serialize and asserting all four Phase 32 success criteria"
  - "Phase 32 acceptance proof for CGSR-04"
affects: [33-computgraph-bridge, 35-computgraph-recognition, 36-computgraph-persistence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixture-copy ItemGroup (<None Include=\"Fixtures\\**\\*.json\"> CopyToOutputDirectory PreserveNewest>) as the standard way DG.Tests ships checked-in JSON fixtures alongside the test assembly"
    - "AppContext.BaseDirectory + Path.Combine to load a checked-in test fixture at runtime, mirrored from no prior exact analog (DesignStatePayloadV2SerializerTests builds its fixture in-code); this is the first file-loaded fixture in DG.Tests"

key-files:
  created:
    - DG/tests/DG.Tests/Fixtures/frame-cg-context.json
    - DG/tests/DG.Tests/FrameFixtureTests.cs
  modified:
    - DG/tests/DG.Tests/DG.Tests.csproj

key-decisions:
  - "Node ids/component GUIDs in the fixture use short descriptive strings (e.g. \"n-spanscount\", \"guid-number-slider\") rather than real GUID-format strings -- neither RawGroup.MemberIds nor CgWire endpoints are parsed/validated as Guid anywhere in the model, parser, or serializer, so plain opaque strings are sufficient and far more readable for a hand-authored fixture"
  - "Procedure groups (11_Proc/12_Proc) carry empty memberIds -- their role in the fixture is purely to establish the Procedure entity and name; all actual canvas nodes are owned by the nested Pattern/Parameter/Interface groups, matching how the real annotated Frame canvas nests components inside the smaller convention groups rather than directly in the procedure container"
  - "Only the SpansCount Variable node carries slider metadata (min:1,max:20,step:1,isIntegerSlider:true); other Variable member nodes are named \"Number Slider\" without the slider object populated, since only SpansCount's dataType/domain inference is an asserted Phase 32 success criterion -- this keeps the fixture's signal-to-noise ratio high while still satisfying the plan's explicit slider requirement"
  - "Added a HostPatternId assertion (divideLine.Id == topChord.HostPatternId) inside the SC1 fact even though not explicitly required by the plan's acceptance criteria, because the plan's own task text explicitly calls out the host-chain nesting as a required fixture element (\"host-chain proof for HostPatternId\") -- asserting it closes the loop between fixture construction intent and test coverage"

requirements-completed: [CGSR-04]

coverage:
  - id: D1
    description: "Checked-in RawCanvas fixture (frame-cg-context.json) representing the annotated Frame worked example -- OBJECT/ALGORITHM scribbles, both Proc groups, nested patterns, 4 interfaces, 6 variables (incl. integer slider), 8 constants, 10 emergents (incl. deliberate Emr typo), one non-conforming group, and one fully unclaimed node -- copied to DG.Tests output via a fixture-copy ItemGroup"
    requirement: "CGSR-04"
    verification:
      - kind: other
        ref: "dotnet build ./DG/tests/DG.Tests/DG.Tests.csproj -c Debug (fixture copied to bin/Debug/net9.0/Fixtures/frame-cg-context.json)"
        status: pass
    human_judgment: false
  - id: D2
    description: "FrameFixtureTests loads the fixture, parses it via CanvasAnnotationParser, and asserts Phase 32 Success Criterion 1: exactly 1 Object 'FRAME', 1 Algorithm (index 1), 2 Procedures (11/12) named '2D Truss Configuration'/'2D Footer Configuration', with patterns/variables/constants/emergents/interfaces matching the OWL named individuals, plus a HostPatternId nesting proof"
    requirement: "CGSR-04"
    verification:
      - kind: unit
        ref: "DG.Tests/FrameFixtureTests.cs#Parse_FrameFixture_MatchesOwlIndividuals"
        status: pass
      - kind: unit
        ref: "DG.Tests/FrameFixtureTests.cs#Parse_EmrTypo_NormalizesToEmergentAndAppendsWarning"
        status: pass
      - kind: unit
        ref: "DG.Tests/FrameFixtureTests.cs#Parse_IntegerSliderMember_InfersIntegerDataTypeAndDomain"
        status: pass
    human_judgment: false
  - id: D3
    description: "FrameFixtureTests asserts Phase 32 Success Criterion 2: the non-conforming 'Scratch notes' group lands in Untagged.Groups with its member ids intact and produces zero typed entities; a fully unclaimed node lands in Untagged.NodeIds"
    requirement: "CGSR-04"
    verification:
      - kind: unit
        ref: "DG.Tests/FrameFixtureTests.cs#Parse_NonConformingGroup_LandsInUntagged"
        status: pass
    human_judgment: false
  - id: D4
    description: "FrameFixtureTests asserts Phase 32 Success Criterion 3: Serialize(Deserialize(Serialize(context))) is byte-stable and the envelope carries schemaVersion 'cg-context-1'"
    requirement: "CGSR-04"
    verification:
      - kind: unit
        ref: "DG.Tests/FrameFixtureTests.cs#Serialize_FrameContext_IsIdempotent"
        status: pass
    human_judgment: false
  - id: D5
    description: "Phase 32 Success Criterion 4: the entire acceptance proof runs in DG.Tests (net9.0) with zero Grasshopper SDK reference"
    requirement: "CGSR-04"
    verification:
      - kind: other
        ref: "grep -v '^\\s*//' DG/tests/DG.Tests/FrameFixtureTests.cs | grep -c \"using DG.Grasshopper\" (returns 0)"
        status: pass
      - kind: unit
        ref: "dotnet test ./DG/tests/DG.Tests/DG.Tests.csproj --filter \"FullyQualifiedName~FrameFixtureTests\" (5/5 pass)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-18
status: complete
---

# Phase 32 Plan 05: Frame Fixture + Acceptance Proof Summary

**A checked-in Frame RawCanvas JSON fixture pinned to the OWL named individuals, plus a 5-fact xUnit integration test proving CanvasAnnotationParser + ComputgraphContextSerializer together satisfy all four Phase 32 success criteria (CGSR-04).**

## Performance

- **Duration:** 30 min
- **Tasks:** 2
- **Files modified:** 3 (2 new files, 1 csproj edit)

## Accomplishments
- `Fixtures/frame-cg-context.json` -- a hand-authored `RawCanvas` document (camelCase, extractor-output shape) covering the full Frame worked example from RESEARCH.md §3: `OBJECT - FRAME` / `1_ALGORITHM` scribbles, both Proc groups (11/12), a nested-pattern pair (`11_Pat_DivideLine` hosting `11_Pat_TopChord` via `nestedGroupIds`), 4 interfaces, 6 variables (including an integer slider `11_Var_SpansCount` with domain 1-20-1), 8 constants, 10 emergents (including the deliberate `11_Emr_UpperChord` typo), one non-conforming `Scratch notes` group, and one fully unclaimed loose node -- 34 nodes, 33 groups, 1 wire, a fixed `capturedAt` literal for deterministic idempotency
- `DG.Tests.csproj` fixture-copy `ItemGroup` (`Fixtures\**\*.json`, `PreserveNewest`) so the fixture ships next to the test assembly at runtime
- `FrameFixtureTests.cs` -- 5 facts loading the fixture via `AppContext.BaseDirectory` + `File.ReadAllText`, running it through `CanvasAnnotationParser.Parse` and `ComputgraphContextSerializer.Serialize/Deserialize`, asserting all four Phase 32 success criteria plus the Emr-normalization warning and integer-slider dataType/domain inference
- Confirmed zero `DG.Grasshopper` reference in the new test (SC4 grep gate) and the full `DG.Tests` suite (272 tests) shows only the 2 pre-existing live-Neo4j E2E failures already documented in plans 32-02/32-03 -- unrelated to this plan

## Task Commits

Each task was committed atomically:

1. **Task 1: Frame RawCanvas fixture + csproj fixture-copy** - `eaa4cfe` (feat)
2. **Task 2: Frame integration test -- all four Phase 32 success criteria** - `6c4b0c3` (feat)

**Plan metadata:** (pending -- final commit below)

## Files Created/Modified
- `DG/tests/DG.Tests/Fixtures/frame-cg-context.json` - Checked-in `RawCanvas` fixture: annotated Frame worked example pinned to the OWL named individuals, with a deliberate Emr typo and a non-conforming group
- `DG/tests/DG.Tests/FrameFixtureTests.cs` - 5-fact xUnit integration test: SC1 (Object/Algorithm/Procedures/Patterns/Parameters/Interfaces matching OWL individuals + HostPatternId nesting), Emr normalization + warning, integer-slider dataType/domain inference, SC2 (untagged routing), SC3 (idempotent serialization)
- `DG/tests/DG.Tests/DG.Tests.csproj` - Added `Fixtures\**\*.json` `CopyToOutputDirectory PreserveNewest` `ItemGroup`

## Decisions Made
- Node ids/component GUIDs use short descriptive strings (not real GUID format) since nothing in the model/parser/serializer parses or validates them as `Guid` -- readability won out over format realism for a hand-authored fixture
- Procedure groups carry empty `memberIds`; all canvas nodes are owned by the nested convention groups (Pattern/Parameter/Interface), matching how the real annotated canvas structures components
- Only `SpansCount`'s member node carries slider metadata -- the only asserted dataType/domain inference case; other Variable nodes stay unclassified (`DataType == null`) to keep the fixture's signal-to-noise high
- Added a `HostPatternId` assertion into the SC1 fact (not explicitly listed in acceptance criteria) because the plan's task text explicitly requires the host-chain nesting as a fixture element -- asserting it closes the loop between the fixture's construction intent and test coverage

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `dotnet build ./DG/tests/DG.Tests/DG.Tests.csproj -c Debug` succeeds with 0 warnings/errors; `dotnet test --filter "FullyQualifiedName~FrameFixtureTests"` passes 5/5; the full `DG.Tests` suite shows 270/272 passing, with the 2 failures being the pre-existing `DG.Tests.E2E.DesignStateValidationFlowTests` live-Neo4j-connection tests already documented as out-of-scope in the 32-02 and 32-03 SUMMARYs.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 32 (Computgraph Serialization Core) is now fully proven: the object model (32-01), parser (32-02), serializer (32-03), extractor (32-04), and this acceptance fixture/test (32-05) together satisfy CGSR-01 through CGSR-04 and all four Phase 32 success criteria
- The fixture is a stable regression guard: any future change to the parser/serializer that silently breaks the `cgContextJson v1` contract (renamed keys, dropped entities, non-idempotent output) will fail `FrameFixtureTests` in CI before it reaches Phase 33 (bridge), 35 (recognition), or 36 (persistence)
- No blockers or concerns

---
*Phase: 32-computgraph-serialization-core*
*Completed: 2026-07-18*

## Self-Check: PASSED

Both created files (`DG/tests/DG.Tests/Fixtures/frame-cg-context.json`, `DG/tests/DG.Tests/FrameFixtureTests.cs`) found on disk; both commit hashes (`eaa4cfe`, `6c4b0c3`) found in git log.
