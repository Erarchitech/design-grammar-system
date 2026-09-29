---
phase: 1205-security-and-tenancy-release-gate
plan: "10"
subsystem: auth
tags: [fastapi, deny-by-default, route-policy, bola, resource-resolver, route-inventory, tenancy, python]

requires:
  - phase: 1205-03
    provides: "Grasshopper C# publish clients send the dgc_ token"
  - phase: 1205-07
    provides: "auth.require_principal, route_policy tracer seed, resolver registry"
  - phase: 1205-08
    provides: "authorised test fixtures (autouse admin/service principal, make_user, session_cookie_for, connector_token_for)"
provides:
  - "route_policy.ROUTE_POLICIES: all 67 routes classified; register_resource_resolver(name, resolve, not_found)"
  - "Global deny-by-default: every data-service route registered on APIRouter(dependencies=[Depends(auth.require_principal)]), included as the last statement of app.py"
  - "Resource resolvers (credential, note, execution) with no-leak 404 semantics"
  - "EXECUTION_OWNERS + record_execution_owner (1000-entry cap) for the 1205-14 relay"
  - "test_route_inventory.py: 588 tests (bidirectional completeness, dependency presence, denial sweeps x 2 profiles)"
affects: [1205-11, 1205-12, 1205-14, 1205-16, 1205-18]

tech-stack:
  added: []
  patterns:
    - "Policy table + bidirectional inventory test: a route without a row, or a row without a route, fails the suite"
    - "Resource routes: resolver derives the project server-side; unknown and unauthorised resources raise the SAME not-found"
    - "Inventory helper flattens both FastAPI route shapes (plain APIRoute in app.routes vs lazy _IncludedRouter in 0.141)"

key-files:
  created:
    - data-service/tests/test_route_inventory.py
  modified:
    - data-service/route_policy.py
    - data-service/auth.py
    - data-service/app.py
    - data-service/connectors.py
    - data-service/tests/test_cg_recognition.py
    - data-service/tests/test_cg_structure_checks.py
    - data-service/tests/test_connectors.py
    - data-service/tests/test_dg_knowledge.py
    - data-service/tests/test_deployment_profile.py
    - data-service/tests/test_designstate_capture.py

key-decisions:
  - "Hidden-path skip in ingest_folder is measured from the repository root, not the requested folder, so path='.secrets' is refused too (a superset of the plan's 'relative to the validated root')"
  - "project_source 'filtered' (GET /connectors) skips project authorisation in require_principal; the handler filters by membership"
  - "An execution whose owner record has no project resolves to 404 (the 1205-14 relay must always record a project)"
  - "Unknown connector id on DELETE credentials now answers CREDENTIAL_NOT_FOUND (resolver runs first) instead of CONNECTOR_NOT_FOUND: no-leak"

patterns-established:
  - "Resolver contract: resolve(request) -> project | None (sync or async); None or any authorisation failure on a resource:* route raises the paired not_found()"

requirements-completed: []  # ALGN12-17 and ALGN12-20 span other plans (12, 14, 15, 16, 18); not closed by this plan alone

coverage:
  - id: D1
    description: "D-03: every data-service route runs auth.require_principal via one router-level dependency; the last statement of app.py is app.include_router(router)"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py::TestInventory::test_every_api_route_has_require_principal -- pass"
    human_judgment: false
  - id: D2
    description: "D-14: the (method, template) set registered on the app equals ROUTE_POLICIES in both directions; comparator reports an induced mismatch; docs routes exist only in the local profile"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py::TestInventory -- 7/7 pass host and in-container"
    human_judgment: false
  - id: D3
    description: "D-14/D-19 denial sweeps, one case per policy row per profile: no credential 401; service token on non-service 403 PRINCIPAL_NOT_PERMITTED; user session on service route 403; non-admin on admin route 403 ADMIN_REQUIRED; no membership 403 PROJECT_FORBIDDEN or the resource 404; viewer on editor/owner route 403; connector bound elsewhere 403; connector on non-connector route 403; body route without project 403 PROJECT_REQUIRED"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py -- 588 passed (host and in-container)"
    human_judgment: false
  - id: D4
    description: "Removed routes: POST /create_node/ and GET /execution-result/latest/{workflow} (and WORKFLOW_STATUS) no longer exist"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py::TestInventory::test_removed_routes_are_gone -- pass"
      - kind: integration
        ref: "live: POST /create_node/ -> 404, GET /execution-result/latest/rules-ingest -> 404"
        status: pass
    human_judgment: false
  - id: D5
    description: "ALGN12-20 no-leak: credential, note and execution ids of another project (or another user) answer the identical 404 as unknown ids; execution results are owner-bound, including against other members and admins"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py::TestResourceNotFoundSemantics -- 7/7 pass"
    human_judgment: false
  - id: D6
    description: "T-1205-10-05: folder ingest skips markdown below any dot-prefixed path segment and reports reason hidden-path; ingest is admin-only"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_knowledge.py::TestIngestFolderHiddenPaths -- 3/3 pass"
    human_judgment: false
  - id: D7
    description: "T-1205-10-06: GET /connectors lists only credentials of the caller's member projects (admin sees all) and derives status/last-connection from those credentials only"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_connectors.py::TestOverviewProjectFilter -- 5/5 pass"
    human_judgment: false

duration: ~20min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 10: Whole-API Enforcement Flip and D-14 Inventory Summary

**All 67 data-service routes are now classified in `route_policy.ROUTE_POLICIES` and registered behind one router-level `require_principal` dependency; the two unsalvageable routes are deleted, id-only routes resolve their project from the stored resource with no-leak 404s, and a 588-case inventory/denial suite proves it under both deployment profiles.**

## Accomplishments

- **Classification (Task 1):** `ROUTE_POLICIES` holds exactly the 67 rows of the plan table (`len == 67` asserted). The resolver registry now stores `(resolve, not_found)` pairs. `require_principal` sets `request.state.principal` before a resolver runs, converts an unknown resource *and* any authorisation failure on a `resource:*` route into the resource's own not-found, and treats project source `filtered` as "no project authorisation" (the handler filters).
- **Removals:** `POST /create_node/` (label interpolated into Cypher, no callers) and `GET /execution-result/latest/{workflow}` plus every `WORKFLOW_STATUS` write are gone.
- **Owner-bound executions:** `EXECUTION_OWNERS` / `_EXECUTION_OWNERS_LOCK` / `record_execution_owner` (oldest-evicted at 1000). `GET /execution-result/{id}` reaches its handler only for the user who started the execution; everyone else (other members, admins, unknown ids) gets `404 EXECUTION_NOT_FOUND`.
- **Resolvers:** `credential` (via `connectors.load_credentials`, legacy records read as `default-project`), `note` (one bound-parameter `read_single`, run in a threadpool), `execution`.
- **Global flip (Task 2):** all 63 `@app.<method>` decorators became `@router.<method>` on `APIRouter(dependencies=[Depends(auth.require_principal)])`; `app.include_router(router)` is the last statement of `app.py`; the tracer route's redundant per-route dependency was removed.
- **Inventory suite:** dependency presence, bidirectional completeness, docs-routes-only-in-local, induced-mismatch comparator, and 11 denial sweeps parametrised per policy row per profile.
- **Hardening (Task 3):** folder ingest skips dot-prefixed path segments (reporting `skippedHidden` and a capped `skippedFiles` list with reason `hidden-path`); `GET /connectors` filters by membership; `get_connector_overview(now=None, *, projects=None)` drops out-of-set credentials before deriving status.

## Task Commits

1. **Task 1: classification, resolvers, route removals** - `4e7a632` (feat)
2. **Task 2: global flip and D-14 sweeps** - `865e056` (feat)
3. **Task 3: hidden-path ingest, filtered overview, suite fallout** - `e80dab8` (feat)

## Verification

| Run | Result |
|---|---|
| `test_route_inventory.py` (host) | 588 passed |
| `test_route_inventory.py` (in-container, FastAPI 0.141.1) | 588 passed |
| `test_auth_tracer.py` (host) | 34 passed |
| Full suite, host | 1787 passed, 1 skipped, 4 failed, 25 errors: the 4 failures are the documented `test_dg_context.py` neo4j-hostname tests; the 25 errors are neo4j-hostname integration fixtures |
| Full suite, in-container (rebuilt image, `pytest -q -p no:cacheprovider --ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`) | **1804 passed, 1 skipped, 12 failed** vs baseline 1207 passed, 1 skipped, 12 failed. +597 = 588 inventory + 3 ingest + 5 overview + 1 split credential test. The 12 failures are exactly the known environmental set (10 `test_cq3_attribute_of.py`, `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, `test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`). No regression |
| `git diff data-service/route_policy.py` during Task 3 | empty (no policy touched by fallout) |
| `grep -c create_node app.py` / `execution-result/latest` / `register_resource_resolver` | 0 / 0 / 3 |
| `grep -cE "^@app\.(get\|post\|put\|delete)\(" app.py` | 0; last line of app.py is `app.include_router(router)` |

### Live-stack probe (rebuilt data-service, DG_DEPLOYMENT=local)

`GET /` 200; `GET /connectors`, `/llm/settings`, `/auth/me`, `/validation/runs/P1`, `/execution-result/x`, `/knowledge/notes/P1` all 401 unauthenticated; `POST /connectors/heartbeat` without a token 401; `GET /mcp` 405 (POST-only route); `POST /create_node/` and `GET /execution-result/latest/rules-ingest` 404; `/docs` and `/openapi.json` 200 (local profile only, as designed). All compose containers Up.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Inventory helper failed under the container's FastAPI 0.141.1**
- **Found during:** Task 3 in-container run (host FastAPI is 0.135.1)
- **Issue:** the newer FastAPI wraps an included router in a lazy `_IncludedRouter`, so `isinstance(route, APIRoute)` over `app.routes` found nothing and 3 inventory tests failed in-container only.
- **Fix:** `_flat_routes()` flattens both shapes (`effective_route_contexts()` for the wrapped form, which carries the merged path and merged dependant, so router-level dependency presence is still proven). A `>= 60` sanity assertion guards against an empty walk.
- **Files modified:** `data-service/tests/test_route_inventory.py`
- **Commit:** `e80dab8`

**2. [Rule 2 - Missing critical] Hidden-path check measured from the repo root**
- **Issue:** measured only against the requested folder, `path=".secrets"` would have ingested `.secrets/*.md`.
- **Fix:** components are taken relative to `KNOWLEDGE_REPO_ROOT` (a superset of the plan wording). A test covers the direct-hidden-folder request.
- **Commit:** `e80dab8`

### Test-side fallout (recorded per plan; no policy changed)

- `test_connectors.py`: credential-create bodies now carry `project`; `test_create_without_body` became `..._fails_closed_project_required` (403 PROJECT_REQUIRED) plus a project-only-body case; the "missing project defaults to default-project" heartbeat test mints its legacy credential directly via `connectors.create_credential`; `test_revoke_unknown_connector_404` now expects `CREDENTIAL_NOT_FOUND` (resolver runs before the handler, no-leak).
- `test_cg_recognition.py`: four `/computgraph/recognize` calls now send `"project": "P1"`.
- `test_cg_structure_checks.py`: missing-project validate call is now rejected by the dependency (403 PROJECT_REQUIRED) before FastAPI's 422; the "never opened a session" intent is unchanged.
- `test_deployment_profile.py`, `test_designstate_capture.py`: the lifespan liveness probe moved from `GET /connectors` to the public `GET /`.
- `test_dg_knowledge.py`: the plan expected note-route fakes to need a project lookup; no note/ingest route tests existed, so only the new hidden-path tests were added. Note-resolver behaviour is covered in `test_route_inventory.py` with a fake `read_single`.

## Expected mid-phase breakage (recorded, not accommodated)

- **Live n8n -> data-service calls will 401.** The repo workflows send the service-token header (1205-05) but LIVE n8n still runs the old published workflows until plan 1205-18. `/mcp`, `/llm/generate`, `/context/*` and `POST /execution-result` are service-only; enforcement was not weakened.
- **ui-v2 polling of the removed route.** `ui-v2/src/lib/graphApi.js:366` (and legacy `graph-viewer/index.html`, `test/test_spec_llm.py`) poll `GET /execution-result/latest/{workflow}`, which no longer exists. The replacement is the owner-bound `GET /execution-result/{executionId}` fed by `record_execution_owner` in the 1205-14 relay; UI migration belongs to 1205-11/14. `README.md:172-173` and `spec/API.md:29` still document the removed route (1205-16 spec pass).
- The V2 UI has no login yet (1205-11), so its data-service calls 401 until that plan lands.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. New surface (`EXECUTION_OWNERS`) is in-memory, capped, and only reachable through the owner-bound route.

## Notes for downstream plans

- 1205-14 must call `app.record_execution_owner(execution_id, username, project, workflow)` with a non-empty project, or the owner's own poll answers 404.
- 1205-12 / 1205-14 add their own rows to `ROUTE_POLICIES`; the completeness test will fail until they do.
- Any new route must be declared on `router` (not `app`) and get a policy row.

## Self-Check: PASSED

Created/modified files found on disk (`data-service/tests/test_route_inventory.py`, `route_policy.py`, `auth.py`, `app.py`, `connectors.py`, this SUMMARY); commits `4e7a632`, `865e056`, `e80dab8` in git log.
