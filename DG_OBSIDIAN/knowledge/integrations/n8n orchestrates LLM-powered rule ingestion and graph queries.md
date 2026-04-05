---
tags: [integration, n8n, workflow, webhook, llm]
date: 2026-04-05
---

# n8n Orchestrates LLM-Powered Rule Ingestion and Graph Queries

## Connection

| Parameter | Value |
|-----------|-------|
| Image | `n8nio/n8n` |
| Port | 5678 (proxied at `/n8n/`) |
| Auth | Basic (`erarchitech@gmail.com`) |

## Webhooks

| Path | Method | Workflow | Response |
|------|--------|----------|----------|
| `/webhook/dg/rules-ingest` | POST | rules-to-metagraph | Async (immediate 200) |
| `/webhook/dg/graph-query` | POST | graph-query-mcp | Async (immediate 200) |

## Ingest Webhook Body

```json
{
  "rules_text": "Max building height is 75 meters",
  "cypher_prompt": "(optional raw Cypher)",
  "project": "my-project",
  "neo4j_url": "http://neo4j:7474",
  "ollama_url": "http://ollama:11434",
  "ollama_model": "llama3.1:latest",
  "data_service_url": "http://data-service:8000"
}
```

## Query Webhook Body

```json
{
  "prompt": "What is the maximum building height?",
  "project": "my-project",
  "ollama_url": "http://ollama:11434",
  "mcp_url": "http://data-service:8000"
}
```

## Progress Tracking

Both workflows report progress to `data-service /execution-result`:
- Status: `running` with step numbers (1–5)
- Final: `completed` or `error` with payload

The UI polls `/execution-result/{executionId}` every 1.5s. See [[Async polling pattern for n8n workflow execution tracking]].

## Prompt Engineering

Prompts are constructed dynamically in Function nodes with:
- v3 schema constraints
- Existing entity IRIs (prevents duplicates)
- Few-shot Cypher examples
- Semantic mapping for violation builtins
- Live schema context from MCP (query workflow)

See [[LLM prompts embed schema constraints instead of fine-tuning]].

## Related

- [[n8n runs two async webhook workflows for ingest and query]]
- [[Ollama runs local LLM inference for Cypher generation]]
- [[LLM Cypher output needs bracket nesting validation]]
