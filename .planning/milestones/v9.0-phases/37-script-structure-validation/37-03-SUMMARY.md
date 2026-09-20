---
phase: 37-script-structure-validation
plan: 03
subsystem: api
tags: [neo4j, cypher, computgraph, structural-validation, pytest, deterministic]

requires:
  - phase: 37-01
    provides: cg_fixtures.py parser-faithful Frame envelope builders (FIXTURE_PROJECT isolation)
  - phase: 37-02
    provides: spec/API.md normative POST /computgraph/validate contract + checkId/entity key vocabulary
provides:
  - "data-service/cg_structure_checks.py: seven deterministic, LLM-free structural checks over the published Computgraph (SVAL-01) with a shared finding/entity constructor and byte-identical repeated-call determinism"
  - "data-service/tests/test_cg_structure_checks.py: two-tier test suite (14 host-only unit tests, 6 live-Neo4j integration tests)"
  - "data-service/tests/conftest.py: registered `integration` pytest marker"
affects: [37-05, 37-06]

tech-stack:
  added: []
  patterns:
    - "Session-injected, single-query, project+definitionId-scoped Cypher checks mirroring computgraph_publish.py's caller-owns-the-session discipline"
    - "JSON-envelope check (not a graph pattern) for facts that never reach the published graph as raw strings -- read Algorithm.contextJson, JSON-parse in Python"
    - "Minimal read-only session double (a bare object exposing `run`) for unit-testing a single-query check, distinct from the write-oriented FakeGraph harness"

key-files:
  created:
    - data-service/cg_structure_checks.py
    - data-service/tests/test_cg_structure_checks.py
  modified:
    - data-service/tests/conftest.py

key-decisions:
  - "Algorithm entities in findings carry cgId='' and the algIndex rendered into `name` -- Algorithm nodes have no cgId in the Phase 36 published contract; documented in-code so a reader doesn't mistake it for an omission"
  - "check_parameters_without_datatype / check_objects_without_behavior implemented as deliberate defensive guards (both currently unreachable post-publish per computgraph_publish.py's ValueError validation) rather than dropped, per 37-RESEARCH.md's Open Question 2 recommendation"
  - "run_structural_checks sorts by (checkId, first entity cgId, message) -- the literal determinism guarantee spec/API.md and the plan's must_haves require"

requirements-completed: [SVAL-01]

coverage:
  - id: D1
    description: "Six session-injected, parameterized structural checks (orphan_pattern, procedure_without_interface, dangling_param_link, algorithm_without_procedure, and the two defensive guards) each issue exactly one bound-parameter Cypher query scoped by project and definitionId, with a shared finding/entity constructor and zero string-interpolated Cypher"
    requirement: "SVAL-01"
    verification:
      - kind: unit
        ref: "python -c one-liner asserting convention_name_from_cg_id/_finding/_entity/CHECK_IDS shapes -- pass"
        status: pass
      - kind: integration
        ref: "data-service/tests/test_cg_structure_checks.py::TestStructuralChecksIntegration (docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k structural -q)"
        status: pass
    human_judgment: false
  - id: D2
    description: "check_annotation_conventions reads Algorithm.contextJson and JSON-parses its top-level warnings array via the total-function parse_context_warnings (never raises on degenerate input); run_structural_checks aggregates all seven checks in CHECK_IDS order, sorted deterministically"
    requirement: "SVAL-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_cg_structure_checks.py -k convention (14 tests, host, no Neo4j)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Two-tier test suite: unit tier (parse_context_warnings degenerate inputs, convention_name_from_cg_id, finding/entity key shapes, check_annotation_conventions against a minimal session double) and integration tier (live Neo4j: zero-violation baseline on the full Frame, SC1 exact-procedure naming on the interface-stripped variant, defensive-check wiring, determinism, project isolation, definitionId isolation)"
    requirement: "SVAL-01"
    verification:
      - kind: unit
        ref: "python -m pytest data-service/tests/test_cg_structure_checks.py -q -k convention -- 14 passed"
        status: pass
      - kind: integration
        ref: "docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -q -k structural -- 6 passed"
        status: pass
      - kind: integration
        ref: "docker compose exec data-service python -m pytest tests/ -q -- 516 passed, 0 failed"
        status: pass
    human_judgment: false
  - id: D4
    description: "SC4 gate: cg_structure_checks.py contains zero references to the LLM gateway or any adapter generate call, in code or comments"
    requirement: "SVAL-01"
    verification:
      - kind: other
        ref: "grep -v '^\\s*#' data-service/cg_structure_checks.py | grep -c 'llm_gateway\\|adapter\\.generate' -- 0"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-07-27
status: complete
---

# Phase 37 Plan 03: Computgraph Structural Checks (SVAL-01) Summary

**`data-service/cg_structure_checks.py` -- seven deterministic, LLM-free Cypher/JSON checks over the published Computgraph (orphan Pattern, Procedure-without-Interface, dangling PARAM_LINK, Algorithm-without-Procedure, two defensive guards, and a contextJson-derived annotation-convention check), verified against live Neo4j with a two-tier pytest suite.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-27T13:35:00+03:00 (first task commit)
- **Completed:** 2026-07-27T13:41:20+03:00 (last task commit)
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `cg_structure_checks.py`: `SEVERITY_*` constants, `CHECK_IDS` (7-tuple), `convention_name_from_cg_id()`, `_entity()`/`_finding()` shared constructors composing the What+Where+How-to-fix message discipline, six graph-shape check functions (five real + two defensive), `parse_context_warnings()` (total function, never raises), `check_annotation_conventions()` reading `Algorithm.contextJson` rather than attempting an impossible graph-pattern match, and `run_structural_checks()` aggregating all seven in deterministic sorted order
- `test_cg_structure_checks.py`: 14 host-only unit tests (`-k convention`, zero Neo4j) plus a 6-test live-Neo4j integration tier (`-k structural`, `integration` marker) that publishes the full Frame + interface-stripped + footer-less envelope variants and proves the zero-violation baseline, SC1 exact-procedure naming (name AND cgId), defensive-check non-firing, byte-identical determinism, and both project- and definitionId-scoped isolation
- `conftest.py`: registered the `integration` marker (not deselected by default, matching the plan's instruction)
- Verified in-container: full suite `516 passed, 1 skipped, 1 deselected, 0 failed` (data-service container rebuilt with `--no-cache` first, per the documented 37-01 image-staleness gotcha)

## Task Commits

Each task was committed atomically:

1. **Task 1: Check module scaffold, finding shape, and the five graph-shape checks** - `ff2a990` (feat)
2. **Task 2: Annotation-convention check via contextJson warnings, plus the aggregator** - `e63987c` (feat)
3. **Task 3: Two-tier test suite - host unit tier and live-Neo4j integration tier** - `ccd9c75` (test)

**Plan metadata:** (pending — final commit below)

## Files Created/Modified
- `data-service/cg_structure_checks.py` - seven SVAL-01 structural checks + shared finding/entity constructors + aggregator (369 lines)
- `data-service/tests/test_cg_structure_checks.py` - two-tier test suite (14 unit + 6 integration tests)
- `data-service/tests/conftest.py` - added `integration` marker registration

## Decisions Made
- Algorithm entities carry `cgId=""` with the `algIndex` rendered into `name` -- Algorithm nodes have no cgId in the Phase 36 published contract; documented in a code comment rather than left as an apparent oversight.
- `parameter_without_datatype` and `object_without_behavior` implemented as deliberate defensive guards even though currently unreachable post-publish (both conditions are pre-empted by `computgraph_publish._build_publish_params`'s `ValueError` validation) -- per 37-RESEARCH.md's Open Question 2 recommendation, cheap insurance against a future publish-path change or a graph mutated outside that path.
- Split the single-file Task 1/Task 2 implementation into two atomic commits by staging a reduced intermediate version first (both tasks target the same new file) -- preserves the plan's one-commit-per-task discipline without altering either task's content.

## Deviations from Plan

None - plan executed exactly as written. Every task's automated verification and acceptance-criteria greps passed on the first attempt; no auto-fixes required.

## Issues Encountered
- The `data-service` container had to be rebuilt (`docker compose build --no-cache data-service && docker compose up -d data-service`) before the integration tier could see the new `test_cg_structure_checks.py` file -- the documented image-staleness gotcha from `37-01-SUMMARY.md`/`data-service/tests/README.md`, not a code defect. Rebuild completed in ~35s; integration tier and full in-container suite both green afterward.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `cg_structure_checks.py` and its normative `entities[]`/`findings[]` shapes are the literal target for Plan 37-04 (SVAL-02 rule-mapped checks, extending this module) and Plan 37-05 (`POST /computgraph/validate` route, assembling `run_structural_checks()`'s output into the report JSON contract `spec/API.md` already documents).
- `check_orphan_patterns`, `check_procedures_without_interface`, and `check_dangling_param_links` are proven against real Neo4j pattern-matches (Pitfall 2 from 37-RESEARCH.md is closed: no correctness claim rests on the FakeGraph duck-typed harness for read-side checks).
- No blockers.

---
*Phase: 37-script-structure-validation*
*Completed: 2026-07-27*

## Self-Check: PASSED

All created/modified files confirmed present on disk (`cg_structure_checks.py`, `test_cg_structure_checks.py`, `conftest.py`, `37-03-SUMMARY.md`); all three task commit hashes (`ff2a990`, `e63987c`, `ccd9c75`) confirmed present in `git log --oneline --all`.
