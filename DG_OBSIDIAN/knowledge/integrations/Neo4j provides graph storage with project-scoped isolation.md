---
tags: [integration, neo4j, database, cypher]
date: 2026-04-05
---

# Neo4j Provides Graph Storage with Project-Scoped Isolation

## Connection Details

| Parameter | Value |
|-----------|-------|
| Image | `neo4j:5` |
| Bolt | `bolt://localhost:7687` (ext) / `bolt://neo4j:7687` (Docker) |
| HTTP | `http://localhost:7474` (ext) / proxied at `/neo4j/` |
| Auth | `neo4j / 12345678` |
| Database | Single default database |

## Access Patterns

### From n8n Workflows
- HTTP API: `POST /db/neo4j/tx/commit` with `{"statements": [{"statement": "..."}]}`
- Basic auth header

### From Data-Service (Python)
- `neo4j.GraphDatabase.driver(bolt_uri, auth=(user, pass))`
- Helper functions: `read_single()`, `read_many()`, `write_query()`
- Read-only enforcement via `is_write_query()` regex check in MCP endpoint

### From Browser (NeoVis)
- Direct bolt connection via `neo4j-driver` JS library
- Configured in `window.GRAPH_CONFIG`

### From Grasshopper Plugin (C#)
- `Neo4j.Driver` 5.28.2 NuGet package
- `INeo4jConnectorService` interface with async connection + 6s timeout
- `Neo4jRuleRepository` for multi-step rule loading

## Project Isolation

All queries include:
```cypher
WHERE n.project = '<project_name>' AND n.graph = '<OntoGraph|Metagraph>'
```

Post-ingestion tagging via `tagProjectNodes()` catches nodes where `project IS NULL`.

## Related

- [[Neo4j stores ontology and metagraph in a single database]]
- [[Project isolation uses property filtering not separate databases]]
- [[Graph schema v3 is the canonical data model]]
