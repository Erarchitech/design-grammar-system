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

// POST /reasoner/consistency with { project, engine: "hermit" }.
// The run always forces the HermiT engine (D-05). Does NOT throw on
// non-2xx — a 504 is ambiguous between a genuine sidecar semantic
// timeout (D-08) and a data-service transport timeout (D-09), so the
// caller branches on body shape, not status code (RESEARCH Pitfall 1).
// Forwards the caller's AbortController signal so a run can be
// cancelled client-side (D-07). Every call is a fresh POST — no
// response is stored or reused across runs (D-10).
export async function runConsistencyCheck(project, { signal } = {}) {
  const res = await fetch("/reasoner/consistency", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project, engine: "hermit" }),
    signal,
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
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
