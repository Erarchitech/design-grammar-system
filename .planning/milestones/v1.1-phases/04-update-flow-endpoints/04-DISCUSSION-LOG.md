# Phase 4: Update Flow Endpoints - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 04-update-flow-endpoints
**Areas discussed:** Match endpoint strategy, Diff computation, Confirm write safety, n8n vs data-service split

---

## Match Endpoint Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Direct full-text search | data-service extracts key terms and runs Neo4j full-text index query directly — no LLM needed | ✓ |
| LLM-interpreted matching via n8n | Send prompt to Ollama via n8n to extract search terms/intent, then run full-text search | |
| Hybrid: direct first, LLM fallback | Try direct full-text search; if zero results, fall back to LLM-interpreted search | |

**User's choice:** Direct full-text search
**Notes:** None — straightforward choice for deterministic matching.

| Option | Description | Selected |
|--------|-------------|----------|
| Top 10 | Balanced — enough to find the right note without overwhelming the UI | ✓ |
| Top 5 | Tighter list, faster for users who know what they're looking for | |
| All matches above threshold | Return everything scored above a relevance cutoff | |

**User's choice:** Top 10
**Notes:** None

---

## Diff Computation

| Option | Description | Selected |
|--------|-------------|----------|
| LLM writes new text, difflib computes diff | Ollama returns full updated text; Python difflib compares old vs new server-side | ✓ |
| LLM annotates changes inline | Ollama returns text with [DEL]/[INS] markers; server parses into HTML spans | |
| LLM returns full text + change description | Ollama returns updated text plus summary; difflib computes actual diff | |

**User's choice:** LLM writes new text, difflib computes diff
**Notes:** Resolves the STATE.md blocker about diff marker convention — pure difflib, no LLM markers.

| Option | Description | Selected |
|--------|-------------|----------|
| Word-level diff | difflib word-level comparison — highlights individual changed words/phrases | ✓ |
| Line-level diff | Standard unified diff style — shows added/removed lines | |
| Character-level diff | Finest granularity — shows every character change | |

**User's choice:** Word-level diff
**Notes:** Best suited for natural language note content where line breaks are sparse.

| Option | Description | Selected |
|--------|-------------|----------|
| Multiple notes per call | Accept array of noteIds, return diff for each in one HTTP round-trip | ✓ |
| One note per call | Simpler endpoint contract; UI calls once per selected note | |

**User's choice:** Multiple notes per call
**Notes:** Matches UPDK-02 requirement for plural "selected node IDs".

---

## Confirm Write Safety

| Option | Description | Selected |
|--------|-------------|----------|
| updatedAt check | Client sends updatedAt from propose step; server rejects with 409 if modified since | ✓ |
| Last-write-wins | No concurrency check; Confirm always writes | |
| Content hash check | Server hashes original content at propose; client sends hash back at confirm | |

**User's choice:** updatedAt check (optimistic locking)
**Notes:** None — uses existing updatedAt field already on KnowledgeNote nodes.

| Option | Description | Selected |
|--------|-------------|----------|
| User-edited text | Client sends final text from inline textarea editor | ✓ |
| LLM proposal only | Client sends proposal ID; server writes LLM output as-is | |

**User's choice:** User-edited text
**Notes:** Matches UPDK-04 requirement that user can modify textarea before confirming.

---

## n8n vs data-service Split

| Option | Description | Selected |
|--------|-------------|----------|
| Match + Confirm in data-service, Propose via n8n | Clean separation: LLM work in n8n, CRUD in data-service | ✓ |
| All three through n8n | Consistent with Phase 3 pattern but adds unnecessary latency for non-LLM ops | |
| All three in data-service | data-service calls Ollama directly; breaks established n8n pattern for LLM calls | |

**User's choice:** Match + Confirm in data-service, Propose via n8n
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| UI → data-service → n8n | data-service acts as proxy, fetches note content, sends to n8n, runs difflib on result | ✓ |
| UI → n8n directly | UI calls n8n webhook directly like Phase 3 insert/query | |

**User's choice:** UI → data-service → n8n
**Notes:** Keeps diff computation in Python (data-service) where difflib lives.

---

## Claude's Discretion

- Exact difflib function choice and word-level tokenization strategy
- n8n workflow internal node layout and prompt construction details
- Error handling for LLM returning malformed/empty text
- HTTP response shapes (field names, nesting) for all three endpoints
- How to handle Propose when LLM returns text identical to original (no-op diff)

## Deferred Ideas

None — discussion stayed within phase scope.
