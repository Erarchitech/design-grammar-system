---
phase: 37-script-structure-validation
fixed_at: 2026-07-27T00:00:00Z
review_path: .planning/milestones/v9.0-phases/37-script-structure-validation/37-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 37: Code Review Fix Report

**Fixed at:** 2026-07-27T00:00:00Z
**Source review:** .planning/milestones/v9.0-phases/37-script-structure-validation/37-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (fix_scope: critical_warning — CR-01, WR-01, WR-02)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: `counts.warning` never reflects rule-mapped check failures — contradicts the documented severity model

**Files modified:** `data-service/cg_structure_checks.py`
**Commit:** 9e60191
**Applied fix:** Chose option (a) from the review's fix guidance (roll `ruleResults` failures into `counts.warning`), since `spec/RULE-PARTITION-POLICY.md`'s "Computgraph Structural Checks (Phase 37)" addendum already normatively states rule-mapped failures are `warning` severity — that doc, not the `counts`-is-findings-only prose in `spec/API.md`, reflects the intended behavior. `build_validation_report()` now adds `sum(1 for r in rule_results if not r["passed"])` to `counts[SEVERITY_WARNING]` after the existing findings-severity loop. Verified: `python -c "import ast; ast.parse(...)"` syntax check passed; all 40 non-integration tests in `data-service/tests/test_cg_structure_checks.py` pass (20 integration tests fail with a DNS-resolution error for hostname `neo4j`, which only resolves inside docker-compose — pre-existing environment dependency, not caused by this change, consistent with the project's known Neo4j E2E baseline).

### WR-01: Structure-rule mapping validation doesn't require the operation-specific param a mapping needs to be meaningful

**Files modified:** `data-service/cg_structure_checks.py`
**Commit:** 906393a
**Applied fix:** Extended `_mapping_rejection_reason()` to reject `requiresProcedure`/`requiresParameter` mappings whose `params.namePattern` is missing, non-string, or blank, and to reject `forbidsOrphan` mappings whose `params.label` is missing/falsy (previously only checked the allow-list when `label` was present). Also removed the now-redundant inner `forbidsOrphan` label-allow-list check that lived inside the `if params is not None:` block, since the new unconditional check at the end of the function supersedes it without changing behavior for well-formed entries. Verified against the real `llm/structure_rules.json`: all four shipped mappings (`requiresProcedure` with `namePattern: "Footer"`, `requiresParameter` with `namePattern: "HTotal"`, `forbidsOrphan` with `label: "Pattern"`, `requiresInterface` with empty `params`) still pass validation. All 40 non-integration tests plus `test_cg_fixtures.py` (11 tests) pass.

### WR-02: `spec/API.md`'s `/computgraph/validate` worked example doesn't match what the implementation actually produces

**Files modified:** `spec/API.md`
**Commit:** aa8ffdd
**Applied fix:** Regenerated the `ruleResults[]` worked example to match the real `_compose_message()` output shape and a real shipped mapping (`R_STRUCT_FRAME_FOOTER_V` / `requiresProcedure` / `namePattern: "Footer"`, from `llm/structure_rules.json`), gave the `offendingEntities[]` entry the full four-key shape (`label`, `cgId`, `name`, `conventionName`) that `_entity()` always returns, and changed `cgId: null` to `cgId: ""` to match `_entity()`'s actual never-null contract for cgId-less Algorithm entities. Also updated the `counts` response-key prose (previously "aggregated over `findings[]`") to describe the post-CR-01 behavior — `warning` now also counts failing `ruleResults[]` entries — so the two docs (`spec/API.md` and `spec/RULE-PARTITION-POLICY.md`) and the implementation now agree.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-07-27T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
