---
tags: [home, priorities]
date: 2026-07-12
---

# Current Priorities

## Active

1. **v8.2 Connector Integration & Reasoning Engine — Phases 820-824** — **Phase 824 executed (2026-07-12).** ConnectorHeartbeatClient (DG.Core, injectable, 6s-timeout) + CONNECTOR component with additive platform-token inputs (idx 6–7, GUID unchanged), heartbeat-on-Connect with Error/Warning feedback, SHA-256 token hashing + PersistentData scrub. 234/234 tests pass, build clean against Rhino 8 SDK, 3 UAT items deferred (live Rhino/data-service needed). Code-complete. See [[sessions/2026-07-12 Phase 824 CONNECTOR Credential Integration execution|session]]. **Phase 823 complete (2026-07-12):** SHACL Validation Layer, 6 plans, SHCL-01/SHCL-02 satisfied, CR-01 bug documented. **Phase 822 complete (2026-07-12):** Reasoner Screen, 4 plans, E2E verified. **Next:** `/gsd-verify-work 824` when in-Rhino UAT ready, then `/gsd-complete-milestone v8.2`.
2. **Phase 822 (OWL 2 DL Reasoner Screen Wiring)** — Должна быть выполнена до v8.2 complete. 4 плана, 3 waves. ReasonerScreen run-state machine + HermiT E2E wiring. **Status:** UAT gate (plan 04) awaits execution.
3. **v8.1 Platform Setup Regions — Phases 810-816** — ✅ Complete. All 7 phases executed and verified (2026-07-11). Formal `/gsd-complete-milestone` (MILESTONES.md entry + phase-directory archive) still pending — not blocking v8.2.
4. **v9.0 AI Workflow Intelligence — Phases 28-40** — Paused. Phase 28 (Cloud LLM Connector) executed and shipped (6/7 must-haves, 1 UAT pending). Resume by planning Phase 29. See [[sessions/2026-07-11 v9.0-v10.0 global phase renumbering|session]].
5. **v10.0 Script Intelligence — Phases 41-49** — Fully planned, isolated.
6. **v4.0 BOT Ontology Bridge** — Planned, isolated, needs renumbering (50+) per [[decisions/Global phase numbering continues across milestones|global numbering]].
7. **Migration pending on live Neo4j** — `migrations/2026-06-23_var_project_merge_key.cypher` still needs to run against a live Neo4j.
8. **T1 submission preparation** — форматирование по ITcon Author Guidelines, DOI-ссылки, рецензирование научным руководителем.

## Upcoming

- **v8.2 Complete:** Phase 822 (Reasoner Screen UAT) → Phase 824 (CONNECTOR Credential Integration) → `/gsd-complete-milestone v8.2`
- **v9.0 AI Workflow Intelligence — Phases 28-40** — Next after v8.2. Phase 28 (Cloud LLM Connector) executed and shipped (6/7 must-haves, 1 UAT pending). Plan Phase 29 (DG-aware context layer).
- **v4.0 BOT Ontology Bridge** — After v9.0
- Рецензирование T2–T4 соавтором или научным руководителем
- Реализация DesignSpaceGraph (T4) as milestone after v8.0
- Суррогатные модели для метрик после накопления >200 DesignSpacePoints
- CR-01 fix: `if valid_status is not None` в `valid_graph_export.py`
- Improve LLM Cypher generation accuracy
- Harden authentication with server-side auth
- Performance optimization for large rule sets

## Completed Recently

- **Phase 823: SHACL Validation Layer executed** — 2026-07-12. All 6 plans executed via `/gsd-execute-phase 823`. SHACL shapes (8 NodeShapes across 3 severities), ValidGraph→RDF ABox exporter, non-fatal sidecar proxy in data-service, Grasshopper DTO+Validator wiring, ModelScreen SHACL panel. 4 Docker containers rebuilt with --no-cache. All tests: 226/226 DG.Tests, 35/35 dg-reasoner, 111/111 data-service, ui-v2 build clean. CR-01 truthy check bug documented. 8 design decisions recorded. See [[sessions/2026-07-12 Phase 823 SHACL Validation Layer execution|session]].
- **Phase 822 executed (2026-07-12)** — 4 plans: label enrichment `{iri,label}`, HermiT integrated status flip, ReasonerScreen 4-state verdict machine, E2E UAT. 3 E2E tests pass with live containers. See [[sessions/2026-07-12 Phase 822 planning — OWL 2 DL Reasoner Screen Wiring|session]].
- **Phase 821 executed** — 2026-07-12. dg-reasoner sidecar with hybrid Cypher→RDF pipeline, pySHACL validation, code review (7 findings fixed). Full verification passed (63/63 tests, source assertions, docker container check). See [[sessions/2026-07-12 Phase 821 execution — dg-reasoner sidecar, code review, full verification|session]].
- **Graph core thinking sphere animation complete** — 2026-07-12. Full animation sequence for Ingest/Query/Edit operations. See [[sessions/2026-07-12 Graph core thinking sphere animation complete|session]].
- **v8.2 milestone initialized (Phases 820-824)** — 2026-07-11.
- **v8.1 milestone complete (Phases 810-816)** — 2026-07-11.
- **v7.0 milestone complete** — 2026-07-05. 8 phases (13–20), 34 plans, 39 requirements.
