---
phase: 1308-dg-web-ui
plan: "04"
subsystem: grasshopper-addin
tags: [csharp, dg-core, auth, connector-session, xunit]
requires:
  - phase: 1308-03
    provides: "dgk_ connector session store (server side of POST/DELETE /auth/connector-session)"
provides:
  - "IConnectorSessionClient / ConnectorSessionClient: account login -> connector-session mint -> best-effort logout, plus SignOutAsync"
  - "ConnectorSessionOutcome / ConnectorSessionResult (redacted ToString)"
  - "DataServiceRequestAuth.TokenPrefix = dgk_"
  - "session-wording publish templates and seven ConnectorSignIn* templates"
affects: [1308-07]
tech-stack:
  added: []
  patterns:
    - "manual dg_session cookie capture/replay (HttpClientHandler UseCookies=false) instead of a cookie container"
    - "result record with PrintMembers override redacting token and Neo4j bundle"
key-files:
  created:
    - DG/src/DG.Core/Data/IConnectorSessionClient.cs
    - DG/src/DG.Core/Data/ConnectorSessionClient.cs
    - DG/src/DG.Core/Models/ConnectorSessionResult.cs
    - DG/tests/DG.Tests/ConnectorSessionClientTests.cs
  modified:
    - DG/src/DG.Core/Data/DataServiceRequestAuth.cs
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/tests/DG.Tests/DataServiceRequestAuthTests.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
key-decisions:
  - "SessionToken and Bundle are both redacted in ConnectorSessionResult.ToString (the bundle carries the Neo4j password)"
  - "SignOutAsync also refuses remote plain http and non-dgk_ values with zero requests"
  - "client catch blocks are message-free so nothing from the request path can reach a caller"
requirements-completed: []
duration: ~35 min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 04: Connector sign-in client Summary

**SDK-free two-step account sign-in client in DG.Core (login -> dgk_ connector session -> logout) with stub-handler tests, the dgk_ prefix in DataServiceRequestAuth and session-wording error templates.**

## What was built

- `ConnectorSessionClient` (D-35): `POST /auth/login` (JSON, `X-DG-CSRF: 1`), reads the `dg_session` value from `Set-Cookie`, `POST /auth/connector-session {project|null, connector_id}` replaying the cookie and CSRF header, then a best-effort `POST /auth/logout` in a `finally` (also after a 403/422 mint). 6 s per-request `WaitAsync`. Status mapping: login 401 Rejected, 429 Throttled, mint 403 Forbidden (ServerCode kept), 422 ProjectRequired (server hint in ServerMessage), 429 Throttled, transport/timeout/other Unreachable. A 201 without a `dgk_` token is treated as Unreachable.
- Remote non-loopback `http://` returns `InsecureTransport` before any request; blank username/password returns `NotAttempted` with zero requests.
- `SignOutAsync`: `DELETE /auth/connector-session` with `Bearer dgk_...`, true on 204, false otherwise, never throws (except caller cancellation).
- `DataServiceRequestAuth.TokenPrefix = "dgk_"`; docs describe the sign-in session.
- `ErrorMessageTemplates`: the four publish texts and `PublishProjectForbidden` rewritten to CONNECTOR.Session wording (signatures kept); `ConnectorTokenMissing` reworded to the sign-in text (it contained `dgc_`); seven new `ConnectorSignIn*`/`ConnectorProjectRequired` templates. `ConnectorTokenRejected` and `ConnectorHeartbeatUnreachable` left for plan 1308-07 as the plan specifies.

## Verification (real runs)

- `dotnet test DG/tests/DG.Tests/ --filter "ConnectorSessionClient|DataServiceRequestAuth|ErrorMessageTemplate|ConnectorComponentPortContract"`: 128 passed, 0 failed.
- `dotnet build DG/DG.sln -c Release`: 0 warnings, 0 errors (DG.Grasshopper compiles against unchanged signatures).
- Full `dotnet test DG/tests/DG.Tests/`: 790 passed, 4 failed. The 4 failures are the known `DesignStateValidationFlowTests` Neo4j auth baseline (env-dependent, not regressions).
- `grep -c dgc_` on ErrorMessageTemplates.cs and DataServiceRequestAuth.cs: 0 / 0. `Mint a new token` count: 1 (ConnectorTokenRejected only).
- Not verified: behaviour against a live data-service (plan uses stub handlers only; live check belongs to 1308-07/UAT). The 6 s timeout is exercised via a handler throwing TaskCanceledException, not by a real 6 s wait.

## Deviations from Plan

1. **[Ordering] Prefix change pulled into Task 1.** The tracer's happy path asserts a `dgk_test` token and the client validates `DataServiceRequestAuth.TokenPrefix`, so the prefix change (and its two test updates) landed in the Task 1 commit to keep it green; Task 2 then carried the templates and sign-out tests. `SignOutAsync` was implemented in Task 1 (the interface requires it) and its tests landed in Task 2.
2. **[TDD] No separate failing-test commits.** Test and implementation were committed together per task so no commit leaves DG.Tests non-compiling. RED was observed implicitly (types did not exist); GREEN was run before each commit.
3. **[Rule 2] ToString also redacts the Neo4j bundle** (not only the token), since it carries the Neo4j password.
4. **[Rule 2] SignOutAsync refuses remote plain http and non-dgk_ values** with zero requests, so the bearer is never put on an unencrypted remote path.

## Requirement status

WEBUI-08 is only partly delivered: the DG.Core client and templates exist and are tested, but CONNECTOR/VALIDATOR/COMPUTGRAPH PUBLISH are rewired in plan 1308-07. It is NOT marked complete in REQUIREMENTS.md.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-1308-04-01..05 mitigated and tested).

## Commits

- 654b947: feat(1308-04): two-step account sign-in client for connector sessions
- f7c95f0: feat(1308-04): session-wording error templates and SignOutAsync tests

## Self-Check: PASSED
