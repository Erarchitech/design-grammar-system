# Phase 4: Update Flow Endpoints - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Three-step Match -> Propose -> Confirm backend for knowledge note updates. An architect describes what to change in natural language, receives a list of matching notes ranked by relevance, gets a diff-annotated proposed edit per note, and confirms the write. No LLM output silently overwrites Neo4j — the user must confirm before any content changes.

</domain>

<decisions>
## Implementation Decisions

### Match Endpoint Strategy
- **D-01:** POST `/knowledge/update/match` uses direct Neo4j full-text search (`knowledge_note_search` index) — no LLM involved in matching
- **D-02:** Returns top 10 candidate notes ranked by full-text relevance score
- **D-03:** Match endpoint lives entirely in data-service as a REST endpoint (no n8n)

### Diff Computation
- **D-04:** LLM (Ollama) receives current note content + update prompt and returns the full updated text — LLM does not annotate changes itself
- **D-05:** Python `difflib` computes word-level diff server-side comparing original vs LLM-proposed text
- **D-06:** Diff output is HTML spans with additions and deletions marked (consistent with UPDK-02 requirement)
- **D-07:** POST `/knowledge/update/propose` accepts an array of noteIds — returns diff for each selected note in one HTTP call

### Confirm Write Safety
- **D-08:** POST `/knowledge/update/confirm` uses optimistic locking via `updatedAt` timestamp — client sends the `updatedAt` from the propose step; server rejects with 409 Conflict if note was modified since
- **D-09:** Client sends the user's final edited text (from the inline textarea editor), not the raw LLM proposal — users can modify before confirming (per UPDK-04)
- **D-10:** Each confirmed update creates a KnowledgeSession node recording the prompt and affected node IDs (per UPDK-06)

### n8n vs data-service Split
- **D-11:** Match and Confirm are pure data-service REST endpoints — no n8n involvement (they don't need LLM)
- **D-12:** Propose routes through n8n for the LLM call: UI -> data-service `/knowledge/update/propose` -> data-service fetches current note content from Neo4j -> sends content + prompt to n8n webhook -> n8n calls Ollama -> posts result to execution-result -> data-service polls/receives result -> data-service runs difflib -> returns HTML diff to client
- **D-13:** New n8n workflow: `knowledge-update` with webhook path `/webhook/dg/knowledge-update` — follows Phase 3 naming convention

### Claude's Discretion
- Exact difflib function choice and word-level tokenization strategy
- n8n workflow internal node layout and prompt construction details
- Error handling for LLM returning malformed/empty text
- HTTP response shapes (field names, nesting) for all three endpoints
- How to handle Propose when LLM returns text identical to original (no-op diff)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing n8n workflow patterns
- `n8n/workflows/rules-to-metagraph.json` — Reference pattern for webhook + prompt building + Ollama + Neo4j + execution-result flow
- `n8n/workflows/graph-query-mcp.json` — Reference pattern for query workflow

### Data service endpoints (Phase 2+3 output)
- `data-service/app.py` lines 934-1085 — Existing knowledge CRUD + folder ingest + sessions endpoints (reuse patterns for new endpoints)
- `data-service/app.py` lines 893-928 — Execution result store/poll endpoints (Propose step posts results here)
- `data-service/app.py` lines 595-600 — Full-text index creation (`knowledge_note_search`) used by Match endpoint

### Phase 3 context (upstream decisions)
- `.planning/phases/03-n8n-knowledge-workflows-llm-ingest-and-query/03-CONTEXT.md` — D-07 through D-11 establish n8n workflow patterns, execution-result polling, and session tracking conventions

### Requirements
- `.planning/REQUIREMENTS.md` — UPDK-01, UPDK-02, UPDK-03, UPDK-04, UPDK-05, UPDK-06

### Graph schema
- `training/dataset_schema.json` — v3 schema definition (KnowledgeNote node shape)
- `cypher_template.txt` — Cypher template reference for prompt construction patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Full-text search**: `knowledge_note_search` index on `KnowledgeNote.title` and `KnowledgeNote.content` — Match endpoint queries this directly
- **CRUD helpers**: `read_single()`, `read_many()`, `write_query()` in `data-service/app.py` — all three endpoints use these
- **Execution result polling**: `EXECUTION_RESULTS` dict + store/get endpoints — Propose step uses same pattern with workflow key `knowledge-update`
- **Note update endpoint**: `PUT /knowledge/note/{note_id}` already does field-level updates with `updatedAt` tracking — Confirm endpoint follows similar pattern
- **n8n workflow blueprint**: `rules-to-metagraph.json` provides webhook -> prompt -> Ollama -> result posting pattern for the new `knowledge-update` workflow

### Established Patterns
- **Python difflib**: Already noted in PROJECT.md as the chosen diff approach — `difflib` is in Python stdlib, no new dependency
- **Pydantic models**: All request/response payloads use `BaseModel` with type hints (Phase 2 convention)
- **Knowledge graph isolation**: All queries filter on `graph: "KnowledgeGraph"` and `project` properties
- **Session tracking**: KnowledgeSession nodes written as final step after successful operations

### Integration Points
- **Nginx proxy**: `/data-service/` proxy already routes to FastAPI — new endpoints auto-available
- **n8n webhook proxy**: `/n8n/` proxy routes to n8n — new `/webhook/dg/knowledge-update` path works through existing proxy
- **Phase 6 UI consumer**: UI Update Panel will call these three endpoints in sequence — response shapes must support the diff editor display

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following existing data-service and n8n patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-update-flow-endpoints*
*Context gathered: 2026-04-06*
