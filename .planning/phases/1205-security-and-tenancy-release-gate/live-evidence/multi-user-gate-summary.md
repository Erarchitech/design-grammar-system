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

## Pending
- Task 2 owner smoke and GATE12-05 verdict: PENDING (blocking checkpoint).
- Task 3 (n8n published-version node check, local-profile restore): NOT STARTED.
