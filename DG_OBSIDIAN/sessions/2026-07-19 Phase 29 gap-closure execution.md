# Session: 2026-07-19 — Phase 29 gap-closure execution

**Duration:** ~3.5 hours (phases 29-06/07/08 execution)  
**Model:** Claude Opus 4.8 → Sonnet 5 → Haiku 4.5  
**Branch:** master  
**Commits:** 5 code + 1 planning docs

## What was done

**Phase 29 gap-closure (3 plans): UAT Success Criterion 4 root-cause fix**

### 29-06: Converge Validgraph schema to real ValidationRun shape
- **Problem:** `dg_context.py` described aspirational `:DesignState`/`:Run` nodes (not shipped) instead of the real `:ValidationRun`/`statePayloadJson`/`HAS_ENTITY` shape from `app.py`'s `store_validation_run()`. LLM generated `:DesignState` queries that returned zero rows despite real design-state data being in the Neo4j.
- **Fix:** Converged `VALIDGRAPH_CONCEPTS` + `validate_cypher()` allow-lists to the real `ValidationRun` shape. `:DesignState` queries now rejected as `unknown_label`. Added `fetch_existing_design_states()` + `_summarize_state_payload()` to surface live per-project design-state data.
- **Verification:** TDD (RED→GREEN×2), 52/52 `test_dg_context.py` + 220/220 full data-service suite green inside the container.
- **Commits:** 4 (test RED + feat GREEN ×2)

### 29-07: Forward existing_design_states into n8n graph-query prompt
- **Fix:** Updated "Build Cypher Prompt" node to include `existing_design_states` in the CONTEXT block.
- **Deployment:** Live n8n re-synced via PATCH `/rest/workflows/{id}`, versionCounter 40→41, `active:true` preserved, zero drift verified by GET + per-node parameter diff.
- **Commit:** 1 (repo JSON edit)

### 29-08: Deploy + re-verify UAT Success Criterion 4
- **Task 1 (auto):** Passed ✓
  - data-service rebuilt/redeployed; `/context/assemble` for ConfigurationC returns corrected shape (`validgraph.node_labels = [ValidationRun, ValidationEntity, IntegrationConfig]`, NO `DesignState`), `existing_design_states` present.
  - For v8-ui-smoke (the only project with live design-state data): **21 real ValidationRun entries** returned with per-run state summaries.
  - `/context/generate-cypher` validates + retries correctly (forced `:DesignState` prompt → attempt 1 rejected, attempt 2 LLM produced valid alternative).
- **Task 2 (human-verify, blocking):** Deferred to manual (user decision)
  - **Discovery:** Live n8n `dg/graph-query` webhook **bypasses `/context/assemble` + `/context/generate-cypher`** entirely — executions hit only `/mcp` + `/llm/generate`, so LLM still emits `:DesignState` queries.
  - **Root cause:** The active workflow `b2c3d4e5` has the correct stored definition (17 nodes, context-layer wiring), but the live instance isn't executing it. API reactivation + full `docker compose restart n8n` did not change routing.
  - **n8n state:** 5 stale duplicate "DG Graph Query (MCP)" workflows + duplicate "DG Rules -> Metagraph" workflows (known drift).
  - **Resolution (user-owned):** User will manually paste `n8n/workflows/graph-query-mcp.json` into n8n, then re-verify by running a v8-ui-smoke design-state query and confirming `/context/*` fires + answer is correct.

## Findings & Follow-ups

### Code deliverables (COMPLETE & COMMITTED)
- ✅ `dg_context.py`: VALIDGRAPH_CONCEPTS + validate_cypher converged to real ValidationRun/statePayloadJson/HAS_ENTITY shape
- ✅ `dg_context.py`: fetch_existing_design_states() + _summarize_state_payload() added
- ✅ `n8n/workflows/graph-query-mcp.json`: Build Cypher Prompt forwards existing_design_states
- ✅ Data-service validation gate (CTXA-04) verified correct at the API + validator levels

### Live end-to-end (DEFERRED)
- ⚠️ **n8n workflow execution anomaly:** Active workflow definition correct, live routing incorrect (bypasses `/context/*`). Cause unknown; API reactivate + restart did not resolve.
- 📋 **User action required:** Manually paste repo JSON + re-verify v8-ui-smoke query.

### n8n follow-ups
- **[manual]** Delete 5 stale duplicate "DG Graph Query (MCP)" workflows (IDs: `F0RCL8vKpzRcEbzp`, `bg9fvbEZS98K1V1y`, `zxUT2nEiiTuYibLk04TKf`, `cg3ypCZ0rRxuyLAO`, `valXl87YPOLJobo9`); keep only `b2c3d4e5` (or paste fresh).
- **[manual]** Paste `n8n/workflows/graph-query-mcp.json` into n8n, re-run v8-ui-smoke query, confirm `/context/*` fires.
- **[future]** Investigate the workflow-execution anomaly (stored def correct, live routing stale) — may be a n8n caching or refresh issue unresolved by standard reactivation.

### Original UAT data note
- ConfigurationC has **zero ValidationRun data** in the live Neo4j (only v8-ui-smoke is queryable, 21 runs; TestA's 20 are pre-v4 `graph:'ValidationGraph'` label, invisible until pending migration).
- Verification re-pointed to v8-ui-smoke per user decision.

## Session files

**Created (this session):**
- `29-06-SUMMARY.md` (4 commits: test RED + feat GREEN ×2)
- `29-07-SUMMARY.md` (1 commit: repo JSON)
- `29-08-SUMMARY.md` (deploy + smoke ✓; human-verify deferred)

**Modified (this session):**
- `29-UAT.md` (Test 1: status updated to pending, resolution recorded)
- `.planning/STATE.md`, `.planning/ROADMAP.md` (phase 29 metrics, 8/8 plans complete status)

**Commits:**
- `36d80a3` test(29-06): add failing tests for ValidationRun/HAS_ENTITY allow-list convergence
- `371e946` feat(29-06): converge VALIDGRAPH_CONCEPTS + validate_cypher allow-lists to real ValidationRun shape
- `fd10bc4` test(29-06): add failing tests for existing-design-states helper + assemble_context wiring
- `c5c83b5` feat(29-06): add live existing-design-states helper wired into graph_query context
- `270395e` feat(29-07): forward existing_design_states into graph-query Cypher prompt
- `a771b53` docs(phase-29): phase gap-closure (29-06/07/08) executed; code+data-service verified; live UAT deferred to manual

## Next steps

1. **User:** Manually paste `n8n/workflows/graph-query-mcp.json` into n8n (delete stale duplicates).
2. **User:** Re-verify v8-ui-smoke design-state query; confirm `/context/*` endpoint hits + answer is correct.
3. **User:** Run `/gsd-verify-work 29` to complete the phase (updates 29-UAT Test 1 → pass).
4. **Optional:** I can delete the 5 stale duplicate n8n workflows via API if requested.

## Lessons

- **n8n workflow state:** Active-toggle reactivation (PATCH `{active: false}` → `{active: true}`) does NOT force a reload of the workflow definition in-memory; a full container restart is needed, and even that may not change the routing if the root cause is elsewhere (caching, webhook registration, duplicates, etc.). The stored JSON definition is not the same as the executing definition.
- **Schema convergence validation:** TDD + live Docker container tests caught the gap early; static grep/pytest cannot verify end-to-end because the validator, LLM, and Neo4j are external.
