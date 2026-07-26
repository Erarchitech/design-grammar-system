---
phase: 35-llm-recognition-canvas-preview
plan: 16
subsystem: computgraph-parsing
tags: [csharp, canvas-annotation-parser, pattern-nesting, order-independence]

# Dependency graph
requires:
  - phase: 32-grammar-vocabulary-extraction
    provides: CanvasAnnotationParser.ComputeHostPatternIds and its NestedGroupIds/MemberIds nesting model
provides:
  - Order-independent pattern host resolution in ComputeHostPatternIds
  - Regression + order-independence test coverage for pattern nesting
affects: [35-11 (Corpus A emitter, confirmed unaffected), 36-computgraph-persistence-display (PATTERN_HOST_TO publish path)]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Primary-path host lookup filters candidates to pending patterns, breaks ties by innermost (smallest MemberIds), before falling back to strict-superset MemberIds"]

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs
    - DG/tests/DG.Tests/CanvasAnnotationParserTests.cs

key-decisions:
  - "Fixed the selection only (candidate filter + innermost tiebreak), not the nesting model itself"
  - "No fixture change — frame-cg-context.json lists only direct children (35-05's deliberate choice) and stays untouched, confirming the fix is a no-op on it"

requirements-completed: [RCGN-03]

coverage:
  - id: D1
    description: "ComputeHostPatternIds resolves a nested pattern's host by preferring a pattern-typed candidate over document order, with ties broken by innermost (smallest MemberIds)"
    requirement: "RCGN-03"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#ComputeHostPatternIds_ProcedureNamesTransitivelyNestedPattern_DoesNotHijackHost"
        status: pass
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#ComputeHostPatternIds_TransitiveDoubleNaming_InnermostPatternWins"
        status: pass
    human_judgment: false
  - id: D2
    description: "Host resolution is order-independent across permutations of RawCanvas.Groups"
    requirement: "RCGN-03"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#ComputeHostPatternIds_IsOrderIndependent_AcrossGroupPermutations"
        status: pass
    human_judgment: false
  - id: D3
    description: "Existing behaviour preserved: Frame fixture's 11_Pat_TopChord still hosted by 11_Pat_DivideLine, and the strict-superset MemberIds fallback still resolves when no group names the pattern"
    verification:
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#ComputeHostPatternIds_FrameFixture_TopChordStillHostedByDivideLine"
        status: pass
      - kind: unit
        ref: "DG.Tests/CanvasAnnotationParserTests.cs#ComputeHostPatternIds_NoNestedGroupIdsAnywhere_StrictSupersetFallbackStillResolves"
        status: pass
      - kind: unit
        ref: "DG.Tests/FrameFixtureTests.cs (8/8, unmodified)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-26
status: complete
---

# Phase 35 Plan 16: Order-independent pattern host resolution Summary

**Fixed `ComputeHostPatternIds`' primary-path lookup to select the innermost enclosing pattern instead of the document-order-first group, closing a silent nesting-drop bug flagged during 35-05.**

## Performance

- **Duration:** 25 min
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `ComputeHostPatternIds`'s primary-path lookup now searches only groups that are themselves pending patterns (excluding the pattern being resolved), and picks the innermost by ascending `MemberIds.Count` — replacing the old unfiltered `allGroups.FirstOrDefault` that could return a non-pattern group (e.g. a Procedure) and silently drop the nesting
- Added 5 new tests: a Procedure-transitively-names-a-nested-pattern repro (fails on old code), an order-independence proof across 4 permutations of `RawCanvas.Groups`, an innermost-wins proof for a 3-level `A ⊃ B ⊃ C` chain where both A and B name C, and two regression tests (Frame fixture direct-nesting case, and the strict-superset `MemberIds`-only fallback case)
- Confirmed the fix is a no-op on the checked-in Frame fixture (`frame-cg-context.json`) — it lists only direct children, so `11_Pat_TopChord.HostPatternId == 11_Pat_DivideLine.Id` holds identically before and after the fix; Corpus A does not need regenerating

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing tests that pin the defect and the invariant** - `1ce96d6` (test)
2. **Task 2: Prefer a pattern host, innermost first** - `c6eabee` (fix)
3. **Task 3: Re-verify the downstream nesting consumers** - no additional commit (verification-only task, see below)

**Plan metadata:** (this commit)

## Files Created/Modified
- `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` - `ComputeHostPatternIds` primary-path lookup rewritten to filter candidates to pending patterns and order by ascending `MemberIds.Count`; XML doc comment extended with the rationale and a pointer to this plan. Fallback block and `result[pending.Group] = hostId` assignment unchanged.
- `DG/tests/DG.Tests/CanvasAnnotationParserTests.cs` - 5 new tests under a `Phase 35-16` region: procedure-does-not-hijack, order-independence (4 permutations), innermost-wins (3-level chain), Frame-fixture regression, strict-superset-fallback-only regression.

## Decisions Made
- Kept the fallback's strict-superset `MemberIds` block untouched — it already covers the case where no group's `NestedGroupIds` names the pattern at all, and the plan's decisions explicitly scoped this to the primary-path selection only
- Removed the now-redundant `idByGroup` dictionary and its `TryGetValue` guard on the primary path, since the new lookup draws candidates directly from `pendingPatterns` and can take `.Id` straight off the winning candidate

## Deviations from Plan

None on the source/test content — plan executed exactly as written (candidate-filter + innermost-tiebreak fix, no fixture change, no touch to `GuardHostChains` or any other method).

**Process note (not a plan deviation, but material to how the commits were produced):** the working tree already carried uncommitted, unrelated changes from a concurrently-executing plan (35-12, Wave 3 — adding `Provider`/`Model`/`Confidence` propagation to `CanvasAnnotationParser.cs`, `CgPattern.cs`, and `StructureConfirmComponent.cs`) at the time this plan started, since `.planning/config.json` has `use_worktrees: false` and this repo runs wave-based execution on a single shared working tree. My first attempt to commit Task 2 used `git commit --only <path>`, which takes the **working-tree** content of the named path rather than what was staged — this pulled 35-12's unrelated hunks for `CanvasAnnotationParser.cs` into my Task 2 commit. Caught immediately via `git diff --name-only` inspection before proceeding to Task 3. Corrected with a `git reset --soft HEAD~1` (local, unpushed commit) followed by `git apply --cached --reverse` against a hand-built patch of just the unrelated hunks, then a plain `git commit` (no pathspec, so it took the index exactly as staged). Final state verified: both 35-16 commits (`1ce96d6`, `c6eabee`) touch only `CanvasAnnotationParser.cs` (my `ComputeHostPatternIds` hunk) and `CanvasAnnotationParserTests.cs`; the concurrent agent's `Provider`/`Model`/`Confidence` edits remain exactly as uncommitted working-tree changes across all three of its files, untouched, ready for that plan's own executor to commit.

## Issues Encountered
None beyond the commit-isolation correction described above, which was resolved before any downstream verification ran.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `PATTERN_HOST_TO` nesting is now order-independent for any future canvas the CanvasContextExtractor produces, including transitive-containment cases a real Grasshopper canvas can legitimately emit
- Corpus A (`frame_ablated.expected.json`, generated by 35-11) does not need regenerating — its `hostPatternId` values are unaffected by this fix
- Downstream `data-service/computgraph_publish.py`'s `PATTERN_HOST_TO` MERGE consumes only null-vs-non-null `hostPatternId`; this fix only ever moves a previously-null value to a correct non-null one, never the reverse

---
*Phase: 35-llm-recognition-canvas-preview*
*Completed: 2026-07-26*

## Self-Check: PASSED

- FOUND: DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs
- FOUND: DG/tests/DG.Tests/CanvasAnnotationParserTests.cs
- FOUND: commit 1ce96d6 (test)
- FOUND: commit c6eabee (fix)
