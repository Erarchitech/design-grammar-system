# API Routes

## data-service (FastAPI, port 8000)

Base URL: `/data-service` (via nginx proxy)

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |

### MCP Protocol

| Method | Path | Description |
|--------|------|-------------|
| POST | `/mcp` | MCP JSON-RPC endpoint |

**MCP Tools:**
- `neo4j_schema` — returns `{labels, relationship_types, property_keys, graphs, projects}`
- `neo4j_query` — executes read-only Cypher (write queries rejected)

### Execution Tracking

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/execution-result` | `{id, status, result, workflow}` | Store workflow execution status |
| GET | `/execution-result/{id}` | — | Retrieve execution status by ID |
| GET | `/execution-result/latest/{workflow}` | — | Latest status for named workflow |

### Speckle Settings

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/settings/speckle` | — | Get Speckle connection settings (tokens masked) |
| PUT | `/settings/speckle` | `{base_url, write_token, read_token}` | Update Speckle settings |

**Fallback chain:** env vars → persisted JSON (`/app/data/speckle-settings.json`) → defaults

### Speckle Integration Config (per project)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/integration/speckle/project/{project}` | — | Get project's Speckle config |
| PUT | `/integration/speckle/project/{project}` | `{project_id, base_model_id, validation_model_id}` | Save project's Speckle config |

### Validation

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/validation/publish` | `{project, run_name, rules: [...]}` | Publish validation to Speckle + store metadata |
| GET | `/validation/runs/{project}` | — | List all validation runs for project |
| DELETE | `/validation/run/{project}/{run_id}` | — | Delete a validation run |
| GET | `/validation/view/{project}` | — | Latest validation manifest |
| GET | `/validation/view/{project}/{run_id}` | — | Specific run manifest |
| GET | `/validation/view/{project}/{run_id}/{rule_id}` | — | Rule-filtered entity sets |

---

## n8n Webhooks (port 5678)

Base URL: `/n8n` (via nginx proxy)

### Rules Ingest

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/webhook/dg/rules-ingest` | `{rules_text, project}` | Convert NL rules → SWRL → Cypher → Neo4j |

**Pipeline:** Webhook → Set Defaults → Fetch Existing → Build LLM Prompt → Ollama Generate → Parse/Validate Cypher → Execute → Annotate Graph → Store Result → Respond ACK

**Edit mode:** Detects keywords (`edit`, `update`, `change`, `modify`), extracts `Rule_Id`, generates MATCH-DELETE cleanup before re-creating atoms.

### Graph Query

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/webhook/dg/graph-query` | `{prompt, project}` | NL question → Cypher → Neo4j → NL answer |

**Pipeline:** Webhook → Fetch Schema (MCP) → Build Cypher Prompt → Ollama Generate → Parse/Validate → Run Cypher (MCP, read-only) → Build Answer Prompt → Ollama Summarize → Store Result → Respond

**Smart overrides:** "list rules" → standard Rule listing query; numeric keywords → keyword-matching on `Rule.text`

---

## Neo4j HTTP API (port 7474)

Base URL: `/neo4j` (via nginx proxy)

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/db/neo4j/tx/commit` | `{statements: [{statement: "CYPHER..."}]}` | Direct Cypher execution |

Used by the SPA for graph visualization (NeoVis), node property editing, and node deletion.

---

## Async Polling Pattern

The SPA does not wait for n8n workflow completion. Instead:

1. UI sends webhook request → receives immediate 200 ACK with execution ID
2. n8n workflow runs asynchronously → stores result via `POST /data-service/execution-result`
3. UI polls `GET /data-service/execution-result/{id}` until status ≠ "pending"
