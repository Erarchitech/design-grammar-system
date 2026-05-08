# Phase 4: Update Flow Endpoints - Research

**Researched:** 2026-04-06
**Domain:** FastAPI REST endpoints + Python difflib + n8n workflow + Neo4j full-text search
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** POST `/knowledge/update/match` uses direct Neo4j full-text search (`knowledge_note_search` index) — no LLM involved in matching
**D-02:** Returns top 10 candidate notes ranked by full-text relevance score
**D-03:** Match endpoint lives entirely in data-service as a REST endpoint (no n8n)
**D-04:** LLM (Ollama) receives current note content + update prompt and returns the full updated text — LLM does not annotate changes itself
**D-05:** Python `difflib` computes word-level diff server-side comparing original vs LLM-proposed text
**D-06:** Diff output is HTML spans with additions and deletions marked (consistent with UPDK-02 requirement)
**D-07:** POST `/knowledge/update/propose` accepts an array of noteIds — returns diff for each selected note in one HTTP call
**D-08:** POST `/knowledge/update/confirm` uses optimistic locking via `updatedAt` timestamp — client sends the `updatedAt` from the propose step; server rejects with 409 Conflict if note was modified since
**D-09:** Client sends the user's final edited text (from the inline textarea editor), not the raw LLM proposal — users can modify before confirming (per UPDK-04)
**D-10:** Each confirmed update creates a KnowledgeSession node recording the prompt and affected node IDs (per UPDK-06)
**D-11:** Match and Confirm are pure data-service REST endpoints — no n8n involvement (they don't need LLM)
**D-12:** Propose routes through n8n: UI -> data-service `/knowledge/update/propose` -> data-service fetches current note content from Neo4j -> sends content + prompt to n8n webhook -> n8n calls Ollama -> posts result to execution-result -> data-service polls/receives result -> data-service runs difflib -> returns HTML diff to client
**D-13:** New n8n workflow: `knowledge-update` with webhook path `/webhook/dg/knowledge-update` — follows Phase 3 naming convention

### Claude's Discretion

- Exact difflib function choice and word-level tokenization strategy
- n8n workflow internal node layout and prompt construction details
- Error handling for LLM returning malformed/empty text
- HTTP response shapes (field names, nesting) for all three endpoints
- How to handle Propose when LLM returns text identical to original (no-op diff)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UPDK-01 | User types an update prompt; LLM identifies matching KnowledgeNote nodes via full-text search and returns candidate list | D-01, D-02, D-03: Neo4j `knowledge_note_search` full-text index + `CALL db.index.fulltext.queryNodes` Cypher |
| UPDK-02 | Matching nodes are isolated in the graph view; user selects one or several nodes | D-07: propose accepts array of noteIds, returns per-note diff; UI phase (Phase 6) consumes response |
| UPDK-03 | User clicks Edit; LLM proposes edits to selected notes with changes highlighted in red | D-04, D-05, D-06: Ollama returns full updated text; Python difflib produces word-level HTML span diff |
| UPDK-04 | User reviews proposed changes in an inline text editor (textarea + diff panel with red-highlighted changes) | D-09: confirm endpoint receives user-edited final text, not raw LLM proposal — response shape must include both diff HTML and raw proposed text |
| UPDK-05 | User clicks Confirm to save changes to Neo4j; sidebar notification lists affected nodes | D-08, D-11: optimistic locking via updatedAt; confirm writes via existing `write_query()` helper |
| UPDK-06 | Each update operation creates a KnowledgeSession node recording the interaction | D-10: KnowledgeSession MERGE written as final step in confirm endpoint |

</phase_requirements>

---

## Summary

Phase 4 adds three REST endpoints to the existing FastAPI data-service: `POST /knowledge/update/match`, `POST /knowledge/update/propose`, and `POST /knowledge/update/confirm`. These implement a three-step update flow that prevents silent LLM overwrites.

The match endpoint is purely a Neo4j full-text search using the `knowledge_note_search` index already created in Phase 2. No new infrastructure is needed. The confirm endpoint is also self-contained in data-service — it performs an optimistic-lock check, writes updated content, and records a KnowledgeSession node.

The propose endpoint is the most complex: data-service fetches note content from Neo4j, calls the new `knowledge-update` n8n webhook synchronously (fire-and-return-executionId), then polls `EXECUTION_RESULTS` until the workflow posts back the LLM-proposed text, computes a word-level HTML diff with Python difflib, and returns the diff to the caller. This matches the polling pattern already established for `knowledge-ingest` and `knowledge-query`.

**Primary recommendation:** Build match and confirm directly in data-service (no n8n). For propose, create a minimal n8n workflow (7-8 nodes) that mirrors `knowledge-ingest.json` but outputs the LLM-proposed text instead of writing to Neo4j — diff computation stays in Python.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `difflib` | stdlib (3.x) | Word-level diff between original and proposed text | Python stdlib — no install; `SequenceMatcher` proven for this use case [VERIFIED: local Python] |
| `fastapi` | pinned in requirements.txt | REST endpoint hosting | Already in use [VERIFIED: data-service/requirements.txt] |
| `neo4j` | pinned in requirements.txt | Neo4j driver for full-text search + write | Already in use [VERIFIED: data-service/requirements.txt] |
| `urllib.request` | stdlib | Outbound HTTP call from data-service to n8n webhook | stdlib — no new dependency; consistent with existing use of `urllib.parse` [VERIFIED: data-service/app.py line 11] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic.BaseModel` | bundled with fastapi | Request/response payload validation | All three endpoint payloads [VERIFIED: data-service/app.py lines 46-120] |
| `datetime` / `timezone` | stdlib | `updatedAt` timestamp generation and comparison | Confirm endpoint optimistic lock [VERIFIED: data-service/app.py line 8] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `urllib.request` | `httpx` | httpx is cleaner async but requires pip install; urllib.request is sufficient for one synchronous webhook call |
| `difflib.SequenceMatcher` | `difflib.ndiff` | `ndiff` is line-oriented; `SequenceMatcher` gives finer control for word-level tokenization and HTML output |

**Installation:** No new packages — all dependencies already present.

---

## Architecture Patterns

### Endpoint Structure in data-service/app.py

All three endpoints follow the pattern established by existing knowledge CRUD endpoints: Pydantic request model, `read_single()` / `read_many()` / `write_query()` helpers, HTTPException for errors.

```
POST /knowledge/update/match    → pure data-service (no n8n)
POST /knowledge/update/propose  → data-service calls n8n, polls, runs difflib
POST /knowledge/update/confirm  → pure data-service (no n8n)
```

### New n8n Workflow Structure

`n8n/workflows/knowledge-update.json` — mirrors `knowledge-ingest.json` (Phase 3 [VERIFIED: n8n/workflows/knowledge-ingest.json]):

```
Webhook (dg/knowledge-update)
  → Set Input Defaults
  → [Fork: Format Ack → Respond Ack]  (immediate 200 response with executionId)
  → Build Update Prompt
  → Ollama Generate  (stream:false, format not JSON — plain text response)
  → Parse LLM Text   (extract raw updated text from response field)
  → Post Execution Result (workflow: "knowledge-update", status: "completed", payload: {noteId, proposedText})
```

The workflow does NOT write to Neo4j — that is data-service's job. The LLM call requests plain-text (not JSON format) because it returns edited prose, not structured data.

### Pattern 1: Match Endpoint — Full-Text Search

**What:** Direct `CALL db.index.fulltext.queryNodes` against the `knowledge_note_search` index.
**When to use:** All calls to `/knowledge/update/match`.

```python
# Source: Neo4j 5 full-text search — index created in data-service/app.py line 595-600 [VERIFIED]
cypher = (
    "CALL db.index.fulltext.queryNodes('knowledge_note_search', $query) "
    "YIELD node, score "
    "WHERE node.project = $project AND node.graph = $graph "
    "RETURN node.noteId AS noteId, node.title AS title, score "
    "ORDER BY score DESC LIMIT 10"
)
rows = read_many(cypher, {"query": payload.prompt, "project": payload.project, "graph": KNOWLEDGE_GRAPH})
```

Note: `read_many()` uses `session.run()` which supports `CALL ... YIELD` procedures. [VERIFIED: data-service/app.py lines 167-170]

### Pattern 2: Propose Endpoint — Call n8n Then Poll

**What:** data-service calls n8n webhook, receives `executionId`, polls `EXECUTION_RESULTS` dict until workflow posts back, then runs difflib.
**When to use:** All calls to `/knowledge/update/propose`.

```python
# Source: CONTEXT.md D-12 + knowledge-ingest.json polling pattern [VERIFIED: n8n/workflows/knowledge-ingest.json]
import urllib.request, json, time, os

N8N_INTERNAL_URL = os.getenv("N8N_INTERNAL_URL", "http://n8n:5678")

def call_n8n_sync(path: str, body: dict, poll_key: str, timeout: int = 120) -> dict:
    """Fire webhook, poll EXECUTION_RESULTS until completed or timeout."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{N8N_INTERNAL_URL}/webhook/{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        ack = json.loads(resp.read())
    execution_id = ack.get("executionId")
    if not execution_id:
        raise HTTPException(status_code=502, detail="n8n did not return executionId")
    # Poll EXECUTION_RESULTS dict directly (same process)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        entry = EXECUTION_RESULTS.get(execution_id, {})
        if entry.get("status") == "completed":
            return entry.get("payload", {})
        if entry.get("status") == "failed":
            raise HTTPException(status_code=502, detail="LLM workflow failed")
        time.sleep(1.5)
    raise HTTPException(status_code=504, detail="LLM workflow timed out")
```

### Pattern 3: Word-Level Diff with difflib

**What:** Tokenize both strings on whitespace, run `SequenceMatcher`, emit HTML spans.
**When to use:** After LLM returns proposed text in propose endpoint.

```python
# Source: Python stdlib difflib — verified working on Windows [VERIFIED: local py -3 test]
import difflib

def word_diff_html(original: str, proposed: str) -> str:
    """Return HTML string with <span class='diff-del'> and <span class='diff-ins'> markers."""
    original_words = original.split()
    proposed_words = proposed.split()
    matcher = difflib.SequenceMatcher(None, original_words, proposed_words, autojunk=False)
    parts = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            parts.extend(original_words[i1:i2])
        elif op == "replace":
            for w in original_words[i1:i2]:
                parts.append(f'<span class="diff-del">{w}</span>')
            for w in proposed_words[j1:j2]:
                parts.append(f'<span class="diff-ins">{w}</span>')
        elif op == "delete":
            for w in original_words[i1:i2]:
                parts.append(f'<span class="diff-del">{w}</span>')
        elif op == "insert":
            for w in proposed_words[j1:j2]:
                parts.append(f'<span class="diff-ins">{w}</span>')
    return " ".join(parts)
```

`autojunk=False` is important for short texts — difflib's junk heuristic can suppress changes in small notes. [VERIFIED: difflib docs, ASSUMED for autojunk impact on short notes]

**No-op diff:** If `original == proposed` (LLM returned identical text), `get_opcodes()` returns a single `('equal', ...)` tuple — `word_diff_html` returns the original text with no spans. The propose response should include a `hasChanges: bool` field so the UI can show "no changes proposed" instead of rendering a diff panel.

### Pattern 4: Confirm Endpoint — Optimistic Lock

**What:** Check `updatedAt` matches, write new content, create KnowledgeSession.
**When to use:** All calls to `/knowledge/update/confirm`.

```python
# Source: existing PUT /knowledge/note/{note_id} pattern [VERIFIED: data-service/app.py lines 1027-1056]
# Plus optimistic lock from CONTEXT.md D-08

existing = read_single(
    "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) "
    "RETURN n.noteId AS noteId, n.updatedAt AS updatedAt",
    {"noteId": note_id, "graph": KNOWLEDGE_GRAPH},
)
if existing is None:
    raise HTTPException(status_code=404, detail="Note not found")
if existing["updatedAt"] != payload.updatedAt:
    raise HTTPException(status_code=409, detail="Note was modified since propose step — reload and retry")

now = datetime.now(timezone.utc).isoformat()
write_query(
    "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) "
    "SET n.content = $content, n.updatedAt = $now",
    {"noteId": note_id, "graph": KNOWLEDGE_GRAPH, "content": payload.content, "now": now},
)
```

### Pattern 5: KnowledgeSession Write in Confirm

Follows the Phase 3 session tracking convention (D-10 [VERIFIED: knowledge-ingest.json ki-write-session node]):

```python
# Source: knowledge-ingest.json ki-write-session pattern [VERIFIED]
session_id = "ks-" + uuid.uuid4().hex[:12]
write_query(
    "MERGE (s:KnowledgeSession {sessionId: $sessionId, project: $project, graph: $graph}) "
    "SET s.mode = 'update', s.prompt = $prompt, s.result = $result, s.createdAt = $createdAt",
    {
        "sessionId": session_id,
        "project": payload.project,
        "graph": KNOWLEDGE_GRAPH,
        "prompt": payload.prompt,
        "result": json.dumps({"affectedNoteIds": affected_ids})[:2000],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    },
)
```

### Anti-Patterns to Avoid

- **Synchronous Ollama call inside FastAPI endpoint:** If data-service calls Ollama directly (bypassing n8n), the FastAPI worker blocks for the entire LLM generation time (~10-60s). D-12 routes through n8n precisely to keep the same async pattern — data-service fires n8n webhook and polls.
- **LLM-annotated diffs:** Do not ask the LLM to mark its own changes with `[DEL]` / `[INS]` markers. LLM output is inconsistent. Python difflib is deterministic and correct.
- **Writing to Neo4j inside n8n for the propose step:** The `knowledge-update` n8n workflow must NOT write to Neo4j. Its only job is calling Ollama and posting the proposed text back via `/execution-result`. The confirm endpoint does the write.
- **Using `read_many` for CALL YIELD procedures without confirming driver compatibility:** Neo4j Python driver's `session.run()` handles `CALL db.index.fulltext.queryNodes` correctly since it returns a regular result cursor. The `read_many()` helper is safe to use. [VERIFIED: data-service/app.py lines 167-170]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Word-level text diff | Custom string comparison | `difflib.SequenceMatcher` | Handles insertions, deletions, replacements in one pass; handles edge cases (empty strings, identical text) |
| Full-text search ranking | Custom Cypher CONTAINS scoring | Neo4j `knowledge_note_search` full-text index + `CALL db.index.fulltext.queryNodes YIELD score` | Built-in Lucene scoring; already indexed [VERIFIED: app.py line 595] |
| HTTP client for n8n call | Requests library install | `urllib.request` (stdlib) | No new dependency; sufficient for one synchronous fire-and-ack call |
| Optimistic lock | DB-level transactions with LOCK | `updatedAt` timestamp comparison | Simple, stateless, consistent with existing update pattern |

**Key insight:** All tools are either already in the project or in Python stdlib. Phase 4 adds zero new pip dependencies.

---

## Common Pitfalls

### Pitfall 1: `CALL ... YIELD` in read_many helper

**What goes wrong:** `read_many()` calls `session.run()` and iterates records — this works for `CALL db.index.fulltext.queryNodes` but the query must be passed to `read_many`, not `read_single`, because it can return multiple rows.
**Why it happens:** The full-text index may return 0-10 results; `read_single().single()` would silently discard all but the first.
**How to avoid:** Always use `read_many()` for the match query. [VERIFIED: data-service/app.py lines 161-170]
**Warning signs:** Match endpoint returning only one candidate when multiple exist.

### Pitfall 2: n8n workflow polling timing

**What goes wrong:** data-service polls `EXECUTION_RESULTS` dict but the workflow hasn't posted back yet (Ollama takes 10-45 seconds). If polling timeout is too short, all propose calls fail.
**Why it happens:** Ollama LLM generation is slow (llama3.1 at ~10 tokens/sec). The `knowledge-ingest` and `knowledge-query` workflows use 900000ms Ollama timeout [VERIFIED: knowledge-ingest.json line 78].
**How to avoid:** Set the data-service polling timeout to at least 120 seconds. Poll every 1.5 seconds (matching existing UI pattern [VERIFIED: graph-viewer/index.html line 1609]).
**Warning signs:** Propose endpoint returning 504 even when n8n workflow eventually succeeds.

### Pitfall 3: Multiple noteIds in one propose call — LLM context size

**What goes wrong:** If the user selects 5 long notes for simultaneous editing, the propose call concatenates all of them into one Ollama prompt, exceeding the context window.
**Why it happens:** D-07 says propose accepts an array of noteIds. REQUIREMENTS.md Out of Scope says "Knowledge node content > 100KB — Ollama context window limitation".
**How to avoid:** Process each noteId in a separate n8n webhook call (one call per note), fire them sequentially or in parallel, merge results. The workflow receives a single `{noteId, prompt, currentContent}` body — data-service loops over noteIds.
**Warning signs:** LLM returning truncated or empty text for notes after the first one.

### Pitfall 4: difflib junk heuristic on short notes

**What goes wrong:** For notes shorter than ~200 words, difflib's auto-junk detection may classify frequently-repeated words (like "the", "is") as junk and produce incorrect diffs.
**Why it happens:** `SequenceMatcher` uses an autojunk heuristic enabled by default.
**How to avoid:** Pass `autojunk=False` to `SequenceMatcher`. [ASSUMED — based on difflib docs pattern for short documents]
**Warning signs:** Common words missing from diff output even when they were changed.

### Pitfall 5: `N8N_INTERNAL_URL` not in docker-compose environment

**What goes wrong:** data-service cannot reach n8n; `urllib.request.urlopen` raises `URLError: connection refused`.
**Why it happens:** The docker-compose.yml data-service environment block has no `N8N_INTERNAL_URL` entry [VERIFIED: docker-compose.yml lines 22-32]. n8n's internal address is `http://n8n:5678` within the Docker network.
**How to avoid:** Add `N8N_INTERNAL_URL: http://n8n:5678` to the data-service environment block in docker-compose.yml. Also add `n8n` to data-service's `depends_on`.
**Warning signs:** `urllib.error.URLError` in data-service logs when propose is called.

### Pitfall 6: 409 false positive if client clock drift

**What goes wrong:** Confirm rejects with 409 even though no one else modified the note — the client sends a slightly different timestamp format.
**Why it happens:** The `updatedAt` written by Neo4j is the ISO string generated by `datetime.now(timezone.utc).isoformat()`. The client must round-trip this exact string unchanged.
**How to avoid:** The propose response must include the verbatim `updatedAt` string read from Neo4j (not re-serialized by JSON). Confirm does string equality comparison, not datetime parsing.
**Warning signs:** All confirm calls return 409 even immediately after propose.

---

## Code Examples

### Match Endpoint — Full Shape

```python
# Source: data-service/app.py CRUD pattern [VERIFIED: lines 934-1085]

class UpdateMatchRequest(BaseModel):
    prompt: str
    project: str

class UpdateMatchCandidate(BaseModel):
    noteId: str
    title: str
    score: float

@app.post("/knowledge/update/match")
def knowledge_update_match(payload: UpdateMatchRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    rows = read_many(
        "CALL db.index.fulltext.queryNodes('knowledge_note_search', $query) "
        "YIELD node, score "
        "WHERE node.project = $project AND node.graph = $graph "
        "RETURN node.noteId AS noteId, node.title AS title, score "
        "ORDER BY score DESC LIMIT 10",
        {"query": payload.prompt, "project": payload.project, "graph": KNOWLEDGE_GRAPH},
    )
    return {"candidates": rows}
```

### Propose Endpoint — Skeleton

```python
# Source: CONTEXT.md D-07, D-12 [CITED]

class UpdateProposeRequest(BaseModel):
    prompt: str
    project: str
    noteIds: list[str]

class NoteDiff(BaseModel):
    noteId: str
    title: str
    originalContent: str
    proposedContent: str
    diffHtml: str
    hasChanges: bool
    updatedAt: str  # verbatim from Neo4j — passed back in confirm

@app.post("/knowledge/update/propose")
def knowledge_update_propose(payload: UpdateProposeRequest):
    if not payload.noteIds:
        raise HTTPException(status_code=400, detail="noteIds must not be empty")
    results = []
    for note_id in payload.noteIds:
        note = read_single(
            "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) "
            "RETURN n.noteId AS noteId, n.title AS title, n.content AS content, n.updatedAt AS updatedAt",
            {"noteId": note_id, "graph": KNOWLEDGE_GRAPH},
        )
        if note is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")
        proposed_text = call_n8n_and_poll(
            webhook_path="dg/knowledge-update",
            body={"prompt": payload.prompt, "noteId": note_id, "currentContent": note["content"]},
            workflow_key="knowledge-update",
        )
        diff_html = word_diff_html(note["content"], proposed_text)
        results.append({
            "noteId": note_id,
            "title": note["title"],
            "originalContent": note["content"],
            "proposedContent": proposed_text,
            "diffHtml": diff_html,
            "hasChanges": proposed_text != note["content"],
            "updatedAt": note["updatedAt"],
        })
    return {"diffs": results}
```

### Confirm Endpoint — Skeleton

```python
# Source: existing PUT /knowledge/note/{note_id} [VERIFIED: app.py lines 1027-1056]

class NoteConfirmItem(BaseModel):
    noteId: str
    content: str       # user's final edited text (may differ from LLM proposal)
    updatedAt: str     # from propose response — optimistic lock token

class UpdateConfirmRequest(BaseModel):
    prompt: str
    project: str
    notes: list[NoteConfirmItem]

@app.post("/knowledge/update/confirm")
def knowledge_update_confirm(payload: UpdateConfirmRequest):
    affected = []
    now = datetime.now(timezone.utc).isoformat()
    for item in payload.notes:
        existing = read_single(
            "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) "
            "RETURN n.updatedAt AS updatedAt",
            {"noteId": item.noteId, "graph": KNOWLEDGE_GRAPH},
        )
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Note not found: {item.noteId}")
        if existing["updatedAt"] != item.updatedAt:
            raise HTTPException(
                status_code=409,
                detail=f"Note {item.noteId} was modified since propose step — reload and retry",
            )
        write_query(
            "MATCH (n:KnowledgeNote {noteId: $noteId, graph: $graph}) "
            "SET n.content = $content, n.updatedAt = $now",
            {"noteId": item.noteId, "graph": KNOWLEDGE_GRAPH, "content": item.content, "now": now},
        )
        affected.append(item.noteId)
    # Write KnowledgeSession
    session_id = "ks-" + uuid.uuid4().hex[:12]
    write_query(
        "MERGE (s:KnowledgeSession {sessionId: $sessionId, project: $project, graph: $graph}) "
        "SET s.mode = 'update', s.prompt = $prompt, s.result = $result, s.createdAt = $createdAt",
        {
            "sessionId": session_id,
            "project": payload.project,
            "graph": KNOWLEDGE_GRAPH,
            "prompt": payload.prompt,
            "result": json.dumps({"affectedNoteIds": affected})[:2000],
            "createdAt": now,
        },
    )
    return {"affectedNoteIds": affected, "sessionId": session_id}
```

### n8n knowledge-update Workflow — Prompt Node

```javascript
// Source: knowledge-ingest.json Build Insert Prompt pattern [VERIFIED]
// Node: "Build Update Prompt" in knowledge-update.json

const input = $items('Set Input Defaults')[0].json;
const currentContent = input.current_content || '';
const updatePrompt = input.prompt_text || '';

const prompt = [
  'You are an architectural knowledge editor.',
  'Revise the note content according to the update instruction.',
  'Return ONLY the revised note text — no explanation, no JSON, no markdown fences.',
  'Preserve the original structure and tone. Only change what the instruction requests.',
  '',
  'Update instruction:',
  updatePrompt,
  '',
  'Current note content:',
  currentContent,
  '',
  'Revised note content:'
].join('\n');

return [{ json: { ...input, update_prompt: prompt } }];
```

The Ollama call for this workflow uses `"stream": false` without `"format": "json"` — the LLM returns plain prose, not a JSON object. The Parse LLM Text node extracts `$json.response` directly (no JSON.parse needed). [VERIFIED: knowledge-ingest.json Ollama node line 78 for model/stream pattern; format omitted for plain text]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM annotates its own diffs | Server-side difflib on LLM output | Phase 4 decision | Deterministic, consistent diffs regardless of LLM version |
| Direct LLM write to Neo4j | Three-step Match/Propose/Confirm | Phase 4 decision | No silent overwrites; user reviews before commit |

**Deprecated/outdated:**
- `[DEL]`/`[INS]` marker approach (discussed in STATE.md): Explicitly rejected — LLM annotation is inconsistent. Python difflib is the canonical approach.

---

## Runtime State Inventory

Step 2.5: SKIPPED — This is a greenfield addition of new endpoints and a new n8n workflow. No rename, refactor, or migration involved. No existing runtime state to audit.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 (data-service container) | All three endpoints | Yes | Pinned in Dockerfile | — |
| `difflib` | Propose endpoint diff computation | Yes | stdlib (no install) | — |
| `urllib.request` | Propose endpoint n8n call | Yes | stdlib (no install) | — |
| Neo4j full-text index `knowledge_note_search` | Match endpoint | Yes (created at startup) | app.py line 595-600 [VERIFIED] | — |
| n8n container reachable from data-service | Propose endpoint | Yes (Docker network) | Verified in docker-compose [VERIFIED] | — |
| `N8N_INTERNAL_URL` env var in data-service | Propose endpoint | NOT PRESENT [VERIFIED: docker-compose.yml] | — | Must add `N8N_INTERNAL_URL: http://n8n:5678` to docker-compose + `depends_on: n8n` |
| Ollama (llama3.1) | knowledge-update n8n workflow | Yes (existing) | Already used by other workflows [VERIFIED] | — |

**Missing dependencies with no fallback:**
- `N8N_INTERNAL_URL` in data-service env — must be added to docker-compose.yml before propose endpoint works.
- `depends_on: n8n` in data-service service block — n8n must start before data-service if propose is called early. Currently data-service does NOT depend on n8n [VERIFIED: docker-compose.yml line 36-38].

**Missing dependencies with fallback:**
- None.

---

## Validation Architecture

> `workflow.nyquist_validation` not present in .planning/config.json — treated as enabled.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | No existing test framework detected in data-service |
| Config file | None — Wave 0 must create test scaffold |
| Quick run command | `docker exec data-service python -m pytest tests/ -x -q` (after Wave 0) |
| Full suite command | `docker exec data-service python -m pytest tests/ -v` |

Note: The C# DG project uses xUnit (`dotnet test`), but data-service is Python/FastAPI with no test directory present. Wave 0 must add pytest.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UPDK-01 | Match returns candidates ranked by score | unit | `pytest tests/test_update_flow.py::test_match_returns_candidates -x` | Wave 0 |
| UPDK-01 | Match returns empty list when no notes match | unit | `pytest tests/test_update_flow.py::test_match_no_results -x` | Wave 0 |
| UPDK-02 | Propose returns diff per selected noteId | integration | `pytest tests/test_update_flow.py::test_propose_returns_diffs -x` | Wave 0 |
| UPDK-03 | word_diff_html marks additions and deletions | unit | `pytest tests/test_update_flow.py::test_word_diff_html -x` | Wave 0 |
| UPDK-04 | Propose hasChanges=False when LLM returns identical text | unit | `pytest tests/test_update_flow.py::test_propose_no_changes -x` | Wave 0 |
| UPDK-05 | Confirm writes content, returns affectedNoteIds | integration | `pytest tests/test_update_flow.py::test_confirm_writes -x` | Wave 0 |
| UPDK-05 | Confirm returns 409 when updatedAt mismatch | unit | `pytest tests/test_update_flow.py::test_confirm_409_on_stale -x` | Wave 0 |
| UPDK-06 | Confirm creates KnowledgeSession node | integration | `pytest tests/test_update_flow.py::test_confirm_creates_session -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `docker exec data-service python -m pytest tests/test_update_flow.py -x -q`
- **Per wave merge:** `docker exec data-service python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `data-service/tests/__init__.py` — test package
- [ ] `data-service/tests/test_update_flow.py` — unit tests for difflib logic + endpoint mocks
- [ ] `data-service/tests/conftest.py` — Neo4j mock fixtures (or skip integration if no test Neo4j)
- [ ] `pytest` install: add `pytest` to `data-service/requirements.txt`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | All endpoints are internal (same origin proxy); no user auth layer in current system |
| V3 Session Management | No | Stateless REST; KnowledgeSession is audit trail not auth session |
| V4 Access Control | No | Project isolation via `project` property on all nodes |
| V5 Input Validation | Yes | Pydantic BaseModel validates all request payloads; `prompt` and `noteIds` validated before use |
| V6 Cryptography | No | No secrets in update flow |

### Known Threat Patterns for FastAPI + Neo4j

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Neo4j injection via prompt string | Tampering | Parameterized queries only — `$query` parameter in CALL, never f-string interpolation [VERIFIED: all existing queries use parameters] |
| Path traversal via noteId | Tampering | noteId is a hash / UUID — never used in filesystem paths; validated against Neo4j graph only |
| LLM prompt injection via note content | Tampering | Acceptable risk — LLM output goes to difflib, not directly executed; no Cypher generated from LLM output in this flow |
| Oversized content payload | DoS | Existing 100KB limit on note content [CITED: REQUIREMENTS.md Out of Scope] — enforce in confirm endpoint payload validation |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `autojunk=False` prevents junk heuristic from suppressing common words in short notes | Code Examples / Pitfall 4 | Diff output may silently omit changed common words — incorrect diff display |
| A2 | `read_many()` correctly handles `CALL db.index.fulltext.queryNodes YIELD` procedures | Architecture Patterns / Pattern 1 | Match endpoint crashes or returns wrong data — would need a custom session.run loop |
| A3 | n8n `knowledge-update` workflow should use plain-text response (no `format: "json"`) from Ollama | Code Examples / n8n workflow prompt | LLM wraps response in JSON object — Parse node extracts wrong field |

---

## Open Questions

1. **Per-note n8n calls vs. batched call for propose with multiple noteIds**
   - What we know: D-07 says propose accepts an array of noteIds. Ollama context window limits (100KB [CITED: REQUIREMENTS.md]).
   - What's unclear: Should data-service call n8n once per note (sequential loop) or one call with all notes concatenated?
   - Recommendation: One call per note (sequential in data-service Python loop). Simpler n8n workflow, avoids context window issues, each note gets independent LLM attention. Total latency for N notes = N * LLM time — acceptable since propose is user-initiated.

2. **Confirm: atomic write across multiple notes**
   - What we know: Confirm receives a list of notes to write. Neo4j driver used via `write_query()` which opens/closes session per call.
   - What's unclear: If the second of five note writes fails, the first is already committed. Is partial update acceptable?
   - Recommendation: For Phase 4, partial writes are acceptable — each note is independent. Add a note to the response listing which noteIds succeeded. Full transaction rollback would require neo4j driver transaction API (`session.begin_transaction()`), which is out of scope for this phase.

---

## Sources

### Primary (HIGH confidence)
- `data-service/app.py` — Existing endpoint patterns, Pydantic models, helper functions, import list [VERIFIED]
- `n8n/workflows/knowledge-ingest.json` — Complete n8n workflow pattern for webhook + Ollama + execution-result post-back [VERIFIED]
- `n8n/workflows/knowledge-query.json` — Polling and progress update pattern [VERIFIED]
- `docker-compose.yml` — Environment variables, service dependencies [VERIFIED]
- `graph-viewer/nginx.conf` — Proxy paths for n8n and data-service [VERIFIED]
- `graph-viewer/index.html` lines 1554-1613 — Client-side polling pattern (1.5s interval) [VERIFIED]
- `.planning/milestones/v1.1-phases/04-update-flow-endpoints/04-CONTEXT.md` — All locked decisions D-01 through D-13 [VERIFIED]
- Python stdlib difflib — Tested locally with `py -3` [VERIFIED]

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — UPDK-01 through UPDK-06, Out of Scope (100KB limit) [VERIFIED]
- `data-service/requirements.txt` — No httpx; urllib.request is the right choice [VERIFIED]

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in existing codebase or stdlib
- Architecture: HIGH — all patterns traced to working existing code
- Pitfalls: MEDIUM-HIGH — most verified; autojunk behavior is ASSUMED
- n8n workflow structure: HIGH — mirrors existing knowledge-ingest.json exactly

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable dependencies, no fast-moving ecosystem)
