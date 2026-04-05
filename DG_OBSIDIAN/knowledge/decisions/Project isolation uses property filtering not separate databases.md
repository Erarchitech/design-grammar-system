---
tags: [decision, architecture, neo4j, isolation]
date: 2026-04-05
---

# Project Isolation Uses Property Filtering Not Separate Databases

## Decision

All projects share a single Neo4j database. Isolation is achieved by mandatory `project` property on every node, filtered in all Cypher queries.

## Implementation

- `buildCypher(view)` includes `project:'<name>'` in all MATCH patterns
- `fetchExistingRules()` filters by project
- `clearGraph()` deletes only nodes matching `project AND graph`
- `tagProjectNodes()` runs post-ingestion to tag nodes where `project IS NULL`
- n8n webhook body includes `project`; "Set Input Defaults" node reads `$json.project`

## Rationale

- **Neo4j Community Edition** supports only one database — multi-database requires Enterprise
- **Shared ontology potential** — Classes/Properties could eventually be shared across projects (same IRI, different project tags)
- **Simpler deployment** — no database provisioning per project

## Trade-offs

- **No hard isolation** — a bug in query filtering could leak data between projects
- **Query overhead** — every query must include `project` filter
- **Cleanup complexity** — deleting a project requires matching all nodes by property, not dropping a database

## Related

- [[Neo4j stores ontology and metagraph in a single database]]
- [[Neo4j provides graph storage with project-scoped isolation]]
