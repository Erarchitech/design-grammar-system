// Connector registry and access API client. Every browser call uses apiFetch
// (session cookie + CSRF header); connector sign-in sessions belong to add-ins.

import { apiFetch, dataServiceBase } from "./apiClient.js";

// GET /connectors → { categories: string[], connectors: ConnectorOverview[] }
// Each overview: { id, name, category, status, last_connection, active_sessions }.
// The server counts only sessions in the caller's visible projects.
// With a project the server adds `access` ("available" | "requestable" |
// "pending") to each registry connector for a caller who is a member of it
// (Phase 1301-40, D-46).
export function listConnectors(project) {
  const query = project ? `?project=${encodeURIComponent(project)}` : "";
  return apiFetch(`${dataServiceBase()}/connectors${query}`);
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
// to a connector; the owner or an admin approves it, then the member signs in
// from the add-in with their DG account. Records contain authorization only.
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
