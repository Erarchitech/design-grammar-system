---
phase: 824-connector-credential-integration
plan: 01
subsystem: grasshopper
tags: [csharp, dotnet, httpclient, connector-auth, dg-core, xunit]

requires:
  - phase: 810-816 (v8.1 Connectors)
    provides: data-service POST /connectors/heartbeat (Bearer dgc_ token → 200/401), connector credential registry
provides:
  - DG.Core ConnectorHeartbeatClient (injectable, timeout-bounded) mapping the heartbeat contract to HeartbeatResult
  - HeartbeatOutcome enum + token-free HeartbeatResult record struct
  - ErrorMessageTemplates.ConnectorTokenRejected() + ConnectorHeartbeatUnreachable(url)
affects: [824-02, connector, grasshopper]

tech-stack:
  added: [System.Net.Http in DG.Core]
  patterns: ["Injectable HttpMessageHandler for unit-testable HTTP client (mirrors Neo4jConnectorService testability + ValidationPublishClient URL handling)"]

key-files:
  created:
    - DG/src/DG.Core/Models/HeartbeatResult.cs
    - DG/src/DG.Core/Data/IConnectorHeartbeatClient.cs
    - DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs
    - DG/tests/DG.Tests/ConnectorHeartbeatClientTests.cs
  modified:
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs

key-decisions:
  - "Heartbeat logic lives in DG.Core (not DG.Grasshopper) so it compiles + unit-tests without the Rhino SDK — the GH components are excluded from DG.Tests"
  - "Non-dgc_ token short-circuits to Rejected with no network call (mirrors backend prefix guard)"
  - "Any non-200/non-401 status or network exception maps to Unreachable (transient); only 401 is Rejected"

patterns-established:
  - "StubHttpMessageHandler nested test double for HttpClient outcome-matrix tests"

requirements-completed: [CONNG-02]

coverage:
  - id: D1
    description: "ConnectorHeartbeatClient maps 200→Authenticated (with Bearer header + /connectors/heartbeat endpoint), 401→Rejected, 500/network/timeout→Unreachable, non-dgc_ token→Rejected (no call), empty→NotAttempted (no call)"
    requirement: "CONNG-02"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ConnectorHeartbeatClientTests.cs (6 facts)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ErrorMessageTemplates.ConnectorTokenRejected() + ConnectorHeartbeatUnreachable(url) render What+Where+How-to-fix house-style strings"
    requirement: "CONNG-02"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ErrorMessageTemplateTests.cs (2 facts)"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-07-12
status: complete
---

# Phase 824 / Plan 01: DG.Core Heartbeat Client + Templates Summary

**Injectable, timeout-bounded `ConnectorHeartbeatClient` that maps data-service's `/connectors/heartbeat` contract to a token-free `HeartbeatResult`, plus two house-style connector error templates — all unit-tested without the Rhino SDK.**

## Performance
- **Duration:** ~15 min
- **Completed:** 2026-07-12
- **Tasks:** 4
- **Files modified:** 6 (4 created, 2 edited)

## Accomplishments
- `HeartbeatOutcome` (NotAttempted/Authenticated/Rejected/Unreachable) + `HeartbeatResult` record struct that deliberately carries no sensitive value.
- `ConnectorHeartbeatClient` posts `Authorization: Bearer <token>` to `{url}/connectors/heartbeat` with a 6s timeout; maps 200→Authenticated (parsing `status`), 401→Rejected, everything else/exception/timeout→Unreachable; short-circuits non-`dgc_` tokens to Rejected with no network call; skips empty tokens (NotAttempted). Constructor accepts an injectable `HttpMessageHandler` for tests.
- `ErrorMessageTemplates.ConnectorTokenRejected()` + `ConnectorHeartbeatUnreachable(url)`.
- 8 new tests (6 client + 2 templates); full suite **234/234 passing**.

## Files Created/Modified
- `DG/src/DG.Core/Models/HeartbeatResult.cs` — outcome enum + token-free result
- `DG/src/DG.Core/Data/IConnectorHeartbeatClient.cs` / `ConnectorHeartbeatClient.cs` — the client
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — two connector-auth templates
- `DG/tests/DG.Tests/ConnectorHeartbeatClientTests.cs` — outcome-matrix tests + `StubHttpMessageHandler`
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` — template tests

## Decisions Made
- Core-side placement for testability (GH components aren't compiled into DG.Tests).
- Token confined to the Authorization header — never logged, never on `HeartbeatResult`.

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
None.

## Next Phase Readiness
Plan 02 (component wiring) consumes `ConnectorHeartbeatClient` + the two templates. Ready.

---
*Phase: 824-connector-credential-integration*
*Completed: 2026-07-12*
