---
tags: [session, degram, phase-1308, planning, i18n, connectors]
date: 2026-10-12
---

# Session: 2026-10-12 — Phase 1308 planned (24 plans), language switch moved to DeGram settings

## Информация о сессии

- Модель: claude-opus-5-5
- Дата: 2026-10-12
- Изменено файлов: 37 (коммиты `c64424a`, `7cbd3d6`, `ba3c529` и коммит сохранения)

## Goal

`/gsd-plan-phase 1308` без discuss-phase: владелец утвердил все рекомендации исследования («skip discussing, approve all recommendations»).

## What Was Done

- `workspace.py verify` (DeGram preflight) зелёный.
- **Research** (gsd-phase-researcher): `1308-RESEARCH.md`, 8 открытых вопросов семени закрыты рекомендациями; предложены WEBUI-01..11. Найдено: образ data-service уже совпадает с HEAD (D-32 закрывается проверкой); D-37 — только UI; D-49 требует замены `dgc_` на сессию входа коннектора `dgk_`.
- `1308-CONTEXT.md` (D-01..D-49 из рекомендаций), WEBUI-01..11 в `REQUIREMENTS.md`, `1308-VALIDATION.md`; коммит `c64424a`.
- **UI-SPEC** (gsd-ui-researcher + gsd-ui-checker, 2 ревизии): метки «Отмена» заменены конкретными, шкала 12/14 px, отступы 4/8/16/24; probe UI-состояний — 24 covered / 4 backstop; коммит `7cbd3d6`.
- Pattern map (33/36 аналогов), edge probe (24 пункта).
- **Planner:** 20 планов → поправка владельца по языку (+1308-21) → ревизия по plan-checker (1 blocker, 7 warnings: тесты легаси-токенов вне списков файлов, `test_auth_store.py` WIP, разбиение 05/16/13 → новые 22, 23, 24, отказ от прошлых шаблонов ошибок GH, waiver на gitlink ≠ child HEAD, каскад D-33 на путях приглашений) → итерация 2: 0 blockers. План 19: проверка дерева `HEAD:data-service HEAD:ui-v2` вместо HEAD (исправлено вручную).
- Итог: **24 плана в 10 волнах**, решения 54/54, WEBUI-01..11 покрыты, gap-analysis пройден; коммит `ba3c529`. STATE: 1308 выполняется до 1302.

## Decisions Made

- **D-50..D-54 (владелец 2026-10-12):** язык всего интерфейса переключается только в DeGram Settings → Appearance → Language, только «Русский» и «English»; живой сигнал `#degram-lang=`; в DG Web UI своего переключателя нет; в обычном браузере — основной язык браузера (рекомендация). Заметка: [[knowledge/decisions/Interface language is switched only in DeGram settings, Russian and English only (D-50..D-54)]].
- Порядок: фаза 1308 выполняется раньше 1302 (владелец).
- Все рекомендации research/UI-SPEC приняты как решения D-01..D-49 (в т.ч. TTL сессии коннектора 8 ч, viewer с грантом может публиковать, «Keys issued» → «Grants issued»).

## Issues Encountered

- 15 из 24 планов с CRLF: `parseMustHavesBlock` читал 0 truths; нормализовано в LF ([[knowledge/debugging/GSD must_haves parse 0 truths when plan files have CRLF line endings]]).
- Planner один раз остановился на лимите API до правок; перезапущен с тем же заданием.

## Next

- `/gsd-execute-phase 1308`; первым — план 1308-01: владелец фиксирует или откладывает незакоммиченные правки (`ProjectsScreen.jsx`, `lib/auth.js`, `ui-v2/tests/*`, data-service WIP с `test_auth_store.py`, `ValidatorComponent.cs`).
