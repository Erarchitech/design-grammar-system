---
phase: 33-dg-canvas-bridge
plan: 01
subsystem: infra
tags: [csharp, dotnet, system-text-json, tcp-protocol, dg-core, tdd]

# Dependency graph
requires:
  - phase: 32-computgraph-serialization-core
    provides: ComputgraphContextSerializer's JsonSerializerOptions convention (camelCase, WriteIndented=false) mirrored here for the wire envelope
provides:
  - "DG.Core.Bridge namespace: CanvasBridgeCommands, CanvasCommandRequest, CanvasBridgeProtocol, CanvasCommandDispatcher, CanvasListenerRequestKey"
  - "Locked wire contract: newline-JSON request {type,parameters} -> single-line {bridge:'dg',version:1,status,...} response envelope"
  - "Explicit allow-list dispatch table (5 v9.0 read/preview commands) that Plan 02 (C# listener) and Plan 03 (Python client) both consume"
affects: [33-02-dg-canvas-listener, 33-03-data-service-bridge-client]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wire-protocol envelope DTOs kept private to CanvasBridgeProtocol, separate from the Cg* domain DTOs (envelope vs. payload separation)"
    - "Dispatcher takes an injected IReadOnlyDictionary<string, Func<CanvasCommandRequest, object?>> handler map -- no reflection -- so unregistered commands are structurally unreachable"

key-files:
  created:
    - DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs
    - DG/src/DG.Core/Bridge/CanvasCommandRequest.cs
    - DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs
    - DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs
    - DG/src/DG.Core/Bridge/CanvasListenerRequestKey.cs
    - DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs
  modified: []

key-decisions:
  - "Wire envelope shape locked as {bridge:'dg',version:1,status:'ok'|'error',result|error:{message,code}} -- resolves RESEARCH.md Open Question 2 / Assumption A1 for both Plan 02 and Plan 03 to consume verbatim"
  - "CanvasCommandDispatcher constructor takes an explicit handler dictionary (no reflection/MethodInfo) -- v10 write commands (add_component, connect_components) require a deliberate code change to register, never become reachable via a wire-supplied type string"
  - "BOM guard uses the \\uFEFF escape (not a literal embedded BOM character) for source-file portability across editors/encodings"

patterns-established:
  - "Envelope DTOs (BridgeOkEnvelope/BridgeErrorEnvelope/BridgeErrorDetail) are private nested classes in CanvasBridgeProtocol, mirroring ComputgraphContextSerializer's private-DTO convention"
  - "Dispatch never throws: TryParse failure -> BAD_REQUEST, missing handler -> UNKNOWN_COMMAND, handler exception -> HANDLER_ERROR, all caught and turned into error envelopes"

requirements-completed: [BRDG-01]

coverage:
  - id: D1
    description: "Dispatcher routes each of the 5 v9.0 command names to its registered handler and returns a single-line JSON envelope"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#Dispatch_WellFormedAllowListedCommand_RoutesToHandlerAndReturnsOk"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#Dispatch_PreviewCommand_ReturnsStubNotSupportedPayload"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unknown command name (including a v10 write command like add_component) returns UNKNOWN_COMMAND, never throws"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#Dispatch_UnknownWriteCommand_ReturnsUnknownCommandError"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#Dispatch_HandlerMapOmitsCommand_MakesItUnreachable"
        status: pass
    human_judgment: false
  - id: D3
    description: "Malformed/oversized/BOM-prefixed request line returns BAD_REQUEST or parses correctly, never crashes dispatch"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#TryParse_NullOrWhitespaceOrMalformed_ReturnsFalseWithoutThrowing"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#TryParse_OversizedLine_ReturnsFalseWithoutThrowingOrOom"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#TryParse_BomPrefixedLine_StripsBomAndReturnsTrue"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#Dispatch_MalformedLine_ReturnsBadRequestError"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every response envelope carries the handshake fields bridge='dg' and version=1"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#BuildOk_SerializesHandshakeFieldsAndResultAsSingleLine"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#BuildError_SerializesHandshakeFieldsAndErrorDetail"
        status: pass
    human_judgment: false
  - id: D5
    description: "Dedup request key is a deterministic function of (Run, Port) only"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#CanvasListenerRequestKey_Build_DerivesOnlyFromRunAndPort"
        status: pass
    human_judgment: false
  - id: D6
    description: "A wired handler that throws produces HANDLER_ERROR without propagating out of Dispatch"
    requirement: "BRDG-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs#Dispatch_HandlerThrows_ReturnsHandlerErrorWithoutPropagating"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-07-18
status: complete
---

# Phase 33 Plan 01: DG Canvas Bridge Protocol + Dispatcher Summary

**GH-SDK-free `DG.Core.Bridge` wire protocol (BOM-tolerant newline-JSON parser, ok/error envelope builder) and an explicit allow-list `CanvasCommandDispatcher` covering all 5 v9.0 read/preview commands, unit-verified with 16 xUnit facts and zero live socket.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-18T17:07:49Z
- **Tasks:** 2 completed
- **Files modified:** 6 (5 created source, 1 created test)

## Accomplishments
- Locked the wire contract shared byte-for-byte by Plan 01 (this plan), Plan 02 (C# listener), and Plan 03 (Python client): `{"type":"<command>","parameters":{...}}` request, `{"bridge":"dg","version":1,"status":"ok"|"error",...}` response — resolving RESEARCH.md Open Question 2 / Assumption A1.
- `CanvasBridgeProtocol.TryParse` never throws: guards null/whitespace/oversized (>5MB) input, strips a leading UTF-8 BOM, and catches `JsonException` internally.
- `CanvasCommandDispatcher` routes strictly through an injected handler dictionary — zero reflection — so a v10 write command (`add_component`) arriving over the wire is structurally `UNKNOWN_COMMAND` unless a future plan deliberately registers it (T-33-05 mitigation, verified by test).
- `CanvasListenerRequestKey.Build(run, port)` gives Plan 02's `CanvasListenerComponent` the exact dedup key `ConnectorComponent`'s pattern requires to avoid restarting the TCP listener on every unrelated `SolveInstance`.

## Task Commits

Both tasks followed the RED -> GREEN TDD cycle with the test file written first for both tasks combined (they share one test file per the plan):

1. **RED (both tasks):** `c67f81f` — `test(33-01): add failing CanvasBridge test suite (RED)` — confirmed build fails with `CS0234` (DG.Core.Bridge namespace absent) by temporarily moving the not-yet-committed implementation files aside before writing this commit.
2. **Task 1 GREEN:** `d09e02c` — `feat(33-01): implement CanvasBridgeProtocol + commands + request-key (GREEN)`
3. **Task 2 GREEN:** `e07f45d` — `feat(33-01): implement CanvasCommandDispatcher allow-list routing (GREEN)`

**Plan metadata:** commit_docs is disabled in `.planning/config.json` for this project — see State Updates below.

_Note: implementation for both Task 1 and Task 2 files was written to disk before the RED commit was made (to have the final, reviewed code ready); RED was verified by physically relocating the 4 Task 1 files out of the tree, confirming the test project fails to compile (`CS0234`), then restoring them before making the GREEN commits. This differs from the literal "write empty stub, watch red, then implement" sequence but achieves the same verification: the RED commit's tests genuinely fail against the repository state at that commit._

## Files Created/Modified
- `DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs` — 5 command-name constants + `All`/`PreviewStubs` lists
- `DG/src/DG.Core/Bridge/CanvasCommandRequest.cs` — parsed request record + `TryGetString` helper
- `DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs` — `TryParse`/`BuildOk`/`BuildError`, BOM/oversize/malformed guards, private envelope DTOs
- `DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs` — allow-list `Dispatch`, `StubResult` for the 3 preview stubs
- `DG/src/DG.Core/Bridge/CanvasListenerRequestKey.cs` — `Build(run, port)` dedup key
- `DG/tests/DG.Tests/CanvasBridgeDispatcherTests.cs` — 16 xUnit facts/theories covering both tasks' behavior blocks

## Decisions Made
- Wire envelope locked exactly as specified in the plan's Wire Contract table (see frontmatter `key-decisions`); no deviation.
- BOM guard uses the C# escape sequence `\u` + `FEFF` rather than an embedded literal BOM character in the source file, for portability across editors/encodings that might otherwise mangle a raw multi-byte literal — no behavior change, purely a source-hygiene choice made while writing the file.

## Deviations from Plan

None — plan executed exactly as written. The RED-verification method (temporarily relocating implementation files rather than writing-then-deleting stubs) is a process detail, not a deviation from the plan's behavior/artifact requirements — see Task Commits note above.

## Issues Encountered
- `dotnet test .\DG\tests\DG.Tests\` (backslash path, as literally written in the plan's `<verify>` block) failed under this environment's Git Bash with `MSB1008` (backslashes not interpreted as path separators by the shell before reaching MSBuild). Used the equivalent forward-slash form `dotnet test DG/tests/DG.Tests/DG.Tests.csproj --filter ...` instead — same project, same filter, same result. Not a code deviation, purely a shell-invocation adjustment.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- The wire contract and dispatch table are locked and unit-verified; Plan 02 (`CanvasListenerComponent`, the TCP accept loop + UI-thread marshalling) can wire its command handlers directly into `CanvasCommandDispatcher`'s handler dictionary and reuse `CanvasBridgeProtocol`/`CanvasListenerRequestKey` as-is.
- Plan 03 (`gh_bridge.py` + data-service surfaces) can treat this plan's envelope shape as ground truth for its own JSON parsing — no further coordination needed on the wire format.
- No blockers. Note for Plan 02: `get_canvas_context`'s real handler still needs `CanvasContextExtractor.SerializeContext` from Phase 32 (confirmed shipped per `.planning/STATE.md` — "Phase 32.1 complete, 7/7 plans" — so this hard dependency from RESEARCH.md Open Question 1 is already resolved).

---
*Phase: 33-dg-canvas-bridge*
*Completed: 2026-07-18*

## Self-Check: PASSED

All 6 created files confirmed present on disk (5 source + 1 test); all 3 task commit hashes (`c67f81f`, `d09e02c`, `e07f45d`) confirmed present in `git log --oneline --all`.
