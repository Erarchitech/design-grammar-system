---
date: 2026-07-04
phase: 16
tags: [session, discuss, v7.0, state-models]
---

# Phase 16 discuss — DG.Core State Models and State Components

**Фаза:** 16 — DG.Core State Models and State Components
**Команда:** `/gsd-discuss-phase 16`
**Результат:** `16-CONTEXT.md` + `16-DISCUSSION-LOG.md` записаны

## Обсуждённые области

### 1. DESIGN STATE — Composition Semantics
**Решение:** Aggregate model. Один DesignState = все ObjState + ParamState + PropState в одном снимке (snapshot). Три входа — независимые наборы (independent bags), без кросс-индексного выравнивания. VALIDATOR (Phase 18) парсит каждый список отдельно под конкретное SWRL-правило.

**Index-mismatch guard** живёт в leaf-компонентах: OBJECT STATE проверяет Object/Geometry/Label на одинаковую длину; PROPERTY STATE проверяет свои параллельные списки значений. DESIGN STATE не имеет кросс-входного правила длины — ObjState и PropState не выровнены по индексу, так как много правил могут применяться к одному объекту, а property value живёт внутри одного PropState, привязанного к конкретному Rule.

**DesignState.StateId** = детерминированный хеш (SHA-256, 16 hex-символов, DS_-префикс) отсортированных member StateIds. Одинаковые члены → одинаковый DesignState → dedup через MERGE по StateId+project (D-03 Phase 13).

### 2. statePayloadJson v2 — Serialization Contract
**Решение:** Версионированный конверт с явным `"version": "2"`, чиcтый разрыв с v1 (без обратной десериализации v1 payloads). Pre-v7.0 run read-side tolerance — забота Phase 18 (GHVL-06).

```json
{
  "version": "2",
  "stateId": "DS_<hex16>",
  "capturedAtUtc": "<ISO 8601 round-trip>",
  "objStates": [ ... ],
  "paramStates": [ ... ],
  "propStates": [ ... ]
}
```

### 3. PropState — Value Model
**Решение:**
- **PropValue** = типизированный Number/Integer/Boolean scalar (та же модель, что DesignStateParameter)
- **Rule/DataProperty** = plain string refs (IRIs: `dgm:Rule_...`, `dg:hasHeight`)
- **PropState rule-scoped** — один PROPERTY STATE компонент = один Rule + один DataProperty + одно значение → один PropState
- **StateId** = `PS_` + SHA-256 хеш (Rule IRI + DataProperty IRI + PropValue) через новый метод `ComputePropStateId()` в `DesignStateIdGenerator`

### 4. Scaffolding Removal & Component Rename
**Решение:**
- **Удалить** `DefState.cs`, `ObjectState.cs`, `ObjectInstance.cs` — unused v3.0 scaffolding
- **DESIGN STATE → PARAMETER STATE** сейчас (новый GUID). Старые canvases ломаются — v7.0 breaking-change milestone
- **DesignStateSnapshot → ParamState** model rename. `DesignStateParameter` остаётся без изменений
- **DesignStateIdGenerator адаптирован:** `ComputeDefStateId` → `ComputeParamStateId` (та же логика, DS_ префикс); добавлен `ComputePropStateId` (PS_ префикс); `ComputeObjectStateId` без изменений (OS_)

## Зона discretion Claude
- Точный per-entity field mapping внутри v2 envelope
- Новый класс `DesignStatePayloadSerializer` vs rework `DesignStateJsonSerializer`
- Формулировки error messages для index-mismatch guards
- Судьба OI_ префикса (удалить с ObjectInstance или оставить зарезервированным)
- Порядок внутренних списков в DesignState модели

## Следующий шаг
`/gsd-plan-phase 16` — создать план фазы с 15 зафиксированными решениями
