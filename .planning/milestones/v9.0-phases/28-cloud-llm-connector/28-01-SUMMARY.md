---
phase: 28-cloud-llm-connector
plan: 01
subsystem: api
tags:
  - llm
  - gateway
  - anthropic
  - openai
  - ollama
  - fernet
  - encryption
  - httpx
  - fastapi
  - pytest

requires: []
provides:
  - Provider-agnostic LLM gateway (POST /llm/generate) with Anthropic, OpenAI, Ollama adapters
  - Encrypted API key storage via Fernet AES-GCM (PUT/GET/DELETE /llm/settings)
  - Connection testing (POST /llm/settings/test) with latency measurement
  - Model discovery (GET /llm/models) with live API query and seed fallback
  - Structured error mapping with What+Where+How-to-fix pattern
affects:
  - 01-02 (n8n workflow rewiring)
  - 01-03 (UI settings panel)

tech-stack:
  added:
    - cryptography (Fernet AES-GCM for at-rest key encryption)
    - httpx (sync HTTP client for provider API calls)
  patterns:
    - Strategy pattern with LLMAdapter ABC and three concrete adapters
    - JSON file settings persistence matching existing Speckle pattern
    - Deterministic SHA-256 key derivation for Fernet (stable across restarts)
    - Structured error responses {error, hint, code} via _structured_error_response

key-files:
  created:
    - data-service/llm_gateway.py (617 lines — adapters, encryption, settings, model discovery, error mapping)
    - data-service/tests/test_llm_gateway.py (30 tests — unit + endpoint-level)
  modified:
    - data-service/app.py (+6 endpoints, +1 import block)
    - docker-compose.yml (+LLM_MASTER_SECRET env var)
    - data-service/requirements.txt (+cryptography, +httpx)

key-decisions:
  - "Sync httpx.Client (not AsyncClient) — simpler testing with FastAPI TestClient"
  - "DATA_DIR re-declared in llm_gateway.py (not imported from app.py) — avoids Neo4j driver initialization side effects"
  - "Adaptors let HTTP exceptions propagate to endpoint handler for consistent error mapping (not wrapped internally)"
  - "LLM_MASTER_SECRET env var checked in PUT /llm/settings (500 if empty) — not on every GET"

patterns-established:
  - "Gateway adapter: LLMAdapter ABC -> AnthropicAdapter/OpenAIAdapter/OllamaAdapter with provider-native prompt format (D-01)"
  - "Settings CRUD: encrypted at rest via Fernet, masked on read via mask_key(), never cached per D-12"
  - "Provider fallback: empty or missing-key settings -> ('ollama', None, None) — full offline capability preserved (LLMC-05)"

requirements-completed:
  - LLMC-01
  - LLMC-03
  - LLMC-05
  - LLMC-06

coverage:
  - id: D1
    description: "Provider adapters (Anthropic, OpenAI, Ollama) instantiate and route correctly"
    requirement: LLMC-01
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::test_module_imports"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestGenerate::test_adapter_routing"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestGenerate::test_fallback_resolution"
        status: pass
    human_judgment: false

  - id: D2
    description: "API keys encrypted at rest with Fernet AES-GCM; round-trip and wrong-key rejection verified"
    requirement: LLMC-03
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestFernet::test_roundtrip"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestFernet::test_wrong_key"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestPutSettings::test_save_settings"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::test_get_settings_with_configured_settings"
        status: pass
    human_judgment: false

  - id: D3
    description: "No-key state resolves to Ollama fallback (provider=ollama) preserving offline capability"
    requirement: LLMC-05
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestGenerate::test_no_key_fallback"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestResolveActiveProvider::test_empty_settings_returns_ollama_fallback"
        status: pass
    human_judgment: false

  - id: D4
    description: "Provider errors map to structured {error, hint, code} responses with no key or URL leakage"
    requirement: LLMC-06
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestGenerate::test_error_mapping"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::test_error_response_shape"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestConnection::test_connection_provider_error"
        status: pass
    human_judgment: false

  - id: D5
    description: "Key masking returns truncated preview with never the full key string"
    requirement: LLMC-03
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestKeyMasking::test_long_key"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestKeyMasking::test_short_key"
        status: pass
    human_judgment: false

  - id: D6
    description: "Settings CRUD endpoints persist encrypted keys and return masked previews"
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestPutSettings::test_save_settings"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestPutSettings::test_empty_api_key_does_not_overwrite"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestDeleteSettings::test_clear_settings"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestGetSettings::test_empty_state"
        status: pass
    human_judgment: false

  - id: D7
    description: "Connection test endpoint validates saved config with latency and model discovery"
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestConnection::test_connection_success"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestConnection::test_connection_no_key"
        status: pass
    human_judgment: false

  - id: D8
    description: "Model discovery returns provider model lists (live or seed fallback)"
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestModels::test_models_endpoint"
        status: pass
    human_judgment: false

  - id: D9
    description: "System prompt passed through to adapter in provider-native placement"
    verification:
      - kind: unit
        ref: "data-service/tests/test_llm_gateway.py::TestGenerate::test_generate_with_system_prompt"
        status: pass
    human_judgment: false

  - id: D10
    description: "docker-compose.yml has LLM_MASTER_SECRET env var on data-service; requirements.txt has cryptography and httpx"
    verification:
      - kind: other
        ref: "grep LLM_MASTER_SECRET docker-compose.yml && grep -E '^(cryptography|httpx)' data-service/requirements.txt"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-06
status: complete
---

# Phase 28 Plan 01: LLM Gateway Core — Provider Adapters, Encryption, Endpoints, Tests

**Provider-agnostic LLM gateway in data-service with Anthropic/OpenAI/Ollama adapters, Fernet-encrypted key storage, 6 REST endpoints, structured error mapping, and 30 pytest tests — no regressions in existing 28 tests.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)
- **Tests added:** 30 (all pass)
- **Existing tests:** 28 (no regressions)

## Accomplishments

- **llm_gateway.py** — 617-line module with LLMAdapter ABC, three concrete adapters (Anthropic Messages API, OpenAI Chat Completions, Ollama Generate), Fernet encrypt/decrypt with SHA-256 deterministic key derivation, graduated key masking, JSON settings persistence in DATA_DIR, active provider resolution with Ollama fallback, model discovery with startup auto-discovery cache, structured error mapping (LLMC-06)
- **6 new endpoints** in app.py: GET/PUT/DELETE /llm/settings, POST /llm/generate, POST /llm/settings/test, GET /llm/models — all with structured error handling
- **docker-compose.yml** updated with LLM_MASTER_SECRET env var
- **requirements.txt** updated with cryptography and httpx
- **30 pytest tests** covering key masking (5), Fernet encryption (4), resolve_active_provider (4), settings CRUD (4), generate routing/fallback/error-mapping/system-prompt (5), connection test (3), models endpoint (2), error shape (1), module imports (1)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create llm_gateway.py with provider adapters, encryption, settings persistence** — `9d0d345` (feat)
2. **Task 2: Add /llm/* endpoints to app.py, update docker-compose and requirements, write pytest suite** — `a7cd151` (feat)

## Files Created/Modified

- `data-service/llm_gateway.py` (created) — 617 lines: Pydantic models (GenerateRequest, GenerateResponse, LLMSettingsPayload, LLMSettingsResponse, TestResult), seed model lists, LLMAdapter ABC, AnthropicAdapter, OpenAIAdapter, OllamaAdapter, get_adapter factory, Fernet encrypt/decrypt, mask_key, settings load/save/get_llm_settings_response, resolve_active_provider, model discovery cache + list_models_for_provider, map_provider_error
- `data-service/app.py` (modified) — +6 endpoints: GET /llm/settings, PUT /llm/settings (encrypts apiKey), DELETE /llm/settings (204), POST /llm/generate (main gateway), POST /llm/settings/test (latency + model discovery), GET /llm/models (live or seed)
- `docker-compose.yml` (modified) — LLM_MASTER_SECRET env var added to data-service environment block
- `data-service/requirements.txt` (modified) — cryptography, httpx added alphabetically
- `data-service/tests/test_llm_gateway.py` (created) — 30 tests across 10 test classes/functions

## Decisions Made

- **Sync httpx.Client vs AsyncClient** — Per plan direction, all adapter HTTP calls use synchronous httpx.Client for simpler TestClient-based testing. No async complexity needed for gateway-to-provider calls.
- **DATA_DIR re-declared in llm_gateway.py** — Not imported from app.py to avoid Neo4j driver initialization side effects at import time. Both read from the same `DG_DATA_DIR` env var with `/app/data` default.
- **Error handling in endpoint layer** — Adapters let HTTP exceptions propagate naturally; the POST /llm/generate endpoint catches all exceptions via `map_provider_error()` and raises structured `HTTPException(502)`.
- **mask_key behavior** — >12 chars: first 6 + "..." + last 6; 5-12: first 2 + "..." + last 2; <=4: "****" (plan verify step had typo in expected value — actual behavior matches acceptance criteria spec)

## Deviations from Plan

None — plan executed exactly as written. Two verify/test assertion corrections were needed:

1. **mask_key verify assertion typo** — Plan verify step expected `'sk-ant-...klmnop'` (with dash) but `'sk-ant-abcdefghijklmnop'[:6]` yields `'sk-ant'` (no dash). Correct output per acceptance criteria (first 6 + "..." + last 6) is `'sk-ant...klmnop'`. Fixed verify command.
2. **Fernet token format** — `cryptography` 46.0.5 produces single base64 string tokens (no dots), so dot-count assertion was replaced with length + prefix check.

Both are test assertion corrections, not code changes.

## Issues Encountered

- `test_save_settings` needed `load_persisted_llm_settings` to return different values on first vs second call (endpoint re-reads after save). Fixed by using `side_effect` list pattern instead of `return_value`.
- `test_empty_api_key_does_not_overwrite` had the same dual-call issue. Fixed with same pattern.

## Threat Surface Scan

No new threat surface found beyond the documented STRIDE register. The `mask_key()` function correctly prevents key leakage in all path lengths. Error mappings in `map_provider_error()` strip provider endpoint URLs and response body content. All 12 T-01 threat items verified during implementation.

## Known Stubs

None identified. All functions have real implementations. Seed model lists are intentional (replaced by live results on first successful test per D-14). Ollama model cache starts empty and populates on container startup or first call.

## Verification Summary

| Check | Result |
|-------|--------|
| `python -c "from llm_gateway import *"` | PASS |
| `pytest tests/test_llm_gateway.py -x -v` | 30/30 PASS |
| `pytest tests/ -x -v` (full suite) | 58/58 PASS (no regressions) |
| `grep LLM_MASTER_SECRET docker-compose.yml` | FOUND |
| `grep -E "^(cryptography\|httpx)" requirements.txt` | BOTH FOUND |
| Security: no raw api_key/apiKey in response bodies | CLEAN |

## Self-Check: PASSED

All created files verified on disk. Both commits confirmed in git log. All 30 new tests pass. Existing 28 tests unmodified and passing.

---

*Phase: 28-cloud-llm-connector*
*Completed: 2026-07-06*
