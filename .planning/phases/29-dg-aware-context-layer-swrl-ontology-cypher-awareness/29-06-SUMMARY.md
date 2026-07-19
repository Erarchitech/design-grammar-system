---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 06
subsystem: api
tags: [python, fastapi, neo4j, cypher, llm-context, dg_context]

# Dependency graph
requires:
  - phase: 29-03
    provides: assemble_context() core assembler + ContextAssembleRequest + fetch_existing_entities() D-17 pattern
  - phase: 29-04
    provides: validate_cypher() schema/verb-policy validator (CTXA-04 primary security control)
provides:
  - VALIDGRAPH_CONCEPTS describing the REAL shipped ValidationRun/statePayloadJson/HAS_ENTITY shape (not the aspirational DesignState/Run nodes)
  - validate_cypher() ALLOWED_LABELS/ALLOWED_RELATIONSHIPS converged to the same real shape (ValidationRun/ValidationEntity/HAS_ENTITY; DesignState/Run/HAS_STATE removed)
  - _summarize_state_payload() -- v4 ObjState/ParamState/PropState count breakdown parsed from statePayloadJson
  - fetch_existing_design_states() -- live per-project ValidationRun union (D-17 pattern), wired into assemble_context() as existing_design_states for graph_query only
affects: [29-07, n8n graph-query-mcp.json Build Cypher Prompt, LLM Cypher generation for design-state questions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Schema-truth convergence: dg_context.py's LLM-facing schema description must mirror the REAL write path (app.py) exactly, not an aspirational/documented-only shape -- verified by reading store_validation_run()/list_validation_runs()/_project_state_summary() before editing"
    - "fetch_existing_design_states() mirrors fetch_existing_entities()'s D-17 injectable-session pattern for a second ValidGraph-layer live query"

key-files:
  created: []
  modified:
    - data-service/dg_context.py
    - data-service/tests/test_dg_context.py

key-decisions:
  - "VALIDGRAPH_CONCEPTS.node_labels -> ValidationRun/ValidationEntity/IntegrationConfig (DesignState/Run removed); added design_state_storage prose + state_payload_json_shape dict documenting the v2 envelope; design_state_kinds preserved (now framed as statePayloadJson entry kinds, not node labels)"
  - "ALLOWED_LABELS gains ValidationRun, loses DesignState/Run; ALLOWED_RELATIONSHIPS gains HAS_ENTITY, loses HAS_STATE -- validate_cypher() now actively rejects MATCH (:DesignState ...) as unknown_label for graph_query"
  - "_summarize_state_payload() is a lightweight port of app.py's _project_state_summary(), extended with a 3-way kind count breakdown (objStateCount/paramStateCount/propStateCount) instead of a single flat parameterCount, since the LLM needs v4 kind values it cannot get from the opaque JSON string"
  - "fetch_existing_design_states() binds $graph=VALIDATION_GRAPH and $project as parameters (never string-interpolated, T-29-06) and mirrors list_validation_runs()'s graph filter exactly, so results match what the user sees in the Model Viewer"
  - "FLAGGED BACKLOG (recorded, NOT implemented): direction 'b' -- materializing first-class :DesignState graph nodes in store_validation_run() -- is an architectural/data-model decision affecting production data, the Grasshopper publish path, and other ValidationRun consumers; needs explicit human sign-off and its own phase per CLAUDE.md"

patterns-established:
  - "Pattern: when an LLM-facing schema description drifts from the real write path, fix by reading the write path's live Cypher first (store_validation_run/list_validation_runs), then converge the schema constants + validator allow-lists together in one task, with a regression-guard test asserting the buggy pattern is now rejected"

requirements-completed: [CTXA-01, CTXA-04]

coverage:
  - id: D1
    description: "VALIDGRAPH_CONCEPTS + validate_cypher() allow-lists converged to the real ValidationRun/statePayloadJson/HAS_ENTITY shape; DesignState/Run/HAS_STATE removed; design_state_kinds preserved"
    requirement: "CTXA-04"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestValidgraphConceptsRealShape and ::TestValidator::test_validationrun_match_is_allowed_for_graph_query / test_has_entity_relationship_is_allowed_for_graph_query / test_designstate_match_is_rejected_as_unknown_label_for_graph_query"
        status: pass
    human_judgment: false
  - id: D2
    description: "_summarize_state_payload() + fetch_existing_design_states() live helper wired into assemble_context() as existing_design_states (graph_query only), project-scoped via bound parameters"
    requirement: "CTXA-01"
    verification:
      - kind: unit
        ref: "data-service/tests/test_dg_context.py::TestExistingDesignStates (all 6 tests)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-19
status: complete
---

# Phase 29 Plan 06: Converge Validgraph schema + live design-state data to the real ValidationRun shape

**Fixed the "no design states were found" gap by converging `dg_context.py`'s Validgraph schema description and `validate_cypher()` allow-lists to the real `ValidationRun.statePayloadJson`/`HAS_ENTITY` shape, and adding a live `fetch_existing_design_states()` helper (D-17 pattern) wired into `assemble_context()` for graph_query.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-19
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `VALIDGRAPH_CONCEPTS` now describes the REAL shipped shape (`ValidationRun`/`ValidationEntity`/`IntegrationConfig` node labels, `HAS_ENTITY` relationship, a `design_state_storage` prose explanation, and a `state_payload_json_shape` dict documenting the v2 envelope) instead of the aspirational `DesignState`/`Run` nodes that were never materialized by the real write path.
- `validate_cypher()`'s `ALLOWED_LABELS`/`ALLOWED_RELATIONSHIPS` converged to match: `ValidationRun` added, `DesignState`/`Run` removed; `HAS_ENTITY` added, `HAS_STATE` removed. A `MATCH (:DesignState ...)` query for `graph_query` is now actively rejected as `unknown_label` — the exact bug root cause (29-UAT.md Success Criterion 4) turned into a corrective-feedback retry signal instead of a silent zero-row result.
- New `_summarize_state_payload()` parses `statePayloadJson` into a v4 kind breakdown (`objStateCount`/`paramStateCount`/`propStateCount`) — a lightweight port of `app.py`'s `_project_state_summary()`, extended because the LLM needs the per-kind counts and the raw JSON string is opaque to a Cypher `MATCH`.
- New `fetch_existing_design_states()` live-queries `ValidationRun` per project (mirroring `list_validation_runs()`'s graph filter exactly, `$graph`/`$project` bound as parameters, deterministic `ORDER BY ... LIMIT 25`), wired into `assemble_context()` as a top-level `existing_design_states` key for `graph_query` requests only.

## Task Commits

Each task followed RED (failing test) → GREEN (implementation):

1. **Task 1: Converge VALIDGRAPH_CONCEPTS + validate_cypher allow-lists**
   - `36d80a3` - test(29-06): add failing tests for ValidationRun/HAS_ENTITY allow-list convergence
   - `371e946` - feat(29-06): converge VALIDGRAPH_CONCEPTS + validate_cypher allow-lists to real ValidationRun shape
2. **Task 2: Add live existing-design-states helper + wire into graph_query context**
   - `fd10bc4` - test(29-06): add failing tests for existing-design-states helper + assemble_context wiring
   - `c5c83b5` - feat(29-06): add live existing-design-states helper wired into graph_query context

## Files Created/Modified

- `data-service/dg_context.py` - VALIDGRAPH_CONCEPTS rewritten to the real shape; ALLOWED_LABELS/ALLOWED_RELATIONSHIPS converged; VALIDATION_GRAPH constant, `_summarize_state_payload()`, `fetch_existing_design_states()` added; `assemble_context()` wired for graph_query
- `data-service/tests/test_dg_context.py` - `TestValidgraphConceptsRealShape` (2 tests), 3 new `TestValidator` cases (ValidationRun-allowed, HAS_ENTITY-allowed, DesignState-rejected regression guard), `TestExistingDesignStates` (6 tests: `_summarize_state_payload` v2/None/malformed/v1-fallback, `fetch_existing_design_states` parsed-rows-and-bound-project, `assemble_context` graph_query-inclusion and rule_ingest-exclusion)

## Decisions Made

- Kept `design_state_kinds`/`DESIGNSTATE_KINDS` as-is (now reframed as statePayloadJson entry kinds rather than node-label properties) — out of this gap's scope to remove the now-moot `bad_kind_enum` DesignState check, per plan instruction.
- Left `VALIDATES` relationship untouched in the allow-list — not named as aspirational in the gap scope.
- Recorded direction "b" (materializing first-class `:DesignState` nodes in `store_validation_run()`) as FLAGGED BACKLOG per the plan's explicit scope guard — NOT implemented; it is an architectural/data-model decision requiring human sign-off and its own phase.

## Deviations from Plan

None - plan executed exactly as written. Both tasks followed the plan's RED→GREEN sequence precisely; no auto-fixes, no architectural changes, no scope creep.

## Issues Encountered

None. Docker was reachable throughout; both in-container test runs (build → up → pytest) executed cleanly on the first attempt after each set of edits.

## Verification

- `docker compose build data-service && docker compose up -d data-service && docker compose exec -T data-service pytest tests/test_dg_context.py -x` — run twice (once per task's GREEN gate). Final state: **52/52 passed** in `test_dg_context.py`.
- `docker compose exec -T data-service pytest -q` (full data-service suite) — **220/220 passed**, no regressions. (The plan's note about one expected pre-existing failure, `test_publish_validation_missing_config`, was not observed — the full suite is fully green.)
- Regression guard confirmed live: `MATCH (:DesignState ...)` for `graph_query` now yields `unknown_label`; `MATCH (:ValidationRun ...)` and `HAS_ENTITY` traversal validate clean.
- `test_bad_kind_enum_is_caught` still passes — membership assertion (`"bad_kind_enum" in codes`) holds even though the same Cypher now also yields `unknown_label` (not weakened, per plan instruction).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `existing_design_states` context key is ready for Plan 29-07 to forward into the n8n `graph-query-mcp.json` "Build Cypher Prompt" node, alongside the corrected `validgraph` schema description.
- Backlog item recorded for a future phase: materializing first-class `:DesignState` graph nodes (direction "b") — needs explicit human sign-off before scheduling, per CLAUDE.md's hard-to-reverse-decision guidance.

---
*Phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness*
*Completed: 2026-07-19*

## Self-Check: PASSED

- FOUND: data-service/dg_context.py
- FOUND: data-service/tests/test_dg_context.py
- FOUND: .planning/phases/29-dg-aware-context-layer-swrl-ontology-cypher-awareness/29-06-SUMMARY.md
- FOUND commit: 36d80a3
- FOUND commit: 371e946
- FOUND commit: fd10bc4
- FOUND commit: c5c83b5
