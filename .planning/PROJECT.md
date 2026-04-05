# Design Grammar System

## What This Is

A platform that automates architectural compliance checking. Architects write design rules in natural language, which an LLM pipeline converts to SWRL ontology atoms stored in a Neo4j graph. A Grasshopper plugin evaluates BIM geometry against these rules and publishes color-coded validation results to a Speckle 3D viewer. The web UI (Grammar Viewer) provides rule management and graph visualization.

## Core Value

Architects can express design constraints in plain language and instantly validate 3D building models against them — no coding or ontology expertise required.

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

### Active

<!-- Current scope. Building toward these. -->

(Defined by current milestone — see below)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Fine-tuning LLM — using prompt-constrained approach instead
- OAuth/SSO — client-side SHA-256 auth sufficient for current use
- Mobile app — desktop/web-first for architect workflows

## Current Milestone: v1.1 Project Knowledge Graph

**Goal:** Add an Obsidian-style Project Knowledge graph database to Design Grammars, allowing users to store, update, and query project knowledge via natural language — separate from SWRL validation rules.

**Target features:**
- UI mode restructuring: group existing modes under "Validation" section, add new "Project Knowledge" section
- Insert Knowledge mode: load data from local repository folder or via NL prompt
- Update Knowledge mode: LLM-driven node matching from prompt, graph isolation of matches, user selects nodes, LLM edits attached notes with red-highlighted changes, user reviews in inline text editor and confirms
- Query Knowledge mode: LLM searches knowledge graph, returns NL answer in sidebar Response field
- Session tracking: every interaction (insert, update, query) saved with prompt, result, date, mode; browsable history

## Context

- 12+ Docker services orchestrated via docker-compose.yml
- Neo4j single database with project-scoped node isolation
- Main UI is single-file React 18 SPA (no build step, no JSX)
- LLM inference via local Ollama (llama3.1)
- n8n handles webhook workflows for rule ingestion and querying
- Existing Obsidian vault (DG_OBSIDIAN/) serves as project documentation — new feature brings similar concept to end users within the app
- The knowledge graph data does NOT require Grasshopper validation — it is informational only

## Constraints

- **Tech stack**: Must integrate into existing Docker Compose stack — no new external services
- **UI pattern**: Main SPA uses React.createElement (no JSX build step) — knowledge UI must follow same pattern
- **Neo4j**: Single database — knowledge nodes need distinct labeling/isolation from SWRL metagraph
- **LLM**: Same Ollama instance — knowledge queries share inference capacity with rule processing
- **Simplicity**: No RAG system — simple Obsidian-style markdown-to-graph approach

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single Neo4j DB with property isolation | Simpler ops, project property on every node | ✓ Good |
| No JSX build for main UI | Faster iteration, no build tooling | ✓ Good |
| SWRL bespoke regex parsing | Lighter than OWL vendor libs | ✓ Good |
| LLM prompts embed schema constraints | More flexible than fine-tuning | ✓ Good |
| Violation rules invert constraint in SWRL body | Matches standard SWRL semantics | ✓ Good |
| Knowledge graph separate from SWRL metagraph | Different data model, no validation needed | — Pending |
| Obsidian-style approach (no RAG) | Keeps system simple, markdown-based; Neo4j full-text search + Ollama sufficient for note-scale data | — Pending |
| Simple inline editor (no separate Vite app) | Consistent with no-JSX pattern; contenteditable/pre with red spans for diff highlighting | — Pending |
| Session tracking for all knowledge interactions | Audit trail + browsable history like browser; prompt + result + date + mode per entry | — Pending |

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
*Last updated: 2026-04-05 after milestone v1.1 initialization*
