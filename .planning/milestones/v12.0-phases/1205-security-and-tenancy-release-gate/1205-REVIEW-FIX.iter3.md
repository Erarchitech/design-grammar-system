---
phase: 1205-security-and-tenancy-release-gate
fixed_at: 2026-09-29T21:35:00Z
review_path: .planning/phases/1205-security-and-tenancy-release-gate/1205-REVIEW.md
iteration: 1
findings_in_scope: 26
fixed: 25
skipped: 1
status: partial
---

# Phase 1205: Code Review Fix Report

**Fixed at:** 2026-09-29T21:35:00Z
**Source review:** .planning/phases/1205-security-and-tenancy-release-gate/1205-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 26 (5 Critical, 21 Warning; Info excluded by `fix_scope: critical_warning`)
- Fixed: 25 (each one commit; WR-13 shares the CR-03 commit)
- Skipped: 1 (CR-05, by design under D-07)

Fixes were made in an isolated worktree on a temp branch, then fast-forwarded onto `master` (25 commits, `54cb2b4`..`382a865`). The worktree, temp branch and recovery sentinel were removed. Regression tests for every fix are in `data-service/tests/test_review_fix_1205.py` (plus additions to `test_graph_routes.py`, `test_rotate_llm_master_secret.py`, `tools/security/tests/test_check_env_file.py`, `tools/de01/tests/test_de01_auth_headers.py` and two DG.Tests files). No test uses an auth override (D-20).

**Status legend.** Most findings are logic or policy errors, so tiers 1 and 2 (syntax and re-read) cannot prove them correct. Those are marked `fixed: requires human verification`. Several fixes are deliberately partial (called out per finding) because the remainder would reverse a locked decision or needs an owner choice.

## Verification performed

- Host pytest on every touched test file after each fix.
- In-container, after `docker compose build data-service && up -d --no-deps data-service` (container confirmed to hold the new code): `3103 passed, 3 skipped, 12 failed`. The 12 failures are exactly the known environmental set (10 `test_cq3_attribute_of.py`, `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, `test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`). Baseline was 2986 passed, 1 skipped; the +117 are new tests, and the 2 extra skips are new node-dependent tests (no `node` in the image).
- `npm --prefix ui-v2 run build`: OK. `design-grammars` rebuilt with `--no-cache` and recreated; the new security headers were confirmed live on `http://localhost:8080/`, and `/data-service/auth/login` still answers 401 for bad credentials.
- `nginx -t` on the new `ui-v2/nginx.conf` (in `nginx:alpine`): OK. `test_static_proxy_boundary.py` (exact proxied-location set) passes.
- `dotnet build DG.sln -c Release`: 0 warnings, 0 errors. `dotnet test` (run in the temp worktree): 587 passed, 5 failed. Four are the known `DesignStateValidationFlowTests` E2E failures (Neo4j and auth not available to the test process). The fifth, `FrameAblatedCorpusEmitterTests`, fails only because a git worktree's `.git` is a file ("Could not locate repository root (no .git ancestor)"). It is an artefact of the worktree, not of these changes. **Re-run `dotnet test .\DG\tests\DG.Tests\` once from the main checkout to confirm 4 failures only** (the C# build outputs there are tracked and already dirty, so I did not build in the main tree).
- `tools/de01` tests: 146 pass; the one failure (`test_de01_runner_against_golden_fixture_has_zero_silent_disagreements`) fails identically without these changes (needs live services).
- n8n live publish (WR-02, WR-21): done. The five active workflows were imported with their live ids preserved (temporary copies; repo files untouched), each published with `n8n publish:workflow`, and n8n recreated (it now runs the pinned `n8nio/n8n:2.4.8`). Confirmed by node names only: `Verify Relay Token` present 5/5, the constant-time check present 5/5, `active` true and `activeVersionId == versionId` 5/5; exactly the same five ids are active. A request with a wrong token is rejected by the new code (n8n log shows `relay token rejected [Line 14]`, the new line number). I did not send a correct-token request, because that would start a real LLM-backed execution.

## Fixed Issues

### CR-01: `/validation/view` returned a server-wide / write Speckle token
**Status:** fixed: requires human verification
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 54cb2b4
**Applied fix:** Removed the `or write_token` fallback from `get_speckle_settings()`. `build_view_payload()` now takes the principal and releases the read token only to `user` and `service` principals, never to `connector` principals and never when the caller is unknown. The three view routes pass `request.state.principal`.
**Residual:** a `user` principal still receives the single server-wide read token (the review's options of per-project tokens or a proxy are not implemented). If no read token is configured, the viewer gets `readToken: null` and the Model screen shows no model, which is the safe outcome.

### CR-02: `/knowledge/update/propose` and `/confirm` were not project-scoped
**Status:** fixed: requires human verification
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** e979194
**Applied fix:** All three note queries now carry `project: $project`; a note of another project gets the same 404 as an unknown one. `noteIds` and `notes` are capped at 20 (`KNOWLEDGE_UPDATE_MAX_NOTES`).

### CR-03: Project-scope static proof for LLM Cypher was forgeable (also fixes WR-13)
**Status:** fixed: requires human verification
**Files modified:** `data-service/dg_context.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 1f57a24
**Applied fix:** `check_query_project_scope` now fails closed. Backticks, backslashes, comments and nested braces are rejected (`unsupported_syntax`). Node patterns are found by walking every `(` that is not a function-call argument list (this also fixes the WR-13 false positives for `count(r)` and `toLower(id)`); `MATCH(n)` is still treated as a pattern. A pattern the parser cannot read (label expressions such as `:A|B`, inline `WHERE`, parameter maps) is rejected, not skipped. `project: $project` must be exactly the key `project` (`subproject:` no longer counts). All four review cases are in the tests.
**Residual:** the guarantee is still static analysis of model-written Cypher, and result-side checking still only sees graph entities, not scalars. A query returning foreign properties as scalars is prevented only by the static proof. The review's stronger fix (execution-time scoping or a parser) is not implemented. Queries using `EXISTS {}` or `COUNT {}` subqueries are now rejected (nested braces), so those will burn retries.

### CR-04: Rule-ingest ownership guards were bypassable
**Status:** fixed: requires human verification
**Files modified:** `data-service/dg_context.py`, `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 44a322d
**Applied fix:** Rule/Atom keys are now collected from any node pattern in any clause (MERGE, MATCH, CREATE; with or without a variable; single or double quotes; backticked key names), reading structure from a string-masked copy of the Cypher. A Rule pattern without a literal `Rule_Id`, an Atom pattern without a literal `Atom_Id` that is not reached through a relationship, or a non-literal or `IN`-list key fails closed without touching Neo4j. `check_foreign_project_literals` also rejects backtick or bracket forms of the `project` key and non-literal `project` values. `/context/generate-cypher` now returns 400 `CONTEXT_PROJECT_REQUIRED` for a blank project on `rule_ingest` and `rule_edit`, as it already did for `graph_query`.
**Residual:** the review's preferred fix (project-qualified MERGE keys, or a post-write verification query inside n8n's transaction) is not implemented. The guard still analyses statement text; an unkeyed Atom chained by relationship to a keyed Rule remains allowed.

### CR-05: Default `local` profile gives Neo4j admin credentials to any editor
**Status:** skipped: by design (D-07), see Skipped Issues.

### WR-01: No login throttling
**Status:** fixed: requires human verification
**Files modified:** `data-service/auth.py`, `data-service/auth_routes.py`, `ui-v2/nginx.conf`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 34f76be
**Applied fix:** In-process per-key failure counters with exponential backoff under a lock (per username, per client address, and per user for `/auth/password`), checked before the scrypt derivation, returning 429 with `Retry-After`; a success clears the user key. Concurrent scrypt derivations are capped by a semaphore (`DG_SCRYPT_CONCURRENCY`, default 4). nginx rate-limits `login`, `password` and `accept-invite` per address through a `map`-keyed `limit_req` zone on the single existing `/data-service/` location (a second proxy location would break the exact proxied-location boundary test).
**Note:** counters are per process and reset on restart. A username lockout can be triggered by someone who only knows the username (accepted trade-off; the cap is 5 minutes).

### WR-02: `claim-untagged` and ingest `postProcess` re-tag every project-less node
**Status:** fixed: requires human verification (partial)
**Files modified:** `data-service/app.py`, `data-service/tests/test_graph_routes.py`, `data-service/tests/test_review_fix_1205.py`, `n8n/workflows/rules-to-metagraph.json`, `spec/SECURITY-BOUNDARY.md`
**Commit:** b5d9b13
**Applied fix:** `claim-untagged` never claims nodes of the shared hub graph `SpecGraph` (bound parameter). The three `postProcess` statements in the ingest workflow now only touch nodes whose `project` is NULL or already the ingesting project, so they no longer re-tag another project's node. The spec's carve-out paragraph is updated. Live-published (see Verification).
**Residual:** a globally untagged node outside `SpecGraph` can still be claimed by the next ingest or claim call, because n8n cannot tell this ingest's nodes from legacy untagged ones without a per-run marker. The live graph held zero untagged nodes on 2026-09-29. Admin-only `claim-untagged` and removing the UI's post-ingest call were not done (would change the documented editor carve-out).

### WR-03: Connector credential store had no lock and non-atomic writes
**Status:** fixed
**Files modified:** `data-service/connectors.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 6b72526
**Applied fix:** A module lock around every read-modify-write (mint, revoke, heartbeat), atomic writes (temp file, `os.chmod 0o600`, `os.replace`, cleanup in `finally`), and a corrupt or empty store now raises `CredentialStoreError` instead of returning `[]`. Authentication and heartbeat treat an unreadable store as "authenticates nobody" and log it.

### WR-04: Editors could write any node property except `project` and `graph`
**Status:** fixed: requires human verification
**Files modified:** `data-service/app.py`, `data-service/tests/test_graph_routes.py`
**Commit:** 33c0865
**Applied fix:** A viewer property edit is refused for identity, structural and evidence keys (case-insensitive: `Rule_Id`, `Atom_Id`, `StateId`, `Run_Id`, `dgId`, `iri`, `SWRL`, `status`, `ValidStatus`, ...), for any `*Json` key and any key starting `evidence` or `shacl`, and the statement refuses nodes labelled `ValidationRun`, `ValidationEntity`, `Run`, `DesignState` or `IntegrationConfig`.
**Note:** this is a denylist, not the allowlist the review asked for, because the property table edits free-form display properties and I could not enumerate which ones the owner wants editable. Replace it with an allowlist if you want the stricter form.

### WR-05: Multi-user startup gate covered four secrets and never forced `Secure` cookies
**Status:** fixed: requires human verification (partial)
**Files modified:** `data-service/secrets_policy.py`, `tools/security/check_env_file.py`, `tools/security/tests/test_check_env_file.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** cde5eff
**Applied fix:** `multi-user` startup now logs a WARNING when `DG_COOKIE_SECURE` is not true. `check_env_file.py` parses inline comments and `export` like Compose (IN-03) and prints a non-fatal `DG_COOKIE_SECURE: warn` when `DG_DEPLOYMENT=multi-user` without it.
**Not done:** the override does not force `DG_COOKIE_SECURE=true` and startup does not refuse. The spec documents TLS as the operator's job; forcing `Secure` would silently break login for a plain-http deployment. The remaining container secrets (`N8N_PASSWORD`, `POSTGRES_PASSWORD`, `MINIO_ROOT_*`, `SPECKLE_SESSION_SECRET`) are still only covered by the owner-run checker and compose `:?`, since passing them to data-service just for validation would widen secret exposure.

### WR-06: Non-ASCII `X-DG-Service-Token` caused an unhandled 500
**Status:** fixed
**Files modified:** `data-service/auth.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 9b0a118
**Applied fix:** The service-token comparison is done on UTF-8 bytes. An HTTP test with a high-byte header asserts 401. (The same commit also corrects one CR-03 test string whose backslash had been lost when the test file was written.)

### WR-07: `POST /computgraph/context/pull` open to `viewer`
**Status:** fixed: requires human verification (partial)
**Files modified:** `data-service/route_policy.py`, `spec/SECURITY-BOUNDARY.md`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 1492453
**Applied fix:** Minimum role raised to `editor`; the policy row and the spec's machine-checked `route-policy` block were changed together (row count unchanged, drift tests pass).
**Not done:** binding the canvas bridge to a project (a per-project bridge token).

### WR-08: Speckle project ids not tenant-bound
**Status:** fixed: requires human verification (partial)
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 21d8628
**Applied fix:** `PUT /integration/speckle/project/{project}` returns 409 `SPECKLE_PROJECT_BOUND` if another DG project already uses that Speckle project id (the answer never names the other project). The deployment's own default `SPECKLE_PROJECT_ID` stays shareable, so the single-Speckle-project local setup keeps working.
**Not done:** an admin-managed mapping, and per-tenant Speckle credentials. Publish and delete still use the one server-wide write token.

### WR-09: Logout and membership loss left tenant data in the browser
**Status:** fixed: requires human verification
**Files modified:** `ui-v2/src/App.jsx`, `ui-v2/src/lib/auth.js`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 1735a73
**Applied fix:** `clearTenantBrowserData()` removes every `dgv2_*` key except the theme. It runs on sign-out or session expiry, on a sign-in as a different account than the browser's last owner (a new `dgv2_owner` key), and when membership loss makes the remembered project be forgotten. The screen layers are keyed on the signed-in identity, so their in-memory graph, run and Speckle-token state is discarded on sign-out or account change. The UI build passes; there is no browser test framework, so the behaviour is covered by a node-run test of the clear function and a static wiring test. Worth a manual sign-out / sign-in-as-other-user pass.

### WR-10: `actor` on supersede and accept-overlap was client-supplied
**Status:** fixed: requires human verification
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** a64a9f5
**Applied fix:** Both routes record the authenticated principal (`username`, `connector:<id>` or `service`); a body `actor` is accepted for wire compatibility and ignored.

### WR-11: Ingest path guard used a string-prefix check
**Status:** fixed
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 71da284
**Applied fix:** `validate_ingest_path` uses `Path.is_relative_to` (a sibling like `/mnt/repo2` is now refused), and each ingested file must resolve inside the repository root, so a symlink cannot lead a read outside it. The `/mnt/repo` mount is unchanged, as instructed.

### WR-12: Internal exception text returned to clients
**Status:** fixed
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** d7e05dd
**Applied fix:** New `_internal_failure()` logs the exception under a 12-character correlation id and returns a generic message that carries only the id. Applied to the seven bare `except Exception` handlers that echoed `str(exc)` (computgraph publish, validate, consult, generate-inputs, accept-candidate, validation publish and delete). Messages of user-facing exception classes (the `ValueError` branches and `SpeckleValidationError`, whose text is written by this code base and contains no exception payload) are unchanged.

### WR-13: Scope validator rejected legitimate queries
**Status:** fixed (with CR-03)
**Commit:** 1f57a24
**Applied fix:** See CR-03. `count(r)`, `toLower(id)` and `timestamp()` are function-call parentheses and are no longer read as node patterns; the two verified queries from the review now pass.

### WR-14: Malformed bootstrap username stopped the service in `local`
**Status:** fixed (partial)
**Files modified:** `data-service/auth.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 4c651a2
**Applied fix:** An invalid bootstrap username now behaves like a weak password: a WARNING and return `invalid-username` in `local`, `RuntimeError` in `multi-user`, never a raw `ValueError` out of the lifespan.
**Not done:** making `DG_BOOTSTRAP_ADMIN_USER`/`PASSWORD` optional in compose. They are required interpolations by D-10 and `test_compose_boundary.py` asserts it, so I left it.

### WR-15: An invite was burned by the first account creation
**Status:** fixed: requires human verification
**Files modified:** `data-service/auth.py`, `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 9de0e65
**Applied fix:** New `auth.peek_invite()`. If the invite's username already has an account, the code is not consumed: the caller must supply that account's own password (same throttling as login), and only then is the membership added and a session issued. A wrong password returns `INVITE_INVALID` with a hint that the account exists, and the invite stays usable. The existing test that an unrelated password never touches the account passes unchanged; the account's password hash is never modified.

### WR-16: nginx set no security headers
**Status:** fixed (partial)
**Files modified:** `ui-v2/nginx.conf`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 2c56279
**Applied fix:** `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy` and a CSP carrying only `frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'`, all `always`, at server level and repeated in `location /` (nginx does not inherit `add_header` into a location that sets its own). Confirmed live.
**Not done:** a script/style/connect CSP (needs a browser pass against the Speckle viewer), and the `127.0.0.1:8080` publish, which is by design under D-09.

### WR-17: C# publish clients hid the token failure and sent the token over plain HTTP
**Status:** fixed: requires human verification (partial)
**Files modified:** `DG/src/DG.Core/Data/DataServiceRequestAuth.cs`, `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`, `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs`, `DG/src/DG.Grasshopper/Validation/ComputgraphPublishClient.cs`, `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs`, `DG/src/DG.Grasshopper/Components/ComputgraphPublishComponent.cs`, `DG/tests/DG.Tests/DataServiceRequestAuthTests.cs`, `DG/tests/DG.Tests/ErrorMessageTemplateTests.cs`, `tools/de01/legs.py`, `tools/de01/run_de01_repeat.py`, `tools/de01/tests/test_de01_auth_headers.py`
**Commit:** 96cfe52
**Applied fix:** A malformed token now throws `PublishTokenMalformed` (must start with `dgc_`) instead of the "no platform token" message. New `IsInsecureRemoteTransport` and a runtime warning on VALIDATOR and COMPUTGRAPH PUBLISH when the data-service URL is plain http to a non-loopback host. The DE-01 harness (`data_service_auth_headers(base_url)`) drops the token and warns on stderr in that case.
**Note:** the components warn rather than refuse, because the stack terminates no TLS itself and a LAN multi-user deployment over http would otherwise be unable to publish. Say so if you want a hard refusal.

### WR-18: Rotation script reported success on an unreadable settings file
**Status:** fixed
**Files modified:** `data-service/rotate_llm_master_secret.py`, `data-service/tests/test_rotate_llm_master_secret.py`
**Commit:** dbf0091
**Applied fix:** A settings file that exists but is malformed, empty, unreadable or not a JSON object now exits 4 with `settings-file-unreadable` and is left untouched; an absent file is still `nothing-to-rotate`. The docstring now says to stop data-service during rotation (the unlocked read-modify-write can race a live `PUT /llm/settings`).

### WR-19: `GET /llm/settings` open to any signed-in user
**Status:** fixed: requires human verification
**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** fe2a29f
**Applied fix:** Non-admin, non-service callers get `provider`, `model` and `apiKeyConfigured`; the masked key preview is blank and `baseUrl` is null. The route policy row is unchanged (still session), so no spec change was needed.

### WR-20: Auth JSON stores were fail-soft on read and hazardous on write
**Status:** fixed
**Files modified:** `data-service/auth.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 2f625fb
**Applied fix:** `_load` raises `AuthStoreError` for a present-but-corrupt store (missing file or missing key is still empty), so the next `_save` can no longer overwrite it and drop every account. `_save` sets owner-only permissions and always removes its temp file. `create_session` prunes expired and revoked sessions of every user. **Operational note:** a corrupt auth store now stops requests (and startup) with a 500 or a raised error until the file is repaired or restored, instead of quietly starting from empty.

### WR-21: n8n container hardening weaker than the comments claim
**Status:** fixed: requires human verification (partial)
**Files modified:** the five files in `n8n/workflows/*.json`, `docker-compose.yml`, `data-service/tests/test_review_fix_1205.py`
**Commit:** 382a865
**Applied fix:** The `Verify Relay Token` node in all five workflows compares the token in constant time (pure JS, no `require`), checked by a node harness against the exact node code (correct token accepted; longer, shorter, wrong, absent and blank-expected all rejected). The n8n image is pinned to `n8nio/n8n:2.4.8`. Live-published and confirmed (see Verification). I created a local alias with `docker tag n8nio/n8n:latest n8nio/n8n:2.4.8`; on another machine compose will pull that tag.
**Not done:** image digests (and the `speckle/*:latest` images) are not pinned; the dead `N8N_BASIC_AUTH_*` variables are kept (required interpolations by D-10, asserted by `test_compose_boundary.py`); `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` is unchanged because the workflows read `$env.DG_SERVICE_TOKEN` and `$env.NEO4J_PASSWORD`; moving the Neo4j password into an n8n credential is not done.

## Skipped Issues

### CR-05: Default `local` profile gives the Neo4j admin credentials to any editor

**File:** `data-service/app.py:1571` (`connector_heartbeat`)
**Reason:** by design (D-07): the Neo4j bundle stays in the heartbeat in the `local` profile, and "local is the default". I checked the gate against `auth.deployment_profile()` as instructed: the heartbeat calls `auth.deployment_profile()` (the resolver) and does not read the raw environment variable, so it agrees with it. An unset `DG_DEPLOYMENT` means `local` by the documented default, and an unrecognised value makes the resolver raise, which also stops startup (the lifespan calls it first), so nothing silently falls through to `local`. No code change.
**Original issue:** the heartbeat returns the admin Neo4j URI, user and password to any editor-minted connector token unless the profile is exactly `multi-user`, and invites and second users work in `local`.
**Follow-up for the owner (not a locked decision):** the review's other points (limit bundle issuance to admin-minted credentials, or warn or forbid second users in `local`) remain open owner decisions.

---

_Fixed: 2026-09-29T21:35:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
