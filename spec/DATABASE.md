# Database Schema (Neo4j Graph v4)

## Overview

All data lives in a **single Neo4j 5 database**. Logical separation uses the `graph` property on every node. Project isolation uses the `project` property. All Cypher queries filter by `project:'<n>'`.

## Graph Separation

| `graph` Value | Node Labels | Purpose |
|---------------|-------------|---------|
| `OntoGraph` | Class, DatatypeProperty, ObjectProperty | Domain ontology terms |
| `Metagraph` | Rule, Atom, Builtin, Var, Literal | SWRL rules and atom structures |
| `ValidGraph` | DesignState, Run, IntegrationConfig, ValidationEntity | Validation runs, design state metadata, integration config |
| `SpecGraph` | SpecNote, SpecTag, SpecSession, SpecClass | Project spec storage |
| `Computgraph` | Object, Behavior, Algorithm, Procedure, Pattern, Parameter, Interface, Representation, SharedProperty | Computgraph runtime entities (Phase 36) + cross-platform identity registry (Phase 32.1) — see [Identity Registry](#identity-registry-phase-321) |

## Node Labels

### OntoGraph

**Class** — Domain concepts (e.g. `ex:Building`, `ex:LivingUnit`)
```
(:Class {iri: "ex:Building", label: "Building", graph: "OntoGraph", project: "1"})
```

**DatatypeProperty** — Numeric/string attributes (e.g. `ex:hasHeight`)
```
(:DatatypeProperty {iri: "ex:hasHeight", SWRL_label: "hasHeight", label: "hasHeight", graph: "OntoGraph", project: "1"})
```

**ObjectProperty** — Relationships between classes
```
(:ObjectProperty {iri: "ex:locatedIn", label: "locatedIn", graph: "OntoGraph", project: "1"})
```

### Metagraph

**Rule** — A design rule with its natural language text
```
(:Rule {Rule_Id: "R_URB_HEIGHT_MAX_75_V", text: "Maximum building height is 75 meters", graph: "Metagraph", project: "1"})
```

**Atom** — An individual SWRL atom (class assertion, property, or builtin)
```
(:Atom {Atom_Id: "R_URB_HEIGHT_MAX_75_V_A1", iri: "ex:Building", SWRL_label: "Building(?b)", graph: "Metagraph", project: "1"})
```

**Var** — A SWRL variable
```
(:Var {name: "b", graph: "Metagraph", project: "1"})
```

**Literal** — A constant value
```
(:Literal {lex: "75", datatype: "xsd:decimal", graph: "Metagraph", project: "1"})
```

**Builtin** — A SWRL comparison operator
```
(:Builtin {iri: "swrlb:greaterThan", label: "greaterThan", graph: "Metagraph", project: "1"})
```

### SpecGraph

**SpecClass** — Parent hub nodes connecting all instances of a spec type
```
(:SpecClass {name: "SpecNote", label: "SpecNote", graph: "SpecGraph"})
(:SpecClass {name: "SpecSession", label: "SpecSession", graph: "SpecGraph"})
```

**SpecNote** — A project spec entry (from folder ingest or NL prompt)
```
(:SpecNote {noteId: "abc123", title: "Site constraints", content: "...", tags: ["zoning"], source: "notes/site.md", graph: "SpecGraph", project: "1"})
```

**SpecTag** — A tag label shared across notes
```
(:SpecTag {name: "zoning", graph: "SpecGraph", project: "1"})
```

**SpecSession** — An interaction log (insert, query, or update)
```
(:SpecSession {sessionId: "ks-abc123", mode: "insert", prompt: "...", result: "...", createdAt: "2026-01-01T00:00:00Z", graph: "SpecGraph", project: "1"})
```

### ValidGraph

**DesignState** — 3-part composed design state (ObjState, ParamState, PropState)
```
(:DesignState {StateId: "OS_abc123", kind: "ObjState", statePayloadJson: '{...}', graph: "ValidGraph", project: "1"})
(:DesignState {StateId: "DS_abc123", kind: "ParamState", statePayloadJson: '{...}', graph: "ValidGraph", project: "1"})
(:DesignState {StateId: "PS_abc123", kind: "PropState", statePayloadJson: '{...}', graph: "ValidGraph", project: "1"})
```
- `kind` = ObjState | ParamState | PropState
- `statePayloadJson` = v2 JSON envelope with `objStates`/`paramStates`/`propStates` keys, each containing typed state arrays
- StateId prefix: `OS_` for ObjState, `DS_` for ParamState, `PS_` for PropState
- Persisted with `graph = 'ValidGraph'` (not Metagraph — corrected in v7.0)
- Written only by VALIDATOR on publish; MERGE'd by StateId + project (dedup across runs)
- No orphan DesignStates — always has >=1 linked Run

**Run** — A validation run execution record
```
(:Run {Run_Id: "VRUN_abc123", ValidStatus: [true, false, true], SendStatus: true, statePayloadJson: '{...}', shaclReportJson: '{...}', graph: "ValidGraph", project: "1"})
```
- `Run_Id` — unique identifier for the validation run
- `ValidStatus` — Boolean list, one element per ObjState in the validated DesignState, index-matched to ObjState order
- `SendStatus` — single Boolean per Run (publish-to-Speckle/data-service success)
- `statePayloadJson` — v2 projection for Model Viewer read-back
- `shaclReportJson` — JSON string holding the per-run SHACL validation report envelope (`status`, `conforms`, `results[]`, per-severity counts); sibling property to `rulesJson`/`statePayloadJson`, written by `data-service`'s publish path after the `dg-reasoner` SHACL call; **absent on pre-823 runs** (Model Viewer/UI must treat missing `shaclReportJson` as "not checked," never as an error) — added Phase 823 (SHCL-01, D-06). Governed by `spec/RULE-PARTITION-POLICY.md`.

### Computgraph

**dgId property** — Every Computgraph entity node (`:Object`, `:Procedure`, `:Pattern`, `:Parameter`, `:Interface`) carries an optional `dgId` property (nullable on pre-32.1 nodes). Format: `dg:` followed by the first 16 uppercase hexadecimal characters of the SHA-256 digest over the UTF-8 bytes of `project|definitionId|cgId`. See `spec/DG-ID.md` for the normative identity specification and golden-vector parity contract.

---

**Object** — A design object, tagged or recognized from the canvas.
```
(:Object {
   objectName: "Building",
   classIri: "ex:Building",        // optional, cross-layer to OntoGraph Class
   source: "tagged",               // tagged | recognized
   definitionId: "abc-123-def",
   fileName: "model.gh",
   publishedAt: datetime(),
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `objectName` | string | Display name of the object (display property) |
| `classIri` | string | Optional cross-layer link to OntoGraph `Class.iri` |
| `dgId` | string | Platform-neutral identity (`dg:` + 16 uppercase hex) |
| `source` | enum | `tagged` \| `recognized` |
| `provider` | string | AI provider (recognized only) |
| `model` | string | AI model (recognized only) |
| `confidence` | float | Recognition confidence (recognized only) |
| `definitionId` | string | Definition id from Phase 30/35 serialization |
| `fileName` | string | Source canvas file name |
| `publishedAt` | datetime | When the node was published |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(cgId, definitionId, project)`
- Written only by `POST /computgraph/publish`
- `REFERS_TO` to OntoGraph `Class` when `classIri` is present (cross-layer bridge)
- **Known gap (Phase 36 WR-06):** `provider`/`model`/`confidence` are read and written by `computgraph_publish.py` for every `recognized` entity (Object, Procedure, Pattern, Parameter, Interface), but none of the GH-side wire DTOs (`ComputgraphContextSerializer.cs` `Cg*Dto` types) carry these fields -- only `Source`/`DgId`. Until the DG.Core accept path and serializer are extended to transport them, every `recognized` entity published from Grasshopper gets `provider`/`model`/`confidence = null`, regardless of this table.

---

**Behavior** — A computational behavior (structural, no cgId or dgId).
```
(:Behavior {
   definitionId: "abc-123-def",
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `definitionId` | string | Definition id from serialization (key part) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(definitionId, project)`
- Structural node — no cgId or dgId
- Written only by `POST /computgraph/publish`

---

**Algorithm** — A specific algorithm within a behavior.
```
(:Algorithm {
   algorithmName: "BuildingHeightChecker",
   algIndex: 0,
   contextJson: '{...}',
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `algorithmName` | string | Algorithm display name (display property) |
| `algIndex` | int | Index within the behavior |
| `contextJson` | string | Full canvas context JSON for reconstruction |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(algIndex, definitionId, project)`
- Written only by `POST /computgraph/publish`

---

**Procedure** — A procedure within an algorithm.
```
(:Procedure {
   procedureName: "CheckHeight",
   procIndex: 0,
   cgId: "cg:alg:kind:CheckHeight",
   dgId: "dg:9F2A4C1E7B03D5A8",
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `procedureName` | string | Procedure display name (display property) |
| `procIndex` | int | Index within the algorithm |
| `cgId` | string | Deterministic Computgraph node id |
| `dgId` | string | Platform-neutral identity (`dg:` + 16 uppercase hex) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(cgId, definitionId, project)`
- Written only by `POST /computgraph/publish`

---

**Pattern** — A design pattern within a procedure.
```
(:Pattern {
   patternName: "HeightConstraint",
   cgId: "cg:alg:kind:HeightConstraint",
   dgId: "dg:3B7D9F1A6C2E8045",
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `patternName` | string | Pattern display name (display property) |
| `cgId` | string | Deterministic Computgraph node id |
| `dgId` | string | Platform-neutral identity (`dg:` + 16 uppercase hex) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(cgId, definitionId, project)`
- Written only by `POST /computgraph/publish`
- `PATTERN_HOST_TO` enables pattern nesting

---

**Parameter** — A parameter driving a procedure.
```
(:Parameter {
   parameterName: "maxHeight",
   paramKind: "Variable",
   dataType: "Float",
   domainMin: 0.0,
   domainMax: 100.0,
   domainStep: 0.5,
   cgId: "cg:alg:kind:maxHeight",
   dgId: "dg:8E6F2C1A9B7D3045",
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `parameterName` | string | Parameter display name (display property) |
| `paramKind` | enum | `Variable` \| `Constant` \| `Emergent` |
| `dataType` | enum | `Float` \| `Integer` \| `Text` \| `Boolean` \| `Geometry` |
| `domainMin` | number | Lower bound (optional, slider parameters) |
| `domainMax` | number | Upper bound (optional, slider parameters) |
| `domainStep` | number | Step size (optional, slider parameters) |
| `cgId` | string | Deterministic Computgraph node id |
| `dgId` | string | Platform-neutral identity (`dg:` + 16 uppercase hex) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(cgId, definitionId, project)`
- Written only by `POST /computgraph/publish`
- `PARAM_LINK` connects this parameter to the Interface nodes its wires feed (wire-derived)

---

**Interface** — A pattern interface (input or output).
```
(:Interface {
   interfaceName: "heightValue",
   ifaceType: "Input",
   cgId: "cg:alg:kind:heightValue",
   dgId: "dg:1C4E7F3A9B2D8056",
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `interfaceName` | string | Interface display name (display property) |
| `ifaceType` | enum | `Input` \| `Output` |
| `cgId` | string | Deterministic Computgraph node id |
| `dgId` | string | Platform-neutral identity (`dg:` + 16 uppercase hex) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(cgId, definitionId, project)`
- Written only by `POST /computgraph/publish`

---

**Representation** — A platform-native identifier bound to a dgId. One entity may have N representations across platforms.

```
(:Representation {
   nativeId: "<platform-native identifier>",
   platform: "Grasshopper",          // Grasshopper | Revit | IFC | Speckle
   nativeIdKind: "InstanceGuid",     // InstanceGuid | UniqueId | GlobalId | ApplicationId
   connector: "gh-plugin",
   boundAt: datetime(),
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `nativeId` | string | The platform-native identifier value (merge key part) |
| `platform` | enum | `Grasshopper` \| `Revit` \| `IFC` \| `Speckle` (merge key part) |
| `nativeIdKind` | enum | `InstanceGuid` \| `UniqueId` \| `GlobalId` \| `ApplicationId` |
| `connector` | string | The connector that created the binding (provenance) |
| `boundAt` | datetime | When the binding was created (provenance) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(nativeId, platform, project)`
- Written only by the data-service identity API (`PATCH /identity/bind`, `POST /identity/{dgId}/representations`)
- Managed via `bind`/`detach` operations — never directly by LLM rule-ingest

---

**SharedProperty** — A cross-platform shared property value keyed by dgId and property name.

```
(:SharedProperty {
   dgId: "dg:9F2A4C1E7B03D5A8",
   propertyName: "insulation",
   value: 2.4,
   platform: "Grasshopper",
   connector: "gh-plugin",
   writtenAt: datetime(),
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `dgId` | string | Identity the property is attached to (merge key part) |
| `propertyName` | string | The shared property name (merge key part) |
| `value` | any | The computed value |
| `platform` | string | Platform that computed the value (provenance) |
| `connector` | string | Connector that wrote it (provenance) |
| `writtenAt` | datetime | Write timestamp (provenance) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (merge key part) |

- Merge key: `(dgId, propertyName, project)` — any bound platform sees the same value
- Conflict policy: last-write-wins (MVP)
- Written only by the data-service identity API (`POST /identity/{dgId}/properties`)
- Cross-platform: a value written from Grasshopper is read identically "as Revit"

---

**Identity Registry (Phase 32.1)**

The identity registry comprises the `Representation` and `SharedProperty` node labels, the `dgId` property on Computgraph entity nodes, and the `HAS_REPRESENTATION` / `HAS_SHARED_PROPERTY` relationships — all under `graph:'Computgraph'`. These nodes are written ONLY by the data-service identity API (`/identity/*` routes), never by LLM rule-ingest.

**Recorded decision:** `dgId` gets **no OWL annotation property in V7**. It is runtime/persistence identity, not ontological vocabulary — the OWL file does not model identity bindings. Rationale: the ADR at `DG_OBSIDIAN/knowledge/decisions/DG ID cross-platform identity scheme.md`.

**Normative spec:** `spec/DG-ID.md` — this database schema documents the structural shape; `DG-ID.md` is the normative contract for format, minting, rename/collision rules, the binding model, and shared-property semantics.

## Relationships

| Relationship | From | To | Properties | Description |
|-------------|------|-----|-----------|-------------|
| `HAS_BODY` | Rule | Atom | `order` (int) | Body atoms (conditions) |
| `HAS_HEAD` | Rule | Atom | `order` (int) | Head atoms (conclusions) |
| `REFERS_TO` | Atom | Class/DatatypeProperty/ObjectProperty/Builtin | — | What the atom references |
| `REFERS_TO` | Object | Class | — | Cross-layer bridge to OntoGraph (when classIri present) |
| `ARG` | Atom | Var/Literal | `pos` (int, 1-indexed) | Atom arguments |
| `HAS_STATE` | DesignState | DesignState | — | Read-side composition: parent DesignState to ObjState/ParamState/PropState |
| `TAGGED_WITH` | SpecNote | SpecTag | — | Note-to-tag association |
| `INSTANCE_OF` | SpecNote/SpecSession | SpecClass | — | Instance-to-parent-class link |
| `HAS_REPRESENTATION` | Computgraph entity | Representation | — | Entity → platform-native id binding |
| `HAS_SHARED_PROPERTY` | Computgraph entity | SharedProperty | — | Entity → cross-platform property value |
| `HAS_BEHAVIOR` | Object | Behavior | — | Object → behavior decomposition |
| `HAS_ALGORITHM` | Behavior | Algorithm | — | Behavior → algorithm decomposition |
| `HAS_PROCEDURE` | Algorithm | Procedure | — | Algorithm → procedure decomposition |
| `HAS_PATTERN` | Procedure | Pattern | — | Procedure → pattern decomposition |
| `PATTERN_HOST_TO` | Pattern | Pattern | — | Pattern nesting (sub-patterns) |
| `HAS_PARAMETER` | Procedure | Parameter | — | Procedure → parameter link |
| `HAS_INTERFACE` | Procedure | Interface | — | Procedure → interface link |
| `PARAM_LINK` | Parameter | Interface | — | Parameter → interface, wire-derived |
| `REFERS_TO` | Object | Class | — | Cross-layer bridge to OntoGraph (when classIri present) |

## Rule ID Format

```
R_<DOMAIN>_<PROPERTY>_<LIMIT>_V
```
Examples: `R_URB_HEIGHT_MAX_75_V`, `R_RES_AREA_MIN_28_V`

## Atom ID Format

```
Body atoms: {Rule_Id}_A1, _A2, _A3, ...
Head atoms: {Rule_Id}_H1, _H2, ...
```

## IRI Prefixes

- `ex:` — Domain terms (classes, properties, violation predicates)
- `swrlb:` — SWRL builtins (`greaterThan`, `lessThan`, `equal`, `notEqual`)

## Violation Pattern (Semantic Mapping)

The system uses **inverted logic** — body atoms fire when the constraint is **violated**:

| Natural Language | SWRL Body Builtin | Fires When |
|-----------------|-------------------|------------|
| "Maximum / at most X" | `swrlb:greaterThan(?val, X)` | Value exceeds limit |
| "Minimum / at least X" | `swrlb:lessThan(?val, X)` | Value below limit |
| "Equal to X" | `swrlb:notEqual(?val, X)` | Value differs |
| "Between min and max" | Two separate rules | One for min, one for max |

## Example: Complete Rule Graph

Rule: "Maximum building height is 75 meters"

```cypher
MERGE (r:Rule {Rule_Id: "R_URB_HEIGHT_MAX_75_V", SWRL: "Maximum building height is 75 meters", RuleName: "Max building height 75m", graph: "Metagraph", project: "1"})

MERGE (a1:Atom {Atom_Id: "R_URB_HEIGHT_MAX_75_V_A1", iri: "ex:Building", SWRL_label: "Building(?b)"})
MERGE (r)-[:HAS_BODY {order: 1}]->(a1)
MERGE (a1)-[:REFERS_TO]->(:Class {iri: "ex:Building"})
MERGE (a1)-[:ARG {pos: 1}]->(:Var {name: "b"})

MERGE (a2:Atom {Atom_Id: "R_URB_HEIGHT_MAX_75_V_A2", iri: "ex:hasHeight", SWRL_label: "hasHeight(?b, ?h)"})
MERGE (r)-[:HAS_BODY {order: 2}]->(a2)
MERGE (a2)-[:REFERS_TO]->(:DatatypeProperty {iri: "ex:hasHeight"})
MERGE (a2)-[:ARG {pos: 1}]->(:Var {name: "b"})
MERGE (a2)-[:ARG {pos: 2}]->(:Var {name: "h"})

MERGE (a3:Atom {Atom_Id: "R_URB_HEIGHT_MAX_75_V_A3", iri: "swrlb:greaterThan", SWRL_label: "greaterThan(?h, 75)"})
MERGE (r)-[:HAS_BODY {order: 3}]->(a3)
MERGE (a3)-[:REFERS_TO]->(:Builtin {iri: "swrlb:greaterThan"})
MERGE (a3)-[:ARG {pos: 1}]->(:Var {name: "h"})
MERGE (a3)-[:ARG {pos: 2}]->(:Literal {lex: "75", datatype: "xsd:decimal"})
```

## Schema Source Files

| File | Role |
|------|------|
| `training/dataset_schema.json` | Formal JSON schema definition |
| `cypher_template.txt` | v4 Cypher template for LLM prompts |
| `training/updated_cypher_reference_examples_v3.cypher` | Complete reference examples (v3 historical, carried forward) |
| `graph-viewer/config.template.js` | NeoVis display configuration |
| `data-service/app.py` | FastAPI data service Cypher for validation publish/read-back |

**When changing schema, update ALL of these files.**

## Cypher Expression Catalog (`llm/cypher_catalog.json`)

Phase 29 (DG-Aware Context Layer) generalizes rule-ingest Cypher generation
from a single hardcoded worked example (`cypher_template.txt`'s "maximum
height" few-shot) into a **versioned six-shape catalog**,
`llm/cypher_catalog.json` (`{version, shapes: [...]}`), loaded defensively by
`data-service/dg_context.py`'s `load_cypher_catalog()`. This is the new
**source of truth for standard Cypher shapes** the LLM gateway is prompted
with — `cypher_template.txt` remains the authoritative *schema* reference
(labels/relationships/key properties), while the catalog supplies the
*worked-example patterns* for each constraint family.

| Shape id | Name | What it represents |
|----------|------|---------------------|
| `max_limit` | Maximum Limit | "maximum X is N" / "at most N" — body fires via `swrlb:greaterThan` against a Literal threshold (violation-inverted). `Rule_Id`: `R_<DOMAIN>_<PROPERTY>_MAX_<LIMIT>_V`. |
| `min_limit` | Minimum Limit | "minimum X is N" / "at least N" — mirror of `max_limit` using `swrlb:lessThan`. `Rule_Id`: `R_<DOMAIN>_<PROPERTY>_MIN_<LIMIT>_V`. |
| `range` | Range (Between Min and Max) | "between MIN and MAX" — emits **two separate** violation Rules (one `min_limit`-shaped, one `max_limit`-shaped) sharing the same Class/DatatypeProperty via MERGE, each with its own violation property, Vars, and Atom subgraph. Not a new schema shape — documents the min+max pair as one worked example, per `cypher_template.txt`'s existing "never combine constraints" convention. |
| `ratio` | Ratio Limit | Relates two DatatypeProperties via a `swrlb:divide` Builtin producing a computed ratio Var, then compares that ratio against a Literal threshold with a second Builtin (`swrlb:greaterThan` for a max-ratio cap, `swrlb:lessThan` for a min-ratio floor). `Rule_Id`: `R_<DOMAIN>_<RATIO_NAME>_MAX_<LIMIT>_V` (or `_MIN_<LIMIT>_V`). |
| `boolean_requirement` | Boolean Requirement | A Boolean DatatypeProperty must equal a required value (usually `true`) — body fires via `swrlb:notEqual` when the actual value doesn't match (violation-inverted). `Rule_Id`: `R_<DOMAIN>_<PROPERTY>_REQ_<VALUE>_V`. |
| `existence_count` | Existence / Count Requirement | **New territory (CTXA-02/D-12).** At least N instances of a related quantity (modeled as a count-valued DatatypeProperty) must exist — a `swrlb:` Builtin ATOM PAIR against a Literal threshold: one Builtin (`swrlb:greaterThanOrEqual` vs. `0`) establishes a valid non-negative count, the second (`swrlb:lessThan` vs. the required minimum) is the violation-inverted threshold check. `Rule_Id`: `R_<DOMAIN>_<COUNT_PROPERTY>_MIN_<LIMIT>_V`. The Var MERGE for the count variable keys on **both** `name` and `project` (omitting `project` reintroduces the historical cross-project Var collision bug). |

**No schema-shape change.** `existence_count` — the one genuinely new
constraint family this catalog adds — reuses ONLY the node labels and
relationship types already documented above (`Class`, `DatatypeProperty`,
`ObjectProperty`, `Rule`, `Atom`, `Var`, `Literal`, `Builtin`; `HAS_BODY`,
`HAS_HEAD`, `REFERS_TO`, `ARG`). It introduces no new labels, no new
relationship types, and no new key properties, so none of the Schema Change
Propagation surfaces above (`cypher_template.txt`, `dataset_schema.json`,
`config.template.js`, n8n workflow prompts) require updating for this
catalog addition — this is a light-touch documentation note, not a
structural schema propagation.

**Runtime enforcement:** the catalog only supplies worked-example *guidance*
to the LLM prompt (via `data-service/dg_context.py`'s deterministic keyword
matcher, `assemble_context()`); it is `data-service`'s Cypher **validator**
(`validate_cypher()`, `POST /context/generate-cypher`) that actually enforces
the schema — allowed labels/relationships, `DesignState.kind` enum, key-name
conventions (`Rule_Id`/`Atom_Id`/`SWRL_label`), and the request-type-aware
write-verb policy — before any LLM-generated Cypher reaches Neo4j
`tx/commit`. No catalog shape bypasses this validator.

## v3→v4 Migration Notes (complete)

### v3→v4 migrations (all completed in v7.0 milestone)

**Graph schema:**
- Added `ValidGraph` as the fourth graph layer (for DesignState, Run, IntegrationConfig, ValidationEntity)
- DesignState moved from `graph='Metagraph'` to `graph='ValidGraph'` (corrected from v3 cypher_template)
- Added `SpecGraph` as the official graph layer for project spec storage

**Rule properties:**
- `Rule.text` → `Rule.SWRL`
- `Rule.title` → `Rule.RuleName`
- Added: `Rule.RuleDescription` (optional)

**DesignState kinds:**
- `DefState` → `ParamState`
- `ObjectState` → `ObjState`
- Added: `PropState` (new, for Rule+DataProperty+PropValue composition)

**Run/Validation labels:**
- `ValidationRun` → `Run` (node label)
- `ValidationGraph` → `ValidGraph` (graph property value)
- Added: `Run.ValidStatus` (Boolean list per ObjState)
- Added: `Run.SendStatus` (single Boolean per Run)

**Legacy → v3 (historical):**
- `Rule.id` → `Rule.Rule_Id`
- `DatatypeProperty.label` → `DatatypeProperty.SWRL_label`
- `Atom.id` / `Atom.Id` → `Atom.Atom_Id`
- Added: `Atom.iri`, `Atom.SWRL_label`
