---
phase: 1205-security-and-tenancy-release-gate
plan: "12"
subsystem: auth
tags: [fastapi, tenancy, invitations, named-endpoints, d-06, parameterised-cypher, route-policy, python]

requires:
  - phase: 1205-10
    provides: "global deny-by-default router, ROUTE_POLICIES, D-14 inventory test"
  - phase: 1205-11
    provides: "UI clients already calling these endpoints (contract table in 1205-11-PLAN.md)"
provides:
  - "GET/POST /projects, GET/DELETE /projects/{project}/members[...], POST /auth/invites, POST /auth/accept-invite (invitation-only onboarding, no self-registration)"
  - "Seven named graph endpoints with fixed parameterised Cypher: /graph/{project}, claim-untagged, node property, /rules/{project}, /rules/{project}/{rule_id}, entity statuses, accepted candidates"
  - "auth_routes.set_session_cookie / clear_session_cookie shared by login and accept-invite"
  - "auth.list_all_member_projects (admin project listing)"
  - "ROUTE_POLICIES now 80 rows (67 + 13)"
affects: [1205-13, 1205-14, 1205-15, 1205-16, 1205-18]

tech-stack:
  added: []
  patterns:
    - "Named endpoint = one module-level Cypher constant + bound parameters; tests assert the project literal never appears in captured statement text"
    - "write_single(query, params): session run returning one row, used for writes that return the updated record"

key-files:
  created:
    - data-service/tests/test_project_routes.py
    - data-service/tests/test_graph_routes.py
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/auth.py
    - data-service/auth_routes.py
    - data-service/tests/test_route_inventory.py

key-decisions:
  - "GET /projects uses one fixed statement with `$projects IS NULL OR n.project IN $projects`: a member binds their membership list, an admin binds null; members with zero graph nodes still list (nodes 0); an empty membership list issues no query"
  - "Invite accept order: password policy (422, code untouched) -> consume code -> create_user; any failure after consume, including a now-existing username, is the single generic 400 INVITE_INVALID, and an existing account is never modified"
  - "Inviting an existing user who is the only owner to a non-owner role answers 409 LAST_OWNER (set_membership upsert would otherwise demote the last owner)"
  - "POST /auth/invites returns expiresAt as ISO-8601 UTC (contract left the format open; epoch seconds would be misread by JS Date)"
  - "PROPERTY_VALUE_INVALID (422) added for object/array/non-finite values; USERNAME_INVALID (422) added for a malformed invitee username"

patterns-established:
  - "Tenancy administration lives in app.py on the enforcing router; every new route needs a ROUTE_POLICIES row"

requirements-completed: []  # ALGN12-17 / ALGN12-18 span 1205-13/14/15/16/18; not closed by this plan alone

coverage:
  - id: D1
    description: "D-06: nine former browser Cypher sites served by seven named endpoints plus GET /projects, each a fixed statement whose only variables are bound parameters; no endpoint accepts statement text"
    requirement: "ALGN12-18"
    verification:
      - kind: unit
        ref: "data-service/tests/test_graph_routes.py::TestEveryEndpoint::test_project_travels_only_as_a_parameter -- 7/7 pass"
      - kind: unit
        ref: "data-service/tests/test_project_routes.py::TestListProjects, ::TestCreateProject (query bound-parameter assertions) -- pass"
    human_judgment: false
  - id: D2
    description: "T-1205-12-01: an invite can never take over an existing account (existing users get membership at invite time; accept refuses an existing username; password hash unchanged)"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_project_routes.py::TestAcceptInvite::test_code_for_a_username_that_now_exists_never_touches_that_account -- pass"
    human_judgment: false
  - id: D3
    description: "D-02/D-05: project registration is first-come with 409 PROJECT_NAME_UNAVAILABLE for any membership or graph-node reuse; names validated (422); no self-registration route exists"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_project_routes.py::TestCreateProject, ::TestNoOpenRegistration -- pass"
    human_judgment: false
  - id: D4
    description: "D-02: member administration is owner-only; removing the last owner is 409 LAST_OWNER; a removed member loses access on the next request"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_project_routes.py::TestMembers -- pass"
    human_judgment: false
  - id: D5
    description: "T-1205-12-03/04: property edit cannot move a node across tenants (project/graph keys 403, id AND project match, 404 without existence leak); claim-untagged matches project IS NULL only and never mentions default-project"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_graph_routes.py::TestNodeProperty, ::TestClaimUntagged -- pass"
    human_judgment: false
  - id: D6
    description: "Every one of the 13 new routes is classified and enforced (P1-only user on P2 -> 403 PROJECT_FORBIDDEN; anonymous -> 401)"
    requirement: "ALGN12-17"
    verification:
      - kind: unit
        ref: "data-service/tests/test_route_inventory.py (data-driven, 80 rows) and test_graph_routes.py::TestEveryEndpoint -- pass host and in-container"
    human_judgment: false
  - id: D7
    description: "Live behaviour with the UI against the rebuilt stack (login, project create, invite round trip)"
    requirement: "ALGN12-17"
    verification: []
    human_judgment: true
    note: "Deferred to 1205-13 (login/members UI) and 1205-18 (live smoke). Unauthenticated live probe of the rebuilt container: GET /projects, /graph/x, /rules/x 401; POST /auth/register 404; POST /auth/accept-invite without CSRF header 403."

duration: ~30min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 12: Project Tenancy, Invitations and Named Graph Endpoints Summary

**The browser now has server-side homes for everything it used to do with raw Cypher: seven fixed, bound-parameter graph endpoints plus a membership-scoped `/projects` listing, and tenancy is administrable without self-registration (project creation, owner-only member management, single-use invitations that can never take over an existing account).**

## Accomplishments

- **Task 1 (projects, memberships, invitations):** `GET /projects` (member: own memberships with role and node count; admin: graph projects union membership projects as owner), `POST /projects` (pattern-validated, existence via bound `$project`, claim under the auth store lock, 409 on reuse), `GET`/`DELETE /projects/{project}/members[...]` (owner-only, LAST_OWNER/MEMBER_NOT_FOUND), `POST /auth/invites` (existing user added directly, new username gets a `dgi_` code, role must be viewer/editor/owner) and public `POST /auth/accept-invite` (password policy before consuming the code, generic INVITE_INVALID, cookie via the shared helper).
- **Task 2 (named graph endpoints):** `/graph/{project}` (2000/8000 limits, both relationship endpoints filtered by `$project`), `claim-untagged` (`n.project IS NULL` only), node property (validated key, protected `project`/`graph`, id AND project, 404 without leak), `/rules/{project}`, `/rules/{project}/{rule_id}`, entity statuses, accepted candidates (`ruleId` bound, null when omitted). Results pass through `normalize_value` plus a JSON-safe fallback for driver temporal types.
- **Policy:** 13 rows added (`ROUTE_POLICIES` 67 -> 80). The D-14 completeness test needed no logic change.

## Task Commits

1. **Task 1: projects, memberships and invitations** - `779ea8a` (feat)
2. **Task 2: seven named graph endpoints** - `1f33a90` (feat)

## Verification

| Run | Result |
|---|---|
| Task 1: `test_project_routes.py` + `test_route_inventory.py` + `test_auth_tracer.py` + `test_auth_store.py` (host) | 759 passed |
| Task 2: `test_graph_routes.py` + `test_project_routes.py` + `test_route_inventory.py` (host) | 781 passed |
| `python -c "... assert len(r.ROUTE_POLICIES)==80"` | ok |
| `grep -c register data-service/auth_routes.py` | 0; `POST /auth/register` live -> 404 |
| Full suite in-container (rebuilt image, `pytest -q -p no:cacheprovider --ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`) | **1997 passed, 1 skipped, 12 failed** vs baseline 1804 passed, 1 skipped, 12 failed (+193 = the two new test files; 8 live-marked deselected as before). The 12 failures are exactly the known environmental set (10 `test_cq3_attribute_of.py`, `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, `test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`). No regression |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_policy_table_size` hardcodes the row count**
- **Found during:** Task 1 verification
- **Issue:** the plan states the inventory test is "data-driven ... without edits", but `test_route_inventory.py::TestInventory::test_policy_table_size` asserts `len(ROUTE_POLICIES) == 67` and failed once rows were added.
- **Fix:** bumped to 73 in Task 1 and 80 in Task 2 (the counts the plan's acceptance criteria name). All completeness/denial logic remains data-driven.
- **Files modified:** `data-service/tests/test_route_inventory.py`
- **Commits:** `779ea8a`, `1f33a90`

**2. [Rule 2 - Missing critical] Last-owner protection also on the invite path**
- **Issue:** `POST /auth/invites` for an existing user calls `set_membership`, an upsert; an owner inviting themselves as viewer would demote the only owner and orphan the project, bypassing the DELETE-side LAST_OWNER guard.
- **Fix:** same LAST_OWNER 409 check under the store lock; tested.
- **Commit:** `779ea8a`

**3. [Rule 3 - Blocking] `auth.list_all_member_projects()` added**
- **Issue:** the admin listing needs every membership project; `auth.py` had no public accessor (only the private `_load`). `auth.py` is not in the plan's `files_modified`.
- **Fix:** an 8-line read-only helper beside `list_member_projects`.
- **Commit:** `779ea8a`

**4. [Rule 2 - Missing critical] Extra validation codes**
- `USERNAME_INVALID` (422) for a malformed invitee username (else `create_invite` would persist an un-acceptable invite) and `PROPERTY_VALUE_INVALID` (422) for object/array/NaN/Infinity property values (the plan named the 422 but not a code).

## Observations for downstream plans

- **claim-untagged and shared ontology nodes (1205-16 / 1205-14):** the plan-mandated statement `MATCH (n) WHERE n.project IS NULL SET n.project = $project` claims EVERY untagged node in the database for the calling editor's project, including any OntoGraph node (Class/ObjectProperty/DatatypeProperty) that lacks a `project` property. This plan follows the plan text literally; if the ontology layer is loaded untagged in a live database, the spec pass should decide whether to exclude those labels. Also, per 1205-11's note, ingest that still writes `default-project` will not be claimed (by design), so the 1205-14 relay must run ingest under the caller's real project.
- **`expiresAt` format:** ISO-8601 UTC string (`2026-...Z`); 1205-13's members panel can display it directly.
- **Race on POST /projects:** the graph-existence read happens before the store lock; the membership half of the check is atomic under the lock (as specified). A node with that project name appearing between the read and the claim is accepted as a residual.
- T-1205-12-06/07 (project-name enumeration via 409; invite brute force, rate limiting deferred) are recorded as accepted in the plan and belong in the 1205-16 residuals list.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register.

## Self-Check: PASSED

Files on disk: `data-service/tests/test_project_routes.py`, `data-service/tests/test_graph_routes.py`, `data-service/app.py`, `data-service/route_policy.py`, `data-service/auth.py`, `data-service/auth_routes.py`, `data-service/tests/test_route_inventory.py`; commits `779ea8a` and `1f33a90` in git log.
