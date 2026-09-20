---
phase: 35-llm-recognition-canvas-preview
fixed_at: 2026-07-19T12:00:00Z
review_path: .planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 35: Code Review Fix Report

**Fixed at:** 2026-07-19
**Source review:** .planning/milestones/v9.0-phases/35-llm-recognition-canvas-preview/35-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (fix_scope: critical_warning — CR-01, WR-01..WR-06; IN-01..IN-08 out of scope)
- Fixed: 7
- Skipped: 0

All fixes were applied in an isolated git worktree on a temp branch and fast-forwarded into `master` on completion. A recovery sentinel from a prior interrupted fixer run was found and cleaned (its orphan worktree + branch removed); its one unmerged `fix(35): CR-01` commit was inspected, verified against current code, and cherry-picked rather than rewritten.

**Verification:** `dotnet build DG/DG.sln -c Release` — 0 errors, 0 warnings. `dotnet test DG/tests/DG.Tests/` — **370/370 green** (baseline 350 + 20 new regression tests added by these fixes). Host pytest: `tests/test_cg_recognition.py` **31/31**, `tests/test_gh_bridge.py` **13/13**. Full in-container 244-test run requires `docker compose build data-service && docker compose up -d data-service` against the now-updated master tree (image is built from the repo, so the rebuild only picks up these fixes post-merge) — run as the normal deploy step.

## Fixed Issues

### CR-01: Accept path rejects every convention-conformant proposal — suggestedName double-prefix contract mismatch

**Files modified:** `DG/src/DG.Core/Parsing/CanvasAnnotationNameFactory.cs`, `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs`, `DG/tests/DG.Tests/CanvasAnnotationNameFactoryTests.cs`
**Commit:** e81c184
**Applied fix:** New GH-free `CanvasAnnotationNameFactory.StripConventionPrefix(kind, suggestedName)` in DG.Core strips a leading `NN<Infix>` convention prefix (per-kind infix, incl. the tolerated `_Emr_` variant; Pat idx token dropped so `ForEntity` re-assigns a fresh index) before the accept path calls `ForEntity`. `11_IntF_ParSplitAt` now round-trips strip→ForEntity back to `11_IntF_ParSplitAt` without `ValidateName` throwing. 13 new DG.Core tests cover strip semantics, kind-mismatch non-stripping, and the exact accept-path composition (per the domain constraint: derived via the factory path, no Neo4j writes, `#if GRASSHOPPER_SDK` guard untouched).

### WR-01: Repeated preview_structure calls orphan previous preview groups and legend

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** 6f88d96
**Applied fix:** Extracted `RemovePendingPreviewObjects(doc)` (pending groups + stashed legend + registry clear, UI-thread only) shared by `HandleClearPreview` and now invoked at the top of `HandlePreviewStructure`'s `InvokeOnCanvasWrite` delegate — a new preview auto-clears the previous one, so re-used `p0/p1/...` ids can no longer orphan un-clearable groups.

### WR-02: kind never validated server-side; Enum.TryParse accepts numeric strings — mid-render throw leaves partial, un-undoable state

**Files modified:** `data-service/cg_recognition.py`, `DG/src/DG.Grasshopper/Canvas/PreviewRegistry.cs`, `data-service/tests/test_cg_recognition.py`
**Commit:** 840d111
**Applied fix:** (a) `validate_proposed_structure` emits `invalid_kind` (case-insensitive) for any kind outside `ALLOWED_PROPOSAL_KINDS`; (b) `ProposalDto.ToEntityTagKind()` replaced `Enum.TryParse` with an explicit switch — numeric strings (`"7"` → undefined enum value, which bypassed the render guard and let `ForKind` throw past the undo push) now hit the throw path and the existing guard-and-continue applies.
**Note (adapted beyond the review's letter, per its option "or the catalog's entity classes"):** the prompt/few-shot actually teach catalog kinds (`"Interface"`, `"Procedure"`, `"VariableParam"`, ...) — the review's proposed set `{"Proc",...,"IntF"}` would have rejected every taught output, and the old C# `Enum.TryParse` silently skipped `"Interface"` proposals during render (a latent dead-preview bug). The allowed set now covers BOTH vocabularies and the C# switch maps catalog kinds onto `EntityTagKind` (`Interface`→`IntF` etc.), making preview work for the wire format the LLM is actually taught.

### WR-03: No cross-proposal duplicate-member check

**Files modified:** `data-service/cg_recognition.py`, `data-service/tests/test_cg_recognition.py`
**Commit:** 293fcd3
**Applied fix:** Cross-proposal pass after the per-proposal loop emits `duplicate_member` for any id appearing in more than one proposal (What+Where+How-to-fix message, path `proposals[i].memberIds`), closing the double-ownership path one confirmation step before it becomes permanent.

### WR-04: SplitNn crashes on single-digit NN tokens — one malformed nickname aborts the entire canvas-context extraction

**Files modified:** `DG/src/DG.Core/Parsing/CanvasAnnotationParser.cs`, `DG/tests/DG.Tests/CanvasAnnotationParserTests.cs`
**Commit:** 0189a10
**Applied fix:** `SplitNn` replaced by non-throwing `TryParseNn` (rejects <2-digit tokens AND int-overflow digit runs — a sibling crash the review's guard missed). All four call sites (Proc/Pat/Var-Const-Emg/IntF) route the group to `Untagged.Groups` with a warning naming the offending nickname, restoring the "throws only for a null raw" contract. 7-case regression theory added.

### WR-05: Reject-path undo records GH_GenericObjectAction for a removed object

**Files modified:** `DG/src/DG.Grasshopper/Components/StructureConfirmComponent.cs`
**Commit:** f3b97ea
**Applied fix:** Reject path now records `GH_RemoveObjectAction(group)` (the removal counterpart to the listener's `GH_AddObjectAction`) before `RemoveObject`, so one Ctrl+Z restores rejected groups too.
**Status: fixed — requires human verification.** The review's own acceptance step ("verify in Rhino that a single Ctrl+Z after a mixed accept/reject Apply restores both") is a live-Rhino check; fold it into this phase's deferred manual UAT.

### WR-06: unrecognized block never validated — hallucinated member ids pass through

**Files modified:** `data-service/cg_recognition.py`, `data-service/tests/test_cg_recognition.py`
**Commit:** a1555d3
**Applied fix:** `validate_proposed_structure` now validates `parsed["unrecognized"]`: must be a list of `{memberIds, reason}` objects (`bad_shape`/`missing_field`), entry count bounded by `MAX_PROPOSALS` (new `too_many_unrecognized` code), per-entry member lists bounded by `MAX_MEMBERS_PER_PROPOSAL` (`too_many_members`), and every id checked against `known_ids` (`unknown_member_id` at `unrecognized[i].memberIds`) — the "never invented" docstring promise is now a validator guarantee.

## Skipped Issues

None.

---

_Fixed: 2026-07-19_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
