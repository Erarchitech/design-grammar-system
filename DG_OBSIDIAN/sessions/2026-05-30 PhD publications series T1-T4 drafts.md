---
tags: [session, publications, phd, itcon]
date: 2026-05-30
---

# Session: 2026-05-30 — PhD Publications Series T1–T4 Drafts

## Goal

Создать четыре полных черновика статей для журнала ITcon в рамках PhD-диссертации по Design Grammar System. Обеспечить согласованность серии (нет пересечений по контенту, плавные переходы), выверить T1 по опубликованной статье ptBIM 2026.

## What Was Done

### T1 — Онтологический фреймворк
- Проверен черновик `DG_Ontology_ITcon_Draft.docx` на соответствие `ptBIM2026_Evgenii_Ermolenko_UMinho_R2.docx`
- Исправлены: автор (Arkhipov→Ermolenko), SWRL-свойства (heightViolation→violatesMaxHeight), точность (94%→95%), время авторинга, IDS-упоминание
- Создан `Publications/T1_ITcon_DG_Draft.docx`

### T2 — Кодирование правил
- Прочитан Obsidian vault, код репозитория (n8n JSON, компоненты GH, app.py)
- Написан полный черновик: n8n 17-узловой воркфлоу, SWRL-парсер, CLASSIFICATOR DataTree-привязка, edit-mode, async-паттерн
- Кейс-стади: жилой фасад, 9 правил, 2 состояния
- Создан `Publications/T2_ITcon_DG_RuleEncoding_Draft.docx`

### T3 — Отслеживание состояний
- Прочитан код: DesignStateReinstatementService.cs, ReinstateComponent.cs, ValidationRunsQueryService.cs, все модели C#
- Написан полный черновик: DesignStateSnapshot, ValidationRun/ValidationEntity, DesignRuleSession, dual-filter, 7 статусов восстановления, per-run thumbnails
- Кейс-стади: mixed-use башня, 3 альтернативы (Alt A/B/C), 9 прогонов, REINSTATE для нелинейной навигации
- Создан `Publications/T3_ITcon_DG_StateTracking_Draft.docx`

### T4 — Дизайн-пространство
- Прочитан roadmap v3.0, spec/DATABASE.md, spec/GRASSHOPPER.md
- Написан полный черновик: DesignSpaceGraph (4-й слой), MetricSpec, ретроспективный сервис, LLM-suggestion (chain-of-thought, temp=0.3), LHS sampling с SWRL пре-фильтром, DESIGN SPACE GH-компонент, parallel coordinates D3.js
- Кейс-стади: продолжение T3 башни, 3 метрики оператора, 5 кандидатов, Gen-02 подтверждён (+5.7% эффективности)
- Создан `Publications/T4_ITcon_DG_DesignSpace_Draft.docx`

### Obsidian — раздел Publications
- Создан `knowledge/publications/` с 6 заметками:
  - `index.md` — обзор раздела
  - T1–T4 — отдельные заметки по каждой статье
  - `Series coherence map.md` — матрица пересечений и прогрессия серии

## Decisions Made

- **Ключевой термин T4**: «design space» = множество дизайн-решений, согласованных с дизайн-состояниями (по требованию пользователя)
- **DesignSpaceGraph**: 4-й граф-слой, не изменяет существующие узлы и отношения T1–T3
- **Генерация кандидатов**: два механизма — LLM-suggestion (exploitation) + LHS (exploration) — намеренно дополняют друг друга
- **Метрики оператора**: вычисляются из scalar-параметров DesignStateSnapshot без доступа к геометрии (осознанное ограничение, будущая работа — OBJECT STATE v3.0)
- **Кейс-стади T4**: продолжение T3 (та же башня), обеспечивает непрерывность серии

## Issues Encountered

- Синтаксическая ошибка в `build_paper3.js`: неэкранированный апостроф в строке `walls'` — исправлено вручную
- Ложные отрицания в spot-checks T3 (Mixed-use с заглавной M, citation format) — верифицированы вручную как корректные

## Next Steps

- Подготовить T1 к отправке в ITcon (форматирование по Author Guidelines, DOI ссылки)
- Рассмотреть рецензирование T2–T4 соавтором или научным руководителем
- Реализовать DesignSpaceGraph как следующий milestone после v3.0 (Typed Variables)
- Суррогатные модели — долгосрочное направление после накопления >200 DesignSpacePoints

## Related Notes

- [[publications/index]]
- [[publications/Series coherence map]]
- [[publications/T4 — Дизайн-пространство]]
