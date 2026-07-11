---
tags: [session, v8.2, phase-821, dg-reasoner, rdf, owl]
date: 2026-07-11
---

# Session: 2026-07-11 — Phase 821 context discussion (dg-reasoner sidecar & RDF translation)

## Goal

Запуск `/gsd-execute-phase 821` показал, что фаза 821 ещё не спланирована (нет директории фазы и планов). Переключились на `/gsd-discuss-phase 821` — собрать контекст и зафиксировать решения для планирования.

## What Was Done

- Проверено состояние фазы 821: есть в ROADMAP (REAS-05, зависит от 820 — завершена), но нет `.planning/phases/821-*/` и планов → execute невозможен
- Проведено обсуждение 4 серых зон (16 вопросов через AskUserQuestion):
  1. Роль n10s vs кастомный транслятор
  2. Топология потока данных
  3. Контракт API и экспозиция
  4. Стратегия fidelity-тестов
- Создан `.planning/phases/821-dg-reasoner-sidecar-ontograph-metagraph-rdf-translation/821-CONTEXT.md` — 16 решений (D-01…D-16), canonical refs, deferred ideas
- Создан `821-DISCUSSION-LOG.md` — полный аудит-лог альтернатив
- Коммиты: `7f6988e` (context + log), `0374b9d` (STATE.md session record)

## Decisions Made

- **Транслятор — кастомный Cypher+RDFLib** по `spec/LPG-OWL-MAPPING.md`; n10s только устанавливается и smoke-проверяется (не в reasoning-пути)
- **821 включает полный hybrid union** (V7 TBox + curated disjointness + live export) через HermiT; 822 только подключает экран
- **Disjointness — отдельный overlay-файл** `ontology/dg-disjointness.ttl` (V7.owl не трогаем)
- **Sidecar сам читает Neo4j по bolt** и владеет всем пайплайном; data-service — тонкий прокси-роут с коротким таймаутом
- **Топ-уровневая директория `dg-reasoner/`** по образцу `data-service/`; TBox — read-only volume-mount `./ontology`
- **`POST /reason/consistency` — синхронный с жёстким таймаутом** (убивает JVM-сабпроцесс); богатый ответ `{consistent, unsatisfiable_classes, axiom_counts, duration_ms, stripped_builtin_rules}`
- **`/shacl/validate` — настоящий pySHACL с placeholder shapes** (`{conforms: true}`), 823 подставит реальные shapes
- **Sidecar internal-only** — без nginx-роута в 821
- **Тесты двухуровневые**: fixture-юниты (структурные проверки через RDFLib: порядок AtomList vs HAS_BODY/HAS_HEAD.order, argument1/2 vs ARG.pos) + live интеграционный round-trip на `v8-ui-smoke`
- **Drift-immunity guard**: live-тест закрепляет 2 известных mistagged атома (`R_DOOR_ORIENTATION_V_A1/_A2`) как регрессионную защиту label-scoped экспорта

См. [[decisions/dg-reasoner sidecar owns the Cypher to RDF pipeline with sync API|заметку-решение]].

## Issues Encountered

- Опечатка команды `/gad-discuss-phase` → повторный запуск `/gsd-discuss-phase 821` (без последствий)
- `init.execute-phase` возвращает `phase_found: true` при `plan_count: 0` — фаза «найдена» в ROADMAP, но директории нет; отработано ручной проверкой `phase-plan-index`

## Next Steps

- `/gsd-plan-phase 821` — планирование против 821-CONTEXT.md (все решения зафиксированы)
- Затем `/gsd-execute-phase 821`
- Дальше по цепочке: 822 (OWL reasoning + Reasoner screen), 823 (SHACL), 824 (Connector GH)

## Related Notes

- [[sessions/2026-07-11 Phase 820 execution — Reasoning-Stack Architecture Decision and OntoGraph Axiom Scoping|Phase 820 session]]
- [[decisions/Reasoning runs in isolated dg-reasoner sidecar not embedded in data-service|Sidecar decision (ADR-820-2)]]
- [[decisions/v8.2 hybrid axiom-scoping spike proven|Hybrid axiom-scoping (ADR-820-1)]]
- [[decisions/dg-reasoner sidecar owns the Cypher to RDF pipeline with sync API|Phase 821 architecture decisions]]
