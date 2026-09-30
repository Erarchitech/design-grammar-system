---
tags: [decision, evidence, validation, compatibility]
date: 2026-09-30
phase: "1205.1"
status: implemented-and-verified
---

# Evidence v2 preserves rule outcomes and keeps legacy projections separate

## Решение владельца

При закрытии v12.0 audit BLOCKER-01 владелец подтвердил расширение envelope результатами правил, совместимое чтение старых данных, сохранение legacy booleans/lists и `unknown` с диагностикой при отсутствии typed binding evidence. Также разрешены минимальная защита corrupt JSON и автономный цикл с независимыми gates.

## Реализация

- Typed outcomes сохраняются вместе с исходными BindingRow references **до** rule rollup; package агрегирует только точную пару `(ruleId, objectId)`.
- GH production mapper передает canonical statuses, warnings/detail и точный selector `2.0.0`.
- Envelope `2.0.0` требует отдельные `ruleResults`. Несколько правил с нулевой population сохраняют identities/status без фиктивного objectId.
- Старые factory defaults и canonicalization остаются прежними. Literal `1` и `1.0.0` сохраняются; strict full schema validation отделена от bounded historical read projection. No-rows historical evidence не создает object verdict из summary.
- Legacy bool/lists/OverallStatus/ValidStatus сохранены для совместимости; canonical evidence authoritative.
- Reader-first deployment обязателен. Локальная сборка не равна установленному плагину или обновленному серверу.

## Проверка и границы

Независимая verification 11/11, review clean; Nyquist 14/14 tasks и security 14/14 planned threats закрыты. Offline proof использует source-linked настоящий GH mapper/DTO/JsonOptions, реальные авторизованные handlers и captured external persistence I/O; те же bytes поступают Python view и C# reader.

Это не live Rhino/Neo4j UAT, не historical backfill, не runtime input/output-hash completeness и не закрытие всего milestone.

Источник: `.planning/phases/1205.1-canonical-status-gh-publish-closure/1205.1-CLOSEOUT.md`, `spec/EVIDENCE-CONTRACT.md`.

Связи: [[knowledge/debugging/Typed non-verdicts can become passed at the GH publication boundary]], [[sessions/2026-09-30 v12 audit and Phase 1205.1 canonical status closure]].
