---
phase: 1205-security-and-tenancy-release-gate
fixed_at: 2026-09-30T06:30:00Z
review_path: .planning/phases/1205-security-and-tenancy-release-gate/1205-REVIEW.md
iteration: 3
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 1205: Code Review Fix Report (iteration 3)

**Fixed at:** 2026-09-30T06:30:00Z
**Source review:** `.planning/phases/1205-security-and-tenancy-release-gate/1205-REVIEW.md` (iteration-2 re-review)
**Iteration:** 3 (final pass of the auto loop)

**Summary:**
- Findings in scope: 5 (CR-03, CR-04, WR-22, WR-23, WR-24)
- Fixed: 5
- Skipped: 0
- Info findings IN-01 to IN-04 are out of scope (`critical_warning`) and unchanged.

The in-container suite is back to exactly the known baseline: 12 failed, 3272 passed, 3 skipped. The 12 failures are the ten in `test_cq3_attribute_of.py`, `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields` and `test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`, all environmental. The run before the final rebuild showed one extra, transient failure (`test_recognition_eval.py::...a0_uses_the_as_shipped_grammar_citing_fixture`), which passes on its own and on the rerun.

## Fixed Issues

### CR-03: The project-scope proof for LLM-written graph queries had verified bypasses

**Files modified:** `data-service/cypher_allowlist.py` (new), `data-service/dg_context.py`, `data-service/tests/test_cypher_allowlist.py` (new), `data-service/tests/test_cypher_project_scope.py`, `data-service/tests/test_dg_context.py`, `data-service/tests/test_review_fix_1205.py`, `data-service/tests/test_n8n_workflow_boundary.py`, `n8n/workflows/graph-query-mcp.json`, `spec/SECURITY-BOUNDARY.md`
**Commits:** `bd97ffb` (shared with CR-04), `8fd1509` (prompt follow-up)
**Status:** fixed: requires human verification (security logic; a grammar, not a patch)
**Applied fix:** I did not add cases to the blocklist. `check_query_project_scope` now delegates to a lexer plus a small recursive grammar in `cypher_allowlist.py` that rejects everything it does not positively recognise.

- **Lexer.** Only ASCII identifiers, standard punctuation and string contents are accepted. Backticks, `//` and `/* */` comments, any non-ASCII character outside a string, control characters, unterminated strings and malformed numbers or parameters are violations (`unsupported_syntax`). Strings follow Neo4j's own backslash-escape rules, so the guard and the server agree where a string ends.
- **Read grammar.** Allowed clauses are `MATCH`, `OPTIONAL MATCH`, `WHERE`, `RETURN` (`DISTINCT`, `AS`, `*`), `ORDER BY`, `SKIP` and `LIMIT`, plus a fixed function list (`count`, `collect`, `sum`, `min`, `max`, `avg`, `size`, `toLower`, `toUpper`, `coalesce`, the `to*` converters, `head`, `last`, `labels`, `type`, `keys`, `id` and a few string and math helpers). WR-13's `count(r)` still passes.
  - Anything else is a violation: `WITH`, `UNWIND`, `CALL`, `UNION`, `FOREACH`, `LOAD`, `USE`, `YIELD` and the write verbs (`forbidden_clause`), `EXISTS {}`, `COUNT {}` and `COLLECT {}` blocks, list and pattern comprehensions (`|`), path variables, variable-length relationships (`*`), namespaced calls such as `apoc.*` and `db.*`, and unlisted functions (`unsupported_function`).
  - Every node pattern must bind a variable and be declared with the exact entry `project: $project` (`project: 'x'` is `project_literal`, an anonymous node is `anonymous_node_pattern`, an unscoped variable is `missing_project_scope`).
  - Later mentions of a declared variable are bare `(v)`. Shared-vocabulary labels are no longer exempt on the read side.
  - A query that never references `$project` is rejected.
- **Prompt.** The graph-query prompt in `n8n/workflows/graph-query-mcp.json` now states the allowlist, including how to exclude by relationship without an anonymous node. The retry-with-feedback loop is unchanged: each violation code and message is fed back to the model (tested).
- **Live n8n.** Both changed workflows were re-imported with their live ids preserved, published with `n8n publish:workflow`, and n8n restarted. Confirmed by node names only: `active` true, `activeVersionId == versionId`, `Verify Relay Token` present, prompt allowlist present. The two workflows are the live ids `a1b2c3d4-...` (rules) and `b2c3d4e5-...` (graph query), the only active copies. The graph-query workflow was published twice (the second time for the `USE` wording); the rules workflow once.
- **Tests.** Both bypasses from the review (WITH re-bind, Unicode identifier) are rejected, along with about 40 further constructs. About 25 legitimate queries are accepted.

### CR-04: Rule-ingest ownership guards were bypassable and covered only Rule/Atom keys

**Files modified:** `data-service/cypher_allowlist.py`, `data-service/dg_context.py`, `llm/cypher_catalog.json`, `cypher_template.txt`, `n8n/workflows/rules-to-metagraph.json`, `data-service/tests/test_cypher_allowlist.py`, `data-service/tests/test_cypher_project_scope.py`, `data-service/tests/test_dg_context.py`, `data-service/tests/test_review_fix_1205.py`, `spec/SECURITY-BOUNDARY.md`
**Commit:** `bd97ffb`
**Status:** fixed: requires human verification (security logic; changes the shape of ingested data, see Deviations)
**Applied fix:** `rule_ingest` and `rule_edit` Cypher now goes through the same lexer and a write grammar (`check_write_allowlist`, wired into `validate_cypher` in place of `check_foreign_project_literals`, which was removed):

- **Clauses.** Only `MERGE`, `MATCH` (no `WHERE`) and `SET`. `WITH`, `UNWIND`, `CALL`, `FOREACH`, `LOAD`, `CREATE`, `DELETE`, `DETACH`, `REMOVE`, `ON CREATE`/`ON MATCH` and everything else are violations.
- **Nodes.** Each declared node has a variable, exactly one label from `Rule`, `Atom`, `Var`, `Literal`, `Builtin`, `Class`, `DatatypeProperty`, `ObjectProperty`, a complete non-empty single string-literal identity key (`Rule_Id`, `Atom_Id`, `name`, `lex`, `iri`) and `project: $project` in the MERGE map.
  - No concatenation, functions or parameters in keys.
  - Unlabeled patterns are rejected. A bare `(v)` is allowed only for a variable bound earlier in the statement.
  - A variable may be bound once (no re-binding).
- **`SET`.** Only `var.prop = <literal>` on a bound variable. `project` and `graph` (case-insensitive) are protected. `SET n += {}`, `SET n = {}`, `SET n:Label`, dynamic `[]` access and parameter values are violations.
- **Relationships.** Only `HAS_BODY`, `HAS_HEAD`, `REFERS_TO` and `ARG`, without a variable, without `*`, with literal properties, between bound nodes.
- **Data shape.** To make the model-facing examples conform, the six `llm/cypher_catalog.json` shapes (template and worked example) and `cypher_template.txt` were rewritten: `project: $project, graph: '<graph>'` go in the MERGE map, `SET` no longer writes them, comments and backticks are gone (Neo4j 5.26 accepts `{order: 1}` and `{pos: 1}` unescaped, checked with `EXPLAIN`). The ingest prompt in `rules-to-metagraph.json` states the allowlist and no longer prints the project name as a literal. The `Execute LLM Cypher` node now sends `parameters: {project}` with the model's statement (before, `$project` would not have been bound).
- **Live n8n.** Re-imported with the live id, published and n8n restarted (see CR-03).
- **Verified against a real Neo4j.** All six migrated worked examples parse with `EXPLAIN`. The `max_limit` worked example was executed with `$project = 'zz-allowlist-e2e'`: 13 nodes were created, each tagged with `project` and `graph` (7 labels), 4 `HAS_BODY`/`HAS_HEAD` edges, and then removed (0 left).
- **Kept as defence in depth.** `find_cross_project_key_collisions` still runs after a valid ingest, and the ingest `postProcess` tagging is unchanged.

**Reference-example corpus results** (requested in the guidance):

| Corpus | Raw (as written) | After mechanical migration |
|---|---|---|
| `training/updated_cypher_reference_examples_v3.cypher` (3 examples) | 0 accepted, 3 rejected | 3 accepted |
| `training/updated_cypher_reference_examples_v4.cypher` (4 examples) | 0 accepted, 4 rejected | 4 accepted |
| Total training examples | **0 / 7 accepted** | **7 / 7 accepted** |
| Old `llm/cypher_catalog.json` (6 shapes, template + worked example) | 0 / 12 accepted | the rewritten catalog is accepted 12 / 12 |
| Recorded model output, `fixtures/llm_repeatability/cassettes` (50 files, 40 untruncated) | 0 / 40 accepted | 37 / 40 accepted |

Every raw example is rejected only for constructs the guard deliberately disallows: comments, backticks, a literal `project`, `SET x.project/x.graph`, and Literal/OntoGraph merges without `project`. The "migration" (drop comments and backticks, use `$project`, move `project`/`graph` into the MERGE map) is a test helper in `test_cypher_allowlist.py`. It is not shipped code, and the reference example files themselves were left unchanged. Of the 3 cassette outputs still rejected after migration, two write a `Parameter` node (a Computgraph label outside the ingest set, a correct rejection) and one is a merge shape the test helper does not rewrite.

### WR-22: The nginx login rate limit never applied

**Files modified:** `ui-v2/nginx.conf`, `data-service/tests/test_static_proxy_boundary.py`, `data-service/tests/test_review_fix_1205.py`
**Commits:** `1bf97b0`, `d63bd06`
**Applied fix:** I did not key the map on `$request_uri` as suggested, because the raw request URI can be spelled around the regex (`%6Cogin`, `//`). The limit moved into a dedicated regex location, `location ~ ^/data-service/auth/(login|password|accept-invite)/?$`, which nginx matches against the decoded, slash-merged path. It carries `limit_req zone=dg_auth burst=10 nodelay`, `limit_req_status 429` and the same proxy settings. The `map` is gone and the zone is keyed on `$binary_remote_addr`. The generic `/data-service/` location is unlimited. The static proxy-boundary test allows the extra proxy location.
**Verified:**
- A throwaway `nginx:alpine` container on this exact config with a stub upstream: 30 rapid POSTs to `login`, `password`, `accept-invite`, `%6Cogin` and `login/` each returned 11 passes and 19 `429`. The `GET /auth/me` control returned no 429.
- Live, after `docker compose build --no-cache design-grammars` and `docker compose up -d --no-deps design-grammars`: 30 POSTs to `http://localhost:8080/data-service/auth/accept-invite` returned 11 × 422 and 19 × 429.

### WR-23: IP-keyed failure limits became one global bucket behind a TLS terminator or NAT

**Files modified:** `data-service/auth.py`, `data-service/auth_routes.py`, `data-service/app.py`, `ui-v2/entrypoint.sh`, `ui-v2/Dockerfile`, `ui-v2/nginx.conf`, `docker-compose.yml`, `.env.example`, `data-service/tests/test_review_fix_1205.py`, `spec/SECURITY-BOUNDARY.md`
**Commit:** `8b38fd6`
**Status:** fixed: requires human verification (behaviour depends on the operator's proxy setup)
**Applied fix:** The per-username counter is the primary throttle. The per-address counter (login and the existing-account invite path) now runs only when `DG_TRUSTED_PROXIES` is set (default limit 30), or when `DG_THROTTLE_LIMIT_IP` is set (integer, 0 disables). The default with nothing configured is off. The UI container's `entrypoint.sh` writes `set_real_ip_from ...; real_ip_header X-Forwarded-For; real_ip_recursive on;` into an include from `DG_TRUSTED_PROXIES`, so the header is trusted only from those addresses. Entries that are not IP addresses or CIDRs stop the container, and an empty include is the default. Compose passes `DG_TRUSTED_PROXIES` to both services and `.env.example` documents it. `spec/SECURITY-BOUNDARY.md` §8 replaces the stale "login rate limiting not implemented" bullet with the layered behaviour and its residuals.
**Verified in the built image:** the default include is empty and a forged `X-Forwarded-For` is ignored (data-service saw the peer address). With the caller's subnet trusted, `X-Real-IP` became the forwarded address. A malicious entry (`10.0.0.1;evil`) refuses to start. Tests cover the limit resolution, no per-address lock by default, and the lock when configured.

### WR-24: An invite for an existing account could change or downgrade a membership

**Files modified:** `data-service/app.py`, `data-service/tests/test_review_fix_1205.py`
**Commit:** `797e183`
**Applied fix:** `_accept_invite_for_existing_account` now adds a missing membership or raises a lower role to the invite's role. It never lowers or replaces a role the account already holds (the "never lower" semantic). The check runs under `auth._STORE_LOCK`. `accept_invite` runs `validate_password_policy` only on the new-account branch, after the existing-account branch has been ruled out, so a legacy account whose current password predates the policy proves ownership with that password. For a new account the policy is still checked before the code is consumed. Tests cover a promoted owner keeping the role after a stale viewer invite, an upgrade, and the policy applying to new accounts only.

## Deviations from the orchestrator guidance (please review)

1. **OntoGraph labels are MERGEd, not MATCH-only.** The guidance said to allow Class, DatatypeProperty and ObjectProperty as MATCH-only references. Every reference example creates Class, DatatypeProperty and a per-rule violation DatatypeProperty with MERGE, and Builtin nodes carry `project` as well, so MATCH-only would break rule ingestion. I allow MERGE on those labels only with a literal `iri` and `project: $project`, so a merge can never touch another project's node. This makes `Class`, `DatatypeProperty`, `ObjectProperty`, `Builtin` and `Literal` nodes per project from now on (previously keyed on `iri` or `lex`+`datatype` alone and re-tagged on every ingest).
2. **`CREATE` is rejected in the write path.** The guidance listed it as allowed. The template and the existing CTXA-04 verb policy say "MERGE and SET only", and a non-idempotent `CREATE` is not needed, so it is a violation.
3. **`WITH` is rejected in the write path.** The guidance allowed it if needed to chain, and it is not needed: the n8n Prepare node already chains the clauses into one statement, and Neo4j accepts `MERGE ... SET ... MERGE` without it. `;` between clauses is treated as whitespace, as n8n strips it.
4. **Data shape change.** New ingests write `graph` and `project` in the MERGE key. Nodes ingested before this change carry `graph` too (the pipeline always set it), so they match; a legacy node lacking `graph` would be duplicated until the `postProcess` tagging step runs. Recorded in `spec/SECURITY-BOUNDARY.md` §5.
5. **Two commits share CR-03 and CR-04** (`bd97ffb`) because the lexer and both profiles are one module and one design. Per-finding follow-ups are separate.

## Verification

- Host: `python -m pytest` on the touched files, all green (`test_cypher_allowlist.py` 156, `test_cypher_project_scope.py`, `test_review_fix_1205.py`, `test_n8n_workflow_boundary.py`, `test_static_proxy_boundary.py`, `test_compose_boundary.py`, `test_security_boundary_spec.py`, `test_route_inventory.py`, `test_mcp_project_scope.py`, `test_cross_project_matrix.py`). The four `test_dg_context.py` endpoint tests fail on the host because the `neo4j` hostname resolves only inside compose (environmental, known).
- Rebuilt: `docker compose build data-service && docker compose up -d --no-deps data-service`, then `docker exec data-service pytest -q -p no:cacheprovider --ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`: **12 failed, 3272 passed, 3 skipped**, exactly the known environmental set.
- The route policy table was not changed, so `route_policy.py`, the SECURITY-BOUNDARY route block and `test_policy_table_size` are untouched.
- `npm --prefix ui-v2 run build`: not run. `ui-v2/src` was not touched; the image was rebuilt with `--no-cache`, which runs the build.
- Docker Desktop was not running at the start; I started it and brought up neo4j (and, on Docker's restart policy, the rest of the stack). Nothing was left behind besides two harmless workflow JSON copies in n8n's `/tmp` that its user cannot delete.

## Residual risks

- The grammar is a subset. Legitimate but unusual read queries (list comprehensions, `EXISTS {}`, `ALL()/ANY()`, path functions) are now refused and the model has to rewrite them. That is deliberate.
- `find_foreign_project_entities` on `/mcp` results still exempts shared-vocabulary labels (accepted residual, documented).
- IN-01 to IN-04 are unchanged.

---

_Fixed: 2026-09-30T06:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
