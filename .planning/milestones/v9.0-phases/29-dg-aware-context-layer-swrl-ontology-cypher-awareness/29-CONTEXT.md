# Phase 29: DG-Aware Context Layer (SWRL + Ontology + Cypher Awareness) - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

LLM calls stop relying on a single static prompt (today's `cypher_template.txt`, inlined into n8n's "Build LLM Prompt" / "Build Cypher Prompt" nodes). Every ingest/edit/query request is instead assembled by a new deterministic context assembler in data-service, drawing from the V7 ontology catalog (Ontograph/Metagraph/Validgraph, plus a forward-prep Computgraph block), SWRL violation-pattern conventions, and a versioned Cypher expression catalog covering max/min limit, range, ratio, boolean requirement, and existence/count shapes. Every generated Cypher statement is schema-validated before touching Neo4j, with a bounded automatic retry loop on failure.

**In scope (CTXA-01..05):**
- `data-service/dg_context.py` — deterministic context assembler
- `POST /context/assemble` — new endpoint, called by n8n before `/llm/generate`
- `GET /context/debug` — inspection endpoint, same params as assemble
- `llm/cypher_catalog.json` — new versioned Cypher expression catalog
- SWRL convention block (machine-readable, lives near `dg_context.py`)
- Computgraph concept catalog block (forward-prep only, sourced from `DesignGrammar-V7.owl`)
- New data-service Cypher validator + internal bounded retry loop
- n8n prompt nodes (`Build LLM Prompt`, `Build Cypher Prompt`, `Fetch Existing Entities`, `Parse LLM Output`) reduced to thin callers

**Out of scope (Phase 29 boundary):**
- Wiring the Computgraph catalog into actual ingest/query context selection — that's Phase 35 (RCGN)
- Building the Computgraph object model itself — Phase 32 (CGSR)
- Orchestration platform choice — Phase 30 (parallel track, no dependency)
- Ambiguity clarification questions, atom-level edit diff preview — Phase 31 (RING), though Phase 29's retry-bound language is reused there
- Embeddings/RAG-based context retrieval — explicitly out per CTXA-05 and the standing v1.1 no-RAG decision

</domain>

<decisions>
## Implementation Decisions

### Context Assembler Interface
- **D-01:** New `POST /context/assemble` endpoint in data-service, called by n8n before `/llm/generate` — keeps the gateway owning all LLM logic (Phase 28 D-05: "n8n stays thin"), matches the ROADMAP's own phrasing ("n8n prompt nodes reduced to thin callers of the context assembler")
- **D-02:** Three request types: `rule_ingest`, `rule_edit`, `graph_query` — matches the two n8n workflows' actual call sites; edit reuses ingest context plus the `cypher_template.txt` property-reuse-on-edit rule (preserve `iri`/`SWRL_label`, change only `Literal` values)
- **D-03:** Relevant-subset selection (CTXA-01) is deterministic keyword/entity matching against the incoming rule text or question — centralizes today's n8n "Smart Overrides" (height/maximum keyword → Rule listing query) into `dg_context.py`, staying consistent with CTXA-05 (no embeddings)
- **D-04:** `GET /context/debug` takes the same params as the real assemble call and returns the full assembled context JSON — what you inspect is exactly what gets sent, no parallel code path to drift out of sync

### Cypher Validator & Retry Loop
- **D-05:** Validation runs as a new data-service function/endpoint — moves today's ad hoc n8n "Parse LLM Output" bracket/dedup checks into a testable, pytest-covered validator (CTXA-04)
- **D-06:** data-service retries internally on validation failure: re-calls the LLM gateway with structured violations appended as corrective feedback, up to the bound; n8n makes one call and gets back valid Cypher or a final structured error
- **D-07:** Bounded retry count: 2 retries (3 attempts total) — same bound language RING-04 (Phase 31) will reuse for the same retry concept; small enough not to balloon latency on this synchronous HTTP + polling architecture (no message queue)
- **D-08:** Structured violations: `{valid: bool, violations: [{code, message, path?}]}` with stable machine-readable codes (e.g. `unknown_label`, `bad_kind_enum`, `unbalanced_brackets`) — mirrors the ErrorMessageTemplates What+Where+How-to-fix pattern already standard on the C# side

### Cypher Expression Catalog Format & Content
- **D-09:** `llm/cypher_catalog.json` structure: `{version, shapes: [{id, name, description, swrl_pattern, cypher_template, worked_example}]}` — array form, trivial iteration in Python and n8n's JS, new shapes just append
- **D-10:** Shape ids cover: max limit, min limit, range, ratio, boolean requirement, existence/count
- **D-11:** "Range" keeps the existing two-separate-violation-rules convention (`cypher_template.txt` SEMANTIC MAPPING) — the catalog entry documents the min-rule + max-rule pair as one worked example together; zero schema propagation cost, no CLAUDE.md checklist changes triggered
- **D-12:** "Existence/count" (no prior art) models as a `swrlb:` builtin atom pair against a `Literal` threshold, reusing the existing `ClassAtom` + `BuiltinAtom` + `ARG` structure — no new node labels or relationship types, stays inside the documented schema (Class/DatatypeProperty/ObjectProperty/Builtin/Rule/Atom/Var/Literal only)
- **D-13:** Versioning: simple integer `version` field, bumped on any shape addition/removal — mirrors the `SCHEMA VERSION: v4.0` header convention already used in `cypher_template.txt`

### Computgraph Catalog Scope (Phase 29 vs. Phase 32-37 boundary)
- **D-14:** Computgraph concept catalog block sources its `dgc:` classes/relations from the static OWL file (`DesignGrammar-V7.owl`) — the ontology-level `dgc:` classes and DG Canvas Annotation Convention grammar already exist from Phase 13's V7 baseline; Phase 29 catalogs what's already defined, it doesn't invent new Computgraph structure (that's Phase 32's CGSR-01/02 job)
- **D-15:** Pure forward-prep: none of Phase 29's four success criteria touch Computgraph. Write the block, unit-test that it loads/parses, but do NOT wire it into `rule_ingest`/`rule_edit`/`graph_query` context selection — that wiring is Phase 35's job
- **D-16:** File split: `llm/cypher_catalog.json` stays Cypher-shapes-only per its ROADMAP deliverable name; SWRL conventions and the Computgraph catalog live as Python data structures in or near `dg_context.py` (read-only reference data, not versioned expression templates)
- **D-17:** Static V7 concept catalog is UNIONED at request time with a live Neo4j query for the project's actually-existing `Class`/`DatatypeProperty` nodes — centralizes today's n8n "Fetch Existing Entities" step into `dg_context.py` rather than dropping it

### Claude's Discretion
- Exact Python module layout beyond `dg_context.py` (e.g. whether the SWRL/Computgraph catalog data lives in the same file or a sibling module) — left to planning/implementation as long as `llm/cypher_catalog.json` stays the separate, Cypher-only versioned artifact
- Exact violation `code` vocabulary (the specific set of machine-readable codes) — derive from the validator's actual checks (labels, relationship types, `kind` enums, property names, bracket nesting) during implementation
- Exact keyword-matching implementation for context scoping (Q3, Area 1) — reuse/extend today's n8n Smart Overrides keyword list, exact match logic is an implementation detail

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data-service/llm_gateway.py` — `POST /llm/generate` contract, adapter Strategy pattern (`LLMAdapter`, `AnthropicAdapter`, `OpenAIAdapter`, `OllamaAdapter`), `resolve_active_provider()`, `get_adapter()` — shipped Phase 28, the context assembler's output feeds into this
- `data-service/app.py` — large FastAPI app (100+ symbols); existing endpoint patterns (Pydantic request/response models, `@app.post`/`@app.get`, `HTTPException`, `_structured_error_response()`) to follow for the new `/context/assemble`, `/context/debug`, and validator endpoints
- `cypher_template.txt` — the current single static prompt/schema template (v4) that Phase 29 supersedes; contains the exact schema rules (allowed labels/relationships, semantic mapping, identifiers, quality checks) the new catalog + validator must preserve and generalize
- n8n `rules-to-metagraph.json` — "Build LLM Prompt" (constructs 4000+ char prompt with schema/few-shot/existing entities), "Fetch Existing Entities" (queries Neo4j for existing Classes/Properties/Rules), "Parse LLM Output" (bracket nesting, dedup validation) — all three collapse into the new assembler + validator
- n8n `graph-query-mcp.json` — "Build Cypher Prompt" (live schema + v3 data model + guidance), "Smart Overrides" (keyword-matching for "list rules", height/maximum patterns) — the keyword-matching precedent for CTXA-01's deterministic scoping

### Established Patterns
- "Gateway owns all LLM logic, n8n stays thin" (Phase 28 D-05/D-07) — the operating principle this phase extends to context assembly and validation
- FastAPI Pydantic models + `@app.post`/`@app.get` + `HTTPException` (data-service/app.py) — the endpoint pattern to follow
- `SCHEMA VERSION: v4.0` header convention (`cypher_template.txt`) — reused for the new catalog's integer version field
- ErrorMessageTemplates What+Where+How-to-fix pattern (C# side, `DG.Core.Services`) — the structured-error vocabulary the new Cypher violation codes should feel consistent with

### Integration Points
- `POST /context/assemble` (new) — called by n8n's Build LLM Prompt / Build Cypher Prompt nodes before `/llm/generate`
- `GET /context/debug` (new) — same params as assemble, for inspection (success criterion 1)
- New Cypher validator function/endpoint — called after LLM generates Cypher, before Neo4j `tx/commit` execution
- `llm/cypher_catalog.json` (new) — read by `dg_context.py`
- `DesignGrammar-V7.owl` — read by `dg_context.py` for both the Ontograph/Metagraph concept catalog and the Computgraph catalog block
- Live Neo4j OntoGraph query — unioned with the static catalog for per-project existing entities

</code_context>

<specifics>
## Specific Ideas

- Retry loop is 2 retries (3 attempts total), data-service-internal, re-calling the LLM gateway with structured violations appended as corrective feedback — n8n never sees the intermediate failed attempts
- Structured violations: `{valid, violations:[{code, message, path?}]}`
- Six catalog shapes: max limit, min limit, range, ratio, boolean requirement, existence/count — range preserves the existing two-rule emission convention; existence/count is new territory modeled as a `swrlb:` builtin atom pair
- Debug endpoint and real assemble endpoint share the exact same param contract — this is a deliberate correctness guarantee, not just convenience

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. All four grey areas resolved with the recommended defaults; no scope-creep items raised.

</deferred>

---

*Phase: 29-DG-Aware Context Layer (SWRL + Ontology + Cypher Awareness)*
*Context gathered: 2026-07-12*
