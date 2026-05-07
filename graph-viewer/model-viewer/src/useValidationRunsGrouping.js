/**
 * Pure grouping adapter for validation runs.
 * Phase 05 / MVGP-01, MVGP-02.
 *
 * NOTE: Despite the name `useX`, this is a pure function (not a React hook).
 * The naming follows the codebase convention of "useFoo" for derivation helpers.
 * Callers can wrap in React.useMemo for memoization.
 */

const NO_RULE = "__no_rule__";
const NO_STATE = "__no_state__";
const NO_RULE_LABEL = "No Rule";
const NO_STATE_LABEL = "No State";

function deriveRuleKey(run) {
  const first = Array.isArray(run.ruleIds) && run.ruleIds.length > 0 ? run.ruleIds[0] : "";
  if (!first) return { key: NO_RULE, label: NO_RULE_LABEL };
  return { key: first, label: first };
}

function deriveStateKey(run) {
  const stateId = run.state && typeof run.state.stateId === "string" ? run.state.stateId : "";
  if (!stateId) return { key: NO_STATE, label: NO_STATE_LABEL };
  return { key: stateId, label: stateId };
}

function parseTimestamp(value) {
  if (!value) return 0;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : 0;
}

function compareRuns(a, b) {
  const ta = parseTimestamp(a.createdAt);
  const tb = parseTimestamp(b.createdAt);
  if (tb !== ta) return tb - ta; // DESC by time
  return (a.runId || "").localeCompare(b.runId || "", undefined, { sensitivity: "variant" });
}

function compareGroups(a, b) {
  // __no_X__ buckets always last
  const aIsBucket = a.groupKey === NO_RULE || a.groupKey === NO_STATE;
  const bIsBucket = b.groupKey === NO_RULE || b.groupKey === NO_STATE;
  if (aIsBucket && !bIsBucket) return 1;
  if (!aIsBucket && bIsBucket) return -1;
  if (aIsBucket && bIsBucket) return 0;
  return a.groupKey.localeCompare(b.groupKey, undefined, { sensitivity: "variant" });
}

export function useValidationRunsGrouping(runs, mode) {
  if (!Array.isArray(runs) || runs.length === 0) return [];
  const resolvedMode = mode === "state" ? "state" : "rule";
  const deriver = resolvedMode === "state" ? deriveStateKey : deriveRuleKey;

  const buckets = new Map();
  for (const run of runs) {
    const { key, label } = deriver(run);
    if (!buckets.has(key)) {
      buckets.set(key, { groupKey: key, groupLabel: label, runs: [] });
    }
    buckets.get(key).runs.push(run);
  }

  const groups = Array.from(buckets.values());
  for (const g of groups) g.runs.sort(compareRuns);
  groups.sort(compareGroups);
  return groups;
}
