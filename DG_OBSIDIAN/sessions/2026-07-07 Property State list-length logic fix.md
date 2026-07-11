---
tags: [session]
date: 2026-07-07
---

# Session: Property State / Design State list-length logic fix

## Информация о сессии
- **Команда:** `/gsd-audit-fix` — корректировка логики Property State, Object State и Design State компонентов
- **Модель:** deepseek-v4-pro
- **Дата:** 2026-07-07
- **Изменено файлов:** 5

## Задача
Исправить логику работы трёх компонентов:

1. **Property State** — список длин входов не обязан быть равным. Размер выхода PropState должен соответствовать длине входа "PropValue". Размер выхода ObjState должен соответствовать длине входов "Geometry" и "Label". Вход "Class" удалён — class IRI читается из входа "Object" (OntologyClass из METAGRAPH Objects).
2. **Object State** — убрать "Class" input. Class IRI извлекается из Object при наличии OntologyClass. Выход управляется Geometry+Label (должны быть равны); Object может различаться.
3. **Design State** — добавлена проверка: если присутствуют ObjState и PropState, их длины должны совпадать.

## Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` | Удалён Class input, ClassIri извлекается из Object (OntologyClass), выход управляется Geometry+Label |
| `DG/src/DG.Grasshopper/Components/PropertyStateComponent.cs` | Убран guard равных длин, выход управляется PropValue, Rule/DataProperty — по индексу |
| `DG/src/DG.Grasshopper/Components/DesignStateCompositionComponent.cs` | Добавлена кросс-индексная проверка ObjState vs PropState counts |
| `DG/src/DG.Core/Services/ErrorMessageTemplates.cs` | Обновлены сообщения ошибок (2-param Geometry/Label, новый DesignStatePropObjCountMismatch, удалён PropStateMismatchedListLengths) |
| `DG/src/DG.Grasshopper/Components/GhCastingHelpers.cs` | Сохранение ClassIri при TryObjState public→core конвертации |

## Коммит
```
873ebf7 fix(grasshopper): adjust Property State, Object State, and Design State list-length logic
```

Build: 0/0 | Tests: 211/211 pass

## Результаты
- [x] ObjectStateComponent: CIRLASS input удалён, ClassIri извлекается из Object
- [x] PropertyStateComponent: guard равных длин снят, выход управляется PropValue
- [x] DesignStateCompositionComponent: кросс-проверка ObjState vs PropState count
- [x] ErrorMessageTemplates: обновлены/добавлены сообщения
- [x] GhCastingHelpers: ClassIri не теряется при конвертации
- [x] Build: 0/0, Tests: 211/211
