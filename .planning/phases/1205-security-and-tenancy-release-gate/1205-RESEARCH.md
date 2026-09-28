# Phase 1205: Security and Tenancy Release Gate - Research

**Researched:** 2026-09-28
**Domain:** Server-side authorization (FastAPI deny-by-default), tenant/project isolation, secrets hardening, deployment-profile boundary
**Confidence:** HIGH (route inventory, C# call sites, compose, n8n, spec pattern all verified on disk); MEDIUM (compose profile mechanics, cookie/CSRF posture — general knowledge, one web-verified); LOW (none presented as fact — see Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01 through D-20, verbatim intent from `1205-CONTEXT.md` (see that file for full text; summarized
here for reference, not re-litigated):

- **D-01:** data-service owns a server-side user store with scrypt hashes and an HttpOnly session
  cookie (SameSite=Strict). `/auth/login` issues an opaque random session token; `/auth/logout`
  revokes it. `ui-v2/src/lib/auth.js` becomes a thin client. No external IdP.
- **D-02:** The tenant is the project, authorized through server-side membership with
  owner/editor/viewer roles. The `project` node property stays the data partition.
- **D-03:** Authorization is deny-by-default through a global FastAPI dependency and an explicit
  public-route allowlist. No principal -> 401; non-member project -> 403; body/path project
  mismatch -> rejected.
- **D-04:** Two machine principal types — project-bound `dgc_` connector tokens (Grasshopper) and
  an internal service token (n8n -> data-service: `/mcp`, `/llm/generate`, `/context/*`,
  `/execution-result*`). Both denied every route outside their scope.
- **D-05:** Existing localStorage accounts are NOT migrated; no open self-registration. Bootstrap
  admin from environment secrets; admin/owner invites users thereafter.
- **D-06:** The nginx `/neo4j/` route is removed; the 9 browser Cypher sites become named,
  parameterized, project-authorized data-service endpoints. `executeCypher` and Neo4j credentials
  deleted from `ui-v2/src/lib/`.
- **D-07:** A `DG_DEPLOYMENT` profile splits `local` (default, keeps heartbeat Neo4j bundle + GH
  direct-Bolt) from `multi-user` (omits Neo4j bundle, no Bolt publish, GH direct-Bolt repos
  documented unsupported). Migrating C# repos to HTTP is deferred.
- **D-08:** The UI stops calling n8n directly; data-service relays rules-ingest/graph-query to n8n
  internally via `call_n8n_sync`. nginx drops `/n8n/`. Workflows use hardcoded internal URLs, no
  longer read `mcp_url`/`data_service_url` from input. Live n8n publish is a manual step
  (import/publish/restart).
- **D-09:** Every internal service port binds to `127.0.0.1`; multi-user also drops
  7474/7687/5678 publishes. Only 8080 (UI) and 8090 (Speckle) stay routable. dg-reasoner 8001 and
  data-service 8000 keep working on localhost.
- **D-10:** All secrets move to a gitignored `.env` with a committed `.env.example`; compose
  requires them with `${VAR:?}`. A missing required secret stops the stack from starting.
- **D-11:** data-service refuses to start in `multi-user` when a secret equals a known default
  (`12345678`, `change-me-*`, `minioadmin`, `speckle`, the committed n8n password), and warns
  loudly in `local`. List kept in code and in `spec/SECURITY-BOUNDARY.md`.
- **D-12:** Browser runtime config carries no secret; `config.js` loses Neo4j/n8n credentials and
  `speckleReadToken`. An authenticated, project-authorized endpoint serves the Speckle read token.
  A test asserts generated `config.js` and built `ui-v2/dist` contain no credential key names or
  known defaults.
- **D-13:** Committed secrets are treated as compromised and rotated; git history is NOT rewritten.
  Rotation runbook covers every D-10 secret including re-encrypting stored LLM API keys when
  `LLM_MASTER_SECRET` changes. Rotating live values is a **human checkpoint** — values never enter
  a brief, worker prompt, commit, or log. No `git filter-repo`/force push.
- **D-14:** A machine-checked route inventory test enumerates `app.routes`; each must be on the
  public allowlist (D-17) or return 401 (no credential) / 403 (non-member project). An
  unclassified new route fails the suite.
- **D-15:** A two-user, two-project fixture drives the cross-project matrix across every
  project-scoped route (P2 in path/body from a P1-scoped caller must 403, or 404 where existence
  must not leak). Body/path project mismatch must also fail.
- **D-16:** Direct-proxy exposure tested statically (parse `nginx.conf` for no `/neo4j/`/`/n8n/`;
  parse `docker-compose.yml` for `127.0.0.1` bindings) AND live against rebuilt containers
  (`/neo4j/` -> 404, unauthenticated API -> 401, Bolt unreachable in `multi-user`).
- **D-17:** A new normative `spec/SECURITY-BOUNDARY.md` follows the `spec/SWRL-SUBSET.md` /
  `spec/REPRODUCIBILITY.md` machine-checked fenced-block pattern: trust zones, two deployment
  profiles, three principal types, known-default secret list, rotation procedure. CLAUDE.md gets a
  pointer to it.
- **D-18:** The gate (GATE12-05) is judged in the `multi-user` profile — D-14/D-15/D-16 must hold
  with `DG_DEPLOYMENT=multi-user`.
- **D-19:** Authentication and authorization are enforced in BOTH profiles; only Bolt, ports, and
  secret strictness vary between `local` and `multi-user`. Browser always logs in; Grasshopper
  always sends its `dgc_` token.
- **D-20:** Existing tests and the DE-01 host runners keep working under enforced auth through
  authorized fixtures, never a bypass. No test-only auth bypass ships in the production image.

### Claude's Discretion

- The exact names/shapes of the D-06 replacement endpoints and how the 9 call sites group into
  them.
- The storage location of users/sessions/memberships (Neo4j nodes vs. JSON under `DATA_DIR`) —
  record its effect on the Schema Change Propagation list if Neo4j is chosen.
- Session lifetime, idle timeout, and the cookie name.
- The internal service token's header name.
- Whether the connector-token principal's route scope is enumerated in the spec's fenced block or
  derived from route classification.

### Deferred Ideas (OUT OF SCOPE)

- Migrating the Grasshopper C# Neo4j repositories from direct Bolt to data-service HTTP (would
  make the GH path supported in `multi-user`, D-07).
- Neo4j Enterprise RBAC or per-tenant databases.
- External IdP / OIDC / SSO.
- TLS termination and Bolt TLS for a real external deployment (compose currently has
  `bolt_tls__level: DISABLED`).
- Audit logging of authorization decisions.
- Rate limiting and brute-force protection on `/auth/login`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALGN12-17 | Ordinary API and graph access enforce server-side user/tenant authorization rather than relying on client-side auth and project predicates | Route Inventory (all 65 routes classified by project source), Principal → Route Scope Matrix, Architecture Pattern 1 (global `Depends(require_principal)` via router refactor), Storage Choice section (D-01/D-02 persistence design) |
| ALGN12-18 | Direct Neo4j proxy exposure is removed or restricted behind an authorized server boundary | D-06 Browser Cypher Call-Site table (9 sites → 7 named endpoints), nginx.conf findings (`/neo4j/` route to be removed), docker-compose.yml port-binding findings (D-09), Deployment Profile Mechanics (D-07 override-file approach) |
| ALGN12-19 | Compose/default credentials and secrets are hardened, rotated, and excluded from browser-readable runtime configuration | docker-compose.yml committed-secret inventory (Correction 6, verified), Speckle Read Token Flow finding (D-12 mostly already server-side), LLM_MASTER_SECRET Rotation section (D-13), entrypoint.sh/config.js findings |
| ALGN12-20 | Unauthorized cross-project and direct-proxy access tests fail closed | Test Impact section (D-20 fixture gap across 8+ test files + DE-01 runner), Validation Architecture (Wave 0 gaps: test_route_inventory.py, test_cross_project_matrix.py, test_static_proxy_boundary.py), Common Pitfalls 1-2 (routes with no project source that need special-case test coverage) |
| GATE12-05 | Phase 1205 is release-blocking for external multi-user evaluation only | Deployment Profile Mechanics (override-file design keeps `local` behavior unchanged), Security Domain ASVS table, D-18/D-19 reflected throughout Architecture Patterns and Route Inventory notes |
</phase_requirements>

## Summary

Phase 1205 turns 65 currently-open FastAPI routes plus a direct browser→Neo4j Cypher channel
into a deny-by-default, project-authorized surface, without breaking the two machine principals
that already exist (`dgc_` connector tokens, minted in `connectors.py`) or the n8n relay path
(`call_n8n_sync`). The codebase already contains every idiom the phase needs to reuse: JSON-file
token storage with SHA-256-at-rest (`connectors.py`), a project-bound-token equality check
(`/designstate/capture`), a house structured-error shape (`_structured_error_response`), and a
machine-checked normative-spec pattern with an HTML-comment-delimited fenced block read verbatim
by a pytest (`spec/REPRODUCIBILITY.md`, `spec/SWRL-SUBSET.md`). No new Python package is required
for D-01 (`hashlib.scrypt` is stdlib; `cryptography` is already a dependency for `llm_gateway.py`).

The route audit below surfaces several **new** findings beyond CONTEXT.md's 8 corrections that
the planner must account for: `POST /create_node/` is an unscoped generic node creator with no
project field at all; `/mcp`'s `neo4j_query`/`neo4j_schema` tools read across **all** projects
with no project filter (worse than the browser Cypher problem, because it is designed to survive
this phase as an n8n-internal route); `DELETE /connectors/{id}/credentials/{cred}` has no project
binding so any authenticated user could revoke another project's connector credential;
`GET /execution-result/latest/{workflow}` is a **global last-write-wins** key shared by every
caller of a given workflow name, which is a live cross-user race condition, not just an
authorization gap, once concurrent multi-user access exists; and three `/knowledge/note/{id}`
routes and `/execution-result/{id}` have no project or ownership binding whatsoever. The D-14
route-classification test needs an explicit disposition for every one of these, not just the
happy-path project-in-path/body cases D-15's matrix already covers.

The Speckle read-token flow (D-12) turns out to already be mostly server-side: `ModelScreen.jsx`
reads `view.readToken` from the `/validation/view/{project}/...` response, which `app.py`
populates from `SPECKLE_READ_TOKEN`/persisted settings — the browser has **never** needed
`config.js`'s `speckleReadToken` for the model viewer. D-12 is therefore mostly a deletion (drop
it from `entrypoint.sh`/`config.js`) plus confirming `/validation/view/*` is project-authorized
under D-03, not new plumbing.

**Primary recommendation:** Implement D-03's authorization as a single FastAPI dependency
(`Depends(require_principal)`) applied globally via `app.dependency_overrides`-free
`Depends(...)` on a shared `APIRouter` wrapping every existing route (see Architecture Patterns),
backed by a route-classification table that is itself the machine-checked fenced block in the new
`spec/SECURITY-BOUNDARY.md`, mirroring `spec/SWRL-SUBSET.md`'s pattern exactly. Store users,
sessions and connector/service-token principals as sibling JSON files under `DATA_DIR` next to
`connector-credentials.json` (D-01/D-04), not as new Neo4j nodes — this avoids touching the
Schema Change Propagation list and keeps the persistence idiom consistent with the one piece of
this codebase (`connectors.py`) that already does exactly this job correctly.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| User/session authentication (D-01) | API/Backend (data-service) | Browser (cookie storage only) | Server must own credential verification; browser is a thin cookie-bearing client |
| Project/tenant membership check (D-02/D-03) | API/Backend | — | Single dependency gate; Neo4j `project` property stays the data partition, not the authority |
| Connector/service machine auth (D-04) | API/Backend | Browser (issues tokens via UI) | Grasshopper and n8n are non-browser callers; token verification is server-side |
| Graph query surface (D-06) | API/Backend | Database/Storage (Neo4j) | Browser loses all direct Neo4j access; every query becomes a named, parameterized endpoint |
| Direct-proxy removal (D-06/D-09) | CDN/Static (nginx config) | API/Backend | nginx is the enforcement point for route removal; data-service enforces auth on what remains |
| Deployment profile (D-07) | API/Backend + CDN/Static (compose) | — | Branch lives in both the compose file (ports) and data-service code (heartbeat payload) |
| Secret handling (D-10/D-11/D-12) | API/Backend + CDN/Static (entrypoint.sh) | Browser (must receive none) | Secrets are minted/read server-side; the browser config generator is where a leak would occur |
| Test gate (D-14/D-15/D-16) | API/Backend (pytest) | CDN/Static (nginx/compose static parse) | Fail-closed is a backend property; static checks cover the proxy/compose surface |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib.scrypt` (stdlib) | Python 3.11+ (already in use) | Password hashing (D-01) | No new dependency; scrypt is memory-hard and stdlib since 3.6, matches D-01's explicit "no new dependency" decision |
| `secrets.token_urlsafe` (stdlib) | — | Session token / token generation | Already used identically in `connectors.py:143` for `dgc_` tokens |
| `cryptography` (Fernet) | already pinned, unversioned in `requirements.txt` [VERIFIED: data-service/requirements.txt] | LLM API key encryption at rest, unchanged by this phase except rotation | Already the phase's only crypto dependency; D-13 rotation reuses it, does not replace it |
| FastAPI `Depends` | already pinned (`fastapi`, unversioned in requirements.txt) [VERIFIED: data-service/requirements.txt] | Global auth dependency (D-03) | Native FastAPI mechanism; no third-party auth framework needed for this phase's scope |
| `starlette.requests.Request` | transitive via fastapi | Reading cookies/headers in the dependency | Already imported and used in `app.py` (`connector_heartbeat`, `capture_design_state`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| none | — | — | No new package is required anywhere in this phase's stack. Confirm this holds at plan time by re-running `pip index versions` only if a plan actually proposes adding one. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `scrypt` password hashing | `passlib`/`bcrypt` package | New dependency for no capability gain; D-01 explicitly rejected this |
| JSON-under-DATA_DIR for users/sessions | Neo4j `:User`/`:Session` nodes | Touches the Schema Change Propagation list (cypher_template.txt, dataset_schema.json, SHACL shapes, LPG-OWL mapping) for data that is not part of the design/validation domain model; JSON avoids all of that and matches the existing `connectors.py` idiom |
| Custom FastAPI dependency | `fastapi-users` / `authlib` | Both pull in OAuth/OIDC machinery D-05 explicitly excludes ("no external IdP"); would be net-new attack surface for a single-tenant-of-tenants app |
| Docker Compose `profiles:` for D-07 | Compose override file (`-f docker-compose.yml -f docker-compose.multi-user.yml`) | `profiles:` toggles whether a service *starts at all*; it cannot conditionally change one service's `ports:` list. Port arrays do not merge across `-f` layers — an override file must fully redeclare the array (empty/absent to drop a publish) [CITED: docker compose reference + community override-file behavior]. Use override file, not `profiles:`, for D-09's port-drop behavior. |

**Installation:** none required.

**Version verification:** `cryptography`, `fastapi`, `httpx`, `pydantic>=2.7,<3`, `neo4j`, `specklepy==3.2.4`, `uvicorn`, `jsonschema>=4.20,<5` are already pinned in `data-service/requirements.txt` [VERIFIED: data-service/requirements.txt]; this phase adds no new line to that file.

## Package Legitimacy Audit

**Not applicable — no new external packages are introduced by this phase's decisions (D-01 through D-20 all name stdlib or already-installed libraries).** If a plan later proposes a package (e.g., a rate-limiter for the deferred brute-force item), run the full Package Legitimacy Gate at that time.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — | — | — | — | — | — | No new packages this phase |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Browser (session cookie only, no Neo4j/n8n creds)
   |
   | POST /data-service/auth/login  ->  sets HttpOnly SameSite=Strict cookie
   | every subsequent fetch: credentials:"include"
   v
nginx (8080)                                   nginx routes REMOVED by D-06/D-08:
   |-- /data-service/*  ---------------------+     /neo4j/*  (deleted)
   |-- /llm/*  (existing passthrough, kept)  |     /n8n/*   (deleted)
   |-- /reasoner/*  (existing passthrough)   |
   v                                          |
data-service:8000 (FastAPI, single `app`)     |
   |                                          |
   |  [ NEW: global Depends(require_principal) on every route,      ]
   |  [   public allowlist = health/login/heartbeat (D-03/D-17)     ]
   |                                          |
   |-- session cookie  -> user principal -> project-membership check (D-02)
   |-- Authorization: Bearer dgc_...  -> connector principal -> bound-project check (D-04, reuses /designstate/capture idiom)
   |-- X-<internal-token-header>  -> internal-service principal -> n8n-only routes (D-04)
   |                                          |
   |-- named graph endpoints (D-06) --------- replace the 9 browser executeCypher call sites
   |         (fetchGraph/tagProjectNodes/updateNodeProp/fetchRules/fetchProjects/
   |          fetchRuleDetails/fetchEntityStatuses/fetchAcceptedCandidates)
   |                                          |
   |-- call_n8n_sync() [existing, app.py:198] internal HTTP only, hardcoded URL
   v                                          v
Neo4j (7474/7687, 127.0.0.1-only in both      n8n:5678 (127.0.0.1-only; workflows read
profiles per D-09)                            hardcoded internal URLs, no caller mcp_url/
   ^                                          data_service_url per D-08)
   |
   | Bolt, direct — ONLY in `local` profile (D-07/D-19)
   |
Grasshopper (DG.Core Data/*Repository.cs, unchanged this phase)
   |
   | HTTP + Authorization: Bearer dgc_... (NEW — Correction 5 fix, D-04)
   v
data-service /connectors/heartbeat, /validation/publish, /computgraph/publish
```

### Recommended Project Structure
```
data-service/
├── auth.py                 # NEW: users.json/sessions.json load/save, scrypt hash, session
│                            #   cookie mint/verify, require_principal dependency (D-01..D-04)
├── app.py                  # adds Depends(require_principal) to the router; route bodies
│                            #   unchanged except reading `principal` where needed
├── connectors.py            # UNCHANGED — reused as-is for dgc_ token verification
├── tests/
│   ├── conftest.py          # NEW: authorized_client fixture (D-20) — wraps TestClient with
│   │                          a bootstrap-admin session cookie or service token
│   ├── test_route_inventory.py   # NEW: D-14 — enumerates app.routes, asserts classification
│   └── test_cross_project_matrix.py  # NEW: D-15 — two-user/two-project fixture
spec/
└── SECURITY-BOUNDARY.md     # NEW: D-17, fenced allowlist block read by test_route_inventory.py
ui-v2/src/lib/
├── auth.js                  # REWRITTEN: thin client of /auth/login, /auth/logout
├── graphApi.js               # executeCypher() and Neo4j DEFAULTS DELETED; named endpoints added
├── modelApi.js               # fetchRuleDetails/fetchEntityStatuses converted to named endpoints
└── inputGenApi.js            # fetchAcceptedCandidates converted to named endpoint
docker-compose.yml            # ${VAR:?err} for required secrets; ports bind 127.0.0.1 (D-09)
docker-compose.multi-user.yml # NEW: override file — port list overrides, DG_DEPLOYMENT=multi-user
.env.example                  # NEW (does not exist today — verified absent on disk)
```

### Pattern 1: Deny-by-default global dependency on an un-routered `app`
**What:** `data-service/app.py` declares all 65 routes directly on `app = FastAPI()` with plain
`@app.get/post/put/delete` decorators — there is no `APIRouter` split today [VERIFIED:
data-service/app.py, 65 `@app.*` decorators enumerated by direct line-by-line grep].
**When to use:** FastAPI supports adding a dependency to every route on an existing `app` two
ways without restructuring the file: (a) `app.router.dependencies.append(Depends(require_principal))`
mutates the dependency list FastAPI already built at decoration time — verify this applies
retroactively in the installed FastAPI version before relying on it; the safer, version-independent
option is (b) wrap route registration by re-decorating, or simplest of all, add
`dependencies=[Depends(require_principal)]` to a new `app.add_api_route`-free approach: **create
one `APIRouter(dependencies=[Depends(require_principal)])` and change every `@app.get(...)` to
`@router.get(...)`, then `app.include_router(router)` once at the bottom.** This is a mechanical,
scriptable rename (regex `@app\.(get|post|put|delete)\(` -> `@router.\1(`) across one file, not a
per-route edit, and it is the version-safe way to guarantee the dependency runs before every
handler, including ones added after this phase ships (satisfying D-14's "new route without a
classification fails the suite" requirement, since an un-routered route literally cannot exist
after this refactor — everything is `@router.*` by convention).
**Example:**
```python
# data-service/auth.py (new)
from fastapi import APIRouter, Depends, Request, HTTPException

PUBLIC_PATHS = {"/", "/connectors/heartbeat"}  # + /auth/login, /auth/logout — see D-17 allowlist

async def require_principal(request: Request):
    if request.url.path in PUBLIC_PATHS:
        return None
    # 1. session cookie -> user principal
    # 2. Authorization: Bearer dgc_... -> connector principal
    # 3. X-<internal-header> -> internal-service principal
    # else: 401
    ...
```
```python
# data-service/app.py — mechanical decorator swap, body unchanged
router = APIRouter(dependencies=[Depends(require_principal)])

@router.get("/validation/runs/{project}")
def get_validation_runs(project: str, principal=Depends(require_principal)):
    _authorize_project(principal, project)  # 403 if not a member
    ...

app.include_router(router)
```

### Pattern 2: Body-vs-path project mismatch without double-consuming the body
**What:** FastAPI/Pydantic already parses the body into the route's declared model exactly once;
a dependency added via `Depends(require_principal)` that only reads `request.url.path` and headers
(never `await request.body()`) cannot double-consume anything. The double-read risk only exists if
the dependency ALSO wants the parsed body's `project` field to cross-check against a path param —
solve this with a **second, route-local dependency** that takes the already-validated Pydantic
model as its own parameter (FastAPI resolves both from the same cached body), not by re-parsing
the raw request:
```python
def _check_body_path_project_match(project: str, payload: ValidationPublishRequest):
    if hasattr(payload, "project") and payload.project != project:
        raise _structured_error_response(...)
```
This only applies to the ONE route in the audit that has both a path `project` and a body
`project` — `PUT /integration/speckle/project/{project}` — and there `SpeckleProjectConfigPayload`
has **no** `project` field [VERIFIED: app.py:233-238], so there is currently no real
mismatch case in the existing route set; D-03's "body project that disagrees with path project is
rejected" rule is a defensive general rule for future routes, not a fix for an existing bug.
**When to use:** any future route that accepts project in both path and body.

### Pattern 3: Fenced-block machine-checked spec (D-17)
**What:** `spec/REPRODUCIBILITY.md` and `spec/SWRL-SUBSET.md` both wrap a normative list in HTML
comments (`<!-- reproducibility:llm-call-sites:start -->` / `...:end`) around a fenced code block,
one line per item in a fixed `field|field|field` format, and a pytest
(`tools/de01/tests/test_reproducibility_scope_drift.py`) reads the block verbatim and cross-checks
it against a static AST scan of the source [VERIFIED: spec/REPRODUCIBILITY.md:156-174].
**When to use:** `spec/SECURITY-BOUNDARY.md`'s D-17 allowlist should follow this exact shape:
```markdown
<!-- security-boundary:public-routes:start -->
```
GET|/|none
POST|/connectors/heartbeat|connector-token
POST|/auth/login|none
POST|/auth/logout|session
```
<!-- security-boundary:public-routes:end -->
```
D-14's `test_route_inventory.py` reads this block and asserts every route in `app.routes` is
either in it or passes the 401/403 behavior check — mirroring
`test_reproducibility_scope_drift.py`'s "agree in both directions" assertion (nothing in the code
that isn't in the block, nothing in the block that isn't in the code).

### Anti-Patterns to Avoid
- **Per-route manual auth checks:** Do not hand-add an `if not principal: raise 401` to each of
  the 65 route bodies — this is exactly the pattern that produced "62 of 65 unauthenticated" in
  the first place (2 routes got it, 63 didn't). Use the router-level `Depends` (Pattern 1).
- **Trusting `project` from an unvalidated source:** `/mcp`'s `neo4j_query` tool has no project
  parameter at all — do not attempt to retrofit project-scoping onto arbitrary caller-supplied
  Cypher; instead classify `/mcp` as internal-service-token-only (D-04) so only n8n can reach it,
  and keep the existing `is_write_query` read-only guard as defense in depth, not as the
  authorization boundary.
- **Reusing `record_heartbeat` for authorization checks that shouldn't stamp liveness:** already
  correctly avoided in `/designstate/capture`, which calls `authenticate_token` instead
  [VERIFIED: app.py:2523-2525 docstring]. Any new connector-token check added for D-04 should
  follow the same `authenticate_token` (not `record_heartbeat`) convention unless the route IS a
  liveness signal.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | A custom KDF or plain SHA-256 (the exact mistake `ui-v2/src/lib/auth.js` already made) | `hashlib.scrypt` with `os.urandom` per-user salt | scrypt is memory-hard; unsalted SHA-256 (the current bug) is why D-05 refuses to migrate existing accounts |
| Session token | A JWT library or hand-rolled signed cookie | Opaque `secrets.token_urlsafe(32)` + server-side session store, hash-at-rest (mirrors `connectors.py`'s token pattern exactly) | No verification-key management, no algorithm-confusion attack surface, and it is already the pattern this codebase trusts for `dgc_` tokens |
| CSRF defense for cookie auth | A custom CSRF token pair | `SameSite=Strict` cookie (D-01) + a same-origin check via a required custom header (e.g. `X-Requested-With`) on state-changing requests, since nginx already proxies same-origin (no CORS) | `SameSite=Strict` blocks cross-site cookie-carrying requests entirely for this app's threat model (no cross-site top-level navigation flow needs the cookie); a same-origin custom-header check is the standard defense-in-depth for the remaining risk (data exfil via response, not applicable to POST-only mutations) without pulling in a CSRF library |
| Encrypted-at-rest secret rotation | A bespoke re-encrypt script | Extend `llm_gateway.py`'s existing Fernet decrypt-with-old-key/encrypt-with-new-key round trip (the module already isolates `LLM_MASTER_SECRET` derivation in one place) | The encryption code already exists and is tested; rotation is "decrypt with old derived key, re-encrypt with new derived key," not new crypto design |

**Key insight:** every primitive this phase needs (token minting, hash-at-rest, structured error
shape, bound-project equality check, encrypted-settings-at-rest) already has one correct,
tested implementation somewhere in `data-service/`. The work is applying the existing idiom
uniformly, not inventing a new one.

## Route Inventory (verified 2026-09-28 by direct line read of `data-service/app.py`)

65 `@app.*` routes confirmed [VERIFIED: data-service/app.py, decorator+signature pairs at every
line below]. `project` column: `path` = path parameter, `body` = Pydantic model field, `query` =
plain query parameter, `token` = derived from an already-authenticated connector token, `—` = no
project source of any kind found in path, body, or query.

| # | Method | Path | project source | Notes / risk |
|---|--------|------|----------------|---------------|
| 1 | GET | `/` | — | health/root — allowlist |
| 2 | POST | `/create_node/` | **—** | **NEW finding:** generic label/name node creator, zero project scoping. Likely a dev-era leftover. Flag for removal or explicit admin-only + project-required rewrite. |
| 3 | GET | `/integration/speckle/project/{project}` | path | |
| 4 | GET | `/settings/speckle` | — (global) | admin/owner-only, not project-scoped |
| 5 | PUT | `/settings/speckle` | — (global) | writes Speckle tokens; admin-only |
| 6 | GET | `/llm/settings` | — (global) | masked response; still classify (not public) |
| 7 | PUT | `/llm/settings` | — (global) | writes encrypted API key; admin-only |
| 8 | DELETE | `/llm/settings` | — (global) | admin-only |
| 9 | POST | `/llm/generate` | — (`GenerateRequest` has no project field) [VERIFIED: llm_gateway.py:30-44] | reachable directly via nginx `location /llm/` passthrough (Correction-adjacent finding — nginx proxies straight to data-service, so D-03 is the only thing that will ever gate this once shipped) |
| 10 | POST | `/llm/settings/test` | — (global) | admin-only |
| 11 | GET | `/llm/models` | — (query `provider`) | admin-only-ish |
| 12 | GET | `/connectors` | — (registry-level, cross-project by design) | lists ALL connectors + credential summaries for every project; never exposes tokens [VERIFIED: connectors.py:288-316] — classify as owner/admin, not per-project |
| 13 | POST | `/connectors/{connector_id}/credentials` | body (`CredentialCreatePayload.project`, optional) | should require caller to be owner/editor of the named project |
| 14 | DELETE | `/connectors/{connector_id}/credentials/{credential_id}` | **—** | **NEW finding:** no project binding at all — any authenticated user can revoke any project's connector credential. D-03/D-15 need an explicit rule here (e.g. resolve the credential's stored `project` first, then authorize). |
| 15 | POST | `/connectors/heartbeat` | token (echoed from stored credential) | existing connector-token auth; allowlisted as its own principal type |
| 16 | GET | `/reasoner/settings` | — (global) | admin-only |
| 17 | PUT | `/reasoner/settings` | — (global) | admin-only |
| 18 | POST | `/reasoner/consistency` | body (`ReasonerConsistencyRequest.project`) [VERIFIED: app.py:1499] | |
| 19 | POST | `/computgraph/context/pull` | body (`ComputgraphContextPullRequest.project`) [VERIFIED: app.py:1556] | |
| 20 | POST | `/computgraph/recognize` | body, **optional** (`RecognizeRequest.project: str \| None = None`) [VERIFIED: app.py:1591] | **NEW finding:** the only computgraph route where project is optional — inconsistent with siblings. Planner must decide: require it, or treat missing-project calls as failing closed (403) rather than silently unscoped. |
| 21 | POST | `/computgraph/publish` | body (`ComputgraphPublishRequest.project`) [VERIFIED: app.py:1669] | GH calls this via `ComputgraphPublishClient.cs` |
| 22 | POST | `/computgraph/validate` | body (`ComputgraphValidateRequest.project`) [VERIFIED: app.py:1710] | |
| 23 | POST | `/computgraph/consult` | body (`ComputgraphConsultRequest.project`) [VERIFIED: app.py:1761] | |
| 24 | POST | `/computgraph/generate-inputs` | body (`ComputgraphGenerateInputsRequest.project`) [VERIFIED: app.py:1805] | UI calls via `inputGenApi.js` |
| 25 | POST | `/computgraph/candidates/accept` | body (`ComputgraphAcceptCandidateRequest.project`) [VERIFIED: app.py:1901] | UI's only writer in `inputGenApi.js` |
| 26 | POST | `/context/assemble` | body (`dg_context.ContextAssembleRequest`) [ASSUMED — class body not fully read this session; docstring at app.py:113-117 states "identical param contract" to `/context/debug`, which does carry `project`] | n8n-facing |
| 27 | GET | `/context/debug` | query (`project: str`) [VERIFIED: app.py:1995] | |
| 28 | POST | `/context/generate-cypher` | body (`dg_context.GenerateCypherRequest`) [ASSUMED — same basis as #26] | the one n8n-facing prompt->cypher route |
| 29 | POST | `/identity/mint` | body (`payload.project` used at call site) [VERIFIED: app.py:2065] | |
| 30 | GET | `/identity/resolve` | query (`project: str`) [VERIFIED: app.py:2074] | |
| 31 | POST | `/identity/bind` | body (`payload.project` used at call site) [VERIFIED: app.py:2104] | |
| 32 | GET | `/identity/{dg_id}/representations` | query (`project: str`) [VERIFIED: app.py:2114] | |
| 33 | DELETE | `/identity/{dg_id}/representations` | query (`project: str`) [VERIFIED: app.py:2121] | |
| 34 | POST | `/identity/{dg_id}/properties` | query (`project: str`, sibling to path `dg_id` and body `payload`) [VERIFIED: app.py:2136] | project is a query param, not path or body — the dependency must read `request.query_params` here, not assume path/body only |
| 35 | GET | `/identity/{dg_id}/properties` | query (`project: str`) [VERIFIED: app.py:2160] | |
| 36 | PUT | `/integration/speckle/project/{project}` | path (+ body `SpeckleProjectConfigPayload`, which has **no** project field — no mismatch possible) [VERIFIED: app.py:233-238, 2176] | |
| 37 | POST | `/designstate/capture` | body (`DesignStateCaptureRequest.project`) + **existing** connector-token bound-project equality check (403 `CAPTURE_PROJECT_MISMATCH`) [VERIFIED: app.py:2514-2558] | D-03's dependency must recognize this route already does its own authorization — do not double-wrap; reuse the idiom, don't duplicate the check |
| 38 | POST | `/validation/publish` | body (`ValidationPublishRequest.project`) [VERIFIED: app.py:290-291, 2591-2592] | GH calls this via `ValidationPublishClient.cs` |
| 39 | GET | `/validation/runs/{project}` | path | UI calls via `modelApi.js` |
| 40 | DELETE | `/validation/run/{project}/{run_id}` | path | |
| 41 | GET | `/validation/view/{project}` | path | feeds Speckle `readToken` to the viewer (D-12) |
| 42 | GET | `/validation/view/{project}/{run_id}` | path | UI calls via `modelApi.js` |
| 43 | GET | `/validation/view/{project}/{run_id}/{rule_id}` | path | |
| 44 | POST | `/mcp` | mixed — `neo4j_schema` and `neo4j_query` tools have **no project scoping at all**; `gh_get_context` reads `project` from `arguments`; `gh_get_selection`/`gh_preview_structure`/`gh_clear_preview` have none (operate on the live singleton GH canvas) [VERIFIED: app.py:2860-2945] | **Critical finding:** `neo4j_query` accepts arbitrary read-only Cypher against ALL projects — same class of problem as the browser's `executeCypher`, just server-side. Must become internal-service-token-only under D-04, never reachable by a user session, ever. |
| 45 | POST | `/execution-result` | — (`ExecutionResult` has no project field) [VERIFIED: app.py:223-230] | n8n callback target; internal-service-token candidate |
| 46 | GET | `/execution-result/{execution_id}` | **—** | **NEW finding:** no project or user binding — any authenticated caller who knows/guesses an `execution_id` can read another user's LLM output. Polled directly by the browser (`graphApi.js` `callWorkflow`/`pollExecution`), so it cannot simply become internal-service-token-only; needs its own authorization design (e.g., bind execution_id to the session that started it). |
| 47 | GET | `/execution-result/latest/{workflow}` | **—** | **NEW finding, worse than #46:** `workflow` is a shared key ("rules-ingest"/"graph-query") with no per-user or per-project scoping at all — this is a **global last-write-wins slot**. Under concurrent multi-user use, two users polling this concurrently can see each other's in-flight result. This is a correctness bug exposed by GATE12-05's multi-user scope, not only an authorization gap — flag prominently for the planner as a Common Pitfall, likely needs a design change (key by session or by a client-supplied request id), not just an auth wrapper. |
| 48 | POST | `/knowledge/ingest/folder` | body (`FolderIngestRequest.project`) [VERIFIED: app.py:326-328] | |
| 49 | GET | `/knowledge/notes/{project}` | path | |
| 50 | GET | `/knowledge/note/{note_id}` | **—** | **NEW finding:** no project param — cross-project note read if `note_id` is known/enumerable |
| 51 | PUT | `/knowledge/note/{note_id}` | **—** (`NoteUpdateRequest` has no project field) [VERIFIED: app.py:331-334] | same gap as #50, write instead of read |
| 52 | DELETE | `/knowledge/note/{note_id}` | **—** | same gap as #50 |
| 53 | GET | `/rules/{project}/{rule_id}/delete-preview` | path | UI calls via `graphApi.js` |
| 54 | DELETE | `/rules/{project}/{rule_id}` | path | UI calls via `graphApi.js` |
| 55 | POST | `/rules/resolve-deletion` | body (`RuleDeleteResolvePayload.project`) [VERIFIED: app.py:3265] | |
| 56 | POST | `/rules/bulk-delete` | body (`RuleBulkDeletePayload.project`) [VERIFIED: app.py:3311] | |
| 57 | POST | `/rules/check-conflict` | body (`RuleConflictCheckPayload.project`) [VERIFIED: app.py:3372] | |
| 58 | POST | `/rules/supersede` | body (`RuleSupersedePayload.project`) [VERIFIED: app.py:3502] | |
| 59 | POST | `/rules/accept-overlap` | body (`RuleAcceptOverlapPayload.project`) [VERIFIED: app.py:3609] | |
| 60 | GET | `/knowledge/sessions/{project}` | path | |
| 61 | POST | `/design-rule-sessions` | body (`DesignRuleSessionPayload.project`) [VERIFIED: app.py:3696] | UI calls via `graphApi.js` |
| 62 | GET | `/design-rule-sessions/{project}` | path | UI calls via `graphApi.js` |
| 63 | POST | `/knowledge/update/match` | body (`UpdateMatchRequest.project`) [VERIFIED: app.py:339] | |
| 64 | POST | `/knowledge/update/propose` | body (`UpdateProposeRequest.project`) [VERIFIED: app.py:344] | |
| 65 | POST | `/knowledge/update/confirm` | body (`UpdateConfirmRequest.project`) [VERIFIED: app.py:356] | |

**Total confirmed: 65 routes** — matches Correction 3's count exactly.

## Principal → Route Scope Matrix (D-04)

| Caller | Reaches (verified call sites) | Should be scoped to |
|--------|-------------------------------|----------------------|
| **Grasshopper C#** (`DG.Grasshopper/Validation/*.cs`, `DG.Core/Data/ConnectorHeartbeatClient.cs`) | `POST /connectors/heartbeat` (`ConnectorHeartbeatClient.cs:48`, sends `Authorization: Bearer`) [VERIFIED]; `POST /validation/publish` (`ValidationPublishClient.cs:36`, **no auth header** — Correction 5) [VERIFIED]; `POST /computgraph/publish` (`ComputgraphPublishClient.cs:33`, **no auth header**) [VERIFIED] | `dgc_` connector-token principal, bound to the credential's project |
| **n8n workflows** (`n8n/workflows/*.json`) | `POST /context/assemble`, `POST /context/generate-cypher`, `POST /execution-result` (callback), and (per `/mcp`'s tool list) potentially `neo4j_query`/`neo4j_schema`/`gh_*` tools via `POST /mcp` [VERIFIED via URL literals in both workflow JSONs; `/mcp` tool usage inferred from route design, not grepped in workflow JSON this session — verify at plan time] | internal-service-token principal, no project restriction needed (workflows are the trusted relay, not a tenant) |
| **ui-v2 browser** (`graphApi.js`, `modelApi.js`, `inputGenApi.js`, `connectorsApi.js`) | `executeCypher` (6 sites, to be deleted per D-06): `graphApi.js:45,49` (`fetchGraph`), `:65` (`tagProjectNodes`), `:74` (`updateNodeProp`), `:84` (`fetchRules`), `:268` (`fetchProjects`); `modelApi.js:39` (`fetchRuleDetails`), `:50` (`fetchEntityStatuses`); `inputGenApi.js:71` (`fetchAcceptedCandidates`) — **9 sites total, confirmed** [VERIFIED]. Plus named REST calls: `/rules/*` (delete-preview, delete, resolve-deletion, bulk-delete, check-conflict, supersede, accept-overlap), `/design-rule-sessions*`, `/validation/runs/{project}`, `/validation/view/*`, `/computgraph/generate-inputs`, `/computgraph/candidates/accept`, `/connectors`, `/connectors/{id}/credentials` (POST/DELETE), n8n webhooks directly (`n8nWebhook`/`n8nQueryWebhook`, to be relayed server-side per D-08), `/execution-result/*` polling | authenticated user-session principal, project-membership-checked per D-02/D-03 |

## D-06: The 9 Browser Cypher Call Sites — What Each Does and Proposed Grouping

| # | Site | Cypher intent | Data-service equivalent exists? | Proposed named endpoint |
|---|------|----------------|-----------------------------------|--------------------------|
| 1 | `graphApi.js:45` `fetchGraph` (nodes) | `MATCH (n) WHERE project-scope RETURN id,labels,props LIMIT 2000` | No | `GET /graph/{project}/nodes` |
| 2 | `graphApi.js:49` `fetchGraph` (rels) | `MATCH (a)-[r]->(b) WHERE project-scope RETURN ids+type LIMIT 8000` | No | fold into the same `GET /graph/{project}` response as `{nodes, rels}` — one round trip, matching the existing `fetchGraph` return shape |
| 3 | `graphApi.js:65` `tagProjectNodes` | `MATCH (n) WHERE n.project IS NULL OR ='default-project' SET n.project=$project` | No — **this is a deliberate cross-project write by design** (claims untagged/default nodes into the active project, the legacy-parity post-ingest fixup) | `POST /graph/{project}/claim-untagged` — authorize as: caller must be editor+ of `{project}`; the route itself is the only place allowed to touch nodes outside its own project scope, and only to *move them into* the caller's project, never out of it or across two named projects. Document this exception explicitly in `spec/SECURITY-BOUNDARY.md` — D-03's general "project must match" rule needs a named carve-out here. |
| 4 | `graphApi.js:74` `updateNodeProp` | `MATCH (n) WHERE id(n)=$id SET n[$key]=$value RETURN props` | No | `PUT /graph/{project}/node/{neo4j_id}/property` — must first verify the node's own `project` property equals the path project before writing (id(n) alone doesn't prove tenancy) |
| 5 | `graphApi.js:84` `fetchRules` | `MATCH (r:Rule) WHERE graph='Metagraph' AND project-scope RETURN ruleId,text` | Partially — `/rules/{project}/{rule_id}/delete-preview` exists but there's no list-all-rules route | `GET /rules/{project}` (new list endpoint) |
| 6 | `graphApi.js:268` `fetchProjects` | `MATCH (n) WHERE n.project IS NOT NULL RETURN DISTINCT project, count(n)` | No | `GET /projects` — this one is inherently cross-project (it's the project picker); authorize as "any authenticated user" (list of project names + counts, no node data), or restrict to only projects the caller is a member of if D-02's membership model should not leak the existence of other projects — **planner discretion, flag as open question below** |
| 7 | `modelApi.js:39` `fetchRuleDetails` | `MATCH (r:Rule {Rule_Id}) WHERE project match RETURN SWRL,name,description` | No | fold into `GET /rules/{project}/{rule_id}` (a natural single-rule-detail route, complementing #5's list) |
| 8 | `modelApi.js:50` `fetchEntityStatuses` | `MATCH (ve:ValidationEntity {project,runId,dgEntityId}) RETURN ruleId,status` | Related to existing `/validation/view/{project}/{run_id}/{rule_id}` but inverted (entity-first, not rule-first) | `GET /validation/view/{project}/{run_id}/entity/{dgEntityId}` |
| 9 | `inputGenApi.js:71` `fetchAcceptedCandidates` | `MATCH (ds:DesignState {project, kind:'ParamState'}) WHERE source='ai-generated' ... RETURN state fields` | No | `GET /computgraph/candidates/{project}` with optional `?ruleId=` query |

**Recommended grouping:** 7 new named endpoints (folding #1+#2 and #5+#7 as noted above), all
project-authorized via the same D-03 dependency, all using fixed parameterized Cypher (no
caller-supplied statement text ever again).

## Cookie / CSRF / Same-Origin Posture (D-01)

- **Same-origin already holds:** nginx proxies `/data-service/` to `data-service:8000` on the same
  origin (`8080`) the browser loads from [VERIFIED: ui-v2/nginx.conf]. `fetch(..., {credentials:
  "include"})` is sufficient for the cookie to be sent — no CORS configuration is needed because
  there is no cross-origin request in this flow.
- **SameSite=Strict + HttpOnly (D-01, locked):** blocks the cookie from being sent on any
  cross-site request, including top-level navigations from another origin. Given this app has no
  legitimate cross-site entry point (no email-link-triggered POST, no third-party embed), Strict
  is safe and simpler than Lax.
- **CSRF residual risk:** `SameSite=Strict` does not fully eliminate CSRF on same-site
  sub-navigation edge cases in older browsers, but for this app's threat model (a single nginx
  origin, no subdomains) the standard supplementary defense is requiring a custom header (e.g.
  `X-Requested-With: XMLHttpRequest` or a fixed app-specific header) on all state-changing
  (POST/PUT/DELETE) requests — a plain `<form>` submission or cross-site `<img>`/`<script>` tag
  cannot set custom headers, so this is a free, dependency-free CSRF check. `ui-v2`'s `fetch`
  calls already set `Content-Type: application/json` on every POST [VERIFIED: graphApi.js
  multiple sites] — requiring `Content-Type: application/json` (rejecting
  `application/x-www-form-urlencoded` and `multipart/form-data`) on state-changing routes is
  **already** a CSRF mitigation the codebase's fetch conventions happen to satisfy, and is
  simpler to enforce than inventing a new header. [ASSUMED — general web-security practice, not
  fetched from an authoritative source this session; treat as a starting recommendation the
  planner should confirm against current OWASP ASVS guidance in the Security Domain section.]
- **Speckle viewer at :8090 is a separate origin** — the DG session cookie is never sent there and
  never needs to be; the viewer only needs the per-run Speckle `readToken`, which is unrelated to
  the DG session cookie and already flows through `/validation/view/*` (see Summary).
- **Logout (D-01):** `POST /auth/logout` should delete the server-side session record (not just
  instruct the browser to clear the cookie) so a stolen cookie is invalidated — mirrors
  `connectors.py`'s `revoke_credential` pattern (mark revoked, stop authenticating).

## Storage Choice: Users/Sessions/Memberships (Claude's Discretion, D-01/D-02)

**Recommendation: JSON files under `DATA_DIR`, mirroring `connectors.py`.**

| Consideration | JSON under `DATA_DIR` | Neo4j nodes |
|---|---|---|
| Schema Change Propagation | Untouched — users/sessions/memberships are not part of the design/validation domain model this list governs | Would require new label rows in `cypher_template.txt`, `training/dataset_schema.json`, `ontology/dg-shapes.ttl` (SHACL), `spec/LPG-OWL-MAPPING.md` — significant unrelated surface area for auth data that has nothing to do with SWRL/ontology semantics |
| Concurrency | Single-process data-service already does read-modify-write JSON without file locking for `connectors.py` (accepted risk today — sessions/logins are lower-frequency writes than heartbeats) [VERIFIED pattern, not a new risk introduced] | Neo4j handles concurrent writes natively, but adds a dependency between "can I log in" and "is Neo4j up" — currently even Neo4j-dependent routes fail independently of auth |
| Consistency with existing idiom | Identical to `connectors.py` (`load_credentials`/`save_credentials`, SHA-256 hash-at-rest) — a reviewer who understands connector tokens already understands sessions | New pattern, first of its kind for non-domain data |
| Backup/portability | Lives in the same volume (`./data-service/data:/app/data`) already gitignored and already backed up as a unit | Would mix auth data into the domain graph's backup/restore/migration story |

**Verdict:** JSON, three new files (`users.json`, `sessions.json`, `memberships.json` or a single
combined file) under `DATA_DIR`, following `connectors.py`'s load/save function pair exactly. No
Schema Change Propagation list update is needed under this choice — note this explicitly in the
plan so a reviewer doesn't go looking for one.

## Test Impact (D-20)

- **No shared client fixture exists today.** 8+ of the 46 files under `data-service/tests/`
  construct their own module-level `client = TestClient(app, raise_server_exceptions=False)` at
  import time (`test_app_computgraph_pull.py`, `test_cg_recognition.py`,
  `test_cg_structure_checks.py`, `test_computgraph_consult.py`, `test_computgraph_publish.py`,
  `test_connectors.py`, `test_designstate_capture.py`, and others) [VERIFIED: grep across
  `tests/*.py`]. There is no `conftest.py` fixture providing an authenticated client, and
  `conftest.py` today only registers the recognition-eval CLI options and markers — it has zero
  auth-related fixtures currently [VERIFIED: data-service/tests/conftest.py, full file read].
- **Recommended fix:** add an `authorized_client` fixture (or module-level helper) to
  `tests/conftest.py` that either (a) logs in a bootstrap test user once per test session and
  reuses the cookie-bearing `TestClient`, or (b) sets the internal-service-token header on every
  request via `TestClient(app, headers={...})` (httpx's `Client` supports default headers,
  confirmed by the same mechanism `httpx.Client(timeout=...)` already uses in
  `tools/de01/legs.py`). Since most existing tests exercise routes that will become
  project-scoped user routes, the pragmatic sizing note for the planner: **every one of the ~8+
  files with a module-level `client = TestClient(app)` needs its calls updated to go through the
  authorized fixture** — this is a mechanical but wide-reaching change across the test suite, size
  it as its own task/wave, not a one-line addition.
- **DE-01 host runner (`tools/de01/legs.py`):** calls data-service via plain `httpx.Client(...)`
  with no auth headers today [VERIFIED: legs.py:185-298, no `headers=` argument on the client
  construction or the request calls found in the read range]. Under D-20 it needs either a
  connector token or the internal-service token added to its `httpx.Client` construction —
  `base_url = config.get("data_service_url", "http://localhost:8000")` is already
  configuration-driven, so adding a `token`/`headers` config key follows the existing pattern.

## Deployment Profile Mechanics (D-07/D-09)

Docker Compose (v2.40.3 confirmed installed [VERIFIED: `docker compose version`]) does not
support conditionally omitting one service's `ports:` entries based on an environment variable
inside a single compose file — env-var substitution can change a *value* (e.g. which host port
number) but not whether the array itself is empty, and `profiles:` controls whether a *service*
participates at all, not one field on an always-running service [CITED: docker compose reference
+ community guides on override-file array-replacement semantics, WebSearch 2026-09-28]. The
correct primitive for D-07/D-09 is a **second compose file used as an override**:

```
docker compose -f docker-compose.yml up -d                                   # local (default)
docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d  # multi-user
```

`docker-compose.multi-user.yml` should, per service that needs it:
- Redeclare `ports:` with only `8080:80` (UI) and `8090:8080` (Speckle ingress) surviving —
  overriding arrays does not merge, so every port line that should NOT be published in multi-user
  must simply be omitted from the override's `ports:` list (Compose replaces the whole array).
- Set `DG_DEPLOYMENT: multi-user` on the `data-service` environment block (Compose *does* merge
  the `environment:` map key-by-key across `-f` layers, unlike arrays) — data-service code reads
  this to (a) omit the Neo4j bundle from the heartbeat response (D-07) and (b) refuse startup on a
  known-default secret (D-11).
- `DG_DEPLOYMENT` itself has zero existing references anywhere in the codebase today [VERIFIED:
  grep found none] — this is a wholly new concept this phase introduces; there is no legacy
  behavior to preserve compatibility with.

## Speckle Read Token Flow (D-12)

- **Already server-side for the model viewer.** `ModelScreen.jsx:583` reads
  `view?.readToken` — the value comes from the `/validation/view/{project}/...` JSON response,
  not from `window.GRAPH_CONFIG`. `app.py` populates this field from `SPECKLE_READ_TOKEN`/
  persisted settings server-side (`get_speckle_settings_response`, referenced at multiple lines
  including `app.py:1056`) [VERIFIED: grep across app.py and ModelScreen.jsx —
  `speckleReadToken`/`GRAPH_CONFIG` do not appear anywhere in `ui-v2/src/`, only in
  `entrypoint.sh`/`config.js`, which nothing in the JS source consumes]. **This means D-12's "an
  authorized data-service endpoint serves the Speckle read token" already exists as
  `/validation/view/*`** — the remaining D-12 work is (1) delete `speckleReadToken` from
  `entrypoint.sh`/`config.js` (a config-only change, zero JS behavior change), and (2) confirm
  `/validation/view/*` is covered by the new project-authorization dependency so an unauthenticated
  or non-member caller can no longer reach it either.
- The `config.js` test asserting "no credential key names, no known default values" (D-12) should
  therefore find an *empty* diff on `speckleReadToken` removal from the JS behavior perspective —
  it's purely a leftover unused config field being deleted.

## LLM_MASTER_SECRET Rotation (D-13)

- `llm_gateway.py` derives a Fernet key from `LLM_MASTER_SECRET` via SHA-256 (`hashlib`,
  `base64` imports present) [VERIFIED: llm_gateway.py:12-24 imports;
  full derivation function not read this session — verify the exact `hashlib.sha256(...).digest()`
  -> `base64.urlsafe_b64encode(...)` chain at plan/execution time before writing the rotation
  script].
- Settings persist to a JSON file in `DATA_DIR` (same idiom as `connectors.py`) — encrypted
  `apiKey` field only, never plaintext [VERIFIED: `LLMSettingsPayload`/`LLMSettingsResponse`
  docstrings, llm_gateway.py:146-177].
- **Rotation procedure shape:** (1) read the persisted settings file with the OLD
  `LLM_MASTER_SECRET`-derived Fernet key, (2) decrypt the stored `apiKey`, (3) re-encrypt with the
  NEW `LLM_MASTER_SECRET`-derived key, (4) write back. This is a one-time migration script run
  once per rotation, invoked manually (D-13 human checkpoint) since it needs both the old and new
  secret values, which "never appear in a brief, a worker prompt, a commit or a log" per CONTEXT.md.
  The script itself (code) can ship in this phase; running it with real values is the owner's
  action.

## Common Pitfalls

### Pitfall 1: `GET /execution-result/latest/{workflow}` is a global mutable slot
**What goes wrong:** Two users triggering `rules-ingest` concurrently will race on the same
`WORKFLOW_STATUS`/`EXECUTION_RESULTS` key (keyed only by `workflow` name, not by user or session),
so one user can poll and receive another user's in-flight or completed result.
**Why it happens:** The route and its backing dict were designed for a single-user local
deployment where "latest" unambiguously means "the one I just started."
**How to avoid:** Under GATE12-05's multi-user profile this needs either (a) a
per-request/per-session correlation id threaded from the initiating call through to the poll (the
`executionId`-keyed `GET /execution-result/{execution_id}` path already does this correctly — the
`latest/{workflow}` fallback path in `callWorkflow()`'s "intermediate echo" branch is the unsafe
one), or (b) scoping the dict key by session/project in addition to workflow name.
**Warning signs:** D-15's cross-project matrix should include this route explicitly — a naive
"call with P2 in path, expect 403" check doesn't even apply here since there's no project in the
path at all; this needs its own test class.

### Pitfall 2: Authorizing `/mcp` per-user would defeat its own purpose
**What goes wrong:** If a plan tries to make `/mcp` a normal user-session route with project
checks, `neo4j_schema` and `neo4j_query` still have no project parameter to check against — the
tempting "fix" is to add one, but that changes an n8n-internal contract that several workflow JSON
nodes may depend on positionally.
**Why it happens:** `/mcp` is a JSON-RPC-shaped multi-tool endpoint, not a single-purpose REST
route; its tools have heterogeneous scoping needs.
**How to avoid:** Classify the whole route as internal-service-token-only (D-04). Do not attempt
per-tool project scoping in this phase — that's a `/mcp` redesign out of scope for 1205.
**Warning signs:** Any plan task that says "add project validation inside the `neo4j_query`
branch" is solving the wrong problem — the actual fix is making the route unreachable by ordinary
user sessions at all.

### Pitfall 3: GH clients breaking under enforced auth before the C# token change ships
**What goes wrong:** `ValidationPublishClient.cs` and `ComputgraphPublishClient.cs` send zero
Authorization header today [VERIFIED]. If D-03's dependency ships and these two routes require a
connector token before the C# clients are updated to send one (D-04's own scope), every existing
`.gh` canvas with a VALIDATOR or COMPUTGRAPH PUBLISH component breaks silently (401) with no
in-canvas explanation until the components are updated to surface the new error and a Token input
is wired.
**Why it happens:** The phase's C# change (adding a Token input/header) and the phase's Python
change (requiring the token) are two different plans; if sequenced wrong, one ships without the
other.
**How to avoid:** Sequence: (1) ship the C# client changes (new `Authorization: Bearer` header,
threaded from a new Token input on `ValidatorComponent`/`ComputgraphPublishComponent`, matching
`ConnectorComponent`'s existing non-persistent-token-param pattern) and confirm they degrade
gracefully with a clear GH runtime-message when the token is missing/rejected, THEN require the
token server-side — not the other way around. Both `ValidatorComponent` (`DataServiceUrl` input
only, no Token input today) [VERIFIED] and `ComputgraphPublishComponent` (same) [VERIFIED] need a
new `Token` input port before D-04 can close for the GH side.
**Warning signs:** dotnet build succeeds but any live-Rhino UAT (out of this phase's scope per
CONTEXT.md, but still worth flagging) would show every publish silently failing.

### Pitfall 4: Stale Docker images mask code state (recorded project memory, applies directly here)
**What goes wrong:** Rebuilding `data-service`/`ui-v2` and testing against the *old* container
gives false confidence that D-03/D-06/D-09 are enforced when they aren't yet.
**Why it happens:** `docker compose up -d` without `--no-cache`/rebuild reuses existing images.
**How to avoid:** D-16's live checkpoint must explicitly rebuild (`docker compose build --no-cache
data-service design-grammars` at minimum, plus the profile-specific compose invocation) before
asserting `/neo4j/` returns 404 or Bolt is unreachable.
**Warning signs:** A "passing" live check immediately after a code change with no visible rebuild
step in the session transcript.

### Pitfall 5: Neo4j HTTP tx/commit returns 200 with `errors[]`
**What goes wrong:** Any remaining live verification that touches Neo4j via HTTP (e.g. confirming
`tagProjectNodes`'s replacement endpoint behaves correctly) must check the `errors` array, not
just the HTTP status code — a 200 with a non-empty `errors[]` is a failure.
**Why it happens:** Neo4j's HTTP transaction endpoint reports Cypher errors in the body, not the
status line.
**How to avoid:** Reuse the exact pattern `graphApi.js`'s `executeCypher` already implements
(`if (Array.isArray(json?.errors) && json.errors.length) throw ...`) in any new
server-side Cypher helper this phase adds.
**Warning signs:** A "successful" claim-untagged-nodes call that silently did nothing.

## Code Examples

### Reusable bound-project check (generalizing `/designstate/capture`'s idiom for D-04)
```python
# Source: data-service/app.py:2547-2558 (existing, T-39-02/T-39-06)
if (record.get("project") or "default-project") != payload.project:
    raise _structured_error_response(
        "This connector token is not authorized for the requested project.",
        "Create a credential scoped to the project you are capturing into, via "
        "POST /connectors/{connector_id}/credentials.",
        "CAPTURE_PROJECT_MISMATCH",
        403,
    )
```
Generalize this into a single `_authorize_project(principal, project)` helper in the new
`auth.py`, called from every route classified as project-scoped, rather than re-deriving the
message/code per route.

### Connector token verification, already correct (reuse verbatim for D-04's dgc_ principal)
```python
# Source: data-service/connectors.py:212-223
def authenticate_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    digest = hash_token(token)
    for record in load_credentials():
        if record.get("token_hash") == digest and not record.get("revoked"):
            return record
    return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Browser holds Neo4j admin credentials, builds arbitrary Cypher client-side | Named, parameterized, project-authorized data-service endpoints (D-06) | This phase | Removes the single largest exposure in the system |
| localStorage-only auth, server never sees identity | Server-side session, scrypt hash-at-rest (D-01) | This phase | Makes "who is this caller" a real, checkable fact for the first time |
| All internal ports on `0.0.0.0` | `127.0.0.1`-only (D-09) | This phase | Closes the direct-proxy exposure Correction 8 documented |
| Secrets committed literally in `docker-compose.yml` | `.env` + `${VAR:?}` required-secret enforcement (D-10) | This phase | Stack refuses to start with a missing secret instead of silently using a known default |

**Deprecated/outdated:**
- `ui-v2/src/lib/auth.js`'s localStorage + unsalted-SHA-256 scheme: fully replaced by D-01, not
  migrated (D-05) — existing accounts do not carry over.
- The nginx `/neo4j/` and `/n8n/` passthrough locations: removed entirely (D-06/D-08); `/llm/` and
  `/reasoner/` passthroughs are NOT removed by any decision in this phase — they still proxy
  straight to `data-service:8000`, which is fine once D-03's dependency covers every route behind
  them, but worth flagging so the planner doesn't assume all passthroughs are gone.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `dg_context.ContextAssembleRequest` and `GenerateCypherRequest` carry a `project` field, inferred from the docstring's "identical param contract" claim to `/context/debug` (which does have `project`) rather than from directly reading the class bodies | Route Inventory #26, #28 | If false, these two n8n-facing routes need the same "no project source" treatment as `/mcp`/`/execution-result` — classify as internal-service-token-only regardless, since only n8n calls them; low practical risk either way but the planner should confirm the field exists before writing D-15's matrix test for these two routes specifically |
| A2 | CSRF defense via `Content-Type: application/json` enforcement is adequate given `SameSite=Strict`, without a dedicated CSRF token | Cookie/CSRF Posture | If OWASP ASVS V4 (session/CSRF) guidance has moved past this being sufficient, a plan built on it could ship a real CSRF gap; verify against current ASVS text before locking this into `spec/SECURITY-BOUNDARY.md` |
| A3 | `llm_gateway.py`'s exact key-derivation chain (SHA-256 -> base64 -> Fernet key) was inferred from imports and module docstring, not read line-by-line | LLM_MASTER_SECRET Rotation | The rotation script's exact re-encrypt steps need this function read directly before implementation; if the derivation differs from the assumed SHA-256-then-base64 shape, the rotation script would be wrong |
| A4 | `/mcp`'s tool set is called by n8n workflows (inferred from route design and this being the only sensible caller of a JSON-RPC-shaped Cypher/GH-bridge endpoint), not confirmed by grepping `/mcp` literal URLs inside `n8n/workflows/*.json` this session | Principal → Route Scope Matrix | If nothing actually calls `/mcp` from n8n today, classifying it as internal-service-token-only is still the safe default (nothing browser-facing should reach it either way), so risk is low |

## Open Questions

1. **Should `GET /projects` (the `fetchProjects` replacement) list only the caller's own
   memberships, or every project that exists?**
   - What we know: Today's `fetchProjects` (browser Cypher) lists every project unconditionally —
     it's the project picker on the landing/graph screens.
   - What's unclear: Whether D-02's membership model should hide the existence of projects a user
     isn't a member of (stricter tenancy) or whether "which projects exist" is considered public
     metadata within a single trusted-user-base deployment (looser, matches today's behavior).
   - Recommendation: Default to "list only the caller's memberships" for a genuine multi-tenant
     posture consistent with D-02's stated model (viewer/editor/owner membership), but flag this
     explicitly for the owner to confirm — it's a user-experience change (no more browsing projects
     you're not on), not just a security tightening.

2. **How should `GET /execution-result/{execution_id}` and `.../latest/{workflow}` be scoped?**
   - What we know: Both are polled directly by the browser after an n8n-workflow-triggering call;
     neither carries a project or user binding today (Route Inventory #46/#47).
   - What's unclear: Whether to bind `execution_id` to the initiating session (requires threading
     session identity through `call_n8n_sync`'s existing `EXECUTION_RESULTS` dict) or to accept
     "any authenticated user can poll any execution_id" as a lower-severity residual risk given
     execution_ids are n8n-generated UUIDs, not guessable — while still fixing `latest/{workflow}`'s
     genuine correctness bug (Pitfall 1) regardless.
   - Recommendation: Fix `latest/{workflow}`'s race unconditionally (it's a correctness bug, not
     just an auth gap); treat `execution_id`-keyed polling as "authenticated, any project" unless
     the owner wants stricter session-binding — size the session-binding version as a stretch task,
     not a gate blocker, since GATE12-05 only requires fail-closed on cross-project/direct-proxy,
     not a fix for every latent multi-user race.

3. **Does `/mcp` actually get called by any n8n workflow node today, or is it dead/future code?**
   - What we know: The route exists, is fully implemented, and is architecturally the only sane
     home for GH-canvas-bridge tool calls (`gh_get_context` etc., Phase 33 BRDG-02).
   - What's unclear: This session did not grep `n8n/workflows/*.json` for a literal `/mcp` URL to
     confirm a live caller exists.
   - Recommendation: Planner/executor should grep `n8n/workflows/*.json` for `/mcp` before writing
     the D-14 classification for this route — if genuinely uncalled today, it's still safest
     classified as internal-service-token-only (never user-facing) regardless of the answer.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose | D-07/D-09 profile split, D-16 live checkpoint | Yes [VERIFIED: `docker compose version`] | v2.40.3-desktop.1 | — |
| `hashlib.scrypt` | D-01 | Yes (Python stdlib, already the interpreter used by data-service's existing image) | stdlib since 3.6 | — |
| `cryptography` (Fernet) | D-13 rotation | Yes [VERIFIED: requirements.txt] | unpinned in requirements.txt — confirm exact resolved version inside the built image at plan time (`docker exec data-service pip show cryptography`) | — |
| A live multi-user rebuild environment for D-16's live checkpoint | D-16 | Not verified this session — requires a human checkpoint per CONTEXT.md's own scoping | — | The static checks (nginx.conf parse, docker-compose.yml parse) can and should be fully automated without this dependency |

**Missing dependencies with no fallback:** none identified — this phase's tooling is entirely
already present.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (data-service), xUnit (`dotnet test`, DG.Tests), no dedicated JS test runner found for `ui-v2` — build (`npm --prefix ui-v2 run build`) is the closest automated JS check |
| Config file | `data-service/tests/conftest.py` (markers/CLI options only, no auth fixtures — see Test Impact) |
| Quick run command | `MSYS_NO_PATHCONV=1 docker exec data-service pytest tests/test_route_inventory.py tests/test_cross_project_matrix.py -x` |
| Full suite command | `MSYS_NO_PATHCONV=1 docker exec data-service pytest` (in-container is authoritative — `neo4j` hostname only resolves inside compose, per the `dg-tests-neo4j-e2e-baseline` project memory) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGN12-17 | Ordinary API/graph access enforces server-side authorization | unit+integration | `pytest tests/test_route_inventory.py -x` | ❌ Wave 0 |
| ALGN12-18 | Direct Neo4j proxy exposure removed/restricted | static+live | `pytest tests/test_static_proxy_boundary.py -x` (parses `nginx.conf`/`docker-compose.yml`) | ❌ Wave 0 |
| ALGN12-19 | Secrets/credentials hardened, excluded from browser config | unit | `pytest tests/test_config_js_no_secrets.py -x` (asserts built `ui-v2/dist` + generated `config.js` contain no credential key names / known defaults) | ❌ Wave 0 |
| ALGN12-20 | Unauthorized cross-project / direct-proxy access fails closed | integration | `pytest tests/test_cross_project_matrix.py -x` | ❌ Wave 0 |
| GATE12-05 | Gate holds specifically in `DG_DEPLOYMENT=multi-user` | integration (live checkpoint) | `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d --build` then curl-based live checks (D-16) | ❌ Wave 0 (human checkpoint) |

### Sampling Rate
- **Per task commit:** targeted `pytest tests/test_route_inventory.py` or the specific new test
  file for that task
- **Per wave merge:** full in-container `pytest` (data-service) + `dotnet test` if any C# client
  changed + `npm --prefix ui-v2 run build` if any `ui-v2/src/lib/*.js` changed
- **Phase gate:** full suite green in BOTH `local` and `multi-user` compose invocations before
  `/gsd-verify-work`, per D-19's "enforced in both profiles" requirement

### Wave 0 Gaps
- [ ] `data-service/tests/conftest.py` — add `authorized_client`/service-token fixture (D-20)
- [ ] `data-service/tests/test_route_inventory.py` — new, D-14
- [ ] `data-service/tests/test_cross_project_matrix.py` — new, D-15, two-user/two-project fixture
- [ ] `data-service/tests/test_static_proxy_boundary.py` — new, D-16 static half (nginx.conf +
      docker-compose.yml parsing)
- [ ] `data-service/tests/test_config_js_no_secrets.py` — new, D-12
- [ ] `spec/SECURITY-BOUNDARY.md` — new, D-17, with the fenced allowlist block
- [ ] Framework install: none — pytest/xUnit/npm already present and configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | scrypt password hashing + opaque session token (D-01) — no external IdP per D-05 |
| V3 Session Management | yes | HttpOnly, SameSite=Strict cookie; server-side revocable session store (D-01) |
| V4 Access Control | yes | Deny-by-default global dependency + project-membership check (D-02/D-03); role model owner>editor>viewer |
| V5 Input Validation | yes (pre-existing) | Pydantic models already validate every request body [VERIFIED pattern across all 65 routes] — unchanged by this phase except adding the auth dependency |
| V6 Cryptography | yes | `hashlib.scrypt` (password), `cryptography.fernet` (LLM key at rest, unchanged), SHA-256 (connector token hash-at-rest, unchanged) — never hand-roll, all already stdlib/library-backed |
| V7 Error Handling/Logging | partial (existing) | `_structured_error_response` house pattern reused for 401/403; note D-13's rotation explicitly keeps secrets out of logs |
| V13 API Security | yes | This entire phase is, in ASVS terms, closing a V13 (and V4) gap — every route now requires authenticated, authorized access |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via caller-supplied statement text | Tampering | Eliminated at the source by D-06 (no more caller-supplied Cypher text from the browser); `/mcp`'s `neo4j_query` retains a read-only guard (`is_write_query`) as defense-in-depth, but its real mitigation is D-04's internal-service-token restriction |
| Broken object-level authorization (BOLA) — id-only lookups with no tenant check | Elevation of Privilege / Info Disclosure | The `note_id`/`execution_id`/`credential_id`-only routes found in the Route Inventory (#14, #46, #47, #50-52) are textbook BOLA candidates; D-15's matrix must explicitly cover id-only routes, not just path-project routes |
| Credential stuffing / brute force on `/auth/login` | Spoofing | Explicitly deferred (CONTEXT.md Deferred Ideas) — note in `spec/SECURITY-BOUNDARY.md` as a known, accepted gap for this phase, not silently absent |
| Session fixation / cookie theft | Spoofing / Elevation of Privilege | HttpOnly (no JS access) + Strict (no cross-site send) + server-side revocation on logout (D-01) |
| Secret sprawl in VCS history | Information Disclosure | D-13's rotation treats committed secrets as compromised; git history is explicitly NOT rewritten (accepted residual exposure of the *old*, now-invalid, values) |

## Sources

### Primary (HIGH confidence)
- `data-service/app.py` (full route decorator enumeration, multiple targeted reads of lines
  130-360, 1420-1470, 1550-1670, 2040-2200, 2500-2600, 2860-2995) — 65-route inventory, project
  source classification, `/mcp` tool behavior, `/designstate/capture`'s existing bound-project check
- `data-service/connectors.py` (full file) — token minting/hash/persistence idiom
- `data-service/llm_gateway.py` (lines 1-210) — Fernet-at-rest pattern, request/response models
- `ui-v2/src/lib/graphApi.js`, `modelApi.js`, `inputGenApi.js`, `connectorsApi.js`, `auth.js` (full
  files) — all 9 executeCypher call sites, localStorage auth scheme, named-endpoint call sites
- `ui-v2/nginx.conf`, `ui-v2/entrypoint.sh` (full files) — proxy routes, config.js generation
- `docker-compose.yml` (full file) — all committed secrets/defaults, port bindings, existing env vars
- `DG/src/DG.Core/Data/ConnectorHeartbeatClient.cs`,
  `DG/src/DG.Grasshopper/Validation/{ComputgraphPublishClient,ValidationPublishClient}.cs`,
  `DG/src/DG.Grasshopper/Components/{ValidatorComponent,ComputgraphPublishComponent,ConnectorComponent}.cs`
  (grepped/read) — confirmed no-auth-header gap and existing Token-input pattern on `ConnectorComponent`
- `spec/REPRODUCIBILITY.md`, `spec/SWRL-SUBSET.md` (targeted reads) — the fenced-block
  machine-checked pattern to mirror in `spec/SECURITY-BOUNDARY.md`
- `data-service/tests/conftest.py` (full file), `data-service/tests/*.py` (grep) — confirmed no
  shared auth fixture exists; 8+ files with module-level `TestClient(app)`
- `tools/de01/legs.py` (grep) — confirmed plain `httpx.Client`, no auth headers today
- `n8n/workflows/graph-query-mcp.json`, `rules-to-metagraph.json` (grep) — confirmed
  `mcp_url`/`data_service_url` read from caller input (SSRF vector, Correction 7)
- `.planning/phases/1205-security-and-tenancy-release-gate/1205-CONTEXT.md` — all 20 locked
  decisions and 8 verified corrections (source of truth for what to build; this research verifies
  and extends it with fresh findings, does not re-litigate it)

### Secondary (MEDIUM confidence)
- WebSearch, "docker compose profiles conditionally publish ports per profile override file same
  service" (2026-09-28) — confirmed profiles-vs-override-file semantics and array-replacement
  behavior across `-f` layers [CITED: oneuptime.com, kokil.com.np summaries of Docker Compose
  reference behavior — not the primary Docker docs page directly fetched this session]

### Tertiary (LOW confidence)
- CSRF/`Content-Type` mitigation reasoning (Cookie/CSRF Posture section) — general web-security
  knowledge, not verified against current OWASP ASVS text this session; flagged as Assumption A2

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library is already installed and verified in `requirements.txt`;
  no new-package risk
- Architecture: HIGH for the route inventory and call-site tables (directly read from disk);
  MEDIUM for the compose-profile mechanics (one web search, not the primary Docker doc page)
- Pitfalls: HIGH for the four disk-verified pitfalls (execution-result race, `/mcp` scope, GH
  no-auth-header, stale-image); the CSRF assumption is explicitly flagged LOW

**Research date:** 2026-09-28
**Valid until:** 30 days (stable domain — FastAPI/compose/Neo4j versions and the codebase's own
route set are not expected to churn faster than that within this milestone)
