---
type: moc
tags: [dissemination, consistency, dev-mapping]
date: 2026-07-18
summary: "Обратный индекс: dev-артефакт → публикации, которые на него опираются. При изменении spec/онтологии grep по этой карте показывает, какие статьи затронуты."
---

# Dissemination ↔ Development consistency map

Прямая карта (публикация → dev-якоря) — во frontmatter `dev_anchor:` каждой заметки в `venues/` и T1–T4. Здесь — обратный индекс.

| Dev-артефакт | Версия/файл | Опирающиеся публикации |
|---|---|---|
| Граф-схема | v4 — [[Graph schema v4 is the canonical data model]], `spec/DATABASE.md` | T1, T2, T3, T4, ptBIM26, IJAC26 |
| SWRL-семантика нарушений | [[Violation rules invert the constraint in SWRL body]] | T1, T2, ptBIM26 |
| LPG↔OWL маппинг | `spec/LPG-OWL-MAPPING.md` | T1, ptBIM26 |
| n8n воркфлоу (17 узлов) | [[n8n runs two async webhook workflows for ingest and query]] | T2, T3, T4 |
| GH-компоненты (8 шт.) | `spec/GRASSHOPPER.md` | T2, T3, T4 |
| DesignStateSnapshot / ValidationRun | [[decisions/Phase 16 DesignState aggregate and statePayloadJson v2]] | T3, T4 |
| REINSTATE | [[decisions/Phase 19 Deconstruct and Reinstate Components decisions]] | T3 |
| DesignSpaceGraph / MetricSpec | T4 определяет | T4 |
| Онтология v5 DCM | [[DCM ComputationGraph as 5th ontology layer]] | IJAC26 |
| Reasoner / SHACL (v8.2) | [[decisions/Phase 823 SHACL validation layer design decisions]] | — ещё не покрыто публикациями (кандидат для T2/T3 ревизий или новой статьи) |

## Правила согласованности

1. При изменении схемы/онтологии: grep `dev_anchor:` по `dissemination/` → обновить статус затронутых venue-заметок (`status: needs-revision`).
2. Новые фичи (v8.2 reasoner, SHACL, DG ID v9.0) до включения в статьи фиксируются в строке «ещё не покрыто».
3. Детальная матрица «кто что определяет» между T1–T4 — [[Series coherence map]].
