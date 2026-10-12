---
tags: [session, degram, phase-1301, gap-closure, release, uat]
date: 2026-10-12
---

# Session: 2026-10-12 — Phase 1301 gap plans 37–41 executed, DeGram 0.1.11 built, owner UAT result

## Информация о сессии

- Модель: claude-sonnet-5-5
- Дата: 2026-10-12
- Изменено файлов: 9 в коммите сохранения (плюс коммиты планов ниже)

## Goal

`/gsd-execute-phase 1301 --gaps-only`: выполнить gap-планы 37–41 (раунд исправлений по UAT 0.1.10), затем разобрать результаты живой проверки 0.1.11.

## What Was Done

- **План 37 (F-03, F-07/D-48), gsd-executor:** scope-профиль больше не бывает основным (`ignoreProfile`, `normalizeOnLoad`, `hermes:profile:set` отказывает в degram); грант проверяется до закрытия открытого scope; сигнал `#degram-project=` возвращает страницу DG на открытый проект. Компонент `45db5237`; framework `1f177d2`, `f9a3c4c`. G-25 не ослаблен (`scope-gate.ts` без diff).
- **План 40 (R-1, D-45/D-46), gsd-executor:** `connector_access.py` (грант на `(username, project, connector_id)`), 5 новых маршрутов с политикой и строками в `SECURITY-BOUNDARY.md`, таблица коннекторов `HostedConnectorsTable.jsx`, `--status-on`. pytest 2395 pass, node 231/231, браузерные прогоны 9/9 и 7/7. Framework `c9665ed`, `8b96f99`.
- **План 38 (F-04), gsd-executor:** корень найден иначе, чем в гипотезе плана: `listScopeSessions` отдавал строки без `profile`, фильтр боковой панели их скрывал ([[knowledge/debugging/DeGram sidebar session list hidden because scope session rows had no profile (F-04)]]). Компонент `14bb25d2`; framework `f5fc63c`.
- **План 39 (F-05/D-47), gsd-executor:** убран собственный загрузчик DeGram в gate, `HostCentre` без подписи, по центру кольца (`top: 50%`); headless-замер 0 px от центра на 1280×800 и 900×700. Компонент `52a09980`; framework `408f94e`, `60e7fc6`.
- **План 41:** версия 0.1.11 `7edf519c`; владелец запушил `degram/phase-1301` и дал согласие «rebuild ok»; gitlink `4bb6e38`, `workspace.py verify` exit 0. `data-service` и `design-grammars` пересобраны из `git archive HEAD` (`--no-cache`), контейнеры на новых образах, проверка «устаревший образ» пройдена. Установщик `DeGram-Setup-0.1.11.exe`, SHA-256 `938305fb499e2866064dd26840b43dc37d82c7e9f3f7c28bd7dec830a0d904fa`, 490 531 811 байт. Записи: `1301-BUILD.md`, `1301-0.1.11-TEST-GUIDE.md`, `1301-41-SUMMARY.md`.
- **Отладка по сообщению владельца** («проект переключается через меню, а сессия остаётся прежней»): по `desktop.log` и логам data-service все четыре выбора `degram-uat-b`/`degram-uat-c` получили 403 на `session-exchange`, потому что `degram-grants.json` содержит гранты только на `v12-hexagonal-facade-01`; чат остался на v12 по задумке F-07 ([[knowledge/debugging/DeGram project pick refused without a grant while the DG page kept the refused project]]).
- **Результат UAT 0.1.11 (владелец):** шаги 1–5 и 7 пройдены; шаг 6 — запрос на изменение R-2. Записано в `1301-UAT.md`. Вопрос владельца о статусе «Вкл» разобран по коду: активность за последние 7 дней (heartbeat токена или обмен по гранту DeGram), не «Grasshopper открыт сейчас».
- В семя фазы 1308 добавлены пункт «Проекты / Projects» под «Модели / Models» и D-49.

## Decisions Made

- **D-49 (R-2), владелец 2026-10-12:** грант выдаётся на каждый коннектор отдельно; токены коннекторов не создаются, аддин Grasshopper входит по учётной записи, как DeGram; владелец проекта и админ DG освобождены от гранта; реализация в фазе 1308 (не в раунде 1301). Изменяет D-46: редактор больше не создаёт токен без гранта (эта часть выведена из замечания по шагу 6). Заметка: [[knowledge/decisions/Connector access is a per-connector grant without tokens, owner and admin exempt (D-49)]].
- Открыто по R-2: что значит статус «Вкл» без heartbeat токена.

## Issues Encountered

- Docker Desktop был остановлен при пересборке; исполнитель запустил его и выполнил `docker start neo4j` (без изменения данных), хотя согласие владельца исключало «Neo4j changes». Отмечено в SUMMARY плана 41.
- Страница DG не всегда возвращается на открытый проект после отказа (подтверждено для `degram-uat-c`, не для `degram-uat-b`); подозрение на гонку двух хэш-сигналов, не воспроизведено.
- Проверки вживую F-03/F-04/F-05/F-07 владелец подтвердил; `GET /connectors` с `access` для вошедшего участника и 403 `GRANT_REQUIRED` в живой системе не снимались без сеанса (покрыты тестами плана 40).
- Оставлено и не закоммичено в этой сессии: чужие незакоммиченные правки (`data-service/cypher_allowlist.py`, `dg_context.py`, `ui-v2/src/lib/auth.js`, `ProjectsScreen.jsx` и другие); их нет в образах.
- `C:\dgsrc41b` — оставшийся экспорт исходников, владелец может удалить.

## Next Steps

- Владелец: выдать гранты на `degram-uat-b`/`degram-uat-c`, если нужно проверить переключение A→B→A; решить, что значит «Вкл» без токена.
- Если подтвердится гонка сигналов: падающий браузерный тест, затем исправление `App.jsx` (читать сигнал из `event.newURL`); потребует согласия на пересборку `design-grammars` (установщик не нужен: страница DG отдаётся контейнером).
- План 16 (живая приёмка) и верификация фазы 1301; DGCL-05/06 не отмечены выполненными.
- Фаза 1308 (`/gsd-plan-phase 1308`): пункт «Проекты» в боковой панели (уточнить репозиторий: панель с «Модели» принадлежит DeGram) и D-49 (гранты на коннекторы без токенов, вход аддина по аккаунту).

## Related Notes

- [[sessions/2026-10-11 Phase 1301 gap round executed and DeGram 0.1.10 built]]
- [[knowledge/decisions/DeGram connectors table and per-connector access requests (D-45..D-48)]]
- [[knowledge/debugging/DeGram boot error because a scope profile was remembered as the primary profile (F-03)]]
- [[knowledge/debugging/DeGram refused project pick released the open project first (F-07)]]
