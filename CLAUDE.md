# CLAUDE.md — Design Grammar System

> Context file for AI coding assistants. Read this first.

## What is this project?

**Design Grammar System (DG)** automates architectural compliance checking. Architects write design rules in natural language (e.g. "maximum building height is 75 meters"), which an LLM pipeline converts to SWRL ontology atoms stored in a Neo4j graph. A Grasshopper plugin then evaluates BIM geometry against these rules and publishes color-coded validation results to a Speckle 3D viewer.

**Target audience:** Architects and urban planners who need to verify designs against regulatory or project-specific rules.

## Knowledge Vault

This project uses an **Obsidian Knowledge Vault** at `DG_OBSIDIAN/` to persist architectural decisions, debugging notes, patterns, and session logs.

### Session Protocol

**On session start:**
1. Read `DG_OBSIDIAN/00-home/index.md` — project map of contents
2. Read `DG_OBSIDIAN/00-home/Current priorities.md` — active work items
3. If the task touches a specific module, read the relevant note from `DG_OBSIDIAN/knowledge/`

**On session end (user says "сохрани сессию" / "save session"):**
1. Create a session note in `DG_OBSIDIAN/sessions/YYYY-MM-DD <title>.md`
2. Update `DG_OBSIDIAN/00-home/Current priorities.md`
3. If a design decision was made → create note in `DG_OBSIDIAN/knowledge/decisions/`
4. If a bug was found/fixed → create note in `DG_OBSIDIAN/knowledge/debugging/`
5. Update `DG_OBSIDIAN/00-home/index.md` if new notes were created

## Architecture (Quick Reference)

**12+ Docker services** orchestrated via `docker-compose.yml`:

```
User (browser) → Nginx SPA (:8080)
  → /n8n/webhook/dg/rules-ingest  →  n8n  →  Ollama (llama3.1)  →  Neo4j
  → /n8n/webhook/dg/graph-query   →  n8n  →  Ollama  →  data-service/mcp  →  Neo4j
  → /data-service/validation/...  →  data-service  →  Speckle
  → /neo4j/db/neo4j/tx/commit     →  Neo4j (direct Cypher)
```

### Service Map

| Service | Tech | Port | Role |
|---------|------|------|------|
| `design-grammars` | Nginx + static | 8080 | Main SPA UI + reverse proxy |
| `neo4j` | Neo4j 5 | 7474/7687 | Graph DB (single DB, project-isolated) |
| `data-service` | Python FastAPI | 8000 | MCP bridge, validation publish, execution tracking |
| `n8n` | n8n | 5678 | 2 webhook workflows (ingest + query) |
| `ollama` | Ollama (GPU) | 11435 | Local LLM (llama3.1) |
| `speckle-*` | Speckle stack | 8090 | Self-hosted 3D model platform (7 containers) |

### Key Design Decisions

- **Single Neo4j database** with project isolation via `project` property on every node
- **No message queue** — synchronous HTTP + async polling for LLM calls
- **No JSX build** for main UI — single-file `index.html` with `React.createElement`
- **Model Viewer** is a separate Vite+React app at `/model-viewer/`
- **SWRL parsing** uses bespoke regex, not vendor OWL libraries
- **LLM prompts embed schema constraints** instead of fine-tuning
- **Violation pattern**: body atoms fire when constraint is violated (inverted logic)

## Repository Structure

```
design-grammar-system/
├── CLAUDE.md                    ← you are here
├── spec/                        ← project specification
├── DG_OBSIDIAN/                 ← Obsidian knowledge vault
├── docker-compose.yml           ← orchestration (12+ services)
├── cypher_template.txt          ← v3 Cypher template for LLM prompts
│
├── graph-viewer/                ← Main UI container
│   ├── index.html               ← Single-file React 18 SPA (no build step)
│   ├── config.template.js       ← NeoVis config (env vars injected at runtime)
│   ├── entrypoint.sh            ← sed-based config injection
│   ├── nginx.conf               ← reverse proxy routes
│   ├── Dockerfile
│   └── model-viewer/            ← Speckle 3D viewer (Vite + React)
│       ├── src/App.jsx
│       ├── vite.config.js
│       └── package.json
│
├── data-service/                ← Python FastAPI service
│   ├── app.py                   ← MCP endpoint, execution tracking, Speckle publish
│   ├── speckle_validation.py    ← Speckle publishing logic
│   ├── Dockerfile
│   └── requirements.txt
│
├── DG/                          ← C# Grasshopper plugin
│   ├── DG.sln
│   ├── src/DG.Core/             ← Pure logic (no GH deps): Models, Parsing, Validation
│   ├── src/DG.Grasshopper/      ← GH components (conditional compilation)
│   └── tests/DG.Tests/          ← xUnit tests
│
├── n8n/workflows/               ← n8n webhook workflow definitions
│   ├── rules-to-metagraph.json  ← NL → SWRL → Cypher → Neo4j (13 nodes)
│   └── graph-query-mcp.json     ← NL question → Cypher → answer (15 nodes)
│
├── training/                    ← LLM fine-tuning (LoRA for llama3.1)
│   ├── dataset_schema.json      ← v3 schema definition
│   ├── updated_cypher_reference_examples_v3.cypher
│   ├── train_lora.py
│   └── training_dataset.json
│
├── speckle/                     ← Speckle bootstrap SQL
├── test/                        ← Test data and fixtures
│
└── .planning/                   ← GSD-managed planning artifacts
    ├── PROJECT.md, ROADMAP.md, REQUIREMENTS.md, STATE.md
    ├── codebase/                ← Static codebase analysis (GSD map output)
    ├── research/                ← Project-level research notes
    ├── phases/                  ← **Active milestone's** phases (flat, e.g. v2.0)
    │   └── NN-<slug>/           ← One dir per phase: PLAN, CONTEXT, RESEARCH, SUMMARY, VERIFICATION, etc.
    └── milestones/              ← **Archived** milestones
        └── v1.1-phases/         ← Same per-phase layout, kept for history
```

### Planning archive convention

`.planning/phases/` always holds the **currently active milestone**. When a milestone ships:

1. `mv .planning/phases .planning/milestones/v<old>-phases`
2. Recreate empty `.planning/phases/` for the next milestone
3. Sweep refs inside the archived plans: `sed -i 's|.planning/phases/|.planning/milestones/v<old>-phases/|g'`

This keeps GSD tooling happy (it always reads `.planning/phases/`) while preserving each milestone's plans separately.

## Graph Schema v3

**Single source of truth:** `training/dataset_schema.json` + `cypher_template.txt`

### Node Labels

| Label | Graph | Key Property | Display |
|-------|-------|-------------|---------|
| `Class` | OntoGraph | `iri` | `label` |
| `DatatypeProperty` | OntoGraph | `iri` | `SWRL_label` |
| `ObjectProperty` | OntoGraph | `iri` | `label` |
| `Rule` | Metagraph | `Rule_Id` | `Rule_Id` |
| `Atom` | Metagraph | `Atom_Id` | `SWRL_label` |
| `Var` | Metagraph | `name` | `name` |
| `Literal` | Metagraph | `lex` | `lex` |
| `Builtin` | Metagraph | `iri` | `label` |

### Relationships

`HAS_BODY`, `HAS_HEAD` (Rule→Atom, with `order`), `REFERS_TO` (Atom→entity), `ARG` (Atom→Var/Literal, with `pos`)

### Rule ID Format

`R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` (e.g. `R_URB_HEIGHT_MAX_75_V`)

### Schema Change Propagation

When changing graph structure, update ALL: `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompts, `config.template.js`, and any Cypher templates in Python/JS.

## Common Commands

```bash
# Start all services
docker compose up -d

# Rebuild UI after index.html changes (--no-cache required!)
docker compose build --no-cache design-grammars && docker compose up -d design-grammars

# Build Grasshopper plugin
dotnet build .\DG\DG.sln -c Release

# Run C# tests
dotnet test .\DG\tests\DG.Tests\
```

## Current Priorities

1. **Phase 14: Graph Schema v4 Propagation** — propagate V7 ontology names across cypher_template.txt, dataset_schema.json, n8n prompts, NeoVis config, data-service Cypher. Start: `/gsd-discuss-phase 14`
2. **Phase 15: SpecGraph Runtime Rename** — runtime rename in data-service, n8n, NeoVis, UI + DB migration
3. **Model Viewer visual bugs** — rotation/mixed state in validation viewport
4. **Validation management** — add delete/rename for validation runs

## Known Gotchas

- **Docker layer caching** can serve stale `index.html` — always use `--no-cache`
- **Browser cache** prevents seeing UI updates — hard-refresh (Ctrl+Shift+R) or incognito
- **Neo4j node tagging** required after n8n ingestion — orphaned nodes need `graph`/`project` props
- **LLM Cypher output** needs bracket nesting validation before execution
- **Edit mode** requires cleanup of old atoms (MATCH-DELETE) before re-creation
- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards all GH-dependent code in DG.Grasshopper

## Tech Stack Summary

| Layer | Language | Key Tech |
|-------|----------|----------|
| Grasshopper Plugin | C# (.NET 7/9) | Neo4j.Driver, Rhino 8 SDK |
| Data Service | Python 3 | FastAPI, neo4j, specklepy, pydantic |
| Workflows | JavaScript (n8n) | Webhook, HTTP, Function nodes |
| Main UI | JavaScript | React 18 (CDN, no JSX), NeoVis.js |
| Model Viewer | JSX | React + Vite, @speckle/viewer, three.js |
| LLM | — | Ollama, llama3.1 |
| Database | Cypher | Neo4j 5 |
| Fonts | — | Inter (body), Space Grotesk (headings) |

## Obsidian Knowledge Vault
Хранилище знаний: ./DG_OBSIDIAN
### При старте сессии
Прочитай 00-home/index.md и текущие приоритеты.md.
Если задача касается модуля — прочитай заметку из knowledge/.
### При завершении (пользователь: "сохрани сессию")
1. Создай заметку в sessions/ с датой
2. Обнови текущие приоритеты.md
3. Если решение — создай в knowledge/decisions/
4. Если баг — создай в knowledge/debugging/
5. Обнови index.md если новые заметки
6. Если в текущей сессии были изменены файлы — создай коммит только из файлов, затронутых в этой сессии (тех, которые ты создал или редактировал через Write/Edit). Изменения из предыдущих сессий не включать. Каждая сессия — отдельный коммит. 
Шаблон:
сессия: <краткое описание работы за сессию в одном предложении>

## Информация о сессии
- Модель: <текущая LLM модель, например claude-sonnet-4-6>
- Дата: <дата последних изменений в формате YYYY-MM-DD>
- Изменено файлов: <N>

## Изменённые файлы
- <список файлов из git status>

## Результаты
- <что было сделано, список ключевых изменений>

Если изменений нет — коммит не создавать.

<!-- PERPLEXITY-MCP-START -->
# Perplexity MCP Server

## Available Tools

- **perplexity_search** — Fast web search with source citations. Use for quick factual lookups. Works with or without authentication.
- **perplexity_reason** — Step-by-step reasoning with web context. Requires Pro account.
- **perplexity_research** — Deep multi-section research reports (30-120s). Requires Pro account.
- **perplexity_ask** — Flexible queries with explicit model/mode/follow-up control.
- **perplexity_compute** — ASI/Computer mode for complex multi-step tasks. Requires Max account.
- **perplexity_models** — List available models, account tier, and rate limits.
- **perplexity_retrieve** — Poll results from pending research/compute tasks.
- **perplexity_export** — Export a saved history entry as PDF, markdown, or DOCX. Uses Perplexity's native export when available.
- **perplexity_sync_cloud** — Sync Perplexity cloud history into the local history store.
- **perplexity_hydrate_cloud_entry** — Hydrate a single cloud-backed history entry by id.
- **perplexity_list_researches** — List saved research history with status.
- **perplexity_get_research** — Fetch full content of a saved research.
- **perplexity_login** — Open browser for Perplexity authentication.
- **perplexity_doctor** — Run diagnostic checks against your Perplexity MCP install. Returns a Markdown report; pass probe:true for a live search probe.

## Usage Guidelines

1. **Start with perplexity_search** for quick questions. Only escalate to research or reason when depth is needed.
2. **Check rate limits** with perplexity_models before batch operations.
3. **Always cite sources** from search results in your responses.
4. **For multi-turn conversations**, pass the follow_up_context JSON from perplexity_ask responses back in subsequent calls.
5. **Long-running research**: perplexity_compute may time out. Use perplexity_retrieve with the returned research_id to poll for results.
6. **Language parameter**: Defaults to en-US. Set explicitly for non-English queries.

## Model Selection

| Tool | Default Model | Best For |
|------|--------------|----------|
| perplexity_search | pplx_pro | General web search |
| perplexity_reason | claude46sonnetthinking | Step-by-step analysis |
| perplexity_research | pplx_alpha | Deep research reports |
| perplexity_compute | pplx_asi | Complex multi-step tasks |
<!-- PERPLEXITY-MCP-END -->

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
