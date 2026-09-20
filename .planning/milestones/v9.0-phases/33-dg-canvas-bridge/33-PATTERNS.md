# Phase 33: DG Canvas Bridge (grasshopper-mcp adaptation) - Pattern Map

**Mapped:** 2026-07-13
**Files analyzed:** 6 (new/modified)
**Analogs found:** 5 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` | component (GH_Component, TCP server) | event-driven / request-response | `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` | role-match (lifecycle/dedup/disposal identical; TCP accept-loop itself has no in-repo analog — see below) |
| `data-service/gh_bridge.py` | service (outbound TCP client) | request-response | `data-service/app.py` reasoner proxy block (`post_reasoner_consistency`, L1197-1239) | role-match (same timeout/structured-error shape, different transport: raw socket vs httpx) |
| `data-service/app.py` — `POST /computgraph/context/pull` | route/controller | request-response | `data-service/app.py` `post_reasoner_consistency` (L1192-1239) | exact (thin proxy handler pattern) |
| `data-service/app.py` — 4 `gh_*` tools in `/mcp` | route/controller (JSON-RPC dispatch extension) | request-response | `data-service/app.py` `mcp()` (L1607-1687) | exact (extend same `tools/list`/`tools/call` chain in place) |
| `docker-compose.yml` — data-service env/`extra_hosts` | config | — | existing `data-service` service block env vars | role-match |
| `DG/tests/DG.Tests/CanvasListenerComponentTests.cs` | test | — | existing `DG.Tests` test conventions (see Testing note) | role-match |
| `data-service/tests/test_gh_bridge.py`, `test_app_computgraph_pull.py`, `test_mcp_gh_tools.py` | test | — | `data-service/tests/test_reasoner.py` | exact |

## Pattern Assignments

### `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` (component, event-driven/request-response)

**Analog:** `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` (full file read)

**Imports / conditional-compile guard** (lines 1-11):
```csharp
#if GRASSHOPPER_SDK
using DG.Core.Data;
using DG.Core.Models;
using DG.Core.Services;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
using System.Drawing;
using System.Security.Cryptography;
using System.Text;

namespace DG.Grasshopper.Components;
```
Copy the `#if GRASSHOPPER_SDK` guard verbatim; add `System.Net.Sockets`, `System.Text.Json`, `System.Threading`, `System.Threading.Tasks` for the listener.

**Component skeleton / fields** (lines 13-30):
```csharp
public sealed class ConnectorComponent : GH_Component
{
    private readonly INeo4jConnectorService _connectorService = new Neo4jConnectorService();
    private Task<ConnectResult>? _connectTask;
    private CancellationTokenSource? _connectCts;
    private string _activeRequestKey = string.Empty;
    ...
}
```
`CanvasListenerComponent` needs analogous fields: `TcpListener? _listener`, `Task? _acceptLoopTask`, `CancellationTokenSource? _listenerCts`, `string _activeRequestKey`, plus `Status`/`LastCommand` string fields for outputs.

**Request-key dedup pattern in `SolveInstance`** (lines 63-135, especially 95-134):
```csharp
if (!connect)
{
    CancelPendingConnection();
    _latestConnection = WithStatus(request, isConnected: false, "Connection prepared. Set Connect=true to test.");
    Message = "Idle";
}
else
{
    var requestKey = BuildRequestKey(request, dataServiceUrl, token);
    if (_connectTask is null || !string.Equals(_activeRequestKey, requestKey, StringComparison.Ordinal))
    {
        StartConnection(request, dataServiceUrl, token, requestKey);
    }
    ...
}
```
Apply identically with `requestKey = $"{Run}|{Port}"`; only `(Run, Port)` should ever change the key (per RESEARCH.md Pitfall 3 — do not key on anything else in the document).

**Disposal on both paths** (lines 143-147, 149-165):
```csharp
public override void RemovedFromDocument(GH_Document document)
{
    CancelPendingConnection();
    base.RemovedFromDocument(document);
}

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
```
`CancelPendingConnection()` becomes `StopListener()`: call `_listener?.Stop()` (unblocks pending `AcceptTcpClientAsync` and releases the port) before disposing `_listenerCts`, exactly mirroring the try/finally shape (RESEARCH.md `33-RESEARCH.md` Pattern 1, lines 208-213 quoted there).

**TCP accept loop + UI-thread marshalling — no in-repo analog, use RESEARCH.md Pattern 2 verbatim** (`33-RESEARCH.md` lines 229-257): the `InvokeOnCanvas(Func<string>)` + `TaskCompletionSource<string>` composition and `ServeClientAsync` loop are the canonical code to copy; this is the one genuinely novel subsystem in the phase (RESEARCH.md "Key insight"). Construct `StreamReader`/`StreamWriter` with `new UTF8Encoding(encoderShouldEmitUTF8Identifier: false)`, `writer.NewLine = "\n"`, and strip a leading BOM (`﻿`) from incoming lines (Pitfall 4).

**Bind to loopback only:**
```csharp
_listener = new TcpListener(IPAddress.Loopback, port);
```
Never `IPAddress.Any` — this is a hard security constraint (RESEARCH.md Security Domain, "Listener accidentally bound to 0.0.0.0").

---

### `data-service/gh_bridge.py` (service, request-response, new file)

**Analog:** `data-service/app.py` `post_reasoner_consistency` (L1192-1239) for the timeout/error-mapping *shape* (transport differs: raw `socket`, not `httpx`).

**Structured error helper — reuse, do not reinvent** (`app.py` L576-581):
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    """Return an HTTPException with a structured JSON detail body (error, hint, code)."""
    return HTTPException(
        status_code=status_code,
        detail={"error": error, "hint": hint, "code": code},
    )
```
Import this from `app.py` into `gh_bridge.py` (or extract to a shared module if a circular import results — `app.py` will itself import `gh_bridge`). Use it for the bridge-unreachable error exactly as `post_reasoner_consistency` uses it for `REASONER_TIMEOUT`/`REASONER_UNAVAILABLE` (L1221-1234).

**Timeout shape to mirror** (`app.py` L1206-1234):
```python
try:
    response = httpx.post(
        f"{DG_REASONER_URL}/reason/consistency",
        json={"project": payload.project, "engine": payload.engine},
        timeout=httpx.Timeout(connect=2.0, read=float(os.getenv("DG_REASONER_TIMEOUT_SECONDS", "90")) + 10, write=2.0, pool=2.0),
    )
except httpx.TimeoutException:
    raise _structured_error_response("Reasoner sidecar request timed out.", "The dg-reasoner sidecar is slow or unreachable. Try again later.", "REASONER_TIMEOUT", 504)
except httpx.ConnectError:
    raise _structured_error_response("Could not connect to the reasoner sidecar.", "Verify the dg-reasoner service is running.", "REASONER_UNAVAILABLE", 502)
```
Translate to `socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS)` + `sock.settimeout(READ_TIMEOUT_SECONDS)`, catching `(ConnectionRefusedError, socket.timeout, OSError)` and mapping to the CONTEXT.md-mandated message: `"Grasshopper bridge unreachable — start Rhino and enable DG CANVAS LISTENER (port 8720)"` with code `GH_BRIDGE_UNREACHABLE`, status `503`. Full composed example already in `33-RESEARCH.md` lines 358-382 — copy verbatim, it directly follows this analog.

**Env var convention** — match `DG_REASONER_URL = os.getenv(...)` style already used at top of `app.py` for `GH_BRIDGE_HOST`/`GH_BRIDGE_PORT`.

---

### `data-service/app.py` — `POST /computgraph/context/pull` (route, request-response)

**Analog:** `post_reasoner_consistency` (L1192-1239), the closest "thin proxy to an external process, Pydantic request model, single forward call" handler in the file.

**Pattern to copy** (L1192-1199 for the shape; RESEARCH.md 33-RESEARCH.md lines 389-398 for the composed target):
```python
class ReasonerConsistencyRequest(BaseModel):
    project: str
    engine: str = "hermit"


@app.post("/reasoner/consistency")
def post_reasoner_consistency(payload: ReasonerConsistencyRequest):
    """Thin proxy to the dg-reasoner sidecar's `POST /reason/consistency` (D-06)."""
    ...
```
Target:
```python
class ComputgraphContextPullRequest(BaseModel):
    project: str


@app.post("/computgraph/context/pull")
def pull_computgraph_context(payload: ComputgraphContextPullRequest):
    result = gh_bridge.get_canvas_context(payload.project)
    context = result.get("result", result)
    context["project"] = payload.project
    return context
```
Note the sync `def` (not `async def`) — matches this file's prevailing style for every route except `mcp()` itself (RESEARCH.md "Alternatives Considered").

---

### `data-service/app.py` — 4 `gh_*` tools in `/mcp` (route, request-response, extend in place)

**Analog:** `mcp()` itself (L1607-1687) — extend the exact same function, do not create a new one.

**`tools/list` extension point** (L1613-1629):
```python
if method == "tools/list":
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {"name": "neo4j_schema", "description": "..."},
                {"name": "neo4j_query", "description": "..."},
                # ADD: gh_get_context, gh_get_selection, gh_preview_structure, gh_clear_preview
            ]
        },
    }
```

**`tools/call` dispatch chain extension point** (L1649-1687):
```python
if tool_name == "neo4j_schema":
    ...
    return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": "schema"}], "data": data}}

if tool_name == "neo4j_query":
    cypher = (arguments.get("cypher") or "").strip()
    if not cypher:
        raise HTTPException(status_code=400, detail="cypher is required")
    ...
    return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": "query"}], "data": data}}

raise HTTPException(status_code=400, detail="Unknown tool name")
```
Append `if tool_name == "gh_get_context": ...`, `"gh_get_selection"`, `"gh_preview_structure"`, `"gh_clear_preview"` branches before the final `raise HTTPException(400, "Unknown tool name")`, each calling into `gh_bridge` and returning the same `{"jsonrpc": "2.0", "id": req_id, "result": {"content": [...], "data": ...}}` envelope shape. Errors from `gh_bridge` should propagate as `HTTPException`/`_structured_error_response` (already raised inside `gh_bridge`), matching the `neo4j_query` precedent of raising `HTTPException` inline rather than a JSON-RPC error object (RESEARCH.md Anti-Patterns, 4th bullet).

---

## Shared Patterns

### Structured error responses (Python)
**Source:** `data-service/app.py:576-581` (`_structured_error_response`)
**Apply to:** `gh_bridge.py` (bridge-unreachable), `app.py`'s new `gh_*` tool branches, `POST /computgraph/context/pull`
```python
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": error, "hint": hint, "code": code})
```
Do not invent a new error vocabulary — every connectivity failure in this file (`REASONER_TIMEOUT`, `REASONER_UNAVAILABLE`) already follows What+Where+How-to-fix via this helper.

### Long-lived GH_Component lifecycle: dedup + disposal
**Source:** `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` (`SolveInstance` L63-141, `RemovedFromDocument` L143-147, `StartConnection`/`CancelPendingConnection` L149-165 and the `CancelPendingConnection` body quoted in `33-RESEARCH.md` lines 208-213)
**Apply to:** `CanvasListenerComponent` — dedup on `(Run, Port)`, stop the listener in both the `Run=false` `SolveInstance` branch and `RemovedFromDocument`.

### TCP accept-loop + UI-thread marshalling (novel, no in-repo analog)
**Source:** `33-RESEARCH.md` Pattern 2 (lines 217-257), grounded in official RhinoCommon (`RhinoApp.InvokeOnUiThread`) and .NET (`TcpListener.AcceptTcpClientAsync(CancellationToken)`) docs.
**Apply to:** `CanvasListenerComponent`'s command dispatch — compute JSON on the UI thread via `InvokeOnCanvas`, write to the socket only from the background accept-loop thread. This is the phase's single highest-risk subsystem; flag for `checkpoint:human-verify` in the live-Rhino end-to-end check.

### MCP JSON-RPC extension (single server, no new abstraction)
**Source:** `data-service/app.py:1607-1687` (`mcp()`)
**Apply to:** the 4 new `gh_*` tools — append to the existing `tools/list` array and `tools/call` `if tool_name == ...` chain in the same function; do not create a second MCP server.

### Command dispatch table structured as an explicit allow-list
**Source:** RESEARCH.md constraint (CONTEXT.md: "the command dispatch should be a table that v10 can extend") + Security Domain note on Elevation of Privilege.
**Apply to:** `CanvasListenerComponent`'s C# dispatch and `gh_bridge.py`'s Python-side tool mapping — use an explicit dictionary/switch of the 5 named v9.0 commands (`get_canvas_context`, `get_selection`, `preview_structure`, `clear_preview`, `get_preview_status`), not a generic reflection-based dispatcher.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `CanvasListenerComponent.cs` TCP accept-loop body (`ServeClientAsync`, `InvokeOnCanvas`) | component (server-side socket loop) | event-driven | No `TcpListener`/`TcpClient`/raw-`Socket` server precedent exists anywhere in this codebase; `ConnectorComponent` is an HTTP/Bolt *client*, not a *server*. Use RESEARCH.md's composed Pattern 2 code (grounded in official docs) as the source of truth instead of an in-repo analog. |

## Testing Conventions (for the 4 new test files)

- **Python:** `data-service/tests/test_reasoner.py` — `TestClient(app, raise_server_exceptions=False)` + `monkeypatch` for module-level state (e.g. monkeypatching `gh_bridge.get_canvas_context` for `test_app_computgraph_pull.py`, or `socket.create_connection` for `test_gh_bridge.py`). Quick-run: `python -m pytest data-service/tests/test_gh_bridge.py -x`.
- **C#:** `DG/tests/DG.Tests/DG.Tests.csproj` (xUnit). Extract dispatch-table and dedup-key logic into plain, minimally `#if GRASSHOPPER_SDK`-guarded methods where possible so `CanvasListenerComponentTests.cs` can exercise `Dispatch`/dedup/lifecycle without a live socket — mirrors how `ComputgraphContextSerializerTests` (Phase 32) tests `DG.Core` code without the GH SDK. Quick-run: `dotnet test --filter FullyQualifiedName~CanvasListener`.

## Metadata

**Analog search scope:** `DG/src/DG.Grasshopper/Components/`, `data-service/app.py`, `data-service/tests/`
**Files scanned:** `ConnectorComponent.cs` (full), `app.py` (L570-585, 1190-1240, 1600-1690)
**Pattern extraction date:** 2026-07-13
**Note on Phase 32 dependency:** `CanvasListenerComponent`'s `get_canvas_context` handler calls `CanvasContextExtractor.SerializeContext(GH_Document, project)` (`DG.Grasshopper.Canvas`, Phase 32) — that file does not yet exist (Phase 32 unexecuted per RESEARCH.md). No pattern excerpt could be extracted from it; the planner must sequence Phase 32 first or add a precondition task, per RESEARCH.md Open Question 1.
