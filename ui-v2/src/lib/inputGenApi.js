// AI-generated Grasshopper script inputs — data-service access for the two
// generation/acceptance routes documented in spec/API.md: the candidate
// generation route and the per-candidate acceptance route below.
//
// GHIN-04 rule this module must keep: `generateInputs` and
// `fetchAcceptedCandidates` are reads; `acceptCandidate` is the ONLY writer in
// this module, and it must only ever be called from an explicit user action
// (a click handler), never from an effect or on render/selection (D-19, SC3).

import { executeCypher, getConfig } from "./graphApi.js";

const base = () => getConfig().dataServiceUrl.replace(/\/$/, "");

// POST helper mirroring modelApi.js's getJson error-unwrapping convention:
// unwrap `detail.error` from the structured `{error, hint, code}` body, and
// surface `detail.hint` too — for these two routes the hint carries the
// actionable part (which parameter, which domain, which available
// definition ids).
async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    let error = "";
    let hint = "";
    try {
      const j = await res.json();
      error = j?.detail?.error || j?.detail || "";
      hint = j?.detail?.hint || "";
    } catch {
      /* non-JSON body */
    }
    const message = [error || `HTTP ${res.status}`, hint].filter(Boolean).join(" — ");
    const err = new Error(message);
    err.hint = hint;
    throw err;
  }
  return res.json();
}

// → { project, definitionId, publishedAt, ruleId, determinabilityClass,
//     ruleLimit, boundParameters[], excludedParameters[], candidates[],
//     tier, attempts, provider, model, flags[] }
export function generateInputs(project, definitionId, ruleId, candidateCount, parameterOverrides) {
  const body = { project, ruleId };
  // Omit falsy/empty optional fields rather than sending nulls, so the
  // server-side defaults and definition resolution apply.
  if (definitionId) body.definitionId = definitionId;
  if (candidateCount) body.candidateCount = candidateCount;
  if (Array.isArray(parameterOverrides) && parameterOverrides.length) {
    body.parameterOverrides = parameterOverrides;
  }
  return postJson(`${base()}/computgraph/generate-inputs`, body);
}

// → { project, stateId, kind, acceptedAt, parameterCount, provenance }
// The only writer in this module — call only from a click handler.
export function acceptCandidate(project, definitionId, ruleId, candidate) {
  // The candidate object is sent through unchanged: the server re-validates
  // it against live published domains, and reshaping it here would make the
  // two sides disagree about what was actually accepted.
  return postJson(`${base()}/computgraph/candidates/accept`, { project, definitionId, ruleId, candidate });
}

// → [{stateId, sourceRuleId, provider, model, generatedAt, acceptedAt, strategy}]
// Targeted read over the graph's accepted AI-generated ParamStates, matching
// modelApi.js's existing targeted-read pattern (bound Cypher parameters only).
export async function fetchAcceptedCandidates(project, ruleId) {
  const json = await executeCypher(
    `MATCH (ds:DesignState {project: $project, kind: 'ParamState'})
     WHERE ds.source = 'ai-generated' AND ($ruleId IS NULL OR ds.sourceRuleId = $ruleId)
     RETURN ds.StateId AS stateId, ds.sourceRuleId AS sourceRuleId, ds.provider AS provider,
            ds.model AS model, ds.generatedAt AS generatedAt, ds.acceptedAt AS acceptedAt,
            ds.strategy AS strategy
     ORDER BY ds.acceptedAt DESC`,
    { project: project || "default-project", ruleId: ruleId || null }
  );
  return (json?.results?.[0]?.data || []).map((d) => ({
    stateId: d.row[0],
    sourceRuleId: d.row[1],
    provider: d.row[2],
    model: d.row[3],
    generatedAt: d.row[4],
    acceptedAt: d.row[5],
    strategy: d.row[6]
  }));
}
