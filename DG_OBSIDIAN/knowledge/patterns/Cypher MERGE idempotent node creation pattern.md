---
tags: [pattern, cypher, neo4j, idempotent]
date: 2026-04-05
---

# Cypher MERGE Idempotent Node Creation Pattern

## Pattern

All graph creation uses `MERGE` + `SET` instead of `CREATE`. MERGE matches existing nodes by key properties and only creates if not found, making operations idempotent.

## Template

```cypher
MERGE (c:Class {iri: 'ex:Building'})
SET c.label = 'Building',
    c.project = 'my-project',
    c.graph = 'OntoGraph'
```

## Key Property per Label

| Label | MERGE Key |
|-------|-----------|
| Class | `iri` |
| DatatypeProperty | `iri` |
| ObjectProperty | `iri` |
| Builtin | `iri` |
| Rule | `Rule_Id` |
| Atom | `Atom_Id` |
| Var | `name` |
| Literal | `lex` + `datatype` |

## Why MERGE

- **Idempotent** — running the same Cypher twice doesn't create duplicates
- **Property reuse** — shared Classes/Properties across rules use same IRI
- **Edit support** — re-ingesting an edited rule updates SET properties without duplicating MERGE targets
- **LLM-friendly** — simpler pattern for LLM to generate consistently

## Caveat

MERGE on relationships can be surprising if not all endpoint nodes are already bound. Always MERGE nodes first, then MERGE relationships.

## Related

- [[Graph schema v3 is the canonical data model]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[Edit mode requires cleanup of old atoms before re-creation]]
