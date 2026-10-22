---
phase: 1303-pravilo-gh-obekt
plan: "17"
subsystem: data-service
tags: [calculator-catalogue, resolve-order, company-vocabulary, route-policy, d-54, d-56, d-57, d-59, d-60, dgopn-05]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-16 company-scoped CatalogueCalculator store, verify_stored_source, load_blocked, locked confirm / reject / retire"
provides:
  - "property_scripts.resolve order file catalogue, company catalogue, project-stored, LLM with integrity checks and the rejected-hash guard"
  - "company vocabulary merged into a deep copy of the SWRL conventions (ingest prompt), never the LLM explanation"
  - "pure candidate read model (source, samples n/min/max, verdicts, run-newer flag, retired copies)"
  - "four routes (candidates, confirm, reject, retire) behind member-only decision rows, SECURITY-BOUNDARY rows and section 3.10"
affects: [1303-18]
tech-stack:
  added: []
  patterns:
    - "resolve takes shared= and blocked= inputs read by generate / ensure_rule_classes through company_of(project)"
    - "deepcopy of module constants before merging request-scoped data"
    - "owner check passed to the store as allow_reconfirm, the store enforces it inside its write transaction"
key-files:
  created:
    - data-service/property_calculator_review.py
    - data-service/tests/test_property_calculator_review.py
    - data-service/tests/test_property_calculator_routes.py
  modified:
    - data-service/property_scripts.py
    - data-service/dg_context.py
    - data-service/app.py
    - data-service/route_policy.py
    - data-service/tests/test_property_scripts.py
    - data-service/tests/test_dg_context.py
    - data-service/tests/test_route_inventory.py
    - spec/SECURITY-BOUNDARY.md
key-decisions:
  - "Retire rights and confirming again: D-59 (retire row owner, any company project may retire, cascade, history kept; a retired calculator is confirmed again through the same gates), D-60 (only an owner confirms a retired calculator again: handler passes allow_reconfirm = owner role, store refuses otherwise; a retired copy is never rejected or regenerated)."
  - "Resolve order is exactly the plan's: file alias or chooser, shared, stored, blocked check, generator. A shared entry the project did not reject binds even when the project's own row is rejected, because it is a different, company-confirmed source."
  - "The generator-built binding now carries unit, explanation and reviewStatus pending (closes the 1303-16 handoff: unit was None for generated rows)."
  - "A confirm unit that is only control characters (non-blank, empty after cleaning) is treated as absent, so the stored calculator unit stays."
requirements-completed: []
requirements_partial: [DGOPN-05]
duration: ~1h45m
completed: 2026-10-22
status: complete
---

# Phase 1303 Plan 17: Resolution, vocabulary and routes for the company calculator catalogue Summary

A confirmed generated calculator now binds in later rules and projects of the same company without the LLM, the ingest vocabulary grows from confirmed company entries only, and four routes (candidates, confirm, reject, retire) carry the human decision behind member-only policy rows that match SECURITY-BOUNDARY.

DGOPN-05 is not marked complete: plan 1303-18 adds the Web UI card, the rollout and the live end-to-end evidence.

## What was built

### Task 1 (commit 08bd4d7): resolution order, integrity and rejected-hash guards, company vocabulary
- `property_scripts.resolve(..., shared=None, blocked=None)` also returns `warnings`. Per DataProperty: file alias or chooser; shared entry by `property_key` (skipped with a warning when the project rejected its sha256, otherwise `_from_shared`); stored record (`_from_stored` now verifies generated records and skips a rejected source); blocked check (`is_blocked`: unsupported with reason `rejected: ...` or `retired: ...`, no generator call); generator (a copy of `dp` with `rejectedReason` when the rejected row asked for regenerate; a digest the project already rejected is unsupported with "regenerated source was already rejected").
- `_from_shared` / `_integrity_problem` use `verify_stored_source`; a failing entry is skipped with a warning and never placed. A `contractVersion` that differs from `catalogue["version"]` adds a warning but still binds. A shared hit reports `resolvedBy "shared"`, `origin "generated"`, `catalogueId`, `reviewStatus "confirmed"`; `new` is false when the project already holds the same sha256 and catalogueId.
- `generate` and `ensure_rule_classes` keep `load_rules` first, then `load_active`, `company_of`, `load_catalogue`, `load_blocked`; a refused `save` (`{"saved": False}`) becomes a warning; both return `warnings`. Generated bindings now carry `unit`, `explanation` and `reviewStatus`.
- `dg_context._shared_vocabulary` and `_conventions_with_vocabulary`: a `copy.deepcopy` of `dg_knowledge.swrl_conventions()` gets the company's rows appended after the file vocabulary (ordered by property name, a name repeating a file name dropped case-insensitively); the vocabulary read runs before the entity read, so the entity read stays the last session call. No company, no catalogue statement. `SWRL_CONVENTIONS` is never assigned into.

### Task 2 (commit 7819c9a): pure candidate read model
`property_calculator_review.py` (no Neo4j, no app import): `SAMPLE_LIMIT=10`, `MEANING_MAX=160`, `UNIT_MAX=40`, `REASON_MAX=300`, `run_values`, `sample_summary`, `verdict_counts`, `clean_line`, `build_candidates`. A retired copy takes its run from `runs_by_property`; `runNewerThanCalculator` is False without a run.

### Task 3 (commit c707b1f): four routes, policy rows, SECURITY-BOUNDARY
- `app.py` section "Property-calculator promotion": `CalculatorConfirmRequest`, `CalculatorRejectRequest`, `CalculatorRetireRequest`, `_CALCULATOR_HINTS` (12 codes), `_calculator_error`, the four handlers. The handlers call no generator and no LLM.
- `route_policy.py`: candidates `{member, delegated}` viewer query; confirm and reject `{member}` editor body; retire `{member}` owner body. SECURITY-BOUNDARY: the four machine-checked rows in path-then-method order and section `3.10 Calculator promotion`.
- `test_route_inventory.py`: `ROUTE_POLICIES` 129 to 133 with the history comment.

## Response shapes and error codes (plan 1303-18 reads these)

Success shapes (no route returns the company name):

```
GET  /scripts/property-calculators/candidates?project=&runId=
  {project, companyAssigned, canRetire, run:{runId,createdAt}|null,
   candidates:[{dataPropertyIri, propertyName, function, source, sha256, unit, explanation, provider, model,
                createdAt, createdBy, readCategories, ruleIds, samples:[{objectRef,label,value}] (max 10),
                stats:{n,numeric,min,max}, verdicts:[{ruleId,counts:{status:n}}], run:{runId,createdAt}|null,
                runNewerThanCalculator, retired, catalogueId|null}],
   blocked:[{dataPropertyIri, propertyName, status:"rejected", sha256, reason, by, regenerate}],   // rejected rows only
   catalogue:[{catalogueId, propertyKey, propertyName, dataPropertyIri, sha256, unit, meaning, readCategories,
               contractVersion, provider, model, confirmedAt, (owners only: sourceProject, confirmedBy)}]}
POST /scripts/property-calculators/confirm  body {project, dataPropertyIri, sha256, runId, meaning, unit?}
  -> {project, dataPropertyIri, catalogueId, alreadyConfirmed, reconfirmed, reactivatedCopies}
POST /scripts/property-calculators/reject   body {project, dataPropertyIri, sha256, reason, regenerate=false}
  -> {project, dataPropertyIri, alreadyRejected, regenerate, rejectedSha256s}
POST /scripts/property-calculators/retire   body {project, catalogueId, reason}
  -> {project, catalogueId, retiredCopies, alreadyRetired}
```

Refusals are `HTTPException` with `detail = {error, hint, code}`. A pydantic body error (bad sha256 pattern, over-long field) is FastAPI's own 422.

Error-code split (three route-level, nine store, twelve in all; `_CALCULATOR_HINTS` has exactly these twelve, pinned by `test_every_calculator_error_code_has_a_hint`):

| Origin | Code | HTTP |
|---|---|---|
| route | `CALCULATOR_RUN_NOT_FOUND` | 404 |
| route | `CALCULATOR_INPUT_INVALID` | 422 |
| route | `CATALOGUE_COMPANY_REQUIRED` | 422 |
| store | `CALCULATOR_NOT_FOUND` | 404 |
| store | `CALCULATOR_NOT_PENDING` | 409 |
| store | `CALCULATOR_CHANGED` | 409 |
| store | `CALCULATOR_INTEGRITY` | 409 |
| store | `CALCULATOR_RUN_INVALID` | 422 (the confirm handler also answers it itself for a run without values) |
| store | `CALCULATOR_IN_CATALOGUE` | 409 |
| store | `CATALOGUE_PROPERTY_TAKEN` | 409 |
| store | `CATALOGUE_ENTRY_NOT_FOUND` | 404 |
| store | `CATALOGUE_RECONFIRM_OWNER_REQUIRED` | 403 |

Policy denials (editor on retire, viewer on confirm, delegated or connector on a decision row) are the auth layer's 403, not these codes.

## Retire rights and confirming again: D-59, D-60

Pinned by tests in `tests/test_property_calculator_routes.py`: `test_reconfirm_retired_requires_owner`, `test_confirm_retired_copy_answers_reconfirmed`, `test_confirm_by_a_project_owner_member_passes_allow_reconfirm`, `test_candidates_blocked_excludes_retired`, `test_candidates_retired_copy_uses_source_run_when_selected_run_has_no_values`, `test_reject_regenerate_on_retired_copy_is_refused`, `test_retire_needs_the_owner_role_of_the_requesting_project`, `test_d57_decision_rows_admit_member_only`; in `tests/test_property_scripts.py`: `test_retire_entry_absent_from_the_catalogue_does_not_bind_and_the_copy_stays_unsupported`, `test_retired_entry_confirmed_again_binds_as_shared`, `test_reject_cycle_regenerated_source_already_rejected_is_unsupported`. The store halves are the plan 1303-16 tests.

## Test evidence (commands run in this worktree)

| Command | Result |
|---|---|
| `cd data-service && python -m pytest tests/test_property_scripts.py tests/test_property_calculator_store.py tests/test_property_calculator_llm.py tests/test_dg_knowledge.py -q -p no:cacheprovider` | 172 passed (property_scripts 51, was 29) |
| `python -m pytest tests/test_dg_context.py -q -p no:cacheprovider -k vocabulary` | 8 passed |
| `python -m pytest tests/test_dg_context.py -q -p no:cacheprovider` | 70 passed, 4 failed (known baseline, below) |
| `-k shared`, `-k reject`, `-k retire`, `-k integrity` on `tests/test_property_scripts.py` | 13, 7, 2, 4 selected, all passed |
| `python -m pytest tests/test_property_calculator_review.py -q -p no:cacheprovider` | 20 passed |
| `python -m pytest tests/test_property_calculator_routes.py -q -p no:cacheprovider` | 40 passed (`-k "unit or retired"`: 8) |
| Task 3 verify set (`routes, review, route_inventory, security_boundary_spec, cross_project_matrix, graph_routes`) | 2798 passed |
| Quick command of 1303-VALIDATION.md (`property_scripts, property_calculator_llm, property_calculator_review, dg_knowledge, route_inventory, security_boundary_spec`) | 1287 passed |
| `cd tools/de01 && python -m pytest tests -q -p no:cacheprovider` | 173 passed, 1 failed: `test_de01_runner_against_golden_fixture_has_zero_silent_disagreements` (known baseline, research A6) |
| `cd data-service && python -m pytest tests -q -p no:cacheprovider` | 6381 passed, 35 skipped, 8 deselected, **6 failed, 25 errors** (1303-16 ended at 6187 passed, same 6 and 25) |

Route count before and after: `len(route_policy.ROUTE_POLICIES)` 129 to 133.

Full-suite failures, classified by name; every one matches the baseline listed in the plan and in `deferred-items.md`, no new name:
- Known host baseline, 4 `test_dg_context` tests: `TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`, `::test_get_debug_matches_post_assemble_body`, `TestDeterminism::test_repeated_assemble_calls_are_byte_identical`, `::test_get_debug_and_post_assemble_are_equal_for_graph_query`; and 25 setup errors (20 in `test_cg_structure_checks.py`, 5 in `test_computgraph_consult.py`, `neo4j:7687` DNS).
- Pre-existing, logged in `deferred-items.md`, not touched: `test_static_proxy_boundary.py::test_nginx_proxies_only_to_data_service` and `::test_nginx_config_is_fully_clean` (`unexpected-proxy-location:/data-service/scripts/`, plan 15 commit `4b03c61`). The new routes live under the existing `/data-service/scripts/` proxy location of plan 15; no nginx file changed and no new proxy location is needed, so this situation is unchanged.

Mutation checks (temporary, reverted, file restored from backup, suite green afterwards): forcing `allow_reconfirm = True` fails `test_reconfirm_retired_requires_owner`; listing every blocked status in `blocked[]` fails `test_candidates_blocked_excludes_retired`.

## Deviations from Plan

### Judgement calls

**1. [Rule 2 - Critical] `save` refusal and `stored` bookkeeping in `ensure_rule_classes`.** `stored[iri] = entry` is only set when the store actually saved (a refused save of a rejected source must not look stored); the refusal becomes a warning. Commit 08bd4d7.

**2. [Minor] Unit of only control characters.** A non-blank confirm unit that is empty after cleaning is treated as absent (stored unit stays) instead of a 422; the plan only specifies the blank and non-blank cases. Commit c707b1f.

**3. [Minor] TDD ordering.** The tasks are marked `tdd="true"`; tests and implementation were written together and committed per task (one commit per task, as in plan 16). Mutation checks stand in for the RED evidence.

**4. [Minor] Regenerate reason fallback.** With a rejected row that asks for regenerate but stored no reason, `rejectedReason` is set to "rejected by the operator" so the prompt still carries the line; the route itself requires a reason (1-600, non-empty after cleaning), so this only covers rows written by other code.

No file outside `files_modified` was changed.

## Authentication gates
None.

## Known Stubs
None.

## Threat Flags
None beyond the plan's threat model. Mitigations T-1303-17-01..11 are covered: member-only decision rows (`test_d57_decision_rows_admit_member_only`, delegated and connector requests answered 403), integrity at resolve (`test_integrity_*`), company scope (`test_shared_generate_without_a_company_runs_no_catalogue_statement`, `test_candidates_never_return_the_company_name`), clean meaning and unit (`test_confirm_cleans_*`, `test_vocabulary_carries_the_cleaned_meaning_never_the_llm_explanation`), rejected-hash cycle, module constant (`test_vocabulary_merge_never_mutates_the_module_conventions`), retire and re-confirm rights.

## Open items for plan 1303-18
- Research assumptions A1/A2 (objectRef to Revit box mapping; a `send=true` run carries the property's propStates) are verified only against canned payloads; the first live run decides.
- `errors.js` copies the twelve codes above; no UI string exists yet.
- The optional read-only `candidates` action of DeGram (`D:\dgb\src`, component repository) stays deferred and owner-gated; the route row already admits the delegated principal.

## Boundaries
No DG.gha, `DG/` source, `apps/degram/` or `D:\dgb\src` file changed. No docker, rebuild, push or deploy. `git diff --name-only` of the three task commits lists only files of `files_modified`. Tracked `bin/`, `obj/` and `graphify-out/` noise and untracked `.claude/`, `diagrams/`, `test/` files were not staged.

## Self-Check: PASSED

Created files exist, commits 08bd4d7, 7819c9a and c707b1f exist, and `git diff --name-only` since plan 16's tracking commit lists only files of `files_modified`.
