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

<!-- gsd:task-2 pending: owner rotation checkpoint -->
