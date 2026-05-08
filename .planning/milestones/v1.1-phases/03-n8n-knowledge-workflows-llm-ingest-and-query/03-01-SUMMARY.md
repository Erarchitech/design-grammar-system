---
phase: 03-n8n-knowledge-workflows-llm-ingest-and-query
plan: "01"
subsystem: n8n-workflows, data-service
tags: [n8n, ollama, neo4j, knowledge-graph, sessions, integration-tests]
dependency_graph:
  requires: []
  provides:
    - n8n/workflows/knowledge-ingest.json
    - data-service GET /knowledge/sessions/{project}
    - test/test_phase03_knowledge_llm.py
  affects:
    - n8n (new workflow importable via UI)
    - data-service (new endpoint live after restart)
tech_stack:
  added: []
  patterns:
    - n8n webhook -> ack path + work path (from rules-to-metagraph.json)
    - Ollama format:json for structured JSON extraction
    - Neo4j parameterized Cypher via HTTP API
    - FastAPI read_many pattern for list endpoints
key_files:
  created:
    - n8n/workflows/knowledge-ingest.json
    - test/test_phase03_knowledge_llm.py
  modified:
    - data-service/app.py
decisions:
  - "Ollama called with format:json to enforce JSON output — avoids markdown fence stripping issues in most cases while keeping fallback parse for edge cases"
  - "Parse LLM JSON fallback: title = first 60 chars of prompt_text, tags = ['untagged'] — satisfies D-02 (note always created)"
  - "graph: 'KnowledgeGraph' hardcoded in Build Cypher Function node parameters, never read from user input — T-3-01 mitigation"
  - "Write KnowledgeSession uses inline bodyParametersJson expression rather than separate Function node — reduces node count while keeping parameterized Cypher"
  - "Set Input Defaults fans out to both Format Ack (ack path) and Build Insert Prompt (work path) simultaneously — matches rules-to-metagraph.json pattern"
metrics:
  duration: "~18 minutes"
  completed_date: "2026-04-06"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 1
---

# Phase 3 Plan 01: Knowledge Ingest Workflow, Sessions Endpoint, and Test Scaffold Summary

**One-liner:** n8n knowledge-ingest workflow with Ollama JSON extraction, parameterized Neo4j MERGE, KnowledgeSession write, sessions list endpoint, and Phase 3 integration test scaffold.

## What Was Built

### Task 1: Phase 3 Integration Test Scaffold

`test/test_phase03_knowledge_llm.py` — standalone Python test script covering all 5 Phase 3 scenarios:

- `test_sc4_webhook_ack` — fast ack check (HTTP 200, status='accepted'), no polling
- `test_sc1_ingest_prompt` — NL ingest -> polls execution-result/latest/knowledge-ingest -> asserts noteId/title/tags in payload -> verifies note in /knowledge/notes
- `test_sc3_session_insert` — verifies KnowledgeSession with mode='insert' was created after sc1
- `test_sc2_query_answer` — NL query -> polls knowledge-query -> asserts answer (non-empty string) and cypher (contains 'knowledge_note_search')
- `test_sc5_sessions_endpoint` — GET /knowledge/sessions/{project} schema check (sessionId, mode, prompt, result, createdAt)

`__main__` block runs in dependency order (sc4, sc1, sc3, sc2, sc5) with cleanup. Exit 0 if all pass, 1 if any fail.

### Task 2: GET /knowledge/sessions/{project} Endpoint

Added to `data-service/app.py` after `delete_knowledge_note`:

```python
@app.get("/knowledge/sessions/{project}")
def list_knowledge_sessions(project: str):
    rows = read_many(
        "MATCH (s:KnowledgeSession {project: $project, graph: $graph}) "
        "RETURN s.sessionId AS sessionId, s.mode AS mode, "
        "       s.prompt AS prompt, s.result AS result, s.createdAt AS createdAt "
        "ORDER BY s.createdAt DESC",
        {"project": project, "graph": KNOWLEDGE_GRAPH},
    )
    return {"project": project, "sessions": rows}
```

Returns `{"project": "...", "sessions": [...]}` — reverse-chronological, filtered by project and KnowledgeGraph.

### Task 3: knowledge-ingest.json n8n Workflow

`n8n/workflows/knowledge-ingest.json` — 11-node n8n workflow:

| Node | Type | Purpose |
|------|------|---------|
| Webhook | Webhook | POST /dg/knowledge-ingest, responseMode: responseNode |
| Set Input Defaults | Set | Extracts prompt_text and project_name from body |
| Format Ack | Function | Returns {status:'accepted', executionId} |
| Respond Ack | Respond to Webhook | Sends ack immediately |
| Build Insert Prompt | Function | Builds few-shot Ollama prompt for JSON extraction |
| Ollama Generate | HTTP Request | POST to ollama:11434/api/generate with format:'json' |
| Parse LLM JSON | Function | Parses response, normalizes tags, generates noteId, falls back on error |
| Build Cypher | Function | Creates parameterized Neo4j statements array (KnowledgeNote + KnowledgeTag + TAGGED_WITH) |
| Execute Neo4j Cypher | HTTP Request | POST to neo4j:7474/db/neo4j/tx/commit with basicAuth |
| Write KnowledgeSession | HTTP Request | MERGE KnowledgeSession with mode='insert', prompt, result, createdAt |
| Post Execution Result | HTTP Request | POST to data-service:8000/execution-result with workflow='knowledge-ingest' |

**Connection wiring:**
- Webhook -> Set Input Defaults -> [Format Ack -> Respond Ack] (ack path ends)
- Set Input Defaults -> Build Insert Prompt -> Ollama Generate -> Parse LLM JSON -> Build Cypher -> Execute Neo4j Cypher -> Write KnowledgeSession -> Post Execution Result (work path)

## Security

All threat model mitigations applied:

- **T-3-01 (Tampering):** `graph: 'KnowledgeGraph'` hardcoded in Build Cypher Function node — never read from user input
- **T-3-02 (Injection):** All Cypher uses parameterized statements (`$noteId`, `$project`, `$graph`, `$title`, etc.) — `prompt_text` is never interpolated into Cypher strings
- **T-3-03 (Info Disclosure):** `prompt_text` sent only to local Ollama instance on Docker network — no external API calls
- **T-3-04 (DoS):** 900s Ollama timeout consistent with existing workflows
- **T-3-05 (Spoofing):** Consistent with existing webhook security model

## Deviations from Plan

### Auto-applied Decisions

**1. Set Input Defaults fans out to both ack path and work path**

The plan described ack path as `Webhook -> Set Input Defaults -> Format Ack -> Respond Ack`. In the connection wiring, `Set Input Defaults` connects to both `Format Ack` (ack path) and `Build Insert Prompt` (work path) simultaneously. This matches how `rules-to-metagraph.json` works — the Set node fans out to multiple downstream paths in parallel, which is necessary for n8n's responseNode mode.

**2. Write KnowledgeSession uses inline bodyParametersJson**

The plan suggested either a preceding Code node or inline expression for the session MERGE. The inline expression approach was chosen (consistent with how `Annotate Graph Props` and other nodes work in the reference workflow) — reduces node count from the described 11 to exactly 11 while keeping Cypher parameterized.

None of the above required Rule 4 escalation — both are implementation details within Claude's discretion per the RESEARCH.md "Claude's Discretion" section.

## Known Stubs

None. All artifacts are fully wired:
- `knowledge-ingest.json` wires all 11 nodes end-to-end
- Sessions endpoint reads from Neo4j (no mock data)
- Test scaffold uses live service URLs (not mocked)

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes beyond what was planned and analyzed in the threat model.

## Self-Check: PASSED

All files exist on disk. All 3 task commits confirmed in git log.

| Item | Status |
|------|--------|
| test/test_phase03_knowledge_llm.py | FOUND |
| n8n/workflows/knowledge-ingest.json | FOUND |
| data-service/app.py (modified) | FOUND |
| commit 215a8eb (test scaffold) | FOUND |
| commit 37d1a79 (sessions endpoint) | FOUND |
| commit df9657d (workflow JSON) | FOUND |
