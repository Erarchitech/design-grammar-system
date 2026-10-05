---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 05
subsystem: data-service-auth
tags: [delegated-token, company-scope, route-policy, security-boundary, csrf, revocation, tdd]
requires: []
provides:
  - "company.py: admin-assigned project to company map (auth-project-companies.json), PUT /projects/{project}/company"
  - "delegation.py: 15-minute dgd_ Bearer bound to user, project, company and parent session (auth-delegated-tokens.json, hash only)"
  - "Principal kind delegated / policy token PRINCIPAL_DELEGATED; routes POST and DELETE /auth/delegated-token"
  - "GET /graph/{project} and GET /rules/{project} reachable by a delegated token for its bound project"
  - "company on GET /projects rows and GET /auth/me memberships"
  - "Error codes DELEGATED_AUTH_FAILED, DELEGATED_EXPIRED, DELEGATED_SESSION_ENDED, DELEGATED_SCOPE_CHANGED"
affects: [1301-06, 1301-09, 1301-10, 1301-12, 1301-13]
tech-stack:
  added: []
  patterns:
    - "New JSON stores derive their directory from auth.MEMBERSHIPS_FILE.parent at call time, so redirected auth stores carry them along"
    - "Derived non-ambient credentials re-validate their parent (session hash, live membership, company) on every request and mark themselves revoked with a reason that selects the named error"
key-files:
  created:
    - data-service/company.py
    - data-service/delegation.py
    - data-service/tests/test_company_scope.py
    - data-service/tests/test_delegated_token.py
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-05-SUMMARY.md
  modified:
    - data-service/auth.py
    - data-service/auth_routes.py
    - data-service/route_policy.py
    - data-service/app.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_project_routes.py
    - data-service/tests/test_auth_tracer.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
key-decisions:
  - "PUT /projects/{project}/company carries no project source in the policy (admin-only, admin is owner everywhere): a path source would add no authorization and breaks the cross-project matrix invariant that every scoped row is member-authorizable"
  - "POST /auth/delegated-token is policy member/body/viewer (a superset-equivalent of the planned session row) so the matrix and member sweeps apply; the handler additionally requires a STORED membership, so an admin who is not a member is refused"
  - "Password change revokes ALL of the user's delegated tokens, including those of the session that is kept"
  - "A revoked row keeps a revoked_reason (session_ended, membership_removed, scope_changed, explicit) selecting the named error; rows are pruned one hour after expiry"
requirements-completed: []
requirements-partial: [DGCL-02, DGCL-05]  # server side only; client display, heartbeat and local erasure are later plans
duration: ~55 min
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 05: Company scope and delegated user token Summary

The backend now has a project to company attribute (D-20) and a short-lived, user-scoped delegated token for the local agent that dies with the user's session or membership (D-06, D-08, server side).

## What was built

Task 1 (commit `a5fce25`): `company.py` stores the admin-assigned map in `auth-project-companies.json` through `auth._load` / `auth._save` under `auth._STORE_LOCK` (imported, not duplicated; atomic temp plus `os.replace`, chmod 600). `PUT /projects/{project}/company` is admin-only (non-admin owner 403 `ADMIN_REQUIRED`, connector/service 403 `PRINCIPAL_NOT_PERMITTED`, empty/whitespace/over-120/control-character company 422 `COMPANY_INVALID`, bad project name 422 `PROJECT_NAME_INVALID`). `GET /projects` rows and `GET /auth/me` memberships carry `company` (string or null).

Task 2 (commit `1e2587b`): `delegation.py` issues `dgd_` + `secrets.token_urlsafe(32)` tokens (TTL `DELEGATED_TOKEN_TTL_SECONDS = 900`), stores only the SHA-256 hash plus the parent session hash, username, project and company. `auth.require_principal` resolves credentials as service header, then `dgd_` Bearer, then `dgc_` Bearer, then cookie; an invalid `dgd_` never falls back to a present cookie. The delegated principal (`kind="delegated"`, `is_admin` always False, `company` set) is authorized by bound-project equality plus the stored membership role, is exempt from `X-DG-CSRF` (the cookie session that mints it is not), and reaches only rows that list `delegated`. New helper `auth.authenticate_session_hash` applies the revoked/expiry/idle rules read-only, so delegated use never refreshes the parent idle timer.

Revocation, each case covered by a test: logout (all tokens of that session, not other sessions), password change (all tokens of the user), parent session expiry, idle timeout, user removed, membership removal (route and behind-the-back), company reassignment (route, behind-the-back, and it stays dead if the company is put back), own expiry (inclusive boundary at exactly 900 s), explicit `DELETE /auth/delegated-token`.

Spec: `spec/SECURITY-BOUNDARY.md` Section 3 precedence prose, new 3.5 "Delegated token", four error-code rows, storage note, Section 10 row and the route-policy fenced block (rows `PUT /projects/{project}/company|admin|-|-`, `DELETE /auth/delegated-token|delegated|-|-`, `POST /auth/delegated-token|member|body|viewer`, and `delegated+member` on the two read rows). `spec/API.md`: principal table, error list, endpoint table. Policy table size 84 to 87.

## TDD

RED observed for both tasks before implementation: `python -m pytest data-service/tests/test_company_scope.py -q -x` and `... test_delegated_token.py -q -x` stopped at collection with `ModuleNotFoundError: No module named 'company'` / `delegation`. GREEN afterwards: 18 company tests, 78 delegated-token tests (every behaviour bullet of the plan, both deployment profiles for the route cases). Each task is one commit (tests plus implementation), so there are no separate `test(...)` commits.

## Verification (host, repo Python 3.14.2; Docker not used)

- Task 1 verify: `python -m pytest data-service/tests/test_company_scope.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` -> 758 passed.
- Task 2 verify: `python -m pytest data-service/tests/test_delegated_token.py data-service/tests/test_auth_tracer.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py data-service/tests/test_cross_project_matrix.py -q` (plus `test_company_scope.py`) -> 1793 passed.
- Pre-change baseline of the four existing suites (route inventory, boundary spec, auth tracer, cross-project matrix): 1653 passed.
- Full suite `python -m pytest data-service/tests -q -p no:cacheprovider` -> 4508 passed, 35 skipped, 8 deselected, 7 failed, 25 errors (273 s). All 32 are environmental, none touches auth:
  - 25 errors + 4 failures in `test_cg_structure_checks.py`, `test_computgraph_consult.py`, `test_dg_context.py`: the `neo4j` hostname does not resolve from the host (known baseline, memory).
  - 2 failures in `recognition_eval/test_repeat_sweep.py`: `FileNotFoundError` for `.planning/phases/1204-.../llm-evidence/llm-repeatability-report.json` (planning tree archived/deleted in the working tree, pre-existing).
  - 1 failure `test_recognition_eval.py::TestArms::test_resolve_arm_artifacts_a0_...`: `git log` subprocess timed out after 15 s while the graphify background rebuild ran; passes in isolation and with both new test files ahead of it (58 passed, 1 skipped).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Admin-only route cannot carry a path project source**
- **Found during:** Task 1 (cross-project matrix went red after adding the row)
- **Issue:** the plan asked for policy "admin-only (path project source)", but `test_cross_project_matrix` asserts every scoped row lists `member` with a `min_role`.
- **Fix:** policy is `_p(_ADM)` (no source). Admin is owner of every project so the source added no authorization; the handler validates the path name itself. Spec block row is `admin|-|-`.
- **Files:** data-service/route_policy.py, spec/SECURITY-BOUNDARY.md. **Commit:** a5fce25

**2. [Rule 1 - Bug/expectation drift] Exact-shape assertions updated for the new `company` field**
- **Found during:** Task 1
- **Issue:** `test_project_routes.py` and `test_auth_tracer.py` compared `/projects` rows and `/auth/me` memberships by exact equality.
- **Fix:** expected values gain `"company": None` (assertions otherwise unchanged).
- **Files:** data-service/tests/test_project_routes.py, data-service/tests/test_auth_tracer.py. **Commit:** a5fce25

**3. [Plan interpretation] Mint route policy is `member/body/viewer`, not `session`**
- A `session` policy with a body project source would also be a scoped row without `member`, violating the same matrix invariant. `member/body/viewer` accepts exactly the same user principals; the handler adds the stored-membership requirement so an admin non-member gets 403. Delegated and connector Bearer callers get `PRINCIPAL_NOT_PERMITTED`.

**4. [Rule 2 - fail-closed additions]** Beyond the plan's exports: `revoke_for_user` (password change revokes every token of the user, including the kept session's), `revoke_for_project` (company reassignment), `revoke_token` (self-revoke), a fourth named code `DELEGATED_AUTH_FAILED` for unknown/malformed/explicitly revoked tokens, and live membership/company checks that also mark the row revoked so a later re-add or reverting the company cannot resurrect it.

## Overlap with pre-existing uncommitted work

`data-service/auth.py` already carried an uncommitted hunk from an earlier session (the Windows `os.replace` retry loop in `_save`, +14 lines). It is NOT part of this plan and was deliberately not committed: the index blob for auth.py was built as the working file minus that hunk, so commit `1e2587b` contains only this plan's auth.py changes and the retry-loop hunk is still an unstaged working-tree modification. Other pre-existing dirty files (`test_auth_store.py`, recognition_eval tests, `spec/SWRL-SUBSET.md`, etc.) were left untouched.

## Known Stubs

None. Delegated reach is deliberately two read routes (`/graph/{project}`, `/rules/{project}`); the LLM relay route (D-16) and agent tools that consume the token are later plans.

## Threat Flags

None beyond the plan's register. T-1301-05-01 (15-min TTL, hash-only, parent-bound), -02 (no admin elevation, bound project, admin routes exclude delegated), -03 (mint keeps cookie + CSRF, Bearer cannot mint), -04 (bound project + live membership + company equality), -06 (caplog test: raw token and its secret part never logged) are mitigated and tested. T-1301-05-05 (audit trail) accepted as planned.

## Self-Check: PASSED

- FOUND: data-service/company.py, data-service/delegation.py, data-service/tests/test_company_scope.py, data-service/tests/test_delegated_token.py
- FOUND commits: a5fce25 (task 1), 1e2587b (task 2)
