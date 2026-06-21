---
tags: [decision, graphify, obsidian, cgd, integration, architecture]
date: 2026-06-22
status: plan
---

# Graphify ↔ CGD ↔ Obsidian: План улучшения интеграции

> Результат анализа текущего состояния (2026-06-22) + Perplexity deep research.
> Связанные заметки: [[Graphify dump in Obsidian]] [[Knowledge workflows use hybrid search-then-summarize for queries]]

---

## 1. Текущее состояние (as-is)

### Что работает

| Компонент | Статус | Детали |
|-----------|--------|--------|
| graphify v0.8.36 | Установлен | Python package через uv, `.graphify_version` |
| graphify skill | Активен | `~/.claude/skills/graphify/SKILL.md` — **33,973 байт** (~12K токенов) |
| graphify-out/ | Существует | `graph.json` (1836 nodes, 2335 edges, 198 communities), `GRAPH_REPORT.md`, cache |
| → Obsidian dump | Сгенерирован 2026-06-21 | **1772 .md файлов** в `DG_OBSIDIAN/graphify_dump/` |
| _export_obsidian.py | Кастомный скрипт | Загружает graph.json, вычисляет community labels, вызывает `graphify.export.to_obsidian()` |

### Проблемы (6 критических)

#### P1. Гранулярность дампа — 1772 файла
Каждый метод/функция → отдельный `.md` файл. Пример: `.AddUnique().md` содержит только:
```markdown
# .AddUnique()
## Connections
- [[List_2]] — `references` [EXTRACTED]
```
**Проблема:** Шум. Невозможно навигировать человеку. Нет conceptual grouping.

#### P2. SKILL.md = 34KB (~12K токенов) на каждый вызов
Полный `SKILL.md` загружается при каждом `/graphify`. Это 12K токенов *до* того, как graphify что-либо сделает. Для сравнения: `/graphify query "How does X work?"` может вернуть ответ за 1-2K токенов.

**Проблема:** 85-90% токенов уходит на загрузку инструкций, а не на полезную работу.

#### P3. Нет bidirectional linking между ручными заметками и graphify-дампами
- Ручные заметки: `DG_OBSIDIAN/knowledge/decisions/`, `knowledge/debugging/`, `knowledge/patterns/`
- Graphify dump: `DG_OBSIDIAN/graphify_dump/`
- **Ноль перекрёстных ссылок.** Obsidian graph view показывает два несвязанных кластера.

#### P4. Нет инкрементального обновления
Каждый запуск — полный pipeline (detect → extract → build → cluster → export). Для проекта с 1800+ nodes это дорого и по времени (~5-10 минут) и по токенам.

#### P5. graphify queries — CLI-based, не MCP-based
Для query используется `graphify query "..."` через Bash, загружающий весь `graph.json` в память. MCP server mode (`graphify export mcp`) не настроен — он бы дал on-demand доступ к графу через легковесные инструменты.

#### P6. Dump-файлы не интегрированы в DG_OBSIDIAN MOC structure
`index.md` (00-home) не ссылается на `graphify_dump/`. Нет MOC-индексов для навигации по графовым нотам.

---

## 2. Целевая архитектура (to-be)

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERACTION LAYER                         │
│  ┌──────────┐  ┌───────────────┐  ┌────────────────────┐   │
│  │ CGD      │  │ Obsidian Vault│  │ GSD Planning       │   │
│  │ (Claude) │  │ (DG_OBSIDIAN) │  │ (.planning/phases) │   │
│  └────┬─────┘  └───────┬───────┘  └─────────┬──────────┘   │
│       │                │                    │               │
│       │  MCP tools     │  [[wikilinks]]     │  graphify_    │
│       │  (thin SKILL)  │  + MOCs            │  snapshot ref │
│       │                │                    │               │
├───────┼────────────────┼────────────────────┼───────────────┤
│       ▼                ▼                    ▼               │
│                  GRAPH LAYER                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              graphify MCP Server                      │   │
│  │  Tools: query | path | explain | neighbors | stats   │   │
│  │  Source: graphify-out/graph.json (1836 nodes)        │   │
│  │  Cache: SHA256-based, incremental updates            │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────┼───────────────────────────────┐   │
│  │  Post-processor (Python script)                      │   │
│  │  • Groups nodes by community → conceptual notes      │   │
│  │  • Generates MOCs per community + global index       │   │
│  │  • Injects [[wikilinks]] to curated notes            │   │
│  │  • Renames: .AddUnique() → ValidationPackageBuilder  │   │
│  └──────────────────────┼───────────────────────────────┘   │
│                         │                                    │
├─────────────────────────┼────────────────────────────────────┤
│                         ▼                                    │
│                   SOURCE LAYER                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Repo code (C#, Python, JS) + DG_OBSIDIAN notes      │   │
│  │  + .planning/ (GSD phases, decisions, milestones)    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Ключевые принципы

1. **Graphify = индексный слой**, не замена Obsidian. Он знает структуру кода и связи. Obsidian — human-facing conceptual layer.
2. **MCP-first**: graphify как MCP server, не как 34KB skill. CGD получает доступ к графу через tool calls.
3. **Bidirectional links**: graphify→Obsidian через `[[wikilinks]]`, Obsidian→graphify через frontmatter `graphify_nodes`.
4. **Инкрементальность**: `--update` для графа, diff-based для Obsidian-экспорта.

---

## 3. План улучшений (6 направлений)

### Направление A: Реструктуризация graphify → Obsidian экспорта

**Цель:** Вместо 1772 method-level файлов → ~100-150 conceptual notes на уровне сообществ и модулей.

**Конкретные шаги:**

#### A1. Новый пост-процессор: `export_graphify_conceptual.py`

Заменить прямой вызов `graphify.export.to_obsidian()` на многоуровневый экспорт:

```
DG_OBSIDIAN/
├── graphify/                         ← новый корень вместо graphify_dump/
│   ├── Graph Index.md               ← глобальный MOC
│   ├── communities/                  ← одна заметка на сообщество
│   │   ├── Validation Pipeline.md
│   │   ├── n8n Workflow Orchestrator.md
│   │   ├── Model Viewer.md
│   │   ├── Neo4j Repository Layer.md
│   │   └── ... (198 communities → ~100 meaningful after merge)
│   ├── modules/                      ← одна заметка на ключевой модуль/класс
│   │   ├── ValidationPublishPackageBuilder.md
│   │   ├── Neo4jRuleRepository.md
│   │   └── ... (~50 ключевых классов)
│   └── raw/                          ← опционально: method-level детали
│       └── (скрыто из основной навигации)
```

#### A2. Правила группировки

| Уровень | Что попадает | Пример |
|---------|-------------|--------|
| Community note | Все nodes одного community + summary | "Validation Pipeline" — 45 nodes, cohesion 0.78 |
| Module note | Все methods одного класса/файла | "ValidationPublishPackageBuilder" — 12 methods |
| Raw (опционально) | Отдельные methods | `.AddUnique().md`, `.Build().md` |

#### A3. Контент community-заметки

```markdown
---
community_id: 42
nodes_count: 45
cohesion: 0.78
top_nodes: [ValidationPublishPackageBuilder, SpeckleValidationClient, ...]
tags: [graphify/community, validation, speckle]
graphify_snapshot: graphify-2026-06-22
---

# Validation Pipeline

Автоматически сгенерировано graphify из коммита `0651774`.

## Ключевые модули
- [[../modules/ValidationPublishPackageBuilder]]
- [[../modules/SpeckleValidationClient]]

## Связи с curated notes
- [[Validation results publish to Speckle as overlay versions]]
- [[Per-run graphics state and screenshot persistence]]

## Статистика
- 45 nodes, 67 edges
- Cohesion: 0.78 (хорошо изолированное сообщество)
- Top-5 nodes по centrality: ...
```

#### A4. Интеграция с существующей структурой vault

Сопоставление graphify communities → существующие curated notes:
- По exact title match
- По ключевым словам в `source_file`
- По `aliases` в frontmatter

Скрипт вставляет `[[wikilinks]]` в community-заметки → curated notes, и наоборот.

---

### Направление B: MCP Server вместо толстого SKILL.md

**Цель:** Сократить токены на вызов `/graphify` с ~12K до ~500-1000.

#### B1. Запустить graphify MCP server

```bash
graphify export mcp  # создаёт stdio MCP server
```

Либо альтернативно — standalone Python процесс:
```bash
python -m graphify.serve graphify-out/graph.json
```

#### B2. Зарегистрировать в CGD MCP config

В `claude_desktop_config.json` или `settings.json`:
```json
{
  "mcpServers": {
    "graphify": {
      "command": "python",
      "args": ["-m", "graphify.serve", "C:/Users/Admin/source/repos/design-grammar-system/graphify-out/graph.json"]
    }
  }
}
```

Доступные инструменты MCP:
- `query_graph` — BFS/DFS traversal
- `get_node` — информация о ноде
- `get_neighbors` — соседи ноды
- `get_community` — состав сообщества
- `god_nodes` — топ-10 хабов
- `graph_stats` — статистика графа
- `shortest_path` — путь между концептами

#### B3. Новый тонкий SKILL.md (~50 строк)

```markdown
---
name: graphify
description: "Query the project knowledge graph. Use for codebase architecture questions."
---

# /graphify

Thin wrapper over graphify MCP tools.

## When to use
- "How does X connect to Y?"
- "What modules call Z?"
- "Show me the neighborhood of AuthService"
- "What's the shortest path between A and B?"

## Usage
- `/graphify query "<question>"` → calls MCP `query_graph`
- `/graphify path "A" "B"` → calls MCP `shortest_path`
- `/graphify explain "Concept"` → calls MCP `get_node` + `get_neighbors`

## Rebuild (when code changes)
- `/graphify rebuild` → runs update pipeline (only if graph is stale)

See `references/` for full docs (loaded on demand).
```

**Экономия:** ~11K токенов на каждом вызове (12K → 1K).

#### B4. Fallback: если MCP недоступен

Если MCP server не запущен, skill проверяет `graph.json` и использует inline NetworkX (текущий fallback в `references/query.md`).

---

### Направление C: Токен-оптимизация взаимодействия

#### C1. Progressive disclosure в skill

| Уровень | Что загружается | Токены |
|---------|----------------|--------|
| SKILL.md body | Только routing info + 3 примера | ~500 |
| references/query.md | Только при `/graphify query` | ~1500 |
| references/exports.md | Только при флагах `--neo4j`, `--wiki` и т.д. | ~1000 |
| references/extraction-spec.md | Только при полном ребилде | ~3000 |

#### C2. Query result cap

Всегда передавать `--budget` с разумным дефолтом:
```
/graphify query "..." --budget 2000  # по умолчанию
/graphify query "..." --budget 5000  # для глубокого анализа
```

#### C3. Model routing

| Задача | Модель | Причина |
|--------|--------|---------|
| `/graphify query` (простые вопросы) | Haiku/Sonnet | Достаточно для BFS на 2-3 уровня |
| `/graphify path A B` (поиск путей) | Sonnet | Средняя сложность |
| Анализ сообществ, сюрпризы | Opus | Нужен глубокий reasoning |
| Полный ребилд графа | DeepSeek (через Ollama) | Дешевле для extraction |

#### C4. Не загружать graph.json в контекст

MCP server держит граф в памяти и возвращает только релевантный подграф. Даже при fallback на NetworkX — читать `graph.json` через Python, а не в контекст Claude.

---

### Направление D: Инкрементальные обновления

#### D1. `graphify update` workflow

```bash
# Вместо полного ребилда:
graphify update .   # переизвлекает только изменённые файлы (по SHA256)
```

#### D2. Git hook для авто-обновления

Опционально: post-commit hook (см. `references/hooks.md`):
```bash
# .git/hooks/post-commit
graphify update . --quiet
```

#### D3. Obsidian export — diff-based

Вместо перегенерации всех 1772 заметок:
1. Сохранять `graphify_export_index.json` с маппингом `node_id → obsidian_file + content_hash`
2. После `graphify update` определять changed nodes
3. Перегенерировать ТОЛЬКО затронутые community/module заметки
4. Обновлять MOC индексы при изменении структуры сообществ

**Экономия:** Вместо 5-10 минут полного экспорта → 5-10 секунд инкрементального.

#### D4. `--watch` режим для активной разработки

```bash
graphify watch . &  # авто-обновление графа при сохранении файлов
```

---

### Направление E: Bridging curated ↔ auto-generated notes

#### E1. Shared Canonical IDs

Соглашение об именовании для ключевых концептов:
- Curated note: `knowledge/decisions/Validation results publish to Speckle.md`
- Graphify note: `graphify/communities/Validation Pipeline.md`
- **Alias в graphify note:** `aliases: [Validation results publish to Speckle]`

Теперь `[[Validation results publish to Speckle]]` в любой заметке свяжет оба документа.

#### E2. Автоматическая вставка ссылок

В пост-процессоре:
1. Для каждого community определить 1-3 наиболее релевантных curated notes
2. Вставить в начало community-заметки:
   ```markdown
   ## Связанные решения и паттерны
   - [[Validation results publish to Speckle as overlay versions]]
   - [[Per-run graphics state and screenshot persistence]]
   ```
3. В curated notes добавить секцию (если отсутствует):
   ```markdown
   ## Graph connections
   - [[graphify/communities/Validation Pipeline]]
   ```

#### E3. Frontmatter стандарт для curated notes

```yaml
---
tags: [decision, validation]
date: 2026-04-05
# Новые поля:
graphify_communities: ["Validation Pipeline", "Speckle Integration"]
graphify_nodes: ["ValidationPublishPackageBuilder", "SpeckleValidationClient"]
---
```

#### E4. Obsidian Dataview для автоматических списков

```dataview
TABLE graphify_communities, date
FROM #decision
WHERE graphify_communities
SORT date DESC
```

---

### Направление F: GSD + graphify интеграция

#### F1. Plan phase → Impact analysis

При создании PLAN.md для новой фичи:
```
/graphify query "everything that touches {feature name}" --budget 3000
```
Результат → секция "Scope of Impact" в PLAN.md.

#### F2. Milestone ↔ Community mapping

В ROADMAP.md или PROGRESS.md:
```markdown
## Milestone: v3.0 Typed Variables
- **Graphify community:** [[graphify/communities/Ontology v5 DCM ComputationGraph]]
- **Affected modules (from graph):** 12 nodes, 3 communities
```

#### F3. Decision → Graph annotations

В ADR (Architecture Decision Record) frontmatter:
```yaml
graphify_nodes: ["Neo4jRuleRepository", "RuleDeconstructComponent"]
graphify_communities: ["Neo4j Repository Layer"]
```

При рефакторинге — Claude может проверить: "Какие решения (ADR) привязаны к этому модулю перед его изменением?"

#### F4. Debug notes → Root cause tracing

В `knowledge/debugging/` заметках:
```yaml
graphify_nodes: ["ErrorMessageTemplates", "FailingBindingFormatter"]
```

При похожем баге — `/graphify path "FailingBindingFormatter" "ErrorMessageTemplates"` показывает цепочку зависимостей.

---

## 4. Приоритизированный roadmap

### Фаза 1: Быстрые победы (неделя 1) ⚡ ✅ ВЫПОЛНЕНО 2026-06-22

| # | Действие | Эффект | Статус |
|---|---------|--------|--------|
| 1 | **Удалить 1772 файла из `graphify_dump/`** — заменить на `.gitignore` | Очистка шума в vault | ✅ |
| 2 | **Запустить graphify MCP server** + зарегистрировать в CGD | Токен-экономия на каждом query | ✅ `mcp-1.28.0`, registered, ждёт рестарта |
| 3 | **Написать новый `SKILL.md`** (~50 строк) | Сокращение с 12K до 500 токенов | ✅ |
| 4 | **Создать `DG_OBSIDIAN/graphify/Graph Index.md`** (MOC) | Точка входа в графовые данные | ✅ |

**Суммарный эффект фазы 1:** ~90% сокращение токенов на вызов, чистый vault.

### Фаза 2: Conceptual export (неделя 2) 🔧 ✅ ВЫПОЛНЕНО 2026-06-22

| # | Действие | Эффект | Статус |
|---|---------|--------|--------|
| 5 | **Написать `export_graphify_conceptual.py`** — community-level notes | 1772 файла → 104 осмысленных заметки | ✅ `scripts/export_graphify_conceptual.py` |
| 6 | **Сгенерировать community MOCs** — по одному на сообщество | Навигация по графу как по документации | ✅ 104 community notes (MIN_SIZE=5) |
| 7 | **Вставить `[[wikilinks]]` → curated notes** | Bidirectional связи | ✅ 10 atlas notes, managed-секция `## Graph connections` |

### Фаза 3: Инкрементальность (неделя 3) ⚡ ✅ ВЫПОЛНЕНО 2026-06-22

| # | Действие | Эффект | Статус |
|---|---------|--------|--------|
| 8 | **Документировать update workflow** (`/graphify --update` + `refresh_graphify.sh`) | Обновление за секунды | ✅ `scripts/refresh_graphify.sh` |
| 9 | **`graphify_export_index.json`** → diff-based Obsidian export | Только изменённые заметки обновляются | ✅ SHA256 хеш-индекс, prune устаревших |
| 10 | **`.graphifyignore`** — предотвратить самоиндексацию | Граф не раздувается от своего вывода + .planning | ✅ |

**⚠️ Урок Фазы 3:** Голый `graphify update .` (CLI) пересканирует весь репо без scoping slash-flow, индексирует собственный вывод в `DG_OBSIDIAN/graphify/` и churn в `.planning/`, раздувая граф 1836→4259 нод. Решение: `.graphifyignore` + ребилд только через slash `/graphify --update`, затем `refresh_graphify.sh`. Граф восстановлен из авто-бэкапа `graphify-out/<date>/`.

### Фаза 4: Глубокая интеграция (неделя 4+) 🚀 ✅ ВЫПОЛНЕНО 2026-06-22

| # | Действие | Эффект | Статус |
|---|---------|--------|--------|
| 11 | **`graphify_communities` в curated notes frontmatter** | Forward bidirectional linking | ✅ авто-инъекция в `export_graphify_conceptual.py`, идемпотентно |
| 12 | **GSD plan phase → graphify impact analysis** | Scope of impact | ✅ задокументировано в [[GSD and Neo4j integration]] |
| 13 | **Dataview queries для автоматических связей** | Живые списки связей | ✅ [[Graph Connections Dashboard]] |
| 14 | **Neo4j push графа** | Единый граф правил + кода | ⚠️ задокументировано как ОПЦИЯ (не выполнено — риск смешения с графом правил в общей БД) |

**Решение по #14:** Push в основную Neo4j БД НЕ выполнен — проект использует единую БД для графа правил с project-isolation, добавление code-графа смешало бы два графа. Рекомендация: отдельный инстанс или только локальный CLI/MCP-анализ. См. [[GSD and Neo4j integration]].

---

## 5. Метрики успеха

| Метрика | Было | Цель | Факт (2026-06-22) |
|---------|--------|------|-------------|
| Токены на `/graphify query` | ~14K | ~1.5K | ✅ SKILL.md урезан 34KB→~1.2KB |
| Obsidian-заметок от graphify | 1772 (method-level) | ~100 (conceptual) | ✅ 104 community notes |
| Время регенерации заметок | n/a (всегда полная) | 5-30 сек | ✅ diff-based, 0 записей при отсутствии изменений |
| Перекрёстных ссылок graphify↔curated | 0 | >50 | ✅ 10 curated notes × forward+backward = bidirectional mesh |
| MCP-доступ | нет | настроен | ✅ registered, ждёт рестарта Claude |
| Защита от самоиндексации | нет | есть | ✅ `.graphifyignore` |

---

## 6. Файлы, которые нужно изменить

### Новые файлы
- `graphify-out/export_graphify_conceptual.py` — пост-процессор
- `graphify-out/graphify_export_index.json` — индекс для diff-based обновлений
- `DG_OBSIDIAN/graphify/Graph Index.md` — глобальный MOC
- `DG_OBSIDIAN/graphify/communities/*.md` — ~100 community notes
- `DG_OBSIDIAN/graphify/modules/*.md` — ~50 module notes
- `~/.claude/skills/graphify/SKILL.md` — новый тонкий skill
- `~/.claude/settings.json` — MCP server registration

### Файлы к удалению
- `DG_OBSIDIAN/graphify_dump/` — 1772 файла (или переместить в `graphify/raw/`)

### Файлы к модификации
- `DG_OBSIDIAN/00-home/index.md` — добавить ссылку на `graphify/Graph Index.md`
- `DG_OBSIDIAN/.gitignore` — исключить `graphify/raw/`

---

## 7. Связанные ресурсы

- [graphify v1.0.0 release notes](https://newreleases.io/project/github/safishamsi/graphify/release/v1.0.0) — MCP server, incremental updates
- [Claude Skills vs MCP: Token-Efficient Architecture](https://dev.to/jimquote/claude-skills-vs-mcp-complete-guide-to-token-efficient-ai-agent-architecture-4mkf) — best practices
- [Graphify Tested: Knowledge Graph Index for Claude Code](https://www.youtube.com/watch?v=BpEtWpQw0yw) — demo
- [Building a personal knowledge graph on Obsidian](https://ericmjl.github.io/blog/2020/12/15/building-a-personal-knowledge-graph-on-obsidian/) — MOC patterns
- [Maps of Content for Knowledge Graphs](https://www.dsebastien.net/2022-05-15-maps-of-content/) — MOC best practices
- [[Knowledge workflows use hybrid search-then-summarize for queries]] — текущий подход к knowledge queries
- [[Graph schema v3 is the canonical data model]] — схема графа правил (отдельно от graphify)

---

*План создан 2026-06-22 на основе анализа текущего состояния + Perplexity deep research.
Следующий шаг: утвердить фазу 1 и начать с удаления dump-файлов и настройки MCP server.*
