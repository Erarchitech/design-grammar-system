# Architecture

## System Overview

Design Grammar System is a multi-component platform for encoding architectural design rules as SWRL (Semantic Web Rule Language) expressions, storing them in a Neo4j knowledge graph, and validating 3D building models against those rules. It spans from a desktop Grasshopper plugin through a web UI to a Dockerized backend pipeline.

## Architectural Pattern

**Distributed services with event-driven workflow orchestration**

- No monolith — each concern is a separate Docker service or desktop plugin
- n8n acts as the workflow orchestrator (LLM prompt building, Cypher execution, result routing)
- data-service acts as the integration hub (MCP endpoint, validation publishing, execution tracking)
- The SPA is a thin client that talks to Neo4j directly (for visualization) and to backend services via REST/webhooks

## Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Presentation Layer                                          │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ Design Grammars SPA  │  │ Grasshopper Plugin (Desktop)  │  │
│  │ (graph-viewer/)      │  │ (DG.Grasshopper/)            │  │
│  └─────────┬───────────┘  └──────────┬───────────────────┘  │
├─────────────┼────────────────────────┼───────────────────────┤
│  API Layer  │                        │                       │
│  ┌──────────▼──────────┐  ┌─────────▼────────────────────┐  │
│  │ Nginx Reverse Proxy  │  │ data-service (FastAPI)       │  │
│  │ /neo4j  /n8n  /ds   │  │ MCP + Validation + Tracking  │  │
│  └──────────┬──────────┘  └──────────┬───────────────────┘  │
├─────────────┼────────────────────────┼───────────────────────┤
│  Workflow Layer                      │                       │
│  ┌──────────▼──────────┐             │                       │
│  │ n8n Workflows        │             │                       │
│  │ rule-ingest + query  │◄────────────┘                      │
│  └──────────┬──────────┘                                     │
├─────────────┼────────────────────────────────────────────────┤
│  LLM Layer  │                                                │
│  ┌──────────▼──────────┐                                     │
│  │ Ollama (llama3.1)    │                                     │
│  │ Prompt-constrained   │                                     │
│  └─────────────────────┘                                     │
├──────────────────────────────────────────────────────────────┤
│  Data Layer                                                   │
│  ┌────────────────┐  ┌──────────────────────────────────┐    │
│  │ Neo4j 5         │  │ Speckle Server (Postgres+Redis   │    │
│  │ OntoGraph       │  │   +MinIO) — 3D model storage     │    │
│  │ Metagraph       │  │                                  │    │
│  │ ValidationGraph │  └──────────────────────────────────┘    │
│  └────────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### Rule Ingestion
1. User types natural-language rule in SPA graph viewer
2. SPA POSTs to `/n8n/webhook/dg/rules-ingest` with `{ rule, project }`
3. n8n "Build LLM Prompt" node constructs prompt with v3 schema constraints + few-shot example
4. Ollama generates Cypher MERGE statements
5. n8n validates and executes Cypher against Neo4j
6. n8n POSTs execution result to `data-service /execution-result`
7. SPA polls `/execution-result` and refreshes NeoVis visualization

### Graph Query
1. User types natural-language question in SPA query panel
2. SPA POSTs to `/n8n/webhook/dg/graph-query` with `{ question, project }`
3. n8n fetches live schema from data-service MCP and builds query prompt
4. Ollama generates read-only Cypher
5. n8n executes Cypher, formats answer
6. Response returned to SPA

### Validation (Grasshopper → Speckle)
1. `CONNECTOR` component establishes Neo4j connection
2. `METAGRAPH` component fetches rules from Neo4j for the project
3. `CLASSIFICATOR` component maps Grasshopper geometry values to SWRL variables
4. `VALIDATOR` component evaluates rules against bindings using `RuleEvaluator`
5. If `SendRules=true`, `VALIDATOR` POSTs results to `data-service /validation/publish`
6. data-service publishes geometry + results to Speckle via `specklepy`
7. model-viewer loads Speckle overlay for 3D visualization

## Key Abstractions

### Graph Model (v3 Schema)
- **OntoGraph**: Domain ontology — `Class`, `DatatypeProperty`, `ObjectProperty` nodes
- **Metagraph**: Rule logic — `Rule`, `Atom`, `Builtin`, `Var`, `Literal` nodes
- **ValidationGraph**: Validation runs — `ValidationRun`, `ValidationEntity`, `IntegrationConfig` nodes
- **Relationships**: `HAS_BODY`, `HAS_HEAD`, `REFERS_TO`, `ARG`
- **Project isolation**: Every node has `project` property; queries always filter by project

### SWRL Rule Representation
Rules stored as a graph substructure: `Rule` → `HAS_BODY`/`HAS_HEAD` → `Atom` → `ARG` → `Var`/`Literal`, `REFERS_TO` → `Class`/`DatatypeProperty`/`Builtin`

### LLM Constraint Strategy
No fine-tuned model required. Cypher generation is constrained at inference time via structured prompts embedding v3 schema rules and few-shot examples. Source of truth: `cypher_template.txt`.

## Entry Points

| Entry Point | File | Purpose |
|---|---|---|
| Web SPA | `graph-viewer/index.html` | All UI: register, projects, graph viewer |
| Model Viewer | `graph-viewer/model-viewer/src/App.jsx` | Speckle 3D viewer (separate React app) |
| FastAPI server | `data-service/app.py` | MCP, validation, execution tracking |
| n8n rule ingest | `n8n/workflows/rules-to-metagraph.json` | NL → Cypher workflow |
| n8n graph query | `n8n/workflows/graph-query-mcp.json` | NL → read-only Cypher workflow |
| Grasshopper plugin | `DG/src/DG.Grasshopper/Components/*.cs` | 5 Grasshopper components |
| Docker orchestration | `docker-compose.yml` | All service definitions |
