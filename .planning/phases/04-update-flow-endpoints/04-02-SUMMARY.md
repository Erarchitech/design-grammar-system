---
phase: 04-update-flow-endpoints
plan: "02"
subsystem: n8n
tags: [n8n, workflow, ollama, integration-test, update-flow, llm]
dependency_graph:
  requires: [04-01]
  provides: [knowledge-update-workflow, integration-test-script]
  affects: [n8n/workflows/knowledge-update.json, test/test_phase04_update_flow.sh]
tech_stack:
  added: []
  patterns: [n8n-async-ack-fork, ollama-plain-text, execution-result-polling]
key_files:
  created:
    - n8n/workflows/knowledge-update.json
    - test/test_phase04_update_flow.sh
  modified: []
decisions:
  - knowledge-update workflow uses Code node (typeVersion 2) with jsCode field for Build Update Prompt — matches n8n v1 JSON format for function-style nodes
  - Workflow plain-text mode (no format:json) per D-04 — LLM returns prose, not JSON
  - Parse LLM Text uses Set node with $items() back-references to preserve execution_id/note_id/project_name across Ollama response
metrics:
  duration: ~10 minutes
  completed: "2026-04-06"
  tasks_completed: 2
  files_modified: 2
---

# Phase 4 Plan 02: Knowledge-Update Workflow + Integration Test Summary

8-node n8n workflow for LLM-based note revision (webhook -> Ollama plain text -> execution-result) plus bash integration test covering the full match/propose/confirm flow including 400 and 409 error cases.

## What Was Built

### Task 1: knowledge-update n8n workflow JSON

- **n8n/workflows/knowledge-update.json**: Valid importable n8n workflow with 8 nodes
  - Node 1 **Webhook**: POST `dg/knowledge-update`, webhookId `dg-knowledge-update`, `responseMode: responseNode`
  - Node 2 **Set Input Defaults**: Extracts `prompt_text`, `current_content`, `note_id`, `project_name`, `execution_id` from `$json.body`
  - Node 3 **Format Ack**: Returns `{status: "accepted", executionId: ...}` from `$execution.id`
  - Node 4 **Respond Ack**: `respondToWebhook` — immediate 200 to HTTP caller
  - Node 5 **Build Update Prompt**: Code node builds prose prompt with update instruction + current content
  - Node 6 **Ollama Generate**: POST `http://ollama:11434/api/generate` with `llama3.1`, no `format:json`, 900s timeout
  - Node 7 **Parse LLM Text**: Set node extracts `response` field as `proposed_text`, back-references `execution_id`/`note_id`/`project_name`
  - Node 8 **Post Execution Result**: POST `http://data-service:8000/execution-result` with `proposedText` payload
- **Connection pattern**: Webhook -> Set Defaults -> [Format Ack -> Respond Ack | Build Update Prompt -> Ollama -> Parse -> Post Result]
- **No Neo4j writes** — workflow is read/transform/notify only (per D-12)

### Task 2: End-to-end integration test script

- **test/test_phase04_update_flow.sh**: Bash script exercising full match -> propose -> confirm flow
  - Creates a `KnowledgeNote` test fixture directly via Neo4j HTTP API
  - Test 1: `POST /knowledge/update/match` returns `candidates` array
  - Test 2: Empty prompt to match returns HTTP 400
  - Test 3: `POST /knowledge/update/propose` returns `diffs[]` with `diffHtml` and `updatedAt`
  - Test 4: `POST /knowledge/update/confirm` writes note and returns `affectedNoteIds` + `sessionId`
  - Test 5: Stale `updatedAt` to confirm returns HTTP 409
  - Cleanup: removes `KnowledgeNote` and `KnowledgeSession` test nodes via Cypher
  - Tests 3-5 skip gracefully if n8n + Ollama not available (propose fails -> skips downstream)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 18f94e8 | feat(04-02): author knowledge-update n8n workflow JSON |
| 2 | 1c5a794 | feat(04-02): add end-to-end integration test script for update flow |

## Verification Results

```
python -c "import json; json.load(open('n8n/workflows/knowledge-update.json'))"
# → valid JSON, 8 nodes

grep -c "dg-knowledge-update" n8n/workflows/knowledge-update.json  → 2
grep -c "knowledge/update" test/test_phase04_update_flow.sh         → 10
bash -n test/test_phase04_update_flow.sh                            → Syntax OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used `jsCode` field instead of `functionCode` for Code node**

- **Found during:** Task 1 authoring
- **Issue:** Plan specified `n8n-nodes-base.code` as node type (JavaScript Code node in n8n v1). The Code node uses `jsCode` as the parameter field and `typeVersion: 2`, whereas the Function node (deprecated) uses `functionCode` and `typeVersion: 1`. Using `functionCode` for a `code` node type would cause import errors in n8n.
- **Fix:** Used `jsCode` field with `typeVersion: 2` for the Build Update Prompt node. All other function-style nodes in the file use `n8n-nodes-base.function` (the legacy type) with `functionCode`, which matches the pattern in `knowledge-ingest.json`.
- **Files modified:** n8n/workflows/knowledge-update.json
- **Commit:** 18f94e8

## Known Stubs

None. The workflow is complete and functional. The `proposedText` output feeds directly into `word_diff_html` in the propose endpoint (Plan 01). No placeholder values.

## Threat Mitigations Applied

| Threat | Mitigation Applied |
|--------|-------------------|
| T-04-02: Prompt injection via note content | LLM output goes to difflib only (string comparison). Workflow does NOT write to Neo4j — no Cypher generated from LLM output. |
| T-04-06: Note content leakage via Ollama | Ollama runs locally in Docker network; no external calls. No new exposure surface beyond what is already in Neo4j. |

## Self-Check: PASSED

Files exist:
- n8n/workflows/knowledge-update.json - confirmed (221 lines, valid JSON)
- test/test_phase04_update_flow.sh - confirmed (124 lines, syntax OK)

Commits exist:
- 18f94e8 - confirmed
- 1c5a794 - confirmed
