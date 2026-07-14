---
tags: [home, priorities]
date: 2026-07-12
---

# Current Priorities

## Active

1. **v9.0 AI Workflow Intelligence — Phases 28-40 (+32.1)** — Phase 32.1 "Cross-Platform Identity and Mapping (DG ID)" inserted after Phase 32 (2026-07-13), 7 plans across 3 waves, plan-checker VERIFICATION PASSED. Delivers `dgId` as a durable platform-neutral identity spine so a GH-authored object and its Revit-generated counterpart resolve to one identity within a Design State, with cross-platform shared properties (Ladybug insulation → Revit). Researched against Rhino.Inside.Revit/Speckle/IFC/BHoM state of the art. See [[sessions/2026-07-13 Phase 32.1 DG ID cross-platform identity planning|session]] and [[decisions/Phase 32.1 DG ID cross-platform identity design|decision]]. Next: Phase 32 executes first (no 32.1 dependency), then `/gsd-execute-phase 32.1`.
2. **v9.0 AI Workflow Intelligence — Phases 28-40** — ✅ Phase 29 execution + UAT → diagnosis → planning complete (2026-07-12). Phase 29 (DG-Aware Context Layer) all 5 plans executed, 57/57 tests green, live n8n reconciled. UAT identified 1 issue (graph_query design-state schema mismatch): root cause diagnosed, 3 fix plans (29-06/29-07/29-08) created and verified. Next: `/gsd-execute-phase 29 --gaps-only` to execute fixes. See [[sessions/2026-07-12 Phase 29 UAT diagnosis and fix planning|session]].
2. **v8.2 Connector Integration & Reasoning Engine — Phases 820-824** — ✅ Shipped 2026-07-12 (override closeout — Phases 822/823/824 verification deferred). Phase 824 CONNECTOR platform-token heartbeat code-complete, 234/234 tests, build clean. Formal `/gsd-complete-milestone v8.2` done. **Deferred:** Phase 822 Reasoner Screen, Phase 823 SHACL Layer, Phase 824 CONNECTOR UAT (live Rhino/data-service) → later.
3. **v8.1 Platform Setup Regions — Phases 810-816** — ✅ Complete (2026-07-11). All 7 phases executed and verified. Phases archived to milestones/v8.1-phases/ on 2026-07-12. Formal `/gsd-complete-milestone v8.1` still pending (low priority).
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

- **Phase 32.1 planned — DG ID cross-platform identity** — 2026-07-13. 7 plans across 3 waves (minting service, spec+ADR, Neo4j registry+API, shared-property proof, Computgraph model wiring, ObjState wiring, schema propagation). Plan-checker found 1 blocker (DGID-02 detach missing) + 2 warnings, revised, re-verified — PASSED. See [[sessions/2026-07-13 Phase 32.1 DG ID cross-platform identity planning|session]].
- **Phase 823: SHACL Validation Layer executed** — 2026-07-12. All 6 plans executed via `/gsd-execute-phase 823`. SHACL shapes (8 NodeShapes across 3 severities), ValidGraph→RDF ABox exporter, non-fatal sidecar proxy in data-service, Grasshopper DTO+Validator wiring, ModelScreen SHACL panel. 4 Docker containers rebuilt with --no-cache. All tests: 226/226 DG.Tests, 35/35 dg-reasoner, 111/111 data-service, ui-v2 build clean. CR-01 truthy check bug documented. 8 design decisions recorded. See [[sessions/2026-07-12 Phase 823 SHACL Validation Layer execution|session]].
- **Phase 822 executed (2026-07-12)** — 4 plans: label enrichment `{iri,label}`, HermiT integrated status flip, ReasonerScreen 4-state verdict machine, E2E UAT. 3 E2E tests pass with live containers. See [[sessions/2026-07-12 Phase 822 planning — OWL 2 DL Reasoner Screen Wiring|session]].
- **Phase 821 executed** — 2026-07-12. dg-reasoner sidecar with hybrid Cypher→RDF pipeline, pySHACL validation, code review (7 findings fixed). Full verification passed (63/63 tests, source assertions, docker container check). See [[sessions/2026-07-12 Phase 821 execution — dg-reasoner sidecar, code review, full verification|session]].
- **Graph core thinking sphere animation complete** — 2026-07-12. Full animation sequence for Ingest/Query/Edit operations. See [[sessions/2026-07-12 Graph core thinking sphere animation complete|session]].
- **v8.2 milestone initialized (Phases 820-824)** — 2026-07-11.
- **v8.1 milestone complete (Phases 810-816)** — 2026-07-11.
- **v7.0 milestone complete** — 2026-07-05. 8 phases (13–20), 34 plans, 39 requirements.
