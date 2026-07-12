# Phase 824: CONNECTOR Credential Integration - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

The Grasshopper `CONNECTOR` component gains **platform-token authentication** layered additively on top of its existing raw-Neo4j (bolt) connection. On the existing `Connect=Go` toggle, when a platform token is supplied, the component calls data-service's live `POST /connectors/heartbeat` endpoint (`Authorization: Bearer dgc_…`) and surfaces the outcome in-canvas. A rejected/unreachable token produces a clear GH runtime message; it **never** gates or replaces the bolt connection, and the raw token is never persisted to the `.gh` file, outputs, status text, or logs.

**In scope:** additive `Token` + `DataServiceUrl` inputs, heartbeat call, in-canvas error/status feedback, token-secrecy handling, `ErrorMessageTemplates` entries, unit tests.
**Out of scope:** any data-service/`connectors.py` backend change (already complete from v8.1 Phase 812), downstream reuse of the token by other components, pre-emptive credential status display (CONN-F03), non-Grasshopper connectors.
</domain>

<decisions>
## Implementation Decisions

### Token Input & Data-Service Reachability
- Add a new **optional `DataServiceUrl`** text input (default `http://localhost:8000`), mirroring the existing `ValidatorComponent` input, so the heartbeat can target local or remote data-service.
- Add a new **optional `Token`** (platform-credential) text input.
- **Both new inputs are appended at the end** of the input list (after `Connect` at index 5 → `DataServiceUrl` index 6, `Token` index 7). Existing input indices 0–5, their wiring, and the component GUID `24E78A17-4533-44E7-8931-1224A70A1B36` stay **unchanged** — saved `.gh` canvases keep working without rewiring (CONNG-01, Success Criterion 1).
- **Empty token → skip the heartbeat entirely.** The component behaves exactly as today (pure bolt connection, backward-compatible, no error or warning).
- The **heartbeat fires on the existing `Connect=Go` toggle**, alongside the bolt connectivity check — not on a separate toggle.

### Invalid-Token Behavior & Status Feedback (CONNG-02)
- The token **authenticates the heartbeat only and never gates or blocks** the bolt connection or the `Database`/`Project` outputs (locked PROJECT.md decision). Bolt connects on raw credentials as before; a token failure surfaces as an in-canvas runtime message only.
- **Two failure buckets:**
  - Heartbeat `401` → `GH_RuntimeMessageLevel.Error` — "token invalid / revoked / expired".
  - Network / timeout / non-401 → `GH_RuntimeMessageLevel.Warning` — "data-service unreachable".
- Canvas `Message` shows **combined bolt + auth state**: `Connected · Auth OK` on success, `Connected · Auth failed` when the token is rejected (bolt still connected).
- **No runtime message on a valid token** (GH convention: only warnings/errors surface); success is reflected only in `Message`. Never a silent failure or crash (Success Criterion 3).

### Token Secrecy / Non-Persistence (Success Criterion 4)
- Token is read from its input **each solve and never written to the `.gh` file**: never call `AddPersistentData` with it, and **actively scrub/clear the token input param's persistent data** after reading so an internalized value cannot be serialized into canvas state. Document "wire the token from a Panel".
- Token is **never added to `ConnectionInfo`** (the serialized `Database` output) — used transiently for the heartbeat call and discarded.
- Token (or any fragment) is **never echoed** into `Message`, `StatusMessage`, or any log/error text.
- The in-memory request-dedup key (`BuildRequestKey`) uses a **SHA-256 hash** of the token, not the raw value.

### Claude's Discretion
- Exact new-input display names / nicknames (following existing naming conventions).
- Whether to fold the heartbeat into the existing async connect `Task` flow (preferred — reuses cancellation + `ScheduleSolution`) or a discrete call.
- Whether to add a small dedicated heartbeat client (mirroring `ValidationPublishClient`) vs. inline `HttpClient` usage.
- New `ErrorMessageTemplates` method names / wording for the auth-failure and unreachable cases (keep the What+Where+How-to-fix shape).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ValidatorComponent`** (`DG.Grasshopper/Components`) — already exposes a `DataServiceUrl` input defaulting to `http://localhost:8000`; mirror it.
- **`ValidationPublishClient`** (`DG.Grasshopper/Validation`) — static `HttpClient`, `PostAsJsonAsync(endpoint, req, JsonOptions).GetAwaiter().GetResult()`, `NormalizeUrl` helper, `#if GRASSHOPPER_SDK` guard + `#else` stub. Template for a heartbeat client.
- **`ErrorMessageTemplates`** (`DG.Core.Services`) — static What+Where+How-to-fix methods (e.g. `PublishFailed`, `ShaclViolation`); add connector-auth entries here.
- **data-service `POST /connectors/heartbeat`** (`app.py:1134`) — reads `Authorization: Bearer <dgc_ token>`, returns `200 {connector_id, status}` or `401` structured error (`CONNECTOR_AUTH_FAILED`). Token hashed server-side (SHA-256), never stored plaintext.
- **`connectors.py`** backend — `record_heartbeat` / `create_credential` / `revoke_credential` already implemented (v8.1 Phase 812). **No backend change needed.**

### Established Patterns
- `ConnectorComponent` uses an **async connect `Task`** with `CancellationTokenSource`, request-key dedup (`BuildRequestKey`), and `ScheduleSolution`/`ExpireSolution` to refresh the canvas — extend this for the heartbeat.
- Inputs read via `da.GetData(index, ref …)`; appending new inputs keeps existing indices stable.
- `#if GRASSHOPPER_SDK` guards all GH-dependent code (both `ConnectorComponent` and `ValidationPublishClient` carry `#else` stubs).
- Runtime feedback via `AddRuntimeMessage(GH_RuntimeMessageLevel.*, msg)` + the `Message` label.
- `ConnectionInfo` (`DG.Core.Models`) fields: `Uri/User/Password/Database/Project/IsConnected/StatusMessage` — the serialized `Database` output; must stay token-free.

### Integration Points
- `ConnectorComponent.RegisterInputParams` — append `DataServiceUrl` + `Token` params.
- `ConnectorComponent.SolveInstance` — read new inputs; when `Connect && token present`, issue heartbeat; map result → runtime message + `Message`.
- `ConnectorComponent.BuildRequestKey` — include the **hashed** token.
- New heartbeat client (DG.Grasshopper/Validation, mirroring `ValidationPublishClient`) + `DG.Tests` coverage.
- `ErrorMessageTemplates` — new connector-auth templates.
</code_context>

<specifics>
## Specific Ideas

- Token format is `dgc_` + url-safe randomness; the heartbeat requires `Authorization: Bearer <token>` and the token to start with `dgc_` (the client should short-circuit / treat a non-`dgc_` value as a rejected token without a network round-trip where sensible).
- The credential source is the **"Grasshopper" connector type** (id `grasshopper`) on the v8.1 Connectors screen (`ConnectorsScreen.jsx` / `connectorsApi.js`).
- The backend has **no token-expiry concept** — only revoke → `401`. "Expired" in CONNG-02 is covered by the `401` "rejected" bucket; no backend change is in scope to add expiry.
- Heartbeat success maps `{connector_id, status}` (status = `active`/`stale`/`never_connected`); a `stale`/`active` 200 both count as authenticated for canvas purposes.
</specifics>

<deferred>
## Deferred Ideas

- **CONN-F03** — pre-emptive credential status display on CONNECTOR (live active/stale/revoked shown before a run, via the heartbeat endpoint). Future requirement.
- Downstream reuse of the token by `GRAPH DECONSTRUCT` / `VALIDATOR` — out of scope; token stays inside CONNECTOR.
- **CONN-F04** — per-connector-type scoping surfaced explicitly in the Grasshopper UX.
</deferred>
