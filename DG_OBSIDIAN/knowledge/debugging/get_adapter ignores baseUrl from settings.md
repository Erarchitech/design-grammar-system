---
tags: [debugging, llm-gateway, phase-01, base-url, openai-adapter]
date: 2026-07-07
severity: blocker
status: fixed
---

# get_adapter() ignores baseUrl from settings

**Found:** 2026-07-07 during Phase 01 manual testing
**Fixed:** 2026-07-07, commit `4724ed9`

## Symptom

A configured API key (DeepSeek, OpenAI-compatible) with `baseUrl: "https://api.deepseek.com/v1"` returned 401 `PROVIDER_AUTH_FAILED` on `POST /llm/settings/test`. Direct curl to `https://api.deepseek.com/v1/chat/completions` with the same key succeeded.

## Root Cause

`get_adapter(provider)` in `llm_gateway.py:320` created `OpenAIAdapter()` with the default `base_url="https://api.openai.com/v1"` — completely ignoring `settings.get("baseUrl")`. The DeepSeek API key was being sent to OpenAI's servers, which rejected it with 401.

Both `llm_generate` and `test_llm_settings` in `app.py` called `get_adapter(provider)` without passing the base URL from settings.

Affected call chain:
```
PUT /llm/settings (saves baseUrl) → OK
POST /llm/settings/test → get_adapter("openai") → OpenAIAdapter()  ← BUG: base_url = "https://api.openai.com/v1"
                                                      ignores settings.baseUrl
```

## Fix

Three-layer change:

1. **`get_adapter()`** — added optional `base_url` parameter:
   ```python
   def get_adapter(provider: str, base_url: str | None = None) -> LLMAdapter:
       ...
       return OpenAIAdapter(base_url=base_url or "https://api.openai.com/v1")
   ```

2. **`list_models_for_provider()`** — added `base_url` parameter, forwards to `get_adapter()`

3. **`app.py` endpoints** — all 3 call sites pass `settings.get("baseUrl")`:
   - `llm_generate`: `get_adapter(provider, settings.get("baseUrl"))`
   - `test_llm_settings`: `get_adapter(provider, settings.get("baseUrl"))` + `list_models_for_provider(provider, api_key, settings.get("baseUrl"))`
   - `get_llm_models`: `list_models_for_provider(provider, api_key, settings.get("baseUrl"))`

## Prevention

- All new adapter factory calls must consider the base URL from settings
- OpenAI-compatible providers (DeepSeek, Groq, Together, Azure, etc.) require this path
- Anthropic adapter is unaffected (hardcoded URL per D-03)
- Ollama adapter is unaffected (hardcoded Docker service URL)

## Verification

- 30/30 gateway tests pass (mocked — no live API key dependency)
- Direct DeepSeek API call confirmed key is valid
- Post-fix manual test pending (requires Docker rebuild)
