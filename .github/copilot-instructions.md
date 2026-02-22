# Copilot Instructions for design-grammar-system

## Overview
This repo orchestrates a Dockerized pipeline for parsing architectural design rules into SWRL + atomic rule atoms, generating a custom ontology, and storing both in Neo4j. It also includes a graph-query workflow (MCP) that turns natural-language questions into read-only Cypher and returns a short answer. A lightweight graph-viewer UI provides ingest, query, and visualization.

## Architecture
- **Neo4j**: Single database. Ontology and rules are separated by `graph` property values `OntoGraph` and `Metagraph`.
- **n8n**: Two workflows:
  - `n8n/workflows/rules-to-metagraph.json` (`/webhook/dg/rules-ingest`)
  - `n8n/workflows/graph-query-mcp.json` (`/webhook/dg/graph-query`)
- **Ollama**: LLM inference. Default model `llama3.1-dg:latest` (container port 11434, host 11435).
- **data-service**: FastAPI for MCP (`/mcp`) plus in-memory execution tracking (`/execution-result`). MCP tools: `neo4j_schema` and read-only `neo4j_query`.
- **graph-viewer**: Static UI + Nginx proxy for `/neo4j`, `/n8n`, `/data-service` to avoid CORS. Runtime config is generated from environment variables in `graph-viewer/entrypoint.sh`.
- **Docker Compose**: Service orchestration. See `docker-compose.yml` for ports, credentials, and defaults.

## Key workflows
- Start services: `docker compose up -d`
- Import workflows:
  - `docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json`
  - `docker exec -it n8n n8n import:workflow --input=/files/workflows/graph-query-mcp.json`
- Activate workflows via n8n UI at `http://localhost:5678`
- Webhooks require Basic Auth by default (same credentials as n8n UI)
- Webhook responses are asynchronous; poll `data-service` `/execution-result` for status

## Webhook payloads (defaults)
### Rules ingest (`/webhook/dg/rules-ingest`)
- Required: `rules_text`
- Optional defaults:
  - `project_name`: `default-project`
  - `neo4j_user`: `neo4j`
  - `neo4j_password`: `12345678`
  - `neo4j_url`: `http://neo4j:7474`
  - `ollama_model`: `llama3.1-dg:latest`
  - `ollama_url`: `http://ollama:11434`
  - `ollama_keep_alive`: `30m`
  - `data_service_url`: `http://data-service:8000`

### Graph query (`/webhook/dg/graph-query`)
- Required: `prompt` (or `question`)
- Optional defaults:
  - `project_name`: none (adds a project filter when provided)
  - `ollama_model`: `llama3.1-dg:latest`
  - `ollama_url`: `http://ollama:11434`
  - `mcp_url`: `http://data-service:8000/mcp`
  - `data_service_url`: `http://data-service:8000`

## Data model conventions
- Graph separation: `graph` property is always `OntoGraph` or `Metagraph`.
- Project scoping: all nodes include `project` (from `project_name`).
- Nodes:
  - OntoGraph: `Class`, `DatatypeProperty`, `ObjectProperty`
  - Metagraph: `Rule`, `Atom`, `Builtin`, `Var`, `Literal`
- Relationships:
  - `HAS_DATA_PROPERTY`, `HAS_OBJECT_PROPERTY`
  - `HAS_BODY` (property `order`), `HAS_HEAD` (property `order`)
  - `REFERS_TO`
  - `ARG` (property `pos`)
- Rule properties include: `id`, `text` (SWRL expression), `kind` (violation).
- Atom properties include: `id`, `type` (ClassAtom|DataPropertyAtom|ObjectPropertyAtom|BuiltinAtom).
- Var properties: `name` (e.g. `?b`). Literal properties: `lex`, `datatype`.
- Ontology node properties: `iri`, `label`, `range` (for DatatypeProperty/ObjectProperty).

## Integration points
- **n8n -> Ollama**: HTTP POST `/api/generate` (raw text for Cypher generation, JSON format for query workflow).
- **n8n -> Neo4j**: HTTP POST `/db/neo4j/tx/commit` with Basic Auth (from payload defaults).
- **n8n -> data-service**: POST `/execution-result` for progress and completion.
- **graph-viewer -> n8n**: POST `/n8n/webhook/dg/rules-ingest` and `/n8n/webhook/dg/graph-query` (Basic Auth).
- **graph-viewer -> data-service**: Polls `/data-service/execution-result/...`.
- **graph-viewer -> Neo4j**: Bolt for visualization and HTTP for property queries.

## Training (LoRA) and dataset
- Dataset lives at `training/training_dataset.json` (JSON Lines, required fields: `prompt`, `cypher`).
- Schema reference: `training/dataset_schema.json`.
- Training entrypoint: `training/train_lora.py` (runs via `training/docker-compose.train.yml`).
- Output adapter: `training/output/adapter` (used to create an Ollama model).
- Model creation script: `training/scripts/create_ollama_model.ps1` (creates `llama3.1-dg` in Ollama).
- The workflows use `ollama_model` (`llama3.1-dg:latest` by default); override in payload or `docker-compose.yml`.

## Key files
- `docker-compose.yml`: Service orchestration, ports, credentials
- `n8n/workflows/rules-to-metagraph.json`: Rules ingest workflow
- `n8n/workflows/graph-query-mcp.json`: Graph query workflow
- `data-service/app.py`: MCP tools + execution-result storage
- `graph-viewer/index.html`: UI (ingest, query, visualization)
- `graph-viewer/nginx.conf`: Proxy routes for `/neo4j`, `/n8n`, `/data-service`
- `graph-viewer/config.template.js`: Viewer config injected at startup
- `graph-viewer/entrypoint.sh`: Generates runtime `config.js`
- `training/README.md`: LoRA training steps
- `README.md`: End-to-end usage and troubleshooting

---
When unsure, verify behavior in `n8n/workflows/*.json` and `graph-viewer/index.html` before changing code.
