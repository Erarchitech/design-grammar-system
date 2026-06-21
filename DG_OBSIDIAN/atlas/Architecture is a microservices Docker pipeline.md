---
tags: [atlas, architecture, docker]
date: 2026-04-05
graphify_communities: ["Concern: Tight Coupling to Neo4j", "Docker Compose Orchestration", "State Projection for Validation Runs"]
---

# Architecture is a Microservices Docker Pipeline

The Design Grammar System uses a **Docker Compose** orchestration of 12+ services that form a pipeline: natural-language rules → LLM parsing → SWRL atoms → Neo4j graph → 3D validation overlay.

## Service Map

| Service | Image | Port | Role |
|---------|-------|------|------|
| `neo4j` | `neo4j:5` | 7474/7687 | Graph database (single DB, project-isolated) |
| `data-service` | FastAPI (custom) | 8000 | MCP bridge, validation publish, execution tracking |
| `n8n` | `n8nio/n8n` | 5678 | Workflow orchestrator (2 webhook workflows) |
| `ollama` | `ollama/ollama` | 11435→11434 | Local LLM inference (GPU, llama3.1) |
| `design-grammars` | Nginx (custom) | 8080 | SPA UI + reverse proxy |
| `speckle-*` | Speckle stack | 8090 | Self-hosted 3D model platform (7 containers) |

## Data Flow

```
User (browser)
  → design-grammars (nginx SPA)
    → /n8n/webhook/dg/rules-ingest  →  n8n  →  ollama  →  neo4j
    → /n8n/webhook/dg/graph-query   →  n8n  →  ollama  →  data-service/mcp  →  neo4j
    → /data-service/validation/...  →  data-service  →  speckle
    → /neo4j/db/neo4j/tx/commit     →  neo4j (direct Cypher)
```

## Key Architectural Traits

- **No message queue** — synchronous HTTP between services with [[Async polling pattern for n8n workflow execution tracking|async polling]] for long-running LLM calls
- **Single Neo4j database** — project isolation via `project` property, not separate DBs. See [[Project isolation uses property filtering not separate databases]]
- **GPU-enabled LLM** — Ollama with NVIDIA GPU reservation for inference
- **Self-hosted Speckle** — full Speckle stack (server, frontend, postgres, redis, minio, preview, webhooks, fileimport, ingress)

## Related

- [[Deployment uses Docker Compose with nginx reverse proxy]]
- [[Technology stack spans C-Sharp Grasshopper and Python FastAPI and React SPA]]
- [[Neo4j stores ontology and metagraph in a single database]]

<!-- graphify:connections:start -->
## Graph connections

- [[graphify/communities/Concern Tight Coupling to Neo4j|Concern: Tight Coupling to Neo4j]]
- [[graphify/communities/Docker Compose Orchestration|Docker Compose Orchestration]]
- [[graphify/communities/State Projection for Validation Runs|State Projection for Validation Runs]]
<!-- graphify:connections:end -->
