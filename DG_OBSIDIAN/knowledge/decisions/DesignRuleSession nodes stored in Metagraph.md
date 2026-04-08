---
tags: [decision, v1.1, phase-07]
date: 2026-04-08
---

# DesignRuleSession nodes stored in Metagraph

## Context
Phase 07 adds Session History panels. KnowledgeSession nodes already exist in `KnowledgeGraph` for Specs&Notes. Design rules need their own session storage.

## Decision
Create `DesignRuleSession` nodes with `graph: 'Metagraph'` to store ingest/query/edit session history for design rules. Uses the same pattern as `KnowledgeSession` but in the Metagraph graph space.

## Properties
- `sessionId` — `drs-` prefix + uuid hex
- `project` — project name for isolation
- `mode` — `ingest` | `query` | `edit`
- `prompt` — user's input text
- `result` — response text (truncated to 2000 chars)
- `createdAt` — ISO timestamp
- `graph` — always `'Metagraph'`

## Endpoints
- `POST /design-rule-sessions` — store a new session
- `GET /design-rule-sessions/{project}` — list sessions descending by date

## Rationale
- Separate node label (`DesignRuleSession` vs `KnowledgeSession`) avoids mixing concerns
- Metagraph is the correct graph space since design rules live there
- Same REST pattern keeps the codebase consistent
- Auto-save on completion (all 8 paths) ensures no sessions are lost
