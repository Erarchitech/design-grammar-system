---
phase: 05-ui-mode-restructuring-insert-and-query-panels
plan: 02
subsystem: graph-viewer
tags: [ui, knowledge, query, polling, requestKnowledge]
dependency_graph:
  requires: [05-01]
  provides: [query-knowledge-panel, requestKnowledge]
  affects: [graph-viewer/index.html]
tech_stack:
  added: []
  patterns: [async-polling, knowledge-query-webhook, step-indicators, workflow-cypher-display]
key_files:
  created: []
  modified:
    - graph-viewer/index.html
decisions:
  - requestKnowledge uses same async polling pattern as submitKnowledgeIngest
  - Workflow Cypher shown in collapsible panel (consistent with DesignRules tab pattern from later phase)
  - Field names use prompt_text/project_name to match n8n webhook expectations
metrics:
  completed: 2026-04-07
---

# Phase 05 Plan 02: Query Knowledge Panel Summary

Query Knowledge panel added to Specs&Notes tab with `requestKnowledge` async function POSTing to `/n8n/webhook/dg/knowledge-query`, using the same async polling pattern as Insert Knowledge, displaying NL answer in Response textarea and Cypher in collapsible Workflow Cypher panel.

## Changes Made

### Task 1: Query Knowledge panel with requestKnowledge function

- Added `const requestKnowledge = async ()` function after `submitKnowledgeIngest` inside `GraphViewerPage`
- Function POSTs to `/n8n/webhook/dg/knowledge-query` with `{ prompt_text, project_name }` body
- On response, calls `startKnowledgePollingLatest("knowledge-query", "knowledge-query")` to poll for NL answer and Cypher
- Replaced Query Knowledge placeholder with full panel: prompt textarea, Query Knowledge button, progress bar, step indicators, Response textarea, Workflow Cypher textarea
- No placeholder text "Query Knowledge panel loading..." remains in file
- No JSX used — all elements via `React.createElement` aliased as `e`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | cffd714 | feat(05-02): Query Knowledge panel with requestKnowledge function |
| fix | fdd7cb0 | fix(05-02): fix stale polling result in knowledge insert/query |
| fix | 3908cae | fix(05-02): fix field name mismatch in knowledge webhook requests |
| feat | 934721d | feat(05-02): auto-switch NeoVis to KnowledgeGraph view in Specs&Notes tab |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale polling result returned wrong execution**
- **Found during:** Post-task verification
- **Issue:** `startKnowledgePollingLatest` could return a stale result from a previous execution
- **Fix:** Added execution ID tracking to pick up the correct result
- **Files modified:** graph-viewer/index.html
- **Commit:** fdd7cb0

**2. [Rule 1 - Bug] Field name mismatch in knowledge webhook requests**
- **Found during:** Integration testing
- **Issue:** Plan spec used `prompt`/`project` but n8n webhook expected `prompt_text`/`project_name`
- **Fix:** Corrected field names to match n8n webhook contract
- **Files modified:** graph-viewer/index.html
- **Commit:** 3908cae

**3. [Rule 2 - Enhancement] Auto-switch NeoVis to KnowledgeGraph view**
- **Found during:** Task 1
- **Issue:** Switching to Specs&Notes tab should show KnowledgeGraph view in NeoVis, not Metagraph
- **Fix:** Added tab-switch side effect to auto-select KnowledgeGraph view when entering Specs&Notes
- **Files modified:** graph-viewer/index.html
- **Commit:** 934721d

## Task 2: Checkpoint (human-verify)

Task 2 is a `type="checkpoint:human-verify"` — requires Docker rebuild and manual browser verification. See checkpoint state returned below.

## Self-Check: PASSED

- graph-viewer/index.html contains `const requestKnowledge = async ()` — FOUND
- graph-viewer/index.html contains `/n8n/webhook/dg/knowledge-query` — FOUND
- graph-viewer/index.html contains `startKnowledgePollingLatest("knowledge-query", "knowledge-query")` — FOUND
- graph-viewer/index.html contains `"Query Knowledge"` button label — FOUND
- graph-viewer/index.html contains `"Ask a question about your project knowledge..."` placeholder — FOUND
- graph-viewer/index.html contains `knowledgeQuerySteps.map(` — FOUND
- graph-viewer/index.html contains `.workflow-output` textarea with `knowledgeResponseCypher` — FOUND
- graph-viewer/index.html contains `"Cypher used to query the knowledge graph will appear here..."` — FOUND
- No `"Query Knowledge panel loading..."` placeholder remains — CONFIRMED
- No JSX syntax — CONFIRMED
- Commits cffd714, fdd7cb0, 3908cae, 934721d exist in history — CONFIRMED
