---
phase: 33-dg-canvas-bridge
reviewed: 2026-07-18T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs
  - DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs
  - DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs
  - DG/src/DG.Core/Bridge/CanvasCommandRequest.cs
  - DG/src/DG.Core/Bridge/CanvasListenerRequestKey.cs
  - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
  - DG/src/DG.Grasshopper/DgIcons.cs
  - DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs
  - data-service/app.py
  - data-service/gh_bridge.py
  - data-service/tests/test_app_computgraph_pull.py
  - data-service/tests/test_gh_bridge.py
  - data-service/tests/test_mcp_gh_tools.py
  - docker-compose.yml
findings:
  critical: 1
  warning: 7
  info: 6
  total: 14
status: issues_found
---

# Phase 33: Code Review Report

**Reviewed:** 2026-07-18
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 33 implements the DG Canvas Bridge: a C# protocol layer (`DG.Core.Bridge`) plus a loopback-only TCP listener component (`CanvasListenerComponent`), and a Python raw-socket client (`gh_bridge.py`) wired into a REST endpoint (`/computgraph/context/pull`) and 4 `gh_*` MCP tools in `data-service/app.py`, with docker-compose env plumbing (`GH_BRIDGE_HOST`/`GH_BRIDGE_PORT` + `extra_hosts: host-gateway`).

The core security posture is largely correct: the bind is `IPAddress.Loopback` (never `Any`), dispatch uses an explicit allow-list dictionary (write commands unreachable), the dispatcher never throws, the Python client is connect/read-bounded, and toggle-off stops and disposes the listener. Tests cover the protocol, dispatcher, client error mapping, and both new HTTP surfaces well.

However, two of the phase's own stated threat mitigations do not actually work as claimed: the 30 s stuck-client timeout (T-33-03) is a no-op because `Socket.ReceiveTimeout` does not apply to async reads (Critical), and the `MaxRequestBytes` "bounded read" guard on the listener side only bounds *parsing* — the read itself (`ReadLineAsync`) buffers unboundedly. Additionally, the listener leaks when the Grasshopper document is closed (no `DocumentContextChanged` cleanup), and the Python client turns malformed bridge responses into unstructured 500s, contradicting the T-33-06 "structured errors, never a hang" contract.

## Critical Issues

### CR-01: 30 s stuck-client timeout is a no-op — `ReceiveTimeout` does not apply to async reads; an idle client wedges the bridge indefinitely

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:252` (with `ServeClientAsync` at 267-299)
**Issue:** The accept loop sets `client.ReceiveTimeout = ClientReceiveTimeoutMs` with the comment "Bounds a stuck client so the single-client slot is released (T-33-03, Pitfall 5)". But `Socket.ReceiveTimeout` applies **only to synchronous** `Receive` calls; `ServeClientAsync` reads via `StreamReader.ReadLineAsync(ct)`, an async I/O path that completely ignores `ReceiveTimeout`. A client that connects and never sends a newline-terminated line (a `telnet`/`nc` probe, a port scanner, a monitoring TCP health check, or a data-service that dies mid-request) blocks `ReadLineAsync` forever. Because the accept loop serves exactly one client at a time, that single idle connection permanently wedges the entire bridge — every subsequent `gh_bridge.py` call times out with 503 — until the user toggles Run off. The threat mitigation the code (and plan T-33-03) claims to ship does not exist at runtime.
**Fix:** Apply a per-read timeout via a linked cancellation token instead of `ReceiveTimeout`:
```csharp
// in ServeClientAsync's read loop, replacing the plain ReadLineAsync(ct):
using var readCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
readCts.CancelAfter(ClientReceiveTimeoutMs);
string? line;
try
{
    line = await reader.ReadLineAsync(readCts.Token).ConfigureAwait(false);
}
catch (OperationCanceledException) when (!ct.IsCancellationRequested)
{
    break; // idle client timed out -- release the single-client slot
}
```
Remove (or keep as harmless documentation) the `ReceiveTimeout` assignment, and correct the comment so it no longer claims the assignment enforces T-33-03.

## Warnings

### WR-01: Listener leaks (port stays bound, socket not disposed) when the Grasshopper document is closed with Run=true

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:90-94`
**Issue:** Cleanup only happens in `RemovedFromDocument`, which Grasshopper raises when the component is deleted from a document — it is **not** raised when the user closes the `.gh` file (or Rhino unloads the document). Closing a document with the listener running leaves the `TcpListener` bound to port 8720 and the accept loop alive for the remainder of the Rhino session, still answering bridge requests against a dead document (`OnPingDocument()` may return the stale document or null). Re-opening the file then fails to start ("Failed to start listener: ... address already in use"). This directly violates the phase's stated "socket disposal on toggle-off (no port leak)" goal for the document-close path.
**Fix:** Override `DocumentContextChanged` and stop the listener on close/unload:
```csharp
public override void DocumentContextChanged(GH_Document document, GH_DocumentContext context)
{
    if (context == GH_DocumentContext.Close || context == GH_DocumentContext.Unloaded)
    {
        StopListener();
        _status = "Idle";
    }
    base.DocumentContextChanged(document, context);
}
```

### WR-02: `MaxRequestBytes` does not bound the read — `ReadLineAsync` buffers an unbounded line into Rhino's memory before the guard runs

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:276`; `DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs:22,44`
**Issue:** `CanvasBridgeProtocol.MaxRequestBytes` (5 MiB) is checked inside `TryParse` — i.e., *after* the full request line already exists as a string. `StreamReader.ReadLineAsync` will happily accumulate a line of any length: a local client that streams gigabytes without a newline grows the buffer without bound inside the Rhino process before the "guard" ever executes. The Python client bounds its `readline(MAX_RESPONSE_BYTES)`; the C# listener has no equivalent bound on ingress. Loopback-only reduces exposure, but the ASVS-L1 "bounded reads" control is only half-implemented — and the half that is implemented (post-hoc size check) cannot protect memory.
**Fix:** Read the line with an explicit byte budget instead of `StreamReader.ReadLineAsync` — e.g., a small helper that reads from the `NetworkStream` into a capped buffer and aborts the connection (or returns a `BAD_REQUEST` envelope and drains) once `MaxRequestBytes` is exceeded before a `\n` is seen.

### WR-03: Toggling the listener off while a client is connected reports "Client error: The operation was canceled." instead of Idle

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:249-259`
**Issue:** On toggle-off, `StopListener` cancels the token; a pending `ReadLineAsync(ct)` throws `OperationCanceledException`, which escapes `ServeClientAsync` and is swallowed by the generic `catch (Exception ex)` around it, setting `_status = "Client error: The operation was canceled."`. This races with (and can land after) the `_status = "Idle"` write in `SolveInstance`, so the component reports a client *error* when the shutdown was deliberate and clean. The same race can overwrite a fresh "Listening on 127.0.0.1:{port}" status after a port-change restart with a stale error from the old loop.
**Fix:** Don't treat cooperative cancellation as a client error:
```csharp
catch (OperationCanceledException) when (ct.IsCancellationRequested)
{
    break; // deliberate shutdown -- leave _status alone
}
catch (Exception ex)
{
    _status = $"Client error: {ex.Message}";
}
```

### WR-04: Malformed, truncated, or non-object bridge responses crash `gh_bridge._call` with an unstructured 500 (violates T-33-06's structured-error contract)

**File:** `data-service/gh_bridge.py:53-74`
**Issue:** The `except` clause only catches `(ConnectionRefusedError, socket.timeout, OSError)`. Three realistic response shapes escape it and surface as generic FastAPI 500s instead of the structured error the module's own docstring promises:
1. **Malformed JSON** from the listener → `json.loads(line)` raises `json.JSONDecodeError` (a `ValueError`, not an `OSError`) — unhandled.
2. **Oversized response**: `readline(MAX_RESPONSE_BYTES)` returns a *truncated* string with no trailing newline when the line exceeds the bound, which then fails `json.loads` — so the very guard meant to produce a bounded structured failure funnels into an unhandled 500. (Also note: the file object is text-mode, so the argument is a *character* count, not bytes as the constant name claims.)
3. **Non-object JSON** (e.g., `"x"` or `[1]`) → `envelope.get(...)` raises `AttributeError` — unhandled.
No test covers any of these paths (test_gh_bridge.py stops at refused/timeout/empty/error-envelope).
**Fix:** Validate the decode inside the function and map to a structured error:
```python
try:
    envelope = json.loads(line)
except ValueError as exc:
    raise _structured_error_response(
        f"Grasshopper bridge returned a malformed response: {exc}",
        "Check the DG CANVAS LISTENER version (wire protocol v1).",
        "GH_BRIDGE_BAD_RESPONSE", 502) from exc
if not isinstance(envelope, dict):
    raise _structured_error_response(
        "Grasshopper bridge returned a non-object response.",
        "Check the DG CANVAS LISTENER version (wire protocol v1).",
        "GH_BRIDGE_BAD_RESPONSE", 502)
```
Also detect the truncation case (`not line.endswith("\n") and len(line) >= MAX_RESPONSE_BYTES`) and raise the same structured 502. Add tests for all three shapes.

### WR-05: Blocking bridge socket I/O (up to ~35 s) runs directly on the event loop inside `async def mcp`

**File:** `data-service/app.py:1892-1923`
**Issue:** `/mcp` is an `async def` handler, so it executes on the FastAPI event loop — not in the threadpool. The four new `gh_*` branches call `gh_bridge.get_canvas_context/get_selection/preview_structure/clear_preview`, which perform **blocking** `socket.create_connection` (5 s) + blocking read (30 s). A slow or hung listener therefore freezes the *entire* data-service — every concurrent request to any endpoint stalls for up to ~35 s per MCP call. (The pre-existing blocking Neo4j calls in this handler share the flaw, but their latency is milliseconds; the new worst case is three orders of magnitude larger.) The REST route `pull_computgraph_context` is a sync `def` and correctly runs in the threadpool — only the MCP path is affected.
**Fix:** Offload the blocking calls:
```python
from fastapi.concurrency import run_in_threadpool
...
context = await run_in_threadpool(gh_bridge.get_canvas_context, project)
```
(apply to all four `gh_*` branches).

### WR-06: A dead accept loop is undetectable — component keeps reporting "Listening" and never restarts

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:244-247,80-83`
**Issue:** If `AcceptTcpClientAsync` throws a `SocketException` for any reason other than a deliberate `Stop()` (e.g., OS-level socket teardown, resource exhaustion), `RunAcceptLoopAsync` silently `break`s: `_status` remains "Listening on 127.0.0.1:{port}", `_acceptLoopTask` remains non-null (completed), and `_activeRequestKey` still matches. `SolveInstance` only restarts when `_acceptLoopTask is null` or the key changed, so subsequent solves with Run=true do nothing — the component permanently displays a listening state while nothing is listening, and only a Run toggle recovers it.
**Fix:** Detect the completed loop and reflect/repair the state:
```csharp
// SolveInstance, run == true branch:
if (_acceptLoopTask is null || _acceptLoopTask.IsCompleted
    || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
{
    StartListener(port, requestKey);
}
```
and set `_status = "Stopped: {ex.Message}"` before the `break` in the `SocketException` catch when `!ct.IsCancellationRequested`.

### WR-07: `CanvasListener24.png` embedded resource does not exist — the new component ships with the pink-X error placeholder icon

**File:** `DG/src/DG.Grasshopper/DgIcons.cs:40`; `DG/src/DG.Grasshopper/Properties/` (file absent)
**Issue:** `DgIcons.CanvasListener24` loads `Properties.CanvasListener24.png`, but no such file exists under `DG/src/DG.Grasshopper/Properties/` (verified against the glob of all 16 PNGs; the csproj embeds `Properties\*.png`). `Load()`'s fallback means DG CANVAS LISTENER renders in the ribbon and on canvas with the light-pink red-X "missing icon" bitmap — a visible shipped defect. (`Label24.png` is missing too, but that predates this phase.)
**Fix:** Add `DG/src/DG.Grasshopper/Properties/CanvasListener24.png` (24×24) so the existing `<EmbeddedResource Include="Properties\*.png" />` picks it up.

## Info

### IN-01: `CanvasBridgeCommands.All` and `PreviewStubs` are dead exports

**File:** `DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs:17-35`
**Issue:** Neither `All` nor `PreviewStubs` is referenced by any production or test code (verified repo-wide; only the constants are used). They exist solely because the plan named them.
**Fix:** Remove them, or add a test asserting the listener's handler map covers exactly `CanvasBridgeCommands.All` — which would give `All` a real job (catching a future command added to the constants but not wired into `BuildDispatcher`).

### IN-02: `gh_bridge.get_preview_status` is unreachable from every consumer

**File:** `data-service/gh_bridge.py:97-99`; `data-service/app.py:1802-1834`
**Issue:** The 5th wire command `get_preview_status` (mandated by BRDG-01, implemented in the C# listener, and designated by 33-RESEARCH.md as the cheap liveness probe) has a Python client wrapper but no MCP tool, no REST route, and no test — dead code from every consumer path. The 4-tool MCP surface matches Plan 03, so this is deliberate deferral, but the orphaned wrapper deserves a marker.
**Fix:** Either expose it (e.g., `gh_get_preview_status` MCP tool or a `/gh/health` route reusing it as the liveness probe RESEARCH suggests) or annotate the wrapper with the phase that will consume it.

### IN-03: Redundant exception tuple in `_call`

**File:** `data-service/gh_bridge.py:57`
**Issue:** `ConnectionRefusedError` and `socket.timeout` (alias of `TimeoutError`) are both subclasses of `OSError`; `except OSError` alone is equivalent. Harmless, but implies a distinction that doesn't exist.
**Fix:** `except OSError as exc:` (keep a comment noting it covers refused + timeout).

### IN-04: `envelope.get("result", envelope)` leaks the whole envelope when `result` is absent

**File:** `data-service/gh_bridge.py:74`
**Issue:** An ok-status envelope without a `result` key returns the entire envelope (`bridge`/`version`/`status` bleed into the payload the caller stamps `project` onto); `"result": null` returns `None`. The C# `BuildOk` always emits `result`, so this is latent, but the fallback silently masks a protocol deviation instead of surfacing it.
**Fix:** `return envelope.get("result") or {}` — or raise `GH_BRIDGE_BAD_RESPONSE` (WR-04's helper) when `"result"` is missing from an ok envelope.

### IN-05: Each request line is parsed twice and BOM-stripped twice in `ServeClientAsync`

**File:** `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs:282-294`
**Issue:** The loop strips a leading U+FEFF (also done inside `TryParse`), calls `CanvasBridgeProtocol.TryParse` just to record `_lastCommand`, then `Dispatch(line)` re-parses the same line (up to 5 MiB of JSON) a second time. Duplicated logic, and two code paths that must stay in agreement about what "parses".
**Fix:** Add a `Dispatch` overload (or out-param) that surfaces the parsed `request.Type`, so the component parses once and records `_lastCommand` from the dispatch result; drop the local BOM strip.

### IN-06: Malformed `GH_BRIDGE_PORT` env var crashes the whole data-service at import time

**File:** `data-service/gh_bridge.py:28`
**Issue:** `int(os.getenv("GH_BRIDGE_PORT", "8720"))` runs at module import (and `app.py` imports `gh_bridge` at module scope), so a typo like `GH_BRIDGE_PORT=87 20` in compose prevents the entire service from starting — a config error in an optional bridge takes down validation, MCP, and every other endpoint.
**Fix:** Parse defensively:
```python
try:
    GH_BRIDGE_PORT = int(os.getenv("GH_BRIDGE_PORT", "8720"))
except ValueError:
    GH_BRIDGE_PORT = 8720
```
(optionally log a warning).

---

## Notes (verified clean — no finding)

- **Loopback bind (T-33-01):** `new TcpListener(IPAddress.Loopback, port)` — correct, never `IPAddress.Any`.
- **Allow-list dispatch (EoP):** explicit dictionary; `add_component` verified unreachable by test; v10 write commands require a code change.
- **Dispatcher never throws (T-33-02):** malformed/unknown/handler-exception all produce error envelopes; covered by tests.
- **UI-thread marshalling (Pitfall 1):** canvas reads run inside `RhinoApp.InvokeOnUiThread` via `InvokeOnCanvas`; the socket write stays on the background thread. `ScheduleSolution(1, ...)` from the background thread is the canonical GH background-update pattern (the `ExpireSolution` runs inside the scheduled UI-thread callback).
- **Toggle-off path:** `StopListener` cancels + `Stop()`s and disposes the CTS; pending accept unblocks; port freed on toggle-off (document-close path is WR-01).
- **docker-compose:** `GH_BRIDGE_HOST=host.docker.internal` + `extra_hosts: host.docker.internal:host-gateway` is the correct cross-platform (Linux/Docker Desktop) reachability setup; no new ports exposed.
- **MCP errors as HTTPException (not JSON-RPC error objects):** deliberate, matches the pre-existing `neo4j_query` precedent, and is pinned by `test_gh_bridge_error_propagates_as_httpexception_not_jsonrpc_error`.
- **`pull_computgraph_context`:** sync `def` (threadpool — correct), stamps `project`, propagates structured 502/503 unchanged; covered by tests.

_Reviewed: 2026-07-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
