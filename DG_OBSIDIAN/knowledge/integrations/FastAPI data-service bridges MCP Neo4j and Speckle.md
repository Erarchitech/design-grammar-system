---
tags: [integration, data-service, fastapi, mcp]
date: 2026-04-05
---

# FastAPI Data-Service Bridges MCP Neo4j and Speckle

## Role

The data-service (`data-service/app.py`) sits between all other services:
- **n8n → data-service** for execution tracking and MCP tool calls
- **UI → data-service** for validation views, Speckle config, settings
- **Grasshopper → data-service** for validation publishing
- **data-service → Neo4j** for graph reads/writes
- **data-service → Speckle** for 3D model operations

## MCP Protocol

The `/mcp` endpoint implements a subset of Model Context Protocol (JSON-RPC):
- `initialize` — handshake
- `tools/list` — returns available tools
- `tools/call` — execute a tool

### Available MCP Tools

| Tool | Purpose | Used By |
|------|---------|---------|
| `neo4j_schema` | Return live schema (labels, rels, props) | n8n query workflow |
| `neo4j_query` | Execute read-only Cypher | n8n query workflow |

Write queries are rejected with an error response.

## Execution Tracking

In-memory dictionaries `EXECUTION_RESULTS` and `WORKFLOW_STATUS` track n8n workflow progress:
- n8n POSTs status updates at each step
- UI polls for completion

## Validation Node Storage

`ValidationRun` and `ValidationEntity` nodes stored in Neo4j with `graph='ValidationGraph'`:
- Tracks run metadata, Speckle version IDs, rule/entity counts
- Supports per-entity, per-rule pass/fail queries

## Related

- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[Speckle hosts 3D BIM models for validation overlay]]
