---
tags: [home, priorities]
date: 2026-04-07
---

# Current Priorities

## Active

1. **v1.1 Phase 05 verification** — Add parent class hub nodes to KnowledgeGraph NeoVis query, then complete verification checkpoint and mark phase done.
2. **v1.1 Phase 04 human verification** — import + activate knowledge-update workflow in n8n, run E2E test. See `04-HUMAN-UAT.md`.
3. **v1.1 Phase 04 security audit** — run `/gsd-secure-phase 4` to verify threat mitigations.
4. **v1.1 Phase 03 security audit** — run `/gsd-secure-phase 03` to verify threat mitigations.
5. **v1.1 Phase 02 human verification** — run `python test/test_knowledge_crud.py` against live Docker stack.
6. **v1.1 Phase 01 human verification** — run `python test/test_knowledge_schema.py` against live Neo4j.
7. **Model Viewer visual bugs** — rotation/mixed state in validation viewport.

## Upcoming

- v1.1 Phase 06 (UI Update Panel + Inline Diff Editor)
- v1.1 Phase 07 (Session History + NeoVis Knowledge View enhancements)
- Improve LLM Cypher generation accuracy
- Harden authentication with server-side auth

## Completed Recently

- **v1.1 Phase 05: Execution (in progress)** — DesignRules/Specs&Notes tabs, Insert Knowledge, Query Knowledge, KnowledgeGraph NeoVis auto-switch. Fixed stale polling + field name mismatch. Pending: parent hub nodes + verification.
- **v1.1 Phase 04: Execution** — Three update-flow endpoints, word_diff_html, n8n knowledge-update workflow. 11 pytest tests pass.
- **v1.1 Phase 03: Execution** — knowledge-ingest/query n8n workflows, sessions endpoint, integration tests.
- **v1.1 Phase 02: data-service CRUD + Folder Ingest** — folder ingest, 4 CRUD endpoints.
- **v1.1 Phase 01: KnowledgeGraph schema** — Neo4j schema, indexes, full-text search.
