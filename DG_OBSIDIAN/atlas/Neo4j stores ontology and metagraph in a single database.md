---
tags: [atlas, neo4j, database, schema, v4]
date: 2026-07-05
---

# Neo4j Stores Ontology and Metagraph in a Single Database

All data lives in **one Neo4j 5 database**. Logical separation is achieved by the `graph` property on every node.

## Graph Separation

| Graph Value | Contains | Purpose |
|-------------|----------|---------|
| `OntoGraph` | Class, DatatypeProperty, ObjectProperty | Domain ontology terms (building types, properties) |
| `Metagraph` | Rule, Atom, Builtin, Var, Literal | SWRL rules and their decomposed atom structures |
| `ValidGraph` | DesignState, Run, IntegrationConfig, ValidationEntity | Validation run state and metadata |
| `SpecGraph` | SpecNote, SpecTag, SpecSession, SpecClass | Project spec storage (notes, tags, sessions) |

## Canonical Node Labels (v4)

| Label | Key Property | Display Property | Graph |
|-------|-------------|-----------------|-------|
| `Class` | `iri` | `label` | OntoGraph |
| `DatatypeProperty` | `iri` | `SWRL_label` | OntoGraph |
| `ObjectProperty` | `iri` | `label` | OntoGraph |
| `Builtin` | `iri` | `label` | Metagraph |
| `Rule` | `Rule_Id` | `Rule_Id` | Metagraph |
| `Atom` | `Atom_Id` | `SWRL_label` | Metagraph |
| `Var` | `name` | `name` | Metagraph |
| `Literal` | `lex` + `datatype` | `lex` | Metagraph |
| `DesignState` | `StateId` | `kind` | ValidGraph |
| `Run` | `Run_Id` | `Run_Id` | ValidGraph |

### DesignState Properties

| Property | Values | Description |
|----------|--------|-------------|
| `kind` | `ObjState`, `ParamState`, `PropState` | State kind discriminator |
| `StateId` | `OS_*`, `DS_*`, `PS_*` | Prefixed identifier per kind |
| `statePayloadJson` | JSON (v2) | Envelope with `objStates`, `paramStates`, `propStates` keys |

### Run Properties

| Property | Type | Description |
|----------|------|-------------|
| `Run_Id` | string | Key property |
| `ValidStatus` | Boolean[] | Per-ObjState validation result (index-matched) |
| `SendStatus` | Boolean | Whether results were published to Speckle |
| `statePayloadJson` | JSON (v2) | Projection of the DesignState that was validated |

## Canonical Relationships

- `HAS_BODY` — Rule → Atom (body atoms, with `order` property)
- `HAS_HEAD` — Rule → Atom (head atoms, with `order` property)
- `REFERS_TO` — Atom → Class/DatatypeProperty/ObjectProperty/Builtin
- `ARG` — Atom → Var/Literal (with `pos` property, 1-indexed)
- `HAS_STATE` — DesignState → state nodes (read-side composition)

## Project Isolation

Every node carries a `project` property. All Cypher queries filter by `project:'<name>'`. See [[Project isolation uses property filtering not separate databases]].

## Schema Migration History (v3→v4, complete)

v3→v4 renames (v7.0 Phase 14, shipped 2026-07):
- DesignState `kind` values: `DefState`→`ParamState`, `ObjectState`→`ObjState`, new `PropState`
- `KnowledgeGraph`→`SpecGraph` (runtime label rename, Phase 15)
- `ValidationGraph`→`ValidGraph` (runtime label rename, Phase 14)
- Rule properties: `text`→`SWRL`, `title`→`RuleName`, new `RuleDescription`

Legacy → v3 renames (v3.0, shipped 2026-06):
- `Rule.id` → `Rule.Rule_Id`
- `DatatypeProperty.label` → `DatatypeProperty.SWRL_label`
- `Atom.id` / `Atom.Id` → `Atom.Atom_Id`
- Added: `Atom.iri`, `Atom.SWRL_label`

## Related

- [[Graph schema v4 is the canonical data model]]
- [[Architecture is a microservices Docker pipeline]]
- [[Cypher MERGE idempotent node creation pattern]]
