// Mapping API client — Phase 1303 MVP slice (1303-API-CONTRACT v0.1; 1303-CONTEXT D-18, D-21, D-29).
// Seven routes under /data-service/mapping. `project` always travels in the JSON body (POST) or in the query (GET),
// because a connector session passes only when its bound project equals the requested project. Every call goes
// through apiFetch (session cookie, CSRF marker on POST), never a token. The pure helpers below hold the Mapping
// panel's data logic so that node tests can cover it without rendering.

import { apiFetch, dataServiceBase } from "./apiClient.js";

// Element and group states in progress order (contract §3 summary keys).
export const MAPPING_STATES = Object.freeze(["confirmed", "auto", "suggested", "ambiguous", "unmapped"]);
export const MAPPING_PLATFORMS = Object.freeze(["grasshopper", "revit"]);
// Server limit (MAPPING_TOO_MANY_ELEMENTS); checked before upload so the owner sees it at once.
export const MAX_ELEMENTS = 5000;
export const SESSION_LIMIT = 20;

function mappingUrl(path) {
  return `${dataServiceBase()}/mapping${path}`;
}

function projectQuery(project) {
  return `project=${encodeURIComponent(project)}`;
}

function sessionPath(sessionId) {
  return `/sessions/${encodeURIComponent(sessionId)}`;
}

// → { sessions: [MappingSessionSummary] }, newest first
export function listSessions(project, limit) {
  const extra = Number.isInteger(limit) && limit > 0 ? `&limit=${limit}` : "";
  return apiFetch(mappingUrl(`/sessions?${projectQuery(project)}${extra}`));
}

// → MappingSession (summary, questions, groups, elements)
export function getSession(project, sessionId) {
  return apiFetch(mappingUrl(`${sessionPath(sessionId)}?${projectQuery(project)}`));
}

// body = the parsed upload { platform, label?, elements, context? }. Only contract fields are sent and `project` is
// always the active project, whatever project the file names.
export function createSession(project, { platform, label, elements, context } = {}) {
  const body = { project, platform, elements };
  if (typeof label === "string" && label) body.label = label;
  if (context && typeof context === "object" && !Array.isArray(context)) body.context = context;
  return apiFetch(mappingUrl("/sessions"), { method: "POST", body });
}

// One decision per call → { decisions, profiles, session }. groupIds narrows a batch-assign answer to a subset.
export function postDecision(project, sessionId, { questionId, optionId, groupIds, roles, comment } = {}) {
  const body = { project, questionId, optionId };
  if (Array.isArray(groupIds)) body.groupIds = [...groupIds];
  if (Array.isArray(roles)) body.roles = [...roles];
  if (typeof comment === "string" && comment.trim()) body.comment = comment.trim();
  return apiFetch(mappingUrl(`${sessionPath(sessionId)}/decisions`), { method: "POST", body });
}

// → MappingApplyResult { applied, byClass, elements, skipped }
export function applySession(project, sessionId) {
  return apiFetch(mappingUrl(`${sessionPath(sessionId)}/apply`), { method: "POST", body: { project } });
}

// → { profiles: [MappingProfile] }
export function listProfiles(project) {
  return apiFetch(mappingUrl(`/profiles?${projectQuery(project)}`));
}

// Authored profile → MappingProfile
export function createProfile(project, { platform, selector, roles, comment } = {}) {
  const body = { project, platform, selector, roles };
  if (typeof comment === "string" && comment.trim()) body.comment = comment.trim();
  return apiFetch(mappingUrl("/profiles"), { method: "POST", body });
}

// ── pure helpers ────────────────────────────────────────────────────────────────────────────────────────────────

// The server sends canonical deterministic text in both languages (D-11, D-16): Russian for a Russian UI, English
// otherwise, and English when the Russian text is missing.
export function questionText(question, lang) {
  if (!question || typeof question !== "object") return "";
  if (lang === "ru" && typeof question.textRu === "string" && question.textRu) return question.textRu;
  return typeof question.text === "string" ? question.text : "";
}

function count(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 0;
}

// Five segments in MAPPING_STATES order; percent is relative to summary.total (or the sum when total is smaller).
export function progressSegments(summary) {
  const counts = MAPPING_STATES.map((state) => count(summary?.[state]));
  const sum = counts.reduce((a, b) => a + b, 0);
  const total = Math.max(count(summary?.total), sum);
  return MAPPING_STATES.map((state, i) => ({ state, count: counts[i], percent: total > 0 ? (counts[i] / total) * 100 : 0 }));
}

export function summaryTotals(summary) {
  const segments = progressSegments(summary);
  const sum = segments.reduce((a, s) => a + s.count, 0);
  return {
    total: Math.max(count(summary?.total), sum),
    mapped: count(summary?.confirmed) + count(summary?.auto),
    openQuestions: count(summary?.openQuestions)
  };
}

// Validates an uploaded descriptor file: the GH DryRun / Revit CLI upload body {project?, platform, label?, elements,
// context?} or a bare array of descriptors. → { body, count, fileProject } or { error } with error in
// json | elements | empty | too-many | descriptor | platform.
export function parseDescriptorUpload(text) {
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    return { error: "json" };
  }
  const source = Array.isArray(data) ? { elements: data } : data && typeof data === "object" ? data : null;
  if (!source || !Array.isArray(source.elements)) return { error: "elements" };
  const elements = source.elements;
  if (elements.length === 0) return { error: "empty" };
  if (elements.length > MAX_ELEMENTS) return { error: "too-many" };
  const ids = new Set();
  for (const element of elements) {
    const id = element && typeof element === "object" && !Array.isArray(element) ? element.nativeId : undefined;
    if (typeof id !== "string" || !id || ids.has(id)) return { error: "descriptor" };
    ids.add(id);
  }
  const declared = source.platform ?? elements[0].platform;
  if (!MAPPING_PLATFORMS.includes(declared)) return { error: "platform" };
  const body = { platform: declared, elements };
  if (typeof source.label === "string" && source.label.trim()) body.label = source.label.trim().slice(0, 120);
  if (source.context && typeof source.context === "object" && !Array.isArray(source.context)) body.context = source.context;
  const fileProject = typeof source.project === "string" && source.project ? source.project : null;
  return { body, count: elements.length, fileProject };
}

// Default session label from the uploaded file name.
export function labelFromFileName(name) {
  const base = String(name || "").replace(/\.json$/i, "").trim();
  return base.slice(0, 120);
}

// MappingSessionSummary = the session without questions, groups and elements (contract §3).
export function sessionSummary(session) {
  if (!session || typeof session !== "object") return null;
  const { questions, groups, elements, ...summary } = session;
  return summary;
}

// Replaces the session's entry in the list, or puts a new one first (the list is newest first).
export function upsertSession(list, session) {
  const summary = sessionSummary(session);
  const items = Array.isArray(list) ? list : [];
  if (!summary || !summary.sessionId) return items;
  if (items.some((s) => s.sessionId === summary.sessionId)) {
    return items.map((s) => (s.sessionId === summary.sessionId ? { ...s, ...summary } : s));
  }
  return [summary, ...items];
}

// Profiles returned by a decision replace their old version in place; new profiles go first.
export function mergeProfiles(list, updates) {
  const items = Array.isArray(list) ? list : [];
  const fresh = (Array.isArray(updates) ? updates : []).filter((p) => p && typeof p.profileId === "string");
  const byId = new Map(fresh.map((p) => [p.profileId, p]));
  const kept = items.map((p) => (byId.has(p.profileId) ? byId.get(p.profileId) : p));
  const known = new Set(items.map((p) => p.profileId));
  return [...fresh.filter((p) => !known.has(p.profileId)), ...kept];
}

// Option ids of contract §3: accept-all | class:<iri> | design-error:<iri> | both | split:<feature> | none.
export function optionKind(optionId) {
  const id = typeof optionId === "string" ? optionId : "";
  if (id === "accept-all" || id === "both" || id === "none") return { kind: id, arg: "" };
  for (const kind of ["class", "design-error", "split"]) {
    if (id.startsWith(`${kind}:`) && id.length > kind.length + 1) return { kind, arg: id.slice(kind.length + 1) };
  }
  return { kind: "other", arg: id };
}

// "ex:GroundFloorUnit" → "GroundFloorUnit"; "http://x/onto#Wall" → "Wall".
export function classLocalName(iri) {
  const text = String(iri ?? "");
  const local = text.split(/[#/:]/).pop();
  return local || text;
}

// classIri → label from every group candidate of the session.
export function classLabels(session) {
  const labels = new Map();
  for (const group of Array.isArray(session?.groups) ? session.groups : []) {
    for (const candidate of Array.isArray(group?.candidates) ? group.candidates : []) {
      if (candidate?.classIri && candidate.label && !labels.has(candidate.classIri)) labels.set(candidate.classIri, candidate.label);
    }
  }
  return labels;
}

// Batch-assign: the question's groups minus the excluded ones, in question order.
export function includedGroupIds(question, excluded) {
  const skip = new Set(Array.isArray(excluded) ? excluded : []);
  return (Array.isArray(question?.groupIds) ? question.groupIds : []).filter((id) => !skip.has(id));
}

// Flattens question consequences into table rows: option → rule → effect × count.
export function consequenceRows(question) {
  const rows = [];
  for (const entry of Array.isArray(question?.consequences) ? question.consequences : []) {
    for (const rule of Array.isArray(entry?.rules) ? entry.rules : []) {
      rows.push({ optionId: entry.optionId, ruleId: rule?.ruleId ?? "", effect: rule?.effect ?? "", count: count(rule?.count) });
    }
  }
  return rows;
}

// Per-class counts of an apply result, largest first, ties by class iri.
export function appliedByClass(result) {
  const entries = Object.entries(result?.byClass && typeof result.byClass === "object" ? result.byClass : {});
  return entries
    .map(([classIri, ids]) => ({ classIri, count: Array.isArray(ids) ? ids.length : 0 }))
    .sort((a, b) => b.count - a.count || (a.classIri < b.classIri ? -1 : a.classIri > b.classIri ? 1 : 0));
}

// Selector / signature chips: "key=value".
export function selectorEntries(selector) {
  if (!selector || typeof selector !== "object") return [];
  return Object.entries(selector).map(([key, value]) => `${key}=${value !== null && typeof value === "object" ? JSON.stringify(value) : String(value)}`);
}

export function confidencePercent(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `${Math.round(n * 100)}%` : "—";
}
