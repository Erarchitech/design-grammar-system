---
phase: 34-ontology-tagging-components
fixed_at: 2026-07-19T00:00:00Z
review_path: .planning/milestones/v9.0-phases/34-ontology-tagging-components/34-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 34: Code Review Fix Report

**Fixed at:** 2026-07-19T00:00:00Z
**Source review:** .planning/milestones/v9.0-phases/34-ontology-tagging-components/34-REVIEW.md (iteration 2 — fix verification)
**Iteration:** 2

**Summary:**
- Findings in scope: 1 (WR-09; fix_scope=critical_warning — IN-01..IN-09 Info findings out of scope by directive)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### WR-09: Pat re-tag equality predicate false-negatives once the Pattern hosts a nested child group

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** e261eb3
**Applied fix:** The re-tag equality predicate in `SolveInstance` now compares the current selection against a Pattern group's **non-group** members, symmetrically on both sides. Concretely:
- Collected all live `GH_Group` `InstanceGuid`s from `doc.Objects` into a `HashSet<string>` (`groupGuids`).
- Filtered `selectedIds` down to `selectedCore` (selection minus any group objects caught in the drag-selection).
- The `existingPat` lookup now filters each candidate group's `MemberIds` down to its non-group `core` before the count + membership equality check.

This removes the false negative introduced by `AttachToHost` adding a nested child group's `InstanceGuid` to the host Pattern's `ObjectIDs`: an identical-selection re-tag of `11_Pat_1` after it gained a nested `11_Var_X` child now matches, reuses the pattern index via `TryExtractPatternIndex`, and takes the update branch in `TagOrUpdateGroup` — instead of auto-incrementing to `11_Pat_2` and re-creating the CR-01 duplicate+nest corruption. As a bonus (per the review), a drag-selection that happens to include the nested child group object itself is also tolerated.

The review's two related lower-severity design ambiguities (membership-*changing* re-tag creating an overlapping duplicate, and empty-Name re-tag stripping an existing trailing label) were explicitly flagged by the reviewer as design ambiguity below warning severity and are not part of the WR-09 fix; the "Pattern with nested child re-tagged by identical selection" case is flagged for the human-verify checkpoint as the review requests.

**Verification:**
- `dotnet build DG/DG.sln -c Release` — exit 0, 0 warnings / 0 errors (fix code compiles under `GRASSHOPPER_SDK`).
- `dotnet test DG/tests/DG.Tests/` — **344/344 passed, 0 failed** (even the documented Neo4j-dependent E2E baseline passed this run; no regressions).
- `git diff` over `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs` — empty; parser remains byte-identical (hard constraint upheld).
- `#if GRASSHOPPER_SDK` / `#else` stub structure preserved (fix is entirely inside the SDK-gated block).
- Note: this is a logic-path fix verified structurally (build + full test suite); the nested-child identical-selection re-tag scenario itself requires a live Grasshopper canvas — covered by the phase's human-verify checkpoint. **Fixed: requires human verification** at that checkpoint.

## Skipped Issues

None — the single in-scope finding was fixed.

Info findings IN-01 through IN-09 were intentionally not fixed (out of critical/warning scope per fix_scope=critical_warning and the orchestrator's explicit directive).

---

_Fixed: 2026-07-19T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
