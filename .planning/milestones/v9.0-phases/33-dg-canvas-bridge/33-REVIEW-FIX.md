---
phase: 33-dg-canvas-bridge
fixed_at: 2026-07-18T20:15:00Z
review_path: .planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-REVIEW.md
iteration: 3
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 33: Code Review Fix Report (iteration 3)

**Fixed at:** 2026-07-18T20:15:00Z
**Source review:** .planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-REVIEW.md (iteration-3 re-review)
**Iteration:** 3

**Summary:**
- Findings in scope: 2 (2 Warnings; fix_scope=critical_warning — the 9 Info findings are out of scope)
- Fixed: 2
- Skipped: 0

**Verification (after each fix and at session end):**
- `dotnet build DG/DG.sln -c Release` — 0 errors / 0 warnings (GRASSHOPPER_SDK defined, `net7.0-windows` target compiles the fixed component)
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasBridge"` — 16/16 passed

Fixes were applied in an isolated git worktree on a temp branch and fast-forwarded back onto `master` (`be88922..46efac9`); worktree, temp branch, and recovery sentinel cleaned up transactionally.

## Fixed Issues

### WR-01: Listener silently died on every document tab switch (`Unloaded`) with a stale "Listening" Status

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** 55aa9a1 — *fixed: requires human verification (Grasshopper document-lifecycle behavior; no automated test exercises the GH component runtime)*
**Applied fix:** Kept the stop on `Close`/`Unloaded` (releases port 8720 while a document is inactive) and added the restart half: on `GH_DocumentContext.Loaded`, `DocumentContextChanged` now calls `ScheduleRefresh()` (the component's existing `ScheduleSolution(1, _ => ExpireSolution(false))` deferral — chosen over the review's inline `ExpireSolution(true)` as the safer, already-established refresh pattern in this file). The scheduled solve makes `SolveInstance` restart the listener when Run=true (`_acceptLoopTask` is null after the Unloaded stop) and refreshes the Status output so it never shows a stale "Listening on 127.0.0.1:{port}" while the port is closed. XML doc comment updated to document the tab-switch semantics. No in-repo `DocumentContextChanged` precedent exists (ConnectorComponent does not override it), so the reviewer's suggested pattern was followed with the in-file refresh idiom.

### WR-02: Response write was unbounded and non-cancellable — a never-reading client re-wedged the single-client slot beyond toggle-off's reach

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** 46efac9 — *fixed: requires human verification (concurrency/backpressure behavior; no automated test exercises the GH component runtime)*
**Applied fix:** Replaced the token-less `writer.WriteLineAsync(response)` with the cancellable `WriteLineAsync(response.AsMemory(), writeCts.Token)` overload guarded by a linked CTS (`CreateLinkedTokenSource(ct)` + `CancelAfter(ClientReceiveTimeoutMs)` — same 30 s window as the read side), exactly as the review suggested. A send-window timeout (`OperationCanceledException` when `!ct.IsCancellationRequested`) breaks the serve loop and releases the single-client slot; a deliberate toggle-off cancels `ct`, which now flows into the pending write via the linked token, so the OCE propagates to the accept loop's shutdown filter and `finally { client.Dispose(); }` runs — closing the remaining half of threat T-33-03. With `AutoFlush = true` the flush rides the same cancellable call (verified real on `net7.0-windows`: `StreamWriter.WriteLineAsync(ReadOnlyMemory<char>, CancellationToken)` flows the token into the underlying `NetworkStream.WriteAsync`).

## Skipped Issues

None of the in-scope findings were skipped.

The 9 Info findings (IN-01..IN-09) are **out of scope** for this pass (fix_scope=critical_warning) and were intentionally not touched: dead exports (IN-01), unreachable `get_preview_status` (IN-02), redundant exception tuple (IN-03), envelope `result` leniency (IN-04), double request parse (IN-05), `GH_BRIDGE_PORT` import-time crash (IN-06), non-dict `error` field 500 (IN-07), dead-accept-loop refresh gap (IN-08), and untestable `BoundedLineReader` (IN-09).

---

_Fixed: 2026-07-18T20:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
