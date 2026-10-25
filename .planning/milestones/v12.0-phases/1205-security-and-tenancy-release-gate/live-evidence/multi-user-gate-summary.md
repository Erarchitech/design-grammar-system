# 1205-19 Multi-user gate record (status lines only)

Date: 2026-09-29. Compose: `docker-compose.yml` + `docker-compose.multi-user.yml`, `up -d --force-recreate`.
No code, config or fixture was changed during this run.

## Bring-up
- Full `--force-recreate` in the multi-user profile: all services started.
- data-service exited once with code 3 at cold start (Bolt 7687 refused while Neo4j was still starting; same race as 1205-18 deviation 3). Restarted once with `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d data-service`. No code change. Startup then completed cleanly. The multi-user default-secret refusal (D-11) did NOT block startup (secrets rotated in 1205-18).
- `docker exec data-service printenv DG_DEPLOYMENT` -> `multi-user`.
- Stale-image guard: `grep -c "def require_principal" /app/auth.py` -> 1. Container image ids equal 1205-18: data-service 2dfbb5c03ed9, design-grammars 29698a960088, dg-reasoner 0c0839cdd3ec (also the current `docker images` ids for the built tags; containers were force-recreated from the same images).
- Host ports: 7687, 7474, 5678 refused (see checker below).

## In-container gate suites (DG_DEPLOYMENT=multi-user)
- D-14/D-15/D-16 static: `tests/test_route_inventory.py tests/test_security_boundary_spec.py tests/test_cross_project_matrix.py tests/test_static_proxy_boundary.py tests/test_compose_boundary.py tests/test_config_js_no_secrets.py` -> **1657 passed, 0 failed**.
- Literal full-suite command `docker exec data-service pytest -q` -> stops at the known collection error (`tests/recognition_eval/test_freeze_rule_ingest_prompts.py` reads repo-root fixtures that are not mounted); 0 tests run.
- Full suite with that file ignored (run twice, identical result): **17 failed, 2981 passed, 1 skipped, 8 deselected**. Local-profile baseline is 12 known environmental failures / 2986 passed / 1 skipped. Failure breakdown:
  - 12 known environmental (10 in `tests/test_cq3_attribute_of.py`, `tests/recognition_eval/test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, `tests/test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`).
  - **5 additional, profile-dependent (NOT in the local baseline)**:
    1. `tests/test_connectors.py::TestHeartbeatBundle::test_heartbeat_returns_host_facing_neo4j_bundle` and `::test_neo4j_public_uri_env_overrides_bundle_uri` fail with `TypeError: 'NoneType' object is not subscriptable` at test_connectors.py:234 / :248. Cause: these tests assert the local-profile heartbeat bundle; in multi-user the bundle is null by design (D-07), so `body["neo4j"]` is None. The tests do not pin the profile.
    2. `tests/test_designstate_capture.py::test_lifespan_starts_and_stops_watcher_thread_injecting_both_callables`, `::test_lifespan_still_runs_ensure_spec_indexes`, `::test_lifespan_survives_watcher_start_failure` fail only in the full-suite run with `RuntimeError: refusing to start in multi-user profile: secrets failing policy: LLM_MASTER_SECRET(too-short)` (run in isolation, the whole file passes 22/22). Cause (unverified in detail): an earlier test leaves a short LLM_MASTER_SECRET in the process environment, and the lifespan hook's D-11 refusal then fires because the container runs multi-user. Order-dependent test isolation issue surfaced by the profile, not a boundary defect.
  - Findings recorded as-is; nothing fixed in this plan. Follow-up: pin the profile (or monkeypatch `DG_DEPLOYMENT=local`) in the heartbeat-bundle tests and restore env in the test that sets LLM_MASTER_SECRET.

## Live boundary checker (D-16), from the host
`python tools/security/check_live_boundary.py --profile multi-user --json-out live-evidence/multi-user-boundary-check.json` -> **exit 0, passed: true**. Includes: `/neo4j/` and `/n8n/` proxy paths not reachable through 8080, unauthenticated API calls 401, config.js holds no credential/known default, and ports 7687, 7474, 5678 refused (three port-refusal checks pass). Details in the JSON.

## Connector heartbeat (D-07)
POST /connectors/heartbeat on http://localhost:8000 with the owner's DE-01 connector token (`.de01/connector-token`, read internally, never printed): HTTP 200; response keys `connector_id, neo4j, project, status`; the `neo4j` key is PRESENT but its value is null (no bundle: no uri/user/password/database). Literal acceptance wording says "no neo4j key"; the observed behavior is a null bundle, consistent with code comment at data-service/app.py:1548-1552 and the two failing heartbeat tests above. Judged as D-07 satisfied (no graph bundle is issued); flagged to the owner for wording.

## Token-shape grep
Token-shape grep over `live-evidence/`: 0 secret-shaped matches. The generic 40+ character pattern matches only long pytest test names in this file (no token, hex digest or bundle value present); the JSON evidence has 0 matches.

## Owner verdict (Task 2, 2026-09-29)
- GATE12-05 verdict, verbatim: "gate-pass".
- The owner did not supply the timestamps of their ingest and query runs (see the n8n check below for how this was handled).
- The owner did not comment on the two Task-1 findings (5 profile-dependent test failures; null `neo4j` heartbeat key). They are recorded as OPEN non-blocking follow-ups under the gate-pass, not as owner-accepted.

## n8n published-version check (D-08), Task 3
- Method: n8n database (plus -wal/-shm) copied to the session scratchpad, opened with sqlite3, only node names, the presence of `Verify Relay Token`, execution start time and status were read. Scratch copies deleted afterwards (confirmed: 0 files remain).
- The two executions below are the most recent rows of each workflow after the 1205-18 publish (~2026-09-29 19:15Z). They could NOT be matched to owner-supplied run times (none were given); they are the most recent rows, presumed but not proven to be the owner's runs.
- Rules ingest ("DG Rules -> Metagraph"): execution 274, started 2026-09-29 20:11:26 (n8n stored time), mode webhook, status success; workflow node list contains `Verify Relay Token`: True (17 nodes).
- Graph query ("DG Graph Query (MCP)"): execution 273, started 2026-09-29 20:09:47 (n8n stored time), mode webhook, status success; node list contains `Verify Relay Token`: True (18 nodes).
- Older executions on the pre-publish version (2026-09-19) lack `Verify Relay Token`, confirming the published version changed. Executions 267-272 (19:19-19:20) were 1205-18 probes on the new version (contain the node; several status error, not analysed here).

## Local profile restored (D-19), Task 3
- `docker compose up -d --force-recreate` (base file only, no override).
- data-service exited with code 3 at cold start again (Neo4j Bolt not ready; no healthcheck/restart policy). Restarted once with `docker compose up -d data-service`. No code change.
- `docker exec data-service printenv DG_DEPLOYMENT` -> `local`.
- Heartbeat with the saved connector token: `neo4j bundle present: True`.
- All 15 containers Up.

## Open follow-ups (non-blocking, not fixed in this plan)
1. Multi-user full-suite: 5 extra failures (`test_connectors.py::TestHeartbeatBundle` x2 hard-code the local bundle; `test_designstate_capture.py` lifespan tests x3 fail only in the full run with the D-11 refusal on LLM_MASTER_SECRET(too-short), suspected env leak, unverified).
2. Multi-user heartbeat keeps a `neo4j` key with a null value versus the plan's literal "no neo4j key".
3. From 1205-18: DG.Tests E2E DesignStateValidationFlowTests (3) fail with 401 (fixture lacks a connector token); data-service cold-start race (exit code 3).

## Status
- Task 1: complete (a1f7e39). Task 2: owner verdict "gate-pass". Task 3: complete.
