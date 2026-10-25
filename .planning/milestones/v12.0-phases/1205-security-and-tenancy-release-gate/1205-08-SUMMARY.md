---
phase: 1205-security-and-tenancy-release-gate
plan: "08"
subsystem: testing
tags: [pytest, conftest, autouse-fixture, auth-store, test-isolation, service-token, python]

requires:
  - phase: 1205-02
    provides: "auth.py store API (create_user, create_session, set_membership, resolve_*_principal, file globals)"
  - phase: 1205-07
    provides: "require_principal tracer (the fixture is harmless until 1205-10 makes it global)"
provides:
  - "data-service/tests/auth_fixtures.py — make_user, session_cookie_for, admin_session_token, service_headers, connector_token_for, resolve_principal_name, authorize_client (returns an undo callable)"
  - "conftest: pytest_configure store redirect to a dg-auth-test-* temp dir, test-only DG_SERVICE_TOKEN / DG_BOOTSTRAP_ADMIN_*, dg_principal marker, session fixture dg_test_admin, autouse _dg_authorize_module_client"
  - "Service-principal pre-marking of modules that call n8n-only routes (/mcp, /context/*, /llm/generate)"
affects: [1205-10, 1205-14, 1205-09]

tech-stack:
  added: []
  patterns:
    - "Real credentials only: the autouse fixture mints sessions/service headers through auth.*; no dependency override, no env bypass (D-20)"
    - "Principal selection precedence: dg_principal marker > module DG_TEST_PRINCIPAL > admin"
    - "authorize_client returns an undo closure that removes exactly what it added and restores prior header values"

key-files:
  created:
    - data-service/tests/auth_fixtures.py
    - data-service/tests/test_authorized_fixtures.py
  modified:
    - data-service/tests/conftest.py
    - data-service/tests/test_mcp_gh_tools.py
    - data-service/tests/test_dg_context.py
    - data-service/tests/test_llm_gateway.py
    - data-service/tests/test_reasoner.py

key-decisions:
  - "Admin token lives in auth_fixtures.admin_session_token() (lazy user creation + re-validation on each use); the conftest session fixture dg_test_admin just calls it, so a test that revokes the token or swaps the store never poisons later tests"
  - "connectors.CREDENTIALS_FILE is not redirected in pytest_configure (plan scoped the redirect to the four auth files); connector tests already patch it per test"

patterns-established:
  - "Module-level TestClient named `client` is auto-authorised; fixture-built clients (e.g. test_auth_tracer.py) are untouched, so negative-path tests keep their anonymous clients"

requirements-completed: []  # ALGN12-17 / ALGN12-20 span other plans in the phase; not closed by this plan alone

coverage:
  - id: D1
    description: "Auth stores redirected to a session temp dir before any test imports app; test-only service token (48 chars) and bootstrap admin values are policy-compliant; DG_DEPLOYMENT untouched"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py::test_auth_store_is_redirected_out_of_the_live_data_dir -- pass"
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py::test_test_only_secrets_are_policy_compliant_and_deployment_untouched -- pass"
    human_judgment: false
  - id: D2
    description: "Autouse fixture authorises module clients with a real admin session cookie + X-DG-CSRF by default; service/none via module attribute or marker; principal restored for the next test"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py::test_default_principal_is_a_real_admin_session -- pass"
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py::test_cookie_and_headers_reach_the_server_side -- pass"
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py::test_marker_service_puts_service_header_and_no_cookie -- pass"
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py::test_default_is_restored_for_the_next_test_after_an_override -- pass"
    human_judgment: false
  - id: D3
    description: "Helpers mint only real credentials: users/memberships, connector tokens bound to a project, service header; no dependency override anywhere"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_authorized_fixtures.py (17 tests total) -- 17/17 pass host and in-container"
    human_judgment: false

duration: ~35min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 08: Authorised Test Fixtures Summary

**A conftest store redirect plus one autouse fixture gives every module-level `TestClient` a real admin session (or the real service token), with service-only modules pre-marked, so the 1205-10 enforcement flip does not turn the existing suite red.**

## Accomplishments

- `pytest_configure` redirects `auth.USERS_FILE/SESSIONS_FILE/MEMBERSHIPS_FILE/INVITES_FILE` (and `AUTH_DIR`) into `tempfile.mkdtemp(prefix="dg-auth-test-")`, sets test-only `DG_SERVICE_TOKEN` (48 chars) and `DG_BOOTSTRAP_ADMIN_USER/PASSWORD` (12+ chars, passes `classify_secret`), and registers the `dg_principal` marker. `DG_DEPLOYMENT` is never touched.
- `auth_fixtures.py` provides the helpers from the plan's Artifacts table. `authorize_client` accepts `"admin"`, `"service"`, `"none"` or `("user", username)` and returns an undo callable.
- The autouse `_dg_authorize_module_client` applies the principal per test and removes exactly what it added (cookie by name via the cookie jar, the two headers; tolerant of a test that already cleared its cookies).
- Pre-marking: `DG_TEST_PRINCIPAL = "service"` in `test_mcp_gh_tools.py` and `test_dg_context.py`; `@pytest.mark.dg_principal("service")` on `TestGenerate` and the one `/llm/generate` endpoint test in `test_llm_gateway.py`; the in-test fresh client in `test_reasoner.py` is authorised via `auth_fixtures.authorize_client(fresh, "admin")`. No assertion changed.
- 17 self-tests in `test_authorized_fixtures.py`, including a throwaway echo app proving the cookie and headers actually reach the server side.

## Task Commits

1. **Task 1 RED** — `c0b21c4` (test): failing self-test
2. **Task 1 GREEN** — `5f24fe5` (feat): conftest redirect, `auth_fixtures.py`, autouse authoriser
3. **Task 2** — `42cf21d` (test): service pre-marking and fresh-client authorisation

## Verification

| Run | Result |
|---|---|
| `test_authorized_fixtures.py` (host) | 17 passed |
| Full suite, host | 1171 passed, 1 skipped, 4 failed, 25 errors — the 4 failures are the documented `test_dg_context.py` neo4j-hostname tests; the 25 errors are neo4j-hostname integration fixtures (host cannot resolve `neo4j`) |
| Full suite, in-container (rebuilt image, `pytest -q -p no:cacheprovider --ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`) | **1188 passed, 1 skipped, 12 failed** — baseline before this plan was 1171 passed, 1 skipped, 12 failed; +17 = this plan's new tests; the 12 failures are exactly the known environmental set (10 in `test_cq3_attribute_of.py`, `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, `test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`) — no regression |
| `grep -c dependency_overrides` conftest.py / auth_fixtures.py | 0 / 0 |
| `grep -c DG_DEPLOYMENT` conftest.py | 0 |
| `grep -c 'DG_TEST_PRINCIPAL = "service"'` mcp / context | 1 / 1 |

## Deviations from Plan

None on scope. Notes:

- The cookie jar (`client.cookies.set`) delivers the session cookie to the test server in practice (verified by the echo-app test), so the explicit `Cookie` header fallback was **not needed**.
- Docker Desktop was not running at the start of Task 2's in-container verification; it was started, the image rebuilt, and the container restarted once after Neo4j finished booting (first data-service start raced Neo4j and exited). Environmental only.

## Known Stubs

None.

## Threat Flags

None. No app code touched; the fixtures ship in the image but only mint credentials through the real store.

## Notes for downstream plans

- The admin cookie is minted in the conftest-redirected store at test setup. A test that later monkeypatches `auth.USERS_FILE` to its own tmp store will hold a cookie unknown to that store; `admin_session_token()` re-validates on the next authorisation, but 1205-10 should re-authorise inside such tests (only relevant once those routes are enforced).
- `connectors.CREDENTIALS_FILE` is intentionally not redirected globally; tests using `connector_token_for` should patch it (as `test_authorized_fixtures.py` does).

## Self-Check: PASSED

Created files found (`auth_fixtures.py`, `test_authorized_fixtures.py`, this SUMMARY); commits `c0b21c4`, `5f24fe5`, `42cf21d` in git log.
