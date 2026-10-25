// The object sets of a validation view (/validation/view objectSets), classified for the Model Viewer.
// Phase 1303-25 (D-71): `unknown` holds objects without a verdict (e.g. no data to measure against); they are drawn
// and listed apart from failing and passing objects. A payload without `unknown` behaves as before.

const toItem = (e) => ({ id: e.dgEntityId, primary: e.displayName || e.dgEntityId, secondary: "id: " + e.dgEntityId });

export function classifyObjectSets(objectSets) {
  const failed = objectSets?.failed || [];
  const passed = objectSets?.passed || [];
  const unknown = objectSets?.unknown || [];
  const failedSet = new Set(failed.map((e) => e.dgEntityId));
  const unknownSet = new Set(unknown.map((e) => e.dgEntityId));
  const entities = [...failed, ...passed, ...unknown].sort((a, b) => a.dgEntityId.localeCompare(b.dgEntityId));
  return {
    failedIds: failed.map((e) => e.dgEntityId),
    passedIds: passed.map((e) => e.dgEntityId),
    unknownIds: unknown.map((e) => e.dgEntityId),
    entities,
    failItems: failed.map(toItem),
    passItems: passed.map(toItem),
    unknownItems: unknown.map(toItem),
    statusOf: (id) => (failedSet.has(id) ? "failed" : unknownSet.has(id) ? "unknown" : "passed"),
  };
}
