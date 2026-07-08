---
tags: [session, audit-fix, model-viewer, validation]
date: 2026-07-08
---

# 2026-07-08: Audit-fix — Model Viewer geometry regression (F-01, F-02, F-03)

Сессия: Диагностика и исправление регрессии Model Viewer v8.0 — fail/pass/base toggleы и colours не работают. Root cause: `DesignStateBindingService` выбросил `ObjState.Geometry` при построении `ElementRef`, поэтому все v7.0+ publishes отправили `displayValue: []`. Спектр validation элементы имели правильные теги, но нулевую геометрию → world tree не имел renderable nodes → hide/isolate/color no-ops. **RESOLVED.**

## Информация о сессии
- Модель: Claude Fable 5
- Дата: 2026-07-08
- Изменено файлов: 5 (2 исправлены, 2 созданы, 1 обновлена в vault)

## Изменённые файлы
- `DG/src/DG.Core/Services/DesignStateBindingService.cs` — добавлен `Geometry = objState.Geometry` в ElementRef
- `DG/tests/DG.Tests/DesignStateBindingServiceTests.cs` — регрессионный тест (F-01)
- `ui-v2/src/components/speckle/SpeckleViewport.jsx` — восстановлены [DG-Debug] логи + окно.__dgSpeckleDebug (F-03)
- `test/publish_validation_run_with_geometry.py` — fixture для E2E-тестирования с реальной геометрией (F-02)
- `DG_OBSIDIAN/knowledge/debugging/Model Viewer validation objects not found in Speckle world tree.md` — обновлена с разрешением

## Результаты

### F-01: ElementRef drops ObjState.Geometry
**Fix:** [commit 0b15ce0](commit 0b15ce0)
- `DesignStateBindingService.CreateBindings()` теперь копирует `objState.Geometry` в `ElementRef`
- Добавлен регрессионный тест: `BuildBindings_ElementRefCarriesObjStateGeometry()`
- 216/216 non-E2E тестов pass (3 E2E failures pre-existing и flaky)
- Требуется пересборка GH-плагина (`.sln` builds clean in Release)

### F-02: Live dataset untestable
**Fixture added:** [commit 88ca…](test/publish_validation_run_with_geometry.py)
- `test/publish_validation_run_with_geometry.py` — публикует 3×3 grid зданий (4 failing / 5 passing)
- Запускается: `python test/publish_validation_run_with_geometry.py`
- Результат: Run `e7839df0…` в project `v8-ui-smoke` с полной геометрией (9 entities / 18 objectIds)

### F-03: Legacy diagnostics lost
**Restored:** [commit dbbb062](commit dbbb062)
- `[DG-Debug]` логирование воссоздано в `SpeckleViewport.jsx`
- Добавлено `window.__dgSpeckleDebug` для live world-tree inspection
- Логи включают: node sampling, per-search match counts, entityMap summary

## Верификация (Live, в продакшене)
Протестировано в Model Viewer на `v8-ui-smoke` (run `e7839df0…`):

✅ World-tree entity mapping: **9/9** entities matched on strict search (было 0)
✅ "Failing" toggle off: hides ровно **8** object IDs
✅ "Base model" toggle off: isolates **18** validation objects
✅ All three toggles off: sentinel isolate — сцена полностью скрыта
✅ Toggles restored: чистое состояние, всё видно
✅ Select by Id + Isolate: isolates obj_1's 2 objects
✅ Hide + Show all: скрывает 2, восстанавливает cleanly
✅ Fail/pass coloring + opacity: red 85% на failing, grey 55% на passing

## Действия для пользователя
1. **Пересобрать GH-плагин:**
   ```bash
   dotnet build ./DG/DG.sln -c Release
   ```
   Результат: `DG/src/DG.Grasshopper/bin/Release/DG.Grasshopper.dll`
   
2. **Установить DLL в Grasshopper:**
   - Close Rhino
   - Copy DLL → `%appdata%\Grasshopper\Libraries\`
   - Restart Rhino

3. **Перепубликовать runs из Grasshopper:**
   - Откройте `.gh` с VALIDATION GRAPH компонентом
   - Перезапустите VALIDATOR
   - Новые runs будут иметь геометрию

## Известные ограничения
- Все **14 существующих runs** в v8-ui-smoke опубликованы ДО этого fix → нет геометрии → останутся серыми
- Только новые runs (после пересборки плагина) будут иметь цвета и toggleability
- Старые runs можно игнорировать для UAT; используйте run `e7839df0…` (создана в этой сессии) как reference

---

**Status:** ✅ Resolved and verified. User approved all checks.
