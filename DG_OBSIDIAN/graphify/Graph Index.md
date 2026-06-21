---
tags: [moc, graphify, knowledge-graph]
date: 2026-06-22
graphify_snapshot: graphify-2026-06-22
source_commit: 0651774
---

# Graphify Knowledge Graph — Индекс

> Автоматически сгенерирован из кодовой базы (commit `0651774`).
> 1836 nodes · 2335 edges · 198 communities · Обновлён 2026-06-22.
>
> **Как использовать:** Это карта кодовой базы в виде графа. Каждое сообщество (community) — группа связанных файлов и концептов. Используй `/graphify query` чтобы навигировать.

## Статистика графа

| Метрика | Значение |
|---------|---------|
| Всего nodes | 1,836 |
| Всего edges | 2,335 |
| Сообществ | 198 |
| Типы файлов | code: 1,291 · concept: 251 · rationale: 134 · document: 114 · image: 42 · paper: 4 |
| Топология | 100% EXTRACTED (AST-based для code, LLM-based для docs) |

---

## Ключевые сообщества

> Таблица ниже генерируется автоматически — `"$(cat graphify-out/.graphify_python)" scripts/export_graphify_conceptual.py`. Не редактировать вручную между маркерами.

<!-- graphify:index:start -->
> 1836 nodes · 2335 edges · 198 communities (104 shown, 94 thin omitted)

| Community | Nodes |
|-----------|-------|
| [[communities/Phase 3 n8n Knowledge Workflows + LLM IngestQuery\|Phase 3: n8n Knowledge Workflows + LLM Ingest/Query]] | 48 |
| [[communities/Phase 03 Validation Runs Summary\|Phase 03 Validation Runs Summary]] | 46 |
| [[communities/ValidationRunsComponent\|ValidationRunsComponent]] | 42 |
| [[communities/Fetch Graph Context (MCP)\|Fetch Graph Context (MCP)]] | 41 |
| [[communities/Prepare Graph Payload\|Prepare Graph Payload]] | 41 |
| [[communities/extractErrorMessage()\|extractErrorMessage()]] | 39 |
| [[communities/Zone A Maximum Height (75m)\|Zone A Maximum Height (75m)]] | 39 |
| [[communities/RuleDeconstructComponent\|RuleDeconstructComponent]] | 37 |
| [[communities/code rule\|code: rule]] | 36 |
| [[communities/ReinstateComponent.cs\|ReinstateComponent.cs]] | 35 |
| [[communities/State Projection for Validation Runs\|State Projection for Validation Runs]] | 33 |
| [[communities/code 32 nodes\|code: 32 nodes]] | 32 |
| [[communities/Create full-text index and parent class hub nodes for Kno...\|Create full-text index and parent class hub nodes for Kno...]] | 31 |
| [[communities/switcherРњРµРЅСЋ Р±С‹СЃС‚СЂРѕРіРѕ РїРµСЂРµС…РѕРґР°\|switcher:РњРµРЅСЋ Р±С‹СЃС‚СЂРѕРіРѕ РїРµСЂРµС…РѕРґР°]] | 30 |
| [[communities/ValidationGeometryPayload\|ValidationGeometryPayload]] | 29 |
| [[communities/Build Full-Text Cypher\|Build Full-Text Cypher]] | 29 |
| [[communities/knowledge-ingest.json\|knowledge-ingest.json]] | 27 |
| [[communities/DesignStateComponent.cs\|DesignStateComponent.cs]] | 24 |
| [[communities/MetagraphComponent.cs\|MetagraphComponent.cs]] | 24 |
| [[communities/n8n Workflow Orchestrator for LLM Rule Ingestion and Queries\|n8n Workflow Orchestrator for LLM Rule Ingestion and Queries]] | 24 |
| [[communities/Neo4jRuleRepository.cs\|Neo4jRuleRepository.cs]] | 23 |
| [[communities/Match Step (Neo4j Full-Text Search, No LLM)\|Match Step (Neo4j Full-Text Search, No LLM)]] | 23 |
| [[communities/Neo4jConnectorService.cs\|Neo4jConnectorService.cs]] | 22 |
| [[communities/collapse-color-groups\|collapse-color-groups]] | 21 |
| [[communities/SpeckleSettingsPayload\|SpeckleSettingsPayload]] | 21 |
| [[communities/knowledge-update.json\|knowledge-update.json]] | 21 |
| [[communities/ReinstatementServiceTests\|ReinstatementServiceTests]] | 20 |
| [[communities/Concern Tight Coupling to Neo4j\|Concern: Tight Coupling to Neo4j]] | 20 |
| [[communities/Validation Results Publish to Speckle as Overlay Versions\|Validation Results Publish to Speckle as Overlay Versions]] | 20 |
| [[communities/ConnectorComponent.cs\|ConnectorComponent.cs]] | 19 |
| [[communities/DG.Grasshopper.csproj\|DG.Grasshopper.csproj]] | 18 |
| [[communities/DesignStateJsonSerializer\|DesignStateJsonSerializer]] | 18 |
| [[communities/Per-Run Graphics State and Screenshot Persistence\|Per-Run Graphics State and Screenshot Persistence]] | 18 |
| [[communities/CLASSIFICATOR Component\|CLASSIFICATOR Component]] | 18 |
| [[communities/.TryResolveVariableValue()\|.TryResolveVariableValue()]] | 17 |
| [[communities/DesignStateValidationFlowTests\|DesignStateValidationFlowTests]] | 17 |
| [[communities/ValidationRunsQueryTests\|ValidationRunsQueryTests]] | 17 |
| [[communities/code 17 nodes\|code: 17 nodes]] | 17 |
| [[communities/FailingBindingFormatter\|FailingBindingFormatter]] | 16 |
| [[communities/ValidationPublishClient\|ValidationPublishClient]] | 16 |
<!-- graphify:index:end -->

---

## Как искать

### Поиск по графу (через CGD)

```
/graphify query "How does ValidationPublishPackageBuilder connect to Speckle?"
/graphify path "Neo4jRuleRepository" "SpeckleValidationClient"
/graphify explain "DCM ComputationGraph"
```

### Поиск по Obsidian

- `Ctrl+O` → название сообщества или модуля
- [[Graph Index]] — этот индекс
- `tag:#graphify/code` — все code nodes
- `tag:#graphify/EXTRACTED` — structural findings

### Запросы через MCP (когда настроен)

```
query_graph("What touches the validation pipeline?")
god_nodes()
graph_stats()
shortest_path("AuthModule", "Database")
```

---

## God Nodes (топ-10 hubs)

> Запусти `/graphify query "show me god nodes"` для актуального списка.

---

## Обновление графа

```bash
# 1. Инкрементальное (после изменений кода)
/graphify --update

# 2. Перегенерировать conceptual notes + этот индекс из обновлённого графа
"$(cat graphify-out/.graphify_python)" scripts/export_graphify_conceptual.py
```

Полный ребилд (`/graphify .`) нужен только после крупных структурных изменений.

---

*Сгенерировано: 2026-06-22 · Conceptual export: Фаза 2 (104 community notes, MIN_COMMUNITY_SIZE=5) · Следующее обновление: после значительных изменений кода*
