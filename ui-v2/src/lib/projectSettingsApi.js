// Project export-policy API client — Phase 1308 (D-02, D-17).
// GET|PUT /projects/{project}/degram-policy are DG-admin-only routes (route policy). The server merges only the
// flags that are sent, and answers 422 DEGRAM_POLICY_INVALID when none is. Every call goes through apiFetch
// (session cookie plus CSRF marker), no token.

import { apiFetch, dataServiceBase } from "./apiClient.js";

export const POLICY_FLAGS = Object.freeze(["providerExportAllowed", "wholeDefinitionAllowed"]);

function policyUrl(project) {
  return `${dataServiceBase()}/projects/${encodeURIComponent(project)}/degram-policy`;
}

// → { project, providerExportAllowed, wholeDefinitionAllowed }
export function getDegramPolicy(project) {
  return apiFetch(policyUrl(project));
}

// patch: only the flags to change, e.g. { wholeDefinitionAllowed: true } → the merged policy
export function setDegramPolicy(project, patch) {
  return apiFetch(policyUrl(project), { method: "PUT", body: patch });
}

// Only the flags whose boolean value differs from the previous state; equal states give {}.
export function policyPatch(prev, next) {
  const patch = {};
  for (const flag of POLICY_FLAGS) {
    const value = next?.[flag];
    if (typeof value === "boolean" && value !== prev?.[flag]) patch[flag] = value;
  }
  return patch;
}

// D-02: the export policy (its controls, values and any placeholder) is for DG admins only. A project owner
// who is not an admin gets nothing. The server routes stay the real control (T-1308-10-01).
export function shouldShowProjectSettings(user, project) {
  return !!project && user?.isAdmin === true;
}
