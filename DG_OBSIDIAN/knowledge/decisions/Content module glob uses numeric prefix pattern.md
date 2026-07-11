---
tags: [decision, phase-815, content-architecture]
date: 2026-07-11
status: locked
---

# Content module glob uses numeric prefix pattern

**Контекст:** Content-модули для DG API Documentation viewer должны авто-регистрироваться в viewer без изменений кода. Используем Vite `import.meta.glob` для discovery.

**Решение:** Файлы именуются `NN-slug.js` (где `NN` = двухзначный числовой префикс 01–99), а glob pattern — `./[0-9][0-9]-*.js`. Сортировка производится по числовому префиксу, извлечённому из имени файла.

**Почему не `##-*.js`:** Символ `#` в picomatch/Vite — literal, не wildcard. Паттерн `##-*.js` не находит файлы. Это было обнаружено code review Phase 815.

**Почему не `index.js` exclude pattern:** Чистый glob `./*.js` включил бы `index.js`, хотя `.filter()` мог бы исключить его по `mod.default.id`. Но явный числовой pattern безопаснее и самодокументируем.

**How to apply:** Когда добавляешь новый раздел документации, создай `NN-slug.js` в `ui-v2/src/screens/apidocs/content/`. Выбери `NN` так, чтобы он встал в желаемом порядке между существующими разделами. Никаких изменений в viewer — только новый файл.
