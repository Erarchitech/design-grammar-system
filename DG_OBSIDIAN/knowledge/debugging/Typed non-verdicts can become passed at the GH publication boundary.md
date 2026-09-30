---
tags: [debugging, csharp, python, validation, json]
date: 2026-09-30
phase: "1205.1"
status: resolved
---

# Typed non-verdicts can become passed at the GH publication boundary

## Симптом и причина

Milestone audit обнаружил `Unsupported → passed`, несмотря на зеленые evaluator tests. Evaluator сохранял rule Status, но терял per-binding outcomes. Package builder выводил entity pass из отсутствия binding в FailingBindings; GH DTO передавал только legacy lists; backend восстанавливал passed из passedRuleIds.

## Исправление

Сохранены identity-bearing binding outcomes до rollup, добавлены exact-pair canonical map и явный production GH transport. Реальный RED через GH mapper/DTO/JsonOptions → authorized publish → actual persistence capture → view → C# reader стал GREEN. Сохранены разные результаты объектов одного правила и отдельные zero-row rule outcomes.

## Независимые проверки нашли второй класс дефектов

Green dict-based tests не проверяли raw JSON:
- duplicate members терялись при decode (last-wins), включая version discriminator;
- syntactically valid deep input проходил decoder и падал позже;
- NaN/Infinity/overflow ломали JSONResponse; tuple-nested nonfinite до dump превращались в null;
- lone Unicode surrogate ломал Python response/C# lazy string decode;
- Python/schema и C# расходились на integral numeric lexemes, диапазонах, final-LF hash и depth.

Общий bounded guard теперь проверяет raw uniqueness, finite binary64, depth 128, корректный Unicode keys/values и closed in-memory container domain до coercion. Strict admission согласован между языками; duplicate array-row collision policy сохранена. Unsupported containers отвергаются явно; finite list/tuple поддержаны. Deep Any tuples могут безопасно выдавать ValueError из-за собственного предела Pydantic serializer.

## Уроки

Проверять реальную границу сериализации, а не копию mapper или только rule-level результат. Для duplicate-key/encoding случаев использовать raw bytes, для silent coercion — входы до JSON-mode dump. HTTP 200 не доказывает сохранение sidecar: нужны capture-hit, view-readback и совпадение bytes. Неизменность исторических артефактов проверять отдельно от параллельно записываемых отчетов.

## Доказательства

`1205.1-VERIFICATION-3.md`: 11/11; `1205.1-REVIEW-3.md`: clean. Файлы в `.planning/phases/1205.1-canonical-status-gh-publish-closure/`; предыдущие failed reports сохранены в `evidence/verification-history/` и round-specific reports.

Связи: [[knowledge/decisions/Evidence v2 preserves rule outcomes and keeps legacy projections separate]], [[sessions/2026-09-30 v12 audit and Phase 1205.1 canonical status closure]].
