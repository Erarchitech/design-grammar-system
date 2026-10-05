# Security Boundary — Trust Zones, Principals, Route Policy and Secrets

## Overview

This is the normative contract for the Design Grammar System security boundary. It covers requirements ALGN12-17 (server-side authorization), ALGN12-18 (no direct-proxy exposure), ALGN12-19 (secret and default-credential hardening) and ALGN12-20 (fail-closed cross-project tests), and it states the gate GATE12-05.

**Gate (GATE12-05, D-18).** Phase 1205 is release-blocking for **external multi-user evaluation only**. Local single-user development and the paper's bounded claims are unaffected: the `local` deployment profile keeps working exactly as before for one developer on one machine. The gate is judged with `DG_DEPLOYMENT=multi-user`: the route inventory (D-14), the cross-project matrix (D-15) and the live boundary check (D-16) must all hold in that profile.

**Enforcement shape.** This file follows the `spec/SWRL-SUBSET.md` and `spec/REPRODUCIBILITY.md` pattern. Section 4 holds four machine-checked fenced blocks, each delimited by HTML comments. `data-service/tests/test_security_boundary_spec.py` parses them and fails the suite when a block differs from the code or compose file it mirrors, in either direction. A new route, principal, published port or known-default secret therefore cannot ship without this document changing.

**Storage note (Schema Change Propagation).** Users, sessions, memberships and invitations live in JSON files under `DG_DATA_DIR` (`auth-users.json`, `auth-sessions.json`, `auth-memberships.json`, `auth-invites.json`), not in Neo4j. Phase 1301 adds `auth-project-companies.json` (the admin-assigned project to company map, D-20; `PUT /projects/{project}/company`, admin only) and `auth-delegated-tokens.json` (SHA-256 hashes of delegated tokens, Section 3.5). No graph node label, relationship type or property was added by Phase 1205, so the Schema Change Propagation list in `CLAUDE.md` is not triggered by this contract.

Related contracts: `spec/EVIDENCE-CONTRACT.md` (validation outcome status and evidence envelope, unchanged by this phase), `spec/RULE-PARTITION-POLICY.md`, `spec/SWRL-SUBSET.md`, `spec/REPRODUCIBILITY.md`.

## 1. Trust Zones

| Zone | Trust | Notes |
|------|-------|-------|
| Browser (V2 UI) | Untrusted | Holds no credential of any kind. `config.js` carries only `dataServiceUrl` and `speckleBaseUrl`. Reaches everything through `/data-service/...`; the `/neo4j/` and `/n8n/` nginx locations are 404 tombstones. |
| Host-local processes | Trusted in the `local` profile only | Grasshopper, the DE-01 host runner and the developer's shell reach `127.0.0.1` ports. In `multi-user`, Bolt, Neo4j HTTP and n8n are not published at all. |
| Internal compose network | Trusted transport, not trusted identity | Services reach each other by name. Machine-to-machine calls to data-service still carry a credential (the service token). |
| data-service | Single policy enforcement point | Every route declares `auth.require_principal` and has exactly one row in `route_policy.ROUTE_POLICIES`. A route with no row answers 403 `ROUTE_UNCLASSIFIED`. Neo4j is reached only from here, from n8n, from dg-reasoner, and (local profile) from Grasshopper over Bolt. |
| Grasshopper host process | Untrusted for tenancy | Authenticates to data-service with a project-bound connector token. Its direct-Bolt repositories are a trusted-local boundary (Section 2). |
| n8n | Internal zone with its own environment | n8n Function nodes can read the environment of the n8n container (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false` is set so the workflows can read `DG_SERVICE_TOKEN` and the Neo4j credentials). Anyone who can edit n8n workflows can read those values, so n8n is reachable only from the internal network (and from `127.0.0.1` in `local`). Workflows use hardcoded internal URLs and never follow a caller-supplied URL. |

## 2. Deployment Profiles

`DG_DEPLOYMENT` selects the profile (`local` is the default; `multi-user` is set by `docker-compose.multi-user.yml`). The profile is read by `auth.deployment_profile()`.

| Aspect | `local` | `multi-user` |
|--------|---------|--------------|
| Heartbeat Neo4j bundle (`POST /connectors/heartbeat`) | Returned to the connector | Omitted |
| Published ports | Section 4 (`published-ports`), local rows | Section 4, multi-user rows: Neo4j (7474, 7687) and n8n (5678) are not published |
| Known-default secrets at startup | Logged as a single WARNING naming keys only; data-service still starts | data-service refuses to start (`secrets_policy.enforce_startup_secrets`) |
| FastAPI docs (`/docs`, `/redoc`, `/openapi.json`) | Enabled | Disabled |
| Self-registration (`POST /auth/register`, `GET /auth/options`) | On by default (toggle `DG_ALLOW_SELF_REGISTRATION`) | Off; the route answers 404, and `docker-compose.multi-user.yml` pins the toggle to `false` |
| Authentication and authorization | Enforced | Enforced (D-19) |

**What never varies (D-19).** Authentication and authorization are identical in both profiles. The browser always logs in, Grasshopper always sends its connector token, every route is classified, and every project-scoped call is membership-checked. Only Bolt exposure, published ports, default-secret strictness and the FastAPI docs vary.

**Self-registration (amendment of D-05, made 2026-09-30).** D-05 originally allowed no open self-registration. The owner amended it for the `local` profile only; invite-only onboarding remains the rule in `multi-user`. `DG_ALLOW_SELF_REGISTRATION` (`true` or `false`, case-insensitive) sets it explicitly; blank or unset follows the profile (on for `local`, off for `multi-user`). Any other value makes data-service refuse to start, like an invalid `DG_DEPLOYMENT`. `GET /auth/options` is public and returns only `{"selfRegistration": <bool>}`. `POST /auth/register` is public, requires the CSRF header, and takes `{username, password}` (username rule and 12 to 128 character password policy as for invitations). The account is never an admin and holds no memberships; the new user creates their own projects through `POST /projects`. A taken username and any other failure answer the same 400 `REGISTRATION_INVALID`, the per-username (and, when configured, per-address) login throttle applies, and success returns the login body with a session cookie. When self-registration is off the route answers 404 with the body of an unknown route, before the CSRF check, so `multi-user` shows no registration surface.

**Invocation.**

- Local: `docker compose up -d`
- Multi-user: `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d`

The override uses the Compose `!reset` tag because Compose concatenates `ports` lists across `-f` files rather than replacing them.

**Direct-Bolt Grasshopper repositories (D-07).** The C# repositories under `DG/src/DG.Core/Data/Neo4j*Repository.cs` connect straight to Neo4j over Bolt. In `local` this is a documented trusted-local boundary: the developer's machine holds the Neo4j credentials anyway. In `multi-user` it is unsupported: Bolt is not published and the heartbeat withholds the bundle. Migrating those repositories to data-service HTTP is deferred.

## 3. Principals

Exactly one principal type is resolved per request, by explicit credential, in this precedence order: service header, then delegated Bearer token (`dgd_`), then connector Bearer token (`dgc_`), then session cookie. An explicit-but-invalid credential never falls back to a weaker one: an invalid `dgd_` Bearer answers 401 even when a valid session cookie is also present.

### 3.1 User session

- Cookie `dg_session`, value prefix `dgs_`, opaque random token; the server stores only its hash.
- Attributes: `HttpOnly`, `SameSite=Strict`, `Path=/`, `Max-Age` equal to the absolute session lifetime. `Secure` is set when `DG_COOKIE_SECURE` is `true` or `1` (off by default; see Section 8, TLS).
- Lifetimes: absolute `DG_SESSION_TTL_SECONDS` (default 43200, 12 hours); idle `DG_SESSION_IDLE_SECONDS` (default 7200, 2 hours). `last_seen_at` is refreshed at most once every 60 seconds.
- Passwords: scrypt with a per-user salt; length 12 to 128 characters.
- CSRF: every unsafe method (`POST`, `PUT`, `PATCH`, `DELETE`) on a session-authenticated request, and on a public route, must carry `X-DG-CSRF: 1`. Missing header: 403 `CSRF_HEADER_REQUIRED`.
- Roles per project: `viewer` (read), `editor` (write), `owner` (also membership and invitations). Rank is viewer < editor < owner. A user with `is_admin` is treated as `owner` of every project and is the only principal allowed on admin-only routes.
- Accounts are created by the bootstrap admin at first start (only when no admin exists) and by invitation (`POST /auth/invites`, code prefix `dgi_`, valid 72 hours, single use). Open self-registration (`POST /auth/register`) exists in the `local` profile only and is off in `multi-user` (Section 2, "Self-registration").

### 3.2 Connector token

- Bearer token `Authorization: Bearer dgc_...`, minted by `POST /connectors/{connector_id}/credentials`, stored only as a SHA-256 hash, and bound to exactly one project.
- Route scope is exactly the rows whose principals include `connector` in the route-policy block: `POST /computgraph/publish`, `POST /validation/publish` and the three `GET /validation/view/...` routes, each authorized only when the token's bound project equals the request project.
- Two further routes use the connector token but carry their own credential check inside the handler and are classed `connector-self` in the policy: `POST /connectors/heartbeat` and `POST /designstate/capture` (bound-project equality, generic 403 message).
- A connector token is denied every other route with 403 `PRINCIPAL_NOT_PERMITTED`.

### 3.3 Internal service token

- Header `X-DG-Service-Token`, value `DG_SERVICE_TOKEN` from the environment (minimum length 32).
- Scope is exactly the rows whose principals are `service`: `POST /llm/generate`, `POST /context/assemble`, `GET /context/debug`, `POST /context/generate-cypher`, `POST /mcp` and `POST /execution-result`. Only n8n calls them.
- The service principal is denied every other route, and no user session or connector token is accepted on these routes.

### 3.4 Errors

Every denial uses the `{error, hint, code}` detail shape with generic messages that never confirm whether a project or resource exists.

| Code | Status | Meaning |
|------|--------|---------|
| `AUTH_REQUIRED` | 401 | No credential, or an invalid or expired session |
| `CONNECTOR_AUTH_FAILED` | 401 | Invalid or revoked connector token |
| `SERVICE_AUTH_FAILED` | 401 | Invalid service token |
| `DELEGATED_AUTH_FAILED` | 401 | Unknown, malformed or explicitly revoked delegated token |
| `DELEGATED_EXPIRED` | 401 | Delegated token past its own expiry |
| `DELEGATED_SESSION_ENDED` | 401 | The parent session of a delegated token was revoked, expired, idle-timed-out or its user no longer exists |
| `DELEGATED_SCOPE_CHANGED` | 403 | The project behind a delegated token was reassigned to a different company |
| `PRINCIPAL_NOT_PERMITTED` | 403 | The principal type is not permitted on this route |
| `CSRF_HEADER_REQUIRED` | 403 | Unsafe cookie-session request without `X-DG-CSRF: 1` (a delegated Bearer is exempt) |
| `ADMIN_REQUIRED` | 403 | Admin-only route, non-admin user |
| `PROJECT_FORBIDDEN` | 403 | Not a member of the project, or role too low; also a delegated token whose membership on its bound project was removed |
| `PROJECT_REQUIRED` | 403 | The declared project source carries no project value |
| `PROJECT_MISMATCH` | 403 | Path, query and body carry different project values |
| `ROUTE_UNCLASSIFIED` | 403 | The route has no policy row (fail closed) |

Resource-bound routes answer an unknown resource and an unauthorized one with the same 404 (`CREDENTIAL_NOT_FOUND`, `EXECUTION_NOT_FOUND`, the note not-found), so a caller cannot probe another project's resources.

### 3.5 Delegated token (Phase 1301, D-06, D-08, D-20)

A user-scoped credential for the local DeGram agent, which holds neither the browser cookie, a connector token nor the service token.

- **Mint.** `POST /auth/delegated-token` with body `{project}`, authenticated by the `dg_session` cookie and `X-DG-CSRF: 1` (policy `member`, viewer). The caller must hold a stored membership on the project; an admin who is not a member is refused (403 `PROJECT_FORBIDDEN`). A Bearer caller (delegated or connector) cannot mint (403 `PRINCIPAL_NOT_PERMITTED`). The 201 answer is `{token, project, company, expiresAt, expiresInSeconds}` with `Cache-Control: no-store`; the raw token is returned once.
- **Credential.** `Authorization: Bearer dgd_...` (`secrets.token_urlsafe(32)`), time to live 900 seconds (`delegation.DELEGATED_TOKEN_TTL_SECONDS`). The server stores only the SHA-256 hash, the parent session hash, the username, the project and the company recorded at issue (`auth-delegated-tokens.json`). The raw token is never logged.
- **Principal.** Resolves to kind `delegated`: never an admin, bound to exactly one project, with the project's company. Route scope is exactly the rows whose principals include `delegated` in the route-policy block: `GET /graph/{project}`, `GET /rules/{project}`, `POST /degram/v1/chat/completions` (the model relay, Section 3.6) and `DELETE /auth/delegated-token` (self-revoke). Authorization is bound-project equality plus the user's stored role, so a delegated token never inherits admin ownership of other projects. Every other route answers 403 `PRINCIPAL_NOT_PERMITTED`.
- **CSRF.** A delegated Bearer is a non-ambient credential and is exempt from `X-DG-CSRF`; the cookie session that mints it is not.
- **Revocation (fail closed, checked on every request).** The token stops working at once when: the parent session is logged out, revoked, expired or idle-timed-out, or its user is gone (401 `DELEGATED_SESSION_ENDED`); the user changes their password (all of the user's tokens, 401 `DELEGATED_SESSION_ENDED`); the membership on the bound project is removed (403 `PROJECT_FORBIDDEN`); the project is reassigned to another company (403 `DELEGATED_SCOPE_CHANGED`); or its own expiry passes (401 `DELEGATED_EXPIRED`). `DELETE /auth/delegated-token` revokes the presented token (later use answers 401 `DELEGATED_AUTH_FAILED`). Delegated use does not refresh the parent session's idle timer.
- **Company.** `PUT /projects/{project}/company` (admin only, D-20) assigns a project to a company; `GET /projects` rows and `GET /auth/me` memberships carry `company` (string or `null`).

### 3.6 DeGram model relay (Phase 1301 plan 08, D-16)

`POST /degram/v1/chat/completions` is the only model path of the local DeGram agent. It is not `/llm/generate` and nothing under `/llm/` routes to it.

- **Principal.** Policy `delegated` only, no project source: the project, user and company are the delegated principal's own (`principal.bound_project`, `principal.username`, `principal.company`). A cookie session (admin included), a connector token and the service token answer 403 `PRINCIPAL_NOT_PERMITTED`; no credential answers 401. Because `require_principal` re-validates the token on every request, a token whose project changed company answers 403 `DELEGATED_SCOPE_CHANGED` before the relay runs.
- **One upstream, no fallback.** The upstream is the single endpoint in `degram-llm.json` (`baseUrl` https, or http for localhost only; `model`, default `mimo-v2.5-pro`; `providerLabel`, default `genpro`; the system key Fernet-encrypted with `LLM_MASTER_SECRET`). The server overwrites `model` and `stream` and drops any client `provider`; the client chooses neither. There is no fallback to another provider, to Ollama or to another model, and no automatic retry. Unconfigured answers 503 `RELAY_NOT_CONFIGURED` before any streaming.
- **Provider-export policy (deny by default, D-17, 1300 D-06).** Reading a project through DG and sending its data to a model provider are separate permissions. `GET` and `PUT /projects/{project}/degram-policy` (admin only, no project source, like the company route) hold `{providerExportAllowed, wholeDefinitionAllowed}` per project in `degram-policy.json`; both are false when no row exists, the store is unreadable or a stored value is not literally boolean true. The relay checks, in this order and always before opening the upstream connection: the delegated principal (and its live company scope, Section 3.5); `providerExportAllowed` (else 403 `POLICY_DENY`, reason `provider-export-not-allowed`); the context scope header `X-DeGram-Context-Scope` (`none`, `selection` default, `whole-definition`; anything else 422 `CONTEXT_SCOPE_INVALID`); for `whole-definition`, `wholeDefinitionAllowed` (else 403 `POLICY_DENY`, reason `whole-definition-not-allowed`) and then the per-request consent header `X-DeGram-Whole-Definition-Consent: true` (else 428 `CONSENT_REQUIRED`); the body size limit of 1 MiB (`DEGRAM_RELAY_MAX_BODY_BYTES`, else 413 `RELAY_BODY_TOO_LARGE`, also from `Content-Length`). A policy deny is terminal: the consent header is consulted only once the policy allows the scope, so consent can never override a deny, and the client must not offer a confirm for it. The recorded `contextScope` is part of every provenance line.
- **Operator config.** `GET` and `PUT /degram/admin/llm-config` are admin-only. `GET` returns a masked key preview, never the key. `PUT` merges fields (an omitted field keeps its stored value).
- **Provenance.** Every relayed request appends one JSON line to `degram-llm-provenance.jsonl` under `DG_DATA_DIR`: requested provider and model, served model as the upstream reported it (`null` when absent), response id, fingerprint, usage, outcome, username, company, project, payload size. It never holds prompt text, tool arguments or the key.

## 4. Machine-Checked Blocks

Each block is enclosed by an HTML-comment marker pair. The drift test compares it to the code or compose file named in the heading.

### 4.1 Public routes (`route_policy.ROUTE_POLICIES` public rows plus the heartbeat)

Format `METHOD|PATH|CREDENTIAL`. Credential is `none`, `invite-code` (a single-use invitation code in the body, validated by the handler) or `connector-token` (validated inside the handler). Unsafe public routes still require the CSRF header.

<!-- security-boundary:public-routes:start -->
```
GET|/|none
GET|/auth/options|none
POST|/auth/login|none
POST|/auth/register|none
POST|/auth/accept-invite|invite-code
POST|/connectors/heartbeat|connector-token
```
<!-- security-boundary:public-routes:end -->

### 4.2 Route policy (`route_policy.ROUTE_POLICIES`, every row)

Format `METHOD|PATH|PRINCIPALS|PROJECT_SOURCE|MIN_ROLE`. Principals are joined with `+` and sorted. `-` means the value is `None` in the code. `PROJECT_SOURCE` is `path`, `body`, `query`, `filtered` (handler filters its own output by membership) or `resource:<name>`. Rows are sorted by path, then method.

<!-- security-boundary:route-policy:start -->
```
GET|/|public|-|-
POST|/auth/accept-invite|public|-|-
DELETE|/auth/delegated-token|delegated|-|-
POST|/auth/delegated-token|member|body|viewer
POST|/auth/invites|member|body|owner
POST|/auth/login|public|-|-
POST|/auth/logout|session|-|-
GET|/auth/me|session|-|-
GET|/auth/options|public|-|-
POST|/auth/password|session|-|-
POST|/auth/register|public|-|-
POST|/computgraph/candidates/accept|member|body|editor
GET|/computgraph/candidates/{project}|member|path|viewer
POST|/computgraph/consult|member|body|viewer
POST|/computgraph/context/pull|member|body|editor
POST|/computgraph/generate-inputs|member|body|editor
POST|/computgraph/publish|connector+member|body|editor
POST|/computgraph/recognize|member|body|viewer
POST|/computgraph/validate|member|body|viewer
GET|/connectors|session|filtered|-
POST|/connectors/heartbeat|connector-self|-|-
POST|/connectors/{connector_id}/credentials|member|body|editor
DELETE|/connectors/{connector_id}/credentials/{credential_id}|member|resource:credential|editor
POST|/context/assemble|service|-|-
GET|/context/debug|service|-|-
POST|/context/generate-cypher|service|-|-
GET|/degram/admin/llm-config|admin|-|-
PUT|/degram/admin/llm-config|admin|-|-
POST|/degram/v1/chat/completions|delegated|-|-
POST|/design-rule-sessions|member|body|editor
GET|/design-rule-sessions/{project}|member|path|viewer
POST|/designstate/capture|connector-self|-|-
POST|/execution-result|service|-|-
GET|/execution-result/{execution_id}|session|resource:execution|viewer
GET|/graph/{project}|delegated+member|path|viewer
POST|/graph/{project}/claim-untagged|member|path|editor
PUT|/graph/{project}/node/{node_id}/property|member|path|editor
POST|/identity/bind|member|body|editor
POST|/identity/mint|member|body|editor
GET|/identity/resolve|member|query|viewer
GET|/identity/{dg_id}/properties|member|query|viewer
POST|/identity/{dg_id}/properties|member|query|editor
DELETE|/identity/{dg_id}/representations|member|query|editor
GET|/identity/{dg_id}/representations|member|query|viewer
GET|/integration/speckle/project/{project}|member|path|viewer
PUT|/integration/speckle/project/{project}|member|path|owner
POST|/knowledge/ingest/folder|admin|-|-
DELETE|/knowledge/note/{note_id}|member|resource:note|editor
GET|/knowledge/note/{note_id}|member|resource:note|viewer
PUT|/knowledge/note/{note_id}|member|resource:note|editor
GET|/knowledge/notes/{project}|member|path|viewer
GET|/knowledge/sessions/{project}|member|path|viewer
POST|/knowledge/update/confirm|member|body|editor
POST|/knowledge/update/match|member|body|viewer
POST|/knowledge/update/propose|member|body|editor
POST|/llm/generate|service|-|-
GET|/llm/models|admin|-|-
DELETE|/llm/settings|admin|-|-
GET|/llm/settings|session|-|-
PUT|/llm/settings|admin|-|-
POST|/llm/settings/test|admin|-|-
POST|/mcp|service|-|-
GET|/projects|session|filtered|-
POST|/projects|session|-|-
PUT|/projects/{project}/company|admin|-|-
GET|/projects/{project}/degram-policy|admin|-|-
PUT|/projects/{project}/degram-policy|admin|-|-
GET|/projects/{project}/members|member|path|owner
DELETE|/projects/{project}/members/{username}|member|path|owner
POST|/reasoner/consistency|member|body|viewer
GET|/reasoner/settings|session|-|-
PUT|/reasoner/settings|admin|-|-
POST|/rules/accept-overlap|member|body|editor
POST|/rules/bulk-delete|member|body|editor
POST|/rules/check-conflict|member|body|viewer
POST|/rules/resolve-deletion|member|body|editor
POST|/rules/supersede|member|body|editor
GET|/rules/{project}|delegated+member|path|viewer
DELETE|/rules/{project}/{rule_id}|member|path|editor
GET|/rules/{project}/{rule_id}|member|path|viewer
GET|/rules/{project}/{rule_id}/delete-preview|member|path|viewer
GET|/settings/speckle|admin|-|-
PUT|/settings/speckle|admin|-|-
POST|/validation/publish|connector+member|body|editor
DELETE|/validation/run/{project}/{run_id}|member|path|editor
GET|/validation/runs/{project}|member|path|viewer
GET|/validation/view/{project}|connector+member|path|viewer
GET|/validation/view/{project}/{run_id}|connector+member|path|viewer
GET|/validation/view/{project}/{run_id}/entity/{dg_entity_id}|member|path|viewer
GET|/validation/view/{project}/{run_id}/{rule_id}|connector+member|path|viewer
POST|/workflows/graph-query|member|body|viewer
POST|/workflows/rules-ingest|member|body|editor
```
<!-- security-boundary:route-policy:end -->

### 4.3 Known-default secrets (`secrets_policy`)

Format `KIND|VALUE`. `literal` is an exact value (`KNOWN_DEFAULT_LITERALS`), `prefix` is a lowercase prefix after normalizing `_` to `-` (`KNOWN_DEFAULT_PREFIXES`), and `sha256` is the hex digest of a value that must never appear in the repository in the clear (`KNOWN_DEFAULT_SHA256`). The committed n8n basic-auth password is listed only as its digest.

<!-- security-boundary:known-default-secrets:start -->
```
literal|12345678
literal|admin
literal|minioadmin
literal|neo4j
literal|password
literal|speckle
prefix|change-me
sha256|e80168a5205e76b3632e451c075e2a6715963f8fd6c3e55f7572fc7ff0f40256
```
<!-- security-boundary:known-default-secrets:end -->

### 4.4 Published ports (`docker-compose.yml`, and `docker-compose.multi-user.yml` layered over it)

Format `PROFILE|SERVICE|HOST_IP|HOST_PORT`. `0.0.0.0` means all interfaces. Only the UI (8080) and the Speckle ingress (8090) are routable beyond the host.

<!-- security-boundary:published-ports:start -->
```
local|neo4j|127.0.0.1|7474
local|neo4j|127.0.0.1|7687
local|dg-reasoner|127.0.0.1|8001
local|data-service|127.0.0.1|8000
local|n8n|127.0.0.1|5678
local|ollama|127.0.0.1|11435
local|design-grammars|0.0.0.0|8080
local|speckle-minio|127.0.0.1|9000
local|speckle-minio|127.0.0.1|9001
local|speckle-ingress|0.0.0.0|8090
multi-user|dg-reasoner|127.0.0.1|8001
multi-user|data-service|127.0.0.1|8000
multi-user|ollama|127.0.0.1|11435
multi-user|design-grammars|0.0.0.0|8080
multi-user|speckle-minio|127.0.0.1|9000
multi-user|speckle-minio|127.0.0.1|9001
multi-user|speckle-ingress|0.0.0.0|8090
```
<!-- security-boundary:published-ports:end -->

## 5. Named Carve-Outs and Exclusions

- **`claim-untagged` (NULL-only).** `POST /graph/{project}/claim-untagged` (editor) claims only nodes whose `project` property is `NULL` for the caller's project. It never reassigns a node that already carries another project. Residual: it also claims untagged shared-ontology nodes (`Class`, `ObjectProperty`, `DatatypeProperty`) if any were ever loaded untagged. The live graph held zero untagged nodes on 2026-09-29, so nothing is affected today. A label exclusion is an open owner decision (source: plan 1205-12). Review-fix WR-02: the route never claims nodes of the shared hub graph `SpecGraph`, and the ingest workflow's `postProcess` statements only tag nodes whose `project` is NULL or already the ingesting project (they no longer re-tag another project's node). Residual: a globally untagged node outside `SpecGraph` can still be claimed by the next ingest or claim call, because n8n cannot tell nodes created by this ingest from legacy untagged nodes without a per-run marker.
- **Connector-self routes.** `POST /connectors/heartbeat` and `POST /designstate/capture` are classed `connector-self`: the dependency does not resolve a principal and the handler validates the connector token itself (the capture route also checks the bound project). They are the only non-public routes outside the generic principal check.
- **FastAPI docs.** `/docs`, `/redoc` and `/openapi.json` exist only in the `local` profile.
- **LLM-written Cypher is checked by a fail-closed allowlist (CR-03/CR-04, iteration 3).** `data-service/cypher_allowlist.py` lexes the text and parses it against a small grammar; anything it does not positively recognise is a violation, never skipped. Read path (`graph_query`, and `/mcp` `neo4j_query`): only `MATCH`, `OPTIONAL MATCH`, `WHERE`, `RETURN` (`DISTINCT`, `AS`), `ORDER BY`, `SKIP`, `LIMIT` and a fixed function list; every node pattern binds a variable and is declared with `project: $project` (later mentions are bare `(v)`), and shared-vocabulary labels are no longer exempt. Write path (`rule_ingest`, `rule_edit`): only `MERGE`, `MATCH` (no `WHERE`) and `SET`; one schema label per node, a complete single string-literal key and `project: $project` in every MERGE map, and `SET var.prop = literal` on a bound variable, never `project` or `graph`. Non-ASCII or backticked identifiers, comments, `WITH`, `UNWIND`, `CALL`, `FOREACH`, `LOAD`, subquery blocks, deletes, concatenated or parameterised keys, unlabeled patterns and variable-length paths are violations. Residuals: the result-side filter `find_foreign_project_entities` still exempts shared-vocabulary labels; ingest MERGE keys now include `project`, so `Class`, `DatatypeProperty`, `ObjectProperty`, `Builtin`, `Var` and `Literal` nodes are per project from this change on, and nodes written earlier without a `graph` property do not match the new keys until the ingest `postProcess` tags them (sources: review CR-03/CR-04; plan 1205-06, threat T-1205-06-04).
- **The allowlist grammar was rewritten in review iteration 4 (CR-01, CR-02, WR-01, WR-04, WR-05).** Read expressions now use an operand/operator grammar, so two operands can never sit side by side and a `(` inside an expression is only a grouping or a call: pattern predicates and pattern expressions are rejected outright (the only route to a relationship is a `MATCH`/`OPTIONAL MATCH`, where every node must carry `project: $project`), and every node pattern goes through one shape reader that accepts only `( [var] [:Label]* [{literal map}] )`; Neo4j 5 label-expression syntax (`IS`, `&`, `|`, `!`, `%`) is rejected, never interpreted. `STARTS WITH` and `ENDS WITH` are one operator recognised only in operator position after a complete operand, and a `WITH` anywhere else is always forbidden whatever precedes it. A post-parse audit fails any query containing a parenthesis the parser never classified or a node pattern it did not prove scoped. String literals may contain no backslash (so no escape or unicode-escape sequences) and no doubled quote, so the lexer and Neo4j cannot disagree on where a string ends. A read query may contain no `;`; a write statement may contain one only as its last token (n8n removes it). Nesting deeper than 64 levels, text over 200000 characters, and any internal exception are violations, never an exception to the caller; `/mcp` `neo4j_query` turns an allowlist exception into a structured 400. The Cypher 25 clause words FOR, LET, FILTER, NEXT, OFFSET and CYPHER are forbidden as defence in depth. `data-service/tests/test_cypher_allowlist_probe.py` (marker `neo4j_probe`, opt in with `DG_ALLOWLIST_PROBE_BOLT`) runs every accepted read query against a disposable Neo4j seeded with two tenants and asserts no foreign marker is returned (sources: review iteration 4).
- **Rule and Atom key collisions fail closed.** The write allowlist forces `project: $project` into every ingest MERGE key, so an ingest can no longer touch a node another project owns. Other code (for example `computgraph_publish.py`) still looks Rule and Atom nodes up by id alone, so the id check remains as defence in depth: `POST /context/generate-cypher` returns the candidate as invalid with the collisions listed when an id is held by another project, and answers 503 `KEY_COLLISION_CHECK_UNAVAILABLE` when Neo4j cannot be reached to check (sources: plans 1205-06 and 1205-14).
- **Single-process auth store.** The JSON stores are guarded by an in-process lock. data-service must run as a single process (one worker). Running more workers would let two processes interleave writes to the same file.
- **Body project is authoritative and cross-checked.** For any route, a project value in the path, query and body must agree; otherwise `PROJECT_MISMATCH`. Routes that need a project and receive none fail with `PROJECT_REQUIRED` and never default to an unscoped query.
- **`POST /projects` race (accepted).** The graph half of the project-name uniqueness check reads the graph before taking the store lock, so two simultaneous creations of the same name can race on that half (source: plan 1205-12, threats T-1205-12-06 and T-1205-12-07, accepted in plan 12).
- **data-service cold start (accepted).** data-service has no healthcheck, no `condition: service_healthy` dependency on Neo4j and no restart policy, so it can exit if the Neo4j Bolt port is not yet listening when it starts. Restart it once Neo4j is up (source: plan 1205-09).
- **n8n environment access (unverified until live).** The workflows read `$env`, which requires `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`. That setting is present in compose and unverified against a live publish until plan 1205-18.

## 6. Removed and Restricted Routes

| Route | Disposition | Research finding closed |
|-------|-------------|-------------------------|
| `POST /create_node/` | Removed | Unscoped generic node creator with no project scoping |
| `GET /execution-result/latest/{workflow}` | Removed (`WORKFLOW_STATUS` deleted) | Global last-write-wins slot: concurrent users could read each other's in-flight result |

Resource-bound routes (project resolved server-side from the stored resource, unknown and unauthorized both 404):

| Route | Resource | Finding closed |
|-------|----------|----------------|
| `DELETE /connectors/{connector_id}/credentials/{credential_id}` | `credential` | Any authenticated user could revoke any project's connector credential |
| `GET /execution-result/{execution_id}` | `execution` | Any caller could read another user's LLM output; a result is now bound to the user who started it |
| `GET`, `PUT`, `DELETE /knowledge/note/{note_id}` | `note` | Cross-project note read and edit by id |

Principal-restricted routes: `POST /llm/generate`, `/context/*`, `POST /mcp` and `POST /execution-result` accept only the service token (n8n); the admin-only routes (`GET`, `PUT /degram/admin/llm-config`, `GET`, `PUT /projects/{project}/degram-policy`, `GET`, `PUT /settings/speckle`, `PUT`, `DELETE /llm/settings`, `POST /llm/settings/test`, `GET /llm/models`, `PUT /reasoner/settings`, `POST /knowledge/ingest/folder`) accept only an admin user. `POST /projects` and the read-only `GET` settings routes marked `session` accept any signed-in user. `POST /computgraph/recognize` now requires a body project (previously optional).

## 7. Unsupported Legacy Callers

These callers target the removed direct proxies (`/neo4j/`, `/n8n/`) or removed routes and now fail closed by design. They are unsupported and are not updated by Phase 1205:

- `test/smoke_e2e.sh`, `test/smoke_graph_query.sh`, `test/smoke_rules_ingest.sh`, `test/test_phase04_update_flow.sh`, `test/test_spec_llm.py`, `test/test_spec_schema.py`
- the archived legacy SPA and its model viewer under `graph-viewer/` (including `graph-viewer/index.html`)
- `README.md` lines describing `/execution-result/latest/{workflow}`, and any external script that posts Cypher to the UI's former `/neo4j/` path or calls the n8n webhooks through the UI

`spec/API.md` is the maintained route reference; older pages describing the removed paths are historical.

## 8. Accepted Gaps

Each is deferred deliberately (CONTEXT Deferred Ideas) or accepted with a recorded source. None is silently ignored.

- **Login brute-force protection is layered and depends on the proxy setup (review WR-01, WR-22, WR-23).** nginx limits `POST /auth/login`, `/auth/password`, `/auth/accept-invite` and `/auth/register` to 5 requests per second per client address (burst 10). data-service counts failures per username (5 free failures, then exponential backoff capped at 300 seconds) in memory, so the counters reset on restart, and counts failures per client address only when `DG_TRUSTED_PROXIES` names the front end (or `DG_THROTTLE_LIMIT_IP` is set). Behind a TLS terminator or NAT without that setting every client shares the proxy's address: the nginx limit is then one shared bucket and the per-address counter stays off, so password spraying across many usernames is bounded only by the nginx limit. The per-username counter lets anyone who knows a username slow that account's logins (accepted). With `DG_TRUSTED_PROXIES` set, the UI container's nginx takes the client address from `X-Forwarded-For` for requests arriving from those addresses only.
- **TLS and the `Secure` cookie flag.** The stack terminates no TLS. Bolt TLS is disabled in the Neo4j configuration. `DG_COOKIE_SECURE=true` must be set behind a TLS-terminating front end before an external deployment.
- **Audit logging** of authorization decisions is not implemented; denials are answered but not recorded in an audit trail.
- **Neo4j RBAC and per-tenant databases.** Neo4j Community has no RBAC; tenancy is enforced by the `project` property and the data-service query guards only.
- **External identity provider (OIDC/SSO)** is not supported; accounts are local to data-service.
- **Remote Speckle blob access via MinIO 9000 in `multi-user`.** MinIO stays published on `127.0.0.1` only, but Speckle object access through the ingress on 8090 is governed by Speckle's own authorization, not by this contract.
- **Read-only repository mount.** data-service mounts the repository read-only for fixtures and tools; it can read repository files, including non-secret configuration, from inside the container.
- **Project-name probing via `POST /projects` 409.** A caller can learn that a project name is taken.
- **Shared vocabulary names across tenants.** Class and property names in the shared ontology are visible to every tenant (Section 5).
- **Direct-Bolt Grasshopper repositories** remain unsupported in `multi-user` until they are moved to HTTP.

## 9. Rotation Runbook (D-13)

Every secret that was ever committed in the base compose file, and every secret introduced by Phase 1205, is treated as compromised and rotated. Git history is not rewritten. The owner performs every step in their own terminal; values are typed or generated locally and never pasted into a brief, a prompt, a commit, a log or a chat. This runbook names secrets by variable name only.

**Never rewrite history.** No history-rewriting tool (no `git filter-repo`) and no force push is used to remove old values; rotation, not deletion, is the control.

Order of execution:

1. **Preconditions.** Stack healthy. `.env` exists, is gitignored and complete against `.env.example` (`python tools/security/check_env_file.py --allow-pending-rotation` reports every key `ok` or `pending-rotation`). Back up the `neo4j_data`, `speckle_postgres_data` and `data-service` data volumes if the data matters.
2. **Generate values locally.** Produce each new value with a local generator (for example `python -c "import secrets; print(secrets.token_urlsafe(48))"` run in your own shell), keep them in a password manager, and enter them into `.env` yourself. Use at least 32 characters for `DG_SERVICE_TOKEN` and `LLM_MASTER_SECRET`, and at least 12 for `DG_BOOTSTRAP_ADMIN_PASSWORD`.
3. **Neo4j (`NEO4J_PASSWORD`).** Open an interactive `cypher-shell` session in the neo4j container and change the password with `ALTER CURRENT USER SET PASSWORD FROM ... TO ...`, entering both values at the prompt. Exit, then clear the container's cypher-shell history. Update `NEO4J_PASSWORD` in `.env`. Recreate `data-service`, `dg-reasoner` and `n8n` (`docker compose up -d --force-recreate data-service dg-reasoner n8n`). The neo4j container itself reads `NEO4J_AUTH` only on first initialization of its data volume, so the interactive change is the authoritative one.
4. **Speckle Postgres (`POSTGRES_PASSWORD`).** Open an interactive `psql` session in the `speckle-postgres` container and change the role password at the prompt (`\password`). Update `POSTGRES_PASSWORD` in `.env`. Recreate `speckle-server`, `speckle-webhook-service` and `speckle-fileimport-service`.
5. **MinIO root credentials (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`).** Update both in `.env`. Recreate `speckle-minio` and `speckle-server` (the server reads the same values as its S3 access and secret keys). Verify by uploading a small model and viewing it.
6. **`LLM_MASTER_SECRET` (re-encrypt the stored LLM API key first).** Stored LLM API keys are encrypted at rest under this secret, so changing it without re-encryption makes them undecryptable.
   - In your own shell, export `DG_ROTATE_OLD_LLM_MASTER_SECRET` (the current value) and `DG_ROTATE_NEW_LLM_MASTER_SECRET` (the new value).
   - Dry run: `docker exec -e DG_ROTATE_OLD_LLM_MASTER_SECRET -e DG_ROTATE_NEW_LLM_MASTER_SECRET data-service python rotate_llm_master_secret.py --dry-run` (expect `dry-run-ok`). Under Git Bash prefix the command with `MSYS_NO_PATHCONV=1`.
   - Real run: the same command without `--dry-run` (expect `rotated` or `nothing-to-rotate`).
   - Switch `LLM_MASTER_SECRET` in `.env` to the new value and recreate `data-service`.
   - Unset both `DG_ROTATE_*` shell variables.
7. **`SPECKLE_SESSION_SECRET`.** Update `.env` and recreate `speckle-server`. Existing Speckle web sessions end.
8. **n8n (`N8N_USER`, `N8N_PASSWORD`).** Update both in `.env` (basic-auth values), recreate `n8n`, then change the n8n owner-account password inside the n8n UI. The committed n8n password default in the base compose history looks like a personal password: rotate it in every other place the owner reused it outside this repository (email, other services, password manager entries). Only its SHA-256 digest is recorded in Section 4.3.
9. **`DG_SERVICE_TOKEN`.** Update `.env` and recreate `data-service` and `n8n` together in one command, so the two never disagree.
10. **Bootstrap admin (`DG_BOOTSTRAP_ADMIN_USER`, `DG_BOOTSTRAP_ADMIN_PASSWORD`).** Bootstrap only applies when no admin exists, so editing `.env` does not change a live account. Change the live admin password through `POST /auth/password` (signed in as that admin), then update `.env` to match.
11. **Speckle API tokens and connector tokens.** Rotate `SPECKLE_WRITE_TOKEN` and `SPECKLE_READ_TOKEN` in the Speckle UI, update `.env` (or `/settings/speckle`) and recreate `data-service`. Revoke every Grasshopper connector credential and reissue new ones from the UI; each old `dgc_` token stops working immediately.
12. **Verification.** `python tools/security/check_env_file.py` with no `--allow-pending-rotation` reports every key `ok`. With the stack rebuilt (no cache) and running, `python tools/security/check_live_boundary.py --profile multi-user` reports no failure. Confirm login, a rule ingest through the relay, and a Speckle publish.

## 10. Enforcement and Ownership

| Block or claim | Enforced by |
|----------------|-------------|
| `route-policy` rows equal `ROUTE_POLICIES` field by field, and equal the registered app routes | `data-service/tests/test_security_boundary_spec.py`, `data-service/tests/test_route_inventory.py` |
| `public-routes` equals the public rows plus the heartbeat | `data-service/tests/test_security_boundary_spec.py` |
| `known-default-secrets` equals `secrets_policy` | `data-service/tests/test_security_boundary_spec.py`, `data-service/tests/test_secrets_policy.py` |
| `published-ports` equals the compose bindings for both profiles | `data-service/tests/test_security_boundary_spec.py`, `data-service/tests/test_compose_boundary.py` |
| No `/neo4j/` or `/n8n/` proxy, no credential in `config.js` or the UI bundle | `data-service/tests/test_static_proxy_boundary.py`, `data-service/tests/test_config_js_no_secrets.py` |
| Delegated token mint, scope, CSRF exemption, no-fallback and every revocation case (Section 3.5); project to company map | `data-service/tests/test_delegated_token.py`, `data-service/tests/test_company_scope.py` |
| DeGram relay principal scope, single upstream with model override, key masking and encryption at rest, provenance without content (Section 3.6) | `data-service/tests/test_degram_relay.py` |
| DeGram provider-export policy store, admin routes, deny-by-default, consent and scope denies with zero upstream requests (Section 3.6) | `data-service/tests/test_degram_policy.py`, `data-service/tests/test_degram_relay.py` |
| Live exposure and 401 behavior | `tools/security/check_live_boundary.py` (owner run, against rebuilt containers) |

**Adding a route.** Add the `@app` route with `Depends(auth.require_principal)` (or the router-level dependency), add its row to `route_policy.ROUTE_POLICIES`, add the row to the `route-policy` block in Section 4.2 (and the `public-routes` block if it is public), and run the route inventory and this contract's drift test. A route without all three fails the suite.

**Adding a principal, port or secret.** A new principal type, published port or known-default value changes the corresponding block and Section 3 or 2 prose in the same commit.

**No graph schema change.** Authentication data is JSON under `DG_DATA_DIR`; `cypher_template.txt`, `dataset_schema.json` and `spec/DATABASE.md` are unchanged by this phase.
