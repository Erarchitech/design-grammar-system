---
tags: [home, priorities]
date: 2026-04-06
---

# Current Priorities

## Active

1. **v1.1 Phase 04 human verification** — import + activate knowledge-update workflow in n8n, run E2E test. See `04-HUMAN-UAT.md`.
2. **v1.1 Phase 04 security audit** — run `/gsd-secure-phase 4` to verify threat mitigations.
3. **v1.1 Phase 03 security audit** — run `/gsd-secure-phase 03` to verify threat mitigations.
4. **v1.1 Phase 02 human verification** — run `python test/test_knowledge_crud.py` against live Docker stack. See `02-HUMAN-UAT.md`.
5. **v1.1 Phase 01 human verification** — run `python test/test_knowledge_schema.py` against live Neo4j. See `01-HUMAN-UAT.md`.
6. **Model Viewer visual bugs** — rotation/mixed state in validation viewport needs fixing. See [[Model viewer needs rotation fix and validation management]].

## Upcoming

- v1.1 Phases 5–7 (UI panels, session history)
- ROADMAP endpoint path documentation drift (Phase 03 webhook paths vs original spec)
- Improve LLM Cypher generation accuracy (schema constraint adherence)
- Add more few-shot examples to [[n8n orchestrates LLM-powered rule ingestion and graph queries|ingest prompt]]
- Harden [[Passwords hashed client-side with SubtleCrypto SHA-256|authentication]] with server-side auth
- Consider localStorage quota management for run screenshots/settings (prune old data)

## Completed Recently

- **v1.1 Phase 04: Execution** — 2 plans, 2 waves. Three update-flow endpoints (match/propose/confirm), word_diff_html, call_n8n_sync, n8n knowledge-update workflow, E2E test script. 11 pytest tests pass. Fixed docker-compose circular dependency. Automated verification passed, human UAT pending.
- **v1.1 Phase 04: Context + Planning** — discussed 4 gray areas (match strategy, diff computation, confirm safety, n8n/data-service split), 13 decisions locked. Researched, 2 plans created and verified across all 11 checker dimensions.
- **v1.1 Phase 03: Execution** — knowledge-ingest and knowledge-query n8n workflows, sessions endpoint, integration tests. All 5 tests pass. Phase verified and marked complete.
- **v1.1 Phase 03: Context + Planning** — discussed 4 gray areas (LLM prompt design, query strategy, n8n wiring, session tracking), 11 decisions locked, researched, 2 plans created and verified.
- **v1.1 Phase 02: data-service CRUD + Folder Ingest** — folder ingest endpoint, 4 CRUD endpoints, verification script. All automated checks passed, human UAT pending.
- **v1.1 Phase 01: KnowledgeGraph schema** — Neo4j schema with labels, indexes, full-text search. Automated checks passed, human UAT pending.
- **Per-run graphics state & screenshots** — each validation run saves/restores its own Graphics Settings Bar state and viewport thumbnail.
