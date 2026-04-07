---
tags: [home, moc]
date: 2026-04-05
---

# Design Grammar System — Knowledge Vault

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

### Debugging
- [[Docker layer caching can serve stale index.html]]
- [[Browser cache prevents seeing UI updates after rebuild]]
- [[Neo4j node tagging required after n8n ingestion]]
- [[LLM Cypher output needs bracket nesting validation]]
- [[Edit mode requires cleanup of old atoms before re-creation]]
- [[docker-compose depends_on cycle with n8n and data-service]]

### Patterns
- [[Async polling pattern for n8n workflow execution tracking]]
- [[Cypher MERGE idempotent node creation pattern]]
- [[Config injection via entrypoint.sh sed replacement]]
- [[Grasshopper async component with ScheduleSolution polling]]
- [[Pydantic models validate all API boundaries]]
- [[Conditional compilation guards Grasshopper SDK availability]]

### Business
- [[Design Grammars automates architectural compliance checking]]
- [[Target audience is architects and urban planners]]
- [[Product bridges natural language rules to graph-based validation]]

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
- [[inbox/Model viewer needs rotation fix and validation management|Inbox items]]
