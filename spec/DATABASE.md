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
(:Run {Run_Id: "VRUN_abc123", ValidStatus: [true, false, true], SendStatus: true, statePayloadJson: '{...}', graph: "ValidGraph", project: "1"})
```
- `Run_Id` — unique identifier for the validation run
- `ValidStatus` — Boolean list, one element per ObjState in the validated DesignState, index-matched to ObjState order
- `SendStatus` — single Boolean per Run (publish-to-Speckle/data-service success)
- `statePayloadJson` — v2 projection for Model Viewer read-back

## Relationships

| Relationship | From | To | Properties | Description |
|-------------|------|-----|-----------|-------------|
| `HAS_BODY` | Rule | Atom | `order` (int) | Body atoms (conditions) |
| `HAS_HEAD` | Rule | Atom | `order` (int) | Head atoms (conclusions) |
| `REFERS_TO` | Atom | Class/DatatypeProperty/ObjectProperty/Builtin | — | What the atom references |
| `ARG` | Atom | Var/Literal | `pos` (int, 1-indexed) | Atom arguments |
| `HAS_STATE` | DesignState | DesignState | — | Read-side composition: parent DesignState to ObjState/ParamState/PropState |
| `TAGGED_WITH` | SpecNote | SpecTag | — | Note-to-tag association |
| `INSTANCE_OF` | SpecNote/SpecSession | SpecClass | — | Instance-to-parent-class link |

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
