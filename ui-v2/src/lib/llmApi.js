// AI Engine backend access — LLM gateway settings, model discovery, connection test.
// nginx proxies /llm/ to data-service (nginx.conf line 23). The vite dev proxy
// also forwards /llm to localhost:8080 for development.

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = j?.detail?.error || j?.detail || "";
    } catch {
      /* non-JSON body */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// GET /llm/settings → { provider, model, apiKeyConfigured, apiKeyPreview, baseUrl }
export function getSettings() {
  return getJson("/llm/settings");
}

// PUT /llm/settings with { provider?, model?, apiKey?, baseUrl? }
// Returns the updated LLMSettingsResponse.
export async function saveSettings(payload) {
  const res = await fetch("/llm/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = j?.detail || "";
    } catch {
      /* non-JSON body */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// POST /llm/settings/test → { success, latencyMs, models, error }
// `selection` carries the form's current provider/model/baseUrl (and a typed but
// unsaved key). Without it the backend tests the persisted config, which reports
// success for whichever provider is selected even when its key belongs to
// another provider.
export async function testConnection(selection = {}) {
  const res = await fetch("/llm/settings/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(selection)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// GET /llm/models?provider=X → string[]
export function fetchModels(provider) {
  return getJson(`/llm/models?provider=${encodeURIComponent(provider)}`);
}
