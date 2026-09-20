---
phase: 35-llm-recognition-canvas-preview
plan: 02
subsystem: canvas
tags: [csharp, grasshopper, dg-core, canvas-annotation-parser, preview-registry, value-table]

# Dependency graph
requires:
  - phase: 35-llm-recognition-canvas-preview (plan 01)
    provides: cg_recognition.py bounded-retry LLM recognition endpoint + proposal validation shape
  - phase: 34-tagging-components
    provides: CanvasAnnotationParser/NameFactory grammar (Proc/Pat/Var/Const/Emg/IntF), CanvasAnnotationStyles color scaffold
provides:
  - PreviewRegistry (internal static class) with PreviewEntry/ProposalDto shared state for the Wave-2 listener/confirm components
  - CanvasAnnotationStyles.PreviewPrefix ("[?] ") preview name-prefix constant
  - RawGroup.Recognized (bool, additive) + CanvasContextExtractor ValueTable read path (dg.recognized.<groupGuid>)
  - CanvasAnnotationParser Source == "recognized" propagation for group-derived Procedure/Pattern/Parameter/Interface entities
affects: [35-03, 35-04, wave-2-canvas-preview-components]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PreviewRegistry follows the CanvasAnnotationStyles internal-static-class idiom, extended with ConcurrentDictionary for cross-component shared state (both writers run on the GH UI thread but the concurrent collection removes any doubt at zero cost)"
    - "Document ValueTable marker namespace dg.recognized.<groupInstanceGuid> reuses the ObjectMarkerComponent/dg.objectClassIri precedent for .gh-save-survivable per-group state"

key-files:
  created:
    - DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs
    - DG/tests/DG.Tests/CanvasAnnotationParserRecognizedSourceTests.cs
  modified:
    - DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs
    - DG/src/DG.Core/Models/Computgraph/RawCanvas.cs
    - DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs
    - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs

key-decisions:
  - "PreviewRegistry backed by ConcurrentDictionary<string, PreviewEntry>; RegisterAll zips (proposalId, groupGuid) pairs against ProposalDto by proposal id, skipping any pair with no counterpart rather than throwing"
  - "ProposalDto.ToEntityTagKind() maps the wire kind string to EntityTagKind case-insensitively via Enum.TryParse, throwing ArgumentOutOfRangeException for an unrecognized kind (never guesses, mirrors the parser's own philosophy)"
  - "CanvasContextExtractor.TryAddGroup threads GH_Document (nullable) into its signature; recognized read is doc?.ValueTable.GetValue(...) == \"true\" so a null doc (already-guarded ExtractRaw early-return path) never throws"
  - "Parser Source propagation uses group.Recognized ? \"recognized\" : \"tagged\" at all 4 group-derived construction sites (Procedure, Parameter, Interface use the loop's group; Pattern uses pending.Group since CgPattern construction happens in a later pass)"

patterns-established:
  - "Additive-only grammar/model extension: new bool field defaults false, existing hard-coded literal replaced with a ternary reading it, zero changes to classification regexes or existing test expectations"

requirements-completed: [RCGN-02, RCGN-03]

coverage:
  - id: D1
    description: "Shared PreviewRegistry (ConcurrentDictionary-backed) with PreviewEntry/ProposalDto records, exposing RegisterAll/Pending/TryGet/Remove/Clear for the Wave-2 listener and confirm components"
    requirement: "RCGN-03"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (Release build clean, GRASSHOPPER_SDK branch compiled)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CanvasAnnotationStyles.PreviewPrefix (\"[?] \") constant available for RCGN-02 preview name styling"
    requirement: "RCGN-02"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (Release build clean); grep -c PreviewPrefix CanvasAnnotationStyles.cs >= 1"
        status: pass
    human_judgment: false
  - id: D3
    description: "RawGroup.Recognized carries the document ValueTable dg.recognized.<groupGuid> marker from extractor through to CanvasAnnotationParser, setting Source == \"recognized\" on group-derived Procedure/Pattern/Parameter/Interface entities while classification (kind) stays unaffected; existing parser/NameFactory/FrameFixture regression suites pass unmodified"
    requirement: "RCGN-03"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserRecognizedSourceTests.cs (6 tests: recognized Procedure/Pattern/Parameter/Interface, unrecognized-stays-tagged control, kind-unchanged control)"
        status: pass
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ --filter FullyQualifiedName~CanvasAnnotationParser (21/21 pass)"
        status: pass
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ (347/350 pass; 3 known env-dependent Neo4j E2E failures unrelated to this plan)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-19
status: complete
---

# Phase 35 Plan 02: Preview Registry + Recognized-Source Foundation Summary

**Shared GH-free foundation for canvas preview: a ConcurrentDictionary-backed PreviewRegistry, a `[?] ` preview name-prefix constant, and additive `Source == "recognized"` propagation from the document ValueTable through RawGroup into CanvasAnnotationParser's typed entities.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-19T09:25:58Z
- **Completed:** 2026-07-19T09:32:25Z
- **Tasks:** 3 completed
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- `PreviewRegistry` (internal static class, `ConcurrentDictionary<string, PreviewEntry>`-backed) with `RegisterAll`/`Pending`/`TryGet`/`Remove`/`Clear`, plus `PreviewEntry` and `ProposalDto` records — the shared state holder that will let the Wave-2 listener (writer, after a recognition run) and the confirm/reject component (reader/mutator) see the same pending proposals without either owning the other (RCGN-03 enabler)
- `CanvasAnnotationStyles.PreviewPrefix = "[?] "` constant for rendering an unconfirmed proposal's display name distinctly, alongside the existing `Preview(Color)` desaturation scaffold (RCGN-02 enabler)
- `RawGroup.Recognized` (additive `bool`, defaults `false`) on the GH-free `RawCanvas` model, populated by `CanvasContextExtractor.TryAddGroup` reading `doc.ValueTable.GetValue("dg.recognized.<groupInstanceGuid>", "false")` — the same document-ValueTable persistence mechanism `ObjectMarkerComponent` already uses for `dg.objectClassIri`, chosen because it survives `.gh` save/reopen (unlike an in-memory listener dictionary)
- `CanvasAnnotationParser.Parse` now sets `Source = group.Recognized ? "recognized" : "tagged"` at all 4 group-derived typed-entity construction sites (Procedure, Pattern, Parameter, Interface) instead of the hard-coded `"tagged"` literal — additive only, zero changes to the classification regexes
- New `CanvasAnnotationParserRecognizedSourceTests.cs` (6 tests, TDD RED→GREEN) covering all 4 recognized-source cases plus an unrecognized-stays-tagged control and a kind-unchanged control

## Task Commits

Each task was committed atomically:

1. **Task 1: PreviewRegistry + PreviewEntry + ProposalDto + [?] style prefix** - `33f7acd` (feat)
2. **Task 2: RawGroup.Recognized + extractor ValueTable read (thread doc into TryAddGroup)** - `7c411f5` (feat)
3. **Task 3: Parser Source propagation (recognized) + DG.Core regression-safe test** - `378b6f1` (test, RED) → `b6002dc` (feat, GREEN)

## Files Created/Modified

- `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs` (new) - Shared `ConcurrentDictionary`-backed proposal registry + `PreviewEntry`/`ProposalDto` records
- `DG/src/DG.Grasshopper/Canvas/CanvasAnnotationStyles.cs` - Added `PreviewPrefix` constant next to the existing `Preview(Color)` scaffold
- `DG/src/DG.Core/Models/Computgraph/RawCanvas.cs` - Added `RawGroup.Recognized` bool
- `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` - `TryAddGroup` now accepts `GH_Document?` and reads the `dg.recognized.<guid>` ValueTable marker
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` - Group-derived `Source` assignment reads `group.Recognized`/`pending.Group.Recognized` instead of a hard-coded literal
- `DG/tests/DG.Tests/CanvasAnnotationParserRecognizedSourceTests.cs` (new) - RecognizedSource regression-safe test suite

## Decisions Made

- Persistence mechanism (per plan's locked decision): `source: recognized` persists via `GH_Document.ValueTable` keyed `dg.recognized.<groupInstanceGuid>`, following the proven `ObjectMarkerComponent` precedent, not an in-memory listener dictionary or sidecar file.
- `PreviewRegistry.RegisterAll` skips any `(proposalId, groupGuid)` pair with no matching `ProposalDto` (or vice versa) rather than throwing — keeps registration best-effort against a partially-applied confirm batch.
- `ProposalDto.ToEntityTagKind()` uses case-insensitive `Enum.TryParse` and throws `ArgumentOutOfRangeException` for an unrecognized kind string, matching the parser's "never guess" philosophy rather than silently defaulting.
- `TryAddGroup`'s new `GH_Document? doc` parameter is nullable and read with `doc?.ValueTable...`, so the pre-existing null-doc early-return path in `ExtractRaw` (which never reaches `TryAddGroup`) stays unaffected and no new null-guard branch was needed.

## Deviations from Plan

None - plan executed exactly as written. All 4 must-haves truths from the plan frontmatter are satisfied: PreviewRegistry visible to both listener/confirm components, `[?] ` prefix constant present, recognized-marked groups parse to `Source == "recognized"` (unmarked stay `"tagged"`), and the existing CanvasAnnotationParser/NameFactory/FrameFixture regression suites pass unmodified.

## Issues Encountered

None. The 3 `DesignStateValidationFlowTests.E2E` failures observed in the full `dotnet test` run are the pre-existing env-dependent Neo4j-down baseline documented in project memory (`dg-tests-neo4j-e2e-baseline`), unrelated to this plan's changes — confirmed by diffing against the pre-change build (this plan touches only `Canvas`/`Parsing`/`Models.Computgraph` files, nowhere near the E2E flow's Neo4j dependency).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `PreviewRegistry`, `PreviewPrefix`, and the `Recognized` read path are all in place for Plan 35-04 (write path: `StructureConfirmComponent`/listener wiring that actually sets the `dg.recognized.<guid>` marker and calls `PreviewRegistry.RegisterAll`) and Plan 35-03's preview-rendering consumers.
- No blockers. The parser's group-derived `Source` field is now a real (if still write-side-unpopulated) signal; Plan 35-04 is expected to wire the actual write path per the plan's `artifacts_produced` note ("write path is Plan 35-04").

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-19*

## Self-Check: PASSED

All 6 files created/modified confirmed present on disk; all 4 task commit hashes (33f7acd, 7c411f5, 378b6f1, b6002dc) confirmed in git log.
