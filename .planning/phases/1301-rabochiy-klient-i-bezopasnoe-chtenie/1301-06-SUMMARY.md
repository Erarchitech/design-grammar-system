---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 06
subsystem: grasshopper-canvas-bridge
tags: [canvas-bridge, document-identity, busy, ui-thread, loopback, tdd]
requires: []
provides:
  - "DG.Core.Bridge.CanvasDocumentIdentity record: {documentId, filePath (null when unsaved), displayName, isModified, capturedAt}"
  - "Bridge command get_document_identity (read-only) answered by CanvasListenerComponent from the served GH document"
  - "CanvasBridgeCommands.ReadCommands: the four read-only commands (get_canvas_context, get_selection, get_preview_status, get_document_identity), the DeGram allowlist consumed by plan 11"
  - "CanvasBridgeProtocol.ErrorCodeBusy = BUSY, CanvasUiTimeoutMs = 10000"
  - "DG.Core CanvasUiWait.Await + CanvasBusyException: GH-independent bounded wait; dispatcher maps expiry to the BUSY envelope"
  - "spec/GRASSHOPPER.md section Canvas bridge"
affects: [1301-11]
tech-stack:
  added: []
  patterns:
    - "Bounded wait helper lives in DG.Core so the timeout/BUSY behaviour is unit-testable without Rhino; the GH listener only swaps its two blocking waits for it"
    - "Handlers signal BUSY by throwing CanvasBusyException; the dispatcher keeps the single never-throws envelope contract"
key-files:
  created:
    - DG/src/DG.Core/Bridge/CanvasDocumentIdentity.cs
    - DG/src/DG.Core/Bridge/CanvasUiWait.cs
    - DG/tests/DG.Tests/CanvasDocumentIdentityTests.cs
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-06-SUMMARY.md
  modified:
    - DG/src/DG.Core/Bridge/CanvasBridgeCommands.cs
    - DG/src/DG.Core/Bridge/CanvasBridgeProtocol.cs
    - DG/src/DG.Core/Bridge/CanvasCommandDispatcher.cs
    - DG/src/DG.Grasshopper/Components/CanvasListenerComponent.cs
    - spec/GRASSHOPPER.md
key-decisions:
  - "BUSY is raised as CanvasBusyException from a GH-independent CanvasUiWait and converted in CanvasCommandDispatcher (own catch before HANDLER_ERROR), rather than a per-handler envelope, so every future handler gets BUSY by using the helper"
  - "A timed-out UI delegate is not cancelled and never retried; documented in the spec that a client hitting BUSY on a mutating command must re-read state"
  - "CanvasBridgeCommands.All gains get_document_identity; PreviewStubs is unchanged"
requirements-completed: []
requirements-partial: [DGCL-04, DGCL-06]  # GH bridge half only (identity read, BUSY); picker UI, Revit side, cancel and reconnect are later plans
duration: ~25 min
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 06: GH bridge document identity and BUSY Summary

The loopback Canvas bridge now answers a read-only `get_document_identity` (documentId, filePath, displayName, isModified, capturedAt) so DeGram can pin a concrete GH document, and any UI-thread wait longer than 10 s returns a `BUSY` error envelope instead of blocking the single-client accept loop.

## What was built

- **Task 1 (tracer, 98e916a):** `CanvasDocumentIdentity` record in DG.Core (no GH dependency), the `GetDocumentIdentity` command constant, the `ReadCommands` allowlist, and `HandleGetDocumentIdentity` in `CanvasListenerComponent` (inside the existing `GRASSHOPPER_SDK` guard) which reads `DocumentID`, `FilePath`, `DisplayName`, `IsModified` through `InvokeOnCanvas`. `filePath` is `null` for an unsaved document; no active document yields a `HANDLER_ERROR`. `get_canvas_context`, `get_selection`, the preview commands and the loopback bind are untouched.
- **Task 2 (9a76729):** `ErrorCodeBusy`/`CanvasUiTimeoutMs`, `CanvasUiWait.Await` (uses the wait handle so a faulted task rethrows its original exception, not an `AggregateException`), `CanvasBusyException`, a `BUSY` catch in the dispatcher, and both `InvokeOnCanvas` (read) and `InvokeOnCanvasWrite` now use the bounded wait. spec/GRASSHOPPER.md gained a `## Canvas bridge` section: transport on 127.0.0.1:8720, read vs mutating command table, error codes (BAD_REQUEST, UNKNOWN_COMMAND, HANDLER_ERROR, BUSY), the read-only guarantee of `get_document_identity`, "DeGram sends read commands only" (D-15) and the unauthenticated loopback trust boundary.

## TDD

RED observed for both tasks (test project did not compile: missing `CanvasDocumentIdentity`, `GetDocumentIdentity`, `ReadCommands`, then `ErrorCodeBusy`, `CanvasUiTimeoutMs`, `CanvasBusyException`, `CanvasUiWait`). GREEN: 30/30 in the filter `CanvasBridge|CanvasDocumentIdentity` (11 existing dispatcher tests plus 19 new/related).

## Verification

- `dotnet build .\DG\DG.sln -c Release`: 0 warnings, 0 errors. Rhino 8 SDK is installed on this machine, so `DG.Grasshopper` compiled with `GRASSHOPPER_SDK` and the new listener code was type-checked against the real SDK.
- `dotnet test .\DG\tests\DG.Tests\`: 716 passed, 4 failed, 720 total. The 4 failures are exactly the known Neo4j-dependent `DesignStateValidationFlowTests` (LegacyNoState_FlowStillWorks, ReinstateFailureModes_ProduceActionableMessages, Filtering_StateAndRule, HappyPath_StatePublishAndRetrieve); no other failure.
- Not run: a live Rhino/Grasshopper session (forbidden here). The listener handler and the BUSY wiring in the GH component are compile-verified only; the BUSY and identity logic is unit-tested in Core. A live check (identity of a saved and an unsaved document; a modal dialog producing BUSY) belongs to the later GH adapter / UAT plans.

## Deviations from Plan

None. The plan listed `CanvasBridgeDispatcherTests.cs` among Task 1 files; it needed no change (all 11 existing tests pass unchanged), and the new tests live in `CanvasDocumentIdentityTests.cs`.

## Threat model

- T-1301-06-01 (UI-thread hang, mitigate): bounded 10 s wait to BUSY, covered by `Await_NeverCompletingTask_Throws_CanvasBusyException_After_Timeout` and `Dispatcher_Handler_Waiting_On_Stuck_Ui_Task_Returns_Busy_Envelope`.
- T-1301-06-02 and -03 accepted as planned; recorded in the spec Trust boundary paragraph.

## Requirements

DGCL-04 and DGCL-06 are only partly delivered here (GH identity read and BUSY outcome). They were deliberately NOT marked complete in REQUIREMENTS.md: the document picker, Revit adapter, cancel/reconnect lifecycle belong to later 1301 plans.

## Notes for downstream plans

- Plan 11 (DeGram GH adapter) should allowlist `CanvasBridgeCommands.ReadCommands` (mirror the four names; the Python side cannot import the C# constant) and treat `error.code == "BUSY"` as retryable.
- Residual: a timed-out UI delegate may still run later; harmless for reads.
- Environment: DG/src/*/bin and obj are tracked in this repo and show as modified after every build; none were staged (staged only the plan's files).

## Known Stubs

None.

## Threat Flags

None. No new network surface; the new command is read-only on the existing loopback socket.

## Commits

- 98e916a feat(1301-06): get_document_identity read command on the GH bridge
- 9a76729 feat(1301-06): bounded UI-thread wait reports BUSY on the GH bridge

## Self-Check: PASSED
