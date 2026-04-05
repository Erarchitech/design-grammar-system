---
tags: [integration, ollama, llm, ai]
date: 2026-04-05
---

# Ollama Runs Local LLM Inference for Cypher Generation

## Connection

| Parameter | Value |
|-----------|-------|
| Image | `ollama/ollama:latest` |
| External port | 11435 → 11434 |
| Docker URL | `http://ollama:11434` |
| Default model | `llama3.1:latest` (env `OLLAMA_MODEL`) |
| GPU | NVIDIA (all GPUs reserved via `deploy.resources`) |

## API Usage

n8n calls `POST http://ollama:11434/api/generate` with:

```json
{
  "model": "llama3.1:latest",
  "prompt": "<constructed prompt>",
  "stream": false,
  "options": {
    "temperature": 0.1,
    "num_predict": 4096
  }
}
```

Low temperature (0.1) ensures deterministic Cypher output.

## Two LLM Call Patterns

### Rules Ingest
- **Input**: NL rule + schema + few-shot → raw Cypher text output
- **Output**: MERGE/SET statements (no JSON wrapper)
- **Post-processing**: Parse, validate bracket nesting, deduplicate

### Graph Query
- **Call 1**: NL question + schema → `{"cypher":"SELECT ..."}` (JSON output)
- **Call 2**: Cypher results + question → natural language answer

## Model Management

Ollama stores models in Docker volume `ollama`. First run requires `ollama pull llama3.1:latest`.

## Related

- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[LLM Cypher output needs bracket nesting validation]]
