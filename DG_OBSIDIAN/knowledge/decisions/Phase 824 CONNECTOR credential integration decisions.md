---
tags: [decision, phase-824, connector, auth, grasshopper, dg-core]
date: 2026-07-12
phase: 824
---

# Phase 824: CONNECTOR Credential Integration — Design Decisions

Four key architectural decisions locked during phase 824 execution (2026-07-12).

---

## D-01: DG.Core Heartbeat Logic (not DG.Grasshopper)

**Decision:** Platform-token heartbeat authentication logic lives in `DG.Core` (`ConnectorHeartbeatClient`, `HeartbeatResult`, `HeartbeatOutcome`) rather than in `DG.Grasshopper`.

**Rationale:**
- DG.Grasshopper targets net7.0-windows (Rhino SDK constraint), but DG.Tests targets net9.0 — TFM incompatibility (NU1201) prevents ProjectReference and means DG.Grasshopper components are excluded from unit tests.
- By placing the heartbeat logic in DG.Core (net9.0), it compiles **without** the Rhino SDK and is fully unit-testable headlessly.
- The component (DG.Grasshopper) then injects and calls the tested client, reducing the scope of untestable runtime code.

**Impact:**
- No DG.Grasshopper code is testable in DG.Tests; the component is excluded by design.
- All heartbeat behavior is verified via DG.Core unit tests (6 facts); component wiring verified via source assertions and Rhino runtime UAT.

---

## D-02: Non-dgc_ Prefix Guard (No Network Call)

**Decision:** When a token is supplied but does not start with `dgc_`, short-circuit to `Rejected` with **no network call** to data-service.

**Rationale:**
- data-service validates the `dgc_` prefix server-side; mirroring this guard on the client saves a network round-trip for obviously invalid input.
- Consistent with data-service's own early validation — fail fast, don't round-trip.
- Reduces load on data-service during development/testing with random token strings.

**Implementation:** ConnectorHeartbeatClient.CheckAsync() checks `token.StartsWith("dgc_")` before POST; non-matching returns `HeartbeatResult.Rejected` with zero HTTP calls.

**Impact:**
- Unit tests verify the short-circuit (StubHttpMessageHandler.CallCount == 0 for non-dgc_ input).
- In-canvas behavior: invalid prefix produces the same Error message as a rejected token (401), but faster.

---

## D-03: Heartbeat Authenticates Heartbeat Only, Never Gates Bolt Connection

**Decision:** The platform token authenticates the **heartbeat request to data-service** only. It **never gates** the Neo4j bolt connection or the component's outputs.

**Rationale:**
- The CONNECTOR component's core function is to establish a bolt connection to Neo4j for validation queries.
- Platform-token authentication is an **optional sidecar integration** (credential registry + audit trail), not a prerequisite for core functionality.
- Decoupling heartbeat from bolt connection preserves backward-compatibility: canvases without a token still work (heartbeat skipped, output ungated).
- Allows graceful degradation: even if data-service is down or token is invalid, the component still connects to Neo4j and produces output (feedback surface via Error/Warning, not via output suppression).

**Implementation:**
- `RunConnectAsync()` calls bolt connection and heartbeat in parallel (via AND composition, not sequential gatekeeping).
- `SolveInstance()` always emits `da.SetData(0, _latestConnection)` and `da.SetData(1, project)` regardless of auth outcome.
- Auth failure surfaces Error/Warning bubble, but outputs are populated.

**Impact:**
- Invalid token does not break validation workflows; it surfaces in-canvas feedback (Error "platform token rejected") while the connection still functions.
- Empty token results in graceful no-heartbeat behavior (backward-compatible with v8.1 canvases).

---

## D-04: Additive Inputs Appended at End (Indices 6–7)

**Decision:** New optional inputs (`DataServiceUrl`, `Platform Token`) are appended at indices 6 and 7, **after** the existing six inputs (indices 0–5), rather than inserted or replacing.

**Rationale:**
- Grasshopper saves canvas wiring as input index → wire connections. If we renumber existing inputs, old canvases break (wires point to wrong indices or "missing component").
- Appending at the end preserves the index-to-wire mapping for indices 0–5, so old v8.1 canvases open without rewiring.
- Both new inputs are `Optional = true`, so old canvases function with default values even if the new inputs are never connected.

**Implementation:**
- `RegisterInputParams()` adds inputs 0–5 unchanged, then appends 6–7 with `pManager[6].Optional = true` and `pManager[7].Optional = true`.
- GUID `24E78A17-4533-44E7-8931-1224A70A1B36` unchanged.
- Both outputs unchanged.

**Impact:**
- Old v8.1 CONNECTOR canvases open with the original six inputs still wired; the two new inputs appear unconnected.
- No "missing component" error; no rewiring required.
- Full backward-compatibility; the additive pattern is a Grasshopper best-practice for non-breaking changes.

---

## Token Secrecy Pattern (Across All Decisions)

All decisions reinforce token secrecy:

1. **Token confined to Authorization header** — never logged, never on `HeartbeatResult`, never on `ConnectionInfo`, never on component message or status.
2. **Hashed in dedup key** — `BuildRequestKey()` uses SHA-256 hash of token, not the raw secret, so change-detection (when to re-run the heartbeat) doesn't leak the token into the request key.
3. **PersistentData scrub** — `ScrubTokenPersistentData()` clears any internalised token from the GH parameter store so the `.gh` file never serializes it (on every solve, before any logic runs).
4. **Token-free record struct** — `HeartbeatResult` is deliberately designed with **no** password/token/credential/secret field; it's impossible to accidentally leak the secret on this type.

---

## Reference

- **Phase:** 824-connector-credential-integration
- **Plans:** 824-01 (DG.Core), 824-02 (DG.Grasshopper)
- **Requirements:** CONNG-01 (additive inputs, GUID unchanged), CONNG-02 (heartbeat auth, Error/Warning, token secrecy)
- **Status:** Code-complete, verification deferred to in-Rhino UAT
- **Session:** [[sessions/2026-07-12 Phase 824 CONNECTOR Credential Integration execution|2026-07-12]]

---

*Locked: 2026-07-12*  
*Phase: 824-connector-credential-integration*
