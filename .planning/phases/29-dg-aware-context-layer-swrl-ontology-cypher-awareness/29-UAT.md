---
status: resolved
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
source: [29-VERIFICATION.md]
started: 2026-07-12T21:40:00Z
updated: 2026-07-20T00:00:00Z
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
result: pass
verified: |
  2026-07-20 — Live re-run confirmed both halves of SC4:
  (1) Routing: docker compose logs showed the exact required sequence for the live
  graph-query webhook call — POST /context/assemble 200, POST /context/generate-cypher 200,
  POST /mcp 200, POST /llm/generate 200. The n8n paste-in fix (re-syncing
  graph-query-mcp.json) resolved the stale-workflow routing bug.
  (2) Grounded answer: fetched GET /execution-result/210 — the synthesized answer cited a
  real runId (a547014ebd824a269c36fd681eb4b1ec), a real timestamp, and real
  statePayloadJson content with stateId DS_44B87E4ED3060032 and ObjState entries
  (OS_... prefixes) — the correct v4 ID scheme, not a "no design states found" hallucination.
  Cosmetic, non-blocking: one state label rendered "ConfigurationС" with a Cyrillic С
  (U+0421) instead of Latin C — looks like a pre-existing data-entry artifact, not caused
  by this fix; not investigated further.
note: |
  CODE FIX APPLIED AND DATA-SERVICE-VERIFIED (29-06 + 29-07, committed).
  - validate_cypher() now rejects :DesignState (both `{...}` and bare `)` forms) as
    unknown_label and accepts :ValidationRun (confirmed in-container).
  - /context/assemble for a real populated project (v8-ui-smoke) returns existing_design_states
    with 21 real ValidationRun entries; validgraph.node_labels is the ValidationRun shape.
  - /context/generate-cypher validates + retries (never leaks invalid Cypher).
  LIVE END-TO-END STILL PENDING — deferred to MANUAL verification (user decision, 2026-07-19):
  - Original target ConfigurationC has zero ValidationRun data in the live Neo4j; verification
    re-pointed to v8-ui-smoke (the only project with queryable design-state data).
  - The live n8n `dg/graph-query` webhook is NOT executing the synced context-layer workflow:
    executions hit only /mcp + /llm/generate, never /context/assemble or /context/generate-cypher,
    so the LLM still emits :DesignState queries → "No data found". The active workflow
    (b2c3d4e5) has the correct stored definition, but the live instance isn't running it
    (5 stale duplicate "DG Graph Query" workflows present — known n8n drift). API reactivation
    and a full n8n restart did not change routing.
  - RESOLUTION (user-owned): user will manually paste n8n/workflows/graph-query-mcp.json into
    the n8n editor, then re-run the v8-ui-smoke design-state query and confirm the data-service
    logs show POST /context/assemble + /context/generate-cypher and the answer references real
    design states. Mark this test `pass` after that manual check succeeds.
severity: major

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps (historical — resolved 2026-07-20, kept for record)

- truth: "The graph_query webhook returns a correct answer that references v4 DesignState kind values (ObjState/ParamState/PropState) sourced from a live Neo4j project, exercising the full n8n -> POST /context/assemble -> POST /context/generate-cypher -> Neo4j -> LLM-answer-synthesis path end-to-end."
  status: fix-applied-pending-manual-verification
  resolution: "Code fix applied and data-service-verified in Phase 29 gap-closure plans 29-06 (dg_context.py: VALIDGRAPH_CONCEPTS + validate_cypher converged to the real ValidationRun/statePayloadJson/HAS_ENTITY shape; DesignState/Run removed from allow-list and now rejected as unknown_label; fetch_existing_design_states() + _summarize_state_payload() added and wired into assemble_context; 52/52 dg_context tests + 220/220 data-service suite green) and 29-07 (graph-query-mcp.json Build Cypher Prompt forwards existing_design_states). Verified live at the data-service layer: /context/assemble for v8-ui-smoke returns 21 real ValidationRun design-state entries; validate_cypher rejects both :DesignState forms. REMAINING (manual, user-owned): the live n8n dg/graph-query webhook is not executing the synced context-layer workflow (executions bypass /context/assemble + /context/generate-cypher; 5 stale duplicate 'DG Graph Query' workflows present). User will manually paste n8n/workflows/graph-query-mcp.json into n8n, then re-run the v8-ui-smoke query to confirm the context layer executes and the answer references real design states. See 29-08-SUMMARY.md."
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
