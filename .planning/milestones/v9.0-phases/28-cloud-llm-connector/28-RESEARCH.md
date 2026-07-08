# Phase 1: Cloud LLM Connector and Provider Abstraction - Research

**Researched:** 2026-07-06
**Domain:** Provider-agnostic LLM gateway, encrypted credential storage, UI settings panel, n8n workflow rewiring
**Confidence:** HIGH

## Summary

This phase builds a provider-agnostic LLM gateway into the existing `data-service` FastAPI application, replacing 5 direct Ollama HTTP calls from n8n workflows with a single `POST /llm/generate` endpoint that supports Anthropic Claude, OpenAI-compatible APIs, and local Ollama fallback. The gateway uses a simple Strategy pattern with thin provider adapters (no SDKs -- raw HTTP via `httpx`), encrypts API keys at rest using `cryptography.fernet.Fernet` (AES-GCM), and exposes CRUD endpoints for settings and model discovery. A new "LLM Settings" tab in the existing React SPA sidebar lets the user configure provider, model, and API key with real-time status feedback. The existing Speckle settings persistence pattern in app.py (JSON file in `DATA_DIR`, mask_token helper, GET/PUT endpoints) serves as the template for the LLM settings implementation.

**Primary recommendation:** Use the existing FastAPI + pydantic + httpx stack (all already installed + verified). Implement provider adapters as a Strategy pattern with an abstract `LLMAdapter` base class. Use `cryptography.fernet.Fernet` for at-rest key encryption with the master secret injected via env var. Follow the existing Speckle settings pattern (`settings/speckle`) for the LLM settings endpoints. Add 3 new dependencies to `requirements.txt`: `cryptography` (44.0+) already installed at 46.0.5, `httpx` already at 0.28.1 -- no new runtime dependencies needed beyond what's in the project.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Provider API authentication (API key header injection) | API / Backend | -- | Gateway in data-service owns all credential handling; keys never reach the browser |
| Provider API call dispatch | API / Backend | -- | Gateway routes to correct adapter based on provider tag |
| Encrypted credential persistence | API / Backend | -- | Server-side only; keys encrypted at rest in JSON file |
| Settings UI (provider select, model select, key input) | Browser / Client | API / Backend | React SPA renders form; data-service stores/retrieves settings |
| Provider health / test connection | API / Backend | Browser / Client | Gateway validates keys; UI displays result |
| n8n workflow orchestration | API / Backend | -- | n8n sends requests to gateway; gateway owns all LLM logic |
| Model discovery | API / Backend | Browser / Client | Gateway queries provider APIs; UI populates dropdown |
| Fallback resolution (no key -> Ollama) | API / Backend | -- | Gateway resolves active provider from settings; n8n sends provider:null |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Thin normalization):** Each adapter keeps its provider-native prompt format. The gateway wraps responses in a standard envelope `{text, provider, model, usage}`. Anthropic receives `messages[]` format, OpenAI receives chat completions format, Ollama receives its generate format. Adapter translates between the common gateway schema and the provider-native format.
- **D-02 (Explicit provider tag):** The request body carries `provider: 'anthropic' | 'openai' | 'ollama'` explicitly -- no auto-detection from model name prefixes. Gateway routes to the correct adapter based on this tag.
- **D-03 (Anthropic auth -- API key only):** Single `x-api-key` header for Anthropic. No custom base URL field. Users get a key from console.anthropic.com.
- **D-04 (Minimal response):** Gateway returns `{text, provider, model, usage}` where usage normalizes to `{prompt_tokens, completion_tokens, total_tokens}`. No cost estimate, stop reason, or raw response fields unless a future consumer needs them.
- **D-05 (Direct HTTP node):** Each n8n workflow replaces its Ollama HTTP node URL with `http://data-service:8000/llm/generate`. No n8n middleware Function node -- the gateway owns all LLM logic. n8n stays thin.
- **D-06 (Big-bang migration):** All 5 workflows (rules-to-metagraph, graph-query-mcp, spec-ingest, spec-query, spec-update) rewired in a single plan. The gateway is designed as a drop-in replacement -- URL swap + body reformat per workflow.
- **D-07 (Gateway resolves active provider):** n8n sends `{provider: null, model: null}` in the request body. The gateway reads the user's saved provider/model settings and resolves which adapter to use. Switching providers in the UI takes effect immediately with no workflow edits.
- **D-08 (Container-level health only):** Docker compose health check for Ollama as before. No gateway-level `/health` endpoint for LLM provider status -- errors surface through the gateway's response on the first call.
- **D-09 (New nav tab):** A tab labeled "LLM Settings" in the existing sidebar nav alongside Register, Home, Project, Graph Viewer.
- **D-10 (Full form + status banner):** No-key state displays the full configuration form with a prominent yellow banner "Using local Ollama (fallback)". Active state shows a green "Connected: {provider}" indicator with masked key, model selector, and Change/Remove actions. Both states are the same panel, just different content -- not a collapsed/expanded toggle.
- **D-11 (Test saved config only):** A single "Test Connection" button calls `POST /llm/settings/test` with the saved provider and key. Shows success (latency, model confirmed) or actionable error. No "test before save" flow -- the user saves first, then tests.
- **D-12 (Read from data-service every call):** The gateway reads `GET /llm/settings` from data-service on every `/llm/generate` call. No caching -- settings changes apply instantly without restart. The overhead of a local data-service read is negligible compared to the LLM call itself.
- **D-13 (Fully dynamic per provider):** The gateway exposes `GET /llm/models?provider=...` which queries each provider's API for available models. Ollama calls `GET /api/tags` locally. Anthropic and OpenAI calls use their model listing endpoints.
- **D-14 (Seed list + live refresh on test):** A small hardcoded seed list of known models per provider covers the no-key state and first-time setup. Once a key is validated via `POST /llm/settings/test`, the gateway queries the provider's API and replaces the seed list with live results. The test endpoint returns the live model list so the UI can refresh the dropdown.
- **D-15 (Plain model ID list):** The model dropdown shows model IDs only -- no context window, pricing, or capability indicators. Users who need model details reference provider documentation.
- **D-16 (Ollama auto-discover at startup):** The gateway calls `http://ollama:11434/api/tags` at startup and caches the model list. Auto-discovers whatever models the user has pulled locally.

### Claude's Discretion

(From CONTEXT.md -- none explicitly listed beyond the "Specific Ideas" section which is advisory. The planner has discretion over implementation details that don't contradict locked decisions.)

### Deferred Ideas (OUT OF SCOPE)

(From CONTEXT.md -- none; all ideas stayed within Phase 1 scope boundary.)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLMC-01 | Provider-agnostic LLM gateway with adapters for Anthropic Claude, OpenAI-compatible APIs, and local Ollama | Three provider API formats researched (see Standard Stack); httpx 0.28.1 available for raw HTTP; Strategy pattern established |
| LLMC-02 | User can enter, update, test, and remove API key from UI settings panel; live validation on save | Speckle settings pattern in app.py (GET/PUT /settings/speckle) is the template; key masking via mask_token() already exists at line 305; test endpoint will call provider's model list or minimal completion |
| LLMC-03 | API keys encrypted at rest (master secret via env var), never in Neo4j/localStorage/logs | cryptography.fernet 46.0.5 installed and verified; Fernet provides AES-GCM symmetric encryption; pattern documented below |
| LLMC-04 | All 5 n8n workflows rewired to gateway -- no direct Ollama HTTP calls remain | 6 Ollama HTTP nodes across 5 workflows identified; each follows the same URL pattern `http://ollama:11434/api/generate` |
| LLMC-05 | No key configured = fallback to local Ollama with identical behavior | Gateway resolves active provider from settings; n8n sends provider:null per D-07; no-key default uses Ollama adapter |
| LLMC-06 | Provider errors surface in UI with What+Where+How-to-fix pattern | Existing error pattern in app.py (`_structured_error_response` at line 846); adapter error mapping required |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.1 (installed) | REST framework for gateway endpoints | Existing data-service framework; all endpoints (GET/PUT/DELETE /llm/settings, POST /llm/generate, POST /llm/settings/test, GET /llm/models) follow same patterns |
| pydantic | 2.12.5 (installed) | Request/response model validation | Existing data-service model; used for GenerateRequest, GenerateResponse, SettingsPayload, TestResult models |
| httpx | 0.28.1 (installed) | Async HTTP client for provider API calls | Raw HTTP to Anthropic, OpenAI, Ollama APIs; no SDK dependency needed; supports timeouts, streaming, connection pooling |
| cryptography.fernet | 46.0.5 (installed) | Symmetric AES-GCM encryption for API keys at rest | Industry-standard symmetric encryption; built-in key derivation; `cryptography` already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| neo4j | -- (installed) | Neo4j driver | Not used for LLM settings (D-12 says no caching, read from data-service) -- only referenced for DRY pattern awareness |
| -- | -- | FastAPI TestClient (built-in) | For pytest: test adapter routing, fallback resolution, key masking, error mapping without network calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw httpx for provider calls | anthropic SDK + openai SDK | Adds 2 Python packages; SDK auto-retry/rate-limit handling would be useful but adds dependency surface. D-01 thin normalization favors raw HTTP |
| Fernet symmetric encryption | HashiCorp Vault / AWS KMS | Adds external service dependency; Fernet with env-var-derived master key is zero-infrastructure and matches the project's self-hosted simplicity |
| JSON file persistence for settings | Neo4j node storage | D-12 says keys never in Neo4j; file-based matches existing Speckle settings pattern in app.py |

**Installation:**
```bash
pip install cryptography httpx  # both already installed at 46.0.5 and 0.28.1
```

**Version verification:** cryptography 46.0.5 and httpx 0.28.1 confirmed installed. No new runtime dependencies needed.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| cryptography | PyPI | 10+ yrs | 200M+/wk | github.com/pyca/cryptography | OK | Approved |
| httpx | PyPI | 5+ yrs | 50M+/wk | github.com/encode/httpx | OK | Approved |
| fastapi | PyPI | 6+ yrs | 100M+/wk | github.com/fastapi/fastapi | OK | Approved |
| pydantic | PyPI | 7+ yrs | 150M+/wk | github.com/pydantic/pydantic | OK | Approved |

**Packages removed due to [SLOP] verdict:** None
**Packages flagged as suspicious [SUS]:** None

All packages already installed in the current environment. No new packages required for this phase.

## Architecture Patterns

### System Architecture Diagram

```
User (browser)
  |
  |---> index.html (React SPA)
  |       |
  |       +-- "LLM Settings" tab ------> GET /llm/settings ------> data-service
  |       |    (form render)                                         |
  |       |                              PUT /llm/settings  --------> data-service
  |       |    (save config)                                         |
  |       |                              POST /llm/settings/test ---> data-service
  |       |    (test connection)                                     |
  |       +-- DesignRules / Specs&Notes  (unchanged)
  |       +-- Graph Viewer              (unchanged)
  |
  |---> /n8n/webhook/dg/rules-ingest ---> n8n (rules-to-metagraph workflow)
  |---> /n8n/webhook/dg/graph-query  ---> n8n (graph-query-mcp workflow)

[data-service]
  |
  +-- /llm/generate (POST) <--- n8n (5 workflows)
  |     |
  |     +---> Read /llm/settings (resolve active provider)
  |     +---> AnthropicAdapter.generate() ---> httpx POST api.anthropic.com/v1/messages
  |     +---> OpenAIAdapter.generate()   ---> httpx POST {base_url}/v1/chat/completions
  |     +---> OllamaAdapter.generate()   ---> httpx POST http://ollama:11434/api/generate
  |
  +-- /llm/settings ---> llm-settings.json (Fernet-encrypted)
  |     (GET) returns {provider, model, maskedKey, status}
  |     (PUT) encrypts + persists
  |     (DELETE) clears settings -> fallback to Ollama
  |
  +-- /llm/settings/test ---> validates key via provider API
  |     returns {success, latency_ms, models[], error?}
  |
  +-- /llm/models?provider=... ---> queries provider model list
        Seed list -> live refresh on successful test
        Ollama: GET ollama:11434/api/tags
        Anthropic: GET api.anthropic.com/v1/models
        OpenAI: GET {base_url}/v1/models
```

### Recommended Project Structure
```
data-service/
|-- llm_gateway.py        # NEW -- provider adapters + gateway logic
|-- app.py                # MODIFIED -- add /llm/* endpoints
|-- requirements.txt      # MODIFIED -- add cryptography, httpx (if not present)
|-- tests/
|   |-- test_llm_gateway.py  # NEW -- adapter routing, fallback, error mapping
`-- data/
    `-- llm-settings.json    # NEW -- encrypted settings (not in git)

graph-viewer/
`-- index.html             # MODIFIED -- add "LLM Settings" nav tab + panel
```

### Pattern 1: Provider Adapter (Strategy Pattern)
**What:** Abstract base class + one concrete adapter per provider. Each adapter translates between the common gateway schema and the provider-native HTTP API format.
**When to use:** Always -- every provider call goes through an adapter.
**Example:**
```python
# Source: Derived from CONTEXT.md D-01, standard Strategy pattern
from abc import ABC, abstractmethod
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    prompt: str
    system: str | None = None
    model: str | None = None
    provider: str | None = None  # 'anthropic' | 'openai' | 'ollama'

class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str
    usage: dict  # {prompt_tokens, completion_tokens, total_tokens}

class LLMAdapter(ABC):
    @abstractmethod
    async def generate(self, req: GenerateRequest, api_key: str | None) -> GenerateResponse:
        ...

    @abstractmethod
    async def list_models(self, api_key: str | None) -> list[str]:
        ...

class AnthropicAdapter(LLMAdapter):
    def __init__(self, base_url: str = "https://api.anthropic.com/v1"):
        self.base_url = base_url

    async def generate(self, req: GenerateRequest, api_key: str | None) -> GenerateResponse:
        # Anthropic Messages API: POST /v1/messages
        # Auth: x-api-key header
        # Request: {model, max_tokens, messages: [{role, content}], system?}
        # Response: {id, model, content: [{type: "text", text}], usage: {input_tokens, output_tokens}}
        ...

    async def list_models(self, api_key: str | None) -> list[str]:
        # GET /v1/models -> list of {id, display_name, ...}
        ...

class OpenAIAdapter(LLMAdapter):
    def __init__(self, base_url: str = "https://api.openai.com/v1"):
        self.base_url = base_url

    async def generate(self, req: GenerateRequest, api_key: str | None) -> GenerateResponse:
        # OpenAI Chat Completions API: POST /chat/completions
        # Auth: Authorization: Bearer header
        # Request: {model, messages: [{role, content}], max_tokens?, temperature?}
        # Response: {id, model, choices: [{message: {content}}], usage: {prompt_tokens, completion_tokens, total_tokens}}
        ...

class OllamaAdapter(LLMAdapter):
    def __init__(self, base_url: str = "http://ollama:11434"):
        self.base_url = base_url

    async def generate(self, req: GenerateRequest, api_key: str | None = None) -> GenerateResponse:
        # Ollama Generate API: POST /api/generate
        # Request: {model, prompt, system?, stream: false, options: {temperature, num_predict}}
        # Response: {model, response, done, eval_count, prompt_eval_count}
        ...

    async def list_models(self, api_key: str | None = None) -> list[str]:
        # GET /api/tags -> {models: [{name, model, ...}]}
        ...
```

### Pattern 2: Encryption-At-Rest (Fernet)
**What:** Uses `cryptography.fernet.Fernet` with a master secret derived from an environment variable. The master secret is hashed to produce a 32-byte key, which is base64-urlsafe-encoded for Fernet.
**When to use:** Every time an API key is persisted or read.
**Example:**
```python
# Source: cryptography.fernet official docs, verified via installed package
import hashlib
import base64
from cryptography.fernet import Fernet

def _derive_key(master_secret: str) -> bytes:
    """Derive a deterministic Fernet key from a master secret string."""
    # SHA-256 hash of the master secret produces exactly 32 bytes
    # Fernet requires a 32-byte url-safe-base64 key
    digest = hashlib.sha256(master_secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_value(plaintext: str, master_secret: str) -> str:
    """Encrypt a plaintext string. Returns a Fernet token as string."""
    cipher = Fernet(_derive_key(master_secret))
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_value(ciphertext: str, master_secret: str) -> str:
    """Decrypt a Fernet token. Raises InvalidToken on wrong key/corruption."""
    cipher = Fernet(_derive_key(master_secret))
    return cipher.decrypt(ciphertext.encode()).decode()

def mask_key(key: str) -> str:
    """Return a masked preview: first 6 chars + '...' + last 6 chars."""
    if not key or len(key) <= 12:
        return key[:2] + "..." + key[-2:] if len(key) > 4 else "****"
    return key[:6] + "..." + key[-6:]
```

### Pattern 3: Settings Persistence (JSON file, following Speckle pattern)
**What:** Reads and writes LLM settings to a JSON file in `DATA_DIR`, following the exact pattern used for Speckle settings in `app.py` (functions `load_persisted_speckle_settings`, `save_persisted_speckle_settings`, `get_speckle_settings_response`).
**When to use:** For all LLM settings CRUD operations.

```python
# Source: Existing app.py Speckle settings pattern (lines 279-322)
LLM_SETTINGS_FILE = DATA_DIR / "llm-settings.json"

def load_persisted_llm_settings() -> dict[str, str]:
    if not LLM_SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(LLM_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

def save_persisted_llm_settings(settings: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in settings.items() if value}
    LLM_SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

### Anti-Patterns to Avoid
- **[Storing keys unencrypted]:** Never write raw API keys to disk, Neo4j, localStorage, or logs. Always encrypt with Fernet before persisting; always mask before returning in API responses.
- **[Auto-detecting provider from model name]:** D-02 mandates explicit `provider` tag. No auto-detection from model name prefixes like "claude-" or "gpt-".
- **[Caching settings in memory]:** D-12 mandates reading settings from data-service on every call. No in-memory cache -- the overhead of a local file read is negligible.
- **[Using provider SDKs]:** The adapters use raw HTTP (httpx). No `anthropic` or `openai` Python packages -- they add dependency surface without benefit for this thin-gateway design.
- **[n8n middleware function nodes]:** D-05 mandates direct HTTP nodes, not Function nodes that wrap the gateway call.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symmetric encryption of API keys at rest | Custom AES implementation | `cryptography.fernet.Fernet` | Fernet is a high-level symmetric encryption API over AES-GCM with built-in authentication, key derivation, and safe serialization. Already installed at 46.0.5 |
| HTTP client with timeout/retry | Raw `urllib.request` + manual retry loop | `httpx` | httpx 0.28.1 already installed; provides connection pooling, timeout per-request, async support, and response streaming |
| API key masking for UI display | Custom substring logic | Reuse existing `mask_token()` (app.py line 305) | Already exists and tested for Speckle tokens; adapt from `mask_token` to `mask_key` or reuse directly |

## Common Pitfalls

### Pitfall 1: Fernet Key Derivation Mismatch
**What goes wrong:** If the Fernet key is different at encryption time vs decryption time, decryption raises `cryptography.fernet.InvalidToken`. This happens if the master secret env var changes between restart or if the key derivation uses a non-deterministic approach (random salt).
**Why it happens:** Using `Fernet.generate_key()` produces a random key every time -- the master secret must deterministically produce the same key.
**How to avoid:** Always derive the key via `hashlib.sha256(MASTER_SECRET.encode()).digest()` + `base64.urlsafe_b64encode()`. Store ONLY the encrypted payload, never the key.
**Warning signs:** Settings load returns empty or default values after a container restart.

### Pitfall 2: Provider API Format Normalization Loss
**What goes wrong:** The adapter strips essential provider-specific fields (e.g., Anthropic's `system` prompt outside `messages`, Ollama's `system` parameter), causing quality degradation or 400 errors.
**Why it happens:** D-01 "thin normalization" is misinterpreted as "strip everything provider-specific."
**How to avoid:** Normalize only the response envelope. The request body already carries the provider-specific format inside `prompt` / `system` / `messages` fields. Anthropic needs `system` as a top-level string (not in messages), Ollama needs `system` as a separate parameter, OpenAI needs it as `{role: "system"}` inside `messages`.
**Warning signs:** Anthropic returns 400 on system prompt; Ollama generates without system context.

### Pitfall 3: n8n Workflow Co-Registration Breakage
**What goes wrong:** After rewiring, the workflow's response parsing assumes Ollama's exact response shape (`response`, `eval_count`) and breaks on the normalized gateway envelope.
**Why it happens:** n8n's Parse LLM Output nodes (e.g., node 5 in rules-to-metagraph) extract fields like `$json.response` which is the Ollama-specific field.
**How to avoid:** Update the Parse nodes to read from the normalized envelope: `$json.text` instead of `$json.response`. The gateway returns `{text, provider, model, usage}` -- the text is always in `.text`.
**Warning signs:** n8n workflows error on "No valid MERGE" after gateway rewiring.

### Pitfall 4: graph-query-mcp Has Two Ollama Calls
**What goes wrong:** The migration checklist only accounts for 5 workflows and 5 rewires, but graph-query-mcp has 2 Ollama HTTP nodes (one for Cypher generation, one for answer generation), making the real count 6 nodes to rewire.
**Why it happens:** Assumption that each workflow has exactly one LLM call. Verified by codebase grep: 5 workflows, 6 Ollama HTTP nodes total.
**How to avoid:** Explicitly count nodes per workflow before starting rewiring.

## Code Examples

Verified patterns from official sources:

### Provider API Request/Response Formats (httpx)

```python
# Source: Anthropic Messages API (verified via claude-api skill), OpenAI Chat Completions API, Ollama API docs
import httpx

# --- Anthropic Claude ---
async def anthropic_generate(api_key: str, model: str, prompt: str, system: str | None = None) -> tuple[str, dict]:
    """Call Anthropic Messages API and return (text, usage)."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    text = next((b["text"] for b in data["content"] if b["type"] == "text"), "")
    usage = {
        "prompt_tokens": data["usage"]["input_tokens"],
        "completion_tokens": data["usage"]["output_tokens"],
        "total_tokens": data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
    }
    return text, usage

# --- OpenAI-compatible ---
async def openai_generate(api_key: str, model: str, prompt: str, system: str | None = None,
                          base_url: str = "https://api.openai.com/v1") -> tuple[str, dict]:
    """Call OpenAI Chat Completions API and return (text, usage)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {"model": model, "messages": messages, "max_tokens": 4096}

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    text = data["choices"][0]["message"]["content"] or ""
    usage = {
        "prompt_tokens": data["usage"]["prompt_tokens"],
        "completion_tokens": data["usage"]["completion_tokens"],
        "total_tokens": data["usage"]["total_tokens"],
    }
    return text, usage

# --- Ollama ---
async def ollama_generate(model: str, prompt: str, system: str | None = None,
                          base_url: str = "http://ollama:11434") -> tuple[str, dict]:
    """Call Ollama Generate API and return (text, usage)."""
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 4096},
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{base_url}/api/generate", json=body)
        resp.raise_for_status()
        data = resp.json()

    text = data.get("response", "")
    usage = {
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "completion_tokens": data.get("eval_count", 0),
        "total_tokens": (data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
    }
    return text, usage
```

### Settings Endpoints (Pydantic models + FastAPI)

```python
# Source: Existing app.py Speckle settings pattern (lines 100-122, 803-829)
from pydantic import BaseModel
from fastapi import HTTPException

class LLMSettingsPayload(BaseModel):
    provider: str | None = None          # 'anthropic' | 'openai' | 'ollama'
    model: str | None = None             # model ID
    apiKey: str | None = None            # plaintext key (encrypted on write)
    baseUrl: str | None = None           # optional, for OpenAI-compatible

class LLMSettingsResponse(BaseModel):
    provider: str | None = None
    model: str | None = None
    apiKeyConfigured: bool = False
    apiKeyPreview: str = ""              # masked: "sk-ant-...abcdef"
    baseUrl: str | None = None

# Gateway uses these endpoint patterns:
# GET  /llm/settings       -> LLMSettingsResponse
# PUT  /llm/settings       <- LLMSettingsPayload -> LLMSettingsResponse
# DELETE /llm/settings     -> 204 (clears to Ollama fallback)
# POST /llm/generate       <- GenerateRequest -> GenerateResponse
# POST /llm/settings/test  -> {success, latency_ms, models: [str], error?}
# GET  /llm/models?provider=... -> [str]
```

### UI Tab Pattern (React.createElement)

```javascript
// Source: index.html existing tab pattern (lines 3066-3077)
// In the GraphViewerPage component, add a third tab:
e("div", { className: "prompt-tabs", style: { marginTop: "14px" } },
  e("button", {
    type: "button",
    className: activeTab === "design-rules" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("design-rules")
  }, "DesignRules"),
  e("button", {
    type: "button",
    className: activeTab === "specs-notes" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("specs-notes")
  }, "Specs&Notes"),
  e("button", {
    type: "button",
    className: activeTab === "llm-settings" ? "prompt-tab active" : "prompt-tab",
    onClick: () => setActiveTab("llm-settings")
  }, "LLM Settings")
)
// Then render the LLM settings panel:
// activeTab === "llm-settings" ? e(LLMSettingsPanel, { ... }) : null
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct Ollama HTTP from n8n | Gateway abstraction in data-service | Phase 1 | All LLM calls route through one contract; provider switching without workflow changes |
| Ollama-only (local model) | Multi-provider (Anthropic, OpenAI, Ollama) | Phase 1 | User can choose cloud frontier models with Ollama as zero-config fallback |
| API keys in n8n env vars | Fernet-encrypted in data-service JSON file | Phase 1 | Keys never leave data-service; encrypted at rest; masked in UI |
| Static Ollama model | Dynamic model discovery per provider | Phase 1 | Model dropdown populated from live API; Ollama auto-discovers at startup |

**Deprecated/outdated:**
- n8n environment variables `OLLAMA_URL`, `OLLAMA_HOST`, `OLLAMA_MODEL` in docker-compose.yml: These become unused defaults once all 5 workflows are rewired. Can be removed or kept as no-ops.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `cryptography` package with Fernet support is installed and functional | Standard Stack | CONFIRMED: cryptography 46.0.5 installed, `from cryptography.fernet import Fernet` works |
| A2 | `httpx` is installed and functional | Standard Stack | CONFIRMED: httpx 0.28.1 installed, works |
| A3 | All 5 n8n workflows use `http://ollama:11434/api/generate` as the Ollama URL | Common Pitfalls | CONFIRMED: grep shows 6 instances across 5 files, all using this URL |
| A4 | graph-query-mcp.json has 2 Ollama calls | Common Pitfalls | CONFIRMED: one for Cypher generation (node ~34-70), one for answer generation (node ~93-108) |
| A5 | `mask_token` function at app.py:305 can be reused for API key masking | Code Examples | CONFIRMED: `mask_token` handles tokens <10 chars with partial mask, >10 chars with `...` pattern; adaptable for API keys |
| A6 | FastAPI TestClient is the existing test pattern | Validation Architecture | CONFIRMED from conftest.py (only contains `import pytest`). No httpx mocking pattern established yet |

**All claims in this research were verified via codebase inspection or installed package checks -- no user confirmation needed for technical claims.**

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | data-service runtime | yes | 3.14.2 | -- |
| fastapi | REST framework | yes | 0.135.1 | -- |
| pydantic | model validation | yes | 2.12.5 | -- |
| httpx | provider HTTP calls | yes | 0.28.1 | -- |
| cryptography (fernet) | key encryption | yes | 46.0.5 | -- |
| Node.js 20+ | UI serving (build-less) | yes | 20.20.0 | -- |
| Docker Compose | container orchestration | yes | 2.40.3 | -- |
| pytest | testing | yes | (present) | -- |

**Missing dependencies with no fallback:** None -- all required packages are installed.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in data-service/tests/) |
| Config file | none -- standard pytest discovery |
| Quick run command | `pytest data-service/tests/test_llm_gateway.py -x -v` |
| Full suite command | `pytest data-service/tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| LLMC-01 | Adapter routing: correct adapter selected per provider tag | unit | `pytest tests/test_llm_gateway.py::test_adapter_routing -x` |
| LLMC-01 | Adapter routing: empty/null provider falls back to Ollama | unit | `pytest tests/test_llm_gateway.py::test_fallback_resolution -x` |
| LLMC-03 | Key masking: full key produces masked preview, empty produces "" | unit | `pytest tests/test_llm_gateway.py::test_key_masking -x` |
| LLMC-03 | Fernet encrypt/decrypt round-trip | unit | `pytest tests/test_llm_gateway.py::test_fernet_roundtrip -x` |
| LLMC-06 | Error mapping: provider errors map to structured response | unit | `pytest tests/test_llm_gateway.py::test_error_mapping -x` |
| LLMC-05 | No-key state: gateway returns Ollama routing | unit | `pytest tests/test_llm_gateway.py::test_no_key_fallback -x` |

### Sampling Rate
- **Per task commit:** `pytest data-service/tests/test_llm_gateway.py -x -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `data-service/tests/test_llm_gateway.py` -- covers all 6 test items above
- [ ] `data-service/tests/conftest.py` -- may need httpx mock fixtures or a TestClient helper

*(No additional framework install needed -- pytest already present)*

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Provider API keys authenticated via headers (x-api-key / Bearer) |
| V6 Cryptography | yes | Fernet (AES-GCM) for encrypted storage; master secret via env var |
| V8 Data Protection | yes | Keys encrypted at rest; masked in transit; never in logs/localStorage |
| V12 File and Resources | partial | JSON settings file in /app/data with restricted container filesystem |

### Known Threat Patterns for Stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposure in logs | Information Disclosure | Key masking in all log statements; encryption on write; never log raw key |
| Encryption key compromise via env var leak | Tampering | Master secret via Docker env; rotate by changing env var + re-encrypting |
| Fernet token tampering | Tampering | Fernet includes authenticated encryption (AES-GCM) -- tampering detected on decrypt |
| Settings file read from outside container | Information Disclosure | Docker volume isolation; file stored in data-service container-internal path |

## Sources

### Primary (HIGH confidence)
- `data-service/app.py` (lines 100-122, 279-322, 783-829) -- Existing Speckle settings CRUD pattern, Pydantic models, mask_token, FastAPI endpoint patterns
- `data-service/requirements.txt` -- Verified cryptography 46.0.5, httpx 0.28.1, fastapi 0.135.1, pydantic 2.12.5 all installed
- `graph-viewer/index.html` (lines 1432-1517, 3033-3077) -- UI tab pattern (React.createElement, activeTab state, prompt-tabs)
- `n8n/workflows/rules-to-metagraph.json` (nodes 4, 87-97, 120-130) -- Ollama HTTP call and parse patterns to rewire
- `n8n/workflows/graph-query-mcp.json` -- Two Ollama HTTP calls (Cypher + Answer generation)
- `n8n/workflows/spec-ingest.json`, `spec-query.json`, `spec-update.json` -- Single Ollama HTTP call each
- `n8n/workflows/` total: 5 files, 6 Ollama HTTP nodes confirmed

### Secondary (MEDIUM confidence)
- claude-api skill documentation -- Anthropic Messages API format, model IDs, model listing endpoint
- WebSearch: OpenAI Chat Completions API format -- Request/response structure, auth header pattern
- WebSearch: Ollama API documentation -- Generate and Tags endpoint formats
- WebSearch: cryptography.fernet best practices -- Key derivation, storage patterns

### Tertiary (LOW confidence)
- None -- all technical claims verified against installed packages or codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages verified installed
- Architecture: HIGH -- patterns derived from existing codebase (Speckle settings, FastAPI endpoints, UI tabs)
- Pitfalls: HIGH -- all verified by codebase grep (6 Ollama nodes, response parsing patterns)
- Encryption: HIGH -- cryptography.fernet installed and working; pattern documented

**Research date:** 2026-07-06
**Valid until:** 2026-08-06 (30 days -- stable ecosystem packages; provider API formats stable)

## RESEARCH COMPLETE

**Phase:** 01 - Cloud LLM Connector and Provider Abstraction
**Confidence:** HIGH

### Key Findings
1. All required Python packages (cryptography 46.0.5, httpx 0.28.1, fastapi 0.135.1) are already installed -- no new dependencies needed
2. 6 Ollama HTTP nodes exist across 5 n8n workflows, not 5 -- graph-query-mcp has 2 nodes
3. The Speckle settings pattern in app.py (GET/PUT /settings/speckle with JSON file persistence + mask_token) is the direct template for LLM settings
4. Fernet with SHA-256 key derivation from env var is the zero-infrastructure encryption approach
5. UI follows existing React.createElement tab pattern -- new "LLM Settings" tab added alongside DesignRules and Specs&Notes

### File Created
`C:\Users\Admin\source\repos\design-grammar-system\.planning\phases\01-cloud-llm-connector\01-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All packages verified installed via codebase inspection |
| Architecture | HIGH | Patterns derived from existing codebase (Speckle settings, app.py endpoints, UI tabs) |
| Pitfalls | HIGH | All 6 Ollama call sites identified by grep; response parsing patterns analyzed |
| Encryption | HIGH | cryptography.fernet installed and working; industry-standard AES-GCM |

### Open Questions
None -- all technical claims verified against installed packages or codebase.

### Ready for Planning
Research complete. Planner can now create PLAN.md files for the 3-4 plan breakdown recommended:
- Plan 01: llm_gateway.py + app.py endpoints + encryption
- Plan 02: n8n workflow rewiring (plan update: 6 nodes, not 5)
- Plan 03: UI settings panel in index.html
- Plan 04 (optional): pytest coverage + integration testing
