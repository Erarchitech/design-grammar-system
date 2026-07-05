---
tags: [home, moc]
date: 2026-04-05
---

# Design Grammar System � Knowledge Vault

Welcome to the DG knowledge base. This vault documents architecture, decisions, integrations, patterns, and operational knowledge for the **Design Grammar System** project.

## Map of Contents

### Atlas (Architecture & Stack)
- [[Architecture is a microservices Docker pipeline]]
- [[Technology stack spans C-Sharp Grasshopper and Python FastAPI and React SPA]]
- [[Neo4j stores ontology and metagraph in a single database]]
- [[Graph schema v3 is the canonical data model]]
- [[Deployment uses Docker Compose with nginx reverse proxy]]
- [[UI is a single-file React 18 SPA with no build step]]
- [[Model Viewer is a Vite-built Speckle 3D viewer]]
- [[DG Grasshopper plugin bridges Rhino to Neo4j validation pipeline]]
- [[Data-service is a FastAPI MCP bridge to Neo4j and Speckle]]
- [[n8n runs two async webhook workflows for ingest and query]]

### Integrations
- [[Neo4j provides graph storage with project-scoped isolation]]
- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[Ollama runs local LLM inference for Cypher generation]]
- [[Speckle hosts 3D BIM models for validation overlay]]
- [[NeoVis renders interactive graph visualization in browser]]
- [[FastAPI data-service bridges MCP Neo4j and Speckle]]

### Decisions
- [[Single-file React SPA avoids build tooling for main UI]]
- [[SWRL parsing is bespoke regex not vendor OWL library]]
- [[Project isolation uses property filtering not separate databases]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[Passwords hashed client-side with SubtleCrypto SHA-256]]
- [[Validation results publish to Speckle as overlay versions]]
- [[Violation rules invert the constraint in SWRL body]]
- [[Per-run graphics state and screenshot persistence]]
- [[Knowledge workflows use hybrid search-then-summarize for queries]]
- [[Update flow uses three-step match-propose-confirm with server-side diff]]
- [[DesignRuleSession nodes stored in Metagraph]]
- [[ResizeObserver wires Speckle viewer.resize on host element]]
- [[ValidationRunsStrip component with per-project localStorage persistence]]
- [[DCM ComputationGraph as 5th ontology layer]]
- [[decisions/v3.0 vendor-neutral rename deferred|v3.0 vendor-neutral rename deferred]]
- [[decisions/Worktree execution disabled due to commit_docs conflict|Worktree execution disabled due to commit_docs conflict]]
- [[decisions/Ontology V7 full rename over incremental|Ontology V7 full rename over incremental]]
- [[decisions/DesignState persists to ValidGraph not Metagraph|DesignState persists to ValidGraph not Metagraph]]
- [[decisions/Run ValidStatus is a per-object boolean array|Run ValidStatus is a per-object boolean array]]
- [[decisions/Rule properties renamed to SWRL RuleName RuleDescription in v4|Rule properties renamed to SWRL RuleName RuleDescription in v4]]
- [[decisions/Kind migration deletes orphan DesignStates on ValidGraph move|Kind migration deletes orphan DesignStates on ValidGraph move]]
- [[decisions/ValidationGraph runtime renamed to ValidGraph per D-14|D-14 — ValidationGraph runtime renamed to ValidGraph]]
- [[decisions/SpecGraph migration matches ValidGraph rename pattern with full index recreation|SpecGraph migration matches ValidGraph rename pattern with full index recreation]]
- [[decisions/Phase 16 DesignState aggregate and statePayloadJson v2|Phase 16: DesignState aggregate + statePayloadJson v2]]
- [[decisions/Phase 17 Graph Access Components layer handles and repository design|Phase 17: Graph Access Components — layer handles + repository design]]
- [[decisions/Phase 18 Rules and Validator Rework decisions|Phase 18: Rules and Validator Rework — ValidStatus per-ObjState, DesignStateBindingService, CLASSIFICATOR purge]]

### Debugging
- [[Docker layer caching can serve stale index.html]]
- [[Browser cache prevents seeing UI updates after rebuild]]
- [[Neo4j node tagging required after n8n ingestion]]
- [[LLM Cypher output needs bracket nesting validation]]
- [[Edit mode requires cleanup of old atoms before re-creation]]
- [[docker-compose depends_on cycle with n8n and data-service]]
- [[Knowledge webhook field name mismatch causes stale LLM output]]
- [[Layout overflow guards required for resizable flex children]]
- [[Worktree branch commits with spurious deletions]]
- [[Stale index name in spec-query n8n workflow]]

### Patterns
- [[Async polling pattern for n8n workflow execution tracking]]
- [[Cypher MERGE idempotent node creation pattern]]
- [[Config injection via entrypoint.sh sed replacement]]
- [[Grasshopper async component with ScheduleSolution polling]]
- [[Pydantic models validate all API boundaries]]
- [[Conditional compilation guards Grasshopper SDK availability]]
- [[Pure grouping adapter testable as plain function]]

### Business
- [[Design Grammars automates architectural compliance checking]]
- [[Target audience is architects and urban planners]]
- [[Product bridges natural language rules to graph-based validation]]

### Publications (PhD Series)
- [[publications/index|Publications index — PhD ITcon series]]
- [[publications/Series coherence map|Карта согласованности серии T1–T4]]
- [[publications/T1 — Онтологический фреймворк|T1 — Онтологический фреймворк]]
- [[publications/T2 — Кодирование правил|T2 — Кодирование правил]]
- [[publications/T3 — Отслеживание состояний|T3 — Отслеживание состояний]]
- [[publications/T4 — Дизайн-пространство|T4 — Дизайн-пространство]]

### Tools & Infrastructure
- [[Graphify-CGD-Obsidian integration improvement plan|Graphify ↔ CGD ↔ Obsidian — план интеграции]]
- [[graphify/Graph Index|Graphify Knowledge Graph — индекс по сообществам]]
- [[graphify/Graph Connections Dashboard|Graph Connections Dashboard (Dataview)]]
- [[graphify/GSD and Neo4j integration|GSD ↔ graphify и Neo4j интеграция]]
- `graphify-out/` — сырой граф (1836 nodes, 198 communities); regen заметок: `scripts/refresh_graphify.sh`

### Operational
- [[sessions/_template|Session log template]]
- [[sessions/2026-04-05 Project specification and CLAUDE.md creation|2026-04-05 Spec & CLAUDE.md]]
- [[sessions/2026-04-05 Obsidian vault creation|2026-04-05 Vault creation]]
- [[sessions/2026-04-05 Model Viewer screenshot and per-run graphics state|2026-04-05 MV screenshots & per-run gfx]]
- [[sessions/2026-04-06 Phase 01 KnowledgeGraph schema execution|2026-04-06 Phase 01 execution]]
- [[sessions/2026-04-06 Phase 02 data-service CRUD and folder ingest execution|2026-04-06 Phase 02 execution]]
- [[sessions/2026-04-06 Phase 03 context and planning|2026-04-06 Phase 03 context & planning]]
- [[sessions/2026-04-06 Phase 03 n8n knowledge workflows execution|2026-04-06 Phase 03 execution]]
- [[sessions/2026-04-06 Phase 04 context and planning|2026-04-06 Phase 04 context & planning]]
- [[sessions/2026-04-07 Phase 04 update-flow-endpoints execution|2026-04-07 Phase 04 execution]]
- [[sessions/2026-04-07 Phase 05 UI mode restructuring execution|2026-04-07 Phase 05 execution]]
- [[sessions/2026-04-08 Phase 06 execution and Phase 07 context|2026-04-08 Phase 06 execution & Phase 07 context]]
- [[sessions/2026-04-08 Phase 07 UI-SPEC design contract|2026-04-08 Phase 07 UI-SPEC]]
- [[sessions/2026-04-08 Phase 07 planning|2026-04-08 Phase 07 planning]]
- [[sessions/2026-04-08 Collapsible Workflow Cypher panels|2026-04-08 Collapsible Workflow Cypher panels]]
- [[sessions/2026-05-10 Phase 05 model-viewer grouping execution|2026-05-10 Phase 05 (v2.0) execution]]
- [[sessions/2026-05-30 PhD publications series T1-T4 drafts|2026-05-30 PhD publications T1–T4 drafts]]
- [[sessions/2026-06-01 Ontology v6.0 restructure — Core band, SpecGraph, partonomy|2026-06-01 Ontology v6.0 restructure]]
- [[sessions/2026-06-01 Ontology v6.1 vendor-neutralization|2026-06-01 Ontology v6.1 vendor-neutralization]]
- [[sessions/2026-06-22 Graphify-CGD-Obsidian integration Phase 1|2026-06-22 Graphify integration Phase 1]]
- [[sessions/2026-06-22 Graphify integration Phases 2-4|2026-06-22 Graphify integration Phases 2-4]]
- [[sessions/2026-06-23 v3.0 Phase 7 Schema Foundation execution|2026-06-23 v3.0 Phase 7 Schema Foundation execution]]
- [[sessions/2026-06-23 New PC Docker setup and n8n workflow fix|2026-06-23 New PC setup + n8n workflow fix]]
- [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|2026-07-02 v7.0 milestone init from GH_DesignGrammars schema]]
- [[sessions/2026-07-03 Phase 13 discuss - ValidGraph and per-object ValidStatus|2026-07-03 Phase 13 discuss — ValidGraph & per-object ValidStatus]]
- [[sessions/2026-07-03 Phase 13 planning - 4 plans across 3 waves|2026-07-03 Phase 13 planning — 4 plans across 3 waves]]
- [[sessions/2026-07-03 Phase 13 execution and Nyquist validation|2026-07-03 Phase 13 execution + Nyquist validation]]
- [[sessions/2026-07-03 Phase 14 planning - 7 plans across 3 waves|2026-07-03 Phase 14 planning — 7 plans across 3 waves]]
- [[sessions/2026-07-03 Phase 15 discuss - SpecGraph rename decisions|2026-07-03 Phase 15 discuss — SpecGraph rename decisions]]
- [[sessions/2026-07-04 Phase 15 execution|2026-07-04 Phase 15 execution — SpecGraph Runtime Rename]]
- [[sessions/2026-07-04 Phase 16 discuss - DG.Core state models and state components|2026-07-04 Phase 16 discuss — DG.Core state models and state components]]
- [[sessions/2026-07-04 Phase 16 planning - 6 plans across 3 waves|2026-07-04 Phase 16 planning — 6 plans across 3 waves]]
- [[sessions/2026-07-04 Phase 16 execution - 6 plans all complete|2026-07-04 Phase 16 execution — all 6 plans complete]]
- [[sessions/2026-07-04 Phase 17 discuss - Graph Access Components|2026-07-04 Phase 17 discuss — Graph Access Components]]
- [[sessions/2026-07-04 Phase 17 planning|2026-07-04 Phase 17 planning — 4 plans, 2 waves]]
- [[sessions/2026-07-04 Phase 17 execution — Graph Access Components|2026-07-04 Phase 17 execution — Graph Access Components]]
- [[sessions/2026-07-04 Phase 18 discuss - Rules and Validator Rework|2026-07-04 Phase 18 discuss — Rules and Validator Rework]]
- [[sessions/2026-07-04 Phase 18 planning — research|2026-07-04 Phase 18 planning — research]]
- [[sessions/2026-07-04 Phase 18 UI design contract|2026-07-04 Phase 18 UI design contract — UI-SPEC approved]]
- [[sessions/2026-07-05 Phase 18 execution — Rules and Validator Rework|2026-07-05 Phase 18 execution — 5 plans complete, 9/9 verified]]
- [[sessions/2026-07-05 Phase 18 planning — 5 plans 2 waves with Path A ClassIri|2026-07-05 Phase 18 planning — 5 plans, 2 waves, Path A ClassIri]]
- [[sessions/2026-07-04 Phase 15 planning — SpecGraph Runtime Rename (replan)|2026-07-04 Phase 15 replan — SpecGraph Runtime Rename]]
- [[inbox/Model viewer needs rotation fix and validation management|Inbox items]]
