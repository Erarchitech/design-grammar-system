# CLAUDE.md — Design Grammar System

> Context file for AI coding assistants. Read this first.

## What is this project?

**Design Grammar System (DG)** automates architectural compliance checking. Architects write design rules in natural language (e.g. "maximum building height is 75 meters"), which an LLM pipeline converts to SWRL ontology atoms stored in a Neo4j graph. A Grasshopper plugin then evaluates BIM geometry against these rules and publishes color-coded validation results to a Speckle 3D viewer.

**Target audience:** Architects and urban planners who need to verify designs against regulatory or project-specific rules.

## Knowledge Vault

This project uses an **Obsidian Knowledge Vault** at `DG_OBSIDIAN/` to persist architectural decisions, debugging notes, patterns, and session logs. Since 2026-07-18 it is also the unified PhD knowledge base (research + dissemination layers merged from Yandex vaults).

### Knowledge routing (token economy — read indexes first, not folders)

| Question about… | Entry point |
|---|---|
| Architecture, stack, deployment | `DG_OBSIDIAN/00-home/index.md` → atlas |
| Decisions, debugging, patterns | `DG_OBSIDIAN/00-home/index.md` → knowledge/ |
| State of the art, literature, SoA taxonomy | `DG_OBSIDIAN/research/index.md` |
| Publications, presentations, paper↔dev consistency | `DG_OBSIDIAN/dissemination/index.md` and `dissemination/consistency-map.md` |
| DeGram (Hermes fork submodule `apps/degram`, v13.0) | `DG_OBSIDIAN/degram/index.md` → `spec/degram/WORKSPACE.md` |

**Do NOT search** (archived/generated/binary): `DG_OBSIDIAN/archive/`, `DG_OBSIDIAN/graphify/communities/`, `Publications/` (binaries; metadata lives in dissemination notes), `.planning/milestones/` (completed milestones), `graphify-out/`, `.secrets/`, `.degram/index/` (local generated graphs). Never sweep `apps/degram/` broadly (it is the whole upstream Hermes tree); search it only for a named area, starting from `apps/degram/AGENTS.md`. PhD archive lives outside the repo at `Yandex.Disk\Studying\03_PHD\99_ARCHIVE`.

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
  → /n8n/webhook/dg/rules-ingest  →  n8n  →  data-service /llm/generate (LLM gateway)  →  Neo4j
  → /n8n/webhook/dg/graph-query   →  n8n  →  data-service /llm/generate  →  data-service/mcp  →  Neo4j
  → /data-service/validation/...  →  data-service  →  Speckle
  → /neo4j/db/neo4j/tx/commit     →  Neo4j (direct Cypher)

LLM gateway (v9.0 Phase 01, data-service/llm_gateway.py) is provider-agnostic:
Anthropic / OpenAI adapters call out with an encrypted-at-rest API key (set via
the LLMSettingsPanel or /llm/settings); an Ollama adapter remains for local
models. n8n workflows no longer call Ollama directly.
```

### Service Map

| Service | Tech | Port | Role |
|---------|------|------|------|
| `design-grammars` | Nginx + Vite build (`ui-v2/`) | 8080 | V2 UI + reverse proxy |
| `neo4j` | Neo4j 5 | 7474/7687 | Graph DB (single DB, project-isolated) |
| `data-service` | Python FastAPI | 8000 | MCP bridge, validation publish, execution tracking |
| `n8n` | n8n | 5678 | 2 webhook workflows (ingest + query), calls the LLM gateway |
| `ollama` | Ollama (GPU) | 11435 | Optional local model — one of the LLM gateway's providers, not called directly by n8n |
| `speckle-*` | Speckle stack | 8090 | Self-hosted 3D model platform (7 containers) |

### Key Design Decisions

- **Single Neo4j database** with project isolation via `project` property on every node
- **No message queue** — synchronous HTTP + async polling for LLM calls
- **V2 UI (v8.0)** is one Vite + React (JSX) app at `ui-v2/` hosting all four screen layers (landing / graph / model / projects); the legacy no-JSX-build SPA and separate Model Viewer app at `graph-viewer/` are archived
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
├── cypher_template.txt          ← v4 Cypher template for LLM prompts
│
├── ui-v2/                       ← Main UI container (V2, ships as design-grammars)
│   ├── Dockerfile               ← node build → nginx serve
│   ├── nginx.conf               ← reverse proxy routes (/neo4j /n8n /data-service /llm)
│   ├── entrypoint.sh            ← regenerates config.js from env
│   └── src/
│       ├── components/          ← 23 design-system primitives (forms/display/surfaces)
│       ├── styles/tokens/       ← 6-file token split + self-hosted fonts
│       ├── landing/             ← particle-ring hero engine + layer
│       ├── graph/               ← orbital datascape engine + ring mapper
│       ├── screens/             ← Graph / Model / Projects screens
│       └── lib/                 ← graphApi, modelApi, auth
│
├── apps/degram/                 ← DeGram: git submodule, fork of NousResearch/hermes-agent
├── integration/degram/          ← workspace.json manifest, child routing template, evidence
├── spec/degram/WORKSPACE.md     ← DeGram integration contract (ownership, update workflow)
├── tools/degram/                ← workspace.py (context|verify|install-context), index_code.py
│
├── graph-viewer/                ← LEGACY dark SPA (archived at v8.0 cutover)
│   └── model-viewer/            ← legacy Speckle 3D viewer (archived)
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
│   ├── dataset_schema.json      ← v4 schema definition
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

## DeGram component (`apps/degram` submodule)

`apps/degram` is a pinned Git submodule: the public DeGram fork `https://github.com/Erarchitech/degram` (`origin`) of `https://github.com/NousResearch/hermes-agent` (`upstream`). DeGram is an integral DG component (milestone **v13.0 DeGram Agent**, phases 1300–1307), not a separate product. Its own Git history exists only so upstream updates stay possible. Contract: `spec/degram/WORKSPACE.md`; manifest: `integration/degram/workspace.json`.

### One planning and knowledge authority

- Framework `.planning/` is the only GSD project and `DG_OBSIDIAN/` the only vault. Never create `.planning/`, a roadmap, a vault or a GSD project inside `apps/degram` (`workspace.py verify` fails if one appears).
- GSD runs from either directory: invoked inside `apps/degram`, `gsd-sdk` resolves `project_root` to the framework root and reads/writes framework `.planning/` (verified 2026-10-04). GSD doc commits therefore land in the **framework** repo, never in the child.
- Claude Code launched inside `apps/degram` loads this CLAUDE.md as a parent memory file. Hermes launched there reads the generated `apps/degram/.hermes.md`; the child `AGENTS.md` (upstream engineering rules) must then be read explicitly.

### Automatic preflight for any DeGram-touching task

Before discuss/plan/execute of a v13.0 phase, or any edit under `apps/degram/**`, `integration/degram/**`, `spec/degram/**`, `tools/degram/**` or `ui-v2/src/degram/**`:

1. `python tools/degram/workspace.py verify`: gitlink = child HEAD, remotes, required context hashes, no competing authority, `componentContextInstalled`. A failure blocks the task; do not work around it.
2. If `componentContextInstalled` is `false` (fresh clone, or template changed): `python tools/degram/workspace.py install-context`. It writes `apps/degram/.hermes.md` from `integration/degram/component-context.md` and adds `/.hermes.md` to the child's Git-local `info/exclude`, so the fork stays source-clean. Edit the template, never the generated copy.
3. Read `DG_OBSIDIAN/degram/index.md`, `spec/degram/WORKSPACE.md`, then `apps/degram/AGENTS.md` (plus `apps/degram/apps/desktop/AGENTS.md` and `DESIGN.md` for Desktop work).
4. For code navigation in the component use the separate local index (`python tools/degram/index_code.py`, output in `.degram/index/`), not a broad sweep of `apps/degram/`.

### Planning rules for cross-repository work

- PLAN `files_modified` and task paths into the component are written as `apps/degram/...`. Each task names its committing repository: **framework** or **component**.
- A task that changes component source and framework files is split by repository, or orders them explicitly: (1) child change + child tests, (2) child commit, (3) push to the fork (explicit authorization needed, since it publishes), (4) framework gitlink bump + framework files, (5) `workspace.py verify` on the exact pair. A root commit cannot include uncommitted child source; never commit a gitlink whose object is not on the fork.
- Verification and acceptance for v13.0 live only in framework phase artifacts (SUMMARY / VERIFICATION / UAT). Never mark GSD work complete from a child-side summary alone.
- DSH worker briefs for component work carry absolute paths under `C:\Users\Admin\source\repos\design-grammar-system\apps\degram\...`, name the committing repository, and forbid `hermes update`, Desktop launches and any write to the installed Hermes profile.
- Upstream merges (`git -C apps/degram fetch upstream`) are deliberate, scoped tasks on a development branch. The initial clone is shallow; fetch history first and never rewrite fork history.

### Boundaries (owner decision 2026-10-04)

Authorized: the public upstream-only fork, local submodule registration, integration workspace files. **Not** authorized without a fresh explicit decision: Desktop launch/build against the installed Hermes profile (Phase 1301 runtime isolation of `HERMES_HOME`, Electron userData, app ID and updater comes first), `hermes update` in the submodule, Docker/service operations for DeGram, paid inference, package installs, CAD/graph/CDE writes. The public fork never receives `.secrets/`, credentials, `Publications/`, `DG_OBSIDIAN/` content or unpublished manuscripts.

### Session-end commits with the submodule

The session commit (protocol below) is a framework commit. It may include `.gitmodules` and the `apps/degram` gitlink only when the child commit already exists on the fork. Child source changes get their own child commit, made only with explicit authorization, in the component repo, before the framework commit.

## Graph Schema v4

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
| `DesignState` | ValidGraph | `StateId` | `kind` (ObjState/ParamState/PropState) |
| `Run` | ValidGraph | `Run_Id` | `Run_Id` |
| `Representation` | Computgraph | `nativeId`+`platform`+`project` | `nativeId` |
| `SharedProperty` | Computgraph | `dgId`+`propertyName`+`project` | `propertyName` |
| `Object` | Computgraph | `cgId`+`definitionId`+`project` | `objectName` |
| `Behavior` | Computgraph | `definitionId`+`project` | `definitionId` |
| `Algorithm` | Computgraph | `algIndex`+`definitionId`+`project` | `algorithmName` |
| `Procedure` | Computgraph | `cgId`+`definitionId`+`project` | `procedureName` |
| `Pattern` | Computgraph | `cgId`+`definitionId`+`project` | `patternName` |
| `Parameter` | Computgraph | `cgId`+`definitionId`+`project` | `parameterName` |
| `Interface` | Computgraph | `cgId`+`definitionId`+`project` | `interfaceName` |

### ValidGraph Labels

| Label | Graph | Properties | Description |
|-------|-------|-----------|-------------|
| `DesignState` | ValidGraph | `StateId` (key), `kind` (ObjState/ParamState/PropState), `statePayloadJson` (v2 envelope); optional `source`, `sourceRuleId`, `provider`, `model`, `determinabilityClass` (Phase 38, present only on AI-generated accepted candidates) | 3-part design state composition |
| `Run` | ValidGraph | `Run_Id` (key), `ValidStatus` (Boolean list per ObjState), `SendStatus` (single Boolean) | Validation run metadata |
| `IntegrationConfig` | ValidGraph | Speckle/project integration settings | External viewer integration |
| `ValidationEntity` | ValidGraph | Per-entity validation results | Individual pass/fail records |

### DesignState kinds

| Kind | Prefix | Component | Content |
|------|--------|-----------|---------|
| `ObjState` | `OS_` | OBJECT STATE | Object + Geometry + Label |
| `ParamState` | `DS_` | PARAMETER STATE | Parameters list (sliders, toggles) |
| `PropState` | `PS_` | PROPERTY STATE | Rule + DataProperty + PropValue |

### Relationships

`HAS_BODY`, `HAS_HEAD` (Rule→Atom, with `order`), `REFERS_TO` (Atom→entity; Object→Class cross-layer), `ARG` (Atom→Var/Literal, with `pos`), `HAS_STATE` (DesignState→ObjState/ParamState/PropState, read-side composition), `IN_SNAPSHOT` (ValidationRun→DesignState `source:"mapping-snapshot"`, the model snapshot «Снимок модели» of a confirmed mapping; server-authored only, Phase 1303-26), `HAS_REPRESENTATION` (entity→Representation), `HAS_SHARED_PROPERTY` (entity→SharedProperty), `HAS_BEHAVIOR` (Object→Behavior), `HAS_ALGORITHM` (Behavior→Algorithm), `HAS_PROCEDURE` (Algorithm→Procedure), `HAS_PATTERN` (Procedure→Pattern), `PATTERN_HOST_TO` (Pattern→Pattern nesting), `HAS_PARAMETER` (Procedure→Parameter), `HAS_INTERFACE` (Procedure→Interface), `PARAM_LINK` (Parameter→Interface, wire-derived), `ATTRIBUTE_OF` (Atom→Parameter, Metagraph→Computgraph cross-layer bridge; derived from `inputBindings` at Computgraph publish time, project-scoped, never authored by rule ingestion)

Every Computgraph entity node (Object, Procedure, Pattern, Parameter, Interface) carries an optional `dgId` property — a deterministic platform-neutral identity (`dg:` + 16 uppercase hex). See `spec/DG-ID.md` for the normative specification (format, minting, collision policy, binding model).

### Identity Registry (Computgraph)

### Rule ID Format

`R_<DOMAIN>_<PROPERTY>_<LIMIT>_V` (e.g. `R_URB_HEIGHT_MAX_75_V`)

### Schema Change Propagation

When changing graph structure, update ALL: `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompts, `config.template.js`, `data-service/app.py` Cypher, `.github/copilot-instructions.md`, `README.md`, `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md` (RDF/OWL mapping contract — a new relationship type needs a TBox-to-LPG correspondence row), `ontology/dg-shapes.ttl` (SHACL shapes — keep in sync with any structural/data-integrity change), `llm/structure_rules.json` (carries `inputBindings`, a rule-referencing artifact, alongside `mappings` — Phase 38), `spec/EVIDENCE-CONTRACT.md`, and any Cypher templates in Python/JS.

`shaclReportJson`/`evidenceEnvelopeJson` (ValidationRun/Run node properties, `spec/DATABASE.md`) are schema-propagation surfaces themselves — `shaclReportJson` added Phase 823, `evidenceEnvelopeJson` added Phase 1200, both sibling to `statePayloadJson`/`rulesJson`.

**Rule partition policy:** `spec/RULE-PARTITION-POLICY.md` governs which validation system (SWRL VALIDATOR vs. SHACL) owns a given rule category — consult it before adding a new SHACL shape or a new SWRL rule category, and update it if a schema change shifts the partition line.

**Evidence and status contract:** `spec/EVIDENCE-CONTRACT.md` governs the canonical validation-outcome status vocabulary and the evidence envelope shape — consult it before adding, renaming, or reinterpreting a validation outcome status or an evidence field, and update it if a schema change shifts the envelope.

**SWRL subset boundary:** `spec/SWRL-SUBSET.md` governs which SWRL atom types the parser recognizes, which builtins the C# evaluator implements, and which status each unsupported construct yields — consult it before adding a builtin, adding an atom type, or changing which construct yields which status, and update it (including its two machine-checked fenced blocks) if such a change shifts the boundary.

**Reproducibility contract:** `spec/REPRODUCIBILITY.md` governs the determinism boundary — the three determinism classes, the measured/unmeasured scope table, the projection + closed exclusion list, the provenance field list, and the reproducibility classes — consult it before adding an LLM call site or claiming a path is deterministic, and update its machine-checked fenced block if such a change shifts the scope.

**Security boundary contract:** `spec/SECURITY-BOUNDARY.md` governs the trust zones, the local and multi-user deployment profiles, the three principal types, the public-route allowlist and full route-policy table, the known-default secret list and the rotation runbook — consult it before adding a route, a principal, a published port or a secret, and update its machine-checked fenced blocks if such a change shifts the boundary.

## Common Commands

```bash
# Start all services
docker compose up -d

# Rebuild V2 UI after ui-v2/ changes (--no-cache required!)
docker compose build --no-cache design-grammars && docker compose up -d design-grammars

# V2 UI dev server (proxies /neo4j /n8n /data-service to :8080)
npm --prefix ui-v2 run dev

# Build Grasshopper plugin
dotnet build .\DG\DG.sln -c Release

# Run C# tests
dotnet test .\DG\tests\DG.Tests\

# DeGram workspace (submodule apps/degram)
git submodule update --init apps/degram          # fresh clone
python tools/degram/workspace.py verify           # preflight before any DeGram task
python tools/degram/workspace.py install-context  # (re)generate apps/degram/.hermes.md
python -m unittest discover -s tools/degram/tests -v
```

## Current Priorities

> The live list is `DG_OBSIDIAN/00-home/Current priorities.md` + `.planning/STATE.md`; this section can lag behind them.

0. **v13.0 DeGram Agent**: active milestone (phases 1300–1307, `apps/degram` submodule). Phase 1300 acceptance gates are still open; Phase 1301 runtime isolation must land before any Desktop launch. Follow the DeGram section above.
1. **v8.0 follow-ups (shipped, still open)** — approve and run `migrations/2026-07-07_validationgraph_to_validgraph.cypher` (v2.0-era validation runs invisible until then); reconcile live n8n workflows with `n8n/workflows/*.json` (live versions drifted ahead of repo)
2. **v9.0 AI Workflow Intelligence** — active (renumbered to global phases 28-40; GH canvas → Computgraph serialization pipeline elaborated into phases 32-37). LLM gateway (Phase 28/cloud-llm-connector) shipped and is what the V2 UI's Graph Viewer prompt console calls
3. **v10.0 Script Intelligence** — planned, phases 41-49, isolated; activates after v9.0
4. **v4.0 BOT Ontology Bridge** — bridge design-grammar concepts with the BOT standard and Topologic for cross-vocabulary architecture analysis

## Known Gotchas

- **Docker layer caching** can serve stale `index.html` — always use `--no-cache`
- **Browser cache** prevents seeing UI updates — hard-refresh (Ctrl+Shift+R) or incognito
- **Neo4j node tagging** required after n8n ingestion — orphaned nodes need `graph`/`project` props; the V2 UI claims `default-project` nodes for the active project after each ingest (legacy parity)
- **v2.0-era validation data** carries `graph:'ValidationGraph'` (pre-v4) — invisible to data-service until `migrations/2026-07-07_validationgraph_to_validgraph.cypher` is approved and run
- **LLM Cypher output** needs bracket nesting validation before execution
- **Edit mode** requires cleanup of old atoms (MATCH-DELETE) before re-creation
- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards all GH-dependent code in DG.Grasshopper
- **Canvas breakage** — old .gh files referencing CLASSIFICATOR/VALIDATION RUNS/old REINSTATE show missing-component placeholders. Re-wire per `docs/RELEASE-NOTES-v7.0.md`.
- **Old component GUIDs in saved .gh files** — opening a v2.0 canvas without updating GUID mapping file causes missing components. The VALIDATION RUNS GUID (A7F2C3E1) is replaced by VALIDATION GRAPH (95fc9d32-307e-41fd-a158-bfae49a3dc2a). CLASSIFICATOR is fully removed — no replacement GUID.
- **Standalone ParamStates are invisible to VALIDATION GRAPH before Phase 38 plan 38-05** — `Neo4jValidGraphRepository.RunsQuery` reads `(:ValidationRun)` nodes only. A `:DesignState` written by `POST /computgraph/candidates/accept` needs the additive second read and a dotnet rebuild before it appears on the canvas.
- **`reinstateParameterId` is nullable and absent on pre-Phase-38 publishes** — treat its absence as "not resolvable", never as an error; the parameter is excluded from generation with a reported reason.

## Tech Stack Summary

| Layer | Language | Key Tech |
|-------|----------|----------|
| Grasshopper Plugin | C# (.NET 7/9) | Neo4j.Driver, Rhino 8 SDK (14 components) |
| Data Service | Python 3 | FastAPI, neo4j, specklepy, pydantic |
| Workflows | JavaScript (n8n) | Webhook, HTTP, Function nodes |
| Main UI (V2) | JSX | React 18 + Vite 5 (`ui-v2/`), canvas datascape |
| Legacy UI (archived) | JavaScript | React 18 CDN no-JSX SPA + separate model-viewer |
| LLM | — | Provider-agnostic gateway (Anthropic/OpenAI via API key, Ollama local fallback) |
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

# DSH Subagent Delegation (dsh-crew)

Implementation subtasks go to **DeepSeek Harness (DSH) workers**, not to Claude subagents. The `dsh-crew` plugin (user scope) provides two agent types and the `dsh_*` MCP tools:

| Agent | Tier | Delegate |
|---|---|---|
| `dsh-crew:ds-flash` | flash — fast, cheap | Mechanical, well-scoped work: renames, small scripts, config lookups, a unit test in an existing style, straightforward fixes |
| `dsh-crew:ds-pro` | pro — stronger reasoning | Multi-file changes, debugging, refactors, anything needing analysis |

When in doubt start with `ds-flash`. For fan-out use `dsh_spawn_worker` + `dsh_worker_result` instead of blocking `dsh_run_worker`.

### When NOT to use DSH

- **GSD / superpowers workflows** that spawn their own typed agents (`gsd-executor`, `gsd-planner`, `gsd-verifier`, …) keep those agent types — their protocols live in the agent definitions. The standing preference for inline GSD work over subagents still applies.
- **Claude-specific agents** (`claude-code-guide`, `statusline-setup`, `scientific-paper-revision:*`) and read-only codebase sweeps (`Explore`) stay on Claude.
- **Anything touching secrets**: never put `.secrets/` contents, API keys, `.credentials.yaml`, or tokens into a brief, and tell the worker not to read `.secrets/`. Briefs and the files a worker reads leave the machine to the DeepSeek API.
- **Unpublished PhD material** (`Publications/`, `DG_OBSIDIAN/dissemination/`, manuscript drafts) — ask the user before delegating.
- **Hub unreachable** (`dsh_worker_config` reports `hub_reachable: false`): fall back to a Claude subagent and tell the user. Standalone mode is not configured (no `~/.config/dsh-crew/.env`).

### Writing the brief

The worker has **zero conversation context**. Every brief must carry:
- Absolute paths (`C:\Users\Admin\source\repos\design-grammar-system\...`) for every file and directory involved.
- Exact acceptance criteria and the verify command (`dotnet test .\DG\tests\DG.Tests\`, `npm --prefix ui-v2 run build`, `pytest`, …).
- What NOT to touch: `DG/src/*/bin/`, `DG/src/*/obj/`, lockfiles, `graphify-out/`, `.planning/milestones/`, `DG_OBSIDIAN/archive/`.
- The relevant project rules — Schema Change Propagation list, `#if GRASSHOPPER_SDK` guards, graph schema v4 — when the task touches them.
- **"Do not commit, push, or publish."** Commits follow the session protocol above and are made by Claude.

### Parallelism and verification

- **One writer per repo.** The cwd lock refuses a second dispatch into a held workspace (it names the holder). Parallel writers need disjoint file territories plus a named owner for each seam; `allow_concurrent_cwd: true` is for read-only tasks only.
- **Trust artifacts, not the worker's summary.** After every worker: `git status` / `git diff`, then run the verify command yourself before reporting success. Report unverified claims as unverified.
- Worker nesting is capped at depth 3 — do not brief a worker to spawn another worker.

### Environment

- The hub runs inside **DSH Desktop** at `http://127.0.0.1:43129` (set in `~/.config/dsh-crew/config.json`, not the plugin's `3080` default). DSH Desktop must be running.
- Start DSH Desktop from the Start menu, **not** from a VS Code terminal: the inherited `ELECTRON_RUN_AS_NODE` makes it exit silently with code 0. Closing its window only hides it to the tray — quit from the tray icon to restart.
- Session switches: `/dsh-crew:status`, `/dsh-crew:config`, `/dsh-crew:off`, `/dsh-crew:on`, `/dsh-crew:playbook`.

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

# Jev routing policy

Use Jev automatically when the task involves choosing a model, classifying
the task, estimating the next step, or deciding whether a task requires
deep reasoning.

For ordinary conversation, translation, short factual answers, and simple
formatting, do not call Jev explicitly unless routing middleware already
handles the request.

For model selection:
- Prefer `jev_route` with `apply: false` when only a recommendation is needed.
- Use `apply: true` only when changing the model for the current turn is useful.
- Never treat a Jev result as permission to execute commands, modify files,
  send messages, or make external changes.

For bounded judgments:
- Use `jev_evaluate` with `task_triage` for task classification.
- Use `next_step` to choose the next action.
- Use `relevance` to filter candidate information or actions.

Avoid sending secrets, API keys, credentials, or unnecessary private project
content to Jev.