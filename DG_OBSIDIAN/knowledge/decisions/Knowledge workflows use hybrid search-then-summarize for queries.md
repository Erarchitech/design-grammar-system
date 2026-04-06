---
tags: [decision, v1.1, phase-03, knowledge-graph, n8n]
date: 2026-04-06
status: active
---

# Knowledge workflows use hybrid search-then-summarize for queries

## Decision

Natural language questions against the knowledge graph use a two-step hybrid approach:
1. **Full-text search** via Neo4j `knowledge_note_search` index finds matching `KnowledgeNote` nodes
2. **Ollama summarizes** the top 5 matching notes into a human-readable NL answer

The Cypher query displayed to the user (QRYK-02) is the deterministic full-text search query, NOT LLM-generated Cypher.

## Rationale

- **Reliability**: Full-text search is deterministic — no risk of LLM generating bad Cypher against knowledge nodes
- **Simplicity**: Avoids needing to teach the LLM the KnowledgeGraph schema for Cypher generation
- **Quality**: LLM focuses on what it's good at (summarization) rather than what it's risky at (Cypher generation for a new schema)
- **Consistency with D-06**: User sees the actual search query, not an opaque LLM-generated one

## Alternatives considered

1. **LLM generates Cypher** (same as graph-query-mcp) — rejected: higher risk of bad Cypher, knowledge schema is simpler than SWRL metagraph
2. **Full-text search only** (no LLM) — rejected: doesn't meet QRYK-01 requirement for NL answer

## Impact

- Knowledge-query n8n workflow has a deterministic Cypher step (no LLM for search)
- Ollama is called once per query (for answer synthesis), not twice
- Top 5 result cap keeps within llama3.1 context window
