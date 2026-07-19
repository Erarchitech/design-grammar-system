---
tags: [home, priorities]
date: 2026-07-12
---

# Current Priorities

## Active

1. **v9.0 AI Workflow Intelligence — Phases 28-40 (+32.1, +33, +34, +35, +36)** — Phase 36 "Computgraph Persistence and Graph Layer Display" ✅ CODE COMPLETE (2026-07-19) + UAT AUTHORED (2026-07-20). 4 plans in 1 wave executed. Code review + 1-iteration fix chain: 2 Critical + 9 Warning fixed. Delivered: `/computgraph/publish` MERGE-idempotent Cypher, DG COMPUTGRAPH PUBLISH component, ui-v2 Computgraph layer (7 labels, 3 orbits, casing fix), schema propagation. 36-UAT.md authored 2026-07-20 (4 items, SC1 is terminal integration gate proving phases 32/34/35 correct). See [[sessions/2026-07-19 Phase 36 code review and fix chain|session]] and [[sessions/2026-07-20 v9.0 UAT audit and live verification|session]].
1. **v9.0 AI Workflow Intelligence — Phases 28-40 (+32.1, +33, +34, +35)** — Phase 35 "LLM Recognition and On-Canvas Proposal Preview" ✅ CODE COMPLETE (2026-07-19). Execution: 4 plans across 2 waves (recognition backend + PreviewRegistry foundation + canvas handlers + DG STRUCTURE CONFIRM component). Code review + 1-iteration fix chain: 7 findings fixed (CR-01 accept-path + WR-01..WR-06). Iteration-2 re-verify: 0 Critical, 0 Warning, 12 Info (out of scope or deferred UAT). Verification: 370/370 C# tests, 251/251 in-container pytest. 6 live-Rhino UAT items deferred (frame recognition quality, preview undo, concurrent-solve safety, accept-survives-reopen, mixed accept/reject undo, re-preview undo stacking). See [[sessions/2026-07-19 phase-35-review-fix-verify|session]].

1. **v9.0 AI Workflow Intelligence — Phases 28-40 (+32.1, +33, +34)** — Phase 34 "Ontology Tagging Components" ✅ COMPLETE (automated scope). Execution: 3 waves, 14 code commits (DG.Core grammar foundation + OBJECT MARKER + ENTITY TAG components). Code review + 3-iteration fix chain: 12 findings fixed (1 Critical + 11 Warnings). Verification: 344/344 tests passing, Release build clean, 5 live-Rhino UAT items deferred to /gsd-verify-work. See [[sessions/2026-07-18 Phase 34 execution, review, and fix chain|session]].

1. **v9.0 AI Workflow Intelligence — Phases 28-40 (+32.1, +33)** — Phase 33 "DG Canvas Bridge" — Plans 01–03 complete (16 C# + 208 Python tests). Plan 04 UAT authored 2026-07-20 (33-UAT.md, 4 items); 2 unique robustness tests passed live (SC3 bounded-timeout error 503/0.017s, SC4 socket lifecycle 5-cycle no-leak with 200 cgContextJson response). 2 transitive tests (happy path SC1/SC2) covered by Phase 35 recognition pipeline (Group 4). See [[sessions/2026-07-20 v9.0 UAT audit and live verification|session]].

2. **v9.0 AI Workflow Intelligence — Phases 28-40 (+32.1)** — Phase 32.1 "Cross-Platform Identity and Mapping (DG ID)" inserted after Phase 32 (2026-07-13), 7 plans across 3 waves, plan-checker VERIFICATION PASSED. Delivers `dgId` as a durable platform-neutral identity spine so a GH-authored object and its Revit-generated counterpart resolve to one identity within a Design State, with cross-platform shared properties (Ladybug insulation → Revit). Researched against Rhino.Inside.Revit/Speckle/IFC/BHoM state of the art. See [[sessions/2026-07-13 Phase 32.1 DG ID cross-platform identity planning|session]] and [[decisions/Phase 32.1 DG ID cross-platform identity design|decision]]. Next: ✅ COMPLETE 2026-07-18 — all 7 plans executed, 290 C# + 15 Python tests green, golden vector `dg:BC8E62EE137E2B56` C#↔Python confirmed. See [[sessions/2026-07-18 Phase 32.1 complete — all 7 plans executed|session]].
2. **v9.0 AI Workflow Intelligence — Phases 28-40** — ✅ Phase 29 UAT RESOLVED (2026-07-20, live verification pass). Root-cause fix from gap-closure: dg_context.py VALIDGRAPH_CONCEPTS + validate_cypher converged to real ValidationRun/statePayloadJson/HAS_ENTITY shape. Live re-run 2026-07-20 confirmed SC4: (1) routing logs showed exact sequence `/context/assemble 200 → /context/generate-cypher 200 → /mcp 200 → /llm/generate 200` after user re-synced n8n graph-query-mcp.json; (2) execution-result fetch showed answer cited real runId, real statePayloadJson, real DS_*/OS_* ID scheme (not hallucination). Cosmetic: one label rendered "ConfigurationС" with Cyrillic С (pre-existing data artifact, unrelated). See [[sessions/2026-07-20 v9.0 UAT audit and live verification|session]].
2. **v8.2 Connector Integration & Reasoning Engine — Phases 820-824** — ✅ Shipped 2026-07-12 (override closeout — Phases 822/823/824 verification deferred). Phase 824 CONNECTOR platform-token heartbeat code-complete, 234/234 tests, build clean. Formal `/gsd-complete-milestone v8.2` done. **Deferred:** Phase 822 Reasoner Screen, Phase 823 SHACL Layer, Phase 824 CONNECTOR UAT (live Rhino/data-service) → later.
3. **v8.1 Platform Setup Regions — Phases 810-816** — ✅ Complete (2026-07-11). All 7 phases executed and verified. Phases archived to milestones/v8.1-phases/ on 2026-07-12. Formal `/gsd-complete-milestone v8.1` still pending (low priority).
5. **v10.0 Script Intelligence — Phases 41-49** — Fully planned, isolated.
6. **v4.0 BOT Ontology Bridge** — Planned, isolated, needs renumbering (50+) per [[decisions/Global phase numbering continues across milestones|global numbering]].
7. **Migration pending on live Neo4j** — `migrations/2026-06-23_var_project_merge_key.cypher` still needs to run against a live Neo4j.
8. **T1 submission preparation** — форматирование по ITcon Author Guidelines, DOI-ссылки, рецензирование научным руководителем.

## Upcoming

- **v9.0 UAT Pipeline (Group 4)** — ✅ Group 3 COMPLETE (2026-07-20): Phase 34 guard-rails + undo + aesthetic verified on Frame definition. Partial-reselection edge case documented as known limitation (deferred). Ready for Group 4 (Phase 35 recognition + Phase 36 publish + ui-v2 display) — the main E2E spine; see `.planning/phases/v9.0-PIPELINE-UAT.md` for unified test structure and dedup map showing how later phases transitively re-prove earlier ones.
- **v8.2 Complete:** Phase 824 (CONNECTOR Credential Integration) in-Rhino UAT → `/gsd-complete-milestone v8.2`
- **v9.0 AI Workflow Intelligence — Phases 28-40** — Phases 37 (Script Structure Validation MVP) next after UAT. Phase 38 (AI-Generated Inputs) planned. Phases 39–40 deferred (auto-validation investigation, E2E + docs).
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
