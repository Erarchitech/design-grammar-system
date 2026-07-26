---
tags: [debugging, phase-35, grasshopper, undo]
date: 2026-07-26
status: closed
---

# Phase 35 F4 — Re-preview undo crash (IN-12)

**Issue:** Running `preview_structure` twice in one listener session, then pressing Ctrl+Z twice, threw "Undo failed: Object could not be found" on the second press.

**Root cause:** The WR-01 auto-clear at the top of `HandlePreviewStructure` removed the first preview's objects via `doc.RemoveObject(obj, false)` (no undo bookkeeping) while leaving the first preview's undo record (R1) on Grasshopper's stack holding `GH_AddObjectAction` for each of those objects. When Ctrl+Z #2 tried to undo R1, it found objects the document no longer owned → crash.

**Fix:** Composed the clear + new render into one coherent undo record. `RemovePendingPreviewObjects` now:
1. Takes the owning `GH_UndoRecord` as a parameter
2. Adds a `GH_RemoveObjectAction` per object BEFORE removing it (action must capture object while document owns it)
3. Calls `doc.RemoveObject(obj, false)` after recording

This is the same record-then-remove ordering that `StructureConfirmComponent.ApplyToDocument`'s reject branch (WR-05) already used and had proven live in test 5.

**Latent issue discovered:** `HandleClearPreview` carried the identical crash. The preview's add-record stayed live after an explicit clear, so `preview → clear_preview → Ctrl+Z` threw the same error. Fixed the same way; explicit clear is now undoable (behavior change from non-undoable to undoable).

**Live verification:** 2026-07-26 on UrbanBlock_V7 with binary provenance check (deployed DG.gha byte-identical to post-fix Release build). Two previews (AlphaOne 90% + AlphaTwo 80%, then BetaOne 70%) → Ctrl+Z #1 restored Alphas + legend → Ctrl+Z #2 removed them cleanly, no dialog. Canvas pulls before/after confirmed objectively.

**Gotcha for re-testing:** F4 only reproduces when `preview_structure` runs **twice in the SAME listener session**. A Rhino restart empties the in-process `PreviewRegistry`, so the auto-clear has nothing to remove (false pass). The first test attempt this session hit exactly that.

**Residual (not fixed, pre-existing):** `PreviewRegistry` is not undo-aware. After Ctrl+Z #1 the canvas shows preview 1 while the registry still holds preview 2's entries, so `get_preview_status` and `clear_preview` are blind to restored groups until Ctrl+Z #2. Making it undo-aware needs a custom `IGH_UndoAction` — a design change, not a fix.

**References**
- Commit: `f2f518c` (the fix), `a82ab03` (verification)
- UAT: `.planning/phases/35-llm-recognition-canvas-preview/35-UAT.md` test 6
- Session: [[sessions/2026-07-26 F4 undo fix verified|2026-07-26]]
- Related: [[Phase 35 latent parser bug — pattern host resolved by document order|parser bug]], [[decisions/Phase 35 recognition quality remediation — hybrid Tier 0 Tier 1 architecture and pytest eval|AI-SPEC design]]