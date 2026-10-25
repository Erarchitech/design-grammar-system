---
phase: 1205-security-and-tenancy-release-gate
reviewed: 2026-09-29T22:30:00Z
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
  critical: 2
  warning: 3
  info: 4
  total: 9
status: issues_found
---

# Phase 1205: Code Review Report (iteration 2, re-review after fixes)

**Reviewed:** 2026-09-29T22:30:00Z
**Depth:** standard
**Files Reviewed:** 45
**Status:** issues_found

## Scope note

Same scope as iteration 1: the 45 production files above (tests and docs excluded by the orchestrator). This pass read `1205-REVIEW-FIX.md`, then the fix commits (`git diff da186f5..HEAD`) and the surrounding code. Claims marked "verified" were reproduced by running the code: `data-service/dg_context.py` imported and called locally, and the nginx rate-limit config run in a throwaway `nginx:alpine` container. Files holding live secrets were not read. No structural (fallow) findings were supplied.

## Summary

Of the five iteration-1 Criticals, two are closed (CR-01, CR-02), two are only partly closed (CR-03, CR-04), and one is accepted by design (CR-05).

- **CR-01, CR-02:** closed. The write-token fallback is gone and the read token goes only to `user` and `service` principals. Note ids are now project-scoped and capped. The remaining server-wide read token for viewers is locked by D-12.
- **CR-03, CR-04:** the four literal cases from iteration 1 are fixed, but both regex guards still have verified bypasses that reach the same cross-tenant outcome. The fix report acknowledged that the stronger design (execution-time scoping) was not implemented. It did not find these specific holes.
- **New defect:** the nginx login rate limit added for WR-01 never applies (verified). Everything else in the fix commits looks correct: the throttle logic, atomic stores, constant-time n8n check, WR-15 invite flow, WR-09 client cleanup, and the C# and DE-01 changes.

## Critical Issues

### CR-03: (still open) The project-scope proof for LLM-written graph queries still has verified bypasses

**File:** `data-service/dg_context.py:858-926` (`check_query_project_scope`, first-occurrence loop), `:733-740` (`_SCOPE_NODE_PATTERN`); consumer `data-service/app.py:3146` (`/mcp neo4j_query`)
**Issue:** The fix closed the four iteration-1 cases (backticks, comments, nested braces, `subproject:`). It kept the "first occurrence of a variable decides" design and the ASCII-only tokenizer. Two further bypasses each return zero violations when run locally (verified):

1. **Variable rebinding after `WITH`.**
   ```
   MATCH (n:Rule {project: $project}) WITH count(n) AS c MATCH (n) RETURN n.text, c LIMIT 5
   ```
   `WITH` drops `n` from scope, so the second `MATCH (n)` binds a fresh, unscoped `n` over every tenant. `seen_vars` still contains `n`, so it is skipped. `find_foreign_project_entities` sees only scalars (`n.text`, `c`) and counts nothing, so the data goes out.
2. **Non-ASCII identifiers.**
   ```
   MATCH (ñ) RETURN ñ.text, $project AS p LIMIT 5
   ```
   Cypher accepts Unicode identifiers. `_SCOPE_NODE_PATTERN` only accepts `[A-Za-z_][A-Za-z0-9_]*`. `(ñ)` and `(ñ:Rule)` match neither the node pattern nor `_NODEISH_PAREN_PATTERN`, so the `(` is silently skipped. This is the "unrecognised construct is skipped" failure that the docstring says never happens.

The threat model is unchanged. `/mcp` runs model-written Cypher under the shared admin driver, from a prompt the end user controls.

**Fix:** Do not extend the regexes. Enforce the boundary at execution time, for example:

- Run `graph_query` Cypher against a project-filtered view.
- Or rewrite the query so that every `MATCH` is anchored on a `$project`-filtered `WITH` and reject any second `MATCH` after a `WITH`.

If the static check stays, make it fail closed on what it cannot read:

- Reject any character outside ASCII in the dequoted text.
- Reject `WITH`/`UNWIND` followed by another `MATCH`, or reset `seen_vars` at every `WITH`.
- Treat any `(` that is neither a recognised node pattern nor a function-call or keyword paren as a violation.

Add both queries above to the test suite.

### CR-04: (still open, narrowed) Rule-ingest ownership guards are still bypassable, and only cover Rule/Atom keys

**File:** `data-service/dg_context.py:1084-1145` (`_collect_rule_atom_keys`), `:1147-1197` (`find_cross_project_key_collisions`); wiring `data-service/app.py:2204-2226`
**Issue:** The fix handles quote style, no-variable MERGE and MATCH-then-SET on `Rule`/`Atom` nodes. It also fails closed on a blank project. The remaining bypasses were verified by calling both guards on the strings below. Each returns no violation, and the Neo4j check either does not run or runs on the wrong key. The resulting Cypher is executed by n8n under the admin credentials.

| Statement (project `p`) | Why it passes |
|---|---|
| `MERGE (r:Rule {Rule_Id: 'R_'+'X'})` | Only the leading quoted literal `'R_'` is read as the key. The ownership query runs on `R_`, not on the real key `R_X`, so a foreign-owned `R_X` is overwritten. Any `'a' + b` or `'a' + $v` form works. |
| `MATCH (a:Atom)-[:ARG]->(v) SET a.SWRL='x'` | An Atom pattern next to any relationship is treated as "reached from a keyed Rule", though no Rule is keyed. No ids are collected, so the function returns `[]`. The same holds for `MATCH (r:Rule {Rule_Id:'R_MINE'}) ... MATCH (a:Atom)-[]-()` and every other Atom pattern with a relationship neighbour. |
| `MATCH (r) WHERE r.Rule_Id STARTS WITH 'R_' SET r.SWRL='x'`, `... r.Rule_Id <> 'zz' DETACH DELETE r` | The unlabeled node is not analysed. The key operator regex only knows `:`, `=` and `IN`. |
| `MATCH (n) DETACH DELETE n`, `MATCH (n:Var) DETACH DELETE n`, `MATCH (n:Class) SET n.label='x'` | The guard reads only `Rule`/`Atom`. Var, Literal, Class, Builtin, or unlabeled writes are not looked at, so one prompt-injected ingest can wipe or edit every tenant's graph. |

The fix report says the database-side option was not implemented, so this class stays open.

**Fix:** Move the enforcement into the database instead of analysing model text:

- In the n8n write transaction, add a verification statement, run before commit, that asserts every node created or modified carries `project = $project` (or is a shared-vocabulary node), and roll back otherwise.
- Or rewrite the `MERGE` keys to project-qualified ones.

If the static guard stays, make it stricter:

- Allow only a whitelist of statement shapes: `MERGE`/`SET` on `Rule`, `Atom`, `Var`, `Literal`, `Builtin`, `Class`, `DatatypeProperty` and `ObjectProperty` patterns, each with a plain quoted key.
- Reject `DELETE`, `REMOVE`, and any pattern that is unlabeled or is not in the whitelist.
- Reject any key expression that is not exactly one quoted literal followed by `,` or `}`.

## Warnings

### WR-22: The nginx login rate limit never applies (verified)

**File:** `ui-v2/nginx.conf:3-10` (`map $uri $dg_auth_limit_key`), `:68-72` (`location /data-service/`)
**Issue:** The map keys on `$uri` with the regex `^/data-service/auth/(login|password|accept-invite)$`. The same location runs `rewrite ^/data-service/(.*) /$1 break;`, which rewrites `$uri` to `/auth/login` in the rewrite phase, before the `limit_req` preaccess phase evaluates the map variable. The regex therefore never matches and the key is always empty, which means no limit.

Reproduced in a throwaway `nginx:alpine` container with the same map, zone and location. 30 rapid requests to `/data-service/auth/login` all returned 200. The access log showed `/auth/login key=[]`.

The fix report checked only `nginx -t` and that a bad login still returns 401, so it never exercised the limit. The comment claims the limit exists and the in-process throttle is documented as sitting "behind" it, so the layered defence is one layer short.
**Fix:** Key on the pre-rewrite URI:
```nginx
map $request_uri $dg_auth_limit_key {
  default "";
  ~^/data-service/auth/(login|password|accept-invite)(\?|$) $binary_remote_addr;
}
```
Then verify with a burst of at least 20 requests that 429 appears.

### WR-23: The IP-keyed failure limits become one global bucket behind a TLS terminator or NAT

**File:** `data-service/auth_routes.py:44-52` (`_client_ip`), `:127-150` (login); `data-service/auth.py:751-757` (`THROTTLE_LIMIT_IP = 30`); `ui-v2/nginx.conf`
**Issue:** The client address is `X-Real-IP`, which nginx sets from `$remote_addr`. `spec/SECURITY-BOUNDARY.md` makes TLS the operator's job, so nginx will normally sit behind a TLS-terminating proxy. There is no `real_ip` / `set_real_ip_from` configuration. Every client then shares the proxy's address, and Docker Desktop's port NAT can produce the same effect.

- 30 failed logins from anyone lock the IP key for up to 300 seconds. During the lock even correct credentials are rejected for every user.
- Once WR-22 is fixed, the nginx `limit_req` (5 requests/s, burst 10) is shared the same way.

The per-username key already lets anyone lock a known account (accepted trade-off). This lets an attacker with no username lock out the whole deployment.
**Fix:**

- Trust `X-Forwarded-For` only from a configured proxy list, by adding `set_real_ip_from` and `real_ip_header` to nginx driven by an env var.
- Make `THROTTLE_LIMIT_IP` env-configurable and document the shared-address caveat in the runbook.
- Consider keying the IP throttle on the pair `ip+username`, so it slows guessing without becoming a global lock.

### WR-24: WR-15's existing-account invite path upserts the role, so it can silently change an existing membership

**File:** `data-service/app.py:4510-4515` (`_accept_invite_for_existing_account`), `data-service/auth.py:451-475` (`set_membership`)
**Issue:** After the password check the code calls `auth.set_membership(username, invite["project"], invite["role"])`. `set_membership` overwrites the role of an existing `(username, project)` row. If the account already holds a different role on the invited project, for example was promoted after the invite was issued, accepting the stale invite replaces it in either direction: a downgrade, or an escalation to whatever role the old invite named.

The path is also reached only after `validate_password_policy` has run on the supplied password. An existing account whose current password is below the policy (a legacy bootstrap password) is rejected with a policy error before its password is ever checked.
**Fix:** Do not lower or change an existing role through an invite:
```python
current = auth.get_role(username, invite["project"])
if current is None:
    auth.set_membership(username, invite["project"], invite["role"])
```
Or keep the higher of the two roles. Also run `validate_password_policy` only on the new-account branch.

## Info

### IN-01: Iteration-1 Info items, not in fix scope, are unchanged

**File:** `data-service/app.py:4195` and `:4404` (`PROJECT_NAME_PATTERN` and `NODE_KEY_PATTERN` end in `$`), `:63-71` (`/docs`, `/redoc` and `/openapi.json` unauthenticated), `:4406-4413` (silent 2000/8000 row truncation), `data-service/auth.py` (`policy.min_role or "viewer"`)
**Issue:** Iteration-1 IN-01, IN-02, IN-04 and IN-05 are untouched. IN-03 was fixed with WR-05.
**Fix:** As listed in the iteration-1 review (`re.fullmatch`, gate or disable the docs routes, a `truncated` flag with `ORDER BY`, and raise when a member policy has no role).

### IN-02: A corrupt auth or credential store now surfaces as an unstructured 500

**File:** `data-service/auth.py:96-115` (`AuthStoreError`), `data-service/connectors.py:112-160` (`CredentialStoreError`)
**Issue:** Failing closed is the right behaviour. Neither exception is handled anywhere, so the login, session-resolution and connector routes return a bare 500 with a logged traceback, and startup crash-loops. The operator sees no hint about which file to repair.
**Fix:** Register an exception handler for both classes that returns a structured 503 with code `AUTH_STORE_UNAVAILABLE` and the store file name (never its content).

### IN-03: The WR-04 fix is a denylist

**File:** `data-service/app.py:4568-4590` (`PROTECTED_NODE_KEYS_CI`, `PROTECTED_NODE_KEY_PATTERN`)
**Issue:** As the fix report notes, identity keys not on the list stay editable, for example `name` on Var nodes and `lex` on Literal nodes, which key those nodes together with the project. New key properties added to the schema later are unprotected by default.
**Fix:** Move to an allowlist of the properties the property table actually edits when the owner confirms them.

### IN-04: The failure counters check before they record

**File:** `data-service/auth_routes.py:127-150`
**Issue:** `throttle_retry_after` runs before verification and `throttle_record_failure` after. A burst of parallel requests all passes the check before the first failure is recorded. This is bounded by the scrypt semaphore and the threadpool, so a burst can overshoot the limit by tens of attempts per lock cycle, not without limit.
**Fix:** Reserve an attempt under `_THROTTLE_LOCK` before verifying, and release it on success.

## Accepted by design (not defects)

- **CR-05, default `local` profile hands editors the Neo4j bundle (D-07).** I confirmed the gate reads `auth.deployment_profile()`, the same resolver the lifespan validates, so an unrecognised value fails startup rather than falling through to `local`. Still an open owner choice: limiting the bundle to admin-minted credentials, or warning on second users in `local`.
- **CR-01 residual, the server-wide Speckle read token goes to `user` principals (D-12).** D-12 specifies a project-authorised endpoint serving the read token. The implementation withholds it from connectors and from unknown callers and no longer falls back to the write token. To narrow it further, configure `SPECKLE_READ_TOKEN` with a token scoped to the shared Speckle projects.
- **WR-16, port 8080 published on all interfaces in `local` (D-09).** Only the UI and the Speckle ingress are routable by decision.
- **WR-14, `DG_BOOTSTRAP_ADMIN_*` stay required compose interpolations (D-10).**
- **WR-11, the whole repository is mounted at `/mnt/repo:ro`.** The path check itself was fixed (`is_relative_to`, symlink containment).
- **WR-01, per-process throttle counters that reset on restart.** Login throttling is listed out of scope in CONTEXT, so the in-process design is acceptable. The nginx half is broken (WR-22).

## Closed since iteration 1

Read against the fix commits and, where noted, exercised. No new defect found in them beyond those listed above.

- **CR-01, CR-02:** closed.
- **WR-02:** the fix is partial, as the report states. `claim-untagged` skips `SpecGraph`, and the n8n `postProcess` no longer re-tags a node that belongs to another project. A globally untagged node outside `SpecGraph` can still be claimed.
- **WR-03, WR-06, WR-10, WR-11, WR-12, WR-18, WR-19, WR-20:** closed.
- **WR-05, WR-07, WR-08, WR-14, WR-17, WR-21:** closed as far as the report states. The pinned `n8nio/n8n:2.4.8` tag exists upstream, and the running container reports 2.4.8. The relay-token comparison is correct: length-XOR plus per-character accumulation, and a blank expected value is rejected.
- **WR-09:** the client cleanup is wired as described (owner key, sign-out clear, keyed screens). It is covered only by static tests, so a manual sign-out and sign-in-as-other-user pass is still worth doing.
- **WR-13:** fixed with CR-03 for the two verified false positives. The `WITH` and Unicode gaps in CR-03 are a separate defect.

---

_Reviewed: 2026-09-29T22:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
