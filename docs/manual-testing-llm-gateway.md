# LLM Gateway — Manual Testing Guide

**Phase:** 01-cloud-llm-connector  
**Date:** 2026-07-07  
**Status:** Ready for human verification (see `01-VERIFICATION.md`, `01-UAT.md`)

---

## Overview

This guide covers end-to-end manual testing of the LLM gateway. The gateway (`data-service:8000`) provides 6 endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/llm/settings` | Read current provider/model/key status |
| `PUT` | `/llm/settings` | Save provider, model, API key (encrypted at rest) |
| `DELETE` | `/llm/settings` | Clear all settings → fall back to Ollama |
| `POST` | `/llm/generate` | Route prompt to active provider adapter |
| `POST` | `/llm/settings/test` | Validate saved key with a minimal API call |
| `GET` | `/llm/models?provider=...` | List available models for a provider |

Two access paths:
- **Via nginx** (browser/UI): `http://localhost:8080/llm/*` ← the new `/llm/` location block added by CR-01 fix
- **Direct** (internal Docker): `http://data-service:8000/llm/*`

---

## Prerequisites

| What | Where to get it |
|------|-----------------|
| Docker Desktop running | — |
| DeepSeek API key | `sk-3c55aefb1b184cce8d30a87f6c45b25f` (from `DeepSeek_API_key.txt` in repo root) |
| Anthropic API key | https://console.anthropic.com/settings/keys |
| OpenAI API key | https://platform.openai.com/api-keys |
| `curl` or PowerShell `Invoke-RestMethod` | Pre-installed on Windows |
| Browser (for UI tests) | Any modern browser |

> **Provider notes:**
> - **DeepSeek** is OpenAI-compatible — use `provider: "openai"` with `baseUrl: "https://api.deepseek.com/v1"`
> - **Ollama** runs in the Docker stack — no API key needed, auto-discovered at startup
> - **Anthropic** uses `x-api-key` header, no base URL field

---

## Step 1: Start the Docker Stack

```powershell
# From project root
cd c:\Users\Admin\source\repos\design-grammar-system

# Rebuild data-service with the gateway changes (including CR fixes)
docker compose build --no-cache data-service design-grammars

# Start all services
docker compose up -d

# Wait ~30s for all services to be healthy
docker compose ps
```

Expected: all services show `Up` or `healthy`.

---

## Step 2: Verify Empty State (No Key → Ollama Fallback)

No API key has been configured yet — the gateway should fall back to Ollama.

### 2a: Check settings are empty

```powershell
# Via nginx (browser path)
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method GET | ConvertTo-Json

# Or direct to data-service
Invoke-RestMethod -Uri "http://localhost:8000/llm/settings" -Method GET | ConvertTo-Json
```

**Expected response:**
```json
{
    "provider": null,
    "model": null,
    "apiKeyConfigured": false,
    "apiKeyPreview": "",
    "baseUrl": null
}
```

### 2b: Verify Ollama fallback on generate

```powershell
$body = @{
    prompt = "Say hello in one word"
    provider = $null
    model = $null
    system = $null
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/generate" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected response:**
```json
{
    "text": "Hello",          // actual text from Ollama
    "provider": "ollama",
    "model": "llama3.1:latest",
    "usage": {
        "prompt_tokens": 15,
        "completion_tokens": 2,
        "total_tokens": 17
    }
}
```

> The `provider` field must be `"ollama"` — this confirms the fallback mechanism works.

---

## Step 3: Configure a Provider (DeepSeek via OpenAI-Compatible)

DeepSeek is OpenAI-compatible. Configure it as `openai` provider with the DeepSeek base URL.

### 3a: Save settings

```powershell
$body = @{
    provider = "openai"
    model = "deepseek-chat"
    apiKey = "sk-3c55aefb1b184cce8d30a87f6c45b25f"
    baseUrl = "https://api.deepseek.com/v1"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected response:**
```json
{
    "provider": "openai",
    "model": "deepseek-chat",
    "apiKeyConfigured": true,
    "apiKeyPreview": "sk-3c5...b25f",     // masked! first 6 + "..." + last 6
    "baseUrl": "https://api.deepseek.com/v1"
}
```

> **Key security checks:**
> - `apiKeyPreview` shows `sk-3c5...b25f` — never the full key
> - The raw key `sk-3c55aefb1b184cce8d30a87f6c45b25f` does NOT appear in the response

### 3b: Verify settings persist

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method GET | ConvertTo-Json
```

Should return the same masked response as above.

---

## Step 4: Test Connection

The `/llm/settings/test` endpoint validates the saved key with a minimal API call.

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings/test" -Method POST | ConvertTo-Json
```

**Expected success response:**
```json
{
    "success": true,
    "latencyMs": 850.5,                    // network-dependent, typically 200-2000ms
    "models": ["deepseek-chat", "deepseek-reasoner"],
    "error": null
}
```

**If failure:** the response will have `success: false` and an `error` field with a What+Where+How-to-fix message.

---

## Step 5: Generate via Configured Provider

Now the gateway should route to DeepSeek (not Ollama).

```powershell
$body = @{
    prompt = "Explain what SOLID principles are in one sentence"
    system = "You are a helpful coding assistant"
    provider = $null      # null → gateway resolves from saved settings
    model = $null         # null → gateway resolves from saved settings
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/generate" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected response:**
```json
{
    "text": "SOLID is a set of five object-oriented design principles...",
    "provider": "openai",
    "model": "deepseek-chat",
    "usage": {
        "prompt_tokens": 20,
        "completion_tokens": 25,
        "total_tokens": 45
    }
}
```

> The `provider` field must show `"openai"` — not `"ollama"`. This confirms the gateway correctly routes to the saved provider.

---

## Step 6: Provider Switching Without Restart (Key UAT Test)

This is the primary UAT test from `01-UAT.md`. It verifies D-07 and D-12 — provider switching takes immediate effect.

### 6a: Switch back to Ollama

```powershell
# Save Ollama as the provider (no API key needed)
$body = @{
    provider = "ollama"
    model = "llama3.1:latest"
    apiKey = $null
    baseUrl = $null
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected:** `apiKeyConfigured: true` (key from Step 3 still stored, just inactive), `provider: "ollama"`.

### 6b: Verify generation uses Ollama now

```powershell
$body = @{ prompt = "Say hello"; provider = $null; model = $null; system = $null } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/llm/generate" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected:** `provider: "ollama"` in response.

### 6c: Switch back to DeepSeek

```powershell
$body = @{
    provider = "openai"
    model = "deepseek-chat"
    apiKey = "sk-3c55aefb1b184cce8d30a87f6c45b25f"
    baseUrl = "https://api.deepseek.com/v1"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json" | ConvertTo-Json
```

### 6d: Generate again — verify switch is instant

```powershell
$body = @{ prompt = "Say hello"; provider = $null; model = $null; system = $null } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/llm/generate" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected:** `provider: "openai"` again.

> **No Docker restart, no n8n workflow edits, no data-service restart.** Switch → generate → immediate effect.

---

## Step 7: Test Request-Level Provider Override

Even with settings saved as `openai`, a request can override the provider:

```powershell
# Force Ollama for this request only
$body = @{
    prompt = "Say hello"
    provider = "ollama"
    model = "llama3.1:latest"
    system = $null
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/generate" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json
```

**Expected:** `provider: "ollama"` in response (but settings still say `openai` for next call).

---

## Step 8: Test Error Handling

### 8a: Invalid API key

```powershell
$body = @{
    provider = "openai"
    model = "deepseek-chat"
    apiKey = "sk-this-is-fake-and-invalid"
    baseUrl = "https://api.deepseek.com/v1"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json"
# Then test
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings/test" -Method POST | ConvertTo-Json
```

**Expected:** `success: false`, `error` contains actionable hint. The raw API key is NOT in the error.

### 8b: Invalid provider name

```powershell
$body = @{ provider = "google" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json"
```

**Expected:** HTTP 400 with `"Unknown provider: google. Valid options: anthropic, ollama, openai"`.

### 8c: Generate with invalid provider

```powershell
$body = @{ prompt = "hi"; provider = "unknown"; model = $null; system = $null } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/llm/generate" -Method POST -Body $body -ContentType "application/json"
```

**Expected:** HTTP 502 with structured error `{error, hint, code}`.

---

## Step 9: Test Model Discovery

```powershell
# Seed models (no key)
Invoke-RestMethod -Uri "http://localhost:8080/llm/models?provider=anthropic" -Method GET | ConvertTo-Json

# Should return seed list:
# ["claude-sonnet-5", "claude-opus-4-8", "claude-haiku-4-5-20251001"]

# Ollama models (auto-discovered at startup)
Invoke-RestMethod -Uri "http://localhost:8080/llm/models?provider=ollama" -Method GET | ConvertTo-Json

# Should return actual Ollama models: ["llama3.1:latest", ...]
```

---

## Step 10: Test Settings CRUD Lifecycle

### Full lifecycle:

```powershell
# 1. Start empty
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method GET | ConvertTo-Json
# → apiKeyConfigured: false

# 2. Save a key
$body = @{ provider = "anthropic"; model = "claude-sonnet-5"; apiKey = "sk-ant-test123456789" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json" | ConvertTo-Json
# → apiKeyConfigured: true, apiKeyPreview: "sk-ant...56789"

# 3. Update model only (key preserved)
$body = @{ model = "claude-opus-4-8" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method PUT -Body $body -ContentType "application/json" | ConvertTo-Json
# → model: "claude-opus-4-8", apiKeyConfigured still true

# 4. Clear everything
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method DELETE
# → HTTP 204 (no body)

# 5. Verify empty again
Invoke-RestMethod -Uri "http://localhost:8080/llm/settings" -Method GET | ConvertTo-Json
# → apiKeyConfigured: false
```

---

## Step 11: UI Verification (Browser)

Open `http://localhost:8080` in a browser:

1. **Login** (if n8n basic auth is enabled: check `docker-compose.yml` for `N8N_USER`/`N8N_PASSWORD`)
2. **Navigate to a project** → see the **"LLM Settings"** tile alongside Graph Viewer and Model Viewer
3. **Click LLM Settings** → the LLM Settings panel opens
4. **No-key state:** Yellow banner "Using local Ollama (fallback)" visible, provider/model/key form displayed
5. **Configure DeepSeek:**
   - Provider: `openai`
   - Model: `deepseek-chat`
   - API Key: `sk-3c55aefb1b184cce8d30a87f6c45b25f`
   - Base URL: `https://api.deepseek.com/v1`
   - Click **Save**
6. **Active state:** Green banner "Connected: openai", masked key preview `sk-3c5...b25f`
7. **Test Connection:** Click the button → shows latency and available models
8. **Remove:** Click Remove → confirm dialog → back to yellow fallback state
9. **Provider dropdown:** Switch to `ollama` → API key input disappears; switch to `openai` → Base URL field appears

> Open browser DevTools (F12) → Network tab. Verify:
> - `/llm/settings` requests return JSON (not HTML) ← CR-01 fix verification
> - API key never appears in response bodies (only masked preview)
> - `Content-Type: application/json` on PUT requests

---

## Step 12: n8n Workflow Integration

After the gateway is verified, test an n8n workflow:

1. Open `http://localhost:8080/n8n/` → log in
2. Open the **rules-to-metagraph** workflow
3. Execute it manually
4. Check that the HTTP node at `http://data-service:8000/llm/generate` returns a valid response
5. The downstream "Parse LLM Output" node should extract `.text` (not `.response`)
6. The Cypher query should execute successfully against Neo4j

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `/llm/settings` returns HTML | nginx not rebuilt. Run `docker compose build --no-cache design-grammars && docker compose up -d design-grammars` |
| Ollama fallback returns error | Ollama not running. `docker compose ps ollama` — wait for it to pull the model |
| DeepSeek returns 401 | API key invalid or expired. Verify at https://platform.deepseek.com/api_keys |
| `LLM_MASTER_SECRET not configured` | Env var missing. Check `docker-compose.yml` line 34 has `${LLM_MASTER_SECRET:-change-me-to-a-random-secret}` |
| "Unknown provider" on PUT | Provider validation working correctly (WR-05 fix). Use `anthropic`, `openai`, or `ollama`. |
| Model dropdown empty in UI | `GET /llm/models` failed. Check browser DevTools Network tab for the error response. |

---

## Sign-Off Checklist

- [ ] Empty settings → Ollama fallback works
- [ ] Save DeepSeek key → masked preview, `apiKeyConfigured: true`
- [ ] Test Connection → success with latency + model list
- [ ] Generate → response from DeepSeek, `provider: "openai"`
- [ ] Switch to Ollama → generate → `provider: "ollama"` (no restart)
- [ ] Switch back to DeepSeek → generate → `provider: "openai"` (no restart)
- [ ] Invalid key → structured error, no raw key leaked
- [ ] Invalid provider name → HTTP 400 with valid options
- [ ] DELETE settings → 204, subsequent GET shows empty
- [ ] UI: yellow banner in no-key state, green banner when connected
- [ ] UI: API key never appears unmasked in DOM or network responses
- [ ] nginx: all `/llm/*` requests return JSON (not SPA HTML)
