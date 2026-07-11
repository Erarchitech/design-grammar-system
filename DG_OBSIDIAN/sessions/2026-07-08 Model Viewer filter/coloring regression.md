---
tags: [session]
date: 2026-07-08
---

# Model Viewer filter/coloring regression

сессия: Model Viewer filter/coloring regression — fail/pass/base toggles and colours not applying after v8.0 SpeckleViewport rewrite

## Информация о сессии
- Модель: deepseek-v4-flash
- Дата: 2026-07-08
- Изменено файлов: 1

## Изменённые файлы
- `ui-v2/src/components/speckle/SpeckleViewport.jsx` (commit `34f26dd`)

## Результаты
- **Commit 34f26dd**: single visibility operation per update — refactored FilteringExtension calls to resolve toggles to exactly ONE hide/isolate call. All-off now correctly hides the scene via a sentinel isolate. Hide-button picks excluded from raw renderer.setMaterial overrides.
- **UAT failed**: User reports fail/pass/base toggles still do nothing, colours don't apply.
- **Root cause (hypothesis)**: `collectValidationObjects()` walks the Speckle world tree looking for nodes with `dgEntityId` + `validationRunId` + `dgProject` in their raw payload. If these properties are absent from the Speckle objects (published via data-service without entity-ID tags), the entityMap stays empty → filtering/coloring operations receive zero object IDs → no-op. The legacy viewer had the same code but may have received different Speckle data, or may have used a different endpoint.
- **Blocked**: User will continue investigation in a separate session. See [[debugging/Model Viewer validation objects not found in Speckle world tree|debugging note]].
