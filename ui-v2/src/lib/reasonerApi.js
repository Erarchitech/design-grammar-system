// Reasoner Screen backend access — reasoner registry settings.
// nginx proxies /reasoner/ to data-service. The vite dev proxy also
// forwards /reasoner to localhost:8080 for development.

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

// GET /reasoner/settings → { reasoners: [...], selected: "hermit" | null }
export function getReasonerSettings() {
  return getJson("/reasoner/settings");
}

// PUT /reasoner/settings with { reasoner: "hermit" }
// Returns the updated settings. Rejects unknown ids with 422.
export async function selectReasoner(id) {
  const res = await fetch("/reasoner/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reasoner: id }),
  });
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
