# Phase 3: n8n Knowledge Workflows + LLM Ingest and Query - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 03-n8n-knowledge-workflows-llm-ingest-and-query
**Areas discussed:** LLM prompt design, Knowledge query strategy, n8n workflow wiring, Session tracking

---

## LLM Prompt Design

### Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON object | LLM returns {"title", "tags", "content"} — easy to parse, n8n processes structured output | ✓ |
| Markdown with markers | LLM returns structured markdown — more natural but harder to parse reliably | |
| You decide | Claude picks during planning | |

**User's choice:** JSON object
**Notes:** None

### Ambiguous Input Handling

| Option | Description | Selected |
|--------|-------------|----------|
| LLM always extracts | Must always produce title + at least one tag, even if inferred. No error branches. | ✓ |
| LLM can signal 'unclear' | Returns special marker when can't extract; system stores raw text. More robust but complex. | |
| You decide | Claude picks during planning | |

**User's choice:** LLM always extracts
**Notes:** None

### Existing Knowledge Context in Prompt

| Option | Description | Selected |
|--------|-------------|----------|
| No context needed | Independent inserts, short/fast prompts, tag dedup via MERGE | ✓ |
| Include existing tags | Feed existing tag names for vocabulary consistency | |
| Include tags + recent titles | Show tags and titles to avoid duplicates | |

**User's choice:** No context needed
**Notes:** None

---

## Knowledge Query Strategy

### Query Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: search then summarize | Full-text search finds notes, Ollama summarizes into NL answer. Two-step. | ✓ |
| LLM generates Cypher | Same pattern as graph-query-mcp. More flexible but riskier. | |
| Full-text search only | No LLM for queries. Doesn't meet QRYK-01. | |

**User's choice:** Hybrid: search then summarize
**Notes:** None

### Result Cap

| Option | Description | Selected |
|--------|-------------|----------|
| Top 5 notes | Fits llama3.1 context, enough material for good answer | ✓ |
| Top 10 notes | More context but risks hitting context limits | |
| You decide | Claude picks during planning | |

**User's choice:** Top 5 notes
**Notes:** None

---

## n8n Workflow Wiring

### Write Path

| Option | Description | Selected |
|--------|-------------|----------|
| n8n writes Neo4j directly | Same pattern as rules-to-metagraph. Consistent architecture. | ✓ |
| n8n calls data-service REST | Simpler n8n but adds endpoint, different coupling. | |
| You decide | Claude picks | |

**User's choice:** n8n writes Neo4j directly
**Notes:** None

### Polling Endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| Same endpoint, new workflow keys | Reuse /execution-result with keys 'knowledge-ingest' and 'knowledge-query' | ✓ |
| Separate /knowledge/result endpoint | New endpoint, more isolation but duplicates pattern | |
| You decide | Claude picks | |

**User's choice:** Same endpoint, new workflow keys
**Notes:** None

### Webhook Paths

| Option | Description | Selected |
|--------|-------------|----------|
| /webhook/dg/knowledge-ingest + /webhook/dg/knowledge-query | Follows existing naming convention | ✓ |
| You decide | Claude picks | |

**User's choice:** /webhook/dg/knowledge-ingest + /webhook/dg/knowledge-query
**Notes:** None

---

## Session Tracking

### Session Creation Location

| Option | Description | Selected |
|--------|-------------|----------|
| In n8n workflow | Final step after Neo4j success. Atomic with operation. | ✓ |
| In data-service endpoint | Centralized in Python but decoupled from n8n. | |
| You decide | Claude picks | |

**User's choice:** In n8n workflow
**Notes:** None

### Result Field Content

| Option | Description | Selected |
|--------|-------------|----------|
| Structured per mode | Insert: {noteId, title, tags}. Query: {answer, cypherUsed, matchCount}. | ✓ |
| Raw LLM output | Full LLM response as-is. Simpler but harder to display. | |
| You decide | Claude picks | |

**User's choice:** Structured per mode
**Notes:** None

---

## Claude's Discretion

- Few-shot example content and prompt structure
- n8n workflow node layout and processing steps
- Error handling for malformed LLM JSON output
- Exact Cypher templates for search + summarization
- Nginx proxy rules if needed

## Deferred Ideas

None — discussion stayed within phase scope.
