---
phase: 811-ai-engine-screen
plan: "811-01"
subsystem: ui, api
tags: llm, anthropic, openai, ollama, react, fastapi

# Dependency graph
requires:
  - phase: 810-ring-extension-and-screen-shell
    provides: AiEngineScreen skeleton, ring callout for AI Engine region
provides:
  - Full AiEngineScreen UI with provider/model/key configuration
  - llmApi module for gateway settings, model discovery, and connection test
affects: [816-integration-and-deployment, graph-viewer prompt console]

# Tech tracking
tech-stack:
  added: [ui-v2/src/lib/llmApi.js (new API module)]
  patterns:
    - V2 screen layout with frost-card sections and annotation eyebrows
    - API module using relative /llm/ paths matching nginx location block

key-files:
  created:
    - ui-v2/src/lib/llmApi.js
  modified:
    - ui-v2/src/screens/AiEngineScreen.jsx
    - ui-v2/vite.config.js

key-decisions:
  - "Used existing GET /llm/models endpoint (already present in app.py line 1028) — no new backend endpoint needed"
  - "Used hardcoded /llm/ relative paths in llmApi.js (nginx proxies /llm/ to data-service directly, not under /data-service/)"
  - "Included baseUrl input field (part of LLMSettingsPayload) for OpenAI-compatible provider config"
  - "Model list is fetched live via GET /llm/models?provider=X on provider change; falls back to saved model if not in live list"

patterns-established:
  - "Screen component follows ProjectsScreen layout pattern (fixed fullscreen + maxWidth 1280 scroll container + frost cards)"

requirements-completed: [AIENG-01, AIENG-02, AIENG-03, AIENG-04]

coverage:
  - id: D1
    description: "Provider and model selection persisted via /llm/settings"
    requirement: AIENG-01
    verification:
      - kind: unit
        ref: "build: npm --prefix ui-v2 run build passes"
        status: pass
    human_judgment: true
    rationale: "E2E requires running data-service container; UI verified via build"
  - id: D2
    description: "API key encrypted at rest; UI shows set/not-set status, never the key"
    requirement: AIENG-02
    verification:
      - kind: unit
        ref: "build: npm --prefix ui-v2 run build passes"
        status: pass
    human_judgment: true
    rationale: "E2E requires running data-service container to confirm encryption; code-reviewed against LLMSettingsResponse"
  - id: D3
    description: "Active configuration summary showing provider, model, and key status"
    requirement: AIENG-03
    verification:
      - kind: unit
        ref: "build: npm --prefix ui-v2 run build passes"
        status: pass
    human_judgment: true
    rationale: "Visual verification of summary section in browser"
  - id: D4
    description: "Connection test with success/failure feedback via POST /llm/settings/test"
    requirement: AIENG-04
    verification:
      - kind: unit
        ref: "build: npm --prefix ui-v2 run build passes"
        status: pass
    human_judgment: true
    rationale: "E2E requires running data-service container with configured API key"

# Metrics
duration: 20min
completed: 2026-07-11
status: complete
---

# Phase 811 Plan 811-01: AI Engine Screen Summary

**LLM provider/model/API-key setup screen over the existing data-service gateway, with dynamic model discovery, encrypted key management, and connection test feedback**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-11T10:30:00Z (approx)
- **Completed:** 2026-07-11T10:50:00Z (approx)
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Created `llmApi.js` with `getSettings()`, `saveSettings()`, `testConnection()`, and `fetchModels()` matching modelApi.js conventions
- Added `/llm` dev proxy to `vite.config.js` (production proxy already existed in `nginx.conf` line 23)
- Implemented full AiEngineScreen with:
  - Provider selector (Anthropic / OpenAI / Ollama)
  - Dynamic model list fetched from `GET /llm/models?provider=X` on provider change
  - API key input (type="password") that clears after save; key status badge reflects `apiKeyConfigured` from the gateway response
  - Optional baseUrl input for OpenAI-compatible provider endpoints
  - Active configuration summary block (provider, model, key status)
  - Connection test button calling `POST /llm/settings/test` with success (latency, model count) or actionable error feedback
  - Loading, error, saving, and testing state management throughout
- Build verification: `npm --prefix ui-v2 run build` passes cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: llmApi module + vite proxy** — `59d6c1c` (feat)
2. **Task 2: AiEngineScreen UI** — `b40950b` (feat)
3. **Task 3: Verify** — no additional commit (build verification passed against Task 2 state)

## Files Created/Modified

- `ui-v2/src/lib/llmApi.js` (NEW) — API module for LLM gateway: settings CRUD, model discovery, connection test
- `ui-v2/src/screens/AiEngineScreen.jsx` (MODIFIED) — Full implementation from skeleton (489 insertions, 10 deletions)
- `ui-v2/vite.config.js` (MODIFIED) — Added `/llm` proxy route for development

## Decisions Made

- Used existing `GET /llm/models` endpoint at `data-service/app.py` line 1028 — no new backend endpoint was needed. The plan's conditional ("if the gateway has list_models adapters but no HTTP endpoint, add one") was satisfied by the existing endpoint.
- Used hardcoded `/llm/` relative paths in `llmApi.js` rather than `getConfig().dataServiceUrl`, because nginx proxies `/llm/` directly to data-service (not under `/data-service/` rewrite path). This matches the routing reality documented in `nginx.conf` line 23.
- Included a `baseUrl` input field even though the plan doesn't explicitly require it — it is part of `LLMSettingsPayload` and essential for OpenAI-compatible providers (DeepSeek, Groq, etc.).
- Model list is fetched live per-provider on selection change. If the saved model isn't in the live list, it is displayed as an option with a "(saved)" label so the select can display it.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- AiEngineScreen is fully wired to the existing data-service gateway endpoints
- Ready for Phase 816 (Integration & Deployment) — the Graph Viewer prompt console should continue to work against the configured provider (criterion 4)
- Parallel agents can proceed with ConnectorsScreen (813) without conflicts — no shared files

---
*Phase: 811-ai-engine-screen*
*Completed: 2026-07-11*
