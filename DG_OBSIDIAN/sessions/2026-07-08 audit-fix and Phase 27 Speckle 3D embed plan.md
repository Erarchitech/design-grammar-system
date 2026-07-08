---
tags: [session]
date: 2026-07-08
model: deepseek-v4-flash (через /model haiku)
---

# Session: Audit-fix classification + Phase 27 Speckle 3D Embed planning

## What was done

### 1. Audit-fix classification (F-01, F-02)

**F-01 — DesignStateLabel не показывается в Model Viewer**
- Проверен полный pipeline из 6 этапов: GH компонент → Core модель → GhCastingHelpers → V2 Serializer → data-service → UI
- **Вердикт: код корректен на всех этапах**
- Свежая сборка: 0 warnings, 0 errors. Тесты сериализатора: 10/10 pass (включая Label round-trip)
- Проблема: `statePayloadJson` в Neo4j был записан ДО добавления Label support (коммит `4d2b45e`), и/или Docker контейнер data-service не пересобран, и/или Rhino держит старый DLL кэш
- Решение: перезапуск Rhino, `docker compose build --no-cache data-service`, репаблиш с Panel → DesignStateLabel подключенным

**F-02 — Абстрактные SVG боксы вместо Speckle 3D в V2 Model Viewer**
- Архитектурное решение, отложенное в Phase 24 (см. `24-01-PLAN.md:27`: "true Speckle 3D embed is deferred (REQUIREMENTS Future)")
- Эскалировано в планирование Phase 27

### 2. Phase 27 Speckle 3D Embed — создана и спланирована

- Phase 27 добавлена в ROADMAP.md (v8.0 милстоун)
- `27-CONTEXT.md` — 6 locked decisions (D-01..D-06):
  - **D-01:** `@speckle/viewer` npm package (не iframe)
  - **D-02:** Viewer lifecycle: создание при выборе run, dispose при смене/анмаунте
  - **D-03:** Токен из data-service view payload (уже возвращает readToken)
  - **D-04:** Без клиентского перекрашивания (сервер уже применяет цвета)
  - **D-05:** Клик по объекту → `pick(dgEntityId)` → instance mode sidebar
  - **D-06:** 3D/Map toggle с fallback на SVG карту
- `27-01-PLAN.md` — 1 план, 2 задачи (Wave 1):
  - Task 1: SpeckleViewport React компонент + @speckle/viewer зависимость
  - Task 2: Интеграция в ModelScreen.jsx с 3D/Map toggle

## Файлы изменены

- `.planning/ROADMAP.md` — Phase 27 добавлена (закоммичено планировщиком d18c56e)
- `.planning/milestones/v8.0-phases/27-speckle-3d-embed/27-CONTEXT.md` — создан
- `.planning/milestones/v8.0-phases/27-speckle-3d-embed/27-01-PLAN.md` — создан (закоммичено планировщиком)

## Результаты

- F-01: Код корректен, проблема окружения (старый statePayloadJson в Neo4j)
- F-02: Phase 27 создана и готовa к execution
- 6 design decisions зафиксированы в 27-CONTEXT.md

## Связанные заметки

- [[2026-07-08 Per-object property binding and Speckle auto-config]] — предыдущая сессия, где F-01/F-02 были идентифицированы
- [[decisions/Phase 27 Speckle 3D embed design decisions]] — 6 locked decisions
