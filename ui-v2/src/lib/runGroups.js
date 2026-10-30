export const NO_STATE = "__no_state__";

// Phase 1303-26 (D-81, D-82): a model snapshot (the «Снимок модели» a confirmed mapping created) is a group even before
// any check joined it; snapshot groups come first, newest first, then the other states as before.
export function groupRunsByState(runs, snapshots = []) {
  const buckets = new Map();
  for (const s of snapshots || []) {
    if (s?.stateId && !buckets.has(s.stateId)) buckets.set(s.stateId, { key: s.stateId, state: s, snapshot: s, runs: [] });
  }
  for (const r of runs) {
    const key = r.state?.stateId || NO_STATE;
    if (!buckets.has(key)) buckets.set(key, { key, state: r.state, runs: [] });
    buckets.get(key).runs.push(r);
  }
  const order = new Map((snapshots || []).map((s, i) => [s?.stateId, i]));
  const arr = [...buckets.values()];
  arr.sort((a, b) => {
    const sa = order.has(a.key), sb = order.has(b.key);
    if (sa || sb) return sa && sb ? order.get(a.key) - order.get(b.key) : sa ? -1 : 1;
    return (a.key === NO_STATE) - (b.key === NO_STATE) || a.key.localeCompare(b.key);
  });
  return arr;
}
