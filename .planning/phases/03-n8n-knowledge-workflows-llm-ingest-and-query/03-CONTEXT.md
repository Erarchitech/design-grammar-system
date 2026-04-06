# Phase 3: n8n Knowledge Workflows + LLM Ingest and Query - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Two new n8n workflows wiring natural language insert and natural language query through Ollama to Neo4j. Architects can insert knowledge via a NL prompt (LLM extracts title, tags, content) and ask NL questions about the knowledge graph (hybrid full-text search + LLM summarization). Every interaction writes a KnowledgeSession node. Phase 2 CRUD endpoints and folder ingest are already built — this phase adds the LLM-powered paths.

</domain>

<decisions>
## Implementation Decisions

### LLM Prompt Design (Insert)
- **D-01:** Ollama returns a JSON object `{"title": "...", "tags": [...], "content": "..."}` from the NL insert prompt — n8n parses the JSON and builds Cypher MERGE statements
- **D-02:** LLM must always extract a title and at least one tag, even if inferred from content — no "unclear" error branch, no fallback to raw text storage
- **D-03:** Insert prompt does NOT include existing knowledge context (no existing tags or titles fed to LLM) — tags deduplicated at Neo4j level via MERGE

### Knowledge Query Strategy
- **D-04:** Hybrid two-step approach: Neo4j full-text search finds matching notes first, then Ollama summarizes the results into a natural language answer
- **D-05:** Top 5 highest-scored full-text matches are fed to Ollama for answer synthesis
- **D-06:** The Cypher query shown to the user (QRYK-02) is the full-text search query, not LLM-generated Cypher

### n8n Workflow Wiring
- **D-07:** n8n writes to Neo4j directly (same pattern as rules-to-metagraph) — n8n builds Cypher from LLM JSON output and executes against Neo4j HTTP API, then posts result to data-service execution-result
- **D-08:** Reuse existing `/execution-result/{id}` and `/execution-result/latest/{workflow}` polling endpoints with new workflow keys: `knowledge-ingest` and `knowledge-query`
- **D-09:** Webhook paths: `/webhook/dg/knowledge-ingest` and `/webhook/dg/knowledge-query` — follows existing naming convention

### Session Tracking
- **D-10:** KnowledgeSession nodes created inside n8n workflows as a final step after Neo4j write/query succeeds — no session recorded if LLM call fails
- **D-11:** Structured result data per mode — Insert: `{noteId, title, tags}`, Query: `{answer, cypherUsed, matchCount}`

### Claude's Discretion
- Few-shot example content and prompt structure details for both insert and query workflows
- n8n workflow node layout and intermediate processing steps
- Error handling for malformed LLM JSON output (retry strategy, fallback)
- Exact Cypher template for the full-text search + summarization query flow
- Nginx proxy rules for new webhook paths (if any needed beyond existing `/n8n/` proxy)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing n8n workflow patterns
- `n8n/workflows/rules-to-metagraph.json` — Reference pattern for webhook + prompt building + Ollama + Neo4j + execution-result flow (13 nodes)
- `n8n/workflows/graph-query-mcp.json` — Reference pattern for query workflow with read-only Cypher generation (15 nodes)

### Data service endpoints
- `data-service/app.py` lines 893-928 — Execution result store/poll endpoints that knowledge workflows will reuse
- `data-service/app.py` lines 595-600 — Full-text index creation (`knowledge_note_search`) used by query workflow
- `data-service/app.py` lines 934-997 — Existing knowledge CRUD + folder ingest endpoints (Phase 2 output)

### Graph schema
- `training/dataset_schema.json` — v3 schema definition (knowledge nodes use same project isolation pattern)
- `cypher_template.txt` — Cypher template reference for prompt construction patterns

### UI integration point
- `graph-viewer/index.html` lines 1554-1676 — Existing async polling pattern (startPollingResult) that Phase 5 UI will use with new workflow keys

### Requirements
- `.planning/REQUIREMENTS.md` — INSK-01, INSK-04, QRYK-01, QRYK-02, QRYK-03, INFR-02, HSTY-01

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Execution result polling**: `data-service/app.py` has `EXECUTION_RESULTS` dict + store/get endpoints — knowledge workflows post to same store with new workflow keys
- **n8n workflow pattern**: `rules-to-metagraph.json` provides the exact blueprint: webhook → set defaults → build prompt → Ollama HTTP → process response → Neo4j execute → post execution-result
- **Full-text index**: `ensure_knowledge_indexes()` already creates `knowledge_note_search` index on `KnowledgeNote.title` and `KnowledgeNote.content` — ready for query workflow to use
- **Knowledge CRUD endpoints**: Phase 2 built list/get/update/delete at `/knowledge/note*` — session list endpoint (`/knowledge/sessions/{project}`) needs to be added

### Established Patterns
- **Prompt construction**: n8n Function node builds multi-section prompt with schema constraints + few-shot examples + existing entities (see Build LLM Prompt in rules-to-metagraph)
- **Neo4j HTTP API**: n8n sends Cypher via POST to `http://neo4j:7474/db/neo4j/tx/commit` with statements array
- **Ollama API**: n8n calls `http://ollama:11434/api/generate` with `{model, prompt, stream: false}`
- **Execution result flow**: n8n posts to `http://data-service:8000/execution-result` with `{executionId, workflow, status, data}`

### Integration Points
- **Nginx proxy**: `/n8n/` already proxied — new webhook paths `/webhook/dg/knowledge-*` route through existing proxy
- **UI polling**: `graph-viewer/index.html` `startPollingResult()` polls `/execution-result/latest/{workflow}` — Phase 5 will use workflow keys `knowledge-ingest` and `knowledge-query`
- **data-service sessions endpoint**: Need to add `GET /knowledge/sessions/{project}` for session history retrieval (serves Phase 7 UI)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following existing n8n workflow patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-n8n-knowledge-workflows-llm-ingest-and-query*
*Context gathered: 2026-04-06*
