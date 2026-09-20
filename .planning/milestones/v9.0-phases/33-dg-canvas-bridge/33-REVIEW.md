---
phase: 33-dg-canvas-bridge
reviewed: 2026-07-18T18:51:43Z
depth: standard
iteration: 3
files_reviewed: 15
files_reviewed_list:
  - DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs
  - DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs
  - DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs
  - DG/src/DG.Core/Bridge/CanvasCommandRequest.cs
  - DG/src/DG.Core/Bridge/CanvasListenerRequestKey.cs
  - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
  - DG/src/DG.Grasshopper/Properties/CanvasListener24.png
  - DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs
  - data-service/app.py
  - data-service/gh_bridge.py
  - data-service/tests/test_gh_bridge.py
  - data-service/tests/test_app_computgraph_pull.py
  - data-service/tests/test_mcp_gh_tools.py
  - docker-compose.yml
findings:
  critical: 0
  warning: 2
  info: 9
  total: 11
status: issues_found
---

# Phase 33: Code Review Report (iteration 3 — re-review after fix pass)

**Reviewed:** 2026-07-18T18:51:43Z
**Depth:** standard
**Files Reviewed:** 15 (14 original scope + `Properties/CanvasListener24.png` introduced by the fix pass)
**Status:** issues_found

## Summary

Re-review after the 8-commit fix pass `8945196..be88922` addressing iteration 2's CR-01 and WR-01..WR-07 (previous review preserved at `33-REVIEW.iter2.md`). The fix range touched 6 files: `CanvasListenerComponent.cs`, `DgIcons.cs`, the new `Properties/CanvasListener24.png`, `app.py`, `gh_bridge.py`, and `test_gh_bridge.py`; all other scoped files are byte-identical to iteration 2 and their prior clean verdicts stand.

**Verification performed (not just claim-checking):** solution builds clean in Release with `GRASSHOPPER_SDK` defined (Rhino 8 present, so the fixed component actually compiles); all 16 C# bridge tests pass; all 21 Python tests pass including 3 new WR-04 tests. `DG.Grasshopper` targets `net7.0-windows` only, which matters: the CR-01 fix relies on cancellable `NetworkStream.ReadAsync(Memory<byte>, CancellationToken)`, which is real on that TFM (it would have been a silent no-op on net48 — verified not applicable).

**All 8 previous findings are genuinely resolved** (per-finding verification below). However, adversarial scrutiny of the fixes themselves surfaces two new warnings: (1) the WR-01 fix stops the listener on `GH_DocumentContext.Unloaded` — which Grasshopper raises on every document *tab switch*, not just close — with no restart on `Loaded` and no output refresh, so switching tabs silently kills the bridge while the Status output still reads "Listening"; (2) with the read path now bounded, the **write** path is the last unbounded blocking operation: `WriteLineAsync` carries no timeout or cancellation token, so a local client that sends a valid request and never reads the response re-wedges the single-client slot (the exact T-33-03 scenario CR-01 fixed on the read side) — and unlike the read side, toggle-off cannot release it. The six Info items from iteration 2 were out of the fix pass's stated scope and all remain present; three new Info items concern residual gaps in the WR-04/WR-06 fixes and test coverage of the new `BoundedLineReader`.

## Previous Findings — Resolution Verification

| Iter-2 finding | Status | Evidence |
|---|---|---|
| CR-01 stuck-client timeout no-op | **RESOLVED** | `ServeClientAsync` (lines 319-332) now uses a linked CTS with `CancelAfter(30000)` per `ReadLineAsync`; idle timeout caught via `when (!ct.IsCancellationRequested)` and releases the slot. Effective on `net7.0-windows` (cancellable async socket reads). The misleading `ReceiveTimeout` assignment is removed and the comment corrected (lines 281-284). |
| WR-01 document-close port leak | **RESOLVED** (with new side effect, see WR-01 below) | `DocumentContextChanged` override (lines 107-116) stops the listener on `Close`/`Unloaded`. |
| WR-02 unbounded ingress read | **RESOLVED** | New `BoundedLineReader` (lines 371-435) replaces `StreamReader`; throws `IOException` once the accumulated line exceeds `MaxRequestBytes` (max overshoot one 4096-byte chunk — bounded), aborting the connection via the accept loop's generic catch. Byte-level `\n` scan is UTF-8-safe; CRLF tolerated; leftover-buffer pipelining state verified correct by trace. |
| WR-03 cancellation reported as client error | **RESOLVED** | Accept loop catches `OperationCanceledException when (ct.IsCancellationRequested)` and breaks without touching `_status` (lines 287-293). |
| WR-04 malformed/truncated/non-object responses → 500 | **RESOLVED** (residual: IN-07) | `gh_bridge.py` lines 64-94: truncation detected via `not line.endswith("\n") and len(line) >= MAX_RESPONSE_BYTES`, `json.loads` wrapped in `except ValueError`, `isinstance(envelope, dict)` checked — all map to structured 502 `GH_BRIDGE_BAD_RESPONSE`. Three new tests cover all three shapes and pass. |
| WR-05 blocking socket I/O on event loop | **RESOLVED** | All four `gh_*` MCP branches now `await run_in_threadpool(...)` (`app.py` lines 1896-1929); `run_in_threadpool` propagates the worker-thread `HTTPException` correctly (verified by passing tests). |
| WR-06 dead accept loop undetectable | **RESOLVED** (residual: IN-08) | `SolveInstance` restarts when `_acceptLoopTask.IsCompleted` (lines 84-89); unexpected `SocketException` sets `_status = "Stopped: {msg}"` before break (lines 266-277). |
| WR-07 missing CanvasListener24.png | **RESOLVED** | `Properties/CanvasListener24.png` exists (valid 24×24 RGBA PNG, byte-identical copy of `DesignState24.png`, documented as a placeholder in `DgIcons.cs:40-42`); picked up by the `Properties\*.png` embedded-resource glob. |

## Warnings

### WR-01: Listener silently dies on every document tab switch (`Unloaded`) and never restarts on `Loaded` — Status output keeps claiming "Listening"

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:107-116`
**Issue:** The WR-01 fix stops the listener on `GH_DocumentContext.Close` **and** `GH_DocumentContext.Unloaded`. In Grasshopper, `Unloaded` is raised whenever a document stops being the *active* canvas — i.e., every time the user switches to another open `.gh` tab (or opens a second file), not only on close. The unloaded document is still alive in memory, but the bridge is now dead. When the user switches back, `Loaded` fires but nothing restarts the listener (`StopListener` nulled `_acceptLoopTask`, so the next `SolveInstance` *would* restart — but re-activating a document does not trigger a solve). Meanwhile `_status` is set to "Idle" without any `ExpireSolution`, so the Status **output param** still holds the stale "Listening on 127.0.0.1:{port}" value while port 8720 is closed — recreating the exact "component claims Listening while nothing is bound" symptom WR-06 was fixed to eliminate, now triggered by a routine user action. Every `gh_bridge.py` call during this state returns 503 with a hint telling the user to "enable DG CANVAS LISTENER" — which appears (stale-)enabled.
**Fix:** Either restrict the stop to `Close` (an inactive document's listener is still serving a live document object), or add the restart half of the pattern:
```csharp
if (context == GH_DocumentContext.Close || context == GH_DocumentContext.Unloaded)
{
    StopListener();
    _status = "Idle";
}
else if (context == GH_DocumentContext.Loaded)
{
    // Re-solve so SolveInstance restarts the listener when Run=true,
    // and the Status output stops showing a stale "Listening ..." value.
    ExpireSolution(true);
}
```

### WR-02: Response write path is unbounded and non-cancellable — a client that never reads re-wedges the single-client slot (T-33-03 on the write side), and toggle-off cannot release it

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:315,352`
**Issue:** With ingress now bounded (BoundedLineReader + 30 s idle token), the last unbounded blocking operation is the response write: `await writer.WriteLineAsync(response)` uses the `WriteLineAsync(string)` overload, which accepts no `CancellationToken` and has no timeout. A local client that sends one valid `get_canvas_context` request and then never reads lets TCP backpressure fill the loopback send buffer (~64 KB on Windows by default); once a large canvas-context response exceeds it, `WriteLineAsync` blocks forever. Consequences: (a) the single-client slot is wedged indefinitely — the same threat class as iteration 2's CR-01, just on the write side; (b) worse than the read-side case, **toggle-off does not recover it**: `StopListener` cancels `ct` (which the write does not observe) and stops the *listener* socket (which does not affect the accepted client socket), so `ServeClientAsync` never returns, the accept loop's `finally { client.Dispose(); }` never runs, and the hung task plus open socket leak until the remote peer disconnects. The shipped `gh_bridge.py` client always reads (with a 30 s timeout), so this needs a buggy or abusive local client — hence Warning rather than Critical — but T-33-03's stated goal ("a stuck client cannot wedge the slot") is only half-met.
**Fix:** Apply the same linked-token pattern to the write, using the cancellable overload (available on net7.0):
```csharp
using var writeCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
writeCts.CancelAfter(ClientReceiveTimeoutMs);
try
{
    await writer.WriteLineAsync(response.AsMemory(), writeCts.Token).ConfigureAwait(false);
}
catch (OperationCanceledException) when (!ct.IsCancellationRequested)
{
    break; // client stopped reading -- release the single-client slot
}
```
(With `AutoFlush = true` the flush rides the same call; alternatively write UTF-8 bytes directly to `stream.WriteAsync(..., writeCts.Token)`.)

## Info

### IN-01: `CanvasBridgeCommands.All` and `PreviewStubs` remain dead exports (carried over)

**File:** `DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs:17-35`
**Issue:** Still declared, still unreferenced by any production or test code (re-verified repo-wide grep — zero usages).
**Fix:** Remove, or add a test asserting the listener's handler map covers exactly `CanvasBridgeCommands.All`.

### IN-02: `gh_bridge.get_preview_status` remains unreachable from every consumer (carried over)

**File:** `data-service/gh_bridge.py:128-130`
**Issue:** No MCP tool, no REST route, no test references it (re-verified).
**Fix:** Expose it (liveness probe per 33-RESEARCH.md) or annotate with the consuming phase.

### IN-03: Redundant exception tuple in `_call` (carried over)

**File:** `data-service/gh_bridge.py:56`
**Issue:** `ConnectionRefusedError` and `socket.timeout` are `OSError` subclasses; `except OSError` alone is equivalent.
**Fix:** `except OSError as exc:` with a comment.

### IN-04: `envelope.get("result", envelope)` leaks the whole envelope when `result` is absent (carried over)

**File:** `data-service/gh_bridge.py:105`
**Issue:** An ok-envelope without `result` returns the full envelope; `"result": null` returns `None`. Latent (C# `BuildOk` always emits `result`), but masks protocol deviation — now inconsistent with the new strictness of the WR-04 checks directly above it.
**Fix:** Raise `GH_BRIDGE_BAD_RESPONSE` when `"result"` is missing from an ok envelope, matching lines 88-94.

### IN-05: Each request line is parsed twice in `ServeClientAsync` (carried over)

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:339-351`
**Issue:** BOM strip + `TryParse` (for `_lastCommand`) + `Dispatch(line)` re-parse — still present, unchanged by the fix pass.
**Fix:** `Dispatch` overload surfacing the parsed request type.

### IN-06: Malformed `GH_BRIDGE_PORT` env var crashes the whole data-service at import time (carried over)

**File:** `data-service/gh_bridge.py:28`
**Issue:** `int(os.getenv("GH_BRIDGE_PORT", "8720"))` at module scope; a compose typo takes down the entire service.
**Fix:** Wrap in `try/except ValueError` falling back to 8720.

### IN-07: Residual WR-04 gap — a non-dict `error` field in an error envelope still escapes as an unstructured 500

**File:** `data-service/gh_bridge.py:96-103`
**Issue:** The new checks validate the *envelope* is a dict, but not the `error` field inside it: for `{"status": "error", "error": "boom"}`, `err = envelope.get("error") or {}` yields the string `"boom"`, and `err.get("message", ...)` raises `AttributeError` → unhandled 500. Same latent-protocol-deviation class as the shapes WR-04 fixed (the C# listener always emits an object), but the strictness now stops one level short.
**Fix:** `err = envelope.get("error"); err = err if isinstance(err, dict) else {}` (and optionally a test mirroring `TestBadResponse`).

### IN-08: Residual WR-06 gap — a dead accept loop sets "Stopped: …" but never schedules a refresh, so status and auto-restart wait for the next user-triggered solve

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:266-277`
**Issue:** When `AcceptTcpClientAsync` dies unexpectedly, `_status = "Stopped: {msg}"` is written from the background thread but nothing calls `ScheduleRefresh()`, so the Status output continues showing "Listening …" and the `IsCompleted` restart path only executes when something else happens to expire the component. The dead state is now *recoverable* (fixing WR-06's core) but still not *visible or self-healing* until user interaction.
**Fix:** Call `ScheduleRefresh()` before the `break` in the `SocketException` catch — the scheduled solve both surfaces the status and triggers the `IsCompleted` restart.

### IN-09: `BoundedLineReader` — a security-relevant hand-rolled parser — has zero test coverage and is structurally untestable

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:371-435`
**Issue:** The WR-02 fix (byte budget, CRLF handling, leftover-buffer pipelining, EOF-mid-line semantics) lives as a `private sealed` nested class inside the `#if GRASSHOPPER_SDK`-guarded component, unreachable from `DG.Tests`. Manual trace confirms the `_start`/`_end` state machine is correct today, but any future edit to this buffering logic ships unverified — unlike every other bridge primitive, which lives in testable `DG.Core.Bridge`.
**Fix:** Promote `BoundedLineReader` to `DG.Core.Bridge` (it depends only on `Stream`) and add tests: over-budget throw, split-across-chunks line, two pipelined lines in one chunk, CRLF, EOF without terminator.

---

## Notes (verified clean — no finding)

- **Build/tests:** `dotnet build DG/DG.sln -c Release` succeeds with `GRASSHOPPER_SDK` defined (0 warnings/errors); 16/16 C# bridge tests pass; 21/21 Python tests pass (including the 3 new WR-04 tests, which correctly exercise truncation via a monkeypatched 16-char bound).
- **TFM check:** `DG.Grasshopper` targets `net7.0-windows` only — `NetworkStream.ReadAsync(Memory<byte>, CancellationToken)` cancellation (the mechanism behind the CR-01 fix) is genuinely effective on this TFM.
- **`readCts` lifecycle:** `using var` inside the loop body disposes each iteration's linked CTS correctly; `CancelAfter` bounds the *whole line*, not per chunk — stronger than a per-read timeout against slow-loris input.
- **Budget overshoot:** BoundedLineReader's check runs after each ≤4096-byte chunk append, so peak memory is `MaxRequestBytes + 4096` — bounded; a just-over-budget line that terminates before the check is still rejected downstream by `TryParse`'s `MaxRequestBytes` guard.
- **Idle-timeout vs. shutdown race:** an idle-timeout OCE that races a deliberate cancel is classified as shutdown — harmless either way.
- **Unchanged files:** `CanvasBridgeProtocol.cs`, `CanvasCommandDispatcher.cs`, `CanvasCommandRequest.cs`, `CanvasListenerRequestKey.cs`, `CanvasBridgeDispatcherTests.cs`, `test_app_computgraph_pull.py`, `test_mcp_gh_tools.py`, `docker-compose.yml` are identical to iteration 2; prior clean verdicts (loopback bind, allow-list dispatch, never-throw dispatcher, UI-thread marshalling, compose host-gateway wiring, sync-def REST route) re-confirmed by diff-range inspection.

_Reviewed: 2026-07-18T18:51:43Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
