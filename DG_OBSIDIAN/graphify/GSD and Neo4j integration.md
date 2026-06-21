---
tags: [graphify, gsd, neo4j, integration, reference]
date: 2026-06-22
---

# GSD ↔ graphify и Neo4j интеграция (Фаза 4)

> Паттерны использования графа кода в GSD-планировании и опциональный экспорт в Neo4j.

## GSD plan-phase: impact analysis

При планировании новой фичи/фазы используй граф для определения зоны влияния **до** написания PLAN.md:

```
/graphify query "everything that touches {feature name}" --budget 3000
```

Или через MCP (когда сервер активен):
```
query_graph("what modules connect to ValidationPublishPackage")
shortest_path("DesignStateComponent", "Neo4jRuleRepository")
```

Результат → вставь в PLAN.md как секцию **"Scope of Impact"**: список затронутых модулей + сообществ. Это снижает риск пропустить зависимости.

## Milestone ↔ Community mapping

В ROADMAP.md / PROGRESS.md связывай milestone с сообществом графа:

```markdown
## Milestone: v3.0 Typed Variables
- **Graphify community:** [[../communities/Ontology v5 DCM ComputationGraph]]
- **Affected modules (from graph):** N nodes, M communities
```

Отслеживай рост "surface area" сообщества (число узлов) между milestone — индикатор scope creep.

## Decision/Debug → Graph annotations

В ADR и debug-заметках проставляй `graphify_communities` в frontmatter (можно вручную, для curated notes вне auto-matching):

```yaml
graphify_communities: ["Neo4j Repository Layer", "Validation Pipeline"]
```

Перед рефакторингом модуля спроси Claude: *"какие решения (ADR) привязаны к этому сообществу?"* — он найдёт через [[Graph Connections Dashboard]] или frontmatter-поиск.

## Опционально: Neo4j push

⚠️ **Не делать на проде без понимания последствий.** Проект уже использует Neo4j для графа правил (Class/Rule/Atom/Var и т.д.) с project-isolation. Экспорт graphify-графа кода добавит туда узлы со СВОИМИ labels — это не сломает граф правил (разные labels), но смешает два графа в одной БД.

Безопасные варианты:
1. **Отдельная Neo4j БД/инстанс** для графа кода (рекомендуется).
2. **Только локальный анализ** через graphify CLI/MCP (текущий подход — достаточно).

Если всё же нужен push в отдельный инстанс:
```bash
graphify export neo4j --push bolt://localhost:7688 --user neo4j --password <PWD>
```
(MERGE-based, идемпотентно. Используй порт/инстанс, отличный от 7687 — основного DG Neo4j.)

## Связанные ресурсы

- [[Graph Index]] — индекс сообществ
- [[Graph Connections Dashboard]] — Dataview-дашборд связей
- [[Graphify-CGD-Obsidian integration improvement plan]] — общий план
- [[Neo4j stores ontology and metagraph in a single database]] — почему общая БД рискованна для push

---

*Создано: 2026-06-22 · Фаза 4 интеграции graphify*
