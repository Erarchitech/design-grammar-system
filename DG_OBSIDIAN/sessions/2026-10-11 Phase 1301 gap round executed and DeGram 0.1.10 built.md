---
tags: [session, degram, phase-1301, gap-closure, release]
date: 2026-10-11
---

# Session: 2026-10-11 — Phase 1301 gap round executed, DeGram 0.1.10 built

## Информация о сессии

- Модель: claude-sonnet-5-5
- Дата: 2026-10-11
- Изменено файлов: 5 в коммите сохранения (плюс коммиты задач ниже)

## Goal

`/gsd-execute-phase 1301 --gaps-only`: начать с плана 33 (владелец разрешил удаление двух файлов pairing-panel), затем выполнить оставшиеся gap-планы 34–36.

## What Was Done

- **План 33 (D-39), inline:** удалены `pairing-panel.tsx` и `pairing-panel.test.tsx` по явному разрешению. Typecheck чистый, Electron 214/214, UI 6268 pass + 2 известных voice-prefs. Компонент `03785f3e`; framework `c2ebd50`.
- **План 34 (D-41/D-42/D-44), gsd-executor:** DeGram остаётся на кольце DG, фрагменты host↔page, боковая панель из шести пунктов, пины по scope, без «DEGRAM», без БОТЫ. Компонент `c3318b2d`; framework `422d065`.
- **План 35 (D-43, G-25), gsd-executor:** экран «Модели», нижняя полоса только со статусами, `scope-gate.ts` против повторного запуска бэкенда ушедшего проекта. Компонент `38728957`; framework `dee60a9`.
- **План 36:** владелец запушил `degram/phase-1301` (дважды: до и после версии). Версия 0.1.10 `93aa2b99`, gitlink `8c4dc7c` (`workspace.py verify` exit 0). `data-service` и `design-grammars` пересобраны **из `git archive` HEAD**, не из рабочего дерева, и перезапущены. Установщик `DeGram-Setup-0.1.10.exe`, SHA-256 `b13d10efd776f83c000ec3c75f91fe03706b72c94e6b3d0beec1fef4bab40e88`, проверки артефактов пройдены. Записи: `1301-BUILD.md`, `1301-0.1.10-TEST-GUIDE.md` (12 шагов, по-русски), `1301-36-SUMMARY.md`; framework `5382e41`, `ef645a5`.
- Проверки живых маршрутов без учётных данных: `session-exchange` без сеанса 401 `AUTH_REQUIRED`; `/auth/degram/exchange` с `dgp_` 401 `PAIRING_RETIRED`.

## Decisions Made

- Сервисы пересобирать из чистого экспорта HEAD, когда рабочее дерево содержит чужие незакоммиченные правки: [[knowledge/decisions/Service images are rebuilt from a clean git export of HEAD, not the dirty working tree]].

## Issues Encountered

- G-25: причина найдена воспроизведением на подменах — лестница переподключения renderer-реестра заново открывала ушедший scope, main её слушался: [[knowledge/debugging/DeGram left-scope backend restarted by the renderer reconnect ladder (G-25)]].
- Падает `cron-detail.test.tsx` «Overdue since … ago» (русская локаль `Intl.RelativeTimeFormat`); ни он, ни `time.ts` не менялись с 0.1.9; на чистом checkout не проверено.
- `workspace.py verify` до пуша печатал «gitlink does not match» — ожидаемо при незапушенных коммитах дочернего репозитория.
- Python-правка `STATE.md` с обычной строкой повредила путь `D:\dgb\src\apps\...` (`\a`, `\r`); исправлено через Edit — см. [[knowledge/debugging/Backslashes lost in a shell edit corrupted the DeGram build adapter path]].
- Устаревший каталог `.git/modules/degram/worktrees/dgp-t` не удаляется (Permission denied); коммиты не затронуты.

## Next Steps

1. Владелец ставит 0.1.10 и проходит `1301-0.1.10-TEST-GUIDE.md`, присылает pass/fail по шагам. Шаг 10 требует времени для сверки `desktop.log` (G-25); `403 GRANT_REQUIRED` с реальным пользователем ещё не проверялся.
2. Затем план 16 (живой UAT, не gap-closure), верификация и завершение фазы.
3. На `D:` свободно 3.4 ГБ: перед следующей сборкой удалить старые установщики по решению владельца.
4. Незакоммиченные правки других сессий в `data-service/cypher_allowlist.py`, `dg_context.py`, `ui-v2/src/lib/auth.js`, `ProjectsScreen.jsx` в образы не попали; их нужно закоммитить и пересобрать отдельно.

## Related Notes

- [[sessions/2026-10-11 Phase 1301 plans 31-32 and plan 33 blocked]]
- [[knowledge/decisions/DeGram access is granted by the project owner, not pasted by the user]]
