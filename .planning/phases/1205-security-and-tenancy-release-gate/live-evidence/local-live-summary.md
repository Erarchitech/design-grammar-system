# Phase 1205 Plan 18 - Local Live Summary (status lines only)

No secret values, tokens or hashes appear in this file. Profile: local.

## Task 1 - Preflight (2026-09-29)

### Host suites

- host data-service pytest (`data-service/tests`): 2973 passed, 1 skipped, 4 failed, 25 errors. The 4 failures are the known `test_dg_context.py` baseline; the 25 errors are the known neo4j-hostname integration errors (`test_cg_structure_checks.py`, `test_computgraph_consult.py`). Nothing outside the baseline.
- `tools/de01/tests` + `tools/security/tests` (`-k "not live"`): 152 passed, 21 deselected.
- `dotnet test DG.Tests`: 577 passed, 3 failed, 580 total. The 3 failures are `DesignStateValidationFlowTests` (`HappyPath_StatePublishAndRetrieve`, `Filtering_StateAndRule`, `LegacyNoState_FlowStillWorks`); the failing calls return 401 Unauthorized from the live, auth-enforcing data-service, which the unauthenticated host E2E fixture does not satisfy. Same 577/580 shape as 1205-03; environment-dependent, not a regression.
- `npm --prefix ui-v2 run build`: built OK (chunk-size warning only).

### Rebuild

- `docker compose build --no-cache data-service design-grammars dg-reasoner`: exit 0, all three images built.
- `docker compose up -d`: exit 0; every service reports running (0 non-running).

### Stale-image guard

- `def require_principal` count in `/app/auth.py` inside data-service: 1 (>= 1, PASS).
- data-service container image equals freshly built image (sha256:2dfbb5c03ed9...): MATCH.
- design-grammars container image equals freshly built image (sha256:29698a960088...): MATCH.
- dg-reasoner container image equals freshly built image (sha256:0c0839cdd3ec...): MATCH.
- `config.js` key names: dataServiceUrl, speckleBaseUrl only (no credential key).

### In-container data-service suite

- Literal `docker exec data-service pytest -q`: 1 collection error in `tests/recognition_eval/test_freeze_rule_ingest_prompts.py` (repo-root fixtures not mounted) - known baseline.
- With `--ignore=tests/recognition_eval/test_freeze_rule_ingest_prompts.py`: 2986 passed, 1 skipped, 8 deselected, 12 failed. The 12 are exactly the known set (10 `test_cq3_attribute_of.py`, 1 `test_repeat_sweep.py::test_llm_report_schema_has_no_shared_or_accuracy_fields`, 1 `test_evidence_contract.py::TestParseEvidenceEnvelope::test_never_raises_on_garbage_input`). Nothing outside the baseline.

Task 1 verdict: PASS. The running stack holds the 1205 code.

## Task 2 - Rotation (owner-authorised, script-driven; status only)

Method: values generated locally and never printed; previous values backed up in the gitignored `.secrets/`; steps follow `spec/SECURITY-BOUNDARY.md` section 9.

| Secret | Status |
|---|---|
| NEO4J_PASSWORD | rotated, new accepted; dependants (data-service, dg-reasoner, n8n) recreated; data-service Neo4j connectivity ok |
| POSTGRES_PASSWORD | rotated, new accepted over the compose network; speckle-server / webhook / fileimport recreated; Speckle GraphQL serverInfo ok |
| MINIO_ROOT_USER + MINIO_ROOT_PASSWORD | rotated; speckle-minio + speckle-server recreated; health live 200; no S3 credential errors |
| LLM_MASTER_SECRET | `rotate_llm_master_secret.py` dry-run ok, then real run rotated; stored keys decrypt under the new secret |
| SPECKLE_SESSION_SECRET | rotated |
| N8N_PASSWORD (.env) | rotated; n8n healthz 200 |
| DG_SERVICE_TOKEN | rotated; data-service + n8n recreated together; POST /mcp accepts new, rejects old |
| DG_BOOTSTRAP_ADMIN_PASSWORD | rotated via POST /auth/password; new login ok, old refused |
| DE-01 connector token | minted as admin for project DG-1200-GOLDEN, saved to `.de01/connector-token`; heartbeat with it 200, bound project matches |

- `python tools/security/check_env_file.py` (no flag), re-run by the executor: all 17 keys `ok`, exit 0.
- Owner-only, NOT done: n8n owner-account password change in the n8n UI (n8n 2.4.8 ignores `N8N_BASIC_AUTH_*`, so `N8N_PASSWORD` in `.env` is not the effective n8n login); rotating the reused n8n password outside the repo; optional runbook step 11 (Speckle API tokens, never committed; old connector credentials not revoked).

## Task 3 - Post-rotation live checks (2026-09-29)

### Restart
- `docker compose up -d --force-recreate`: exit 0. data-service exited (code 3) once because it started before Neo4j accepted Bolt connections; `docker compose up -d data-service` after Neo4j was up fixed it. Every service then reports running (0 non-running).

### n8n publish (D-08)
- n8n version 2.4.8; repo `n8n/workflows/` is bind-mounted at `/files/workflows` in the container. The mounted copies carry no workflow ids for 4 of 5 files, so a plain import would have created duplicate workflows on the same webhook paths. Copies with the live workflow ids injected (temporary, not committed) were imported instead, updating the five live workflows in place.
- Imported: DG Rules -> Metagraph, DG Graph Query (MCP), Spec Ingest, Spec Query, spec-update (5/5, each reported "Deactivating ... Remember to activate later").
- `n8n publish:workflow --id=<id>` for each of the five (n8n 2.x command); `docker compose restart n8n`.
- `n8n list:workflow --active=true` after restart: exactly the five workflows, no others.
- Node-name check on an export of the live workflows (names only): `Verify Relay Token` present in 5/5; `activeVersionId == versionId` for 5/5 (the published version is the imported one).
- Unauthenticated direct webhook POST to `dg/rules-ingest` and `dg/graph-query` (host port 5678, no relay token): n8n answers HTTP 200 with an empty body (responseNode mode on a thrown error) and its log records `relay token rejected` for each call; no executionId is returned, so the relay cannot mistake it for an ack.
- Relay round trip (status-only script that reads `.env` internally): admin login 200; POST `/workflows/graph-query` (project DG-1200-GOLDEN) 202 with an executionId; GET `/execution-result/{id}` 200. So n8n accepts the rotated DG_SERVICE_TOKEN and reads it via env (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`).

### Old public defaults rejected (D-13 / T-1205-18-04)
- Neo4j: `cypher-shell -u neo4j -p <old default>` -> "The client is unauthorized due to authentication failure", exit 1 (REJECTED).
- Speckle Postgres: the plan's literal check (`docker exec speckle-postgres psql postgresql://speckle:speckle@localhost/speckle`) is invalid because the official postgres image's pg_hba trusts TCP from 127.0.0.1 inside the container, so it succeeds regardless of password. Checked over the compose network instead (`docker run --network design-grammar-system_default -e PGPASSWORD=<old default> postgres:16.4-alpine3.20 psql -h speckle-postgres ...`) -> "password authentication failed", exit 2 (REJECTED).

### Local boundary checker (D-16, D-19)
- `python tools/security/check_live_boundary.py --profile local --json-out live-evidence/local-boundary-check.json`: exit 0, `passed: true`; 13 rows = 10 pass + 3 info (trusted-local ports 7687, 7474, 5678); check families config_js, proxy_removed, unauthenticated, ports. Report: `local-boundary-check.json`.

### DE-01 (D-20)
- `python tools/de01/run_de01.py`: exit 0; available legs = data-service, dg-reasoner, csharp, replay; every leg `available: true`, `error: null`; report contains 0 occurrences of 401/unauthorized; `silent_disagreement_count = 0`; canonical state hash agreement `not_applicable`.

### Evidence hygiene
- Token-shape grep (`dgc_`/`dgs_` prefixes) over `live-evidence/`: 0 matches in every file.

Task 3 verdict: PASS.
