# Architecture Research

**Domain:** v3.0 Typed Variables and Composable Design State — integration into existing DG Architecture
**Researched:** 2026-05-11
**Confidence:** HIGH (based on direct codebase inspection of all named files)

---

## Five Integration Questions — Direct Answers

### (a) Where Does Object/Property Type Inference Live?

**Read-time in Neo4j repository — not write-time in n8n.**

The inference rule is: a Var that appears as arg-1 of a ClassAtom is an Object variable; a Var that appears as arg-1 of a DataPropertyAtom is a Property variable. Both atom types already exist as `Atom.type` on nodes loaded by `Neo4jRuleRepository.GetRulesAsync`. The `Atom` model (`DG/src/DG.Core/Models/Atom.cs`) carries `Type`, `PredicateIri`, and `Args` after the atoms query runs. The variables are then assembled by `PopulateVariables()` (`Neo4jRuleRepository.cs:212-256`), which currently does not classify by kind.

The correct insertion point is the end of `PopulateVariables()`: for each variable name, inspect the atoms it appears in and assign `VariableKind.Object` if any atom with that var is a ClassAtom, `VariableKind.Property` otherwise. This stays in `DG.Core.Data.Neo4jRuleRepository` — pure read-path, zero schema change to Neo4j.

n8n ingest does NOT need to know about variable kinds. The SWRL metagraph already encodes the structural fact (ClassAtom vs DataPropertyAtom) that determines the kind. Adding a `kind` property to `Var` nodes in n8n would be redundant data duplication and would require every existing Cypher template to be updated. Reject this option.

The `Variable` model (`DG/src/DG.Core/Models/Variable.cs`) currently has only `Name` and `InferredDatatype`. A new `Kind` property (enum `VariableKind { Object, Property }`) is added here. The public `DG.Variable` wrapper in `DG.Grasshopper` must be updated to mirror it.

**Where the inference appears in the data flow:**

```
Neo4jRuleRepository.GetRulesAsync()
  → LoadAtomsAsync()       ← atom type already present in DB
  → PopulateVariables()    ← NEW: assign VariableKind per variable name
  → Rule.Variables[]       ← now carries Kind
  → MetagraphComponent output "Rules"
  → RuleDeconstructComponent inputs Rule, separates into Objects list + Properties list
```

No Neo4j write, no n8n change, no schema migration.

---

### (b) DesignState Class Hierarchy in Neo4j

**Recommendation: single label `DesignState` with `kind` property (`DefState` | `ObjectState`), not multi-label, not separate labels.**

Rationale by criterion:

| Criterion | Multi-label (`:DesignState:DefState`) | Single label + `kind` | Separate labels (`DefState`, `ObjectState`) |
|-----------|--------------------------------------|----------------------|---------------------------------------------|
| Query pattern | `MATCH (d:DesignState)` works; `MATCH (d:DefState)` also works — two valid paths, ambiguity risk | `MATCH (d:DesignState {kind:'DefState'})` — single clear pattern | `MATCH (d:DefState)` or `MATCH (d:ObjectState)` — no parent class query without UNION |
| NeoVis display | Renders by first label; multi-label display is inconsistent across Neo4j versions | Single label = deterministic NeoVis node type mapping | Two separate node visuals; harder to show class relationship |
| Schema migration | MATCH-SET ADD label on existing nodes is low risk | MATCH-SET ADD `kind` property on existing nodes is lowest risk | MATCH-REMOVE + CREATE new nodes with new label = highest risk |
| Cypher template | Extra label in every MERGE; LLM must know the compound label rule | Simple: `MERGE (d:DesignState {DesignState_Id: $id}) SET d.kind = 'DefState'` | No parent-class relationship possible without explicit relationship |
| Backward compat | Neo4j multi-label is stable but adds complexity to existing `MATCH (d:DesignState)` queries which must continue to return both subtypes | Existing queries on `DesignState` nodes just gain a new property — zero breakage | Existing GH components output `DesignState` label; all must be updated |

Use `kind` property. This is also the pattern already established by the `Rule` node which has a `kind: "violation|compliance"` property rather than separate node labels.

**ID prefix convention:**

```
DefState:    DS_<contentHash16>        (existing DesignStateSnapshot.StateId pattern — preserve)
ObjectState: OS_<elementId>_<ruleId>  (new; unique per object-rule binding)
DesignState: (parent has no standalone instances — it is a virtual group, not a separate node)
```

Wait: the v3.0 spec says `DesignState` is the parent class, with `DefState` and `ObjectState` as subclasses. In Neo4j terms, the cleanest mapping is: every DesignState-family node has label `DesignState` and `kind` property. The parent class has no concrete instances — there are only `DefState` and `ObjectState` instances.

**NeoVis config impact:** `config.template.js` needs one entry for `DesignState` label with style variations driven by `kind` property (color/icon). This is a single label → single NeoVis config block, cleanest possible.

---

### (c) Cross-Rule Object Identity and ElementId Bindings

**Where bindings are stored: on the `DesignState` node (specifically the composed `DesignState` output of the reworked DESIGN STATE component), NOT in a cross-cutting cache.**

The current `BindingRow.ElementRefsByVar` holds per-run bindings in C# memory. For v3.0, the Object variable cross-rule identity means: the same Object variable instance (e.g. `?b` for Building) must resolve to the same set of ElementIds across multiple rules applied in the same run. The storage answer:

```
DESIGN STATE component (reworked)
  inputs: DefState (from DESIGN STATE legacy behavior), ObjectState list
  outputs: IdRefs (list of element IDs), GeoRefs (geometry), DefState

IdRefs are held in the DesignState output object in C# component state
→ wired to CLASSIFICATOR.IdRefs
→ CLASSIFICATOR uses IdRefs as the cross-rule object binding anchor
→ VALIDATOR receives the composed state with IdRefs attached
→ ValidationPublishClient sends IdRefs alongside the run
```

**Regeneration trigger rule:** Element Ids (ObjectRef bindings) are recomputed only when `DefState` changes. `DefState` changes are detected by comparing `DefState.StateId` (the content hash). If `DefState.StateId` is unchanged, the cached `IdRefs` list is reused without re-querying geometry.

The C# component holds a cached tuple: `(string lastDefStateId, IReadOnlyList<string> cachedIdRefs)`. On SolveInstance, if `DefState.StateId == lastDefStateId`, skip geometry re-scan and emit cached IdRefs. On change, re-scan ObjectState inputs, rebuild IdRefs list, update cache. This is local C# component state — no Neo4j involvement.

**What goes into Neo4j ValidationRun:** The composed DesignState (including IdRefs and DefState parameters) is serialized as `statePayloadJson` on the `ValidationRun` node, extending the existing `statePayloadJson` field. No new Neo4j node type needed for the bindings themselves at run time. The `ObjectState` nodes in Neo4j (if persisted) serve as structural descriptors, not as runtime binding caches.

---

### (d) METAGRAPH Loader Changes for RULE DECONSTRUCT

**The problem:** RULE DECONSTRUCT has no Neo4j connection. Currently it takes a single `Rule` item from METAGRAPH output and extracts variables. In v3.0 it must also emit `Runs` — but Runs live in `ValidationGraph` which RULE DECONSTRUCT cannot query.

**Solution: METAGRAPH loads Runs in its own async query and passes them through as a new output.**

The METAGRAPH component currently runs one async load task (`_ruleRepository.GetRulesAsync`). In v3.0 it runs two concurrent tasks:

1. Existing: `IRuleRepository.GetRulesAsync` → Rules output
2. New: `IValidationRunRepository.GetRunsAsync` (new interface/class) → Runs output

Both tasks are awaited on the same `ScheduleSolution` callback. METAGRAPH gains four new outputs:

| Output index | Name | Type | Source |
|---|---|---|---|
| 0 | Rules | `IReadOnlyList<DG.Rule>` | existing |
| 1 | RuleName | `IReadOnlyList<string>` | existing |
| 2 | Count | int | existing |
| 3 | Objects | `IReadOnlyList<DG.Variable>` where Kind=Object | derived from rules |
| 4 | Properties | `IReadOnlyList<DG.Variable>` where Kind=Property | derived from rules |
| 5 | DesignStates | `IReadOnlyList<DG.DesignState>` | from ValidationGraph (new query) |
| 6 | Runs | `IReadOnlyList<DG.ValidationRunQueryResult>` | from ValidationGraph (reuse existing query service) |

The `Objects` and `Properties` outputs are derived by iterating the loaded rules' variables and partitioning by `Kind`. No second DB query needed.

`ValidationRunsQueryService` already exists at `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` and returns `IReadOnlyList<ValidationRunQueryResult>`. METAGRAPH creates an instance of it and calls `QueryAsync(connection, ruleId: null, stateId: null)` to get all runs. The existing service is reused without modification.

**DataTree flow from METAGRAPH to RULE DECONSTRUCT:**

METAGRAPH emits `Rules` as a flat list (existing). RULE DECONSTRUCT receives a single `Rule` item wired from a GH List Item or directly. The `Runs` output from METAGRAPH feeds RULE DECONSTRUCT's new `Runs` input as a list. RULE DECONSTRUCT then filters `Runs` to those referencing its input Rule's ID and emits them as the `Runs` output. No DataTree branching needed — all flat lists, consistent with existing component contracts.

```
METAGRAPH.Rules  → (List Item or split) → RULE DECONSTRUCT.Rule
METAGRAPH.Runs   → ─────────────────────→ RULE DECONSTRUCT.Runs (filter by rule)
```

This preserves RULE DECONSTRUCT's stateless, no-Neo4j nature: it only filters and restructures data already loaded by METAGRAPH.

---

### (e) Build Order — Phase Dependency Graph

The following dependency relationships are hard (a phase cannot start until its dependency is complete):

```
Schema changes (DG.Core models + Neo4j nodes)
  ↓
Neo4jRuleRepository type inference  ─────────────────────────────────┐
  ↓                                                                   │
METAGRAPH output expansion (Objects/Properties/Runs outputs)          │
  ↓                                                                   │
RULE DECONSTRUCT rework (Objects/Properties/Runs outputs)    ← parallel with ObjectState nodes (right)
  ↓                                                                   │
CLASSIFICATOR rework (new inputs/outputs)                ←────────────┤
  ↓                                                                   │
DESIGN STATE rework (new inputs/outputs) + OBJECT STATE new component─┘
  ↓
VALIDATOR unchanged; ValidationPublishClient extended
  ↓
VALIDATION RUNS → RUN DECONSTRUCT rename + output changes
  ↓
Schema propagation sweep (cypher_template, dataset_schema, n8n prompts, NeoVis config)
```

**What can run in parallel:**

- OBJECT STATE (new component) implementation is independent of RULE DECONSTRUCT rework. Both depend only on Schema (models) being done.
- VARIABLE NAME (new component) depends only on `Variable.Kind` being available — can be built alongside RULE DECONSTRUCT.
- n8n workflow prompt updates (schema propagation) are independent of all GH component work and can proceed after the schema is finalized.
- NeoVis config update is fully independent — no GH or data-service dependency.
- data-service `statePayloadJson` format extension (to include IdRefs) depends on the DesignState model shape being final.

---

## System Architecture — v3.0 Grasshopper Component Graph

### Current Data Flow (v2.0)

```
CONNECTOR → METAGRAPH (Rules, RuleName, Count)
              ↓
           RULE DECONSTRUCT (Rule, Variables, VariableName, SWRL, RuleName, RuleDescription)
                            Variables ↓    VariableName ↓
                         DESIGN STATE (State) ───────────────────────────┐
                                               ↓                         │
                           CLASSIFICATOR (BoundVariables, MissingVariables, Status, State)
                                           ↓                     State ↓
                                        VALIDATOR ←──────────────────────┘
                                           ↓
                                   data-service publish → Neo4j ValidationRun + Speckle

VALIDATION RUNS (Runs, Results, States, Status) ← query Neo4j ValidationGraph
REINSTATE ← States output
```

### Target Data Flow (v3.0)

```
CONNECTOR → METAGRAPH (Rules, RuleName, Count, Objects, Properties, DesignStates, Runs)
              ↓              ↓             ↓
           [Rules]        [Objects]    [Runs]
              ↓              │             │
           RULE DECONSTRUCT  │             │
           (Rule, Objects,   │             │
            Properties, Runs)│             │
                 ↓           │             │
           [Objects]         │             │
           [Properties]      │             │
           [Runs]            │             │
                 ↓      ←────┘             │
           CLASSIFICATOR (new inputs:      │
             Rule, Objects, Properties,    │
             PropValues, IdRefs, GeoRefs,  │
             DefState)                     │
             outputs:                      │
             BoundVariables,              │
             MissingVariables, Status,    │
             Values[DataTree], Variables, │
             DefState)                     │
                 ↓                         │
           VALIDATOR (unchanged inputs)    │
                 ↓                         │
         data-service publish             │
                                           ↓
           RUN DECONSTRUCT ←──── METAGRAPH.Runs
           (passing items, failing items,
            RunId, DateCreated, State)

OBJECT STATE (new) → IdRefs, GeoRefs → DESIGN STATE (reworked) → CLASSIFICATOR
VARIABLE NAME (new) → Variable → Name string
```

---

## Component Boundaries — New vs Modified

### Brand New Artifacts

| Artifact | Location | Responsibility |
|----------|----------|----------------|
| `VariableKind` enum | `DG/src/DG.Core/Models/Variable.cs` | `Object \| Property` classification |
| `ObjectStateComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Accepts ObjectRef + GeoRef inputs, emits `DG.ObjectState` |
| `VariableNameComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Accepts `DG.Variable` input, emits name string |
| `DG.ObjectState` (public type) | `DG/src/DG.Grasshopper/` public API surface | GH-wirable ObjectState wrapper |
| `IValidationRunRepository` (optional) | `DG/src/DG.Core/Data/` | Interface for run loading (if METAGRAPH needs DI) |

### Modified Artifacts — Grasshopper Components

| Artifact | Location | What Changes |
|----------|----------|--------------|
| `Variable.cs` | `DG/src/DG.Core/Models/Variable.cs` | Add `Kind` property (VariableKind enum) |
| `MetagraphComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Add outputs: Objects, Properties, DesignStates, Runs; second concurrent load task for Runs |
| `Neo4jRuleRepository.cs` | `DG/src/DG.Core/Data/` | `PopulateVariables()` assigns `Kind` by inspecting atom types |
| `RuleDeconstructComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Remove Variables+VariableName outputs; add Objects, Properties, Runs outputs; add Runs input |
| `ClassificatorComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Add Rule/Objects/Properties/PropValues/IdRefs/GeoRefs/DefState inputs; add Values(DataTree)+Variables+DefState outputs; rename ElementRefs→GeoRefs |
| `DesignStateComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Rework inputs to ObjectState+DefState; outputs become IdRefs, GeoRefs, DefState; add cached IdRefs regeneration logic |
| `ValidationRunsComponent.cs` | `DG/src/DG.Grasshopper/Components/` | Rename file→`RunDeconstructComponent.cs`; update component name/GUID; change outputs to passing items, failing items, RunId, DateCreated, State |
| `DesignStateSnapshot.cs` | `DG/src/DG.Core/Models/` | Extend serialization to include IdRefs list |
| `ValidationPublishClient.cs` (and related) | `DG/src/DG.Core/Validation/` or adjacent | Pass IdRefs in publish payload |

### Modified Artifacts — Schema Propagation

| Artifact | Location | What Changes |
|----------|----------|--------------|
| `cypher_template.txt` | repo root | Add DesignState node shapes with `kind` property; update Var node to reflect typed classification note |
| `training/dataset_schema.json` | `training/` | Add DesignState/DefState/ObjectState to node section; document VariableKind |
| n8n workflow prompts | `n8n/workflows/*.json` | Update LLM system prompts to describe variable kind inference (ObjectProperty, ClassAtom distinction) |
| `config.template.js` | `graph-viewer/` | Add NeoVis label config for DesignState nodes |
| `data-service/app.py` | `data-service/` | Extend `statePayloadJson` format to include IdRefs; update `_project_state_summary()` if needed |

---

## Architectural Patterns for v3.0

### Pattern 1: Read-Time Inference, Not Write-Time Storage

**What:** Variable kind (Object vs Property) is inferred from atom structure at read time in `Neo4jRuleRepository.PopulateVariables()`, not stored as a `kind` property on `Var` nodes in Neo4j.

**When to use:** Always — the structural information is already present (atom type tells us). Avoid duplicating it.

**Trade-offs:** Cannot query "give me all Object variables" from Cypher alone; but this query is never needed server-side. GH components always receive full Rule objects. The inference is O(atoms) per rule, negligible cost.

**Example sketch:**
```csharp
// In PopulateVariables(), after collecting atom args:
var objectVarNames = new HashSet<string>(
    rule.BodyAtoms
        .Where(a => a.Type == "ClassAtom")
        .SelectMany(a => a.Args.Where(arg => arg.Kind == ArgKind.Variable).Select(arg => arg.Value)),
    StringComparer.Ordinal);

foreach (var name in names.OrderBy(n => n, StringComparer.Ordinal))
{
    rule.Variables.Add(new Variable
    {
        Name = name,
        Kind = objectVarNames.Contains(name) ? VariableKind.Object : VariableKind.Property,
    });
}
```

### Pattern 2: Composable DesignState via Input Aggregation

**What:** The reworked DESIGN STATE component aggregates `ObjectState` items (each carrying ElementId + geometry) and a `DefState` item (parametric snapshot) into a single composed output. This replaces the current single-path `DesignStateSnapshot → State` output.

**When to use:** DESIGN STATE is the composition point. Users wire one or more OBJECT STATE components and one (legacy) DefState capture into DESIGN STATE, which validates, deduplicates, and caches the composed state.

**Trade-offs:** The reworked DESIGN STATE output signature changes. Existing canvases wired to the old single `State` output will need rewiring. This is a deliberate v3.0 breaking change on canvas wiring (not API, since the canvas is user-configured, not code-deployed).

### Pattern 3: IdRef Cache Keyed on DefState Hash

**What:** DESIGN STATE component holds `_cachedIdRefs` (list of element ID strings) and `_lastDefStateId` (the DefState content hash). On each SolveInstance, if DefStateId is unchanged, IdRefs are emitted from cache without re-scanning ObjectState geometry.

**When to use:** This is the regeneration trigger rule: geometry re-scan only on DefState parameter change.

**Trade-offs:** Cache is per-component-instance (GH component field), invalidated correctly. Geometry scans are expensive in Rhino; caching is necessary for responsive canvas.

### Pattern 4: METAGRAPH as the Single Neo4j Consumer for Downstream Components

**What:** METAGRAPH is the only component with a Neo4j connection in the validation pipeline reading both Metagraph and ValidationGraph data. All downstream components (RULE DECONSTRUCT, CLASSIFICATOR, DESIGN STATE) operate on data already loaded by METAGRAPH. RUN DECONSTRUCT receives pre-loaded Runs from METAGRAPH.

**When to use:** Always. This keeps the component graph's network dependency surface minimal: only METAGRAPH and CONNECTOR need database credentials and network access.

**Trade-offs:** METAGRAPH becomes heavier — it now runs two concurrent async queries (rules + runs). The existing `ScheduleSolution` polling pattern (`ContinueWith` on task completion) must be extended to wait for both tasks. Use `Task.WhenAll` and only fire `ExpireSolution` after both complete.

---

## Data Flow — v3.0 Key Paths

### Validation Run with Typed Variables and ObjectState

```
[User action: canvas solve]
CONNECTOR → connection object
METAGRAPH (Refresh=true)
  → Task 1: Neo4jRuleRepository.GetRulesAsync()
      → LoadRulesAsync() + LoadAtomsAsync() + PopulateVariables() [now with Kind]
  → Task 2: ValidationRunsQueryService.QueryAsync()
  → Task.WhenAll → ScheduleSolution → ExpireSolution
  → outputs: Rules[], Objects[], Properties[], Runs[]

RULE DECONSTRUCT (Rule input from List Item on Rules)
  → filters rule.Variables by Kind → Objects[], Properties[]
  → filters Runs by rule.Id → Runs[]
  → passthrough Rule, SWRL, RuleName, RuleDescription

OBJECT STATE (one per BIM object class)
  → user wires geometry + element ID panel
  → outputs DG.ObjectState (elementId string + geometry object)

DESIGN STATE (reworked)
  → inputs: ObjectState list, DefState (from legacy Design State sub-component)
  → if DefStateId changed: re-scan ObjectStates → rebuild IdRefs
  → outputs: IdRefs[], GeoRefs[], DefState

CLASSIFICATOR (reworked)
  → inputs: Rule, Objects, Properties, PropValues (DataTree), IdRefs, GeoRefs, DefState
  → builds BindingRows using Objects→IdRefs mapping + Properties→values
  → outputs: BoundVariables, Values (DataTree), Variables, DefState

VALIDATOR (unchanged inputs structure)
  → inputs: Rules, Variables (bindings), Run, SendRules, DataServiceUrl, State
  → EvaluateRules() → publish to data-service
  → ValidationPublishClient now includes IdRefs in statePayloadJson

RUN DECONSTRUCT
  → input: ValidRun (from METAGRAPH.Runs or RULE DECONSTRUCT.Runs)
  → outputs: passing items (element ID list), failing items, RunId, DateCreated, State
```

### Object→ElementId Binding Persistence

```
DESIGN STATE.IdRefs (in-memory list per SolveInstance)
    ↓ wired to CLASSIFICATOR.IdRefs
CLASSIFICATOR builds BindingRow.ElementRefsByVar with IdRefs[i] → Objects[i] mapping
    ↓
VALIDATOR.ValidationPublishClient serializes state including IdRefs list
    ↓
data-service /validation/publish receives statePayloadJson (extended to include idRefs)
    ↓
Neo4j: ValidationRun.statePayloadJson stores full composed state
    ↓
RUN DECONSTRUCT reads ValidationRunQueryResult.StatePayloadJson → deserializes → emits passing/failing items
```

---

## Integration Points — Explicit New vs Modified

### Hard Integration Boundaries

| Boundary | Type | Files Involved |
|----------|------|----------------|
| `Variable.Kind` inference | MODIFIED — pure C# | `DG.Core/Models/Variable.cs`, `DG.Core/Data/Neo4jRuleRepository.cs` |
| METAGRAPH Runs loading | MODIFIED component | `DG.Grasshopper/Components/MetagraphComponent.cs`, `DG.Core/Services/ValidationRunsQueryService.cs` (reused as-is) |
| RULE DECONSTRUCT signature | MODIFIED component | `DG.Grasshopper/Components/RuleDeconstructComponent.cs` (output layout rebuild via EnsureOutputLayout pattern) |
| OBJECT STATE component | NEW file | `DG.Grasshopper/Components/ObjectStateComponent.cs` |
| VARIABLE NAME component | NEW file | `DG.Grasshopper/Components/VariableNameComponent.cs` |
| DESIGN STATE rework | MODIFIED component | `DG.Grasshopper/Components/DesignStateComponent.cs` |
| CLASSIFICATOR rework | MODIFIED component | `DG.Grasshopper/Components/ClassificatorComponent.cs` |
| ValidationRunsComponent → RunDeconstructComponent | MODIFIED (rename + rework) | `DG.Grasshopper/Components/ValidationRunsComponent.cs` → new file name |
| statePayloadJson schema | MODIFIED | `DG.Core/Models/DesignStateSnapshot.cs`, `data-service/app.py` (`_project_state_summary`), `DG.Core/Services/ValidationRunPersistenceService.cs` |
| Cypher/schema propagation | MODIFIED documents | `cypher_template.txt`, `training/dataset_schema.json`, `n8n/workflows/*.json`, `graph-viewer/config.template.js` |

### Unchanged Integration Points

| Component | Status | Reason |
|-----------|--------|--------|
| CONNECTOR component | UNCHANGED | Connection model unchanged |
| VALIDATOR component | UNCHANGED (inputs) | Receives same Rules + BoundVariables; State input shape is same wrapper |
| ValidationPublishClient | MINOR EXTENSION | statePayloadJson gains idRefs field; no structural change to publish endpoint |
| data-service `/validation/publish` | MINOR EXTENSION | Reads idRefs from extended statePayloadJson; `store_validation_run()` unchanged |
| data-service `/validation/runs/{project}` | UNCHANGED | List runs endpoint unchanged |
| REINSTATE component | UNCHANGED | Operates on DefState parameters only; not affected by ObjectState addition |
| Speckle stack (7 containers) | UNCHANGED | No new publish format at Speckle level |
| n8n ingest workflow logic | UNCHANGED (Cypher template only gets doc update) | Atom-level structure unchanged; LLM prompt updated for awareness only |
| Ollama service | UNCHANGED | No new inference patterns |
| Model Viewer (Vite+React) | UNCHANGED | Consumes run list from data-service; format additions are backward-compatible |

---

## Suggested Phase Decomposition (3–7 phases)

This decomposition follows the dependency graph from section (e). Each phase has a clean boundary.

### Phase 1: Schema Foundation — C# Models + Type Inference

**Boundary:** All downstream GH component changes depend on `Variable.Kind` being available. Nothing else can be built until this is done.

**New artifacts:**
- `VariableKind` enum in `Variable.cs`
- `Kind` property on `DG.Core.Models.Variable`
- `PopulateVariables()` extended with kind inference logic in `Neo4jRuleRepository.cs`
- `DG.Variable` public wrapper updated with `Kind`

**Modified artifacts:** `Variable.cs`, `Neo4jRuleRepository.cs`, public API surface in `DG.Grasshopper/`

**Test coverage:** Unit tests on `PopulateVariables()` with mock atom structures covering ClassAtom → Object, DataPropertyAtom → Property, mixed-atom variable (both assignments same variable → Object wins).

**Can run in parallel with:** Nothing — this is the root dependency.

---

### Phase 2: METAGRAPH Loader Expansion + RULE DECONSTRUCT Rework

**Boundary:** METAGRAPH must expose Runs before RULE DECONSTRUCT can emit them. Both are independent of OBJECT STATE or DESIGN STATE rework.

**New artifacts:**
- METAGRAPH: Objects, Properties, DesignStates, Runs outputs
- METAGRAPH: concurrent `ValidationRunsQueryService.QueryAsync` call (reuses existing service)
- RULE DECONSTRUCT: Objects, Properties, Runs outputs (derived from Rule.Variables + filtered Runs input)
- RULE DECONSTRUCT: remove Variables + VariableName outputs; update `EnsureOutputLayout`
- VARIABLE NAME component (new, trivial — Variable input → Name string output)

**Modified artifacts:** `MetagraphComponent.cs`, `RuleDeconstructComponent.cs`

**New artifacts:** `VariableNameComponent.cs`

**Can run in parallel with:** Phase 3 (ObjectState + DesignState rework) — they share no intermediate state.

---

### Phase 3: OBJECT STATE Component + DESIGN STATE Rework

**Boundary:** Depends on Phase 1 (Variable.Kind). Independent of Phase 2. Produces the IdRefs/GeoRefs contract that CLASSIFICATOR needs.

**New artifacts:**
- `ObjectStateComponent.cs` — new GH component (ObjectRef + GeoRef inputs → DG.ObjectState output)
- `DG.ObjectState` public type

**Modified artifacts:**
- `DesignStateComponent.cs` — reworked: inputs change to ObjectState list + DefState; outputs become IdRefs, GeoRefs, DefState; cache logic added

**Test coverage:** Unit tests on IdRef cache invalidation (DefState hash change triggers rebuild; same hash returns cache).

**Can run in parallel with:** Phase 2.

---

### Phase 4: CLASSIFICATOR Rework

**Boundary:** Depends on Phase 1 (Variable.Kind) and Phase 3 (IdRefs/GeoRefs contract). Must precede VALIDATOR integration test.

**Modified artifacts:**
- `ClassificatorComponent.cs` — input rename (ElementRefs→GeoRefs) and addition (Rule, Objects, Properties, PropValues, IdRefs, GeoRefs, DefState); output addition (Values DataTree, Variables, DefState); pass DefState through

**Test coverage:** Unit tests on binding construction with Objects→IdRefs mapping; DataTree output shape matches variable order.

---

### Phase 5: RUN DECONSTRUCT + statePayloadJson Extension

**Boundary:** Depends on Phase 2 (Runs data flowing from METAGRAPH). Depends on Phase 3/4 (extended DesignState shape) for complete IdRefs in statePayloadJson. Can be partially built after Phase 2 (passing/failing items from existing entity set data).

**Modified artifacts:**
- `ValidationRunsComponent.cs` → `RunDeconstructComponent.cs`: rename, new GUID, output signature change (passing items, failing items, RunId, DateCreated, State)
- `DesignStateSnapshot.cs`: add `IdRefs` list to model
- `data-service/app.py`: extend `statePayloadJson` deserialization; update `_project_state_summary()` if summary adds idRefs count
- `ValidationRunPersistenceService.cs` or `ValidationPublishClient.cs`: serialize IdRefs into statePayloadJson

---

### Phase 6: Schema Propagation Sweep

**Boundary:** Can only finalize after Phase 1 is complete (VariableKind semantics are locked). All document updates — no code logic changes.

**Modified artifacts:**
- `cypher_template.txt` — add DesignState/DefState/ObjectState node shapes; add VariableKind note
- `training/dataset_schema.json` — add DesignState hierarchy to nodes section
- `n8n/workflows/rules-to-metagraph.json` — update LLM system prompt to clarify ClassAtom → Object variable distinction
- `graph-viewer/config.template.js` — add NeoVis label config for DesignState (kind-based display)

**Can run in parallel with:** Phases 3, 4, 5 (document work only, no shared code state).

---

## Anti-Patterns to Avoid in v3.0

### Anti-Pattern 1: Storing Variable Kind on Var Nodes in Neo4j

**What:** Writing a `kind: "Object"` property to every `Var` node in Neo4j during ingest or as a backfill migration.

**Why it's wrong:** The kind is derivable from the atom structure already stored in Neo4j. Storing it redundantly requires n8n prompt updates (error-prone with LLM), a backfill migration on existing Var nodes, and version-skew risk if atom structure and Var.kind ever disagree.

**Do this instead:** Infer at read time in `PopulateVariables()`. Zero Neo4j schema change, zero n8n change.

---

### Anti-Pattern 2: Multi-Label Neo4j Nodes for DesignState Hierarchy

**What:** Using `:DesignState:DefState` or `:DesignState:ObjectState` dual-label nodes.

**Why it's wrong:** NeoVis renders by first label in a non-deterministic order across Neo4j 5 minor versions. Cypher `MATCH (d:DesignState)` is ambiguous about which subtype is returned. LLM must be taught a two-label MERGE pattern. No existing pattern in this codebase uses multi-label nodes.

**Do this instead:** Single label `DesignState` with `kind: 'DefState' | 'ObjectState'` property, mirroring the established `Rule.kind` pattern.

---

### Anti-Pattern 3: RULE DECONSTRUCT Querying Neo4j Directly

**What:** Adding a Neo4j connection to RULE DECONSTRUCT so it can fetch Runs itself.

**Why it's wrong:** RULE DECONSTRUCT is a stateless unpacking component by design. Adding network I/O turns it into an async loader, requiring the same `ScheduleSolution` polling pattern as METAGRAPH. Two components now hold DB connections, doubling connection pool usage and making connection management harder to reason about.

**Do this instead:** METAGRAPH loads Runs; RULE DECONSTRUCT filters the pre-loaded list by rule ID (pure C# list LINQ).

---

### Anti-Pattern 4: Recomputing IdRefs on Every Solve

**What:** DESIGN STATE re-scans all ObjectState geometry inputs on every `SolveInstance` call.

**Why it's wrong:** Geometry scanning in Rhino is expensive. In a live canvas, `SolveInstance` fires on any upstream change, including slider drag (which changes DefState constantly). Re-scanning geometry on every solve makes the canvas unresponsive.

**Do this instead:** Cache `(DefStateId → IdRefs)`. Only invalidate when DefState.StateId changes. Object identity in Grasshopper is stable per solve unless geometry is explicitly changed.

---

### Anti-Pattern 5: New GH Component GUID Reuse

**What:** Reusing the existing `ValidationRunsComponent.ComponentGuid` for `RunDeconstructComponent`.

**Why it's wrong:** Existing `.gh` canvas files that contain the old VALIDATION RUNS component store the GUID in the file. If the new component reuses the GUID, Grasshopper will load it as the old component type, causing silent output mismatch (user sees wrong output port names with wires attached to wrong indices).

**Do this instead:** Generate a new GUID for `RunDeconstructComponent`. Old canvases will fail to find the old GUID (expected) and show an unresolved component placeholder — this is the correct signal to the user that rewiring is needed.

---

## Scaling Considerations

| Concern | Current (v2.0) | v3.0 Change | Risk |
|---------|----------------|-------------|------|
| METAGRAPH query count | 1 async task (rules) | 2 concurrent async tasks (rules + runs) | LOW — both queries are bounded by project; `Task.WhenAll` with existing timeout pattern |
| Canvas solve performance | DESIGN STATE always reserializes State | DESIGN STATE caches IdRefs by DefState hash | IMPROVEMENT — reduces geometry re-scan |
| statePayloadJson size | Scalar parameters only (~100-500 bytes) | Adds IdRefs list (strings per object variable) | LOW — IdRefs are short strings; payload remains well under Neo4j property limits |
| RuleDeconstructComponent output count | 6 outputs | 4 outputs (Variables+VariableName removed, 3 new) | CANVAS BREAK — intentional v3.0 change; old wires must be reconnected |
| ClassificatorComponent input count | 4 inputs | 8+ inputs | LOW — GH supports many inputs; DataTree branching unchanged |

---

## Sources

- Direct codebase inspection: `DG/src/DG.Core/Models/Variable.cs`, `DG/src/DG.Core/Models/DesignStateSnapshot.cs`, `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`, `DG/src/DG.Core/Services/ValidationRunsQueryService.cs`, all 7 GH component files, `data-service/app.py`, `cypher_template.txt`, `training/dataset_schema.json`
- `.planning/PROJECT.md` — v3.0 milestone requirements (active)
- `DG_OBSIDIAN/atlas/Graph schema v3 is the canonical data model.md` — schema propagation checklist
- `DG_OBSIDIAN/atlas/DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline.md` — component pipeline structure
- Existing pattern precedents: `Rule.kind` property on Rule nodes (single-label-plus-property > multi-label), `EnsureOutputLayout` pattern in `RuleDeconstructComponent` (safe output restructuring), `ScheduleSolution` polling in `MetagraphComponent`, `ValidationRunsQueryService` reuse

---
*Architecture research for: Design Grammar System v3.0 Typed Variables and Composable Design State*
*Researched: 2026-05-11*
