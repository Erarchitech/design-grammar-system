---
tags: [session, mapping, phase-1303, grasshopper, revit]
date: 2026-10-17
model: claude-opus-5-5
status: paused
---

# Phase 1303 — MVP автоматизированного меппинга собран и развёрнут локально, готова инструкция репетиции

## Цель

Запрос владельца: пересмотреть планы под приоритет — автоматизированный меппинг элементов Grasshopper и Revit на классы DG, демонстрация **19.10.2026**. Планы, не связанные с этой задачей, отложить. Найти кратчайший путь к автономной реализации и согласовать упрощённый, но наглядный локальный сценарий на существующем проекте `v12-hexagonal-facade-01`. Основа — исследование `docs/reviews/mapping-issue-investigation/Interactive Visual Mapping and Active-Learning UX for Design Grammars in Revit and Grasshopper.md`. Работу 1309 (параллельная сессия Hermes) не прерывать.

## Результат и границы

- Вся работа — в git worktree `C:\Users\Admin\source\repos\dg-mapping`, ветка `feature/mapping-mvp` от `535eb30`. Основная папка и ветка `feature/hosting-dg-pilot` (1309) не тронуты. Коммиты `38f2ff6`…`0955dde` и коммит этой сессии.
- MVP-срез Phase 1303: планы 01–05 выполнены офлайн. План 06 (пересборка + живое демо) выполняется: стек пересобран, пробы пройдены. **Вживую не проверены** Rhino, Revit, браузер и запись в граф — это репетиция владельца 18.10. План 07 (объяснения LLM) — линия отсечения, не начат.
- Docker на этом ПК (`DESKTOP-3M60KIN`) запущен с разрешения владельца, данного в этой сессии. В заметках 1309 для этого ПК записано «Docker не запускать». Агенту 1309 нужно знать: локальный стек работает на образах 1303, откат — теги `:pre-1303`.

## Сделано

- **Планирование.** Todo с решениями D-01..D-04; ROADMAP / REQUIREMENTS (DGMAP-01..06 вне 51 MVP ID); STATE на 1303. В фазе: CONTEXT (D-01..D-32), API-контракт, планы 01–07, UAT (7 тестов ждут), инструкция `1303-TEST-GUIDE.md`.
- **Движок** `data-service/mapping_engine.py`: свидетельства → группы → вопросы о последствиях → обучаемые профили. Детерминирован, 17 тестов.
- **Хранение и маршруты.** `mapping_store.py`, 7 маршрутов `/mapping/*`, политики маршрутов (инвентарь 113 → 120), строки в `spec/SECURITY-BOUNDARY.md`, узлы MappingSession / MappingDecision / MappingProfile; 10 тестов маршрутов. Также обновлены `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md` и `spec/API.md`.
- **Web UI.** Панель «Меппинг» в «Проектах», перевод RU; 322/322 тестов, сборка проходит.
- **Grasshopper.** Компонент C# Script `test/v12-hexagonal-facade-01/gh-mapping-intake.cs`: компилируется с DLL Rhino 8, DG.gha не пересобирается. RhinoCode-скрипты и `mapping-demo/GH-RUNBOOK.md`.
- **Revit, только чтение.** `tools/mapping/revit_read.py`: revit-mcp, только loopback, список разрешённых путей; ключи `--vocabulary` и `--populations-from`. Плюс `tools/mapping/evaluate_session.py`; 18 тестов.
- **Развёртывание.** Образы собраны из `git archive`: data-service `sha256:f241574d…`, design-grammars `sha256:b3c9b98e…`; откат `:pre-1303`. Пробы: 401 AUTH_REQUIRED на 8000 и 8080, в бандле есть «Меппинг». Генеральная проверка движка на реальных классах и правилах проекта дала 2 вопроса, как задумано.
- **Под конец сессии.** `RhinoCode.exe script <PATH>` не передаёт аргументы скрипту. `dgmap_run_act.py` заменён библиотекой `dgmap_acts.py` и файлом-обёрткой на каждое действие. Акты оставляют вариант на холсте; при ошибке слайдеры восстанавливаются. Smoke-тест на заглушках Grasshopper проходит.

## Решения

- Владелец: групповое подтверждение + профили; GH + Revit вживую (модель Revit построена через Rhino.Inside, модули фасада — семейства обобщённой модели по адаптивным точкам); Revit только читается. Разрешены Docker на этом ПК, живой Rhino/GH, чтение Revit, платные вызовы LLM.
- Архитектура: [[knowledge/decisions/Automated mapping MVP uses group questions and learned profiles (Phase 1303)|решение о меппинге]].
- Изоляция: [[knowledge/decisions/Mapping MVP is developed in a separate git worktree so Phase 1309 is not interrupted|worktree вместо переключения ветки]]. Владелец сначала не понял, зачем «новый репозиторий»; после объяснения оставил worktree.

## Проблемы

- [[knowledge/debugging/Rule body comparisons must be evaluated as one conjunction (R9)|R9: сравнения тела правила нужно оценивать вместе]] (исправлено, `a0cead0`).
- [[knowledge/debugging/data-service exits at startup when Neo4j does not accept Bolt yet|data-service падает, если Neo4j ещё не принимает Bolt]] (обход: `docker start data-service`).
- [[knowledge/debugging/RhinoCode script passes no arguments to the Python script|RhinoCode не передаёт аргументы скрипту]] (исправлено в рабочей копии, вживую не проверено).
- Импорт в Web UI ограничен 1 МБ nginx. nginx не меняли: он входит в пакет 1309. Вместо этого `--max-parameters 40` по умолчанию и предупреждение.
- Субагенты упёрлись в лимиты, оставшиеся планы контроллер выполнил сам.
- В worktree: GSD-инструменты скопированы в `.claude/` без отслеживания (не коммитить); хуки graphify переписывают `graphify-out/`; артефакты сборки удалены. Коммитить только явные пути.

## Следующие шаги

1. Владелец, 18.10: репетиция по `.planning/phases/1303-pravilo-gh-obekt/1303-TEST-GUIDE.md` (шаги 0–7). Нужна открытая модель фасада в Revit 2024 с DeGram pyRevit.
2. По материалам (`%TEMP%\dgmap-rhinocode.log`, скриншоты, `act3-revit-read*.json`) заполнить `mapping-demo/PROTOCOL.md` и `1303-UAT.md`, исправить расхождения.
3. 19.10 — демо.
4. После демо и точки фиксации 1309 — слить `feature/mapping-mvp`. Ожидаемые конфликты: `Current priorities.md`, `00-home/index.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`.
5. План 07 (объяснения LLM) — только если останется время.

## Связанные заметки

- [[v12-hexagonal-facade-test]] (память), `test/v12-hexagonal-facade-01/README.md`
- `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`, `1303-API-CONTRACT.md`
- [[00-home/Current priorities|Текущие приоритеты]]
