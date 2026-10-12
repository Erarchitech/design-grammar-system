---
phase: 1308-dg-web-ui
plan: "03"
subsystem: auth
tags: [connector-session, dgk, sha256, fastapi, pytest, tdd]

requires:
  - phase: 1301-degram
    provides: delegation.py shape, connector_access grants, company.py project-company map
provides:
  - "data-service/connector_session.py: dgk_ connector sign-in session store (issue, authenticate, touch, revoke_*, status_for, public_answer)"
  - "connector_access.is_exempt / is_authorized (D-29 owner/admin exemption predicate)"
  - "Error codes CONNECTOR_AUTH_FAILED / CONNECTOR_SESSION_EXPIRED / CONNECTOR_SESSION_ENDED (401); CONNECTOR_ACCESS_REQUIRED (403) reused"
affects: [1308-06, 1308-08, 1308-09, 1308-13, 1308-24]

tech-stack:
  added: []
  patterns:
    - "Hash-only token store next to auth.MEMBERSHIPS_FILE, all read-modify-write under auth._STORE_LOCK"
    - "Live re-check of user, company and connector authorization on every authenticate; grant loss answers 403 without killing the row"

key-files:
  created:
    - data-service/connector_session.py
    - data-service/tests/test_connector_session.py
  modified:
    - data-service/connector_access.py

key-decisions:
  - "authenticate returns None for a non-dgk_ input (caller falls through to the next credential kind) and raises only for dgk_ strings"
  - "Order of checks: prefix, lookup, revoked, expiry (now >= expires_at), user exists, company equal, is_authorized; only user and company failures mark the row revoked"
  - "Revoked and expired rows are retained 90 days after expiry so status_for can answer stale; afterwards never_connected"
  - "public_answer accepts the neo4j bundle as a dict or a pydantic model (model_dump) and adds it only when given; expiresInSeconds = expires_at - issued_at"

patterns-established:
  - "Session public record: token_hash removed, session_id = token_hash[:16]"

requirements-completed: [WEBUI-07]

coverage:
  - id: D1
    description: "dgk_ session store: issue mints a prefixed CSPRNG token, stores only the SHA-256 hash; authenticate re-checks user, company and grant live"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_session.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Revoke cascades, touch, status derivation (active/stale/never_connected), public answer and TTL override"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_session.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "connector_access.is_exempt / is_authorized added without changing any existing caller"
    requirement: "WEBUI-07"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connector_access.py"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 03: Connector Session Store Summary

**`dgk_` connector sign-in session store (hash-only, 8 h TTL, live user/company/grant re-check) plus the D-29 owner/admin exemption helpers, fully unit-tested.**

## Accomplishments

- `connector_session.py` mirrors `delegation.py`: `issue` mints `dgk_` + `secrets.token_urlsafe(32)`, persists only the SHA-256 hash with username, project, connector_id, company, issued_at, expires_at, last_seen, revoked in `auth-connector-sessions.json`, prunes rows older than expiry + 90 days.
- `authenticate` re-checks live on every call (user exists, company unchanged, `connector_access.is_authorized` with an admin-elevated effective role). Editor/viewer without a grant get 403 `CONNECTOR_ACCESS_REQUIRED` and the row survives; a deleted user or a company change revokes the row and answers 401 `CONNECTOR_SESSION_ENDED`. `now == expires_at` is rejected, `expires_at - 1` accepted.
- `touch`, `revoke_token`, `revoke_for_user`, `revoke_for_user_project`, `revoke_for_project`, `revoke_for_connector_grant`, `revoke_unauthorized`, `status_for` (D-32), `public_answer` and `session_ttl_seconds` (`DG_CONNECTOR_SESSION_TTL_SECONDS`, invalid falls back to 28800) are in place for plans 06/08/09/13/24.
- `connector_access.is_exempt` / `is_authorized` are additive; no existing caller or route changed, `connectors.py` untouched.

## Task Commits

1. Task 1 RED: `c3f7e05` (test) - failing session/exemption tests
2. Task 1 GREEN: `c02e5cf` (feat) - issue/authenticate + exemption helpers
3. Task 2 RED: `e90db7f` (test) - failing revoke/touch/status/answer tests
4. Task 2 GREEN: `79ced51` (feat) - revoke cascades, touch, status, answer

## Verification

- `python -m pytest data-service/tests/test_connector_session.py data-service/tests/test_connector_access.py -q` -> 105 passed (51 new session tests + 54 existing access tests, run from the host).
- `grep` checks: `def is_exempt` / `def is_authorized` found in `connector_access.py`; `SESSION_TOKEN_PREFIX = "dgk_"` found once; `connectors.py` has no working-tree change.
- A test asserts the raw token is absent from the store file bytes (after issue, authenticate and revoke).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `_revoke_where` and `revoke_token` implemented in Task 1**
- **Found during:** Task 1 (the plan's revoked-token and "row marked revoked" tests need them)
- **Fix:** Added the two helpers to Task 1 GREEN; Task 2 added the remaining revoke helpers. Behaviour unchanged from the plan.

**2. [Rule 1 - Bug] Wrong hand-computed timestamp literals in my own Task 2 tests**
- **Found during:** Task 2 GREEN (two literal expectations were off by the TTL / offset)
- **Fix:** Corrected to the values `time.gmtime` yields (`2027-01-15T16:00:00Z`, `2027-01-15T08:01:40Z`); no production code affected.

**3. [Plan acceptance wording] `grep -c "^def revoke_"` returns 6, not 5**
- The pattern also matches `revoke_unauthorized`, which the plan lists separately. All six functions exist; the intent (five named helpers plus `revoke_unauthorized`) is met.

## Known Stubs

None.

## Threat Flags

None. New surface is the store file `auth-connector-sessions.json` (hash-only), covered by T-1308-03-02.

## Issues Encountered

None. Pre-existing unrelated working-tree changes were left untouched.

## Next Phase Readiness

Plan 1308-06 can mint and resolve `dgk_` sessions, 1308-09 can call `is_exempt` / `is_authorized`, 1308-13 `touch`, 1308-24 `status_for` and the revoke cascades.

## Self-Check: PASSED

- FOUND: data-service/connector_session.py, data-service/tests/test_connector_session.py, data-service/connector_access.py
- FOUND commits: c3f7e05, c02e5cf, e90db7f, 79ced51
