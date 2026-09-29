// Connector credential API client — Phase 813
// Talks to data-service connector endpoints via the nginx /data-service/ proxy.
// Backend shapes: GET /connectors returns registry + status + credential
// summaries (never tokens); POST creates and returns token once; DELETE revokes.
// Phase 1205: every call goes through apiFetch (session cookie + CSRF header).

import { apiFetch, dataServiceBase } from "./apiClient.js";

// GET /connectors → { categories: string[], connectors: ConnectorOverview[] }
// Each overview: { id, name, category, status, last_connection, credentials }
// The server lists only credentials of the caller's member projects.
export function listConnectors() {
  return apiFetch(`${dataServiceBase()}/connectors`);
}

// POST /connectors/{connectorId}/credentials
// Body: { project, label? } → { credential_id, token } (201, token shown once)
// Phase 825 (CONNG-03): project scopes the token so the CONNECTOR component no
// longer needs a Project input; the heartbeat echoes it back. Phase 1205: the
// server requires the project (it authorises the caller against it), so it is
// always sent.
export function createCredential(connectorId, label, project) {
  const body = { project };
  if (label) body.label = label;
  return apiFetch(`${dataServiceBase()}/connectors/${encodeURIComponent(connectorId)}/credentials`, {
    method: "POST",
    body
  }); // { credential_id, token }
}

// DELETE /connectors/{connectorId}/credentials/{credentialId} → 204
export async function revokeCredential(connectorId, credentialId) {
  await apiFetch(
    `${dataServiceBase()}/connectors/${encodeURIComponent(connectorId)}/credentials/${encodeURIComponent(credentialId)}`,
    { method: "DELETE" }
  );
}
