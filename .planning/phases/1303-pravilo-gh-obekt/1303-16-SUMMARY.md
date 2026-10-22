---
phase: 1303-pravilo-gh-obekt
plan: "16"
subsystem: data-service
tags: [calculator-catalogue, review-lifecycle, neo4j-store, d-54, d-56, d-59, d-60, dgopn-05]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-15 property_calculator_store / property_calculator_llm / property_scripts (generated calculators)"
provides:
  - "company-scoped CatalogueCalculator node and locked confirm / reject / retire store transactions"
  - "verify_stored_source integrity check, review-preserving save, blocked-hash read"
  - "graph-route guards (locked labels, protected keys, claim-untagged exclusion)"
  - "REPRODUCIBILITY row for generate_calculator, DATABASE / LPG-OWL-MAPPING rows"
affects: [1303-17, 1303-18]
tech-stack:
  added: []
  patterns:
    - "row write lock by SET reviewLock inside one execute_write, decision computed in Python"
    - "single-worker _CATALOGUE_LOCK (auth._STORE_LOCK idiom)"
    - "stateful no-Neo4j fake dispatching on query-constant identity, with rollback on exception"
key-files:
  created:
    - data-service/tests/test_property_calculator_store.py
    - .planning/phases/1303-pravilo-gh-obekt/deferred-items.md
  modified:
    - data-service/property_calculator_store.py
    - data-service/property_calculator_llm.py
    - data-service/tests/test_property_calculator_llm.py
    - data-service/app.py
    - data-service/tests/test_graph_routes.py
    - data-service/tests/test_property_scripts.py
    - spec/REPRODUCIBILITY.md
    - spec/DATABASE.md
    - spec/LPG-OWL-MAPPING.md
    - tools/de01/tests/test_reproducibility_scope_drift.py
key-decisions:
  - "Retire rights and confirming again: D-59 (any company project may retire, cascade to copies, nothing deleted, history kept; a retired calculator is confirmed again through the same gates); D-60 (only an owner confirms a retired calculator again, a retired copy is never rejected per project)."
  - "BLOCKED_QUERY has no origin filter: a rejection list stays visible even if a catalogue binding later replaced the generated source."
  - "confirm refuses a source already confirmed for another DataProperty (same catalogueId, different propertyKey) with CATALOGUE_PROPERTY_TAKEN."
  - "A fresh pending copy that matches a retired entry also needs allow_reconfirm=True (closes a D-60 bypass through the reactivation branch)."
requirements-completed: []
requirements_partial: [DGOPN-05]
duration: ~2h
completed: 2026-10-22
status: complete
---

# Phase 1303 Plan 16: Calculator review lifecycle, store half Summary

Company-scoped `CatalogueCalculator` with locked confirm / reject / retire transactions, a save that never undoes a review decision, a durable rejected-hash read and the graph-route guards, pinned by 78 store tests that run without Neo4j.

DGOPN-05 is the store half only (plans 1303-17 and 1303-18 add routes, UI and live evidence), so the requirement is not marked complete.

## What was built

### Task 1 (commit 0448848): wave-0 guards and fixtures
- `spec/REPRODUCIBILITY.md` registers `property_calculator_llm.py|generate_calculator|model-dependent-unmeasured` (ten rows, prose paragraph, "exactly ten lines"); `tools/de01` drift test pinned to 10 and green (8 passed; it was red at plan start).
- `app.py`: `PropertyCalculator` and `CatalogueCalculator` in `LOCKED_NODE_LABELS`; `source` and `sha256` protected keys; `CLAIM_UNTAGGED_SHARED_GRAPHS = ["SpecGraph", "CalculatorCatalogue"]`. `test_graph_routes.py` updated and extended (80 passed).
- `spec/DATABASE.md` CatalogueCalculator block and the new PropertyCalculator review properties; `spec/LPG-OWL-MAPPING.md` not-exported row.
- `test_property_scripts._Session` answers `reviewLock`, `rejectedSha256Json` and `CatalogueCalculator` statements and implements `execute_write`.

### Task 2 (commit 1b8dba3): integrity, save, blocked read
- `property_calculator_llm`: `validate_function(source, name=)`, `GENERATED_NAME`, `verify_stored_source`, the rejection-reason prompt line (prompt byte-identical without the key, pinned by sha256 and length of the pre-change prompt), and the `dg.property_calculator_generation` logger with its own stderr handler (one handler after reload, one INFO record per `generate_calculator` call before the provider call, IRI only).
- `property_calculator_store`: constants, `CalculatorReviewError`, `_CATALOGUE_LOCK`, helpers, `load_blocked`, `_save_tx` / `save` (keeps status, review state, catalogueId, createdAt, createdBy on an unchanged sha256; refuses a generated source in `rejectedSha256Json`; never writes that list).

### Task 3 (commit e60d5e7): catalogue reads and locked transactions
- Reads: `load_catalogue`, `vocabulary_rows`, `load_catalogue_entries`, `load_candidates`, `load_verdict_counts` (every catalogue statement binds `$company`; falsy company runs no statement).
- Writes: `confirm`, `reject`, `retire` as in the plan, with REACTIVATE statements for D-59.

## Final store API (plan 1303-17 calls exactly these)

```
CATALOGUE_LABEL = "CatalogueCalculator"; CATALOGUE_GRAPH = "CalculatorCatalogue"
STATUS_ACTIVE / STATUS_REJECTED / STATUS_RETIRED; REVIEW_PENDING / REVIEW_CONFIRMED / REVIEW_REJECTED
class CalculatorReviewError(Exception): .code .status .detail
property_key(iri) -> str                      catalogue_id(company, sha256) -> "CC-<16 hex>"
company_of(project) -> str | None             created_after(later_iso, earlier_iso) -> bool
is_blocked(entry) -> bool                     rejected_source(blocked, iri, sha256) -> bool
load_active(session, project) -> {iri: row}   load_blocked(session, project) -> {iri: {status, sha256, sha256s, reason, by, regenerate}}
load_catalogue(session, company) -> {propertyKey: row}
vocabulary_rows(session, company) -> [{property, meaning, unit}]
load_candidates(session, project) -> [row + retired:bool]
load_catalogue_entries(session, company) -> [entry]
load_verdict_counts(session, project, run_id, rule_ids) -> [{ruleId, status, count}]
save(session, project, entry, actor) -> {"saved": bool, "reason": str | None}
confirm(session, *, project, company, data_property_iri, sha256, run, actor, meaning, unit, contract_version,
        allow_reconfirm=False) -> {catalogueId, entry, alreadyConfirmed, reconfirmed, reactivatedCopies}
reject(session, *, project, data_property_iri, sha256, actor, reason, regenerate) -> {alreadyRejected, regenerate, rejectedSha256s}
retire(session, *, project, company, catalogue_id, actor, reason) -> {catalogueId, retiredCopies, alreadyRetired}
```

Notes for plan 1303-17:
- `run` is `{"runId": str, "createdAt": iso}`.
- Codes raised by `CalculatorReviewError`: `CALCULATOR_NOT_FOUND` 404, `CALCULATOR_NOT_PENDING` 409, `CALCULATOR_CHANGED` 409, `CALCULATOR_INTEGRITY` 409, `CALCULATOR_RUN_INVALID` 422, `CALCULATOR_IN_CATALOGUE` 409, `CATALOGUE_PROPERTY_TAKEN` 409, `CATALOGUE_ENTRY_NOT_FOUND` 404, `CATALOGUE_RECONFIRM_OWNER_REQUIRED` 403. As a fail-closed guard, `confirm` with a falsy company also raises `CATALOGUE_COMPANY_REQUIRED` 403 (same name as the planned route-level code, so the route layer can map both identically).
- `save` now returns a dict; `property_scripts` ignores the return value today.
- The resolver's generated binding carries `explanation` but no `unit`, so `save` stores `unit=None` for a generated calculator until the resolver passes `answer["unit"]` through (`property_scripts.py` is not in this plan's `files_modified`). `confirm` takes `unit` from the request first, so this is not blocking.

## Retire rights and confirming again: D-59 / D-60

Pinned by tests in `tests/test_property_calculator_store.py`:
- `test_retired_entry_confirmed_again_reactivates_entry_and_copies`
- `test_confirm_again_refused_while_another_entry_holds_the_key`
- `test_reconfirm_retired_copy_refused_without_owner_flag` (D-60)
- `test_reject_retired_copy_refused_with_or_without_regenerate` (D-60)
- `test_a_fresh_pending_copy_of_a_retired_source_also_needs_the_owner_flag`
- `test_retire_from_another_project_of_the_company_retires_entry_and_copies_and_deletes_nothing`
- `test_reject_regenerate_reject_cycle_never_revives_a_rejected_source`, `test_active_row_with_earlier_rejection_still_refuses_that_source`

## Test evidence (commands run in this worktree)

| Command | Result |
|---|---|
| `cd tools/de01 && python -m pytest tests/test_reproducibility_scope_drift.py -q -p no:cacheprovider` | 8 passed |
| `cd data-service && python -m pytest tests/test_property_calculator_store.py tests/test_property_calculator_llm.py tests/test_property_scripts.py tests/test_graph_routes.py -q -p no:cacheprovider` | 209 passed (store 78, llm 22, scripts 29, graph routes 80) |
| plan-end set plus `tests/test_dg_knowledge.py` | 230 passed |
| `cd tools/de01 && python -m pytest tests -q -p no:cacheprovider` | 173 passed, 1 failed: `test_de01_runner_against_golden_fixture_has_zero_silent_disagreements` (known baseline, research A6) |
| `cd data-service && python -m pytest tests -q -p no:cacheprovider` | 6187 passed, 35 skipped, 8 deselected, **6 failed, 25 errors** (see below) |

Full-suite failures, classified by name:
- Known host baseline: 4 `test_dg_context` tests (`TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`, `::test_get_debug_matches_post_assemble_body`, `TestDeterminism::test_repeated_assemble_calls_are_byte_identical`, `::test_get_debug_and_post_assemble_are_equal_for_graph_query`) and 25 setup errors in `test_cg_structure_checks.py` / `test_computgraph_consult.py` (`neo4j:7687` DNS).
- **Not in the plan's baseline, pre-existing, not caused by this plan:** `test_static_proxy_boundary.py::test_nginx_proxies_only_to_data_service` and `::test_nginx_config_is_fully_clean` (`unexpected-proxy-location:/data-service/scripts/`, introduced by 1303-15 commit `4b03c61`). Logged in `deferred-items.md`; no nginx file touched here.
- No new failure name originates from the files of this plan.

Mutation check (temporary, reverted, diff against backup clean): removing the integrity check, the in-catalogue refusal, the save refusal of a rejected source, the retire history event, the blocked read's active-list branch, or the owner gate each makes at least one store test fail.

## Deviations from Plan

### Auto-fixed / judgement calls

**1. [Rule 2 - Critical] Retired entry reactivation also needs the owner flag**
- **Found during:** Task 3 design
- **Issue:** the plan checks `allow_reconfirm` only for the project's own retired copy. A fresh pending copy of the same source (another project regenerating identical code) that meets a retired entry would reactivate it without the owner role, bypassing D-60.
- **Fix:** the reactivation branch re-checks `allow_reconfirm is not True` and raises `CATALOGUE_RECONFIRM_OWNER_REQUIRED`. Test `test_a_fresh_pending_copy_of_a_retired_source_also_needs_the_owner_flag`.
- **Commit:** e60d5e7

**2. [Rule 2 - Critical] Source already confirmed for another DataProperty**
- **Issue:** two DataProperties with byte-identical source share a `catalogueId`; confirming the second would silently reuse an entry keyed to the first (prohibition: "already confirmed under another key").
- **Fix:** `confirm` raises `CATALOGUE_PROPERTY_TAKEN` when the existing entry's `propertyKey` differs. Test `test_confirm_refuses_a_source_already_confirmed_for_another_property`.
- **Commit:** e60d5e7

**3. [Rule 2] `BLOCKED_QUERY` without `origin = 'generated'`**
- The plan describes "generated rows"; the origin filter was dropped so a rejection list never becomes invisible if a catalogue binding replaced the row. The marker contract is unaffected.
- **Commit:** 1b8dba3

**4. [Minor] TDD ordering.** Tasks are marked `tdd="true"`; tests and implementation were written together and committed per task (one commit per task, as the plan structures them), not as separate RED and GREEN commits. Mutation checks above stand in for the RED evidence.

**5. [Minor] `CATALOGUE_COMPANY_REQUIRED`** raised by `confirm` for a falsy company (see API notes).

## Authentication gates
None.

## Known Stubs
None. `unit` for a generated calculator stays `None` in `save` until the resolver passes it (see API notes); it is data plumbing owned by 1303-17, not a stub in this plan's goal.

## Threat Flags
None beyond the plan's threat model; mitigations T-1303-16-01..11 are covered by the tests named above.

## Boundaries
No DG.gha, `DG/` source, `apps/degram/` or `D:\dgb\src` file changed. No docker, rebuild, push or deploy. `git diff --name-only` of the three task commits lists only files of `files_modified` (plus nothing else). Tracked `bin/`, `obj/` and `graphify-out/` noise was not staged.

## Self-Check: PASSED
