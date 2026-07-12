# Phase 33 Context: DG Canvas Bridge (grasshopper-mcp adaptation)

**Milestone:** v9.0 AI Workflow Intelligence (restructured 2026-07-08)
**Requirements:** BRDG-01..04
**Depends on:** Phase 32 (serves `cgContextJson v1`). Parallel-safe with Phase 34.

## What this phase is

The transport between the live Grasshopper canvas (Rhino on the Windows host) and data-service (Docker): a native re-implementation of the [grasshopper-mcp](https://github.com/alfredatnycu/grasshopper-mcp) bridge pattern inside the DG plugin, plus the data-service client and `gh_*` MCP tools. Protocol details in [../32-computgraph-serialization-core/32-RESEARCH.md](../32-computgraph-serialization-core/32-RESEARCH.md) §1.

## Decided

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

## Constraints

- Localhost bind only; the bridge carries design IP — never expose beyond the machine.
- The listener is *pull-based* for context (data-service asks); no unsolicited pushes in v9.0.
- **Write commands (`add_component`, `connect_components`, document mutation) are out of scope** — deferred to v10 (`.planning/milestones/v10.0-SEED.md`). The command dispatch should be a table that v10 can extend.
- Protocol/version handshake: responses include `{"bridge": "dg", "version": 1}` so future clients can detect capabilities.
- No secrets over the bridge; no LLM calls in this phase.

## Open for planning

- Threading model detail: dedicated thread + `CancellationToken` vs async accept loop; how Grasshopper solution expiry interacts with a long-lived listener component.
- Whether `get_canvas_context` triggers a fresh solve or reads current state (read current — but confirm slider values are current without solve).
- Health command (`ping`) for the data-service `/computgraph/context/pull` pre-check.

## Verification sketch

Rhino open + listener on → `curl -X POST :8000/computgraph/context/pull` inside the compose network returns the Frame `cgContextJson`; listener off → actionable 503-style error, no hang; `tools/list` on `/mcp` shows the four `gh_*` tools.
