---
tags: [debugging]
date: 2026-07-04
phase: 15
severity: medium
status: resolved
resolved_in: commit 9b1bea6
---

# Stale knowledge_note_search index name in spec-query.json

## Симптом

Verification агент Phase 15 обнаружил: `n8n/workflows/spec-query.json` line 74 в inline Cypher (Build Full-Text Cypher функция) всё ещё использует `'knowledge_note_search'` вместо `'spec_note_search'`.

## Почему возникло

15-03 Task 2 (rename knowledge-query.json → spec-query.json) сфокусировался на:
- git mv файла
- rename workflow name
- rename node display names + connections
- inline Cypher labels (KnowledgeNote → SpecNote и т.д.)
- graph literal (KnowledgeGraph → SpecGraph)

Но индекс fulltext search (`knowledge_note_search`) был пропущен, потому что он не является ни label, ни graph literal — это имя индекса. Plan.md не содержал явного требования проверить индекс, а RESEARCH.md не перечислял `knowledge_note_search` как цель для замены.

## Последствия

После применения 15-01 migration (DROP knowledge_note_search, CREATE spec_note_search) n8n query workflow вызывал бы `CALL db.index.fulltext.queryNodes('knowledge_note_search', ...)` что привело бы к runtime ошибке "index not found".

## Фикс

`9b1bea6`: замена `'knowledge_note_search'` → `'spec_note_search'` в spec-query.json line 74 functionCode.

## Предупреждение

Inline Cypher strings внутри JSON functionCode полей не покрываются простым find/replace по файлу. Планы rename-фаз должны явно перечислять все inline Cypher строки для проверки, включая имена индексов, не только node labels и graph literals.

**Why:** The fulltext index name is embedded inside a JavaScript functionCode string inside a JSON file — invisible to label-based search patterns. The plan's search pattern ("Knowledge* graph-layer tokens") covered labels and graph values but not the index name `knowledge_note_search`, which starts with lowercase and doesn't match the Knowledge* pattern.
**How to apply:** In any future rename phase, add `grep -rin "knowledge_note_search\|spec_note_search\|old_index_name\|new_index_name"` to the acceptance gate to catch inline index references inside function/parameter strings.
