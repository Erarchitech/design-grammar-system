# Architecture

## Overview

Design Grammar System is a **microservices Docker pipeline** of 12+ containers orchestrated via Docker Compose. Services communicate over synchronous HTTP with async polling for long-running LLM calls. There is no message queue.

## Service Map

| Service | Image | Internal Port | External Port | Role |
|---------|-------|--------------|---------------|------|
| `design-grammars` | Nginx (custom) | 80 | 8080 | SPA UI + reverse proxy |
| `neo4j` | `neo4j:5` | 7474, 7687 | 7474, 7687 | Graph database |
| `data-service` | FastAPI (custom) | 8000 | 8000 | MCP bridge, validation, execution tracking |
| `n8n` | `n8nio/n8n` | 5678 | 5678 | Workflow orchestrator (2 webhooks) |
| `ollama` | `ollama/ollama` | 11434 | 11435 | Local LLM inference (GPU, llama3.1) |
| `speckle-server` | Speckle | — | 8090 (via ingress) | 3D model platform |
| `speckle-frontend` | Speckle | — | — | Speckle web UI |
| `speckle-postgres` | PostgreSQL | 5432 | — | Speckle metadata |
| `speckle-redis` | Redis | 6379 | — | Speckle cache |
| `speckle-minio` | MinIO | 9000/9001 | 9000/9001 | Speckle object storage |
| `speckle-preview` | Speckle | — | — | 3D preview generation |
| `speckle-webhooks` | Speckle | — | — | Webhook processing |
| `speckle-fileimport` | Speckle | — | — | File import service |

## Data Flow

### Rule Ingestion
```
Browser → POST /n8n/webhook/dg/rules-ingest {rules_text, project}
  → n8n: parse NL → build LLM prompt → Ollama generate → validate Cypher
  → n8n: execute Cypher → Neo4j (MERGE nodes/rels)
  → n8n: annotate graph props → store execution result → respond 200
```

### Graph Query
```
Browser → POST /n8n/webhook/dg/graph-query {prompt, project}
  → n8n: fetch schema (via MCP) → build Cypher prompt → Ollama generate
  → n8n: validate + run Cypher (via MCP, read-only) → Ollama summarize
  → n8n: store execution result → respond with answer
```

### Validation Publish (from Grasshopper)
```
Grasshopper VALIDATOR component
  → HTTP POST /data-service/validation/publish {package JSON}
  → data-service: create Speckle version → store metadata in Neo4j
  → Model Viewer: fetch validation manifest → load 3D overlay
```

### Direct Graph Operations
```
Browser → POST /neo4j/db/neo4j/tx/commit {statements}
  → Neo4j HTTP API (proxied by nginx)
```

## Nginx Reverse Proxy

All external traffic enters via the `design-grammars` container on port 8080. Nginx routes:

| URL Path | Upstream | Purpose |
|----------|----------|---------|
| `/` | Static files | Main SPA |
| `/model-viewer/` | Static files | Vite-built 3D viewer |
| `/neo4j/*` | `http://neo4j:7474` | Neo4j HTTP API |
| `/data-service/*` | `http://data-service:8000` | FastAPI service |
| `/n8n/*` | `http://n8n:5678` | n8n webhooks |

## Key Architectural Traits

- **No message queue** — all inter-service communication is HTTP
- **Single Neo4j database** — project isolation via `project` property filter
- **GPU-enabled LLM** — Ollama with NVIDIA GPU reservation
- **Self-hosted Speckle** — full stack (7 containers) for 3D model hosting
- **Config injection** — `entrypoint.sh` uses `sed` to replace env var placeholders in `config.template.js`
- **Async polling** — UI polls `/execution-result/{id}` after triggering n8n webhooks
