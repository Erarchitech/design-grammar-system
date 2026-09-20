# Phase 33: DG Canvas Bridge (grasshopper-mcp adaptation) - Research

**Researched:** 2026-07-13
**Domain:** TCP server inside a Grasshopper/Rhino plugin, marshalled to a UI thread; a Python TCP client behind an existing FastAPI service; JSON-RPC MCP tool extension
**Confidence:** MEDIUM-HIGH (protocol/pattern grounded in this repo's own precedents and Phase 32's research; the TCP-listener-in-GH-component pattern itself has no precedent in this codebase and is flagged accordingly)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Native, not vendored** (user decision 2026-07-08): no GH_MCP.gha dependency; the TCP listener is a DG component so one plugin owns the whole workflow.
2. **DG CANVAS LISTENER** component (`Components/CanvasListenerComponent.cs`):
   - Inputs: `Run` (bool), `Port` (int, default **8720**); outputs: `Status`, `LastCommand`
   - `System.Net.Sockets.TcpListener` on 127.0.0.1 (localhost only — no LAN exposure of the canvas), accept loop on a background thread, one client at a time
   - Wire format identical to grasshopper-mcp: newline-terminated JSON `{"type": ..., "parameters": {...}}` → single-line JSON response; UTF-8, BOM-tolerant
   - Every canvas touch through `RhinoApp.InvokeOnUiThread`; command handlers must never block the UI thread on network I/O
   - Commands (v9.0, read+preview only): `get_canvas_context` (→ Phase 32 extractor+serializer), `get_selection` (selected instance GUIDs), `preview_structure`, `clear_preview`, `get_preview_status` (implemented as no-op stubs returning "not supported" until Phase 35 fills them)
   - Toggle-off closes the socket deterministically; repeated on/off must not leak the port (dispose listener in `RemovedFromDocument` too — see ConnectorComponent precedent)
3. **data-service side:**
   - `gh_bridge.py`: small TCP client; env `GH_BRIDGE_HOST` (default `host.docker.internal`), `GH_BRIDGE_PORT` (default `8720`); connect/read timeouts ~5s/30s; `ConnectionRefused`/timeout → structured error "Grasshopper bridge unreachable — start Rhino and enable DG CANVAS LISTENER (port 8720)" (What+Where+How-to-fix)
   - `app.py`: `POST /computgraph/context/pull` `{project}` → forwards `get_canvas_context`, stamps project, returns `cgContextJson`
   - Extend the existing `POST /mcp` JSON-RPC server (`neo4j-mcp`): add tools `gh_get_context`, `gh_get_selection`, `gh_preview_structure`, `gh_clear_preview` to `tools/list` + `tools/call` dispatch
4. **docker-compose.yml:** data-service gets `GH_BRIDGE_HOST/PORT` env + `extra_hosts: ["host.docker.internal:host-gateway"]` (needed on Linux hosts; harmless on Docker Desktop).

### Claude's Discretion

- Threading model detail: dedicated thread + `CancellationToken` vs async accept loop; how Grasshopper solution expiry interacts with a long-lived listener component.
- Whether `get_canvas_context` triggers a fresh solve or reads current state (read current — but confirm slider values are current without solve).
- Health command (`ping`) for the data-service `/computgraph/context/pull` pre-check.

### Deferred Ideas (OUT OF SCOPE)

- Write commands (`add_component`, `connect_components`, document mutation) — deferred to v10 (`.planning/milestones/v10.0-SEED.md`). The command dispatch should be a table that v10 can extend.
- No unsolicited pushes in v9.0 — the listener is pull-based for context (data-service asks).
- No secrets over the bridge; no LLM calls in this phase.
- Localhost bind only; the bridge carries design IP — never expose beyond the machine.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BRDG-01 | DG CANVAS LISTENER hosts a TCP listener (default port 8720) speaking the grasshopper-mcp wire protocol with 5 named commands | §"Architecture Patterns" (TCP listener component design), §"Common Pitfalls" (thread marshalling, port leak, solve-expiry interaction), §"Code Examples" (accept loop + InvokeOnUiThread bridge) |
| BRDG-02 | data-service pulls live canvas context via a bridge client and `POST /computgraph/context/pull` | §"Architecture Patterns" (gh_bridge.py client design), reuses existing `_structured_error_response` + `httpx.Timeout` precedents from `app.py` reasoner proxy |
| BRDG-03 | Existing `POST /mcp` JSON-RPC server exposes 4 new `gh_*` tools | §"Architecture Patterns" (extend existing `tools/list`/`tools/call` switch verbatim, same file/pattern) |
| BRDG-04 | Bridge is safe and diagnosable: UI-thread marshalling, bounded timeouts, clean shutdown, actionable errors | §"Common Pitfalls" (all five pitfalls), §"Don't Hand-Roll" (error templates, timeout patterns) |
</phase_requirements>

## Summary

Phase 33 builds the transport layer connecting the live Grasshopper canvas (Rhino, Windows host) to data-service (Docker). It has two independently-testable halves: a **C# TCP listener** living inside a new `DG.Grasshopper` component (`CanvasListenerComponent`), and a **Python TCP client + two data-service surfaces** (`POST /computgraph/context/pull` and 4 new `POST /mcp` tools). Both halves are wire-compatible with the [grasshopper-mcp](https://github.com/alfredatnycu/grasshopper-mcp) protocol (newline-terminated JSON, `{type, parameters}` request shape) per Phase 32's research (`32-RESEARCH.md` §1), but are a from-scratch re-implementation — no vendored plugin, no NuGet/pip dependency to add.

The **hard blocker for this phase**: it depends on `CanvasContextExtractor.SerializeContext(GH_Document, project)` (`DG.Grasshopper.Canvas`, `#if GRASSHOPPER_SDK`) and `ComputgraphContextSerializer` (`DG.Core.Serialization`), both scoped to **Phase 32**, which has 5 PLAN.md files written but **no SUMMARY/VERIFICATION artifacts — Phase 32 has not been executed yet** (confirmed by directory listing; `.planning/STATE.md` still shows `current_phase: 29`). The planner must either (a) sequence Phase 32 execution before Phase 33, or (b) plan Phase 33's listener against the *documented* Phase 32 interface (`CanvasContextExtractor.SerializeContext`) as a forward dependency and add an explicit precondition check/task. This is not a research gap — the interface is fully specified in `32-04-PLAN.md` — but it is an execution-order risk the plan must state explicitly.

On the C# side, this codebase has **no existing `TcpListener`/`TcpClient`/raw-`Socket` precedent** — `ConnectorComponent.cs` (the closest analog for "long-lived component managing an external connection, disposed in `RemovedFromDocument`, Task-based async, request-key dedup to avoid redundant work on every `SolveInstance`") is an HTTP/Bolt *client*, not a *server*. The TCP accept-loop-inside-a-GH-component pattern is genuinely novel for this repo; `ConnectorComponent`'s lifecycle/dedup/disposal patterns transfer directly, but the accept-loop-plus-UI-thread-marshalling code must be written fresh, grounded in official RhinoCommon/.NET APIs (cited below) rather than an in-repo analog.

On the Python side, `gh_bridge.py` needs a **raw TCP socket client** (stdlib `socket`, not `httpx` — the bridge is not HTTP), while `app.py`'s new `/computgraph/context/pull` endpoint and the JSON-RPC error/timeout handling should reuse the **exact `httpx.Timeout` + `_structured_error_response`** pattern already used for the `dg-reasoner` sidecar proxy (`app.py:1197-1234`) and the existing `POST /mcp` `tools/list`/`tools/call` dispatch (`app.py:1607-1687`) verbatim — no new error-handling vocabulary needed.

**Primary recommendation:** Treat `CanvasListenerComponent` as architecturally identical to `ConnectorComponent` (Task-based async work, request-key dedup on `(Run, Port)`, disposal in both the `Run=false` branch and `RemovedFromDocument`) but with the async work being "accept + serve one client at a time" instead of "connect once." Treat `gh_bridge.py` + the two data-service surfaces as a thin, boring extension of already-proven `app.py` patterns (reasoner proxy's timeout/error shape, `/mcp`'s tool dispatch switch) — no new architecture needed there.

## Architectural Responsibility Map

> This project's architecture does not fit the standard 5-tier web taxonomy (Browser/Frontend-SSR/API/CDN/Database) — `DG.Grasshopper` is a **native desktop CAD plugin process** (Rhino), a tier outside that list. Capabilities are mapped to the closest-fitting tier with an explicit note where the taxonomy doesn't apply.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TCP listener / live canvas access (`get_canvas_context`, `get_selection`, preview stubs) | **Desktop Plugin** (DG.Grasshopper, in-process with Rhino — not a standard web tier) | — | Only the Rhino/Grasshopper process holds the live `GH_Document`; this must run embedded in that process, on/marshalled to its UI thread. |
| Outbound bridge client (`gh_bridge.py`) | API / Backend (data-service) | — | data-service is this system's standard backend; it already owns all outbound network client responsibility (Neo4j driver, Speckle, dg-reasoner proxy, LLM gateway). |
| MCP tool exposure (`gh_get_context`, `gh_get_selection`, `gh_preview_structure`, `gh_clear_preview`) | API / Backend (data-service `/mcp`) | — | One MCP server for the whole system (existing `neo4j-mcp` server); extending its `tools/list`/`tools/call` keeps a single JSON-RPC surface for any MCP client. |
| Context-pull REST endpoint (`POST /computgraph/context/pull`) | API / Backend | — | Standard REST surface for non-MCP callers (future UI, other services) to pull the same document without speaking JSON-RPC. |
| Docker network reachability (`host.docker.internal`) | Infra / Orchestration (docker-compose — not a standard web tier) | — | Cross-boundary networking (container → Windows host loopback) is a compose-level concern, not application code. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `System.Net.Sockets.TcpListener`/`TcpClient` | BCL (.NET 7/9, no NuGet) | TCP server accept loop + per-client read/write | Base Class Library — zero dependency; `AcceptTcpClientAsync(CancellationToken)` overload available since .NET 6, confirmed present on both `net7.0-windows` (DG.Grasshopper) and `net7.0;net9.0` (DG.Core) [CITED: learn.microsoft.com/en-us/dotnet/api/system.net.sockets.tcplistener.accepttcpclientasync] |
| `System.Text.Json` | BCL | Parse/emit the `{type, parameters}` wire JSON on the listener side | Already the project's exclusive JSON library (`ComputgraphContextSerializer`, `DesignStatePayloadV2Serializer` both use it with the same `JsonSerializerOptions` convention) [VERIFIED: codebase — `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs`] |
| `Rhino.RhinoApp.InvokeOnUiThread(Delegate, params object[])` | RhinoCommon (already referenced by DG.Grasshopper) | Marshal canvas-touching calls from the background accept-loop thread to Rhino's UI thread | Official, documented API for exactly this purpose [CITED: developer.rhino3d.com/api/rhinocommon/rhino.rhinoapp/invokeonuithread] |
| Python `socket` (stdlib) | 3.11 (data-service container) | TCP client in `gh_bridge.py` | The bridge speaks a raw newline-JSON TCP protocol, not HTTP — `httpx` (already a dependency) does not apply here; stdlib `socket` needs no new package [VERIFIED: codebase — `data-service/requirements.txt` has no TCP-client library, none needed] |
| `httpx` | already pinned (no version constraint in `requirements.txt`) | `POST /computgraph/context/pull`'s own error/timeout conventions (NOT the bridge transport itself — httpx is unrelated to the raw TCP hop, but its `Timeout`/exception-mapping *pattern* is what `gh_bridge.py`'s `socket.settimeout()` + try/except should mirror) | Already used identically for the `dg-reasoner` sidecar proxy [VERIFIED: codebase — `data-service/app.py:1197-1234`] |
| `FastAPI` | already pinned | Hosts `/computgraph/context/pull` and extends `/mcp` | Existing framework for all data-service HTTP surfaces [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| none | — | — | This phase introduces zero new packages in either C# or Python — see Package Legitimacy Audit below. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw `TcpListener`/`TcpClient` (BCL) | `System.IO.Pipelines` / Kestrel-based custom protocol server | Massive overkill for a single-client, request/response, localhost-only protocol; no precedent in this codebase; rejected by the user's explicit "native, not vendored" / grasshopper-mcp-wire-compatible decision, which specifies plain newline-JSON sockets. |
| Python `socket` for the bridge client | `asyncio` streams (`asyncio.open_connection`) | data-service's existing endpoints are sync `def` (not `async def`) except `/mcp` itself (`async def mcp`); a blocking `socket` call with `settimeout()` inside a sync function matches the codebase's prevailing sync-httpx style (STATE.md: "matches app.py's prevailing sync-def style ... rather than introducing async" — same precedent from Phase 821 Plan 04) and is simpler to unit-test with a fake server. |

**Installation:**
```bash
# No installation required — TcpListener/TcpClient/System.Text.Json are BCL;
# Python `socket` is stdlib; httpx and fastapi are already in requirements.txt.
```

**Version verification:** No new package versions to verify — see Package Legitimacy Audit.

## Package Legitimacy Audit

**This phase introduces zero new external packages.** All new code (`CanvasListenerComponent.cs`, `gh_bridge.py`) is built exclusively from:
- .NET Base Class Library (`System.Net.Sockets`, `System.Text.Json`, `System.Threading`)
- RhinoCommon (already referenced by `DG.Grasshopper.csproj` for every existing `#if GRASSHOPPER_SDK` component)
- Python 3.11 standard library (`socket`, `json`)
- Already-pinned data-service dependencies (`httpx`, `fastapi`) — reused only for pattern consistency in the REST layer, not for the TCP hop itself

No `gsd-tools query package-legitimacy check` run was needed — there is nothing to check against a registry. The planner does not need any `checkpoint:human-verify` gate for package installation in this phase.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────── Rhino process (Windows host) ───────────────────────────────┐
│                                                                                                │
│  GH_Document (live canvas)                                                                    │
│        ▲                                                                                      │
│        │ RhinoApp.InvokeOnUiThread (sync hand-off, UI thread only)                            │
│        │                                                                                      │
│  ┌─────┴──────────────────────┐        background Task (accept loop, one client at a time)    │
│  │ CanvasListenerComponent    │◄───────────────────────────────────────────────────────────┐  │
│  │ (GH_Component)             │        TcpListener.AcceptTcpClientAsync(ct)                 │  │
│  │  - Run (bool) / Port (int) │        newline-JSON read → dispatch table → write response  │  │
│  │  - Status / LastCommand    │                                                              │  │
│  └─────────────────────────────────────────────────── 127.0.0.1:8720 (loopback only) ────────┘
│                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
                                          ▲
                                          │ raw TCP, newline-terminated JSON
                                          │ {"type": "get_canvas_context", "parameters": {}}
                                          │
┌──────────────────────────── Docker network (data-service container) ────────────────────────┐
│                                                                                                │
│  gh_bridge.py                                                                                 │
│    connect(GH_BRIDGE_HOST:GH_BRIDGE_PORT)  ── ConnectionRefusedError/timeout ──► structured   │
│    send request, read one line, parse JSON      error (What+Where+How-to-fix)                 │
│        │                                                                                      │
│        ▼                                                                                      │
│  app.py                                                                                        │
│    POST /computgraph/context/pull {project}  ──► stamps project ──► returns cgContextJson      │
│    POST /mcp  (existing JSON-RPC "neo4j-mcp" server)                                           │
│      tools/list   ──► now also lists gh_get_context, gh_get_selection,                         │
│                        gh_preview_structure, gh_clear_preview                                  │
│      tools/call   ──► dispatch switch: gh_* tool → gh_bridge.py → TCP round-trip → JSON result │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
                                          ▲
                                          │ POST /computgraph/context/pull  or  POST /mcp
                                          │
                                   any MCP client / caller (LLM gateway, future UI, curl)
```

### Recommended Project Structure

```
DG/src/DG.Grasshopper/
├── Components/
│   └── CanvasListenerComponent.cs   # NEW — TCP listener GH_Component (BRDG-01)
├── Canvas/
│   └── CanvasContextExtractor.cs    # Phase 32 dependency — SerializeContext(GH_Document, project)
DG/src/DG.Core/
├── Serialization/
│   └── ComputgraphContextSerializer.cs   # Phase 32 dependency (transitively via extractor)

data-service/
├── gh_bridge.py                     # NEW — TCP client (BRDG-02)
├── app.py                           # MODIFIED — POST /computgraph/context/pull + 4 gh_* tools in /mcp (BRDG-02, BRDG-03)

docker-compose.yml                   # MODIFIED — GH_BRIDGE_HOST/PORT env + extra_hosts on data-service
```

### Pattern 1: Long-lived GH_Component with async external work, request-key dedup, and disposal on removal

**What:** `ConnectorComponent`'s existing pattern — `SolveInstance` fires on every canvas recompute, but the component must not redo expensive/stateful work (connect, or here, start/stop a listener) unless its relevant inputs actually changed. It builds a string "request key" from the inputs that matter, compares to the last-started key, and only (re)starts work when the key changes. Disposal happens in `RemovedFromDocument` in addition to the normal off-path.

**When to use:** `CanvasListenerComponent` — apply identically, with `(Run, Port)` as the key instead of `ConnectorComponent`'s connection-string key.

**Example:**
```csharp
// Source: DG/src/DG.Grasshopper/Components/ConnectorComponent.cs (existing code, this repo)
private void StartConnection(ConnectionInfo request, string dataServiceUrl, string token, string requestKey)
{
    CancelPendingConnection();
    _activeRequestKey = requestKey;
    _connectCts = new CancellationTokenSource();
    _connectTask = RunConnectAsync(request, dataServiceUrl, token, _connectCts.Token);
    _ = _connectTask.ContinueWith(
        _ => { var doc = OnPingDocument(); doc?.ScheduleSolution(1, _ => ExpireSolution(false)); },
        TaskScheduler.Default);
}

public override void RemovedFromDocument(GH_Document document)
{
    CancelPendingConnection();
    base.RemovedFromDocument(document);
}

private void CancelPendingConnection()
{
    try { _connectCts?.Cancel(); }
    catch { /* best-effort */ }
    finally { _connectCts?.Dispose(); _connectCts = null; _connectTask = null; _activeRequestKey = string.Empty; }
}
```
Apply to `CanvasListenerComponent`: replace `RunConnectAsync` with `RunAcceptLoopAsync(TcpListener, CancellationToken)`; `CancelPendingConnection` becomes `StopListener()`, calling `_listener?.Stop()` (which both unblocks a pending `AcceptTcpClientAsync` and releases the port) before disposing the `CancellationTokenSource`.

### Pattern 2: TCP accept loop + UI-thread marshalling for canvas access

**What:** A background `Task` runs `while (!ct.IsCancellationRequested) { client = await listener.AcceptTcpClientAsync(ct); ServeClient(client, ct); }` — one client at a time, as CONTEXT.md requires. Per accepted client, read one newline-terminated JSON line, dispatch by `type`, and — **only for commands that touch the canvas** — synchronously hand off to the UI thread via `RhinoApp.InvokeOnUiThread`, using a `TaskCompletionSource<string>` (or `ManualResetEventSlim` + a result field) to get the computed JSON back to the background thread, which then performs the actual socket write (never the UI thread).

**When to use:** Every command handler in `CanvasListenerComponent`'s dispatch table.

**Example:**
```csharp
// Source: composed from RhinoCommon docs [CITED: developer.rhino3d.com/api/rhinocommon/rhino.rhinoapp/invokeonuithread]
// and .NET docs [CITED: learn.microsoft.com/en-us/dotnet/api/system.net.sockets.tcplistener.accepttcpclientasync]
// — no in-repo analog exists for this exact shape; this is the recommended composition.

private string InvokeOnCanvas(Func<string> canvasWork)
{
    var tcs = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
    RhinoApp.InvokeOnUiThread(new Action(() =>
    {
        try { tcs.SetResult(canvasWork()); }
        catch (Exception ex) { tcs.SetException(ex); }
    }));
    // Blocks the background accept-loop thread (fine — it's not the UI thread),
    // never blocks the UI thread on network I/O.
    return tcs.Task.GetAwaiter().GetResult();
}

private async Task ServeClientAsync(TcpClient client, CancellationToken ct)
{
    using var stream = client.GetStream();
    using var reader = new StreamReader(stream, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    using var writer = new StreamWriter(stream, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false)) { AutoFlush = true, NewLine = "\n" };

    while (!ct.IsCancellationRequested)
    {
        var line = await reader.ReadLineAsync(ct).ConfigureAwait(false);
        if (line is null) break; // client disconnected

        var request = JsonSerializer.Deserialize<CommandRequest>(line.TrimStart('﻿'), JsonOptions);
        var responseJson = Dispatch(request); // command handler decides whether InvokeOnCanvas is needed
        await writer.WriteLineAsync(responseJson).ConfigureAwait(false); // I/O off the UI thread
    }
}
```

### Pattern 3: Extend the existing `/mcp` JSON-RPC dispatch verbatim

**What:** `app.py`'s `POST /mcp` already implements `tools/list`, `initialize`, and `tools/call` with an `if tool_name == "..."` chain. Adding `gh_*` tools means appending 4 entries to the `tools/list` array and 4 `if tool_name == "gh_..."` branches to the same chain — no new abstraction.

**When to use:** BRDG-03, exactly as CONTEXT.md specifies.

**Example:**
```python
# Source: data-service/app.py:1613-1687 (existing code, this repo) — extend this exact structure
if method == "tools/list":
    return {
        "jsonrpc": "2.0", "id": req_id,
        "result": {"tools": [
            {"name": "neo4j_schema", "description": "..."},
            {"name": "neo4j_query", "description": "..."},
            {"name": "gh_get_context", "description": "Return the live Grasshopper canvas as cgContextJson v1."},
            {"name": "gh_get_selection", "description": "Return currently-selected object instance GUIDs."},
            {"name": "gh_preview_structure", "description": "Preview a proposed Computgraph structure on the canvas (stub in v9.0)."},
            {"name": "gh_clear_preview", "description": "Clear any active canvas preview (stub in v9.0)."},
        ]},
    }
# ... in the tools/call branch, after the existing neo4j_query branch:
if tool_name == "gh_get_context":
    project = arguments.get("project", "")
    context = gh_bridge.get_canvas_context(project)  # raises _structured_error_response internally on failure
    return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": "context"}], "data": context}}
```

### Anti-Patterns to Avoid

- **Calling `RhinoApp.InvokeOnUiThread` and doing the socket write inside the delegate:** the delegate must return the computed JSON string only; the TCP write must happen back on the background thread after the UI-thread call completes. Writing to the socket from inside `InvokeOnUiThread` blocks Rhino's UI thread on network I/O — exactly what CONTEXT.md's constraint forbids.
- **Restarting the `TcpListener` on every `SolveInstance` when `Run=true` and nothing changed:** `SolveInstance` fires on unrelated canvas recomputes too (any upstream expire). Always dedup on `(Run, Port)` like `ConnectorComponent` does on its connection key, or every drag-a-slider-elsewhere event will tear down and rebind the listener.
- **Accepting multiple concurrent clients:** CONTEXT.md specifies "one client at a time." Do not spin up a new `Task` per accepted connection in a loop that keeps accepting — accept, fully serve, then accept again.
- **Using JSON-RPC error objects (`{"error": {"code":..., "message":...}}`) for `tools/call` failures:** the existing `/mcp` handler raises `HTTPException`/`_structured_error_response` instead (see `app.py:1673-1687`, `1622-1234`). Match that precedent for the 4 new `gh_*` tools rather than inventing a JSON-RPC-spec-correct error envelope that the rest of the file doesn't use.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured, actionable error messages | Ad-hoc error strings per failure site | `ErrorMessageTemplates` (C#, `DG.Core.Services`) / `_structured_error_response(error, hint, code, status_code)` (Python, `app.py:576`) | Both are already the project-wide What+Where+How-to-fix convention; every existing connectivity error (`ConnectorHeartbeatUnreachable`, `REASONER_UNAVAILABLE`) follows this shape — the bridge-unreachable error CONTEXT.md specifies should be a new template/response using the same helpers, not a new pattern. |
| JSON serialization of domain objects | Attribute-decorated domain models (`[JsonPropertyName]` on `Cg*` classes) | The existing DTO-tree + `JsonSerializerOptions{CamelCase, WriteIndented=false}` convention (`DesignStatePayloadV2Serializer`, `ComputgraphContextSerializer`) | `CanvasListenerComponent`'s wire envelope (`{type, parameters}` request / response wrapper) should get its own small private DTO type using the identical `Options` block — do not reuse the Computgraph DTOs for the *envelope*, only for the payload they carry (which is already a pre-serialized string from `SerializeContext`). |
| Outbound network client timeout/retry | Custom retry loops around `socket` calls | `socket.settimeout(connect_seconds)` for the connect phase + a second timeout for the blocking `recv`/`makefile().readline()` call, mirroring the `httpx.Timeout(connect=2.0, read=..., write=2.0, pool=2.0)` shape already used for the reasoner proxy | Keeps the mental model ("short connect timeout, longer read timeout, fail fast, surface actionable error") consistent across every outbound integration in `app.py`, even though the transport (raw socket vs. httpx) differs. |
| MCP JSON-RPC request/response plumbing | A new MCP server/router | Extend the existing `POST /mcp` function's `if method == ...` / `if tool_name == ...` chains | One MCP server for the whole system is an explicit v9.0 architectural decision (`REQUIREMENTS.md` Key Decisions: "data-service reuses its existing `/mcp` server and Phase-01 gateway"). |

**Key insight:** every piece of this phase except the TCP accept-loop-plus-UI-marshalling logic itself has a direct, provable in-repo analog. Concentrate implementation risk and review attention on `CanvasListenerComponent`'s threading code — that is the one genuinely novel subsystem being introduced.

## Common Pitfalls

### Pitfall 1: Blocking the UI thread on network I/O inside `InvokeOnUiThread`
**What goes wrong:** The socket write (or the whole `ServeClientAsync` loop) gets called from inside the `RhinoApp.InvokeOnUiThread` delegate "for convenience," freezing Rhino's UI for the duration of every TCP round-trip.
**Why it happens:** It's the path of least resistance — the delegate already has access to both the canvas and (via closure) the socket.
**How to avoid:** Strictly separate "compute JSON on the UI thread, return a string" (inside `InvokeOnUiThread`) from "write JSON to socket" (on the background accept-loop thread), as in Pattern 2 above. Use a `TaskCompletionSource<string>` to hand the result back.
**Warning signs:** Rhino UI becomes unresponsive whenever data-service polls `/computgraph/context/pull`; a slow/misbehaving TCP client (or a Docker network hiccup) freezes the whole Rhino session, not just the listener.

### Pitfall 2: Port leak / stale listener across repeated on/off cycles
**What goes wrong:** Toggling `Run` false→true→false→true repeatedly (or GH's own `RemovedFromDocument`/undo/redo of the component) eventually throws `SocketException: Address already in use`, or leaves an orphaned background `Task` still holding the port after the component appears "off."
**Why it happens:** `SolveInstance` runs on every recompute; without request-key dedup (Pattern 1), the component may call `listener.Start()` again while a previous listener/task from an earlier solve is still alive, or `RemovedFromDocument` is not covered so the listener survives component deletion.
**How to avoid:** Dedup on `(Run, Port)` exactly like `ConnectorComponent` dedups on its connection key; call `listener.Stop()` (which also unblocks any in-flight `AcceptTcpClientAsync`) in **both** the `Run=false` branch of `SolveInstance` **and** `RemovedFromDocument` — mirror `ConnectorComponent.CancelPendingConnection()`'s try/finally shape exactly.
**Warning signs:** Repeated `SocketException` after several on/off toggles in a single Rhino session; `netstat`/Resource Monitor still shows the process listening on 8720 after `Run=false`.

### Pitfall 3: Restarting the listener on every unrelated `SolveInstance`
**What goes wrong:** Any canvas recompute (moving a slider elsewhere on the same document, adding an unrelated component) re-triggers `SolveInstance` on `CanvasListenerComponent`; without dedup, this tears down and rebinds the TCP listener on every single recompute, causing a visible flicker in `Status`, dropped in-flight connections, and (briefly) the exact port-already-in-use race from Pitfall 2.
**Why it happens:** This is CONTEXT.md's own flagged open question ("how Grasshopper solution expiry interacts with a long-lived listener component") — GH gives no built-in "only run once" semantics for a component whose job is to persist state across solves.
**How to avoid:** Same request-key dedup as `ConnectorComponent` — build a key from `(Run, Port)` only (not from anything else in the document), compare to the currently-running key, and no-op if unchanged.
**Warning signs:** `Status` output flickers or resets during unrelated canvas edits; a client mid-request gets an abrupt disconnect when the user tweaks an unrelated slider.

### Pitfall 4: BOM / line-ending mismatches on the wire
**What goes wrong:** A client (Python `socket` sends `\n`; some Windows tools or a hand-typed `telnet` test might send `\r\n`; a UTF-8 BOM prepended by some JSON emitters) causes `StreamReader.ReadLine()` to either hang (never sees the expected terminator) or `JsonSerializer.Deserialize` to throw on a stray `﻿` prefix.
**Why it happens:** CONTEXT.md explicitly calls out "BOM-tolerant" because the reference grasshopper-mcp protocol had exactly this class of bug across its Python/C# boundary.
**How to avoid:** Construct `StreamReader`/`StreamWriter` with `new UTF8Encoding(encoderShouldEmitUTF8Identifier: false)` (Pattern 2 example) to avoid emitting a BOM; strip a leading `﻿` from any incoming line before `Deserialize`; set `writer.NewLine = "\n"` explicitly rather than relying on `Environment.NewLine` (which is `\r\n` on Windows).
**Warning signs:** First request after connecting silently hangs; intermittent `JsonException: '﻿' is an invalid start of a value`.

### Pitfall 5: Unbounded read blocking the accept loop indefinitely
**What goes wrong:** A client connects but never sends a complete newline-terminated line (network partition, misbehaving client, or someone `nc`-ing into port 8720 and doing nothing) — `ReadLineAsync` with no timeout blocks forever, and because CONTEXT.md specifies "one client at a time," this starves every other request until the process is killed.
**Why it happens:** The default `TcpClient`/`NetworkStream` has no read timeout unless one is explicitly set.
**How to avoid:** Set a read timeout on the accepted `TcpClient` (`client.ReceiveTimeout`) or wrap `ReadLineAsync` in a `Task.WhenAny` against a timeout `Task.Delay`, and close the connection (looping back to `AcceptTcpClientAsync`) on timeout rather than hanging. This is the C#-side mirror of `gh_bridge.py`'s own `~5s connect / ~30s read` timeout requirement from CONTEXT.md — both ends need a bound, not just the client.
**Warning signs:** `POST /computgraph/context/pull` from data-service hangs past its own 30s read timeout and eventually returns the "unreachable" error even though Rhino is running and the listener is nominally "on" — because a previous stuck client never released the single-client slot.

## Code Examples

### `gh_bridge.py` — TCP client with connect/read timeouts and structured errors

```python
# Source: pattern composed from data-service/app.py:1197-1234 (existing httpx.Timeout +
# _structured_error_response precedent for the dg-reasoner sidecar proxy), adapted to raw
# sockets since the bridge speaks newline-JSON TCP, not HTTP.
import json
import os
import socket

from app import _structured_error_response  # or move _structured_error_response to a shared module

GH_BRIDGE_HOST = os.getenv("GH_BRIDGE_HOST", "host.docker.internal")
GH_BRIDGE_PORT = int(os.getenv("GH_BRIDGE_PORT", "8720"))
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 30.0


def _call(command_type: str, parameters: dict) -> dict:
    try:
        with socket.create_connection(
            (GH_BRIDGE_HOST, GH_BRIDGE_PORT), timeout=CONNECT_TIMEOUT_SECONDS
        ) as sock:
            sock.settimeout(READ_TIMEOUT_SECONDS)
            request = json.dumps({"type": command_type, "parameters": parameters}) + "\n"
            sock.sendall(request.encode("utf-8"))
            buffered = sock.makefile("r", encoding="utf-8")
            line = buffered.readline()
            if not line:
                raise ConnectionError("Bridge closed the connection without a response.")
            return json.loads(line)
    except (ConnectionRefusedError, socket.timeout, OSError) as exc:
        raise _structured_error_response(
            f"Grasshopper bridge unreachable at {GH_BRIDGE_HOST}:{GH_BRIDGE_PORT}: {exc}",
            "Start Rhino and enable DG CANVAS LISTENER (port 8720).",
            "GH_BRIDGE_UNREACHABLE",
            503,
        ) from exc


def get_canvas_context(project: str) -> dict:
    return _call("get_canvas_context", {"project": project})
```

### `app.py` — `POST /computgraph/context/pull`

```python
# Source: pattern composed from existing app.py route conventions
# (Pydantic request model + thin handler, e.g. ReasonerConsistencyRequest at app.py:1192-1198)
class ComputgraphContextPullRequest(BaseModel):
    project: str


@app.post("/computgraph/context/pull")
def pull_computgraph_context(payload: ComputgraphContextPullRequest):
    result = gh_bridge.get_canvas_context(payload.project)
    context = result.get("result", result)  # unwrap bridge envelope per Open Question below
    context["project"] = payload.project  # stamp project per CONTEXT.md
    return context
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Third-party `GH_MCP.gha` plugin (grasshopper-mcp reference project) providing the TCP bridge | Native re-implementation inside `DG.Grasshopper`, protocol-compatible only | Decided 2026-07-08 (v9.0 restructure, `REQUIREMENTS.md` Key Decisions) | No second plugin on the canvas; DG owns the whole workflow and can diverge from the reference protocol (e.g., add `gh_*`-specific commands) without waiting on an upstream fork. |

**Deprecated/outdated:** N/A — this is new functionality in this codebase, not a replacement of an existing one.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The TCP response envelope should carry `{"bridge": "dg", "version": 1, "status": "ok"/"error", "result"/"error": {...}}` — CONTEXT.md only mandates that responses include `{"bridge": "dg", "version": 1}`, not the full success/error shape | Architecture Patterns (Pattern 2), Code Examples | Low-medium — if the planner/executor picks a different envelope shape, `gh_bridge.py`'s unwrap logic (`result.get("result", result)`) and the `/mcp` tool responses must match whatever shape is actually implemented; get this nailed down in a Task 1 checkpoint before writing both C# and Python sides in parallel, since they must agree on the exact same envelope. |
| A2 | Grasshopper number sliders' `CurrentValue`/persistent data reflects the live value without requiring a fresh solve — i.e., `get_canvas_context` reading "current state" (CONTEXT.md's decision) doesn't need to trigger `ExpireSolution` first | Common Pitfalls (implicitly informs Pitfall 3 / the "read current, no solve" open question) | Low — this is standard, well-documented GH/RhinoCommon behavior (slider values are UI-driven, not solve-output-driven), but it was not independently verified against Phase 32's actual `CanvasContextExtractor` implementation because that code does not exist yet (Phase 32 unexecuted). If Phase 32's extractor turns out to read solved data-tree outputs instead of live document state for some field, this assumption breaks. |
| A3 | `RhinoApp.InvokeOnUiThread`'s delegate execution model (queued, asynchronous relative to the caller unless the caller blocks on a signal) works safely from a `Task`-based background thread the way `Pattern 2` assumes | Architecture Patterns (Pattern 2) | Medium — this is standard RhinoCommon usage with no known gotcha in official docs, but no in-repo precedent exists to cross-check against; the planner should treat the exact threading code as needing a `checkpoint:human-verify` (live Rhino test) before considering BRDG-01/BRDG-04 done, consistent with this repo's Phase 824 precedent of gating socket/thread-adjacent work behind an in-Rhino manual check. |

**If this table is empty:** N/A — see above.

## Open Questions

1. **Phase 32 execution status blocks this phase's implementation, not just its research.**
   - What we know: Phase 32's PLAN.md files fully specify `CanvasContextExtractor.SerializeContext(GH_Document, project) : string` (namespace `DG.Grasshopper.Canvas`) and `ComputgraphContextSerializer` (namespace `DG.Core.Serialization`) — the exact seam `get_canvas_context` must call.
   - What's unclear: Whether Phase 32 will be executed before Phase 33 starts, or whether Phase 33's plan needs a precondition/gate task that fails fast with a clear message if those types don't exist yet.
   - Recommendation: The planner should add an explicit Task 0 (or a plan-level precondition note) checking `DG/src/DG.Grasshopper/Canvas/CanvasContextExtractor.cs` exists before wiring `get_canvas_context`'s handler to it; if Phase 32 is still unexecuted when Phase 33 planning happens, sequence Phase 32 first (the roadmap already lists it as a hard dependency: "Requires: Phase 32").

2. **Wire envelope shape for responses beyond the `{"bridge": "dg", "version": 1}` handshake fields (see Assumption A1).**
   - What we know: CONTEXT.md mandates the two capability-detection fields; it does not specify success/error/result field names.
   - What's unclear: The exact shape both the C# listener and the Python client must agree on byte-for-byte.
   - Recommendation: Lock this in the plan itself (not left to each side's implementer to guess independently) — e.g. as a shared "wire contract" note referenced by both the `CanvasListenerComponent` task and the `gh_bridge.py` task.

3. **`ping`/health command for `/computgraph/context/pull`'s pre-check (CONTEXT.md "Claude's Discretion").**
   - What we know: CONTEXT.md flags this as open; the 5 mandated commands (`get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`, `get_preview_status`) don't include one.
   - What's unclear: Whether a dedicated lightweight `ping` command is worth adding to the dispatch table for BRDG-04's "actionable error, not a hang" requirement, versus just relying on the TCP connect itself (refused/timeout) as the liveness signal.
   - Recommendation: Skip a dedicated `ping` command — the connect-refused/timeout path already produces the exact structured error CONTEXT.md specifies, and `get_preview_status` (already in the 5-command list, defined as a stub) can double as a cheap liveness probe if a distinct health check is later wanted. Avoids growing the v9.0 command surface beyond what's specified.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| .NET SDK (net7.0-windows target) | `CanvasListenerComponent` build | ✓ | 9.0.308 (SDK; targets net7.0-windows via multi-targeting, confirmed working per `.planning/STATE.md` Phase 824 note: "dotnet test/dotnet build ran clean on net9.0 without DOTNET_ROLL_FORWARD") | — |
| Docker + Docker Compose | data-service rebuild, `host.docker.internal` networking | ✓ | Docker 29.1.3, Compose v2.40.3-desktop.1 | — |
| Rhino + Grasshopper running with the DG plugin loaded, on the Windows host | All live verification (BRDG success criteria 1, 2, 4) | Cannot be probed via CLI — must be manually confirmed at execution/verification time | — | None — this is an unavoidable manual/human-verify step, consistent with this repo's Phase 824 precedent (3 in-Rhino UAT checks). The plan should include a `checkpoint:human-verify` task for the live end-to-end check rather than assuming CI/automated coverage can substitute. |
| Python 3.11 (container) | `gh_bridge.py` runtime | ✓ (pinned via `data-service/Dockerfile: FROM python:3.11-slim`) | 3.11 | — |
| Windows loopback (127.0.0.1) TCP accept | Listener binding | ✓ — loopback traffic bypasses Windows Firewall's inbound rules by default; no firewall exception should be needed since the listener never binds `0.0.0.0` | — | — |

**Missing dependencies with no fallback:**
- Live Rhino/Grasshopper session for end-to-end verification (manual, human-verify checkpoint required — see above).

**Missing dependencies with fallback:**
- None beyond the Rhino live-session item above.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (C#) | xUnit (`DG/tests/DG.Tests/DG.Tests.csproj`) — existing project, `net9.0` per `DG_ROLL_FORWARD`-free build confirmed in STATE.md |
| Framework (Python) | pytest + FastAPI `TestClient` (`data-service/tests/`) — existing pattern, e.g. `test_reasoner.py`'s `TestClient(app, raise_server_exceptions=False)` with `monkeypatch` for module-level state |
| Config file (C#) | `DG/tests/DG.Tests/DG.Tests.csproj` |
| Config file (Python) | none dedicated — `data-service/tests/conftest.py` + per-file `sys.path.insert` bootstrap (existing convention) |
| Quick run command (C#) | `dotnet test .\DG\tests\DG.Tests\ --filter FullyQualifiedName~CanvasListener` |
| Quick run command (Python) | `python -m pytest data-service/tests/test_gh_bridge.py -x` (new file, to be created) |
| Full suite command (C#) | `dotnet test .\DG\tests\DG.Tests\` |
| Full suite command (Python) | `python -m pytest data-service/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRDG-01 | Dispatch table routes each of the 5 command types to the right handler (unit-testable independent of a real socket by extracting a pure `Dispatch(CommandRequest) : string` method) | unit | `dotnet test --filter FullyQualifiedName~CanvasListenerDispatch` | ❌ Wave 0 |
| BRDG-01 | Request-key dedup: same `(Run, Port)` across two `SolveInstance` calls does not restart the listener; changed `Port` does | unit | `dotnet test --filter FullyQualifiedName~CanvasListenerDedup` | ❌ Wave 0 |
| BRDG-01 | Live socket round-trip: start listener, connect a raw `TcpClient` in the test, send `get_canvas_context`, assert a well-formed JSON line comes back | integration (requires `#if GRASSHOPPER_SDK` — likely only runnable where the Grasshopper SDK assemblies are present, i.e. NOT in the DG.Tests default CI config per the existing `net7.0-windows` vs `net9.0` TFM split noted in STATE.md Phase 823 Plan 05) | manual / conditional | ❌ Wave 0 — flag as environment-gated, may need to be a manual/human-verify step rather than CI-automated |
| BRDG-02 | `gh_bridge.get_canvas_context` maps `ConnectionRefusedError`/timeout to the structured 503 error with the exact hint text | unit | `python -m pytest data-service/tests/test_gh_bridge.py::test_connection_refused_maps_to_structured_error -x` | ❌ Wave 0 |
| BRDG-02 | `POST /computgraph/context/pull` stamps `project` onto the returned document and forwards the bridge's `get_canvas_context` result | integration (TestClient + monkeypatched `gh_bridge`) | `python -m pytest data-service/tests/test_app_computgraph_pull.py -x` | ❌ Wave 0 |
| BRDG-03 | `tools/list` on `/mcp` includes all 4 `gh_*` tool names | unit | `python -m pytest data-service/tests/test_mcp_gh_tools.py::test_tools_list_includes_gh_tools -x` | ❌ Wave 0 |
| BRDG-03 | `tools/call` with `gh_get_context` dispatches through `gh_bridge` and returns the expected `data` shape | unit (mocked `gh_bridge`) | `python -m pytest data-service/tests/test_mcp_gh_tools.py::test_tools_call_gh_get_context -x` | ❌ Wave 0 |
| BRDG-04 | Listener off / Rhino closed → `/computgraph/context/pull` returns actionable error, not a hang, within the configured timeout budget | integration | `python -m pytest data-service/tests/test_gh_bridge.py::test_unreachable_bridge_times_out_bounded -x` | ❌ Wave 0 |
| BRDG-04 | Toggling `Run` false after true calls `TcpListener.Stop()` and does not throw on a second start (no port leak) | unit | `dotnet test --filter FullyQualifiedName~CanvasListenerLifecycle` | ❌ Wave 0 |
| BRDG-04 | End-to-end live check: Rhino running, listener on, `curl -X POST :8000/computgraph/context/pull` from inside the compose network returns real `cgContextJson`; listener off → actionable error; `tools/list` shows the 4 `gh_*` tools | manual (per Phase's own Verification sketch) | N/A — `checkpoint:human-verify` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** relevant quick-run command above (C# or Python, matching the file touched)
- **Per wave merge:** both full suite commands (`dotnet test`, `python -m pytest data-service/tests/`)
- **Phase gate:** full suites green + the manual live-Rhino end-to-end check (`checkpoint:human-verify`) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `data-service/tests/test_gh_bridge.py` — new file, covers BRDG-02/BRDG-04 bridge-client error mapping and timeout behavior (mock the socket via `unittest.mock.patch("socket.create_connection", ...)`, mirroring `test_reasoner.py`'s `monkeypatch`/fixture style)
- [ ] `data-service/tests/test_app_computgraph_pull.py` — new file, covers BRDG-02's `/computgraph/context/pull` endpoint (TestClient + monkeypatched `gh_bridge.get_canvas_context`)
- [ ] `data-service/tests/test_mcp_gh_tools.py` — new file, covers BRDG-03's 4 new tools in `tools/list`/`tools/call`
- [ ] `DG/tests/DG.Tests/CanvasListenerComponentTests.cs` (or split into `Dispatch`/`Dedup`/`Lifecycle` test classes) — new file(s), covers BRDG-01/BRDG-04's dispatch, dedup, and lifecycle logic; extract the dispatch table and dedup-key logic into plain, `#if GRASSHOPPER_SDK`-free (or minimally-guarded) methods where possible so they're testable the same way `ComputgraphContextSerializerTests` tests DG.Core code without the SDK — but note `CanvasListenerComponent` itself, being a `GH_Component`, likely needs the same `net7.0-windows`-only test gating noted for `CanvasContextExtractor` in Phase 32's plans; confirm during planning whether DG.Tests can exercise it directly or whether only the extracted pure logic is unit-testable
- [ ] Framework install: none — xUnit and pytest are both already wired into this repo

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | The bridge is explicitly unauthenticated by design (CONTEXT.md: "No secrets over the bridge"); localhost-only binding is the sole trust boundary. |
| V3 Session Management | No | Stateless request/response per TCP connection; no session concept. |
| V4 Access Control | Partial | Enforced entirely by network topology (127.0.0.1 bind + `extra_hosts`/Docker networking), not application-level authorization — document this as the accepted control, not a gap. |
| V5 Input Validation | Yes | Incoming wire JSON (`{type, parameters}`) must be validated before dispatch: unknown `type` → structured error, not a silent no-op; malformed JSON → caught `JsonException`/`json.JSONDecodeError`, never an unhandled crash of the accept loop. |
| V6 Cryptography | No | No secrets transit this bridge in v9.0 (explicit constraint); no TLS needed for a loopback-only socket. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Listener accidentally bound to `0.0.0.0` instead of `127.0.0.1`, exposing the live canvas (design IP) to the LAN | Information Disclosure | `TcpListener` must be constructed with `IPAddress.Loopback` (`127.0.0.1`), never `IPAddress.Any`; CONTEXT.md is explicit about this — add an assertion/test that the bound address is loopback-only. |
| A malformed or oversized line causing an unhandled exception that crashes the accept loop, taking the listener down silently (denial of service against subsequent legitimate requests) | Denial of Service | Wrap per-client handling in try/catch that logs + continues the accept loop rather than propagating; a single bad client must not kill the whole listener. |
| A future v10 write-command (`add_component`, etc.) accidentally becoming reachable through this v9.0 dispatch table if the table isn't structured for safe extension | Elevation of Privilege (scope creep) | CONTEXT.md's own constraint: "The command dispatch should be a table that v10 can extend" — structure it as an explicit allow-list dictionary/switch of the 5 named v9.0 commands, not a generic reflection-based dispatcher, so v10's write commands require a deliberate code change to add, not just a new `type` string arriving over the wire. |

## Sources

### Primary (HIGH confidence)
- `.planning/milestones/v9.0-phases/32-computgraph-serialization-core/32-RESEARCH.md` §1, §7 — grasshopper-mcp protocol adaptation decisions and existing-code-to-reuse table, already researched for this milestone [VERIFIED: repo]
- `.planning/milestones/v9.0-phases/32-computgraph-serialization-core/32-03-PLAN.md`, `32-04-PLAN.md` — exact `ComputgraphContextSerializer`/`CanvasContextExtractor` interface this phase must call [VERIFIED: repo]
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` (full file read) — the closest in-repo analog for long-lived-component/async/dedup/disposal patterns [VERIFIED: repo]
- `data-service/app.py:1607-1687` (existing `/mcp` handler), `1197-1234` (reasoner proxy timeout/error pattern), `576-581` (`_structured_error_response`) [VERIFIED: repo]
- `.planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-CONTEXT.md` — locked user decisions [VERIFIED: repo]
- Microsoft Learn: `TcpListener.AcceptTcpClientAsync` — confirms `CancellationToken` overload availability [CITED: learn.microsoft.com/en-us/dotnet/api/system.net.sockets.tcplistener.accepttcpclientasync]
- Rhino Developer docs: `RhinoApp.InvokeOnUiThread` signature [CITED: developer.rhino3d.com/api/rhinocommon/rhino.rhinoapp/invokeonuithread]

### Secondary (MEDIUM confidence)
- WebSearch results on grasshopper-mcp repository structure (`alfredatnycu/grasshopper-mcp`) — confirmed `GH_MCP/` (C#) and `grasshopper_mcp/bridge.py` (Python) directory layout exists, but the exact `.cs` listener implementation could not be fetched (404 on the guessed raw path; GitHub page fetch did not enumerate individual `.cs` files) — protocol shape is instead taken from Phase 32's already-researched summary of this same repo, not independently re-verified this session [CITED: github.com/alfredatnycu/grasshopper-mcp]
- WebSearch: TcpListener graceful shutdown pattern discussion (darchuk.net, homedutech.com) — general community guidance consistent with the official Microsoft Learn API docs, used only to corroborate the CancellationToken-based shutdown approach [CITED: community sources, cross-checked against Microsoft Learn]

### Tertiary (LOW confidence)
- None — no findings relied on unverified training-data-only claims beyond what's logged in Assumptions Log (A1-A3).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages, every library already in use in this exact codebase with a direct precedent
- Architecture: MEDIUM-HIGH — data-service side is a direct, low-risk extension of proven patterns; the C# TCP-listener-in-GH-component side is architecturally sound (grounded in official docs + the closest in-repo analog) but has no in-repo precedent to cross-check against, hence not HIGH
- Pitfalls: MEDIUM-HIGH — five concrete, mechanism-level pitfalls identified with specific avoidance code, but none could be empirically reproduced this session (no live Rhino environment available to the researcher) — treat as informed prediction, not observed failure

**Research date:** 2026-07-13
**Valid until:** 30 days (stable BCL/RhinoCommon APIs; the one fast-moving risk is Phase 32's execution status, which could change within days — re-check `CanvasContextExtractor` actually exists before Phase 33 execution begins, regardless of this document's age)
