---
tags: [home, priorities]
date: 2026-06-23
---

# Current Priorities

## Active

1. **Запустить pending migration** — `migrations/2026-06-23_var_project_merge_key.cypher` против live Neo4j (стек теперь работает — можно выполнить немедленно).
2. **v3.0 Phase 7 (Schema Foundation)** — 3/4 plans executed (07-01 VariableKind/Inferrer, 07-02 DefState/ObjectState/ObjectInstance models, 07-03 Var merge-key fix + DesignState Cypher block). 07-04 (schema propagation across dataset_schema.json/n8n/config.template.js/data-service) remains — resume with `/gsd-execute-phase 7`. Then Phases 8–12.
2. **Model Viewer visual bugs** — rotation/mixed state in validation viewport (carried from v1.1).
3. **T1 submission preparation** — форматирование по ITcon Author Guidelines, DOI-ссылки, рецензирование научным руководителем.
4. **Migration pending on live Neo4j** — `migrations/2026-06-23_var_project_merge_key.cypher` needs to run against a live Neo4j once the Docker stack is up (Phase 7 follow-up).

> ℹ️ **Требуется рестарт Claude Desktop/Code** — активировать graphify MCP server (зарегистрирован, но не подхвачен).
> ℹ️ **.NET SDK теперь установлен** (10.0.109) — `dotnet build`/`dotnet test` работают; `dotnet test` требует `DOTNET_ROLL_FORWARD=LatestMajor` (нет net9.0 runtime, только 7/8/10).
> ℹ️ **`workflow.use_worktrees: false`** в `.planning/config.json` — параллельное worktree-исполнение отключено из-за конфликта с `commit_docs: false`. См. [[knowledge/decisions/Worktree execution disabled due to commit_docs conflict|решение]].

## Upcoming

- Рецензирование T2–T4 соавтором или научным руководителем
- Реализация DesignSpaceGraph (T4) как milestone после v3.0
- Суррогатные модели для метрик после накопления >200 DesignSpacePoints
- Improve LLM Cypher generation accuracy
- Harden authentication with server-side auth
- Performance optimization for large rule sets

## Completed Recently

- **v3.0 Phase 7 plans 07-01..07-03** — 2026-06-23. VariableKind/VariableTypeInferrer, DefState/ObjectState/ObjectInstance models + ID generation, Var merge-key cross-project bug fix + DesignState Cypher block + migration script. See [[sessions/2026-06-23 v3.0 Phase 7 Schema Foundation execution|сессия]].
- **Graphify-CGD-Obsidian integration Phases 1–4** — 2026-06-22. Полный проект интеграции: SKILL.md 34KB→1.2KB, 1772 dump-файла → 104 community notes, MCP server registered, diff-based export (`scripts/export_graphify_conceptual.py` + `refresh_graphify.sh`), `.graphifyignore` (защита от feedback loop), bidirectional linking (frontmatter + `## Graph connections`), Dataview dashboard, GSD-паттерны. См. [[sessions/2026-06-22 Graphify integration Phases 2-4|сессия Фазы 2-4]] и [[sessions/2026-06-22 Graphify-CGD-Obsidian integration Phase 1|Фаза 1]].
- **Ontology v6.1 vendor-neutralization** — 2026-06-01. Removed Speckle/Rhino from all DG-owned ontology entities and comments. `dgv:speckleProjectId`→`dgv:externalProjectId`; ABox instances neutralized; standards/Topologic/BOT alignments retained. Runtime schema propagation pending.
- **Ontology v6.0 restructure** — 2026-06-01. Core band (Gero FBS over-layer: Object/Function/Behavior/Structure/Geometry/Topology, DesignState, Session); IRI shortening (meta#/valid#/comp#); KnowledgeGraph→SpecGraph (spec#); Reasoner→ValidationGraph (= GH Validator); unified Session; ParametricState dropped; ERD partonomy via `dg:hasPart` sub-property hierarchy; all V6 files pass XML + stale-token verification.
- **Ontology v5.0 — ComputationGraph individuals** — 2026-05-30. Added Frame/Truss example instances from Grasshopper screenshot: Object, Algorithm, 2 Procedures, 3 Patterns, 12 Parameters (Var/Const/Emg), 4 Interfaces, ParametricState.
- **Ontology v5.0 — DCM ComputationGraph** — 2026-05-30. 5th graph layer for Grasshopper parametric design (FBS: Object→Function/Behavior/Structure, Algorithm→Procedure→Pattern). BOT + Topologic extensions created. Per-vocabulary extension naming adopted.
- **PhD ITcon series T1–T4 drafts complete** — 2026-05-30. Все четыре черновика в `Publications/`, раздел `knowledge/publications/` в Obsidian создан.
- **v2.0 milestone shipped** — 6 phases, all 18 requirements validated. Design State capture, Classificator persistence, Validation Runs retrieval, Reinstatement, Model Viewer grouping, E2E hardening.
- **v2.0 Phase 06 complete** � End-to-End Hardening. ErrorMessageTemplates, structured error responses, E2E tests, UAT 5/5 passed.
- **v2.0 Phase 05 complete** � Model Viewer Grouping. State projection endpoint + ValidationRunsStrip with Rule/State grouping + draggable resize.
- **v2.0 Phase 04 complete** � Reinstatement Component. Service + GH component with rising-edge trigger, ScheduleSolution writes, assembly mismatch handling.
- **v1.1 milestone shipped** � 7 phases, Project Knowledge Graph complete.
