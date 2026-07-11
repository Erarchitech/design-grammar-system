# Design Grammar System

## What This Is

A platform that automates architectural compliance checking. Architects write design rules in natural language, which an LLM pipeline converts to SWRL ontology atoms stored in a Neo4j graph. A Grasshopper plugin evaluates BIM geometry against these rules, captures parameterized design states, and publishes color-coded validation results to a Speckle 3D viewer. Architects can save and compare design alternatives by reinstating captured parameter states. The web UI (Grammar Viewer) provides rule management, graph visualization, and the Model Viewer provides validation run browsing with grouping by rule or design state.

## Core Value

Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.

## Current Milestone: v8.1 Platform Setup Regions

**Goal:** Extend the V2 landing ring with four new region callouts — AI Engine, Connectors, Reasoner, DG API Documentation — each opening a real screen layer wired to backend services. Positioned between shipped v8.0 (V2 UI) and parked v9.0 (AI Workflow Intelligence). Phases numbered 810–819 per the milestone-derived numbering convention (vX.Y → X·100+Y·10, max 10 phases).

**Target features:**

- Ring extension: 4 new region callouts (AI Engine, Connectors, Reasoner, DG API Docs) placed along the particle ring alongside Graph Viewer / Model Viewer / Projects, with fly-in navigation and screen layers
- AI Engine screen: LLM provider/model selection + manual API key input, wired to the existing data-service LLM gateway (`/llm/settings`, encrypted-at-rest keys)
- Connectors: 14 connectors in 5 categories (VPL: Grasshopper, Dynamo · BIM Authoring: Revit, Blender, Tekla, Archicad, Civil3D, Infraworks · BIM Coordination: Navisworks, Solibri · BCF Trackers: BIMCollab, BIMTrack · Visualization: Lumion, Twinmotion); credential creation with copyable tokens for pasting into connector components in target software; per-connector activation status + last-connection date
- Connector backend: data-service credential CRUD + authenticated heartbeat/status endpoints recording each connector's last request/post
- Reasoner screen: reasoner model selector for the Validation Graph — HermiT and Pellet as placeholders until real reasoner integration is elaborated
- DG API Documentation: in-app, Revit-API-style structured doc browser (sections → endpoints/classes → members) documenting the DG connector API, extendable via content files

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ **RULE-01**: User can insert design rules via natural language prompt — v1.0
- ✓ **RULE-02**: User can query existing rules via natural language — v1.0
- ✓ **RULE-03**: User can edit existing rules — v1.0
- ✓ **GRAPH-01**: Rules are visualized as interactive graph (NeoVis) — v1.0
- ✓ **GRAPH-02**: Graph nodes are project-isolated — v1.0
- ✓ **LLM-01**: LLM converts NL rules to SWRL/Cypher — v1.0
- ✓ **VAL-01**: Grasshopper plugin validates BIM geometry against rules — v1.0
- ✓ **VAL-02**: Validation results publish to Speckle as colored overlays — v1.0
- ✓ **UI-01**: Multi-page SPA (Register, Home, Project, Graph Viewer) — v1.0
- ✓ **UI-02**: Model Viewer with Speckle 3D viewer integration — v1.0
- ✓ **UI-03**: Per-run graphics state and screenshot persistence — v1.0
- ✓ **DGST-01..03**: Design state capture (Number/Integer/Boolean, stable IDs, timestamps) — v2.0
- ✓ **DGCL-01..03**: Classificator state input and run persistence to Neo4j — v2.0
- ✓ **DGRN-01..03**: Validation runs retrieval with rule/state filtering — v2.0
- ✓ **REIN-01..03**: Trigger-based reinstatement with per-parameter status — v2.0
- ✓ **MVGP-01..03**: Model Viewer grouping by rule and design state — v2.0
- ✓ **INTG-01..03**: E2E state lifecycle, backward compat, actionable errors — v2.0
- ✓ **ONTO-01..06**: Ontology V7 baseline — V6→V7 rename table, DesignGrammar-V7.owl, extension facades, catalog, port-IRI map, markdown docs — Phase 13
- ✓ **v7.0 (Phases 13–20)**: Ontology-aligned 14-component Grasshopper addin — state trio (ObjState/ParamState/PropState), DesignState composition, graph access chain (GRAPH DECONSTRUCT, ONTOGRAPH, VALIDATION GRAPH), VALIDATOR rework, CLASSIFICATOR elimination, SpecGraph rename, schema v4 propagation — shipped 2026-07-05, archived to `.planning/milestones/v7.0-phases/`
- ✓ **v8.0 (Phases 21–27)**: Design Grammars V2 UI — light clinical-blueprint interface at `ui-v2/` (Vite + React): design-system foundation, particle-ring landing with inline auth, canvas datascape Graph Viewer (live Neo4j + n8n), Model Viewer over data-service validation runs, Projects screen, layered navigation shell, deployment cutover at :8080, Speckle 3D embed — shipped 2026-07-07, archived to `.planning/milestones/v8.0-phases/`

### Active

<!-- Current scope. Building toward these. -->

**Milestone v8.1 — Platform Setup Regions** (see `.planning/REQUIREMENTS.md` for REQ-IDs)

- [ ] Ring extension: 4 new region callouts + screen layers (AI Engine, Connectors, Reasoner, DG API Docs)
- [ ] AI Engine screen (provider/model selection, API key input, wired to LLM gateway `/llm/settings`)
- [ ] Connector credential backend (data-service CRUD, token generation, heartbeat/status endpoints)
- [ ] Connectors screen (14 connectors / 5 categories, credential create+copy, status + last-connection date)
- [ ] Reasoner screen (HermiT/Pellet placeholder selector, persisted selection)
- [ ] DG API Documentation (Revit-API-style in-app doc browser, extendable content)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Fine-tuning LLM — using prompt-constrained approach instead
- OAuth/SSO — client-side SHA-256 auth sufficient for current use
- Mobile app — desktop/web-first for architect workflows
- Arbitrary object/geometry serialization in state capture — limited to Number/Integer/Boolean for deterministic reinstatement (v2.0 decision, still holds)
- Cross-project state sharing — project isolation remains mandatory
- v3.0 Phases 8–12 component plan (CLASSIFICATOR rework, RUN DECONSTRUCT, VARIABLE NAME, IdRefs/GeoRefs DESIGN STATE) — superseded 2026-07-02 by the GH_DesignGrammars.pdf schema; do not re-add: CLASSIFICATOR is eliminated by design, run reading is VALIDATION GRAPH's role
- Neo4j label renames beyond Knowledge*→Spec* (e.g. ValidationRun→Run, DatatypeProperty→DataProperty in DB) — DB keeps existing labels/graph values; ontology↔DB mapping is documented instead (propagation cost outweighs benefit)

## Current State

v8.0 (Design Grammars V2 UI) shipped 2026-07-07 and archived; post-ship Phase 27 added the Speckle 3D embed 2026-07-08. v9.0 AI Workflow Intelligence remains parked in `.planning/milestones/v9.0-phases/` (Phase 28 cloud-llm-connector executed — its LLM gateway is what the AI Engine screen will surface). Starting v8.1: four new setup regions along the landing ring (AI Engine, Connectors, Reasoner, DG API Documentation), phases 810+.

**Grasshopper Plugin (C# .NET 7/9):**
- 5 components: DESIGN STATE, CLASSIFICATOR, VALIDATOR, VALIDATION RUNS, REINSTATE
- ErrorMessageTemplates with What+Where+How-to-fix pattern
- 61+ unit tests, 4 E2E integration tests

**Data Service (Python FastAPI):**
- Validation publish/delete with structured JSON error responses
- State projection in validation runs retrieval
- 23+ pytest tests

**Model Viewer (React + Vite):**
- ValidationRunsStrip with Rule/Design-State grouping
- Collapsible groups, resize handle, localStorage persistence
- Error hint extraction from structured API responses

## Context

- 12+ Docker services orchestrated via docker-compose.yml
- Neo4j single database with project-scoped node isolation
- Main UI is single-file React 18 SPA (no build step, no JSX)
- Model Viewer is separate Vite+React app
- LLM inference via local Ollama (llama3.1)
- n8n handles webhook workflows for rule ingestion and querying

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single Neo4j DB with property isolation | Simpler ops, project property on every node | ✓ Good |
| No JSX build for main UI | Faster iteration, no build tooling | ✓ Good |
| SWRL bespoke regex parsing | Lighter than OWL vendor libs | ✓ Good |
| LLM prompts embed schema constraints | More flexible than fine-tuning | ✓ Good |
| Violation rules invert constraint in SWRL body | Matches standard SWRL semantics | ✓ Good |
| Knowledge graph separate from SWRL metagraph | Different data model, no validation needed | ✓ Good — v1.1 |
| Obsidian-style approach (no RAG) | Keeps system simple, markdown-based | ✓ Good — v1.1 |
| Simple inline editor (no separate Vite app) | Consistent with no-JSX pattern | ✓ Good — v1.1 |
| Session tracking for all knowledge interactions | Audit trail + browsable history | ✓ Good — v1.1 |
| ErrorMessageTemplates as static class in DG.Core.Services | What+Where+How-to-fix pattern for all error surfaces | ✓ Good — v2.0 |
| Typed design state limited to Number/Integer/Boolean | Deterministic reinstatement, bounded payload size | ✓ Good — v2.0 |
| Rising-edge trigger for reinstatement | Prevents auto-apply on wire change | ✓ Good — v2.0 |
| Separate Vite app for Model Viewer | Complex 3D viewer needs build tooling | ✓ Good — v2.0 |
| localStorage per-project for grouping prefs | No cross-project state leakage | ✓ Good — v2.0 |
| Single `:DesignState` label + `kind` property | Mirrors `Rule.kind` pattern; deterministic NeoVis; lower propagation surface | ✓ Carried into v7.0 (kind enum revised to ObjState/ParamState/PropState) |
| New GUID for RUN DECONSTRUCT (no migration shim) | Clean break from VALIDATION RUNS; accept canvas breakage | ✗ Superseded — v7.0 (component dropped; VALIDATION GRAPH takes the role) |
| CLASSIFICATOR full input reset (no backward compat) | Cleanest v3.0 API | ✗ Superseded — v7.0 (CLASSIFICATOR eliminated entirely) |
| PropValues = renamed Values (same DataTree structure) | Narrower semantic scope | ✗ Superseded — v7.0 (PROPERTY STATE owns value binding) |
| VALIDATOR input State → DefState | Consistency with CLASSIFICATOR output name | ✗ Superseded — v7.0 (input is DesignState composition) |
| Var merge key includes `project` | Fixes latent v2.0 cross-project collision bug | ✓ Shipped — v3.0 Phase 7 |
| Variable type inferred at read-time (not stored on Var nodes) | 100% computable from atom structure | ✓ Shipped — v3.0 Phase 7 (drives RULE DECONSTRUCT Objects/DataProperties partition) |
| ObjectRef is user-supplied string (not geometry-hash) | Geometry regenerates on every GH solve; hash would break cross-run identity | ✓ Carried into v7.0 (OBJECT STATE Label input) |
| Full ontology rename V6→V7 to match GH schema | V6 is publication-only, no runtime consumer; schema is the single source of naming | — Pending — v7.0 |
| V6→V7 IRI mapping file (recovery-only) | Guard against rename regret; publications reference V6 names | — Pending — v7.0 |
| KnowledgeGraph→SpecGraph runtime rename in scope | Closes pre-existing ontology↔runtime drift; GRAPH DECONSTRUCT exposes SpecGraph | — Pending — v7.0 |
| Component ports: update where overlapping, keep where no overlap | Preserves publish extras (DataServiceUrl, Report, ValidationRunId…) without schema conflict | — Pending — v7.0 |
| DB keeps existing labels except Knowledge*→Spec* | Ontology↔DB mapping documented; avoids invasive migrations | — Pending — v7.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-11 — milestone v8.1 Platform Setup Regions started*
