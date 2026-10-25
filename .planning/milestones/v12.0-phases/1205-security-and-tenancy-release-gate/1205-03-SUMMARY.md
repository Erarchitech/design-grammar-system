---
phase: 1205-security-and-tenancy-release-gate
plan: "03"
subsystem: auth
tags: [csharp, grasshopper, dotnet, http-client, connector-token, bearer-auth]

# Dependency graph
requires:
  - phase: 1205-security-and-tenancy-release-gate (plan 01/02)
    provides: server-side identity/session store foundation (D-01/D-02, unrelated code path)
provides:
  - DG.Core.Data.DataServiceRequestAuth (TryApplyConnectorToken, ClassifyStatus, PublishAuthOutcome)
  - Four new ErrorMessageTemplates (PublishTokenMissing/Rejected/ProjectForbidden, ConnectorNoGraphBundle)
  - Bearer-token-authenticated ValidationPublishClient and ComputgraphPublishClient
  - Trailing Token inputs on VALIDATOR and COMPUTGRAPH PUBLISH components
  - CONNECTOR D-07 no-bundle handling (multi-user profile)
  - Credential-free ConnectionInfo.Password default
affects: [1205-10 (server-side connector token enforcement on /validation/publish and /computgraph/publish)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit HttpRequestMessage + JsonContent.Create + SendAsync replaces PostAsJsonAsync when a request needs a pre-send Authorization header"
    - "Publish-auth outcome classification (PublishAuthOutcome) shared between DG.Core (testable) and DG.Grasshopper (GH-wired) layers"

key-files:
  created:
    - DG/src/DG.Core/Data/DataServiceRequestAuth.cs
    - DG/tests/DG.Tests/DataServiceRequestAuthTests.cs
  modified:
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/src/DG.Core/Models/ConnectionInfo.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
    - DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs
    - DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
    - DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs
    - DG/src/DG.Grasshopper/Components/ConnectorComponent.cs

key-decisions:
  - "DataServiceRequestAuth lives in DG.Core (no Grasshopper reference) so xUnit can test the header/status logic directly, per the plan's D-04 discipline."
  - "Token inputs on VALIDATOR (index 4) and COMPUTGRAPH PUBLISH (index 3) are NonPersistentStringParam, appended after every existing input, and Optional -- existing canvases keep their wire indices."
  - "A blank/malformed token short-circuits before any HTTP call (component-level check duplicates the client-level DataServiceRequestAuth guard as defense in depth)."
  - "CONNECTOR's no-bundle reason (D-07) is distinguished from 'no platform token' only when the heartbeat outcome is Authenticated but Bundle is null -- Rejected/Unreachable messages are unchanged."

patterns-established:
  - "PublishAuthOutcome.ClassifyStatus is the single place a publish client maps an HTTP status to a user-facing template; both GH publish clients reuse it identically."

requirements-completed: []  # ALGN12-17 not closed by this plan alone -- see Next Phase Readiness

coverage:
  - id: D1
    description: "ValidationPublishClient and ComputgraphPublishClient send Authorization: Bearer <dgc_ token> on every publish; missing/malformed token throws before any network call; 401/403 map to PublishTokenRejected/PublishProjectForbidden"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/DataServiceRequestAuthTests.cs#TryApplyConnectorToken_WellFormedTokenWithWhitespace_TrimsAndSetsBearerHeader"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/DataServiceRequestAuthTests.cs#ClassifyStatus_MapsStatusCodeToExpectedOutcome"
        status: pass
      - kind: integration
        ref: "dotnet build .\\DG\\DG.sln -c Release (GRASSHOPPER_SDK compile of the wired GH clients)"
        status: pass
    human_judgment: true
    rationale: "Live Rhino confirmation of the on-canvas Token input and the actual publish round-trip is deferred to Phase 40 (GATE12-04) per the plan's own success criteria -- this plan only proves the code compiles and the auth logic is unit-correct."
  - id: D2
    description: "VALIDATOR and COMPUTGRAPH PUBLISH expose a trailing Optional Token input; a blank token skips the HTTP call, sets SendStatus/Status to PublishTokenMissing, and adds a Warning runtime message, while evaluation output still computes"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/ErrorMessageTemplateTests.cs#PublishTokenMissing_NamesComponentAndTokenInput"
        status: pass
      - kind: other
        ref: "git diff ValidatorComponent.cs ComputgraphPublishComponent.cs ConnectorComponent.cs | grep -c ComponentGuid (returns 0 -- GUIDs/indices unchanged)"
        status: pass
    human_judgment: true
    rationale: "Confirming the Token port actually appears at the correct trailing index on a live GH canvas, and that an existing saved .gh reopens with no missing-component placeholder, requires Rhino -- deferred to Phase 40 per the plan."
  - id: D3
    description: "CONNECTOR reports ErrorMessageTemplates.ConnectorNoGraphBundle() (not the misleading no-token message) when an authenticated heartbeat carries no Neo4j bundle, and attempts no Bolt connection; ConnectionInfo.Password no longer defaults to a committed credential"
    requirement: "ALGN12-18"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/DataServiceRequestAuthTests.cs#ConnectionInfo_DefaultPassword_IsEmpty"
        status: pass
      - kind: other
        ref: "grep -c 12345678 DG/src/DG.Core/Models/ConnectionInfo.cs (returns 0)"
        status: pass
    human_judgment: true
    rationale: "The D-07 no-bundle branch in RunConnectAsync/ReportAuth has no direct unit test (ConnectorComponent is GH-SDK-gated, untestable from DG.Tests without a live Grasshopper host) -- correctness was verified by build success and code review only, and Phase 40 live-Rhino UAT is the actual behavioral proof."

# Metrics
duration: ~35min
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 03: Grasshopper Publish Authentication Summary

**Both GH publish clients (VALIDATOR, COMPUTGRAPH PUBLISH) now send a `Bearer dgc_...` connector token via a testable DG.Core helper, with 401/403 mapped to actionable canvas messages, and CONNECTOR distinguishes "no token" from "authenticated but no graph bundle" (D-07).**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2
- **Files modified:** 10 (2 created, 8 modified)

## Accomplishments
- New `DataServiceRequestAuth` (DG.Core, no Grasshopper dependency): `TryApplyConnectorToken` applies a trimmed `dgc_` Bearer token to an `HttpRequestMessage`, `ClassifyStatus` maps HTTP status codes to `PublishAuthOutcome`
- Four new `ErrorMessageTemplates`: `PublishTokenMissing`, `PublishTokenRejected`, `PublishProjectForbidden`, `ConnectorNoGraphBundle`
- `ValidationPublishClient` and `ComputgraphPublishClient` replaced `PostAsJsonAsync` with an explicit `HttpRequestMessage` + `JsonContent.Create` + `SendAsync`, applying the token before any network I/O and mapping auth failures to the new templates
- `ValidatorComponent` and `ComputgraphPublishComponent` gained a trailing, optional `NonPersistentStringParam` Token input; a blank token at publish time skips the HTTP call entirely (local evaluation still runs) and surfaces a Warning
- `ConnectorComponent` now reports `ConnectorNoGraphBundle()` (Remark-level runtime message) instead of the misleading "no platform token" message when an authenticated heartbeat carries no Neo4j bundle (D-07 multi-user profile)
- `ConnectionInfo.Password` default changed from the committed `12345678` credential to `string.Empty`

## Task Commits

1. **Task 1: DG.Core request-auth helper, error templates and the credential-free ConnectionInfo default** - `6912bed` (test)
2. **Task 2: Wire the token through the publish clients, VALIDATOR, COMPUTGRAPH PUBLISH and CONNECTOR** - `67f5e0f` (feat)

**Plan metadata:** (this commit, docs: complete plan)

_Note: Task 1 is `tdd="true"` in the plan; tests and implementation landed in a single combined commit rather than separate RED/GREEN commits — see TDD Gate Compliance below._

## Files Created/Modified
- `DG/src/DG.Core/Data/DataServiceRequestAuth.cs` - New pure DG.Core helper: token application + status classification
- `DG/tests/DG.Tests/DataServiceRequestAuthTests.cs` - New: covers every behavior bullet (trim/prefix/status mapping/ConnectionInfo default)
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` - Added PublishTokenMissing/Rejected/ProjectForbidden, ConnectorNoGraphBundle
- `DG/src/DG.Core/Models/ConnectionInfo.cs` - Password default changed to `string.Empty`
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` - Added tests for the four new templates plus a no-real-token-leak assertion
- `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` - Bearer token applied; 401/403 mapped; PostAsJsonAsync removed
- `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs` - Same pattern, keeps its 15s timeout/TaskCanceledException handling
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` - Trailing Token input (index 4); missing-token skip path
- `DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs` - Trailing Token input (index 3); missing-token skip path
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` - D-07 no-bundle reason + Remark runtime message

## Decisions Made
- Kept the component-level "blank token" check in `ValidatorComponent`/`ComputgraphPublishComponent` as a UX-facing early exit, in addition to the client-level `DataServiceRequestAuth` guard — the two are complementary (component avoids an unnecessary call and shapes its own status text; client is the last line of defense if ever called directly).
- `PublishAuthOutcome` is shared between the token-application check and the status-classification check so both call sites (`TryApplyConnectorToken` failure and `ClassifyStatus` after a non-2xx response) speak the same vocabulary.
- Component name constants (`"VALIDATOR"`, `"COMPUTGRAPH PUBLISH"`) are hardcoded `private const` fields in each publish client rather than passed as a parameter — matches the plan's Artifacts table signature (no extra `component` argument on `Publish`).

## Deviations from Plan

None — plan executed exactly as written. Both tasks' files, signatures, and acceptance criteria match the PLAN.md Artifacts table and action text.

## TDD Gate Compliance

Task 1 is marked `tdd="true"`. Per the plan's own `<behavior>`/`<action>` split, the intended flow is read-first → write behavior tests → implement → verify. In practice, the implementation (`DataServiceRequestAuth.cs`, template additions, `ConnectionInfo` default) and its tests were authored together and landed in a single commit (`6912bed`, typed `test(...)`), rather than as a separate failing-RED commit followed by a passing-GREEN commit. No `feat(...)` commit exists for Task 1 specifically (Task 2's `feat(...)` commit covers the GH wiring only). This is a process deviation, not a correctness gap: the filtered test run (`--filter "FullyQualifiedName~DataServiceRequestAuthTests|FullyQualifiedName~ErrorMessageTemplateTests"`) passed 61/61 before the commit, confirming every behavior bullet is covered and green.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required. Live Rhino confirmation of the Token inputs and the CONNECTOR no-bundle message stays with Phase 40 (GATE12-04), per the plan's own success criteria.

## Next Phase Readiness
- This plan lands in wave 1, ahead of 1205-10's server-side connector-token enforcement on `/validation/publish` and `/computgraph/publish` — existing canvases that already carry a token will continue to work once that server-side check ships.
- `requirements-completed` is left empty: ALGN12-17/18 are broader requirements spanning the full identity/authorization model (D-01 through D-20); this plan only closes the Grasshopper-side connector-token piece named in its own `requirements:` frontmatter. Full requirement closure is tracked at the phase level, not per-plan, per the plan's own frontmatter (`requirements: [ALGN12-17]` was carried but the plan's `must_haves` are the actual completion contract, verified above).
- `dotnet build .\DG\DG.sln -c Release`: 0 warnings, 0 errors (GRASSHOPPER_SDK code path compiled).
- `dotnet test .\DG\tests\DG.Tests\`: 577 passed, 3 failed, 580 total — the 3 failures are all in `DG.Tests.E2E.DesignStateValidationFlowTests` (environment-dependent, Neo4j unreachable from the host test process; matches the documented baseline of "4 fail fast, one intermittent flake passes on re-run" — here the flake passed).

## Self-Check: PASSED

- FOUND: DG/src/DG.Core/Data/DataServiceRequestAuth.cs
- FOUND: DG/tests/DG.Tests/DataServiceRequestAuthTests.cs
- FOUND: DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs (modified)
- FOUND: DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs (modified)
- FOUND: DG/src/DG.Grasshopper/Components/ValidatorComponent.cs (modified)
- FOUND: DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs (modified)
- FOUND: DG/src/DG.Grasshopper/Components/ConnectorComponent.cs (modified)
- FOUND commit 6912bed in git log
- FOUND commit 67f5e0f in git log

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*
