// AI Engine backend access — LLM gateway settings, model discovery, connection test.
// nginx proxies /llm/ to data-service (nginx.conf line 23). The vite dev proxy
// also forwards /llm to localhost:8080 for development.
// Phase 1205: every call goes through apiFetch (session cookie + CSRF header).

import { apiFetch } from "./apiClient.js";

// GET /llm/settings → { provider, model, apiKeyConfigured, apiKeyPreview, baseUrl }
export function getSettings() {
  return apiFetch("/llm/settings");
}

// PUT /llm/settings with { provider?, model?, apiKey?, baseUrl? }
// Returns the updated LLMSettingsResponse.
export function saveSettings(payload) {
  return apiFetch("/llm/settings", { method: "PUT", body: payload });
}

// POST /llm/settings/test → { success, latencyMs, models, error }
// `selection` carries the form's current provider/model/baseUrl (and a typed but
// unsaved key). Without it the backend tests the persisted config, which reports
// success for whichever provider is selected even when its key belongs to
// another provider.
export function testConnection(selection = {}) {
  return apiFetch("/llm/settings/test", { method: "POST", body: selection });
}

// GET /llm/models?provider=X → string[]
export function fetchModels(provider) {
  return apiFetch(`/llm/models?provider=${encodeURIComponent(provider)}`);
}
