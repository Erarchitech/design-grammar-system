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

// ── DeGram pairing (Phase 1301-17, D-25, D-26) ──
// The "degram" card of GET /connectors lists pairings, not connector
// credentials: each row is { credential_id, label, created_at, last_exchange,
// revoked } (an admin also gets username). A pairing has no project; DeGram
// chooses the project when it exchanges the token.
export const DEGRAM_CONNECTOR_ID = "degram";

// POST /connectors/degram/pairings  Body: { label? } → { credential_id, token }
// (201; the dgp_ token is shown once). Normalised to the credential shape the
// screen already handles.
export async function createDegramPairing(label) {
  const body = {};
  if (label) body.label = label;
  const result = await apiFetch(`${dataServiceBase()}/connectors/degram/pairings`, {
    method: "POST",
    body
  });
  return { credential_id: result.pairing_id, token: result.token };
}

// DELETE /connectors/degram/pairings/{pairingId} → 204. Also ends every
// delegated token DeGram minted from this pairing.
export async function revokeDegramPairing(pairingId) {
  await apiFetch(
    `${dataServiceBase()}/connectors/degram/pairings/${encodeURIComponent(pairingId)}`,
    { method: "DELETE" }
  );
}
