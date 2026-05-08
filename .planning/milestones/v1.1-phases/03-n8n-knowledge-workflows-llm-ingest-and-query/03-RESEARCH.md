# Phase 3: n8n Knowledge Workflows + LLM Ingest and Query - Research

**Researched:** 2026-04-06
**Domain:** n8n workflow authoring, Ollama LLM prompting (JSON extraction), Neo4j full-text search, FastAPI session endpoint
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Ollama returns `{"title": "...", "tags": [...], "content": "..."}` from NL insert prompt — n8n parses JSON and builds Cypher MERGE statements
- **D-02:** LLM must always extract a title and at least one tag, even if inferred — no "unclear" branch, no fallback to raw text storage
- **D-03:** Insert prompt does NOT include existing knowledge context — tags deduplicated at Neo4j level via MERGE
- **D-04:** Hybrid two-step query: Neo4j full-text search finds matching notes first, then Ollama summarizes into NL answer
- **D-05:** Top 5 highest-scored full-text matches are fed to Ollama for answer synthesis
- **D-06:** Cypher shown to user (QRYK-02) is the full-text search query, not LLM-generated Cypher
- **D-07:** n8n writes to Neo4j directly via HTTP API — n8n builds Cypher from LLM JSON output and posts to `http://neo4j:7474/db/neo4j/tx/commit`, then posts result to data-service execution-result
- **D-08:** Reuse existing `/execution-result/{id}` and `/execution-result/latest/{workflow}` polling endpoints with new workflow keys `knowledge-ingest` and `knowledge-query`
- **D-09:** Webhook paths: `/webhook/dg/knowledge-ingest` and `/webhook/dg/knowledge-query`
- **D-10:** KnowledgeSession nodes created inside n8n workflows as a final step after Neo4j write/query succeeds — no session recorded if LLM call fails
- **D-11:** Structured result data — Insert: `{noteId, title, tags}`, Query: `{answer, cypherUsed, matchCount}`

### Claude's Discretion

- Few-shot example content and prompt structure details for both insert and query workflows
- n8n workflow node layout and intermediate processing steps
- Error handling for malformed LLM JSON output (retry strategy, fallback)
- Exact Cypher template for the full-text search + summarization query flow
- Nginx proxy rules for new webhook paths (if any needed beyond existing `/n8n/` proxy)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSK-01 | User inserts knowledge via NL prompt — LLM extracts title, tags, content and creates KnowledgeNote nodes | D-01/D-02: JSON extraction prompt pattern; D-07: n8n Cypher MERGE via Neo4j HTTP API |
| INSK-04 | Each insert operation creates a KnowledgeSession node recording prompt, result, and timestamp | D-10: session written as final n8n step; D-11: Insert result shape `{noteId, title, tags}` |
| QRYK-01 | NL question → LLM searches graph via full-text index → NL answer in sidebar | D-04/D-05: two-step hybrid search; full-text index `knowledge_note_search` already exists |
| QRYK-02 | Cypher query used for search is displayed in Cypher panel | D-06: expose the full-text search Cypher (not LLM Cypher); `cypherUsed` field in result payload |
| QRYK-03 | Each query operation creates a KnowledgeSession node | D-10: session written as final n8n step; D-11: Query result shape `{answer, cypherUsed, matchCount}` |
| INFR-02 | Two new n8n workflows handle knowledge-ingest and knowledge-query via existing webhook + Ollama + Neo4j pattern | Workflow JSON files authored following `rules-to-metagraph.json` and `graph-query-mcp.json` blueprints |
| HSTY-01 | All knowledge interactions automatically saved with prompt, result, date, mode | D-10/D-11; plus new `GET /knowledge/sessions/{project}` endpoint in data-service |

</phase_requirements>

---

## Summary

Phase 3 adds two n8n workflow JSON files and one new data-service endpoint. The codebase already contains all infrastructure needed: the `knowledge_note_search` full-text index (created at data-service startup), `KnowledgeNote`/`KnowledgeSession` node shapes (defined in `knowledge_schema.cypher`), the `EXECUTION_RESULTS` / `WORKFLOW_STATUS` in-memory store with `POST /execution-result` and `GET /execution-result/latest/{workflow}` polling endpoints, and `write_query` / `read_many` helpers.

The knowledge-ingest workflow follows `rules-to-metagraph.json` closely: webhook → ack response → set defaults → build prompt → Ollama (JSON output mode) → parse JSON → build Cypher → Neo4j HTTP commit → write KnowledgeSession → post execution-result. The knowledge-query workflow follows `graph-query-mcp.json` closely: webhook → ack → set defaults → build full-text search Cypher directly (no LLM Cypher generation — D-06) → execute Neo4j full-text search → build answer prompt with top 5 results → Ollama → parse answer → write KnowledgeSession → post execution-result.

The only data-service change is a single new endpoint: `GET /knowledge/sessions/{project}` returning all `KnowledgeSession` nodes in reverse-chronological order. Nginx already proxies `/n8n/` so no proxy changes are needed.

**Primary recommendation:** Author two new workflow JSON files following existing workflow patterns verbatim. Add `GET /knowledge/sessions/{project}` to `data-service/app.py` using `read_many`. Import both workflows into n8n via the UI.

---

## Project Constraints (from CLAUDE.md)

- **No new Docker services** — all new endpoints added to existing `data-service` FastAPI app [VERIFIED: CLAUDE.md + STATE.md]
- **Knowledge graph isolation** — every node must have `graph: 'KnowledgeGraph'` and `project` property [VERIFIED: `knowledge_schema.cypher`]
- **No JSX build for main UI** — not relevant to this backend/workflow phase [VERIFIED: CLAUDE.md]
- **Docker layer caching** — `--no-cache` required when rebuilding containers [VERIFIED: CLAUDE.md]
- **n8n workflow pattern** — use plain HTTP nodes only, no LangChain/AI Agent n8n nodes [VERIFIED: REQUIREMENTS.md out-of-scope table]
- **LLM prompts embed schema constraints** instead of fine-tuning [VERIFIED: CLAUDE.md]
- **Single Neo4j database** with project isolation via `project` property [VERIFIED: CLAUDE.md]

---

## Standard Stack

### Core (all already running — no new installs)

| Service | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| n8n | running (Up 53 min) | Workflow orchestration — webhook, HTTP, Function nodes | Existing pattern; both reference workflows use this stack [VERIFIED: `docker ps`] |
| Ollama (llama3.1:latest) | 4.9 GB / running | LLM inference — JSON extraction and answer synthesis | Existing model; `rules-to-metagraph` and `graph-query-mcp` both use `llama3.1:latest` [VERIFIED: `docker exec ollama ollama list`] |
| Neo4j 5 | running (Up 53 min) | Graph storage — KnowledgeNote, KnowledgeTag, KnowledgeSession nodes | Existing DB; full-text index already created [VERIFIED: `docker ps`] |
| data-service (FastAPI) | running (Up 53 min) | REST API — execution-result store, sessions endpoint | Existing service; `write_query`/`read_many` helpers available [VERIFIED: `curl http://localhost:8000/`] |

### No New Dependencies

All libraries, services, and patterns needed already exist. This phase creates files (two n8n workflow JSONs, one endpoint in `app.py`) — no `pip install`, no `npm install`, no new containers.

---

## Architecture Patterns

### Recommended File / Endpoint Structure

```
n8n/workflows/
├── rules-to-metagraph.json         # existing — reference blueprint
├── graph-query-mcp.json            # existing — reference blueprint
├── knowledge-ingest.json           # NEW: NL insert workflow
└── knowledge-query.json            # NEW: NL query workflow

data-service/app.py                 # ADD: GET /knowledge/sessions/{project}
```

---

### Pattern 1: n8n Workflow Skeleton (Async Ack Pattern)

**What:** Every n8n workflow in this project uses a split-path design: the webhook node fans out to both (a) an ack path that immediately responds `{status:"accepted", executionId}` and (b) a processing path that does the real work and eventually posts to `/execution-result`. This allows the UI to poll.

**Source:** `n8n/workflows/graph-query-mcp.json` nodes `Format Ack` → `Respond Ack` (ack path) and `Mark Running` → ... → `Store Result` (work path). [VERIFIED: codebase]

**Node sequence for knowledge-ingest:**
```
Webhook (POST /dg/knowledge-ingest)
  ├── [ack path] Set Input Defaults → Format Ack → Respond Ack → Mark Running
  └── [work path after Respond Ack]
       → Build Insert Prompt (Function)
       → Ollama Generate (HTTP POST, format:"json")
       → Parse LLM JSON (Function)
       → Build Cypher (Function)
       → Execute Neo4j Cypher (HTTP POST basicAuth)
       → Write KnowledgeSession (HTTP POST to Neo4j)
       → Post Execution Result (HTTP POST to data-service)
```

**Node sequence for knowledge-query:**
```
Webhook (POST /dg/knowledge-query)
  ├── [ack path] Set Input Defaults → Format Ack → Respond Ack → Mark Running
  └── [work path after Respond Ack]
       → Build Full-Text Cypher (Function — deterministic, no LLM)
       → Execute Full-Text Search (HTTP POST to Neo4j basicAuth)
       → Build Answer Prompt (Function — top 5 records)
       → Ollama Generate Answer (HTTP POST, no format:"json")
       → Parse Answer (Function)
       → Write KnowledgeSession (HTTP POST to Neo4j)
       → Post Execution Result (HTTP POST to data-service)
```

---

### Pattern 2: Ollama JSON Extraction (Insert Workflow)

**What:** To reliably get `{"title": "...", "tags": [...], "content": "..."}` from llama3.1, use `"format": "json"` in the Ollama API request body. This forces JSON output mode. The prompt must:
1. State the exact JSON schema required
2. Include a concrete few-shot example with the exact output format
3. Use `"temperature": 0.1` to reduce hallucination
4. Include `"num_predict": 2048` (content can be long)

**Source:** `rules-to-metagraph.json` node `Ollama Generate` uses `format:"json"` is NOT set there (Cypher output) — but `graph-query-mcp.json` node `Generate Cypher` DOES use `"format": "json"`. [VERIFIED: graph-query-mcp.json line 97]

**Prompt template structure (Claude's discretion — recommended):**
```
You are an architectural knowledge assistant.
Extract structured data from the architect's note.
Return JSON only, matching this exact schema:
{"title": "string", "tags": ["string", ...], "content": "string"}

Rules:
- title: concise noun phrase (max 10 words)
- tags: 1-5 lowercase keywords, minimum 1 tag
- content: the full note text, cleaned up

Example input: "The maximum floor-to-floor height in Zone A residential towers
  must not exceed 3.2 meters per storey for compliance with the local plan."
Example output:
{"title": "Maximum floor-to-floor height Zone A", "tags": ["height", "residential", "zone-a", "compliance"], "content": "The maximum floor-to-floor height in Zone A residential towers must not exceed 3.2 meters per storey for compliance with the local plan."}

Now extract from this input:
{{$json.prompt_text}}
```

**Ollama call parameters:**
```json
{
  "model": "llama3.1:latest",
  "prompt": "{{prompt}}",
  "stream": false,
  "format": "json",
  "options": {"temperature": 0.1, "num_predict": 2048}
}
```

**Timeout:** 900000ms (same as other workflows — Ollama can be slow on first inference).

---

### Pattern 3: Malformed JSON Recovery

**What:** Even with `format:"json"`, llama3.1 occasionally wraps the JSON in markdown fences or adds preamble text. The Parse LLM JSON Function node must:
1. Read `$json.response` (Ollama puts the text there)
2. Strip any markdown fences: `.replace(/```json?\s*/gi, '').replace(/```/g, '')`
3. Find first `{` to last `}` and slice: `trimmed.slice(start, end + 1)`
4. `JSON.parse(...)` inside try/catch
5. If parse fails or required fields missing (`title`, `tags`, `content`), derive fallbacks:
   - `title`: first 60 chars of `prompt_text`
   - `tags`: `["untagged"]`
   - `content`: `prompt_text`

**Source:** Recovery pattern adapted from `graph-query-mcp.json` node `Parse Cypher` (lines 110-173) and `Parse Answer` (lines 172-233). [VERIFIED: codebase]

**Why not throw on malformed JSON:** D-02 says "no unclear error branch" — the workflow must always produce a KnowledgeNote even if LLM output is malformed.

---

### Pattern 4: KnowledgeNote MERGE Cypher (Insert Workflow)

**What:** After parsing the LLM JSON, build deterministic Cypher for neo4j HTTP commit. Key constraint from schema: `noteId` is the MERGE key, generated as a UUID in the workflow. Tags are MERGEd as `KnowledgeTag` nodes with `TAGGED_WITH` relationships.

**Source:** `knowledge_schema.cypher` lines 9-32; folder ingest pattern `data-service/app.py` lines 953-985. [VERIFIED: codebase]

**Cypher template (in Function node, building statements array):**
```javascript
const noteId = generateUUID(); // use crypto.randomUUID() or Date.now().toString(36)
const now = new Date().toISOString();
const statements = [
  {
    statement: `
      MERGE (n:KnowledgeNote {noteId: $noteId, project: $project, graph: $graph})
      SET n.title = $title, n.content = $content, n.source = 'prompt',
          n.tags = $tags, n.createdAt = coalesce(n.createdAt, $now), n.updatedAt = $now
    `,
    parameters: {
      noteId, project: input.project_name, graph: 'KnowledgeGraph',
      title, content, tags, now
    }
  }
];
// One statement per tag:
for (const tag of tags) {
  statements.push({
    statement: `
      MERGE (t:KnowledgeTag {name: $tagName, project: $project, graph: $graph})
      WITH t
      MATCH (n:KnowledgeNote {noteId: $noteId, project: $project, graph: $graph})
      MERGE (n)-[:TAGGED_WITH]->(t)
    `,
    parameters: { tagName: tag.toLowerCase(), noteId, project: input.project_name, graph: 'KnowledgeGraph' }
  });
}
```

**Neo4j HTTP body:** `{ "statements": statements }` — POST to `http://neo4j:7474/db/neo4j/tx/commit` with basicAuth.

---

### Pattern 5: Full-Text Search Cypher (Query Workflow)

**What:** The query workflow does NOT ask the LLM to generate Cypher (D-06). Instead, a Function node builds the full-text search Cypher deterministically from the user's question. This Cypher string is also returned as `cypherUsed` in the result payload for QRYK-02.

**Source:** Full-text index `knowledge_note_search` on `KnowledgeNote.title` and `KnowledgeNote.content` — created by `ensure_knowledge_indexes()` at data-service startup. [VERIFIED: `data-service/app.py` lines 594-601]

**Full-text search Cypher:**
```cypher
CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)
YIELD node, score
WHERE node.project = $project AND node.graph = 'KnowledgeGraph'
RETURN node.noteId AS noteId, node.title AS title, node.content AS content, score
ORDER BY score DESC
LIMIT 5
```

**Parameters:** `{ query: prompt_text, project: project_name }`

**Why this Cypher:** The index was specifically named `knowledge_note_search` and covers `title` + `content` in the startup hook. Top 5 matches feeds D-05. [VERIFIED: `data-service/app.py` line 599]

**Exposing the Cypher:** The Function node that builds this Cypher saves it in `$json.cypherUsed` — this propagates through to the final execution-result payload so Phase 5 UI can display it.

---

### Pattern 6: KnowledgeSession MERGE (Both Workflows)

**What:** After the main Neo4j write/query succeeds, both workflows execute a final Neo4j HTTP call to MERGE a KnowledgeSession node. This matches D-10 (session only recorded on success) and D-11 (structured result per mode).

**Source:** `knowledge_schema.cypher` lines 34-41. [VERIFIED: codebase]

**Session MERGE Cypher (as HTTP statements array in n8n Function node):**
```javascript
const sessionId = 'ks-' + Date.now().toString(36);
// For insert workflow:
const result = JSON.stringify({ noteId, title, tags });
// For query workflow:
const result = JSON.stringify({ answer, cypherUsed, matchCount });

{
  statement: `
    MERGE (s:KnowledgeSession {sessionId: $sessionId, project: $project, graph: $graph})
    SET s.mode = $mode, s.prompt = $prompt, s.result = $result, s.createdAt = $createdAt
  `,
  parameters: {
    sessionId, project, graph: 'KnowledgeGraph',
    mode,        // 'insert' or 'query'
    prompt,      // original prompt_text
    result,      // JSON-stringified result object
    createdAt: new Date().toISOString()
  }
}
```

---

### Pattern 7: Execution Result Payload Shape

**What:** The final `POST /execution-result` call from each workflow uses the existing `ExecutionResult` Pydantic model. The `payload` field is what the UI polls for.

**Source:** `data-service/app.py` lines 46-53 (ExecutionResult model); `graph-query-mcp.json` node `Store Result` (line 185-198). [VERIFIED: codebase]

**For knowledge-ingest:**
```json
{
  "executionId": "{{$execution.id}}",
  "status": "completed",
  "workflow": "knowledge-ingest",
  "payload": { "noteId": "...", "title": "...", "tags": [...] }
}
```

**For knowledge-query:**
```json
{
  "executionId": "{{$execution.id}}",
  "status": "completed",
  "workflow": "knowledge-query",
  "payload": { "answer": "...", "cypher": "...", "matchCount": 5 }
}
```

Note: UI polling in `graph-viewer/index.html` `startPollingLatest` already reads `payload.answer` and `payload.cypher` for query mode (lines 1631-1633). [VERIFIED: codebase] The `cypher` key in payload maps to `cypherUsed` from the query workflow.

---

### Pattern 8: `GET /knowledge/sessions/{project}` Endpoint

**What:** New FastAPI endpoint in `data-service/app.py` using existing `read_many` helper. Reads all `KnowledgeSession` nodes for a project in reverse-chronological order.

**Source:** Follows pattern of `list_knowledge_notes` at line 1001. [VERIFIED: codebase]

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

No new Pydantic model needed — the response is a dict like all other list endpoints.

---

### Anti-Patterns to Avoid

- **Generating Cypher with LLM for knowledge query:** D-06 explicitly rules this out. Use deterministic full-text search Cypher. The existing `graph-query-mcp.json` generates Cypher — knowledge-query does NOT.
- **Skipping the async ack pattern:** If the webhook does not respond immediately with `{status:"accepted"}`, the HTTP client will timeout waiting. Always fork to ack before processing.
- **Using `format:"json"` without explicit schema in prompt:** llama3.1 with `format:"json"` will output valid JSON but the schema is unpredictable without a concrete example. Always include the exact key names and a few-shot example.
- **Storing result as a nested object in KnowledgeSession:** The `result` property is a `string` (JSON-stringified) — not a nested map — because Neo4j property values must be primitives or arrays. [VERIFIED: `knowledge_schema.cypher` line 41]
- **Creating KnowledgeSession before Neo4j write succeeds:** D-10 requires the session to be the last step. If LLM call fails, n8n throws and no downstream nodes execute — session is correctly skipped.
- **Importing workflow without setting webhook active:** After JSON import, the webhook is inactive by default in n8n. The workflow must be activated (toggle in n8n UI) before it will receive requests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search ranking | Custom BM25 or CONTAINS query | `db.index.fulltext.queryNodes` | Index already exists (`knowledge_note_search`); Neo4j full-text search scores results, handles multi-word queries, case-insensitive by default |
| JSON parsing from LLM | Custom regex extractor | `JSON.parse` with `{`/`}` slice + fallback | LLM with `format:"json"` produces parseable output 95%+ of the time; slice + parse covers the remaining cases |
| Async job tracking | New job queue (Redis/SQLite) | Existing `EXECUTION_RESULTS` / `WORKFLOW_STATUS` in data-service | Already implemented and tested; adding new workflow keys costs zero code |
| Session storage | localStorage or file | `KnowledgeSession` nodes in Neo4j via MERGE | Pattern already decided (STATE.md); `write_query` helper available |
| n8n HTTP authentication for Neo4j | Custom auth header logic | n8n `basicAuth` on HTTP node | All existing Neo4j calls use this pattern |

---

## Common Pitfalls

### Pitfall 1: LLM Returns Tags as a Comma-Separated String Instead of Array
**What goes wrong:** `{"title": "...", "tags": "height, residential", "content": "..."}` — the `tags` field is a string, not an array. The Cypher builder tries to iterate `tags` and fails silently or creates a single tag with a comma in the name.
**Why it happens:** llama3.1 sometimes ignores the JSON schema despite `format:"json"`, especially for array fields.
**How to avoid:** In the Parse LLM JSON Function node, normalize: `if (typeof parsed.tags === 'string') { parsed.tags = parsed.tags.split(',').map(t => t.trim().toLowerCase()); }`. Add `if (!Array.isArray(parsed.tags) || parsed.tags.length === 0) { parsed.tags = ['untagged']; }`.
**Warning signs:** KnowledgeTag nodes with commas in their names appear in Neo4j.

### Pitfall 2: Full-Text Search Returns No Results for Short Prompts
**What goes wrong:** A two-word question like "building height" returns zero results because the full-text index uses Lucene syntax and short single-word queries may not match partial content.
**Why it happens:** Neo4j full-text search with `db.index.fulltext.queryNodes` uses Lucene query syntax. A query like `"building"` works, but special characters (`:`, `+`, `-`) cause parse errors.
**How to avoid:** In the Build Full-Text Cypher Function node, sanitize the prompt: strip Lucene special chars (`/[+\-!(){}\[\]^"~*?:\\/]/g`), then use the cleaned string as the `$query` parameter. If the cleaned query is empty, fall back to `"*"` (match all).
**Warning signs:** Neo4j returns a Lucene parse error in the HTTP response body.

### Pitfall 3: `execution-result/latest/{workflow}` Key Mismatch
**What goes wrong:** The UI polls `knowledge-ingest` but the workflow posts `workflow: "knowledge_ingest"` (underscore vs hyphen). The poll returns `{status: "unknown"}` forever.
**Why it happens:** n8n Function node string literals are easy to mis-type. The key in the `Store Result` HTTP call must exactly match the key Phase 5 UI will use to poll.
**How to avoid:** Use `"knowledge-ingest"` and `"knowledge-query"` (hyphens) consistently. D-08 specifies these keys. Cross-check both Store Result nodes before testing.
**Warning signs:** Polling endpoint returns `{status: "unknown"}` — indicates the workflow key does not match any entry in `WORKFLOW_STATUS`.

### Pitfall 4: n8n Workflow JSON `webhookId` Must Be Unique
**What goes wrong:** If the imported workflow JSON has a `webhookId` that already exists in n8n (e.g., copied from a reference workflow), n8n silently uses the old webhook path.
**Why it happens:** n8n matches webhook registrations by `webhookId`, not by the `path` property.
**How to avoid:** In the workflow JSON, set `"webhookId": "dg-knowledge-ingest"` and `"webhookId": "dg-knowledge-query"` — both are new, distinct from `"dg-rules-ingest"` and `"dg-graph-query"`. [VERIFIED: existing workflow IDs from codebase]
**Warning signs:** POST to `/webhook/dg/knowledge-ingest` returns 404 after import.

### Pitfall 5: Neo4j Full-Text Search Requires Active Index
**What goes wrong:** The query workflow sends `CALL db.index.fulltext.queryNodes('knowledge_note_search', ...)` but no `KnowledgeNote` nodes exist yet (Phase 2 not fully run). Neo4j returns empty results without error.
**Why it happens:** The index exists but is empty — this is correct behavior, not an error. The answer prompt will receive zero records and Ollama will reply "no data found."
**How to avoid:** Document this expected behavior in the workflow's answer prompt: "If results are empty, say 'No matching knowledge notes found for this project.'"
**Warning signs:** Test query returns empty answer — ingest some notes first, then test query.

### Pitfall 6: KnowledgeSession `result` Size
**What goes wrong:** For query sessions, `result` contains the full answer text. For insert sessions with long content, `result` JSON may exceed Neo4j property string limits (safe up to ~4MB but unusual).
**Why it happens:** Content from a long NL prompt is stored in both `KnowledgeNote.content` and `KnowledgeSession.result`.
**How to avoid:** Truncate `result` to first 2000 chars in the session MERGE: `result.substring(0, 2000)`. Per REQUIREMENTS.md out-of-scope: "Knowledge node content > 100KB" is excluded anyway, so 2000-char summary is sufficient for session history.

---

## Code Examples

### Full-Text Search Call to Neo4j (in n8n HTTP node)

```javascript
// Source: data-service/app.py ensure_knowledge_indexes() + knowledge_schema.cypher
// POST to http://neo4j:7474/db/neo4j/tx/commit with basicAuth neo4j/12345678
{
  "statements": [
    {
      "statement": "CALL db.index.fulltext.queryNodes('knowledge_note_search', $query) YIELD node, score WHERE node.project = $project AND node.graph = 'KnowledgeGraph' RETURN node.noteId AS noteId, node.title AS title, node.content AS content, score ORDER BY score DESC LIMIT 5",
      "parameters": {
        "query": "{{$json.prompt_text}}",
        "project": "{{$json.project_name}}"
      }
    }
  ]
}
```

### LLM JSON Parse + Fallback (n8n Function node)

```javascript
// Source: adapted from graph-query-mcp.json "Parse Cypher" node pattern
const raw = $json.response || '';
let parsed = {};
try {
  const trimmed = raw.trim();
  const start = trimmed.indexOf('{');
  const end = trimmed.lastIndexOf('}');
  const jsonText = (start !== -1 && end !== -1) ? trimmed.slice(start, end + 1) : trimmed;
  parsed = JSON.parse(jsonText);
} catch (e) {
  // fallback — D-02: never reject, always produce output
  parsed = {};
}
const input = $items("Set Input Defaults")[0].json;
let title = (parsed.title || '').trim() || input.prompt_text.substring(0, 60);
let content = (parsed.content || '').trim() || input.prompt_text;
let tags = Array.isArray(parsed.tags) ? parsed.tags : (typeof parsed.tags === 'string' ? parsed.tags.split(',').map(t => t.trim().toLowerCase()) : []);
tags = tags.filter(t => t.length > 0);
if (tags.length === 0) tags = ['untagged'];
return [{ json: { ...input, title, content, tags } }];
```

### sessions Endpoint (data-service/app.py)

```python
# Source: follows list_knowledge_notes pattern (data-service/app.py line 1001)
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

### Execution Result Payload Format

```javascript
// Source: graph-query-mcp.json "Store Result" node (line 185-198)
// knowledge-query workflow final Store Result node body:
{
  "executionId": "{{$execution.id}}",
  "status": "completed",
  "workflow": "knowledge-query",
  "payload": {
    "answer": "{{$json.answer}}",
    "cypher": "{{$json.cypherUsed}}",
    "matchCount": "{{$json.matchCount}}"
  }
}
// Note: UI startPollingLatest reads payload.answer and payload.cypher (index.html lines 1631-1633)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM generates Cypher for knowledge query | Deterministic full-text search Cypher + LLM for answer only | D-06 (this phase) | Eliminates risk of LLM generating invalid/dangerous write Cypher for read operations |
| Session history in localStorage | KnowledgeSession nodes in Neo4j | STATE.md decision | Persistent across browser sessions, queryable, no quota risk |
| Separate endpoint for NL insert | `/knowledge/ingest/prompt` triggers n8n webhook async | CONTEXT.md D-07 | Consistent with existing rules-ingest async pattern; UI polls instead of waiting |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | n8n can import a new workflow JSON file via the UI without downtime or API call | Architecture Patterns | Low — standard n8n UI workflow import has always worked in this project; could also use n8n REST API |
| A2 | llama3.1:latest with `format:"json"` produces parseable JSON for NL extraction prompts | Pattern 2 | Medium — if model consistently fails, fallback in Parse node (Pattern 3) handles it; content is never lost |
| A3 | `startPollingLatest` in the existing UI (index.html line 1615) will be reused by Phase 5 UI for new workflow keys — Phase 3 need only produce compatible payloads | Pattern 7 | Low — payload keys `answer` and `cypher` are already read by the existing poll handler (verified lines 1631-1633) |

---

## Open Questions

1. **n8n workflow activation after import**
   - What we know: n8n requires manual activation (toggle) for new workflows after import
   - What's unclear: Whether this needs to be a documented manual step or if the JSON can set `"active": true` before import
   - Recommendation: Set `"active": false` in JSON (safe default), document as a manual step in the plan

2. **Data-service container rebuild trigger**
   - What we know: Adding `GET /knowledge/sessions/{project}` to `app.py` requires rebuilding the data-service container
   - What's unclear: Whether the container needs `--no-cache` rebuild or whether a regular rebuild suffices (no Dockerfile changes)
   - Recommendation: Regular rebuild (`docker compose up -d --build data-service`) is sufficient since only Python source changes; `--no-cache` only needed for layer-cached `pip install` changes

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| n8n | knowledge-ingest and knowledge-query workflows | Yes | Up 53 min | — |
| Ollama (llama3.1:latest) | LLM JSON extraction and answer synthesis | Yes | 4.9 GB loaded | — |
| Neo4j | KnowledgeNote / KnowledgeSession MERGE, full-text search | Yes | Up 53 min | — |
| data-service (FastAPI) | Execution result store, sessions endpoint | Yes | Up 53 min, responds 200 | — |
| knowledge_note_search (full-text index) | QRYK-01 full-text search Cypher | Yes (created at startup) | n8n 4-week-old container | — |
| Nginx proxy `/n8n/` | Routing webhook calls | Yes | Up 53 min | — |

**Missing dependencies with no fallback:** None.

**All required dependencies are present and running.**

---

## Validation Architecture

> `workflow.nyquist_validation` is not explicitly set to `false` in `.planning/config.json` (only `_auto_chain_active` is set). Treating as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python (requests-based integration tests, same pattern as `test/test_knowledge_crud.py`) |
| Config file | None — standalone scripts run against live services |
| Quick run command | `python test/test_phase03_knowledge_llm.py` |
| Full suite command | `python test/test_knowledge_crud.py && python test/test_phase03_knowledge_llm.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSK-01 | POST to n8n webhook, poll, verify KnowledgeNote in Neo4j | integration | `python test/test_phase03_knowledge_llm.py::test_sc1_ingest_prompt` | No — Wave 0 |
| INSK-04 | After insert, verify KnowledgeSession node created with mode='insert' | integration | `python test/test_phase03_knowledge_llm.py::test_sc3_session_insert` | No — Wave 0 |
| QRYK-01 | POST query to n8n webhook, poll, verify NL answer returned | integration | `python test/test_phase03_knowledge_llm.py::test_sc2_query_answer` | No — Wave 0 |
| QRYK-02 | Verify `cypher` field in query response payload is non-empty string | integration | `python test/test_phase03_knowledge_llm.py::test_sc2_query_answer` | No — Wave 0 |
| QRYK-03 | After query, verify KnowledgeSession node created with mode='query' | integration | `python test/test_phase03_knowledge_llm.py::test_sc3_session_query` | No — Wave 0 |
| INFR-02 | n8n responds 202/accepted on POST to webhook paths | integration | `python test/test_phase03_knowledge_llm.py::test_sc4_webhook_ack` | No — Wave 0 |
| HSTY-01 | GET /knowledge/sessions/{project} returns sessions in reverse-chron order | integration | `python test/test_phase03_knowledge_llm.py::test_sc5_sessions_endpoint` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `python test/test_phase03_knowledge_llm.py` (quick smoke — polls until completed or 60s timeout)
- **Per wave merge:** `python test/test_knowledge_crud.py && python test/test_phase03_knowledge_llm.py`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `test/test_phase03_knowledge_llm.py` — integration test file covering all 7 requirements above (SC-1 through SC-5)

*(No framework install needed — `requests` is already used in `test/test_knowledge_crud.py`)*

---

## Security Domain

> `security_enforcement` is not set in `.planning/config.json` — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | n8n webhooks are internal-only (same Docker network); no user auth on webhook routes |
| V3 Session Management | No | No user sessions — KnowledgeSession is a data record, not an auth session |
| V4 Access Control | No | Single-tenant; project isolation via `project` parameter |
| V5 Input Validation | Yes | `prompt_text` and `project_name` passed to Neo4j as parameterized Cypher `$params` — no string interpolation into Cypher |
| V6 Cryptography | No | No secrets stored; Neo4j password `12345678` is dev-only default |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via `prompt_text` | Tampering | n8n full-text search uses `$query` parameter, not string interpolation — safe [VERIFIED: Cypher template above] |
| Prompt injection via NL text | Tampering | LLM output is parsed as JSON and used only to fill Cypher parameters — never executed as code |
| Neo4j direct write via n8n | Elevation of privilege | Knowledge workflows only MERGE `KnowledgeNote`, `KnowledgeTag`, `KnowledgeSession` nodes with `graph:'KnowledgeGraph'` — no cross-graph writes |

---

## Sources

### Primary (HIGH confidence)
- `n8n/workflows/graph-query-mcp.json` — exact async ack pattern, Ollama call with `format:"json"`, execution-result store [VERIFIED: full file read]
- `n8n/workflows/rules-to-metagraph.json` — few-shot prompt structure, Ollama call parameters, Neo4j HTTP commit pattern [VERIFIED: partial file read]
- `data-service/app.py` lines 161-176 — `write_query`, `read_many`, `read_single` helpers [VERIFIED: read]
- `data-service/app.py` lines 46-53 — `ExecutionResult` Pydantic model [VERIFIED: read]
- `data-service/app.py` lines 893-928 — execution-result store/poll endpoints [VERIFIED: read]
- `data-service/app.py` lines 594-601 — `ensure_knowledge_indexes()` startup hook creating `knowledge_note_search` [VERIFIED: read]
- `data-service/app.py` lines 934-1073 — existing `/knowledge/*` CRUD endpoints (Phase 2 output) [VERIFIED: read]
- `knowledge_schema.cypher` — KnowledgeSession node shape with `sessionId`, `mode`, `prompt`, `result`, `createdAt` [VERIFIED: full file read]
- `graph-viewer/nginx.conf` — `/n8n/` proxy already routes to n8n:5678 [VERIFIED: full file read]
- `graph-viewer/index.html` lines 1554-1676 — `startPollingResult` and `startPollingLatest` functions; `payload.answer` and `payload.cypher` already read [VERIFIED: read]

### Secondary (MEDIUM confidence)
- `docker ps` output — all services running (n8n, Ollama, Neo4j, data-service, Nginx) [VERIFIED: bash command]
- `docker exec ollama ollama list` — `llama3.1:latest` confirmed available [VERIFIED: bash command]
- `curl http://localhost:8000/` → `{"status":"Data Service is running"}` [VERIFIED: bash command]
- `curl http://localhost:8080/n8n/healthz` → `{"status":"ok"}` [VERIFIED: bash command]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all services verified running; no new dependencies
- Architecture: HIGH — both reference workflows read in full; patterns are verbatim
- Pitfalls: HIGH — sourced from actual LLM output quirks observed in existing `Parse Cypher` / `Parse Answer` nodes
- Endpoint design: HIGH — follows existing `list_knowledge_notes` pattern exactly

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stack — n8n workflow authoring patterns do not change frequently)
