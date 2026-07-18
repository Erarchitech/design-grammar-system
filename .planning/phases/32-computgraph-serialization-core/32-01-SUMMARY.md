---
phase: 32-computgraph-serialization-core
plan: 01
subsystem: infra
tags: [csharp, dotnet, poco, computgraph, ontology-mirror]

# Dependency graph
requires: []
provides:
  - "GH-free Computgraph object model in DG.Core.Models.Computgraph (CgObject, CgAlgorithm, CgProcedure, CgPattern, CgParameter, CgInterface, CgNode, CgWire, SliderDomain)"
  - "cgContextJson v1 document root (CgContext, CgDefinition, CgUntagged, CgUntaggedGroup)"
  - "RawCanvas extractor-output input contract (RawCanvas, RawGroup, RawScribble)"
  - "ParamKind, ParamDataType, IfaceType enums matching CONTEXT decision #1 wording"
affects: [32-computgraph-serialization-core plan 02 (CanvasAnnotationParser), plan 03 (ComputgraphContextSerializer), plan 04+ (CanvasContextExtractor), phase 33 bridge, phase 35 recognition, phase 36 persistence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "POCO model style mirrored exactly from ObjState.cs/DesignStateParameter.cs/ParamState.cs: init-only auto-properties, non-null strings default to string.Empty, List<T> defaults to new(), nullable reference types for optional fields, no serialization attributes"
    - "Pattern nesting via flat parent-pointer (HostPatternId) instead of recursive nested List — arbitrary host-chain depth without unbounded recursion"
    - "Wire endpoints reference param instance GUIDs (stable under renames), not param indices"

key-files:
  created:
    - DG/src/DG.Core/Models/Computgraph/CgObject.cs
    - DG/src/DG.Core/Models/Computgraph/CgAlgorithm.cs
    - DG/src/DG.Core/Models/Computgraph/CgProcedure.cs
    - DG/src/DG.Core/Models/Computgraph/CgPattern.cs
    - DG/src/DG.Core/Models/Computgraph/CgParameter.cs
    - DG/src/DG.Core/Models/Computgraph/CgInterface.cs
    - DG/src/DG.Core/Models/Computgraph/CgNode.cs
    - DG/src/DG.Core/Models/Computgraph/CgWire.cs
    - DG/src/DG.Core/Models/Computgraph/CgContext.cs
    - DG/src/DG.Core/Models/Computgraph/RawCanvas.cs
    - DG/tests/DG.Tests/ComputgraphModelTests.cs
  modified: []

key-decisions:
  - "CgObject.Source stays a plain string (\"tagged\"|\"recognized\"), not an enum — matches the envelope's freeform value and avoids enum-serialization config; Phase 35 adds \"recognized\" as a second literal value"
  - "SliderDomain and the three enums (ParamKind, ParamDataType, IfaceType) live alongside their owning entity (CgParameter.cs, CgInterface.cs) rather than in separate files — kept file count at exactly the 10 the plan specifies"
  - "CgDefinition is a shared type used by both CgContext and RawCanvas (not duplicated) since both envelopes carry identical documentId/fileName/capturedAt semantics per RESEARCH §5"

patterns-established:
  - "Computgraph POCOs: zero Grasshopper references, zero serialization attributes — the serializer (plan 03) owns its own DTO tree and maps both directions"
  - "Untagged/warnings sub-pattern (CgUntagged, CgUntaggedGroup, CgContext.Warnings) as a new soft-failure bucket convention for DG.Core, to be used by the parser in plan 02"

requirements-completed: [CGSR-01]

coverage:
  - id: D1
    description: "GH-free Computgraph entity model (8 entity types + SliderDomain + 3 enums) compiles in DG.Core with zero Grasshopper references"
    requirement: "CGSR-01"
    verification:
      - kind: unit
        ref: "dotnet build ./DG/src/DG.Core/DG.Core.csproj -c Debug"
        status: pass
      - kind: other
        ref: "grep -rl \"using Grasshopper\" DG/src/DG.Core/Models/Computgraph/ (zero matches)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CgContext document root mirrors cgContextJson v1 envelope; RawCanvas mirrors the GH-free extractor-output input contract"
    requirement: "CGSR-01"
    verification:
      - kind: unit
        ref: "DG.Tests/ComputgraphModelTests.cs#CgContext_DefaultConstruction_SchemaVersionIsCgContext1"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphModelTests.cs#RawCanvas_DefaultConstruction_CollectionsAreNonNullAndEmpty"
        status: pass
    human_judgment: false
  - id: D3
    description: "ParamKind, ParamDataType, IfaceType enums carry exactly the members named in CONTEXT decision #1"
    requirement: "CGSR-01"
    verification:
      - kind: unit
        ref: "DG.Tests/ComputgraphModelTests.cs#ParamKind_EnumMembers_MatchContextDecision"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphModelTests.cs#ParamDataType_EnumMembers_MatchContextDecision"
        status: pass
      - kind: unit
        ref: "DG.Tests/ComputgraphModelTests.cs#IfaceType_EnumMembers_MatchContextDecision"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-18
status: complete
---

# Phase 32 Plan 01: Computgraph Model Foundation Summary

**GH-free Computgraph POCO model (CgObject through CgWire + CgContext/RawCanvas) mirroring the ontology's Computgraph layer, with a 6-fact construction/enum smoke test — the shared vocabulary for the canvas→Computgraph pipeline.**

## Performance

- **Duration:** 20 min
- **Tasks:** 2
- **Files modified:** 11 (10 new source files + 1 new test file)

## Accomplishments
- Eight entity POCOs (CgObject, CgAlgorithm, CgProcedure, CgPattern, CgParameter, CgInterface, CgNode, CgWire) in `DG.Core.Models.Computgraph`, zero Grasshopper references, following the `ObjState.cs`/`DesignStateParameter.cs`/`ParamState.cs` style exactly
- Three enums (`ParamKind`, `ParamDataType`, `IfaceType`) with exact member wording from CONTEXT decision #1, plus `SliderDomain` (min/max/step)
- `CgContext` document root mirroring the `cgContextJson v1` envelope 1:1 (schemaVersion, project, definition, object, algorithms, untagged, nodes, wires, warnings) — the versioned contract for the parser/serializer/extractor plans
- `RawCanvas` extractor-output input contract (`RawGroup` with `NestedGroupIds` for pattern-nesting detection, `RawScribble`) — the GH-free shape the DG.Grasshopper extractor will produce
- `ComputgraphModelTests.cs` — 6 passing facts proving default construction (non-null empty collections) and enum membership

## Task Commits

Each task was committed atomically:

1. **Task 1: Computgraph entity model + enums** - `44a776f` (feat)
2. **Task 2: CgContext document root + RawCanvas input contract + model smoke test** - `895a6a6` (feat)

**Plan metadata:** (pending — final commit below)

## Files Created/Modified
- `DG/src/DG.Core/Models/Computgraph/CgObject.cs` - Object entity (name, optional classIri, source)
- `DG/src/DG.Core/Models/Computgraph/CgAlgorithm.cs` - Algorithm (index, name, Procedures list)
- `DG/src/DG.Core/Models/Computgraph/CgProcedure.cs` - Procedure (id, index NN, name, MemberIds, Patterns, Parameters, Interfaces)
- `DG/src/DG.Core/Models/Computgraph/CgPattern.cs` - Pattern with HostPatternId flat-nesting reference
- `DG/src/DG.Core/Models/Computgraph/CgParameter.cs` - Parameter + ParamKind/ParamDataType enums + SliderDomain
- `DG/src/DG.Core/Models/Computgraph/CgInterface.cs` - Interface + IfaceType enum
- `DG/src/DG.Core/Models/Computgraph/CgNode.cs` - Raw canvas component (instance GUID, position, optional slider metadata)
- `DG/src/DG.Core/Models/Computgraph/CgWire.cs` - Wire (FromNode/FromParam/ToNode/ToParam, all instance GUIDs)
- `DG/src/DG.Core/Models/Computgraph/CgContext.cs` - Document root (CgContext, CgDefinition, CgUntagged, CgUntaggedGroup)
- `DG/src/DG.Core/Models/Computgraph/RawCanvas.cs` - Extractor-output input contract (RawCanvas, RawGroup, RawScribble)
- `DG/tests/DG.Tests/ComputgraphModelTests.cs` - Construction/enum smoke test, 6 facts

## Decisions Made
- `CgObject.Source` stays a plain `string` ("tagged"|"recognized") rather than an enum, per plan's explicit "Claude's discretion" note — matches the freeform envelope value and avoids enum-serialization config since Phase 35 adds a second literal value
- `SliderDomain` and the three enums live in their owning entity's file (`CgParameter.cs`, `CgInterface.cs`) rather than separate files, keeping the file count at exactly the 10 the plan specifies
- `CgDefinition` is a single shared type reused by both `CgContext` and `RawCanvas` (not duplicated) since both envelopes need identical `documentId`/`fileName`/`capturedAt` fields per RESEARCH §5

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `Cg*` model + `CgContext` + `RawCanvas` contracts are ready for plan 02 (`CanvasAnnotationParser`, which will consume `RawCanvas` and produce a populated `CgContext`) and plan 03 (`ComputgraphContextSerializer`, which will map `CgContext` to/from the `cgContextJson v1` JSON envelope)
- No blockers or concerns — build and tests both green, zero Grasshopper references confirmed via grep

---
*Phase: 32-computgraph-serialization-core*
*Completed: 2026-07-18*
