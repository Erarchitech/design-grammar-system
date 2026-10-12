---
phase: 1308-dg-web-ui
plan: "13"
subsystem: auth
tags: [connector-session, legacy-token-retirement, heartbeat, designstate-capture, route-policy, security-boundary, pytest]

requires:
  - phase: 1308-dg-web-ui
    provides: "dgk_ connector sign-in session, connector_session.touch/status_for (plan 06) and the 410 tombstone on credential creation (plan 09)"
provides:
  - "auth.resolve_connector_principal resolves only dgk_; a dgc_ Bearer is 401 CONNECTOR_AUTH_FAILED on every connector route (D-26)"
  - "POST /connectors/heartbeat as a normal connector row (_p(_CON)): touches the session, answers {connector_id, status, project, neo4j} (D-34)"
  - "POST /designstate/capture resolved through resolve_connector_principal, CAPTURE_PROJECT_MISMATCH kept"
  - "auth_fixtures.seed_legacy_credential and a six-route legacy-refusal sweep"
  - "SECURITY-BOUNDARY blocks/prose and API.md in step: five-row public-routes block, heartbeat row `connector`, capture the only connector-self route (D-41)"
affects: [1308-19, 1308-20, 1308-24]

tech-stack:
  added: []
  patterns:
    - "Fail-closed refusal: the retired prefix resolves to no principal, so the generic dispatch answers 401 with the sign-in hint, and the stored row is never touched"
    - "Tests that only need a stored legacy row seed it (seed_legacy_credential); no test mints a usable dgc_ token for authentication any more"

key-files:
  created: []
  modified:
    - data-service/app.py
    - data-service/auth.py
    - data-service/route_policy.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - data-service/tests/auth_fixtures.py
    - data-service/tests/test_auth_store.py
    - data-service/tests/test_auth_tracer.py
    - data-service/tests/test_cross_project_matrix.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_review_fix_1205.py
    - data-service/tests/test_security_boundary_spec.py
    - data-service/tests/test_designstate_capture.py
    - data-service/tests/test_connectors.py
    - data-service/tests/test_deployment_profile.py
    - data-service/tests/test_connector_session_routes.py

key-decisions:
  - "Owner answered proceed at the 1308-09 gate (retire connector-token creation with 410 now, refuse existing legacy dgc_ tokens in this plan); this plan is code and tests only, no Docker, no live service or data-store change (live cleanup is 1308-19/20)"
  - "Heartbeat reads the already-resolved principal from request.state and touches the session; a touch that finds the session gone answers CONNECTOR_SESSION_ENDED rather than a generic 401"
  - "auth.py no longer imports connectors (the legacy branch was its only use)"
  - "The legacy-refusal sweep also covers DELETE /auth/connector-session, so every route that lists the connector principal is covered"

patterns-established:
  - "Legacy-credential tests build a stored, non-revoked row without the legacy minting helpers (the sweep and the capture refusal test), so they survive the helper removal in 1308-24"

requirements-completed: []

coverage:
  - id: D1
    description: "Every test that authenticated with, or minted, a legacy token is moved onto dgk_ sessions or seed_legacy_credential, green before and after the server change (D-26)"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_store.py, test_auth_tracer.py, test_cross_project_matrix.py, test_route_inventory.py, test_review_fix_1205.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Heartbeat on a live dgk_ session answers active with project and neo4j (absent in multi-user) and stamps last_seen (D-26, D-34)"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connectors.py::TestHeartbeat, TestHeartbeatBundle; test_deployment_profile.py heartbeat bundle tests"
        status: pass
    human_judgment: false
  - id: D3
    description: "A stored, non-revoked legacy dgc_ token answers 401 CONNECTOR_AUTH_FAILED on heartbeat, capture, validation publish, computgraph publish, validation view and connector-session DELETE, without touching the row"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_session_routes.py::test_a_stored_legacy_token_answers_401_on_every_connector_route, test_the_legacy_refusal_leaves_the_credential_row_untouched"
        status: pass
    human_judgment: false
  - id: D4
    description: "Capture resolves through resolve_connector_principal and keeps CAPTURE_PROJECT_MISMATCH against the session's bound project"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_designstate_capture.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Spec 3.2, 4.1, 4.2, 5 and API.md changed in the same commit; public-routes block lists exactly five rows and the spec test asserts it without a heartbeat special case (D-41, WEBUI-10)"
    requirement: "WEBUI-10"
    verification:
      - kind: unit
        ref: "data-service/tests/test_security_boundary_spec.py::test_public_routes_block_equals_public_policies"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 13: Connectors authenticate only with sign-in sessions Summary

**The server no longer authenticates the retired `dgc_` connector token anywhere: heartbeat and Design State capture run on `dgk_` sessions, a legacy Bearer is a 401 with a sign-in hint on every connector route, and the spec blocks changed in the same commit.**

## Owner decision

Owner answered **proceed at the 1308-09 gate** (connector-token creation retired with 410 now, refusal of existing legacy `dgc_` tokens in this plan). This plan is code and tests only: no Docker, no live service, no live data-store change. The live credential cleanup is plans 1308-19/20.

## Accomplishments

- Task 1 (tracer, commit `0339075`): `auth_fixtures.seed_legacy_credential(project, connector_id)` writes one non-revoked row through `connectors.save_credentials` and returns the record (random hash, no usable token). The resolver tests, the tracer helper, matrix world T1 (`dgk_` for P1, a seeded row only for the overview/cleanup cases), the route-inventory DELETE cases and the WR-03 corrupt-store tests no longer authenticate with or mint a `dgc_` token. The suite was green on the old server (2343 passed) and stays green on the new one.
- WR-03 was rewritten rather than dropped: a corrupt credential store still refuses seeding and the DELETE cleanup without rewriting the file; a corrupt connector-session store authenticates nobody (`AuthStoreError` from `authenticate` and `touch`); the racing-heartbeat-versus-revoke test now races `connector_session.touch` against `revoke_token` and asserts the revoke sticks.
- Task 2 (commit `1acf3cf`): `resolve_connector_principal` resolves only `dgk_`; the heartbeat policy row is `_p(_CON)`; the handler reads the principal from `request.state`, calls `connector_session.touch`, answers `status_for(connector_id, projects={bound_project})["status"]`, the bound project and `_neo4j_bundle_or_none()`; capture resolves its Bearer through `auth.resolve_connector_principal` (named session errors propagate, None gives 401 `CONNECTOR_AUTH_FAILED`) and keeps the bound-project mismatch check with its generic 403.
- Spec (same commit, D-41): section 3.2 (mint sentence, status/heartbeat sentence with the Rhino-crash note, principal scope now lists the heartbeat and one connector-self route, the legacy paragraph rewritten as the retired-token paragraph), error table, 4.1 heading/credential wording and the block (five rows), 4.2 row `POST|/connectors/heartbeat|connector|-|-`, section 5 carve-out (capture only), section 10 enforcement line. `spec/API.md` principal table and the public-routes sentence updated too.
- Tests: heartbeat (valid session with `last_seen` check, unknown dgk_, stored legacy dgc_, missing/malformed, ended session via DELETE, user cookie refused 403), bundle (project echo, local Neo4j bundle, public URI override), capture (legacy stored token 401, ended session 401, mismatch, no liveness stamp), and a parametrized six-route legacy sweep plus a "row untouched" check.

## Task Commits

1. Task 1: `0339075`
2. Task 2: `1acf3cf`

## Verification (real output, run from the host)

- Baseline before changes (Task 1 verify files): 2342 passed, 1 skipped.
- Task 1 verify (test_auth_store, test_auth_tracer, test_cross_project_matrix, test_route_inventory, test_review_fix_1205, test_deployment_profile, test_authorized_fixtures): 2343 passed, 1 skipped.
- Task 2 verify (test_connectors, test_designstate_capture, test_deployment_profile, test_review_fix_1205, test_connector_session_routes, test_cross_project_matrix, test_auth_store, test_auth_tracer, test_security_boundary_spec, test_route_inventory): 2471 passed, 1 skipped.
- Adjacent files run as a regression check (test_authorized_fixtures, test_connector_session, test_degram_pairing, test_connector_access, test_dsav_watcher): 203 passed.
- Acceptance greps: `create_credential|authenticate_token|record_heartbeat` in the five Task 1 files prints nothing; `def seed_legacy_credential` found; route row `("POST", "/connectors/heartbeat"): _p(_CON)`; `grep -c 'POST|/connectors/heartbeat|connector|-|-' spec/SECURITY-BOUNDARY.md` returns 1 and the public block has no heartbeat line; `grep HEARTBEAT test_security_boundary_spec.py` prints nothing.
- Not run: the full data-service suite, any Docker or live check (not authorized).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Spec contract] spec/API.md edited in Task 2**
- **Found during:** Task 2 (the principal table said the legacy token is accepted and listed the heartbeat as public)
- **Fix:** Updated the legacy row and the public-routes sentence in the same commit as the behavior (CLAUDE.md spec-with-code contract); the file is not in the plan's file list.
- **Commit:** 1acf3cf

**2. [Rule 1 - Test intent] Heartbeat tests needed an unauthenticated client**
- **Found during:** Task 2 (the module client carries an admin cookie by default; the heartbeat is no longer connector-self, so a cookie without a Bearer would answer 403 rather than 401)
- **Fix:** The heartbeat test classes use `dg_principal("none")`, and a dedicated test pins that a user cookie is refused with 403 `PRINCIPAL_NOT_PERMITTED`.
- **Commit:** 1acf3cf

**3. [Rule 1 - Test intent] Two legacy-only heartbeat tests rewritten**
- **Found during:** Task 2 (`test_missing_project_defaults_to_default_project` and the overview-stamping assertion depended on the legacy `last_connection` stamp)
- **Fix:** The default-project test is removed (a session always has a project); the overview-history test now stamps the legacy row directly, since the session-based overview is 1308-24.
- **Commit:** 1acf3cf

### Process notes

- Task 2 production code and its rewritten tests were run RED first (16 failures against the old server), then GREEN after the server change.

## Deferred Issues

- `data-service/tests/test_dsav_live_loop.py` (L368) and `data-service/tests/test_dsav_publish_leg.py` (L439) still mint a credential over HTTP against a live `BASE_URL` (they answer 410 since 1308-09) and would authenticate with a `dgc_` token that is now refused. They are live-only, not in this plan's file list and were not run; they need a `POST /auth/login` + `POST /auth/connector-session` sign-in instead, to be handled with the live cleanup (1308-19/20) or 1308-24.
- `connectors.create_credential`, `authenticate_token`, `record_heartbeat` and the legacy overview (`last_connection`) remain until 1308-24; `TestOverviewProjectFilter` in test_connectors.py still calls `record_heartbeat` directly for that reason.
- `ui-v2/src/lib/connectorsApi.js` and the API docs content still describe the credential POST (carried over from 1308-09 to the Web UI plans).

## Known Stubs

None.

## Threat Flags

None. T-1308-13-01 (resolver refuses the prefix, six-route sweep), -02 (`_neo4j_bundle_or_none` in the heartbeat, bundle tests on sessions), -03 (block and spec test changed in the same commit) and -04 (each migrated test keeps its assertion intent; Task 1 green on the old and the new server) are mitigated and asserted.

## Requirements

WEBUI-07 (authentication half) and WEBUI-10 are only partly delivered: session-based connector status in the overview, removal of the legacy helpers and the D-33 cascades are 1308-24, the live credential cleanup is 1308-19/20 and the Web UI plans replace the credential client. Neither is marked complete in REQUIREMENTS.md.

## Self-Check: PASSED

- FOUND: data-service/app.py, data-service/auth.py, data-service/route_policy.py, spec/SECURITY-BOUNDARY.md, spec/API.md, data-service/tests/auth_fixtures.py (`seed_legacy_credential`)
- FOUND commits: 0339075, 1acf3cf
