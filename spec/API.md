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
| POST | `/computgraph/generate-inputs` | `{project, definitionId?, ruleId, candidateCount?, parameterOverrides?}` | Generate AI candidate parameter sets that respect a Metagraph Rule's SWRL threshold, from published Computgraph parameter bindings. Zero graph writes. See below. |
| POST | `/computgraph/candidates/accept` | `{project, definitionId, ruleId, candidate}` | Persist one architect-accepted candidate from a `generate-inputs` response as a standalone, Run-less `ParamState` `DesignState`. The only write path for AI-generated candidates. See below. |

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

#### `POST /computgraph/generate-inputs`

Request body: `{project: string, definitionId?: string, ruleId: string, candidateCount?: integer, parameterOverrides?: string[]}`.

**`definitionId` resolution rule** (when omitted) — identical to `validate`'s resolution rule:
- exactly one published definition exists -> use it
- zero published definitions -> 422 `COMPUTGRAPH_GENERATE_INPUTS_NO_DEFINITION`
- more than one published definition -> 422 `COMPUTGRAPH_GENERATE_INPUTS_AMBIGUOUS_DEFINITION`, hint lists the available ids

**`ruleId`** is **required** and must name an existing Metagraph `Rule` by `Rule_Id`; free design-intent text is out of scope (D-11). An unknown id is 422 `COMPUTGRAPH_GENERATE_INPUTS_RULE_NOT_FOUND`.

**`candidateCount`** defaults to **4**, bounded to **1..8** inclusive (D-15); out of range is 422 `COMPUTGRAPH_GENERATE_INPUTS_REQUEST_INVALID`.

**`parameterOverrides`** is the architect's binding override (D-06): an explicit list of Computgraph parameter names to generate over, replacing the declarative `inputBindings` selection (`spec/RULE-PARTITION-POLICY.md`) for this call only. If the override set resolves to zero eligible parameters, the response is 422 `COMPUTGRAPH_GENERATE_INPUTS_NO_ELIGIBLE_PARAMETERS`.

200 response:

```json
{
  "project": "p1",
  "definitionId": "frame.gh",
  "publishedAt": "2026-07-08T00:00:00Z",
  "ruleId": "R_URB_HEIGHT_MAX_75_V",
  "determinabilityClass": "monotone-bound",
  "ruleLimit": 75,
  "boundParameters": [
    {
      "cgId": "cg:1:param:11_Var_HTotal",
      "dgId": "dg:8E6F2C1A9B7D3045",
      "parameterName": "HTotal",
      "reinstateParameterId": "HTotal",
      "dataType": "Float",
      "stateType": "Number",
      "domainMin": 0.0,
      "domainMax": 100.0,
      "domainStep": 0.5
    }
  ],
  "excludedParameters": [
    {"cgId": "cg:1:param:11_Var_Notes", "parameterName": "Notes", "reason": "unsupported-datatype"}
  ],
  "candidates": [
    {
      "candidateId": "c0",
      "strategy": "conservative",
      "parameters": [
        {"parameterId": "HTotal", "displayName": "HTotal", "type": "Number", "numberValue": 40.0, "integerValue": null, "booleanValue": null}
      ],
      "excludedParameters": [],
      "ruleSatisfaction": {"claim": "satisfied", "basis": "HTotal=40.0 <= 75 (monotone-bound, direct read against ruleLimit)"},
      "provenance": {
        "source": "ai-generated",
        "sourceRuleId": "R_URB_HEIGHT_MAX_75_V",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "confidence": 0.82,
        "definitionId": "frame.gh",
        "publishedAt": "2026-07-08T00:00:00Z",
        "strategy": "conservative",
        "determinabilityClass": "monotone-bound",
        "generatedAt": "2026-07-27T12:00:00Z"
      },
      "statePayload": {"stateKind": "ParamState", "paramStates": [{"parameterId": "HTotal", "displayName": "HTotal", "type": "Number", "numberValue": 40.0}]}
    }
  ],
  "tier": 1,
  "attempts": 1,
  "provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "flags": []
}
```

Response keys: `project`, `definitionId`, `publishedAt` (nullable, ISO 8601 UTC, sourced from the published nodes), `ruleId`, `determinabilityClass`, `ruleLimit` (nullable), `boundParameters[]`, `excludedParameters[]`, `candidates[]`, `tier` (0 or 1, which generation tier produced the final set), `attempts` (bounded-retry count), `provider`, `model`, `flags[]` (advisory strings, e.g. Tier-0-floor fallback).

- `boundParameters[]` item keys: `cgId`, `dgId`, `parameterName`, `reinstateParameterId`, `dataType`, `stateType`, `domainMin`, `domainMax`, `domainStep`
- `excludedParameters[]` item keys: `cgId`, `parameterName`, `reason`
- `candidates[]` item keys: `candidateId`, `strategy`, `parameters[]`, `excludedParameters[]`, `ruleSatisfaction`, `provenance`, `statePayload`
- `parameters[]` item keys: `parameterId`, `displayName`, `type`, `numberValue`, `integerValue`, `booleanValue` — `type` is one of `Number` | `Integer` | `Boolean` only, mirroring `DG.Core.Models.DesignStateParameter`
- `ruleSatisfaction` keys: `claim` (`satisfied` | `violated` | `undeterminable`), `basis` (prose)
- `provenance` keys: `source` (always `ai-generated`), `sourceRuleId`, `provider`, `model`, `confidence`, `definitionId`, `publishedAt`, `strategy`, `determinabilityClass`, `generatedAt`

**`determinabilityClass` vocabulary (all three):** `direct-parameter`, `monotone-bound`, `geometry-required` — sourced from the matching `inputBindings` entry in `llm/structure_rules.json` (`spec/RULE-PARTITION-POLICY.md`); a rule with no `inputBindings` entry defaults to `geometry-required`.

**`strategy` vocabulary (all four):** `conservative`, `balanced`, `exploratory`, `near-limit`.

**`excludedParameters[].reason` vocabulary (all four):** `unresolved-reinstate-id`, `non-variable-kind`, `unsupported-datatype`, `missing-domain`.

**Normative guarantees:**
- Every value in every returned candidate satisfies `domainMin <= v <= domainMax` and is aligned to `domainStep`. There is **no partial result**: the response is all-valid or an error — never a mix (D-14).
- Clamping is **not implemented**. An out-of-domain model value causes rejection and bounded retry, then 502 `COMPUTGRAPH_GENERATE_INPUTS_DOMAIN_VIOLATION` whose `hint` names each offending parameter and its domain, and whose response body carries the per-attempt violation list.
- `parameters[].type` is one of `Number` | `Integer` | `Boolean` only. Computgraph `Text` and `Geometry` parameters never appear in `parameters[]`; they are reported in `excludedParameters[]` with reason `unsupported-datatype` (GHIN-02, D-05).
- A parameter with no resolvable `reinstateParameterId` is excluded with reason `unresolved-reinstate-id` and named on the candidate — never silently dropped (D-04).
- When `determinabilityClass` is `geometry-required`, **every** candidate's `ruleSatisfaction.claim` is `undeterminable`. The endpoint never reports `satisfied` for a rule it cannot check from parameters alone — this is the credibility invariant (D-09).
- `ruleLimit` is read from the Rule's SWRL atoms at request time and is `null` for a `geometry-required` rule. It is never denormalized into any configuration file (D-10).
- The endpoint performs **zero graph writes** and has no code path to the Grasshopper canvas bridge (GHIN-04, D-19, D-22) — no write, no bridge call.
- The provider is resolved once per request; every retry attempt calls the same adapter in-process (D-16).

##### SC1 acceptance thresholds

These are normative numbers, measured on the Frame definition fixture over the phase's fixture rule set, and plan 38-07 asserts them:

| # | Metric | Threshold |
|---|---|---|
| SC1-a | Candidates whose every parameter is in-domain and step-aligned | **100%** — any failure is a validator defect, not a quality score |
| SC1-b | Candidates satisfying the rule limit, for `direct-parameter` and `monotone-bound` rules | **>= 75%** (3 of the default 4) |
| SC1-c | Valid candidates returned when the LLM tier is stubbed to return nothing usable | **>= 1** (the Tier 0 floor, D-12) |
| SC1-d | Minimum normalized pairwise L1 distance across the candidate set | **>= 0.10** (each parameter scaled to its own domain) |
| SC1-e | Candidates claiming `satisfied` for a `geometry-required` rule | **exactly 0** |

**Errors:** 422 `COMPUTGRAPH_GENERATE_INPUTS_REQUEST_INVALID`, 422 `COMPUTGRAPH_GENERATE_INPUTS_NO_DEFINITION`, 422 `COMPUTGRAPH_GENERATE_INPUTS_AMBIGUOUS_DEFINITION`, 422 `COMPUTGRAPH_GENERATE_INPUTS_RULE_NOT_FOUND`, 422 `COMPUTGRAPH_GENERATE_INPUTS_NO_ELIGIBLE_PARAMETERS`, 502 `COMPUTGRAPH_GENERATE_INPUTS_DOMAIN_VIOLATION`, 502 `COMPUTGRAPH_GENERATE_INPUTS_FAILED`. Every error body is the standard `{error, hint, code}` detail shape.

#### `POST /computgraph/candidates/accept`

Request body: `{project: string, definitionId: string, ruleId: string, candidate: <one candidates[] item>}` — `candidate` is exactly one item from a prior `generate-inputs` response's `candidates[]` array, round-tripped verbatim by the caller.

The server **re-validates every parameter against the live published domains before writing** and rejects with 422 `COMPUTGRAPH_ACCEPT_CANDIDATE_DOMAIN_VIOLATION` on any miss — the client round-trip is never trusted (T-38-01).

200 response:

```json
{
  "project": "p1",
  "stateId": "DS_a1b2c3d4e5f6a7b8",
  "kind": "ParamState",
  "acceptedAt": "2026-07-27T12:05:00Z",
  "parameterCount": 1,
  "provenance": {
    "source": "ai-generated",
    "sourceRuleId": "R_URB_HEIGHT_MAX_75_V",
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "confidence": 0.82,
    "definitionId": "frame.gh",
    "publishedAt": "2026-07-08T00:00:00Z",
    "strategy": "conservative",
    "determinabilityClass": "monotone-bound",
    "generatedAt": "2026-07-27T12:00:00Z"
  }
}
```

Response keys: `project`, `stateId` (carries the `DS_` prefix, D-18), `kind` (always the literal `ParamState`), `acceptedAt`, `parameterCount`, `provenance`.

**Normative guarantees:**
- The write is a MERGE keyed by `StateId` + `project`, so re-accepting the same candidate is idempotent.
- **Only accepted candidates are persisted** — a rejected candidate leaves no trace anywhere in the graph (D-19).

**Errors:** 422 `COMPUTGRAPH_ACCEPT_CANDIDATE_REQUEST_INVALID`, 422 `COMPUTGRAPH_ACCEPT_CANDIDATE_DOMAIN_VIOLATION`, 502 `COMPUTGRAPH_ACCEPT_CANDIDATE_FAILED`. Every error body is the standard `{error, hint, code}` detail shape.

### LLM Gateway

The provider-agnostic LLM gateway. Routes a prompt to the active provider adapter (Anthropic, OpenAI, or a local Ollama server) and normalises every adapter's response into one envelope.

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/llm/generate` | `{prompt, system?, model?, provider?}` | Route the prompt to the active provider adapter and return the normalised envelope. See below. |

#### `POST /llm/generate`

Request body: `{prompt: string, system?: string, model?: string, provider?: string}`

When `provider` / `model` are omitted (n8n sends `null` per D-07), the gateway resolves the active provider from saved LLM settings; a request-level `provider` / `model` overrides the saved value for that call only.

Response envelope:

```json
{
  "text": "...",
  "provider": "anthropic",
  "model": "claude-sonnet-5",
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
  "truncated": false,
  "finish_reason": "end_turn",
  "served_model": "claude-sonnet-5-20261022",
  "response_id": "msg_01X",
  "system_fingerprint": null
}
```

- `text` — the generated text.
- `provider` — the provider that served the request.
- `model` — **the REQUESTED model id.** This ships today and is not repointed (D-20/Correction 5).
- `usage` — normalised token usage `{prompt_tokens, completion_tokens, total_tokens}`.
- `truncated` — `true` when the provider stopped because the output cap was hit.
- `finish_reason` — the provider's raw stop reason, in the provider's own spelling.
- `served_model` — the model id the provider **reported serving**, read verbatim from the provider response.
- `response_id` — the provider's own message/response id for this call.
- `system_fingerprint` — a provider-side configuration fingerprint.

**Per-provider availability of the provenance fields (D-20):**

| Provider | `served_model` | `response_id` | `system_fingerprint` |
|----------|----------------|---------------|----------------------|
| OpenAI (and OpenAI-compatible base URLs) | yes | yes | yes |
| Anthropic | yes | yes | never (the Messages API carries no fingerprint key) |
| Ollama | yes | never (the parsed `/api/generate` response carries no `id`) | never |

**Normative rules:**
- A field absent from the provider response is **`null`** in the envelope. The gateway never synthesises or guesses a value for a key the provider omitted.
- `served_model` is **provider-attested**, not independently verified: it records what the provider reported serving, which is what makes a provider alias re-pointing behind a requested id observable. `model` continues to carry the requested id, so the two can be compared (D-20/Correction 5).
- The three provenance fields are additive: they default to `null` for any caller that never sets them, so existing consumers are unaffected.

**Errors:** 502 with the standard `{error, hint, code}` detail shape for any provider failure.

### Identity (`/identity/*`, Phase 32.1/1203)

The identity registry API. Normative contract: `spec/DG-ID.md` (format, minting, collision policy, binding model). This is a first-write for this document — no `/identity/*` route was previously documented here.

| Method | Path | Body / Params | Description |
|--------|------|---------------|-------------|
| POST | `/identity/mint` | `{project, definition_id, cg_id, entity_kind}` | Deterministically mint + persist a `dgId` for a Computgraph entity. See below. |
| GET | `/identity/resolve` | Query: `platform, native_id, project` | Resolve a `(platform, native_id)` representation to its owning entity's `dgId`. |
| POST | `/identity/bind` | `{dg_id, platform, native_id_kind, native_id, connector, project}` | Bind a native-id representation to a `dgId` — never a silent repoint. |
| GET | `/identity/{dg_id}/representations` | Query: `project` | List all platform representations bound to a `dgId`. |
| DELETE | `/identity/{dg_id}/representations` | Query: `platform, native_id, project` | Detach a representation from a `dgId` — removes only the `Representation` node/edge; the `dgId` is untouched. |
| POST | `/identity/{dg_id}/properties` | `{property_name, value, platform, connector}` + query `project` | Write (upsert) a cross-platform shared property on a `dgId`. |
| GET | `/identity/{dg_id}/properties` | Query: `project, property_name?` | Read one shared property (when `property_name` given) or list all shared properties on a `dgId`. |

#### `POST /identity/mint`

Request body:

```json
{
  "project": "p1",
  "definition_id": "wall.gh",
  "cg_id": "cg:1:param:heightValue",
  "entity_kind": "Parameter"
}
```

`entity_kind` is a required field, validated against the fixed allowlist `ENTITY_KINDS = ("Object", "Procedure", "Pattern", "Parameter", "Interface")` — these are exactly the five Computgraph labels `POST /computgraph/publish`'s writers MERGE on. An unrecognized `entity_kind` is rejected before any Cypher runs (both at the pydantic field-validator level and again inside `mint_identity` itself, defense-in-depth).

200 response:

```json
{"dgId": "dg:9F2A4C1E7B03D5A8"}
```

**Idempotent** — safe to call unconditionally ahead of a publish; re-minting the same `(project, definition_id, cg_id)` triple returns the same `dgId` without duplicating the node. The anchor MERGE is **label-aware**: it upserts on `(:<entity_kind> {cgId, definitionId, project})`, the same labelled three-part key `POST /computgraph/publish`'s writers use, so a pre-publish mint and a later publish coincide on one node rather than orphaning (CR-01, Phase 1203 Plan 03). Minted nodes are tagged `graph = 'Computgraph'`.

**Errors:** 422 (pydantic validation failure on an unrecognized `entity_kind`, FastAPI's standard validation-error body — not the `{error, hint, code}` shape, since this is caught before the route body runs).

**Other identity routes' structured error codes** (standard `{error, hint, code}` detail shape): `DGID_NOT_FOUND` (404 — no entity/binding/property matches the given key), `DGID_AMBIGUOUS_BINDING` (409 — `POST /identity/bind` only, when the native id is already bound to a *different* `dgId`; the response includes the existing `dgId` in the message so the caller can detach-then-rebind or confirm intent).

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
