---
tags: [atlas, data-service, fastapi, mcp, python]
date: 2026-04-05
---

# Data-Service is a FastAPI MCP Bridge to Neo4j and Speckle

Located in `data-service/app.py`, this Python service provides the MCP protocol endpoint, execution tracking for n8n workflows, Speckle validation publishing, and settings management.

## Endpoints

### Core
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/mcp` | POST | MCP JSON-RPC (tools/list, tools/call) |

### MCP Tools (via `/mcp`)
- `neo4j_schema` — returns labels, relationship_types, property_keys, graphs, projects
- `neo4j_query` — executes read-only Cypher (write queries rejected)

### Execution Tracking
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/execution-result` | POST | Store workflow execution status |
| `/execution-result/{id}` | GET | Retrieve execution status |
| `/execution-result/latest/{workflow}` | GET | Latest status for workflow |

### Speckle Settings
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/settings/speckle` | GET | Get Speckle connection settings (tokens masked) |
| `/settings/speckle` | PUT | Update Speckle settings |

### Speckle Integration Config (per project)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/integration/speckle/project/{project}` | GET | Get project's Speckle config |
| `/integration/speckle/project/{project}` | PUT | Save project's Speckle config |

### Validation
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/validation/publish` | POST | Publish validation to Speckle + store metadata |
| `/validation/runs/{project}` | GET | List all validation runs |
| `/validation/run/{project}/{run_id}` | DELETE | Delete a validation run |
| `/validation/view/{project}` | GET | Latest validation view |
| `/validation/view/{project}/{run_id}` | GET | Specific run view |
| `/validation/view/{project}/{run_id}/{rule_id}` | GET | Rule-filtered entity sets |

## Speckle Settings Fallback Chain

1. Environment variables (`SPECKLE_BASE_URL`, `SPECKLE_WRITE_TOKEN`, `SPECKLE_READ_TOKEN`)
2. Persisted JSON file (`/app/data/speckle-settings.json`)
3. Defaults (`http://localhost:8090`, empty tokens)

## Dependencies

`fastapi`, `uvicorn`, `neo4j`, `specklepy`, `pydantic`

## Related

- [[FastAPI data-service bridges MCP Neo4j and Speckle]]
- [[Speckle hosts 3D BIM models for validation overlay]]
- [[Pydantic models validate all API boundaries]]
