---
tags: [debugging, grasshopper, designstate, validator, fixed]
date: 2026-10-05
status: fixed-2026-10-05
---

# DESIGN STATE and VALIDATOR assumed one class per Design State (F15, F16)

## Symptoms (test v12-hexagonal-facade-01, step 5)

- **F15.** DESIGN STATE refused the composition: "PropState list length (976) does not match ObjState list length (376)". VALIDATOR then received an empty state, and all 11 rules reported `NO PASS: empty binding population`. One Design State carried 11 rules over 5 classes, so several rules applied to the same objects. For example, GlassPanel has 4 rules, which gives 500 PropStates for 125 objects.
- **F16.** VALIDATOR filled `ValidStatus[i]` from `bindings[i]`. Binding rows exist only for ObjStates of the rule's class, so a rule on the second class (R3 on `HexagonalUnit`) had its statuses written onto the GlassPanel slots 0–99. The same list is stored as `Run.ValidStatus` in ValidGraph. Publishing to Speckle was not affected, because it is keyed by `DgEntityId`.

## Cause

Both are leftovers of positional pairing. The binder never pairs by index: a PropState with an `ObjectRef` binds to that object's row, and one without is broadcast (`DesignStateBindingService.ApplyPropertyValues`). Rows are built only from ObjStates whose `ClassIri` matches.

## Fix (TDD, DG.Core predicates the components call)

- `DesignStateGuard.IsPropObjCountMismatch` checks lengths only for **unlinked** PropStates. The message now names the unlinked count and the fix.
- `BindingRow.SourceObjStateIndex` is set by the binder. `ValidStatusMapper.PerObjState` places each row on its source ObjState.
- Tests: `DesignStateGuardTests` (6), `ValidStatusMapperTests` (2).
- Verified live: DESIGN STATE gives `376O/1P/976Pr`, V1 gives 11/11 PASS, and the ValidStatus `true` values sit exactly on each class's slots. In ValidGraph, R3/V1 has `true` at 125–224.

## Related

- [[knowledge/debugging/OBJECT STATE index ObjectRefs collide across classes for computed geometry]]: ObjectRefs repeat across classes (`obj_0` …), which is why the mapper uses the source index and not `ObjectRef`.
- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]
