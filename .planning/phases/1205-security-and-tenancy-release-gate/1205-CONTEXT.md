# Phase 1205: Security and Tenancy Release Gate - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning

<domain>
## Phase Boundary

**Establish server-side authorization and fail-closed project boundaries** so that unauthorized
cross-project and direct-proxy access fail closed and secret handling is deployment-safe.

Five deliverables, from `.planning/ROADMAP.md` Phase 1205:

1. Server-side user/tenant authorization.
2. Direct Neo4j proxy exposure review and removal/restriction.
3. Secret/default-credential hardening and rotation procedure.
4. Unauthorized cross-project and direct-proxy tests.
5. Deployment boundary for connector heartbeat and privileged graph access.

**Requirements:** ALGN12-17, ALGN12-18, ALGN12-19, ALGN12-20 (`.planning/REQUIREMENTS.md:44-49`);
gate GATE12-05 (`.planning/REQUIREMENTS.md:57`).
**Package:** `ALIGN-P14` (`docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md:278,326,409,414,435`).
**Gate:** unauthorized cross-project and direct-proxy access fail closed; secret handling is deployment-safe.

**GATE12-05 scope:** 1205 blocks external multi-user evaluation only. It must not break local
single-user feature development or the paper's bounded claims. The two deployment profiles below
(D-07) exist to satisfy that constraint without weakening authorization (D-19).

**Out of scope:** migrating the Grasshopper C# Neo4j repositories off direct Bolt (D-07 defers it);
live Rhino UAT (Phase 40, GATE12-04); full RDF/OWL migration; manuscript edits.

</domain>

<upstream_corrections>
## Disk facts that change how this phase must be planned

Verified on disk 2026-09-28 during smart discuss. Planning must work from these, not from the
audit's shorter summary.

### Correction 1 — the browser holds Neo4j admin credentials and runs arbitrary Cypher
`ui-v2/entrypoint.sh` writes `neo4jUser`/`neo4jPassword` (default `12345678`) into the
browser-readable `config.js`; `ui-v2/src/lib/graphApi.js:5-12` also hardcodes them as `DEFAULTS`.
`executeCypher` (`graphApi.js:18`) posts any statement to `/neo4j/db/neo4j/tx/commit` with Basic
auth. There are **9 call sites**: `graphApi.js` ×6 (lines 45, 49, 65, 74, 84, 268 —
`fetchGraph`, `tagProjectNodes`, `updateNodeProp`, `fetchRules`, `fetchProjects`),
`modelApi.js` ×2 (39, 50), `inputGenApi.js` ×1 (71). Project isolation is only a predicate these
client-built queries choose to include.

### Correction 2 — authentication is localStorage only
`ui-v2/src/lib/auth.js` stores users in `localStorage.dg_users` with an unsalted-per-user
`SHA-256("dg_salt_" + password)` hash; the session is `localStorage.dg_current_user`. The server
never sees a user identity.

### Correction 3 — 62 of 65 data-service routes are unauthenticated
`data-service/app.py` declares 65 `@app.*` routes. Only `/connectors/heartbeat` (app.py:1431) and
`/designstate/capture` (app.py:2513, with a bound-project equality check, CAPTURE_PROJECT_MISMATCH
403) authenticate — both with `dgc_` connector tokens. Rule delete/supersede, knowledge CRUD,
validation publish/delete, identity bind, `/llm/settings` (writes encrypted API keys),
`/computgraph/*`, `/mcp` (Cypher, read-only guard only) all accept any caller.

### Correction 4 — the heartbeat hands the Neo4j admin password to connectors
`connector_heartbeat` (app.py:1450-1457) returns `Neo4jBundle(uri, user, password, database)` with
the admin credentials. The Grasshopper plugin then uses Bolt directly through
`DG/src/DG.Core/Data/Neo4j*Repository.cs` (5 files + `ValidationRunsQueryService.cs`).
Neo4j is `neo4j:5.26` **Community** (`neo4j/Dockerfile`) — there is no RBAC, so a restricted
database user is not available.

### Correction 5 — Grasshopper HTTP clients send no credential to data-service
Only `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs:48` sets an `Authorization` header.
`ComputgraphPublishClient.cs`, `ValidationPublishClient.cs` and the other GH components call
`http://localhost:8000` unauthenticated. D-04 therefore needs a C# change: those clients must send
the connector's `dgc_` token. GH-dependent code stays under `#if GRASSHOPPER_SDK`.

### Correction 6 — secrets are committed literally in docker-compose.yml
`NEO4J_AUTH: neo4j/12345678` (line 10), `NEO4J_PASSWORD: 12345678` (31, 51, 134), an n8n basic-auth
password default that looks like a real personal password (93, 139), `minioadmin`/`minioadmin`
(199-200), `POSTGRES_PASSWORD: speckle` (154, 190), and `change-me-*` defaults for
`LLM_MASTER_SECRET` (67) and `SPECKLE_SESSION_SECRET` (184). All of these are in git history.
`.env` is already gitignored (`.gitignore:1`).

### Correction 7 — n8n webhooks are open and accept caller-supplied service URLs
nginx routes `/n8n/` to n8n (ui-v2/nginx.conf). The UI calls the webhooks directly
(`graphApi.js:373,384`). `n8n/workflows/graph-query-mcp.json:43,47,63,95,188…` read
`$json.mcp_url` / `$json.data_service_url` from the webhook input before falling back to the
internal URL — an SSRF vector for any caller.

### Correction 8 — internal services are published on all host interfaces
Neo4j 7474/7687, dg-reasoner 8001, data-service 8000, n8n 5678, Ollama 11435, MinIO 9000/9001
are bound to `0.0.0.0`. dg-reasoner 8001 is published on purpose for the host DE-01 runner
(Phase 1201 D-11); data-service 8000 is what Grasshopper calls.

</upstream_corrections>

<decisions>
## Implementation Decisions

All 20 decisions below were proposed by Claude in smart discuss and accepted by the owner
("Accept all" on all four areas, 2026-09-28).

### Identity and authorization model (ALGN12-17)

- **D-01: data-service owns a server-side user store with scrypt hashes and an HttpOnly session cookie.**
  Passwords are hashed with stdlib `hashlib.scrypt` (per-user random salt, no new dependency).
  `/auth/login` issues an opaque random session token as an HttpOnly, SameSite=Strict cookie; the
  server stores only its hash. `/auth/logout` revokes it. `ui-v2/src/lib/auth.js` becomes a thin
  client of these endpoints. There is no external IdP.

- **D-02: The tenant is the project, authorized through server-side membership with owner/editor/viewer roles.**
  The `project` node property stays as the data partition. Authorization comes from a server-side
  user↔project membership record. `viewer` may read, `editor` may write, and `owner` may also
  manage membership.

- **D-03: Authorization is deny-by-default through a global FastAPI dependency and an explicit public-route allowlist.**
  Every route requires an authenticated principal unless it is on the allowlist (health, login,
  connector heartbeat, which uses its own token). A project taken from the path or body is checked
  against the principal's membership. No principal returns 401, and a non-member project returns 403.
  A body `project` that disagrees with a path `project` is rejected.

- **D-04: Two machine principal types exist — project-bound connector tokens and an internal service token.**
  `dgc_` connector tokens are accepted on the routes Grasshopper calls, scoped to their bound project
  (the `/designstate/capture` T-39-02 idiom, generalised). n8n → data-service calls (`/mcp`,
  `/llm/generate`, `/context/*`, `/execution-result*`) carry an internal service token header whose
  secret comes from the environment. Both principals are denied every route outside their scope.

- **D-05: Existing localStorage accounts are not migrated, and there is no open self-registration.**
  A bootstrap admin is created from environment secrets on first start. After that, an admin or a
  project owner invites users. The localStorage hashes are too weak to import.

### Graph access path and direct-proxy exposure (ALGN12-18)

- **D-06: The nginx /neo4j/ route is removed and the 9 browser Cypher sites become named, parameterized data-service endpoints.**
  There is no generic Cypher passthrough for the browser. Each replacement endpoint is
  project-authorized under D-03 and uses fixed parameterized Cypher. `executeCypher` and the Neo4j
  credentials are deleted from `ui-v2/src/lib/`.

- **D-07: A DG_DEPLOYMENT profile splits local from multi-user, and multi-user withholds the Neo4j bundle and Bolt.**
  `local` is the default: it keeps today's heartbeat Neo4j bundle and the GH direct-Bolt path as a
  documented trusted-local boundary. `multi-user` omits the Neo4j bundle from the heartbeat
  response, does not publish Bolt, and documents the GH direct-Bolt repositories as unsupported.
  Migrating the C# repositories to HTTP is deferred.

- **D-08: The UI stops calling n8n, data-service relays to n8n internally, and the workflows ignore caller-supplied URLs.**
  Authorized data-service routes relay rules-ingest and graph-query to the n8n webhooks over the
  internal network, reusing `call_n8n_sync` (app.py:198). nginx drops the `/n8n/` route. The n8n
  workflows use hardcoded internal URLs and no longer read `mcp_url`/`data_service_url` from input.
  Because the live n8n workflows drift from the repo, publishing them is a live step (see the
  `n8n-draft-vs-published-versions` memory: import, publish, restart).

- **D-09: Every internal service port binds to 127.0.0.1, and multi-user also drops the 7474/7687/5678 publishes.**
  7474, 7687, 8000, 8001, 5678, 9000, 9001 and 11435 bind to `127.0.0.1` in both profiles. Only
  8080 (UI) and 8090 (Speckle) stay routable. The dg-reasoner 8001 host publish (1201 D-11) and
  data-service 8000 for Grasshopper keep working on localhost.

### Secret and credential hardening (ALGN12-19)

- **D-10: All secrets move to a gitignored .env with a committed .env.example, and compose requires each one.**
  Compose uses the required-variable syntax `${VAR:?}`, so a missing required secret stops the
  stack from starting. `.env.example` carries placeholders
  only.

- **D-11: data-service refuses to start in multi-user when a secret equals a known default, and warns loudly in local.**
  The known-default list covers at least `12345678`, `change-me-*`, `minioadmin`, `speckle` and the
  committed n8n password. The list is kept in code and in `spec/SECURITY-BOUNDARY.md`.

- **D-12: Browser runtime configuration carries no secret, and the Speckle read token comes only from an authorized endpoint.**
  `config.js` loses the Neo4j and n8n credentials and `speckleReadToken`. An authenticated,
  project-authorized data-service endpoint serves the Speckle read token to the viewer. A test
  asserts that the generated `config.js` and the built `ui-v2/dist` bundle contain no credential
  key names and no known default values.

- **D-13: Committed secrets are treated as compromised and rotated, and git history is not rewritten.**
  A rotation runbook covers every secret in D-10, including re-encrypting stored LLM API keys when
  `LLM_MASTER_SECRET` changes. Rotating the live values is a **human checkpoint**: the owner enters
  the values, and they never appear in a brief, a worker prompt, a commit or a log. No
  `git filter-repo` or force push is used.

### Fail-closed test gate and contract (ALGN12-20, GATE12-05)

- **D-14: A machine-checked route inventory test classifies every FastAPI route and fails on any unclassified route.**
  A pytest test enumerates `app.routes`. Each route must either be on the public allowlist (D-17)
  or return 401 with no credential and 403 for a non-member project. A new route without a
  classification fails the suite, so new routes fail closed by default.

- **D-15: A two-user, two-project fixture drives the cross-project matrix across every project-scoped route.**
  User A is a member of P1 only, and a connector token is bound to P1. Every project-scoped route is
  called with P2 in the path or body, and every call must fail with 403 (or 404 where the existence
  of a P2 resource must not leak). A body/path project mismatch must also fail.

- **D-16: Direct-proxy exposure is tested statically and then checked live against rebuilt containers.**
  The static checks parse `ui-v2/nginx.conf` to assert there is no `/neo4j/` or `/n8n/` location,
  and parse `docker-compose.yml` to assert internal ports bind to `127.0.0.1`. A live checkpoint
  runs against rebuilt containers (see the `stale-docker-images-mask-code-state` memory):
  `/neo4j/` returns 404, unauthenticated API calls return 401, and Bolt is unreachable in the
  `multi-user` profile.

- **D-17: A new normative spec/SECURITY-BOUNDARY.md carries a machine-checked public-route allowlist.**
  It follows the `spec/SWRL-SUBSET.md` / `spec/REPRODUCIBILITY.md` pattern. It covers trust zones,
  the two deployment profiles, the three principal types (user session, connector token, internal
  service token), the known-default secret list and the rotation procedure. Its fenced allowlist
  block is the one the D-14 test reads. CLAUDE.md gets a pointer to it next to the other contracts.

- **D-18: The gate is judged in the multi-user profile.**
  GATE12-05: 1205 blocks external multi-user evaluation only. The pass condition is that D-14,
  D-15 and D-16 hold with `DG_DEPLOYMENT=multi-user`.

- **D-19: Authentication and authorization are enforced in both profiles, and only Bolt, ports and secret strictness vary.**
  The browser always logs in, and Grasshopper always sends its `dgc_` token. The `local` profile
  relaxes only the D-07 Bolt bundle, the D-09 multi-user port drops and the D-11 default-secret
  refusal.

- **D-20: Existing tests and the DE-01 host runners keep working under enforced auth through authorized fixtures.**
  Existing pytest suites authenticate through a fixture rather than bypassing the dependency. The
  host DE-01 runner reaches its legs with a connector or service token. No test-only auth bypass
  ships in the production image.

### Claude's Discretion

- The exact names and shapes of the D-06 replacement endpoints, and how the 9 call sites group
  into them.
- The storage location of users, sessions and memberships: Neo4j nodes under a project-isolated
  label, or a JSON file under `DATA_DIR` mirroring `connectors.py`. The planner should pick one and
  record its effect on the schema-propagation list if Neo4j is chosen.
- Session lifetime, idle timeout and the cookie name.
- The internal service token's header name.
- Whether the connector-token principal's route scope is enumerated in the spec's fenced block or
  derived from the route classification.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 1205 section (goal, deliverables, gate)
- `.planning/REQUIREMENTS.md:44-49,57` — ALGN12-17..20, GATE12-05
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md:37,162,278,326,409,414,435,475` — ALIGN-P14 package, risks R-11 and R-16
- `spec/SWRL-SUBSET.md`, `spec/REPRODUCIBILITY.md` — the machine-checked fenced-block pattern D-17 follows
- `spec/EVIDENCE-CONTRACT.md` — the evidence envelope that 1205 "requires" and must not change
- `data-service/connectors.py` — token minting, SHA-256-at-rest, and the JSON-under-DATA_DIR persistence idiom
- `data-service/app.py:1431-1458` (heartbeat), `2513-2560` (capture, the bound-project check idiom), `198` (`call_n8n_sync`)
- `ui-v2/nginx.conf`, `ui-v2/entrypoint.sh`, `ui-v2/src/lib/{auth,graphApi,modelApi,inputGenApi}.js`
- `docker-compose.yml`, `neo4j/Dockerfile`
- `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs`, `DG/src/DG.Grasshopper/Validation/{ComputgraphPublishClient,ValidationPublishClient}.cs`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `connectors.py`: `dgc_` token minting (`secrets.token_urlsafe(32)`), SHA-256 hash-at-rest,
  `authenticate_token`, `record_heartbeat`, and JSON persistence under `DATA_DIR`. This is the
  model for D-01 session tokens and D-04 principals.
- `_structured_error_response(message, how_to_fix, code, status)` in app.py: the house error
  shape for the 401/403 responses.
- The `/designstate/capture` bound-project equality check, with its generic "not authorized for
  the requested project" message (T-39-06, no project-existence leak), generalises into the D-03
  dependency.
- `call_n8n_sync` (app.py:198) already relays to n8n internally, which D-08 reuses.
- `llm_gateway.py` encrypts at rest under `LLM_MASTER_SECRET`, which the D-13 rotation procedure
  must handle.

### Established Patterns
- Normative specs with machine-checked fenced blocks, verified by a pytest that parses the block
  (SWRL-SUBSET, REPRODUCIBILITY).
- In-container pytest is authoritative: host runs fail 4 `test_dg_context.py` tests because the
  `neo4j` hostname resolves only inside compose. Docker exec from Git Bash needs `MSYS_NO_PATHCONV=1`.
- After a ui-v2 change: `docker compose build --no-cache design-grammars`. Container images can be
  stale, so verify the running code before trusting a live check.
- Neo4j HTTP `tx/commit` returns 200 with `errors[]`. This matters less once the browser path is
  gone, but it applies to any live Cypher verification.

### Integration Points
- A FastAPI global dependency, or a router-level dependency on `app`, for D-03.
- The ui-v2 login screen and `auth.js` switch to `/data-service/auth/*`. Every `fetch` needs
  `credentials: "include"` (same origin through nginx, so no CORS change).
- GH C# publish clients add the `Authorization: Bearer dgc_…` header (Correction 5).
- n8n workflow JSON under `n8n/workflows/` plus live publish (D-08).
- `docker-compose.yml`, `.env.example`, `ui-v2/entrypoint.sh`, `ui-v2/nginx.conf`.

</code_context>

<specifics>
## Specific Ideas

- The committed n8n basic-auth password looks like a real personal password. Treat it as
  compromised immediately, and rotate it wherever it is reused outside this repo. That part is the
  owner's action, outside this repository.
- Secrets never enter a DSH brief (CLAUDE.md DSH rules). Workers must not read `.env` or `.secrets/`.
- The D-16 live checkpoint and the D-13 rotation are both human checkpoints, like 1204 D-28.

</specifics>

<deferred>
## Deferred Ideas

- Migrating the Grasshopper C# Neo4j repositories from direct Bolt to data-service HTTP, which
  would make the GH path supported in `multi-user` (D-07).
- Neo4j Enterprise RBAC or per-tenant databases.
- External IdP / OIDC / SSO.
- TLS termination and Bolt TLS for a real external deployment. The current compose has
  `bolt_tls__level: DISABLED`.
- Audit logging of authorization decisions.
- Rate limiting and brute-force protection on `/auth/login`.

</deferred>
