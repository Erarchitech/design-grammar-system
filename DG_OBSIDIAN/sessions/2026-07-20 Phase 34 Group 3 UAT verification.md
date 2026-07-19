---
session_date: 2026-07-20
phase: 34-ontology-tagging-components
group: Group 3 (Tag guard-rails & undo)
status: complete
---

# Phase 34 Group 3 UAT Verification Session

## Сессия
Завершена верификация UAT для Group 3 (v9.0-PIPELINE-UAT): тестирование DG ENTITY TAG компонента с охватом guard-rails, undo, nesting и эстетики.

## Информация о сессии
- Модель: Claude Haiku 4.5 / Sonnet 5
- Дата: 2026-07-20
- Изменено файлов: 1

## Изменённые файлы
- .planning/phases/34-ontology-tagging-components/34-UAT.md

## Результаты

### Тесты (все пройдены)
1. **3.1 Guard rails** (2/2 subtests)
   - Empty selection → Warning "No objects selected", no group created ✓
   - Reserved infix name (`Foo_Var_Bar`) → Warning, no group created ✓
   - Note: ProcIndex input has no `Optional` flag; unwired ProcIndex shows GH's own "failed to collect data" error first — expected, not a component bug

2. **3.2 Undo & nesting** (3/3 subtests)
   - Create pink `11_Var_SpansCount` group, Ctrl+Z removes cleanly ✓
   - Tag inside existing `11_Pat_*` → purple nested group with correct HostPatternId ✓
   - Re-tag same core selection with label-only change → existing group updated in place, nested child stays nested ✓

3. **3.3 Aesthetic pass** (3/3 subtests)
   - ObjectMarker24 / EntityTag24 icons: currently reuse icons from other components (deferred adjustment by user, no functional risk)
   - CanvasAnnotationStyles palette: confirmed correct (Proc near-white, Pattern orange, NestedPattern purple, Parameter pink, Interface near-white) ✓
   - preview_structure desaturated [?] style: confirmed ✓

### Known gap (documented, deferred)
**Partial-reselection re-tag edge case:** If user drops one member from the reselection when re-tagging a Pattern group, component creates a **new nested duplicate group inside the original** instead of updating or warning. Root cause: exact set-match predicate in EntityTagComponent.cs:246-263 + no exclusion of stale hosts when lookup misses. Documented in 34-UAT.md Gaps section; decision needed later (warn vs. tolerate+confirm).

## Summary
- All 3 Group 3 tests marked **pass**
- Tests 3/4/5 in 34-UAT.md now reflect verified results + detailed gap documentation
- Ready for Group 4 (E2E spine: recognition, preview, accept, publish) in next session

## Ссылки
- Test results: .planning/phases/34-ontology-tagging-components/34-UAT.md
- Component source: DG/src/DG.Grasshopper/Components/EntityTagComponent.cs
- Pipeline plan: .planning/phases/v9.0-PIPELINE-UAT.md (Group 3 section)
