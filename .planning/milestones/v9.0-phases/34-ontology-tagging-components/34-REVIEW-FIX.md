---
phase: 34-ontology-tagging-components
fixed_at: 2026-07-18T22:32:32Z
review_path: .planning/milestones/v9.0-phases/34-ontology-tagging-components/34-REVIEW.md
iteration: 3
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 34: Code Review Fix Report

**Fixed at:** 2026-07-18T22:32:32Z
**Source review:** .planning/milestones/v9.0-phases/34-ontology-tagging-components/34-REVIEW.md (iteration 3 — WR-09 fix verification, FINAL)
**Iteration:** 3

**Summary:**
- Findings in scope: 2 (WR-10, WR-11; fix_scope=critical_warning — IN-01..IN-09 Info findings out of scope by directive)
- Fixed: 2
- Skipped: 0

This is the final fix iteration (3/3) — no automatic re-review follows. Both fixes apply the report's prescribed snippets verbatim, with no opportunistic refactoring.

## Fixed Issues

### WR-10: Pat re-tag match/rebuild asymmetry — a matched re-tag silently detaches the Pattern's nested child groups

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** 4d794f5
**Applied fix:** The update branch of `TagOrUpdateGroup` now preserves during the membership rebuild exactly the child-group guids the WR-09 equality predicate deliberately ignored, and never adds the group to itself:
- Before clearing `ObjectIDs`, live `GH_Group` `InstanceGuid`s are collected from `currentDoc.Objects` (`liveGroupGuids`) and the existing group's current child-group member guids are captured into `preservedChildIds` (excluding the group's own `InstanceGuid`).
- The re-add loop over `selected` now skips `existingGroup.InstanceGuid`, so a drag-selection covering the parent Pattern can no longer produce a self-referencing group (`AddObject(existingGroup.InstanceGuid)`).
- After re-adding the selection, each preserved child-group guid not already present is re-added — so a core-only label re-tag of a child-hosting Pattern keeps the parent→child nesting edge intact (GH visual containment and `CanvasContextExtractor.NestedGroupIds` both preserved), eliminating the colour/structure disagreement the review flagged.
- The `#if GRASSHOPPER_SDK` / `#else` stub structure is unchanged; the edit is entirely inside the SDK-gated block.

**Note per report:** the human-verify checkpoint should cover "re-tag a child-hosting Pattern by core-only selection, then verify the child is still nested" — this is a canvas-interaction behavior that cannot be exercised by the unit suite.

### WR-11: Empty-core vacuous match — a group-only selection hijacks the first same-NN pattern-of-patterns instead of creating a new one

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** 8074e23
**Applied fix:** The re-tag equality predicate in `SolveInstance` gains the report's prescribed guard: when BOTH the candidate group's filtered `core` and the selection's `selectedCore` are empty (group-only Pattern vs group-only selection), the predicate falls back to exact full-set comparison of `g.MemberIds` against `selectedIds` instead of the vacuous `0 == 0 && [].All(...)`. A group-only selection of DIFFERENT child groups now fails the match and routes to `NextFreePatternIndex` (a new `NN_Pat_2` is created), while an identical group-only re-selection still matches its exact Pattern — restoring the pre-WR-09 correct behavior for pattern-of-patterns without regressing the WR-09 mixed-membership fix.

## Skipped Issues

None — both in-scope findings fixed.

## Verification

- `dotnet build DG/DG.sln -c Release` after each fix: exit 0, **0 warnings / 0 errors** (verified independently after WR-10 and after WR-11).
- `dotnet test DG/tests/DG.Tests/` after WR-11: **343 passed, 1 failed** — the single failure is `DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve`, within the documented Neo4j-availability baseline (0-4 env-dependent failures), not a regression. All 38 `CanvasAnnotationNameFactoryTests` pass.
- Hard constraint `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` byte-identical: `git diff 82875c4..HEAD -- <file>` empty and working tree clean for the file.
- `#if GRASSHOPPER_SDK` + `#else` stub structure preserved (both edits are inside the SDK-gated region of `EntityTagComponent.cs`).
- Tier 1 re-read confirmed both snippets present and surrounding code intact.

---

_Fixed: 2026-07-18T22:32:32Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
