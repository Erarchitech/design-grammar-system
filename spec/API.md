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

### Computgraph

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/computgraph/publish` | `{project, cgContext}` | Publish a confirmed `cgContextJson` v1 envelope as a Computgraph subgraph (shipped Phase 36; documented here only to close the doc gap). Returns `{status, publishedCounts, staleEntityIds}`. Errors: 422 `COMPUTGRAPH_PUBLISH_REQUEST_INVALID`, 502 `COMPUTGRAPH_PUBLISH_FAILED`. |
| POST | `/computgraph/validate` | `{project, definitionId?}` | Run the deterministic, LLM-free structural + rule-mapped checks over the published Computgraph. See below. |
| POST | `/computgraph/consult` | `{project, definitionId, question}` | Read-only, grounded LLM consult over the published Computgraph subgraph. See below. |

#### `POST /computgraph/validate`

Request body: `{project: string, definitionId?: string}`

**`definitionId` resolution rule** (when omitted): resolve the project's published definitions —
- exactly one published definition exists -> use it
- zero published definitions -> 422 `COMPUTGRAPH_VALIDATE_NO_DEFINITION`
- more than one published definition -> 422 `COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION`, hint lists the available ids

200 response:

```json
{
  "project": "p1",
  "definitionId": "frame.gh",
  "publishedAt": "2026-07-08T00:00:00Z",
  "checkedAt": "2026-07-27T12:00:00Z",
  "findings": [
    {
      "checkId": "procedure_without_interface",
      "severity": "violation",
      "message": "Procedure '11_Proc' has no Interface. Where: Procedure cgId=cg:1:proc:11_Proc. How to fix: tag at least one IntF_ group under this Procedure and re-publish.",
      "entities": [
        {"label": "Procedure", "cgId": "cg:1:proc:11_Proc", "name": "11_Proc", "conventionName": "11_Proc"}
      ]
    }
  ],
  "ruleResults": [
    {
      "ruleId": "R_STRUCT_FRAME_FOOTER_V",
      "operation": "requiresProcedure",
      "passed": false,
      "ruleExists": true,
      "message": "No Procedure matching 'Footer' was found. Where: Procedures scoped to definitionId=frame.gh. How to fix: tag a Procedure whose name contains 'Footer' and re-publish.",
      "satisfyingEntities": [],
      "offendingEntities": [{"label": "Algorithm", "cgId": "", "name": "1", "conventionName": ""}]
    }
  ],
  "counts": {"violation": 1, "warning": 1, "info": 0}
}
```

Response keys:
- `project`, `definitionId` — echo the resolved scope
- `publishedAt` (nullable, ISO 8601 UTC) — sourced from the published nodes, so staleness relative to the live canvas is visible
- `checkedAt` (ISO 8601 UTC) — when this report was computed
- `findings[]` — deterministic structural checks (SVAL-01); each item: `checkId`, `severity`, `message`, `entities[]`; each `entities[]` item: `label`, `cgId`, `name`, `conventionName`
- `ruleResults[]` — rule-mapped structural checks (SVAL-02); each item: `ruleId`, `operation`, `passed`, `ruleExists`, `message`, `satisfyingEntities[]`, `offendingEntities[]`
- `counts` — `{violation, warning, info}` integer keys; `violation`/`info` are aggregated over `findings[]` severities, `warning` also includes every `ruleResults[]` entry with `passed: false` (rule-mapped failures are warning-severity per `spec/RULE-PARTITION-POLICY.md`)

**`checkId` vocabulary (all seven):** `orphan_pattern`, `procedure_without_interface`, `dangling_param_link`, `algorithm_without_procedure`, `parameter_without_datatype`, `object_without_behavior`, `annotation_convention`

**Rule-mapped `operation` vocabulary (all four):** `requiresProcedure`, `requiresParameter`, `requiresInterface`, `forbidsOrphan`

**Invariants:**
- **Deterministic:** `findings` and `ruleResults` are byte-identical across repeated calls against an unchanged graph; `checkedAt` is the only permitted varying field.
- **LLM-free:** this endpoint never calls the LLM gateway.

**Errors:** 422 `COMPUTGRAPH_VALIDATE_REQUEST_INVALID`, 422 `COMPUTGRAPH_VALIDATE_NO_DEFINITION`, 422 `COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION`, 502 `COMPUTGRAPH_VALIDATE_FAILED`. Every error body is the standard `{error, hint, code}` detail shape.

#### `POST /computgraph/consult`

Request body: `{project: string, definitionId: string, question: string}` — both ids required.

200 response:

```json
{
  "project": "p1",
  "definitionId": "frame.gh",
  "publishedAt": "2026-07-08T00:00:00Z",
  "question": "Which parameters drive the truss height?",
  "answer": "The truss height is driven by 11_Var_HTotal (Variable, Float)...",
  "grounded": true,
  "groundedCount": 1,
  "citedEntities": ["11_Var_HTotal"],
  "ungroundedMentions": [],
  "subgraphEntityCount": 42,
  "truncated": false
}
```

Response keys: `project`, `definitionId`, `publishedAt`, `question`, `answer`, `grounded` (boolean), `groundedCount` (integer), `citedEntities` (sorted array of entity names found in both the answer and the subgraph), `ungroundedMentions` (sorted array of convention-shaped tokens found in the answer but absent from the subgraph), `subgraphEntityCount`, `truncated` (true when the subgraph exceeded the prompt entity cap).

**Behavioural guarantees:**
- **Read-only:** the endpoint is strictly read-only and never executes any Cypher derived from the model's output.
- **Flag, don't block:** a grounding miss sets `grounded` to `false` and populates `ungroundedMentions`, but still returns 200.
- **Staleness visible:** `publishedAt` is always present, so an answer computed from a stale publish is visibly stale.

**Errors:** 422 `COMPUTGRAPH_CONSULT_REQUEST_INVALID`, 502 `COMPUTGRAPH_CONSULT_FAILED`.

**Report surface:** the `/computgraph/validate` response is the report surface for this milestone, consumable directly over HTTP by a future ui-v2 panel. Printing it from a Grasshopper panel through the canvas bridge is a named deferred item — it requires a new dispatcher handler in `CanvasCommandDispatcher` and a plugin rebuild, disproportionate for an MVP whose report is already consumable over plain HTTP.

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
