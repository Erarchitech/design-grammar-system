# design-grammar-system

This repo provides a Docker-based environment plus an n8n workflow that:
- parses text design rules into SWRL + atomic rule atoms using Ollama,
- derives a custom ontology from the same rules,
- writes ontology to nodes tagged with `graph = "OntoGraph"`,
- writes rules + atoms to nodes tagged with `graph = "Metagraph"`.

## Services
- Neo4j 5 Community (single database, graphs separated by `graph` property)
- n8n
- Ollama
- data-service (existing FastAPI service)
- graph-viewer (React + Neovis.js)

## Start
1) Start containers:
```
docker compose up -d
```

2) Pull an Ollama model inside the container (example):
```
docker exec -it ollama ollama pull llama3.1
```
Note: the Ollama container is exposed on host port `11435` to avoid clashing with Ollama Desktop (`11434`).

3) Confirm services are up:
```
docker compose ps
```

4) Open n8n UI:
```
http://localhost:5678
```
Login with the credentials in `docker-compose.yml`.

## Import the workflow
The workflow JSON is stored at:
`n8n/workflows/rules-to-metagraph.json`

Import via CLI:
```
docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json
```
Or import from the n8n UI (Workflow > Import).

Activate the workflow to enable the production webhook.

## Webhook request
Endpoint (after activation):
```
http://localhost:5678/webhook/dg/rules-ingest
```

Request body example:
```json
{
  "rules_text": "grid size of urban block is between 12 and 48 m; maximum height of buildings in the block is 75 m; minimum hours of direct sunlight for each building is 2.8 hours per day; minimum dimension for each building is 12 m; site coverage ratio allowed range is between 0.45 and 0.60; minimum floor area of the building is 8000 square meters; all residential buildings must be at least 10 meters apart; commercial buildings must be at least 6 meters apart.",
  "neo4j_user": "neo4j",
  "neo4j_password": "12345678",
  "project_name": "urban-block-case-study",
  "ollama_model": "llama3.1"
}
```

## End-to-end test (step-by-step)
1) Import the workflow (UI or CLI) and activate it.

2) Send a test request from PowerShell:
```
$body = @{
  rules_text = "grid size of urban block is between 12 and 48 m; maximum height of buildings in the block is 75 m; minimum hours of direct sunlight for each building is 2.8 hours per day; minimum dimension for each building is 12 m; site coverage ratio allowed range is between 0.45 and 0.60; minimum floor area of the building is 8000 square meters; all residential buildings must be at least 10 meters apart; commercial buildings must be at least 6 meters apart."
  neo4j_user = "neo4j"
  neo4j_password = "12345678"
  project_name = "urban-block-case-study"
  ollama_model = "llama3.1"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:5678/webhook/dg/rules-ingest" -ContentType "application/json" -Body $body
```

Expected response includes counts for rules/atoms/classes and confirms write to `neo4j` with graphs `OntoGraph` and `Metagraph`.

3) Verify data in Neo4j Browser:
```
http://localhost:7474
```
Login with `neo4j / 12345678`.

Useful queries:
```
MATCH (r:Rule {graph:'Metagraph'}) RETURN r LIMIT 25;
MATCH (c:Class {graph:'OntoGraph'}) RETURN c LIMIT 25;
MATCH (r:Rule {graph:'Metagraph'})-[:HAS_ATOM]->(a:Atom) RETURN r, a LIMIT 25;
```

## Test the framework (clear checklist)
Use this section as a practical validation checklist after the containers are running.

### A) Verify containers and ports
1) Check all containers are up:
```
docker compose ps
```
You should see `neo4j`, `n8n`, `ollama`, and `data-service` in `running`.

2) Confirm ports:
- n8n UI: `http://localhost:5678`
- Neo4j Browser: `http://localhost:7474`
- Ollama (host): `http://localhost:11435`
- Graph Viewer: `http://localhost:8080`

### B) Verify Ollama is ready
1) List models:
```
docker exec -it ollama ollama list
```
2) Pull a model if missing (example):
```
docker exec -it ollama ollama pull llama3.1
```

### C) Verify n8n workflow is loaded
1) Import the workflow from `n8n/workflows/rules-to-metagraph.json`.
2) Activate the workflow.
3) Confirm the production webhook URL is visible in n8n.

### D) Run a full rule ingestion test
Send a request:
```
$body = @{
  rules_text = "grid size of urban block is between 12 and 48 m; maximum height of buildings in the block is 75 m; minimum hours of direct sunlight for each building is 2.8 hours per day; minimum dimension for each building is 12 m; site coverage ratio allowed range is between 0.45 and 0.60; minimum floor area of the building is 8000 square meters; all residential buildings must be at least 10 meters apart; commercial buildings must be at least 6 meters apart."
  neo4j_user = "neo4j"
  neo4j_password = "12345678"
  project_name = "urban-block-case-study"
  ollama_model = "llama3.1"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:5678/webhook/dg/rules-ingest" -ContentType "application/json" -Body $body
```
Expected: JSON response with counts for rules/atoms/classes.

### E) Validate data in Neo4j
Open `http://localhost:7474` and run:
```
MATCH (r:Rule {graph:'Metagraph'}) RETURN r LIMIT 10;
MATCH (c:Class {graph:'OntoGraph'}) RETURN c LIMIT 10;
MATCH (r:Rule {graph:'Metagraph'})-[:HAS_ATOM]->(a:Atom) RETURN r, a LIMIT 10;
```

### F) Common failure points
- Ollama timeout: check `docker logs -f ollama`
- n8n errors: check `docker logs -f n8n`
- Neo4j auth: verify `neo4j / 12345678`

## Troubleshooting
- If the webhook errors, check n8n logs:
```
docker logs -f n8n
```
- If Ollama does not respond, confirm the model exists:
```
docker exec -it ollama ollama list
```
- If Neo4j rejects the query, confirm credentials and that `neo4j` is healthy:
```
docker logs -f neo4j
```

## Notes
- Neo4j Community only supports a single database (`neo4j`). The workflow stores ontology and rules in the same DB and separates them by the `graph` property (`OntoGraph`, `Metagraph`).
- You can edit the ontology and rules manually later in Neo4j Browser or by Cypher.
- Validation types are tagged as `geometric`, `semantic`, or `topological` per rule.

## Persistence
All services run locally in dedicated Docker containers with data stored in named Docker volumes:
- `neo4j_data` → Neo4j database files
- `n8n_data` → n8n SQLite + workflows/credentials
- `ollama` → Ollama models
