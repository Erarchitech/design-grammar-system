# Phase 35 F4 — Re-preview orphans prior undo record, second Ctrl+Z crashes

## Issue
When `preview_structure` is called twice in a row, the second call invokes `RemovePendingPreviewObjects(doc)` ([CanvasListenerComponent.cs:295](../../DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs#L295)) to clear the first preview's objects before rendering new ones. This removal uses `doc.RemoveObject(obj, **false**)` (lines 386, 396) — the `false` means no undo bookkeeping. But Grasshopper's undo stack still has the first preview's `GH_UndoRecord` (R1, an add-action) on it. When the user then presses Ctrl+Z twice:

1. **Ctrl+Z #1:** undoes the second preview's record (R2) → removes second preview ✅
2. **Ctrl+Z #2:** undoes the first preview's record (R1) → R1 is an add-action, so undo tries to REMOVE the first preview's objects — but they were already deleted → Grasshopper throws **"Undo failed: Object could not be found"**

This is the exact scenario IN-12 / test 6 was written to catch.

## Root cause
The auto-clear (WR-01 fix for a registry-overwrite problem in Phase 35-02) removes objects without reconciling GH's undo stack. The `false` flag in `RemoveObject` is correct for *explicit* `clear_preview` (which is deliberately non-undoable), but wrong when a live undo record still references those objects.

## Evidence (2026-07-25)
- Synthetic proposals on UrbanBlock
- Run preview (5 groups + legend) → Ctrl+Z removes all (test 2/4.2a pass)
- Run preview again (second call auto-clears first preview) → Ctrl+Z ×1 succeeds, Ctrl+Z ×2 throws Grasshopper breakpoint: `Undo failed: Object could not be found`
- Confirmed via code: `RemovePendingPreviewObjects` (lines 382–402) calls `doc.RemoveObject` with `false`; no undo record composition

## Does NOT block
The single-preview → DG STRUCTURE CONFIRM → DG COMPUTGRAPH PUBLISH path (4.4–4.5). Only blocks the edge case of re-previewing then undoing past the current record.

## Fix suggestion
When auto-clearing on re-preview, either:
1. Invalidate/discard the previous preview's undo record from GH's stack (if possible without a public API), or
2. Compose the clear + new render into one coherent undo record so both ops undo together

## Severity
Medium. Edge case (requires deliberately re-previewing mid-session), but a hard crash/breakpoint when triggered.

## Related
[[Phase 35 F1 — Recognition output-token truncation]], [[Phase 35 F2 — Silent full-scope fallback]]
