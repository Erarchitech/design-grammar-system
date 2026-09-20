---
phase: 33-dg-canvas-bridge
plan: 02
subsystem: grasshopper-plugin
tags: [tcp-listener, grasshopper, ui-thread-marshalling, canvas-bridge, rhinocommon]

# Dependency graph
requires:
  - phase: 33-01
    provides: CanvasBridgeProtocol (newline-JSON envelope), CanvasCommandRequest, CanvasBridgeCommands (5-command allow-list), CanvasCommandDispatcher (handler-map routing), CanvasListenerRequestKey
  - phase: 32
    provides: CanvasContextExtractor.SerializeContext (GH_Document -> cgContextJson v1 string)
provides:
  - CanvasListenerComponent (DG CANVAS LISTENER) - long-lived GH_Component hosting a loopback-only TcpListener
  - single-client accept-loop-plus-UI-thread-marshalling pattern (first in-repo precedent for this shape)
  - DgIcons.CanvasListener24 icon accessor
affects: [33-04 (in-Rhino live verification checkpoint), 33-03 (gh_bridge.py Python client connects to this listener)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TCP-accept-loop-plus-UI-thread-marshalling: background Task hosts TcpListener.AcceptTcpClientAsync loop; canvas reads run inside RhinoApp.InvokeOnUiThread via a TaskCompletionSource bridge, the socket write always stays on the background thread"
    - "Dedup-on-(Run,Port) lifecycle mirrors ConnectorComponent's StartConnection/CancelPendingConnection try/finally shape, applied to a listener instead of a connection task"

key-files:
  created:
    - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
  modified:
    - DG/src/DG.Grasshopper/DgIcons.cs

key-decisions:
  - "New ComponentGuid B0F26347-BB77-4593-A192-7BC3B0BC6169 assigned (verified unique via repo-wide grep before use)"
  - "Input names Run/Go and Port/Port mirror ConnectorComponent's Connect/Go trigger-button convention"
  - "BOM strip implemented as (char)0xFEFF cast rather than a \\uFEFF literal char, to avoid embedding an actual invisible Unicode codepoint in source"
  - "No bundled icon artwork for CanvasListener24 - DgIcons.Load's existing Phase 19 fallback (24x24 pink/red-X placeholder bitmap) covers it"

patterns-established:
  - "Pattern 2 (InvokeOnCanvas/ServeClientAsync composition) from 33-RESEARCH.md implemented as: TaskCompletionSource<object?> + RhinoApp.InvokeOnUiThread for reads, all socket I/O (ReadLineAsync/WriteLineAsync) on the background accept-loop thread"

requirements-completed: [BRDG-01, BRDG-04]

coverage:
  - id: D1
    description: "DG CANVAS LISTENER component compiles, binds 127.0.0.1 only (never 0.0.0.0), and dedups the listener lifecycle on (Run,Port)"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "dotnet build DG/DG.sln -c Release (0 warnings, 0 errors, GRASSHOPPER_SDK branch confirmed compiled via /define: flag)"
        status: pass
      - kind: other
        ref: "source assertion: grep confirms IPAddress.Loopback used, zero IPAddress.Any references; SolveInstance gates StartListener behind CanvasListenerRequestKey.Build(...) comparison"
        status: pass
    human_judgment: false
  - id: D2
    description: "Listener lifecycle disposes cleanly on both Run=false and RemovedFromDocument (no port leak across on/off cycles)"
    requirement: "BRDG-04"
    verification:
      - kind: other
        ref: "source assertion: StopListener() invoked from SolveInstance's !run branch (line 74) and from RemovedFromDocument override (line 92)"
        status: pass
    human_judgment: true
    rationale: "Static source assertion confirms the call sites exist; the actual repeated on/off port-leak behavior requires a live Rhino/Grasshopper session and is explicitly deferred to the Plan 04 in-Rhino checkpoint per RESEARCH.md Environment Availability."
  - id: D3
    description: "All 5 wire-protocol commands route through Plan 01's CanvasCommandDispatcher; get_canvas_context/get_selection marshal canvas reads onto the UI thread while the socket write stays on the background thread"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ --filter FullyQualifiedName~CanvasBridge (16/16 pass, Plan 01 regression)"
        status: pass
      - kind: other
        ref: "source assertion: WriteLineAsync call site (line 295) is outside the RhinoApp.InvokeOnUiThread delegate (line 155); get_canvas_context handler calls CanvasContextExtractor.SerializeContext inside InvokeOnCanvas"
        status: pass
    human_judgment: true
    rationale: "Live socket round-trip and UI-responsiveness during a real canvas read are environment-gated to the Plan 04 in-Rhino checkpoint (RESEARCH.md Assumption A3) - cannot be exercised in CI."

# Metrics
duration: 20min
completed: 2026-07-18
status: complete
---

# Phase 33 Plan 02: DG Canvas Listener Component Summary

**DG CANVAS LISTENER component hosts a loopback-only TcpListener with a single-client accept loop, delegating all wire-protocol routing to Plan 01's CanvasCommandDispatcher and marshalling canvas reads onto Rhino's UI thread via RhinoApp.InvokeOnUiThread.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-18T17:34:19Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- `CanvasListenerComponent` (`DG CANVAS LISTENER`): a `GH_Component` that binds `new TcpListener(IPAddress.Loopback, port)` — never `IPAddress.Any` — with inputs `Run`/`Go` (bool, default false) and `Port` (int, default 8720), outputs `Status` and `LastCommand`
- Lifecycle mirrors `ConnectorComponent` exactly: `SolveInstance` dedups on `CanvasListenerRequestKey.Build(run, port)`, `StopListener()` runs from both the `Run=false` branch and `RemovedFromDocument`, all disposal is try/catch/finally best-effort
- Single-client accept loop (`RunAcceptLoopAsync`) accepts one `TcpClient` at a time via `AcceptTcpClientAsync(ct)`, sets a 30s `ReceiveTimeout`, and fully serves each client before accepting the next; a per-client try/catch logs to `_status` and continues the loop so one bad client cannot kill the listener
- `ServeClientAsync` frames the wire protocol per spec: no-BOM UTF-8 (`UTF8Encoding(encoderShouldEmitUTF8Identifier: false)`), `StreamWriter.NewLine = "\n"`, `AutoFlush = true`; strips a leading BOM via `(char)0xFEFF` before dispatch
- All 5 commands wired through a single dispatcher instance built once in the constructor: `get_canvas_context` and `get_selection` run their canvas read inside `InvokeOnCanvas` (blocks the background thread on a `TaskCompletionSource`, runs the work on `RhinoApp.InvokeOnUiThread`); the 3 preview commands (`preview_structure`, `clear_preview`, `get_preview_status`) route to `CanvasCommandDispatcher.StubResult`
- `get_canvas_context` returns `CanvasContextExtractor.SerializeContext(OnPingDocument(), project)` parsed via `JsonNode.Parse` so `BuildOk` embeds it as a nested JSON object, not a quoted string
- New `DgIcons.CanvasListener24` accessor added (no bundled artwork — falls back to the existing Phase 19 placeholder bitmap)
- Fresh `ComponentGuid` `B0F26347-BB77-4593-A192-7BC3B0BC6169`, confirmed unique via repo-wide grep before assignment

## Task Commits

1. **Task 1: CanvasListenerComponent — TcpListener host, accept loop, UI-thread marshalling, lifecycle** - `8f46237` (feat)

**Plan metadata:** (this commit, following)

## Files Created/Modified
- `DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs` - the DG CANVAS LISTENER component: TcpListener host, accept loop, dispatcher wiring, UI-thread marshalling, lifecycle
- `DG/src/DG.Grasshopper/DgIcons.cs` - added `CanvasListener24` icon accessor

## Decisions Made
- Input port naming follows `ConnectorComponent`'s `Connect`/`Go` trigger-button convention: `Run`/`Go` for the boolean, `Port`/`Port` for the integer
- BOM strip in `ServeClientAsync` uses `line[0] == (char)0xFEFF` rather than a raw BOM character literal — avoids embedding an actual invisible Unicode BOM codepoint in the source file (flagged by the injection scanner as a low-severity invisible-unicode pattern during drafting; resolved before commit, no functional change)
- `_status`/`_lastCommand` are `volatile string` fields (not locked) — sufficient for single-writer (accept-loop thread) / single-reader (SolveInstance on UI thread) visibility per the plan's "volatile or guarded" guidance
- `ScheduleRefresh()` (via `OnPingDocument()?.ScheduleSolution(1, _ => ExpireSolution(false))`) is called after every served request, not just on connect/disconnect, so `Status`/`LastCommand` outputs refresh on the canvas after each bridge round-trip — extends `ConnectorComponent`'s single post-connect `ContinueWith` refresh to the recurring per-request case, appropriate for a long-lived listener rather than a one-shot connect

## Deviations from Plan

None - plan executed exactly as written. The BOM-strip literal was drafted, then hardened to avoid an invisible-Unicode source-scanner flag before the task commit — not a deviation from the plan's intent (still "strip a leading U+FEFF from the line"), just a safer literal representation.

## Issues Encountered
- The build tool's Windows-style path (`.\DG\DG.sln`) failed under the Bash tool's POSIX shell (`MSB1009: file does not exist`) — resolved by using the forward-slash equivalent (`DG/DG.sln`), same file, no plan or code impact.
- Confirming the `#if GRASSHOPPER_SDK` branch (not the `#else` stub) actually compiled required checking that `C:\Program Files\Rhino 8\System\RhinoCommon.dll` exists locally (it does) and inspecting the `csc.exe` invocation's `/define:` flags directly, since the plan's `dotnet build` verification alone doesn't distinguish which branch compiled.

## Next Phase Readiness
- `CanvasListenerComponent` is ready for Plan 04's in-Rhino live verification: live socket round-trip (Python `gh_bridge.py` client from Plan 03 connecting on port 8720), repeated on/off port-leak check, and UI-responsiveness during a real `get_canvas_context`/`get_selection` call — all explicitly deferred per RESEARCH.md Environment Availability (cannot run in CI)
- No blockers for Plan 03 (already shipped, ships the client side of this exact wire contract) or Plan 04

## Self-Check: PASSED

- FOUND: DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
- FOUND: DG/src/DG.Grasshopper/DgIcons.cs
- FOUND: .planning/milestones/v9.0-phases/33-dg-canvas-bridge/33-02-SUMMARY.md
- FOUND: commit 8f46237

---
*Phase: 33-dg-canvas-bridge*
*Completed: 2026-07-18*
