---
date: 2026-07-04
phase: 16
tags: [decision, v7.0, state-models, serialization]
---

# Phase 16: DesignState aggregate model + statePayloadJson v2

**Контекст:** `/gsd-discuss-phase 16` — four gray areas discussed.

## D-01: DESIGN STATE = aggregate (one snapshot)

All wired ObjStates + all ParamStates + all PropStates fold into **one** DesignState. Output is a single DesignState, not a list. The three inputs are **independent bags** — no cross-index alignment. VALIDATOR (Phase 18) parses each list separately per SWRL rule.

Objs and Props are NOT index-aligned: many Rules can apply to one Object; a property value lives within a single PropState bound to a specific Rule.

**Index-mismatch guard**: lives in leaf components (OBJECT STATE: Object/Geometry/Label same-length; PROPERTY STATE: parallel value lists same-length). DESIGN STATE has no cross-input length rule.

## D-02: DesignState.StateId = hash of member StateIds

`DS_` + SHA-256(sorted `OS_xxx` + `DS_xxx` + `PS_yyy` concatenated) → 16-char hex. Same members → same StateId → dedup across runs (MERGE by StateId+project per Phase 13 D-03). Natural extension of the existing `DesignStateIdGenerator` pattern.

## D-03: statePayloadJson v2 — versioned envelope, clean break

```json
{
  "version": "2",
  "stateId": "DS_<hex16>",
  "capturedAtUtc": "<ISO 8601>",
  "objStates": [ ... ],
  "paramStates": [ ... ],
  "propStates": [ ... ]
}
```

Explicit `version` discriminator. **No v1 fallback** — pre-v7.0 runs with v1 payloads are Phase 18's read-side tolerance (GHVL-06).

## D-04: PropValue = typed Number/Integer/Boolean scalar

Same type system as `DesignStateParameter`. Rule and DataProperty stored as **plain string refs** (IRIs). PropState is **rule-scoped** — one component = one Rule + one DataProperty + one value. StateId = `PS_` + SHA-256(Rule IRI + DataProperty IRI + PropValue). New method `ComputePropStateId()` in `DesignStateIdGenerator`.

## D-05: Rename DESIGN STATE → PARAMETER STATE now

- Delete `DefState.cs`, `ObjectState.cs`, `ObjectInstance.cs` (unused scaffolding)
- DESIGN STATE component renamed to PARAMETER STATE (new GUID replaces `B3D1E7F2-...`)
- `DesignStateSnapshot` → `ParamState` model rename
- `ComputeDefStateId` → `ComputeParamStateId` (same logic, same `DS_` prefix)
- v7.0 is a breaking-change milestone — old canvases break, release notes cover rewiring at Phase 20

## Связанные решения
- [[DesignState persists to ValidGraph not Metagraph]] — Phase 13 D-01/D-03 (where DesignState lives, MERGE semantics)
- [[Run ValidStatus is a per-object boolean array]] — Phase 13 D-06/D-07 (per-ObjState Boolean list, no Status text)
- [[Ontology V7 full rename over incremental]] — Phase 13 state-kind names, PS_ prefix

## См. также
- [[sessions/2026-07-04 Phase 16 discuss - DG.Core state models and state components|Session note]]
- `.planning/phases/16-dg-core-state-models-and-state-components/16-CONTEXT.md` — full context for planner
