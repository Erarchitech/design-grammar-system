---
phase: 1205-security-and-tenancy-release-gate
plan: "07"
subsystem: auth
tags: [fastapi-dependency, deny-by-default, route-policy, session-cookie, csrf, scrypt, deployment-profile, python]

# Dependency graph
requires:
  - phase: 1205-01
    provides: "secrets_policy.enforce_startup_secrets (known-default secret refusal)"
  - phase: 1205-02
    provides: "auth.py identity store — Principal, three resolvers, create_session/effective_role, SESSION_COOKIE_NAME/CSRF_HEADER/SERVICE_TOKEN_HEADER, ensure_bootstrap_admin, deployment_profile"
provides:
  - "data-service/route_policy.py — RoutePolicy dataclass, seeded ROUTE_POLICIES table, RESOURCE_RESOLVERS registry, policy_for()"
  - "data-service/auth.py — auth_error, cookie_secure, require_principal (the deny-by-default FastAPI dependency: policy lookup, credential precedence, principal-kind check, CSRF, project mismatch/required/forbidden)"
  - "data-service/auth_routes.py — POST /auth/login, POST /auth/logout, GET /auth/me, POST /auth/password"
  - "One enforced project route (GET /validation/runs/{project}) proving D-01..D-04 end to end"
  - "Startup-time profile consumers wired into the FastAPI lifespan: DG_DEPLOYMENT validation, known-default secret refusal, bootstrap admin"
  - "Heartbeat Neo4j bundle omission in multi-user; import-time docs/redoc/openapi gating"
affects:
  - "1205-10 (the wide route-inventory flip reuses require_principal/ROUTE_POLICIES/RESOURCE_RESOLVERS verbatim; adds a resolver per resource-scoped route)"
  - "1205-08 (test fixtures across the rest of the suite build authorized clients on this contract)"
  - "1205-09 (docker-compose.yml wiring for DG_SERVICE_TOKEN/DG_BOOTSTRAP_ADMIN_*/DG_DEPLOYMENT — the live container currently warns these as missing in local profile, confirmed by this plan's live smoke test)"
  - "1205-11 (ui-v2 auth.js becomes a thin client of the four /auth/* routes this plan ships)"
  - "1205-16 (spec/SECURITY-BOUNDARY.md's public-route allowlist must include this plan's five seeded routes)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deny-by-default FastAPI dependency: (method, route.path template) -> RoutePolicy lookup, missing entry fails closed with 403 ROUTE_UNCLASSIFIED"
    - "Explicit-credential precedence with no fallback: service header > connector Bearer > session cookie; an invalid explicit credential never falls through to a weaker one"
    - "Project-source declaration decoupled from mismatch detection: ALL present candidates (path/query/body) are compared for mutual agreement regardless of which one the route declares as authoritative"
    - "Fixed dummy-hash timing equalization for login (anti-enumeration, T-1205-07-05)"
    - "Lifespan startup hooks that let exceptions propagate (profile/secrets/bootstrap-admin) vs. ones that must never block serving (the pre-existing watcher) — same lifespan function, deliberately different failure-handling policy per hook"

key-files:
  created:
    - data-service/route_policy.py
    - data-service/auth_routes.py
    - data-service/tests/test_auth_tracer.py
    - data-service/tests/test_deployment_profile.py
  modified:
    - data-service/auth.py
    - data-service/app.py

key-decisions:
  - "Project-mismatch detection gathers path+query+body candidates unconditionally (not just the route's declared project_source) — a body-and-path route with disagreeing values fails PROJECT_MISMATCH even though only one source is authoritative for authorization"
  - "Admin-only routes (a RoutePolicy whose principals is exactly {admin}) require is_admin; no route in this tracer's seeded table uses this branch yet (1205-10 will), so it is implemented per the plan's step 6 but only reachable via a future route"
  - "Docs/redoc/openapi gating reads DG_DEPLOYMENT directly via os.getenv at import time (not through auth.deployment_profile, which raises ValueError on an unrecognized value) — an import-time crash on an unrelated env typo would be worse than fail-closed docs"

patterns-established:
  - "auth_error()/cookie_secure() live in auth.py alongside require_principal rather than app.py, to avoid an app.py<->auth.py circular import while keeping the same {error,hint,code} detail shape as app.py's _structured_error_response"

requirements-completed: []  # ALGN12-17 and ALGN12-19 both span multiple plans in this phase (01, 02, 04, 07, 08, 09, 10, 11, 12, 15, 16, 18 variously declare them) — NOT marked complete here, consistent with 1205-01/1205-02's own precedent.

coverage:
  - id: D1
    description: "Server-side login (D-01): POST /auth/login issues an HttpOnly, SameSite=Strict dg_session cookie; wrong-password and unknown-user both answer 401 AUTH_FAILED with an identical message; login without X-DG-CSRF answers 403"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_login_success_sets_httponly_samesite_cookie_and_no_token_in_body -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_login_wrong_password_and_unknown_user_both_401_auth_failed_identical_message -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_login_without_csrf_header_403 -- pass"
    human_judgment: false
  - id: D2
    description: "Deny-by-default require_principal dependency (D-03): policy-driven lookup on (method, route template); an unclassified route answers 403 ROUTE_UNCLASSIFIED"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_unclassified_route_answers_403_route_unclassified -- pass"
    human_judgment: false
  - id: D3
    description: "Principal precedence with no fallback (D-04): service header > connector Bearer > session cookie; an invalid explicit credential never falls back to a weaker one; a principal kind not permitted for the route answers 403 PRINCIPAL_NOT_PERMITTED"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_connector_token_bound_to_p1_on_p1_route_is_principal_not_permitted -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_invalid_bearer_plus_valid_cookie_401_connector_auth_failed_no_fallback -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_valid_service_header_on_route_is_principal_not_permitted -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_wrong_service_header_401_service_auth_failed -- pass"
    human_judgment: false
  - id: D4
    description: "Project scoping (D-03): a path/query/body disagreement answers 403 PROJECT_MISMATCH; a declared-but-absent project source answers 403 PROJECT_REQUIRED; membership-based access on the one enforced route (GET /validation/runs/{project}) answers 200 for a member, 403 PROJECT_FORBIDDEN for a non-member, 401 with no cookie, and 200 for an admin on any project"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_body_and_path_project_mismatch_403 -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_declared_project_source_absent_403_project_required -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_member_access_cross_project_403_and_no_cookie_401 -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_admin_user_can_access_any_project -- pass"
    human_judgment: false
  - id: D5
    description: "Auth account routes (D-01): GET /auth/me returns username/isAdmin/memberships; POST /auth/logout revokes the session (401 afterward); POST /auth/password rejects a wrong current password (403) and a weak new password (422), and on success revokes every other session while the current one keeps working"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_auth_me_returns_username_isadmin_and_memberships -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_logout_revokes_session_then_401 -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_password_change_wrong_current_403 -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_password_change_weak_new_password_422 -- pass"
      - kind: unit
        ref: "data-service/tests/test_auth_tracer.py::test_password_change_success_revokes_other_sessions_keeps_current -- pass"
    human_judgment: false
  - id: D6
    description: "Startup profile consumers (D-05/D-07/D-11/D-19): DG_DEPLOYMENT validated before ensure_spec_indexes; a known-default secret raises in multi-user and warns once (naming the key) in local; DG_DEPLOYMENT=prod raises; the bootstrap admin is created from env when none exists; the heartbeat omits the Neo4j bundle in multi-user; /docs, /redoc, /openapi.json exist only under the import-time local profile"
    requirement: "ALGN12-19"
    verification:
      - kind: unit
        ref: "data-service/tests/test_deployment_profile.py -- 7/7 pass (heartbeat bundle x2, lifespan secrets-refusal, lifespan warn-and-start, unknown-profile raise, bootstrap-admin creation, docs gating subprocess check)"
      - kind: integration
        ref: "docker compose build/up data-service; live startup log shows exactly one WARNING naming the four currently-unwired secret keys and continues (local profile, confirms the code path fires against the real container before 1205-09 wires compose env)"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 07: Tracer Slice — Server-Side Login, Deny-by-Default Dependency, One Enforced Project Route Summary

**A `require_principal` FastAPI dependency reads a policy-driven route table (`route_policy.py`) to enforce server-side login (`auth_routes.py`, scrypt + HttpOnly/SameSite=Strict session cookies) and project membership on one real route (`GET /validation/runs/{project}`), with a startup-time profile gate that refuses known-default secrets in multi-user, bootstraps the admin account, and withholds the Neo4j heartbeat bundle and API docs outside the local profile.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2 (both `type="auto" tdd="true"`)
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- `route_policy.py`: `RoutePolicy` dataclass (`principals`, `project_source`, `min_role`), the principal-token vocabulary, a seeded `ROUTE_POLICIES` table (health, the four `/auth/*` routes, and the one enforced project route), an empty `RESOURCE_RESOLVERS` registry for 1205-10, and `policy_for(method, path)`.
- `auth.py` gained `auth_error`, `cookie_secure`, and `require_principal` — the full D-03/D-04 decision tree: policy lookup (fail-closed `ROUTE_UNCLASSIFIED`), public/connector-self bypass with CSRF-on-unsafe-public, credential resolution in strict service-header > connector-Bearer > session-cookie order with no fallback on an explicit-but-invalid credential, principal-kind gating (`PRINCIPAL_NOT_PERMITTED`), CSRF on session-authenticated unsafe methods, admin-only gating, and project scoping (mismatch/required/forbidden) via `effective_role`/`role_satisfies` for users and `bound_project` equality for connectors.
- `auth_routes.py`: `POST /auth/login` (scrypt verify against a fixed dummy hash for unknown usernames so both failure branches cost the same derivation and share one message), `POST /auth/logout` (revokes + clears the cookie), `GET /auth/me`, `POST /auth/password` (wrong-current 403, weak-new 422, success revokes every other session).
- `app.py`: the tracer route (`GET /validation/runs/{project}`) carries `dependencies=[Depends(auth.require_principal)]` — the only explicit occurrence of that dependency in `app.py` (`auth_routes.router`'s own router-level dependency is a separate file); `auth_routes.router` is included on the app.
- `app.py` lifespan: `auth.deployment_profile()` → `secrets_policy.enforce_startup_secrets()` → `auth.ensure_bootstrap_admin()` now run before `ensure_spec_indexes()`, letting a refusal propagate as a failed start (unlike the pre-existing watcher, which stays non-fatal on failure).
- `app.py` FastAPI construction: `docs_url`/`redoc_url`/`openapi_url` are computed once at import time from `DG_DEPLOYMENT` (anything but exactly `"local"` disables all three, fail-closed).
- `connector_heartbeat`: the `Neo4jBundle` is `None` when `auth.deployment_profile() == "multi-user"`, unchanged in `local`.
- 41 new tests (34 in `test_auth_tracer.py` = 17 cases × 2 deployment profiles; 7 in `test_deployment_profile.py`), all passing on the host and in-container.

## Task Commits

1. **Task 1: Tracer — require_principal, route_policy seed, auth routes, one enforced project route, end-to-end tests** — `0ea20d7` (feat)
2. **Task 2: Startup profile consumers — DG_DEPLOYMENT, D-11 refusal, bootstrap admin, heartbeat bundle, docs exposure** — `8d7176e` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `data-service/route_policy.py` - new: `RoutePolicy`, seeded `ROUTE_POLICIES`, `RESOURCE_RESOLVERS`/`register_resource_resolver`, `policy_for`
- `data-service/auth_routes.py` - new: the four `/auth/*` endpoints, dummy-hash timing equalization
- `data-service/auth.py` - added `auth_error`, `cookie_secure`, `_require_csrf`, `_resolve_project`, `require_principal`
- `data-service/app.py` - imports (`auth`, `auth_routes`, `secrets_policy`, `Depends`), tracer route dependency, `app.include_router(auth_routes.router)`, lifespan startup hooks, import-time docs gating, heartbeat Neo4j bundle omission
- `data-service/tests/test_auth_tracer.py` - new: 34 tests
- `data-service/tests/test_deployment_profile.py` - new: 7 tests

## Decisions Made

- Project-mismatch detection gathers path+query+body candidates unconditionally rather than only checking the route's declared `project_source` against itself — any two present sources that disagree fail `PROJECT_MISMATCH`, which is the stricter and safer reading of the plan's action text ("more than one distinct non-empty value" is evaluated across all gathered candidates, not just the declared one).
- `auth_error`/`cookie_secure` were added to `auth.py` (not `app.py`) per the plan's own Artifacts table, keeping the same `{error, hint, code}` shape as `app.py`'s `_structured_error_response` without introducing an `app.py`↔`auth.py` circular import.
- Docs/redoc/openapi gating reads `DG_DEPLOYMENT` via a bare `os.getenv` at import time rather than through `auth.deployment_profile()` (which raises `ValueError` on an unrecognized value) — an import-time crash from an unrelated environment typo would be a worse failure mode than simply keeping docs disabled.

## Deviations from Plan

None - plan executed exactly as written, including the exact function signatures, error codes, and file layout specified in the Artifacts table.

## Issues Encountered

- The live `data-service` container's `.env` does not yet export `DG_SERVICE_TOKEN`, `DG_BOOTSTRAP_ADMIN_USER`, or `DG_BOOTSTRAP_ADMIN_PASSWORD` into the container environment (that wiring is 1205-09's `docker-compose.yml` job, not this plan's). Rebuilding and restarting the container to run the in-container test suite surfaced this as a live smoke test: startup logged exactly one WARNING listing `NEO4J_PASSWORD(known-default)`, `LLM_MASTER_SECRET(known-default,too-short)`, `DG_SERVICE_TOKEN(missing)`, `DG_BOOTSTRAP_ADMIN_PASSWORD(missing)` and continued serving (local profile, as designed) rather than crashing the container. This is expected given the current compose wiring and is recorded here as evidence the D-05/D-07/D-11 code paths fire correctly against the real container — not a defect in this plan, and not something this plan's scope should fix (1205-09 owns it).

## User Setup Required

None — no external service configuration required for this plan itself. (1205-09 will need `docker-compose.yml` updated to pass the new env vars into the `data-service` container so the bootstrap admin actually gets created on the live stack; until then the live container runs with the pre-1205 no-bootstrap-admin state, unaffected by this plan.)

## Next Phase Readiness

- `route_policy.ROUTE_POLICIES`/`RESOURCE_RESOLVERS`/`register_resource_resolver` and `auth.require_principal` are ready for 1205-10's wide route-inventory flip — every remaining route just needs a `RoutePolicy` entry (and a registered resolver for any `resource:<name>` project source) plus `dependencies=[Depends(auth.require_principal)]` on its decorator.
- `auth_routes.py`'s four endpoints are ready for 1205-11's `ui-v2/src/lib/auth.js` rewrite (contract: `{username, isAdmin}` on login, `{username, isAdmin, memberships}` on `/auth/me`, 204s on logout/password-change).
- The startup profile gate is live in the running container (confirmed via rebuild) but currently only ever warns (local profile default with unwired secrets) — 1205-09's compose wiring is a prerequisite for the multi-user refusal path to matter operationally, though it is already fully tested in isolation here.

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*

## Self-Check: PASSED

All created files found on disk (`data-service/route_policy.py`, `data-service/auth_routes.py`, `data-service/tests/test_auth_tracer.py`, `data-service/tests/test_deployment_profile.py`, this SUMMARY.md); commits `0ea20d7` and `8d7176e` found in git log.
