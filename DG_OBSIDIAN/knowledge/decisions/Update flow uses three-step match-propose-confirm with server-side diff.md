---
tags: [decision, v1.1, phase-04, knowledge-graph, update-flow]
date: 2026-04-06
status: active
---

# Update flow uses three-step match-propose-confirm with server-side diff

## Decision

The knowledge update flow uses a three-step backend pattern:

1. **Match** — direct Neo4j full-text search (no LLM), top 10 candidates, runs entirely in data-service
2. **Propose** — data-service fetches note content, sends to n8n → Ollama for text revision, then computes word-level diff via Python `difflib.SequenceMatcher(autojunk=False)` server-side, returns HTML spans (`diff-del`, `diff-ins`)
3. **Confirm** — data-service writes user-edited text (not raw LLM output) with optimistic locking (`updatedAt` check, 409 on mismatch), creates KnowledgeSession with `mode=update`

## Rationale

- **Match without LLM**: full-text search is fast, deterministic, and the index already exists from Phase 1
- **Server-side difflib over LLM annotation**: `[DEL]/[INS]` markers from LLM are unreliable; difflib is deterministic
- **Word-level granularity**: knowledge notes are prose (not code), so line-level diffs would be too coarse
- **Optimistic locking via updatedAt**: simple, uses existing field, no schema changes needed
- **User-edited text in confirm**: matches UPDK-04 requirement for inline editing before save
- **n8n returns plain text** (no `format: "json"`): output is prose, not structured data

## Alternatives considered

1. **LLM-annotated diff markers** — rejected: LLM marker accuracy unreliable
2. **Line-level diff** — rejected: too coarse for prose content
3. **Last-write-wins on confirm** — rejected: risks silent overwrite if note changed between propose and confirm
4. **Content hash check** — rejected: updatedAt is simpler and already exists

## Impact

- data-service gets 3 new POST endpoints (`/knowledge/update/match`, `/propose`, `/confirm`)
- New n8n workflow `knowledge-update` (8 nodes, no Neo4j writes)
- docker-compose needs `N8N_INTERNAL_URL` env var for data-service → n8n calls
- Resolves STATE.md blocker: "Diff marker convention needs a decision"
