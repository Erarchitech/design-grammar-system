---
phase: 1308-dg-web-ui
plan: "09"
subsystem: auth
tags: [connector-access, owner-admin-exemption, tombstone-410, route-policy, security-boundary, pytest]

requires:
  - phase: 1308-dg-web-ui
    provides: "connector_access.is_exempt / is_authorized (plan 03) and POST /auth/connector-session (plan 06)"
provides:
  - "Owner/admin exemption through is_exempt in access_state, create_request and request_connector_access (D-29); editor and viewer need a per-connector grant"
  - "connectors.tokens_retired(status_code=410) and POST /connectors/{connector_id}/credentials as a 410 CONNECTOR_TOKENS_RETIRED tombstone on a session policy row (D-31)"
  - "Rewritten access-matrix and credential tests; SECURITY-BOUNDARY and API.md in step with the code"
affects: [1308-10, 1308-13, 1308-19, 1308-24]

tech-stack:
  added: []
  patterns:
    - "Tombstone route on a plain session policy row (precedent: retired DeGram pairing)"
    - "tokens_retired built with fastapi.HTTPException inside connectors.py because auth imports connectors (no auth.auth_error import)"

key-files:
  created: []
  modified:
    - data-service/connector_access.py
    - data-service/app.py
    - data-service/connectors.py
    - data-service/route_policy.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - data-service/tests/test_connector_access.py
    - data-service/tests/test_cross_project_matrix.py
    - data-service/tests/test_connectors.py
    - data-service/tests/test_route_inventory.py

key-decisions:
  - "Task 2 (checkpoint:decision, one-way retirement): owner answered proceed in this session; connector-token creation retired now, refusal of existing tokens follows in 1308-13"
  - "The credentials POST row moved from member/body/viewer to session so every signed-in caller gets the same 410 (flagged assumption of the plan)"
  - "tokens_retired lives in connectors.py with HTTPException directly: auth imports connectors, so importing auth there would be a cycle"
  - "ACCESS_EXISTS message and hint reworded from credential creation to connector sign-in; no test or client depended on the old text"
  - "connectors.create_credential kept to seed legacy rows in tests (test_connectors.py _mint helper) until 1308-13 / 1308-24"

patterns-established:
  - "Credential-create tests seed legacy dgc_ rows with a local _mint helper instead of the retired route"

requirements-completed: []

coverage:
  - id: D1
    description: "Owner/admin exempt, editor/viewer need a grant in access_state, create_request and POST /connector-access-requests (D-29)"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_access.py, data-service/tests/test_cross_project_matrix.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "A viewer with a grant signs in on a dgk_ session and publishes for its bound project; another project is refused (D-30)"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_access.py::test_viewer_with_a_grant_publishes_for_its_bound_project"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /connectors/{id}/credentials answers 410 CONNECTOR_TOKENS_RETIRED for every role and mints nothing; unknown id and degram stay 404; DELETE cleanup kept (D-31)"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connectors.py, test_connector_access.py, test_cross_project_matrix.py, test_route_inventory.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Spec sections 3.2, 3.4, 4.2 route row, 6 and API.md changed in the same commits as the behavior (D-41)"
    requirement: "WEBUI-10"
    verification:
      - kind: unit
        ref: "data-service/tests/test_security_boundary_spec.py"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 09: Connector access matrix and token retirement Summary

**Owner and admin are the only roles exempt from a per-connector grant (editor and viewer need one), and `POST /connectors/{connector_id}/credentials` is now a 410 `CONNECTOR_TOKENS_RETIRED` tombstone, with spec and tests in step.**

## Owner decision (Task 2)

Checkpoint `checkpoint:decision` (one-way retirement of connector tokens): **owner answered "proceed"** in the invoking session. Task 3 was executed on that basis. Rollback would mean restoring the handler and the legacy resolver branch from git; plan 1308-13 then refuses existing `dgc_` tokens and 1308-20 marks the live credentials revoked.

## Accomplishments

- Task 1: `access_state`, `create_request` (stored role) and the `request_connector_access` handler decide exemption with `is_exempt`. An editor without a row is `requestable`, gets 201 pending on a request, and `pending` then `available` after approval; owner/admin and active-grant holders get 409 `ACCESS_EXISTS`. The `ACCESS_EXISTS` text now speaks of connector sign-in.
- D-30 is pinned by a test: a viewer holding a grant mints a `dgk_` session and `POST /validation/publish` for its bound project is admitted by the policy (answers the Speckle-config 404, not 401/403) while another project is 403.
- Task 3: `connectors.tokens_retired()` plus the tombstone handler (404 for unknown id and `degram` first, then 410, no minting); policy row `_p(_SES)`; DELETE cleanup untouched.
- Tests rewritten, not patched: the grant-then-create flow now asserts 410 with no token and uses `POST /auth/connector-session` to exercise the grant; the matrix class asserts 410 for every member role and project; test_connectors seeds legacy rows through a `_mint` helper; the route-inventory assertion expects the session row with no project source.
- Spec: SECURITY-BOUNDARY 3.2 legacy-token paragraph, 3.4 row `CONNECTOR_TOKENS_RETIRED` (410), 3.5 connector-card sentence, 4.2 block row `POST|/connectors/{connector_id}/credentials|session|-|-`, 6 retired-route entry (DELETE kept one release); API.md rows for the tombstone and the DELETE cleanup, and the access-state text.

## Task Commits

1. Task 1 (exemption, tests, spec text): `d94958b`
2. Task 2: owner decision, no commit
3. Task 3 (410 tombstone, policy row, tests, spec): `8caa384`

## Verification (real output, run from the host)

- Task 1 verify (test_connector_access, test_cross_project_matrix, test_connector_session, test_connector_session_routes): 1343 passed. Baseline before changes: 1331 passed.
- Task 3 verify (test_connectors, test_cross_project_matrix, test_connector_access, test_degram_pairing, test_route_inventory, test_security_boundary_spec, test_deployment_profile, test_review_fix_1205): 2408 passed, 1 skipped.
- Acceptance greps: no `role_satisfies(..., "editor")` left in connector_access.py; `is_exempt(` used in access_state, create_request, is_authorized and `request_connector_access`; no `startswith("dgc_")` in test_connector_access.py; `CONNECTOR_TOKENS_RETIRED` found in connectors.py (1), SECURITY-BOUNDARY.md (3), API.md (1); the route-policy block row count is 1; `create_credential(` calls in the tombstone body: 0.
- Not run: the full data-service suite, any Docker or live check (not authorized).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Spec contract] SECURITY-BOUNDARY.md edited in Task 1**
- **Found during:** Task 1 (line 78 said 409 `ACCESS_EXISTS` for an owner/editor/admin, now false)
- **Fix:** Reworded in the same commit as the behavior change (CLAUDE.md spec-with-code contract), although Task 1's file list named only API.md. Task 3 then made the remaining section edits.
- **Commit:** d94958b

**2. [Rule 3 - Blocking] `tokens_retired` cannot use `auth.auth_error`**
- **Found during:** Task 3 (auth imports connectors; importing auth into connectors is a cycle)
- **Fix:** Built the same `{error, hint, code}` detail with `fastapi.HTTPException` directly; a test pins the shape.
- **Commit:** 8caa384

### Process notes

- Task 3 production code and its rewritten tests were written together; no separate RED run was observed. The rewritten tests assert 410 and the new policy row, so they fail on the old handler (which answered 201/403).
- Matrix tests use the module-scoped world; the new editor case cleans its pending request through `revoke_for_user_project` (which closes requests), and the full matrix still passes.

## Deferred Issues

- `data-service/tests/test_dsav_live_loop.py` (L368) and `test_dsav_publish_leg.py` (L439) mint a credential over HTTP against a live `BASE_URL`; they will answer 410 against a deployed image after 1308-19. They were not run here (live-only) and are outside this plan's file list; they belong with the 1308-13 seeding-helper work.
- `ui-v2/src/lib/connectorsApi.js` (L20-35) and the API docs content `ui-v2/src/screens/apidocs/content/03-credentials-api.js` still call and describe the credential POST; the Web UI plans of this phase replace them.
- `connectors.create_credential` and the `dgc_` resolver branch stay until 1308-13 / 1308-24, per the plan.

## Known Stubs

None.

## Threat Flags

None. T-1308-09-01 (single `is_exempt` helper, grep gate, matrix tests), -02 (410 without minting, session row, test per role) and -04 (same-commit spec rows plus test_security_boundary_spec) are mitigated and asserted; -03 accepted by the owner at the checkpoint.

## Requirements

WEBUI-07 and WEBUI-10 are only partly delivered (server access matrix and token-creation retirement; refusal of existing `dgc_` tokens, UI and cleanup belong to 1308-13, 1308-19, 1308-20, 1308-24), so neither is marked complete in REQUIREMENTS.md.

## Self-Check: PASSED

- FOUND: data-service/connectors.py, data-service/connector_access.py, data-service/route_policy.py, spec/SECURITY-BOUNDARY.md, spec/API.md
- FOUND commits: d94958b, 8caa384
