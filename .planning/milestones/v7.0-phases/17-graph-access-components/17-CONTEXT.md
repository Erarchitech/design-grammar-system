# Phase 17: Graph Access Components - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

5 Grasshopper components that provide **read-only access to all 4 Neo4j graph layers** through the CONNECTOR → GRAPH DECONSTRUCT → layer-reader chain. These are the "eyes" of the canvas — they pull rules, ontology terms, and validation results from Neo4j into Grasshopper for downstream components (Phase 18 VALIDATOR, Phase 19 DECONSTRUCT/REINSTATE) to work with.

**In scope (GHGA-01..05):**
- CONNECTOR update — rename ports to match port-IRI map, output "Database" (was "Connection")
- GRAPH DECONSTRUCT (new) — splits Database handle into 4 typed layer handles
- METAGRAPH rework — adds Objects output (index-matched with Rules)
- ONTOGRAPH (new) — reads Class/ObjProperties/DataProperties from OntoGraph layer
- VALIDATION GRAPH (new, replaces VALIDATION RUNS) — reads Run/Status/DesignState from ValidGraph layer

**Out of scope (belongs in other phases):**
- Rule evaluation, validation publish — Phase 18 (VALIDATOR rework)
- DesignState write/persistence — Phase 18 (VALIDATOR on publish)
- State deconstruction (DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT) — Phase 19
- Parameter reinstatement — Phase 19
- E2E live chain, docs — Phase 20

**Already locked upstream (do NOT re-open):**
- Port names and IRIs for all 5 components — `ontology/port-iri-map-V7.md` (Phase 13)
- `Run.ValidStatus` = Boolean list per-ObjState, `Run.SendStatus` = single Boolean — Phase 13 D-06/D-08
- DesignState stored in `graph='ValidGraph'`, MERGE'd by StateId+project, no-orphan invariant — Phase 13 D-01/D-03/D-05
- DesignState is 3-part composition (ObjState+ParamState+PropState) — Phase 16 D-01/D-02
- Layer literal `'ValidGraph'` already applied in `ValidationRunsQueryService` — Phase 14 D-14
- SpecGraph runtime rename complete (Phase 15) — `SpecGraph` handle matches DB
- CONNECTOR already has async-connect pattern with `Neo4jConnectorService` — keep architecture
- METAGRAPH already has async-load pattern with `Neo4jRuleRepository` — extend, don't replace
- VALIDATION GRAPH has a **new GUID** (replaces VALIDATION RUNS) — canvas breakage is expected, documented at Phase 20
- DB keeps existing labels (ValidationRun, ValidationEntity) — only `graph` property value changed per Phase 14 D-14
</domain>

<decisions>
## Implementation Decisions

### Layer Handle Model (Area 1)
- **D-01:** **Individual handle types per graph layer.** `MetagraphHandle`, `OntographHandle`, `ValidGraphHandle`, `SpecGraphHandle` — each wraps a `ConnectionInfo`. GRAPH DECONSTRUCT is the sole producer; each layer-reader component accepts only its specific handle type. Grasshopper wires are type-safe — a MetagraphHandle wire cannot connect to ONTOGRAPH's Ontograph input. Each handle is an immutable record-like class in `DG.Core.Models` with a public wrapper in `DG/PublicTypes.cs`. Follows the existing `ConnectionInfo` pattern (init-only properties, no behavior).

### METAGRAPH Objects Extraction (Area 2)
- **D-02:** **Query REFERS_TO→Class directly from Neo4j.** New Cypher query in `Neo4jRuleRepository`: `MATCH (r:Rule {graph:'Metagraph', project:$project})-[:HAS_BODY|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class)` — deduplicated by Class IRI. Each Object carries IRI + label. The query can run in parallel with the existing Rules query (two async calls, single driver session). Clean graph-structural approach — no dependency on VariableTypeInferrer naming conventions.

### VALIDATION GRAPH Output Semantics (Area 3)
- **D-03:** **Run↔Status are 1:1 paired (index-matched parallel lists).** Run[i] and Status[i] correspond to the same validation run. Same length, same order. Follows the METAGRAPH Rules/Objects index-matched pattern.
- **D-04:** **DesignState output is deduplicated by StateId.** Only unique DesignStates across all runs. The DesignState list may be shorter than the Run list (many runs can share one DesignState via MERGE by StateId+project per Phase 13 D-03). DesignState is NOT index-matched with Run/Status — it's a separate deduplicated list. Consumers that need run→state mapping join by StateId.
- **D-05:** **Status[i] = `IReadOnlyList<bool>`** — one bool per ObjState in the run's DesignState, index-matched to the ObjState order within that DesignState. Overall pass = `AND(all bools)`, derived at read time (not stored). Matches Phase 14 D-01 contract. No wrapper type — the Boolean list IS the status.

### Repository Layer Design (Area 4)
- **D-06:** **Per-layer repository + interface.** Three interfaces in `DG.Core.Data`:
  - `IRuleRepository` — extend with `GetObjectsAsync(ConnectionInfo, CancellationToken)` for METAGRAPH Objects
  - `IOntoGraphRepository` / `Neo4jOntoGraphRepository` — `GetClassesAsync`, `GetObjPropertiesAsync`, `GetDataPropertiesAsync` (queries `graph='OntoGraph'`)
  - `IValidGraphRepository` / `Neo4jValidGraphRepository` — `GetRunsAsync` (adapts existing `ValidationRunsQueryService.QueryAsync`), returns Run + Status + DesignState
  Each interface enables unit testing with mock repositories. Follows the existing `IRuleRepository` pattern exactly (single async method pattern, `ConnectionInfo` + `CancellationToken` params, `TimeSpan QueryTimeout`).

### Claude's Discretion
- Exact CONNECTOR update details: input nickname renames ("Neo4j URI"→"Neo4jURI", "User"→"Neo4jUser", "Password"→"Neo4jPassword"), database-name input kept as runtime-only (not in port-IRI map), Connect boolean kept, output renamed "Connection"→"Database", Project passthrough output port (if port-IRI map specifies it — researcher to verify)
- GRAPH DECONSTRUCT is a pure passthrough `GH_Component` — no async, no database calls, no `SolveInstance` complexity. Takes ConnectionInfo from CONNECTOR, wraps in 4 layer-specific handle types, outputs them. Each handle carries the same ConnectionInfo reference.
- Exact property names for handle types (e.g., `MetagraphHandle.Connection` vs `MetagraphHandle.ConnectionInfo` — follow existing `ConnectionInfo` naming)
- Whether `Neo4jValidGraphRepository` adapts `ValidationRunsQueryService` in-place or creates a fresh class (recommend: new class, deprecate old service — VALIDATION RUNS component is being replaced)
- DesignState output type from VALIDATION GRAPH — use the Phase 16 `DesignState` model (3-part composition) directly, since VALIDATION GRAPH reads DesignState from ValidGraph which was written by VALIDATOR in Phase 18 with statePayloadJson v2. But at Phase 17 time, Phase 16 models exist and VALIDATOR doesn't write v2 yet — the repository should handle both v1 (ParamState-only) and v2 (3-part) payloads gracefully.
- GRAPH DECONSTRUCT, ONTOGRAPH, and VALIDATION GRAPH component icons — use placeholder or generate from existing icon pattern
- Error message wording for index-mismatch guards and handle validation — follow `ErrorMessageTemplates` What+Where+How-to-fix pattern
- Whether `GhCastingHelpers` gets per-handle `Try*` methods or a generic `Unwrap<T>` is sufficient (recommend: generic `Unwrap<T>` works since each handle is a distinct .NET type — downstream components use `Unwrap<MetagraphHandle>()`, etc.)
- Exact ordering of Run/Status/DesignState outputs (order by `createdAt DESC, runId ASC` preserved from existing `ValidationRunsQueryService`)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Component contract & ontology
- `ontology/port-iri-map-V7.md` — per-port IRI contract for CONNECTOR, GRAPH DECONSTRUCT, METAGRAPH, ONTOGRAPH, VALIDATION GRAPH (grep for component names). **MUST read.**
- `ontology/GH_DesignGrammars.pdf` — the 14-component schema; wiring diagrams for all 5 graph-access components. Note: PDF's port labels (e.g., "Status Datatype: text") may be stale — the port-IRI map + Phase 13 investigation take precedence.
- `ontology/DesignGrammar-V7.owl` — V7 ontology: `dgm:Metagraph`, `dg:Ontograph`, `dgv:Validgraph`, `dgs:SpecGraph` layer classes; `dg:Class`, `dg:ObjProperty`, `dg:DataProperty` reification classes; `dgv:Run`, `dg:DesignState`, `dg:ObjState`; `dgv:ValidStatus`
- `ontology/V7-INVESTIGATION.md` — conflict resolutions (a) ValidStatus vs Status, (b) DesignState storage layer (ValidGraph), (c) version marker

### Existing code to adapt or replace
- `DG/src/DG.Grasshopper/Components/ConnectorComponent.cs` — existing CONNECTOR component to update (rename ports, output name)
- `DG/src/DG.Grasshopper/Components/MetagraphComponent.cs` — existing METAGRAPH component to extend (add Objects output, index-matched)
- `DG/src/DG.Grasshopper/Components/ValidationRunsComponent.cs` — existing VALIDATION RUNS to replace with VALIDATION GRAPH (new GUID, new output schema)
- `DG/src/DG.Core/Data/Neo4jRuleRepository.cs` — extend with `GetObjectsAsync` (REFERS_TO→Class query)
- `DG/src/DG.Core/Data/IRuleRepository.cs` — extend interface with `GetObjectsAsync`
- `DG/src/DG.Core/Data/Neo4jConnectorService.cs` — connection test pattern (reused by CONNECTOR, unchanged)
- `DG/src/DG.Core/Services/ValidationRunsQueryService.cs` — adapt into `Neo4jValidGraphRepository` (same ValidGraph Cypher, different output schema — Run + Status + DesignState instead of ValidationRunQueryResult list)
- `DG/src/DG.Core/Models/ConnectionInfo.cs` — the credential bundle wrapped by all handle types
- `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` — shared GH value unwrapping (generic `Unwrap<T>` pattern)
- `DG/src/DG.Grasshopper/PublicTypes.cs` — add public wrappers for 4 handle types + any new output models
- `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` — extend for graph-access error messages

### Models to create
- `DG/src/DG.Core/Models/MetagraphHandle.cs` — wraps ConnectionInfo (new)
- `DG/src/DG.Core/Models/OntographHandle.cs` — wraps ConnectionInfo (new)
- `DG/src/DG.Core/Models/ValidGraphHandle.cs` — wraps ConnectionInfo (new)
- `DG/src/DG.Core/Models/SpecGraphHandle.cs` — wraps ConnectionInfo (new)
- `DG/src/DG.Core/Models/OntologyClass.cs` — IRI + label (for ONTOGRAPH Class output)
- `DG/src/DG.Core/Models/OntologyProperty.cs` — IRI + label (for ONTOGRAPH ObjProperties/DataProperties outputs)

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — GHGA-01..05 (graph access components)
- `.planning/ROADMAP.md` — Phase 17 goal + 4 success criteria
- `.planning/PROJECT.md` — key decisions: project isolation, DB labels unchanged except Knowledge*→Spec*, port-IRI contract

### Prior phase context (decisions carried forward)
- `.planning/milestones/v7.0-phases/13-ontology-v7-and-contract-investigation/13-CONTEXT.md` — D-01 through D-11: DesignState layer placement (ValidGraph), MERGE by StateId+project, no-orphan invariant, ValidStatus per-ObjState Boolean array, VALIDATION GRAPH new GUID
- `.planning/milestones/v7.0-phases/14-graph-schema-v4-propagation/14-CONTEXT.md` — D-01 (no Status text field), D-14 (ValidGraph runtime literal), D-06 (coalesce read pattern)
- `.planning/milestones/v7.0-phases/16-dg-core-state-models-and-state-components/16-CONTEXT.md` — D-01/D-02 (DesignState composition = independent bags), D-04 (deterministic StateId), DesignState model definition
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`Neo4jRuleRepository`** (`DG.Core.Data`): Established async query pattern — `GraphDatabase.Driver` → `AsyncSession` → `RunAsync` → `ForEachAsync`. Both `GetRulesAsync` and the new `GetObjectsAsync` follow this same pattern. Two queries can share one driver/session.
- **`ValidationRunsQueryService`** (`DG.Core.Services`): Already queries ValidGraph with the correct `graph='ValidGraph'` literal. Already parses `statePayloadJson`. The `Neo4jValidGraphRepository` adapts this: same Cypher template, different output model (Run + Status + DesignState instead of `ValidationRunQueryResult`).
- **`ConnectionInfo`** (`DG.Core.Models`): Immutable credential bundle (`Uri`, `User`, `Password`, `Database`, `Project`, `IsConnected`, `StatusMessage`). All handle types wrap this — no new connection logic needed.
- **`ConnectorComponent` async pattern**: `Task<T>` + `CancellationTokenSource` + `ContinueWith` → `ScheduleSolution` + `ExpireSolution`. All 3 reader components (METAGRAPH, ONTOGRAPH, VALIDATION GRAPH) reuse this exact pattern — CONNECTOR established it; the readers follow it.
- **`GhCastingHelpers.Unwrap<T>`**: Generic GH_Goo → .NET type unwrapping. Works for any type registered in Grasshopper's type system — handles are just types.

### Established Patterns
- **Async load with edge-triggered refresh**: Every reader component uses the same pattern: (1) accept ConnectionInfo + bool Refresh, (2) start async task on refresh rising edge or connection change, (3) `ContinueWith` schedules re-solve, (4) display status in `Message` and `AddRuntimeMessage`. CONNECTOR, METAGRAPH, VALIDATION RUNS all follow this. GRAPH DECONSTRUCT is the exception — no async, no refresh, pure passthrough.
- **`#if GRASSHOPPER_SDK` guards**: All GH-dependent component code lives inside `#if GRASSHOPPER_SDK`. The `#else` block provides a stub class for non-GH builds. All 3 new components follow this.
- **`DgComponentCategory.Category` + `.Subcategory`**: All components share the same category ("DG") and subcategory ("Design Grammar") for Grasshopper toolbar grouping.
- **`DgIcons`**: Static icon references (`DgIcons.Connector24`, `DgIcons.Metagraph24`, etc.) — new components need icon entries (researcher to verify icon naming convention and whether placeholder icons exist).
- **Per-layer repository separation**: The decision (D-06) follows the existing pattern — `IRuleRepository` already separates Metagraph queries from `Neo4jConnectorService` (connection testing). Adding `IOntoGraphRepository` and `IValidGraphRepository` extends this pattern rather than inventing it.
- **Immutable model classes**: `ConnectionInfo` uses `{ get; init; }` with default values. Handle types follow the same pattern.

### Integration Points
- **Phase 16 (DG.Core State Models)**: VALIDATION GRAPH outputs `DesignState` objects — the DesignState model (with 3-part ObjState/ParamState/PropState composition) is defined in Phase 16. VALIDATION GRAPH's repository deserializes `statePayloadJson` into DesignState. At Phase 17 time, only v1 payloads exist in the DB — the repository must handle v1 (ParamState-only) gracefully until Phase 18 VALIDATOR starts writing v2.
- **Phase 18 (Rules and Validator Rework)**: VALIDATOR accepts DesignState from the canvas (produced by DESIGN STATE component, Phase 16) and writes `statePayloadJson` v2 on publish. VALIDATION GRAPH then reads those v2 payloads back — Phase 17 builds the read side, Phase 18 builds the write side.
- **Phase 19 (Deconstruct and Reinstate)**: DESIGN STATE DECONSTRUCT and OBJECT DECONSTRUCT consume ObjState and DesignState from VALIDATION GRAPH's outputs.
- **Phase 15 (SpecGraph Runtime Rename)**: `SpecGraph` handle matches DB after rename — GRAPH DECONSTRUCT's SpecGraph output is a future hook for SpecGraph-reading components (currently none exist; the handle is wired but no consumer component yet).
- **data-service** (Python): Not directly touched by Phase 17 — these are C# Grasshopper components. But the Cypher queries in `Neo4jValidGraphRepository` must match the write schema in `app.py` (ValidationRun node structure, `statePayloadJson` format).
</code_context>

<specifics>
## Specific Ideas

- **GRAPH DECONSTRUCT is a pure type-wrapper.** The user confirmed individual handle types — GRAPH DECONSTRUCT is essentially a 1→4 type adapter. It takes one ConnectionInfo input and produces 4 typed outputs, all wrapping the same ConnectionInfo. No database calls, no async, no error states beyond "no input connected." This is the simplest component in the entire v7.0 set.
- **METAGRAPH Objects are graph-structural, not naming-convention-based.** The user chose direct REFERS_TO→Class Neo4j query over VariableTypeInferrer. This means Objects = the set of Class nodes that rules actually reference, not the set of variables that happen to be named like objects. Clean and robust — if a rule references a Class, it shows up; if it doesn't, it doesn't.
- **DesignState deduplication is a read-side convenience.** The user chose deduplicated DesignState output from VALIDATION GRAPH. This means the component does a small amount of post-processing (DistinctBy StateId) after loading runs. The raw Neo4j query still returns all runs with their DesignStates — dedup happens in C# before output.
- No other specific references or "I want it like X" moments — the decisions above capture the full intent.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Cross-phase notes (not scope changes)
- **Phase 18**: VALIDATOR writes `statePayloadJson` v2 — this is when v2 payloads first appear in the DB. Phase 17's `Neo4jValidGraphRepository` should handle both v1 and v2 payloads gracefully (read-side tolerance) since it may run before or during Phase 18 development.
- **Phase 18**: `ValidationRunsQueryService` is deprecated/removed when VALIDATION GRAPH replaces VALIDATION RUNS — coordinate with Phase 18 planner to avoid merge conflicts on the same file.
- **Phase 20**: SpecGraph handle currently has no consumer component — it's wired for future use. If no SpecGraph-reading component is planned for v7.0, document this in release notes.
</deferred>

---

*Phase: 17-graph-access-components*
*Context gathered: 2026-07-04*
