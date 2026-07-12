---
name: graph-query-design-states-schema-mismatch
date: 2026-07-12
phase: 29
severity: major
status: diagnosed-and-planned-fix
---

## Bug: graph_query Returns "No Design States Found" Despite Visible Data

**Reported:** Phase 29 UAT, Success Criterion 4 test for ConfigurationC project
**User observation:** "no design states were found despite I see them in Model Viewer - ConfigurationC"

## Root Cause

**Schema mismatch in `data-service/dg_context.py` between aspirational and production data models.**

### The Problem
1. **Aspirational schema** (what dg_context.py describes):
   - Separate `:DesignState` and `:Run` nodes in ValidGraph
   - `HAS_STATE` relationship connecting them
   - Introduced by Phase 29-03, first time Validgraph awareness added to LLM context

2. **Real production schema** (what app.py actually implements):
   - Single `:ValidationRun` node per validation run
   - Entire design-state snapshot serialized in `run.statePayloadJson` (JSON string blob)
   - No separate `:DesignState` nodes ever created by the write path (`store_validation_run()`)
   - Documented in migrations/2026-07-03 header: shipped runtime uses ValidationEntity, ValidationRun, IntegrationConfig

3. **The query failure**:
   - LLM follows the aspirational schema, generates: `MATCH (ds:DesignState {project:$project}) ...`
   - Validator allow-lists it (`:DesignState` is in ALLOWED_LABELS)
   - Query executes successfully, returns zero rows (nodes don't exist)
   - n8n Parse Answer → "no data found"
   - **No error surfaced** — silent empty result looks like a data absence, not a schema bug

### Why Model Viewer Works
The Model Viewer directly reads `ValidationRun.statePayloadJson` via `list_validation_runs()` (app.py L677-721), parsing the JSON blob in Python rather than querying a DesignState node graph. So the user sees design states in the UI but the LLM can't find them.

## Evidence Trail

| File | Finding |
|------|---------|
| `data-service/dg_context.py:328-369` | `assemble_context()` feeds `VALIDGRAPH_CONCEPTS` (describes :DesignState/:Run) but never queries live DesignState data |
| `data-service/dg_context.py:385-407` | `validate_cypher()` ALLOWED_LABELS include DesignState/Run; missing ValidationRun/HAS_ENTITY |
| `data-service/dg_context.py:92-110` | `fetch_existing_entities()` query filters only `(Class OR DatatypeProperty OR ObjectProperty) AND graph='OntoGraph'`; never covers ValidGraph |
| `data-service/app.py:441-499` | `store_validation_run()` MERGEs `:ValidationRun`, never `:DesignState` |
| `data-service/app.py:634-674` | `_project_state_summary()` parses `statePayloadJson` blob directly; real source of truth for design states |
| `migrations/2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher` | Own header admits shipped runtime used ValidationRun/ValidationEntity, not DesignState nodes |
| `test/seed_designstates.cypher` | Only test fixture creating :DesignState nodes; never converged into production |

## When This Surfaced

Phase 29-03 was the first code to teach the LLM about Validgraph at all. The aspirational schema came from the migration apparatus and test fixtures (well-intentioned but unconverged), not the production code. When Phase 29-05 wired the graph_query workflow end-to-end and UAT exercised a design-state question for the first time, the mismatch became user-visible.

## Fix Direction

**Planned (29-06/29-07/29-08):** Converge the assembler/validator to describe the REAL ValidationRun/statePayloadJson shape. Add a live helper (fetch_existing_design_states) so the LLM gets real per-project data, since JSON string introspection requires Python parsing, not raw Cypher.

**Out-of-scope (flagged as backlog):** Materialize actual :DesignState nodes in production (`store_validation_run()`) to match CLAUDE.md's canonical schema — this is a larger decision touching the Grasshopper plugin write path, existing data, and multiple consumers.

## Anti-Recurrence

Plan 29-06 adds a regression guard: the validator will reject `MATCH (:DesignState ...)` as `unknown_label` once the fix lands, turning silent empty results back into corrective-feedback retries that steer the LLM to the correct shape.
