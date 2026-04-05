# Architecture Research

**Domain:** Project Knowledge Graph integration into existing Design Grammar System
**Researched:** 2026-04-05
**Confidence:** HIGH (based on direct codebase inspection)

## Standard Architecture

### System Overview — Current State (v1.0)

```
Browser (:8080)
  └── Nginx (design-grammars container)
        ├── /                     → graph-viewer/index.html (React 18 SPA, no JSX)
        ├── /model-viewer/        → model-viewer/index.html (Vite+React)
        ├── /neo4j/*              → neo4j:7474  (direct Cypher over HTTP)
        ├── /data-service/*       → data-service:8000  (FastAPI)
        └── /n8n/webhook/*        → n8n:5678   (webhook workflows)

data-service (FastAPI)
  ├── POST /mcp                   MCP bridge (neo4j_schema, neo4j_query)
  ├── POST /execution-result      n8n callback store (in-memory dict)
  ├── GET  /execution-result/*    Async polling by UI
  ├── GET/PUT /settings/speckle   Persisted JSON file on volume
  ├── GET/PUT /integration/...    Neo4j IntegrationConfig nodes
  ├── POST /validation/publish    Speckle publish + ValidationRun nodes
  ├── GET  /validation/runs/*     List ValidationRun nodes
  └── DELETE /validation/run/*    Delete run + Speckle version

n8n workflows
  ├── /webhook/dg/rules-ingest    NL → Ollama → SWRL Cypher → Neo4j
  └── /webhook/dg/graph-query     NL → Ollama → Cypher → answer

Neo4j (single DB, property-scoped)
  ├── graph:"OntoGraph"           Class, DatatypeProperty, ObjectProperty
  ├── graph:"Metagraph"           Rule, Atom, Var, Literal, Builtin
  └── graph:"ValidationGraph"    ValidationRun, ValidationEntity, IntegrationConfig
```

### System Overview — Target State (v1.1, Knowledge Graph added)

```
Browser (:8080)
  └── Nginx (design-grammars container)
        ├── /                     → index.html  (adds KnowledgeGraph section)
        ├── /model-viewer/        → unchanged
        ├── /neo4j/*              → neo4j:7474  (unchanged)
        ├── /data-service/*       → data-service:8000  (NEW: /knowledge/* endpoints)
        └── /n8n/webhook/*        → n8n:5678  (NEW: /dg/knowledge-ingest, /dg/knowledge-query)

data-service (FastAPI) — MODIFIED
  ├── [all existing endpoints unchanged]
  ├── POST /knowledge/ingest/prompt   NL prompt → call n8n → KnowledgeNote nodes
  ├── POST /knowledge/ingest/folder   Read local FS path → parse files → KnowledgeNote nodes
  ├── GET  /knowledge/notes/{project} List KnowledgeNote nodes + tags
  ├── GET  /knowledge/note/{id}       Get single note content
  ├── PUT  /knowledge/note/{id}       Update note content (confirmed edits)
  ├── DELETE /knowledge/note/{id}     Delete note + tag relationships
  ├── POST /knowledge/update/match    NL prompt → LLM → candidate nodes list
  ├── POST /knowledge/update/propose  Selected node IDs → LLM → diff-marked content
  ├── POST /knowledge/update/confirm  Confirmed diff → write to Neo4j
  ├── POST /knowledge/query           NL question → n8n → NL answer
  ├── GET  /knowledge/sessions/{project}  List KnowledgeSession nodes
  └── POST /knowledge/session         Store session entry (prompt, result, mode, date)

n8n workflows — NEW (2 additional workflows)
  ├── /webhook/dg/knowledge-ingest    NL → Ollama → KnowledgeNote Cypher → Neo4j
  └── /webhook/dg/knowledge-query     NL → Ollama → full-text search → NL answer

Neo4j (single DB, property-scoped) — NEW graph label
  ├── graph:"OntoGraph"           unchanged
  ├── graph:"Metagraph"           unchanged
  ├── graph:"ValidationGraph"     unchanged
  └── graph:"KnowledgeGraph"      KnowledgeNote, KnowledgeTag, KnowledgeSession
                                  TAGGED_WITH (Note→Tag), REFERENCES (Note→Note)
                                  PART_OF_SESSION (Session→Note)
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `graph-viewer/index.html` | Main SPA UI — adds Knowledge section to MODE_OPTIONS, renders Insert/Update/Query/Session sub-modes | MODIFIED |
| `graph-viewer/config.template.js` | NeoVis config — add KnowledgeGraph visualization config | MODIFIED |
| `graph-viewer/nginx.conf` | Reverse proxy — no changes needed (existing /data-service/ route covers new endpoints) | UNCHANGED |
| `data-service/app.py` | FastAPI — add /knowledge/* endpoint group, file-system reader, LLM dispatch via n8n | MODIFIED |
| `n8n/knowledge-ingest.json` | n8n workflow — NL → KnowledgeNote Cypher | NEW |
| `n8n/knowledge-query.json` | n8n workflow — NL + full-text search → answer | NEW |
| `Neo4j KnowledgeGraph` | Stores KnowledgeNote, KnowledgeTag, KnowledgeSession nodes | NEW (schema extension) |
| `docker-compose.yml` | Mount local repo folder into data-service container for folder ingest | MODIFIED |

## Recommended Project Structure — Changes Only

```
design-grammar-system/
├── graph-viewer/
│   └── index.html               MODIFIED — add Knowledge section, session history panel
│
├── data-service/
│   ├── app.py                   MODIFIED — add /knowledge/* routes
│   └── knowledge.py             NEW — knowledge-specific helpers (note parsing, diff logic, folder reader)
│
└── n8n/
    └── workflows/
        ├── rules-to-metagraph.json      unchanged
        ├── graph-query-mcp.json         unchanged
        ├── knowledge-ingest.json        NEW
        └── knowledge-query.json         NEW
```

No new Docker services. No new npm packages (knowledge UI uses same React.createElement pattern as existing SPA). No new external tools.

## Architectural Patterns

### Pattern 1: Separate Graph Label, Same Isolation Pattern

**What:** Knowledge nodes live in `graph:"KnowledgeGraph"` and carry the same `project` property used throughout the existing system. This mirrors how `ValidationGraph`, `Metagraph`, and `OntoGraph` already coexist in the single Neo4j database.

**When to use:** Every Cypher query for knowledge nodes filters on `{graph:"KnowledgeGraph", project:$project}`.

**Trade-offs:** Consistent with existing isolation pattern. No migration needed on existing data. Adding a full-text index on `KnowledgeNote.content` is the only schema change required.

**Example (Cypher MERGE pattern for a note):**
```cypher
MERGE (n:KnowledgeNote {graph:"KnowledgeGraph", project:$project, noteId:$noteId})
SET n.title = $title,
    n.content = $content,
    n.source = $source,
    n.createdAt = $createdAt,
    n.updatedAt = $updatedAt
```

### Pattern 2: Three-Step Update Flow (Match → Propose → Confirm)

**What:** Knowledge update is a three-call interaction, not a single LLM write. This avoids silent overwrites and exposes LLM suggestions to user review before committing.

Step 1 — Match: UI sends NL prompt to `POST /knowledge/update/match`. data-service calls Ollama to extract entity names, then searches KnowledgeNote nodes using Neo4j full-text index. Returns candidate list with node IDs and titles.

Step 2 — Propose: UI sends selected node IDs to `POST /knowledge/update/propose`. data-service fetches full note content, sends to Ollama with "propose edits, mark changes with [DEL]...[/DEL] and [INS]...[/INS] markers". Returns diff-annotated content per note.

Step 3 — Confirm: UI renders diff in inline editor (contenteditable with red/green spans from diff markers). On confirm, UI calls `POST /knowledge/update/confirm` with cleaned content. data-service writes to Neo4j and appends a KnowledgeSession entry.

**When to use:** Any user-initiated update to existing knowledge nodes.

**Trade-offs:** More round-trips than single-shot LLM write. Essential for trust — LLM errors are visible and correctable before persistence. Consistent with existing async polling pattern (n8n execution-result polling).

### Pattern 3: Folder Ingest as data-service File Reader

**What:** The "load from local repository folder" feature cannot run in the browser (no FS access). The data-service container is the correct place: it already has a writable data volume. A new env var `DG_REPO_DIR` mounts a read-only bind-mount of the local repo directory into the container. data-service reads `.md` files, extracts frontmatter and content, converts to KnowledgeNote MERGE queries.

**When to use:** User selects "Insert from folder" mode, provides a relative path within the mounted directory.

**Trade-offs:** Requires one new docker-compose bind-mount (`./:/repo:ro`). The path is restricted to within the mount (validated server-side). This is a one-time container config change, not a service addition.

**Example (docker-compose addition):**
```yaml
data-service:
  volumes:
    - ./data-service/data:/app/data
    - .:/repo:ro                      # NEW — read-only repo mount for folder ingest
  environment:
    DG_REPO_DIR: /repo                # NEW — path available to data-service
```

### Pattern 4: Neo4j Full-Text Index for Knowledge Search

**What:** Knowledge query and update-match both need content-based search. Neo4j's built-in full-text index (`CREATE FULLTEXT INDEX knowledgeNoteContent FOR (n:KnowledgeNote) ON EACH [n.title, n.content]`) covers both fields with single-call Cypher. No external search engine needed.

**When to use:** Any time the n8n knowledge-query workflow needs to find relevant notes before handing context to Ollama for NL answer generation.

**Trade-offs:** Full-text index creation is a one-time Cypher command on startup (data-service startup hook or first-use creation). Appropriate for note-scale data (hundreds to low thousands of notes per project). Not a replacement for semantic/vector search at large scale, but the project decision is explicitly no-RAG.

**Startup index creation (data-service startup):**
```python
# In data-service startup (lifespan or startup event)
driver.execute_query(
    "CREATE FULLTEXT INDEX knowledgeNoteContent IF NOT EXISTS "
    "FOR (n:KnowledgeNote) ON EACH [n.title, n.content]"
)
```

### Pattern 5: Session Tracking as KnowledgeSession Nodes

**What:** Every knowledge interaction (insert, update, query) writes a `KnowledgeSession` node: `{graph:"KnowledgeGraph", project, sessionId, mode, prompt, result, createdAt}`. The UI Session History panel reads `GET /knowledge/sessions/{project}` and displays them in reverse-chronological order.

**When to use:** Automatically on every knowledge operation completion — no separate user action needed.

**Trade-offs:** Storage is bounded by project activity. No localStorage quota risk (unlike run screenshots). History is persistent across browser sessions. Querying sessions is a simple `MATCH (s:KnowledgeSession {graph:..., project:...}) RETURN s ORDER BY s.createdAt DESC` — no complexity.

Replaces any localStorage-based session tracking (localStorage is already stressed by run screenshots per the known gotchas).

## Data Flow

### Insert Knowledge (NL Prompt path)

```
User types prompt in "Insert Knowledge" panel
    ↓
UI: POST /data-service/knowledge/ingest/prompt  {project, prompt}
    ↓
data-service: generate executionId, POST /n8n/webhook/dg/knowledge-ingest
    ↓
n8n knowledge-ingest workflow:
  1. Extract note structure via Ollama (title, tags, content from prompt)
  2. Generate MERGE Cypher for KnowledgeNote + KnowledgeTag nodes
  3. POST to Neo4j HTTP transaction
  4. POST result back to data-service /execution-result
    ↓
UI polls GET /data-service/execution-result/{executionId}  (existing async pattern)
    ↓
On success: data-service writes KnowledgeSession node
UI refreshes note list
```

### Insert Knowledge (Folder path)

```
User selects folder path in "Insert from Folder" panel
    ↓
UI: POST /data-service/knowledge/ingest/folder  {project, path}
    ↓
data-service:
  1. Validate path is within DG_REPO_DIR
  2. Walk directory, collect .md files
  3. Parse frontmatter (title, tags) + body content per file
  4. MERGE KnowledgeNote nodes directly (no n8n needed — no LLM required)
  5. Write KnowledgeSession node
    ↓
Returns {inserted: N, skipped: M}
UI shows result inline
```

### Query Knowledge

```
User types question in "Query Knowledge" panel
    ↓
UI: POST /data-service/knowledge/query  {project, question}
    ↓
data-service: POST /n8n/webhook/dg/knowledge-query
    ↓
n8n knowledge-query workflow:
  1. Ollama extracts search terms from question
  2. Cypher full-text search: CALL db.index.fulltext.queryNodes(...)
  3. Top N matching notes passed as context to Ollama
  4. Ollama generates NL answer
  5. POST result + cypher used to data-service /execution-result
    ↓
UI polls, receives {answer, cypher}
data-service writes KnowledgeSession node
UI displays answer in Response field, cypher in Cypher panel
```

### Update Knowledge (3-step)

```
Step 1 — Match:
  User types "what to update" prompt
  UI: POST /data-service/knowledge/update/match {project, prompt}
  data-service: Ollama extracts entity names → full-text search → return candidate list
  UI renders selectable node list

Step 2 — Propose:
  User selects nodes to update
  UI: POST /data-service/knowledge/update/propose {project, nodeIds, prompt}
  data-service: fetch note contents → Ollama proposes diff-annotated edits
  UI renders inline diff editor (contenteditable, red [DEL], green [INS] spans)

Step 3 — Confirm:
  User reviews, accepts/rejects changes inline, clicks Confirm
  UI: POST /data-service/knowledge/update/confirm {project, nodeId, content}
  data-service: SET n.content = $content, n.updatedAt = now()
               write KnowledgeSession node
  UI: refresh note list
```

## Integration Points

### New vs Existing — Explicit Boundary Table

| Touchpoint | Status | What Changes |
|------------|--------|--------------|
| `graph-viewer/index.html` | MODIFIED | Add "Project Knowledge" section to MODE_OPTIONS, new sub-mode panels (Insert, Update, Query, Sessions), NeoVis config toggle for KnowledgeGraph |
| `graph-viewer/config.template.js` | MODIFIED | Add NeoVis visualization config for KnowledgeNote and KnowledgeTag node styles |
| `graph-viewer/nginx.conf` | UNCHANGED | Existing `/data-service/` proxy covers all new endpoints |
| `data-service/app.py` | MODIFIED | Add `/knowledge/*` route group (~8 new endpoints) |
| `data-service/knowledge.py` | NEW | File parsing, diff generation, note helpers |
| `data-service/requirements.txt` | MAYBE MODIFIED | Only if markdown frontmatter parsing needs a library (python-frontmatter); alternatively handled with bespoke regex consistent with existing patterns |
| `n8n/workflows/knowledge-ingest.json` | NEW | ~10-node workflow: Webhook → Set → HTTP(Ollama) → Function(parse) → HTTP(Neo4j) → HTTP(data-service callback) |
| `n8n/workflows/knowledge-query.json` | NEW | ~12-node workflow: Webhook → Set → HTTP(Ollama extract terms) → HTTP(Neo4j full-text) → HTTP(Ollama answer) → HTTP(callback) |
| `docker-compose.yml` | MODIFIED | Add read-only repo bind-mount + `DG_REPO_DIR` env var to data-service |
| `Neo4j schema` | MODIFIED | New node labels (KnowledgeNote, KnowledgeTag, KnowledgeSession), new FULLTEXT index, new relationships (TAGGED_WITH, REFERENCES, PART_OF_SESSION) |
| Nginx reverse proxy routes | UNCHANGED | No new routes needed |
| Speckle stack (7 containers) | UNCHANGED | Knowledge graph has no Speckle integration |
| Grasshopper plugin (C#) | UNCHANGED | Knowledge graph is informational only, no validation path |
| Ollama service | UNCHANGED | Shared inference capacity; knowledge queries use same endpoint |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI → data-service (knowledge) | REST over `/data-service/knowledge/*` via Nginx proxy | Same CORS/proxy setup as existing endpoints |
| data-service → n8n (knowledge workflows) | POST to n8n webhook + async polling via /execution-result | Same pattern as existing rules-ingest workflow |
| n8n → Ollama (knowledge) | HTTP POST to `http://ollama:11434/api/generate` | Same internal Docker network, same model |
| n8n → Neo4j (knowledge Cypher) | HTTP POST to `http://neo4j:7474/db/neo4j/tx/commit` | Same as existing rules-ingest workflow |
| data-service → Neo4j (knowledge CRUD) | neo4j Python driver (existing `driver` instance) | All knowledge queries via same connection pool |
| data-service → file system (folder ingest) | Python `pathlib.Path` reads from `/repo` mount | Path traversal validation required |

## Build Order (Phase Dependencies)

The suggested implementation sequence, based on hard dependencies:

**Phase 1 — Neo4j Schema Foundation**
Create KnowledgeNote, KnowledgeTag, KnowledgeSession node shapes and the full-text index. Write startup index-creation code in data-service. This unblocks all subsequent phases.

**Phase 2 — data-service Knowledge Endpoints (CRUD + Folder Ingest)**
Add `/knowledge/ingest/folder`, `/knowledge/notes/*`, `/knowledge/note/*` (GET/PUT/DELETE), `/knowledge/session` endpoints. Folder ingest can be fully tested without n8n or LLM. Session tracking write/read can be verified here.

**Phase 3 — n8n Knowledge Workflows**
Build `knowledge-ingest` and `knowledge-query` n8n workflows against the Neo4j schema from Phase 1. Wire data-service `/knowledge/ingest/prompt` and `/knowledge/query` endpoints to call these webhooks and poll results via the existing execution-result pattern.

**Phase 4 — Update Flow (Match → Propose → Confirm)**
Add the three `/knowledge/update/*` endpoints. Requires: Phase 1 (nodes to find), Phase 3 (Ollama access via data-service calls). The diff-marking logic lives entirely in data-service (Python string manipulation + Ollama call), not in n8n.

**Phase 5 — UI: Mode Restructuring + Insert/Query Panels**
Restructure `MODE_OPTIONS` into two sections ("Validation" grouping existing 3 modes, "Project Knowledge" grouping 4 new modes). Add Insert and Query panels (simpler — single-step flows). Requires Phase 3 endpoints to be live.

**Phase 6 — UI: Update Panel + Inline Diff Editor**
Add the three-step Update UI with contenteditable diff rendering. Requires Phase 4. The diff rendering (red span for deletions, green for insertions) is the most complex UI work in this milestone.

**Phase 7 — UI: Session History Panel + NeoVis Knowledge Graph View**
Session history list panel (read from Phase 2 endpoint). Optional NeoVis toggle to show KnowledgeGraph nodes. Lowest dependency — can be done last.

## Anti-Patterns

### Anti-Pattern 1: Mixing Knowledge and SWRL Nodes in Same Graph Label

**What people do:** Reuse existing `graph:"Metagraph"` or add knowledge properties directly to Rule nodes.

**Why it's wrong:** Destroys isolation. NeoVis queries for Metagraph will return knowledge noise. Any future migration or visualization of knowledge graph becomes entangled with SWRL semantics.

**Do this instead:** Strict `graph:"KnowledgeGraph"` on every knowledge node. Never cross-label.

### Anti-Pattern 2: Storing Large Note Content in n8n Workflow Memory

**What people do:** Pass full note content through n8n workflow node parameters for the update flow.

**Why it's wrong:** n8n workflow node parameters have size limits and are stored in n8n's internal SQLite/Postgres. Note content belongs in Neo4j where it can be queried.

**Do this instead:** n8n workflows operate on note IDs and short summaries. Full content fetch/write goes through data-service ↔ Neo4j directly.

### Anti-Pattern 3: New Docker Service for Knowledge Features

**What people do:** Add a dedicated "knowledge-service" container for the new endpoints.

**Why it's wrong:** Violates the project constraint "no new external services." Adds operational complexity (new Dockerfile, compose service, internal networking). The existing data-service FastAPI app already has the Neo4j driver, the execution-result store, and the Speckle settings pattern — knowledge endpoints follow the same shape.

**Do this instead:** Add knowledge routes as a new module imported into the existing `app.py`. Keep `knowledge.py` for helpers to avoid bloating `app.py`.

### Anti-Pattern 4: JSX or Vite Build for Knowledge UI

**What people do:** Build the knowledge UI as a separate Vite+React app (like model-viewer) because it has complex state (diff editor, multi-step update flow).

**Why it's wrong:** Inconsistent with the main SPA pattern. Introduces a second build step. The diff editor complexity is manageable with `React.createElement` + `contenteditable` — no component library needed.

**Do this instead:** Add knowledge panels as new branches in the existing `GraphViewerPage` component using the same `React.createElement` calls and CSS variables already established.

### Anti-Pattern 5: localStorage for Session History

**What people do:** Store session history in localStorage to avoid database writes.

**Why it's wrong:** localStorage is already stressed by run screenshots. Sessions accumulate indefinitely. History disappears on browser data clear, making it useless as an audit trail.

**Do this instead:** `KnowledgeSession` nodes in Neo4j. Cheap writes, persistent, queryable. The existing `ValidationRun` pattern is the direct precedent.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single project, hundreds of notes | Current design is correct. Full-text index handles this trivially. |
| Multiple projects, thousands of notes | Current design holds. Neo4j full-text index scales to millions of nodes. Property-based project isolation continues to work. |
| Very large documents (100KB+ markdown files) | Neo4j has a 4GB property value limit; not practically reachable. Only concern is Ollama context window: llama3.1 has 128K tokens. Truncate content before sending to Ollama if source files exceed ~50KB. |
| High concurrent knowledge queries | Ollama is single-threaded per request. Contention with rule-ingest workflows is a real risk. Mitigation: document that LLM-dependent knowledge features queue behind SWRL workflows. Not a blocker for current single-user/small-team usage. |

## Sources

- Direct codebase inspection: `graph-viewer/index.html`, `data-service/app.py`, `docker-compose.yml`, `graph-viewer/nginx.conf`, `training/dataset_schema.json`, `n8n/workflows/rules-to-metagraph.json`
- Existing patterns: ValidationRun node storage, execution-result async polling, n8n webhook + Ollama HTTP call chain, React.createElement SPA mode switching (MODE_OPTIONS pattern)
- Project constraints: `.planning/PROJECT.md` — no new services, no JSX build, single Neo4j DB, same Ollama instance, no RAG
- Neo4j full-text index: HIGH confidence, standard Neo4j 5 feature (`db.index.fulltext.queryNodes`)

---
*Architecture research for: Design Grammar System v1.1 Project Knowledge Graph*
*Researched: 2026-04-05*
