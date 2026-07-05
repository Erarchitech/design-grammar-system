# Phase 19: Deconstruct and Reinstate Components - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Three Grasshopper components that let architects disassemble stored DesignStates and re-apply captured parameters to the live canvas. Two are pure synchronous passthrough components (DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT). The third is PARAMETER REINSTATE — a rework of the existing REINSTATE with target discovery, pre-validation via `DesignStateReinstatementService`, and deferred value writing to Grasshopper sliders/toggles.

**In scope (GHST-05, GHST-06, GHST-07):**
- **DESIGN STATE DECONSTRUCT** — DesignState → ObjState / ParamState / PropState (pure synchronous passthrough)
- **OBJECT DECONSTRUCT** — ObjState → Object / Geometry / Label (pure synchronous passthrough)
- **PARAMETER REINSTATE** — reworked REINSTATE: ParamState + Reinstate (rising-edge trigger) + Target (PARAMETER STATE reference) → Parameters + StateStatus + Status

**Out of scope (belongs in other phases):**
- DesignState model, ObjState/ParamState/PropState models — Phase 16 (already shipped)
- VALIDATION GRAPH DesignState output (the source of DesignStates to deconstruct) — Phase 17 (already shipped)
- VALIDATOR write-side (produces the DesignStates being deconstructed) — Phase 18 (already shipped)
- E2E live chain, docs, release notes — Phase 20

**Already locked upstream (do NOT re-open):**
- DesignState = 3 independent bags (ObjState, ParamState, PropState) — Phase 16 D-01/D-02
- ObjState model: StateId, ObjectRef, Geometry, Label, ClassIri, CapturedAtUtc — Phase 16
- ParamState model: StateId, CapturedAtUtc, Collection<DesignStateParameter> — Phase 16 D-14
- PropState model: StateId, RuleIri, DataPropertyIri, PropValue — Phase 16 D-08/D-10
- Port-IRI map for all 3 components — Phase 13 (ontology/port-iri-map-V7.md)
- Rising-edge trigger for reinstatement — v2.0 decision, carries forward
- 7-value ReStatus reporting preserved (Applied, MissingTarget, TypeMismatch, AmbiguousTarget, OutOfRange, Unchanged, WouldApply) — GHST-07
- `DesignStateReinstatementService` — pure logic, atomic validation, WouldApply pattern — already exists in DG.Core.Services
- `ReinstatementResult`, `ReinstatementStatus`, `ReinstatementParameterReport`, `ResolvedTarget` models — already exist in DG.Core.Models
- DECONSTRUCT = pure synchronous passthrough (follows GRAPH DECONSTRUCT pattern from Phase 17 D-01)
- ErrorMessageTemplates What+Where+How-to-fix pattern — all new error surfaces
- `#if GRASSHOPPER_SDK` guards, DgComponentCategory, immutable model classes
- CLASSIFICATOR is gone (Phase 18) — REINSTATE/DECONSTRUCT do not reference it
</domain>

<decisions>
## Implementation Decisions

### REINSTATE Target Discovery (Area 1)
- **D-01:** PARAMETER REINSTATE keeps a **'Target' input** — wired from PARAMETER STATE component's State output. REINSTATE walks upstream wires from that PARAMETER STATE to discover which sliders/toggles to push captured values to. Same proven wire-traversal pattern as the old REINSTATE. The wire IS the target declaration.
- **D-02:** Target input is **Required** (not optional). No fallback search from the ParamState input — simpler contract, no ambiguity about which PARAMETER STATE is the target.
- **D-03:** Target input is a **runtime/DB concern** (no ontology IRI). Annotated alongside the Reinstate trigger — it's a Grasshopper-internal wiring mechanism, not an ontology concept.

### StateStatus & Parameters Outputs (Area 2)
- **D-04:** **StateStatus list is index-matched to ParamState.Parameters** — one ReStatus per parameter, same length, same order. Downstream components can pair Parameters[i] with StateStatus[i]. Follows the index-matched list contract pattern from METAGRAPH Rules/Objects (Phase 17 D-02) and VALIDATOR ValidStatus/ObjStates (Phase 18 D-01).
- **D-05:** **Parameters output contains ALL parameters** from the captured ParamState (not just applied ones). Clean separation of concerns — data vs. status. Downstream filters by cross-referencing with StateStatus.
- **D-06:** **Keep summary Status text output** as a third output alongside Parameters + StateStatus. Human-readable summary ("Applied 5 parameters" / "Aborted: 2 blocked" / "Unchanged (same state)" / "Idle"). Ergonomic — architects see the outcome directly on the component without inspecting lists.

### DECONSTRUCT Error Contract (Area 3)
- **D-07:** Both DESIGN STATE DECONSTRUCT and OBJECT DECONSTRUCT use **Warning + empty outputs** on null/missing input. `AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, ...)` + set all outputs to empty lists + return. Consistent with standard Grasshopper component behavior. Empty list inputs (e.g., DesignState with no ObjStates) are valid and passthrough as empty lists — no warning.

### Claude's Discretion
- Exact GUID assignments for DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, and PARAMETER REINSTATE (whether old REINSTATE GUID `D4E2F8A1-C736-4B9D-AE51-2B1F7C9D0E63` is kept or a new GUID assigned — recommend: new GUID for the reworked component, matching the VALIDATION GRAPH precedent from Phase 17)
- Component icons (DgIcons entries — follow existing icon naming convention)
- Exact GH_Component layout: RegisterInputParams/RegisterOutputParams for all 3 components
- Wire-traversal implementation for Target input (reuse `FindUpstreamDesignState` pattern from current ReinstateComponent)
- Deferred write scheduling — reuse `ScheduleSolution` pattern from current ReinstateComponent
- Error message wording (follow ErrorMessageTemplates What+Where+How-to-fix pattern)
- Exact output type for Parameters output (DesignStateParameter list vs custom goo wrapper)
- Exact output type for StateStatus output (ReinstatementStatus enum vs int vs text — recommend: ReinstatementStatus enum, wrapped for GH)
- Whether the old REINSTATE component file is renamed in-place or replaced with a new file (recommend: replace — new GUID, new contract, cleaner git history)
- DECONSTRUCT component output typing — ObjState/ParamState/PropState lists, wrapped via `GH_ObjectWrapper` or `GhCastingHelpers` generic pattern
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Component contract & ontology
- `ontology/port-iri-map-V7.md` — per-port IRI contract for DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, and PARAMETER REINSTATE (grep for component names). **MUST read.**
- `ontology/GH_DesignGrammars.pdf` — the 14-component schema; wiring diagrams for all 3 components. PDF port labels may be stale — port-IRI map + Phase 13 investigation take precedence.
- `ontology/DesignGrammar-V7.owl` — V7 ontology: `dg:DesignState`, `dg:ObjState`, `dg:ParamState`, `dg:PropState`, `dgv:ReStatusValue`, `dgv:objectRefName`, `dgc:Parameter`
- `ontology/V7-INVESTIGATION.md` — conflict resolutions, final state-kind names, ReStatus→ReStatusValue IRI resolution

### Existing code to adapt or replace
- `DG/src/DG.Grasshopper/Components/ReinstateComponent.cs` — existing REINSTATE to rework into PARAMETER REINSTATE: wire-traversal pattern (`FindUpstreamDesignState`, `ResolveTargets`), rising-edge trigger (`_lastApplyInput`), deferred write scheduling (`ScheduleWriteValues`, `WriteToSource`), assembly-mismatch fallback (`ReconstructSnapshot`), GH container unwrapping (`UnwrapGhContainer`)
- `DG/src/DG.Core/Services/DesignStateReinstatementService.cs` — pure logic service: `Validate(ParamState, IReadOnlyList<ResolvedTarget>, string?)` → `ReinstatementResult`. Atomic decision (D-06: all-or-nothing), WouldApply flip, type compatibility check, domain bounds check. Already tested and ready for reuse.
- `DG/src/DG.Core/Models/ReinstatementResult.cs` — output model: Applied, Aborted, Reports (list of ReinstatementParameterReport)
- `DG/src/DG.Core/Models/ReinstatementStatus.cs` — 7-value enum: Applied, MissingTarget, TypeMismatch, AmbiguousTarget, OutOfRange, Unchanged, WouldApply
- `DG/src/DG.Core/Models/ResolvedTarget.cs` — target model: ParameterId, Resolution (Resolved/Missing/Ambiguous), TargetType, DomainMin, DomainMax
- `DG/src/DG.Core/Models/DesignState.cs` — 3-part composition model (ObjStates, ParamStates, PropStates lists) — consumed by DESIGN STATE DECONSTRUCT
- `DG/src/DG.Core/Models/ObjState.cs` — StateId, ObjectRef, Geometry, Label, ClassIri, CapturedAtUtc — consumed by OBJECT DECONSTRUCT
- `DG/src/DG.Core/Models/ParamState.cs` — StateId, CapturedAtUtc, Parameters (Collection<DesignStateParameter>) — consumed by PARAMETER REINSTATE
- `DG/src/DG.Core/Models/PropState.cs` — StateId, RuleIri, DataPropertyIri, PropValue — consumed by DESIGN STATE DECONSTRUCT
- `DG/src/DG.Core/Models/DesignStateParameter.cs` — typed param model (Number/Integer/Boolean, ParameterId, DisplayName) — reused unchanged
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — Phase 16 artifact; may be referenced for ID validation in REINSTATE
- `DG/src/DG.Grasshopper/PublicTypes.cs` — add public wrappers for new component outputs (ObjState list, ParamState list, PropState list, ReinstatementStatus list, DesignStateParameter list)
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — extend for deconstruct warnings + reinstatement error messages

### Reference patterns from other phases
- `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs` — async-load pattern (not needed for DECONSTRUCT, but reference for GH component layout conventions)
- `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs` — `IGH_VariableParameterComponent` pattern, NickName→ParameterId, `UnwrapScalar`, `BuildParameter` — the Target input wire-traversal target for REINSTATE
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — shared GH value unwrapping (generic `Unwrap<T>` pattern for handle types)
- `DG/src/DG.Grasshopper/Components/ValidationGraphComponent.cs` — Phase 17 precedent for replacing old component with new GUID (VALIDATION RUNS → VALIDATION GRAPH)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — GHST-05 (DESIGN STATE DECONSTRUCT), GHST-06 (OBJECT DECONSTRUCT), GHST-07 (PARAMETER REINSTATE)
- `.planning/ROADMAP.md` — Phase 19 goal + 3 success criteria
- `.planning/PROJECT.md` — key decisions: typed state limited to Number/Integer/Boolean, rising-edge trigger, ObjectRef = user-supplied string, port-IRI contract, DB labels unchanged

### Prior phase context (decisions carried forward)
- `.planning/phases/16-dg-core-state-models-and-state-components/16-CONTEXT.md` — D-01/D-02 (DesignState composition = independent bags), D-04 (deterministic StateId), D-05/D-06 (statePayloadJson v2), D-08/D-10 (PropState = rule-scoped, typed value), D-11 (PropState.StateId = PS_ prefix)
- `.planning/phases/17-graph-access-components/17-CONTEXT.md` — D-01 (individual handle types, GRAPH DECONSTRUCT is pure passthrough), D-02 (METAGRAPH Objects), D-03/D-04/D-05 (VALIDATION GRAPH Run/Status/DesignState outputs)
- `.planning/phases/18-rules-and-validator-rework/18-CONTEXT.md` — D-01/D-02 (ValidStatus per-ObjState Boolean list, index-matched), D-03 (DesignStateBindingService replaces VariableBinder), D-09 (CLASSIFICATOR fully purged)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`DesignStateReinstatementService`** (`DG.Core.Services`): Stateless pure-logic service. `Validate(ParamState, IReadOnlyList<ResolvedTarget>, string?)` → `ReinstatementResult`. Handles StateId dedup guard, type compatibility check, domain bounds check, atomic WouldApply flip. **Already exists and is tested** — PARAMETER REINSTATE calls it directly. No changes needed.
- **`ReinstateComponent` wire-traversal logic** (`DG.Grasshopper.Components`): `FindUpstreamDesignState()` walks input sources to locate a PARAMETER STATE component. `ResolveTargets()` enumerates its inputs to build `ResolvedTarget` list (ParameterId via NickName, TargetType via source inspection, DomainMin/DomainMax for sliders). `ScheduleWriteValues()` defers slider writes via `ScheduleSolution`. `WriteToSource()` handles GH_NumberSlider, GH_BooleanToggle, and generic Param_Number/Param_Integer/Param_Boolean. All of this carries forward into the reworked component.
- **`ReinstateComponent` assembly-mismatch fallback** (`ReconstructSnapshot`, `ReconstructParameter`, `UnwrapGhContainer`): Handles the case where GH loads a different copy of DG.Core.dll. Reflection-based reconstruction of ParamState and DesignStateParameter. Carry forward into the reworked component.
- **`DesignState` model** (`DG.Core.Models`): 3-part composition — `ObjStates`, `ParamStates`, `PropStates` as `List<T>`. DESIGN STATE DECONSTRUCT simply unpacks these three lists. Pure data, no behavior.
- **`ObjState` model** (`DG.Core.Models`): StateId, ObjectRef, Geometry, Label, ClassIri, CapturedAtUtc. OBJECT DECONSTRUCT outputs ObjectRef→Object, Geometry, Label. Pure data.

### Established Patterns
- **Pure synchronous passthrough (GRAPH DECONSTRUCT pattern)**: No async, no DB, no `CancellationTokenSource`, no `ScheduleSolution`. `SolveInstance` reads input, unwraps type, outputs parts. Both DECONSTRUCT components follow this exactly.
- **Async load with edge-triggered refresh**: NOT applicable to DECONSTRUCT components. PARAMETER REINSTATE is also synchronous — it uses rising-edge trigger + deferred write, not async loading.
- **`#if GRASSHOPPER_SDK` guards**: All GH-dependent component code lives inside `#if GRASSHOPPER_SDK`. The `#else` block provides a stub class for non-GH builds.
- **`DgComponentCategory.Category` + `.Subcategory`**: "DG" / "Design Grammar" for Grasshopper toolbar grouping. All 3 new components use this.
- **Immutable model classes**: `{ get; init; }` with default values. All state models (DesignState, ObjState, ParamState, PropState) follow this — DECONSTRUCT reads them, doesn't mutate.
- **Index-matched parallel lists**: Used by METAGRAPH (Rules/Objects), VALIDATION GRAPH (Run/Status), VALIDATOR (ValidStatus/ObjStates). PARAMETER REINSTATE extends this to StateStatus/Parameters.
- **Rising-edge trigger with `_lastApplyInput`**: Boolean toggle detection. Prevents auto-apply on wire change. Carry forward from existing REINSTATE.

### Integration Points
- **Phase 16 (State Models)**: DESIGN STATE DECONSTRUCT consumes `DesignState` and outputs its three internal lists. OBJECT DECONSTRUCT consumes `ObjState`. PARAMETER REINSTATE consumes `ParamState`.
- **Phase 17 (Graph Access)**: VALIDATION GRAPH outputs DesignState from ValidGraph — this is the upstream source for DESIGN STATE DECONSTRUCT in the E2E chain: VALIDATION GRAPH → DESIGN STATE DECONSTRUCT → OBJECT DECONSTRUCT / PARAMETER REINSTATE.
- **Phase 18 (Rules and Validator)**: VALIDATOR produces the DesignStates that get stored in ValidGraph and later read back by VALIDATION GRAPH. DESIGN STATE DECONSTRUCT closes the loop by taking apart what VALIDATOR assembled.
- **PARAMETER STATE component (Phase 16)**: The Target input on PARAMETER REINSTATE wires from PARAMETER STATE's State output. REINSTATE walks PARAMETER STATE's input sources to find sliders/toggles. This is the same relationship as in the old REINSTATE.
- **data-service** (Python): Not directly touched by Phase 19 — these are C# Grasshopper components with no network calls (DECONSTRUCT) or deferred local writes only (REINSTATE).
- **Model Viewer** (React): Not directly touched. The deconstruct/reinstate chain is canvas-only.
</code_context>

<specifics>
## Specific Ideas

- **PARAMETER REINSTATE is a rework, not a new component.** The old REINSTATE (GUID `D4E2F8A1`) should be replaced with a new GUID — following the VALIDATION GRAPH precedent (Phase 17: old VALIDATION RUNS GUID replaced with new GUID). Canvas breakage is expected in v7.0; documented at Phase 20.
- **DECONSTRUCT components have no refresh/trigger inputs.** Unlike METAGRAPH or VALIDATION GRAPH, there's nothing to refresh — the input data IS the source of truth. This makes them the simplest components in the entire v7.0 set (even simpler than GRAPH DECONSTRUCT which has 4 output handles).
- **DesignState with empty bags is valid.** A DesignState may have ObjStates but no ParamStates or PropStates (or vice versa). DESIGN STATE DECONSTRUCT passes empty lists through without warnings. Only null/missing input triggers a warning.
- No other specific references or "I want it like X" moments — the decisions above capture the full intent.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Cross-phase notes (not scope changes)
- **Phase 20**: E2E live chain tests the full round-trip: VALIDATION GRAPH → DESIGN STATE DECONSTRUCT → OBJECT DECONSTRUCT, and VALIDATION GRAPH → DESIGN STATE DECONSTRUCT → PARAMETER REINSTATE. Canvas breakage from REINSTATE GUID change is documented in release notes.
- **Phase 20**: Release notes document the old REINSTATE → PARAMETER REINSTATE re-wiring (new GUID, required Target input, new output contract).
</deferred>

---

*Phase: 19-deconstruct-and-reinstate-components*
*Context gathered: 2026-07-05*
