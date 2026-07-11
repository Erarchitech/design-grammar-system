---
tags: [debugging, phase-815, code-review]
date: 2026-07-11
status: resolved
---

# Glob pattern ##-*.js matched zero content modules

**Симптом:** Code review (CR-01) обнаружил, что `import.meta.glob("./##-*.js", { eager: true })` в `index.js` не находит ни одного файла. Все 7 content-модулей используют числовые префиксы (`01-getting-started.js`, `02-authentication.js`, и т.д.), а символ `#` в picomatch/Vite — не спецсимвол, а literal.

**Последствие:** Документационный браузер рендерится, но дерево навигации пустое (`sections = []`), пользователь видит "Select a page from the tree."

**Причина:** В шаблоне `##-*.js` решено было документировать naming convention с плейсхолдером `##-`, но glob pattern должен был быть `[0-9][0-9]-*.js`. В момент написания кода не заметили несовпадение паттерна и реальных имён файлов.

**Фикс (commit `f2e2a53`):**
- `index.js:6`: `./##-*.js` → `./[0-9][0-9]-*.js`
- `07-extending.js`: обновлена документация naming convention

**Предотвращение рецидива:** Code review в GSD catch-этапе автоматически проверил код и выявил проблему до того, как она попала в production билд. Build `npm run build` проходит, но не сигналит о пустом glob — только инспекция содержимого bundle через `grep` обнаружила отсутствие content module ID. Возможное улучшение: добавить тест, проверяющий что `sections.length > 0`.

**Why:** The developer (or in this case AI executor) chose `##-` as a placeholder convention in the glob pattern, but Vite's glob engine treats `#` literally — not as a wildcard. The actual files used numeric `01-` prefixes. This is a classic "convention vs. implementation mismatch" bug.

**How to apply:** When using `import.meta.glob` with numbered file prefixes, always use `[0-9][0-9]-*.js` pattern, not placeholder characters. Self-documentation files must match actual conventions.
