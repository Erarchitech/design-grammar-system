---
tags: [session]
date: 2026-07-04
---

# Session: 2026-07-04 — Phase 17 discuss — Graph Access Components

## Goal

Обсудить и зафиксировать решения для Phase 17 (Graph Access Components) — 5 компонентов Grasshopper для чтения 4 слоёв Neo4j: CONNECTOR, GRAPH DECONSTRUCT, METAGRAPH (добавление Objects), ONTOGRAPH (новый), VALIDATION GRAPH (замена VALIDATION RUNS).

## What Was Done

- Загружен prior context (PROJECT.md, REQUIREMENTS.md, STATE.md, ROADMAP.md, CONTEXT.md фаз 13–16)
- Исследован код существующих компонентов: ConnectorComponent, MetagraphComponent, ValidationRunsComponent, Neo4jConnectorService, Neo4jRuleRepository, ValidationRunsQueryService, ConnectionInfo, PublicTypes
- Прочитан port-iri-map-V7.md для всех 5 компонентов
- Выявлены 4 серые зоны для обсуждения
- Все 4 зоны обсуждены и зафиксированы решения

## Decisions Made

- **D-01 (Layer Handle Model):** Individual types per layer — `MetagraphHandle`, `OntographHandle`, `ValidGraphHandle`, `SpecGraphHandle` — каждый оборачивает `ConnectionInfo`. Type-safe Grasshopper провода.
- **D-02 (METAGRAPH Objects):** Query REFERS_TO→Class напрямую из Neo4j (новый Cypher запрос), а не через VariableTypeInferrer. Дедупликация по IRI.
- **D-03/04 (VALIDATION GRAPH):** Run↔Status index-matched (1:1). DesignState — отдельный deduplicated список (короче Run, join по StateId).
- **D-05 (Status Type):** `IReadOnlyList<bool>` per run — один bool на ObjState. Overall pass = AND(bool).
- **D-06 (Repository Design):** Per-layer repository + interface — `IOntoGraphRepository`, `IValidGraphRepository`, extend `IRuleRepository` с `GetObjectsAsync`.

## Issues Encountered

- None — discussion stayed within phase scope.

## Next Steps

`/gsd-plan-phase 17` — спланировать реализацию 5 компонентов + 3 новых репозитория.

## Related Notes

- [[decisions/Phase 17 Graph Access Components layer handles and repository design|Phase 17: Graph Access Components decisions]]
- [[sessions/2026-07-04 Phase 16 discuss - DG.Core state models and state components|Phase 16 discuss session]]
- [[sessions/2026-07-04 Phase 16 planning - 6 plans across 3 waves|Phase 16 planning session]]
