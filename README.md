# design-grammar-system

This repo provides a Docker-based pipeline for:
- converting natural-language design rules into SWRL + atomic rule atoms with Ollama,
- generating a domain ontology from the same rules,
- storing the ontology and rules in Neo4j,
- querying the graph via a natural-language MCP workflow,
- visualizing and interacting through a lightweight graph viewer UI.

## Services and ports
- Neo4j 5 Community: http://localhost:7474 (Bolt 7687)
- n8n: http://localhost:5678
- Ollama: http://localhost:11435 (container 11434)
- data-service (FastAPI + MCP + execution tracking): http://localhost:8000
- graph-viewer (UI + reverse proxy): http://localhost:8080

## Quick start
1) Start containers:
```
docker compose up -d
docker compose ps
```

2) Ensure an Ollama model exists:
```
docker exec -it ollama ollama pull llama3.1
```
The workflows default to `llama3.1-dg:latest`. Either create that model (see `training/README.md`), override `ollama_model` per request, or change `OLLAMA_MODEL` in `docker-compose.yml`.

3) Import n8n workflows:
```
docker exec -it n8n n8n import:workflow --input=/files/workflows/rules-to-metagraph.json
docker exec -it n8n n8n import:workflow --input=/files/workflows/graph-query-mcp.json
```

4) Activate workflows in n8n:
```
http://localhost:5678
```
Login with the credentials in `docker-compose.yml`.

5) Open the graph viewer UI:
```
http://localhost:8080
```
Use "Ingest Rules" or "Request Grammar". The UI handles polling and shows responses and generated Cypher.

## Webhook APIs

### Auth
n8n Basic Auth is enabled by default. Use the same credentials as the n8n UI.

PowerShell helper:
```powershell
$user = "<n8n_user>"
$pass = "<n8n_password>"
$token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${user}:$pass"))
$headers = @{ Authorization = "Basic $token" }
```

### Rules ingest
Endpoint:
```
http://localhost:5678/webhook/dg/rules-ingest
```

Required:
- `rules_text`

Optional (defaults shown):
- `project_name` (`default-project`)
- `neo4j_user` (`neo4j`)
- `neo4j_password` (`12345678`)
- `neo4j_url` (`http://neo4j:7474`)
- `ollama_model` (`llama3.1-dg:latest`)
- `ollama_url` (`http://ollama:11434`)
- `ollama_keep_alive` (`30m`)
- `data_service_url` (`http://data-service:8000`)

Example:
```powershell
$body = @{
  rules_text = "grid size of urban block is between 12 and 48 m; maximum height of buildings in the block is 75 m; minimum hours of direct sunlight for each building is 2.8 hours per day; minimum dimension for each building is 12 m; site coverage ratio allowed range is between 0.45 and 0.60; minimum floor area of the building is 8000 square meters; all residential buildings must be at least 10 meters apart; commercial buildings must be at least 6 meters apart."
  project_name = "urban-block-case-study"
  ollama_model = "llama3.1"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:5678/webhook/dg/rules-ingest" `
  -Headers $headers -ContentType "application/json" -Body $body
```

### Graph query
Endpoint:
```
http://localhost:5678/webhook/dg/graph-query
```

Required:
- `prompt` (or `question`)

Optional:
- `project_name` (adds a project filter when provided)
- `ollama_model` (`llama3.1-dg:latest`)
- `ollama_url` (`http://ollama:11434`)
- `mcp_url` (`http://data-service:8000/mcp`)
- `data_service_url` (`http://data-service:8000`)

Example:
```powershell
$body = @{
  prompt = "What is the maximum height for buildings?"
  project_name = "urban-block-case-study"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:5678/webhook/dg/graph-query" `
  -Headers $headers -ContentType "application/json" -Body $body
```

## Async results (execution-result)
Both webhooks respond immediately with an acknowledgment:
```
{ "status": "accepted", "executionId": "<id>" }
```

Poll status via data-service:
- `GET http://localhost:8000/execution-result/<id>`
- `GET http://localhost:8000/execution-result/latest/rules-ingest`
- `GET http://localhost:8000/execution-result/latest/graph-query`

Example:
```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/execution-result/<id>"
```

## Neo4j validation
Open `http://localhost:7474` and run:
```
MATCH (r:Rule {graph:'Metagraph'}) RETURN r LIMIT 25;
MATCH (c:Class {graph:'OntoGraph'}) RETURN c LIMIT 25;
MATCH (r:Rule {graph:'Metagraph'})-[:HAS_BODY]->(a:Atom) RETURN r, a LIMIT 25;
MATCH (a:Atom)-[:ARG]->(v:Var) RETURN a, v LIMIT 25;
```
Login with `neo4j / 12345678` unless changed.

## Data model conventions
- Nodes:
  - OntoGraph: `Class`, `DatatypeProperty`, `ObjectProperty`
  - Metagraph: `Rule`, `Atom`, `Builtin`, `Var`, `Literal`
- Relationships:
  - `HAS_DATA_PROPERTY`, `HAS_OBJECT_PROPERTY`
  - `HAS_BODY` (property: `order`), `HAS_HEAD` (property: `order`)
  - `REFERS_TO`
  - `ARG` (property: `pos`)
- Key properties:
  - Class/DatatypeProperty/ObjectProperty: `iri`, `label`
  - Rule: `id`, `text` (SWRL expression), `kind` (violation)
  - Atom: `id`, `type` (ClassAtom|DataPropertyAtom|ObjectPropertyAtom|BuiltinAtom)
  - Var: `name` (e.g. `?b`), Literal: `lex`, `datatype`
- All nodes include `graph` (`OntoGraph` or `Metagraph`) and `project` (from `project_name`).

## Machine learning (LoRA) and training dataset
This repo includes a complete LoRA fine-tuning pipeline to create a custom Ollama model for rule parsing.

### Dataset
- Location: `training/training_dataset.json`
- Schema reference: `training/dataset_schema.json`
- Format: JSON Lines (one JSON object per line)
- Required fields: `prompt`, `cypher`

### Train (Docker + GPU)
From the repo root:
```powershell
$env:HF_TOKEN = "<your_hf_token>"
docker compose -f training/docker-compose.train.yml build
docker compose -f training/docker-compose.train.yml run --rm trainer
```
This runs `training/train_lora.py`, which reads `training/training_dataset.json` and writes the adapter to:
```
training/output/adapter
```

### Create an Ollama model from the adapter
```powershell
$env:HF_TOKEN = "<your_hf_token>"
\training\scripts\create_ollama_model.ps1 `
  -AdapterDir .\training\output\adapter `
  -BaseModel llama3.1 `
  -ModelName llama3.1-dg
```
Then verify:
```powershell
docker exec -it ollama ollama list
```

### Use the trained model
- Update `OLLAMA_MODEL` in `docker-compose.yml`, or
- Pass `ollama_model` in the webhook payloads.

See `training/README.md` for advanced options (4-bit, max samples, smoke tests).

## Troubleshooting
- n8n: `docker logs -f n8n`
- Ollama: `docker exec -it ollama ollama list`
- Neo4j: `docker logs -f neo4j`
- data-service: `docker logs -f data-service`

## Persistence
Named volumes:
- `neo4j_data` -> Neo4j database files
- `n8n_data` -> n8n SQLite, workflows, credentials
- `ollama` -> Ollama models

## Grasshopper add-in scaffold (DG)
A new folder `DG/` contains an initial implementation of the Design Grammars Grasshopper add-in:
- `DG/src/DG.Core` -> Neo4j connector, rule repository, SWRL parser, validator engine
- `DG/src/DG.Grasshopper` -> components: `CONNECTOR`, `METAGRAPH`, `RULE DECONSTRUCT`, `CLASSIFICATOR`, `VALIDATOR`
- `DG/tests/DG.Tests` -> parser/evaluator/classificator tests

Build and test:
```powershell
dotnet build .\DG\DG.sln
dotnet test .\DG\DG.sln
```
