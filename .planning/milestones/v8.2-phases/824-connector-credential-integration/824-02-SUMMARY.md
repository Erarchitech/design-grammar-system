---
phase: 824-connector-credential-integration
plan: 02
subsystem: grasshopper
tags: [csharp, grasshopper, gh-component, connector-auth, secrecy, dg-grasshopper]

requires:
  - phase: 824-01
    provides: ConnectorHeartbeatClient, HeartbeatResult/HeartbeatOutcome, ConnectorTokenRejected/ConnectorHeartbeatUnreachable templates
provides:
  - CONNECTOR component with two additive optional inputs (DataServiceUrl idx 6, Platform Token idx 7)
  - Heartbeat-on-Connect with in-canvas Error/Warning feedback via AddRuntimeMessage
  - Token secrecy — SHA-256 hash in the dedup key, PersistentData scrub, token-free ConnectionInfo/Message/logs
affects: [connector, grasshopper]

tech-stack:
  added: []
  patterns: ["Additive GH input params appended at the end (indices unchanged, GUID unchanged) for backward-compatible canvases", "Secret scrub of GH_PersistentParam persistent data to keep credentials out of .gh files"]

key-files:
  created: []
  modified:
    - DG/src/DG.Grasshopper/Components/ConnectorComponent.cs
    - DG/README.md

key-decisions:
  - "New inputs appended at indices 6-7 (after Connect) — the only additive option that preserves existing wire→index mapping in saved canvases"
  - "Token authenticates the heartbeat ONLY; it never gates the bolt connection or output (locked PROJECT.md decision)"
  - "Internalised token persistent-data is cleared each solve + a Remark nudges wiring from a Panel"

patterns-established:
  - "ConnectResult record struct bundling ConnectionInfo + HeartbeatResult through the existing async connect task"

requirements-completed: [CONNG-01, CONNG-02]

coverage:
  - id: D1
    description: "CONNECTOR exposes DataServiceUrl (idx 6) + Platform Token (idx 7) as additive optional inputs; the four Neo4j inputs, PROJECT NAME, Connect, both outputs, and GUID 24E78A17-4533-44E7-8931-1224A70A1B36 are unchanged"
    requirement: "CONNG-01"
    verification:
      - kind: other
        ref: "source-assertion INPUTS_OK + dotnet build DG.sln -c Release (GRASSHOPPER_SDK compile) exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "A valid token minted from the Connectors screen authenticates a heartbeat to data-service, observed end-to-end in the Grasshopper canvas"
    requirement: "CONNG-01"
    verification:
      - kind: manual_procedural
        ref: "824-UAT.md Test 1"
        status: unknown
    human_judgment: true
    rationale: "Requires a live Rhino/Grasshopper session + running data-service + a real dgc_ token; not exercisable in this environment. Client logic is unit-proven in Plan 01, but the in-canvas E2E has not been observed."
  - id: D3
    description: "An invalid/revoked/expired token surfaces a clear in-canvas Error (data-service unreachable a Warning), never a silent failure or crash, and never blocks the bolt output"
    requirement: "CONNG-02"
    verification:
      - kind: other
        ref: "source-assertion HEARTBEAT_WIRED_OK + OUTPUT_UNGATED_OK; outcome→message mapping unit-tested in Plan 01"
        status: pass
      - kind: manual_procedural
        ref: "824-UAT.md Test 2 (in-canvas bubble render)"
        status: unknown
    human_judgment: true
    rationale: "The outcome→message logic and the ungated output are code-proven, but observing the runtime message bubble on the component requires a live Rhino session."
  - id: D4
    description: "The raw token is never persisted inside the .gh file or written to outputs/logs/status in plaintext"
    requirement: "CONNG-02"
    verification:
      - kind: other
        ref: "source-assertion SECRECY_OK (token-free ConnectionInfo/HeartbeatResult, SHA-256 hashed key, PersistentData scrub)"
        status: pass
      - kind: manual_procedural
        ref: "824-UAT.md Test 3 (save canvas, inspect .gh has no dgc_)"
        status: unknown
    human_judgment: true
    rationale: "Code paths that could persist the token are all closed and asserted, but confirming an actual saved .gh contains no dgc_ string is a manual inspection."

duration: ~20min
completed: 2026-07-12
status: complete
---

# Phase 824 / Plan 02: CONNECTOR Component Wiring Summary

**CONNECTOR gains an additive platform-token heartbeat with in-canvas Error/Warning feedback and full token secrecy (hashed dedup key, persistent-data scrub, token-free outputs) — GUID and existing ports untouched, whole solution builds green against the Rhino SDK.**

## Performance
- **Duration:** ~20 min
- **Completed:** 2026-07-12
- **Tasks:** 4
- **Files modified:** 2

## Accomplishments
- Appended two optional inputs — `DataServiceUrl` (idx 6, default `http://localhost:8000`) and `Platform Token` (idx 7) — leaving inputs 0–5, both outputs, and GUID `24E78A17-4533-44E7-8931-1224A70A1B36` unchanged (CONNG-01).
- On `Connect` with a non-empty token, the async connect flow also runs the heartbeat; `Rejected`→`AddRuntimeMessage(Error, ConnectorTokenRejected())`, `Unreachable`→`AddRuntimeMessage(Warning, ConnectorHeartbeatUnreachable(url))`, and the `Message` label carries an `Auth OK / Auth failed / Auth unreachable` suffix (CONNG-02). Empty token ⇒ no heartbeat, byte-identical legacy behavior.
- Secrecy: `BuildRequestKey` hashes the token (SHA-256), `ScrubTokenPersistentData()` clears any internalised token so the `.gh` never serializes it, and the token never enters `ConnectionInfo`, `Message`, `StatusMessage`, or any log; the bolt outputs are emitted regardless of auth outcome (token never gates the connection).
- `DG/README.md` CONNECTOR contract updated; `dotnet build DG.sln -c Release` compiles `DG.Grasshopper` against the real Rhino/Grasshopper SDK (0 warnings, 0 errors).

## Files Created/Modified
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` — inputs, heartbeat integration, `ReportAuth`, `AuthSuffix`, `HashToken`, `ScrubTokenPersistentData`, `ConnectResult`
- `DG/README.md` — CONNECTOR contract documents the two additive inputs

## Decisions Made
- Append-at-end input ordering (the only GUID/wiring-safe additive option).
- Token flows only to `CheckAsync` + `HashToken`; never onto a serialized/displayed surface.

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
None. The `DG.Grasshopper` project auto-detected Rhino 8 at `C:\Program Files\Rhino 8`, so `GRASSHOPPER_SDK` was defined and the real component code compiled (not the placeholder stub).

## Next Phase Readiness
Feature code-complete and building. Remaining acceptance is in-Rhino UAT (see `824-UAT.md`): live heartbeat auth, in-canvas message render, and `.gh` non-persistence — none exercisable without a Rhino runtime + running data-service.

---
*Phase: 824-connector-credential-integration*
*Completed: 2026-07-12*
