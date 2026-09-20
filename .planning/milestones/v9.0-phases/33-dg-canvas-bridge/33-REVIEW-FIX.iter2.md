---
phase: 33-dg-canvas-bridge
fixed_at: 2026-07-18T19:00:00Z
review_path: .planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 33: Code Review Fix Report

**Fixed at:** 2026-07-18
**Source review:** .planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (1 Critical + 7 Warnings; fix_scope=critical_warning, 6 Info findings out of scope)
- Fixed: 8
- Skipped: 0

**Verification (whole session):**
- `dotnet build DG/DG.sln -c Release` — 0 errors / 0 warnings
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanvasBridge"` — 16/16 passed
- `python -m pytest data-service/tests/ -q` (host) — 204 passed, 4 failed; the 4 failures are the documented pre-existing `test_dg_context.py` Neo4j-DNS env failures (not phase 33 regressions). Suite grew 205 → 208 (3 new WR-04 tests, all green).

## Fixed Issues

### CR-01: 30 s stuck-client timeout was a no-op (`ReceiveTimeout` ignores async reads)

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** 8945196 — *fixed: requires human verification (concurrency behavior; no automated test exercises the GH component runtime)*
**Applied fix:** Removed the ineffective `client.ReceiveTimeout` assignment; the idle timeout is now enforced per read in `ServeClientAsync` via `CancellationTokenSource.CreateLinkedTokenSource(ct)` + `CancelAfter(ClientReceiveTimeoutMs)`. An idle-client `OperationCanceledException` (when `!ct.IsCancellationRequested`) breaks the serve loop and releases the single-client slot; a cooperative-shutdown OCE propagates (handled by WR-03). Comments corrected to no longer claim `ReceiveTimeout` enforces T-33-03.

### WR-01: Listener leaked port 8720 when the document was closed with Run=true

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** 4c5f943
**Applied fix:** Added a `DocumentContextChanged` override that calls `StopListener()` and sets `_status = "Idle"` on `GH_DocumentContext.Close` and `GH_DocumentContext.Unloaded` (per the review's suggested fix, verbatim semantics).

### WR-02: `MaxRequestBytes` did not bound the read — `ReadLineAsync` buffered unboundedly

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** d9b35b9 — *fixed: requires human verification (custom framing reader; only compile-verified, no listener-level integration test exists)*
**Applied fix:** Replaced `StreamReader.ReadLineAsync` with a new private `BoundedLineReader` nested class that reads raw bytes from the `NetworkStream` in 4 KiB chunks, scans for `\n`, preserves leftover bytes across lines, tolerates CRLF, and throws `IOException` (aborting the connection via the existing per-client catch) as soon as the accumulated line exceeds `CanvasBridgeProtocol.MaxRequestBytes` before a newline is seen. UTF-8 decoding happens once per complete line, so multi-byte characters split across chunks decode correctly.

### WR-03: Toggle-off while a client was connected reported "Client error: The operation was canceled."

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** e5fdcaa — *fixed: requires human verification (status-race behavior; no automated test exercises the GH component runtime)*
**Applied fix:** Added `catch (OperationCanceledException) when (ct.IsCancellationRequested)` before the generic per-client `catch (Exception)` in `RunAcceptLoopAsync` — deliberate shutdown breaks the loop without touching `_status`, so it can no longer overwrite a fresh "Idle"/"Listening" status. Composes with CR-01: idle-timeout OCEs are consumed inside `ServeClientAsync` and never reach this handler.

### WR-04: Malformed/truncated/non-object bridge responses crashed `gh_bridge._call` with an unstructured 500

**Files modified:** `data-service/gh_bridge.py`, `data-service/tests/test_gh_bridge.py`
**Commit:** 1bd0e36
**Applied fix:** Moved `json.loads` out of the socket `try`. Added three structured 502 `GH_BRIDGE_BAD_RESPONSE` paths: (1) truncation detection (`not line.endswith("\n") and len(line) >= MAX_RESPONSE_BYTES`, with a comment noting the text-mode bound is a character count); (2) `ValueError` from `json.loads` (malformed JSON); (3) `not isinstance(envelope, dict)` (non-object JSON). Added a `TestBadResponse` class with 3 tests covering all three shapes — all green.

### WR-05: Blocking bridge socket I/O (~35 s worst case) ran on the event loop in `async def mcp`

**Files modified:** `data-service/app.py`
**Commit:** be88922
**Applied fix:** Imported `fastapi.concurrency.run_in_threadpool` and wrapped all four `gh_*` MCP branches (`get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`) in `await run_in_threadpool(...)`. HTTPException propagation is unchanged (pinned by the existing `test_gh_bridge_error_propagates_as_httpexception_not_jsonrpc_error`); all 8 MCP/pull tests pass.

### WR-06: A dead accept loop was undetectable — component reported "Listening" forever

**Files modified:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs`
**Commit:** ec06207 — *fixed: requires human verification (restart-condition logic; no automated test exercises the GH component runtime)*
**Applied fix:** `SolveInstance`'s run==true branch now also restarts when `_acceptLoopTask.IsCompleted`; the `SocketException` catch in `RunAcceptLoopAsync` sets `_status = "Stopped: {ex.Message}"` when the death was not a deliberate `Stop()` (`!ct.IsCancellationRequested`), so the next solve both shows the truth and self-repairs.

### WR-07: `CanvasListener24.png` embedded resource missing — component shipped with the pink-X placeholder

**Files modified:** `DG/src/DG.Grasshopper/Properties/CanvasListener24.png` (new), `DG/src/DG.Grasshopper/DgIcons.cs`
**Commit:** a965726
**Applied fix:** Followed the documented Phase 19 placeholder-icon convention (no invented binary artwork): copied the existing spare embedded resource `DesignState24.png` (present in `Properties/` but unreferenced by `DgIcons`) to `CanvasListener24.png`, which the existing `<EmbeddedResource Include="Properties\*.png" />` glob picks up. Added a comment at the `CanvasListener24` property documenting the placeholder and that it should be replaced with bespoke artwork.

## Skipped Issues

None — all 8 in-scope findings were fixed. (IN-01 through IN-06 were out of scope for fix_scope=critical_warning.)

## Notes for the human verifier

- CR-01 / WR-02 / WR-03 / WR-06 change runtime behavior of the Grasshopper component, which has no automated harness (guarded by `#if GRASSHOPPER_SDK`, exercised only inside Rhino). Suggested manual check in Rhino: start the listener, connect with `nc 127.0.0.1 8720` and send nothing (slot should free after ~30 s, CR-01); toggle Run off mid-connection (Status should stay Idle, WR-03); close the .gh file with Run=true and reopen (no "address already in use", WR-01).
- WR-07 intentionally reuses `DesignState24.png` pixels as a placeholder; replace with bespoke artwork when available.
- Fix commits were made on a temporary worktree branch and fast-forwarded into `master` (see workflow log).

---

_Fixed: 2026-07-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
