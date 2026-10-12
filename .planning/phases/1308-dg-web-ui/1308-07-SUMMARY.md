---
phase: 1308-dg-web-ui
plan: "07"
subsystem: grasshopper-addin
tags: [csharp, grasshopper, connector, auth, connector-session]
requires:
  - phase: 1308-04
    provides: "IConnectorSessionClient / ConnectorSessionClient, session-wording templates"
provides:
  - "CONNECTOR with account sign-in: Username/Password/Project/Connect in, Database/Project/Session out (fresh GUID)"
  - "VALIDATOR and COMPUTGRAPH PUBLISH Token input repurposed to CONNECTOR.Session (GUIDs and port order unchanged)"
  - "heartbeat client, its types, tests and heartbeat-only templates removed"
  - "spec/GRASSHOPPER.md connector-session section and docs/RELEASE-NOTES-v13.0.md re-wire guide"
affects: [1308-09, 1308-13, 1308-20]
tech-stack:
  added: []
  patterns:
    - "sign-in request key is a SHA-256 of username, project and password; password only in task locals, never a field"
    - "Interlocked.Exchange on the live session so sign-out is exactly-once and fire-and-forget"
key-files:
  created:
    - docs/RELEASE-NOTES-v13.0.md
  modified:
    - DG/src/DG.Grasshopper/Components/ConnectorComponent.cs
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
    - DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs
    - DG/src/DG.Grasshopper/Params/NonPersistentStringParam.cs
    - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
    - DG/tests/DG.Tests/ErrorMessageTemplateTests.cs
    - spec/GRASSHOPPER.md
  deleted:
    - DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs
    - DG/src/DG.Core/Data/IConnectorHeartbeatClient.cs
    - DG/src/DG.Core/Models/HeartbeatResult.cs
    - DG/tests/DG.Tests/ConnectorHeartbeatClientTests.cs
key-decisions:
  - "Owner answered proceed on the one-way CONNECTOR GUID change (Task 1 checkpoint); fresh GUID EF2E6F2A-3450-4907-94CB-31B1240AB848 per D-36"
  - "A sign-in that completes after it was superseded or switched off is signed out immediately instead of waiting for the 8 h TTL"
  - "Faulted-task status text is a fixed string; exception messages never reach the canvas"
requirements-completed: [WEBUI-08, WEBUI-10]
duration: ~40 min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 07: Grasshopper account sign-in Summary

**CONNECTOR now signs in with a DG account (Username/Password, non-persistent) and outputs a dgk_ Session that VALIDATOR and COMPUTGRAPH PUBLISH take on their Token input; the heartbeat client is gone and the canvas re-wire is documented.**

## Checkpoint

Task 1 (checkpoint:decision, one-way CONNECTOR GUID change): owner answered **proceed** in the spawning session, so Tasks 2 and 3 were executed.

## What was built

- `ConnectorComponent`: new GUID with an ADR-825-3 comment; inputs Username ("User") and Password ("Pwd") as `NonPersistentStringParam` (optional), Project (text, optional), Connect ("Go", default false); outputs Database, Project, Session. `IConnectorSessionClient` replaces the heartbeat client. A new request key (SHA-256 of username, project, password) signs out the previous session first, then `SignInAsync`. All seven outcomes map to the 1308-04 templates; SignedIn without a bundle shows `ConnectorNoGraphBundle` and still outputs the Session. Connect=false, missing credentials and `RemovedFromDocument` call `SignOutCurrentSession()` (fire-and-forget `SignOutAsync`).
- Heartbeat removal (D-35): `ConnectorHeartbeatClient`, `IConnectorHeartbeatClient`, `HeartbeatResult` and `ConnectorHeartbeatClientTests` deleted; `ConnectorTokenRejected`, `ConnectorHeartbeatUnreachable` and `ConnectorTokenMissing` (duplicate of `ConnectorSignInMissing`, no caller left) removed with their tests.
- VALIDATOR and COMPUTGRAPH PUBLISH: only the Token description changed ("Connector session: wire CONNECTOR.Session. ..."); GUIDs and port order untouched.
- `spec/GRASSHOPPER.md`: CONNECTOR row and the "Connector session on publish components (Phase 1308)" section. `docs/RELEASE-NOTES-v13.0.md`: connector sign-in section with the six-step re-wire guide, per-connector grant note and the D-38 deferral.

## Verification (real runs)

- `dotnet build DG/DG.sln -c Release`: 0 warnings, 0 errors. DG.Grasshopper was freshly rebuilt (dll timestamp matched the run) and defines `GRASSHOPPER_SDK`, so the component body was compiled.
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName!~DesignStateValidationFlowTests"`: 780 passed, 0 failed.
- Greps: GUID present in ConnectorComponent.cs; `3F9B1C7E-6A24` count 1 (the ADR comment); no references to heartbeat types or the removed templates in DG/src or DG/tests; two `NonPersistentStringParam()` registrations in ConnectorComponent; `SignOutCurrentSession`/`SignOutAsync` on Connect=false, missing credentials, removal and supersession; `dgc_` absent from DG/src *.cs; `CONNECTOR.Session` found in all four files.
- `git diff --stat` for the two publish components: 1 line each (description only).
- Not verified: behaviour in a live Rhino/Grasshopper canvas and against a live data-service (no Rhino launch or install authorized; the owner live check belongs to 1308-20). The DG.Tests project has no Grasshopper reference, so the component (including ports and GUID) has no automated test; it is covered by compile, grep and review only.

## Deviations from Plan

1. **[Scope] ConnectorComponentPortContractTests.cs not modified.** It contains only template and handle-type tests with nothing heartbeat-related, and the GH component is not reachable from DG.Tests, so no adjustment was needed.
2. **[Rule 2] Late-arriving session is signed out.** If a sign-in finishes after it was cancelled (new credentials or Connect=false), the minted session is ended at once so no live session is orphaned until its TTL. Supports threat T-1308-07-04.
3. **[Rule 1/2] Faulted sign-in task** shows a fixed "Connection task failed." instead of the exception message, so nothing from the sign-in path can reach the canvas (prohibition on secrets in messages).
4. **[Cleanup]** `ConnectorTokenMissing` removed as a template with no caller left (plan allowed "any other with no caller left"); the retired-wording test list was adjusted.

## Requirement status

WEBUI-08 is delivered by this plan (component, publish wiring, docs) and marked complete, with the owner live check still pending in 1308-20. WEBUI-10 was already complete.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-1308-07-01/02/04 are implemented (non-persistent params; template-only messages with no secret arguments; sign-out on Connect=false, removal and supersession). T-1308-07-03 is accepted per D-38 and stated in the release note.

## Commits

- 0a10003: feat(1308-07): CONNECTOR signs in with the DG account and outputs Session
- cdd2e40: feat(1308-07): publish components take CONNECTOR.Session; spec and release note

## Self-Check: PASSED
