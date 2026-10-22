// Backend access for the Graph Viewer — named, project-authorised data-service
// endpoints only (phase 1205, D-06/D-08). The browser holds no Neo4j or n8n
// credential, cannot choose a Cypher statement, and never calls n8n: rules
// ingest and graph query go through the data-service workflow relay and are
// polled by executionId. Project isolation is enforced by the server.

import { apiFetch, dataServiceBase, getConfig } from "./apiClient.js";
import { t } from "../i18n/index.js";

// Existing importers keep reading the runtime config from here.
export { getConfig };

const enc = encodeURIComponent;

// GET /graph/{project} → { nodes:[{id, labels, props}], rels:[{source, type, target}] }
// There is no unscoped graph any more: an empty project yields an empty graph
// without a request.
export async function fetchGraph(project) {
  if (!project) return { nodes: [], rels: [] };
  const data = await apiFetch(`${dataServiceBase()}/graph/${enc(project)}`);
  return {
    nodes: Array.isArray(data?.nodes) ? data.nodes : [],
    rels: Array.isArray(data?.rels) ? data.rels : []
  };
}

// Legacy-parity post-ingest fixup ("Neo4j node tagging" gotcha): the workflow
// writes nodes under default-project; the client asks the server to claim them
// for the active project afterwards (POST /graph/{project}/claim-untagged).
export async function tagProjectNodes(project) {
  if (!project) return;
  await apiFetch(`${dataServiceBase()}/graph/${enc(project)}/claim-untagged`, { method: "POST" });
}

// Manual property editing (legacy SPA parity): write a single property on a
// node by Neo4j id and return the updated property map.
// PUT /graph/{project}/node/{neoId}/property  { key, value } → { props }
export async function updateNodeProp(project, neoId, key, value) {
  const data = await apiFetch(
    `${dataServiceBase()}/graph/${enc(project)}/node/${enc(Number(neoId))}/property`,
    { method: "PUT", body: { key, value } }
  );
  return data?.props || null;
}

// Existing rules for the Edit mode picker (legacy fetchExistingRules parity)
// GET /rules/{project} → { project, rules: [{ruleId, text}] }
export async function fetchRules(project) {
  if (!project) return [];
  const data = await apiFetch(`${dataServiceBase()}/rules/${enc(project)}`);
  return (Array.isArray(data?.rules) ? data.rules : []).map((r) => ({
    ruleId: r.ruleId,
    text: r.text || ""
  }));
}

// GET /rules/{project}/{ruleId}/delete-preview → what a delete would remove.
// Read-only: fetch it, show the user, and only then call deleteRule().
// `shared` args are referenced by other rules and are deliberately KEPT.
export function fetchRuleDeletePreview(project, ruleId) {
  return apiFetch(`${dataServiceBase()}/rules/${enc(project)}/${enc(ruleId)}/delete-preview`);
}

// DELETE /rules/{project}/{ruleId} → removes the Rule, its Atoms, and any
// Literal/Var orphaned by that. Destructive and not undoable: only call this
// after the user has confirmed against fetchRuleDeletePreview() output.
export function deleteRule(project, ruleId) {
  return apiFetch(`${dataServiceBase()}/rules/${enc(project)}/${enc(ruleId)}`, { method: "DELETE" });
}

// Near-duplicate classes/properties (Phase 1303-15). GET → { candidates: [{kind, a, b, reason}] }.
export function fetchOntologyDuplicates(project) {
  return apiFetch(`${dataServiceBase()}/ontology/duplicates?project=${enc(project)}`);
}

// decision: "use_existing" merges a (new) into b (existing); "keep_new" records that they are different concepts.
export function resolveOntologyDuplicate(project, a, b, decision) {
  return apiFetch(`${dataServiceBase()}/ontology/duplicates/resolve`, {
    method: "POST",
    body: { project, a, b, decision }
  });
}

// POST /rules/resolve-deletion → { matches[], reason, hallucinated[] }
// Resolves a natural-language deletion request ("all height rules above 50 m")
// to concrete rules, each with its own delete preview. Selection only —
// deletes nothing.
export function resolveRuleDeletion(project, request) {
  return apiFetch(`${dataServiceBase()}/rules/resolve-deletion`, {
    method: "POST",
    body: { project, request }
  });
}

// POST /rules/bulk-delete → deletes the confirmed Rule_Ids. Destructive.
export function bulkDeleteRules(project, ruleIds) {
  return apiFetch(`${dataServiceBase()}/rules/bulk-delete`, {
    method: "POST",
    body: { project, ruleIds }
  });
}

// GET /rules/{project}/{ruleId}/conflicts → { ruleId, conflict, matches[], reason? }.
// Plan 1303-21 (D-65): the conflict check runs on the atoms of a rule that has
// ALREADY been written, so it works for any language and covers every
// participant class. Each match is { ruleId, swrl, description, currentValue,
// sharedClasses[] }. Read-only. A rule whose subject cannot be read answers
// conflict:false with a `reason`.
export function fetchRuleConflicts(project, ruleId) {
  return apiFetch(`${dataServiceBase()}/rules/${enc(project)}/${enc(ruleId)}/conflicts`);
}

// What a dialog decision does to a rule that is already written (D-65). Pure,
// so it can be tested without React. Only the exact "cancel" decision leads to
// the delete dialog, and that dialog still previews and waits for the user's
// confirmation; any unknown or missing decision does nothing.
//   replace | update -> supersede the first matching rule with the new one
//   keep             -> record the accepted overlap on the new rule
//   cancel           -> open the delete dialog for the new rule
export function planConflictDecision(decision, matches, newRuleId) {
  const list = Array.isArray(matches) ? matches : [];
  if ((decision === "replace" || decision === "update") && list.length > 0 && newRuleId) {
    return { action: "supersede", oldRuleId: list[0].ruleId, newRuleId };
  }
  if (decision === "keep" && list.length > 0 && newRuleId) {
    return { action: "accept-overlap", ruleId: newRuleId, conflictsWith: list.map((m) => m.ruleId) };
  }
  if (decision === "cancel" && newRuleId) {
    return { action: "delete-dialog", ruleId: newRuleId };
  }
  return { action: "none" };
}

// POST /rules/check-conflict → { grounding, conflict, matches[] }. Pre-ingest
// text check (paper T1 ITcon R15.6 §4), retained for other callers; the Graph
// Viewer no longer calls it on the ingest path since 1303-21 (it grounds
// English labels only). Read-only. It was meant to run BEFORE ingestRules() so
// the blocking dialog could run entirely client-side, ahead of the rules-ingest
// relay. `grounding` is null and `conflict` is false whenever the NL text
// could not be confidently resolved to a known Class+DatatypeProperty+
// comparator in this project — treat that identically to "no conflict".
export function checkRuleConflict(project, rulesText) {
  return apiFetch(`${dataServiceBase()}/rules/check-conflict`, {
    method: "POST",
    body: { project, rules_text: rulesText }
  });
}

// POST /rules/supersede → records old→new SUPERSEDED_BY provenance. Call
// AFTER ingestRules() has written the new rule (Replace/Update dialog
// actions): the new Rule_Id must already exist in the graph before this
// call can link to it.
//
// The thrown ApiError carries `code`/`hint` (not just a folded message) so a
// caller can distinguish a REFUSED supersede (RULE_NOT_PUBLISHABLE — the old
// rule was correctly left untouched) from a transient/network failure, and
// show the actionable hint rather than just the error — see GraphScreen.jsx's
// runIngestWithConflictCheck for why this distinction matters (live UAT
// regression, debug session rule-ingest-no-conflict-check, 2026-09-19).
export function supersedeRule(project, oldRuleId, newRuleId, prompt) {
  return apiFetch(`${dataServiceBase()}/rules/supersede`, {
    method: "POST",
    body: { project, oldRuleId, newRuleId, prompt: prompt || "" }
  });
}

// POST /rules/accept-overlap → provenance-only annotation for "Keep both".
// Call AFTER ingestRules() has written the new rule. Never blocks or
// mutates the rule corpus — records that the overlap was seen and accepted.
export function acceptRuleOverlap(project, ruleId, conflictsWith) {
  return apiFetch(`${dataServiceBase()}/rules/accept-overlap`, {
    method: "POST",
    body: { project, ruleId, conflictsWith: conflictsWith || [] }
  });
}

// GET /projects → { projects: [{project, nodes, role}] } — only the caller's
// member projects (an admin sees all).
export async function fetchProjects() {
  const data = await apiFetch(`${dataServiceBase()}/projects`);
  return Array.isArray(data?.projects) ? data.projects : [];
}

// ---- design-rule session history (data-service, legacy SPA parity) ----

export async function fetchDrSessions(project) {
  const data = await apiFetch(`${dataServiceBase()}/design-rule-sessions/${enc(project || "default-project")}`);
  return Array.isArray(data?.sessions) ? data.sessions : [];
}

export async function saveDrSession(project, mode, prompt, result) {
  try {
    const data = await apiFetch(`${dataServiceBase()}/design-rule-sessions`, {
      method: "POST",
      body: {
        project: project || "default-project",
        mode,
        prompt,
        result: (result || "").slice(0, 2000)
      }
    });
    return data?.sessionId || null;
  } catch {
    // history is best-effort — never block the workflow on it
    return null;
  }
}

// ---- workflow relay with the async "accepted → poll data-service" contract ----
// POST /workflows/{rules-ingest|graph-query} answers 202 {status:"accepted",
// executionId}; the result is polled at /execution-result/{executionId} only.
// The server binds each execution to the user who started it, so a foreign or
// unknown id is a 404 — there is no latest-by-workflow fallback.

// The Error messages thrown here are UI text (D-06) and are looked up with t() at throw time; a server-supplied
// `data.message` and any ApiError from apiFetch (code/hint passthrough) stay untouched so describeError can map them.
async function pollExecution(executionId, { onProgress, intervalMs = 1500, timeoutMs = 180000 } = {}) {
  const url = `${dataServiceBase()}/execution-result/${enc(executionId)}`;
  const t0 = Date.now();
  for (;;) {
    if (Date.now() - t0 > timeoutMs) throw new Error(t("Workflow timed out."));
    let data = null;
    try {
      data = await apiFetch(url);
    } catch (err) {
      if (err?.status === 404) throw new Error(t("Execution not found or not permitted."));
      // Auth/permission problems are terminal; anything else (transient 5xx,
      // network blip) keeps polling until the timeout, as before.
      if (err?.status === 401 || err?.status === 403) throw err;
    }
    if (data) {
      const status = data.status || "running";
      if (status === "completed") return data.payload || {};
      if (status === "failed") throw new Error(data.message || t("Workflow failed."));
      if (status === "cancelled") throw new Error(t("Workflow cancelled."));
      if (onProgress) onProgress(data);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

async function callWorkflow(path, body, { onProgress } = {}) {
  const data = await apiFetch(`${dataServiceBase()}${path}`, { method: "POST", body });
  if (data?.status !== "accepted" || !data?.executionId) {
    throw new Error(t("Workflow relay did not return an execution id."));
  }
  return pollExecution(data.executionId, { onProgress });
}

export function ingestRules(rulesText, project, opts) {
  return callWorkflow(
    "/workflows/rules-ingest",
    { project: project || "default-project", rulesText },
    opts
  );
}

export function queryGraph(prompt, project, opts) {
  return callWorkflow(
    "/workflows/graph-query",
    { project: project || "default-project", prompt },
    opts
  );
}
