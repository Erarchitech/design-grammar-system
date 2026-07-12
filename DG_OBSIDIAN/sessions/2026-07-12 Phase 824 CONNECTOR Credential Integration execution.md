---
tags: [session, phase-824, connector, auth, grasshopper, dg-core]
date: 2026-07-12
phase: 824-connector-credential-integration
milestone: v8.2
---

# 2026-07-12 — Phase 824: CONNECTOR Credential Integration execution

## Summary

**Phase 824 executed end-to-end (2 plans)** via `/gsd-autonomous --only 824`. CONNECTOR Grasshopper component now authenticates with platform-issued tokens via data-service heartbeat. Two-wave delivery:
- **Plan 01 (DG.Core):** `ConnectorHeartbeatClient` (injectable, 6s-timeout, maps 200→Authenticated / 401→Rejected / else→Unreachable) + `HeartbeatResult` (token-free record struct) + two `ErrorMessageTemplates` entries (ConnectorTokenRejected + ConnectorHeartbeatUnreachable). 8 new unit tests, 234/234 pass.
- **Plan 02 (DG.Grasshopper):** CONNECTOR component appended with two optional additive inputs (`DataServiceUrl` idx 6, `Platform Token` idx 7); GUID `24E78A17…` and all existing ports unchanged; heartbeat-on-Connect with in-canvas Error/Warning feedback; full token secrecy (SHA-256 hashed dedup key, PersistentData scrub, token-free ConnectionInfo/outputs/logs).

**Verification:** Code-complete and green on all automatable checks:
- `dotnet build DG.sln -c Release` — 0 warnings / 0 errors (DG.Grasshopper compiled against the real Rhino 8 SDK, GRASSHOPPER_SDK defined)
- `dotnet test DG/tests/DG.Tests` — **234/234 pass**
- 6 source assertions all pass (GUID unchanged, additive inputs, heartbeat wiring, token secrecy, ungated outputs)
- **Verification status:** `human_needed` — 3 success criteria require in-Rhino UAT (live Grasshopper + data-service)

**Requirements:** CONNG-01 (additive inputs, unchanged GUID + ports) ✓, CONNG-02 (heartbeat auth + in-canvas Error/Warning + token secrecy) ✓

---

## Performance

- **Duration:** ~35 min (Plan 01 ~15 min, Plan 02 ~20 min)
- **Completed:** 2026-07-12
- **Tasks:** 8 (4 per plan)
- **Files modified:** 14 (6 created in DG.Core/DG.Grasshopper, 2 test files, 1 README, 5 plan artifacts, STATE.md)

---

## Accomplishments

### Plan 01: DG.Core Heartbeat Client + Templates (15 min)

- `HeartbeatResult.cs`: Outcome enum (NotAttempted/Authenticated/Rejected/Unreachable) + token-free result record struct (no password/token/credential/secret field — prevents leakage by design).
- `ConnectorHeartbeatClient.cs`: Injectable HttpClient with 6s timeout; maps 200→Authenticated (with Bearer header + /connectors/heartbeat endpoint), 401→Rejected, else/exception/timeout→Unreachable; short-circuits non-dgc_ tokens and empty tokens to avoid network calls.
- `ErrorMessageTemplates`: Two new static methods: `ConnectorTokenRejected()` + `ConnectorHeartbeatUnreachable(url)` with house-style What+Where+How-to-fix format.
- **Tests:** 8 new facts (6 client outcome-matrix facts + 2 template-rendering facts); full suite 234/234.

### Plan 02: CONNECTOR Component Wiring (20 min)

- **Additive inputs:** DataServiceUrl (idx 6, default http://localhost:8000) and Platform Token (idx 7) appended after Connect, preserving indices 0–5 and GUID `24E78A17…` for backward-compatibility (saved canvases keep wiring).
- **Heartbeat integration:** RunConnectAsync now calls `_heartbeatClient.CheckAsync()` after the bolt connection; empty/null token skips the heartbeat (byte-identical legacy).
- **In-canvas feedback:** ReportAuth() dispatches Error (Rejected) and Warning (Unreachable) via `AddRuntimeMessage()`, message label includes auth suffix (" · Auth OK", " · Auth failed", " · Auth unreachable").
- **Token secrecy:** 
  - `BuildRequestKey()` hashes the token (SHA-256, never raw).
  - `ScrubTokenPersistentData()` clears internalised token from GH_PersistentParam so .gh files never serialize the secret.
  - `ConnectionInfo` never carries the token; outputs emitted regardless of auth outcome (token never gates the bolt connection).
- **Documentation:** DG/README.md CONNECTOR contract updated with the two additive inputs and their purpose.
- **Build verification:** `dotnet build DG.sln -c Release` compiles successfully against Rhino 8 SDK.

---

## Architecture Decisions Recorded

Four key decisions locked during execution:

1. **DG.Core heartbeat logic, not DG.Grasshopper** — Enables unit testing without the Rhino SDK; DG.Grasshopper components are excluded from DG.Tests (net7.0-windows TFM incompatibility with net9.0 test runner).
2. **Non-dgc_ token prefix guards with no network call** — Mirrors backend guard; saves round-trip for invalid prefixes; consistent with data-service validation logic.
3. **Token authenticates heartbeat only, never gates bolt connection** — Locked in PROJECT.md; outputs always emitted; invalid token surfaces Error/Warning but doesn't block validation flow.
4. **Append-at-end input ordering for backward-compatible canvases** — The only safe way to add parameters without renumbering existing wires; old v8.1 canvases open with new inputs unconnected, no "missing component" error.

---

## Files Modified

### Source Code (DG.Core, DG.Grasshopper)
- `DG/src/DG.Core/Models/HeartbeatResult.cs` — **new**
- `DG/src/DG.Core/Data/IConnectorHeartbeatClient.cs` — **new**
- `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs` — **new**
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` — rewritten (additive inputs, heartbeat, secrecy)
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — extended with 2 new methods

### Tests (DG.Tests)
- `DG/tests/DG.Tests/ConnectorHeartbeatClientTests.cs` — **new** (6 outcome-matrix facts + StubHttpMessageHandler)
- `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs` — extended with 2 new facts

### Documentation
- `DG/README.md` — CONNECTOR contract updated

### Phase Artifacts
- `.planning/phases/824-connector-credential-integration/824-01-SUMMARY.md` — **new**
- `.planning/phases/824-connector-credential-integration/824-02-SUMMARY.md` — **new**
- `.planning/phases/824-connector-credential-integration/824-VERIFICATION.md` — **new** (human_needed status)
- `.planning/phases/824-connector-credential-integration/824-UAT.md` — **new** (3 manual checks scripted)
- `.planning/STATE.md` — updated with Phase 824 position and deferral status

---

## Verification Status

### Code-Level (Automated ✅)
- Build: `dotnet build DG.sln -c Release` → 0 warnings / 0 errors
- Tests: `dotnet test DG/tests/DG.Tests` → **234/234 pass**
- Source assertions: 6 sentinels all pass (GUID, inputs, heartbeat wiring, secrecy, ungated outputs)

### Runtime-Level (Deferred to In-Rhino UAT)
Three success criteria remain unverified pending a live Rhino/Grasshopper session + running data-service:

1. **Valid token heartbeat → Auth OK** — Code is proven (unit tests + build), but the in-canvas message render + data-service heartbeat record have not been observed.
2. **Invalid token Error / unreachable Warning + outputs ungated** — Outcome→message mapping unit-tested and code-verified, but runtime message bubbles require a live session.
3. **Token scrubbed from .gh + old canvas opens** — Code paths closed and asserted, but on-disk .gh inspection + backward-compat canvas open require Rhino.

**Verdict:** `verification: human_needed` with three manual checks documented in [824-UAT.md](.planning/phases/824-connector-credential-integration/824-UAT.md). No automation possible; UAT can resume anytime by `/gsd-verify-work 824`.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| DG.Core placement (not GH) | Testable without Rhino SDK; DG.Grasshopper can't build into DG.Tests (TFM incompatibility) |
| Non-dgc_ prefix guard (no call) | Backend validates prefix; saves network round-trip on invalid input |
| Heartbeat-only auth (never gates bolt) | Token authenticates the sidecar integration, not the core Neo4j connection; unlock flexibility |
| Additive inputs at end (idx 6–7) | Preserves wire→index mapping in saved canvases; GUID unchanged; old v8.1 files open without rewiring |

---

## Issues Encountered

None. The DG.Grasshopper project auto-detected Rhino 8 at `C:\Program Files\Rhino 8`, so `GRASSHOPPER_SDK` was defined and the real component code compiled (not the placeholder stub).

---

## Notes

- **Stale blocker resolved:** STATE.md warned net9.0 runtime was absent, requiring `DOTNET_ROLL_FORWARD=LatestMajor`. This session ran `dotnet build` + `dotnet test` cleanly on net9.0 without that flag — the blocker appears stale or environment-specific.
- **Single-phase autonomous mode:** Phase 824 was executed in isolation (no milestone lifecycle) per the `/gsd-autonomous --only 824` invocation. Milestone complete/archive is pending Phase 822/823 UAT and a formal `/gsd-complete-milestone v8.2` sweep.

---

## What's Next

1. **In-Rhino UAT (824-UAT.md):** 3 manual checks when a live Rhino/Grasshopper session + data-service are available. Resume with `/gsd-verify-work 824`.
2. **v8.2 completion:** After phase 824 UAT passes (or if deferred), the milestone is ready for `/gsd-complete-milestone v8.2` (audit → archive → next milestone).
3. **v9.0 resumption:** Phase 28 (Cloud LLM Connector) is shipped but has 1 UAT item pending; Phase 29 (DG-aware context layer) is ready to plan.

---

## Requirements Satisfied

- **CONNG-01:** Additive platform-token inputs + GUID + existing ports unchanged ✓
- **CONNG-02:** Heartbeat authentication + in-canvas Error/Warning feedback + token secrecy ✓

---

*Phase: 824-connector-credential-integration*  
*Completed: 2026-07-12*  
*Status: Code-complete, verification deferred to in-Rhino UAT*
