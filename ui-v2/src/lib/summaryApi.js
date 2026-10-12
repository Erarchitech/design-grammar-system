import { apiFetch, dataServiceBase } from "./apiClient.js";

export function getProjectSummary(project) {
  return apiFetch(`${dataServiceBase()}/projects/${encodeURIComponent(project)}/summary`);
}
