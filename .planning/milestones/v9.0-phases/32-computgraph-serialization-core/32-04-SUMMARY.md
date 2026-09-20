---
phase: 32-computgraph-serialization-core
plan: 04
subsystem: dg-grasshopper
tags: [csharp, dotnet, grasshopper, canvas-extraction, computgraph, conditional-compilation]

# Dependency graph
requires:
  - phase: 32-computgraph-serialization-core plan 01
    provides: "RawCanvas/RawGroup/RawScribble/CgNode/CgWire/SliderDomain/CgDefinition model shapes"
  - phase: 32-computgraph-serialization-core plan 02
    provides: "CanvasAnnotationParser.Parse(RawCanvas) : CgContext"
  - phase: 32-computgraph-serialization-core plan 03
    provides: "ComputgraphContextSerializer.Serialize(CgContext) : string"
provides:
  - "CanvasContextExtractor.ExtractRaw(GH_Document, project) : RawCanvas -- live GH_Document traversal (nodes, wires, groups+nesting, scribbles, slider domains)"
  - "CanvasContextExtractor.SerializeContext(GH_Document, project) : string -- one-call extract+parse+serialize seam producing cgContextJson v1"
affects: ["phase 33 (DG CANVAS LISTENER get_canvas_context command calls SerializeContext directly)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guard-and-continue traversal: every per-object cast/read wrapped in try/catch that skips (not throws) on failure -- mirrors ValidatorComponent's guard philosophy but adapted to direct GH_Document.Objects iteration rather than IGH_DataAccess"
    - "#if GRASSHOPPER_SDK / #else stub pattern matching DG_OBSIDIAN's canonical shape, with the #else stub declaring the same public method names/return types (RawCanvas, string) but an object-typed doc parameter (GH_Document itself is unavailable to the compiler when GRASSHOPPER_SDK is undefined, since the Rhino/Grasshopper assembly references are conditional in the .csproj)"
    - "Bounded pairwise group-nesting scan: for each group, iterate all other groups once and test ObjectIDs.Contains -- O(n^2) worst case but n = document group count, no recursion (T-32-10)"

key-files:
  created:
    - DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
  modified: []

key-decisions:
  - "Split the single-file plan into two atomic commits mirroring the plan's two tasks: Task 1 commit contains only ExtractRaw + traversal helpers (with a stub exposing only ExtractRaw); Task 2 commit adds SerializeContext to both the real and stub branches plus the DG.Core.Parsing/DG.Core.Serialization usings -- both commits independently build clean, matching plans 32-02/32-03's precedent of growing one file across two atomic commits"
  - "#else stub's ExtractRaw/SerializeContext take `object? doc` (not GH_Document) because the Grasshopper/RhinoCommon assembly references in DG.Grasshopper.csproj are themselves conditional on Exists(RhinoCommon.dll) -- GH_Document is not a resolvable type at all when GRASSHOPPER_SDK is undefined, so the 'same signature' acceptance criterion is satisfied on name/return-type (RawCanvas, string) rather than the doc parameter type; both stub methods throw PlatformNotSupportedException"
  - "Node/wire/group/scribble collection split into three passes over doc.Objects (groups+scribbles+nodes in pass 1, group-nesting resolution in pass 2, wire enumeration in pass 3) rather than one combined pass, so group-nesting can reference the fully-populated groupsByGuid dictionary and wire enumeration can treat every doc object uniformly (component -> Params.Input, floating IGH_Param -> itself)"
  - "Wire FromNode/ToNode resolved via `param.Attributes.GetTopLevel.DocObject.InstanceGuid` (the owning component's instance guid, or the param's own instance guid if it is a floating param) -- exactly the plan's specified API path, giving symmetric behavior for both component-owned params and standalone floating params"
  - "Slider Step derived from `GH_SliderAccuracy.Integer -> 1.0`, otherwise `10^-DecimalPlaces` -- not specified as an exact formula in RESEARCH.md/CONTEXT.md, chosen as the most direct reading of 'step from decimal places'"

requirements-completed: [CGSR-03]

coverage:
  - id: D1
    description: "With the Grasshopper SDK available, the extractor traverses a live GH_Document into a RawCanvas carrying every component, wire, group (with nesting), scribble, and slider domain"
    requirement: "CGSR-03"
    verification:
      - kind: other
        ref: "dotnet build ./DG/src/DG.Grasshopper/DG.Grasshopper.csproj -c Release (Rhino 8 SDK present in this environment -- GRASSHOPPER_SDK branch compiles); source assertions: GH_Document (7 refs), GH_Group, GH_Scribble, IGH_Param, GH_NumberSlider, .Sources, .ObjectIDs all present"
        status: pass
    human_judgment: false
  - id: D2
    description: "The extractor exposes a one-call seam that turns a GH_Document into a cgContextJson v1 string by chaining the DG.Core parser + serializer"
    requirement: "CGSR-03"
    verification:
      - kind: other
        ref: "SerializeContext composes ExtractRaw -> CanvasAnnotationParser.Parse -> ComputgraphContextSerializer.Serialize; dotnet build ./DG/src/DG.Core/DG.Core.csproj confirmed still green (no GH leak into DG.Core)"
        status: pass
    human_judgment: false
  - id: D3
    description: "When GRASSHOPPER_SDK is undefined the file compiles to a stub so DG.Grasshopper still builds"
    requirement: "CGSR-03"
    verification:
      - kind: other
        ref: "dotnet build ./DG/src/DG.Grasshopper/DG.Grasshopper.csproj -c Release -p:RhinoInstallDir=\"C:\\NoSuchRhinoDir\" (forces GRASSHOPPER_SDK undefined) -- builds clean, 0 warnings/0 errors"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-18
status: complete
---

# Phase 32 Plan 04: Canvas Context Extractor Summary

**`CanvasContextExtractor` (DG.Grasshopper, `#if GRASSHOPPER_SDK`) -- a pure GH_Document -> RawCanvas traversal (nodes, wires, groups with nesting, scribbles, slider domains) plus a one-call `SerializeContext` seam chaining the DG.Core parser and serializer into a cgContextJson v1 string.**

## Performance

- **Duration:** 30 min
- **Tasks:** 2
- **Files modified:** 1 (new source file, grown across 2 commits)

## Accomplishments

- `CanvasContextExtractor.ExtractRaw(GH_Document, project)` traverses `doc.Objects` in three passes: (1) classify every object into `RawGroup`/`RawScribble`/`CgNode` (component-or-param default case), (2) resolve group nesting (`NestedGroupIds`) via a bounded pairwise `ObjectIDs.Contains` scan across the document's groups, (3) enumerate wires by walking every component's `Params.Input` (or a floating param's own `Sources`)
- Slider domains: `GH_NumberSlider.Slider.Minimum/Maximum` map to `SliderDomain.Min/Max`; `Step` is `1.0` for `GH_SliderAccuracy.Integer`, otherwise `10^-DecimalPlaces`; `IsIntegerSlider` set from the same `Type` check
- Wire endpoints are param instance GUIDs (`FromParam`/`ToParam`); `FromNode`/`ToNode` resolve to the owning component (or the param itself, if floating) via `param.Attributes.GetTopLevel.DocObject.InstanceGuid`
- Guard-and-continue on every per-object try/catch (node read, slider read, scribble read, group read, wire read) -- a single malformed canvas object cannot abort the traversal (T-32-10); a null `GH_Document` returns an empty, well-formed `RawCanvas` rather than throwing
- `SerializeContext(GH_Document, project)` composes `ExtractRaw` -> `CanvasAnnotationParser.Parse` -> `ComputgraphContextSerializer.Serialize` as a thin one-call seam -- the exact entry point Phase 33's `get_canvas_context` command will invoke
- Full `#if GRASSHOPPER_SDK ... #else ... #endif` wrapper matching the repo's canonical conditional-compilation shape; the `#else` stub declares both `ExtractRaw` and `SerializeContext` (same names/return types), throwing `PlatformNotSupportedException`, so the public surface exists in both compilation modes
- Verified in both directions: `dotnet build ./DG/src/DG.Grasshopper/DG.Grasshopper.csproj -c Release` compiles the real implementation (Rhino 8 SDK present in this environment) and, forcing `RhinoInstallDir` to a nonexistent path, compiles the stub -- both 0 warnings/0 errors; `dotnet build ./DG/src/DG.Core/DG.Core.csproj` confirms DG.Core gained no Grasshopper dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: GH_Document traversal -> RawCanvas (components, wires, groups+nesting, scribbles, slider domains)** - `2c55fd9` (feat)
2. **Task 2: SerializeContext seam (extract -> parse -> serialize -> cgContextJson v1)** - `c7c5397` (feat)

**Plan metadata:** (pending -- final commit below)

## Files Created/Modified

- `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` - Static class in `DG.Grasshopper.Canvas`: `ExtractRaw` (Task 1, GH_Document traversal) + `SerializeContext` (Task 2, extract/parse/serialize composition), with private `TryAddNode`/`TryReadSliderDomain`/`TryAddScribble`/`TryAddGroup`/`TryAddWires`/`TryAddWire` helpers, all guard-and-continue; `#else` stub for both public methods

## Decisions Made

- Split the single-file plan into two atomic commits mirroring the plan's two tasks, matching the precedent set by plans 32-02/32-03 (one file grown across two commits); each commit independently builds clean
- `#else` stub methods take `object? doc` rather than `GH_Document` -- `GH_Document` is not a resolvable type at all when `GRASSHOPPER_SDK` is undefined (the Rhino/Grasshopper assembly references in `DG.Grasshopper.csproj` are themselves conditional on `Exists(RhinoCommon.dll)`), so an identical parameter type is impossible; the stub matches on method name and return type (`RawCanvas`, `string`) instead, both throwing `PlatformNotSupportedException`
- Traversal split into three passes over `doc.Objects` (classify -> resolve nesting -> enumerate wires) rather than one combined pass, so group-nesting resolution can reference a fully-populated `groupsByGuid` dictionary and wire enumeration can treat every doc object uniformly
- Slider `Step` computed as `1.0` for `GH_SliderAccuracy.Integer`, else `10^-DecimalPlaces` -- the plan's "step from decimal places" wording left the exact formula to Claude's discretion; chose the most direct reading

## Deviations from Plan

None - plan executed exactly as written. The only structural departure (splitting the single described file-growth into two atomic commits rather than one combined commit) is process, not implementation, and matches the pattern already established by plans 32-02 and 32-03.

## Issues Encountered

None. `dotnet build ./DG/DG.sln -c Release` builds clean (0 warnings, 0 errors) with the real Rhino 8-backed `CanvasContextExtractor` implementation. `dotnet test ./DG/tests/DG.Tests/DG.Tests.csproj -c Release` runs 263/267 passing; the 4 failures are the pre-existing `DG.Tests.E2E.DesignStateValidationFlowTests` live-Neo4j-connection tests (unrelated to this plan, already noted in the 32-02/32-03 summaries) -- out of scope per the scope-boundary rule. No unit test is possible for the GH-SDK traversal itself (Success Criterion 4 keeps GH out of DG.Tests, per the plan's own `<verification>` section) -- the compile gate (both SDK-present and SDK-absent) plus source assertions are the honest verification for this plan; live-canvas behavior will be exercised by Phase 33 + Phase 40 E2E.

## User Setup Required

None -- no external service configuration required. This plan is LLM-free and network-free (per CONTEXT.md constraints); it also does not require an actual Rhino/Grasshopper session to build (Rhino 8 SDK is installed in this build environment, but the stub path was also verified independently).

## Next Phase Readiness

- `CanvasContextExtractor.SerializeContext(GH_Document, project) : string` is ready for Phase 33's DG CANVAS LISTENER (`get_canvas_context` command) to call directly -- it is the complete, one-call live-canvas-to-cgContextJson-v1 entry point
- Phase 32's four-plan pure-logic foundation (model / parser / serializer / extractor) is now complete: `RawCanvas` (32-01) -> `CanvasAnnotationParser` (32-02) -> `ComputgraphContextSerializer` (32-03) -> `CanvasContextExtractor` (32-04) form the full canvas-to-JSON pipeline
- No blockers or concerns -- build green in both SDK-present and SDK-absent modes; DG.Core confirmed to carry zero Grasshopper dependency

---
*Phase: 32-computgraph-serialization-core*
*Completed: 2026-07-18*

## Self-Check: PASSED

Created file (`DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs`) found on disk; both commit hashes (`2c55fd9`, `c7c5397`) found in git log.
