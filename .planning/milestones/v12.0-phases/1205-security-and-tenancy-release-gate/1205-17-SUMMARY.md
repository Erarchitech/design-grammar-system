---
phase: 1205-security-and-tenancy-release-gate
plan: "17"
subsystem: data-service tenancy tests
tags: [pytest, tenancy, bola, route-policy, cross-project, d-15, d-18, d-19, python]

requires:
  - phase: 1205-10
    provides: "completed ROUTE_POLICIES table and the credential/note/execution resource resolvers"
  - phase: 1205-12
    provides: "project tenancy, GET /projects filtering"
  - phase: 1205-14
    provides: "owner-bound executions (record_execution_owner) and the final 82-row table"
provides:
  - "data-service/tests/test_cross_project_matrix.py: D-15 cross-project matrix generated from ROUTE_POLICIES (50 path/body/query rows) plus resource, execution, principal and listing cases, all under both DG_DEPLOYMENT profiles"
affects: [1205-19]

tech-stack:
  added: []
  patterns:
    - "Matrix generated from the policy table at collection time; new scoped rows are covered without editing the test"
    - "Positive controls call auth.require_principal directly on a constructed Starlette Request (no handler, no Neo4j)"
    - "Module-scoped real-store world (scrypt is slow); function-scoped offline-graph and profile fixtures"

key-files:
  created:
    - data-service/tests/test_cross_project_matrix.py
  modified: []

key-decisions:
  - "Tasks 1 and 2 both live in one file (as the plan specifies) and were committed together in one commit rather than two"
  - "Extra coverage beyond the plan: an editor on owner-only rows (downgrade), B2 (P2 editor) and V as positive controls, an admin as a non-initiator on executions, body-sourced rows also probed with a disagreeing query project"
  - "_call_dependency looks up the registered route (APIRoute, or ctx.starlette_route / original_route for FastAPI 0.141 wrapped routers) and falls back to a path-only stand-in because require_principal reads only route.path"

requirements-completed: []  # ALGN12-20 / GATE12-05 also need 1205-19 (multi-user container re-run)

coverage:
  - id: D1
    description: "D-15: every path/body/query scoped row denies A(P1) asking P2, a P1 connector asking P2, roles below the row minimum, and disagreeing project locations; positive controls pass"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cross_project_matrix.py (887 cases host and container)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-15: id-only credential/note routes and owner-bound executions answer the same 404 for another project's or another user's resource with no side effect"
    requirement: "ALGN12-20"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cross_project_matrix.py::TestResourceBola, ::TestExecutionOwnerBinding"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-18/D-19: every case identical under DG_DEPLOYMENT local and multi-user"
    requirement: "GATE12-05"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cross_project_matrix.py (profile fixture params)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 17: Cross-Project Matrix Summary

**A 887-case D-15 matrix, generated from the 82-row ROUTE_POLICIES table, proves cross-project, cross-role, mismatch, id-only (BOLA) and owner-bound-execution access fail closed under both deployment profiles, with positive controls and mutation-verified sensitivity.**

## What was built

`data-service/tests/test_cross_project_matrix.py` (662 lines), one file, no production code changed.

World (module-scoped, real auth store and connectors API, no dependency override): A editor of P1, V viewer of P1, B owner of P2, B2 editor of P2, an admin, and a connector token T1 bound to P1.

Generated from the 50 scoped rows (project source path, body or query), giving 354 matrix cases per profile:

| Category | Cases | Expectation |
|---|---|---|
| forbidden | 50 | A with P2 in the declared location -> 403 PROJECT_FORBIDDEN |
| connector | 50 | T1 with P2 -> 403 PROJECT_FORBIDDEN on connector rows, PRINCIPAL_NOT_PERMITTED elsewhere |
| downgrade | 29 | V on editor/owner rows, A on owner rows -> 403 PROJECT_FORBIDDEN |
| mismatch | 53 | path/query/body disagreeing project -> 403 PROJECT_MISMATCH |
| positive | 172 | A (P1 viewer/editor rows), V (viewer rows), B and B2 (P2), T1 (P1 connector rows) pass `require_principal` |

Other classes: `TestResourceBola` (P2 credential 404 and stays unrevoked, P2 owner 204, P1 connector token 403, P2 note GET/PUT/DELETE 404 identical to an unknown id with only the resolver reading and no write), `TestExecutionOwnerBinding` (A, V, B2 same-project, admin all 404 identical to unknown; B 200 `{"status":"running"}`; result payload never served to B2), per-row service-token-on-user-route and session-on-service-route sweeps, and `TestListingFilters` (`GET /projects` query restricted to the caller's projects; `GET /connectors` shows no P2 credential to A).

`test_matrix_is_not_vacuous` asserts at least 40 scoped rows, per-category coverage of exactly the scoped key set, and at least 3 cases per row.

## Verification

- Host: `python -m pytest data-service/tests/test_cross_project_matrix.py` -> 887 passed (7 s). Task 1 filter (`-k "not resource and not execution"`) -> 863 passed, 24 deselected. Collected 887, versus the acceptance floor of 2 x 50 x 2 = 200.
- Container (rebuilt image): `tests/test_cross_project_matrix.py` -> 887 passed.
- Full in-container suite: **2986 passed, 1 skipped, 12 failed** (8 deselected as live). Baseline was 2062 passed / 1 skipped / 12 known environmental failures; the 12 failures are the identical set (10 test_cq3_attribute_of.py, test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields, test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input). The +924 passed are 887 from this file plus 37 from the 1205-15/16 tests now in the image; none of those failed in-container, including test_config_js_no_secrets.py.
- Mutation checks (auth.py restored afterwards; `git status` clean for it): forcing `authorized = True` for users failed 164 cases; disabling the PROJECT_MISMATCH branch failed 106 cases. The matrix is therefore not vacuous.

## Deviations from Plan

None on behaviour. Process note: the two tasks were committed together (7cbb97e) because both edit the single file the plan lists.

## Flagged assumption (carried from plan)

Routes whose project cannot be expressed as path/body/query/resource are covered only by the resource, execution, `GET /projects` and `GET /connectors` cases plus the 1205-10 sweeps; a future route of a new shape is caught by the route-inventory completeness test, not this matrix (T-1205-17-04, accepted).

## Threat Flags

None.

## Known Stubs

None.

## Commits

- 7cbb97e test(1205-17): add D-15 cross-project matrix over all scoped routes, resources, executions and listings

## Self-Check: PASSED

- data-service/tests/test_cross_project_matrix.py exists and is committed (7cbb97e).
- Host and in-container runs green; full suite failure set equals the documented baseline.
