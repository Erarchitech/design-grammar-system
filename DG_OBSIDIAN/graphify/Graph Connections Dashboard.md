---
tags: [dashboard, graphify, dataview]
date: 2026-06-22
---

# Graph Connections Dashboard

> Живые списки связей между curated notes и graphify-сообществами.
> Требует плагин **Dataview** в Obsidian. Если запросы не рендерятся — установи Dataview (Settings → Community plugins).

## Curated notes, связанные с графом

Заметки, у которых проставлен `graphify_communities` (forward mapping, авто из `export_graphify_conceptual.py`):

```dataview
TABLE graphify_communities AS "Сообщества графа", date AS "Дата"
FROM "DG_OBSIDIAN/atlas" OR "DG_OBSIDIAN/knowledge"
WHERE graphify_communities
SORT length(graphify_communities) DESC
```

## Сообщества графа по размеру

Все авто-сгенерированные community notes, отсортированные по числу узлов:

```dataview
TABLE nodes_count AS "Узлов", community_id AS "ID"
FROM "DG_OBSIDIAN/graphify/communities"
SORT nodes_count DESC
LIMIT 30
```

## Сообщества без связи с curated notes

Community notes, для которых не нашлось curated-аналога (кандидаты на ручное связывание или новые области знания):

```dataview
LIST
FROM "DG_OBSIDIAN/graphify/communities"
WHERE !contains(file.outlinks, this.file.link)
SORT nodes_count DESC
LIMIT 20
```

## Как это работает

1. **Forward mapping** (curated → graph): `graphify_communities` в frontmatter curated note. Ставится автоматически скриптом по keyword-overlap (≥2 слова заголовка).
2. **Backward mapping** (graph → curated): секция `## Graph connections` в curated note + `## Связанные curated notes` в community note.
3. Обновляется: `bash scripts/refresh_graphify.sh` после ребилда графа.

## Смотрите также

- [[Graph Index]] — индекс всех сообществ
- [[Graphify-CGD-Obsidian integration improvement plan]] — план интеграции

---

*Создано: 2026-06-22 · Фаза 4 интеграции graphify*
