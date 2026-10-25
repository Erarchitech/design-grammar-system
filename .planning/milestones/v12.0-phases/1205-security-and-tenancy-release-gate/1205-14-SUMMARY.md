---
phase: 1205-security-and-tenancy-release-gate
plan: "14"
subsystem: data-service n8n boundary
tags: [fastapi, n8n-relay, service-token, tenancy, cypher-scope, d-04, d-08, route-policy, python]

requires:
  - phase: 1205-05
    provides: "n8n Verify Relay Token node checking X-DG-Service-Token against DG_SERVICE_TOKEN"
  - phase: 1205-06
    provides: "dg_context.check_query_project_scope / find_foreign_project_entities / find_cross_project_key_collisions / generate_validated_cypher(project=)"
  - phase: 1205-10
    provides: "EXECUTION_OWNERS / record_execution_owner and the owner-bound `execution` resolver"
  - phase: 1205-12
    provides: "project tenancy; claim-untagged claims only project IS NULL nodes"
provides:
  - "fire_n8n_webhook(webhook_path, body, timeout=15) -> executionId; call_n8n_sync now calls it"
  - "POST /workflows/rules-ingest (editor) and POST /workflows/graph-query (viewer) -> 202 {status, executionId}, owner recorded before the 202"
  - "/mcp neo4j_query project-scope enforcement before (static) and after (result) execution; neo4j_schema no longer lists projects"
  - "/context/generate-cypher project requirement, project pass-through, and Rule_Id/Atom_Id collision -> valid:false"
  - "ROUTE_POLICIES now 82 rows (80 + 2)"
affects: [1205-15, 1205-16, 1205-17, 1205-18]

tech-stack:
  added: []
  patterns:
    - "Relay body is built from the validated Pydantic model only; extra request fields are dropped by the model"
    - "Guard functions run in the route, error bodies carry violation codes and never another project's name or data"
    - "Fail-closed on infrastructure failure: unset token -> 503, collision check unreachable -> 503"

key-files:
  created:
    - data-service/tests/test_workflow_relay.py
    - data-service/tests/test_mcp_project_scope.py
  modified:
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/test_route_inventory.py
    - data-service/tests/test_dg_context.py

key-decisions:
  - "Relay webhook paths are dg/rules-ingest and dg/graph-query (the n8n webhook paths in the workflow JSON); body fields rules_text/project/project_name/cypher_prompt=false and prompt/project/project_name/cypher_prompt=false"
  - "Missing parameters.project on /mcp answers 400 QUERY_PROJECT_REQUIRED (message contains 'project is required'); the scope check runs before the read-only guard, both before any session opens"
  - "The cross-project key collision check in generate-cypher fails closed (503 KEY_COLLISION_CHECK_UNAVAILABLE) if Neo4j cannot be reached, instead of returning unchecked Cypher that the workflow would write"
  - "fire_n8n_webhook maps URLError/timeout/OSError to RELAY_UNAVAILABLE 503 so the relay never leaks a raw connection error"

requirements-completed: []  # ALGN12-17 / ALGN12-18 span 1205-15/16/18; not closed by this plan alone

coverage:
  - id: D1
    description: "D-08: relay routes fire the n8n webhooks over the internal network with the authorised project; 202 {status: accepted, executionId}"
    requirement: "ALGN12-17"
    verification:
      - kind: test
        ref: "data-service/tests/test_workflow_relay.py::TestRelayRoutes"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-04: every data-service to n8n request carries X-DG-Service-Token; unset token 503 RELAY_UNAVAILABLE with no network call; ack without executionId 502 RELAY_NO_EXECUTION_ID"
    requirement: "ALGN12-17"
    verification:
      - kind: test
        ref: "data-service/tests/test_workflow_relay.py::TestFireN8nWebhook, ::TestCallN8nSync"
        status: pass
    human_judgment: false
  - id: D3
    description: "Research gap 5: only the initiating user polls GET /execution-result/{id}; another project member gets 404; two concurrent relays each read only their own result in either post order"
    requirement: "ALGN12-17"
    verification:
      - kind: test
        ref: "data-service/tests/test_workflow_relay.py::TestOwnerBoundPolling, ::TestConcurrentRelays"
        status: pass
    human_judgment: false
  - id: D4
    description: "Research gap 4: /mcp neo4j_query requires project, rejects unscoped Cypher (QUERY_NOT_PROJECT_SCOPED) before execution, withholds results with foreign entities (CROSS_PROJECT_RESULT_WITHHELD); neo4j_schema has no projects key"
    requirement: "ALGN12-17"
    verification:
      - kind: test
        ref: "data-service/tests/test_mcp_project_scope.py::TestMcpNeo4jQuery, ::TestMcpNeo4jSchema"
        status: pass
    human_judgment: false
  - id: D5
    description: "generate-cypher: graph_query requires project (CONTEXT_PROJECT_REQUIRED), project passed to generate_validated_cypher for every type, rule_ingest/rule_edit key collisions become valid:false with attempts preserved"
    requirement: "ALGN12-17"
    verification:
      - kind: test
        ref: "data-service/tests/test_mcp_project_scope.py::TestGenerateCypherProject"
        status: pass
    human_judgment: false
  - id: D6
    description: "ROUTE_POLICIES reaches 82 and the inventory test covers the two new rows unchanged"
    requirement: "ALGN12-17"
    verification:
      - kind: test
        ref: "data-service/tests/test_route_inventory.py::test_policy_table_size and completeness tests"
        status: pass
    human_judgment: false
  - id: D7
    description: "Live relay against the real n8n (published workflows, token wired in the n8n container, real execution-result round trip)"
    requirement: "ALGN12-17"
    verification: []
    human_judgment: true
    note: "Deliberately not fired: the live n8n publish is plan 1205-18; relay tested with a mocked urlopen"

duration: ~35min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 14: n8n Relay and Cypher Scope Enforcement Summary

**The data-service side of the n8n boundary is finished: two authenticated, project-authorised relay routes that replace the browser's direct webhook calls with owner-bound polling, the service token on every data-service to n8n request (fail-closed when unset), and the 1205-06 project-scope guard enforced before and after execution in `/mcp neo4j_query` and in `/context/generate-cypher`.**

## Accomplishments

- **Task 1 (relay):** `fire_n8n_webhook` extracted from `call_n8n_sync` (which now calls it and keeps its polling loop). It sends `X-DG-Service-Token` from `DG_SERVICE_TOKEN`, raises `RELAY_UNAVAILABLE` (503) before any request when the token is blank and on URLError/timeout, and `RELAY_NO_EXECUTION_ID` (502) when the ack has no id. `POST /workflows/rules-ingest` (editor) and `POST /workflows/graph-query` (viewer) are sync `def` routes; the n8n body is built from the validated `WorkflowRulesIngestRequest` / `WorkflowGraphQueryRequest` only, and `record_execution_owner(executionId, username, project, workflow)` runs before the 202.
- **Task 2 (scope):** `/mcp neo4j_query` requires `arguments.parameters.project`, runs `check_query_project_scope` (codes only in the error) before opening a session, keeps the read-only guard, then feeds the raw `record.values()` of every record to `find_foreign_project_entities` and withholds the whole result on any foreign entity. `neo4j_schema` lost its `projects` query and key (and the tools/list description). `/context/generate-cypher` requires a project for `graph_query`, always passes `project=` through, and turns a valid `rule_ingest`/`rule_edit` result whose Rule_Id/Atom_Id collides with another project into `{valid: false, violations, attempts}`.

## Task Commits

1. **Task 1: relay routes, fire_n8n_webhook, owner-bound polling** - `4852b53` (feat)
2. **Task 2: project-scope enforcement in /mcp and generate-cypher** - `d598883` (feat)

## Verification

| Check | Result |
|---|---|
| Host: `test_workflow_relay.py` + `test_route_inventory.py` | 738 passed |
| Host: `test_mcp_project_scope.py`, `test_mcp_gh_tools.py`, `test_cypher_project_scope.py`, `test_dg_context.py` | 128 passed, 5 failed before the test_dg_context fix; after it 4 failed (the known host-only `neo4j` hostname failures in `test_dg_context.py`: 2 ContextEndpoints, 2 Determinism) |
| In-container full suite (rebuilt data-service image, `--ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`) | **2062 passed, 1 skipped, 8 deselected, 12 failed** |
| Baseline after 1205-12 | 1997 passed, 1 skipped, 12 failed; the 12 failures are the identical known environmental set (10 `test_cq3_attribute_of.py`, `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, `test_evidence_contract.py::...::test_never_raises_on_garbage_input`); +65 passing are this plan's new tests |
| `grep -c` in app.py: `def fire_n8n_webhook` / `SERVICE_TOKEN_HEADER` / `check_query_project_scope` / `find_foreign_project_entities` / `find_cross_project_key_collisions` | 1 / 1 / 1 / 1 / 1 |
| `len(ROUTE_POLICIES)` | 82 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing endpoint test would now hit the live graph**
- **Found during:** Task 2 verification
- **Issue:** `test_dg_context.py::TestGenerateCypherEndpoint::test_endpoint_returns_validated_cypher_for_mocked_valid_adapter` sends a valid `rule_ingest` with a project; the new collision check opens a live Neo4j session (`neo4j` hostname unresolvable from the host).
- **Fix:** the test monkeypatches `dg_context.find_cross_project_key_collisions` and asserts it is invoked with the generated Cypher and the project.
- **Files modified:** `data-service/tests/test_dg_context.py`
- **Commit:** `d598883`

**2. [Rule 2 - Missing critical] Collision check fails closed**
- The plan did not say what happens if the collision lookup itself errors. Returning the unchecked Cypher would let the workflow write a possibly colliding rule, so the route answers 503 `KEY_COLLISION_CHECK_UNAVAILABLE` (test covers it; the driver error text is not echoed).
- **Commit:** `d598883`

**3. [Rule 2 - Missing critical] Relay maps transport errors and non-JSON acks**
- `fire_n8n_webhook` maps `URLError`/`TimeoutError`/`OSError` to `RELAY_UNAVAILABLE` and any unparseable or non-object ack to `RELAY_NO_EXECUTION_ID`, and `_relay_workflow` refuses a principal with no username (`RELAY_USER_REQUIRED`), so an unowned execution can never be created.
- **Commit:** `4852b53`

**4. [Rule 3 - Blocking] `test_policy_table_size` bump**
- Row count bumped 80 to 82 in `test_route_inventory.py`, as planned in the environment notes.
- **Commit:** `4852b53`

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None. The two new routes and the changed `/mcp` behaviour are exactly the surface in the plan's threat model (T-1205-14-01 through -07).

## Notes for downstream plans

- No workflow was imported, published or fired; the live n8n publish and a real relay round trip belong to 1205-18. Until n8n is republished with the Verify Relay Token node and `DG_SERVICE_TOKEN` in its environment, a live relay call would be rejected by n8n.
- `graph-query-mcp.json` must send `parameters.project` to `/mcp` and `project` to `/context/generate-cypher` (1205-05 did the /mcp side; the graph_query `CONTEXT_PROJECT_REQUIRED` and rule-ingest collision paths now depend on the workflows passing `project`).
- The `neo4j_schema` `projects` key is gone; any n8n prompt or client that read it must not.
- `ui-v2/src/lib/graphApi.js callWorkflow` (1205-11) now has live counterpart routes; a UI container rebuild is needed to exercise them end to end.

## Self-Check: PASSED

- FOUND: data-service/tests/test_workflow_relay.py, data-service/tests/test_mcp_project_scope.py
- FOUND commits: 4852b53, d598883
