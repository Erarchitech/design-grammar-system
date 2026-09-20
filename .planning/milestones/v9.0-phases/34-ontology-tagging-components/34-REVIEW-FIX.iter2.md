---
phase: 34-ontology-tagging-components
fixed_at: 2026-07-19T00:00:00Z
review_path: .planning/milestones/v9.0-phases/34-ontology-tagging-components/34-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 34: Code Review Fix Report

**Fixed at:** 2026-07-19T00:00:00Z
**Source review:** .planning/milestones/v9.0-phases/34-ontology-tagging-components/34-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (1 Critical + 8 Warnings; fix_scope=critical_warning, 7 Info findings out of scope)
- Fixed: 9
- Skipped: 0

All fixes were applied in an isolated git worktree on a temp branch and fast-forwarded onto `master` after verification. Every fix was verified with `dotnet build DG/DG.sln -c Release` (0 warnings, 0 errors after each commit). Full suite after all fixes: **343/344 passed** — the single failure is `DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve`, the documented Neo4j-down E2E environment baseline (env-dependent, not a regression; not a file touched by any fix). Hard constraint held: `CanvasAnnotationParser.cs` is byte-identical (`git diff master..HEAD` on the parser was empty before merge).

## Fixed Issues

### CR-01: Pattern kind can never re-tag — duplicate Pattern group + spurious self-nesting

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** bc20cf2
**Applied fix:** Before auto-incrementing, the Pat path now scans `raw.Groups` for an existing `NN_Pat_*` group whose member set equals the current selection and reuses its integer index (new `TryExtractPatternIndex` helper, `NumberStyles.None`/invariant, mirrors `NextFreePatternIndex`'s slice). `TagOrUpdateGroup` gained a `retagTargetNickname` parameter: the existing group is looked up under its OLD nickname and renamed, so a re-tag with a changed trailing label still routes into the update branch instead of creating a same-index duplicate. The re-tag target is also excluded from nesting-host detection so a re-tagged Pattern is never treated as its own host.
Status: fixed — requires human verification (GH canvas runtime behavior; press Tag twice on the same selection and confirm a single `11_Pat_1` group, no purple nested duplicate).

### WR-01: Undo records do not cover host-group mutation; re-tag never detaches from a stale host

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** b9c7354
**Applied fix:** `AttachToHost` now takes the active `GH_UndoRecord` and adds `GH_GenericObjectAction(hostGroup)` BEFORE mutating the host's `ObjectIDs` (both create and update branches). New `DetachFromStaleHosts` removes the re-tagged group's guid from every other Pattern group still listing it (scoped to `_Pat_`-nicknamed groups, excluding the newly detected host), recording each touched host in the same undo record — colour and structural nesting can no longer disagree, and undo restores hosts atomically.
Status: fixed — requires human verification (undo semantics only observable in Rhino/GH).

### WR-02: Duplicate value lists on file open (guard/mutation race in AddedToDocument)

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** 8bc1df8
**Applied fix:** The `Params.Input[0].Sources.Count > 0` check is re-run inside the `ScheduleSolution` delegate — where wire restoration is guaranteed complete — and returns early if the Kind input is already wired. The outer guard is kept as a cheap fast path.
Status: fixed — requires human verification (save/reopen a .gh file with a wired Kind input; no second value list should appear).

### WR-03: Deferred-mutation failures invisible (error wiped by forced re-solve)

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`, `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs`
**Commit:** 364f44f
**Applied fix:** Both components carry deferred failures in a new `_lastError` field. EntityTag: the catch sets `_lastError` and `_status = "Error: ..."`; the non-rising-edge path (where the post-expire re-solve lands) re-emits `_lastError` as a runtime Error; a new rising edge clears it; success clears it in the delegate. ObjectMarker: catch sets `_lastError` (plus the transient message); `SolveInstance` re-emits it before scheduling a new attempt; success clears it.
Status: fixed — requires human verification (failure path needs a live GH solver to observe).

### WR-04: OBJECT MARKER unbounded schedule→fail→expire→schedule loop

**Files modified:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs`
**Commit:** f5a2443
**Applied fix:** `ExpireSolution(false)` moved inside the try block, after all mutations succeed — the review's "only expire when the mutation succeeded" option. On failure the delegate's runtime Error now survives (no re-solve wipes it) and the next attempt waits for a real user-triggered solve instead of self-retrying without bound.
Status: fixed — requires human verification (loop behavior only observable in a live GH solver).

### WR-05: Partial-annotation path misreports canvas state

**Files modified:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs`
**Commit:** d1aca79
**Applied fix:** CREATE-mode outputs now report per-artifact truth: ObjectName output is `context.Object?.Name ?? objectName.Trim()` (the identity actually on the canvas), and Status is built from `needsObjectScribble`/`needsAlgorithmScribble` as `"Kept existing: OBJECT - FRAME; Created: 2_ALGORITHM"` etc. A runtime Warning fires when the input ObjectName conflicts with an existing canvas OBJECT identity (the optional part of the review fix).
Status: fixed — requires human verification (mixed-canvas reporting).

### WR-06: Class IRI binding silently dropped in REPORT mode

**Files modified:** `DG/src/DG.Grasshopper/Components/ObjectMarkerComponent.cs`
**Commit:** 36d209e
**Applied fix:** `classIri` is hoisted above the REPORT branch. In REPORT mode the stored `dg.objectClassIri` is read via `doc.ValueTable.GetValue(key, "")` (compiles against the real Rhino 8 Grasshopper SDK); when the input IRI is non-empty and differs, a small `ScheduleSolution` updates the ValueTable (mutation stays deferred), with its own catch feeding `_lastError`. The current binding is appended to the REPORT status string (`... / Class: <iri>`).
Status: fixed — requires human verification (ValueTable state only observable in a live document).

### WR-07: `ForObjectScribble` violates the round-trip guarantee for names with newlines

**Files modified:** `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs`, `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs`
**Commit:** 9765239
**Applied fix:** `ForObjectScribble` now throws `ArgumentException` (What/Where/How-to-fix format) on `\n` or `\r` in the name, before building the scribble text — the guarantee no longer depends on caller-side `ValidateName` discipline. Added `ForObjectScribble_NameWithNewline_ThrowsArgumentException` theory (`\n`, `\r`, `\r\n`). All 38 factory tests pass.
Status: fixed (unit-tested).

### WR-08: Update path mutates `GH_Group.ObjectIDs` directly via `Clear()`

**Files modified:** `DG/src/DG.Grasshopper/Components/EntityTagComponent.cs`
**Commit:** 879887e
**Applied fix:** The re-tag branch now rebuilds membership via the symmetric API — `RemoveObject(id)` over a snapshot of `ObjectIDs`, then `AddObject` for the new selection, then `ExpireCaches()` — exactly the review's sketch. Both `RemoveObject` and `ExpireCaches` compile against the deployed Rhino 8 Grasshopper.dll (verified by the Release build).
Status: fixed — requires human verification per the review itself: confirm during the human-verify checkpoint that a shrink-re-tag actually removes members.

## Skipped Issues

None — all 9 in-scope findings were fixed.

## Out of Scope (not attempted)

IN-01 through IN-07 (Info tier) — excluded by `fix_scope: critical_warning`.

## Verification Summary

- Per-fix: `dotnet build DG/DG.sln -c Release` — 0 errors / 0 warnings after every commit
- Factory tests after WR-07: 38/38 passed
- Full suite after all fixes: 343 passed / 1 failed / 344 total — sole failure is the documented Neo4j-down E2E baseline (`DesignStateValidationFlowTests`), unrelated to fixed files
- `CanvasAnnotationParser.cs`: byte-identical (empty diff) — hard constraint upheld
- `#if GRASSHOPPER_SDK` / `#else` stub structure preserved in both components

---

_Fixed: 2026-07-19T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
