---
phase: 1205-security-and-tenancy-release-gate
plan: "02"
subsystem: auth
tags: [scrypt, session-tokens, rbac, json-persistence, python, threading, tdd]

# Dependency graph
requires: []
provides:
  - "data-service/auth.py — user store (scrypt passwords), opaque hashed session tokens with absolute+idle expiry, project memberships (viewer/editor/owner), single-use invites, three principal resolvers (user session, connector token, internal service token), bootstrap-admin routine, deployment-profile reader"
  - "data-service/tests/test_auth_store.py — 55 unit + concurrency + expiry-boundary tests, all passing"
affects:
  - "1205-07 (require_principal dependency imports Principal/resolve_*_principal/SESSION_COOKIE_NAME/CSRF_HEADER/SERVICE_TOKEN_HEADER)"
  - "1205-08 (test fixtures build an authorized_client on create_session/set_membership)"
  - "1205-10 (auth flip wires ensure_bootstrap_admin into the FastAPI lifespan hook)"
  - "1205-12 (project routes consume create_project_if_unclaimed/effective_role/list_member_projects)"
  - "1205-16 (spec/SECURITY-BOUNDARY.md documents the single-uvicorn-worker RLock constraint recorded in this module's docstring)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JSON-under-DATA_DIR persistence mirroring connectors.py: _load/_save with fail-soft-to-empty-list reads and atomic temp-file + os.replace writes"
    - "One threading.RLock (_STORE_LOCK) serializes every read-modify-write across all four stores — sufficient because data-service/Dockerfile runs a single uvicorn worker with no --workers flag"
    - "Store functions return None/False uniformly on any lookup failure (unknown vs wrong-password vs revoked vs expired) — no distinct return shape or log line leaks which case occurred"

key-files:
  created:
    - data-service/auth.py
    - data-service/tests/test_auth_store.py
  modified: []

key-decisions:
  - "Storage choice executed per plan: JSON files under AUTH_DIR (DG_DATA_DIR), NOT Neo4j nodes — Schema Change Propagation list left untouched, confirmed by zero neo4j references in auth.py"
  - "ensure_bootstrap_admin's weak-password branch returns \"weak-password\" (a name the plan didn't specify) distinct from \"missing-env\", since the plan named a return value only for the missing-env case"
  - "resolve_connector_principal calls connectors.authenticate_token, never connectors.record_heartbeat — an auth check must not stamp liveness (T-39-02 idiom generalized); acceptance criterion confirms zero record_heartbeat references in auth.py"

patterns-established:
  - "Two-commit-per-task TDD gate: test(...) commit with tests failing against a not-yet-existing/extended module, then feat(...) commit implementing just enough to pass — enforced literally (auth.py deleted before writing Task 1's tests to get a true ModuleNotFoundError RED, not a rationalized skip)"

requirements-completed: []  # ALGN12-17 spans multiple plans in this phase (07, 08, 10, 12 also consume this store's contract) — NOT marked complete, per this plan's own success_criteria instruction.

coverage:
  - id: D1
    description: "Users, scrypt password hashing/verification, opaque hashed session tokens with inclusive-expired absolute+idle boundaries, and the three principal resolvers (user session, connector token, internal service token)"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_store.py -- 30 Task-1 tests, all pass (hash_password/verify_password/validate_password_policy/normalize_username/create_user/create_session/authenticate_session/revoke_session/revoke_user_sessions/resolve_session_principal/resolve_connector_principal/resolve_service_principal/deployment_profile)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Project memberships (viewer/editor/owner), atomic project claiming, single-use invites (72h TTL), bootstrap-admin routine (fail-closed in multi-user, warn-only in local), and the three concurrency proofs (session churn, project race, membership writes)"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_store.py -- 25 Task-2 tests, all pass (set_membership/get_role/remove_membership/effective_role/role_satisfies/create_project_if_unclaimed/create_invite/consume_invite/ensure_bootstrap_admin x6/3 concurrency tests)"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 02: Server-Side Identity Store (Users, Sessions, Memberships, Invites) Summary

**`data-service/auth.py` — a pure JSON-backed identity store mirroring `connectors.py`'s persistence idiom: scrypt password hashing, `dgs_`-prefixed hashed session tokens with inclusive absolute+idle expiry, viewer/editor/owner project memberships with an atomic project-claim primitive, single-use `dgi_` invite codes, the three D-04 principal resolvers, and a fail-closed bootstrap-admin routine — no route wiring yet, 55/55 tests green including three multi-threaded concurrency proofs.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 2 (both `type="auto" tdd="true"`)
- **Files modified:** 2 (`data-service/auth.py` created, `data-service/tests/test_auth_store.py` created)
- **Tests:** 55 passed (30 Task 1 + 25 Task 2), 0 failed

## Accomplishments

- `hash_password`/`verify_password`: stdlib `hashlib.scrypt` (n=16384, r=8, p=1, dklen=64), per-user `os.urandom(16)` salt, `scrypt$16384$8$1$<salt_b64>$<hash_b64>` encoding, `hmac.compare_digest` verification, malformed-encoding-safe (returns `False`, never raises).
- `create_session`/`authenticate_session`: `dgs_` + `secrets.token_urlsafe(32)` tokens, SHA-256 hash-at-rest (raw token never persisted — asserted by a test reading the sessions file text), inclusive-expired boundary semantics (`now >= expires_at` and `now - last_seen_at >= idle` are both expired), touch-on-activity only past `SESSION_TOUCH_INTERVAL_SECONDS`.
- Three principal resolvers (D-04): `resolve_session_principal`, `resolve_connector_principal` (delegates to `connectors.authenticate_token`, never `record_heartbeat`), `resolve_service_principal` (fails closed on an unset/blank `DG_SERVICE_TOKEN`, even against an empty header value).
- `deployment_profile` (D-07/D-19): `local` default, `multi-user`, `ValueError` on anything else.
- Memberships (D-02): `set_membership`/`get_role`/`remove_membership`/`list_memberships`/`list_members`/`list_member_projects`/`project_has_members`/`count_owners`, `role_satisfies`/`effective_role` (admin user principal is always `"owner"`; connector/service principals always `None`).
- `create_project_if_unclaimed`: atomic check-and-set inside one lock acquisition — proven race-free by an 8-thread concurrency test (exactly one `True`, exactly one owner).
- Invites (D-05): `create_invite`/`consume_invite` — `dgi_` codes, SHA-256 at rest, 72h TTL, single-use (second consume, expired, and unknown codes all return `None`).
- `ensure_bootstrap_admin` (D-05): creates once, never overwrites; missing or policy-failing secrets raise `RuntimeError` in `multi-user` and log exactly one `WARNING` (creating nothing) in `local`; the password never appears in the log text.
- Concurrency proof (ALGN12-17): 16-thread session create/revoke churn never resurrects a revoked token; 8-thread `create_project_if_unclaimed` race yields exactly one owner; 16-thread `set_membership` writes all 16 rows.

## Task Commits

Each task committed as a RED test commit followed by a GREEN implementation commit (TDD gate, `tdd="true"`):

1. **Task 1 RED:** `004fcb4` (test) — 30 failing tests against a not-yet-existing `auth` module (confirmed `ModuleNotFoundError` before writing any implementation)
2. **Task 1 GREEN:** `6e12fe3` (feat) — users, passwords, sessions, the three principal resolvers, deployment profile
3. **Task 2 RED:** `5846c91` (test) — 24 failing tests against not-yet-existing membership/invite/bootstrap functions (confirmed `AttributeError` before implementing)
4. **Task 2 GREEN:** `8c4a55c` (feat) — memberships, invites, atomic project claiming, bootstrap admin, concurrency proof

**Plan metadata:** (this commit)

## Files Created/Modified

- `data-service/auth.py` - new module: users, scrypt passwords, sessions, memberships, invites, principal resolvers, deployment profile, bootstrap admin (~470 lines)
- `data-service/tests/test_auth_store.py` - 55 tests covering every behavior bullet in both tasks, plus the three concurrency proofs (~500 lines)

## Decisions Made

- Storage choice (Claude's discretion per 1205-CONTEXT.md): JSON files under `AUTH_DIR = DG_DATA_DIR` mirroring `connectors.py` — not Neo4j. Confirmed by the acceptance-criteria grep (`neo4j` count = 0 in `auth.py`).
- `ensure_bootstrap_admin`'s weak-password branch (11-character `DG_BOOTSTRAP_ADMIN_PASSWORD`) returns `"weak-password"`, a return-value name the plan text didn't specify (it only named `"missing-env"` for the missing-env branch) — chosen for symmetry and because no downstream consumer in this phase's plans reads this specific string yet.
- `resolve_connector_principal` calls `connectors.authenticate_token` only, never `connectors.record_heartbeat` — an auth check must not stamp connector liveness, per the `/designstate/capture` idiom this plan generalizes.
- Cookie/header names, TTLs and the `SESSION_TOUCH_INTERVAL_SECONDS=60` value all follow the plan's Artifacts table verbatim (Claude's discretion already exercised at plan-authoring time, not re-litigated here).

## Deviations from Plan

None - plan executed exactly as written, including the exact function signatures, constants, and file layout specified in the Artifacts table. The two-commit-per-task TDD sequencing (delete-then-recreate `auth.py` to get a genuine RED before any implementation existed) was a process choice within the plan's own `tdd="true"` contract, not a deviation from it.

## Issues Encountered

- Initial `test_session_expiry_boundary_inclusive` used the default `DG_SESSION_IDLE_SECONDS` (7200s), which is shorter than the default `DG_SESSION_TTL_SECONDS` (43200s) — the test's `expires_at - 1` probe point was already idle-expired, producing a false failure unrelated to the expiry-boundary logic under test. Fixed by monkeypatching `DG_SESSION_IDLE_SECONDS` to a large value in that specific test so only the `expires_at` boundary is exercised (the idle boundary has its own dedicated test). This was a test-authoring correction, not a bug in `auth.py` — caught during the Task 1 GREEN run and fixed before the GREEN commit, so no separate deviation commit was needed.

## User Setup Required

None - no external service configuration required. This module has no route wiring yet (by design — 1205-07 wires it into FastAPI).

## Next Phase Readiness

- `data-service/auth.py`'s full contract (Principal dataclass, three resolvers, `SESSION_COOKIE_NAME`/`CSRF_HEADER`/`SERVICE_TOKEN_HEADER` constants, `create_session`/`set_membership`) is ready for 1205-07's `require_principal` FastAPI dependency and 1205-08's test fixtures.
- `ensure_bootstrap_admin` is ready for 1205-10's lifespan-hook wiring; it composes cleanly with `data-service/secrets_policy.py` (1205-01) since both take `(env, profile, logger)`-shaped signatures and never log a secret value.
- No Neo4j schema change was needed (storage choice confirmed JSON-only) — the Schema Change Propagation list in CLAUDE.md remains untouched by this plan, as anticipated.

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*

## Self-Check: PASSED

All created files found on disk (`data-service/auth.py`, `data-service/tests/test_auth_store.py`, this SUMMARY.md); commits `004fcb4`, `6e12fe3`, `5846c91`, `8c4a55c` found in git log.
