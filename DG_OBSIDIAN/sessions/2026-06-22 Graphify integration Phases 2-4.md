---
tags: [session, graphify, obsidian, cgd, integration]
date: 2026-06-22
---

# 2026-06-22 — Graphify интеграция: Фазы 2–4

> Продолжение [[2026-06-22 Graphify-CGD-Obsidian integration Phase 1|Фазы 1]]. Выполнены Фазы 2, 3, 4 из [[Graphify-CGD-Obsidian integration improvement plan|плана]].

## Фаза 2 — Conceptual export

- **`scripts/export_graphify_conceptual.py`** — пост-процессор: graph.json → community-level Obsidian notes вместо 1772 method-level файлов.
- **104 community notes** в `DG_OBSIDIAN/graphify/communities/` (порог MIN_COMMUNITY_SIZE=5; из 198 сообществ).
- Каждая нота: frontmatter (community_id, nodes_count, tags), топ-12 узлов с source_file, авто-matching на curated notes.
- **Дизамбигуация коллизий**: 4 пары сообществ с одинаковым label различены `(cid)`-суффиксом.
- **Bidirectional linking**: 10 atlas-notes получили managed-секцию `## Graph connections` (маркеры `<!-- graphify:connections:start/end -->`).
- Ужесточил matching: только заголовки curated notes, overlap ≥2 слова (иначе flood 70+ ложных ссылок).
- **`Graph Index.md`** — автогенерируемая таблица топ-40 сообществ между маркерами `<!-- graphify:index:start/end -->`.

## Фаза 3 — Инкрементальность

- **Diff-based экспорт**: `graphify-out/graphify_export_index.json` (SHA256 на сообщество) — перезапуск переписывает только изменённые заметки + prune исчезнувших. Проверено: 2-й прогон = 0 записей, 104 unchanged.
- **`scripts/refresh_graphify.sh`** — однокомандный регенератор из текущего graph.json.
- **`.graphifyignore`** — исключает `DG_OBSIDIAN/graphify/`, `graphify-out/`, `.planning/`.

### ⚠️ Главный урок: feedback loop от `graphify update .`

Голый CLI `graphify update .` пересканировал весь репо БЕЗ scoping slash-flow, проиндексировал собственный вывод (`DG_OBSIDIAN/graphify/` 1380 нод) и `.planning/` churn (1549 нод) → граф раздулся **1836 → 4259 нод**, документов 114 → 2885.

**Исправление:**
1. Восстановил исходный граф из авто-бэкапа `graphify-out/2026-06-22/` (graphify сам бэкапит перед update).
2. Создал `.graphifyignore`.
3. `refresh_graphify.sh` НЕ делает `graphify update .` — только regen заметок. Ребилд графа = slash `/graphify --update` (со scoping + semantic extraction), затем regen.

## Фаза 4 — Глубокая интеграция

- **Forward mapping**: `graphify_communities` в frontmatter curated notes (line-based YAML инъекция в `export_graphify_conceptual.py`, идемпотентно — проверено: ровно 1 ключ после 2 прогонов). Теперь bidirectional mesh: curated→graph (frontmatter + `## Graph connections`) и graph→curated (`## Связанные curated notes`).
- **`Graph Connections Dashboard.md`** — Dataview-дашборд: curated notes по сообществам, сообщества по размеру, сообщества без curated-связи.
- **`GSD and Neo4j integration.md`** — паттерны: plan-phase impact analysis (`/graphify query "everything that touches X"` → Scope of Impact), milestone↔community mapping, decision/debug annotations.
- **Neo4j push НЕ выполнен** — проект использует единую Neo4j БД для графа правил (Class/Rule/Atom) с project-isolation; добавление code-графа смешало бы два графа. Задокументировано как опция (отдельный инстанс или только локальный CLI/MCP).

## Изменённые/созданные файлы

| Файл | Назначение |
|------|-----------|
| `scripts/export_graphify_conceptual.py` | Пост-процессор (community notes + backlinks + frontmatter + index) |
| `scripts/refresh_graphify.sh` | Однокомандный regen |
| `scripts/setup_graphify_mcp.bat` | (Фаза 1) MCP setup |
| `.graphifyignore` | Защита от самоиндексации |
| `DG_OBSIDIAN/graphify/Graph Index.md` | MOC с автотаблицей |
| `DG_OBSIDIAN/graphify/communities/*.md` | 104 community notes |
| `DG_OBSIDIAN/graphify/Graph Connections Dashboard.md` | Dataview dashboard |
| `DG_OBSIDIAN/graphify/GSD and Neo4j integration.md` | Паттерны интеграции |
| 10 atlas notes | `## Graph connections` + `graphify_communities` frontmatter |

## Грабли (зафиксировано)

- **`graphify update .` (CLI) ≠ `/graphify --update` (slash).** CLI не делает scoping → feedback loop + раздувание. Всегда slash для ребилда.
- **graphify авто-бэкапит граф** перед update в `graphify-out/<date>/` — спасло от потери исходного графа.
- **`ls | wc -l` врёт** на именах со спецсимволами — считать через Python pathlib.
- **НИКОГДА `graphify install`** — перезапишет тонкий SKILL.md.
- **PYTHONIOENCODING=utf-8** обязателен для graphify Python на cp1251-консоли Windows.

## Итоговый workflow

```
/graphify --update                 # ребилд графа (Claude-driven, scoping + semantic)
bash scripts/refresh_graphify.sh   # diff-based regen 104 заметок + frontmatter + index
```

## Связанные заметки

- [[Graphify-CGD-Obsidian integration improvement plan]]
- [[2026-06-22 Graphify-CGD-Obsidian integration Phase 1]]
- [[graphify/Graph Index|Graph Index]]
- [[graphify/Graph Connections Dashboard|Graph Connections Dashboard]]
- [[graphify/GSD and Neo4j integration|GSD ↔ graphify и Neo4j]]
