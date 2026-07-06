---
phase: 01-cloud-llm-connector
verified: 2026-07-06T12:00:00Z
status: human_needed
score: 6/7 must-haves verified
behavior_unverified: 1
overrides_applied: 0
gaps: []
behavior_unverified_items:
  - truth: "Provider switching takes immediate effect without restart (E2E: n8n webhook -> gateway -> provider API -> response -> Neo4j)"
    test: "Run the full Docker stack, configure an Anthropic API key in the UI, submit a rule through the n8n webhook, verify a graph is written. Then switch provider to Ollama (no key), resubmit, verify it works without restart."
    expected: "Rules submitted through n8n webhook route through the gateway to the configured provider. Switching provider dropdown in UI and resubmitting works immediately without any container restart."
    why_human: "Requires running Docker stack with n8n, data-service, Neo4j, and provider API connectivity. Unit tests verify the routing mechanism; E2E provider switching behavior cannot be verified by static analysis."
human_verification:
  - test: "End-to-end provider switching without restart"
    expected: "Configure Anthropic key in UI, submit rule through n8n webhook, verify graph appears in Neo4j. Switch provider dropdown to Ollama, resubmit, verify it works without restart. The gateway reads settings fresh every call (D-12) and n8n sends provider:null (D-07) for the gateway to resolve."
    why_human: "Requires running Docker stack with all services. The code is present and wired (unit-tested adapter routing, gateway reads settings per call, n8n workflows rewired), but the full E2E flow cannot be verified by static analysis."
---

# Phase 01: Cloud LLM Connector and Provider Abstraction — Verification Report

**Phase Goal:** Build a provider-agnostic LLM gateway in data-service (POST /llm/generate) with adapters for Anthropic Claude, OpenAI-compatible APIs, and local Ollama — replacing 5 direct Ollama HTTP calls from n8n workflows — plus encrypted key storage (GET/PUT/DELETE /llm/settings, POST /llm/settings/test, GET /llm/models) and a UI settings panel (new nav tab in graph-viewer/index.html) for provider/model/key management.

**Verified:** 2026-07-06
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Provider-agnostic LLM gateway with 3 adapters (Anthropic, OpenAI, Ollama), explicit provider tag, normalized response envelope (LLMC-01) | VERIFIED | `data-service/llm_gateway.py` — LLMAdapter ABC, AnthropicAdapter, OpenAIAdapter, OllamaAdapter, get_adapter factory, GenerateRequest/GenerateResponse. Test: `test_adapter_routing` (30/30 tests pass). |
| 2 | User can enter, update, test, and remove API key from UI settings panel (LLMC-02) | VERIFIED | `graph-viewer/index.html` — LLMSettingsPanel with fetchModels, saveSettings (PUT), testConnection (POST), deleteSettings (DELETE). Provider dropdown, model dropdown, password-masked input. |
| 3 | API keys encrypted at rest with Fernet AES-GCM, masked in UI, never in logs/localStorage (LLMC-03) | VERIFIED | `llm_gateway.py` — encrypt_value/decrypt_value with SHA-256 key derivation, mask_key(). Test: `test_fernet_roundtrip`, `test_key_masking`. No localStorage.setItem for API keys in index.html. No raw apiKey in log statements. |
| 4 | All 5 n8n workflows (6 HTTP nodes) rewired to gateway — no direct Ollama HTTP calls remain (LLMC-04) | VERIFIED | `grep -r "ollama:11434" n8n/workflows/` returns 0. `grep -r "data-service:8000/llm/generate" n8n/workflows/` returns 6 matches across 5 files. All 5 JSON files valid. Response parsing uses `$json.text` not `$json.response`. |
| 5 | No key configured = Ollama fallback with identical behavior (LLMC-05) | VERIFIED | `resolve_active_provider()` returns `("ollama", None, None)` when no key/settings. Tests: `test_fallback_resolution`, `test_no_key_fallback`. Each workflow sends `provider: null, model: null` per D-07. |
| 6 | Provider errors map to structured {error, hint, code} with What+Where+How-to-fix, no key leakage (LLMC-06) | VERIFIED | `map_provider_error()` in llm_gateway.py. `_structured_error_response()` in app.py. Tests: `test_error_mapping`, `test_error_response_shape`. UI error display parses the structured response. |
| 7 | Provider switching takes effect without restart (E2E: n8n webhook -> gateway -> provider API) | PRESENT_BEHAVIOR_UNVERIFIED | Mechanism verified: D-12 (settings read fresh every call via load_persisted_llm_settings()), D-07 (n8n sends provider:null, gateway resolves from settings via resolve_active_provider()). Full E2E needs live Docker to exercise. |

**Score:** 6/7 truths verified (1 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `data-service/llm_gateway.py` | Provider adapters, encryption, settings, models, error mapping | VERIFIED | 618 lines, all symbols present (5 Pydantic models, 3 adapters, 6 utility functions). No stubs. |
| `data-service/app.py` — 6 endpoints | GET/PUT/DELETE /llm/settings, POST /llm/generate, POST /llm/settings/test, GET /llm/models | VERIFIED | All 6 endpoints present at lines 858-974. Properly wired to llm_gateway functions. Structured error handling. |
| `docker-compose.yml` | LLM_MASTER_SECRET env var on data-service | VERIFIED | Line 34: `LLM_MASTER_SECRET: ${LLM_MASTER_SECRET:-change-me-to-a-random-secret}` |
| `data-service/requirements.txt` | cryptography, httpx | VERIFIED | `cryptography`, `httpx` listed alphabetically alongside fastapi |
| `data-service/tests/test_llm_gateway.py` | 14+ tests covering key masking, Fernet, routing, fallback, settings CRUD, error mapping, models | VERIFIED | 500 lines, 30 tests across 10 test classes/functions. All pass. |
| `n8n/workflows/` (5 files) | All HTTP nodes rewired to gateway | VERIFIED | 0 `ollama:11434` references. 6 `data-service:8000/llm/generate` references. All 5 files valid JSON. |
| `graph-viewer/index.html` | LLMSettingsPanel component, routing, nav tile, CSS | VERIFIED | 399 lines added. Component defined at line 3991. `handleOpenLLMSettings` at line 4337. `page === "llm-settings"` routing at line 4359. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| LLMSettingsPanel (UI) | GET /llm/settings | fetch() on mount (line 4123) | WIRED | Fetches current settings; populates form and model dropdown |
| LLMSettingsPanel (UI) | PUT /llm/settings | fetch() in saveSettings (line 4031) | WIRED | Encrypts apiKey server-side; returns masked preview |
| LLMSettingsPanel (UI) | DELETE /llm/settings | fetch() in deleteSettings (line 4058) | WIRED | Returns 204; resets to Ollama fallback |
| LLMSettingsPanel (UI) | POST /llm/settings/test | fetch() in testConnection (line 4077) | WIRED | Tests saved config only; returns latency + model list |
| LLMSettingsPanel (UI) | GET /llm/models | fetch() in fetchModels (line 4012) | WIRED | Populates model dropdown; seed initially, live on test |
| n8n HTTP nodes (5 workflows) | POST /llm/generate | 6 HTTP nodes with URL data-service:8000/llm/generate | WIRED | Each sends `provider: null, model: null` per D-07 |
| POST /llm/generate | resolve_active_provider | load_persisted_llm_settings() on every call (app.py line 905) | WIRED | No caching per D-12 — settings changes apply instantly |
| encrypt_value / decrypt_value | Fernet key derivation | `_derive_key()` via SHA-256 (line 345) | WIRED | Deterministic — same secret produces same key across restarts |
| map_provider_error | _structured_error_response | POST /llm/generate catch block (app.py line 927-928) | WIRED | Maps httpx errors to {error, hint, code}; never leaks key/URL |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| POST /llm/generate | settings dict | `load_persisted_llm_settings()` reads JSON file | YES — reads from persisted file on every call | FLOWING |
| POST /llm/generate | provider/model/api_key | `resolve_active_provider()` decrypts settings | YES — real decryption or Ollama fallback | FLOWING |
| POST /llm/settings | apiKey | `encrypt_value()` on write, `decrypt_value()` on read | YES — Fernet AES-GCM round-trip | FLOWING |
| GET /llm/models | model list | `list_models_for_provider()` — live API or seed | YES — live API query with key, seed fallback without | FLOWING |
| LLMSettingsPanel (UI) | settings + models | fetch() from /llm/settings + /llm/models | YES — real JSON responses from data-service | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Module imports without errors | `python -c "from llm_gateway import *"` | No import errors | PASS |
| mask_key produces correct output | `mask_key('sk-ant-abcdefghijklmnop')` | `'sk-ant...klmnop'` | PASS |
| Fernet encrypt/decrypt round-trip | `decrypt_value(encrypt_value('test-key', 'secret'), 'secret')` | `'test-key'` | PASS |
| _derive_key is deterministic | `_derive_key('hello')` called twice | Same key both times | PASS |
| Adapter factory routing | `get_adapter('anthropic')` returns AnthropicAdapter | Correct type | PASS |
| resolve_active_provider fallback | `resolve_active_provider({}, 'secret')` | `('ollama', None, None)` | PASS |
| All 30 pytest tests pass | `python -m pytest tests/test_llm_gateway.py -x -v` | 30/30 PASS | PASS |
| All 5 n8n workflows valid JSON | `python -c "json.load(open(...))"` for all 5 | All valid | PASS |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None | - | - | - | No TBD/FIXME/XXX markers, no stub patterns, no placeholder comments found in any modified file |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| LLMC-01 | 01-01 | Provider-agnostic LLM gateway with 3 adapters | VERIFIED | llm_gateway.py — LLMAdapter ABC + 3 concrete adapters; POST /llm/generate endpoint |
| LLMC-02 | 01-03 | User UI for API key/provider/model management | VERIFIED | LLMSettingsPanel component with save/test/remove; provider/model/key form |
| LLMC-03 | 01-01 | API keys encrypted at rest, masked, never leaked | VERIFIED | Fernet encrypt/decrypt; mask_key(); no raw keys in responses/localStorage/logs |
| LLMC-04 | 01-02 | All n8n workflows rewired to gateway | VERIFIED | 0 ollama:11434 refs; 6 gateway URL refs; response parsing uses $.text |
| LLMC-05 | 01-01, 01-02 | No-key = Ollama fallback | VERIFIED | resolve_active_provider returns ollama fallback; n8n sends provider:null |
| LLMC-06 | 01-01, 01-03 | Structured error responses with What+Where+How-to-fix | VERIFIED | map_provider_error() + _structured_error_response(); UI error display |

### Human Verification Required

#### 1. End-to-end provider switching without restart

**Test:** Run the full Docker stack. Configure an Anthropic API key in the LLM Settings UI. Submit a rule through the n8n webhook (rules-to-metagraph workflow). Verify a graph is written in Neo4j containing Claude-generated atoms. Then switch the provider dropdown to "Ollama" and remove the API key. Resubmit the same rule. Verify it works without any container restart.

**Expected:** 
- First submission: graph written with content generated by Anthropic Claude (via gateway -> Anthropic adapter -> api.anthropic.com)
- Second submission (Ollama): graph written with content generated by local Ollama (via gateway -> Ollama adapter -> http://ollama:11434)
- No container restarts between submissions
- Provider switch is instant because:
  - D-12: gateway reads settings from file on every /llm/generate call (no caching)
  - D-07: n8n sends `provider: null, model: null`, gateway resolves from settings
  - UI changes settings via PUT /llm/settings, which writes to the same file

**Why human:** Requires a live Docker environment with all 8+ services running. Unit tests verify the mechanism (adapter routing, settings resolution, fallback logic) but cannot verify the full service mesh interaction.

## Gaps Summary

No blocking gaps found. The phase goal is substantially achieved:

- Backend: Provider-agnostic LLM gateway with 3 adapters, Fernet-encrypted key storage, 6 REST endpoints, error mapping, model discovery — all implemented and tested (30/30 tests pass)
- n8n: All 5 workflows rewired (6 HTTP nodes), zero direct Ollama calls remaining, response parsing updated for gateway envelope
- UI: LLM Settings panel with two-state display (no-key/active), provider/model/key management, Test Connection, Remove with confirmation
- Security: Keys encrypted at rest (Fernet AES-GCM), masked in UI, never in logs or localStorage

The single behavioral-unverified item (E2E provider switching without restart) requires a live Docker environment to validate and is not a code-level gap.

---

*Verified: 2026-07-06*
*Verifier: Claude (gsd-verifier)*
