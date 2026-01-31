# Copilot Instructions for design-grammar-system

## Overview
This project orchestrates a pipeline for parsing architectural design rules into SWRL and atomic rule atoms, generating a custom ontology, and storing both in Neo4j using Dockerized services and an n8n workflow. The system leverages LLMs (via Ollama) for rule parsing and supports end-to-end automation from text input to graph database population.


## Architecture
- **Neo4j**: Stores ontology (graph = "OntoGraph") and rules/atoms (graph = "Metagraph") in a single database, separated by the `graph` property.
- **n8n**: Hosts the main workflow (`n8n/workflows/rules-to-metagraph.json`) that ingests rules, builds LLM prompts, parses LLM output, and upserts data into Neo4j.
- **Ollama**: Provides LLM inference for rule-to-ontology conversion. Exposed on port 11435 (container 11434).
- **data-service**: FastAPI app for simple Neo4j operations (see `data-service/app.py`).
- **graph-viewer**: React + Neovis.js web UI for graph visualization and rule submission (served via nginx on port 8080).
- **Docker Compose**: Orchestrates all services. See `docker-compose.yml` for service definitions, ports, and environment variables.

## Key Workflows
- **Start all services**: `docker compose up -d`
- **Pull Ollama model**: `docker exec -it ollama ollama pull llama3.1`
- **Import n8n workflow**: `docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json`
- **Activate workflow**: Use n8n UI at http://localhost:5678 (credentials in `docker-compose.yml`).
- **Trigger workflow**: POST to `http://localhost:5678/webhook/dg/rules-ingest` with JSON body (see README for example).
- **Open graph viewer**: http://localhost:8080 (includes rules prompt, progress bar, and graph reload).
- **Inspect Neo4j**: http://localhost:7474 (neo4j/12345678). Use Cypher queries from README.

## Project Conventions
- **Graph separation**: Use `graph` property (`OntoGraph`, `Metagraph`) to distinguish ontology and rules in Neo4j.
- **Project scoping**: All nodes include a `project` property (from input `project_name`).
- **LLM prompt schema**: See n8n workflow for the exact JSON schema expected from LLM output.
- **Validation types**: Rules are tagged as `geometric`, `semantic`, or `topological`.
- **n8n workflow**: All environment/config values are set via workflow node defaults or Docker env vars.
- **Graph viewer proxies**: Nginx proxies `/neo4j/` to Neo4j HTTP and `/n8n/` to n8n. The web UI uses these paths to avoid CORS.
- **Graph viewer filtering**: UI toggles OntoGraph vs MetaGraph; queries filter by `graph` property to show only the selected dataset.

## Integration Points
- **n8n <-> Ollama**: HTTP POST to `/api/generate` with prompt and model.
- **n8n <-> Neo4j**: HTTP POST to `/db/neo4j/tx/commit` with Cypher statements for upserts.
- **data-service**: Exposes `/create_node/` for simple node creation (not used in main workflow, but available for extensions).
- **graph-viewer <-> n8n**: POST to `/n8n/webhook/dg/rules-ingest` (Basic Auth enabled by default).
- **graph-viewer <-> Neo4j**: Uses Bolt for visualization and `/neo4j/db/neo4j/tx/commit` for property fetch.

## Troubleshooting
- **n8n logs**: `docker logs -f n8n`
- **Ollama models**: `docker exec -it ollama ollama list`
- **Neo4j health**: `docker logs -f neo4j`

## Key Files
- `docker-compose.yml`: Service orchestration, ports, credentials
- `n8n/workflows/rules-to-metagraph.json`: Main workflow logic
- `data-service/app.py`: FastAPI service for Neo4j
- `graph-viewer/index.html`: UI (rules prompt, progress, graph, node/edge details)
- `graph-viewer/nginx.conf`: Proxy routes for `/neo4j` and `/n8n`
- `graph-viewer/config.template.js`: Viewer configuration injected at startup (Neo4j, n8n, labels, styling)
- `README.md`: End-to-end usage, test, and troubleshooting

## Examples
- **Webhook request**: See README for full JSON example
- **Cypher queries**: See README for ontology/rule/atom inspection

---
For any unclear or missing conventions, review the README and n8n workflow JSON for up-to-date patterns and integration details.
