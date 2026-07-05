# Release Notes: DG Plugin v7.0

**Date:** 2026-07-06
**Version:** DG Plugin v7.0

v7.0 of the Design Grammar Grasshopper plugin moves from a 5-component architecture to a **14-component set** aligned with the `GH_DesignGrammars.pdf` schema. The ontology is renamed V6->V7 to match the schema notation, ports carry explicit ontology IRIs, and the validation pipeline is rebuilt around a 3-part **DesignState composition** (ObjState + ParamState + PropState). The `CLASSIFICATOR` and `VALIDATION RUNS` components are removed; `REINSTATE` and `DESIGN STATE` are reworked; `CONNECTOR` ports are renamed; and 9 new components are introduced.

**This is a breaking-change release.** Old `.gh` files will show missing-component placeholders for CLASSIFICATOR, VALIDATION RUNS, and old REINSTATE. Follow the Upgrade Guide below to re-wire your canvases.

---

## Breaking Changes

### CLASSIFICATOR (removed)

**What broke:** The CLASSIFICATOR component no longer exists. It previously accepted Rule + Variables/Objects/Properties inputs and produced a DefState output. In v7.0, its role is split across three capture components (OBJECT STATE, PROPERTY STATE) and the composition DESIGN STATE component.

**Before (v2.0):**
```
METAGRAPH -> RULE DECONSTRUCT -> CLASSIFICATOR -> VALIDATOR
```

**After (v7.0):**
```
METAGRAPH -> RULE DECONSTRUCT -> OBJECT STATE -> DESIGN STATE -> VALIDATOR
                           \-> PROPERTY STATE -/
```

**Port mapping:**

| Old CLASSIFICATOR port | New wiring |
|------------------------|------------|
| Rule input | Wire from RULE DECONSTRUCT.Rule (same source) |
| Variables/Objects/Properties inputs | Wire each source component: Object+Geometry+Label -> OBJECT STATE; Rule+DataProperty+PropValue -> PROPERTY STATE |
| DefState output | Replace with DESIGN STATE.DesignState output |

**GUID change:** Removed — no replacement GUID (component eliminated).

---

### VALIDATION RUNS (replaced by VALIDATION GRAPH)

**What broke:** The VALIDATION RUNS component is removed. Its old GUID (A7F2C3E1) is replaced by the new VALIDATION GRAPH GUID (95fc9d32-307e-41fd-a158-bfae49a3dc2a). The new component reads from a ValidGraph handle (not a CONNECTOR handle directly) and outputs Run/Status/DesignState as separate lists instead of a single ValidationRuns list.

**Before (v2.0):**
```
CONNECTOR -> VALIDATION RUNS -> [ValidationRuns list]
```

**After (v7.0):**
```
CONNECTOR -> GRAPH DECONSTRUCT -> VALIDATION GRAPH -> Run + Status + DesignState
```

**Port mapping:**

| Old VALIDATION RUNS port | New VALIDATION GRAPH port |
|--------------------------|---------------------------|
| Connection (in) | Wire CONNECTOR.Database -> GRAPH DECONSTRUCT.Database; wire GRAPH DECONSTRUCT.ValidGraph -> VALIDATION GRAPH.ValidGraph |
| [ValidationRuns list] (out) | Replace with separate Run, Status, DesignState outputs |

**GUID:** `A7F2C3E1` (old, removed) -> `95fc9d32-307e-41fd-a158-bfae49a3dc2a` (new)

---

### REINSTATE (replaced by PARAMETER REINSTATE)

**What broke:** The old REINSTATE component auto-fired on every Grasshopper solve, accepting a ParamState and immediately writing parameters to canvas sliders/toggles. The new PARAMETER REINSTATE requires an explicit **Target** input (wired from the PARAMETER STATE component's state output) and a rising-edge trigger on the **Reinstate** input (false->true transition). The **StateStatus** output is added (7-value ReStatus enum, index-matched to Parameters). The **Parameters** output now returns ALL parameters from ParamState (not just applied ones).

**Before (v2.0):**
```
ParamState -> REINSTATE -> Parameters + Status
```

**After (v7.0):**
```
ParamState -> PARAMETER REINSTATE -> Parameters + StateStatus + Status
  Target (Input 1) -/
```

**Port mapping:**

| Old REINSTATE port | New PARAMETER REINSTATE port |
|--------------------|------------------------------|
| ParamState (in) | ParamState (in) — unchanged |
| — (no equivalent) | **Target** (Input 1) — **required**, wire from PARAMETER STATE.State output |
| — (no equivalent) | StateStatus (out) — 7-value ReStatus list, index-matched to Parameters |
| Status (out) | Status (out) — preserved (human-readable summary text) |
| Parameters (out) | Parameters (out) — now returns ALL params (not just applied ones) |

**Behavior change:** Old REINSTATE auto-fired on every solve. New PARAMETER REINSTATE fires only when Reinstate transitions from `false` to `true`. This prevents accidental re-application when the canvas updates.

---

### DESIGN STATE (old) -> PARAMETER STATE + OBJECT STATE + PROPERTY STATE + DESIGN STATE (new)

**What broke:** The old monolithic DESIGN STATE component (DefState) is split into three dedicated capture components and one composition component. Captured state is split by kind: object state (geometry + label), parameter state (slider/toggle values), and property state (rule-to-value binding). The composition DESIGN STATE component accepts all three kinds and produces a single DesignState.

**Before (v2.0):**
```
Object -> DESIGN STATE -> DesignState (DefState)
Params -/
```

**After (v7.0):**
```
Object + Geometry + Label -> OBJECT STATE -> ObjState -> DESIGN STATE -> DesignState
Parameters -> PARAMETER STATE -> ParamState -/
Rule + DataProperty + PropValue -> PROPERTY STATE -> PropState -/
```

**Port mapping:**

| Old DESIGN STATE port | New wiring |
|-----------------------|------------|
| Object (in) | Wire to OBJECT STATE.Object |
| Parameters (in) | Wire to PARAMETER STATE.Parameters |
| — (no equivalent) | Add OBJECT STATE.Geometry, OBJECT STATE.Label inputs |
| — (no equivalent) | Add PROPERTY STATE.Rule + DataProperty + PropValue inputs |
| DesignState/DefState (out) | Wire from DESIGN STATE.DesignState (composition component) |

**State kind renames:**

| Old kind value | New kind value | Component |
|----------------|----------------|-----------|
| `DefState` | `ParamState` | PARAMETER STATE |
| `ObjectState` | `ObjState` | OBJECT STATE |
| — (new) | `PropState` | PROPERTY STATE (new) |

---

### CONNECTOR (port renames)

**What broke:** Input and output ports are renamed to match ontology conventions. ServerURI -> Neo4jURI, User -> Neo4jUser, Password -> Neo4jPassword. A new **DbName** input is added (preserved from the old component). The output is renamed from `Connection` to `Database`.

**Before (v2.0):**
```
CONNECTOR (ServerURI, User, Password) -> Connection (Handle)
```

**After (v7.0):**
```
CONNECTOR (Neo4jURI, Neo4jUser, Neo4jPassword, DbName, Project) -> Database (Handle)
```

**Port mapping:**

| Old port | New port | Notes |
|----------|----------|-------|
| ServerURI (in) | Neo4jURI (in) | Renamed |
| User (in) | Neo4jUser (in) | Renamed |
| Password (in) | Neo4jPassword (in) | Renamed |
| — (no equivalent) | DbName (in) | New input, preserved |
| — (no equivalent) | PROJECT NAME (in) | Project scope for downstream queries |
| Connection (out) | Database (out) | Renamed |

---

### RULE DECONSTRUCT (extended)

**What broke:** Old Variables and VariableName outputs are removed. Two new outputs are added: **Objects** (IRIs of Classes/ObjProperties that atoms REFERS_TO) and **DataProperties** (DatatypeProperty IRIs). The partition is driven by `VariableTypeInferrer` (priority chain: Object reference wins over Property reference).

**Before (v2.0):**
```
RULE DECONSTRUCT -> Variables + VariableName + Rule + SWRL + RuleName + RuleDescription
```

**After (v7.0):**
```
RULE DECONSTRUCT -> Objects + DataProperties + Rule + SWRL + RuleName + RuleDescription
```

**Port mapping:**

| Old port | New port | Notes |
|----------|----------|-------|
| Variables (out) | **Objects** (out) | Replaced — IRIs of Class/ObjProperty references |
| VariableName (out) | **DataProperties** (out) | Replaced — DatatypeProperty IRIs |
| Rule (out) | Rule (out) | Unchanged |
| SWRL (out) | SWRL (out) | Unchanged |
| RuleName (out) | RuleName (out) | Unchanged |
| RuleDescription (out) | RuleDescription (out) | Unchanged |

---

### VALIDATOR (reworked)

**What broke:** The old CLASSIFICATOR input is removed. A composed **DesignState** input replaces DefState. Two new Boolean inputs are added: **Run** (triggers validation) and **SendValid** (triggers publish). Two new outputs are added: **RuleName** and **RuleDescription** (passthrough from the bound Rule) and **SendStatus** (single Boolean per Run indicating publish success). Non-overlapping extras (DataServiceUrl input; Report, FailingBindings, ValidationRunId, ModelViewerUrl outputs) are preserved.

**Before (v2.0):**
```
Rule + DefState + DataServiceUrl -> VALIDATOR -> ValidStatus + FailingBindings + Report + ValidationRunId + ModelViewerUrl
```

**After (v7.0):**
```
Rule + DesignState + Run + SendValid + DataServiceUrl -> VALIDATOR -> ValidStatus + RuleName + RuleDescription + SendStatus + FailingBindings + Report + ValidationRunId + ModelViewerUrl
```

**Port mapping:**

| Old port | New port | Notes |
|----------|----------|-------|
| Rule (in) | Rule (in) | Unchanged |
| DefState (in) | **DesignState** (in) | Replaced — accepts composed DesignState from DESIGN STATE component |
| — (no equivalent) | **Run** (in) | New — Boolean trigger to start validation |
| — (no equivalent) | **SendValid** (in) | New — Boolean trigger to publish to Speckle/data-service |
| DataServiceUrl (in) | DataServiceUrl (in) | Preserved non-overlapping extra |
| ValidStatus (out) | ValidStatus (out) | Now a per-ObjState Boolean list (index-matched to ObjState order) |
| — (no equivalent) | **RuleName** (out) | New — passthrough from bound Rule |
| — (no equivalent) | **RuleDescription** (out) | New — passthrough from bound Rule |
| — (no equivalent) | **SendStatus** (out) | New — single Boolean per Run (publish success) |
| Report (out) | Report (out) | Preserved non-overlapping extra |
| FailingBindings (out) | FailingBindings (out) | Preserved non-overlapping extra |
| ValidationRunId (out) | ValidationRunId (out) | Preserved non-overlapping extra |
| ModelViewerUrl (out) | ModelViewerUrl (out) | Preserved non-overlapping extra |

---

## New Features

### 3-Part State Composition

DesignState is no longer a monolithic blob. Three dedicated capture components produce typed state outputs:

- **OBJECT STATE** — Captures `Object` (GH geometry reference) + `Geometry` (rendering hint) + `Label` (user-supplied string) into an `ObjState` (prefix `OS_`).
- **PARAMETER STATE** — Captures a `Parameters` list (sliders, toggles) into a `ParamState` (prefix `DS_`, deterministic `StateId`).
- **PROPERTY STATE** — Captures `Rule` + `DataProperty` + `PropValue` into a `PropState` (prefix `PS_`).

The **DESIGN STATE** (new) component composes multiple ObjState + ParamState + PropState inputs into a single DesignState with an aggregated StateId, ready for VALIDATOR consumption.

### SpecGraph Layer

**KnowledgeGraph is renamed to SpecGraph** at runtime. All `Knowledge*` Neo4j labels become `Spec*` (`KnowledgeNote`->`SpecNote`, `KnowledgeTag`->`SpecTag`, etc.). The GRAPH DECONSTRUCT component exposes a `SpecGraph` handle for project spec storage (notes, tags, sessions). This closes a pre-existing drift between ontology naming (`SpecGraph`) and runtime naming (`KnowledgeGraph`).

### Ontology-Aligned Port Names

Every output port of every component carries an explicit ontology IRI reference matching `DesignGrammar-V7.owl`. Port names are aligned with the `GH_DesignGrammars.pdf` schema:

- `METAGRAPH.Objects` -> `dg:Object`
- `ONTOGRAPH.ObjProperties` -> `dg:ObjProperty`
- `ONTOGRAPH.DataProperties` -> `dg:DataProperty`
- `VALIDATOR.ValidStatus` -> `dgv:ValidStatus`
- `VALIDATOR.SendStatus` -> `dgv:SendStatus`
- `PARAMETER REINSTATE.StateStatus` -> `dgv:ReStatusValue`

See `ontology/port-iri-map-V7.md` for the complete per-port IRI map (appendix below).

### Full 14-Component Architecture

The v7.0 plugin covers all four graph layers:

| Component | Layer | Role |
|-----------|-------|------|
| CONNECTOR | Runtime | Neo4j connection + project scope |
| GRAPH DECONSTRUCT | Runtime | Splits Database into 4 layer handles |
| METAGRAPH | Metagraph | Reads Rules + Objects |
| ONTOGRAPH | Ontograph | Reads Class/ObjProperties/DataProperties |
| VALIDATION GRAPH | ValidGraph | Reads Run/Status/DesignState |
| RULE DECONSTRUCT | Metagraph | Partitions Rule into Objects + DataProperties |
| OBJECT STATE | Core | Captures Object+Geometry+Label into ObjState |
| PARAMETER STATE | Core | Captures Parameters into ParamState |
| PROPERTY STATE | Core | Captures Rule+DataProperty+PropValue into PropState |
| DESIGN STATE | Core | Composes all three state types |
| DESIGN STATE DECONSTRUCT | Core | Splits DesignState into ObjState/ParamState/PropState |
| OBJECT DECONSTRUCT | Core | Splits ObjState into Object/Geometry/Label |
| PARAMETER REINSTATE | Core | Applies ParamState to canvas (rising-edge trigger) |
| VALIDATOR | ValidGraph | Evaluates Rule+DesignState, publishes to Speckle |

### New Deconstruct Components

- **DESIGN STATE DECONSTRUCT** — Accepts a DesignState and outputs its constituent ObjState/ParamState/PropState lists. Pure synchronous passthrough, no DB calls.
- **OBJECT DECONSTRUCT** — Accepts an ObjState and outputs its Object/Geometry/Label. Pure synchronous passthrough.

These components enable architects to unpack validation results from VALIDATION GRAPH for detailed inspection or selective reinstatement.

### GRAPH DECONSTRUCT

A single component that accepts the CONNECTOR `Database` handle and outputs four layer-specific handles: **Metagraph**, **Ontograph**, **ValidGraph**, **SpecGraph**. This replaces the pattern of wiring CONNECTOR directly to every data-consuming component.

### ONTOGRAPH

Reads the ontology layer (Class, ObjProperties, DataProperties) from the Ontograph handle. Enables rules to reference ontology terms directly.

---

## Upgrade Guide

### Step 1: Install the new .gha

Replace the existing `DG.gha` with the v7.0 package:

1. Close Rhino 8.
2. Remove the old `DG.gha` from the Grasshopper Components folder.
3. Copy the v7.0 `DG.gha` to the Grasshopper Components folder.
4. Restart Rhino 8 and open Grasshopper.

### Step 2: Run DB migrations

Before opening an existing project, run these database migrations against your Neo4j instance:

```cypher
// Kind rename: DefState -> ParamState
MATCH (ds:DesignState {kind: "DefState"})
SET ds.kind = "ParamState";

// Kind rename: ObjectState -> ObjState
MATCH (ds:DesignState {kind: "ObjectState"})
SET ds.kind = "ObjState";

// ValidGraph layer assignment (correct from Metagraph)
MATCH (ds:DesignState)
WHERE ds.graph = "Metagraph" OR ds.graph IS NULL
SET ds.graph = "ValidGraph";
```

If you have existing `Knowledge*` labels (from pre-v7.0) and have not run the SpecGraph rename:
```cypher
// SpecGraph runtime rename (if not already run)
MATCH (n)
WHERE any(lbl IN labels(n) WHERE lbl STARTS WITH 'Knowledge')
SET n.graph = 'SpecGraph'
WITH n, labels(n) AS oldLabels
UNWIND oldLabels AS lbl
WITH n, lbl WHERE lbl STARTS WITH 'Knowledge'
CALL apoc.create.setLabels(n, [replace(lbl, 'Knowledge', 'Spec')]) YIELD node
RETURN count(node) AS migrated;

// Note: requires APOC library. If APOC is not available, migrate manually per label.
```

### Step 3: Open your existing .gh file

When you open an old canvas in Grasshopper, you will see **missing-component placeholders** (red exclamation marks on grey boxes) for:

- **CLASSIFICATOR** — Fully removed; replace with OBJECT STATE + PROPERTY STATE + DESIGN STATE wiring
- **VALIDATION RUNS** — Replaced by VALIDATION GRAPH (new GUID)
- **REINSTATE** (old) — Replaced by PARAMETER REINSTATE (new GUID, new input contract)

Old `CONNECTOR` and `RULE DECONSTRUCT` components will still load (ports updated), but the canvas will show disconnected wires where port names changed.

### Step 4: Re-wire per the breaking changes section

For each placeholder or disconnected component, follow the ASCII wiring diagrams and port mappings in the **Breaking Changes** section above. The general approach:

1. **CONNECTOR** — Reconnect: ServerURI/Limit/Password/User are now Neo4jURI/DbName/Neo4jPassword/Neo4jUser. Add a PROJECT NAME input.
2. **GRAPH DECONSTRUCT** — Wire from CONNECTOR.Database. This component replaces direct CONNECTOR wiring to METAGRAPH/VALIDATION GRAPH.
3. **CLASSIFICATOR** -> Replace with OBJECT STATE + PROPERTY STATE + DESIGN STATE. Wire Object+Geometry+Label to OBJECT STATE; wire Rule+DataProperty+PropValue to PROPERTY STATE; wire DIAGRAM from RULE DECONSTRUCT.Objects to OBJECT STATE.Object.
4. **VALIDATION RUNS** -> Replace with VALIDATION GRAPH. Wire from GRAPH DECONSTRUCT.ValidGraph.
5. **REINSTATE** -> Replace with PARAMETER REINSTATE. Add Target input wire from PARAMETER STATE. Add Reinstate Boolean trigger.
6. **RULE DECONSTRUCT** -> Variables/VariableName ports are now Objects/DataProperties. Rename downstream references.
7. **VALIDATOR** -> Add Run and SendValid Boolean inputs. Wire DesignState from DESIGN STATE component (not DefState from old CLASSIFICATOR).

### Step 5: Verify the full chain

Follow the [E2E verification checklist](test/e2e-v7.0-checklist.md) to validate that your re-wired canvas produces correct outputs:

1. Rule ingest creates valid Cypher in Neo4j
2. METAGRAPH returns rules
3. RULE DECONSTRUCT partitions correctly (Objects + DataProperties)
4. OBJECT STATE produces ObjState with correct StateId prefix (OS_)
5. PARAMETER STATE produces ParamState with correct StateId prefix (DS_)
6. PROPERTY STATE produces PropState with correct StateId prefix (PS_)
7. DESIGN STATE composes all three types correctly
8. VALIDATOR evaluates rules, produces ValidStatus per ObjState
9. VALIDATION GRAPH reads back Run/Status/DesignState
10. PARAMETER REINSTATE applies parameters with correct StateStatus

---

## Appendix: GUID Reference

| Component | Old GUID | New GUID | Status |
|-----------|----------|----------|--------|
| CONNECTOR | — | — | Updated (port renames only, same GUID) |
| GRAPH DECONSTRUCT | — (new) | — | New component |
| METAGRAPH | — (existing) | — | Updated (Objects output added) |
| ONTOGRAPH | — (new) | — | New component |
| VALIDATION GRAPH | — (new) | `95fc9d32-307e-41fd-a158-bfae49a3dc2a` | New component (replaces VALIDATION RUNS A7F2C3E1) |
| RULE DECONSTRUCT | — | — | Updated (outputs changed) |
| OBJECT STATE | — (new) | — | New component |
| PARAMETER STATE | — (new) | — | New component (replaces old DESIGN STATE capture) |
| PROPERTY STATE | — (new) | — | New component |
| DESIGN STATE (new) | — (new) | — | New composition component |
| DESIGN STATE DECONSTRUCT | — (new) | — | New component |
| OBJECT DECONSTRUCT | — (new) | — | New component |
| PARAMETER REINSTATE | `D4E2F8A1-C736-4B9D-AE51-2B1F7C9D0E63` (old REINSTATE) | — | Reworked (new input contract, rising-edge trigger) |
| VALIDATOR | — | — | Updated (inputs/outputs changed) |

**Old GUIDs that are fully removed:**

| Old GUID | Component | Status |
|----------|-----------|--------|
| `A7F2C3E1` | VALIDATION RUNS | Removed — no migration shim |
| — | CLASSIFICATOR | Removed — no replacement GUID |

---

## Appendix: Port IRI Reference

The canonical per-port IRI mapping for all 14 components is maintained at:
[`ontology/port-iri-map-V7.md`](ontology/port-iri-map-V7.md)

Every output port of every component and every IRI-carrying input port resolves to either a verified ontology IRI (grep-resolvable in `DesignGrammar-V7.owl`) or an explicitly annotated runtime/DB construct (credentials, driver handles, Boolean triggers, publish extras). The map contains **25 distinct ontology IRIs** across 5 prefix namespaces:

| Namespace | Prefix | Examples |
|-----------|--------|---------|
| Core | `dg:` | `dg:DesignState`, `dg:ObjState`, `dg:ParamState`, `dg:PropState`, `dg:Object`, `dg:Class`, `dg:Geometry` |
| Metagraph | `dgm:` | `dgm:Rule`, `dgm:SWRL`, `dgm:RuleName`, `dgm:RuleDescription`, `dgm:Metagraph` |
| Validgraph | `dgv:` | `dgv:Run`, `dgv:ValidStatus`, `dgv:SendStatus`, `dgv:ReStatusValue`, `dgv:objectRefName`, `dgv:Validgraph` |
| Specgraph | `dgs:` | `dgs:SpecGraph` |
| Computgraph | `dgc:` | `dgc:Parameter` |

**10 runtime/DB ports** are annotated without IRIs (by design — credentials, driver handles, and Boolean triggers are not ontology concepts): CONNECTOR Neo4jURI/Neo4jUser/Neo4jPassword/Database; GRAPH DECONSTRUCT Database; PARAMETER REINSTATE Reinstate; VALIDATOR SendValid/DataServiceUrl/Report/ValidationRunId.

---

*For developer reference: this document was produced as part of Phase 20 Plan 02 of the v7.0 milestone. The E2E verification checklist is at `test/e2e-v7.0-checklist.md`.*
