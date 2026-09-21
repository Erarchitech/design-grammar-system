---
status: diagnosed
trigger: "Investigate issue: graph-query-no-design-states-found (Phase 29 UAT Success Criterion 4 — user reported: 'no design states were found despite I see them in Model Viewer - ConfigurationC')"
created: 2026-07-12T22:10:00Z
updated: 2026-07-12T22:40:00Z
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  status: diagnosed
---

## Current Focus

hypothesis: CONFIRMED — see Resolution.root_cause
test: n/a (goal: find_root_cause_only — no fix applied)
expecting: n/a
next_action: return ROOT CAUSE FOUND to caller

## Symptoms

expected: The graph_query webhook returns a correct answer that references v4 DesignState kind values (ObjState/ParamState/PropState) sourced from a live Neo4j project, exercising the full n8n -> POST /context/assemble -> POST /context/generate-cypher -> Neo4j -> LLM-answer-synthesis path end-to-end.
actual: "no design states were found despite I see them in Model Viewer - ConfigurationC"
errors: None reported by the user (no error message, just an empty/negative-result answer)
reproduction: Test 1 in .planning/phases/29-dg-aware-context-layer-swrl-ontology-cypher-awareness/29-UAT.md — trigger the graph-query-mcp.json webhook with a natural-language question about design states for project "ConfigurationC"
started: Discovered during Phase 29 UAT, immediately after Plan 29-05 reduced this workflow's prompt nodes to thin HTTP callers of /context/assemble + /context/generate-cypher

## Eliminated

- hypothesis: Project name mismatch / casing issue (ConfigurationC vs configurationc vs whitespace) between the webhook payload and Neo4j's stored `project` property.
  evidence: ui-v2/src/lib/graphApi.js `queryGraph()` sends `{project: p, project_name: p}` where `p` is the exact string chosen in the UI (no case transform). n8n's "Set Input Defaults" node reads `project_name` verbatim from the body with no normalization. The failure is structural (wrong node label targeted), not a string-matching issue — reproducible regardless of project name.
  timestamp: 2026-07-12T22:25:00Z

- hypothesis: n8n thin-caller wiring bug from Plan 29-05 — project param dropped/hardcoded in the HTTP Request node bodies.
  evidence: Read n8n/workflows/graph-query-mcp.json in full. "Assemble Context" node body correctly threads `$items('Set Input Defaults')[0].json.project_name` into `/context/assemble`'s `project` field; "Generate Validated Cypher" does the same into `/context/generate-cypher`; "Run Cypher (MCP)" passes `{project: project_name}` as bound Cypher parameters when project_name is truthy. Project threading is intact end-to-end.
  timestamp: 2026-07-12T22:27:00Z

- hypothesis: ConfigurationC's DesignState/Run data is orphaned pre-migration data still tagged `graph='ValidationGraph'` (the pending `migrations/2026-07-07_validationgraph_to_validgraph.cypher`, per STATE.md Pending Todos).
  evidence: That pending-migration item in STATE.md explicitly names project **TestA** (20 runs/1148 entities), not ConfigurationC. More importantly, evidence below shows the real issue is unrelated to graph-value tagging — it's a node-label/data-model mismatch that affects ALL projects, not a stale-tag issue affecting only pre-migration data.
  timestamp: 2026-07-12T22:30:00Z

## Evidence

- timestamp: 2026-07-12T22:12:00Z
  checked: data-service/dg_context.py assemble_context() (Phase 29-03, CTXA-01)
  found: For `graph_query` requests, assemble_context() calls fetch_existing_entities(project) — but that function's query (`_EXISTING_ENTITIES_QUERY`) is hardcoded to `MATCH (n) WHERE (n:Class OR n:DatatypeProperty OR n:ObjectProperty) AND n.graph = 'OntoGraph' AND n.project = $project` — i.e. it unions only OntoGraph entities. The Validgraph layer's "existing entities" (live DesignState/Run instances) are NEVER queried live anywhere in assemble_context(). The only Validgraph information handed to the LLM is the static `VALIDGRAPH_CONCEPTS` dict (schema-level facts: node_labels, key_properties, design_state_kinds enum) — a fixed module-level constant, not a live query.
  implication: The LLM crafting Cypher for a "what design states exist" question has zero live ground truth about DesignState/Run — it must construct a query from schema description alone.

- timestamp: 2026-07-12T22:18:00Z
  checked: n8n/workflows/graph-query-mcp.json — full node/connection graph (Ingest Prompt -> ... -> Parse Answer)
  found: Confirms the pipeline: Assemble Context -> Build Cypher Prompt (thin string-join of the assembled context) -> Generate Validated Cypher (POST /context/generate-cypher) -> Parse Cypher -> Run Cypher (MCP) [real Neo4j execution via MCP neo4j_query] -> Build Answer Prompt -> Generate Answer -> Parse Answer (`"If results are empty, say no data found."`). Project threading (project_name) is correctly passed to every step, including as a bound Cypher parameter in Run Cypher (MCP). No wiring bug.
  implication: The actual Cypher DOES execute for real against live Neo4j. An empty-with-no-error result means the query executed successfully but the label/pattern it queries has zero matching live rows for this project — not a plumbing failure.

- timestamp: 2026-07-12T22:33:00Z
  checked: ui-v2/src/lib/modelApi.js fetchValidationRuns() -> data-service GET /validation/runs/{project} -> app.py list_validation_runs()
  found: This is the REAL code path that powers what the user sees in Model Viewer. list_validation_runs() runs `MATCH (run:ValidationRun {graph:$graph, project:$project}) ... RETURN run.statePayloadJson AS statePayloadJson ...` (label **ValidationRun**, not "Run"), then `_project_state_summary()` (app.py ~634) parses `statePayloadJson` — a JSON STRING property containing the entire captured objStates/paramStates/propStates snapshot — into the summary the Model Viewer displays. This is confirmed by store_validation_run() (app.py ~441-499), the actual write path invoked by the Grasshopper plugin's publish flow: it `MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId}) SET run.statePayloadJson = $statePayloadJson, ...` — the entire DesignState snapshot is embedded as an opaque JSON blob on a ValidationRun node. NO separate `:DesignState`-labeled nodes are ever created by this write path.
  implication: For a real project like ConfigurationC (validated via the live Grasshopper -> data-service -> Neo4j -> Model Viewer flow), "design states" exist ONLY as JSON embedded inside ValidationRun.statePayloadJson — never as first-class `:DesignState` graph nodes.

- timestamp: 2026-07-12T22:35:00Z
  checked: migrations/2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher header comment (SECTION B)
  found: Explicitly states "The shipped runtime used graph='ValidationGraph' (1169 live nodes: ValidationEntity, ValidationRun, IntegrationConfig)" — i.e. ValidationRun is documented, in this repo's own migration notes, as the actual shipped-runtime node label for validation-run/design-state data. SECTION A of the same migration only renames/cleans up an older/different `:DesignState` node population (kind rename DefState/ObjectState -> ParamState/ObjState, orphan deletion) — a distinct, legacy, mostly-decorative node population that test/seed_designstates.cypher also seeds for smoke tests. No application code path was found that keeps `:DesignState` nodes in sync with real `ValidationRun.statePayloadJson` writes going forward.
  implication: `:DesignState`-labeled nodes are a documentation-only / test-fixture-only construct in the current shipped system; the real production data model for design states is `ValidationRun.statePayloadJson`. dg_context.py's VALIDGRAPH_CONCEPTS (and validate_cypher()'s ALLOWED_LABELS, which includes DesignState/Run but NOT ValidationRun) documents the aspirational schema, not the implemented one.

- timestamp: 2026-07-12T22:37:00Z
  checked: git history of n8n/workflows/graph-query-mcp.json pre-Phase-29 (commits 0eb65d4, 708c6f9 — the "v4 (SCHM-10)" and cloud-llm-connector versions)
  found: The pre-Phase-29 hand-rolled "Build Cypher Prompt" JS ALSO had zero mention of ValidationRun/statePayloadJson/DesignState/Run anywhere in its inlined schema text — it only documented Rule/Atom/Var/Literal/Builtin (Metagraph) and Class/DatatypeProperty/ObjectProperty (OntoGraph). The Validgraph layer was completely absent from the LLM's context before Phase 29 too.
  implication: This is not a regression introduced by Plan 29-05's thin-caller rewiring. The gap (LLM has no correct live/schema knowledge of how design states are actually stored) pre-dates Phase 29 entirely. Phase 29-03's VALIDGRAPH_CONCEPTS was a genuine improvement in intent (first time the Validgraph layer was documented for the LLM at all) but encoded the wrong (aspirational, not implemented) schema, so the underlying user-facing symptom persisted — it was simply invisible before because no Validgraph query was ever attempted at all, and only became visible now that Phase 29 UAT specifically exercised a design-state question end-to-end.

- timestamp: 2026-07-12T22:38:00Z
  checked: data-service/dg_context.py ALLOWED_LABELS / ALLOWED_RELATIONSHIPS (validate_cypher(), ~L385-407)
  found: ALLOWED_LABELS = {Class, DatatypeProperty, ObjectProperty, Builtin, Rule, Atom, Var, Literal, DesignState, Run, IntegrationConfig, ValidationEntity} — "ValidationRun" is absent. ALLOWED_RELATIONSHIPS = {HAS_BODY, HAS_HEAD, REFERS_TO, ARG, HAS_STATE, VALIDATES} — "HAS_ENTITY" (the real relationship type used between ValidationRun and ValidationEntity per app.py) is absent.
  implication: Even if the LLM somehow knew about the real ValidationRun/statePayloadJson shape, validate_cypher() would reject any Cypher referencing the label "ValidationRun" as an unknown_label violation and retry up to 3 times, ultimately failing closed. The validator's allow-list itself is built from the same aspirational/documented (not implemented) schema.

## Resolution

root_cause: |
  data-service/dg_context.py's assemble_context() (called by n8n's "Assemble Context" node for every
  graph_query request) supplies the LLM with a STATIC schema description of the Validgraph layer
  (VALIDGRAPH_CONCEPTS: node_labels=["DesignState","Run"], design_state_kinds enum, key_properties)
  and NEVER performs a live query for actual DesignState/Run existence data — fetch_existing_entities()
  only unions live OntoGraph (Class/DatatypeProperty/ObjectProperty) entities, never Validgraph ones.

  Worse, the schema VALIDGRAPH_CONCEPTS describes is not what the live, shipped production write path
  actually implements. data-service's real validation-publish path (store_validation_run(), invoked by
  the Grasshopper plugin -> POST /validation/publish -> Neo4j, which is exactly what populates what the
  user sees in Model Viewer for project "ConfigurationC") MERGEs a single `:ValidationRun`-labeled node
  per run and stores the ENTIRE captured design-state snapshot (objStates/paramStates/propStates) as an
  opaque JSON string in `run.statePayloadJson` — it never creates separate `:DesignState`-labeled graph
  nodes. `:DesignState` nodes only exist as a legacy/test-fixture construct (test/seed_designstates.cypher)
  and as the target shape of an old, narrowly-scoped migration
  (migrations/2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher, SECTION A) that the
  shipped write path was never updated to converge with going forward.

  Consequently, when a user asks the graph_query pipeline "what design states exist for
  ConfigurationC", the LLM — correctly following the only schema information it was given —
  generates a read-only Cypher query matching `:DesignState` nodes (e.g. `MATCH (ds:DesignState
  {project:$project}) RETURN ...`). This query is valid per validate_cypher()'s allow-list (DesignState
  IS in ALLOWED_LABELS) and executes successfully against live Neo4j with zero errors, but returns zero
  rows, because no `:DesignState`-labeled nodes exist for real validation runs published through the
  live production write path. n8n's "Parse Answer" node's own instruction ("If results are empty, say
  no data found") then produces exactly the reported symptom.

  This is a pre-existing schema/documentation-vs-implementation split (aspirational v4 DesignState-node
  model vs. actual shipped ValidationRun+statePayloadJson-blob model) that predates Phase 29 — confirmed
  by the pre-Phase-29 n8n prompt having ZERO knowledge of the Validgraph layer at all. Phase 29-03 added
  Validgraph schema awareness for the first time (a genuine improvement in intent), but encoded the wrong
  (undocumented-as-unimplemented) schema, so the gap remained invisible until Phase 29 UAT specifically
  exercised an end-to-end design-state question for the first time.
fix: (not applied — goal: find_root_cause_only)
verification: (not applicable — diagnosis only)
files_changed: []
