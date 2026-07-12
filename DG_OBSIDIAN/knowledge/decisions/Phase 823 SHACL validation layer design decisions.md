---
tags: [decision, shacl, phase-823, v8.2]
date: 2026-07-12
status: resolved
---

# Phase 823: SHACL Validation Layer — Design Decisions

## D-823-01: Canonical envelope контракт

**Решение:** `/shacl/validate` success body возвращает строго:
- `conforms`: boolean | null (null только при timeout)
- `results`: array of finding objects (пустой массив = conforms). Ключ `results` — сохраняет 821 backward-compat contract
- `counts`: `{ "violation": <int>, "warning": <int>, "info": <int> }`

Каждый finding:
- `severity`: `"violation" | "warning" | "info"`
- `what`: plain-language описание (из `sh:message`)
- `where`: human location (focusLabel + property path)
- `howToFix`: remediation (из `dgsh:howToFix`)
- `focusLabel`: human label focus node
- `shapeId`: local-name shape (internal — UI не рендерит)

**Почему:** Единый контракт для всех слоёв — data-service (823-03), Grasshopper (823-05), UI (823-06).

**Связано:** [[sessions/2026-07-12 Phase 823 SHACL Validation Layer execution]]

## D-823-02: Non-fatal SHACL sidecar proxy в publish path

**Решение:** `_call_shacl_validate` обёрнут в `try/except` так, что HTTP 504/timeout/unavailable никогда не роняют publish response (200). SHACL findings — дополнительная информация к основному publish, не блокирующий шаг.

**Почему:** Публикация результата валидации в Speckle и Neo4j — основной path. SHACL — необязательный сопутствующий анализ.

## D-823-03: UI state gating на `results.length`, не на `conforms`

**Решение:** Четыре состояния SHACL Data Integrity panel:
1. Not checked — `shaclReport === null` (pre-823 runs)
2. Not evaluated — `shaclReport.status === "unavailable" | "timeout"`
3. Conforms — `results.length === 0` (neutral, без цвета)
4. Findings — `results.length > 0`

**Почему:** `conforms == true` возможен при наличии Info/Warning findings (allow_infos/warnings). Gating на `results.length` точнее.

## D-823-04: Data-integrity shapes только, без бизнес-правил

**Решение:** `ontology/dg-shapes.ttl` содержит только data-integrity NodeShapes: DesignState-kind membership, PropState completeness, Run status, ObjState objectRef, Var name, Rule structural. Ни одного quantitative geometry/parameter правила (partition policy D-08/D-12).

**Почему:** Архитектурное разделение — SHACL для data-integrity (формальные RDF ограничения), SWRL для бизнес-правил (количественные проверки).

## D-823-05: `shaclReportJson` сохраняется на ValidationRun additively

**Решение:** `_persist_shacl_report` использует `MERGE/SET`, не `CREATE`. Запускается строго после `store_validation_run`, добавление к существующей записи. `shaclReportJson` строковое JSON-поле на ноде `ValidationRun`.

**Почему:** Data-integrity не должна перезаписывать или конфликтовать с основным validation run.

## D-823-06: SHACL severity color tokens расширяют DSYS токены

**Решение:** Новые цветовые тока:
- `--color-warning` (оранжевый, dark: warm orange)
- `--color-warning-ink` / `--color-warning-soft`
- `--color-info` (голубой, dark: sky blue)
- `--color-info-ink` / `--color-info-soft`
- `--color-warning-tint` / `--color-info-tint` (transparent halos)

Severity → цвет: violation → red, warning → orange, info → нейтральный/голубой.

**Почему:** Единая система для всех SHACL severity в UI. Badge/Collapsible severity variants используют те же токены.

## D-823-07: Timeout budget согласован между proxy и sidecar

**Решение (applied post-review, WR-01):** `DG_SHACL_HTTP_TIMEOUT_SECONDS` в data-service должна превышать `DG_REASONER_TIMEOUT_SECONDS` (внутренний таймаут dg-reasoner) с запасом — аналогично `/reason/consistency` proxy.

**Почему:** 15s HTTP read timeout vs 90s SHACL subprocess timeout даёт false timeout на медленных, но успешных валидациях. Воспроизводит уже исправленный паттерн в `/reason/consistency`.

## D-823-08: `validStatus` truthy check — confirmed regression (CR-01)

**Решение (исправление pending):** `valid_graph_export._mint_run_individual` должен использовать `is not None` вместо truthy check для `validStatus`, чтобы пустой список `[]` (ноль ObjStates — поддерживаемый сценарий) не трактовался как отсутствие и не вызывал false-positive SHACL Violation.

**Почему:** `ValidatorComponent.cs` поддерживает zero ObjStates. Truthy check уже исправлен для соседнего `sendStatus`, но не для `validStatus`.

**Статус:** Задокументирован, исправление pending в баг-трекинге.
