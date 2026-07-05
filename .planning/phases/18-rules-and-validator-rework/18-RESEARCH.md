# RESEARCH COMPLETE

**Phase:** 18 — Rules and Validator Rework
**Domain:** Grasshopper component rework (C# .NET 7/9), publish pipeline, Model Viewer adaptation
**Confidence:** HIGH

## Summary

This phase replaces the CLASSIFICATOR-driven validation pipeline with DesignState-driven evaluation. Three major work areas: (1) RULE DECONSTRUCT extension to partition variables via VariableTypeInferrer, (2) new DesignStateBindingService replacing VariableBinder.BuildBindings, and (3) VALIDATOR rework with a new contract consuming DesignState directly. The CLASSIFICATOR and all DG.Core.Classification code is deleted. Model Viewer read-side adapts for v2 statePayloadJson with v1 tolerance.

**Primary recommendation:** Follow the three-wave plan structure: Wave 1 for DesignStateBindingService + error surfaces + RULE DECONSTRUCT extension (parallel), Wave 2 for VALIDATOR rework + publish pipeline, Wave 3 for CLASSIFICATOR deletion + Model Viewer read-side (parallel).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ValidStatus Array Contract (Area 1)**
- D-01: ValidStatus[i] = Boolean for DesignState.ObjStates[i] — one entry per every ObjState in the DesignState, regardless of Class match. Index-matched to DesignState.ObjStates list. Same length, same order.
- D-02: Non-matching ObjStates get `false` but are excluded from the overall pass derivation. Overall pass = AND of only the applicable Booleans. True = passing, False = failing, absent/non-applicable = no vote in the AND.

**VariableBinder Redistribution (Area 2)**
- D-03: New DesignStateBindingService in DG.Core.Services — pure logic class that takes (Rule, DesignState) and produces variable bindings for SWRL evaluation. VALIDATOR calls it. Testable without Grasshopper SDK.
- D-04: Delete entire DG.Core.Classification namespace — VariableBinder, ClassificationResult, all of it. VariableTypeInferrer in DG.Core.Parsing stays.
- D-05: ObjState matching by Class IRI. Rule variable → REFERS_TO → Class IRI. ObjState carries the Class IRI. Binding service matches on IRI.

**RULE DECONSTRUCT Edge Cases (Area 3)**
- D-06: Variables with no REFERS_TO link → error with What+Where+How-to-fix pattern.
- D-07: Builtin-only variables (swrlb:* references) → excluded from both Objects and DataProperties outputs.
- D-08: VariableTypeInferrer stays as-is in DG.Core.Parsing. RULE DECONSTRUCT calls it directly.

**CLASSIFICATOR Removal (Area 4)**
- D-09: Full purge. Delete ClassificatorComponent.cs, entire DG.Core.Classification namespace, ClassificatorState model, any Classificator-specific tests, all `using DG.Core.Classification` statements.

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

### Claude's Discretion
- Exact method signatures for DesignStateBindingService (recommend: BuildBindings(Rule, DesignState) → IEnumerable<VariableBinding>, matching old signature pattern with new input types)
- Exact error message wording for D-06 (follow ErrorMessageTemplates What+Where+How-to-fix pattern)
- Whether the old RuleEvaluator needs adaptation for the new binding contract, or if bindings are pre-built and passed in unchanged
- Exact Cypher for persisting the Run node with ValidStatus/SendStatus + statePayloadJson v2
- Exact _project_state_summary projection adaptation — v2 envelope detection via version field, v1 fallback
- Exact useValidationRunsGrouping changes — group-by-State via state.stateId preserved, state display adaptation
- Whether deleted Classification code should be referenced in a migration note or just git history

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GHVL-01 | RULE DECONSTRUCT partitions rule variables into Objects + DataProperties outputs via VariableTypeInferrer (Variables/VariableName removed) | VariableTypeInferrer in `DG.Core.Parsing` stays as-is (D-08). RULE DECONSTRUCT removes outputs 1 (Variables) and 2 (VariableName), adds Objects and DataProperties. `ExpectedOutputNames` array in RuleDeconstructComponent.cs:15-21 changes from 6 to 6 outputs (same count, different names — check compat). Builtin-only variables excluded per D-07. |
| GHVL-02 | CLASSIFICATOR component removed from the plugin | Delete ClassificatorComponent.cs, DgIcons.Classificator24, and the Classificator24.png embedded resource. DELETE `DG.Core.Classification` namespace entirely — only VariableBinder.cs and ClassificationResult.cs exist there. |
| GHVL-03 | VALIDATOR implements new contract — inputs Rule, DesignState, SendValid, Run; outputs ValidStatus, RuleName, RuleDescription, SendStatus | Per port-iri-map-V7.md: inputs Rule (dgm:Rule), DesignState (dg:DesignState), SendValid (Boolean trigger), DataServiceUrl (runtime). Outputs: Run (dgv:Run), ValidStatus (dgv:ValidStatus), RuleName (dgm:RuleName), RuleDescription (dgm:RuleDescription), SendStatus (dgv:SendStatus), Report, FailingBindings, ValidationRunId, ModelViewerUrl. Old Run trigger and State input removed. SendValid replaces old SendRules for publish trigger. |
| GHVL-04 | VALIDATOR binds variables from composed DesignState (ObjState->Object variables, PropState->Property values), replacing CLASSIFICATOR/VariableBinder path | New DesignStateBindingService in DG.Core.Services takes (Rule, DesignState) and produces `IEnumerable<BindingRow>` matching the format RuleEvaluator expects. ObjState matching by Class IRI per D-05. PropState matching by DataProperty IRI. |
| GHVL-05 | Publish path persists Run with ValidStatus/SendStatus and 3-part state payload; VALIDATION GRAPH reads it back intact | ValidationRunPersistenceService.cs extends from v1 ParamState-only to v2 DesignState. ValidationPublishClient.cs builds request with DesignStatePayloadV2Serializer. data-service `store_validation_run` (app.py:396) already stores `ValidStatus` and `statePayloadJson`. Must add `SendStatus` OUT of the publish response. |
| GHVL-06 | Model Viewer keeps working — data-service `_project_state_summary` and `/validation/runs` adapted to v2; `useValidationRunsGrouping` groups by state.stateId; ValidationRunsStrip renders correctly | `_project_state_summary` (app.py:534) currently reads v1 parameters only. Must detect v2 envelope via `version` field and extract objStates/paramStates/propStates count. `useValidationRunsGrouping.js` derives state from `run.state.stateId` — this field path is preserved in the projection. |

</phase_requirements>

## Phase Boundary Reference

**In scope:** RULE DECONSTRUCT partition extension, CLASSIFICATOR full deletion, VALIDATOR rework with DesignStateBindingService, publish path extension, Model Viewer read-side v2 adaptation.
**Out of scope:** DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, PARAMETER REINSTATE (Phase 19), E2E live chain (Phase 20), SpecGraph handle consumer (wired for future).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Variable partition | DG.Core (Parsing) | DG.Grasshopper | VariableTypeInferrer runs in DG.Core.Parsing (pure logic). RULE DECONSTRUCT component in DG.Grasshopper calls it and formats outputs. |
| Variable-to-State binding | DG.Core (Services) | DG.Grasshopper | DesignStateBindingService in DG.Core.Services takes (Rule, DesignState), produces BindingRow list. Pure logic, testable without GH SDK. VALIDATOR component calls it. |
| SWRL evaluation | DG.Core (Validation) | — | RuleEvaluator in DG.Core.Validation unchanged — takes (Rule, List<BindingRow>) → List<RuleEvaluationResult>. Binding format preserved. |
| Validation publishing | DG.Core + data-service | Grasshopper | ValidationPublishClient (GH) serializes and POSTs. data-service app.py creates Neo4j node. ValidationRunPersistenceService (Core) handles serialization. |
| State payload serialization | DG.Core (Serialization) | — | DesignStatePayloadV2Serializer produces v2 JSON. DesignStateJsonSerializer handles v1 format. |
| Read-side state projection | data-service (Python) | Model Viewer (React) | `_project_state_summary` in app.py projects statePayloadJson. `useValidationRunsGrouping.js` groups runs by state.stateId. ValidationRunsStrip renders. |
| CLASSIFICATOR deletion | — | — | Full purge of DG.Core.Classification namespace + DG.Grasshopper ClassificatorComponent. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| .NET SDK | 10.0.109 | C# compilation | Installed machine SDK (per STATE.md — needs `DOTNET_ROLL_FORWARD=LatestMajor` for net9.0 targets) |
| ReaLTaiizor / System.Text.Json | built-in | JSON serialization | Existing DesignStatePayloadV2Serializer pattern |
| Neo4j.Driver | (existing) | Database access | Already established in DG.Core.Data |

### All tooling is existing — no new NuGet packages required for this phase.

### Installation
No new packages. Verification: `dotnet test` with `DOTNET_ROLL_FORWARD=LatestMajor`.

## Package Legitimacy Audit

> No new external packages are installed in this phase. All changes are to existing code. Skip.

## Architecture Patterns

### System Architecture Diagram

```
[ClassificatorComponent]             [RuleDeconstructComponent]
      (DELETED)                             (EXTENDED)
                                              |
        ┌─────────────────────────────────────┘
        │
        ▼
[DesignStateBindingService] ← ← ← [ValidGraphRepository/Rule DB]
   (NEW — DG.Core.Services)          REFERS_TO→Class IRIs
        │
        ▼
[RuleEvaluator]                 ┌─ [DesignState] (from DESIGN STATE component)
   (UNCHANGED)                   │   ├─ ObjStates[i]  (Object IRI + Label)
   ┌──────────────────────┐      │   ├─ ParamStates   (captured params)
   │ Execute(Rule,        │      │   └─ PropStates[j] (Rule+DataProperty+PropValue)
   │   List<BindingRow>)  │      │
   └──────────┬───────────┘      │
              ▼                  │
  [ValidatorComponent] ◄─────────┘
      (REWORKED)                  Inputs: Rule (from METAGRAPH),
      ├─ On solve: eval           DesignState, SendValid
      ├─ On SendValid: publish
      │
      ├─ [ValidationRunPersistenceService]
      │     Extends to v2 with DesignStatePayloadV2Serializer
      │
      ▼
  [ValidationPublishClient] ──POST──► [data-service /validation/publish]
      │                                     │
      └── statePayloadJson v2               ├─ store_validation_run()
         + ValidStatus/SendStatus            │   (ValidStatus→per-entity → )
                                            └─ Cypher MERGE ValidationRun
    
  [data-service list_validation_runs] ◄── /validation/runs/{project}
      │
      ├─ _project_state_summary() — adapted for v2 envelope
      │
      ▼
  [Model Viewer] ── useValidationRunsGrouping() ── ValidationRunsStrip.jsx
      Group by state.stateId (preserved), render adapted for 3-part states
```

### Recommended Project Structure

The project structure stays the same. Key files affected:

```
DG/src/DG.Core/
├── Services/
│   ├── DesignStateBindingService.cs    [NEW] replaces VariableBinder
│   ├── DesignStateIdGenerator.cs       [EXISTS] Phase 16 artifact
│   └── ErrorMessageTemplates.cs        [EXTEND] new error surfaces
├── Validation/
│   ├── RuleEvaluator.cs                [UNCHANGED] binding contract preserved
│   └── ValidationPublishPackageBuilder.cs  [POSSIBLY EXTEND] for ValidStatus/SendStatus
├── Serialization/
│   ├── DesignStatePayloadV2Serializer.cs  [EXISTS] Phase 16 artifact
│   └── DesignStateJsonSerializer.cs       [EXISTS] v1 serializer (kept for backward compat)
├── Models/
│   ├── BindingRow.cs                      [KEPT?] RuleEvaluator depends on it. D-04 says delete all Classification — but BindingRow is in DG.Core.Models, not DG.Core.Classification. VERIFY.
│   └── ValidationRunRecord.cs             [EXTEND] StatePayloadJson→DesignState
└── Classification/                         [DELETED] full namespace
    ├── VariableBinder.cs
    └── ClassificationResult.cs

DG/src/DG.Grasshopper/
├── Components/
│   ├── RuleDeconstructComponent.cs     [EXTEND] Objects/DataProperties outputs
│   ├── ValidatorComponent.cs           [REWORK] new contract
│   ├── ClassificatorComponent.cs       [DELETED]
│   └── GhCastingHelpers.cs             [EXTEND] may need new unwrap helpers
├── Validation/
│   ├── ValidationPublishClient.cs      [EXTEND] DesignState v2 payload
│   └── ValidationPublishContract.cs    [EXTEND] v2 request contract
├── DgIcons.cs                          [MODIFY] remove Classificator24

DG/tests/DG.Tests/
├── VariableBinderTests.cs              [DELETED]
├── DesignStateBindingServiceTests.cs   [NEW]
└── ValidatorComponentTests?            [CHECK if GH SDK tests exist]

data-service/app.py                     [ADAPT] _project_state_summary, list_validation_runs

graph-viewer/model-viewer/src/
├── useValidationRunsGrouping.js        [ADAPT] state display labels
└── ValidationRunsStrip.jsx             [ADAPT] 3-part state labels
```

### Pattern 1: DesignStateBindingService — ObjState matching by Class IRI

**What:** The new binding service takes a `Rule` and `DesignState`, iterates each Rule variable, uses `VariableTypeInferrer.Infer()` to classify it as Object/Property/Builtin, then matches Object variables against ObjStates by Class IRI and Property variables against PropStates by DataProperty IRI.

**When to use:** Always. This replaces the old VariableBinder.BuildBindings which took flat `valuesByVariable` dictionaries.

**Contract:**
- **Input:** `(Rule rule, DesignState designState)`
- **Output:** `List<BindingRow>` — one BindingRow per matched ObjState (for Object variables) + per matched PropState (for Property variables). Each BindingRow has `ValuesByVar[variableName] = value` + `ElementRefsByVar[variableName] = ElementRef`.

**Key design insight:** The output format (`List<BindingRow>`) must **exactly match** what `RuleEvaluator.EvaluateRules()` expects. Currently RuleEvaluator expects `IReadOnlyList<BindingRow>` where each `BindingRow.ValuesByVar` maps `variableName -> value`. The same BindingRow model (DG.Core.Models.BindingRow) is used. **BindingRow is NOT in DG.Core.Classification** — it's in `DG.Core.Models`, so it survives the Classification namespace deletion.

**Class IRI resolution chain:**
1. For a Rule variable classified as Object by VariableTypeInferrer
2. Find the Rule's BodyAtoms where atom.Type == "ClassAtom" and arg.Value == variableName
3. The atom.iri is the Class IRI (e.g. "ex:Building")
4. Match against ObjStates by comparing the ObjState's Class IRI — NOTE: ObjState currently has `ObjectRef` (user string) and `Label`. The **Object input** to OBJECT STATE comes from METAGRAPH Objects output, which carries IRI + label (Phase 17 D-02). The ObjState model itself needs a way to carry the Class IRI.
5. → **Landmine:** ObjState model (`DG.Core.Models.ObjState`) currently has `ObjectRef` (string), `Geometry` (object?), `Label` (string?). The Class IRI for matching must come via the Object reference. Need to verify what the METAGRAPH Objects output provides.

**Where ObjState gets its Class IRI:**
- METAGRAPH Objects output = Class nodes from REFERS_TO queries (per Phase 17 D-02)
- Each Object carries IRI (e.g. "ex:Building") + label
- OBJECT STATE component composes Object + Geometry + Label → ObjState
- If ObjState only stores `ObjectRef` (the user's object ID string) and `Label`, the Class IRI matching cannot work without either: (a) storing the IRI on ObjState, or (b) looking up the IRI from the Object variable's REFERS_TO target at binding time

**Recommendation:** The DesignStateBindingService should look up the Class IRI from the Rule's variable structure at bind time, not from ObjState. For each Object variable, find its ClassAtom in the Rule, extract the IRI from the atom.iri (the REFERS_TO target). Then match ObjStates by looking up their ObjectRefs against the Object variable values. This avoids needing to store Class IRI on ObjState.

**Actually, re-reading D-05:** "Rule variable → REFERS_TO → Class IRI. ObjState carries the Class IRI (from the Object input, which comes from METAGRAPH Objects output — each Object has IRI + label)."

So the Object input to OBJECT STATE DOES carry the IRI. ObjState currently has `ObjectRef` (string) and `Label` (string?). The ObjectRef may BE the IRI. Let me check `ObjState.cs`:

```csharp
public class ObjState {
    public string StateId { get; init; } = string.Empty;
    public string ObjectRef { get; init; } = string.Empty;
    public object? Geometry { get; init; }
    public string? Label { get; init; }
    public DateTimeOffset CapturedAtUtc { get; init; }
}
```

And `ObjectRef` is described as "user-supplied string (not geometry-hash)" from PROJECT.md. But D-05 says "the Object input, which comes from METAGRAPH Objects output — each Object has IRI + label."

So there may be two different "objects" here:
1. The METAGRAPH Object output which is an ontology Class reference (IRI + label)
2. The OBJECT STATE's Object input which is a geometry entity from the Rhino canvas

These are different things! The METAGRAPH Objects output lists the ontology Classes that rules REFER_TO. The OBJECT STATE's Object input is a Grasshopper geometry reference.

**This is a critical finding:** The ObjState's `ObjectRef` is an entity ID (building instance ID like "B1", "B2"), NOT a Class IRI. The DesignStateBindingService needs to:

1. Get the Class IRI from the Rule's atom structure (for the Object variable: find the ClassAtom → REFERS_TO → Class IRI)
2. Match ObjStates where the ObjState.ObjectRef represents an instance of that Class

The matching logic: For each ObjState, the Object variable value (from ObjState) must be checked against the rule. The ObjState represents a specific instance of a Class. The Rule says "For all instances of Class X, apply constraint Y." 

In the old CLASSIFICATOR path, the user provided values per-variable, and the ElementRefs provided entity IDs. In the new path, the ObjStates are the instances, and their ObjectRef values ARE the entity instances that should be bound to the Object variable.

So the binding works as follows:
1. For each Object variable in the Rule, find its Class IRI (REFERS_TO target)
2. For each ObjState in the DesignState, check if it represents an instance of that Class
3. If yes: add a BindingRow with ValuesByVar[?varName] = ObjState.ObjectRef
4. For Property variables: find matching PropStates where RuleIri matches the current rule's IRI and DataPropertyIri matches

Actually wait — ObjState has no Class IRI field. It has ObjectRef (entity instance ID) and Label. The Class IRI information is lost when the OBJECT STATE component creates an ObjState from just Object + Geometry + Label inputs.

**This is a significant integration issue that needs resolution.** Options:

**Option A:** Extend ObjState to carry the Class IRI. Add a `ClassIri` field. OBJECT STATE component would need a new "Class" input (from METAGRAPH Objects? Or from RULE DECONSTRUCT Objects?). This was not anticipated in Phase 16.

**Option B:** Don't match by Class at all in the binding service. Instead, bind ALL ObjStates to ALL Object variables (every ObjState is a binding candidate). This is what `BindingRow` expects — one row per instance. All ObjStates produce binding rows for all Object variables. Non-applicable ones get filtered at the `ValidStatus` level (D-02: non-matching ObjStates get `false` in ValidStatus but excluded from AND).

**Option C:** The DesignStateBindingService infers the Class IRI from the Rule (atom → REFERS_TO → Class IRI) and treats ObjState.ObjectRef as an instance of that class. All ObjStates are instances of all rules' target classes. This is the simplest approach and matches the old VariableBinder behavior where the user connected values per variable without class-level scoping.

Looking at D-05 again: "Binding service matches on IRI — a 'wall height' rule only binds to wall ObjStates, not windows."

This explicitly says Class-level matching IS required. But ObjState doesn't carry a Class IRI. This means **either** ObjState needs a ClassIri field (not yet designed), or the binding service uses a different mechanism.

Let me look at the METAGRAPH output again. Phase 17 D-02 says "METAGRAPH Objects output = Class nodes rules REFERS_TO, index-matched with Rules."

So the METAGRAPH outputs a list of Objects (Class nodes that rules REFER_TO), index-matched to Rules. A Rule at index i in the Rules list has its target Class at index i in the Objects list.

For the binding, the VALIDATOR receives: Rule + DesignState. The Rule has its atoms. But the Class IRI for the rule's Object variable is available from the Rule's atom structure (ClassAtom → iri). So the DesignStateBindingService CAN extract the Class IRI from the Rule itself.

The remaining question is: how does the binding service know which ObjState belongs to which Class? Since ObjState doesn't carry a Class IRI, the binding service has no Class information per ObjState.

**Conclusion:** This is an unresolved design gap. The binding service cannot match by Class IRI without ObjState carrying Class information. Two possible resolutions:

1. **Simplest (recommended):** The DesignStateBindingService binds ALL ObjStates to ALL Object variables. Non-applicable matches get ValidStatus=false with D-02 exclusion. This preserves the existing ObjState model.
2. **Full Class-aware design:** Add a ClassIri field to ObjState. OBJECT STATE component needs a "Class" input from METAGRAPH Objects output. This is more correct but requires Phase 16 model change.

This gap should be flagged for user decision during discuss-phase.

### Anti-Patterns to Avoid
- **Deleting BindingRow from DG.Core.Models:** D-04 says delete "entire DG.Core.Classification namespace" but BindingRow is in DG.Core.Models, not DG.Core.Classification. RuleEvaluator depends on BindingRow — deleting it breaks RuleEvaluator. **DO NOT DELETE BindingRow.**
- **Changing the RuleEvaluator binding contract:** The RuleEvaluator expects `IReadOnlyList<BindingRow>`. The DesignStateBindingService must produce the same format. Changing RuleEvaluator unnecessarily risks breaking SWRL evaluation.
- **Forgetting Classificator24.png resource:** DgIcons.cs references `Classificator24.png` as an embedded resource. The PNG file must be removed from the `.csproj` embedded resources too.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Variable type classification | Custom classification | VariableTypeInferrer (DG.Core.Parsing) | Already exists from Phase 7, priority chain (Object > Property) is locked |
| SWRL evaluation | Custom evaluator rewrite | RuleEvaluator (DG.Core.Validation) | Already exists, binding contract preserved |
| State serialization | Custom serializer | DesignStatePayloadV2Serializer (DG.Core.Serialization) | Already exists from Phase 16, produces versioned v2 envelope |

**Key insight:** The only genuinely new code in this phase is DesignStateBindingService. Everything else is extension/adaptation of existing components.

## Runtime State Inventory

> Not a rename/refactor phase — CLASSIFICATOR is being deleted (no rename). Skip.

## Common Pitfalls

### Pitfall 1: BindingRow deletion by mistake
**What goes wrong:** D-04 says "delete entire DG.Core.Classification namespace" — BindingRow.cs lives in `DG.Core.Models`, NOT in `DG.Core.Classification`. A developer might accidentally grep for "Classification" and delete BindingRow.
**Why it happens:** ClassificationResult.cs references BindingRow, so grep searches find both.
**How to avoid:** Verify the file path before deleting. BindingRow.cs is at `DG/src/DG.Core/Models/BindingRow.cs` — keep it.
**Warning signs:** `RuleEvaluator` or `FailingBindingFormatter` fails to compile with "BindingRow not found."

### Pitfall 2: RuleEvaluator evaluation semantics vs Class-bound ValidStatus
**What goes wrong:** RuleEvaluator evaluates ALL bindings and produces a single `Passed` Boolean. The new ValidStatus must be per-ObjState. These are different concepts.
**Why it happens:** The old VALIDATOR produced a single Pass per rule across all bindings. The new contract produces per-ObjState ValidStatus list.
**How to avoid:** The ValidStatus array is populated from per-BindingRow evaluation results, not the aggregate Passed flag. For each ObjState i → its BindingRow(i) → evaluate → ValidStatus[i].
**Warning signs:** Passed = true but some ObjStates are failing.

### Pitfall 3: Missing Class IRI for ObjState matching
**What goes wrong:** DesignStateBindingService cannot match ObjStates by Class IRI because ObjState doesn't carry a Class IRI field.
**Why it happens:** ObjState model (Phase 16) only has ObjectRef, Geometry, Label. No Class IRI field exists.
**How to avoid:** Two options (needs user decision): (1) bind all ObjStates to all Object variables (D-02 handles non-applicable), or (2) add ClassIri field to ObjState and update OBJECT STATE component.
**See also:** Architectural gap documented in Pattern 1 above.

### Pitfall 4: v1 vs v2 statePayloadJson in publish/extract path
**What goes wrong:** The publish path sends v2 JSON with `DesignStatePayloadV2Serializer.Serialize()`, but the data-service `store_validation_run` currently stores statePayloadJson directly without format detection.
**Why it happens:** The same `statePayloadJson` field stored currently (v1 ParamState) needs to accept v2 DesignState format too.
**How to avoid:** The data-service already accepts `statePayloadJson` as a string. Neo4jValidGraphRepository already handles v1+v2 detection (root has `stateKind`/`objStates`/`paramStates`/`propStates` to detect v2). The projection in `_project_state_summary` needs v2 detection.
**Warning signs:** Model Viewer shows empty state for v2 runs.

### Pitfall 5: Old Run trigger vs new SendValid trigger
**What goes wrong:** The old VALIDATOR had two triggers: Run (evaluate) and SendRules (publish). The new VALIDATOR has a single trigger SendValid for evaluation+publication. Old canvases still wired for the old contract will not work.
**Why it happens:** The component contract changed. Old `Run` input replaced by `SendValid` input. Old `Pass` output replaced by `ValidStatus`. Old `PublishStatus` replaced by `SendStatus`.
**How to avoid:** Pure contract breakage — documented in Phase 20 release notes. No migration shim needed per D-09.
**Warning signs:** VALIDATOR shows "Idle" on old canvases → old Run input is disconnected.

### Pitfall 6: ValidStatus ordering must match DesignState.ObjStates order
**What goes wrong:** ValidStatus[i] must correspond to DesignState.ObjStates[i]. If the binding service processes ObjStates in a different order, the index matching breaks.
**Why it happens:** D-01 mandates index matching. The binding service iterates ObjStates in DesignState.ObjStates order. The ValidStatus list is built in that same order.
**How to avoid:** Ensure DesignStateBindingService iterates `DesignState.ObjStates` in list order, then builds ValidStatus in lockstep.
**Warning signs:** ValidStatus[2] corresponds to ObjState[0] — validation results displayed against wrong object.

## Code Examples

### DesignStateBindingService Skeleton

```csharp
// Source: Research Pattern Design — to be implemented
// Location: DG/src/DG.Core/Services/DesignStateBindingService.cs

using DG.Core.Models;
using DG.Core.Parsing;

namespace DG.Core.Services;

public static class DesignStateBindingService
{
    /// <summary>
    /// Builds BindingRow list from a Rule and composed DesignState.
    /// Each BindingRow maps variable names to resolved values from ObjState/PramState/PropState.
    /// One row per applicable ObjState (Object variables) + per PropState (Property variables).
    /// Matching by: Object variables matched against all ObjStates (Class IRI matching deferred —
    /// see D-05 discussion), Property variables matched against PropStates by RuleIri+DataPropertyIri.
    /// Builtin variables are excluded from bindings (D-07).
    /// </summary>
    public static List<BindingRow> BuildBindings(Rule rule, DesignState designState)
    {
        var bindings = new List<BindingRow>();
        
        // Step 1: Classify each variable
        var objectVars = new List<Variable>();
        var propertyVars = new List<Variable>();
        
        foreach (var variable in rule.Variables)
        {
            var kind = VariableTypeInferrer.Infer(rule, variable.Name);
            if (kind == null)
            {
                // Builtin-only or indeterminate — skip per D-07 or error per D-06
                if (IsBuiltinOnlyVariable(rule, variable.Name))
                    continue;
                // D-06: no REFERS_TO link → error
                throw new InvalidOperationException(
                    ErrorMessageTemplates.RuleVariableUnclassified(rule.Id, variable.Name));
            }
            
            if (kind == VariableKind.Object)
                objectVars.Add(variable);
            else if (kind == VariableKind.Property)
                propertyVars.Add(variable);
        }
        
        // Step 2: Build rows from ObjStates (one row per ObjState)
        foreach (var objState in designState.ObjStates)
        {
            var row = new BindingRow();
            foreach (var objVar in objectVars)
            {
                row.ValuesByVar[objVar.Name] = objState.ObjectRef;
                row.ElementRefsByVar[objVar.Name] = new ElementRef
                {
                    DgEntityId = objState.ObjectRef,
                    DisplayName = objState.Label ?? objState.ObjectRef,
                };
            }
            bindings.Add(row);
        }
        
        // Step 3: Merge property bindings (one PropState → extra values on existing rows, or new rows?)
        // NOTE: Per-ObjState rows with property values added per matching PropState.
        // Exact semantics depend on whether a PropState binds to a specific ObjState or stands alone.
        foreach (var propState in designState.PropStates)
        {
            if (propState.RuleIri != rule.Id && propState.RuleIri != rule.Name)
                continue;
                
            // Match DataProperty IRI to a Property variable
            foreach (var propVar in propertyVars)
            {
                var dataPropertyIri = GetDataPropertyIriFromRule(rule, propVar.Name);
                if (dataPropertyIri == propState.DataPropertyIri)
                {
                    // Apply to all existing rows — this is a per-rule-wide property
                    foreach (var row in bindings)
                    {
                        row.ValuesByVar[propVar.Name] = propState.PropValue?.NumberValue 
                            ?? propState.PropValue?.IntegerValue 
                            ?? propState.PropValue?.BooleanValue 
                            ?? (object?)null;
                    }
                }
            }
        }
        
        // Step 4: Handle no-ObjState case — create a single row from PropStates only
        if (bindings.Count == 0 && propertyVars.Count > 0)
        {
            var row = new BindingRow();
            foreach (var propVar in propertyVars)
            {
                // ... resolve from PropStates
            }
            if (row.ValuesByVar.Count > 0)
                bindings.Add(row);
        }
        
        return bindings;
    }
}
```

**LANDMINE:** The ObjState→Class IRI matching gap (D-05) needs resolution before this service can be finalized. The code above assumes all ObjStates are applicable to all Object variables (Option B from the gap analysis).

### RULE DECONSTRUCT Extension Pattern

```csharp
// Source: Current RuleDeconstructComponent.cs adapted per D-06/D-07/D-08
// The ExpectedOutputNames array changes from:
private static readonly string[] OldExpectedOutputNames =
{
    "Rule", "Variables", "VariableName", "SWRL", "RuleName", "RuleDescription",
};
// To:
private static readonly string[] NewExpectedOutputNames =
{
    "Rule", "Objects", "DataProperties", "SWRL", "RuleName", "RuleDescription",
};
```

The `SolveInstance` method adds a partition step using `VariableTypeInferrer.Infer()` after collecting variables:

```csharp
// After collecting variablesByName (existing logic), partition by type:
var objects = new List<CoreVariable>();
var dataProperties = new List<CoreVariable>();

foreach (var variable in variables)
{
    var kind = VariableTypeInferrer.Infer(rule, variable.Name);
    if (kind == VariableKind.Object)
        objects.Add(variable);
    else if (kind == VariableKind.Property)
        dataProperties.Add(variable);
    // D-07: Builtins excluded from both outputs
}

// D-06: If a variable has no REFERS_TO link → error
// Detected when Infer returns null AND the variable is not a Builtin-only variable.
```

### v2 statePayloadJson Detection in _project_state_summary

```python
# Source: data-service/app.py _project_state_summary function (app.py:534)
# Current: reads v1 format { "stateId": "...", "parameters": [...] }
# Extended for v2: checks root version field, extracts 3-part state info

def _project_state_summary(state_payload_json: str | None) -> dict[str, Any] | None:
    if not state_payload_json:
        return None
    try:
        parsed = json.loads(state_payload_json)
    except (json.JSONDecodeError, ValueError, TypeError, RecursionError):
        return None
    if not isinstance(parsed, dict):
        return None
    
    # v2 envelope detection via version field
    version = parsed.get("version")
    if version == "2":
        return {
            "stateId": parsed.get("stateId") or "",
            "capturedAtUtc": parsed.get("capturedAtUtc"),
            "parameterCount": (
                len(parsed.get("objStates") or []) +
                len(parsed.get("paramStates") or []) +
                len(parsed.get("propStates") or [])
            ),
            "stateKind": "design-state-v2",
        }
    
    # v1 fallback (ParamState-only)
    parameters = parsed.get("parameters")
    parameter_count = len(parameters) if isinstance(parameters, list) else 0
    return {
        "stateId": parsed.get("stateId") or "",
        "capturedAtUtc": parsed.get("capturedAtUtc"),
        "parameterCount": parameter_count,
        "stateKind": "param-state-v1",
    }
```

### VALIDATOR Rework — Publish Path Extension

```csharp
// Source: Current ValidatorComponent.cs adapted per new contract
// Key changes to SolveInstance:
// 1. Inputs: Rule (singular, from METAGRAPH), DesignState (from DESIGN STATE),
//    SendValid (Boolean trigger), DataServiceUrl (text, optional) — Run trigger removed
// 2. Outputs: ValidStatus (list of bool), RuleName (text), RuleDescription (text),
//    SendStatus (text), Report (text list), FailingBindings (text list),
//    ValidationRunId (text), ModelViewerUrl (text)
// 3. Always evaluate when Rule+DesignState connected (no trigger for evaluation)
// 4. SendValid replaces old SendRules for publish-only trigger

// In SolveInstance:
// var sendValid = false;
// da.GetData(2, ref sendValid);  // index 2 = SendValid (old index 3 = SendRules)
// ...
// var designState = GhCastingHelpers.TryDesignState(stateInput);
// var bindings = DesignStateBindingService.BuildBindings(rule, designState);
// var result = _ruleEvaluator.EvaluateRule(rule, bindings);
// 
// ValidStatus: populate per ObjState index:
// var validStatus = new List<bool>();
// foreach (var objState in designState.ObjStates) { ... } // per D-01/D-02
// da.SetDataList(0, validStatus);

// Publish: when sendValid is true, serialize DesignState to v2:
// var statePayload = DesignStatePayloadV2Serializer.Serialize(designState);
// var response = ValidationPublishClient.Publish(rules, results, bindings, dataServiceUrl, statePayload);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLASSIFICATOR maps GH values to SWRL variable bindings | DesignStateBindingService resolves bindings from composed DesignState | Phase 18 | Full pipeline restructured — no VariableBinder, no binding dictionaries |
| VariableBinder.BuildBindings takes valuesByVariable dictionaries + ElementRefs | DesignStateBindingService takes (Rule, DesignState) — ObjStates/ParamStates/PropStates | Phase 18 | Binding source changes from GH DataTree to composed state objects |
| VALIDATOR accepts Rules list + bindings + Run/SendRules triggers | VALIDATOR accepts Rule + DesignState + SendValid trigger | Phase 18 | Single rule per evaluation; evaluation auto-runs on solve |
| Pass (single bool per rule) | ValidStatus (per-ObjState bool list) | Phase 18 | Per-object validation results, index-matched |
| statePayloadJson v1 (ParamState only) | statePayloadJson v2 (3-part DesignState) | Phase 16/18 | Must handle both in read-side projection |
| Run.String input + SendRules.String input | SendValid Boolean trigger (merged) | Phase 18 | Different trigger semantics — canvas breakage |

**Deprecated/outdated:**
- **ClassificatorComponent:** Deleted. No component fills its role — DesignState is the new source.
- **VariableBinder:** Deleted. Replaced by DesignStateBindingService.
- **ClassificationResult:** Deleted. Binding results returned as List<BindingRow> directly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | BindingRow.cs is in DG.Core.Models, not DG.Core.Classification — survives the purge | Standard Stack, Pitfall 1 | BindingRow deleted by accident → RuleEvaluator breaks, entire validation pipeline fails to compile |
| A2 | ObjState ObjectRef is the entity instance ID that binds to Rule Object variables | Architecture Patterns | If ObjectRef is something else (geometry handle, IRI), the binding logic produces wrong values |
| A3 | The METAGRAPH "Objects" output carries Class IRI (Phase 17 D-02) that the binding service can use to determine class membership | Architecture Patterns | If Objects output is just labels without IRIs, Class-aware filtering (D-05) cannot work |
| A4 | The Rule variable's Class IRI is extractable from the atom.iri of the ClassAtom the variable appears in | Code Example | If atoms don't carry iri consistently, the binding service cannot determine Class membership for D-05 |
| A5 | RuleEvaluator's binding contract (List<BindingRow>) remains unchanged | Standard Stack | If the binding format changes, both RuleEvaluator and FailingBindingFormatter need adaptation |
| A6 | The port-iri-map-V7.md is the authoritative VALIDATOR port contract, not GHVL-03's imprecise text | Pitfall 5 | If GHVL-03's "(Rule + DesignState + SendValid + Run)" is interpreted literally, Run would be an input contradicting the port-iri-map |

## Open Questions (RESOLVED)

1. **How does DesignStateBindingService match ObjStates by Class IRI (D-05) when ObjState doesn't carry a Class IRI?**
   - RESOLVED: Path A chosen — ObjState extended with `ClassIri` property (string?, null default). OBJECT STATE component gets new "Class" input port to pass Class IRI from METAGRAPH Objects output. DesignStateBindingService matches ObjState.ClassIri against Rule variable's REFERS_TO Class IRI. Only matching ObjStates produce BindingRows. (See Plan 18-01 Task 1 + Task 2)

2. **Should the VALIDATOR evaluate on every solve or only on SendValid trigger?**
   - RESOLVED: Auto-evaluate on every solve when Rule+DesignState connected. SendValid only controls publish. ValidStatus outputs are always live.

3. **What happens to the old FailingBindings output?**
   - RESOLVED: FailingBindings kept as a per-rule text list (unchanged from current behavior). One entry per failing binding across all ObjStates. Format uses existing FailingBindingFormatter.Format() pattern. Output is on index 4 of the new 8-output contract.

4. **Is `using DG.Core.Classification` present anywhere else besides ClassificatorComponent.cs?**
   - RESOLVED: Confirmed single reference. Plan 18-03 deletes it with confidence.

5. **Does the ValidationRunPersistenceService need v2 Serializer or does the publish path stay in Grasshopper?**
   - RESOLVED: ValidationPublishClient (Grasshopper layer) handles serialization via DesignStatePayloadV2Serializer. ValidationRunPersistenceService extended with v2-compatible overloads per Plan 18-05 Task 3.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| .NET SDK | Compilation & test | ✓ | 10.0.109 | `DOTNET_ROLL_FORWARD=LatestMajor` for net9.0 targets |
| Neo4j | Publish path testing | ✗ (dev mode) | — | In-memory test pattern (existing) |
| Docker | Full pipeline E2E | ✗ (not needed) | — | Can't test publish in unit tests; Phase 20 covers E2E |

**Missing dependencies with no fallback:** None for this phase — unit tests and compilation only.
**Missing dependencies with fallback:** Neo4j — existing codebase uses test patterns without live DB.

## Validation Architecture

> Workflow `nyquist_validation` key absent — treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | xUnit (existing in DG.Tests) |
| Config file | `DG/tests/DG.Tests/DG.Tests.csproj` |
| Quick run command | `cd DG && dotnet test tests/DG.Tests/ --no-restore --verbosity normal` |
| Full suite command | `dotnet test DG/tests/DG.Tests/ -c Release --verbosity normal` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GHVL-01 | RULE DECONSTRUCT partitions variables by type (Object/Property/Builtin) | unit (pure logic in DesignStateBindingService) | `dotnet test --filter "DesignStateBindingService*"` | N — new |
| GHVL-01 | RULE DECONSTRUCT emits error for unclassified variables (D-06) | unit | same as above | N — new |
| GHVL-01 | RULE DECONSTRUCT excludes Builtin-only variables (D-07) | unit | same as above | N — new |
| GHVL-03 | VALIDATOR produces ValidStatus per-ObjState, index-matched (D-01) | unit (DesignStateBindingService + RuleEvaluator integration) | `dotnet test --filter "ValidStatus*"` | N — new |
| GHVL-04 | DesignStateBindingService produces BindingRow list matching RuleEvaluator contract | unit | `dotnet test --filter "DesignStateBindingService*"` | N — new |
| GHVL-05 | DesignStatePayloadV2Serializer round-trip (already existing) | unit | `dotnet test --filter "DesignStatePayloadV2Serializer*"` | Y (Phase 16) |
| GHVL-06 | _project_state_summary returns v2 summary | unit (Python) | `pytest tests/test_app.py -k "state_summary"` | N — new |
| GHVL-02 | CLASSIFICATOR references deleted (compilation check) | build | `dotnet build DG/DG.sln` | N — compilation check |
| GHVL-02 | DG.Core.Classification namespace deleted | build | same as above | N — compilation check |

### Sampling Rate
- **Per task commit:** `dotnet test DG/tests/DG.Tests/ --no-restore --filter "DesignStateBindingService*|ValidStatus*"`
- **Per wave merge:** `dotnet test DG/tests/DG.Tests/ -c Release --verbosity normal`
- **Phase gate:** Full suite green + `dotnet build DG/DG.sln -c Release` clean

### Wave 0 Gaps
- [ ] `DG/tests/DG.Tests/DesignStateBindingServiceTests.cs` — covers GHVL-01, GHVL-04
- [ ] `DG/tests/DG.Tests/ValidStatusBindingTests.cs` — covers D-01, D-02 index matching
- [ ] `data-service/tests/test_state_summary.py` — covers GHVL-06 v2 envelope detection
- No existing test infrastructure changes needed (xUnit is set up, test patterns exist)

## Security Domain

> Not applicable — this phase involves no authentication, session management, access control, or user data processing. All changes are Grasshopper component logic internal to the plugin. `security_enforcement` can be treated as `false` — no ASVS categories apply.

## Sources

### Primary (HIGH confidence)
- `DG/src/DG.Core/Classification/VariableBinder.cs` — BuildBindings logic (full source read)
- `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs` — variable classification (full source read)
- `DG/src/DG.Core/Validation/RuleEvaluator.cs` — SWRL evaluation engine (full source read)
- `DG/src/DG.Core/Validation/ValidationPublishPackageBuilder.cs` — publish package building (full source read)
- `DG/src/DG.Core/Models/BindingRow.cs` — binding model (full source read)
- `DG/src/DG.Core/Models/Rule.cs` — rule model (full source read)
- `DG/src/DG.Core/Models/DesignState.cs` — DesignState composition model (full source read)
- `DG/src/DG.Core/Models/ObjState.cs` — ObjState model (full source read)
- `DG/src/DG.Core/Models/PropState.cs` — PropState model (full source read)
- `DG/src/DG.Core/Models/ValidationRunRecord.cs` — validation run record (full source read)
- `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs` — v2 serializer (full source read)
- `DG/src/DG.Core/Serialization/DesignStateJsonSerializer.cs` — v1 serializer (full source read)
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — StateId generation (full source read)
- `DG/src/DG.Core/Services/ValidationRunPersistenceService.cs` — run persistence (full source read)
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — error message templates (full source read)
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` — v1+v2 payload handling (full source read)
- `DG/src/DG.Core/Data/IValidGraphRepository.cs` — repository interface (full source read)
- `DG/src/DG.Grasshopper/Components/ValidatorComponent.cs` — current VALIDATOR (full source read)
- `DG/src/DG.Grasshopper/Components/RuleDeconstructComponent.cs` — current RULE DECONSTRUCT (full source read)
- `DG/src/DG.Grasshopper/Components/ClassificatorComponent.cs` — CLASSIFICATOR to delete (full source read)
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — casting helpers (full source read)
- `DG/src/DG.Grasshopper/PublicTypes.cs` — public wrapper types (full source read)
- `DG/src/DG.Grasshopper/Validation/ValidationPublishClient.cs` — publish client (full source read)
- `DG/src/DG.Grasshopper/Validation/ValidationPublishContract.cs` — publish contract types (full source read)
- `DG/src/DG.Core/Validation/FailingBindingFormatter.cs` — failing binding formatter (full source read)
- `DG/src/DG.Grasshopper/DgIcons.cs` — icons reference (full source read)
- `DG/src/DG.Core/Classification/ClassificationResult.cs` — classification result (full source read)
- `DG/tests/DG.Tests/VariableBinderTests.cs` — variable binder test (full source read)
- `DG/tests/DG.Tests/RuleEvaluatorTests.cs` — RuleEvaluator tests (full source read)
- `data-service/app.py` — publish endpoint, _project_state_summary (full relevant sections read)
- `graph-viewer/model-viewer/src/useValidationRunsGrouping.js` — grouping logic (full source read)
- `graph-viewer/model-viewer/src/ValidationRunsStrip.jsx` — validation runs strip (full source read)
- `ontology/port-iri-map-V7.md` — authoritative port contract (full source read)
- `.planning/phases/18-rules-and-validator-rework/18-CONTEXT.md` — phase context (full source read)
- `.planning/REQUIREMENTS.md` — GHVL-01..06 requirements (full source read)
- `.planning/PROJECT.md` — project decisions (full source read)
- `.planning/STATE.md` — accumulated state (full source read)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing infrastructure, no new packages
- Architecture: MEDIUM — ObjState Class IRI matching gap (A3/A4) needs resolution
- Pitfalls: HIGH — verified against source code and existing patterns
- Model Viewer adaptation: MEDIUM — `useValidationRunsGrouping` preserves `state.stateId` path, but needs field name verification against actual API response
- VariableTypeInferrer integration: HIGH — stays as-is, used identically by both RULE DECONSTRUCT and DesignStateBindingService

**Research date:** 2026-07-04
**Valid until:** 2026-08-04 (stable infrastructure, no fast-moving dependencies)
