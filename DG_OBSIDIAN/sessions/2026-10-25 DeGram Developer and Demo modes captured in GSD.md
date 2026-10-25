---
tags: [session, degram, gsd, planning, hosting]
date: 2026-10-25
status: saved
---

# DeGram Developer and Demo modes captured in GSD

## Запрос

`/gsd-capture`: адаптировать DeGram для Developer Mode (DG localhost, разработка/внутренние тесты) и Demo Mode (реальный DG stand на Contabo), реализовать в ближайшее время и встроить в планы GSD. Затем владелец попросил сохранить сессию.

## Сделано

- Выполнен add-todo workflow; проверены дубликаты — совпадений нет. GSD распознаёт новую задачу, pending todo files: 3.
- Добавлен priority todo `.planning/todos/pending/2026-10-25-add-degram-developer-mode-and-demo-mode.md`.
- Добавлен planning brief `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-DUAL-MODE.md`: поведение/границы, предложенные пакеты A/B/C и матрица приёмки.
- В `.planning/REQUIREMENTS.md` добавлены DGMODE-01..04 и traceability к Phase 1301; hosted leg связан с 1309/HOST-05. Исходные 51 MVP ID не изменяют ownership.
- ROADMAP и Pending Todos в STATE фиксируют ближайший bounded DeGram client follow-up, без ожидания всех 1302–1307 или полного HOST-04.
- Главное: явный mode/target, isolation по environment/origin, безопасный lifecycle переключения и Developer→Demo→Developer test. Developer не обход прав, Demo не mock; native bridges остаются локальными.
- Решение сохранено в [[knowledge/decisions/DeGram Developer Mode uses localhost and Demo Mode uses Contabo]]. Приоритеты и home index обновлены.

## Проверки и фактический статус

- `python tools/degram/workspace.py verify` — exit 0 перед planning и после изменений; component/gitlink `b619e02e3725869b1ab5125951d3311e3656dc9a`, component context installed. `productAccepted: false` и прежние pending gates не изменены.
- `node .claude/gsd-core/bin/gsd-tools.cjs query init.todos` — 3 задачи, новая распознана с корректными metadata.
- `git diff --check 1d90141..ba0368c` — PASS; итог capture: 5 файлов, 129 добавленных строк.
- Проверены отсутствие BOM и LF в новых planning files. Прежние изменения shared planning files сохранены отдельно от capture-коммитов; real Git index после reconciliation пуст.
- Первые попытки изолированного commit preparation остановлены на patch context / Windows stdout encoding. Commit `6549b01` создал capture; отдельный `ba0368c` исправил размещение вставок по стабильным anchors, после чего сохранность прежних изменений подтверждена. История не переписывалась.
- Код продукта, gitlink, сервер, контейнеры, установленный Desktop и Hermes profile не менялись. Product tests/build/live UAT не запускались. Jev tool lookup не нашёл доступного инструмента; внешняя оценка не выполнялась.

## Git

Framework branch: `gsd/milestone13`.

Локальные capture-коммиты:

- `6549b01` — `docs: capture priority DeGram Developer and Demo modes`.
- `ba0368c` — `docs: align mode capture insertions with stable planning anchors`.

Session-save документация коммитится отдельно только собственными добавлениями. Прежние несохранённые source/planning/vault изменения не включать. Push в этой сессии не выполнялся.

## Следующий шаг

`/gsd-plan-phase 1301` с явным ограничением на новый срез DGMODE-01..04 и brief `1301-DUAL-MODE.md`; сначала проверить существующие планы и выделить следующие свободные номера (на capture момент планы доходили до 41).

Пакеты: A — component config/migration/isolation → B — component selector/safe target switch/real-path A→B→A tests → C — framework exact published gitlink/docs и отдельно разрешённые build/install + localhost/Contabo acceptance. Детальные executable PLAN-файлы **не созданы**, реализация **не начата**, ни одно требование/фаза автоматически не закрыты.

Рабочая база DeGram — `apps/degram` / `degram/milestone13`; `D:\dgb\src` build-only. Перед component-touching работой повторить workspace preflight и прочитать area instructions. Отдельные разрешения нужны для component commit/push, build/install/launch, runtime/paid inference и мутаций; capture не расширяет их scope.
