---
tags: [session]
date: 2026-07-04
model: deepseek-v4-flash
phase: 15
status: complete
---

# Phase 15: SpecGraph Runtime Rename — Execution

**Model:** deepseek-v4-flash
**Дата:** 2026-07-04
**Phase:** 15 (SpecGraph Runtime Rename)
**Статус:** Complete — 5/5 plans, 2 waves

## Что сделано

Wave 1 (4 параллельных плана):
- **15-01** — DB migration + seed script: `migrations/2026-07-03_knowledge_to_spec_rename.cypher` (4 ops: graph value rename, hub-node name normalization, label SET/REMOVE, index DROP/CREATE) + `test/seed_knowledge_nodes.cypher` (SC#1 proof seed)
- **15-02** — data-service/app.py: все Knowledge* → Spec* (SPEC_GRAPH, ensure_spec_indexes, spec_note_search, CRUD labels, hub MERGEs). `/knowledge/` routes preserved
- **15-03** — 3 n8n workflows renamed (ingest/query/update): git mv, Cypher labels, node names + connections (L-1), webhook paths preserved. 2 stale export snapshots deleted
- **15-04** — UI: NeoVis label/visGroups keys (8 keys) + index.html (4 sites: view key + Cypher literals + buildCypher call). Notes-panel identifiers preserved

Wave 2:
- **15-05** — 3 test files renamed + content rewrite, test shell script updated, `_add_backfill.py` deleted, docs (spec/DATABASE.md, CLAUDE.md) updated, **SC#4 gate: PASS** — zero orphaned Knowledge* graph-layer references

## Блокер найден и исправлен

Verifier обнаружил, что `n8n/workflows/spec-query.json` всё ещё ссылался на `knowledge_note_search` в inline Cypher вместо `spec_note_search`. Исправлено в `9b1bea6`.

## Ключевые файлы сессии

| Файл | Описание |
|------|----------|
| `migrations/2026-07-03_knowledge_to_spec_rename.cypher` | DB migration (SPEC-01) |
| `test/seed_knowledge_nodes.cypher` | Seed for SC#1 proof |
| `data-service/app.py` | Knowledge* → Spec* rename |
| `spec_schema.cypher` | Renamed from knowledge_schema.cypher |
| `test/test_spec_schema/crud/llm.py` | Renamed test files |
| `n8n/workflows/spec-*.json` | Renamed n8n workflows |
| `graph-viewer/config.template.js` | NeoVis label keys |
| `graph-viewer/index.html` | View-key + Cypher rename |

## Commits (13)

```
f5232b6 docs(phase-15): complete phase execution
e2ddd2a docs(phase-15): update VERIFICATION.md
9b1bea6  fix(15-03): correct stale index name in spec-query.json
6397694 docs(phase-15): update tracking after wave 2
83aef68 docs: add 15-05-SUMMARY.md
fe813d6 docs: update Knowledge* in schema docs
735b13d chore: delete _add_backfill.py
...
```

## Статус

Phase 15 полность выполнена. SC#4 gate пройден. 3 behavior-unverified items требуют ручного запуска на Docker stack (SC#1, SC#2, SC#3).
