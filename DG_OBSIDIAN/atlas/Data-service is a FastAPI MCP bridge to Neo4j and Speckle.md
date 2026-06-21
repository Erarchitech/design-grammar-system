---
tags: [atlas, data-service, fastapi, mcp, python]
date: 2026-04-05
graphify_communities: ["Concern: Tight Coupling to Neo4j", "Create full-text index and parent class hub nodes for Kno...", "Match Step (Neo4j Full-Text Search, No LLM)", "Model Viewer (graph-viewer/model-viewer/)", "Neo4jConnectorService", "Neo4jRuleRepository.cs", "Ontology v5 DCM ComputationGraph", "Phase 3: n8n Knowledge Workflows + LLM Ingest/Query", "Remove all test notes from Neo4j.", "Return an HTTPException with a structured JSON detail bod...", "SpeckleProjectConfigPayload", "SpeckleSettingsPayload", "Validation Endpoints (publish/runs/view)", "Validation Endpoints (publish/runs/view)", "Validation Results Publish to Speckle as Overlay Versions", "Validation Viewer API", "ValidationGeometryPayload", "n8n Workflow Orchestrator for LLM Rule Ingestion and Queries"]
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

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Concern Tight Coupling to Neo4j|Concern: Tight Coupling to Neo4j]]
- [[graphify/communities/Create full-text index and parent class hub nodes for Kno...|Create full-text index and parent class hub nodes for Kno...]]
- [[graphify/communities/Match Step (Neo4j Full-Text Search, No LLM)|Match Step (Neo4j Full-Text Search, No LLM)]]
- [[graphify/communities/Model Viewer (graph-viewermodel-viewer)|Model Viewer (graph-viewer/model-viewer/)]]
- [[graphify/communities/Neo4jConnectorService|Neo4jConnectorService]]
- [[graphify/communities/Neo4jRuleRepository.cs|Neo4jRuleRepository.cs]]
- [[graphify/communities/Ontology v5 DCM ComputationGraph|Ontology v5 DCM ComputationGraph]]
- [[graphify/communities/Phase 3 n8n Knowledge Workflows + LLM IngestQuery|Phase 3: n8n Knowledge Workflows + LLM Ingest/Query]]
- [[graphify/communities/Remove all test notes from Neo4j.|Remove all test notes from Neo4j.]]
- [[graphify/communities/Return an HTTPException with a structured JSON detail bod...|Return an HTTPException with a structured JSON detail bod...]]
- [[graphify/communities/SpeckleProjectConfigPayload|SpeckleProjectConfigPayload]]
- [[graphify/communities/SpeckleSettingsPayload|SpeckleSettingsPayload]]
- [[graphify/communities/Validation Endpoints (publishrunsview) (51)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/Validation Endpoints (publishrunsview)|Validation Endpoints (publish/runs/view)]]
- [[graphify/communities/Validation Results Publish to Speckle as Overlay Versions|Validation Results Publish to Speckle as Overlay Versions]]
- [[graphify/communities/Validation Viewer API|Validation Viewer API]]
- [[graphify/communities/ValidationGeometryPayload|ValidationGeometryPayload]]
- [[graphify/communities/n8n Workflow Orchestrator for LLM Rule Ingestion and Queries|n8n Workflow Orchestrator for LLM Rule Ingestion and Queries]]
<!-- graphify:connections:end -->
