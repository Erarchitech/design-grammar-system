---
phase: 1308-dg-web-ui
plan: "16"
subsystem: ui-v2-remaining-screens-i18n
tags: [i18n, react, llm-model, reasoner, api-docs, degram-grants, node-test]
requires:
  - phase: 1308-01
    provides: "settled ui-v2 working tree (lib/auth.js)"
  - phase: 1308-05
    provides: "i18n layer (t, tc, tp, describeError, formatDate, raw-text guard, swept-manifest format)"
provides:
  - "AiEngineScreen reads «LLM model» / «Модель LLM» (D-21); screen, provider form, key labels and connection-test results on t()/tp()/describeError"
  - "ReasonerScreen chrome, run states, relative times and plural unsatisfiable-class count on t()/tp(); reasoner names and descriptions stay server data"
  - "ApiDocsScreen chrome only (D-10); apidocs/content untouched"
  - "DegramGrantsPanel on t() with formatDate; the local ?lang=ru word table is gone"
  - "apiClient.js and lib/auth.js messages on t(), code/hint passthrough and storage unchanged"
  - "dict/screens.js RU dictionary (about 100 keys, 2 plural tables) and tests/i18n-swept/screens.json manifest (8 files)"
affects: [1308-22]
tech-stack:
  added: []
  patterns:
    - "error state holds the error object (or {err, kind} / {text}) and describeError runs at render, so text follows a live language switch"
    - "a module-level relative-time helper imports t directly (the guard only recognises the literal name t/tc/tp)"
    - "JSX ternary chains built outside the markup as plain branches when the raw-text guard reads ' : x ? ' as JSX text"
key-files:
  created:
    - ui-v2/tests/i18n-swept/screens.json
  modified:
    - ui-v2/src/screens/AiEngineScreen.jsx
    - ui-v2/src/screens/ReasonerScreen.jsx
    - ui-v2/src/screens/ApiDocsScreen.jsx
    - ui-v2/src/screens/DegramGrantsPanel.jsx
    - ui-v2/src/lib/apiClient.js
    - ui-v2/src/lib/auth.js
    - ui-v2/src/lib/llmApi.js
    - ui-v2/src/i18n/dict/screens.js
key-decisions:
  - "llmApi.js and reasonerApi.js build no user-facing message (they only call apiFetch), so they needed no t(); llmApi.js only had the old name in a comment, now «LLM model». Both stay in the manifest so the guard covers them"
  - "the API-docs «Name» column uses tc('parameter', 'Name') («Имя») and the grants input uses tc('grant', 'Name') («Название»): one English word, two Russian meanings"
  - "the grant-request defaults «DeGram access» and «Requested access» are payload data sent to the server (stored on the grant), not display text; they are allow-listed in screens.json rather than translated, so stored grants do not depend on the viewer's language"
  - "«Validation Graph» in the Reasoner note is rendered as «граф валидации» (the GH component name, not the ValidGraph layer label, which stays Latin per D-13)"
  - "AiEngineScreen keeps Latin provider names and the placeholder URLs untouched; API-key state and handling are not altered (T-1308-16-02)"
requirements-completed: []
duration: ~55 min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 16: LLM model, Reasoner, API docs, DeGram grants and lib messages i18n Summary

**The LLM model screen (D-21 rename), Reasoner, API docs chrome, DeGram grants panel and the apiClient/auth messages run through the i18n layer with an RU dictionary and a raw-text-guard manifest over all eight plan files; documentation content, reasoner names, provider/model names and user data stay as they are.**

## What was built

- **Task 1 (c8b6c42):** `AiEngineScreen` caption and title are `t("Region · LLM model")` / `t("LLM model.")`; provider form, key labels and hints, saved/configured badges, active-configuration summary and connection-test result (latency, `tp("{n} model available")`) are translated. Load, save and test errors are kept as error objects and rendered through `describeError`; a server-reported `testResult.error` string is shown as received. `ReasonerScreen`: header, loading/error states, screen note (split around the `<strong>` so the RU word order works), badges, every run state, `formatRelativeDate` now on `t()` («5 мин назад»), plural «{n} unsatisfiable class» through `tp`, run/save/load errors via `describeError`. `ApiDocsScreen`: back, region caption, title, parameter table headers, Yes/No, request/response example labels and the empty-state line; section/page titles, summaries and blocks are content and untouched (D-10).
- **Task 2 (cf1c89c):** `DegramGrantsPanel` drops its private `?lang=ru` word table and its `toLocaleDateString` helper (now `formatDate(iso, { dateStyle: "medium" })`); every label, placeholder, aria-label, confirm text and error goes through `t()`/`tc()`/`describeError`. `apiClient.js` fallback message and `auth.js` «Session could not be established» go through `t()`; `ApiError` code/hint passthrough, storage keys and `clearTenantBrowserData` are unchanged. `screens.json` lists all eight source files.

## Verification (real runs)

- `node --test ui-v2/tests/` (= `npm --prefix ui-v2 test`): 274 pass, 0 fail, after Task 1 and after Task 2 (includes key coverage in both directions, placeholder parity and the raw-text guard over `screens.json`).
- `npm --prefix ui-v2 run build`: succeeds after each task.
- `node ui-v2/tests/run-grants.mjs` and `node ui-v2/tests/run-grants.mjs host` (real React in headless Chrome, fake fetch): exit 0, 7 PASS, 0 FAIL in the normal run; the host run also exits 0.
- Acceptance greps: `grep -n "AI Engine" AiEngineScreen.jsx llmApi.js | grep -v "//"` prints nothing; no `toLocaleDateString` in `DegramGrantsPanel.jsx`; `screens.json` lists all eight files.
- Node check of plural forms in RU (1/3/5/21 for models, 1/3/5 for classes) and EN, plus «Раздел · Модель LLM», «Модель LLM.», «Проверено 5 мин назад».
- Not verified: rendering of the LLM model, Reasoner and API docs screens in a real browser (no render harness for them was written; the grants panel has the existing one), the live stack (no `design-grammars` rebuild), the Russian wording by a Russian reader (D-38 glossary is a draft; the prohibition on translating content is satisfied structurally and the judgment review stays with the RU visual pass), the live `#degram-lang` path. No mutation check was run by hand beyond what plan 05 recorded for the guard; the guard did catch a real false positive here (see Deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Raw-text guard false positive in DegramGrantsPanel**
- **Found during:** Task 2 verification
- **Issue:** the request-state ternary chain (`... </p> :\n hasRequest ? <p ...`) put `: hasRequest ?` between two tags, which the guard (written in plan 05) reads as JSX text.
- **Fix:** the three branches are built as a `requestForm` variable before the return; markup and behaviour are unchanged (run-grants 7/7 PASS).
- **Files modified:** `ui-v2/src/screens/DegramGrantsPanel.jsx`
- **Commit:** cf1c89c

**2. [Rule 3 - Blocking] `t` alias not recognised by the key-coverage test**
- **Found during:** Task 1 verification
- **Issue:** `import { t as tr }` in `ReasonerScreen.jsx` hid four relative-time keys from the "RU key never used" rule.
- **Fix:** import `t` by its own name for the module-level helper (the component's `useT()` destructuring shadows it inside the component).
- **Commit:** c8b6c42

**3. [Process] No separate RED tests**
- The plan names the guard and the key-coverage rules as the test. They were run after the edits, not before; no `test(...)` commit exists.

No other deviations. `llmApi.js`/`reasonerApi.js` needed no message translation (listed under key-decisions); `reasonerApi.js` is unmodified.

## Limitations

- `apiClient.js` and `auth.js` messages are fixed at throw time in the language of that moment (as in plan 12); the `ApiError` code mapping through `describeError` is the live path.
- `ConnectorsScreen.jsx` embeds `DegramGrantsPanel` and is not part of this plan; its own strings belong to plan 1308-14.
- Shared primitives rendered on these screens (`Button`, `Badge`, `Select`, `Input`, `CodeBlock`) carry no English defaults used here, but any such default in a primitive belongs to 1308-22.
- Relative time «{n}m ago» is computed once per render; it is not refreshed on a timer (unchanged from before).

## Known Stubs

None. No empty or placeholder data flows to the UI.

## Threat Flags

None. T-1308-16-01: all text goes through React text nodes and attributes, interpolation is plain replacement, no HTML injection API was added. T-1308-16-02: only labels and hints on the LLM model screen are translated; `apiKey` state, the password input, the save/test payloads and `llmApi.js` calls are unchanged. The prohibition on translating API-docs content, reasoner/provider/model names and user data holds structurally (content modules untouched, names rendered from data); it stays `unresolved` in the plan for the RU visual pass.

## Self-Check: PASSED

- Files exist: `ui-v2/tests/i18n-swept/screens.json`, `ui-v2/src/i18n/dict/screens.js`, the four screens and four lib files listed above.
- Commits exist: c8b6c42, cf1c89c.
