# Phase 29: DG-Aware Context Layer (SWRL + Ontology + Cypher Awareness) - Research

**Researched:** 2026-07-12
**Domain:** Python/FastAPI data-service internals + n8n JSON workflow surgery (no Grasshopper/C#, no frontend)
**Confidence:** HIGH

## Summary

Phase 29 replaces one static prompt-building path (`cypher_template.txt` inlined into n8n Function nodes) with a deterministic, testable Python module (`data-service/dg_context.py`) plus a versioned JSON catalog (`llm/cypher_catalog.json`), following the exact module-layout precedent already established twice in this codebase by `connectors.py` (Phase 812/824) and `reasoner.py` (Phase 814): a small registry/data module with `load_*`/`save_*` JSON persistence helpers, Pydantic request/response models, and FastAPI routes in `app.py` that stay thin wrappers. All the actual schema knowledge Phase 29 must generalize already exists in one file — `cypher_template.txt` — and its exact duplicate logic embedded in n8n's "Build LLM Prompt" (ingest) and "Build Cypher Prompt" (query) Function nodes. There is no ambiguity about what the new catalog must preserve: allowed labels/relationships, the `SWRL`/`SWRL_label`/`Rule_Id`/`Atom_Id` naming quirks, the inverted violation-pattern semantic mapping, the two-rule range convention, and the `` `order` ``/`` `pos` `` backtick-quoting rule.

The retry loop's call-back-into-the-gateway shape has a direct precedent in `llm_generate()` (`app.py:996-1027`) which already resolves `provider`/`model`/`api_key` via `resolve_active_provider()` and calls `adapter.generate()` — the new internal retry function in `dg_context.py`/`app.py` should call this same resolve→adapter→generate sequence directly (in-process function calls, not a second HTTP round-trip to `/llm/generate`) since both live in the same FastAPI process. The Cypher validator's job is a straight port of what n8n's "Parse LLM Output" (rules-to-metagraph.json) and the inline label/relationship-checking regex block in "Parse Cypher" (graph-query-mcp.json) already do ad hoc in JavaScript — bracket-nesting balance check, unknown-label/relationship/property detection against an allow-list, and the `Rule_Id`/`Atom_Id` key-name checks from the QUALITY CHECKS section of `cypher_template.txt`.

The Computgraph catalog block sources cleanly from `ontology/DesignGrammar-V7.owl` — it is RDF/XML with a `dgc:` namespace prefix declared at the document root (`xmlns:dgc="&dgc;"`), a single `dgc:Computgraph` hub class (line 2261), five `dgc:` entity classes (Algorithm, Procedure, Pattern, Parameter, Interface) each tagged `<dg:graph rdf:resource="&dgc;Computgraph"/>`, and one fully worked example (the "Frame" object, lines 2719-2930) that is the canonical few-shot RCGN (Phase 35) will reuse. Phase 29 only needs to parse this file (via a Python XML/RDF parser — no `rdflib` currently in `requirements.txt`) and expose it as a static Python data structure or a small extracted JSON; wiring it into live context selection is explicitly out of scope.

**Primary recommendation:** Build `dg_context.py` as a peer to `connectors.py`/`reasoner.py` — same file layout template (registry constants → Pydantic models → load/save or parse helpers → assembly functions) — with `llm/cypher_catalog.json` as a standalone versioned JSON loaded at import time or per-request (mirroring how `llm_gateway.py` reads its own JSON settings file), and wire the new endpoints into `app.py` immediately after the existing `/llm/*` block using the exact `_structured_error_response()` pattern already proven at `/reasoner/consistency`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Context assembly (ontology + SWRL + Cypher catalog selection) | API/Backend (data-service) | — | New `dg_context.py` module; deterministic keyword/entity matching against Neo4j + static files, no client involvement |
| Cypher validation + retry loop | API/Backend (data-service) | — | Calls back into the in-process LLM gateway (`llm_gateway.py` adapters), never touches Neo4j until valid |
| Cypher expression catalog storage | API/Backend (data-service, `llm/` dir) | — | Static versioned JSON, read by `dg_context.py`; not a DB-backed resource |
| Ontology/Computgraph concept source | API/Backend (data-service, `ontology/` dir) | — | `DesignGrammar-V7.owl` parsed by `dg_context.py`; static file, not runtime-editable |
| Live per-project entity union | API/Backend (data-service) → Database | Database (Neo4j) | `dg_context.py` unions static catalog with a live `neo4j_schema`-style query, same pattern as today's n8n "Fetch Existing Entities" |
| n8n prompt nodes | Orchestration (n8n) | — | Reduced to thin HTTP callers of `/context/assemble`; all prompt-construction logic moves out of n8n Function nodes |
| Cypher execution | Database (Neo4j, via n8n's `tx/commit`) | — | Unchanged — n8n still POSTs the (now pre-validated) Cypher to Neo4j's HTTP transaction endpoint |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (pinned unversioned in `requirements.txt`, live install currently resolves 0.11x-class) | New `/context/assemble`, `/context/debug` endpoints | Already the app framework; `app.py` has 40+ existing `@app.get`/`@app.post` routes to follow |
| pydantic | bundled with FastAPI (v2-class, matches `BaseModel` usage throughout `app.py`/`llm_gateway.py`) | Request/response models for the new endpoints | Every existing endpoint in this codebase uses Pydantic `BaseModel` — no exception should be made here |
| httpx | (unversioned, sync `httpx.Client`) | N/A for new context code — retry loop should call adapters in-process, not via httpx | `llm_gateway.py` adapters already use `httpx.Client(timeout=...)`; the retry loop reuses these adapter objects directly rather than re-entering via HTTP |
| pytest | (unversioned) | Unit tests for `dg_context.py` assembler + validator | Existing `data-service/tests/` suite (`test_reasoner.py`, `test_connectors.py`, `test_llm_gateway.py`) is 100% pytest + FastAPI `TestClient` |

**Version verification:** `data-service/requirements.txt` pins no versions for `fastapi`, `httpx`, `neo4j`, `pytest`, `cryptography`, `uvicorn` — only `specklepy==3.2.4` is pinned `[VERIFIED: data-service/requirements.txt]`. This means the actual installed versions are resolved at Docker build time; there is no drift risk to introduce here since Phase 29 adds zero new third-party dependencies (see Package Legitimacy Audit below — nothing new to install).

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `xml.etree.ElementTree` (stdlib) | Python 3.13 stdlib | Parse `DesignGrammar-V7.owl` (RDF/XML) to extract `dgc:` classes | No new dependency needed — the file uses simple RDF/XML with entity refs (`&dgc;`); stdlib `ElementTree` with a custom entity resolver, or a regex-based extraction pass (matching the existing `apply_v7_rename.py`/`apply_v7_extensions.py` scripts' approach — see below), both avoid adding `rdflib` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib XML parsing of the OWL file | `rdflib` (proper RDF/OWL library) | `rdflib` is not in `requirements.txt` and would be a new dependency for a forward-prep-only, read-once-at-startup parse; the OWL file's DOCTYPE entity block (`<!ENTITY dgc "...">`) makes raw `ElementTree` parsing non-trivial (XML entity expansion needs the DOCTYPE processed) — `[ASSUMED]` this needs verification during implementation: check whether `ontology/export_to_markdown_v7.py` or `apply_v7_extensions.py` already contain a working OWL-parsing routine that can be reused instead of writing a new one |
| In-process adapter reuse for the retry loop | A second internal HTTP call to `POST /llm/generate` | In-process (`get_adapter()` + `adapter.generate()` called directly from the new retry function) avoids one extra network hop per retry attempt (up to 3 total per CONTEXT.md's bound) and avoids re-resolving `resolve_active_provider()` redundantly through a second HTTP boundary; the tradeoff is the retry function must import `llm_gateway` directly (already done via `from llm_gateway import ...` in `app.py`) |

**Installation:**
```bash
# No new packages required — dg_context.py uses only stdlib (json, pathlib, re, xml.etree)
# plus objects already imported from llm_gateway.py (get_adapter, resolve_active_provider, GenerateRequest)
```

## Package Legitimacy Audit

Not applicable — Phase 29 introduces zero new third-party packages. All work is done with Python stdlib plus the already-vetted `llm_gateway.py`/`app.py` imports (`fastapi`, `pydantic`, `httpx`, `neo4j` — all pre-existing in `requirements.txt`, confirmed via `[VERIFIED: data-service/requirements.txt]`).

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
n8n "Ingest Rules" webhook (rules-to-metagraph.json)
  │
  ├─(1)─▶ POST /context/assemble {type: "rule_ingest", rules_text, project}   [NEW]
  │         │
  │         ▼
  │       dg_context.py: assemble_context()
  │         ├─ load static V7 ontology catalog block (parsed once from DesignGrammar-V7.owl)
  │         ├─ load SWRL convention block (Python dict/dataclass, near dg_context.py)
  │         ├─ load llm/cypher_catalog.json (versioned shapes)
  │         ├─ deterministic keyword match (rules_text → relevant catalog shape(s))
  │         └─ UNION with live Neo4j query for project's existing Class/DatatypeProperty
  │               (replaces today's n8n "Fetch Existing Entities" HTTP node)
  │         ◀── returns assembled context JSON
  │
  ├─(2)─▶ n8n builds the final LLM prompt string from the assembled context (thin — string join only)
  │
  ├─(3)─▶ POST /llm/generate {prompt, provider:null, model:null}    [EXISTING, unchanged contract]
  │         │
  │         ▼
  │       llm_gateway.resolve_active_provider() → get_adapter() → adapter.generate()
  │         ◀── returns {text, provider, model, usage}
  │
  ├─(4)─▶ POST /context/validate {cypher: <llm output>, ...}    [NEW — or same call as (1)? see Open Questions]
  │         │
  │         ▼
  │       Cypher validator (bracket nesting, label/rel/prop allow-list, kind enum, Rule_Id/Atom_Id key checks)
  │         │
  │         ├─ valid=true  → n8n receives {valid:true, cypher: <clean>}
  │         └─ valid=false → INTERNAL retry loop (up to 2 retries):
  │                            re-call llm_gateway adapter.generate() with structured
  │                            violations appended as corrective feedback to the prompt
  │                            (in-process, n8n never sees intermediate attempts)
  │                            └─ exhausted → n8n receives {valid:false, violations:[...]}
  │
  └─(5)─▶ n8n "Execute LLM Cypher" → Neo4j /db/neo4j/tx/commit   [EXISTING, unchanged]
              (only reached if validator returned valid:true)

Parallel path — n8n "Ingest Prompt" webhook (graph-query-mcp.json):
  same (1)-(3) shape with type: "graph_query", context includes live neo4j_schema()
  result (labels/relationship_types/property_keys/graphs/projects) UNIONed with static
  catalog — replaces "Fetch Graph Context (MCP)" + "Build Cypher Prompt" node logic.

GET /context/debug?type=...&...   [NEW — same param contract as /context/assemble]
  → returns the exact same assembled context JSON, for human inspection
    (success criterion 1: inspect that a "maximum height" rule's context contains
    the max-limit shape + the referenced V7 concepts)
```

### Recommended Project Structure
```
data-service/
├── app.py                  # add /context/assemble, /context/debug, /context/validate routes here
├── dg_context.py           # NEW — context assembler + Cypher validator + retry orchestration
├── llm_gateway.py          # UNCHANGED — reused via get_adapter()/resolve_active_provider() imports
├── connectors.py           # unchanged — layout precedent only
├── reasoner.py             # unchanged — layout precedent only
└── tests/
    ├── test_dg_context.py  # NEW — mirrors test_reasoner.py structure

llm/
└── cypher_catalog.json     # NEW — versioned {version, shapes:[{id,name,description,swrl_pattern,cypher_template,worked_example}]}

ontology/
└── DesignGrammar-V7.owl    # UNCHANGED, read-only source for dg_context.py's Computgraph + V7 concept parsing

n8n/workflows/
├── rules-to-metagraph.json # MODIFY — "Build LLM Prompt", "Fetch Existing Entities", "Parse LLM Output" → thin callers
└── graph-query-mcp.json    # MODIFY — "Build Cypher Prompt", "Smart Overrides" → thin callers
```

### Pattern 1: Settings-file-style module with static registry + dynamic union
**What:** `connectors.py` and `reasoner.py` both follow: module-level constant registry (`CONNECTOR_REGISTRY`, `REASONER_REGISTRY`) → Pydantic models → `DATA_DIR`/file-path module constant (patched in tests via `monkeypatch.setattr`) → `load_*()`/`save_*()` JSON helpers with defensive empty-dict/list fallbacks on missing/malformed files.
**When to use:** `dg_context.py`'s static SWRL-convention block and Computgraph catalog block should follow this exact shape — module-level Python dict/list constants, not re-parsed per request unless the source file changes (OWL file is static within a deployment).
**Example:**
```python
# Source: data-service/reasoner.py:20-41 (existing pattern to mirror)
REASONER_REGISTRY: list[dict[str, str]] = [
    {"id": "hermit", "name": "HermiT", "description": "...", "status": "integrated"},
]
DATA_DIR = Path(os.getenv("DG_DATA_DIR", "/app/data"))
REASONER_SETTINGS_FILE = DATA_DIR / "reasoner-settings.json"

def load_settings() -> dict[str, Any]:
    if not REASONER_SETTINGS_FILE.exists():
        return {}
    try:
        payload = json.loads(REASONER_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload
```
For `dg_context.py`, `llm/cypher_catalog.json` is a project-root artifact (not `DATA_DIR`-scoped like settings), so its load helper should resolve relative to the repo/container root (e.g. `Path(__file__).resolve().parent.parent / "llm" / "cypher_catalog.json"` — verify the actual Docker `WORKDIR`/volume-mount path for `data-service` at implementation time, since `llm/` currently has no analog inside `data-service/Dockerfile`'s COPY scope — see Open Questions).

### Pattern 2: Thin sidecar-style proxy with `_structured_error_response()`
**What:** `POST /reasoner/consistency` (`app.py:1196-1242`) is the closest existing precedent for a data-service endpoint that (a) accepts a Pydantic payload, (b) does a bounded/timed piece of work, (c) returns either a success body or a `_structured_error_response(error, hint, code, status_code)` — exactly the `{error, hint, code}` shape CONTEXT.md's `{valid, violations:[{code, message, path?}]}` should mirror stylistically (per the "ErrorMessageTemplates What+Where+How-to-fix pattern" callout in CONTEXT.md's Established Patterns).
**When to use:** Both `/context/assemble` and the Cypher validator endpoint.
**Example:**
```python
# Source: data-service/app.py:575-580
def _structured_error_response(error: str, hint: str, code: str, status_code: int = 500) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": error, "hint": hint, "code": code})
```
The validator's per-violation shape (`{code, message, path?}`) is a peer/plural form of this same triple — reuse the same vocabulary discipline (short stable `code`, human `message`, optional `path` pointing at the offending Cypher fragment or node type).

### Pattern 3: In-process adapter reuse for the retry loop
**What:** `llm_generate()` (`app.py:996-1027`) already shows the full resolve→override→adapter→generate→map-errors sequence. The Cypher validator's internal retry loop should call the *same* sequence directly as a Python function call — not re-POST to `/llm/generate` — because both run in the same FastAPI process and avoid an unnecessary network round-trip per retry attempt.
**When to use:** Inside `dg_context.py`'s retry orchestration function.
**Example:**
```python
# Source: data-service/app.py:996-1027 (pattern to replicate as a direct function call, not HTTP)
provider, model, api_key = resolve_active_provider(settings, master_secret)
adapter = get_adapter(provider, settings.get("baseUrl"))
response = adapter.generate(req_with_model, api_key)  # GenerateResponse
```

### Anti-Patterns to Avoid
- **Re-POSTing to `/llm/generate` from inside the retry loop:** Adds latency (this is a synchronous HTTP + polling architecture per CLAUDE.md — "No message queue") and duplicates provider-resolution work already done once. Call the adapter directly.
- **Embedding the Cypher catalog inside `dg_context.py` as Python literals:** CONTEXT.md explicitly locks `llm/cypher_catalog.json` as a separate versioned JSON artifact — do not inline the six shapes as Python dicts even though the SWRL-convention/Computgraph blocks *do* live as Python data near `dg_context.py`.
- **Parsing the OWL file per-request:** `DesignGrammar-V7.owl` is a large static file (2900+ lines); parse once (module import time or lazy-cached-on-first-call) and hold the extracted Computgraph catalog in memory, matching how `_ollama_models_cache` in `llm_gateway.py` caches expensive discovery work.
- **Skipping the `Rule_Id`/`Atom_Id` key-name QUALITY CHECKS from `cypher_template.txt`:** These are non-obvious ("Rule key is Rule_Id (not id)", "DatatypeProperty display property is SWRL_label (not label)") and are exactly the class of subtle regression the validator exists to catch — carry every line of the `QUALITY CHECKS` section (`cypher_template.txt:197-206`) into the validator's check list, not just bracket-balance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bracket-nesting validation | A new from-scratch parser | Port the existing `hasValidNesting()` JS logic (rules-to-metagraph.json "Parse LLM Output" node) to Python almost line-for-line — it already handles the quoted-string-exclusion edge case (`str.replace(/'[^']*'/g, '')` before stack-matching) | This exact function is already battle-tested against live LLM output noise (MERME/MERX typos, unbalanced quotes) — re-deriving it from scratch risks regressing on cases the current n8n node already handles |
| Label/relationship/property allow-list checking | New regex from scratch | Port `graph-query-mcp.json`'s "Parse Cypher" node regexes (`labelRegex`, `relRegex`, `propRegex` — lines matching `\(\s*[^\)]*:\s*([A-Za-z_][A-Za-z0-9_]*)`, `-\s*\[[^\]]*:\s*([A-Za-z_][A-Za-z0-9_|]*)`, `\.([A-Za-z_][A-Za-z0-9_]*)\b`) to Python | Same rationale — these regexes are already tuned against real LLM Cypher output shapes in production for months; a rewrite risks missing an edge case (e.g. multi-label nodes `n:LabelA:LabelB`, pipe-separated relationship types `HAS_BODY\|HAS_HEAD`) |
| RDF/OWL parsing | A hand-rolled XML-entity-expanding regex scraper | First check whether `ontology/export_to_markdown_v7.py` (already used by `make_docs_v7.py`) has reusable OWL-parsing code — it already walks this exact file to generate `DesignGrammar-V7.md` | Avoids duplicating OWL-parsing logic; `[ASSUMED — verify at implementation time]` whether this script exposes an importable function vs. being a standalone CLI |
| Project-scoped Neo4j entity queries | New Cypher from scratch | Port the existing "Fetch Existing Entities" node's Cypher verbatim (`app.py`/n8n node, lines ~294-312 of `rules-to-metagraph.json`) — `MATCH (n) WHERE (n:Class OR n:DatatypeProperty OR n:ObjectProperty) AND n.graph = 'OntoGraph' RETURN labels(n)[0] AS nodeLabel, n.iri AS iri, ...` | Exact schema-correct query already proven against the live schema; re-deriving risks subtle column-order or coalesce-fallback (`coalesce(n.label, '')`) mismatches |

**Key insight:** Nearly everything Phase 29 needs already exists as working code in three places — `cypher_template.txt` (the schema rules), the two n8n JSON workflow files (the JS implementations of prompt-building and validation), and `llm_gateway.py`/`app.py` (the FastAPI + adapter call pattern). This phase is fundamentally a **port-and-centralize** exercise, not a from-scratch design — the highest-risk failure mode is silently dropping a rule or regex nuance during the JS→Python port, not inventing new logic.

## Common Pitfalls

### Pitfall 1: Losing the `Var` merge key's `project` component
**What goes wrong:** `cypher_template.txt` (line 44) and `spec/DATABASE.md` (line 49) show `Var` keyed differently — `cypher_template.txt` says `key: name (?<varName>) + project`; `spec/DATABASE.md`'s example omits `project` from the key entirely (`(:Var {name: "b", graph: "Metagraph", project: "1"})` — project is a property there, not explicitly called out as part of the merge key). STATE.md confirms this was a real historical bug: "Var merge key includes `project` — fixes latent v2.0 cross-project collision bug" (v2.0 decisions carried forward).
**Why it happens:** `spec/DATABASE.md` is stale relative to `cypher_template.txt` — it still says "v3→v4 migration notes (complete)" as its newest section and does not mention the Computgraph layer at all, while `cypher_template.txt`'s header says `SCHEMA VERSION: v4.0` and is the file n8n's prompt nodes actually embed verbatim.
**How to avoid:** Treat `cypher_template.txt` as the single source of truth for catalog content, not `spec/DATABASE.md` — the validator and catalog must match `cypher_template.txt`'s `Var` key definition (`name + project`) exactly, since that's what n8n's few-shot example and QUALITY CHECKS section actually enforce today.
**Warning signs:** If the new catalog's `existence/count` shape (new territory, no prior art) defines a `Var` MERGE without the `project` property in its key match clause, cross-project variable collisions will silently reappear.

### Pitfall 2: n8n live workflows have drifted ahead of the repo JSON files
**What goes wrong:** STATE.md's Pending Todos explicitly flags: "live n8n workflows drifted ahead of `n8n/workflows/*.json` (user editor changes, versionCounter 22); repo JSONs carry the quote-syntax + project_name body-fallback fixes — export live → repo or re-import repo → live" — unresolved as of this research date (2026-07-12).
**Why it happens:** n8n's live instance state (SQLite) is the actual runtime source, while the repo JSON files are periodically exported/re-imported; edits made directly in the n8n editor UI do not automatically sync back to git.
**How to avoid:** Before planning changes to "Build LLM Prompt"/"Build Cypher Prompt"/"Fetch Existing Entities"/"Parse LLM Output"/"Smart Overrides" nodes, the plan should include a task to export the LIVE n8n workflow JSON (via n8n's UI export or API) and diff it against the repo's `rules-to-metagraph.json`/`graph-query-mcp.json` before editing — otherwise the phase risks "fixing" a repo file that the live instance has already diverged from, or worse, re-importing repo JSON that clobbers live-only fixes.
**Warning signs:** If the live n8n instance's "Build Cypher Prompt" node behaves differently from what's read in this research (e.g. no quote-syntax bug), that confirms drift and the plan must reconcile before touching these nodes.

### Pitfall 3: `Rule_Id` format collision on edit (numeric-limit-in-ID)
**What goes wrong:** `cypher_template.txt`'s `IDENTIFIERS` section and the n8n "Build LLM Prompt" EDIT MODE instructions both embed the numeric threshold *inside* the Rule_Id itself (`R_URB_HEIGHT_MAX_75_V` → editing to 80m becomes `R_URB_HEIGHT_MAX_80_V`, a **different** node key). CONTEXT.md's edit contract says "preserve `iri`/`SWRL_label`, change only `Literal` values" — but the current n8n prompt tells the LLM to *change* `Rule_Id` on numeric edits ("Update Rule_Id to reflect the new numeric limit").
**Why it happens:** The Rule_Id embeds the limit value by convention, so a pure "change only Literal values" edit contract is inconsistent with the existing Rule_Id-regeneration behavior unless the old Rule node is also cleaned up (which "Prepare Graph Payload" already does via `cleanupStatements` MATCH-DELETE).
**How to avoid:** When designing the `rule_edit` request type in `dg_context.py`, decide explicitly whether the assembled context instructs the LLM to keep Rule_Id stable (contradicts existing convention, requires a naming-convention change) or regenerate it (matches existing behavior, requires the MATCH-DELETE cleanup path to survive the port) — flag this as a planning-time decision, not an implementation detail, since it affects both the catalog's edit guidance text and whether "old-atom MATCH-DELETE cleanup" (mentioned in RING-02, Phase 31) still applies unchanged.
**Warning signs:** A `checkpoint:human-verify` or explicit CONTEXT.md-derived task should confirm which convention Phase 29's `rule_edit` context type documents — this directly affects RING-02's diff-preview design in the next phase.

### Pitfall 4: OWL file's DOCTYPE entity block breaks naive XML parsing
**What goes wrong:** `DesignGrammar-V7.owl` uses XML internal DTD entities (`xmlns:dgc="&dgc;"` — the `&dgc;` is an entity reference, not inline text) declared in a `<!DOCTYPE ... [ <!ENTITY dgc "..."> ... ]>` header block. Python's `xml.etree.ElementTree` by default does NOT process external/internal general entities the way a full XML processor would for some entity patterns, and `ElementTree.parse()` can raise `xml.etree.ElementTree.ParseError: undefined entity` if the parser doesn't see the DOCTYPE internal subset correctly.
**Why it happens:** RDF/XML files commonly use this entity-shorthand convention (seen across all the `ontology/*.owl` files, not just V7) to keep IRIs short in the markup; it's valid XML but requires the parser to process the internal DTD subset.
**How to avoid:** `[ASSUMED — verify at implementation time]` Test `ElementTree.parse()` against `DesignGrammar-V7.owl` directly before committing to stdlib-only parsing; if it fails, either (a) use `xml.sax` with a custom `EntityResolver`, (b) pre-process the file to inline entity values via string substitution (simple, since the entity table is small and fixed), or (c) check whether `ontology/export_to_markdown_v7.py` already solved this problem (Don't Hand-Roll #3).
**Warning signs:** A `ParseError` or entity-reference-as-literal-text (`&dgc;Computgraph` appearing unresolved) in the extracted Computgraph catalog block.

## Code Examples

### FastAPI endpoint with Pydantic model + structured error (pattern to copy for /context/assemble)
```python
# Source: data-service/app.py:1191-1242 (ReasonerConsistencyRequest + post_reasoner_consistency)
class ReasonerConsistencyRequest(BaseModel):
    project: str
    engine: str = "hermit"

@app.post("/reasoner/consistency")
def post_reasoner_consistency(payload: ReasonerConsistencyRequest):
    try:
        response = httpx.post(...)
    except httpx.TimeoutException:
        raise _structured_error_response("...", "...", "REASONER_TIMEOUT", 504)
    except httpx.ConnectError:
        raise _structured_error_response("...", "...", "REASONER_UNAVAILABLE", 502)
    ...
```

### Retry-with-corrective-feedback shape (new — no direct precedent, derive from llm_generate())
```python
# Composition of app.py:996-1027 (llm_generate) + a new violations-append step
def generate_validated_cypher(prompt: str, max_retries: int = 2) -> dict:
    settings = load_persisted_llm_settings()
    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    provider, model, api_key = resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))

    current_prompt = prompt
    for attempt in range(max_retries + 1):  # 3 attempts total per CONTEXT.md
        req = GenerateRequest(prompt=current_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key)
        validation = validate_cypher(response.text)
        if validation["valid"]:
            return {"cypher": response.text, "attempts": attempt + 1}
        current_prompt = append_corrective_feedback(prompt, validation["violations"])
    return {"valid": False, "violations": validation["violations"]}
```

### Bracket-nesting check (port target from n8n "Parse LLM Output")
```javascript
// Source: n8n/workflows/rules-to-metagraph.json, "Parse LLM Output" node functionCode
function hasValidNesting(str) {
  const u = str.replace(/'[^']*'/g, '');  // strip quoted strings first
  const stack = [];
  const opn = {'(':')','{':'}','[':']'};
  for (const c of u) {
    if (opn[c]) stack.push(c);
    else if (c === ')' || c === '}' || c === ']') {
      if (!stack.length || opn[stack.pop()] !== c) return false;
    }
  }
  return !stack.length;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Static `cypher_template.txt` inlined verbatim into n8n Function-node JS string-building | Deterministic `dg_context.py` assembler + versioned `llm/cypher_catalog.json` | Phase 29 (this phase) | n8n Function nodes shrink from ~4000-char inline JS prompt-builders to thin HTTP callers; schema changes become a JSON/Python edit instead of a triple edit across `cypher_template.txt` + 2 n8n node JS strings |
| Ad hoc bracket/dedup validation in n8n "Parse LLM Output" (JS, untested) | pytest-covered Python validator in `dg_context.py` | Phase 29 | CTXA-04's "testable, pytest-covered validator" requirement |
| No retry on invalid Cypher — first LLM output either works or the ingest fails downstream at Neo4j `tx/commit` | Bounded 2-retry loop with structured violation feedback before Neo4j ever sees the Cypher | Phase 29 | Matches RING-04 (Phase 31 reuses the same retry-bound language) |

**Deprecated/outdated:**
- `spec/DATABASE.md`'s schema documentation is stale relative to `cypher_template.txt` (still headed "v3→v4 migration notes (complete)" with no Computgraph mention) — do not treat it as authoritative for the new catalog; use `cypher_template.txt` as ground truth and update `spec/DATABASE.md` per the Schema Change Propagation checklist if Phase 29 changes any schema-visible behavior (it should not, since Phase 29 generalizes existing rules rather than changing the schema itself — but the six-shape catalog, especially the new existence/count shape, should still get a `spec/DATABASE.md` mention for consistency).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ontology/export_to_markdown_v7.py` contains reusable OWL-parsing code that can be imported rather than reimplemented | Don't Hand-Roll, Pitfall 4 | Low — worst case, implementer writes a fresh (small) parser; wastes at most an hour rediscovering this |
| A2 | `ElementTree.parse()` will fail or need a workaround on `DesignGrammar-V7.owl`'s DOCTYPE entity block without verification | Standard Stack (Supporting), Pitfall 4 | Medium — if wrong, the planned "check reusable script first, else regex-extract" fallback path is unnecessary complexity; if right and unaddressed, `dg_context.py`'s Computgraph parsing silently fails or half-parses |
| A3 | `llm/cypher_catalog.json`'s file path should resolve relative to a fixed location not yet wired into `data-service/Dockerfile`'s COPY scope — the exact Docker path/volume-mount for `llm/` from `data-service`'s container is unconfirmed | Recommended Project Structure, Open Questions | Medium — if the plan doesn't add a Dockerfile COPY line or volume mount for `llm/`, the catalog file will be unreadable at runtime inside the container even though it exists in the repo |
| A4 | The retry loop should call `llm_gateway` adapters in-process rather than re-POST to `/llm/generate` | Architecture Patterns Pattern 3, Don't Hand-Roll | Low-Medium — CONTEXT.md doesn't explicitly say "in-process vs HTTP," only that n8n never sees intermediate attempts; if planner instead chooses a loopback HTTP call to `/llm/generate` from within the validator endpoint, it still satisfies CONTEXT.md's contract, just with slightly more latency overhead — not a correctness risk, only a design-quality one |

**If this table is empty:** N/A — see entries above.

## Open Questions

1. **Should `/context/validate` be a separate endpoint from `/context/assemble`, or is the validator only invoked internally by the retry loop with no standalone HTTP surface?**
   - What we know: CONTEXT.md's decisions describe "Validation runs as a new data-service function/endpoint" (ambiguous — function OR endpoint) and separately describes the retry loop as "data-service retries internally... n8n makes one call and gets back valid Cypher or a final structured error." Success criterion 2 ("Deliberately corrupting the LLM output... is caught by the validator... returned as a structured violation list") implies the validator's output shape must be independently inspectable/testable.
   - What's unclear: Whether n8n calls one endpoint (e.g. `/context/generate-cypher` wrapping assemble+generate+validate+retry in one call) or two (`/context/assemble` then a separate `/llm/generate` then a separate `/context/validate`), given CONTEXT.md never names a third endpoint explicitly beyond `/context/assemble` and `/context/debug`.
   - Recommendation: The planner should design one additional endpoint (name TBD, e.g. `POST /context/generate-cypher` or extend the retry loop as a mode within `/llm/generate` itself) that wraps prompt-in → validated-cypher-out as a single n8n-facing call, since CONTEXT.md is explicit that "n8n makes one call" for this step — the validator function itself stays internal/importable for pytest coverage (matching `validate_cypher()` as a plain testable function, called both by this new endpoint and directly by tests), which resolves the ambiguity: function for testability, no separate HTTP surface required unless the planner decides debug/inspection value justifies one.

2. **Where does `llm/cypher_catalog.json` physically live relative to `data-service`'s Docker build context, and does the Dockerfile need a new COPY line?**
   - What we know: `cypher_template.txt` currently lives at the repo root (sibling to `docker-compose.yml`, NOT inside `data-service/`) and appears to be read only by n8n's inlined JS (not by data-service at all — grep found no data-service reference to `cypher_template.txt`). `llm/cypher_catalog.json` is specified as a new top-level `llm/` directory per the ROADMAP deliverable list.
   - What's unclear: Whether `data-service/Dockerfile` needs a `COPY ../llm /app/llm` (requires moving the Docker build context, since Docker COPY can't reach outside the build context by default) or whether `llm/cypher_catalog.json` should instead live inside `data-service/llm/` to stay within the existing build context.
   - Recommendation: The planner should read `data-service/Dockerfile` and `docker-compose.yml`'s `build:` context for `data-service` (`./data-service`, confirmed at `docker-compose.yml:33`) before finalizing the exact path — `llm/cypher_catalog.json` at the repo root will NOT be visible inside the `data-service` container unless either (a) the file lives inside `data-service/llm/cypher_catalog.json` instead, or (b) the Docker build context is widened, or (c) it's volume-mounted like `./data-service/data:/app/data` already is. This is a concrete implementation blocker, not a stylistic choice — flag it for the plan's first task.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | data-service runtime | ✓ (host) | 3.13.7 | Runs inside Docker (`data-service` container) regardless of host version — host Python version is informational only |
| Docker | Running/testing the full stack | ✓ | 29.1.3 | — |
| pytest | Running data-service test suite | ✗ (not on host PATH) | — | Run via `docker compose exec data-service pytest` or a local venv with `pip install -r data-service/requirements.txt`; existing test files (`test_reasoner.py` etc.) already assume this workflow (`sys.path.insert` + `os.environ.setdefault` boilerplate at the top of each test file is designed for exactly this) |
| Neo4j | Live entity union query (CTXA-01) | Not probed this session (requires `docker compose up`) | — | N/A — required for full E2E testing; unit tests should mock/stub the Neo4j session per the existing `FixtureSession` duck-typing pattern noted in STATE.md (Phase 821 Plan 02) |
| n8n | Thin-caller workflow changes | Not probed this session | — | Workflow JSON edits can be authored/reviewed without a live n8n instance, but end-to-end verification requires `docker compose up` + the live n8n editor (see Pitfall 2 — live workflows have drifted from repo JSON) |

**Missing dependencies with no fallback:** none — all gaps have a documented fallback above.

**Missing dependencies with fallback:** pytest (use Docker exec or local venv), Neo4j/n8n live verification (use `docker compose up` when ready for integration testing; unit-level work can proceed with mocks/fixtures).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (unversioned in `requirements.txt`) with FastAPI `TestClient` |
| Config file | none found — no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section in `data-service/`; tests rely on `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))` boilerplate per file (see `test_reasoner.py:18`) |
| Quick run command | `docker compose exec data-service pytest tests/test_dg_context.py -x` (new file) |
| Full suite command | `docker compose exec data-service pytest` (runs all of `data-service/tests/`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CTXA-01 | `/context/assemble` returns V7 concept subset per graph layer for `rule_ingest`/`rule_edit`/`graph_query` | unit + integration (TestClient) | `pytest tests/test_dg_context.py::TestContextAssemble -x` | ❌ Wave 0 |
| CTXA-02 | `llm/cypher_catalog.json` loads and exposes all 6 shapes with worked examples | unit | `pytest tests/test_dg_context.py::TestCypherCatalog -x` | ❌ Wave 0 |
| CTXA-03 | SWRL convention block (violation-inverted semantics, atom ordering, Var/Literal rules) is machine-readable and included in assembled context | unit | `pytest tests/test_dg_context.py::TestSwrlConventions -x` | ❌ Wave 0 |
| CTXA-04 | Validator catches corrupted Cypher (wrong label, bad `kind` enum) and returns structured violations; retry loop bounded at 2 retries | unit (validator) + integration (retry loop with mocked adapter, following `TestReasonerConsistencyProxy`'s `monkeypatch.setattr(app_module.httpx, "post", fake_post)` pattern but for `adapter.generate`) | `pytest tests/test_dg_context.py::TestValidator tests/test_dg_context.py::TestRetryLoop -x` | ❌ Wave 0 |
| CTXA-05 | Context selection is deterministic (no embeddings) — same request twice yields byte-identical assembled context | unit (idempotency assertion) | `pytest tests/test_dg_context.py::TestDeterminism -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `docker compose exec data-service pytest tests/test_dg_context.py -x`
- **Per wave merge:** `docker compose exec data-service pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus manual inspection of `GET /context/debug` for a "maximum height" rule (success criterion 1) and a deliberately-corrupted-Cypher validator run (success criterion 2)

### Wave 0 Gaps
- [ ] `data-service/tests/test_dg_context.py` — new test file, follow `test_reasoner.py`'s structure exactly (`isolated_store` fixture pattern if `dg_context.py` gains any persistence; likely not needed since the catalog/SWRL/Computgraph blocks are read-only)
- [ ] `llm/cypher_catalog.json` — the artifact itself must exist before any test can load it; first task in the plan
- [ ] Fixture: a small `dgc:` OWL snippet or the real `DesignGrammar-V7.owl` file for parser tests — reuse the live file (already checked into the repo) rather than authoring a synthetic fixture, so parser tests catch real-file parsing issues (Pitfall 4)
- [ ] Mock/stub for `adapter.generate()` in retry-loop tests — no existing fixture for this specific mock exists yet; follow `TestReasonerConsistencyProxy`'s `monkeypatch.setattr` pattern but targeting `llm_gateway.get_adapter` or the adapter instance's `.generate` method instead of `httpx.post`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 29 adds no new auth surface — `/context/*` endpoints are internal data-service routes, same trust boundary as existing `/llm/*`, `/reasoner/*` routes (no nginx-exposed public route implied unless the planner adds one; verify against `ui-v2/nginx.conf`'s proxy allow-list) |
| V3 Session Management | no | No session concept introduced |
| V4 Access Control | no | Same internal-service trust boundary as existing endpoints; no new privilege tiers |
| V5 Input Validation | yes | The Cypher validator IS the input-validation control for this phase — Pydantic models validate request shape (`type` enum for `rule_ingest`/`rule_edit`/`graph_query`), and the Cypher validator itself is the domain-specific injection-adjacent control (see Known Threat Patterns below) |
| V6 Cryptography | no | No new secrets/crypto — `LLM_MASTER_SECRET`/Fernet encryption is unchanged, owned entirely by `llm_gateway.py` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM-generated Cypher injection (malicious or malformed Cypher reaching `tx/commit` before validation) | Tampering | This IS what CTXA-04 exists to prevent — the validator's label/relationship/property allow-list check (already proven in n8n's "Parse Cypher" node) plus the bracket-nesting check together form a whitelist-based Cypher sanitization gate. **Do not** treat this as SQL/Cypher-injection-from-user-input in the traditional sense (the LLM's output, not a raw user string, reaches Neo4j) — the threat model is "hallucinated/malformed Cypher," not "malicious end-user injection," since n8n already interpolates `rules_text` as natural-language prompt content, never as raw Cypher |
| Prompt injection via `rules_text`/`prompt_text` (a user submits rule text designed to make the LLM emit Cypher outside the allowed schema, e.g. `DELETE`/`DETACH DELETE` statements) | Tampering/Elevation of Privilege | The existing `is_write_query()` check (`app.py`, used by the `/mcp` `neo4j_query` tool to block writes) is a precedent worth extending: the new Cypher validator should explicitly reject any Cypher containing `DELETE`, `REMOVE`, `DETACH`, `DROP`, or any verb outside `MERGE`/`SET` (per `cypher_template.txt`'s "OUTPUT RULES — Use only MERGE and SET") as a hard validation failure, not just an unknown-label violation — this is currently enforced only implicitly (the LLM is *told* to use only MERGE/SET, but nothing in the current n8n pipeline verifies it did) |
| Structured-error information disclosure (validator violation messages leaking internal schema details to an untrusted caller) | Information Disclosure | Low risk here — `/context/*` and `/llm/*` are internal service-to-service endpoints (n8n → data-service), not directly exposed to end users through nginx per the existing routing table in CLAUDE.md; violation messages can be verbose/technical without the LLMC-06-style "never include raw API key" concern that applies to `map_provider_error()`, since no secrets flow through Cypher validation |

## Sources

### Primary (HIGH confidence)
- `data-service/llm_gateway.py` (full file read) — adapter Strategy pattern, `resolve_active_provider()`, `get_adapter()`, encryption utilities `[VERIFIED: local file read]`
- `data-service/app.py` (relevant sections: imports, `/llm/*` routes, `/reasoner/*` routes, `_structured_error_response()`, `/mcp` endpoint) `[VERIFIED: local file read]`
- `data-service/connectors.py`, `data-service/reasoner.py` (full files) — module layout precedent `[VERIFIED: local file read]`
- `cypher_template.txt` (full file) — the exact schema/prompt content Phase 29 must generalize `[VERIFIED: local file read]`
- `n8n/workflows/rules-to-metagraph.json`, `n8n/workflows/graph-query-mcp.json` (full files) — exact node logic to port `[VERIFIED: local file read]`
- `ontology/DesignGrammar-V7.owl` (grepped sections: `dgc:` prefix declarations, `Computgraph` hub class, Frame worked example, Builtin individuals list) `[VERIFIED: local file read]`
- `spec/DATABASE.md` (full file) — cross-checked against `cypher_template.txt`, found stale in places (see Pitfall 1) `[VERIFIED: local file read]`
- `data-service/tests/test_reasoner.py`, `conftest.py` — pytest/TestClient conventions `[VERIFIED: local file read]`
- `.planning/milestones/v9.0-phases/29-.../29-CONTEXT.md` — all 16 locked decisions `[VERIFIED: local file read]`
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — requirement text and decision history `[VERIFIED: local file read]`

### Secondary (MEDIUM confidence)
- `data-service/requirements.txt` — confirms no version pins beyond `specklepy==3.2.4`, meaning no drift-risk from Phase 29 (adds zero new packages) `[VERIFIED: local file read]`

### Tertiary (LOW confidence)
- None — this phase required no external web research; all findings are grounded in direct codebase reads, consistent with the research_focus's explicit instruction to map locked decisions onto actual current code rather than re-litigate them externally.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, all patterns directly observed in existing code
- Architecture: HIGH — module layout, endpoint patterns, and retry-loop shape all have direct working precedents in this exact codebase
- Pitfalls: HIGH — all four pitfalls are grounded in actual file contents (stale docs, live/repo n8n drift documented in STATE.md, Rule_Id edit-convention conflict found by comparing CONTEXT.md against cypher_template.txt, OWL entity-parsing risk found by inspecting the actual XML)

**Research date:** 2026-07-12
**Valid until:** 30 days (stable internal codebase; revisit sooner if `n8n/workflows/*.json` are reconciled with the live instance before this phase executes, per STATE.md's Pending Todos, as that reconciliation could change the exact node content this research read)
