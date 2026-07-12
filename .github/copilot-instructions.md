# Copilot Instructions for design-grammar-system

## Overview
This repo orchestrates a Dockerized pipeline for parsing architectural design rules into SWRL + graph atoms, generating a custom ontology, and storing both in Neo4j. LLM-based Cypher generation is constrained at inference time via structured prompts embedding the v4 schema and few-shot examples (no fine-tuned model required). It also includes a graph-query workflow (MCP) that turns natural-language questions into read-only Cypher and returns a short answer.

The **Design Grammars** UI is a multi-page single-page application providing user registration/login, project management, and per-project graph ingest, query, and visualization. A 14-component DG Grasshopper plugin evaluates BIM geometry against rules and publishes validation results.

## Current canonical graph model (v4)
Use the v4 schema as the source of truth for all code changes, prompts, generated Cypher, and UI labels.

### Graph separation
- `graph = 'OntoGraph'` for ontology terms.
- `graph = 'Metagraph'` for rules, atoms, variables, literals, and builtins.
- `graph = 'ValidGraph'` for validation runs, design states, and integration config.
- `graph = 'SpecGraph'` for project spec storage (notes, tags, sessions).
- Every persisted node must include `project` and `graph`.
- DesignState persisted with `graph = 'ValidGraph'`, `kind` in {ObjState, ParamState, PropState}.

### Canonical node labels and properties
- `Class`: key `iri`, display property `label`
- `DatatypeProperty`: key `iri`, display property `SWRL_label`
- `ObjectProperty`: key `iri`, display property `label`
- `Builtin`: key `iri`, display property `label`
- `Rule`: key `Rule_Id`, properties `SWRL`, `RuleName`, `RuleDescription`
- `Atom`: key `Atom_Id`; required properties `Atom_Id`, `type`, `iri`, `SWRL_label`, `project`, `graph`
- `Var`: key `name`
- `Literal`: key `lex` + `datatype`
- `DesignState`: key `StateId`, `kind` {ObjState, ParamState, PropState}, `statePayloadJson` v2
- `Run`: key `Run_Id`, `ValidStatus` (Boolean list per ObjState), `SendStatus` (single Boolean), `shaclReportJson` (per-run SHACL report envelope JSON string, sibling to `statePayloadJson`; absent on pre-Phase-823 runs — see `spec/RULE-PARTITION-POLICY.md`)

### Canonical relationships
Use these relationship types in generated Cypher and UI assumptions:
- `HAS_BODY`
- `HAS_HEAD`
- `REFERS_TO`
- `ARG`
- `HAS_STATE`: DesignState -> state nodes (read-side composition)

Do not use legacy assumptions like `Rule.id`, `Atom.id`, `Atom.Id`, `DatatypeProperty.label`, or `HAS_ATOM` unless you are explicitly writing a migration.

## Component Architecture (14 components)

| # | Component | Role | Wiring Flow |
|---|-----------|------|-------------|
| 1 | CONNECTOR | Database layer handle output (Neo4jURI/Neo4jUser/Neo4jPassword/DbName/Project) | Foundation — wires to GRAPH DECONSTRUCT |
| 2 | GRAPH DECONSTRUCT | Splits Database into Metagraph/OntoGraph/ValidGraph/SpecGraph handles | Wires from CONNECTOR.Database |
| 3 | METAGRAPH | Reads Rules + Objects from Metagraph handle | Wires from GRAPH DECONSTRUCT.Metagraph |
| 4 | ONTOGRAPH | Reads Class/ObjProperties/DataProperties from OntoGraph handle | Wires from GRAPH DECONSTRUCT.Ontograph |
| 5 | VALIDATION GRAPH | Reads Run/Status/DesignState from ValidGraph handle | Wires from GRAPH DECONSTRUCT.ValidGraph |
| 6 | RULE DECONSTRUCT | Partitions rule into Objects + DataProperties outputs | Wires from METAGRAPH.Rules |
| 7 | OBJECT STATE | Captures Object+Geometry+Label into ObjState | Wires from METAGRAPH.Objects + geometry sources |
| 8 | PARAMETER STATE | Captures Parameters list into ParamState | Wires from canvas sliders/toggles |
| 9 | PROPERTY STATE | Captures Rule+DataProperty+PropValue into PropState | Wires from RULE DECONSTRUCT + ONTOGRAPH |
| 10 | DESIGN STATE | Composes ObjState/ParamState/PropState into DesignState | Wires from OBJECT STATE + PARAMETER STATE + PROPERTY STATE |
| 11 | DESIGN STATE DECONSTRUCT | Splits DesignState into ObjState/ParamState/PropState | Wires from VALIDATION GRAPH.DesignState |
| 12 | OBJECT DECONSTRUCT | Splits ObjState into Object/Geometry/Label | Wires from DESIGN STATE DECONSTRUCT.ObjState |
| 13 | PARAMETER REINSTATE | Applies ParamState to canvas (rising-edge trigger on Reinstate, Target input required) | Wires from PARAMETER STATE + Boolean trigger |
| 14 | VALIDATOR | Evaluates Rule+DesignState, publishes validations to Speckle/data-service | Wires from RULE DECONSTRUCT + DESIGN STATE + Boolean triggers |

### Mandatory dependency propagation for schema v4
Whenever you change graph generation or query logic, update all affected layers together:
1. cypher template (`cypher_template.txt`)
2. dataset schema reference (`training/dataset_schema.json`)
3. n8n workflow prompts and validators
4. graph-viewer configuration
5. data-service Cypher (`data-service/app.py`)
6. `.github/copilot-instructions.md`
7. `README.md`
8. `spec/DATABASE.md`
9. any Cypher templates or parsing logic in Python/JS

### Required property migrations (v7.0 completed these migrations)
- `Rule.id` -> `Rule.Rule_Id`
- `Rule.text` -> `Rule.SWRL`
- `Rule.title` -> `Rule.RuleName`
- `DatatypeProperty.label` -> `DatatypeProperty.SWRL_label`
- `Atom.id` / `Atom.Id` -> `Atom.Atom_Id`
- Added: `Atom.iri`, `Atom.SWRL_label`
- `DefState` -> `ParamState` (DesignState kind)
- `ObjectState` -> `ObjState` (DesignState kind)
- `ValidationRun` -> `Run` (ValidGraph label)
- `Knowledge*` -> `Spec*` (all KnowledgeGraph labels)
- Added: `Run.ValidStatus` (Boolean list per ObjState), `Run.SendStatus` (Boolean)
- Added: `RuleDescription` (optional text on Rule nodes)

Any code that reads, renders, queries, validates, or exports the graph must be checked against these changes.

## Architecture

### Docker services (`docker-compose.yml`)
- **Neo4j** (`neo4j:5`): Single database, port 7474/7687. Auth: `neo4j/12345678`. Ontology, rules, validation, and spec separated by `graph` property (`OntoGraph` / `Metagraph` / `ValidGraph` / `SpecGraph`).
- **n8n** (`n8nio/n8n`): Two workflows:
  - `n8n/workflows/rules-to-metagraph.json` → `/webhook/dg/rules-ingest`
  - `n8n/workflows/graph-query-mcp.json` → `/webhook/dg/graph-query`
- **Ollama** (`ollama/ollama:latest`): LLM inference, GPU-enabled, port 11435→11434. Default model: `llama3.1:latest` (env `OLLAMA_MODEL`).
- **data-service** (FastAPI): MCP endpoint (`/mcp`) plus in-memory execution tracking (`/execution-result`).
- **design-grammars** (Nginx): Static SPA + reverse proxy for `/neo4j`, `/n8n`, `/data-service`. Port 8080. Build context: `./graph-viewer`.

### UI application — Design Grammars (`graph-viewer/index.html`)
The app is a single-file React 18 SPA (CDN, no JSX — uses `React.createElement` throughout). All HTML, CSS, and JS live in `index.html`. Google Fonts: Inter (body) + Space Grotesk (headings/branding).

#### Page flow
`RegisterPage` → `HomePage` → `GraphViewerPage`, managed by `AppRouter`.

#### Components
| Component | Purpose |
|---|---|
| `AppRouter` | Top-level state machine. Manages `page` state (`register` / `home` / `graph`), `currentUser`, `currentProject`. Restores session from `localStorage` on mount. |
| `RegisterPage` | Login/Register toggle. Login mode: Email + Password. Register mode: Email + Name + Surname + Create Password. Stores user profiles in `localStorage` key `dg_users` with SHA-256 hashed passwords (`hashPassword()`). |
| `HomePage` | Header with logo, search bar, "New Project" button, profile avatar (user initials) with dropdown (name, email, logout). Body shows project grid filtered by search query. Projects stored per-user in `localStorage`. |
| `GraphViewerPage` | Full graph viewer with left panel (mode selector, ingest/query/edit controls), center NeoVis visualization, right detail panel. Nav bar has "← Projects" back button and project name (no logout button). |

#### User & project storage
- Users stored in `localStorage` key `dg_users` as `{ [email]: { passwordHash, name, surname, projects: [{ name, createdAt, lastEdited }] } }`.
- Current session stored in `localStorage` key `dg_current_user`.
- Passwords hashed via `SubtleCrypto.digest('SHA-256')` with `"dg_salt_"` prefix.

#### Project-scoped graph isolation
All nodes live in a single Neo4j database. Project isolation is achieved by filtering on the `project` property:
- `buildCypher(view)` includes `project:'<name>'` in all graph queries.
- `fetchExistingRules()` and `clearGraph()` filter by project name.
- `tagProjectNodes()` runs after ingestion to retag nodes where `project IS NULL OR project = 'default-project'` to the current project name.
- Webhook body sends the actual project name to n8n; the n8n workflow "Set Input Defaults" node reads `$json.project` and falls back to `'default-project'`.

#### Design files (Pencil `.pen`)
- `graph-viewer/interface/design-grammars-RegisterForm.pen` — Two frames: "Login Mode" and "Register Mode" showing both form states.
- `graph-viewer/interface/design-grammars-home.pen` — Projects Home page with header (logo, search, New Project, profile avatar with dropdown), project tile grid.

When UI changes are made to `index.html`, the corresponding `.pen` design files should be updated to stay in sync.

## LLM integration (prompt-based)

Instead of a fine-tuned model, Cypher generation is constrained at inference time via structured prompts that embed the v4 schema rules and a few-shot example.

### Prompt structure for rules-ingest workflow
The `Build LLM Prompt` node in `rules-to-metagraph.json` constructs a prompt with:
1. **Schema constraints** — allowed labels, relationships, key properties, graph assignments.
2. **Node key conventions** — `Rule_Id`, `Atom_Id`, `SWRL_label`, etc.
3. **Semantic mapping** — how NL constraint phrases map to SWRL builtins.
4. **Few-shot example** — a complete v4-compliant Cypher block for a height violation rule.
5. **The user's NL rule** — appended at the end.

### Prompt structure for graph-query workflow
The `Build Cypher Prompt` node in `graph-query-mcp.json` constructs a prompt with:
1. **v4 data model description** — node labels, key/display properties, relationship types.
2. **Live schema context** — labels, relationships, property keys fetched from Neo4j via MCP.
3. **Guidance** — query patterns for numeric limits, rule listing, keyword matching.
4. **The user's question** — appended at the end.

### Reference files
| File | Purpose |
|---|---|
| `cypher_template.txt` | v4 Cypher template with placeholders — source of truth for prompt structure |
| `training/dataset_schema.json` | v4 dataset schema — defines allowed node types, keys, properties, connections |
| `training/updated_cypher_reference_examples_v3.cypher` | Complete Cypher examples for reference (v3 historical, carried forward) |

## Files to inspect first when making repo-wide changes
- `graph-viewer/index.html` — all UI code (components, routing, graph queries, project filtering)
- `graph-viewer/config.template.js` — NeoVis graph configuration
- `graph-viewer/interface/*.pen` — Pencil design files (keep in sync with UI)
- `n8n/workflows/*.json` — n8n workflow definitions
- `data-service/app.py` — FastAPI MCP endpoint
- `training/dataset_schema.json` — v4 dataset schema
- `cypher_template.txt` — Cypher template source of truth
- `docker-compose.yml` — service definitions (note: UI service is `design-grammars`, build context `./graph-viewer`)

## Deployment notes
- Build and deploy the UI: `docker compose build --no-cache design-grammars && docker compose up -d design-grammars`
- Use `--no-cache` when `index.html` changes to avoid Docker layer caching serving stale files.
- If the browser shows stale UI after rebuild, hard-refresh (Ctrl+Shift+R) or use incognito mode.

---
Always prefer the v4 schema conventions above over older examples elsewhere in the repo.

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
