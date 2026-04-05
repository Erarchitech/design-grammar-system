# Project Research Summary

**Project:** Design Grammar System v1.1 — Project Knowledge Graph
**Domain:** LLM-assisted knowledge management integrated into an architecture compliance graph system
**Researched:** 2026-04-05
**Confidence:** HIGH (architecture based on direct codebase inspection), MEDIUM (feature patterns from AEC knowledge tool references)

## Executive Summary

The v1.1 Project Knowledge Graph milestone adds an LLM-assisted knowledge management layer to an existing, validated system. The architecture is an additive extension — not a redesign. All new capability routes through the three already-running services: FastAPI data-service (new `/knowledge/*` endpoints), n8n (two new webhook workflows), and Neo4j (new `KnowledgeGraph` label in the single existing database). Zero new Docker services, zero new npm packages, and at most one new pip package (`python-frontmatter`, optional) are required. This is the most important constraint to hold: every proposed feature must be implementable within the existing service boundaries.

The recommended approach follows five established patterns from the existing codebase. Knowledge nodes use the same `graph` + `project` property isolation already proven with `Metagraph`, `OntoGraph`, and `ValidationGraph`. LLM calls go through n8n webhook workflows using plain HTTP nodes to Ollama — no LangChain, no AI Agent nodes. Async results use the existing execution-result polling pattern. Session history stores as `KnowledgeSession` nodes in Neo4j, following the `ValidationRun` precedent. The one genuinely new pattern is the three-step Update flow (Match → Propose → Confirm), which is the key architectural differentiator: it prevents silent LLM overwrites and exposes proposed changes for user review before any write occurs.

The primary risks are UI complexity for the inline diff editor and Ollama contention under concurrent SWRL + knowledge queries. The diff editor risk is mitigated by using server-computed diffs (`difflib`, stdlib) rendered as HTML via `dangerouslySetInnerHTML` in a `<textarea>` + read-only diff panel pair — no client-side diff library, no `contenteditable` cursor management. The Ollama contention risk is documented but acceptable for single-user/small-team usage at this stage.

---

## Key Findings

### Recommended Stack

The v1.1 stack is almost entirely the existing stack. The only new capabilities are: Neo4j full-text index (built into Neo4j 5, no plugin), Python `difflib` (stdlib, no install), Python `pathlib` (stdlib, already in use), and optionally `python-frontmatter` (pip, only if Obsidian-style YAML frontmatter parsing is needed). The inline diff editor avoids any client-side diff library by computing diffs server-side and returning HTML fragments.

**Core technologies:**
- **Neo4j 5 full-text index** — knowledge search backbone — native Lucene-powered, `db.index.fulltext.queryNodes()`, covers keyword + fuzzy search, no new service required
- **FastAPI `pathlib` (stdlib)** — folder ingest file reader — `Path.rglob('*.md')` + `Path.read_text()`, zero new dependencies
- **Python `difflib` (stdlib)** — server-side diff computation — `ndiff` generates diff, serialized as HTML `<span>` fragments, returned to client
- **React 18 `createElement` + `dangerouslySetInnerHTML`** (CDN, already in use) — renders diff HTML and all new knowledge panels without a build step
- **`python-frontmatter` (pip, optional)** — YAML frontmatter extraction from `.md` files — add only if ingesting Obsidian-format notes with frontmatter headers

**What NOT to use:**
- No vector search / RAG (explicitly out of scope, no embedding model served)
- No CodeMirror / Monaco (requires npm build step)
- No `react-diff-viewer` (requires JSX pipeline)
- No LangChain n8n AI Agent nodes (breaks existing HTTP-node pattern)
- No APOC procedures (not confirmed installed; built-in Neo4j 5 procedures preferred)
- No new Docker service for search (built-in Neo4j full-text index is sufficient)

### Expected Features

**Must have — v1.1 core (P1):**
- **KnowledgeNote schema in Neo4j** — foundational; nothing else works without distinct labeling
- **UI mode restructuring** — Validation / Project Knowledge sidebar grouping; zero backend cost; gives users orientation before features arrive
- **Insert Knowledge via NL prompt** — primary entry point; validates LLM-to-knowledge-graph pipeline
- **Insert Knowledge from local markdown folder** — architects have existing notes; unlocks real adoption
- **Query Knowledge** — closes the loop; validates the graph has utility
- **Session history storage** — store from day one; interaction history is not retroactively recoverable

**Should have — after P1 is stable (P2):**
- **Update Knowledge with LLM node matching** — trigger: users duplicate notes instead of updating
- **Inline diff editor (red-span review)** — required companion to Update; prevents silent LLM corruption
- **Subgraph isolation on node selection** — NeoVis filter to collapse graph to affected nodes + neighbors
- **Session history browsable UI panel** — surface after enough sessions accumulate

**Defer to v2+:**
- Cross-graph linking (Knowledge nodes ↔ SWRL Rule atoms) — mixed graph UX model unresolved
- Obsidian vault live sync — two-way sync complexity out of scope; one-time import is sufficient
- Versioned node history — session log provides adequate audit trail at current scale
- Collaborative editing — single-writer model is sufficient; collab requires WebSocket infrastructure

### Architecture Approach

The system extends the existing data flow by adding a parallel `KnowledgeGraph` lane that shares all infrastructure. The `data-service` FastAPI app gains a `/knowledge/*` route group (implemented as a separate `knowledge.py` module to avoid bloating `app.py`). Two new n8n workflows handle NL-to-Cypher translation for insert and query operations. The Neo4j database gains a new `graph:"KnowledgeGraph"` partition containing `KnowledgeNote`, `KnowledgeTag`, and `KnowledgeSession` nodes. The main SPA (`index.html`) gains a new "Project Knowledge" section in `MODE_OPTIONS` with four sub-mode panels. No new containers, no new proxy routes — the existing `/data-service/` Nginx proxy covers all new endpoints automatically.

**Major components and their responsibilities:**
1. **`graph-viewer/index.html`** — adds Knowledge section to MODE_OPTIONS, renders Insert / Update / Query / Sessions panels using existing `React.createElement` pattern
2. **`data-service/app.py` + `knowledge.py`** — exposes 8 new `/knowledge/*` REST endpoints; handles file-system reading, diff computation, LLM dispatch via n8n, and Neo4j CRUD
3. **`n8n/knowledge-ingest.json`** — NL prompt → Ollama → structured note fields → Neo4j MERGE Cypher (~10-node workflow, mirrors existing patterns)
4. **`n8n/knowledge-query.json`** — NL question → Ollama term extraction → Neo4j full-text search → Ollama context assembly → NL answer (~12-node workflow)
5. **Neo4j `KnowledgeGraph` partition** — stores `KnowledgeNote`, `KnowledgeTag`, `KnowledgeSession` nodes with `graph:"KnowledgeGraph"` + `project` property isolation; full-text index on `title` + `content`
6. **Docker Compose** — one new bind-mount (`.:/repo:ro` + `DG_REPO_DIR=/repo` env var on data-service) for folder ingest

### Critical Pitfalls

1. **Mixing Knowledge and SWRL nodes under the same graph label** — every knowledge node must carry `graph:"KnowledgeGraph"`. Never add knowledge properties to existing Rule or Atom nodes. Destroys NeoVis isolation and makes future migration impossible.

2. **Using localStorage for session history** — localStorage is already stressed by run screenshots. Sessions accumulate indefinitely and disappear on browser data clear. Use `KnowledgeSession` nodes in Neo4j; the `ValidationRun` pattern is the direct precedent.

3. **Adding a new Docker service for knowledge features** — the existing data-service already has the Neo4j driver, the execution-result store, and the Speckle settings pattern. A new container adds operational complexity for no gain. Add knowledge routes as a new module inside the existing `app.py`.

4. **Passing full note content through n8n workflow node parameters** — n8n workflow node parameters have size limits and are stored in n8n's internal SQLite. Note content belongs in Neo4j. n8n workflows should operate on note IDs and short summaries only; full content fetch/write goes through data-service ↔ Neo4j directly.

5. **JSX or Vite build for knowledge UI** — the multi-step Update diff editor feels complex enough to tempt a Vite sub-app, but `React.createElement` + `<textarea>` + server-rendered diff HTML is fully adequate. A second build pipeline is inconsistent with the main SPA pattern and adds maintenance overhead.

---

## Implications for Roadmap

Research establishes a clear 7-phase dependency chain. Phases 1–4 are backend-only and testable without any UI changes. UI work begins in Phase 5. The Update flow (the most complex feature) depends on all earlier backend phases and should not be started until Phase 3 is verified.

### Phase 1: Neo4j Schema Foundation

**Rationale:** Every subsequent phase depends on the `KnowledgeNote`, `KnowledgeTag`, and `KnowledgeSession` node shapes existing in Neo4j. The full-text index must be created at data-service startup — it cannot be retrofitted without downtime risk. This is the only phase with no predecessor.

**Delivers:** New node label schema, full-text index, startup index-creation code in data-service, and a verified Cypher MERGE pattern for `KnowledgeNote`.

**Addresses:** KnowledgeNote schema (P1 table stakes), project isolation enforcement.

**Avoids:** Pitfall 1 (label mixing) — establish strict `graph:"KnowledgeGraph"` convention before any data is written.

### Phase 2: data-service CRUD + Folder Ingest Endpoints

**Rationale:** CRUD endpoints (`GET /knowledge/notes/*`, `GET/PUT/DELETE /knowledge/note/*`) and `/knowledge/ingest/folder` can be built and fully tested against the Phase 1 schema without any n8n or LLM involvement. This isolates the file-system reading complexity early and validates the `DG_REPO_DIR` bind-mount pattern.

**Delivers:** Working folder ingest (walk `.md` files, MERGE to Neo4j), note listing, read, update, delete, and session write/read endpoints. The entire CRUD surface is testable via curl or Postman before any UI exists.

**Uses:** `pathlib.rglob`, optional `python-frontmatter`, existing neo4j Python driver.

**Avoids:** Pitfall 3 (no new Docker service), Pitfall 4 (note content in Neo4j, not n8n).

### Phase 3: n8n Knowledge Workflows (Insert NL + Query)

**Rationale:** The two n8n workflows are the LLM integration point. They must be verified independently before the Update flow (Phase 4) relies on Ollama availability. Build and test `knowledge-ingest` and `knowledge-query` workflows against the Phase 1 schema. Wire data-service `/knowledge/ingest/prompt` and `/knowledge/query` to call these webhooks and poll via the existing execution-result pattern.

**Delivers:** End-to-end NL → KnowledgeNote graph pipeline and NL → full-text search → NL answer pipeline. Session nodes written automatically on completion.

**Uses:** Existing n8n HTTP node pattern, Ollama `llama3.1`, Neo4j full-text index from Phase 1.

**Avoids:** Pitfall 4 (n8n operates on IDs and short strings, not full note content).

### Phase 4: Update Flow (Match → Propose → Confirm Endpoints)

**Rationale:** The three `/knowledge/update/*` endpoints are the most complex backend work. They depend on Phase 1 (nodes to find), Phase 2 (note content readable from Neo4j), and Phase 3 (Ollama accessible via data-service). Isolate diff logic in `knowledge.py` using Python `difflib` — no new dependency. The three-step flow (Match → Propose → Confirm) is the key trust mechanism; never collapse it to a single write.

**Delivers:** LLM node matching via full-text search + Ollama, server-computed diff HTML, confirmed-edit write path, KnowledgeSession nodes for update operations.

**Uses:** `difflib` (stdlib), Ollama (via direct data-service → HTTP call, not n8n), Neo4j full-text index.

**Avoids:** Pitfall 2 (session in Neo4j, not localStorage), silent LLM overwrites.

### Phase 5: UI — Mode Restructuring + Insert and Query Panels

**Rationale:** UI work begins here. Mode restructuring (Validation vs Project Knowledge sidebar sections) is purely cosmetic and can ship first as a scaffold — no backend required. Insert and Query panels are simpler (single-step flows) and provide immediate utility once Phase 3 endpoints are live. Build and verify these before the more complex Update panel.

**Delivers:** Restructured MODE_OPTIONS with "Validation" and "Project Knowledge" sections, Insert Knowledge panel (NL prompt + folder path), Query Knowledge panel with Response + Cypher display fields.

**Uses:** Existing `React.createElement` pattern, existing execution-result polling, existing sidebar CSS variables.

**Avoids:** Pitfall 5 (no JSX/Vite build).

### Phase 6: UI — Update Panel + Inline Diff Editor

**Rationale:** The three-step Update UI is the most complex UI work. It depends on Phase 4 backend endpoints. The inline diff editor uses `<textarea>` for editable content alongside a read-only `dangerouslySetInnerHTML` diff panel — not `contenteditable`, which has brittle cursor management under DOM mutation. Build the diff rendering first (static HTML from server), then wire the three-step interaction.

**Delivers:** Update Knowledge panel with node candidate list (Step 1), diff preview with red-highlighted deletions and additions (Step 2), confirm/edit flow that writes to Neo4j (Step 3).

**Uses:** `dangerouslySetInnerHTML`, server-rendered diff HTML from Phase 4, existing polling pattern.

**Avoids:** Pitfall 5 (no CodeMirror, no Monaco, no `react-diff-viewer`).

### Phase 7: UI — Session History Panel + NeoVis Knowledge Graph View

**Rationale:** Session history has the lowest dependency (read-only from Phase 2 endpoint) and can be done last. NeoVis knowledge graph toggle (showing `KnowledgeNote` and `KnowledgeTag` nodes) extends the existing `config.template.js` pattern and is the lowest-risk UI change.

**Delivers:** Browsable session history panel (mode-tagged, reverse-chronological), optional NeoVis graph toggle filtered to `graph:"KnowledgeGraph"`, `KnowledgeTag` node styling in NeoVis config.

**Uses:** Existing NeoVis `updateWithCypher` pattern, `graph-viewer/config.template.js`.

**Avoids:** None of the major pitfalls apply here — this is the safest phase.

### Phase Ordering Rationale

- **Schema before endpoints:** No data-service endpoint can write knowledge nodes until the schema and full-text index exist. Phase 1 is the only non-negotiable first step.
- **CRUD before LLM:** Folder ingest (Phase 2) is testable without LLM involvement. Establishing the insert/read/delete surface early means Phase 3 can focus entirely on the n8n/Ollama integration without also debugging schema issues.
- **Workflows before Update:** The Update flow (Phase 4) calls Ollama directly from data-service, but requires verified note content in Neo4j (Phase 2) and a proven Ollama call pattern (Phase 3).
- **Backend complete before UI:** Phases 5–7 are all UI-only. Having all endpoints live before any UI work means panels can be built against real data, not mocks.
- **Insert/Query UI before Update UI:** Simpler single-step flows validate the polling pattern and sidebar layout before the complex three-step Update panel is built.
- **Session history last:** It is read-only from an already-verified endpoint. There is no risk in deferring it, and it has the least blocking potential.

### Research Flags

Phases with well-documented patterns (skip `/gsd-research-phase` during planning):
- **Phase 1:** Neo4j full-text index creation is a standard, documented Cypher DDL command. HIGH confidence.
- **Phase 2:** FastAPI endpoint patterns and `pathlib` file reading are thoroughly documented. HIGH confidence.
- **Phase 5:** React.createElement SPA patterns are established within this codebase. HIGH confidence.
- **Phase 7:** NeoVis `updateWithCypher` and config.template.js extension are existing codebase patterns. HIGH confidence.

Phases that may benefit from deeper research during planning:
- **Phase 3 (n8n workflows):** The exact prompt structure for extracting structured note fields from NL input (title, tags, content) needs careful prompt engineering. The existing `rules-to-metagraph.json` workflow is the model, but knowledge note extraction is a different schema. Recommend reviewing that workflow's Ollama prompt structure before writing the new workflow.
- **Phase 4 (Update flow):** The `difflib.ndiff` output format and the conversion to HTML `<span>` fragments needs a small prototype. The `[DEL]...[/DEL]` / `[INS]...[/INS]` marker approach (LLM-annotated) vs pure `difflib` output (line-level) needs a decision before implementation.
- **Phase 6 (Inline diff editor):** The `<textarea>` + adjacent read-only diff panel interaction (live diff on debounced keyup) needs UX validation. The debounce interval and whether to POST to `/preview-edit` on every keyup or only on blur needs a decision.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Neo4j full-text index verified against current Neo4j docs. `difflib` and `pathlib` are Python stdlib. `python-frontmatter` has no known conflicts. No novel dependencies. |
| Features | MEDIUM | Feature priorities reasoned from domain references (Obsidian, Neo4j LLM Graph Builder, AEC knowledge tools). The three-step Update flow is a reasoned design, not a pattern observed in the wild — validate with users after P1 ships. |
| Architecture | HIGH | Based on direct codebase inspection of `index.html`, `app.py`, `docker-compose.yml`, `nginx.conf`, and both existing n8n workflows. All integration points verified against actual code, not assumptions. |
| Pitfalls | HIGH | All 5 pitfalls are grounded in existing codebase gotchas (localStorage screenshot stress, label mixing risk in NeoVis, n8n parameter size limits). Not hypothetical. |

**Overall confidence:** HIGH for architecture and stack decisions. MEDIUM for feature priority ordering (needs user validation after Insert + Query ship).

### Gaps to Address

- **Ollama prompt for knowledge note extraction:** The exact prompt structure to extract `{title, tags, content}` from a free-form NL insert prompt is not defined in research. Needs a small prompt-engineering session before Phase 3 implementation. Reference: existing `rules-to-metagraph.json` Ollama prompt as starting model.

- **Diff marker convention:** Research identifies two approaches — LLM uses `[DEL]...[/DEL]` / `[INS]...[/INS]` inline markers (Phase 4 Propose step), or data-service uses `difflib.ndiff` to compute the diff after LLM returns plain proposed text. The second approach is more robust (LLM is unreliable at marker placement) but requires two round-trips. Recommend deciding this before Phase 4 implementation begins.

- **`python-frontmatter` gate:** If the Obsidian vault notes (`DG_OBSIDIAN/`) do not use YAML frontmatter consistently, `p.stem` as title + full body as content is sufficient and `python-frontmatter` can be omitted entirely. Verify by inspecting a sample of target `.md` files before Phase 2 implementation.

- **NeoVis knowledge node visual design:** Node colors and shapes for `KnowledgeNote` vs `KnowledgeTag` vs existing SWRL nodes are not defined. Needs a design decision before Phase 7. Recommend distinct color (e.g., teal/green for knowledge vs blue for SWRL) to avoid visual confusion.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `graph-viewer/index.html`, `data-service/app.py`, `docker-compose.yml`, `graph-viewer/nginx.conf`, `n8n/workflows/rules-to-metagraph.json`, `training/dataset_schema.json`
- [Neo4j Full-Text Indexes — Cypher Manual](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/) — index creation syntax, query procedures, OPTIONS config
- [Python pathlib docs](https://docs.python.org/3/library/pathlib.html) — `rglob`, `read_text`
- [Python difflib docs](https://docs.python.org/3/library/difflib.html) — `ndiff`, line-level diff
- [FastAPI Official Docs](https://fastapi.tiangolo.com/tutorial/static-files/) — file serving and endpoint patterns

### Secondary (MEDIUM confidence)
- [Neo4j LLM Knowledge Graph Builder — First Release 2025](https://neo4j.com/blog/developer/llm-knowledge-graph-builder-release/) — feature comparison, graph builder patterns
- [LLM-empowered knowledge graph construction: A survey](https://arxiv.org/html/2510.20345v1) — background on LLM graph construction patterns
- [Building a Visual Diff System for AI Edits](https://medium.com/illumination/building-a-visual-diff-system-for-ai-edits-like-git-blame-for-llm-changes-171899c36971) — diff rendering approaches
- [Neo4j Full-Text Search — Knowledge Base](https://neo4j.com/developer/kb/fulltext-search-in-neo4j/) — Lucene query syntax, fuzzy, wildcard, scoring

### Tertiary (MEDIUM-LOW confidence)
- [Top Graph-Based Knowledge Management Tools 2025](https://blog.knowing.app/posts/top-graph-based-knowledge-management-tools-2025/) — feature landscape survey
- [Best Practices: Knowledge Management for AEC Firms](https://www.knowledge-architecture.com/aec-knowledge-management) — domain context
- [Obsidian in 2025](https://productivitywork.com/obsidian-in-2025-the-revolutionary-knowledge-management-tool-thats-transforming-how-we-think-and-learn/) — user expectation baseline
- WebSearch: n8n workflow patterns for LLM+graph — existing project workflows are the primary reference; web sources are corroborating

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
*Note: PITFALLS.md was not produced by parallel research agents. Pitfall analysis was synthesized from ARCHITECTURE.md anti-patterns section, which contained 5 explicitly documented anti-patterns grounded in codebase inspection.*
