---
phase: 1308-dg-web-ui
plan: "24"
subsystem: auth
tags: [connector-session, legacy-token-retirement, revocation, project-scope, dsav, security-boundary]
requires:
  - phase: 1308-dg-web-ui
    provides: "Plan 13 retired dgc_ authentication and moved connector routes onto dgk_ sessions"
provides:
  - "GET /connectors reports session-based status, last sign-in and live sign-in count within the caller's visible projects"
  - "Legacy dgc_ mint/auth/heartbeat helpers removed; credential store retained for cleanup only"
  - "Access-changing routes revoke affected connector sessions without ending still-authorized sessions"
  - "Live DSAV fixtures use account-backed connector sign-in instead of the retired credential endpoint"
affects: [1308-15, 1308-19, 1308-20, connector-status, connector-access]
tech-stack:
  added: []
  patterns:
    - "Compute registry status from connector_session.status_for with a visible-project filter"
    - "Revoke only newly unauthorized sessions after a role/grant change; retain valid replacement grants and owner/admin exemptions"
key-files:
  created: []
  modified:
    - data-service/connectors.py
    - data-service/app.py
    - data-service/auth_routes.py
    - data-service/tests/test_connectors.py
    - data-service/tests/test_cross_project_matrix.py
    - data-service/tests/test_connector_session_routes.py
    - data-service/tests/test_designstate_capture.py
    - data-service/tests/test_dsav_live_loop.py
    - data-service/tests/test_dsav_publish_leg.py
    - spec/API.md
    - spec/SECURITY-BOUNDARY.md
key-decisions:
  - "Invite acceptance preserves or raises an existing role per WR-24; it never demotes merely to satisfy contradictory plan prose. Existing-account invite creation can change a role and is covered by the revocation cascade."
  - "Deleting a previously revoked grant or a grant superseded by an active replacement does not revoke a still-authorized session; owner/admin exemptions are retained."
  - "Legacy credential storage remains available solely to the DELETE cleanup route and d49_store_cleanup.py."
patterns-established:
  - "Connector-session status is filtered to the caller's visible projects; admin sees all projects."
  - "Access-change cascades revoke stored session rows so their next request answers CONNECTOR_SESSION_ENDED, rather than relying only on a live authorization re-check."
requirements-completed: [WEBUI-07, WEBUI-10]
coverage:
  - id: D1
    description: "Registry overview uses project-filtered sign-in sessions for active/stale/never_connected status, last_connection and active_sessions; DeGram retains its seven-day grant rule."
    requirement: WEBUI-07
    verification:
      - kind: unit
        ref: "python -m pytest data-service/tests/test_connectors.py data-service/tests/test_degram_pairing.py data-service/tests/test_cross_project_matrix.py data-service/tests/test_connector_session.py -q"
        status: pass
    human_judgment: false
  - id: D2
    description: "Legacy credential mint, authentication and heartbeat helpers are absent while cleanup-store operations remain."
    requirement: WEBUI-07
    verification:
      - kind: unit
        ref: "python -m pytest data-service/tests/test_connectors.py data-service/tests/test_connector_session.py data-service/tests/test_connector_session_routes.py data-service/tests/test_designstate_capture.py data-service/tests/test_review_fix_1205.py data-service/tests/test_deployment_profile.py data-service/tests/test_route_inventory.py data-service/tests/test_d49_store_cleanup.py -q"
        status: pass
    human_judgment: false
  - id: D3
    description: "Password, membership, company, connector-grant and invite-route changes revoke affected dgk_ sessions, preserving still-authorized sessions."
    requirement: WEBUI-07
    verification:
      - kind: unit
        ref: "python -m pytest data-service/tests/test_connector_session_routes.py data-service/tests/test_connector_access.py data-service/tests/test_member_roles.py data-service/tests/test_project_routes.py data-service/tests/test_company_scope.py data-service/tests/test_auth_tracer.py data-service/tests/test_delegated_token.py data-service/tests/test_self_registration.py data-service/tests/test_deployment_profile.py data-service/tests/test_review_fix_1205.py data-service/tests/test_security_boundary_spec.py data-service/tests/test_route_inventory.py -q"
        status: pass
    human_judgment: false
  - id: D4
    description: "API and security-boundary documentation describe session-based overview, revocation and cleanup-only credential storage."
    requirement: WEBUI-10
    verification:
      - kind: unit
        ref: "data-service/tests/test_security_boundary_spec.py and test_route_inventory.py in the Task 3 suite"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live DSAV fixtures obtain and tear down dgk_ tokens through account sign-in, without calling the retired credentials route."
    requirement: WEBUI-07
    verification:
      - kind: integration
        ref: "python -m pytest data-service/tests/test_dsav_live_loop.py data-service/tests/test_dsav_publish_leg.py -q --collect-only -m 'integration and live' (collection only; seven tests)"
        status: unknown
    human_judgment: true
    rationale: "The fixtures collected but were not executed against a live stack; account credentials, Docker deployment and live DSAV behavior remain unverified."
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 24: Connector Session Status and Revocation Summary

**Registry status now reflects live account-backed sign-ins, legacy token helpers are gone, and access changes explicitly end affected connector sessions.**

## Accomplishments

- Task 1: `GET /connectors` derives each registry entry from `connector_session.status_for`, filtered by visible projects for members and unfiltered for admins. It returns `status`, `last_connection` (last sign-in) and `active_sessions` with no exposed credentials. DeGram's grant-based card remains unchanged.
- Task 2: Removed the legacy `dgc_` prefix and token mint/auth/heartbeat/status helpers. Kept the credential-store read/write/revoke operations for cleanup. The two live DSAV test fixtures now read `DSAV_USERNAME` and `DSAV_PASSWORD` from the environment, skip when absent, sign in through `/auth/login` and `/auth/connector-session`, and revoke the session in teardown. No password or token is written to evidence.
- Task 3: Password changes, member removal, project company reassignment, connector-access revocation, membership-role changes and the invite paths cascade revocation to stored `dgk_` sessions. Tests exercise the next request's 401 `CONNECTOR_SESSION_ENDED`, stale/zero-active status where applicable, and valid-session retention for replacement grants or exempt owner roles. `spec/SECURITY-BOUNDARY.md` and `spec/API.md` describe the new contract.

## Task Commits

1. Task 1 RED tests: `47a64f6`.
2. Task 1 implementation and API documentation: `63288f7`.
3. Task 2 legacy helper removal and live-fixture migration: `5f59ace`.
4. Task 3 cascades, route tests and security specification: `0db9239`.

## Verification

- Task 1 acceptance rerun: 1316 passed (`test_connectors`, `test_degram_pairing`, `test_cross_project_matrix`, `test_connector_session`).
- Task 2 acceptance rerun: 1307 passed, 1 skipped. Seven `integration and live` DSAV tests collected without import errors; they were **not run** against a live stack.
- Task 3 acceptance rerun: 1446 passed, 1 skipped, 4 existing Starlette per-request-cookie deprecation warnings. A prior focused connector-session/access rerun passed 135 tests. The earlier full Task 3 run passed 1446, 1 skipped after the additional edge tests (the preceding run had 1444, 1 skipped).
- Source gates: `status_for(` occurs in the overview; it constructs no `credentials` field. The removed helper definitions are absent, the two DSAV fixtures contain no `/credentials` call, and `revoke_unauthorized` occurs in four membership/invite paths. Password, project, member and grant cascades are present. Scoped `git diff --check` passed.
- `graphify update .` completed: 18492 nodes, 30884 edges and 1071 communities; it reported missing optional `tree_sitter_sql` for one SQL file. Generated graph/cache changes are excluded from this plan's commit.

## Decisions and Deviations

- The plan prose asks invite acceptance to lower an existing member's role, but WR-24 forbids demotion on acceptance. Tests preserve or raise the role on acceptance; the existing-account invite creation route is the role-changing path that can demote and revoke an unauthorized session. No security guarantee was weakened to satisfy the contradictory example.
- Connector-access DELETE revokes sessions only when it removes a previously live authorization and the user is no longer authorized. A redundant DELETE, replacement grant and exempt owner/admin do not unnecessarily end a valid session.
- The real cleanup script is `data-service/d49_store_cleanup.py`, rather than the stale path in the plan prose. No code or data in the running stack was changed by this plan.

## Deferred Verification

- No live DSAV execution, Docker rebuild/deployment, credential use against a running stack or in-container baseline check was performed. The two fixtures were collected only; plans 1308-19/20 own live retirement/rollout and its human checkpoints.
- WEBUI-07 is delivered for this server-side slice but remains open in the phase requirement ledger until the dependent UI and live work are accepted. The plan's `requirements-completed` field mirrors its required IDs, not a claim that the entire phase requirement has passed live acceptance.

## Next Phase Readiness

Server-side D-26/D-32/D-33/D-41 is ready for 1308-15 (Web UI connector flows), then the later dependency and live rollout plans. Keep unrelated dirty planning files and generated graph output out of scoped commits.

## Self-Check: PASSED (offline scope)

All four task commits are present and the three automated task suites passed. Live DSAV and deployment acceptance remain explicitly open.
