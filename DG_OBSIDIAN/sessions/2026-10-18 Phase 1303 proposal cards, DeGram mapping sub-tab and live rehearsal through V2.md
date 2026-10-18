---
tags: [session, mapping, phase-1303, grasshopper, degram, llm]
date: 2026-10-18
model: claude-opus-5-5
status: done
---

# Phase 1303 — карточки предложений, подвкладка DeGram «Меппинг», живая репетиция до V2

## Цель

Вторая сессия 18.10, накануне демо 19.10. Всё — в worktree `C:\Users\Admin\source\repos\dg-mapping`, ветка `feature/mapping-mvp`. Основная папка и 1309 не тронуты. Задачи владельца:

1. Разобрать результаты шагов 3–5 инструкции и исправить расхождения с тестами.
2. Прогнать тесты.
3. Заполнить PROTOCOL / UAT / SUMMARY по фактам.
4. Сделать понятнее вопрос «ошибка меппинга или проекта?».
5. Сценарий демо.

По ходу владелец добавил запрос (план 1303-10): отчёт в Web UI неудобен, много текста и не видно, какие элементы предлагаются. Нужно:
- временные теги и группы на холсте;
- в DeGram «Модели» подвкладка «Меппинг» под каждой моделью: прогресс, сворачиваемые предложения, отмена у каждого решения, цветные кликабельные компоненты с зумом в Grasshopper, кнопка запуска;
- в Web UI то же, но без кликабельности и без запуска.

## Результат

- **Прогон 1** (`ms-98a39fa841bc`, утро): Panels C отвечен «GlassPanel — ошибки проекта» вместо BottomTriangularPanel. Причина: LLM предложил GlassPanel для треугольных потоков, а текст вопроса не объяснял кнопки. Исправлено в `ab04bb3`. По решению владельца профили этих ответов выключены, прогон начат заново.
- **План 1303-10** выполнен:
  - сервер `c8c24d2`: заголовки и `items`, `answers`, `POST …/undo`, `document`, делегированный токен DeGram на маршрутах меппинга;
  - DG.gha `2a87093`: рамки и теги на холсте, 10 с до применения, команды моста `focus_component`, `start_mapping`, `get_mapping_status`;
  - Web UI `a1ea659`: карточки, по строке на компонент, отмена у каждого решения;
  - DeGram `93997683` в `D:\dgb\src`, не запушен: подвкладка «Меппинг» и RPC `degram.mapping.*`.
- **Прогон 2** (`ms-56907a90d11f`, ответы в DeGram):
  - 13 → 6 вопросов;
  - одна отмена и повторный ответ;
  - применение через 13 с после последнего ответа;
  - расстановка: 5 OBJECT STATE, 11 PROPERTY STATE + RULE BY ID, 13 параметров, DESIGN STATE, VALIDATOR;
  - потоки совпали с эталоном V1 (376);
  - VALIDATOR V1: 11/11 PASS.
  Владелец: «меппинг протестирован в DeGram — всё работает как положено».
- **V2** (Claude через RhinoCode): 421 элемент по профилям, ответов человека нет. VALIDATOR: R_GLASS_ASPECTRATIO_MAX ×12 и R_GP_WIDTH_MIN ×57, как в замерах 05.10. V1 возвращён.
- **Подготовка демо**: все 27 профилей за 18.10 выключены (`retiredReason` «cold start for the demo…»). Пересчёт без записи даёт 6 вопросов.
- **Документы**: PROTOCOL.md, 1303-UAT.md (10/12 pass, 1 issue, 1 pending), 1303-08/09/10-SUMMARY, 1303-10-PLAN, D-39…D-43, TEST-GUIDE, DEMO-19-10.md.
- **Тесты**:
  - data-service 5809 пройдено, известные 4 + 25 от окружения;
  - mapping 50/50;
  - DG 48/48, сборка Release;
  - UI 331/331;
  - DeGram: Python 75/75; vitest 314 пройдено, 1 давнее падение каталога настроек; tsc и eslint чистые.
- **Развёртывание**:
  - data-service `7867f98` (`8c8c04a8…`) и UI `a1ea659` (`aae916eb…`), откат — теги `:pre-1303-10`;
  - DG.gha `3D1202A3…`, откат `%LOCALAPPDATA%\DG\plugin-backups\pre-1303-10-20261018-140305`;
  - DeGram — `D:\dgb\src\apps\desktop\release\win-unpacked\DeGram.exe`; установленная 0.1.11 не тронута;
  - на очищенной копии стоит LISTENER (Run = True), резервная копия — `…-auto-mapping.pre-listener.gh`.

## Решения

- [[knowledge/decisions/Mapping proposals are cards with per-answer undo, canvas tags and a DeGram sub-tab with full GH bridge access (Phase 1303)|D-39…D-43]]: карточки с отменой, рамки на холсте, граница DeGram расширена по решению владельца, подвкладка DeGram, сборка в клоне без push.
- Холодный старт на демо: профили 18.10 выключены, не удалены.
- Кнопка «Импорт дескрипторов (JSON)» в Web UI пока остаётся: она нужна для акта Revit.

## Проблемы

- [[knowledge/debugging/LLM-held slider was never decided and was asked again in every variant|Слайдер, удержанный LLM, не получал решения]]: 1 лишний вопрос и вызов LLM после расстановки и на каждом варианте. Исправлено в `7867f98`, вживую ещё не проверено.
- [[knowledge/debugging/Retired mapping profile stayed retired after the same answer|Выключенный профиль оставался выключенным после того же ответа]]. Исправлено в `ab04bb3` и проверено вживую: профиль Panels A снова включился.
- [[knowledge/debugging/RhinoCode act scripts failed on System.Decimal slider values|Скрипты актов падали на System.Decimal]]. Исправлено в `c3e673c`.
- [[knowledge/debugging/Facade gh copies sign in to CONNECTOR on open from Panels|Panel с паролем]]: снимок холста (DrawToBitmap) захватил Panel CONNECTOR с паролем. Файл сразу удалён; владельцу советовано сменить пароль и убрать Panel.
- Субагент DeGram остановился на лимите API и был продолжен; DSH-хаб недоступен, поэтому работу делали субагенты Claude.
- Сборка DeGram перезаписала `release\DeGram-Setup-0.1.11.exe` в клоне.

## Следующие шаги

1. 19.10 — демо по `test/v12-hexagonal-facade-01/mapping-demo/DEMO-19-10.md`. Перед ним: не сохранять открытую копию (в памяти Rhino там группа DG), открыть её с диска, убрать Panel с паролем.
2. После демо — меппинг Revit (модель того же фасада даёт владелец), промпт ниже.
3. Слияние с 1309: STATE / ROADMAP / REQUIREMENTS вручную. Push `93997683` в форк — с разрешения владельца, затем сдвиг ссылки подмодуля.

## Промпт следующей сессии

```
/gsd-discuss-phase 1303 — Revit-срез меппинга (план 1303-11)

Работай только в worktree C:\Users\Admin\source\repos\dg-mapping, ветка feature/mapping-mvp.
Основную папку C:\Users\Admin\source\repos\design-grammar-system и ветку feature/hosting-dg-pilot (1309)
не трогай и ничего там не коммить. GSD-артефакты пиши inline, без субагентов-планировщиков.

Сначала прочитай:
- DG_OBSIDIAN/sessions/2026-10-18 Phase 1303 proposal cards, DeGram mapping sub-tab and live rehearsal through V2.md
- .planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md (D-05, D-07, D-09, D-10, D-20, D-27, D-39…D-43),
  1303-API-CONTRACT.md §1 и §7, 1303-10-SUMMARY.md, 1303-UAT.md (тест 12), 1303-TEST-GUIDE.md (шаг 6)
- tools/mapping/revit_read.py; data-service/mapping_engine.py (population evidence, IFC hints, профили)
- DeGram (клон D:\dgb\src, ветка feature/mapping-mvp): degram_variant/revit_bridge.py, degram_variant/mapping.py,
  apps/desktop/src/degram/mapping-panel.tsx (Revit-строки сейчас показывают только сессии)

Цель: меппинг модели Revit того же фасада (v12-hexagonal-facade-01) по тем же классам и правилам, с вопросами
по группам семейств и переносом профилей GH → Revit. Модель Revit даю я (путь сообщу), открываю её в Revit 2024
с pyRevit и расширением DeGram; revit-mcp на http://127.0.0.1:48884/revit_mcp/ — только чтение.

Обсудить и записать решения D-44+:
1. Запуск меппинга Revit: из DeGram («Запустить меппинг» для Revit-модели — бэкенд читает выделение через
   revit_bridge и создаёт сессию; для этого делегированному токену нужен POST /mapping/sessions — изменение
   route policy и SECURITY-BOUNDARY) и/или через Web UI «Импорт дескрипторов (JSON)» + revit_read.py.
2. Какие свидетельства есть у Revit: семейство/тип, параметры, IfcExportAs, численность групп против последней
   подтверждённой GH-сессии (populationsFromSessionId); адаптивных точек маршруты не отдают (D-27).
3. Перенос профилей GH → Revit и вопрос «обе роли» (HexagonalUnit + FacadeModule); ожидание: первое чтение —
   не больше одного вопроса на группу семейств, второе чтение — 0 вопросов (D-24).
4. Клик по элементу Revit в DeGram: выделение/показ в Revit — это запись в UI Revit, сейчас запрещено
   (D-10, D-20, Phase 1306). Нужно моё отдельное решение; без него строки Revit не кликабельны.
5. Как проверять: шаги теста, ожидаемые числа по семействам (узнаем, когда модель открыта), протокол.

Затем /gsd-plan-phase 1303 (план 1303-11) и выполнение с тестами.

Ограничения:
- Revit — только чтение (никаких записей в модель, параметров, цветов, выделения).
- Не читай .secrets/ и значения Panel с логином и паролем у CONNECTOR; не делай снимков холста рядом с CONNECTOR.
- Профили 18.10 выключены для холодного старта демо (retiredReason «cold start for the demo…»);
  не включай их без моего слова.
- Каждое переоткрытие GH-копии — новая сессия и платный вызов LLM; делай это только по необходимости.
- Docker, живой Rhino/GH и платные вызовы LLM на этом ПК разрешены для 1303. Образы — из git archive
  коммита, откат по тегам. DG.gha ставь только при закрытом Rhino.
- DeGram: правки и коммиты в D:\dgb\src (feature/mapping-mvp), сборка D:\dgb\run-build.sh, запуск
  win-unpacked с очищенным окружением; без push, без hermes update, без записи в установленный профиль Hermes.
- Коммить только явные пути; не коммить .claude/, graphify-out/, bin/obj (верни git checkout), *.3dm.rhl.
- Слияние с 1309 — после демо, отдельной задачей.
```

## Связанные заметки

- [[sessions/2026-10-18 Phase 1303 automatic mapping in CONNECTOR with LLM proposal and placement up to VALIDATOR|утренняя сессия 18.10]]
- [[knowledge/decisions/Mapping is proposed with an LLM and CONNECTOR places DG components bound by identity (Phase 1303)|D-33…D-38]]
- `test/v12-hexagonal-facade-01/mapping-demo/PROTOCOL.md`, `DEMO-19-10.md`; `.planning/phases/1303-pravilo-gh-obekt/1303-10-PLAN.md`, `1303-10-SUMMARY.md`, `1303-UAT.md`
- [[00-home/Current priorities|Текущие приоритеты]]
