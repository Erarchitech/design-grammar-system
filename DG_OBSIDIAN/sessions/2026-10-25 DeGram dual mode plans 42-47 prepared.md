---
tags: [session, degram, planning, dual-mode]
date: 2026-10-25
---

# DeGram dual mode — plans 42–47 prepared

## Результат

Подготовлены только новые планы Phase 1301 для DGMODE-01..04: 42 конфигурация/ownership, 43 профили/миграция, 44 main/backend switch, 45 UI/renderer, 46 real-path offline, 47 интеграция и отдельно разрешаемая live-приёмка. Зависимости 42→43→44→45→46→47, waves 29–34. Старые планы 01–41 не переписаны; требования и Phase1301/DGCL/HOST-05 не закрыты.

Артефакты: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-42-PLAN.md` … `1301-47-PLAN.md`, `1301-DGMODE-RESEARCH.md`, `1301-DGMODE-VALIDATION.md`, `1301-DGMODE-PLAN-CHECK.md`; обновлена навигация/статус `1301-DUAL-MODE.md`.

## Проверки и ограничения

- workspace.py verify прошёл; child/gitlink `b619e02e3725869b1ab5125951d3311e3656dc9a`, context installed, productAccepted false.
- GSD plan-structure/frontmatter прошли для шести планов; проверены зависимости, scoped requirement IDs, задачи и настоящий parseMustHavesBlock; UTF-8 без BOM/LF.
- Предупреждение wave>1 без зависимости у 42 намеренное: независимый новый срез продолжает нумерацию волн, но не зависит от старого release-плана 41.
- Независимый checker НЕ запускался. После неудачных isolated-agent запусков владелец запретил subagent worktrees/отдельные ветки и явно выбрал inline-продолжение. Это самопроверка, не независимый PASS.
- Node на planning host v20.20.0 ниже Desktop engines. Перед тестами выбрать уже установленный поддерживаемый Node либо зафиксировать blocker; не устанавливать автоматически.
- Код компонента не изменён; продуктовые тесты, сборка, установка, Desktop launch, deploy, paid inference и CAD-действия не выполнялись.

## Ключевые технические решения планов

Явный origin/env override; не путать новый Developer/Demo с существующим graph/full. Legacy cookies adopt-in-place только для доказанного origin; сохранить revitPython/revitMcpDir и неизвестные config keys. Origin в profile manifest/hash и ВСЕХ purge/cleanup путях. Main/backend guard вместо renderer-only idle; строгий teardown и environment+generation fence; no replay/fallback. Same-home A→B→A с реальным profiles CLI/файловой системой, не только mocks. Решения являются implementation choices, не новыми заявлениями владельца. См. [[knowledge/decisions/DeGram dual mode is an additive plan slice with explicit runtime gates]].

## Продолжение — только эти планы

Работать из `C:/Users/Admin/source/repos/design-grammar-system` на framework `gsd/milestone13`, child `apps/degram` на `degram/milestone13`. Не создавать worktrees/ветки для субагентов; D:/dgb/src только build clone. Запустить в следующей сессии:

```text
/gsd-execute-phase 1301 --wave 29 --no-transition
```

Это только 1301-42. После её успешного завершения последовательно запускать следующие команды (каждую отдельно, после проверки предыдущей):

```text
/gsd-execute-phase 1301 --wave 30 --no-transition
/gsd-execute-phase 1301 --wave 31 --no-transition
/gsd-execute-phase 1301 --wave 32 --no-transition
/gsd-execute-phase 1301 --wave 33 --no-transition
/gsd-execute-phase 1301 --wave 34 --no-transition
```

Локальный execute-phase workflow действительно поддерживает один `--wave N` и `--no-transition`; фильтр диапазона/--plans не предполагается. Не запускать bare `/gsd-execute-phase 1301` или `--gaps-only`: они не ограничивают исполнение этим срезом. Перед исполнением подтвердить mapping waves→plans по текущему диску. В plan47 остановиться на отдельных authorization checkpoints: child commit, public push, build/install/launch/live; команда сама их не разрешает. Требования и весь этап не закрывать автоматически.

## Сохранение

По запросу владельца «Сохрани сессию» создаётся отдельный локальный framework-коммит только с файлами/хунками этой сессии. Предыдущие чужие изменения vault/planning/source/generated остаются вне коммита. Push не разрешён и не выполняется. Модель: Claude (точный model ID не предоставлен средой).
