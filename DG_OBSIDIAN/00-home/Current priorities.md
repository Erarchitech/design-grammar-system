---
tags: [home, priorities]
date: 2026-07-02
---

# Current Priorities

## Active

1. **v7.0 Phase 13 (Ontology V7 and Contract Investigation)** — milestone just initialized, roadmap committed. Next: `/gsd-discuss-phase 13`. Must resolve the PDF-internal ValidStatus(Boolean)-vs-Status(text) conflict before locking the port↔IRI map. See [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|session]] and [[decisions/Ontology V7 full rename over incremental|rename decision]].
2. **Migration pending on live Neo4j** — `migrations/2026-06-23_var_project_merge_key.cypher` still needs to run against a live Neo4j (carried from v3.0 Phase 7 — not yet superseded, applies to v7.0 too).
3. **Model Viewer visual bugs** — rotation/mixed state in validation viewport (carried from v1.1, still open).
4. **T1 submission preparation** — форматирование по ITcon Author Guidelines, DOI-ссылки, рецензирование научным руководителем.

> ℹ️ **v3.0 superseded 2026-07-02** — Phase 7 (Schema Foundation) shipped and carried forward; Phases 8–12 dropped in favor of the GH_DesignGrammars.pdf-driven v7.0 component set. Archive: `.planning/milestones/v3.0-phases/`.
> ℹ️ **Требуется рестарт Claude Desktop/Code** — активировать graphify MCP server (зарегистрирован, но не подхвачен).
> ℹ️ **.NET SDK статус для v7.0 не подтверждён в этой сессии** — verify `dotnet build DG/DG.sln -c Release` before Phase 16+ state-model changes land.
> ℹ️ **`workflow.use_worktrees: false`** в `.planning/config.json` — параллельное worktree-исполнение отключено из-за конфликта с `commit_docs: false`. См. [[knowledge/decisions/Worktree execution disabled due to commit_docs conflict|решение]].

## Upcoming

- Phases 14–20 of v7.0: graph schema v4 propagation, SpecGraph runtime rename, DG.Core state models, graph access components, rules/validator rework, deconstruct/reinstate components, E2E validation
- Рецензирование T2–T4 соавтором или научным руководителем
- Реализация DesignSpaceGraph (T4) as milestone after v7.0
- Суррогатные модели для метрик после накопления >200 DesignSpacePoints
- Improve LLM Cypher generation accuracy
- Harden authentication with server-side auth
- Performance optimization for large rule sets

## Completed Recently

- **v7.0 milestone initialized** — 2026-07-02. Analyzed `ontology/GH_DesignGrammars.pdf` (14 components, rendered via WinRT PDF API + PIL tiling since no PyMuPDF/network available), compared against Ontology V6 (61 classes/43 obj-props/64 data-props, confirmed no runtime consumer) and the current 8-component addin. v3.0 superseded — Phase 7 carried forward, Phases 8–12 dropped. REQUIREMENTS.md (34 reqs, 8 categories) + ROADMAP.md (phases 13–20) committed. Key decisions: full ontology V6→V7 rename with recovery mapping, SpecGraph runtime rename in scope, CLASSIFICATOR eliminated. See [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|session]].
- **v3.0 Phase 7 plans 07-01..07-04** — 2026-06-23. VariableKind/VariableTypeInferrer, DefState/ObjectState/ObjectInstance models + ID generation, Var merge-key cross-project bug fix + DesignState Cypher block + migration script, schema propagation. See [[sessions/2026-06-23 v3.0 Phase 7 Schema Foundation execution|сессия]]. Shipped as v7.0's foundation.
- **Graphify-CGD-Obsidian integration Phases 1–4** — 2026-06-22. Полный проект интеграции: SKILL.md 34KB→1.2KB, 1772 dump-файла → 104 community notes, MCP server registered, diff-based export (`scripts/export_graphify_conceptual.py` + `refresh_graphify.sh`), `.graphifyignore` (защита от feedback loop), bidirectional linking (frontmatter + `## Graph connections`), Dataview dashboard, GSD-паттерны. См. [[sessions/2026-06-22 Graphify integration Phases 2-4|сессия Фазы 2-4]] и [[sessions/2026-06-22 Graphify-CGD-Obsidian integration Phase 1|Фаза 1]].
- **Ontology v6.1 vendor-neutralization** — 2026-06-01. Removed Speckle/Rhino from all DG-owned ontology entities and comments. `dgv:speckleProjectId`→`dgv:externalProjectId`; ABox instances neutralized; standards/Topologic/BOT alignments retained.
- **Ontology v6.0 restructure** — 2026-06-01. Core band (Gero FBS over-layer: Object/Function/Behavior/Structure/Geometry/Topology, DesignState, Session); IRI shortening (meta#/valid#/comp#); KnowledgeGraph→SpecGraph (spec#) — **not yet propagated to runtime as of v6.1; propagation now scheduled as v7.0 Phase 15**; Reasoner→ValidationGraph (= GH Validator); unified Session; ParametricState dropped; ERD partonomy via `dg:hasPart` sub-property hierarchy.
- **Ontology v5.0 — ComputationGraph individuals** — 2026-05-30. Added Frame/Truss example instances from Grasshopper screenshot.
- **PhD ITcon series T1–T4 drafts complete** — 2026-05-30. Все четыре черновика в `Publications/`, раздел `knowledge/publications/` в Obsidian создан.
- **v2.0 milestone shipped** — 6 phases, all 18 requirements validated.
- **v1.1 milestone shipped** — 7 phases, Project Knowledge Graph complete.
