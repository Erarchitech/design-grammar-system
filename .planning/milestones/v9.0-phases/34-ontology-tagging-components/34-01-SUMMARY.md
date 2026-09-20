---
phase: 34-ontology-tagging-components
plan: 01
subsystem: grasshopper-plugin
tags: [dg-core, parsing, canvas-annotation, xunit, tdd]

# Dependency graph
requires:
  - phase: 32-canvas-serialization-core
    provides: CgContext/RawCanvas Computgraph model shapes, CanvasAnnotationParser read path
provides:
  - CanvasAnnotationGrammar (shared grammar-token constants, ReservedInfixTokens)
  - CanvasAnnotationNameFactory (write path) + EntityTagKind enum
  - Round-trip-proven (write -> parse) name construction for all six EntityTagKind values plus Object/Algorithm scribbles
affects: [34-02-ontology-tagging-components, 34-03-ontology-tagging-components]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Grammar constants mirror parser regex literals without editing the locked parser source; drift caught by a source-inspection consistency test"
    - "NN token built by string concatenation, never arithmetic, to invert CanvasAnnotationParser.SplitNn safely"

key-files:
  created:
    - DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs
    - DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs
    - DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs
  modified: []

key-decisions:
  - "Additive-only grammar extraction (DEVIATES from RESEARCH Pattern 1) -- CanvasAnnotationParser.cs is never edited; a consistency test enforces single-source-of-truth in both directions instead"
  - "ProcIndex is the full NN token uniformly across all Kinds (adopts RESEARCH Open Question 1); NN < 10 rejected"
  - "Pattern naming: idx slot is always the auto-assigned integer; a provided Name is the optional trailing label (NN_Pat_idx or NN_Pat_idx Name)"
  - "Consistency test checks bare Emg/Emr tag literals (not the full _Emg_/_Emr_ infix) because the parser embeds them inside a capture-group alternation (_(?<tag>Emg|Emr)_), so the contiguous underscored substring never appears verbatim in source"

patterns-established:
  - "Write-path factory methods are pure, culture-invariant, and validated inline (ValidateName) so every constructed name is guaranteed parseable before it reaches the parser"

requirements-completed: [TAGC-01, TAGC-02, TAGC-03]

coverage:
  - id: D1
    description: "CanvasAnnotationGrammar token constants extracted, matching parser's literal regex tokens exactly"
    requirement: "TAGC-01"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#Grammar_ConstantsAppearVerbatimInParserSource"
        status: pass
    human_judgment: false
  - id: D2
    description: "CanvasAnnotationNameFactory builds grammar-conformant names for all six EntityTagKind values plus Object/Algorithm scribbles"
    requirement: "TAGC-01"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#ForEntity_Var_BuildsVariableName (and 8 sibling construction facts)"
        status: pass
    human_judgment: false
  - id: D3
    description: "NextFreePatternIndex computes the next-free integer Pattern index under a given NN (auto-increment)"
    requirement: "TAGC-02"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#NextFreePatternIndex_ExistingPatterns_ReturnsMaxPlusOne"
        status: pass
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#NextFreePatternIndex_NoExistingPatterns_ReturnsOne"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every factory-built name round-trips through CanvasAnnotationParser.Parse to the expected typed entity with Source == 'tagged' (write/read grammar symmetry)"
    requirement: "TAGC-03"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#RoundTrip_* (10 facts: Object, Algorithm, Proc, Var, Const, Emg, IntF, Pat-with-name, Pat-without-name, Cyrillic Var)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Reserved grammar infix tokens and structurally invalid input (empty/whitespace Name, NN < 10) are rejected with What+Where+How-to-fix ArgumentException/ArgumentOutOfRangeException"
    requirement: "TAGC-01"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#ForEntity_NameContainsReservedInfixToken_ThrowsArgumentException"
        status: pass
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationNameFactoryTests.cs#ForEntity_ProcIndexBelowTen_ThrowsArgumentOutOfRangeException"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-18
status: complete
---

# Phase 34 Plan 01: CanvasAnnotationGrammar + CanvasAnnotationNameFactory Summary

**GH-free write-path foundation for canvas tagging: a shared grammar-token constants class plus a pure name factory that provably round-trips through `CanvasAnnotationParser` for all six entity kinds, with the parser source left byte-identical.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-18T20:50:36Z
- **Completed:** 2026-07-18T21:15:00Z
- **Tasks:** 2
- **Files modified:** 3 (2 created source, 1 created test)

## Accomplishments
- `CanvasAnnotationGrammar` static class mirrors all 8 literal grammar tokens embedded in `CanvasAnnotationParser`'s regexes (`ObjectPrefix`, `AlgorithmSuffix`, `ProcedureInfix`, `PatternInfix`, `VariableInfix`, `ConstantInfix`, `EmergentInfix`, `EmergentToleratedInfix`, `InterfaceInfix`) plus `ReservedInfixTokens`, with a source-inspection consistency test guarding against drift in either direction
- `CanvasAnnotationNameFactory` (write path) with `EntityTagKind` enum builds names for `ForObjectScribble`, `ForAlgorithmScribble`, and `ForEntity` across all six kinds (Proc/Pat/Var/Const/Emg/IntF), plus `NextFreePatternIndex`, `IsReservedName`, `ValidateName`
- TAGC-03 round-trip symmetry proven by construction + test: every factory-built name parses back through `CanvasAnnotationParser.Parse` to the expected typed entity with `Source == "tagged"`, for all six kinds plus Object/Algorithm scribbles, including a Cyrillic name case
- `CanvasAnnotationParser.cs` never edited — confirmed via `git diff --exit-code` after both tasks
- Zero regressions: full `DG.Tests` suite 340/341 (the 1 failure is the documented pre-existing Neo4j-down E2E baseline, unrelated to this change)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract CanvasAnnotationGrammar token constants + parser-consistency regression test** - `a993322` (feat)
2. **Task 2: CanvasAnnotationNameFactory (write path) + xUnit round-trip suite** - `4002175` (feat)

**Plan metadata:** (this commit) - docs: complete plan

## Files Created/Modified
- `DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs` - Shared grammar-token constants + `ReservedInfixTokens` array
- `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs` - Write-path name factory + `EntityTagKind` enum
- `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs` - 35 xUnit facts: consistency guard, construction, next-free-index, reserved-name/NN validation, and TAGC-03 round-trip suite

## Decisions Made
- Additive-only grammar extraction (DEVIATES from RESEARCH Pattern 1): interpolating constants into `CanvasAnnotationParser`'s regex fields would break the locked source-inspection test (`CanvasAnnotationParserSource_UsesCompiledAnchoredGrammarRegexes`), so the parser stays untouched and a bidirectional consistency test enforces single-source-of-truth instead
- ProcIndex is the full NN token uniformly across all Kinds (NN < 10 rejected with `ArgumentOutOfRangeException`) — matches RESEARCH Open Question 1's recommendation
- Pattern naming: idx slot is always the auto-assigned integer; a provided Name is the optional trailing label (`NN_Pat_idx` or `NN_Pat_idx Name`) — avoids the ambiguous `NN_Pat_Name` reading that would break round-trip parsing for names containing spaces
- NN construction is always `int.ToString(InvariantCulture)` string concatenation, never arithmetic — inverse of `CanvasAnnotationParser.SplitNn` (Pitfall 2, T-34-02)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Consistency test literal-match assertion adjusted for Emg/Emr tokens**
- **Found during:** Task 1 (running the new consistency test against the real parser source)
- **Issue:** The plan's `<behavior>` spec called for `Assert.Contains` on the full `"_Emg_"`/`"_Emr_"` infix constants, but `CanvasAnnotationParser`'s actual regex embeds these as a capture-group alternation (`_(?<tag>Emg|Emr)_`), so those contiguous underscored substrings never appear verbatim in the parser source — only the bare `Emg`/`Emr` tag literals do. The literal-match assertion as specified would always fail.
- **Fix:** For `EmergentInfix`/`EmergentToleratedInfix` only, the consistency test asserts the bare tag literals (`"Emg"`, `"Emr"`) are present in source, plus an `Assert.Equal` pinning the constants' full values — preserving the drift-guard intent (renaming the tag in either the parser alternation or the constants breaks the test) without asserting an impossible substring match. The other 7 tokens keep the full literal-match assertion unchanged.
- **Files modified:** `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs`
- **Verification:** `Grammar_ConstantsAppearVerbatimInParserSource` passes; all 15 pre-existing parser tests unaffected
- **Committed in:** `a993322` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — test-assertion correction, no production code affected)
**Impact on plan:** Adjustment scoped entirely to a test assertion; the drift-guard property the plan intended is preserved. No scope creep.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `CanvasAnnotationGrammar` and `CanvasAnnotationNameFactory` are ready for Plans 02/03 (the two GH components) to build tag names without risking a name the parser can't read back
- `NextFreePatternIndex` gives Plan 02/03 the auto-increment logic needed for `11_Pat_k` labeling
- No blockers; parser source remains byte-identical to pre-Phase-34 state

---
*Phase: 34-ontology-tagging-components*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: DG/src/DG.Core/Parsing/CanvasAnnotationGrammar.cs
- FOUND: DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs
- FOUND: DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs
- FOUND: commit a993322
- FOUND: commit 4002175
