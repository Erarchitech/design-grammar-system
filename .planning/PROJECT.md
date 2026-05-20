# Design Grammar System

## What This Is

A platform that automates architectural compliance checking. Architects write design rules in natural language, which an LLM pipeline converts to SWRL ontology atoms stored in a Neo4j graph. A Grasshopper plugin evaluates BIM geometry against these rules, captures parameterized design states, and publishes color-coded validation results to a Speckle 3D viewer. Architects can save and compare design alternatives by reinstating captured parameter states. The web UI (Grammar Viewer) provides rule management, graph visualization, and the Model Viewer provides validation run browsing with grouping by rule or design state.

## Core Value

Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.

## Current Milestone: v3.0 Typed Variables and Composable Design State

**Goal:** Restructure DG schema and components around typed variables (Object vs Property) and a parent `DesignState` class composed of `DefState` + `ObjectState`, enabling cross-rule object identity, richer state composition, and a deconstructed run/rule data flow in Grasshopper.

**Target features:**

- Variable type inference (Object vs Property) from SWRL atoms (Class atom → Object; datatype property atom → Property)
- Object variable cross-rule identity — same Object variable is shared across rules; Element Ids stored on `DesignState` node persist cross-rule and regenerate only when `DefState` changes
- `DesignState` class hierarchy: parent class with `DefState` (parametric capture, existing) and `ObjectState` (new: `ObjectRef` + `GeoRef`) subclasses; unique ID prefixes per class
- New components: `OBJECT STATE` (ObjectRef + GeoRef inputs), `VARIABLE NAME` (Variable in → name out)
- Reworked `DESIGN STATE` component — inputs `ObjectState` + `DefState`; outputs `IdRefs`, `GeoRefs`, `DefState`
- Reworked `CLASSIFICATOR` — `ElementRefs` renamed to `GeoRefs` and wired from `DESIGN STATE.GeoRefs`; add `Rule`/`Objects`/`Properties`/`PropValues`/`IdRefs`/`DefState` inputs; outputs add `DefState` (renamed from `State`), `Values` (DataTree), `Variables`
- Updated `RULE DECONSTRUCT` — new outputs `Objects`, `Properties`, `Runs`; remove obsolete `Variables` and `VariableName` outputs
- Renamed `VALIDATION RUNS` → `RUN DECONSTRUCT` — input `ValidRun`; outputs `passing items`, `failing items` (both element id lists), `Run Id`, `Date created`, `State`
- `METAGRAPH` loads Runs data and gains outputs `Objects`, `Properties`, `DesignStates`, `Runs`
- Schema-propagation updates across `cypher_template.txt`, `dataset_schema.json`, n8n prompts, NeoVis config, and any Cypher templates in Python/JS

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

### Active

<!-- Current scope. Building toward these. -->

**Milestone v3.0 — Typed Variables and Composable Design State**

- [ ] Variable type inference (Object vs Property) from SWRL atoms
- [ ] Object variable cross-rule identity (shared instance + cross-rule Element Ids)
- [ ] `DesignState` class hierarchy with `DefState` + `ObjectState` subclasses
- [ ] `OBJECT STATE` and `VARIABLE NAME` Grasshopper components
- [ ] Reworked `DESIGN STATE` (IdRefs / GeoRefs / DefState outputs)
- [ ] Reworked `CLASSIFICATOR` (Rule/Objects/Properties/PropValues/IdRefs/GeoRefs/DefState inputs; Values + Variables outputs; ElementRefs → GeoRefs rename wired from DESIGN STATE)
- [ ] `RULE DECONSTRUCT` outputs Objects, Properties, Runs (Variables / VariableName removed)
- [ ] `VALIDATION RUNS` renamed to `RUN DECONSTRUCT` (passing/failing items, Run Id, Date, State)
- [ ] `METAGRAPH` loads Runs and exposes Objects / Properties / DesignStates / Runs outputs
- [ ] Unique ID prefixes for new node classes; schema-propagation updates (Cypher template, dataset schema, n8n prompts, NeoVis config)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Fine-tuning LLM — using prompt-constrained approach instead
- OAuth/SSO — client-side SHA-256 auth sufficient for current use
- Mobile app — desktop/web-first for architect workflows
- Arbitrary object/geometry serialization in DESIGN STATE — v2.0 limited to Number/Integer/Boolean for deterministic reinstatement
- Cross-project state sharing — project isolation remains mandatory

## Current State

Shipped v2.0 on 2026-05-10. All 18 v2.0 requirements validated via human UAT.

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
| Single `:DesignState` label + `kind` property | Mirrors `Rule.kind` pattern; deterministic NeoVis; lower propagation surface | — Pending — v3.0 |
| New GUID for RUN DECONSTRUCT (no migration shim) | Clean break from VALIDATION RUNS; accept canvas breakage; release notes document re-wire | — Pending — v3.0 |
| CLASSIFICATOR full input reset (no backward compat) | Cleanest v3.0 API; v2.0 canvases require re-wire | — Pending — v3.0 |
| PropValues = renamed Values (same DataTree structure) | Narrower semantic scope: Property variables only | — Pending — v3.0 |
| VALIDATOR input State → DefState | Consistency with CLASSIFICATOR output name | — Pending — v3.0 |
| Var merge key includes `project` | Fixes latent v2.0 cross-project collision bug; prerequisite for cross-rule identity | — Pending — v3.0 |
| Variable type inferred at read-time (not stored on Var nodes) | 100% computable from atom structure; avoids schema change on Var nodes | — Pending — v3.0 |
| ObjectRef is user-supplied string (not geometry-hash) | Geometry regenerates on every GH solve; hash would break cross-run identity | — Pending — v3.0 |

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
*Last updated: 2026-05-10 after starting milestone v3.0*
