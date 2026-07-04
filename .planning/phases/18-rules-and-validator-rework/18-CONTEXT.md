# Phase 18: Rules and Validator Rework - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Replaces the CLASSIFICATOR-driven validation pipeline with DesignState-driven evaluation — RULE DECONSTRUCT partitions typed variables, VALIDATOR binds from the composed DesignState and publishes runs with statePayloadJson v2, and CLASSIFICATOR is fully purged. The Model Viewer adapts to read v2 payloads while keeping v1 tolerance.

**In scope (GHVL-01..06):**
- RULE DECONSTRUCT — partitions rule variables into Objects + DataProperties via VariableTypeInferrer (Variables/VariableName removed)
- CLASSIFICATOR removal — full purge of component + DG.Core.Classification namespace + ClassificatorState
- VALIDATOR rework — new contract (Rule + DesignState + SendValid + Run → ValidStatus + RuleName + RuleDescription + SendStatus), binding driven by DesignState
- New `DesignStateBindingService` in DG.Core — replaces VariableBinder.BuildBindings
- Publish path — persists Run with ValidStatus/SendStatus + statePayloadJson v2
- Model Viewer read-side — adapt `_project_state_summary` and `useValidationRunsGrouping` to v2 payloads, v1 tolerance

**Out of scope (belongs in other phases):**
- DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT — Phase 19
- PARAMETER REINSTATE — Phase 19
- E2E live chain, docs, release notes — Phase 20
- SpecGraph handle consumer — no consumer exists yet (wired for future)

**Already locked upstream (do NOT re-open):**
- Port names and IRIs for RULE DECONSTRUCT and VALIDATOR — `ontology/port-iri-map-V7.md` (Phase 13)
- DesignState = 3 independent bags (ObjState+ParamState+PropState) — Phase 16 D-01/D-02
- PropState is rule-scoped (one Rule + one DataProperty) — Phase 16 D-10
- statePayloadJson v2 with version envelope — Phase 16 D-05/D-06
- DesignState stored in `graph='ValidGraph'`, MERGE'd by StateId+project — Phase 13 D-01/D-03
- Run.ValidStatus = Boolean list per-ObjState, Run.SendStatus = single Boolean, no Status text field — Phase 13/14
- VariableTypeInferrer in DG.Core.Parsing carries forward from Phase 7 (priority chain: Object > Property)
- METAGRAPH Objects output = Class nodes rules REFERS_TO, index-matched with Rules — Phase 17 D-02
- Neo4jValidGraphRepository handles v1+v2 payloads — Phase 17
- Non-overlapping VALIDATOR ports kept (DataServiceUrl input; Report, FailingBindings, ValidationRunId, ModelViewerUrl outputs) — PROJECT.md
- DB keeps existing labels except Knowledge*→Spec* — PROJECT.md
- ErrorMessageTemplates What+Where+How-to-fix pattern — all new error surfaces
</domain>

<decisions>
## Implementation Decisions

### ValidStatus Array Contract (Area 1)
- **D-01:** ValidStatus[i] = Boolean for DesignState.ObjStates[i] — one entry per **every** ObjState in the DesignState, regardless of Class match. Index-matched to DesignState.ObjStates list. Same length, same order.
- **D-02:** Non-matching ObjStates get `false` but are **excluded** from the overall pass derivation. Overall pass = AND of only the applicable Booleans (where the ObjState's Class matches the rule's target). True = passing, False = failing, absent/non-applicable = no vote in the AND.

### VariableBinder Redistribution (Area 2)
- **D-03:** New **`DesignStateBindingService`** in `DG.Core.Services` — pure logic class that takes (Rule, DesignState) and produces variable bindings for SWRL evaluation. VALIDATOR calls it. Extracted from VariableBinder.BuildBindings logic. Testable without Grasshopper SDK.
- **D-04:** Delete **entire `DG.Core.Classification` namespace** — VariableBinder, VariableBinding, BindingContext, all of it. The new DesignStateBindingService is the replacement. VariableTypeInferrer is already in DG.Core.Parsing (Phase 7) and stays.
- **D-05:** **ObjState matching by Class IRI.** Rule variable → REFERS_TO → Class IRI. ObjState carries the Class IRI (from the Object input, which comes from METAGRAPH Objects output — each Object has IRI + label). The binding service matches on IRI — a "wall height" rule only binds to wall ObjStates, not windows.

### RULE DECONSTRUCT Edge Cases (Area 3)
- **D-06:** Variables with **no REFERS_TO link** → **error** with clear runtime message (What+Where+How-to-fix pattern via ErrorMessageTemplates). This is a malformed rule — the graph ingestion pipeline should never produce it. Fail loud.
- **D-07:** **Builtin-only variables** (`swrlb:*` references) → **excluded** from both Objects and DataProperties outputs. These are internal to SWRL evaluation (math comparisons, string ops). RULE DECONSTRUCT surfaces domain references; Builtins are VALIDATOR's concern.
- **D-08:** **VariableTypeInferrer stays as-is** in DG.Core.Parsing. RULE DECONSTRUCT calls it directly to classify each variable. VALIDATOR also uses it to know which vars bind to ObjStates vs PropValues. No enhancements — the Phase 7 priority chain (Object > Property) is sufficient.

### CLASSIFICATOR Removal (Area 4)
- **D-09:** **Full purge.** Delete all of: `ClassificatorComponent.cs` (DG.Grasshopper), entire `DG.Core.Classification` namespace (VariableBinder.cs, VariableBinding.cs, BindingContext.cs), `ClassificatorState` model, any Classificator-specific tests, and all `using DG.Core.Classification` statements. One clean commit. Release notes at Phase 20 document the removal and re-wiring path.

### Claude's Discretion
- Exact method signatures for `DesignStateBindingService` (recommend: `BuildBindings(Rule, DesignState) → IEnumerable<VariableBinding>`, matching the old signature pattern with new input types)
- Exact error message wording for D-06 (follow `ErrorMessageTemplates` What+Where+How-to-fix pattern)
- Whether the old `RuleEvaluator` (SWRL evaluation engine) needs adaptation for the new binding contract, or if bindings are pre-built and passed in unchanged
- Exact Cypher for persisting the Run node with ValidStatus/SendStatus + statePayloadJson v2 (extend existing `ValidationRunPersistenceService` pattern)
- Exact `_project_state_summary` projection adaptation in `data-service/app.py` — v2 envelope detection via `version` field (reuse Phase 17 Neo4jValidGraphRepository's heuristic), v1 fallback
- Exact `useValidationRunsGrouping.js` changes — group-by-State via `state.stateId` preserved, state display adaptation for 3-part state labels
- Whether deleted Classification code should be referenced in a migration note or just git history (recommend: git history is sufficient — full purge, no shim)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Component contract & ontology
- `ontology/port-iri-map-V7.md` — per-port IRI contract for RULE DECONSTRUCT and VALIDATOR (grep for component names). **MUST read.**
- `ontology/GH_DesignGrammars.pdf` — 14-component schema; wiring diagrams for RULE DECONSTRUCT and VALIDATOR. PDF port labels may be stale — port-IRI map + Phase 13 investigation take precedence.
- `ontology/DesignGrammar-V7.owl` — V7 ontology: `dgm:Rule`, `dg:Class`, `dg:DataProperty`, `dg:ObjState`, `dg:PropState`, `dgv:ValidStatus`, `dgv:SendStatus`, `dgm:SWRL`, `dgm:RuleName`, `dgm:RuleDescription`
- `ontology/V7-INVESTIGATION.md` — conflict resolutions (a) ValidStatus vs Status, (b) DesignState storage layer (ValidGraph), (c) version marker; final names

### Existing code to adapt or replace
- `DG/src/DG.Core/Classification/VariableBinder.cs` — **read before planning** — BuildBindings logic being redistributed to DesignStateBindingService, then DELETED
- `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs` — stays as-is, used by RULE DECONSTRUCT and VALIDATOR
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` — reworked with new contract (Rule + DesignState + SendValid + Run inputs; ValidStatus + RuleName + RuleDescription + SendStatus outputs)
- `DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs` — **DELETED** (full purge)
- `DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs` — existing component (Phase ~17), extend with Objects/DataProperties outputs, remove Variables/VariableName
- `DG/src/DG.Core/Services/RuleEvaluator.cs` — SWRL evaluation engine, may need binding contract adaptation
- `DG/src/DG.Core/Services/ValidationRunPersistenceService.cs` — extend for v2 statePayloadJson with ValidStatus/SendStatus
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — Phase 16 artifact, `ComputeDesignStateId` for aggregate StateId
- `DG/src/DG.Core/Serialization/DesignStatePayloadSerializer.cs` — Phase 16 v2 serializer (or whatever name was chosen)
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — extend for RULE DECONSTRUCT unclassified-var errors + VALIDATOR binding errors
- `DG/src/DG.Grasshopper/PublicTypes.cs` — may need new wrappers for updated VALIDATOR outputs
- `DG/tests/DG.Tests/` — delete Classificator tests, add DesignStateBindingService tests

### Code to delete
- `DG/src/DG.Core/Classification/` — entire namespace (VariableBinder.cs, VariableBinding.cs, BindingContext.cs)
- `DG/src/DG.Core/Models/ClassificatorState.cs` — Classificator state model
- `DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs` — GH component
- Any `using DG.Core.Classification` references across the solution

### Model Viewer adaptation
- `data-service/app.py` — `_project_state_summary` (line ~521), `/validation/runs` projection (GHVL-06)
- `graph-viewer/model-viewer/src/useValidationRunsGrouping.js` — group-by-State via `state.stateId` (GHVL-06)
- `graph-viewer/model-viewer/src/components/ValidationRunsStrip.jsx` — render adaptation for 3-part state labels

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — GHVL-01..06 (rules and validator)
- `.planning/ROADMAP.md` — Phase 18 goal + 5 success criteria
- `.planning/PROJECT.md` — key decisions: violation pattern (inverted logic), project isolation, DB labels unchanged, port-IRI contract

### Prior phase context (decisions carried forward)
- `.planning/phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` — D-01..D-11: DesignState layer placement (ValidGraph), MERGE by StateId+project, no-orphan invariant, ValidStatus per-ObjState Boolean array, VALIDATOR new GUID
- `.planning/phases/16-dg-core-state-models-and-state-components/16-CONTEXT.md` — D-01/D-02 (DesignState composition = independent bags), D-04 (deterministic StateId), D-05/D-06 (statePayloadJson v2), D-08/D-10 (PropState = rule-scoped, typed value)
- `.planning/phases/17-graph-access-components/17-CONTEXT.md` — D-02 (METAGRAPH Objects = REFERS_TO→Class query), D-03/D-04/D-05 (VALIDATION GRAPH Run/Status/DesignState outputs)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`VariableTypeInferrer`** (`DG.Core.Parsing`): Phase 7 artifact — classifies variables as Object/DataProperty/Builtin via priority chain. RULE DECONSTRUCT calls it directly for the Objects/DataProperties partition. VALIDATOR uses it to route bindings. Pure logic, no changes needed.
- **`RuleEvaluator`** (`DG.Core.Services`): Evaluates SWRL rules against variable bindings. The evaluation engine itself likely doesn't change — only the binding source changes (DesignStateBindingService instead of VariableBinder). The input contract (rule + bindings → results) should be preserved.
- **`ValidationRunPersistenceService`** (`DG.Core.Services`): Existing publish path to data-service. Extend with v2 payload serialization + ValidStatus/SendStatus fields. The HTTP POST pattern and error handling stay the same.
- **`DesignStateIdGenerator`** (`DG.Core.Services`): Phase 16 artifact. `ComputeDesignStateId` for the aggregate DesignState ID — used by VALIDATOR to emit the StateId on publish.
- **`DesignStatePayloadSerializer`** (`DG.Core.Serialization`): Phase 16 v2 serializer. VALIDATOR calls it at publish time to produce the v2 JSON envelope.
- **`Neo4jValidGraphRepository`** (`DG.Core.Data`): Phase 17 artifact — reads Run+Status+DesignState from ValidGraph. The write side (VALIDATOR publish) must match this read contract. Already handles v1+v2 payloads on read.

### Established Patterns
- **Async load with edge-triggered refresh**: CONNECTOR, METAGRAPH, VALIDATION GRAPH. RULE DECONSTRUCT is likely **not** async — it's a pure synchronous transform (rule → partition). VALIDATOR is likely **both** — synchronous evaluation + async publish on SendValid edge.
- **`#if GRASSHOPPER_SDK` guards**: All GH-dependent code in DG.Grasshopper is conditional-compilation guarded. `DesignStateBindingService` in DG.Core is not — pure logic, multi-targeting.
- **`DgComponentCategory.Category` + `.Subcategory`**: "DG" / "Design Grammar" for Grasshopper toolbar grouping.
- **Immutable model classes**: `{ get; init; }` with default values. New output models follow this pattern.
- **`ErrorMessageTemplates`**: Static class with What+Where+How-to-fix templates. Extend for D-06 errors (unclassified variables) and VALIDATOR binding failures.

### Integration Points
- **Phase 16 (State Models)**: DesignState, ObjState, ParamState, PropState models — VALIDATOR consumes DesignState input, parses its three lists separately per the SWRL rule under evaluation. statePayloadJson v2 serializer used at publish time.
- **Phase 17 (Graph Access)**: METAGRAPH provides Rules + Objects (index-matched). VALIDATION GRAPH reads runs back. The write side built here must match the read contract built in Phase 17.
- **data-service** (Python): `_project_state_summary` (line ~521) projects DesignState from `statePayloadJson`. Must handle v2 envelope (detect `version: "2"`, extract `objStates`/`paramStates`/`propStates`) while keeping v1 fallback. `/validation/runs` projection includes state summary in response.
- **Model Viewer** (React): `useValidationRunsGrouping.js` groups runs by `state.stateId`. `ValidationRunsStrip.jsx` renders state labels. v2 state labels may differ from v1 — the adapter should surface meaningful labels for 3-part states (e.g., "3 objects, 5 params" or the aggregate StateId).
</code_context>

<specifics>
## Specific Ideas

- **VariableBinder.BuildBindings must be read before planning** (STATE.md research flag). The binding logic is being redistributed to `DesignStateBindingService`, not deleted blind. The planner must understand what the old code does before designing its replacement.
- **data-service `_project_state_summary` + Model Viewer `useValidationRunsGrouping` must be read before planning** (STATE.md research flag). These are the read-side consumers of statePayloadJson — the v2 adaptation must preserve their existing behavior for v1 payloads.
- No other specific references or "I want it like X" moments — the decisions above capture the full intent.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Cross-phase notes (not scope changes)
- **Phase 19**: DESIGN STATE DECONSTRUCT consumes VALIDATOR outputs (DesignState from VALIDATION GRAPH). The read-back integrity (publish → read → deconstruct) is tested in Phase 20 E2E.
- **Phase 20**: Release notes document CLASSIFICATOR removal + VALIDATOR re-wiring. Canvas breakage is expected — v7.0 is a breaking-change milestone.
- **Phase 14 research flag**: "ValidStatus added as best-effort per-entity Boolean list; full per-ObjState index-matched population deferred to Phase 18" — **now implemented here** (D-01/D-02).
</deferred>

---

*Phase: 18-rules-and-validator-rework*
*Context gathered: 2026-07-04*
