---
phase: 29-dg-aware-context-layer-swrl-ontology-cypher-awareness
plan: 08
type: execute
status: complete
gap_closure: true
requirements: [CTXA-01, CTXA-04]
tasks_completed: 1
tasks_total: 2
human_verify_status: deferred-to-manual
completed: 2026-07-19
---

# 29-08 SUMMARY — Deploy + re-verify UAT Success Criterion 4

## Outcome

**Task 1 (auto — deploy + smoke-check): COMPLETE and PASSED.**
**Task 2 (checkpoint:human-verify, blocking): DEFERRED to manual verification** per explicit
user instruction ("skip this n8n workflow issue marking it for manual verification"; "i will
update workflow in n8n manually pasting file"). NOT self-approved.

## Task 1 — data-service deploy + smoke check (passed)

- `docker compose build data-service && docker compose up -d data-service` — succeeded; the
  29-06 `dg_context.py` fix is live.
- `POST /context/assemble {type:graph_query, project:ConfigurationC}` → HTTP 200 with the
  corrected shape: `validgraph.node_labels = ['ValidationRun','ValidationEntity','IntegrationConfig']`
  (contains `ValidationRun`, does NOT contain `DesignState`), and `existing_design_states` key present.
- Independent confirmation the fix works with REAL data: `POST /context/assemble` for
  **v8-ui-smoke** returns `existing_design_states` with **21 real ValidationRun entries**
  (runId, createdAt, entityCount, per-run validStatus, parsed state summary).
- `validate_cypher()` verified inside the container: rejects both `MATCH (:DesignState {...})`
  and the bare `MATCH (:DesignState) WHERE ...` form as `unknown_label`; accepts
  `MATCH (:ValidationRun {...})`. The security gate (CTXA-04) is correct at the data-service level.
- `/context/generate-cypher` verified live: rejects a forced `:DesignState` output and retries
  (bounded loop) — returns `{valid:false, violations}` on exhaustion (never leaks invalid Cypher).

## Task 2 — live end-to-end human-verify: DEFERRED (blocked by an n8n live-workflow anomaly)

The original UAT target project **ConfigurationC has zero ValidationRun data** in the live
Neo4j (only `v8-ui-smoke` has queryable data — 21 runs; `TestA`'s 20 runs are pre-v4
`graph:'ValidationGraph'` data, invisible to data-service until the pending migration). Per
user decision, verification was re-pointed at **v8-ui-smoke**.

Running the live graph-query webhook for v8-ui-smoke repeatedly returned **"No data found"**
with an LLM-generated `MATCH (ds:DesignState ...)` query. Diagnosis:

- The live n8n executions for the `dg/graph-query` webhook hit only `POST /mcp` +
  `POST /llm/generate` — **never `POST /context/assemble` or `POST /context/generate-cypher`.**
  So the entire Phase-29 context layer (including the `validate_cypher` gate) is **not actually
  executing** for graph queries; the workflow generates Cypher via a direct `/llm/generate`
  call (old, pre-29 architecture), producing aspirational `:DesignState` queries.
- The active workflow serving the webhook (`b2c3d4e5-f6a7-8901-bcde-f12345678901`,
  "DG Graph Query (MCP)") has the **correct** context-layer definition in storage (17 nodes,
  `Assemble Context` → `/context/assemble`, `Generate Validated Cypher` → `/context/generate-cypher`),
  and n8n's execution log attributes executions 201–205 to this workflow id with `status:success`
  — yet its `/context/*` nodes never reach data-service. This is a genuine n8n live-instance
  anomaly (the instance also carries **5 stale duplicate "DG Graph Query (MCP)"** workflows and
  duplicate "DG Rules -> Metagraph" workflows — the known n8n drift flagged in CLAUDE.md).
- Attempted fixes that did NOT resolve it: in-place API reactivation (PATCH active-toggle had
  no effect); full `docker compose restart n8n` (re-registered active workflows, routing unchanged).

**29-07's repo edit is correct** (Build Cypher Prompt forwards `existing_design_states`); the
issue is purely that the live n8n instance is not executing the synced definition.

## Resolution path (user-owned)

User will **manually update the n8n workflow by pasting `n8n/workflows/graph-query-mcp.json`**
into the n8n editor (cleanest fix given the duplicate-workflow mess), then verify Success
Criterion 4 manually. After the manual paste, the acceptance check is:
1. Run a v8-ui-smoke design-state question via the Graph Viewer console (http://localhost:8080).
2. Confirm the execution hits `POST /context/assemble` + `POST /context/generate-cypher` in the
   data-service logs (i.e. the context layer executes), and the answer references real design
   states (run/state ids, labels, ObjState/ParamState/PropState counts) — no longer "No data found".

## Files

- No repo files modified by this plan (deploy + verification only).
- n8n was restarted once during diagnosis (routine; `b2c3d4e5` remains active — no adverse effect).

## Deviations

- Task 2 human-verify deferred to manual per user instruction (same precedent as Phase 33 / 34-02 / 34-03
  live-UAT deferrals). NOT self-approved as passed.
- Verification re-pointed from ConfigurationC (no live data) to v8-ui-smoke (21 live runs) per user decision.

## Follow-ups recorded

- **[manual]** User to paste `n8n/workflows/graph-query-mcp.json` into n8n and verify the live
  graph-query path executes the context layer (`/context/assemble` + `/context/generate-cypher`).
- **[n8n reconciliation]** The live n8n instance carries 5 stale duplicate "DG Graph Query (MCP)"
  workflows + duplicate "DG Rules -> Metagraph" workflows. The active `b2c3d4e5` workflow's stored
  (correct) definition is not executing its `/context/*` nodes despite success-status executions —
  worth a manual look during the paste. Aligns with CLAUDE.md's existing "reconcile live n8n
  workflows with n8n/workflows/*.json" open item.

## Self-Check: PASSED (with human-verify deferred)

Code + data-service deliverables (29-06, 29-07) are complete, committed, and verified.
Live end-to-end (n8n) verification is deferred to the user's manual workflow update + check.
