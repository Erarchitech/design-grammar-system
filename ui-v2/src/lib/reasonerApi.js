// Reasoner Screen backend access — reasoner registry settings.
// nginx proxies /reasoner/ to data-service. The vite dev proxy also
// forwards /reasoner to localhost:8080 for development.
// Phase 1205: every call goes through apiFetch (session cookie + CSRF header).

import { apiFetch } from "./apiClient.js";

// GET /reasoner/settings → { reasoners: [...], selected: "hermit" | null }
export function getReasonerSettings() {
  return apiFetch("/reasoner/settings");
}

// POST /reasoner/consistency with { project, engine: "hermit" }.
// The run always forces the HermiT engine (D-05). Does NOT throw on
// non-2xx — a 504 is ambiguous between a genuine sidecar semantic
// timeout (D-08) and a data-service transport timeout (D-09), so the
// caller branches on body shape, not status code (RESEARCH Pitfall 1).
// Forwards the caller's AbortController signal so a run can be
// cancelled client-side (D-07). Every call is a fresh POST — no
// response is stored or reused across runs (D-10).
export function runConsistencyCheck(project, { signal } = {}) {
  return apiFetch("/reasoner/consistency", {
    method: "POST",
    body: { project, engine: "hermit" },
    signal,
    passthrough: true
  }); // { ok, status, body }
}

// PUT /reasoner/settings with { reasoner: "hermit" }
// Returns the updated settings. Rejects unknown ids with 422.
export function selectReasoner(id) {
  return apiFetch("/reasoner/settings", { method: "PUT", body: { reasoner: id } });
}
