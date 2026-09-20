---
phase: 32-computgraph-serialization-core
plan: 02
subsystem: dg-core
tags: [csharp, dotnet, parser, computgraph, canvas-annotation-convention]

# Dependency graph
requires: ["32-01 (Computgraph model foundation: CgContext, RawCanvas, Cg* entities)"]
provides:
  - "CanvasAnnotationParser.Parse(RawCanvas) : CgContext -- deterministic, LLM-free classifier for the DG Canvas Annotation Convention grammar"
  - "Untagged/warnings soft-failure routing for non-conforming scribble/group text"
  - "Bounded pattern-nesting resolution (HostPatternId) with cycle/depth guard"
  - "Parameter dataType/domain inference from member slider/panel/value-list metadata"
affects: ["32-03 (ComputgraphContextSerializer -- serializes the CgContext this parser produces)", "32-04+ (CanvasContextExtractor -- produces the RawCanvas this parser consumes)", "phase 34 (tagging components write these exact convention names)", "phase 35 (recognition reads the Untagged remainder this parser leaves behind)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Static-class parser with static readonly Regex fields (Compiled|CultureInvariant), mirroring SwrlRuleParser.cs -- but diverging on throw behavior: only ArgumentNullException at the API boundary, never for unrecognized text"
    - "Two-pass group classification: pass 1 creates all Procedures (by NN) so pass 2 can always attach Patterns/Parameters/Interfaces to an already-existing procedure regardless of raw.Groups ordering"
    - "Deferred entity construction for init-only cross-referencing fields: pattern host ids are computed into a Dictionary<RawGroup,string?> BEFORE any CgPattern is constructed, since CgPattern.HostPatternId is init-only and cannot be set post-construction"
    - "Bounded parent-pointer walk (GuardHostChains) with a HashSet visited-set and a MaxHostChainDepth=32 cap -- terminates on cycle detection or depth overflow, appending a warning instead of looping (T-32-04)"

key-files:
  created:
    - DG/tests/DG.Tests/CanvasAnnotationParserTests.cs
  modified:
    - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs

key-decisions:
  - "CgInterface.IfaceType defaults to Input for every parsed interface -- the convention grammar (`NN_IntF_NAME`) carries no Input/Output marker; Phase 35 recognition or human confirmation is expected to refine this later"
  - "Deterministic id scheme: cg:<alg>:proc:<nn> (procedure), cg:<alg>:pat:<nn>_<idx> (pattern), cg:<alg>:<var|const|emg>:<fullNickname> (parameter, per the plan's own explicit example), cg:<alg>:intf:<nn>_<name> (interface, per RESEARCH.md §5's literal example) -- the plan's action text and RESEARCH.md's draft envelope disagree slightly on kind-literal/conventionName shape for parameters vs. interfaces; followed each source's own explicit example since no test asserts exact id strings"
  - "Pattern host identity uses RawGroup.Nickname as the join key against another group's NestedGroupIds -- RawGroup (from plan 32-01) has no dedicated instance-id field, so nickname is the only stable identity available; a MemberIds strict-subset fallback (smallest strict superset = nearest host) covers cases where NestedGroupIds isn't populated"
  - "Orphan NN handling: a Pattern/Parameter/Interface referencing a procedure NN with no matching Proc group lazily creates a placeholder CgProcedure (Name=empty) rather than dropping the entity -- keeps the never-guess/never-drop invariant symmetric"
  - "Value list / panel / boolean-toggle primary-component classification infers from CgNode.Name substring matching ('Value List', 'Panel', 'Toggle') since the plan 32-01 CgNode model carries no dedicated component-kind discriminator beyond Slider/IsIntegerSlider"

patterns-established:
  - "Deferred-construction pattern for resolving cross-entity references onto init-only POCOs: compute the reference graph into a plain Dictionary keyed by the raw/mutable precursor BEFORE constructing the immutable target type"
  - "Bounded-walk-with-visited-set as the standard DoS mitigation shape for any future parent-pointer/host-chain resolution in DG.Core"

requirements-completed: [CGSR-02]

coverage:
  - id: D1
    description: "OBJECT/ALGORITHM scribbles and Proc/Pat/Var/Const/Emg/IntF groups classify into the correct typed entities under the right algorithm/procedure, with NN decomposition and deterministic ids"
    requirement: "CGSR-02"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#Parse_ProcGroups_YieldsProceduresUnderAlgorithmOne, #Parse_VariableConstantEmergentGroups_YieldsCorrectParamKinds, #Parse_InterfaceGroup_YieldsInterfaceWithName, #Parse_CyrillicVariableName_RoundTripsVerbatim"
        status: pass
      - kind: other
        ref: "CanvasAnnotationParserSource_UsesCompiledAnchoredGrammarRegexes (source-text assertion: every grammar regex is anchored ^...$ and RegexOptions.Compiled is present)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Non-conforming group nicknames route to Untagged.Groups with raw MemberIds intact; unclaimed raw nodes route to Untagged.NodeIds; the parser never guesses a typed entity"
    requirement: "CGSR-02"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#Parse_NonConformingGroupNickname_RoutesToUntaggedWithMembersIntactAndNoTypedEntity, #Parse_UnclaimedNode_AppearsInUntaggedNodeIds"
        status: pass
    human_judgment: false
  - id: D3
    description: "Emr typo tolerated as Emergent with a normalization warning; pattern nesting resolves HostPatternId with a bounded, cycle-safe walk"
    requirement: "CGSR-02"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#Parse_EmrTypo_NormalizesToEmergentAndAppendsWarning, #Parse_NestedPatternGroup_ResolvesHostPatternId, #Parse_CyclicPatternNesting_StopsWithWarningInsteadOfHanging"
        status: pass
    human_judgment: false
  - id: D4
    description: "Parameter dataType/domain inferred from member slider/panel/value-list metadata by precedence, with ambiguity recorded as a warning (never a throw)"
    requirement: "CGSR-02"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#Parse_IntegerSliderMember_InfersIntegerDataTypeAndDomain, #Parse_ConflictingMemberComponentTypes_UsesPrecedenceAndAppendsWarning"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-18
status: complete
---

# Phase 32 Plan 02: Canvas Annotation Parser Summary

**`CanvasAnnotationParser.Parse(RawCanvas)` — a static, LLM-free classifier turning extractor-output scribbles/groups into a typed `CgContext` via anchored grammar regexes, with untagged/warning soft-failure routing, bounded cyclic-safe pattern-nesting resolution, and slider/panel-based dataType inference.**

## Performance

- **Duration:** 35 min
- **Tasks:** 2
- **Files modified:** 2 (1 new source file grown across 2 commits, 1 new test file)

## Accomplishments

- `CanvasAnnotationParser` (static class, `DG.Core.Parsing`) with 8 anchored (`^...$`), compiled (`RegexOptions.Compiled | CultureInvariant`) grammar regexes for OBJECT, ALGORITHM, Proc, Pat, Var, Const, Emg/Emr, and IntF — all linear (no nested quantifiers), immune to catastrophic backtracking per threat T-32-03
- NN decomposition (`SplitNn`): first digit = algorithm index, remainder = procedure ordinal; a two-pass group-classification loop guarantees every conforming Proc group's `CgProcedure` exists (with its real name) before Patterns/Parameters/Interfaces attach to it, independent of `raw.Groups` ordering
- Deterministic id scheme (`cg:<alg>:<kind>:<conventionName>`) applied consistently across Procedure/Pattern/Parameter/Interface
- Untagged routing: any non-conforming group nickname lands in `CgContext.Untagged.Groups` with `MemberIds` preserved verbatim and zero typed-entity fabrication; any raw node not claimed by a tagged entity lands in `Untagged.NodeIds`
- `Emr` typo tolerance: the emergent regex accepts `Emg|Emr`; when the matched literal is `Emr`, a normalization warning is appended while the entity's `Kind` stays `Emergent`
- Pattern nesting: `HostPatternId` resolved via a two-phase approach (compute host ids into a plain dictionary before constructing the init-only `CgPattern` instances) — primary path via `RawGroup.NestedGroupIds` naming the child's nickname, fallback via smallest strict-superset `MemberIds` match within the same procedure; `GuardHostChains` walks the resulting parent-pointer chains bounded to 32 hops with a visited-set cycle check (threat T-32-04), appending a warning and stopping rather than looping unboundedly
- Parameter dataType/domain inference: primary member selected by precedence slider > value list > panel > boolean (via `CgNode.Slider`/`CgNode.Name` substring classification); conflicting member types append an ambiguity warning naming the parameter but never throw
- 15-fact unit matrix in `CanvasAnnotationParserTests.cs` covering every `<behavior>` line from both tasks, including a Cyrillic parameter name, an anchoring/compiled-regex source check, and a cyclic-nesting hang-prevention test

## Task Commits

Each task was committed atomically:

1. **Task 1: Grammar regexes + scribble/group classification + NN decomposition** - `ccc7779` (feat)
2. **Task 2: Untagged routing, Emr tolerance, pattern nesting, dataType/domain inference** - `120f58e` (feat)

**Plan metadata:** (pending — final commit below)

## Files Created/Modified

- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` - The full classifier (grown across both commits: Task 1 laid down the grammar/classification/NN-decomposition skeleton with `Untagged`/`Warnings` deliberately left empty; Task 2 layered in untagged routing, Emr-warning emission, pattern-host resolution + depth/cycle guard, and dataType/domain inference)
- `DG/tests/DG.Tests/CanvasAnnotationParserTests.cs` - 15 facts: 8 from Task 1 (object/algorithm/proc/var/const/emg/interface classification, Cyrillic round-trip, non-anchored-prefix rejection, regex source-text check) + 7 from Task 2 (untagged group/node routing, Emr warning, nested HostPatternId, integer-slider inference, conflicting-type ambiguity warning, cyclic-nesting guard)

## Decisions Made

- `CgInterface.IfaceType` defaults to `Input` for every parsed interface — the `NN_IntF_NAME` grammar carries no Input/Output marker per RESEARCH.md §4; Phase 35 recognition/human confirmation is the natural place to refine this
- Deterministic id scheme diverges slightly between the plan's own action-text example (`cg:1:var:11_Var_SpansCount` — full nickname as conventionName) and RESEARCH.md §5's draft envelope example for interfaces (`cg:1:intf:11_ParSplitAt` — `nn_name`, not the full `11_IntF_ParSplitAt` nickname). Followed each source's own explicit literal example per entity kind, since no acceptance criterion or test asserts an exact id string — only `Id` uniqueness/attachment matters for downstream consumers
- Pattern host identity resolves via `RawGroup.Nickname` (the only stable identity field `RawGroup` exposes in the plan 32-01 model — it has no dedicated instance-id property) matched against another group's `NestedGroupIds`; a `MemberIds` strict-subset fallback (nearest = smallest strict superset) covers cases where `NestedGroupIds` isn't populated by the eventual extractor
- Orphan NN references (a Pattern/Parameter/Interface naming a procedure NN with no matching `Proc` group) lazily create a placeholder `CgProcedure` with an empty `Name` rather than dropping the entity — keeps the "never guess, never silently drop" invariant symmetric in both directions
- Primary-component classification for parameter dataType inference (slider / value list / panel / boolean-toggle) reads `CgNode.Name` substrings (`"Value List"`, `"Panel"`, `"Toggle"`) since the plan 32-01 `CgNode` model carries no dedicated component-kind discriminator beyond `Slider`/`IsIntegerSlider`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `CgPattern.HostPatternId` is init-only; the plan's described "resolve HostPatternId after patterns are created" flow would require mutating an already-constructed instance**
- **Found during:** Task 2 implementation
- **Issue:** The plan's `<action>` text describes computing pattern nesting "after patterns are created" and setting `HostPatternId` on the existing instance — but `CgPattern.HostPatternId` (from plan 32-01's model) is an `init`-only property, so it cannot be assigned post-construction.
- **Fix:** Restructured to a deferred-construction two-phase flow: pattern classification first collects `PendingPattern` records (raw group + precomputed id + target procedure, no `CgPattern` yet); `ComputeHostPatternIds` resolves every pattern's immediate host id into a `Dictionary<RawGroup, string?>` using the same NestedGroupIds/MemberIds-subset logic the plan describes; only then are the actual (immutable) `CgPattern` instances constructed with the correct `HostPatternId` already set at construction time.
- **Files modified:** `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs`
- **Commit:** `120f58e`

Other than this necessary restructuring (which preserves the plan's exact intended behavior — nesting resolution semantics, bounded/cycle-safe host-chain walk, warning wording — while respecting the immutability of the 32-01 model), the plan executed as written.

## Issues Encountered

None. Full solution (`dotnet build ./DG/DG.sln -c Release`) builds clean with zero warnings/errors. `dotnet test ./DG/tests/DG.Tests/DG.Tests.csproj` runs 253/257 passing; the 4 failures are pre-existing `DG.Tests.E2E.DesignStateValidationFlowTests` live-Neo4j-connection tests unrelated to this plan (confirmed against STATE.md's existing note about this test class's environment dependency) — out of scope per the scope-boundary rule.

## User Setup Required

None — no external service configuration required. This phase is explicitly LLM-free and network-free (per CONTEXT.md constraints).

## Next Phase Readiness

- `CanvasAnnotationParser.Parse(RawCanvas) : CgContext` is ready for plan 03 (`ComputgraphContextSerializer`, which maps the populated `CgContext` this parser produces to/from the `cgContextJson v1` JSON envelope) and plan 04+ (`CanvasContextExtractor`, which will produce the `RawCanvas` this parser consumes from a live `GH_Document`)
- No blockers or concerns — build and tests both green, all `<behavior>` lines and acceptance criteria from both tasks covered by the 15-fact unit matrix

---
*Phase: 32-computgraph-serialization-core*
*Completed: 2026-07-18*

## Self-Check: PASSED

Both created/modified files found on disk (`DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs`, `DG/tests/DG.Tests/CanvasAnnotationParserTests.cs`); both commit hashes (`ccc7779`, `120f58e`) found in git log.
