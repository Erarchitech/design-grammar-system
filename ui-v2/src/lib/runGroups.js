export const NO_STATE = "__no_state__";

export function groupRunsByState(runs) {
  const buckets = new Map();
  for (const r of runs) {
    const key = r.state?.stateId || NO_STATE;
    if (!buckets.has(key)) buckets.set(key, { key, state: r.state, runs: [] });
    buckets.get(key).runs.push(r);
  }
  const arr = [...buckets.values()];
  arr.sort((a, b) => (a.key === NO_STATE) - (b.key === NO_STATE) || a.key.localeCompare(b.key));
  return arr;
}
