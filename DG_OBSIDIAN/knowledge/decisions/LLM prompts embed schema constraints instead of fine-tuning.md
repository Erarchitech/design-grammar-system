---
tags: [decision, llm, prompt-engineering, architecture]
date: 2026-04-05
---

# LLM Prompts Embed Schema Constraints Instead of Fine-Tuning

## Decision

Cypher generation is constrained at **inference time** via structured prompts — no fine-tuned model is used. The prompts embed the full v3 schema, semantic mapping rules, and few-shot examples.

## Prompt Components

### Ingest Prompt (Build LLM Prompt node)
1. **Schema constraints** — allowed labels, relationships, key properties, graph assignments
2. **Node key conventions** — Rule_Id format, Atom_Id format, SWRL_label rules
3. **Semantic mapping** — how NL phrases map to SWRL builtins (violation inversion)
4. **Few-shot example** — complete v3-compliant Cypher for a height violation rule
5. **Existing entities** — IRIs already in the graph (for reuse, not duplication)
6. **User's NL rule** — appended at the end

### Query Prompt (Build Cypher Prompt node)
1. **v3 data model** — node labels, properties, relationship types
2. **Live schema context** — actual labels/rels/props from MCP `neo4j_schema`
3. **Query guidance** — patterns for numeric limits, rule listing, keyword matching
4. **User's question** — appended at the end

## Rationale

- **No training data required** — schema changes propagate instantly via prompt edits
- **Model-agnostic** — works with any instruction-following LLM (default: llama3.1)
- **Transparent** — prompt is visible and debuggable in n8n Function nodes
- **Low temperature (0.1)** — ensures deterministic, schema-compliant output

## Trade-offs

- **Prompt length** — 4000+ characters per prompt; token overhead per request
- **Accuracy gaps** — LLM sometimes generates invalid Cypher despite constraints
- **No learning** — repeated similar queries don't improve over time

## Related

- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[Ollama runs local LLM inference for Cypher generation]]
- [[Graph schema v3 is the canonical data model]]
- [[LLM Cypher output needs bracket nesting validation]]
