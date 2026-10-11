---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 30
subsystem: auth
status: complete
tags: [fastapi, authorization, degram, delegated-token, csrf, route-policy]

requires:
  - phase: 1301-17
    provides: DeGram pairing and delegated-token authorization baseline
provides:
  - Server-only per-project DeGram grants issued by project owners or DG admins
  - Cookie-session exchange requiring stored membership and an active grant
  - Retired user-created DeGram pairings and immediate delegated-token revocation cascades
  - Owner-visible grant requests and caller-filtered grant views
affects: [1301-31, 1301-33, DeGram client, Connectors]

tech-stack:
  added: []
  patterns:
    - JSON authorization store protected by auth._STORE_LOCK and auth._load/_save
    - Delegated token records may carry a session-bound grant_id rechecked on every request
    - Retired credential routes retain cleanup while rejecting issuance and exchange

key-files:
  created:
    - data-service/degram_grants.py
    - data-service/tests/test_degram_grants.py
  modified:
    - data-service/app.py
    - data-service/auth_routes.py
    - data-service/delegation.py
    - data-service/degram_pairing.py
    - data-service/route_policy.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md

key-decisions:
  - "D-39 grants are server-side authorization records, not secrets or user-managed credentials."
  - "Session-exchanged dgd_ tokens retain the cookie-session parent and add grant_id so logout and grant revocation both terminate access."
  - "Retired dgp_ pairing records remain deletable for cleanup, but no longer authenticate or support delegation."

patterns-established:
  - "Grant-specific revocation: revoke delegation records immediately and recheck grant liveness on every delegated request."
  - "Least-privilege listing: owner/admin project views may identify recipients; /degram/grants/mine omits grant identifiers and other users."

requirements-completed: []

coverage:
  - id: D1
    description: Owner/admin-issued project-member grants with no secret-bearing serializer and owner-visible pending requests.
    requirement: DGCL-05
    verification:
      - kind: integration
        ref: data-service/tests/test_degram_grants.py
        status: pass
    human_judgment: false
  - id: D2
    description: Cookie-session exchange mints a session-parented delegated token only for a current project member holding an active grant.
    requirement: DGCL-01
    verification:
      - kind: integration
        ref: data-service/tests/test_degram_grants.py
        status: pass
      - kind: integration
        ref: data-service/tests/test_delegated_token.py
        status: pass
    human_judgment: false
  - id: D3
    description: User-created pairing issuance and exchange are retired while legacy pairing-derived tokens fail closed.
    requirement: DGCL-05
    verification:
      - kind: integration
        ref: data-service/tests/test_degram_pairing.py
        status: pass
    human_judgment: false
  - id: D4
    description: Route-policy inventory and the SECURITY-BOUNDARY machine-checked block describe the new grant surface.
    verification:
      - kind: integration
        ref: data-service/tests/test_route_inventory.py and data-service/tests/test_security_boundary_spec.py
        status: pass
    human_judgment: false

duration: multi-session
completed: 2026-10-11
---

# Phase 1301 Plan 30: DeGram Owner/Admin Access Grants Summary

**Project owners and DG admins now grant server-only, per-project DeGram access; a signed-in member exchanges their cookie session only while that grant remains live, with legacy pairing credentials retired.**

## Performance

- **Duration:** Multi-session continuation
- **Started:** 2026-10-11T12:15:04Z (implementation commit timestamp)
- **Completed:** 2026-10-11T12:17:12Z
- **Tasks:** 3/3
- **Files modified:** 13

## Accomplishments

- Added a lock-protected grant and grant-request store with member validation, bounded label/purpose/note fields, one active grant per user/project, owner/admin management, and caller-filtered self-service views.
- Added `POST /auth/degram/session-exchange`, which requires cookie authentication, CSRF, stored membership, and a live grant before issuing a session-parented `dgd_` token that records `grant_id`.
- Added immediate delegated-token termination for grant replacement/revocation and member removal, plus live grant checks on each delegated request; logout, password change, and user deletion fail closed through existing session/user checks.
- Retired user-created `dgp_` pairing creation and exchange (`PAIRING_RETIRED`) while preserving legacy-row deletion cleanup and making historic pairing-derived delegation fail closed.
- Synchronized route inventory, cross-project coverage, connector expectations, `spec/SECURITY-BOUNDARY.md`, and `spec/API.md` with the grant model.

## Task Commits

The plan explicitly deferred commits for Tasks 1 and 2; their completed implementation and Task 3 documentation/tests were committed together by the plan's final framework-commit instruction.

1. **Tasks 1–3: Grant store/routes, session exchange/pairing retirement, specs and inventory** — `d58a56d` (feat)

**Plan metadata:** committed with this plan documentation

## Files Created/Modified

- `data-service/degram_grants.py` — server-side grant/request persistence, public serializers, active-grant resolution, and revocation cascades.
- `data-service/app.py` — grant administration/self-service routes, grants connector card, retired pairing creation, and membership-removal cascade.
- `data-service/auth_routes.py` — grant-gated cookie-session exchange and retired pairing exchange.
- `data-service/delegation.py` — grant-aware session delegation and `revoke_for_grant`.
- `data-service/degram_pairing.py` — retired pairing authentication semantics with cleanup retained.
- `data-service/route_policy.py` — six grant/session route classifications and retired-pairing policy annotations.
- `data-service/tests/test_degram_grants.py` — integration coverage of issuance, requests, least privilege, exchange, and revocation.
- `data-service/tests/test_degram_pairing.py` — retirement and legacy cleanup coverage.
- `data-service/tests/test_route_inventory.py` — 104-route inventory and grant-policy assertions.
- `data-service/tests/test_connectors.py` — grants-card terminology expectation.
- `data-service/tests/test_cross_project_matrix.py` — project-scoped grant/session-exchange coverage commentary.
- `spec/SECURITY-BOUNDARY.md` — grant lifecycle, retired pairing policy, route-policy block, and enforcement references.
- `spec/API.md` — grant/session-exchange and retired pairing API documentation.

## Verification

- `python -m pytest data-service/tests/test_degram_grants.py data-service/tests/test_degram_pairing.py data-service/tests/test_delegated_token.py data-service/tests/test_route_inventory.py data-service/tests/test_connectors.py data-service/tests/test_cross_project_matrix.py data-service/tests/test_security_boundary_spec.py -q` — **2222 passed in 50.83s**.
- `docker compose exec -T data-service ...` was intentionally not used for a source verdict: the existing container lacks `/app/degram_grants.py`, so its image predates Plan 30. Rebuilding or restarting it is reserved for the owner-consent checkpoint in Plan 36.
- A host-wide suite was attempted before finalization and reported environmental/infrastructure failures outside this plan's files: compose-only `neo4j` hostname resolution, Neo4j-backed integration collection, and missing archived Phase 1204 evidence paths. It was not accepted as a clean Plan 30 regression verdict. The targeted authorization, inventory, and security-spec suite above is clean.

## Decisions Made

- Grants deliberately carry no raw credential, token, secret, or hash; they are authorization records only.
- The standard session-delegation path remains available for the existing `ui-v2/#degram` slice; only the dedicated DeGram session-exchange endpoint requires a grant.
- Password change revokes active delegated tokens but does not silently revoke an owner/admin's authorization grant; a subsequent exchange remains governed by that current grant.

## Deviations from Plan

None - plan implementation executed as specified. Tasks 1 and 2 were intentionally held for the single final framework commit required by Task 3.

## Issues Encountered

- The running data-service container is stale for this plan (`degram_grants.py` is absent in `/app`). No rebuild or restart was performed because the plan reserves that operation for Plan 36 owner consent.
- The project-required `graphify update .` was denied by the execution environment because it would overwrite `graphify-out/`, which the owner explicitly excluded from this plan. No generated graph artifact was modified.

## User Setup Required

None - no external service configuration required. Plan 31 owns the browser UI for owners/admins; Plan 33 owns DeGram-client adoption of session exchange.

## Requirement Status

- `DGCL-01` and `DGCL-05` remain phase-level pending: this plan delivers their backend grant/session and revocation leg, while client adoption and live owner acceptance remain in Plans 31, 33, and 36.

## Next Phase Readiness

- Plan 31 can render the owner/admin grant and member request workflow on CONNECTORS.
- Plan 33 can remove local pairing-token handling and call `POST /auth/degram/session-exchange` after DG sign-in.
- Deployment/live verification remains pending Plan 36's owner-authorized data-service rebuild/restart and its live test guide.

## Self-Check: PASSED

- Confirmed all created and modified Plan 30 implementation files exist.
- Confirmed implementation commit `d58a56d` exists in repository history.
- No stub markers were found in Plan 30 source/test changes, and no security-relevant surface beyond the plan's explicit grant/session route threat model was introduced.

---
*Phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie*
*Completed: 2026-10-11*
