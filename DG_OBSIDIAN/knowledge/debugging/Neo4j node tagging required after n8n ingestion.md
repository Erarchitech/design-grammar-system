---
tags: [debugging, neo4j, n8n, ingestion]
date: 2026-04-05
---

# Neo4j Node Tagging Required After n8n Ingestion

## Problem

After n8n ingests rules, some nodes may have `project IS NULL` or `project = 'default-project'` instead of the actual project name.

## Root Cause

The n8n workflow's "Set Input Defaults" node reads `$json.project` from the webhook body and falls back to `'default-project'`. If the LLM-generated Cypher doesn't include the correct project name in MERGE statements, or if the project parameter isn't propagated correctly, nodes get orphaned.

## Solution

1. **Post-ingest tagging** — `tagProjectNodes()` in the UI runs after ingestion completes:
   ```cypher
   MATCH (n) WHERE n.project IS NULL OR n.project = 'default-project'
   SET n.project = '<actual_project_name>'
   ```

2. **Annotate Graph Props** — n8n post-processing step sets `graph` and `project` on orphaned nodes:
   ```cypher
   MATCH (n) WHERE (n:Class OR ...) AND n.graph IS NULL
   SET n.graph = 'OntoGraph', n.project = $project
   ```

## Prevention

- Always include project name in webhook body
- Verify n8n "Set Input Defaults" properly parses `$json.project`
- Check LLM-generated Cypher includes `project` property in all MERGE/SET statements

## Related

- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[Project isolation uses property filtering not separate databases]]
