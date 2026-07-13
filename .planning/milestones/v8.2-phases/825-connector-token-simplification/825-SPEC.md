---
phase: 825-connector-token-simplification
milestone: v8.2 (follow-up; free block 825–829)
status: spec
created: 2026-07-13
requirement: CONNG-03 (new)
supersedes_ux: 824 (8-input additive CONNECTOR)
backward_compat: intentionally broken (user-approved 2026-07-13)
---

# Phase 825 — CONNECTOR Token-Driven Simplification

## Origin

`/gsd-audit-fix` on the Phase 824 CONNECTOR component. The audit classified every
requested change as **manual-only** (needs design + backend features that don't exist),
so per user decision this graduates into a proper phase rather than a mechanical fix.

User intent (verbatim): *"Simplify CONNECTOR component inputs, only necessary inputs
should remain: if we have Token, do we need Project? Token should be Project-scoped and
substitute Project and DB inputs, DataServiceUrl, URI seems is not necessary. Only User
and Password information are needed, but User and passwords must share credentials from
Design Grammars platform … Token label is impossible to input now, the field is not active."*

## Problem (current state, Phase 824)

`ConnectorComponent` registers **8 inputs**: `URI, User, Password, DB, Project, Connect,
DataServiceUrl, Token`. Only `Token` and `Connect` carry the user's real decision; the
other six are either deployment infra (URI/User/Password/DB/DataServiceUrl — identical for
everyone on this single-Neo4j deployment) or derivable (Project). The `Token` field is also
**effectively unusable when typed directly**: `ScrubTokenPersistentData()` clears any
internalised value on *every solve*, so it reads as "not active."

Blockers the audit surfaced:
- A connector credential (`data-service/connectors.py`) stores **no project and no
  database** — `{credential_id, connector_id, label, token_hash, created_at, revoked,
  last_connection}`. There is nothing for the token to "substitute Project/DB" *from*.
- `/connectors/heartbeat` returns only `{connector_id, status}`.
- The "platform sign-in credentials" are a **browser-only, client-hashed** value
  (`localStorage.dg_users`, SubtleCrypto SHA-256) — **not** Neo4j bolt credentials, and a
  desktop C# process cannot read them. The coherent reading is: *the platform Token itself
  is the single shared credential*; it unlocks the connection server-side.

## Goal

Reduce CONNECTOR to **two inputs — `Token` + `Connect`**. On connect, the token is
authenticated by data-service, which returns the **project scope** and a **Neo4j
connection bundle**; the component opens the bolt connection from that bundle and emits its
`Database`/`Project` outputs. The token is typeable live but never persisted to the `.gh`.

## Success criteria

1. **SC-1 (input surface):** CONNECTOR registers exactly two inputs — `Token` (text) and
   `Connect` (bool). No URI/User/Password/DB/Project/DataServiceUrl inputs remain.
2. **SC-2 (token → project):** A credential is minted **bound to a project** (Connectors
   screen create form supplies it). `/connectors/heartbeat` returns that `project`.
3. **SC-3 (token → connection bundle):** `/connectors/heartbeat` returns a `neo4j` bundle
   `{uri, user, password, database}` derived from data-service env, using a **host-facing**
   URI (`NEO4J_PUBLIC_URI`, default `bolt://localhost:7687`) — never the Docker-internal
   `bolt://neo4j:7687`.
4. **SC-4 (component uses bundle):** With a valid token + `Connect=true`, the component
   connects to Neo4j using the bundle, emits the `Database` handle and the bundle's
   `Project`, and `Message` reads `Connected · Auth OK`.
5. **SC-5 (failure feedback preserved):** Invalid/revoked token → red Error, service
   unreachable → orange Warning (existing ErrorMessageTemplates), and — since the bundle is
   now the *only* connection source — a rejected/unreachable auth yields a clear "cannot
   connect without a valid platform token" state rather than a silent bolt attempt.
6. **SC-6 (typeable, non-persistent):** The `Token` field accepts a directly-typed value
   during a session (no immediate scrub), but the saved `.gh` contains **no `dgc_`
   substring** (persistent data cleared at serialization time).

## Design decisions (ADRs)

- **ADR-825-1 — Project-scoped credential.** `create_credential` gains a `project`
  parameter, persisted on the record; `CredentialCreatePayload` gains `project`. Missing
  project defaults to `"default-project"` for backward tolerance of old records.
- **ADR-825-2 — data-service owns the connection bundle.** It already holds
  `NEO4J_URI/USER/PASSWORD`. A new env `NEO4J_PUBLIC_URI` (default `bolt://localhost:7687`)
  is what the heartbeat returns, so host-side Grasshopper can reach Neo4j (the internal
  `bolt://neo4j:7687` is unreachable off the Docker network). Returning the bolt password
  over HTTP is acceptable here: single trusted localhost deployment, creds already live in
  data-service env, returned only on a valid authenticated token — and the component
  previously shipped the same plaintext default anyway.
- **ADR-825-3 — GUID regenerated, compat broken (user-approved).** Rather than reuse GUID
  `24E78A17…` and silently rebind old panels by index into the new 2-input layout, the
  component gets a **new GUID**; old canvases show a clean missing-component placeholder.
  Documented as a breaking change.
- **ADR-825-4 — DataServiceUrl baked as a compile default** (`http://localhost:8000`), not
  a wired input, per "DataServiceUrl … not necessary." A future CONN-F can re-expose it.
- **ADR-825-5 — Typeable token via a non-persistent param.** Register `Token` as a custom
  `Param_String` subclass whose `Write` clears `PersistentData` before serialization. The
  value is usable live (feeds `SolveInstance`) but never written to the `.gh` — replacing
  the every-solve scrub. Honors the v8.2 Out-of-Scope "no token in .gh" rule.
- **ADR-825-6 — Auth gates the connection now.** In 824 auth never gated the bolt output
  (additive). In 825 the bundle *is* the connection, so a Rejected/Unreachable/NotAttempted
  auth means there is no bundle → the component reports the failure and emits no live
  connection (Database output carries a not-connected `ConnectionInfo` with the reason).

## Scope

**In:** data-service (`connectors.py`, `app.py`, tests), UI create-credential project field
(`ConnectorsScreen.jsx`, `connectorsApi.js`), DG.Core (`HeartbeatResult`,
`ConnectorHeartbeatClient`, `ConnectionInfo` reuse), DG.Grasshopper (`ConnectorComponent`,
new non-persistent param), DG.Tests, schema-propagation docs (`spec/DATABASE.md`,
release notes, `.github/copilot-instructions.md` if it names the ports).

**Out:** non-Grasshopper connectors (CONN-F01); per-credential analytics (CONN-F02);
pre-emptive status display (CONN-F03); binding *multiple* projects to one token; any change
to the Neo4j schema.

## Verification tiers

- **Headless-automatable:** data-service pytest (project-binding + bundle shape + host URI
  + 401 paths); `dotnet build -c Release` (0/0); `dotnet test` (HeartbeatResult/client
  bundle parsing, source assertions: 2-input registration, new GUID, non-persistent param,
  auth-gated output).
- **In-Rhino UAT (human):** live token → `Connected · Auth OK` + real bolt connect; saved
  `.gh` has no `dgc_`; typed token survives a solve (field is "active"). Carried in
  `825-UAT.md`.
