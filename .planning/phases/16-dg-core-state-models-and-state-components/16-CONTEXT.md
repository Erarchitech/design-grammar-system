# Phase 16: DG.Core State Models and State Components - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure-logic C# models (`ObjState`, `ParamState`, `PropState`, `DesignState`) plus `statePayloadJson` v2 serializer in `DG.Core`, plus four Grasshopper capture/compose components (OBJECT STATE, PARAMETER STATE, PROPERTY STATE, DESIGN STATE).

**No graph reads, persistence, or validation** — those are Phases 17–18. The DESIGN STATE model is defined here; its persistence (into `graph='ValidGraph'` via VALIDATOR) belongs to Phase 18.

**Already locked upstream (do NOT re-open):**
- State-kind names `ObjState` / `ParamState` / `PropState`; ID prefixes `DS_` / `OS_` / `OI_` / `PS_` — Phase 13
- Port↔IRI contract for all 4 components — `ontology/port-iri-map-V7.md` (Phase 13)
- DesignState lives in `graph='ValidGraph'`, written only by VALIDATOR on publish, `MERGE`'d by StateId+project — D-01/D-03 Phase 13
- No orphan DesignStates — always has ≥1 linked Run — D-05 Phase 13
- ObjectRef = user-supplied string (the Label input); geometry NOT hashed/serialized — PROJECT.md
- Params stay Number/Integer/Boolean; deterministic SHA-256 StateId preserved — v2.0 decision
- `DesignStateParameter` model stays unchanged (typed param contract carries forward)
</domain>

<decisions>
## Implementation Decisions

### DESIGN STATE — Composition Semantics
- **D-01:** DESIGN STATE is an **aggregate** — all wired ObjStates + all ParamStates + all PropStates fold into **one** DesignState snapshot. Output is a single DesignState (not a list), consistent with the SC#3 "composes into A DesignState" wording. A full design alternative = N objects + M params + K property values.
- **D-02:** The three DESIGN STATE inputs (ObjState, ParamState, PropState) are **independent bags** — no cross-index alignment between them. 3 objects + 5 params + 2 props → one DesignState with three separate internal lists. VALIDATOR (Phase 18) parses each list separately per the SWRL rule under evaluation.
- **D-03:** **Index-mismatch guard lives in the parallel-list leaf components, not in DESIGN STATE.** OBJECT STATE enforces Object/Geometry/Label same-length (each index i needs all three). PROPERTY STATE enforces its parallel value lists same-length. DESIGN STATE treats its three inputs as independent bags (no cross-length rule). This aligns with the domain model: ObjState and PropState are NOT index-aligned — many rules can apply to one object, and property values live within single PropStates aligned with specific Rules.
- **D-04:** **DesignState.StateId = deterministic hash over sorted member StateIds.** Input: sorted `OS_xxx` + `DS_xxx` + `PS_yyy` concatenated. SHA-256 → 16-char hex, `DS_`-prefixed via DesignStateIdGenerator. Same members → same StateId → dedup across runs (MERGE by StateId+project per D-03 Phase 13). Natural extension of the existing DesignStateIdGenerator pattern.

### statePayloadJson v2 — Serialization Contract
- **D-05:** **Versioned envelope:**
  ```json
  {
    "version": "2",
    "stateId": "DS_<hex16>",
    "capturedAtUtc": "<ISO 8601 round-trip>",
    "objStates": [ ... ],
    "paramStates": [ ... ],
    "propStates": [ ... ]
  }
  ```
  Explicit `version` discriminator. Per-entity fields inside each sub-array follow the CORE-01/02/03 models.
- **D-06:** **Clean break — no v1 deserialization fallback.** v2 serializer only handles `version: "2"`. Pre-v7.0 runs with v1 payloads are Phase 18's read-side tolerance concern (GHVL-06: _project_state_summary and /validation/runs projection adapted, v1-payload runs still render).
- **D-07:** **New/reworked serializer class in `DG.Core.Serialization`** — replaces the v1 `DesignStateJsonSerializer` pattern. The old serializer only handles the flat `DesignStateSnapshot` (now `ParamState`); the new serializer handles the full 3-part composition.

### PropState — Value Model
- **D-08:** **PropValue = typed Number/Integer/Boolean scalar** — same type system as `DesignStateParameter`. One calculated value per PROPERTY STATE component. Matches the existing typed-state contract (Number/Integer/Boolean limit still holds per PROJECT.md out-of-scope).
- **D-09:** **Rule and DataProperty stored as plain string references** (IRIs, e.g. `dgm:Rule_R_URB_HEIGHT_MAX_75_V`, `dg:hasHeight`). Simple, serializable, sufficient for VALIDATOR to look up.
- **D-10:** **PropState is rule-scoped.** One PROPERTY STATE component = one Rule + one DataProperty + one value → one PropState. Multiple properties across different rules = multiple PropState instances, all wired to DESIGN STATE's PropState input.
- **D-11:** **PropState.StateId = `PS_` + deterministic SHA-256 hash** (following existing `DesignStateIdGenerator` pattern). Hash input = concatenated Rule IRI + DataProperty IRI + PropValue. Add `ComputePropStateId()` to `DesignStateIdGenerator`.

### Scaffolding Removal & Component Rename
- **D-12:** **Delete `DefState.cs`, `ObjectState.cs`, `ObjectInstance.cs`** — zero call sites, marked as unused v3.0 scaffolding. No migration shim needed.
- **D-13:** **Rename DESIGN STATE → PARAMETER STATE.** New component name, new GUID (replaces `B3D1E7F2-A945-4C8B-B6F0-1A0D3C4E9B72`). Old canvases break — v7.0 is a breaking-change milestone; release notes cover rewiring at Phase 20.
- **D-14:** **Rename `DesignStateSnapshot` → `ParamState` model.** Same fields: StateId, CapturedAtUtc, Collection<DesignStateParameter>. The capture logic in the component is unchanged (variable-input pattern, NickName→ParameterId, typed scalars).
- **D-15:** **`DesignStateIdGenerator` adapted:**
  - `ComputeDefStateId` → `ComputeParamStateId` (same logic, same `DS_` prefix)
  - Add `ComputePropStateId` (`PS_` prefix per D-11)
  - `ComputeObjectStateId` unchanged (`OS_` prefix, existing)
  - `ComputeObjectInstanceId` — remove if `ObjectInstance` is deleted (OI_ prefix unused); researcher to verify no hidden call sites

### Claude's Discretion
- Exact per-entity serialized field mapping within the v2 envelope (field names, ordering)
- Whether the v2 serializer is a new `DesignStatePayloadSerializer` class or a rework of the existing `DesignStateJsonSerializer`
- Error message wording for index-mismatch guards (follow `ErrorMessageTemplates` What+Where+How-to-fix pattern)
- Whether `OI_` prefix is removed with `ObjectInstance` deletion or kept as reserved
- Internal list ordering within the DesignState model (preserve wiring order vs sorted)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Component contract & ontology
- `ontology/GH_DesignGrammars.pdf` — the 14-component schema; component wiring diagrams for OBJECT STATE, PARAMETER STATE, PROPERTY STATE, DESIGN STATE
- `ontology/port-iri-map-V7.md` — per-port IRI contract for all four state components (grep for `OBJECT STATE|PARAMETER STATE|PROPERTY STATE|DESIGN STATE`)
- `ontology/DesignGrammar-V7.owl` — V7 ontology: `dg:ObjState`, `dg:ParamState`, `dg:PropState`, `dg:DesignState` classes; `dgv:propValue`/`dgv:propValueOf` properties; `dgv:objectRefName`; `dgm:Rule`; `dg:DataProperty`
- `ontology/V7-INVESTIGATION.md` — conflict resolutions (a)/(b)/(c), final state-kind names, `PS_` prefix decision

### Existing code to adapt or replace
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — existing deterministic hash pattern (SHA-256, 16-char hex, `DS_/OS_/OI_` prefixes); add `ComputePropStateId` and `ComputeDesignStateId`, rename `ComputeDefStateId` → `ComputeParamStateId`
- `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs` — v1 serializer to adapt into v2; `SnapshotDto`/`ParameterDto` DTO pattern, camelCase policy, validation logic
- `DG/src/DG.Core/Models/DesignStateParameter.cs` — typed param model (Number/Integer/Boolean, typed nullable value fields) — reused unchanged by both ParamState and PropState
- `DG/src/DG.Core/Models/ElementRef.cs` — `DgEntityId` + `Geometry` + `DisplayName` — geometry reference contract for ObjState
- `DG/src/DG.Grasshopper/Components/DesignStateComponent.cs` — v2.0 DESIGN STATE component to rename into PARAMETER STATE; `IGH_VariableParameterComponent` pattern, `UnwrapScalar`/`BuildParameter` helpers, NickName→ParameterId logic
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — shared GH value unwrapping pattern (used by all state components)
- `DG/src/DG.Grasshopper/PublicTypes.cs` — public type wrappers for cross-component Grasshopper data — add wrappers for ObjState/ParamState/PropState/DesignState
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — error message pattern (What+Where+How-to-fix); extend for index-mismatch guards

### Models to delete
- `DG/src/DG.Core/Models/DefState.cs` — unused v3.0 scaffolding (DELETE)
- `DG/src/DG.Core/Models/ObjectState.cs` — unused v3.0 scaffolding (DELETE)
- `DG/src/DG.Core/Models/ObjectInstance.cs` — unused v3.0 scaffolding (DELETE)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — CORE-01..05 (state models), GHST-01..04 (state components)
- `.planning/ROADMAP.md` — Phase 16 goal + 4 success criteria
- `.planning/PROJECT.md` — key decisions: typed state limited to Number/Integer/Boolean, ObjectRef = user-supplied string (not geometry-hash), DesignStateIdGenerator prefixes

### Prior phase context (decisions carried forward)
- `.planning/phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` — D-01 through D-11: DesignState layer placement (ValidGraph), MerGE by StateId+project, no-orphan invariant, ValidStatus per-ObjState Boolean array, PS_ prefix, V7 ontology names
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`DesignStateIdGenerator`** (`DG.Core.Services`): SHA-256 → 16-char hex pattern. Three existing methods (`ComputeDefStateId`, `ComputeObjectStateId`, `ComputeObjectInstanceId`). Add `ComputePropStateId` and `ComputeDesignStateId`; rename `ComputeDefStateId` → `ComputeParamStateId`. Pure static logic, testable without GH SDK.
- **`DesignStateParameter`** (`DG.Core.Models`): Typed (Number/Integer/Boolean) with nullable per-type value fields, `ParameterId`, `DisplayName`. Reused as-is by both `ParamState` and `PropState` — no model changes needed.
- **`DesignStateComponent`** (`DG.Grasshopper.Components`): `IGH_VariableParameterComponent` pattern (add/remove inputs at runtime, NickName → ParameterId), `UnwrapScalar` (IGH_Goo → native .NET scalar), `BuildParameter` (scalar → typed DesignStateParameter). Rename to `ParameterStateComponent`, change output type to `ParamState`. Core capture logic is unchanged.
- **`ElementRef`** (`DG.Core.Models`): `DgEntityId` + `Geometry` + `DisplayName` — the geometry attachment contract for ObjState.
- **`ErrorMessageTemplates`** (`DG.Core.Services`): Static class with What+Where+How-to-fix templates. Extend with index-mismatch errors for OBJECT STATE and PROPERTY STATE.

### Established Patterns
- **Deterministic StateId via SHA-256**: Every state entity gets a content-addressed ID — identical inputs → identical ID. ParamState (was DesignStateSnapshot) already follows this. Extend to PropState and DesignState.
- **Typed nullable value fields**: `DesignStateParameter` uses `double? NumberValue` / `long? IntegerValue` / `bool? BooleanValue` — exactly one is set per parameter. PropValue reuses the same pattern.
- **`IGH_VariableParameterComponent`**: Grasshopper's dynamic-input pattern — user right-clicks "Add input" to add parameter sockets. PARAMETER STATE keeps this; OBJECT STATE and PROPERTY STATE are fixed-input.
- **`#if GRASSHOPPER_SDK` guards**: All GH-dependent code in DG.Grasshopper is conditional-compilation guarded. Models in DG.Core are not — they're pure logic multi-targeting net7.0+net9.0.

### Integration Points
- **Phase 17 (Graph Access Components)**: VALIDATION GRAPH outputs `DesignState` objects read from ValidGraph — consumes the DesignState model defined here.
- **Phase 18 (Rules and Validator Rework)**: VALIDATOR accepts DesignState input and parses its three lists separately per SWRL rule; writes statePayloadJson v2 on publish. CLASSIFICATOR (and its VariableBinder dependency) is deleted in Phase 18 — do NOT remove VariableBinder in this phase.
- **Phase 19 (Deconstruct and Reinstate)**: DESIGN STATE DECONSTRUCT splits DesignState back into ObjState/ParamState/PropState lists; OBJECT DECONSTRUCT splits ObjState; PARAMETER REINSTATE reads ParamState. All consume the models defined here.
- **data-service** (Python, Phase 18): `_project_state_summary` and `/validation/runs` projection adapted to statePayloadJson v2.
</code_context>

<specifics>
## Specific Ideas

- The user explicitly described the **VALIDATOR's consumption pattern**: "Validator treats each of them separately parsing DesignState and retrieving necessary objects and properties which are used in validated SWRL Rule." This is a key implementation constraint — the DesignState model must support efficient lookup by Rule (PropState scoped to a specific Rule) and by Object variable (ObjState carries an ObjectRef label).
- No other specific references or "I want it like X" moments — the decisions above capture the full intent.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Cross-phase notes (not scope changes)
- **Phase 18**: Per-object `ValidStatus` population semantics — does the array cover **all** ObjStates in the DesignState, or only those matching the rule's target Class? (Carried from Phase 13 deferred.)
- **Phase 18**: `VariableBinder.BuildBindings` logic is redistributed to OBJECT STATE / PROPERTY STATE / VALIDATOR — do NOT delete in Phase 16; Phase 18 owns that migration.
- **Phase 18**: data-service `_project_state_summary` + Model Viewer `useValidationRunsGrouping` adaptation to statePayloadJson v2.
</deferred>

---

*Phase: 16-dg-core-state-models-and-state-components*
*Context gathered: 2026-07-04*
