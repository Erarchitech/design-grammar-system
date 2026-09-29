// AI-generated Grasshopper script inputs — data-service access for the two
// generation/acceptance routes documented in spec/API.md: the candidate
// generation route and the per-candidate acceptance route below.
//
// GHIN-04 rule this module must keep: `generateInputs` and
// `fetchAcceptedCandidates` are reads; `acceptCandidate` is the ONLY writer in
// this module, and it must only ever be called from an explicit user action
// (a click handler), never from an effect or on render/selection (D-19, SC3).

import { apiFetch, dataServiceBase } from "./apiClient.js";

const base = dataServiceBase;

// POST helper on apiFetch: the ApiError already unwraps `detail.error` from the
// structured `{error, hint, code}` body; for these two routes the hint carries
// the actionable part (which parameter, which domain, which available
// definition ids), so it is appended to the message and kept on `err.hint`.
async function postJson(url, body) {
  try {
    return await apiFetch(url, { method: "POST", body });
  } catch (err) {
    if (err?.hint) {
      const wrapped = new Error([err.message, err.hint].filter(Boolean).join(" — "));
      wrapped.hint = err.hint;
      wrapped.code = err.code;
      wrapped.status = err.status;
      throw wrapped;
    }
    throw err;
  }
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
// GET /computgraph/candidates/{project}?ruleId= → { candidates: [...] } — the
// project's accepted AI-generated ParamStates, authorised server-side.
export async function fetchAcceptedCandidates(project, ruleId) {
  const qs = ruleId ? `?ruleId=${encodeURIComponent(ruleId)}` : "";
  const data = await apiFetch(
    `${base()}/computgraph/candidates/${encodeURIComponent(project || "default-project")}${qs}`
  );
  return Array.isArray(data?.candidates) ? data.candidates : [];
}
