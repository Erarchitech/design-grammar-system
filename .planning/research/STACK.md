# Stack Research

**Domain:** Project Knowledge Graph additions to existing Design Grammar System
**Researched:** 2026-04-05
**Confidence:** HIGH (Neo4j full-text indexes, FastAPI pathlib), MEDIUM (inline diff editor pattern)

## Scope

This document covers ONLY the new capabilities needed for v1.1 Project Knowledge Graph milestone. The existing validated stack (Neo4j 5, Ollama/llama3.1, n8n, React 18 via CDN, FastAPI, Docker Compose) is not re-researched.

---

## Recommended Stack

### Core Technologies (Additions/Changes)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Neo4j 5 full-text index | Built-in (no version change) | Search `KnowledgeNote` node content/title | Native Lucene-powered; `db.index.fulltext.queryNodes()` returns scored results; covers keyword + fuzzy search without adding any new service |
| FastAPI `pathlib` (stdlib) | Python 3.11 (already in container) | File system reading for repository folder ingest | `Path.rglob('*.md')` + `Path.read_text()` — zero new dependencies; existing data-service pattern uses `pathlib.Path` already |
| FastAPI `starlette.responses.JSONResponse` | Already installed via fastapi | Return file tree + content for UI | No additions; consistent with existing endpoint style |
| React 18 `createElement` + `dangerouslySetInnerHTML` | Already on CDN | Render inline text editor with red-span diff | No build step; diff is pre-computed on server and sent as HTML fragment with `<span style="color:red">` wrappers |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `difflib` (Python stdlib) | Built-in | Server-side diff computation between original and LLM-edited note | Use in data-service `POST /knowledge/nodes/{id}/preview-edit` endpoint; returns `{original, edited, diff_html}` where `diff_html` uses `<mark>` or `<span>` tags for red highlights |
| `python-frontmatter` | 3.x (pip) | Parse YAML frontmatter from Markdown files during folder ingest | Extracts title/tags from `.md` files; zero runtime overhead; only needed if ingesting Obsidian-style markdown with frontmatter headers |
| `glob` / `pathlib` (stdlib) | Built-in | Recursive file tree traversal | No pip install required; `Path.rglob('*.md')` handles nested folder structures |

### Development Tools (Unchanged)

No new dev tools needed. Existing Docker Compose `volumes` pattern (bind mount) is extended for the repository folder feature.

---

## Neo4j Full-Text Index Setup

### Index Creation (idempotent, run at data-service startup)

```cypher
CREATE FULLTEXT INDEX knowledge_note_search IF NOT EXISTS
FOR (n:KnowledgeNote)
ON EACH [n.title, n.content, n.tags]
OPTIONS {
  indexConfig: {
    `fulltext.analyzer`: 'english',
    `fulltext.eventually_consistent`: true
  }
}
```

**Why `english` analyzer:** Strips stop words and applies stemming — "buildings" matches "building". Appropriate for architectural domain text.

**Why `eventually_consistent: true`:** Defers index updates to background thread. Improves write throughput during bulk folder ingest. Acceptable for knowledge search (not transactional).

### Query Pattern

```cypher
CALL db.index.fulltext.queryNodes('knowledge_note_search', $query)
YIELD node, score
WHERE node.project = $project
RETURN node.Node_Id AS nodeId, node.title AS title,
       node.content AS content, score
ORDER BY score DESC
LIMIT 20
```

**Important:** The full-text procedure returns ALL matching nodes across the database. The `WHERE node.project = $project` post-filter is mandatory to maintain project isolation consistent with the existing SWRL graph pattern.

### Node Schema for KnowledgeNote

```cypher
MERGE (n:KnowledgeNote {Node_Id: $nodeId, project: $project})
SET
  n.graph    = 'KnowledgeGraph',
  n.title    = $title,
  n.content  = $content,
  n.tags     = $tags,       -- list<string>
  n.source   = $source,     -- 'manual' | 'file' | 'prompt'
  n.filePath = $filePath,   -- original path if source='file', else null
  n.createdAt = $createdAt,
  n.updatedAt = $updatedAt
```

**`graph: 'KnowledgeGraph'`** — distinct from `'Metagraph'` and `'ValidationGraph'` already in use. Prevents NeoVis visualization mixing unless explicitly requested.

**`Node_Id`** — follows existing `Rule_Id` convention; format `KN_<PROJECT>_<SLUG>`.

---

## File System Reading (Folder Ingest)

### Docker Volume Pattern

Add a bind mount to the `data-service` in `docker-compose.yml`:

```yaml
data-service:
  volumes:
    - ./data-service/data:/app/data
    - /path/to/repo:/app/repo:ro    # user-configurable at runtime
```

**Alternative (runtime-configurable):** Accept a host path from the UI via a POST request and validate it is within an allowed prefix. This avoids hardcoding paths in `docker-compose.yml`. The existing `DG_DATA_DIR` env-var pattern supports this style.

### FastAPI Endpoint Pattern

```python
@app.post("/knowledge/ingest/folder")
def ingest_folder(project: str, folder_path: str):
    base = FilePath(folder_path).resolve()
    allowed = FilePath(os.getenv("KNOWLEDGE_REPO_ROOT", "/app/repo")).resolve()
    if not str(base).startswith(str(allowed)):
        raise HTTPException(status_code=403, detail="Path outside allowed root")
    files = []
    for p in base.rglob("*.md"):
        files.append({
            "path": str(p.relative_to(base)),
            "title": p.stem,
            "content": p.read_text(encoding="utf-8", errors="replace"),
        })
    # batch-upsert to Neo4j as KnowledgeNote nodes
    ...
```

**Why stdlib pathlib only:** `python-frontmatter` is optional. If `.md` files don't use YAML frontmatter, `p.stem` as title + full text as content is sufficient. Add `python-frontmatter` only when frontmatter parsing is required.

---

## Inline Text Editor with Diff Highlighting

### Approach: Server-computed diff, React renders HTML

**Do NOT use a client-side diff library loaded from CDN.** The no-JSX-build constraint makes importing large diff libraries awkward and fragile. Instead:

1. **Server side:** `difflib.unified_diff` or `difflib.ndiff` generates change markers.
2. **Server serializes to HTML fragment:** changed lines/words wrapped in `<span style="color:#e53e3e;text-decoration:line-through">` (removed) and `<span style="color:#e53e3e;font-weight:600">` (added).
3. **Client renders via `dangerouslySetInnerHTML`** inside a `<pre>` or scrollable `<div>`:

```javascript
React.createElement('div', {
  className: 'diff-viewer',
  dangerouslySetInnerHTML: { __html: diffHtml }
})
```

4. **Confirmed editable text:** A separate `<textarea>` holds the LLM-proposed full text. User edits the textarea; diff panel updates live via a debounced POST to `/knowledge/nodes/{id}/preview-edit`.

**Why not `contenteditable`:** Cursor position management under DOM mutation is brittle in vanilla React. `<textarea>` + adjacent read-only diff panel is simpler, more accessible, and follows the existing UI pattern (single-file React, no complex state).

### Server-side diff endpoint

```python
import difflib

@app.post("/knowledge/nodes/{node_id}/preview-edit")
def preview_edit(node_id: str, body: PreviewEditPayload):
    original_lines = body.original.splitlines(keepends=True)
    proposed_lines = body.proposed.splitlines(keepends=True)
    diff = list(difflib.ndiff(original_lines, proposed_lines))
    diff_html = _diff_to_html(diff)
    return {"diffHtml": diff_html, "proposed": body.proposed}
```

`difflib` is Python stdlib — no pip install required.

---

## Session Tracking Storage

### Store in Neo4j (same database, new label)

```cypher
MERGE (s:KnowledgeSession {Session_Id: $sessionId, project: $project})
SET
  s.graph     = 'KnowledgeGraph',
  s.mode      = $mode,       -- 'insert' | 'update' | 'query'
  s.prompt    = $prompt,
  s.result    = $result,     -- NL answer or node IDs affected
  s.createdAt = $createdAt
```

**Why Neo4j, not a flat file or in-memory dict:** Consistent with how the existing service stores `ValidationRun` history. Query/filter by project, mode, and date via Cypher. No new service needed.

**Do NOT add a range index on `createdAt` initially.** The session volume at this stage is low (dozens per day per project). Add it when listing queries exceed 50ms.

---

## n8n Workflow Additions

Three new workflows (following the existing `rules-to-metagraph.json` / `graph-query-mcp.json` pattern):

| Workflow | Webhook Path | Purpose |
|----------|-------------|---------|
| `knowledge-ingest.json` | `/n8n/webhook/dg/knowledge-ingest` | NL prompt → Ollama → structured note fields → data-service `/knowledge/nodes` |
| `knowledge-update.json` | `/n8n/webhook/dg/knowledge-update` | Node IDs + edit prompt → Ollama → proposed content → data-service `/knowledge/nodes/{id}/preview-edit` |
| `knowledge-query.json` | `/n8n/webhook/dg/knowledge-query` | NL question → full-text search → Ollama context assembly → NL answer |

**Pattern to follow exactly:** HTTP Webhook node → Function node (build prompt with schema) → HTTP Request to Ollama → Function node (parse LLM JSON) → HTTP Request to data-service. This mirrors the existing 13-node and 15-node workflows.

**No LangChain, no AI Agent node.** The existing project uses plain HTTP nodes for Ollama communication. Introducing LangChain nodes would add a dependency footprint and break the "no external services" constraint.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Neo4j full-text index | Elasticsearch / OpenSearch | New Docker service; violates "no new external services" constraint |
| Neo4j full-text index | Vector embeddings + Ollama embedding model | RAG explicitly out of scope; no embedding model served currently |
| `difflib` (stdlib) | `diff-match-patch` (pip) | Added dependency for same capability; stdlib sufficient for line-level diff |
| `pathlib.rglob` (stdlib) | `watchdog` (pip) | File watching not needed; on-demand ingest is sufficient |
| `python-frontmatter` (pip, optional) | Manual regex frontmatter parse | Library is safer for edge cases; keep as optional — skip if not needed |
| `<textarea>` + server diff | `contenteditable` + client diff | Cursor management under DOM mutation is brittle without JSX state management |
| Session stored in Neo4j | In-memory dict (like EXECUTION_RESULTS) | Does not survive restarts; needs to be browsable history |
| Session stored in Neo4j | SQLite file | Additional driver dependency; Neo4j already covers this use case |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Vector search / RAG pipeline | Explicitly out of scope; no embedding model available | Neo4j full-text (Lucene) with Ollama context assembly |
| CodeMirror / Monaco editor | Requires npm build step — violates no-JSX constraint | `<textarea>` + server-rendered diff HTML via `dangerouslySetInnerHTML` |
| `react-diff-viewer` npm package | Requires JSX/build pipeline | `difflib` on server + `dangerouslySetInnerHTML` on client |
| LangChain n8n AI Agent node | Adds LangChain dependency; inconsistent with existing HTTP-node pattern | Plain HTTP Request nodes to Ollama |
| New Docker service for search | Violates "no new external services" constraint | Built-in Neo4j full-text index |
| APOC full-text procedures | APOC plugin not confirmed installed; built-in Neo4j 5 procedures preferred | `db.index.fulltext.queryNodes()` (built-in since Neo4j 3.5, stable in 5.x) |

---

## Version Compatibility

| Component | Version | Compatibility Notes |
|-----------|---------|---------------------|
| Neo4j 5 full-text index | `neo4j:5` (docker image) | `CREATE FULLTEXT INDEX IF NOT EXISTS` syntax available since Neo4j 4.1; stable in all Neo4j 5.x versions |
| `db.index.fulltext.queryNodes()` | Neo4j 5 | Built-in procedure, no plugin required — confirmed in current docs |
| `difflib` | Python stdlib (3.x) | Ships with Python 3.11 already in data-service container |
| `python-frontmatter` | `>=3.0.0` | No known conflicts with existing `fastapi`, `neo4j`, `specklepy` stack |
| FastAPI `pathlib` | Python stdlib | Already imported in `app.py` as `from pathlib import Path as FilePath` |

---

## Installation

```bash
# data-service: only if frontmatter parsing is required
pip install python-frontmatter

# No other new pip packages required
# No npm packages required (no build step)
# No new Docker services required
```

---

## Sources

- [Neo4j Full-Text Indexes — Cypher Manual (current)](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/) — index creation syntax, query procedures, OPTIONS config; HIGH confidence
- [Neo4j Full-Text Search — Knowledge Base](https://neo4j.com/developer/kb/fulltext-search-in-neo4j/) — Lucene query syntax, fuzzy, wildcard, scoring; MEDIUM confidence
- [FastAPI Official Docs — Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — file serving patterns; HIGH confidence
- [Python pathlib docs](https://docs.python.org/3/library/pathlib.html) — `rglob`, `read_text`; HIGH confidence
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) — `ndiff`, line-level diff; HIGH confidence (stdlib)
- WebSearch: n8n workflow patterns for LLM+graph — MEDIUM confidence (existing project workflows as primary reference)

---
*Stack research for: Design Grammar System v1.1 Project Knowledge Graph*
*Researched: 2026-04-05*
