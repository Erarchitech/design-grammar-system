// Model Viewer backend access — data-service validation endpoints plus
// targeted Cypher for rule SWRL text and per-entity rule statuses.

import { executeCypher, getConfig } from "./graphApi.js";

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

// → { project, runs: [{runId, createdAt, ruleIds, ruleCount, failedRuleCount,
//      entityCount, state: {stateId, capturedAtUtc, parameterCount} | null, …}] }
export function fetchValidationRuns(project) {
  return getJson(`${base()}/validation/runs/${encodeURIComponent(project || "default-project")}`);
}

// → { runId, rules: [{ruleId, ruleName, ruleDescription, passed}],
//      objectSets: {failed: [{dgEntityId, displayName}], passed: […]}, createdAt, … }
export function fetchValidationView(project, runId, ruleId) {
  const p = encodeURIComponent(project || "default-project");
  const tail = ruleId ? `/${encodeURIComponent(runId)}/${encodeURIComponent(ruleId)}` : `/${encodeURIComponent(runId)}`;
  return getJson(`${base()}/validation/view/${p}${tail}`);
}

// SWRL + naming for a rule straight from the metagraph (Rule.SWRL per schema v4).
export async function fetchRuleDetails(ruleId, project) {
  const json = await executeCypher(
    `MATCH (r:Rule {Rule_Id: $ruleId}) WHERE $project IS NULL OR r.project = $project
     RETURN r.SWRL AS swrl, r.RuleName AS name, r.RuleDescription AS description LIMIT 1`,
    { ruleId, project: project || null }
  );
  const row = json?.results?.[0]?.data?.[0]?.row;
  return row ? { swrl: row[0] || "", name: row[1] || "", description: row[2] || "" } : null;
}

// Per-rule pass/fail breakdown for one geometry entity in a run.
export async function fetchEntityStatuses(project, runId, dgEntityId) {
  const json = await executeCypher(
    `MATCH (ve:ValidationEntity {graph:'ValidGraph', project:$project, runId:$runId, dgEntityId:$dgEntityId})
     RETURN ve.ruleId AS ruleId, ve.status AS status ORDER BY ruleId`,
    { project: project || "default-project", runId, dgEntityId }
  );
  return (json?.results?.[0]?.data || []).map((d) => ({ ruleId: d.row[0], status: d.row[1] }));
}
