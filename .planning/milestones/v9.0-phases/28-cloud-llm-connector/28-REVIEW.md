---
phase: 28-cloud-llm-connector
reviewed: 2026-07-07T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - data-service/llm_gateway.py
  - data-service/app.py
  - data-service/requirements.txt
  - docker-compose.yml
  - data-service/tests/test_llm_gateway.py
  - n8n/workflows/rules-to-metagraph.json
  - n8n/workflows/graph-query-mcp.json
  - n8n/workflows/spec-ingest.json
  - n8n/workflows/spec-query.json
  - n8n/workflows/spec-update.json
  - graph-viewer/index.html
findings:
  critical: 3
  warning: 5
  info: 3
  total: 11
status: issues_found
---

# Phase 28: Code Review Report — Cloud LLM Connector

**Reviewed:** 2026-07-07
**Depth:** standard
**Files Reviewed:** 11 (6 data-service, 5 n8n workflows, 1 UI)
**Status:** issues_found

## Summary

Code review of the provider-agnostic LLM gateway implementation covering 11 source files across the data-service (Python), n8n workflow rewiring (JSON), and UI (HTML/JS). The implementation is structurally sound with clean adapter separation, proper Fernet encryption, and correct n8n response field renaming. However, 3 critical findings were identified:

1. **LLM Settings API calls from the UI use broken URLs** — the `/llm/*` endpoints are not proxied by nginx, so all fetches silently return HTML instead of JSON, making the settings panel non-functional in production.
2. **OpenAI adapter sends `"Bearer None"`** when the API key is unset and provider is overridden at request level.
3. **Hardcoded credentials** in docker-compose.yml checked into version control.

Additional warnings cover missing startup initialization, a race condition on the Ollama model cache, dead code/unused parameters, and missing input validation.

---

## Critical Issues

### CR-01: LLM Settings fetch calls not proxied by nginx

**File:** `graph-viewer/index.html` lines 4013, 4031, 4058, 4077
**Issue:** The LLMSettingsPanel component (`LLMSettingsPanel`) makes fetch requests using relative URLs `/llm/settings`, `/llm/settings/test`, and `/llm/models`. However, the nginx config (`graph-viewer/nginx.conf`) only proxies `/data-service/` to the data-service container. The catch-all `location /` block serves the SPA `index.html` for all unmatched routes. Therefore all LLM Settings API calls receive HTML instead of JSON, causing the panel to fail silently or display parse errors.

The GraphViewerPage correctly uses `getDataServiceBaseUrl()` returning `/data-service` prefix, but the LLMSettingsPanel does not follow the same pattern.

**Fix:** Either add an nginx `/llm/` location block proxying to `http://data-service:8000`, or change the fetch calls to use `/data-service/llm/settings` etc. The latter is consistent with the existing pattern:

```nginx
# Option A: nginx.conf — add location block
location /llm/ {
    set $ds_upstream http://data-service:8000;
    proxy_pass $ds_upstream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Or in index.html:
```javascript
// Option B: Use data-service prefix consistent with other components
// Replace line 4013
fetch(getDataServiceBaseUrl() + "/llm/models?provider=" + encodeURIComponent(provider || "ollama"))
// Replace line 4031
fetch(getDataServiceBaseUrl() + "/llm/settings", { method: "PUT", ... })
```

---

### CR-02: OpenAI adapter sends `"Bearer None"` when api_key is None

**File:** `data-service/llm_gateway.py` line 224
**Issue:** The OpenAI adapter formats its auth header using an f-string:
```python
"Authorization": f"Bearer {api_key}",
```
When `api_key` is `None` (which happens when no API key is configured in settings and the request provider is overridden to "openai"), this produces the literal header `Authorization: Bearer None`.

The root cause is in `data-service/app.py` lines 907-913: `resolve_active_provider()` resolves the api_key based on saved settings. If settings are empty, it returns `("ollama", None, None)`. The request-level override on line 910 can then change `provider` to "openai" without re-resolving the api_key. The OpenAI adapter then receives `None` instead of a valid key.

The AnthropicAdapter handles this correctly at line 165: `"x-api-key": api_key or ""` — but OpenAIAdapter does not.

**Fix:** Either add an `api_key or ""` guard in the OpenAIAdapter:
```python
"Authorization": f"Bearer {api_key or ''}",
```
Or better, re-resolve api_key in the endpoint after applying request-level overrides, or validate that api_key is not None for non-Ollama providers:

```python
# In app.py llm_generate, after request-level overrides (line 913):
if provider != "ollama" and not api_key:
    raise HTTPException(status_code=400, detail="API key required for provider: " + provider)
```

---

### CR-03: Hardcoded n8n credentials in docker-compose.yml

**File:** `docker-compose.yml` lines 49-50
**Issue:** n8n authentication credentials are hardcoded in plaintext:
```
N8N_BASIC_AUTH_USER: erarchitech@gmail.com
N8N_BASIC_AUTH_PASSWORD: Ermolenko#^4538!
```
These values are checked into version control. Even for a local deployment, having secrets in a committed YAML file is a security risk. If the repository is shared, forked, or made public, these credentials are immediately exposed.

**Fix:** Use environment variable interpolation consistent with the existing pattern (e.g., `SPECKLE_WRITE_TOKEN: ${SPECKLE_WRITE_TOKEN:-}`):
```
N8N_BASIC_AUTH_USER: ${N8N_USER:-erarchitech@gmail.com}
N8N_BASIC_AUTH_PASSWORD: ${N8N_PASSWORD:-Ermolenko#^4538!}
```

---

## Warnings

### WR-01: `init_ollama_models()` never called at startup

**File:** `data-service/llm_gateway.py` lines 514-525, `data-service/app.py` (missing)
**Issue:** Per D-16, Ollama models should be auto-discovered at startup. The `init_ollama_models()` function exists in `llm_gateway.py` but is neither imported nor called from `app.py`. The `@app.on_event("startup")` handler only calls `ensure_spec_indexes()`. The model cache initializes lazily on the first `GET /llm/models` call, which introduces a delay and a race condition (see WR-02).

**Fix:** Import `init_ollama_models` in `app.py` and call it in the startup handler:
```python
from llm_gateway import init_ollama_models  # add to existing import block

@app.on_event("startup")
def ensure_spec_indexes():
    init_ollama_models()  # add this line
    # ... existing code ...
```

---

### WR-02: Race condition on `_ollama_models_cache`

**File:** `data-service/llm_gateway.py` line 511
**Issue:** `_ollama_models_cache` is a module-level mutable global accessed and mutated without any synchronization primitive. In `list_models_for_provider()` (lines 539-551), when the cache is `None`, `init_ollama_models()` can be called concurrently by multiple requests. The function writes to the same global without locking:
```python
global _ollama_models_cache
if _ollama_models_cache is None:
    init_ollama_models()  # possible concurrent execution
return _ollama_models_cache or []
```

**Fix:** Use `threading.Lock` or, preferably, initialize synchronously at startup (see WR-01) so the cache is never `None` during request handling. For the lock approach:
```python
import threading
_ollama_models_cache: list[str] | None = None
_ollama_cache_lock = threading.Lock()

def list_models_for_provider(...):
    if provider == "ollama":
        global _ollama_models_cache
        with _ollama_cache_lock:
            if _ollama_models_cache is None:
                init_ollama_models()
            return _ollama_models_cache or []
```

---

### WR-03: `should_refresh_on_test` imported but never called

**File:** `data-service/llm_gateway.py` lines 554-560, `data-service/app.py` line 47
**Issue:** The function `should_refresh_on_test()` is defined in `llm_gateway.py` and imported in `app.py` (line 47), but it is never referenced in any endpoint handler. This is dead code. The function was intended to determine whether to replace seed models with live results after a successful connection test, but the logic was never wired into the `POST /llm/settings/test` or `GET /llm/models` endpoints.

**Fix:** Either implement the wiring in the test endpoint to call `should_refresh_on_test` and update the model cache accordingly, or remove the import and the function.

---

### WR-04: `hasApiKey` parameter passed but unused in `fetchModels`

**File:** `graph-viewer/index.html` line 4012 (function signature), lines 4053, 4069, 4130 (call sites)
**Issue:** The `fetchModels(provider, hasApiKey)` function accepts a second parameter `hasApiKey` but never references it in the function body. Callers pass `data.apiKeyConfigured` as the second argument, but this value is silently ignored. This is dead parameter passing.

**Fix:** Remove the unused parameter from the function signature and call sites:
```javascript
function fetchModels(provider) {
  return fetch("/llm/models?provider=" + encodeURIComponent(provider || "ollama"))
    // ...
}
```

---

### WR-05: No provider validation in `PUT /llm/settings`

**File:** `data-service/app.py` lines 867-887
**Issue:** The `PUT /llm/settings` endpoint accepts any string for `provider` without validation against known provider names. An invalid provider value gets persisted and only surfaces as a 502 error at generate time (when `get_adapter()` raises `ValueError`). This allows persisting invalid state that degrades user experience.

**Fix:** Add validation against allowed provider values:
```python
VALID_PROVIDERS = {"anthropic", "openai", "ollama"}

@app.put("/llm/settings")
def put_llm_settings(payload: LLMSettingsPayload):
    if payload.provider is not None and payload.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {payload.provider}")
    # ... rest of handler ...
```

---

## Info

### IN-01: `call_n8n_sync` uses `urllib.request` instead of `httpx`

**File:** `data-service/app.py` lines 96-118
**Issue:** The existing `call_n8n_sync` function uses the standard library `urllib.request` for HTTP calls, while the new LLM gateway code uses `httpx`. Now that `httpx` is a project dependency (added in this phase via requirements.txt), the n8n polling code could be migrated for consistency and better error handling. Minor style inconsistency, not a bug.

---

### IN-02: New `httpx.Client` created per request in all adapters

**File:** `data-service/llm_gateway.py` lines 177, 202, 234, 259, 289, 310
**Issue:** Every `generate()` and `list_models()` call creates a new `httpx.Client` instance inside a `with` block. This prevents TCP connection reuse and adds allocation overhead per request. For a low-traffic internal service this is acceptable, but a shared client with connection pooling would be more efficient. Minor performance concern.

---

### IN-03: `LLM_MASTER_SECRET` default is a weak placeholder

**File:** `docker-compose.yml` line 34
**Issue:** The default value `change-me-to-a-random-secret` is a clear instruction to users, which is good. However, there is no startup-time check that warns or blocks if the default hasn't been changed. The `PUT /llm/settings` endpoint checks if the secret is empty (line 870-871) but doesn't check if it equals the default placeholder. A deployment running with the default secret would have trivially breakable encryption.

---

_Reviewed: 2026-07-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
