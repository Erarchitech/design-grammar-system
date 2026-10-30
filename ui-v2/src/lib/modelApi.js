// Model Viewer backend access — data-service validation endpoints plus the
// named rule-detail and per-entity status reads (phase 1205: no client Cypher).

import { apiFetch, dataServiceBase } from "./apiClient.js";

const base = dataServiceBase;
const getJson = (url) => apiFetch(url);

// → { project, runs: [{runId, createdAt, ruleIds, ruleCount, failedRuleCount,
//      entityCount, state: {stateId, capturedAtUtc, parameterCount} | null, …}] }
export function fetchValidationRuns(project) {
  return getJson(`${base()}/validation/runs/${encodeURIComponent(project || "default-project")}`);
}

// → { runId, rules: [{ruleId, ruleName, ruleDescription, passed}],
//      objectSets: {failed: [{dgEntityId, displayName}], passed: […]}, createdAt,
//      viewerResources: [DG-proxy object URLs], … }
// D-21 (1301-09): the payload carries no Speckle credential. Geometry is loaded through the
// project-authorised /speckle-proxy/ URLs in viewerResources (see lib/speckleProxy.js).
export function fetchValidationView(project, runId, ruleId) {
  const p = encodeURIComponent(project || "default-project");
  const tail = ruleId ? `/${encodeURIComponent(runId)}/${encodeURIComponent(ruleId)}` : `/${encodeURIComponent(runId)}`;
  return getJson(`${base()}/validation/view/${p}${tail}`);
}

// Phase 1303-26 (D-82): the mapping view of a model snapshot (the «Снимок модели» a confirmed mapping created).
// → { stateId, label, document, capturedAtUtc, viewerResources, elements: [{nativeId, label, revitId, classIris,
//      classLabels, state}], classes: [{iri, label, count}], states: {state: count} }
export function fetchSnapshotView(project, stateId) {
  const p = encodeURIComponent(project || "default-project");
  return getJson(`${base()}/validation/snapshot/${p}/${encodeURIComponent(stateId)}`);
}

// SWRL + naming for a rule from the metagraph (Rule.SWRL per schema v4).
// GET /rules/{project}/{ruleId} → { ruleId, swrl, name, description }; null when
// the rule is absent (404) or no project is set.
export async function fetchRuleDetails(ruleId, project) {
  if (!project || !ruleId) return null;
  const data = await apiFetch(
    `${base()}/rules/${encodeURIComponent(project)}/${encodeURIComponent(ruleId)}`,
    { allow404: true }
  );
  return data
    ? { swrl: data.swrl || "", name: data.name || "", description: data.description || "" }
    : null;
}

// Per-rule pass/fail breakdown for one geometry entity in a run.
// GET /validation/view/{project}/{runId}/entity/{dgEntityId} → { statuses:[{ruleId, status}] }
export async function fetchEntityStatuses(project, runId, dgEntityId) {
  const data = await apiFetch(
    `${base()}/validation/view/${encodeURIComponent(project || "default-project")}/${encodeURIComponent(runId)}/entity/${encodeURIComponent(dgEntityId)}`
  );
  return (Array.isArray(data?.statuses) ? data.statuses : []).map((s) => ({
    ruleId: s.ruleId,
    status: s.status
  }));
}
