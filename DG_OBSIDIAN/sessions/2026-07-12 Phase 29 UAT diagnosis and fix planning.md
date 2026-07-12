---
date: 2026-07-12
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
status: diagnosed-and-planned
type: UAT → Diagnosis → Planning
---

## Session Summary

Phase 29 UAT ran with 1 human test (Success Criterion 4: graph_query webhook for design-state questions), which reported failure: "no design states were found despite I see them in Model Viewer - ConfigurationC". Diagnosed root cause and created 3 fix plans (29-06/29-07/29-08) to close the gap.

## Work Done

### UAT Failure Diagnosis
- **Issue:** graph_query webhook (graph-query-mcp.json) returns empty answer for design-state questions, despite runs visible in Model Viewer
- **Root Cause (confirmed by gsd-debugger):** Schema mismatch in `data-service/dg_context.py`
  - Phase 29-03 introduced Validgraph awareness for the first time, using an aspirational schema: separate `:DesignState`/`:Run` nodes with `HAS_STATE` relationships
  - Production's real write path (`store_validation_run()` in app.py) never creates those nodes; it only MERGEs a single `:ValidationRun` node and serializes the design-state snapshot into `run.statePayloadJson` (a JSON string blob)
  - The LLM correctly follows the wrong schema, generates valid `MATCH (ds:DesignState {project:$project})...` Cypher, validator allow-lists it (DesignState is in ALLOWED_LABELS), query executes against live Neo4j with zero errors, returns zero rows (nodes don't exist), n8n reports "no data found"
  - Model Viewer works because it reads the same `ValidationRun.statePayloadJson` directly (list_validation_runs()), not via a DesignState node query
- **Evidence:** Full investigation in `.planning/debug/graph-query-no-design-states-found.md`
  - Traced production write path (store_validation_run), read path (list_validation_runs), and production data model (ValidationRun + statePayloadJson)
  - Confirmed assemble_context() never queries live DesignState data; fetch_existing_entities() only unions Class/DatatypeProperty/ObjectProperty from OntoGraph
  - Confirmed n8n thin-caller wiring is intact (project param threading correct end-to-end)
  - Ruled out project-name casing and the pending ValidationGraph→ValidGraph migration (project-independent structural bug)

### Fix Plans Created
Three plans spawned by gsd-planner (verified by gsd-plan-checker):

1. **29-06** (Wave 1): Converge `dg_context.py` to the real ValidationRun/statePayloadJson shape
   - Rewrite VALIDGRAPH_CONCEPTS to describe ValidationRun + statePayloadJson + HAS_ENTITY + ValidationEntity
   - Update validate_cypher()'s ALLOWED_LABELS/ALLOWED_RELATIONSHIPS to match
   - Add fetch_existing_design_states() + _summarize_state_payload() (port of app.py's real _project_state_summary)
   - Wire into assemble_context() for graph_query requests only
   - Key regression guard: validator now rejects :DesignState as unknown_label (turns silent-empty-result into corrective feedback)
   - TDD; 40 existing tests green (including test_bad_kind_enum_is_caught, test_graph_query_design_states_surfaces_v4_kind_enum)

2. **29-07** (Wave 2, depends on 29-06): Wire the live design-state summary into n8n
   - Forward existing_design_states from /context/assemble into the Build Cypher Prompt node
   - Re-sync live n8n instance (patch-based, versionCounter tracking)

3. **29-08** (Wave 3, depends on both): Deploy, smoke test, human verify
   - Blocking human-verify checkpoint re-runs Success Criterion 4 against ConfigurationC (exact failing scenario)
   - Requires that design-state question no longer returns "no data found"

### Scope Decision (Honored)
Plans implement direction (a) only — converge the assembler/validator to the REAL shape. Direction (b) — materialize first-class :DesignState graph nodes in production to match CLAUDE.md's canonical schema — is flagged as a backlog item requiring human sign-off (touches Grasshopper plugin, existing data, other consumers, broader schema implications). Not silently executed.

### Key Notes
- The aspirational :DesignState/:Run schema comes from migrations/2026-07-03 and test/seed_designstates.cypher — well-intentioned but unconverged with production
- CLAUDE.md's Graph Schema v4 section already commits to DesignState-node model as canonical, so the larger decision (option b) has architectural weight — correctly flagged for human review rather than auto-executed
- Pre-existing test failure (test_publish_validation_missing_config) is unrelated, already logged in deferred-items.md from 29-01

## Next Steps

Execute the three fix plans with `/gsd-execute-phase 29 --gaps-only`
- Waves run sequentially (1 → 2 → 3)
- 29-08 will pause at the human-verify checkpoint for ConfigurationC test re-run

## Files Changed This Session
- `.planning/phases/29-dg-aware-context-layer-swrl-ontology-cypher-awareness/29-UAT.md` — updated with diagnosis + root_cause + artifacts + missing

## Related Notes
- [[graph-query-design-states-debug]] — Full root cause investigation
- [[phase-29-fix-plans]] — 29-06, 29-07, 29-08 plan details
