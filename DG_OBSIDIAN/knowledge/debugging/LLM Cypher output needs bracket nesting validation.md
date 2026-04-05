---
tags: [debugging, llm, cypher, validation]
date: 2026-04-05
---

# LLM Cypher Output Needs Bracket Nesting Validation

## Problem

The Ollama LLM sometimes generates malformed Cypher with mismatched brackets, unclosed strings, or invalid MERGE patterns.

## Symptoms

- Neo4j returns syntax errors on generated Cypher
- Parse LLM Output node throws on validation
- Ingestion workflow fails at "Execute LLM Cypher" step

## Validation in Parse LLM Output Node

The n8n Function node performs:
1. Split response by `MERGE` keyword
2. Validate bracket nesting per chunk (count `(`, `)`, `{`, `}`, `[`, `]`)
3. Drop malformed chunks
4. Consolidate duplicate variable definitions
5. Separate node MERGEs from relationship MERGEs
6. Enforce consistent single/double quote handling

## Mitigation Strategies

- **Low temperature (0.1)** — reduces creative/hallucinated output
- **Few-shot example** — teaches the model correct Cypher structure
- **Schema constraints in prompt** — limits vocabulary to known labels/relationships
- **Post-validation** — Parse node filters bad output before execution
- **Smart overrides** — Query workflow forces standard patterns for common questions

## Related

- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[Ollama runs local LLM inference for Cypher generation]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
