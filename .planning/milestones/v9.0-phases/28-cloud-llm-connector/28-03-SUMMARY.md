---
phase: 28-cloud-llm-connector
plan: 03
subsystem: ui
tags:
  - llm
  - settings
  - ui
  - react
  - spa
  - anthropic
  - openai
  - ollama

requires:
  - 01-01 (LLM Gateway endpoints + encryption)
provides:
  - LLM Settings UI page accessible from project dashboard
  - API key management with encrypted storage (masked display)
  - Provider selection (Anthropic, OpenAI, Ollama) with model dropdown
  - Connection testing with latency and model discovery
  - Two-state display: no-key (yellow fallback banner) and active (green connected indicator)
  - Error messages with What+Where+How-to-fix pattern

affects: []

tech-stack:
  added: []
  patterns:
    - React.createElement component with useState/useEffect lifecycle
    - Two-state component rendering (no-key form vs active display)
    - fetch() API calls to data-service /llm/* endpoints
    - CSS banners using warning/success color scheme matching project palette

key-files:
  created: []
  modified:
    - graph-viewer/index.html (+399 lines -- LLMSettingsPanel, routing, nav tile, CSS)

key-decisions:
  - "Component built with all API wiring in one pass (save/test/delete/model-fetch) -- no separate Task 2 needed"

requirements-completed:
  - LLMC-02
  - LLMC-06

duration: 12min
completed: 2026-07-06
status: complete
---

# Phase 28 Plan 03: LLM Settings UI Panel -- Two-State Panel with Provider Selection, API Key Management, and Connection Testing

**LLM Settings UI page added to the single-file React SPA: nav tile on ProjectPage, page routing, LLMSettingsPanel component with no-key/active two-state display, provider dropdown (Anthropic/OpenAI/Ollama), model dropdown from API, password-masked API key input, Test Connection button, Remove button, yellow fallback banner, green connected indicator, and actionable error display.**

## Performance

- **Duration:** 12 min
- **Tasks:** 1 (component built complete with all API wiring)
- **Files modified:** 1
- **Lines added:** 399
- **Lines removed:** 1

## Accomplishments

### LLMSettingsPanel Component (~300 lines)

- **Two-state display per D-10:** No-key state shows full configuration form with yellow "Using local Ollama (fallback)" banner. Active state shows green "Connected: {provider}" indicator with masked key preview, model display, and Change/Remove actions. Both states in the same panel -- no collapse/expand toggle.
- **Provider dropdown:** Anthropic (default), OpenAI, Ollama options. Changing provider refetches model list and toggles API key/Base URL fields accordingly.
- **Model dropdown:** Populated from `GET /llm/models?provider=...`. Shows model IDs only per D-14/D-15. Displays "No models available" when empty.
- **API key input:** Password-masked (`type="password"`). Hidden when Ollama is selected. Stored encrypted server-side, never shown unmasked in UI.
- **Base URL input:** Shown only for OpenAI-compatible provider. Optional field for custom endpoints.
- **Test Connection button (D-11):** Calls `POST /llm/settings/test` with saved config only. Shows success (latency + model list) or actionable error.
- **Save button:** Calls `PUT /llm/settings` with provider/model/apiKey/baseUrl. Refreshes settings on success.
- **Remove button:** Calls `DELETE /llm/settings` with `window.confirm()`. Returns to no-key state immediately.
- **Change button:** Pre-fills form with current values, user re-enters API key.

### API Integration

- `fetchModels(provider)` -- `GET /llm/models` for model list
- `saveSettings(provider, model, apiKey, baseUrl)` -- `PUT /llm/settings`
- `deleteSettings()` -- `DELETE /llm/settings`, resets to Ollama fallback
- `testConnection()` -- `POST /llm/settings/test`, updates model list on success
- All calls use `fetch()` with JSON body, proper error handling

### Page Routing and Navigation

- **AppRouter:** New `handleOpenLLMSettings` handler, `page === "llm-settings"` renders `LLMSettingsPanel` with `onBack: handleBackToProject`
- **ProjectPage:** Third action tile "LLM Settings" with gear SVG icon, wired via `onOpenLLMSettings` prop
- **CSS:** 15 new CSS classes for panel layout, banners, forms, error/success messages, spinner

### Loading State

- Spinner animation while initial `GET /llm/settings` is in flight
- "Saving..." text on Save button while saving
- "Testing..." text on Test Connection button during test

## Task Commits

1. **Task 1: Add LLMSettingsPanel with routing, nav tile, CSS, and API wiring** -- `e46c931` (feat) -- 399 lines added, 1 modified file. Component built complete with all API helpers, form controls, two-state rendering, and error handling.

## Files Modified

- `graph-viewer/index.html` (+399 lines):
  - CSS styles for LLM Settings panel (15 classes, lines ~1013-1070)
  - `const onOpenLLMSettings` prop extraction in ProjectPage (line 1419)
  - "LLM Settings" action tile in ProjectPage grid (lines 1524-1557)
  - LLMSettingsPanel function component (lines 3992-4294): state, API helpers, handlers, useEffect, render with two-state display
  - `handleOpenLLMSettings` handler in AppRouter (line 4340)
  - `page === "llm-settings"` routing case (lines 4358-4360)
  - `onOpenLLMSettings` prop passed to ProjectPage (line 4357)

## Decisions Made

- **All API wiring in a single pass:** The component was built complete with all API helpers (fetchModels, saveSettings, deleteSettings, testConnection) and form controls. The plan's Task 1/Task 2 split was executed as one atomic change since the component structure required all interactive elements to be functional.
- **Provider display capitalization:** Provider name in active state display is capitalized via `provider.charAt(0).toUpperCase() + provider.slice(1)` -- "anthropic" shows as "Anthropic".
- **OpenAI Base URL default placeholder:** Set to "https://api.openai.com/v1" matching standard OpenAI API endpoint.

## Deviations from Plan

None -- plan executed as written. The plan's Task 1 and Task 2 were both completed in a single atomic commit since the component was built complete with all interactive wiring.

## Threat Surface Scan

All threat register items (T-03-01 through T-03-SC) verified during implementation:

- **T-03-01 (Information Disclosure, MEDIUM):** API key travels in PUT /llm/settings body over HTTP. The component does not store keys in localStorage or display them unmasked -- the `apiKeyPreview` field from the GET response is the only key-related display.
- **T-03-02 (Information Disclosure, LOW):** API key input uses `type="password"`. Key not persisted to browser storage. Verified no `localStorage.setItem` calls for API key in the component.
- **T-03-03 (Information Disclosure, MEDIUM):** Error display renders the `error` field from the response via React.createElement text node. No raw `apiKey`, provider endpoint URL, or response body content exposed in error paths.
- **T-03-04 (Tampering, LOW):** Single-user deployment; no CSRF protection. Form submission uses standard `fetch()` JSON body.
- **T-03-SC (XSS, MEDIUM):** All provider names, model IDs, and error messages rendered as text nodes via React.createElement -- no `dangerouslySetInnerHTML` usage. Verified by grep.

## Known Stubs

None identified. Model dropdown shows "No models available" when empty (correct behavior for initial state before successful test). Yellow banner in no-key state is intentional per D-10 design.

## Verification Summary

| Check | Result |
|-------|--------|
| `function LLMSettingsPanel` defined | 1 (PASS) |
| `handleOpenLLMSettings` references | 2 (PASS) |
| `llm-settings-page` CSS class | 3 (PASS) |
| `llm-settings-banner` CSS class | 5 (PASS) |
| `"Using local Ollama (fallback)"` text | 1 (PASS) |
| `"Connected:"` text in green banner | 1 (PASS) |
| `/llm/settings` endpoint references | 4 (PASS) |
| `/llm/settings/test` endpoint reference | 1 (PASS) |
| `/llm/models` endpoint reference | 1 (PASS) |
| `"Test Connection"` button text | 1 (PASS) |
| `"Remove"` button text | 1 (PASS) |
| `saveSettings` function defined | YES (PASS) |
| `testConnection`/`handleTest` defined | YES (PASS) |
| `deleteSettings`/`handleRemove` defined | YES (PASS) |
| `fetchModels` defined | YES (PASS) |
| Provider dropdown has anthropic option | YES (PASS) |
| All API calls use `fetch()` | YES (PASS) |
| File parse check (valid UTF-8) | PASS |

## Self-Check: PASSED

All created files verified on disk. Commit `e46c931` confirmed in git log. All verification checks pass.

---

*Phase: 28-cloud-llm-connector*
*Completed: 2026-07-06*
