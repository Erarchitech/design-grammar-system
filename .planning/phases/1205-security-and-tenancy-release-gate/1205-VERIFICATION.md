---
phase: 1205-security-and-tenancy-release-gate
verified: 2026-09-30T12:00:00Z
status: human_needed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Owner review of the iteration-3 security logic (data-service/cypher_allowlist.py, wired through dg_context.check_query_project_scope / check_write_allowlist)"
    expected: "Owner accepts the read/write Cypher grammar as the CR-03/CR-04 closure. The fix report itself marks both 'requires human verification (security logic)'. No fresh code-review pass ran after iteration 3; the latest REVIEW.md is the iteration-2 review."
    why_human: "Security logic added after the last independent review. The verifier probed about 25 adversarial queries and found no bypass (see Anti-patterns), but that is not a review."
    update_2026_09_30: "At the owner's request a final deep independent review ran (1205-REVIEW.md, commit 1907184). It found 2 Critical read-path bypasses (a STARTS/ENDS…WITH scope reset, and Neo4j 5 IS label syntax), both verified on a disposable Neo4j, plus 4 warnings. Iteration 4 (commits 4f21d60..1c367d1, report a993710) replaced the read expression handler with an operand/operator grammar, a single node-shape reader and an unclassified-paren audit. It now rejects pattern predicates, IS label syntax, backslash and doubled-quote escapes, and every ';' in the read profile. Orchestrator re-check: the differential probe against a fresh disposable two-tenant Neo4j 5.26 passed 17/17 with 0 foreign-data leaks; the full in-container suite is 3875 passed with only the 12 known environmental failures. No independent review has run on the iteration-4 rewrite; the owner decides whether this evidence is sufficient."
  - test: "Owner decision on the two accepted-by-design residuals: default local profile hands editors the Neo4j bundle (CR-05, D-07); server-wide Speckle read token goes to any user principal (D-12 residual)"
    expected: "Owner confirms both stay as documented for the external multi-user evaluation, or asks for narrowing."
    why_human: "Deliberate design trade-offs that the reviewer left as open owner choices."
  - test: "Owner-only secret steps still outstanding"
    expected: "Change the n8n owner-account password in the n8n UI; rotate the reused n8n password outside the repo; optionally do runbook step 11 (Speckle API tokens, old connector credentials). (The DG_TRUSTED_PROXIES part is DONE by the orchestrator on 2026-09-30: empty line added to .env and the checker's OPTIONAL_BLANK_KEYS fixed in 124b505; strict `check_env_file.py` exits 0.)"
    why_human: "Outside the repository, or values only the owner may type."
  - test: "Manual sign-out then sign-in-as-a-different-user pass in the browser (WR-09 client cleanup)"
    expected: "No graph, project, snapshot or draft state from user A is visible to user B."
    why_human: "Client cleanup is covered only by static tests; the review asked for a manual pass."
---

# Phase 1205: Security and Tenancy Release Gate Verification Report

**Phase Goal:** Establish server-side authorization and fail-closed project boundaries. Gate: unauthorized cross-project and direct-proxy access fail closed; secret handling is deployment-safe.
**Verified:** 2026-09-30
**Status:** human_needed
**Re-verification:** No (initial verification)

## Goal Achievement

No must-have failed. The status is `human_needed` rather than `passed` because security logic added in the last fix iteration has had no independent review, and a few owner-only steps remain (see the frontmatter).

### Observable Truths

Roadmap deliverables and gate, merged with the plan-level truths. All of the roadmap contract is covered.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Server-side user/tenant authorization (ALGN12-17, D-01..D-05, D-19) | VERIFIED | `data-service/app.py:161` `router = APIRouter(dependencies=[Depends(auth.require_principal)])`. `route_policy.py` holds the deny-by-default table. `auth.py` implements scrypt users, sessions, memberships and the service-token principal (`X-DG-Service-Token`, fails closed on blank). The GH clients call `DataServiceRequestAuth.TryApplyConnectorToken`. `ui-v2/src/lib/apiClient.js:75` uses `credentials: "include"`. The old localStorage accounts are deleted by `auth.js`. Live re-check: `GET :8000/validation/runs/x` returns 401 and `GET :8080/data-service/auth/me` returns 401. |
| 2 | Direct Neo4j/n8n proxy exposure removed or restricted (ALGN12-18, D-06/D-08/D-09) | VERIFIED | `ui-v2/nginx.conf:37-43` has `location ^~ /neo4j` and `/n8n` returning 404. There are no `executeCypher`, `tx/commit` or Neo4j credential references in `ui-v2/src`. Compose binds 7474/7687/8000/8001/5678/9000/9001/11435 to 127.0.0.1; only 8080 and 8090 are public. Live re-check: `/neo4j/` returns 404 and the `/n8n/webhook/...` path returns 404 through :8080. n8n workflows have zero `mcp_url` / `data_service_url` reads. All 5 carry a `Verify Relay Token` node. |
| 3 | Secret/default-credential hardening and rotation (ALGN12-19, D-10..D-13) | VERIFIED (with warnings) | `docker-compose.yml` requires every secret with `${VAR:?}`. `.env` and `.secrets` are untracked. `ui-v2/gen-config.sh` emits exactly two non-secret keys. `secrets_policy.py` holds the known-default list, and `spec/SECURITY-BOUNDARY.md` (342 lines) carries the rotation runbook. Plan 18 recorded live rotation of the secrets, and the old Neo4j and Postgres defaults are rejected. `test_config_js_no_secrets.py` passes. Warnings: the strict `.env` checker now exits 1 (see Anti-patterns) and owner-only residuals remain. |
| 4 | Unauthorized cross-project and direct-proxy tests fail closed (ALGN12-20, D-14/D-15/D-16) | VERIFIED | The verifier ran the gate suites on the host: `test_route_inventory`, `test_security_boundary_spec`, `test_cross_project_matrix`, `test_static_proxy_boundary`, `test_compose_boundary`, `test_config_js_no_secrets`, `test_cypher_allowlist`, `test_n8n_workflow_boundary`, `test_mcp_project_scope` and `test_review_fix_1205` gave **1965 passed, 1 skipped**. `tools/security/check_live_boundary.py` (local and multi-user) exited 0 (evidence JSON in `live-evidence/`). |
| 5 | Deployment boundary for connector heartbeat and privileged graph access (D-07) | VERIFIED | `app.py:1604` builds the Neo4j bundle only when the profile is not `multi-user`. `test_deployment_profile.py:86,100` pins both branches. Live multi-user run: the heartbeat returned `neo4j: null`, and 7687, 7474 and 5678 were refused. |
| 6 | Normative `spec/SECURITY-BOUNDARY.md` with machine-checked allowlist; CLAUDE.md pointer (D-17) | VERIFIED | File exists and is parsed by `test_security_boundary_spec.py` (passes). `CLAUDE.md:218` points to it. |
| 7 | GATE12-05: judged in multi-user, does not block local single-user work (D-18/D-19) | VERIFIED | Multi-user gate suites passed 1657/1657 in-container. Owner verdict "gate-pass" is recorded verbatim in `live-evidence/multi-user-gate-summary.md`. The local profile was restored, and the live local checker exited 0. |
| 8 | LLM-written graph queries are provably project-scoped (`/mcp neo4j_query`, CR-03) | VERIFIED | `dg_context.check_query_project_scope` delegates to `cypher_allowlist.check_read_allowlist`. It is wired at `app.py:3146`. Verifier probes: the WITH re-bind, the Unicode identifier, the unscoped MATCH, the second unscoped MATCH, an anonymous relationship end, `CALL`, `UNION`, variable-length paths, comments, `;`-chained MATCH and duplicate `project` keys were all rejected. Properly scoped queries were accepted. |
| 9 | Rule-ingest Cypher can only touch the relayed project (CR-04) | VERIFIED | `check_write_allowlist` is wired through `validate_cypher` (`dg_context.py:1203`). n8n calls `/context/generate-cypher`, which validates each attempt. Verifier probes: `MATCH (n) DETACH DELETE n`, key concatenation, `SET r.project=...`, an unlabeled MERGE, a MATCH without project and a parameter key were all rejected. A well-formed MERGE with `project: $project` was accepted. |

**Score:** 9/9 truths verified. None is behavior-unverified: the state and invariant claims are exercised by tests, and the boundary claims by the live checker.

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `data-service/auth.py`, `auth_routes.py`, `route_policy.py`, `secrets_policy.py`, `cypher_allowlist.py` | VERIFIED | Substantive; wired through the router dependency, the lifespan hook, `dg_context` and `app.py`. |
| `spec/SECURITY-BOUNDARY.md` | VERIFIED | Machine-checked by test. |
| `.env.example`, `tools/security/check_env_file.py`, `check_live_boundary.py`, `data-service/rotate_llm_master_secret.py` | VERIFIED | Present and exercised; see the checker warning below. |
| `docker-compose.yml`, `docker-compose.multi-user.yml`, `ui-v2/nginx.conf`, `ui-v2/gen-config.sh` | VERIFIED | Content checked above. |
| `n8n/workflows/*.json` (5) | VERIFIED | Relay-token node present; no caller-supplied URLs. Published live per evidence. |
| `DG/src/DG.Core/Data/DataServiceRequestAuth.cs` and the GH publish clients | VERIFIED | Wired at `ComputgraphPublishClient.cs:42` and `ValidationPublishClient.cs:51`. |

### Key Link Verification

| From | To | Status | Details |
|------|----|--------|---------|
| Every `@router` route | `auth.require_principal` | WIRED | Router-level dependency; `test_route_inventory` fails on any unclassified route. |
| `ui-v2` fetches | data-service `/auth/*` | WIRED | `apiClient.js` sends the session cookie. |
| n8n `Generate Validated Cypher` | `/context/generate-cypher` | WIRED | Validation runs before n8n executes the statement. |
| `/mcp neo4j_query` | scope guard plus result withholding | WIRED | `app.py:3146` and `:3162`. |
| Heartbeat | deployment profile | WIRED | `app.py:1604`. |
| GH publish clients | `dgc_` Bearer token | WIRED | See artifacts. |

### Requirements Coverage

Every requirement ID from the plan frontmatter appears in REQUIREMENTS.md, and none is orphaned.

| Requirement | Source plans | Status | Evidence |
|-------------|--------------|--------|----------|
| ALGN12-17 | 02, 03, 05, 06, 07, 08, 10, 11, 12, 13, 14, 16 | SATISFIED | Truths 1, 8 and 9. **REQUIREMENTS.md still shows it unchecked; recommend marking it complete.** |
| ALGN12-18 | 05, 09, 11, 12, 14, 15, 16, 18, 19 | SATISFIED | Truths 2 and 5. Already marked. |
| ALGN12-19 | 01, 04, 07, 09, 11, 15, 16, 18 | SATISFIED (owner residuals) | Truth 3. **REQUIREMENTS.md still shows it unchecked; recommend marking it complete.** The remaining items are owner-only or optional runbook steps, and are tracked as human items, not gaps. |
| ALGN12-20 | 04, 08, 10, 16, 17, 18, 19 | SATISFIED | Truth 4. Already marked. |
| GATE12-05 | 16, 17, 19 | SATISFIED | Truth 7. Already marked. |

### Behavioral Spot-Checks and Probe Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gate suites (host) | `pytest` on the 10 gate/boundary test files | 1965 passed, 1 skipped | PASS |
| Read allowlist rejects the review bypasses | `check_read_allowlist` on about 13 queries | The bypasses were rejected and the scoped queries accepted | PASS |
| Write allowlist rejects wipe, concat, protected SET, unlabeled MERGE | `check_write_allowlist` on 7 statements | As expected | PASS |
| Proxy removal, live | `curl` on `/neo4j/` and `/n8n/...` at :8080 | 404 and 404 | PASS |
| Auth enforced, live | `curl` on :8000 and `/auth/me` | 401 and 401 | PASS |
| Env checker | `python tools/security/check_env_file.py` | Exit 1: `DG_TRUSTED_PROXIES: missing` | WARNING |

No `probe-*.sh` scripts are declared for this phase. Bolt 7687 is open on 127.0.0.1 in the running local profile, which is the documented trusted-local boundary (D-07), so the check does not apply.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `tools/security/check_env_file.py` and the gitignored `.env` | WR-23 (iteration 3) added `DG_TRUSTED_PROXIES` to `.env.example`, but the owner's `.env` predates it. The checker treats an absent key as `missing` and exits 1. Compose defaults the value to empty, so the stack is unaffected. | WARNING | The orchestrator-reported `exit 0` on the strict checker no longer holds after the last code change. It is a one-line owner fix. |
| `DG.Tests` `DesignStateValidationFlowTests` (4 tests) | The E2E fixture sends no connector token, so it gets 401 from the auth-enforcing data-service. D-20 says existing suites keep working through authorized fixtures. | WARNING | The host E2E suite is not authorized; it needs a fixture token. It does not affect the boundary. |
| `tests/test_connectors.py::TestHeartbeatBundle` (2), `tests/test_designstate_capture.py` lifespan (3, full-run only) | Fail in multi-user only. The first two hard-code the local bundle. The lifespan tests likely leak a short `LLM_MASTER_SECRET` into the process environment. | WARNING | Test isolation and profile pinning. The gate suites are green in multi-user, so the boundary is unaffected. |
| data-service startup | Cold-start race: it exited with code 3 twice when Neo4j was not yet accepting Bolt connections. There is no healthcheck or restart policy. | WARNING | An operational hardening item, not a boundary defect. |
| Iteration-2 review IN-01..IN-04 | `/docs`, `/redoc` and `/openapi.json` are unauthenticated. The `$` pattern ends and the denylist `PROTECTED_NODE_KEYS_CI` remain. A corrupt auth store gives a bare 500. Failure counters check before they record. | INFO | Out of fix scope. Not gate-blocking. |
| Debt markers (TBD, FIXME, XXX) | Not scanned across the phase's changed files; only the security modules were spot-read. | INFO | No marker surfaced in the files read. |

### Human Verification Required

See the frontmatter `human_verification` list.

1. **Review the iteration-3 security logic.** Confirm the read/write Cypher grammar as the CR-03/CR-04 closure. No review followed the last fix pass.
2. **Decide on the accepted residuals.** These are the `local` profile Neo4j bundle for editors and the server-wide Speckle read token for user principals.
3. **Finish the owner-only secret steps.** Add `DG_TRUSTED_PROXIES=` to `.env`, change the n8n owner password, rotate the reused n8n password, and optionally do runbook step 11.
4. **Run the manual sign-out and sign-in-as-another-user pass** for the WR-09 client cleanup.

### Gaps Summary

There are no blocking gaps. All five requirement IDs are supported by code, tests and status-only live evidence. The deny-by-default dependency, the removal of the `/neo4j` and `/n8n` proxies, the non-secret browser config, the required-secret compose and the multi-user Bolt withholding were each confirmed independently, with host tests plus live probes that the verifier ran.

The phase ends in `human_needed` because of four things. The last security fix was not independently re-reviewed. Two design residuals are still open owner choices. A few secret steps only the owner can perform remain. The WR-09 client cleanup has only static test coverage.

The four warning-level test and operational follow-ups (E2E fixture token, multi-user test pinning, `.env` checker key, cold-start race) should be scheduled but do not gate the phase.

Decision for ALGN12-17 and ALGN12-19: both are satisfied by the evidence above, so REQUIREMENTS.md can mark them complete.

---

_Verified: 2026-09-30_
_Verifier: Claude (gsd-verifier)_
