# Feature Landscape: v3.0 Typed Variables and Composable Design State

**Domain:** Parametric architectural compliance checking — SWRL/OWL rule system with Grasshopper plugin
**Researched:** 2026-05-11
**Milestone context:** Adding typed variable inference, composable DesignState (DefState + ObjectState), and reworked Grasshopper component graph to the existing DG v2.0 system.

---

## Research Grounding

All behavioral claims below are derived from three authoritative sources plus the existing codebase:

- **SWRL W3C Submission** — formal semantics for variable typing and scoping (HIGH confidence)
- **SWRL Language FAQ (protegeproject/swrlapi)** — confirms rule-local variable scope (HIGH confidence)
- **Speckle Core Concepts docs** — applicationId pattern for stable cross-session identity (HIGH confidence)
- **Grasshopper McNeel forum + Rhino dev docs** — GUID persistence / loss behavior on regeneration (MEDIUM confidence)
- **Existing v2.0 codebase** — current `Variable`, `Atom`, `DesignStateSnapshot`, `ElementRef`, component signatures (HIGH confidence — direct code read)

---

## A. Variable Typing (Object vs Property)

### Background: What SWRL Actually Says

The SWRL formal semantics define two disjoint variable categories:
- **i-variable (Individual / Object variable):** maps to `EC(owl:Thing)` — an OWL individual
- **d-variable (Data / Property variable):** maps to `LV` (literal values) — a typed scalar

These are distinguished entirely by *usage context in atoms*, not by declaration:
- Arg-1 of a `ClassAtom` → always an i-variable (Object)
- Arg-1 of a `DataPropertyAtom` → i-variable (Object); Arg-2 → d-variable (Property)
- Both args of an `ObjectPropertyAtom` → i-variables (both Object)

Variable scope is **rule-local**: `?x` in Rule A has no relationship to `?x` in Rule B at the SWRL semantics level. Cross-rule identity is a *DG-level concept layered on top*, not a SWRL primitive.

The existing `Variable` model has `Name` (string) and `InferredDatatype` (string?) but no type enum. The existing `Atom` model has `type` (string: `ClassAtom | DataPropertyAtom | ObjectPropertyAtom | BuiltinAtom`). The inference rule is straightforward and deterministic from atom type + arg position.

### Table Stakes

| Feature | Why Expected | Complexity | Depends On / Replaces |
|---------|--------------|------------|----------------------|
| **VT-01** Variable type inference from atom structure — ClassAtom arg-1 → Object; DataPropertyAtom arg-2 → Property; DataPropertyAtom arg-1 → Object; ObjectPropertyAtom both args → Object | Users expect `RULE DECONSTRUCT` and `CLASSIFICATOR` to tell them which variables represent building elements vs which represent measured values. Without this, wiring is manual guesswork. | S | Depends: existing `Atom.Type` string in Rule model. Replaces: no existing type inference — current `Variable.InferredDatatype` tracks XSD range only, not Object/Property role. |
| **VT-02** `RULE DECONSTRUCT` exposes separate `Objects` output (list of Object-typed variables) and `Properties` output (list of Property-typed variables) | Architect needs to know which wires to run to geometry sources vs number sliders. Flat `Variables` list makes this invisible. | S | Depends: VT-01. Replaces: existing `Variables` and `VariableName` outputs on RULE DECONSTRUCT (these become redundant and are removed). |
| **VT-03** `CLASSIFICATOR` accepts typed `Objects` and `Properties` inputs (replacing the current flat `Variables` list) and maintains the split in its binding logic | Once types are exposed, the binding step must respect them. A flat `Variables` input loses the distinction the architect just made. | M | Depends: VT-01, VT-02. Replaces: current `Variables` input on CLASSIFICATOR (index 0). |
| **VT-04** `METAGRAPH` exposes `Objects` and `Properties` outputs in addition to `Rules` | The pattern of "load from METAGRAPH, deconstruct, wire" needs the split available at the source so that RULE DECONSTRUCT receives typed data, not raw strings. | S | Depends: VT-01. Replaces: nothing added — METAGRAPH currently only outputs `Rules`, `RuleName`, `Count`. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **VT-D1** Error bubble on CLASSIFICATOR when an Object variable receives a scalar value (or vice versa) — type-mismatch detection at solve time | Prevents silent wrong binding that produces spurious pass/fail results. Other tools let bad wiring through silently. | M | Requires type info flowing through from VT-01. |
| **VT-D2** RULE DECONSTRUCT component message displays `N objects, M properties` — visible at a glance without expanding outputs | Architect gets immediate feedback on rule shape without reading variable lists. | S | |

### Anti-Features

| Anti-Feature | Why Tempting | Why Bad for v3.0 |
|--------------|-------------|-----------------|
| Explicit variable type declaration in the UI (user annotates "this variable is Object") | Feels like control and is familiar from typed languages | SWRL atom structure *already determines* the type — asking the user to declare it is redundant input that can contradict the graph, causing silent inconsistency. Inference from atoms is the correct model. |
| Surfacing `BuiltinAtom` variables (e.g. `?val` in `swrlb:greaterThan`) as a third variable type | Completeness / formal correctness | Builtin arguments are internal to the rule evaluation and have no user-facing object identity or GH wire mapping. Exposing them clutters the `Objects`/`Properties` split with internal infrastructure. Leave them invisible in v3.0. |
| Storing inferred type on the `Var` node in Neo4j | Persisting derived data feels rigorous | The type is 100% computable from the existing `Atom.type` + arg `pos`. Storing it introduces a synchronization invariant (schema must update when atoms change) with no retrieval benefit — the client can always recompute. |

---

## B. Object Variable Cross-Rule Identity

### Background: What Needs to Happen

SWRL defines variable scope as rule-local. DG extends this with a domain convention: *same variable name in multiple rules targeting the same OWL Class* refers to the same real-world element. This is a user-observable identity contract: "If I validate Rule A and Rule B against Building X, both rules bind to the same Building X element — not two different instances."

This requires the Element Id (the `DgEntityId` in `ElementRef`) for Object variables to be stored at the `DesignState` level and reused across rules without the user re-wiring it each time.

The existing `ElementRef` carries `DgEntityId` (string) + `Geometry` (object) + `DisplayName`. The current flow requires the user to wire `ElementRefs` per variable into CLASSIFICATOR. The v3.0 flow moves element identity into `ObjectState` so it persists at the `DesignState` node and is available across all rules automatically.

Speckle's `applicationId` pattern (stable per-source-application identifier, distinct from content-hash `id`) is the right analogy: the `ObjectRef` in `ObjectState` acts as the `applicationId` — stable even when the geometric content (`GeoRef`) changes.

### Table Stakes

| Feature | Why Expected | Complexity | Depends On / Replaces |
|---------|--------------|------------|----------------------|
| **OI-01** `OBJECT STATE` component — accepts `ObjectRef` (stable string ID) and `GeoRef` (geometry reference) as inputs; outputs a typed `ObjectState` object | Users need a dedicated place to declare "this is element X and here is its geometry." Without a component, there is no canonical place to wire object identity, so it gets buried in ad-hoc CLASSIFICATOR wiring. | S | Replaces: ad-hoc ElementRef wiring directly into CLASSIFICATOR. |
| **OI-02** `DESIGN STATE` rework — inputs changed to `ObjectState` (list) + `DefState` (list); outputs become `IdRefs` (list of stable element IDs), `GeoRefs` (geometry list), `DefState` (DefState pass-through) | The parent DesignState must aggregate Object and Def sub-states and expose them to downstream components cleanly. | M | Depends: OI-01. Replaces: current DESIGN STATE which only has scalar Number/Integer/Boolean inputs with a single `State` output. |
| **OI-03** Element Ids stored on `DesignState` node in Neo4j persist cross-rule — the same ObjectRef ID is not re-generated when `DefState` changes, only when the ObjectState input itself changes | Users expect that if they move a slider (DefState change), validation runs stay linked to the same element. Re-generating element IDs on every solve would break run history and state filtering. | M | Depends: OI-02, composable DesignState ID scheme (unique prefixes per class). |
| **OI-04** `CLASSIFICATOR` rework — `ElementRefs` renamed to `GeoRefs` and wired from `DESIGN STATE.GeoRefs`; gains `IdRefs` input wired from `DESIGN STATE.IdRefs` | With the split now explicit, CLASSIFICATOR must accept the pre-split geometry and ID references separately. The rename makes the role of each input legible. | M | Depends: OI-02. Replaces: current `ElementRefs` (optional tree) on CLASSIFICATOR at index 2. |
| **OI-05** `VARIABLE NAME` component — accepts a single variable (from `Objects` or `Properties` output); outputs its name as a plain string | After the RULE DECONSTRUCT split, users need a simple way to label geometry output or look up a specific variable by name without writing custom scripting. | S | Replaces: current `VariableName` output on RULE DECONSTRUCT (that output is removed from RULE DECONSTRUCT). |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **OI-D1** `DESIGN STATE` component message displays `N objects, M def params` — architect sees the composition at a glance | Compared to v2.0 which shows only `N param(s)`, the v3.0 message communicates the richer structure without opening the panel. | S | |
| **OI-D2** IdRef prefix encoding: `ObjectState` IDs prefixed with `OS_`, `DefState` IDs prefixed with `DS_`, combined `DesignState` with `DGST_` — collision-proof namespacing | Enables Neo4j queries to filter by node class purely from the ID string without a label join. Also makes Cypher MERGE conditions unambiguous. | S | Schema propagation impact: cypher_template.txt must document prefix conventions. |

### Anti-Features

| Anti-Feature | Why Tempting | Why Bad for v3.0 |
|--------------|-------------|-----------------|
| Automatic geometry-hash-based stable ID generation (derive ObjectRef ID from geometry content) | Feels like it removes a manual step for the user | Geometry is regenerated on every Grasshopper solution. Content-hash IDs would change whenever geometry is modified (e.g., building footprint changes during design exploration), breaking cross-run history exactly when the architect is most actively designing. The user must supply a stable semantic ID (e.g. a Rhino object GUID referenced from the model, or a named string) — this mirrors Speckle's `applicationId` vs content-hash `id` distinction. |
| Cross-project object identity (sharing ObjectState across projects) | Architects work on related buildings | PROJECT isolation is a load-bearing architectural decision (every node carries `project` property; validated through v2.0). Cross-project sharing would require multi-tenant Cypher queries and breaks the isolation invariant. Out of scope. |
| ObjectState supporting arbitrary geometry types (meshes, Breps, surfaces) for full serialization | Completeness | v2.0 Out of Scope explicitly deferred arbitrary geometry serialization. `GeoRef` carries a reference (GUID or ID string) + display geometry for Speckle coloring — not a full geometry serialization. The serialization-for-reinstatement problem is unsolved for geometry and should not be attempted in v3.0. |

---

## C. Composable DesignState Hierarchy

### Background: DefState vs ObjectState

v2.0 `DesignStateSnapshot` carries only scalar parameters (Number/Integer/Boolean) in a flat `Collection<DesignStateParameter>`. The `StateId` is a SHA-256 hash of sorted parameter values — identical slider positions produce identical IDs, enabling reliable filtering.

v3.0 introduces a two-tier composition:
- **`DefState`** — the existing scalar parameter capture (renamed from "State" in v2.0), unchanged semantics
- **`ObjectState`** — new: captures `ObjectRef` (stable element ID string) + `GeoRef` (geometry reference for Speckle publishing)
- **`DesignState`** — parent class aggregating one or more `DefState` and one or more `ObjectState` sub-states

The composable structure means CLASSIFICATOR and VALIDATOR receive richer context without requiring re-wiring for each new rule.

### Table Stakes

| Feature | Why Expected | Complexity | Depends On / Replaces |
|---------|--------------|------------|----------------------|
| **CS-01** `DesignState` class hierarchy with unique ID prefixes per class (`DGST_` parent, `OS_` ObjectState, `DS_` DefState) stored in Neo4j as distinct node types with labeled relationships | Users (and Cypher queries) need to distinguish "what changed was a slider" from "what changed was a building element." A single flat node cannot carry this distinction. | M | Replaces: current single `DesignStateSnapshot` model with flat parameters list. Schema propagation required: cypher_template.txt, dataset_schema.json, n8n prompts, NeoVis config. |
| **CS-02** `DESIGN STATE` content-hash ID remains deterministic: same ObjectRefs + same DefState values → same `DesignState` ID | v2.0 validated this for DefState (SHA-256 of sorted param values). v3.0 must extend the hash to include ObjectRef IDs so that combined state produces a stable ID for filtering. | M | Depends: CS-01. Existing `ComputeStateId` logic must be extended to include ObjectRef strings in the sorted input. |
| **CS-03** `CLASSIFICATOR` outputs `DefState` (renamed from `State`) pass-through — downstream components use the name `DefState` consistently | Renaming clarifies that `CLASSIFICATOR.State` was always the DefState portion. Keeping the old name would create a naming inconsistency with the new hierarchy. | S | Replaces: current `State` output (index 3) on CLASSIFICATOR. |
| **CS-04** `METAGRAPH` loads `DesignStates` and exposes a `DesignStates` output (list) | Architects browsing saved runs from METAGRAPH need to see which design states exist — both for reinstatement and for filtering validation runs. Without this output, they must query Neo4j directly. | M | Depends: CS-01. Adds new Neo4j query to `IRuleRepository`. |
| **CS-05** `METAGRAPH` exposes `Runs` output (list of `ValidationRunQueryResult`) — relocating the run-loading responsibility from `VALIDATION RUNS` to `METAGRAPH` | `METAGRAPH` is the natural data-loading hub. Having `VALIDATION RUNS` also load data creates two competing query paths. Centralizing run loading in `METAGRAPH` makes the data flow directional: load in METAGRAPH → deconstruct in RUN DECONSTRUCT. | M | Depends: existing async load pattern in MetagraphComponent. Enables RUN DECONSTRUCT (formerly VALIDATION RUNS) to become a pure deconstruction component with no network calls. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **CS-D1** DefState-only change detection: if ObjectRefs are unchanged and only DefState values changed, ObjectState node is reused (no new Neo4j node created) — only DefState node is updated | Reduces Neo4j write volume during design exploration (many slider changes, same elements). Keeps the object identity graph clean. | M | Requires comparing incoming ObjectRef IDs against stored ones before MERGE. |
| **CS-D2** `DESIGN STATE` component outputs separate `IdRefs`, `GeoRefs`, `DefState` — architects can wire only what they need rather than destructuring a single opaque `State` blob | v2.0 required threading the `State` object through multiple components invisibly. The v3.0 split makes data flow legible on the canvas. | S | |

### Anti-Features

| Anti-Feature | Why Tempting | Why Bad for v3.0 |
|--------------|-------------|-----------------|
| Nested sub-state arbitrarily deep (DefState of a DefState, etc.) | Academic completeness, covers future cases | Two levels (parent DesignState → DefState / ObjectState) is already the maximum complexity the CLASSIFICATOR and VALIDATOR downstream consumers can usefully consume. Deeper nesting requires recursive Cypher queries and adds no user-observable value in v3.0. |
| Version history / diff UI for DesignState evolution | Architects would love to see "what changed between state A and state B" | Full version diffing requires a separate UI surface (the Model Viewer or web UI). Not in v3.0 scope. The foundation (stable IDs per sub-state class) enables it later without retrofitting. |
| Automatic sub-state merge when two DesignStates share the same ObjectRefs | Clever deduplication | Makes the ID scheme non-deterministic from the user's perspective. The rule "same inputs → same ID" is load-bearing for filtering (validated in v2.0 DGST-03). Auto-merging would break that invariant. |

---

## D. Component Rework (Grasshopper Data Flow)

### Background: What Changes and What Stays

The v3.0 component rework restructures the middle of the GH canvas pipeline. CONNECTOR and VALIDATOR are unchanged (no new features needed). The rework touches:
- DESIGN STATE (input/output signature)
- CLASSIFICATOR (input/output signature + rename)
- RULE DECONSTRUCT (outputs: add Objects/Properties/Runs, remove Variables/VariableName)
- VALIDATION RUNS → renamed to RUN DECONSTRUCT (becomes pure deconstruction, inputs/outputs change)
- METAGRAPH (new outputs: Objects, Properties, DesignStates, Runs)
- Two new components: OBJECT STATE, VARIABLE NAME

### Table Stakes

| Feature | Why Expected | Complexity | Depends On / Replaces |
|---------|--------------|------------|----------------------|
| **CR-01** `VALIDATION RUNS` renamed to `RUN DECONSTRUCT` — input `ValidRun` (single run object from METAGRAPH.Runs); outputs: `passing items` (element ID list), `failing items` (element ID list), `Run Id` (string), `Date created` (datetime), `State` (DesignState) | The name change signals the semantic shift: this component no longer queries Neo4j, it deconstructs a run object that METAGRAPH already loaded. Input/output rename makes the new role obvious. | M | Depends: CS-05 (METAGRAPH loads Runs). Replaces: current VALIDATION RUNS component with its 4 inputs (Connection, Rule, State, Refresh) and 4 outputs (Runs, Results, States, Status). The `EnsureOutputLayout` migration guard must be applied (see CR-D1). |
| **CR-02** `RULE DECONSTRUCT` removes `Variables` and `VariableName` outputs; adds `Objects` (typed Object variable list), `Properties` (typed Property variable list), `Runs` (list of runs for this rule, sourced from METAGRAPH) | `Variables` and `VariableName` are superseded by the typed split (VT-02). `Runs` per rule enables architects to filter runs by rule directly from RULE DECONSTRUCT without a separate filter step. | M | Depends: VT-01, CS-05. Replaces: `Variables` (index 1) and `VariableName` (index 2) on existing RULE DECONSTRUCT. `EnsureOutputLayout` migration guard already exists in RuleDeconstructComponent — use that pattern. |
| **CR-03** `CLASSIFICATOR` input rename: `ElementRefs` → `GeoRefs` (index 2); new inputs: `Rule` (index 0), `Objects` (index 1), `Properties` (index 2), `PropValues` (index 3), `IdRefs` (index 4), `GeoRefs` (index 5), `DefState` (index 6); outputs add `Values` (DataTree), `Variables` (full bound variable list) | The reworked CLASSIFICATOR is the main composition point: it takes typed objects + properties + their values + state and produces a complete binding ready for VALIDATOR. | L | Depends: VT-01, VT-02, OI-02, OI-04. Major change to existing ClassificatorComponent. |
| **CR-04** `CLASSIFICATOR` output rename: `State` → `DefState` (index 3 pass-through) | Consistency with the hierarchy rename (CS-03). | S | Replaces: `State` output (index 3). |
| **CR-05** `METAGRAPH` new outputs: `Objects` (all unique Object variables across all rules), `Properties` (all unique Property variables), `DesignStates` (list), `Runs` (all runs) — added alongside existing `Rules`, `RuleName`, `Count` | METAGRAPH becomes the single data-loading hub. Architects expect "load once, distribute everywhere" rather than multiple Neo4j-querying components. | M | Depends: CS-04, CS-05. Existing async load pattern in MetagraphComponent is reusable. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **CR-D1** `EnsureOutputLayout` migration guard applied to all reworked components — saved .gh files open without crashing even if output count changes | Architects have saved canvas files. A component GUID collision or output-count mismatch silently breaks the canvas. The existing migration guard pattern (read outputs, wipe and re-register) is load-bearing. | S | Existing pattern in RuleDeconstructComponent is the template. Must be applied to VALIDATION RUNS → RUN DECONSTRUCT rename too. |
| **CR-D2** CLASSIFICATOR component message shows `N objects bound, M properties bound` vs v2.0 `Classification OK [+state]` | Tells the architect at a glance what was bound without opening the panel. | S | |

### Anti-Features

| Anti-Feature | Why Tempting | Why Bad for v3.0 |
|--------------|-------------|-----------------|
| Making CLASSIFICATOR a `IGH_VariableParameterComponent` (variable inputs that user adds) | Mirrors DESIGN STATE pattern; feels flexible | CLASSIFICATOR has a fixed contract with RULE DECONSTRUCT outputs. Variable parameters would make wire-matching ambiguous and break the typed binding logic. Fixed inputs with clear names is correct. |
| Preserving old VALIDATION RUNS component alongside new RUN DECONSTRUCT | Backward compatibility for existing .gh files | The component has a new semantic role (deconstruct vs query). Keeping both creates two competing ways to do the same thing. The correct approach is the `EnsureOutputLayout` migration guard — same GUID, updated outputs, old wires reconnect or produce clear errors. |
| METAGRAPH loading DesignStates + Runs in the same query as Rules | Performance: one round trip | DesignStates and Runs can be large datasets. A single load query that blocks on all three before returning any data degrades perceived responsiveness. Three async loads with separate scheduling (following the existing `ContinueWith` → `ScheduleSolution` pattern) is correct. |

---

## E. Schema Propagation

### Background

Every schema change in v3.0 must propagate across six locations simultaneously. This is not optional — the v2.0 gap-closure retrospective (REQUIREMENTS.md) explicitly documented that missing one propagation point (the Neo4j write path in DGCL-02) caused a silent data loss that was only caught in human UAT. Schema drift is the highest-risk failure mode in this system.

The propagation surface for v3.0:
1. `cypher_template.txt` — new node labels (`DesignState`, `DefState`, `ObjectState`), ID prefix conventions, MERGE patterns
2. `training/dataset_schema.json` — `ObjectProperty` handling (currently present in schema but unused in atoms), new `Var` type field
3. `n8n` workflow prompts (rules-to-metagraph.json, graph-query-mcp.json) — new node labels in `ALLOWED node labels` and `GRAPH SCHEMA` sections
4. `config.template.js` (NeoVis) — new labels for graph visualization node styling
5. Python/FastAPI (`app.py`, `speckle_validation.py`) — Cypher templates for state persistence
6. C# Core models (`DG.Core.Models`) — new `DesignState`, `DefState`, `ObjectState` classes; updated `Variable` with `VariableRole` enum

### Table Stakes

| Feature | Why Expected | Complexity | Depends On / Replaces |
|---------|--------------|------------|----------------------|
| **SP-01** `Variable` model gains `VariableRole` enum (`Object | Property | Unknown`) — populated by inference from atom structure | Downstream consumers (CLASSIFICATOR, RULE DECONSTRUCT) need a typed field, not string comparison against atom type. An enum makes the contract explicit and avoids magic strings. | S | Extends: existing `Variable` class in DG.Core.Models. |
| **SP-02** New `DesignState` / `DefState` / `ObjectState` C# models in DG.Core.Models with unique ID prefix constants | Components pass these typed objects between each other. Untyped `object` or generic `DesignStateSnapshot` cannot carry the hierarchy. | M | Replaces / extends: existing `DesignStateSnapshot` model. |
| **SP-03** `cypher_template.txt` updated with new node labels, ID prefix conventions (`DGST_`, `OS_`, `DS_`), and MERGE patterns for the three DesignState node classes | The template is the single source of truth for the LLM prompt. If it doesn't document new node labels, the LLM will not produce them. | M | Replaces: cypher_template.txt sections that reference Rule/Atom/Var/Literal structure — these stay, new DesignState sections are added. |
| **SP-04** `dataset_schema.json` updated to reflect `VariableRole` field on `Var` nodes and new DesignState hierarchy node labels | Training data quality gate. Used for LLM prompt constraint. Without this update, the LLM prompt schema is inconsistent with the actual graph. | S | Extends: existing `dataset_schema.json` `Var` node definition. |
| **SP-05** n8n workflow prompts updated — `ALLOWED node labels` and `GRAPH SCHEMA` sections include new labels | n8n prompt is the other place the LLM is constrained. Missing labels here cause the LLM to produce Cypher with unlisted labels, which may MERGE unknown nodes into the graph silently. | S | Requires: n8n workflow JSON edits (rules-to-metagraph.json, graph-query-mcp.json). |
| **SP-06** Python data-service Cypher templates updated for DesignState persistence with new node classes | State is persisted via the data-service, not via n8n. If the Cypher in `app.py` uses the old flat `DesignStateSnapshot` model, the new sub-states are never written. | M | Extends: existing state persistence Cypher in `app.py`. |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **SP-D1** Unit tests for `VariableRole` inference from all four atom types (ClassAtom, DataPropertyAtom, ObjectPropertyAtom, BuiltinAtom) with all arg positions | Regression gate: ensures future atom type additions don't silently break the inference rule. Follows existing xUnit test pattern in DG.Tests. | S | |
| **SP-D2** NeoVis config updated so `ObjectState` and `DefState` nodes render with distinct colors in the Graph Viewer | Architects using the web UI can visually distinguish the three DesignState node classes. Without styling, new nodes render with the default label color and blend into the graph. | S | Requires: config.template.js label-to-color mapping. |

### Anti-Features

| Anti-Feature | Why Tempting | Why Bad for v3.0 |
|--------------|-------------|-----------------|
| Keeping `DesignStateSnapshot` as the canonical model and adding optional fields for ObjectState | Backward compatibility; minimal change | The flat model cannot represent the two-level hierarchy without nullable fields that carry semantic ambiguity (`ObjectRefs: null` vs `ObjectRefs: []` vs not present). A proper class hierarchy is required. The migration cost is bounded: it affects 4 C# files + data-service Cypher. |
| Auto-generating `dataset_schema.json` from C# models via reflection | Keeps schema in sync automatically | The schema also documents LLM constraints (IRI patterns, allowed values) that are not representable in C# type annotations. A generated schema would lose those constraints. The schema must be maintained by hand, with tests to catch drift. |

---

## Feature Dependencies

```
VT-01 (variable type inference)
  → VT-02 (RULE DECONSTRUCT Objects/Properties outputs)
      → VT-03 (CLASSIFICATOR typed inputs)
      → CR-02 (RULE DECONSTRUCT rework)
  → VT-04 (METAGRAPH Objects/Properties outputs)
      → CR-05 (METAGRAPH full rework)

OI-01 (OBJECT STATE component)
  → OI-02 (DESIGN STATE rework)
      → OI-03 (cross-rule Element Id persistence)
      → OI-04 (CLASSIFICATOR GeoRefs/IdRefs inputs)
          → CR-03 (CLASSIFICATOR full rework)

CS-01 (DesignState hierarchy + ID prefixes)
  → CS-02 (deterministic combined hash)
  → CS-04 (METAGRAPH DesignStates output)
  → CS-05 (METAGRAPH Runs output)
      → CR-01 (RUN DECONSTRUCT rework)

SP-01 (VariableRole enum on Variable model)    prerequisite for VT-01 implementation
SP-02 (new C# models)                          prerequisite for OI-01, CS-01
SP-03..SP-06 (schema propagation)              must follow CS-01, OI-02
```

**Suggested phase ordering:**
1. Schema + Core models (SP-01, SP-02, CS-01) — lay the data contracts before any component touches them
2. Variable typing inference + METAGRAPH expansion (VT-01, VT-04, CR-05 partial) — enables downstream components to receive typed data
3. OBJECT STATE + DESIGN STATE rework (OI-01, OI-02, CS-02) — new component + reworked output signature
4. CLASSIFICATOR rework + RULE DECONSTRUCT rework (VT-02, VT-03, CR-02, CR-03, CR-04) — main wiring changes
5. RUN DECONSTRUCT (CR-01) — depends on METAGRAPH Runs output being available
6. Schema propagation across all 6 surfaces (SP-03..SP-06) — must validate end-to-end in Neo4j

---

## MVP Recommendation

For v3.0 to feel correct (not just technically complete), the following must ship together as an atomic unit — partial delivery leaves the canvas in a state where wires do not connect:

**Phase gate 1 (data contracts):** SP-01, SP-02, CS-01
**Phase gate 2 (variable typing visible):** VT-01, VT-02, VT-04, CR-02
**Phase gate 3 (composable state):** OI-01, OI-02, CS-02, OI-03
**Phase gate 4 (reworked CLASSIFICATOR + wiring):** VT-03, OI-04, CR-03, CR-04, CR-05
**Phase gate 5 (run deconstruct + schema propagation):** CR-01, CS-04, CS-05, SP-03..SP-06

Defer to post-v3.0:
- **OI-D1** (geometry-hash stable ID generation) — user-supplied semantic ID is the correct model; geometry hashes break on any design change
- **CS-D1** (DefState-only change detection optimization) — correctness can be achieved without this optimization; add when Neo4j write volume is observed to be a problem
- **SP-D2** (NeoVis color styling for new node classes) — visual polish, not correctness; add in the schema-propagation phase if time permits

---

## Sources

- [SWRL: A Semantic Web Rule Language Combining OWL and RuleML (W3C Submission)](https://www.w3.org/submissions/SWRL/) — HIGH confidence, formal semantics for i-variable / d-variable distinction and rule-local scoping
- [SWRL Language FAQ — protegeproject/swrlapi](https://github.com/protegeproject/swrlapi/wiki/SWRLLanguageFAQ) — HIGH confidence, confirms rule-local scope, ClassAtom / DataPropertyAtom argument semantics
- [SWRL Direct Semantics — DAML.org](https://www.daml.org/rules/proposal/direct.html) — HIGH confidence, formal binding semantics for i-object / d-object distinction
- [Speckle Core Concepts — applicationId and object identity](https://docs.speckle.systems/developers/data-schema/concepts) — HIGH confidence, applicationId vs content-hash id pattern for stable cross-session element tracking
- Rhino/Grasshopper community (discourse.mcneel.com, grasshopper3d.com forums) — GUID loss on internalization and regeneration (MEDIUM confidence — consistent across multiple community posts)
- Existing v2.0 codebase: `DG.Core.Models.*`, `DG.Grasshopper.Components.*` — HIGH confidence (direct code read)
