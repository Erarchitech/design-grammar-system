// Member role API client — Phase 1308 (D-01, D-14).
// PUT /projects/{project}/members/{username} with body { role: viewer|editor|owner }
// answers { project, username, role }. Owner or DG admin only (route policy); the
// server refuses to demote the last owner (409 LAST_OWNER). Every call goes through
// apiFetch: session cookie plus the CSRF marker header, no token.

import { apiFetch, dataServiceBase } from "./apiClient.js";

export function changeMemberRole(project, username, role) {
  return apiFetch(
    `${dataServiceBase()}/projects/${encodeURIComponent(project)}/members/${encodeURIComponent(username)}`,
    { method: "PUT", body: { role } }
  );
}
