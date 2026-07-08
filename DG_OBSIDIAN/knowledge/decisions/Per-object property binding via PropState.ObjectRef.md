---
tags: [decision, architecture]
date: 2026-07-08
---

# Per-object property binding via PropState.ObjectRef

## Decision

PropState gains an optional `ObjectRef` field linking a property value to a specific
object instance (ObjState.ObjectRef). When set, the binder applies the value only to
the matching object's binding row. When null, the legacy broadcast-to-all-rows behavior
is preserved (full backward compatibility).

## Why

The pre-v7.0 binding model was rule-scoped: one PropState broadcast one property value
to ALL object binding rows (e.g. one height applied to all buildings). Per-object
validation ("building A = 60m pass, building B = 84m fail") was impossible.

The user's canvas had 57 building instances each with a distinct height, wired as
parallel lists. The position in the geometry list and the height list encodes the
object↔value relationship.

## How

**Core:**
- `PropState.ObjectRef` (string?, optional) — matches `ObjState.ObjectRef`
- `DesignStateBindingService.ApplyPropertyValues`: when `ObjectRef` is set, filter rows
  by `RowMatchesObjectRef(row, objectRef)`; else broadcast (unchanged)
- `DesignStateIdGenerator.ComputePropStateId`: fold `ObjectRef` into SHA256 hash —
  two objects sharing the same value no longer MERGE-collide in Neo4j
- `DesignStatePayloadV2Serializer`: round-trip `objectRef` in PropStateDto (additive,
  no envelope version bump)

**Grasshopper:**
- PROPERTY STATE: new optional **ObjState** input (list), paired positionally with
  PropValue. Each PropState is stamped with its ObjState's `ObjectRef`.
- OBJECT STATE: single OntologyClass on Object input is now **broadcast** as shared
  ClassIri across all geometry instances. Each ObjState gets a UNIQUE ObjectRef:
  explicit per-instance ref → geometry reference GUID → `obj_{i}` fallback.

## Impact

- 14 files changed (10 source + 4 test)
- 5 new tests (per-object binding, broadcast fallback, id collision, id compat, serializer round-trip)
- Zero breaking changes — all existing tests pass unchanged
- No Neo4j migration, no envelope version bump

## Related

- [[decisions/Phase 18 Rules and Validator Rework decisions]]
- [[sessions/2026-07-08 Per-object property binding and Speckle auto-config]]
