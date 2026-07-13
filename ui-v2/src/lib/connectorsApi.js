// Connector credential API client — Phase 813
// Talks to data-service connector endpoints via the nginx /data-service/ proxy.
// Backend shapes: GET /connectors returns registry + status + credential
// summaries (never tokens); POST creates and returns token once; DELETE revokes.

import { getConfig } from "./graphApi.js";

const base = () => getConfig().dataServiceUrl.replace(/\/$/, "");

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

// GET /connectors → { categories: string[], connectors: ConnectorOverview[] }
// Each overview: { id, name, category, status, last_connection, credentials }
export function listConnectors() {
  return getJson(`${base()}/connectors`);
}

// POST /connectors/{connectorId}/credentials
// Body: { label?, project? } → { credential_id, token } (201, token shown once)
// Phase 825 (CONNG-03): project scopes the token so the CONNECTOR component no
// longer needs a Project input; the heartbeat echoes it back.
export async function createCredential(connectorId, label, project) {
  const body = {};
  if (label) body.label = label;
  if (project) body.project = project;
  const res = await fetch(
    `${base()}/connectors/${encodeURIComponent(connectorId)}/credentials`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }
  );
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
  return res.json(); // { credential_id, token }
}

// DELETE /connectors/{connectorId}/credentials/{credentialId} → 204
export async function revokeCredential(connectorId, credentialId) {
  const res = await fetch(
    `${base()}/connectors/${encodeURIComponent(connectorId)}/credentials/${encodeURIComponent(credentialId)}`,
    { method: "DELETE" }
  );
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
}
