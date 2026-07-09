---
tags: [home, priorities]
date: 2026-07-08
---

# Current Priorities

## Active

1. **Model Viewer regression RESOLVED (audit-fix F-01, 2026-07-08)** — root cause was `DesignStateBindingService` dropping `ObjState.Geometry` from ElementRefs → all v7.0+ publishes sent `displayValue: []` → viewer had nothing to color/toggle. Fixed in commit `0b15ce0` + verified live (toggles hide/isolate correct object IDs, materials apply). **Остаётся:** пересобрать GH-плагин у себя (`dotnet build DG/DG.sln -c Release` — уже проверено, собирается) и перезапустить publish из Grasshopper — все старые runs без геометрии останутся серыми. Тестовый run с геометрией: `test/publish_validation_run_with_geometry.py`. See [[debugging/Model Viewer validation objects not found in Speckle world tree|debugging note]].
2. **v9.0 Phase 01 Cloud LLM Connector** — Executed (3/3 plans, 2 waves). 6/7 must-haves verified, 1 UAT pending (E2E provider switch). Ship blocked: UAT completion, gh CLI install. See [[sessions/2026-07-07 v9.0 Phase 01 execution|session]].
3. **v4.0 BOT Ontology Bridge** — Next milestone. BOT anchor nodes + ALIGNED_TO edges. See `.planning/milestones/v4.0-ROADMAP.md`.
4. **Migration pending on live Neo4j** — `migrations/2026-06-23_var_project_merge_key.cypher` still needs to run against a live Neo4j.
5. **T1 submission preparation** — форматирование по ITcon Author Guidelines, DOI-ссылки, рецензирование научным руководителем.

> ℹ️ **v3.0 superseded 2026-07-02** — Phase 7 (Schema Foundation) shipped and carried forward; Phases 8–12 dropped in favor of the GH_DesignGrammars.pdf-driven v7.0 component set. Archive: `.planning/milestones/v3.0-phases/`.
> ℹ️ **Требуется рестарт Claude Desktop/Code** — активировать graphify MCP server (зарегистрирован, но не подхвачен).
> ℹ️ **.NET SDK статус для v7.0 не подтверждён** — verify `dotnet build DG/DG.sln -c Release` before Phase 16 state-model changes land.
> ℹ️ **`workflow.use_worktrees: false`** в `.planning/config.json` — параллельное worktree-исполнение отключено из-за конфликта с `commit_docs: false`. См. [[knowledge/decisions/Worktree execution disabled due to commit_docs conflict|решение]].

## Upcoming

- **v4.0 BOT Ontology Bridge** — Next milestone
- Рецензирование T2–T4 соавтором или научным руководителем
- Реализация DesignSpaceGraph (T4) as milestone after v8.0
- Суррогатные модели для метрик после накопления >200 DesignSpacePoints
- Improve LLM Cypher generation accuracy
- Harden authentication with server-side auth
- Performance optimization for large rule sets

## Completed Recently

- **v8.0 Phases 21–26 autonomous execution + CLAUDE.md correction** — 2026-07-08. Whole milestone executed via `/gsd-execute-phase`, GSD docs written post facto. Found and fixed two live n8n bugs (fatal quote-syntax hang in graph-query, silent project-scoping failure) and confirmed the container cutover with a 7-point E2E parity pass. Corrected CLAUDE.md's architecture description — LLM calls route through the v9.0 gateway (`data-service/llm_gateway.py`), not Ollama directly. See [[sessions/2026-07-08 v8.0 Phases 21-26 autonomous execution|session]] and [[debugging/n8n workflows had a fatal quote bug and silent project-scoping failure|debugging note]].
- **Phase 27: Speckle 3D Embed executed** — 2026-07-08. 1 plan executed via `/gsd-execute-phase 27`. SpeckleViewport React component created with full viewer lifecycle, 3D/Map toggle in ModelScreen toolbar, entity click wiring to Properties sidebar. 4 code review findings fixed (CR-01 stabilised callback refs, WR-01/02/03). Build passes (931 modules). See [[sessions/2026-07-08 Phase 27 Speckle 3D embed execution|session]].
- **Phase 27: Speckle 3D Embed planned** — 2026-07-08. New v8.0 phase to replace synthetic SVG boxes with `@speckle/viewer` in V2 ModelScreen. 1 plan, 2 tasks, 6 decisions locked. Audit-fix F-02 escalated to this phase. See [[sessions/2026-07-08 audit-fix and Phase 27 Speckle 3D embed plan|session]].
- **Audit-fix F-01: DesignStateLabel code verified** — 2026-07-08. Full 6-stage pipeline checked. Code correct at every stage. Root cause: environmental (old Neo4j data before Label support). See [[sessions/2026-07-08 audit-fix and Phase 27 Speckle 3D embed plan|session]].
- **LABEL component added** — 2026-07-07. New single-purpose LABEL component accepting a `DG.Variable` (Var input) and displaying its `Name` property as text. Synchronous passthrough — no async or DB access. 3 files changed, 214/214 tests pass. Commit `82ed38e`. See [[sessions/2026-07-07-LABEL-component|session]].
- **DesignStateLabel added to DESIGN STATE + DECONSTRUCT** — 2026-07-07. New optional `DesignStateLabel` text input on DESIGN STATE composition component, new 4th output on DESIGN STATE DECONSTRUCT. Label flows through Core model, V2 serializer, GhCastingHelpers, data-service, and displays as tile header in V2 Model Viewer. 11 files changed, 214/214 C# + 14/14 Python tests pass. Commit `4d2b45e`. See [[sessions/2026-07-07 DesignStateLabel input and output|session]].
- **v8.0 Phase 21 context gathered** — 2026-07-07. Four gray areas discussed and locked. 11 decisions captured. See [[sessions/2026-07-07 Phase 21 context|session]] and [[decisions/V8 frontend build supersedes no-JSX pattern|decision]].
- **v9.0 Phase 01 executed** — 2026-07-07. 3/3 plans across 2 waves, 12 commits. LLM gateway with 3 providers. 6/7 must-haves verified. 58/58 tests pass. See [[sessions/2026-07-07 v9.0 Phase 01 execution|session]].
- **v7.0 Phase 20 executed** — 2026-07-05. 3/3 plans across 3 waves, all E2E-01..04 requirements satisfied. **v7.0 milestone complete — 8 phases (13–20), 34 plans, 39 requirements.** See [[sessions/2026-07-05 Phase 20 E2E Validation and Docs|session]].
- **v7.0 Phase 19 executed** — 2026-07-05. 3/3 plans across 2 waves, 19/19 must-haves verified, 3 requirements (GHST-05/06/07) satisfied. 207/207 non-E2E tests pass.
- **v7.0 Phase 18 executed** — 2026-07-05. 5/5 plans across 2 waves, 9/9 must-haves verified, 6/6 requirements (GHVL-01..06) satisfied. 179/179 C# + 28/28 Python tests pass.
- **v7.0 Phase 17 executed** — 2026-07-04. 4/4 plans, 24/24 must-haves verified, 5/5 requirements (GHGA-01..05) satisfied. 61 new tests.
- **v7.0 Phase 15 executed** — 2026-07-04. 5/5 plans across 2 waves, 13/14 must-haves verified.
- **v7.0 Phase 16 executed** — 2026-07-04. 6/6 plans across 3 waves, 25/25 must-haves verified, 9/9 requirements satisfied. 41 new tests.
- **v7.0 Phase 13 executed + Nyquist-validated** — 2026-07-03. 4/4 plans across 3 waves, 24/24 must-haves verified, 6/6 requirements (ONTO-01..06) satisfied. 17 commits.
- **v7.0 milestone initialized** — 2026-07-02. Analyzed `ontology/GH_DesignGrammars.pdf` (14 components). REQUIREMENTS.md (34 reqs, 8 categories) + ROADMAP.md (phases 13–20) committed.
- **Graphify-CGD-Obsidian integration Phases 1–4** — 2026-06-22. Полный проект интеграции: SKILL.md 34KB→1.2KB, 1772 dump-файла → 104 community notes, MCP server registered.
- **Ontology v6.1 vendor-neutralization** — 2026-06-01.
- **Ontology v6.0 restructure** — 2026-06-01.
- **PhD ITcon series T1–T4 drafts complete** — 2026-05-30.
- **v2.0 milestone shipped** — 6 phases, all 18 requirements validated.
- **v1.1 milestone shipped** — 7 phases, Project Knowledge Graph complete.
