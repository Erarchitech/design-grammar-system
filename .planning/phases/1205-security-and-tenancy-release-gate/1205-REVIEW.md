---
phase: 1205-security-and-tenancy-release-gate
reviewed: 2026-09-29T20:35:00Z
depth: standard
files_reviewed: 45
files_reviewed_list:
  - data-service/auth.py
  - data-service/auth_routes.py
  - data-service/route_policy.py
  - data-service/secrets_policy.py
  - data-service/app.py
  - data-service/connectors.py
  - data-service/dg_context.py
  - data-service/rotate_llm_master_secret.py
  - data-service/.dockerignore
  - docker-compose.yml
  - docker-compose.multi-user.yml
  - .env.example
  - n8n/workflows/rules-to-metagraph.json
  - n8n/workflows/graph-query-mcp.json
  - n8n/workflows/spec-ingest.json
  - n8n/workflows/spec-query.json
  - n8n/workflows/spec-update.json
  - tools/de01/legs.py
  - tools/de01/run_de01_repeat.py
  - tools/security/check_env_file.py
  - tools/security/check_live_boundary.py
  - ui-v2/nginx.conf
  - ui-v2/entrypoint.sh
  - ui-v2/gen-config.sh
  - ui-v2/Dockerfile
  - ui-v2/vite.config.js
  - ui-v2/src/lib/apiClient.js
  - ui-v2/src/lib/auth.js
  - ui-v2/src/lib/graphApi.js
  - ui-v2/src/lib/modelApi.js
  - ui-v2/src/lib/inputGenApi.js
  - ui-v2/src/lib/connectorsApi.js
  - ui-v2/src/lib/llmApi.js
  - ui-v2/src/lib/reasonerApi.js
  - ui-v2/src/App.jsx
  - ui-v2/src/landing/LandingLayer.jsx
  - ui-v2/src/screens/ProjectsScreen.jsx
  - ui-v2/src/screens/GraphScreen.jsx
  - DG/src/DG.Core/Data/DataServiceRequestAuth.cs
  - DG/src/DG.Core/Models/ConnectionInfo.cs
  - DG/src/DG.Core/Services/ErrorMessageTemplates.cs
  - DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs
  - DG/src/DG.Grasshopper/Components/ConnectorComponent.cs
  - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
  - DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs
  - DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs
findings:
  critical: 5
  warning: 21
  info: 5
  total: 31
status: issues_found
---

# Phase 1205: Code Review Report

**Reviewed:** 2026-09-29T20:35:00Z
**Depth:** standard
**Files Reviewed:** 45
**Status:** issues_found

## Scope note

The orchestrator limited scope to the 45 production files above (diff base `361d092`; `app.py`, `dg_context.py`, `GraphScreen.jsx`, `ProjectsScreen.jsx`, `LandingLayer.jsx` reviewed by hunk plus surrounding handlers). The phase's 42 test files and its docs were excluded because the total scope exceeded 50 files. No verdict is given on test adequacy. Files that hold live secrets (`.env`, `.secrets/`, `.de01/`, `data-service/data/`) were not read. No structural (fallow) findings were supplied for this run.

Claims marked "verified" were reproduced by importing `data-service/dg_context.py` and running the functions locally. The other claims come from reading the code.

## Summary

The authentication core is sound: scrypt with a dummy hash for unknown users, hashed opaque sessions, deny-by-default `require_principal`, a single-answer 404 for resource routes, and a CSRF header on session-authenticated mutations. The failures are in what sits behind that gate. Five defects break the tenancy boundary that the phase exists to establish:

- **Speckle tokens:** `/validation/view` hands a server-wide Speckle token, falling back to the write token, to every viewer and connector.
- **Knowledge notes:** two knowledge-update routes take note ids with no project filter.
- **Regex guards:** the two regex-based Cypher guards that keep LLM-written Cypher inside one project are both bypassable, and this was verified.
- **Neo4j admin credentials:** in the default `local` profile any editor can obtain the Neo4j admin credentials.

The warnings cover missing login throttling, unsynchronised JSON stores (a revoke can be lost), a global untagged-node claim, incomplete startup secret enforcement, and browser data that survives logout.

## Critical Issues

### CR-01: `/validation/view` returns a server-wide Speckle token, falling back to the WRITE token, to every viewer and connector

**File:** `data-service/app.py:522`, `data-service/app.py:1158` (routes: `data-service/route_policy.py:171-175`)
**Issue:** `get_speckle_settings()` computes `read_token = SPECKLE_READ_TOKEN or persisted.readToken or write_token`. `build_view_payload()` puts `settings.read_token` in every `/validation/view/{project}[/{run_id}[/{rule_id}]]` response. Those three routes allow `viewer` members and also `connector` principals.

- The token is one credential for the whole Speckle server. A viewer of project A can use it against Speckle directly to read every model, including other tenants' models. This defeats the project isolation the phase is meant to enforce.
- When no read token is configured (the `.env.example` default leaves `SPECKLE_READ_TOKEN` as a placeholder that is often never replaced), the fallback returns the WRITE token. A viewer or a connector token then gets write and delete access to all Speckle data.
- `docker-compose.yml` passes `SPECKLE_READ_TOKEN: ${SPECKLE_READ_TOKEN:-}`, so blank is allowed.

**Fix:** Do not return a global token to callers. Options:

- Mint a per-project, per-model, short-lived Speckle token server-side.
- Proxy the Speckle viewer through data-service with the project check.

At minimum, remove the `or write_token` fallback and make the response omit `readToken` for connector principals:
```python
read_token = os.getenv("SPECKLE_READ_TOKEN", "").strip() or persisted.get("readToken", "")  # never write_token
```
and return `{"readToken": settings.read_token if principal.kind == "user" else None}`.

### CR-02: `/knowledge/update/propose` and `/confirm` do not scope note ids to the authorised project (cross-project read and write, BOLA)

**File:** `data-service/app.py:4015-4101`
**Issue:** The route policy authorises the body `project`. The handlers then look notes up with `MATCH (n:SpecNote {noteId: $noteId, graph: $graph})`, which has no `project` predicate.

- `propose` returns `originalContent`, `proposedContent` and `diffHtml` for any `noteId` in `noteIds`. An editor of project A who supplies `project=A` and a note id belonging to project B reads B's note content. The id is also sent to the LLM.
- `confirm` overwrites the content of any note id, passing the optimistic-lock `updatedAt` check, whatever project the note belongs to. It then records the `SpecSession` under project A.
- The sibling single-note routes were fixed with the `note` resource resolver, but these two routes were missed. Note ids from `n8n` are `Date.now().toString(36)-random`, so they are guessable or enumerable through `GET /knowledge/notes/{project}` on any project the attacker can see.
- `noteIds` is also unbounded. Each id triggers a sequential `call_n8n_sync` that blocks a threadpool thread for up to 120 seconds, so one editor request can exhaust the pool.

**Fix:** Add `project: $project` to all three note queries: the propose read, the confirm existence check, and the confirm `SET`. Return 404 for a mismatch. Cap `noteIds` and `notes`, for example at 20.
```python
"MATCH (n:SpecNote {noteId: $noteId, project: $project, graph: $graph}) ...",
{"noteId": note_id, "project": payload.project, "graph": SPEC_GRAPH}
```

### CR-03: The project-scope "static proof" for LLM-written graph queries is forgeable (verified)

**File:** `data-service/dg_context.py:718-751` (`_STRING_LITERAL_PATTERN`, `_SCOPE_NODE_PATTERN`), `data-service/dg_context.py:754-871` (`check_query_project_scope`); consumers `data-service/app.py:3052-3090` (`/mcp neo4j_query`) and the `/context/generate-cypher` guard
**Issue:** `/mcp` executes model-written Cypher with the shared admin driver. The Cypher comes from a prompt the end user controls, so a prompt-injected query is the threat. The tenancy control for graph reads is `check_query_project_scope` plus `find_foreign_project_entities`. Running the checker locally, each query below returned NO violations:

| Query | Why it passes |
|---|---|
| ``MATCH (`n`) RETURN `n`.text, $project AS p LIMIT 50`` | The regex does not recognise a backticked variable, so the node pattern is skipped entirely. |
| `/* (n {project: $project}) */ MATCH (n) RETURN n.text LIMIT 5` | Comments are not stripped. The commented pattern becomes the "first occurrence", so the real `(n)` is treated as already scoped. The same works with `//` comments. |
| `MATCH (n {a: {b: 1}.b}) RETURN n.text, $project LIMIT 5` | `\{[^{}]*\}` cannot match nested braces, so the node is skipped (fail-open). |
| `MATCH (n {subproject: $project}) ...` | `project\s*:\s*\$project` also matches inside `subproject:`. |

The result-side defence, `find_foreign_project_entities`, only counts graph entities (nodes, relationships, paths). A query that returns properties (`n.text`, `n.SWRL`, `r.statePayloadJson`) as scalars exfiltrates other tenants' data undetected. Only the first-occurrence rule stands between a user and every project. The docstring says it "never fails open", but unrecognised constructs are silently skipped.

**Fix:** Do not rely on regex analysis for the isolation guarantee. Enforce scope at execution time:

- Rewrite or wrap the query so it runs only over a project-filtered view, or run it in a read-only session against a per-project projection.
- If static checking is kept, parse with a real Cypher parser (or reject any query containing a comment, a backtick, nested braces or a `[` map access) and fail closed on anything the tokenizer does not fully consume.
- Verify results per returned scalar row, not only per graph entity.

Also add the four cases above to the test suite.

### CR-04: Rule-ingest ownership guards are bypassable (verified), letting one project overwrite another project's Rule/Atom

**File:** `data-service/dg_context.py:874-980` (`check_foreign_project_literals`, `find_cross_project_key_collisions`, `_RULE_ID_PROP_PATTERN`, `_MERGE_NODE_PATTERN` at `:614`); wiring `data-service/app.py:2126-2160`
**Issue:** Schema v4 keys Rule and Atom by id alone. The only protection against cross-project overwrite is a regex collision check on `MERGE (var:Rule {…Rule_Id: '…'})`. Verified locally:

- Double quotes: `MERGE (r:Rule {Rule_Id: "R_X"}) SET r.SWRL="a"` collects no ids, so the function returns `[]` without querying Neo4j.
- No variable: `MERGE (:Rule {Rule_Id: 'R_X'})` is not matched by `_MERGE_NODE_PATTERN`, because it requires `(\w+)`.
- MATCH-then-SET: `MATCH (r:Rule {Rule_Id: 'R_X'}) SET r.SWRL='a'` is not analysed at all.
- Foreign-literal check: it misses `` SET r.`project` = 'victim' `` and `SET r['project'] = 'victim'`.

n8n executes the resulting Cypher under the admin credentials. A user who can post `rulesText` and is willing to steer the LLM output (rule ids follow the predictable `R_<DOMAIN>_<PROP>_<LIMIT>_V` pattern) can therefore modify or re-tag another tenant's rules.

Separately, `post_context_generate_cypher` only runs the ownership guards when `project` is non-blank. A blank project on a `rule_ingest` or `rule_edit` request skips them silently. The route is service-only and n8n always sends a project, but the guard should fail closed.

**Fix:** Enforce ownership in the database, not by regex on model text:

- Run the generated Cypher only after rewriting `Rule`/`Atom` MERGE keys to project-qualified keys.
- Or execute the ingest Cypher with a bound `$project` and a post-write verification query. Assert that every node the statement touched has `project = $project`, and roll back otherwise.
- Require `project` for `rule_ingest` and `rule_edit`, and return 400 when it is missing.

### CR-05: The default `local` profile gives the Neo4j admin credentials to any editor

**File:** `data-service/app.py:1547-1567` (`connector_heartbeat`); `docker-compose.yml:76` (`DG_DEPLOYMENT: ${DG_DEPLOYMENT:-local}`); `data-service/route_policy.py:136`
**Issue:** The heartbeat returns `Neo4jBundle(uri, user, password, database)` unless the profile is exactly `multi-user`.

- `POST /connectors/{id}/credentials` is open to `editor` members, so any editor of any project can mint a connector token, call the heartbeat, and receive the admin Neo4j password with a reachable Bolt endpoint. That gives full read/write access to every tenant, bypassing everything else in this phase.
- The profile defaults to `local` when `DG_DEPLOYMENT` is unset, and the gate is written as `!= "multi-user"`, so a forgotten variable in a shared deployment fails open.
- Invites, memberships and multiple users are fully functional in `local`, so "trusted local" is not actually enforced.

**Fix:**

- Return the bundle only when the profile is explicitly `local` and the principal is trusted for it.
- Better, restrict bundle issuance to admin-minted credentials, or drop the bundle and route the Grasshopper components through data-service.
- Make `multi-user` the default, or refuse to start when `DG_DEPLOYMENT` is unset.
- Either forbid invites and second users in `local`, or document and warn on it.
```python
if auth.deployment_profile() == "local" and record.get("issued_by_admin"):
    neo4j_bundle = ...
```

## Warnings

### WR-01: No throttling, lockout or rate limit on `/auth/login`, and each attempt costs a scrypt derivation

**File:** `data-service/auth_routes.py:84-107`, `ui-v2/nginx.conf`
**Issue:** There is no per-account or per-IP attempt limit, no backoff, and no nginx `limit_req`. The minimum password length is 12 with no complexity rule. Every unauthenticated login runs a 16 MB scrypt in the threadpool, including the dummy hash for unknown users, so unauthenticated CPU and memory exhaustion is trivial. `POST /auth/password` also re-verifies the current password with no throttle.
**Fix:** Add a per-username and per-IP failure counter with exponential backoff, kept under the store lock. Add an nginx `limit_req` on `/data-service/auth/`. Cap concurrent scrypt work.

### WR-02: `claim-untagged` and the ingest `postProcess` re-tag every project-less node in the database

**File:** `data-service/app.py:4416-4418` and `:4491`; `n8n/workflows/rules-to-metagraph.json` ("Prepare Graph Payload", `postProcess`)
**Issue:** `MATCH (n) WHERE n.project IS NULL SET n.project = $project` runs for any editor of any project and claims all untagged nodes globally. That includes shared hub nodes (for example `SpecClass`) and another tenant's nodes that are not yet tagged. The ingest `postProcess` statements do the same (`MATCH (n) WHERE n.graph IS NULL SET n.graph=…, n.project=$project`). The stated aim of 1205-05 was to scope these. The UI still calls `tagProjectNodes` after every ingest, so this global write path is exercised routinely.
**Fix:** Drop `claim-untagged` (the ingest already tags) or restrict it to admin. Restrict `postProcess` to nodes created in this transaction, for example by matching on a per-run marker, not on "untagged".

### WR-03: `connectors.py` credential store has no lock and non-atomic writes, so a concurrent heartbeat can silently un-revoke a credential

**File:** `data-service/connectors.py:110-135`, `:193-209`, `:226-241`
**Issue:** `create_credential`, `revoke_credential` and `record_heartbeat` each read the whole list and write it back. The routes are sync `def`, so they run in a threadpool. A heartbeat that read the list before a revoke and saved it after resurrects the revoked credential. `save_credentials` uses a plain `write_text`, so a crash truncates the file. `load_credentials` then returns `[]` on the parse error, and the next mint wipes all credentials. `auth.py` has both the lock and the atomic replace; this store was not brought up to the same standard.
**Fix:** Reuse `auth._STORE_LOCK`, or a lock local to `connectors.py`, around every read-modify-write. Write through a temp file and `os.replace`. Treat a malformed file as an error, not as an empty list.

### WR-04: Editors can write any node property except `project` and `graph`, including validation and evidence properties

**File:** `data-service/app.py:4403-4404`, `:4497-4530` (`update_node_property`)
**Issue:** The denylist is `{"project", "graph"}`. An editor can set `status` on a `ValidationEntity`, `ValidStatus`, `shaclReportJson`, `evidenceEnvelopeJson`, `statePayloadJson`, `Rule_Id`, `SWRL`, `dgId`, `StateId` and any key that identity or evidence logic relies on. That defeats the evidence contract and the reproducibility claims of the earlier phases, and it lets one editor rewrite a rule's identity.
**Fix:** Switch to an allowlist of the properties the graph viewer actually edits. Restrict to specific labels. Never allow `Rule_Id`, `Atom_Id`, `StateId`, `dgId` or the `*Json` evidence properties.

### WR-05: The multi-user startup gate covers only four secrets and never forces `Secure` cookies

**File:** `data-service/secrets_policy.py:79-84`; `docker-compose.multi-user.yml`; `docker-compose.yml:77` (`DG_COOKIE_SECURE: ${DG_COOKIE_SECURE:-false}`)
**Issue:** `enforce_startup_secrets` checks `NEO4J_PASSWORD`, `LLM_MASTER_SECRET`, `DG_SERVICE_TOKEN` and `DG_BOOTSTRAP_ADMIN_PASSWORD`. `N8N_PASSWORD`, `POSTGRES_PASSWORD`, `MINIO_ROOT_*` and `SPECKLE_SESSION_SECRET` are consumed by other containers. Compose only requires them to be non-empty (`:?`), so the `change-me-*` placeholders from `.env.example` boot in `multi-user`. The multi-user override does not set `DG_COOKIE_SECURE=true`, and nothing requires it, so the session cookie is sent over plain HTTP to port 8080 unless the operator adds TLS and the flag. `check_env_file.py` covers the other keys, but it is owner-run and optional.
**Fix:** Have the multi-user override set `DG_COOKIE_SECURE: "true"`, or refuse to start `multi-user` with it false. Add a compose-level check, such as an init container or a wrapper script, that runs `check_env_file.py` before `up`, or extend `DATA_SERVICE_SECRET_KEYS` with the remaining keys passed to the data-service container.

### WR-06: A non-ASCII `X-DG-Service-Token` header causes an unhandled 500 from `hmac.compare_digest` (verified)

**File:** `data-service/auth.py:407`
**Issue:** `hmac.compare_digest(header_value, expected)` raises `TypeError` for `str` arguments containing non-ASCII characters. Starlette decodes headers as latin-1, so an unauthenticated request with a byte of 0x80 or higher in the header produces a 500 and a logged traceback instead of a 401. It fails closed, but it is an unauthenticated error and noise generator.
**Fix:** Compare bytes: `hmac.compare_digest(header_value.encode("utf-8"), expected.encode("utf-8"))`, or catch `TypeError` and return `None`.

### WR-07: `POST /computgraph/context/pull` is open to `viewer` and returns whatever is on the single live canvas

**File:** `data-service/app.py:1667-1679`; `data-service/route_policy.py:146`
**Issue:** The canvas bridge reads the one Grasshopper session on the host. A viewer of project X can pull an architect's live canvas, which may belong to another project, then have it stamped `project=X`. Nothing binds the canvas to a project.
**Fix:** Raise the minimum role to `editor` or `owner` at minimum. Bind the bridge to a project (a per-project bridge token), and refuse when the canvas belongs to a different project.

### WR-08: Speckle project ids are not tenant-bound, so an owner can point their DG project at another tenant's Speckle project

**File:** `data-service/app.py` (`PUT /integration/speckle/project/{project}`, `publish_validation`, `delete_validation_run`); `data-service/route_policy.py:124`
**Issue:** The integration is owner-editable with arbitrary `speckleProjectId` and `baseModelId`. Publishing and deleting use the single server-wide write token, so an owner of A can write validation models into, or delete versions from, a Speckle project that another tenant's DG project uses. `_auto_configure_integration` also falls back to the global env project for any project.
**Fix:** Keep a server-side mapping from DG project to allowed Speckle project ids, and admin-gate changes to it. Reject a `speckleProjectId` already bound to a different DG project.

### WR-09: Logout and membership loss leave tenant data in browser memory and `localStorage`

**File:** `ui-v2/src/App.jsx:66-110`; `ui-v2/src/screens/GraphScreen.jsx:157-194`, `:420-427`; `ui-v2/src/landing/LandingLayer.jsx` (`signOut`)
**Issue:** `signOut` calls `logout()` and `onUser(null)` only. All screen layers stay mounted with their graph, run and token state. `dgv2_project`, `dgv2_graph_snapshots_<project>` (whole built graphs), run thumbnails and viewport blobs stay in `localStorage`. The next user of the same browser, or a user whose membership was revoked, still holds that data and the last project selection. The Speckle read token returned by `/validation/view` also stays in Model screen state.
**Fix:** On logout or `AUTH_EXPIRED_EVENT`, clear `project`, remove every `dgv2_*` key that holds tenant content, and remount the screen layers (for example, key them on the user). Namespace stored keys by username.

### WR-10: `actor` on `/rules/supersede` and `/rules/accept-overlap` is client-supplied, so provenance can be forged

**File:** `data-service/app.py:3769`, `:3875`
**Issue:** The provenance record stores `actor` verbatim from the request body. Any editor can attribute the supersede or overlap acceptance to another user. The authenticated principal is available in `request.state.principal` and is unused here.
**Fix:** Ignore the body `actor` and write `request.state.principal.username`. Accept the parameter only as a display hint if it must stay.

### WR-11: The whole repository, including `.env`, is mounted into the data-service container, and the ingest path guard uses a string prefix check

**File:** `docker-compose.yml:86` (`.:/mnt/repo:ro`); `data-service/app.py:1177-1184` (`validate_ingest_path`)
**Issue:** `.env`, `.secrets/` and `data-service/data/` (session and user stores) are readable inside the container. The only barrier is the dot-segment filter added in `ingest_folder`, which does not cover non-dot paths such as `data-service/data`. `validate_ingest_path` uses `str(candidate).startswith(str(root))`, which also accepts a sibling directory such as `/mnt/repo2`. It should use `Path.is_relative_to`.
**Fix:** Mount only the directories the ingest actually needs (for example `DG_OBSIDIAN` read-only). Replace the prefix comparison with `candidate.is_relative_to(root.resolve())`.

### WR-12: Internal exception text is returned to clients

**File:** `data-service/app.py:1796-1808`, `:1846-1860`, `:1889-1902`, `:1992-1998`, `:2065-2071`, `:2857-2864`
**Issue:** Handlers place `str(exc)` or `{exc}` directly in the response. Neo4j, driver and Speckle exceptions can contain URIs, Cypher fragments, internal hostnames and token fragments. These routes are now reachable by any viewer or editor.
**Fix:** Log the exception server-side with a correlation id and return a generic message with a code. Keep `str(exc)` only for exceptions defined as user-facing (the `ValueError` validation branches).

### WR-13: The scope validator rejects legitimate queries (verified false positives)

**File:** `data-service/dg_context.py:732-751`
**Issue:** The comment claims a function call's argument list can never match the node pattern, but `count(r)` and `toLower(id)` are `(var)` and match. If the variable is a relationship or an alias that was not introduced through a scoped node pattern, the query is reported as `missing_project_scope`. Verified: ``MATCH (a {project:$project})-[r]->(b {project:$project}) RETURN count(r)`` and ``MATCH (a:Rule {project:$project}) WITH a.Rule_Id AS id RETURN toLower(id)`` are both rejected. That burns the bounded retries and makes common questions ("how many rules…") fail.
**Fix:** Track variable bindings for relationships and aliases (see CR-03) rather than treating every `(name)` as a node pattern.

### WR-14: A malformed bootstrap username stops the service even in the `local` profile, and the bootstrap secrets stay required forever

**File:** `data-service/auth.py:665` (`create_user` inside `ensure_bootstrap_admin`); `docker-compose.yml:74-75`
**Issue:** The docstring says a bad bootstrap value logs a warning in `local`. Only a weak password is handled that way. An invalid username makes `normalize_username` raise `ValueError` out of the lifespan, so startup fails in both profiles. Compose also requires `DG_BOOTSTRAP_ADMIN_USER` and `DG_BOOTSTRAP_ADMIN_PASSWORD` on every start, so the admin password stays in the container environment (visible through `docker inspect`) after the admin exists.
**Fix:** Catch the username `ValueError` and treat it as `weak-password`-style. Make the compose variables optional (`${VAR:-}`), and have the bootstrap function enforce presence only when no admin exists.

### WR-15: An invite for a username is burned by the first account creation

**File:** `data-service/app.py:4366-4390` (`accept_invite`)
**Issue:** When two projects invite the same new username, accepting the first invite creates the account. The second code then fails at `create_user` with the generic `INVITE_INVALID`, and the invite is already consumed. The invitee cannot join the second project until an owner re-invites, which then takes the "member-added" path. There is no message telling the user why.
**Fix:** Look up the account before consuming. If it exists, add the membership for the invited project and require login, or return a distinct hint.

### WR-16: nginx sets no security headers, and port 8080 is published to all interfaces in `local`

**File:** `ui-v2/nginx.conf`; `docker-compose.yml:146`
**Issue:** There is no `Content-Security-Policy`, `frame-ancestors`/`X-Frame-Options`, `X-Content-Type-Options` or `Referrer-Policy`. In `local`, `8080:80` binds every interface while the rest of the stack was moved to `127.0.0.1`, so a local-profile deployment is reachable from the LAN with its default secrets allowed.
**Fix:** Add the headers in a shared `add_header ... always` block. Publish `127.0.0.1:8080:80` in the base file and let the multi-user override widen it.

### WR-17: C# publish clients hide the real token failure and send the token over plain HTTP

**File:** `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs`, `ComputgraphPublishClient.cs` (the `TryApplyConnectorToken(..., out _)` call); `tools/de01/legs.py` (`data_service_auth_headers`)
**Issue:** The failure reason is discarded (`out _`) and `PublishTokenMissing` is thrown for both a blank token and a token without the `dgc_` prefix, so a mistyped token reads as "no platform token". The token is sent to whatever `DataServiceUrl` the user typed, including `http://` to a non-loopback host. `legs.py` attaches it as a client-level header to `config`-supplied base URLs.
**Fix:** Branch on `PublishAuthOutcome.MalformedToken` and give it its own message. Warn or refuse to send the token to a non-loopback `http://` URL.

### WR-18: `rotate_llm_master_secret.py` reports success when the settings file cannot be read

**File:** `data-service/rotate_llm_master_secret.py:79-96`, `:126-128`
**Issue:** A malformed, unreadable or non-dict `llm-settings.json` returns `None`, and `rotate` maps that to `nothing-to-rotate` with exit 0. An operator following the runbook then changes `LLM_MASTER_SECRET`, and the stored API key becomes undecryptable. The write also races a live `PUT /llm/settings`, since there is no lock.
**Fix:** Distinguish "file absent" from "file present but unreadable" and exit non-zero for the latter. Document stopping data-service (or taking a lock) during rotation.

### WR-19: `GET /llm/settings` is open to any signed-in user

**File:** `data-service/route_policy.py:128`; `data-service/app.py:1309`
**Issue:** Any member sees the provider, model, `baseUrl` and the masked API key preview. Only admin routes should expose key material, even masked, and internal `baseUrl` values.
**Fix:** Return only `provider` and `model` to non-admins. Gate the rest to `_ADM`.

### WR-20: Auth JSON stores are fail-soft on read and hazardous on write

**File:** `data-service/auth.py:83-112`
**Issue:** `_load` returns `[]` for an unreadable or corrupt file. The next `_save` then overwrites it. A corrupt `auth-users.json` therefore loses every account, and bootstrap recreates only the admin. Files and temp files are created with default permissions inside a bind mount that is visible on the host (scrypt hashes and session token hashes). A failed write leaks its `.tmp-…` file. Sessions of other users are never pruned (`create_session` prunes only the caller's), so `auth-sessions.json` grows without bound.
**Fix:** Raise on corruption, or move the bad file aside and refuse to start. `os.chmod(tmp, 0o600)` before the replace, and clean up the temp file in a `finally`. Prune all expired sessions in `create_session`.

### WR-21: n8n container hardening is weaker than the comments claim

**File:** `docker-compose.yml:96-121`; `n8n/workflows/*.json` ("Verify Relay Token")
**Issue:**

- `N8N_BASIC_AUTH_*` is ignored by current n8n releases. The image is `n8nio/n8n` with no tag (and `speckle/*:latest`), so the editor is protected only by first-visitor account creation on the loopback port.
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` exposes `DG_SERVICE_TOKEN` and `NEO4J_PASSWORD` to every workflow expression and code node.
- The relay check `provided !== expected` is not constant-time. Exposure is limited to the internal network, but it is the same secret that authenticates `/mcp` and `/llm/generate`.

**Fix:** Pin image digests. Set up n8n owner accounts explicitly and remove the dead basic-auth variables. Move the Neo4j password into an n8n credential and keep only the token in the environment. Use a constant-time compare in the relay check.

## Info

### IN-01: `$` in `PROJECT_NAME_PATTERN` and `NODE_KEY_PATTERN` accepts a trailing newline (verified)

**File:** `data-service/app.py:4195`, `:4404`
**Issue:** `re.match(r"^…$", "proj\n")` matches. `POST /projects` accepts `"proj\n"`, which then flows into LLM prompts (`project = '…'` in the ingest prompt) and UI labels. The property-key check similarly accepts `"key\n"`.
**Fix:** Use `re.fullmatch` or `\Z`.

### IN-02: `/docs`, `/redoc` and `/openapi.json` are unauthenticated in the `local` profile

**File:** `data-service/app.py:63-71`
**Issue:** They are registered on `app`, outside the guarded router, so they list every route for anyone who can reach port 8000 (or `/data-service/docs`) in `local`.
**Fix:** Serve them behind the same dependency, or disable them by default and opt in with an env flag.

### IN-03: `check_env_file.py` does not check `DG_COOKIE_SECURE` or `DG_DEPLOYMENT`, and its parser mishandles inline comments

**File:** `tools/security/check_env_file.py:51-70`
**Issue:** `KEY=value # note` keeps the comment in the value, while Compose strips it. `DG_COOKIE_SECURE=false` with `DG_DEPLOYMENT=multi-user` is reported `ok`. `export KEY=…` lines are ignored.
**Fix:** Parse inline comments as Compose does, and add a cross-key rule for the multi-user profile.

### IN-04: The graph read silently truncates

**File:** `data-service/app.py:4406-4413` (`GRAPH_NODES_QUERY … LIMIT 2000`, `GRAPH_RELS_QUERY … LIMIT 8000`)
**Issue:** Neither query has an `ORDER BY`, and the response has no `truncated` flag. Nodes and relationships are truncated independently, so dangling relationships and partial graphs look complete in the UI.
**Fix:** Add a deterministic order, return `truncated: true` when a limit is hit, and filter relationships to the returned node ids.

### IN-05: `min_role` defaults to `viewer` when a member policy omits it

**File:** `data-service/auth.py:890`
**Issue:** `policy.min_role or "viewer"` is fail-open toward the weakest role if a future `_MEM` policy forgets `role=`. The route-inventory test may not catch it.
**Fix:** Raise `ROUTE_UNCLASSIFIED` when a `member` policy has no `min_role`.

---

_Reviewed: 2026-09-29T20:35:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
