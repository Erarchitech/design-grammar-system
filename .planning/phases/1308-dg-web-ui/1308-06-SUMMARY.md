---
phase: 1308-dg-web-ui
plan: "06"
subsystem: auth
tags: [connector-session, dgk, fastapi, route-policy, security-boundary, pytest]

requires:
  - phase: 1308-dg-web-ui
    provides: "connector_session store and connector_access.is_authorized (plan 03)"
provides:
  - "auth.Principal.connector_id and a dgk_ branch in resolve_connector_principal (every _CON route row works unchanged)"
  - "POST /auth/connector-session (mint, 201, no-store) and DELETE /auth/connector-session (self-revoke, 204)"
  - "_neo4j_bundle_or_none helper shared by the heartbeat and the mint"
  - "tests/auth_fixtures.connector_token_for on dgk_ sessions of the shared test admin"
  - "SECURITY-BOUNDARY 3 / 3.2 / 3.4 / route-policy block, API.md and DEPLOYMENT.md updated in the same commits"
affects: [1308-07, 1308-08, 1308-09, 1308-13, 1308-24]

tech-stack:
  added: []
  patterns:
    - "Lazy import of connector_session inside the resolver (cycle-safe, like delegation)"
    - "Session-only mint route whose handler performs project, exemption and grant checks, because a blank project cannot be resolved by the policy layer"

key-files:
  created:
    - data-service/tests/test_connector_session_routes.py
  modified:
    - data-service/auth.py
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/auth_fixtures.py
    - data-service/tests/test_authorized_fixtures.py
    - data-service/tests/test_route_inventory.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - spec/DEPLOYMENT.md

key-decisions:
  - "Mint policy is _p(_SES) (flagged assumption of the plan): the handler checks membership, exemption and grant itself; DELETE is _p(_CON) with no project source, which test_route_inventory accepted unchanged"
  - "For a blank project an admin's eligible set is every project that has members (admin is exempt everywhere); a non-admin's is their own member projects filtered by is_authorized"
  - "The existing 403 PROJECT_REQUIRED row of spec 3.4 is kept and a second 422 row added for the connector mint, since the code is shared"
  - "dgc_ stays accepted by the resolver and by POST /connectors/{id}/credentials until plan 1308-13"

patterns-established:
  - "Revoke handler reads the Bearer itself and answers Response(204); the resolver already refused unknown or revoked tokens before the handler runs"

requirements-completed: []

coverage:
  - id: D1
    description: "dgk_ resolves to a connector Principal (username, bound_project, connector_id, session id); expired, revoked, ungranted and foreign-project cases answer the named errors on a _CON route"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_session_routes.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST/DELETE /auth/connector-session: role matrix, blank-project resolution, no-store, CSRF, Bearer classes refused, Neo4j bundle local only"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_session_routes.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Spec and route table stay in step: policy table 113, SECURITY-BOUNDARY machine-checked block, API and DEPLOYMENT rows"
    requirement: "WEBUI-10"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py, data-service/tests/test_security_boundary_spec.py"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 06: Connector sign-in session routes Summary

**`dgk_` connector sessions now authenticate on every connector route and can be minted (`POST /auth/connector-session`) and ended (`DELETE`) from the server, with the spec, API and deployment docs changed in the same commits and legacy `dgc_` tokens still working.**

## Accomplishments

- `resolve_connector_principal` sends a `dgk_` Bearer through `connector_session.authenticate` (lazy import) and returns a `connector` principal carrying `username`, `connector_id`, `company` and the session id; the legacy `dgc_` branch is unchanged. The 401 hint now points at `POST /auth/connector-session`.
- `POST /auth/connector-session` (`ConnectorSessionRequest`, handler `mint_connector_session`): 201 with `Cache-Control: no-store` and the exact answer keys; owner and admin exempt, editor/viewer need a grant (403 `CONNECTOR_ACCESS_REQUIRED`), non-member or admin on a memberless project 403 `PROJECT_FORBIDDEN`, unknown connector and `degram` 404; blank project picks the single eligible project, 422 `PROJECT_REQUIRED` listing only the caller's eligible names for several, 403 for none. The Neo4j bundle is returned only outside the multi-user profile via the extracted `_neo4j_bundle_or_none` (heartbeat behaviour unchanged).
- `DELETE /auth/connector-session` revokes the presented session (204); the same token then answers 401 `CONNECTOR_SESSION_ENDED`.
- `connector_token_for(project, *, username=None, connector_id="grasshopper")` issues a `dgk_` session of the shared test admin with no membership row; the 11 callers across the suite run on sessions unchanged.
- Spec: SECURITY-BOUNDARY 3 intro, 3.2 rewritten as «Connector sign-in session», 3.4 rows (CONNECTOR_SESSION_EXPIRED, CONNECTOR_SESSION_ENDED, CONNECTOR_ACCESS_REQUIRED, PROJECT_REQUIRED 422), two route-policy block rows; API.md principal table plus both routes; DEPLOYMENT.md `DG_CONNECTOR_SESSION_TTL_SECONDS`.

## Task Commits

1. Task 1 (resolver, fixture seam, spec 3.2): `783dbf5`
2. Task 2 (routes, policy rows, spec block, API, DEPLOYMENT): `758d92e`

## Verification (real output, run from the host)

- Task 1 verify command (plus test_route_inventory): 2529 passed.
- Task 2 verify command: 1056 passed (test_connector_session_routes, test_connectors, test_route_inventory, test_security_boundary_spec, test_deployment_profile).
- Wider run (cross_project_matrix, error_responses, graph_routes, degram_grants, delegated_token, connector_session, connector_access, designstate_capture, auth_tracer, member_roles, project_summary, company_scope): 1636 passed. test_connectors/test_designstate_capture/test_auth_tracer/test_auth_store/test_review_fix_1205: 360 passed, 1 skipped.
- Acceptance greps: `/auth/connector-session` in route_policy.py = 2; `auth/connector-session|` in SECURITY-BOUNDARY.md = 2; DEPLOYMENT.md entry found; `test_policy_table_size` asserts 113; `connector_id: str | None = None` and `connector_session.issue` found.
- Not run: the full data-service suite, any Docker or live check (not authorized in this plan).

## Deviations from Plan

### Auto-fixed Issues

None in behaviour. Notes:

- **[Process] Task 2 implementation was written before its tests.** The route tests were added immediately after the handlers rather than first, so there is no observed RED run for Task 2 (Task 1 had one: 13 failed, then green). The tests were then run against the finished code and pass; they assert 404/405-sensitive behaviour (status codes, headers, error codes) so they would fail without the routes.
- **[Spec] PROJECT_REQUIRED already existed** in 3.4 as a 403 policy code; the 422 connector-mint form is added as a second row rather than replacing it.
- The plan asked for the no-project-source `_CON` question to be recorded: `_p(_CON)` with no source needed no change in `test_route_inventory.py` beyond the size 113.
- `docker-compose.yml` does not pass `DG_CONNECTOR_SESSION_TTL_SECONDS` through (not in this plan's files); DEPLOYMENT.md says so. Passing it is a compose follow-up for the rollout plan.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat register (T-1308-06-01..07: each mitigation is asserted by a test; no new surface).

## Requirements

WEBUI-07 and WEBUI-10 are only partly delivered here (server resolver and routes; the add-in client, Web UI, `dgc_` retirement, status derivation and heartbeat/capture wiring belong to later plans), so neither is marked complete in REQUIREMENTS.md.

## Self-Check: PASSED

- FOUND: data-service/tests/test_connector_session_routes.py, data-service/app.py, data-service/auth.py, data-service/route_policy.py
- FOUND commits: 783dbf5, 758d92e
