---
phase: 1308-dg-web-ui
plan: "05"
subsystem: ui-v2-i18n
tags: [i18n, react, host-signal, node-test]
requires:
  - phase: 1308-01
    provides: "settled ui-v2 working tree (ProjectsScreen/auth.js WIP committed)"
provides:
  - "ui-v2/src/i18n: t, tc, tp, translate, plural, resolveLang, initLang, getLang, setLang, subscribe, describeError, formatDate, formatTime, PROPER_NOUNS, OWNER_FIXED"
  - "LanguageProvider + useT (module store via useSyncExternalStore, works without the provider)"
  - "#degram-lang=ru|en host signal in parseHostSignal; App applies it live through setLang"
  - "dict/{core,errors,projects,landing,graph,model,connectors,screens}.js merged into RU, EN, AREAS"
  - "enums.js roleLabel / connectorStatusLabel / ROLE_VALUES"
  - "i18n.test.mjs: D-12 coverage rules and the raw-text guard reading tests/i18n-swept/*.json"
affects: [1308-10, 1308-11, 1308-12, 1308-14, 1308-15, 1308-16, 1308-21, 1308-22, 1308-23]
tech-stack:
  added: []
  patterns:
    - "English text is the key; area modules export { ru, en } where en holds only error.* texts and tp() plural tables"
    - "language state is module-level and only written by initLang/setLang; no storage, no control"
key-files:
  created:
    - ui-v2/src/i18n/index.js
    - ui-v2/src/i18n/enums.js
    - ui-v2/src/i18n/LanguageProvider.jsx
    - ui-v2/src/i18n/dict/index.js
    - ui-v2/src/i18n/dict/core.js
    - ui-v2/src/i18n/dict/errors.js
    - ui-v2/src/i18n/dict/projects.js
    - ui-v2/src/i18n/dict/landing.js
    - ui-v2/src/i18n/dict/graph.js
    - ui-v2/src/i18n/dict/model.js
    - ui-v2/src/i18n/dict/connectors.js
    - ui-v2/src/i18n/dict/screens.js
    - ui-v2/tests/i18n.test.mjs
  modified:
    - ui-v2/src/lib/hostMode.js
    - ui-v2/src/App.jsx
    - ui-v2/tests/host-degram.test.mjs
    - ui-v2/package.json
key-decisions:
  - "npm test is `cd .. && node --test ui-v2/tests/` (not the plan's `node --test tests/*.test.mjs`): the glob is not expanded by cmd on Windows with Node 20, and degram-boundary.test.mjs resolves ui-v2/src/... from the repo root"
  - "App.jsx default export became a thin wrapper (LanguageProvider around AppShell) so the provider sits at the app root without touching the rest of the component"
  - "OWNER_FIXED keys are exempt from the unused-RU-key rule until 1308-23 renders them in the landing"
  - "never_connected maps to its own key 'Never connected' / 'Не подключался' (the plan fixed only active and stale)"
requirements-completed: []
duration: ~50 min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 05: ui-v2 i18n layer Summary

**In-house EN/RU i18n for ui-v2 driven only from outside the page (DeGram live `#degram-lang` signal, `?lang=` at load, or the primary browser language), with error-code mapping, enum labels, a key-coverage test and a raw-text guard; no control and no storage in ui-v2.**

## What was built

- `index.js`: English-as-key `translate`/`t`/`tc`/`tp` with `Object.hasOwn` lookups (`toString`, `__proto__` stay literal), `{name}` plain-text interpolation, `Intl.PluralRules` for RU plurals, `resolveLang` (host: allowlisted `hostLang`, else `en`; outside host: first browser language starting with `ru`, else `en`; `["en-US","ru"]` gives `en`), `initLang` (optional injected env for tests), `setLang` (only `en`/`ru`, sets `<html lang>`, notifies subscribers, dispatches `dg-lang`, never persists), `describeError` (mapped `error.<CODE>`, else server text, else fallback), `formatDate`/`formatTime` (`Intl.DateTimeFormat`, dash for empty/invalid).
- `hostMode.js`: `parseHostSignal("#degram-lang=ru|en")` returns `{lang}` in host mode only; everything else (`de`, `RU`, trailing text) is `null`.
- `App.jsx`: `<LanguageProvider>` at the root; the existing `onHash` handler calls `setLang(signal.lang)` before `clearHostSignal()`, so a live signal beats `?lang=` and re-renders without reload.
- `dict/errors.js`: the 15 D-09 codes in EN and RU (UI-SPEC wording where given). Eight area modules merged by `dict/index.js` into frozen null-prototype `RU`/`EN` plus `AREAS`.
- `enums.js`: `roleLabel`, `connectorStatusLabel`, `ROLE_VALUES`; RU entries in `dict/core.js` (Наблюдатель, Редактор, Владелец, Вкл, Выкл).
- `tests/i18n.test.mjs` (27 tests): rules (a)-(f) and (h), owner strings verbatim, error-key parity, `describeError`, enums, dates, D-50 (no `LanguageBadge`, no `dgv2_lang`, no `EN | RU`, no storage in `src/i18n`), no new dependency, and the raw-text guard (JSX text, `title/placeholder/aria-label/label/alt`, sentence-like literals; `console.*` and import lines ignored; zero manifests passes) with unit tests of the guard itself.

## Verification (real runs)

- `node --test ui-v2/tests/i18n.test.mjs ui-v2/tests/host-degram.test.mjs`: 34 pass, 0 fail.
- `npm --prefix ui-v2 test`: 259 pass, 0 fail (whole tests directory).
- `npm --prefix ui-v2 run build`: succeeds.
- Mutation checks run by hand and reverted: a bogus/unused RU key, a placeholder mismatch, `t(variable)`, an unmapped literal key and a conflicting RU value across modules each made the matching test fail.
- Acceptance greps: three owner strings found in `dict/core.js`; `degram-lang` in `hostMode.js`; `setLang(`/`LanguageProvider` in `App.jsx`; no `localStorage` under `src/i18n`; `grep -c '"error\.' errors.js` = 30; `package.json` diff touches only `scripts`; `lib/auth.js` untouched.
- Not verified: the live DeGram-to-page signal (the sender is plan 1308-21 in the component repo) and rendering in a real browser. `LanguageProvider.jsx`/`App.jsx` are verified by build and source-pattern tests only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `npm test` script form**
- **Found during:** Task 1 verification
- **Issue:** `node --test tests/*.test.mjs` failed under npm on Windows ("Could not find ...*.test.mjs"; Node 20 has no glob expansion in cmd). The directory form `node --test tests/` run from `ui-v2` fails `degram-boundary.test.mjs`, which resolves `ui-v2/src/degram/...` relative to the repo root.
- **Fix:** script is `cd .. && node --test ui-v2/tests/`. It runs the whole directory (259 pass). The directory argument is Node 20 behaviour; newer Node majors treat it differently, so revisit if the Node version is bumped.
- **Files modified:** `ui-v2/package.json` (scripts block only)
- **Commit:** eede8e0

**2. [Process] Tests written alongside the implementation, not strictly RED first**
- The Task 1 tests were run after the implementation existed, so no recorded failing-first run. Compensated by the mutation checks listed above for Task 2 rules; the Task 1 behaviours are asserted by 19 passing tests. No separate `test(...)` commit exists (TDD gate warning).

No other deviations. `ui-v2/src/i18n/index.js` was not modified in Task 2 (describeError, dates and PROPER_NOUNS were already written in Task 1 and committed there).

## Known Stubs

None that block the plan goal. Area dictionaries `projects`, `landing`, `graph`, `model`, `connectors`, `screens` are intentionally empty (`ru = {}`, `en = {}`); they are filled by plans 1308-10/11/12/14/15/16/22/23. `tests/i18n-swept/` has no manifest yet (first one is written by 1308-23), so the raw-text guard currently passes vacuously.

## Threat Flags

None. T-1308-05-01..04 mitigations are implemented: closed vocabulary in `resolveLang`/`setLang`/`parseHostSignal`, host signal honoured in host mode only, plain-text interpolation with no HTML injection API, `Object.hasOwn` lookups, `#degram-lang` changes only the display language.

## Self-Check: PASSED

- Files exist: `ui-v2/src/i18n/index.js`, `enums.js`, `LanguageProvider.jsx`, `dict/index.js`, `dict/core.js`, `dict/errors.js`, the six empty area modules, `ui-v2/tests/i18n.test.mjs`.
- Commits exist: `eede8e0` (Task 1), `b91176f` (Task 2).
