---
status: diagnosed
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
source: [29-VERIFICATION.md]
started: 2026-07-12T21:40:00Z
updated: 2026-07-12T22:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Success Criterion 4 — Live end-to-end natural-language design-state query
expected: The graph_query webhook returns a correct answer that references v4 DesignState
  kind values (ObjState/ParamState/PropState) sourced from a live Neo4j project, exercising
  the full n8n -> POST /context/assemble -> POST /context/generate-cypher -> Neo4j ->
  LLM-answer-synthesis path end-to-end. Requires a configured LLM provider
  (Anthropic/OpenAI/Ollama) and real project data — cannot be exercised by static
  grep/pytest.
result: issue
reported: "no design states were found despite I see them in Model Viewer - ConfigurationC"
severity: major

## Summary

total: 1
passed: 0
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "The graph_query webhook returns a correct answer that references v4 DesignState kind values (ObjState/ParamState/PropState) sourced from a live Neo4j project, exercising the full n8n -> POST /context/assemble -> POST /context/generate-cypher -> Neo4j -> LLM-answer-synthesis path end-to-end."
  status: failed
  reason: "User reported: no design states were found despite I see them in Model Viewer - ConfigurationC"
  severity: major
  test: 1
  root_cause: "dg_context.py's assemble_context() feeds the LLM a static, aspirational Validgraph schema (VALIDGRAPH_CONCEPTS: node_labels=[DesignState, Run]) that does not match the real shipped write path. Production's store_validation_run() (app.py) MERGEs a single :ValidationRun node per run with the whole design-state snapshot serialized into run.statePayloadJson -- it never creates separate :DesignState nodes (those exist only in test fixtures / an unconverged migration). The LLM correctly follows the wrong schema it was given, generates a valid MATCH (ds:DesignState {project:$project}) query, validate_cypher() allow-lists it (DesignState/Run are in ALLOWED_LABELS but the real ValidationRun/HAS_ENTITY shape is not), it executes against live Neo4j with zero errors, and returns zero rows because no :DesignState nodes exist. Model Viewer shows design states because it reads the same ValidationRun.statePayloadJson blob directly (list_validation_runs()), not via a DesignState node query. Predates Phase 29 (pre-29 prompt had zero Validgraph awareness); Phase 29-03 added the awareness for the first time with the wrong schema, only surfaced by this UAT run. Project-name casing and the pending ValidationGraph->ValidGraph migration were both ruled out (project-independent, structural bug)."
  artifacts:
    - path: "data-service/dg_context.py"
      issue: "VALIDGRAPH_CONCEPTS describes an unimplemented :DesignState/:Run node model; fetch_existing_entities() never covers the Validgraph layer; validate_cypher()'s ALLOWED_LABELS/ALLOWED_RELATIONSHIPS recognize DesignState/Run/HAS_STATE but not the real ValidationRun/HAS_ENTITY shape"
    - path: "data-service/app.py"
      issue: "store_validation_run() / list_validation_runs() are the real (only) live implementation of design-state persistence, keyed on ValidationRun.statePayloadJson -- the schema assemble_context() should have described"
  missing:
    - "Update VALIDGRAPH_CONCEPTS (and validate_cypher's allow-lists) to describe the real shipped shape: ValidationRun node + statePayloadJson JSON blob + HAS_ENTITY -> ValidationEntity, instead of the aspirational separate :DesignState/:Run nodes"
    - "Add a live 'existing design states' helper (analogous to fetch_existing_entities()) so graph_query context includes real per-project ValidationRun/statePayloadJson data, since raw Cypher can't cleanly introspect JSON-string internals for the LLM"
    - "Decide and document the long-term direction: either converge dg_context.py's schema to match production (smaller, immediate fix), or converge store_validation_run() to also materialize real :DesignState graph nodes (larger, matches the canonical v4/v7 ontology/migration model already committed to elsewhere in the codebase) -- CLAUDE.md's schema table and the migration apparatus already assume the DesignState-node model is canonical, so this decision has broader consequences than this one bug"
  debug_session: .planning/debug/graph-query-no-design-states-found.md
