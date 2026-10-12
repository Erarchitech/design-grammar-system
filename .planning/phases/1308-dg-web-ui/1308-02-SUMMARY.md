---
phase: 1308-dg-web-ui
plan: "02"
subsystem: data-service
tags: [fastapi, route-policy, security-boundary, membership, neo4j]
requires: []
provides:
  - "PUT /projects/{project}/members/{username} role change with last-owner protection"
  - "GET /projects/{project}/summary landing counts (counts only)"
  - "_last_owner_guard shared with POST /auth/invites"
affects: [1308-10, 1308-11, 1308-13]
tech-stack:
  added: []
  patterns: ["route-policy row + spec row + API row in the same commit (D-41)", "file-backed grant stores counted via _public active flag"]
key-files:
  created:
    - data-service/tests/test_member_roles.py
    - data-service/tests/test_project_summary.py
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - spec/SECURITY-BOUNDARY.md
    - spec/API.md
    - data-service/tests/test_route_inventory.py
key-decisions:
  - "Summary read uses read_single (the module helper), not a raw driver session, so tests monkeypatch it like the other graph routes"
  - "Unparseable path username answers MEMBER_NOT_FOUND 404 rather than a new USERNAME_INVALID code (no probe surface)"
  - "LAST_OWNER, MEMBER_NOT_FOUND and ROLE_INVALID added to SECURITY-BOUNDARY section 3.4 (they were absent)"
requirements-completed: [WEBUI-03, WEBUI-05, WEBUI-10]
duration: 25min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 02: Member role change and project summary routes Summary

Two data-service routes for the Web UI: owner/admin role change with a server-side last-owner invariant under `auth._STORE_LOCK`, and a project-scoped counts-only landing summary, each with its policy row, spec rows, API doc row and tests.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. PUT members role change | 6b68f40 | route, `_last_owner_guard` (reused by `create_project_invite`), `MemberRoleRequest`, policy row, spec rows, 3 error-table rows, API row, inventory 110, 15 tests |
| 2. GET summary | 4cf4fda | `PROJECT_SUMMARY_QUERY`, `get_project_summary`, policy row, spec row, API row, inventory 111, 9 tests |

## Verification (real output)

- `pytest test_project_summary.py test_member_roles.py test_project_routes.py test_route_inventory.py test_security_boundary_spec.py -q`: 1024 passed.
- Also green: test_cross_project_matrix, test_cypher_project_scope, test_error_responses, test_graph_routes, test_connector_access (1345 passed).
- RED observed first for both test files (15 failed with 405; 8 failed before the constant/route existed).
- `grep -c "_last_owner_guard("` app.py = 3; `test_policy_table_size` asserts 111.
- Not run: the full data-service suite and any live Docker check (not authorized in this plan).

## Deviations from Plan

None in behaviour. Notes:
- Task 1 spec edits to SECURITY-BOUNDARY section 3.4 added three error rows (plan said "if absent"; all three were absent).
- connector_access.py and degram_grants.py untouched (confirmed by `git status`).
- The plan text says "run the query with `with driver.session()` as the rules route does"; the rules route actually goes through `read_many`, so `read_single` was used for the same effect.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat register (T-1308-02-01..05 each covered by a test: 403 for editor/viewer/other-project owner, LAST_OWNER incl. self-demotion and admin, missing CSRF header, key-set and leak assertions on the summary, parameter-bound project).

## Self-Check: PASSED

- FOUND: data-service/tests/test_member_roles.py, data-service/tests/test_project_summary.py
- FOUND commits 6b68f40, 4cf4fda
