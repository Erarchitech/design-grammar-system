# Phase 16: DG.Core State Models and State Components - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 16-dg-core-state-models-and-state-components
**Areas discussed:** DESIGN STATE composition semantics, statePayloadJson v2 shape, PropState value model, Scaffolding removal scope

---

## DESIGN STATE — Composition Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Aggregate → one DesignState | All ObjStates + ParamStates + PropStates fold into ONE snapshot. Single DesignState output. Index-mismatch guard on a specific pairing. | ✓ |
| Index-zip → list of DesignStates | Three parallel lists: index i of each → DesignState #i. Output = list(DesignState). Mismatch = unequal lengths → error. | |
| You decide | Pick aggregate as domain-correct default | |

**User's choice:** Aggregate → one DesignState. The three inputs are independent bags — no cross-index alignment. VALIDATOR treats each separately, parsing DesignState and retrieving necessary objects and properties for the validated SWRL Rule. ObjState and PropState outputs are NOT aligned by index. Many Rules can apply to a single Object; property lives within a single PropState aligned with a specific Rule.

**Notes:** This is a significant design clarification — the port map says `list(DesignState())` as output, but the domain model is one snapshot aggregating heterogeneous state types. The list() notation in the port map reflects the internal lists inside the DesignState, not N DesignState outputs.

### Index-Mismatch Guard Placement

| Option | Description | Selected |
|--------|-------------|----------|
| In OBJECT STATE (+PROPERTY STATE) | Parallel-list guard where the parallel wiring actually is. DESIGN STATE treats inputs as independent bags. | |
| In DESIGN STATE (obj↔prop pairing) | ObjState count == PropState count enforced at DESIGN STATE level. | |
| You decide | Default to guard-in-OBJECT-STATE/PROPERTY-STATE; researcher to confirm against PDF. | ✓ |

**User's choice:** "ObjState and PropState are not aligned by index. All 3 outputs are not aligned by index. Validator treats each separately." — this confirms the guard lives in the leaf components (OBJECT STATE's Object/Geometry/Label same-length; PROPERTY STATE's parallel value lists), not in DESIGN STATE.

---

## statePayloadJson v2 — Serialization Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Versioned envelope, clean break | `{version, stateId, capturedAtUtc, objStates[], paramStates[], propStates[]}`. No v1 fallback. | ✓ |
| Versioned envelope + v1 fallback | Same but deserializes legacy `parameters[]` payloads if version==1. | |
| Implicit version, clean break | No version field; presence of objStates/propStates IS the signal. | |

**User's choice:** Versioned envelope, clean break. v2 only — pre-v7.0 run read-side tolerance is Phase 18's concern.

### DesignState.StateId Computation

| Option | Description | Selected |
|--------|-------------|----------|
| Hash of member StateIds | Deterministic hash over sorted OS_xxx + DS_xxx + PS_yyy. Same members → same DesignState. | ✓ |
| DS_ prefix + new GUID | Every composition unique regardless of members. | |
| You decide | Use deterministic hash. | |

**User's choice:** Hash of member StateIds — natural extension of the existing DesignStateIdGenerator pattern.

---

## PropState — Value Model

| Option | Description | Selected |
|--------|-------------|----------|
| Typed scalar (Num/Int/Bool) | PropValue = Number/Integer/Boolean, same type system as DesignStateParameter. | ✓ |
| Per-object list (ObjState-aligned) | PropState[i].value ↔ ObjState[i] in the same DesignState. Conflicts with aggregate model. | |
| Free-form string | Any calculated value as text. | |

**User's choice:** Typed Number/Integer/Boolean scalar. Matches the existing typed-state contract.

### Rule/DataProperty Referencing

| Option | Description | Selected |
|--------|-------------|----------|
| Plain string refs | Rule and DataProperty stored as IRI strings. | ✓ |
| Hybrid: structured Rule + string IRI | Rule as full object, DataProperty as string. | |
| You decide | Use plain string IRIs. | |

**User's choice:** Plain string refs — consistent with ObjState's ObjectRef string pattern and ParamState's parameter name strings.

---

## Scaffolding Removal & Component Rename

| Option | Description | Selected |
|--------|-------------|----------|
| Rename now, accept breakage | Delete scaffolding. Rename DESIGN STATE → PARAMETER STATE + DesignStateSnapshot → ParamState now. Old canvases break. | ✓ |
| Add new + keep old (dual) | New PARAMETER STATE with new GUID; old DESIGN STATE compiles alongside. Phase 18 deletes old. | |
| You decide | Rename now — v7.0 is explicitly a breaking-change milestone. | |

**User's choice:** Rename now, accept breakage. Clean break — the v2.0 DESIGN STATE component's capture logic is the direct behavioral predecessor of v7.0 PARAMETER STATE.

---

## Claude's Discretion

- Exact per-entity serialized field mapping within the v2 envelope
- Whether the v2 serializer is a new `DesignStatePayloadSerializer` class or a rework of the existing `DesignStateJsonSerializer`
- Error message wording for index-mismatch guards (follow `ErrorMessageTemplates` pattern)
- Whether `OI_` prefix is removed with `ObjectInstance` deletion or kept as reserved
- Internal list ordering within the DesignState model

## Deferred Ideas

None — discussion stayed within phase scope.
