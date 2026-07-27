---
phase: 37-script-structure-validation
plan: 04
subsystem: api
tags: [neo4j, cypher, computgraph, structural-validation, rule-mapping, pytest, deterministic]

requires:
  - phase: 37-01
    provides: cg_fixtures.py parser-faithful Frame envelope builders (FIXTURE_PROJECT isolation, PROC_12_NAME, PARAM_HTOTAL_CG_ID)
  - phase: 37-02
    provides: spec/API.md ruleResults[] normative contract + spec/RULE-PARTITION-POLICY.md value-threshold exclusion for structural checks
  - phase: 37-03
    provides: cg_structure_checks.py's _entity()/_finding() shared constructors, session-injection discipline, and the module's SC4 (LLM-free) grep gate this plan extends
provides:
  - "llm/structure_rules.json: versioned {version, mappings} declarative rule-mapping artifact seeded with four SVAL-02 mappings, sibling convention to llm/cypher_catalog.json"
  - "cg_structure_checks.py: load_structure_rules()/valid_structure_mappings()/structure_rule_ids() defensive loader trio, four static _OPERATION_TEMPLATES compiled from mapping operations, and evaluate_rule_mappings() -- the declarative-mapping-to-Cypher evaluator reporting pass/fail per rule with satisfying/offending entities"
  - "data-service/tests/test_cg_structure_checks.py: 17 new loader unit tests (-k structure_rules) + 8 new live-Neo4j integration tests (-k rule_mapped)"
affects: [37-05, 37-06]

tech-stack:
  added: []
  patterns:
    - "Declarative operation-to-Cypher compiler: a JSON mapping entry names an operation + bound params; the module owns exactly one static parameterized Cypher template per operation, never built or edited at runtime"
    - "Soft foreign key: Rule_Id existence is probed but never gates evaluation -- a missing Metagraph Rule node sets ruleExists=false and the structural verdict is still computed and reported"
    - "Fixed relationship-type alternation for a dynamic-label orphan check: forbidsOrphan matches any allow-listed label via `$label IN labels(n)` plus a single static HAS_* alternation, avoiding both label interpolation and per-label template branching"

key-files:
  created:
    - llm/structure_rules.json
  modified:
    - data-service/cg_structure_checks.py
    - data-service/tests/test_cg_structure_checks.py

key-decisions:
  - "_FORBIDDEN_PARAM_KEYS = {min, max, greaterThan, lessThan, greaterThanOrEqual, lessThanOrEqual, threshold, value} -- the eight value-comparison forms Pitfall 3 (37-RESEARCH.md) and T-37-10 require rejected; a mapping using any of them is SWRL scope, not a structural check"
  - "_COMPUTGRAPH_ORPHAN_LABELS excludes Object (root, structurally ownerless) from the forbidsOrphan allow-list -- {Behavior, Algorithm, Procedure, Pattern, Parameter, Interface} only"
  - "requiresInterface is a for-all check (every scoped Procedure needs >=1 matching Interface) unlike requiresProcedure/requiresParameter's exists semantics -- documented in-code so a future contributor doesn't collapse it into an exists check"
  - "_compose_message() extracted from _finding()'s inline f-string as the shared What+Where+How-to-fix composer, reused by both SVAL-01 findings and SVAL-02 rule results, per the plan's explicit instruction"
  - "A mapping rejected by valid_structure_mappings() is reported in evaluate_rule_mappings()'s output as passed=false with an 'INVALID MAPPING -- not evaluated.' prefixed message, rather than silently dropped -- visible in the report, never mistaken for a genuine structural failure"

requirements-completed: [SVAL-02]

coverage:
  - id: D1
    description: "llm/structure_rules.json: versioned {version, mappings} envelope seeded with four real mappings (Footer procedure, height variable float parameter, no-orphan Pattern, Procedure interface presence), each entry carrying exactly ruleId/operation/params/description with no embedded Cypher fragment"
    requirement: "SVAL-02"
    verification:
      - kind: unit
        ref: "python -c one-liner asserting envelope shape, key sets, and zero MATCH/RETURN/MERGE substrings -- pass"
        status: pass
    human_judgment: false
  - id: D2
    description: "load_structure_rules()/valid_structure_mappings()/structure_rule_ids() defensive loader trio mirrors dg_context.load_cypher_catalog() exactly -- never raises on missing/malformed/degenerate input, rejects forbidden value-threshold param keys and out-of-allowlist forbidsOrphan labels, deterministic order-preserving filter"
    requirement: "SVAL-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_structure_checks.py -k structure_rules (17 tests, host, no Neo4j) -- pass"
        status: pass
    human_judgment: false
  - id: D3
    description: "Four static _OPERATION_TEMPLATES (requiresProcedure/requiresParameter exists-checks, requiresInterface for-all check, forbidsOrphan against a fixed HAS_* ownership alternation) plus the RULE_EXISTS_METAGRAPH soft-foreign-key probe; evaluate_rule_mappings() joins Rule_Id without gating on its existence and emits the normative ruleId/operation/passed/ruleExists/message/satisfyingEntities/offendingEntities shape, sorted for determinism"
    requirement: "SVAL-02"
    verification:
      - kind: unit
        ref: "python -c one-liner asserting _OPERATION_TEMPLATES keys match STRUCTURE_RULE_OPERATIONS and every template carries its own op= tag -- pass"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_cg_structure_checks.py::TestRuleMappedChecksIntegration (docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k rule_mapped -q -- 8 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "SC2 proven automatically: the Footer rule (R_STRUCT_FRAME_FOOTER_V) passes on the full Frame (satisfyingEntities names procedure 12) and fails on the footer-less copy (offendingEntities non-empty), the two results differing only in passed"
    requirement: "SVAL-02"
    verification:
      - kind: integration
        ref: "test_rule_mapped_footer_rule_passes_on_full_frame / test_rule_mapped_footer_rule_fails_on_footer_less_copy / test_rule_mapped_footer_pass_fail_pair_differs_only_in_passed -- 3/3 passed"
        status: pass
    human_judgment: false
  - id: D5
    description: "SC4 gate: cg_structure_checks.py still contains zero references to the LLM gateway or any adapter generate call after both new sections, in code or comments"
    requirement: "SVAL-02"
    verification:
      - kind: other
        ref: "grep -v '^\\s*#' data-service/cg_structure_checks.py | grep -c 'llm_gateway\\|adapter\\.generate' -- 0"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-27
status: complete
---

# Phase 37 Plan 04: Rule-Mapped Structural Checks (SVAL-02) Summary

**`llm/structure_rules.json` (4 seeded mappings) plus `evaluate_rule_mappings()` in `cg_structure_checks.py` -- a declarative operation-to-Cypher compiler that evaluates Design Rules as script-structure requirements over the published Computgraph, joining Rule_Id as a soft foreign key and reporting pass/fail per rule with satisfying/offending entities.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-27T13:53:37+03:00 (first task commit)
- **Completed:** 2026-07-27T14:01:01+03:00 (last task commit)
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `llm/structure_rules.json`: versioned `{version, mappings}` envelope, sibling convention to `llm/cypher_catalog.json`, seeded with `R_STRUCT_FRAME_FOOTER_V` (requiresProcedure), `R_STRUCT_FRAME_HEIGHT_VAR_V` (requiresParameter), `R_STRUCT_NO_ORPHAN_PATTERN_V` (forbidsOrphan), `R_STRUCT_PROC_INTERFACE_V` (requiresInterface)
- `cg_structure_checks.py`: `STRUCTURE_RULES_FILE`/`STRUCTURE_RULE_OPERATIONS`/`_FORBIDDEN_PARAM_KEYS`/`_COMPUTGRAPH_ORPHAN_LABELS` constants, `load_structure_rules()`/`valid_structure_mappings()`/`structure_rule_ids()`/`STRUCTURE_RULE_IDS` defensive loader trio, `_OPERATION_TEMPLATES` (four static parameterized Cypher templates), `evaluate_rule_mappings()` evaluator, `_compose_message()` extracted as the shared What+Where+How-to-fix composer now reused by `_finding()` too
- `test_cg_structure_checks.py`: 17 host-only loader unit tests (`-k structure_rules`, zero Neo4j) plus an 8-test live-Neo4j integration tier (`-k rule_mapped`, `TestRuleMappedChecksIntegration`) proving SC2's Footer-rule pass/fail pair, the height-parameter rule's cgId-convention-token match, the for-all interface check's offending/satisfying split, the Rule_Id soft-foreign-key behaviour, determinism, and project isolation
- Verified in-container after a `--no-cache` rebuild: `tests/test_cg_structure_checks.py -k rule_mapped` -- 8/8 passed; full suite `tests/` -- 541 passed, 1 skipped, 1 deselected, 0 failed

## Task Commits

Each task was committed atomically:

1. **Task 1: structure_rules.json artifact and its defensive loader** - `cf99b6a` (feat)
2. **Task 2: Operation templates and the rule-mapping evaluator** - `6c1ff11` (feat)
3. **Task 3: Rule-mapping tests - loader unit tier and SC2 integration tier** - `a3df1a0` (test, includes the Task 1 mapping-data fix below)

**Plan metadata:** (pending -- final commit below)

## Files Created/Modified
- `llm/structure_rules.json` - versioned declarative rule-mapping artifact, 4 seeded mappings
- `data-service/cg_structure_checks.py` - loader trio + operation templates + evaluator (+279/+121 lines across two commits)
- `data-service/tests/test_cg_structure_checks.py` - 17 loader unit tests + 8 rule-mapped integration tests

## Decisions Made
- `_FORBIDDEN_PARAM_KEYS` fixed to the eight value-comparison forms (`min`, `max`, `greaterThan`, `lessThan`, `greaterThanOrEqual`, `lessThanOrEqual`, `threshold`, `value`) -- pinned by a test parameterized over the frozenset itself, so widening the module automatically widens coverage (T-37-10).
- `forbidsOrphan`'s label allow-list (`_COMPUTGRAPH_ORPHAN_LABELS`) excludes `Object` -- it is the Computgraph root and structurally has no owner, so the check would be vacuously true/meaningless for it.
- `requiresInterface` implemented as a for-all requirement (every scoped Procedure needs >=1 matching Interface), explicitly commented as different from the two exists-style operations, per the plan's instruction not to let it silently collapse into an exists check.
- `_compose_message()` extracted from `_finding()`'s inline f-string so both SVAL-01 findings and the new SVAL-02 rule results are built through one shared composer, as the plan explicitly required.
- Rejected mappings surface in `evaluate_rule_mappings()`'s output as `passed=false` with an `"INVALID MAPPING -- not evaluated."`-prefixed message (a distinct signal), rather than being silently dropped from the report.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `R_STRUCT_PROC_INTERFACE_V`'s `ifaceType: "Input"` filter could never pass against the real Frame fixture**
- **Found during:** Task 3, live-Neo4j integration test (`test_rule_mapped_interface_rule_fails_on_interface_stripped_and_passes_on_full_frame`)
- **Issue:** The plan's Task 1 seeded `R_STRUCT_PROC_INTERFACE_V` with `params: {"ifaceType": "Input"}`. `requiresInterface` is a for-all check across every Procedure in scope. The Frame fixture's procedure 12 (Footer, `source: "recognized"`) carries exactly one Interface, `FooterFrame`, typed `Output` -- never `Input`. With the `Input` filter bound, procedure 12 could never satisfy the check, so the full Frame (the well-formed baseline) would always fail this rule -- directly contradicting the plan's own required behaviour ("the interface rule ... passes against the full Frame").
- **Fix:** Removed the `ifaceType` filter from `R_STRUCT_PROC_INTERFACE_V`'s `params` (now `{}`) and reworded its description to "Every Procedure must expose at least one Interface" (dropping the "input" qualifier). With no type filter, the full Frame passes (procedure 11 has an Input interface, procedure 12 has an Output interface -- both satisfy "at least one"), and the interface-stripped variant still fails with exactly procedure 11 as the offending entity (procedure 12's Output interface is untouched by that fixture mutation) -- matching the plan's literal required test behaviour without altering the frozen `cg_fixtures.py` builders.
- **Files modified:** `llm/structure_rules.json`
- **Verification:** `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -q -k rule_mapped` -- 8/8 passed (was 7 passed, 1 failed before the fix); full in-container suite re-verified green after the fix.
- **Committed in:** `a3df1a0` (Task 3 commit, alongside the new tests that surfaced the mismatch)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix is a one-field data correction to the seeded mapping, made necessary by a mismatch between the plan's literal params instruction and the real (frozen, parser-faithful) fixture data it was meant to validate against. The operation's for-all semantics and offending/satisfying-entity reporting are unchanged and fully exercised by both the passing and failing variants. No scope creep.

## Issues Encountered
- Two `docker compose build --no-cache data-service` + `up -d data-service` rebuild cycles were required: once before the first in-container run (documented image-staleness gotcha from `37-01`/`37-03`), and once more after the `structure_rules.json` fix above, since the file is baked into the image rather than volume-mounted in this environment. Both rebuilds completed in ~20s; the full in-container suite was re-verified green after the second rebuild.
- Initial test name `test_rule_mapped_height_parameter_rule_passes_with_convention_token_match` accidentally matched pytest's `-k convention` substring filter (via `..._convention_token_match`), causing it to run on the host without live Neo4j and fail with a DNS resolution error. Renamed to `test_rule_mapped_height_parameter_rule_passes_via_cg_id_suffix_match` to avoid the substring collision -- caught immediately by the plan's own host-only verification step before any commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `llm/structure_rules.json` is the extension point future waves (v10) grow -- adding a mapping entry requires no code change as long as it uses one of the four existing operations; adding a fifth operation requires one new template in `_OPERATION_TEMPLATES` plus one new `_eval_*` function.
- `evaluate_rule_mappings()`'s output shape (`ruleId`, `operation`, `passed`, `ruleExists`, `message`, `satisfyingEntities`, `offendingEntities`) is the literal target for Plan 37-05's `POST /computgraph/validate` route, which assembles `run_structural_checks()` (SVAL-01, Plan 37-03) and `evaluate_rule_mappings()` (SVAL-02, this plan) into the `findings[]`/`ruleResults[]`/`counts` report contract `spec/API.md` already documents.
- No blockers.

---
*Phase: 37-script-structure-validation*
*Completed: 2026-07-27*

## Self-Check: PASSED

All created/modified files confirmed present on disk (`llm/structure_rules.json`, `cg_structure_checks.py`, `test_cg_structure_checks.py`, `37-04-SUMMARY.md`); all three task commit hashes (`cf99b6a`, `6c1ff11`, `a3df1a0`) confirmed present in `git log --oneline --all`.
