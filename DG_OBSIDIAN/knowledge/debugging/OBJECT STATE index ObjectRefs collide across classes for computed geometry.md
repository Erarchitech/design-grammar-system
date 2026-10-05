---
tags: [debugging, grasshopper, objstate, identity, open]
date: 2026-10-03
status: open-observed-in-code
---

# OBJECT STATE index ObjectRefs collide across classes for computed geometry

## Symptom (expected, from code reading — not yet reproduced live)

When computed (non-referenced) geometry is fed to OBJECT STATE together with a single `OntologyClass` broadcast, every instance gets `ObjectRef = obj_0 … obj_n` from its list index. A canvas with several populations (for example `GlassPanel` and `HexagonalUnit`, each with its own OBJECT STATE) therefore issues the same `obj_3` to two different objects.

## Cause

In `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs`, the priority is: explicit per-instance ref → geometry `ReferenceID` → `obj_{i}`. Only an `OntologyClass` gives a `ClassIri`. A per-item string or `ElementRef` gives identity but **no** class, and binding requires a class (`DesignStateBindingService` skips ObjStates whose `ClassIri` is null). The component has no input that carries **both** a class and a per-instance id. Parametric (unbaked) geometry has no `ReferenceID`.

## Impact

- Within one VALIDATOR run there is no collision: `Rule` is an item, so one run covers one rule and one class.
- Possible cross-run and cross-class ambiguity in published `dgEntityId`s, Model Viewer highlighting and ValidationEntity rows. This is to be observed in step 7 of the facade test.
- Identity is index-based, so it is not stable across variants: if the panel count changes, `obj_3` refers to a different panel.

## Possible fixes (not decided)

1. Add an optional `Id` list input to OBJECT STATE that is used together with the broadcast class.
2. Accept `OntologyClass` + `ElementRef` pairs per item.
3. Prefix the index ref with the class local name (`GlassPanel/obj_3`). This fixes the collision only, not stability.

Related: [[knowledge/decisions/Per-object property binding via PropState.ObjectRef]], [[sessions/2026-10-04 v12 hexagonal facade full-cycle test setup]]

## Observed in the facade test (2026-10-05)

- No wrong colouring in Model Viewer: publish is per run (one rule, one class), and the owner confirmed the highlighting.
- The collision did bite **inside VALIDATOR**: the ValidStatus mapping could not use `ObjectRef` (GP `obj_0` and HU `obj_0` coexist in one Design State), so F16 was fixed with the binder's source ObjState index. See [[knowledge/debugging/DESIGN STATE and VALIDATOR assumed one class per Design State]].
- Index identity is not stable across variants: changing `Module Width F1` changes the panel count (125 → 140 → 105) and shifts every index (finding F8).
