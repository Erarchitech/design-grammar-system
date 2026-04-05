# External Integrations

## Neo4j (Graph Database)

- **Protocol:** Bolt (`bolt://neo4j:7687` inter-container, `bolt://localhost:7687` from host)
- **HTTP:** Port 7474, proxied via Nginx at `/neo4j/`
- **Auth:** `neo4j/12345678` (hardcoded across all consumers)
- **Single database**, project isolation via `project` property on every node
- **Graph separation:** `graph='OntoGraph'` for ontology terms, `graph='Metagraph'` for rules/atoms, `graph='ValidationGraph'` for validation runs

### Consumers
| Consumer | Driver | Access Pattern |
|---|---|---|
| `data-service/app.py` | `neo4j` Python driver | Direct Bolt — CRUD for validation runs, integration configs, MCP schema/query |
| `graph-viewer/index.html` | NeoVis.js + Neo4j HTTP | Visualization queries via Neo4j HTTP API (`/neo4j/`), Cypher filtered by `project` |
| `DG.Core` (C#) | `Neo4j.Driver 5.28.2` | Query rules + atoms from Metagraph, connection testing |
| `n8n` workflows | n8n Neo4j node | Execute LLM-generated Cypher to create/update rules |

## n8n (Workflow Automation)

- **Image:** `n8nio/n8n`, port 5678
- **Proxied** at `/n8n/` by Nginx in the `design-grammars` container
- **Auth:** Basic auth (`N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`)

### Workflows
| Workflow | Webhook | Purpose |
|---|---|---|
| `rules-to-metagraph.json` | `/webhook/dg/rules-ingest` | NL rule → LLM prompt → Cypher → Neo4j MERGE |
| `graph-query-mcp.json` | `/webhook/dg/graph-query` | NL question → LLM → read-only Cypher → answer |

### Flow
1. UI sends POST to webhook with `{ rule, project }` or `{ question, project }`
2. n8n builds structured prompt embedding v3 schema + few-shot examples
3. Ollama LLM generates Cypher from prompt
4. n8n executes Cypher against Neo4j
5. Execution result posted back to `data-service /execution-result`

## Ollama (Local LLM)

- **Image:** `ollama/ollama:latest` with NVIDIA GPU passthrough
- **Port:** 11434 internal, 11435 host-mapped
- **Default model:** `llama3.1:latest` (configurable via `OLLAMA_MODEL` env var)
- **Called by:** n8n workflows via `OLLAMA_URL: http://ollama:11434`
- **Purpose:** Generate Cypher from natural language (rule ingest + graph queries)

## Speckle (AEC Data Platform)

Full local Speckle deployment with 4 containers:
- `speckle-server` — main API server
- `speckle-postgres` — PostgreSQL 16.4 backing store
- `speckle-redis` — Valkey 8.1 cache
- `speckle-minio` — MinIO object storage

### Integration Points
| Component | Integration | Tokens |
|---|---|---|
| `data-service/app.py` | Publishes validation versions to Speckle using `specklepy` SDK | `SPECKLE_WRITE_TOKEN`, `SPECKLE_READ_TOKEN` |
| `data-service/speckle_validation.py` | Creates validation models, uploads geometry + rule results | Uses `ServerTransport` for object upload |
| `graph-viewer/model-viewer/` | Loads Speckle models via `@speckle/viewer` SDK for 3D visualization | `readToken` from `config.js` |
| `DG.Grasshopper` (`ValidatorComponent`) | Sends validation results to `data-service /validation/publish` | Indirect (via data-service) |

### Data Flow
1. Grasshopper validates rules against building geometry
2. `ValidatorComponent` POSTs rule results + entity geometry to `data-service /validation/publish`
3. `data-service` creates a Speckle model version with validation overlay using `specklepy`
4. Stores validation run metadata in Neo4j (`ValidationRun`, `ValidationEntity` nodes)
5. `model-viewer` loads base model + validation overlay from Speckle for 3D viewing

## data-service (FastAPI — MCP Endpoint)

- **MCP protocol** at `POST /mcp` — implements JSON-RPC with `tools/list`, `initialize`, `tools/call`
- **Tools exposed:** `neo4j_schema` (returns labels/rels/projects), `neo4j_query` (read-only Cypher)
- **Write protection:** `is_write_query()` regex rejects `CREATE|MERGE|DELETE|SET|REMOVE|DROP`
- **Execution tracking:** In-memory `EXECUTION_RESULTS` and `WORKFLOW_STATUS` dicts, polled by UI
- **Validation REST API:** CRUD for Speckle integration configs, validation run publish/list/delete/view

## Google Fonts (CDN)

- **Inter** — body text (weights 400, 500, 600)
- **Space Grotesk** — headings and branding (weights 500, 600)
- Loaded via `<link>` in `graph-viewer/index.html`
