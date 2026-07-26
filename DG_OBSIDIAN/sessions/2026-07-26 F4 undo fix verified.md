# 2026-07-26 — F4 undo fix verified live

**Finding:** IN-12 / F4 — re-preview double-undo crashed with "Undo failed: Object could not be found"

**What was fixed**
- `HandlePreviewStructure` WR-01 auto-clear was removing objects untracked while leaving the previous preview's undo record (R1) pointing at them
- On Ctrl+Z #2, undoing R1 found objects already gone → crash
- Fix: auto-clear now shares the new render's `GH_UndoRecord`, so one record spans "remove previous + render new"
- `HandleClearPreview` carried the identical latent crash; fixed same way; explicit clear is now undoable (behavior change)

**Commits**
- `f2f518c` — the code fix (CanvasListenerComponent.cs, 77 lines)
- `a82ab03` — UAT verification results

**Live verification (2026-07-26, UrbanBlock_V7)**
- Re-preview path: two previews in one listener session, Ctrl+Z ×2 → both previews restored then removed cleanly, no dialog
- `clear_preview` path: preview → clear → Ctrl+Z ×2 → restored then removed, no dialog
- Canvas pulls before/after every step; all confirmed objectively

**Status**
- 35-UAT test 6: FAIL → **pass** (tests 2–6 now closed; only test 1 blocked on a frontier-class LLM, not code)
- Group 4 outstanding audit items: **4 → 3**
- F4 fully closed

**Gotchas for future runs**
- F4 only reproduces when `preview_structure` runs **twice in the same listener session** — a Rhino restart empties the in-process `PreviewRegistry`, so the auto-clear has nothing to remove (false pass)
- A preview left on canvas at shutdown becomes a permanent orphan on reopen (unreachable by `clear_preview`, invisible to DG STRUCTURE CONFIRM, parses as untagged group) — same root cause as the registry residual, needs a custom `IGH_UndoAction` to fix

**Notes**
- Binary provenance checked: deployed `%APPDATA%\Grasshopper\Libraries\DG\DG.gha` is byte-identical to post-fix Release build
- No automated coverage is possible (`DG.Tests` does not reference `DG.Grasshopper`, GH types need Rhino runtime)
- `DG.sln` Release build clean, `dotnet test` 377/377 green
