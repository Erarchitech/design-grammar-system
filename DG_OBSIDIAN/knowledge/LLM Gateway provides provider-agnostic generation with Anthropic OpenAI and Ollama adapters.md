---
tags: [architecture, llm-gateway, phase-01, v9.0]
date: 2026-07-07
---

# LLM Gateway provides provider-agnostic generation with Anthropic OpenAI and Ollama adapters

The LLM Gateway (`data-service/llm_gateway.py`) is a provider-agnostic abstraction layer that routes LLM prompts to the configured provider. Built in [[sessions/2026-07-07 v9.0 Phase 01 execution|Phase 01]].

## Architecture

- **Strategy pattern** — `LLMAdapter` ABC with 3 concrete adapters: `AnthropicAdapter`, `OpenAIAdapter`, `OllamaAdapter`
- **Factory** — `get_adapter(provider, base_url)` returns the correct adapter instance
- **Encryption** — Fernet AES-GCM for API key at-rest storage, master secret from `LLM_MASTER_SECRET` env var
- **Settings persistence** — JSON file in `DATA_DIR/llm-settings.json`, read on every call (no caching per D-12)

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /llm/settings | Read provider/model/key status (masked) |
| PUT | /llm/settings | Save config, encrypt key |
| DELETE | /llm/settings | Clear → Ollama fallback |
| POST | /llm/generate | Route prompt to active provider |
| POST | /llm/settings/test | Validate saved key |
| GET | /llm/models | List provider models |

## Key decisions

- D-01: Thin normalization — each adapter keeps native prompt format
- D-02: Explicit `provider` tag — no auto-detection
- D-07: Gateway resolves active provider from settings; n8n sends `{provider: null, model: null}`
- D-12: Settings read on every call — instant provider switch, no restart

## Related

- [[debugging/get_adapter ignores baseUrl from settings|Bug: get_adapter() ignored baseUrl]]
- [[n8n runs two async webhook workflows for ingest and query]]
- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
