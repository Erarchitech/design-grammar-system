// Connector credential API client — Phase 813
// Talks to data-service connector endpoints via the nginx /data-service/ proxy.
// Backend shapes: GET /connectors returns registry + status + credential
// summaries (never tokens); POST creates and returns token once; DELETE revokes.
// Phase 1205: every call goes through apiFetch (session cookie + CSRF header).

import { apiFetch, dataServiceBase } from "./apiClient.js";

// GET /connectors → { categories: string[], connectors: ConnectorOverview[] }
// Each overview: { id, name, category, status, last_connection, credentials }
// The server lists only credentials of the caller's member projects.
// With a project the server adds `access` ("available" | "requestable" |
// "pending") to each registry connector for a caller who is a member of it
// (Phase 1301-40, D-46).
export function listConnectors(project) {
  const query = project ? `?project=${encodeURIComponent(project)}` : "";
  return apiFetch(`${dataServiceBase()}/connectors${query}`);
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

// DeGram grants are project-scoped authorization records, not credentials.
// No endpoint returns a key to the browser.
export const DEGRAM_CONNECTOR_ID = "degram";

function projectGrantsUrl(project) {
  return `${dataServiceBase()}/projects/${encodeURIComponent(project)}/degram-grants`;
}

export function listProjectGrants(project) {
  return apiFetch(projectGrantsUrl(project));
}

export function issueGrant(project, { username, label, purpose }) {
  return apiFetch(projectGrantsUrl(project), {
    method: "POST",
    body: { username, label, purpose }
  });
}

export async function revokeGrant(project, grantId) {
  await apiFetch(`${projectGrantsUrl(project)}/${encodeURIComponent(grantId)}`, {
    method: "DELETE"
  });
}

export function listMyGrants() {
  return apiFetch(`${dataServiceBase()}/degram/grants/mine`);
}

export function requestGrant(project, note) {
  return apiFetch(`${dataServiceBase()}/degram/grant-requests`, {
    method: "POST",
    body: { project, note }
  });
}

// Per-connector access (Phase 1301-40, D-46). A project viewer asks for access
// to a connector; the owner or an admin approves it, then the viewer creates the
// connector's credential. Records carry no token and no hash.
function projectAccessUrl(project) {
  return `${dataServiceBase()}/projects/${encodeURIComponent(project)}/connector-access`;
}

export function requestConnectorAccess(project, connectorId, note) {
  const body = { project, connector_id: connectorId };
  if (note) body.note = note;
  return apiFetch(`${dataServiceBase()}/connector-access-requests`, { method: "POST", body });
}

export function listMyConnectorAccess() {
  return apiFetch(`${dataServiceBase()}/connector-access/mine`);
}

// → { project, grants: [{access_id, username, connector_id, active, ...}], requests: [{request_id, username, connector_id, note, ...}] }
export function listProjectConnectorAccess(project) {
  return apiFetch(projectAccessUrl(project));
}

export function issueConnectorAccess(project, { username, connectorId }) {
  return apiFetch(projectAccessUrl(project), {
    method: "POST",
    body: { username, connector_id: connectorId }
  });
}

export async function revokeConnectorAccess(project, accessId) {
  await apiFetch(`${projectAccessUrl(project)}/${encodeURIComponent(accessId)}`, {
    method: "DELETE"
  });
}
