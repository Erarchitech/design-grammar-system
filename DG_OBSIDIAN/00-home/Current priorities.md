---
tags: [home, priorities]
date: 2026-05-10
---

# Current Priorities

## Active

1. **Model Viewer visual bugs** — rotation/mixed state in validation viewport (carried from v1.1).
2. **v3.0 implementation** — Typed Variables and Composable Design State (Phases 7–12, planned).
3. **T1 submission preparation** — форматирование по ITcon Author Guidelines, DOI-ссылки, рецензирование научным руководителем.

## Upcoming

- Рецензирование T2–T4 соавтором или научным руководителем
- Реализация DesignSpaceGraph (T4) как milestone после v3.0
- Суррогатные модели для метрик после накопления >200 DesignSpacePoints
- Improve LLM Cypher generation accuracy
- Harden authentication with server-side auth
- Performance optimization for large rule sets

## Completed Recently

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
