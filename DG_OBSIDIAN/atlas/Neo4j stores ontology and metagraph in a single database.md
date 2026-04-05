---
tags: [atlas, neo4j, database, schema]
date: 2026-04-05
---

# Neo4j Stores Ontology and Metagraph in a Single Database

All data lives in **one Neo4j 5 database**. Logical separation is achieved by the `graph` property on every node.

## Graph Separation

| Graph Value | Contains | Purpose |
|-------------|----------|---------|
| `OntoGraph` | Class, DatatypeProperty, ObjectProperty | Domain ontology terms (building types, properties) |
| `Metagraph` | Rule, Atom, Builtin, Var, Literal | SWRL rules and their decomposed atom structures |
| `ValidationGraph` | IntegrationConfig, ValidationRun, ValidationEntity | Speckle integration config + validation run metadata |

## Canonical Node Labels (v3)

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

## Canonical Relationships

- `HAS_BODY` — Rule → Atom (body atoms, with `order` property)
- `HAS_HEAD` — Rule → Atom (head atoms, with `order` property)
- `REFERS_TO` — Atom → Class/DatatypeProperty/ObjectProperty/Builtin
- `ARG` — Atom → Var/Literal (with `pos` property, 1-indexed)

## Project Isolation

Every node carries a `project` property. All Cypher queries filter by `project:'<name>'`. See [[Project isolation uses property filtering not separate databases]].

## v3 Migration Notes

Legacy → v3 renames:
- `Rule.id` → `Rule.Rule_Id`
- `DatatypeProperty.label` → `DatatypeProperty.SWRL_label`
- `Atom.id` / `Atom.Id` → `Atom.Atom_Id`
- Added: `Atom.iri`, `Atom.SWRL_label`

## Related

- [[Graph schema v3 is the canonical data model]]
- [[Architecture is a microservices Docker pipeline]]
- [[Cypher MERGE idempotent node creation pattern]]
