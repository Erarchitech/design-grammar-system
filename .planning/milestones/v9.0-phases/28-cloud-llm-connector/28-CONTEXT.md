# Phase 1: Cloud LLM Connector and Provider Abstraction - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a provider-agnostic LLM gateway in data-service (`POST /llm/generate`) with adapters for Anthropic Claude, OpenAI-compatible APIs, and local Ollama — replacing 5 direct Ollama HTTP calls from n8n workflows — plus encrypted key storage and a UI settings panel for provider/model/key management.

**In scope (LLMC-01..06):**
- `data-service/llm_gateway.py` — provider adapters behind one `POST /llm/generate` contract
- `data-service/app.py` — gateway endpoint + `GET/PUT/DELETE /llm/settings` + `POST /llm/settings/test`
- Encrypted-at-rest key storage (master secret via env var in docker-compose.yml)
- `graph-viewer/index.html` — LLM settings panel (new nav tab)
- n8n workflows (`rules-to-metagraph.json`, `graph-query-mcp.json`, `spec-ingest.json`, `spec-query.json`, `spec-update.json`) — direct HTTP nodes rewired to gateway
- pytest coverage: adapter routing, fallback resolution, key masking, error mapping

**Out of scope (Phase 1 boundary):**
- DG context layer (ontology/SWRL/Cypher awareness) — Phase 2
- Rules ingest/edit workflow upgrades — Phase 4
- Any GH node recognition or input generation — Phases 5-6
- OpenClaw evaluation — Phase 3 (parallel track)

</domain>

<decisions>
## Implementation Decisions

### Provider Adapter Design
- **D-01 (Thin normalization):** Each adapter keeps its provider-native prompt format. The gateway wraps responses in a standard envelope `{text, provider, model, usage}`. Anthropic receives `messages[]` format, OpenAI receives chat completions format, Ollama receives its generate format. Adapter translates between the common gateway schema and the provider-native format.
- **D-02 (Explicit provider tag):** The request body carries `provider: 'anthropic' | 'openai' | 'ollama'` explicitly — no auto-detection from model name prefixes. Gateway routes to the correct adapter based on this tag.
- **D-03 (Anthropic auth — API key only):** Single `x-api-key` header for Anthropic. No custom base URL field. Users get a key from console.anthropic.com.
- **D-04 (Minimal response):** Gateway returns `{text, provider, model, usage}` where usage normalizes to `{prompt_tokens, completion_tokens, total_tokens}`. No cost estimate, stop reason, or raw response fields unless a future consumer needs them.

### n8n Gateway Wiring
- **D-05 (Direct HTTP node):** Each n8n workflow replaces its Ollama HTTP node URL with `http://data-service:8000/llm/generate`. No n8n middleware Function node — the gateway owns all LLM logic. n8n stays thin.
- **D-06 (Big-bang migration):** All 5 workflows (rules-to-metagraph, graph-query-mcp, spec-ingest, spec-query, spec-update) rewired in a single plan. The gateway is designed as a drop-in replacement — URL swap + body reformat per workflow.
- **D-07 (Gateway resolves active provider):** n8n sends `{provider: null, model: null}` in the request body. The gateway reads the user's saved provider/model settings and resolves which adapter to use. Switching providers in the UI takes effect immediately with no workflow edits.
- **D-08 (Container-level health only):** Docker compose health check for Ollama as before. No gateway-level `/health` endpoint for LLM provider status — errors surface through the gateway's response on the first call.

### UI Settings Panel
- **D-09 (New nav tab):** A tab labeled "LLM Settings" in the existing sidebar nav alongside Register, Home, Project, Graph Viewer.
- **D-10 (Full form + status banner):** No-key state displays the full configuration form with a prominent yellow banner "Using local Ollama (fallback)". Active state shows a green "Connected: {provider}" indicator with masked key, model selector, and Change/Remove actions. Both states are the same panel, just different content — not a collapsed/expanded toggle.
- **D-11 (Test saved config only):** A single "Test Connection" button calls `POST /llm/settings/test` with the saved provider and key. Shows success (latency, model confirmed) or actionable error. No "test before save" flow — the user saves first, then tests.
- **D-12 (Read from data-service every call):** The gateway reads `GET /llm/settings` from data-service on every `/llm/generate` call. No caching — settings changes apply instantly without restart. The overhead of a local data-service read is negligible compared to the LLM call itself.

### Model Discovery
- **D-13 (Fully dynamic per provider):** The gateway exposes `GET /llm/models?provider=...` which queries each provider's API for available models. Ollama calls `GET /api/tags` locally. Anthropic and OpenAI calls use their model listing endpoints.
- **D-14 (Seed list + live refresh on test):** A small hardcoded seed list of known models per provider covers the no-key state and first-time setup. Once a key is validated via `POST /llm/settings/test`, the gateway queries the provider's API and replaces the seed list with live results. The test endpoint returns the live model list so the UI can refresh the dropdown.
- **D-15 (Plain model ID list):** The model dropdown shows model IDs only — no context window, pricing, or capability indicators. Users who need model details reference provider documentation.
- **D-16 (Ollama auto-discover at startup):** The gateway calls `http://ollama:11434/api/tags` at startup and caches the model list. Auto-discovers whatever models the user has pulled locally.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and Requirements
- `.planning/milestones/v9.0-ROADMAP.md` — Full v9.0 roadmap, Phase 1 goal and success criteria (LLMC-01..06)
- `.planning/milestones/v9.0-REQUIREMENTS.md` — Full v9.0 requirements including LLMC-01..06 traceability

### Codebase Reference
- `data-service/app.py` — Where the gateway endpoint will be added; current MCP protocol, write protection, execution tracking patterns
- `n8n/workflows/rules-to-metagraph.json` — Primary ingest workflow, current Ollama call pattern (nodes 42-93)
- `n8n/workflows/graph-query-mcp.json` — Query workflow, current Ollama call pattern (nodes 34-97)
- `n8n/workflows/spec-ingest.json` — Spec ingest workflow, current Ollama call
- `n8n/workflows/spec-query.json` — Spec query workflow, current Ollama call
- `n8n/workflows/spec-update.json` — Spec update workflow, current Ollama call
- `graph-viewer/index.html` — SPA where the new LLM Settings nav tab and panel will be added
- `docker-compose.yml` — Where the master-secret env var and any new service config goes
- `.planning/codebase/ARCHITECTURE.md` — System architecture reference
- `.planning/codebase/INTEGRATIONS.md` — Current external integration points (Neo4j, n8n, Ollama, Speckle, data-service)

### Prior Decisions (from v9.0-ROADMAP.md Key Decisions)
- Single LLM gateway in data-service, not per-workflow provider nodes
- Ollama retained as zero-config fallback (no key configured = today's behavior)
- Keys encrypted server-side (master secret via env var), never in Neo4j/localStorage/logs
- No token-streaming UI — async polling pattern stays

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data-service/app.py` — Existing FastAPI app with `POST /mcp` JSON-RPC + REST endpoints. Gateway and settings endpoints follow the same FastAPI patterns (Pydantic models, `@app.post`, `@app.get`, `HTTPException`). The MCP `neo4j_query` tool has write protection regex — the gateway needs no such guard.
- `graph-viewer/index.html` — Single-file React 18 SPA with existing nav tabs (Register, Home, Project, Graph Viewer). Adding a new tab and panel follows the existing pattern: nav click handler → state change → conditional render of panel component.

### Established Patterns
- All UI styling uses Tailwind CSS (loaded from CDN in `index.html`)
- API calls from UI use `fetch()` with async/await — no React Query or axios
- Secrets in docker-compose use `- SECRET_NAME=${SECRET_NAME:-default_value}` pattern
- The `data-service` container already has the encryption dependencies (cryptography package likely available via requirements.txt)

### Integration Points
- `POST /llm/generate` — New endpoint in data-service. Called by 5 n8n workflows via HTTP nodes
- `GET/PUT/DELETE /llm/settings` — Settings CRUD in data-service. Called by UI
- `POST /llm/settings/test` — Live key validation endpoint. Called by UI "Test Connection" button
- `GET /llm/models?provider=...` — Model discovery endpoint. Called by UI to populate model dropdown
- 5 n8n workflows need URL + body format updates to call gateway instead of Ollama directly

</code_context>

<specifics>
## Specific Ideas

- The gateway adapter pattern should follow a standard Strategy pattern: a base `LLMAdapter` abstract class with `generate(prompt, system, model) → GenerateResponse` and `list_models() → List[str]` methods, one concrete subclass per provider.
- Encryption at rest: Python's `cryptography.fernet` (symmetric AES-GCM via a master secret derived key) is the simplest option — `cryptography` is already a common dependency.
- The `POST /llm/settings/test` endpoint should call the provider's model listing API (or a simple chat completion with max_tokens=1) to validate the key is functional, not just that it parses.
- For the seed model list, use the current Claude and OpenAI model lineups as of July 2026: Anthropic — `claude-sonnet-5`, `claude-opus-4-8`, `claude-haiku-4-5-20251001`; OpenAI — `gpt-4o`, `gpt-4o-mini`, `o3-mini`. These are replaced on first successful test+save.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within the Phase 1 scope boundary. The user's original framing about scalabilty for generative functionality, parametric model parsing, and lessons-learned mechanisms maps to Phases 2+ (context layer) and Phases 5-6 (GH recognition and input generation).

</deferred>

---

*Phase: 1-Cloud LLM Connector and Provider Abstraction*
*Context gathered: 2026-07-03*
