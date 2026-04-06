---
phase: 03-n8n-knowledge-workflows-llm-ingest-and-query
plan: 02
subsystem: n8n-workflows
tags: [n8n, knowledge-query, full-text-search, ollama, neo4j, knowledge-graph]
depends_on:
  requires: [03-01]
  provides: [knowledge-query-workflow]
  affects: [data-service, neo4j, ollama]
tech_stack:
  added: []
  patterns: [webhook-ack, deterministic-cypher, full-text-search, session-tracking, execution-result-polling]
key_files:
  created:
    - n8n/workflows/knowledge-query.json
  modified: []
decisions:
  - D-06: Cypher for full-text search is deterministic (built in Function node), NOT LLM-generated
  - T-3-01: graph parameter hardcoded as KnowledgeGraph, never from user input
  - T-3-02: All Cypher uses parameterized queries ($query, $project) — prompt_text never interpolated
  - T-3-06: Lucene special chars stripped from prompt before use as $query parameter
metrics:
  completed_date: "2026-04-06"
  tasks_completed: 1
  tasks_total: 2
  status: awaiting-checkpoint
---

# Phase 3 Plan 02: Knowledge Query Workflow Summary

**One-liner:** n8n knowledge-query workflow using deterministic full-text search + Ollama NL answer synthesis with parameterized Cypher and KnowledgeSession tracking.

## Status

Task 1 complete. Awaiting human verification at checkpoint (Task 2).

## Tasks Completed

### Task 1: Author knowledge-query n8n workflow JSON

**Commit:** d48ddda

Created `n8n/workflows/knowledge-query.json` — a valid 11-node n8n workflow implementing:

**Node sequence:**
1. Webhook — POST `/dg/knowledge-query`, webhookId `dg-knowledge-query`
2. Set Input Defaults — extracts `prompt_text` and `project_name` from request body
3. Format Ack — returns `{status: "accepted", executionId}`
4. Respond Ack — immediately responds to the HTTP client
5. Build Full-Text Cypher — sanitizes Lucene special chars, builds deterministic `CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)` Cypher, saves `cypherUsed`
6. Execute Full-Text Search — POST to `http://neo4j:7474/db/neo4j/tx/commit` with basicAuth
7. Build Answer Prompt — extracts top-5 results, builds Ollama summarization prompt
8. Ollama Generate Answer — POST to `http://ollama:11434/api/generate` WITHOUT `format:"json"` (free-text NL), temperature 0.3
9. Parse Answer — trims Ollama response, falls back to "No answer could be generated."
10. Write KnowledgeSession — MERGE KnowledgeSession with `mode: 'query'` in Neo4j
11. Post Execution Result — POST to `http://data-service:8000/execution-result` with workflow key `"knowledge-query"` and payload `{answer, cypher, matchCount}`

**Security mitigations applied (from threat model):**
- T-3-01: `graph: 'KnowledgeGraph'` hardcoded in Build Full-Text Cypher — never from user input
- T-3-02: Cypher uses `$query` and `$project` parameters — `prompt_text` never string-interpolated into Cypher
- T-3-06: Lucene special chars stripped from prompt via regex `/[+\-!(){}\[\]^"~*?:\\/]/g` before use as `$query`

## Deviations from Plan

None — plan executed exactly as written.

## Awaiting: Task 2 Checkpoint

**Type:** human-verify

Human must:
1. Open n8n at http://localhost:5678
2. Import `n8n/workflows/knowledge-ingest.json` — activate the workflow
3. Import `n8n/workflows/knowledge-query.json` — activate the workflow
4. Run: `python test/test_phase03_knowledge_llm.py`
5. Expected: All 5 tests print PASS, script exits with code 0

## Self-Check

- [x] `n8n/workflows/knowledge-query.json` exists and is valid JSON
- [x] Commit d48ddda exists
- [x] Workflow name is "Knowledge Query"
- [x] 11 nodes wired correctly
- [x] Lucene sanitization present
- [x] No `format:"json"` on Ollama call
- [x] Workflow key is "knowledge-query" (hyphen)
- [x] Payload has `cypher` key (not `cypherUsed`)
- [x] KnowledgeSession mode is "query"
- [x] `graph: 'KnowledgeGraph'` hardcoded

## Self-Check: PASSED
