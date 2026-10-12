---
phase: 1308-dg-web-ui
plan: "23"
subsystem: ui-v2-landing-i18n
tags: [i18n, landing, react, canvas, node-test, host-signal]

requires:
  - phase: 1308-05
    provides: "ui-v2/src/i18n (t, useT, describeError, setLang, dg-lang event), dict/core.js owner-fixed strings, raw-text guard reading tests/i18n-swept/*.json"
provides:
  - "Bilingual landing: hero (D-03 owner strings), boot line, region labels with AI Engine renamed to LLM model (D-21), hint, auth card, sign-in errors, HostCentre pill and connecting label"
  - "landingEngine relayout on the window event dg-lang (D-52), listener and pending frame removed in stop()"
  - "ui-v2/tests/i18n-swept/core.json: first coverage manifest (eight core files)"
  - "ui-v2/tests/landing-i18n.test.mjs: source-pattern tests for the dg-lang listener lifecycle, keyed landing strings, no language control"
affects: [1308-24]

tech-stack:
  added: []
  patterns:
    - "Components that must follow a live switch call useT() (the provider alone does not rerender its children)"
    - "Client-side error messages are stored as a code and translated at render (authMessage), server errors as the error object mapped by describeError"

key-files:
  created:
    - ui-v2/tests/i18n-swept/core.json
    - ui-v2/tests/landing-i18n.test.mjs
  modified:
    - ui-v2/src/landing/LandingLayer.jsx
    - ui-v2/src/landing/HostCentre.jsx
    - ui-v2/src/landing/landingEngine.js
    - ui-v2/src/i18n/dict/core.js
    - ui-v2/tests/host-centre.browser.jsx

key-decisions:
  - "Relayout runs one animation frame after dg-lang: setLang notifies React subscribers first and dispatches dg-lang synchronously, so the new text is not in the DOM yet when the event fires"
  - "RU entries live in dict/core.js as the plan says (not dict/landing.js); landing.js stays empty"
  - "Auth error state holds {key} or {err} instead of a pre-translated string, so a live switch retranslates a visible error"
  - "core.json allow list holds only the three OWNER_FIXED literals in i18n/index.js"

patterns-established:
  - "authMessage(t, e): switch over error codes with literal t() calls (keeps coverage rule d: keys are literals)"

requirements-completed: []

coverage:
  - id: D1
    description: "Landing hero, boot line, region labels, hint, auth card and errors render through t(); owner-fixed RU strings shown under RU"
    requirement: "WEBUI-02"
    verification:
      - kind: unit
        ref: "ui-v2/tests/landing-i18n.test.mjs, ui-v2/tests/i18n.test.mjs"
        status: pass
      - kind: integration
        ref: "ui-v2/tests/run-host-centre.mjs (headless Chrome, ?host=degram&lang=ru, two viewports)"
        status: pass
    human_judgment: false
  - id: D2
    description: "landingEngine re-measures labels on dg-lang and removes the listener on teardown (D-52, T-1308-23-02)"
    requirement: "WEBUI-01"
    verification:
      - kind: unit
        ref: "ui-v2/tests/landing-i18n.test.mjs (source-pattern)"
        status: pass
    human_judgment: true
  - id: D3
    description: "core.json lists the eight core files and the raw-text guard reports zero findings"
    requirement: "WEBUI-02"
    verification:
      - kind: unit
        ref: "ui-v2/tests/i18n.test.mjs raw-text guard test"
        status: pass
    human_judgment: false
status: complete
---

# Phase 1308 Plan 23: Bilingual landing Summary

**The landing layer reads through the 1308-05 i18n layer (hero and boot line with the owner-fixed RU strings, region labels with «Модель LLM», auth card with code-based error messages), relayouts on a live `dg-lang` switch, and is the first area guarded by a coverage manifest.**

## What was built

- `LandingLayer.jsx`: `useT()`; hero title and subtitle, «System initiated ·», project fallback, sign-in/sign-out, the whole auth card (titles, field placeholders, buttons, mode switches, Cancel) and all seven region labels plus the hint go through `t()`. `AI Engine` is now `t("LLM model")`. Auth messages are stored as `{ key }` or `{ err }` and turned into text by `authMessage` at render, using `describeError` for server errors; user and project names stay data. No language control was added.
- `landingEngine.js`: `start()` registers a `dg-lang` window listener that schedules `relayout()` (`layoutLanding` + `layoutHero`) one frame later; `stop()` removes the listener and cancels the pending frame. The engine draws no UI text on the canvas (labels are DOM), so nothing else needed translating there.
- `HostCentre.jsx`: the `hostLang() === "ru"` branches became `t("Start new session")` and `t("Connecting to DG")`.
- `dict/core.js`: RU entries for all landing keys, wording from the 1301-D38 glossary and the UI-SPEC copy tables; owner-fixed entries unchanged.
- `tests/i18n-swept/core.json`: `LanguageProvider.jsx`, `index.js`, `enums.js`, `hostMode.js`, `LandingLayer.jsx`, `HostCentre.jsx`, `landingEngine.js`, `main.jsx`; `allow` holds only the three OWNER_FIXED literals that `i18n/index.js` must contain.

## Verification (real runs)

- RED: `node --test ui-v2/tests/landing-i18n.test.mjs` before the implementation: 3 fail, 1 pass.
- `node --test ui-v2/tests/i18n.test.mjs ui-v2/tests/landing-i18n.test.mjs`: 31 pass, 0 fail (after Task 1).
- `npm --prefix ui-v2 test`: 263 pass, 0 fail, including the raw-text guard over core.json.
- `npm --prefix ui-v2 run build`: succeeds.
- `node ui-v2/tests/run-host-centre.mjs`: all PASS at 1278x799 and 898x699, exit 0 (12 PASS lines over both viewports).
- `node ui-v2/tests/run-degram.mjs` (DeGram workspace harness, unaffected area): exit 0, 22 PASS.
- Acceptance greps: no `AI Engine` in LandingLayer.jsx; `t("LLM model")` present; `dg-lang` on 2 lines of landingEngine.js (add and remove).

Not verified: the live relayout in a real browser (the listener lifecycle is asserted by source pattern, the one-frame deferral is reasoned from `setLang` ordering, not observed); the RU visual pass of the landing (Michroma/Cyrillic fallback, label widths, the long RU sign-up hint inside the card) and the prohibition review "do not translate user/project names" remain a human judgment step. The live DeGram `#degram-lang` signal itself is sent by plan 1308-21.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] host-centre harness asserted English landing text**
- **Found during:** Task 2 verification (`run-host-centre.mjs`)
- **Issue:** The harness runs with `?host=degram&lang=ru`; with the landing now Russian, `System initiated`, `Projects.` and the leftover `Access` probe (it matched the always-mounted, hidden auth-card title) no longer exist, and the English-label case relied on `hostLang()` being read per render, while the language is now a module store.
- **Fix:** assert `Система инициализирована`, `Грамматика.`, `Граф правил проекта.`, label `Проекты.`, the `Доступ` probe, and call `setLang('en')` before the English HostCentre case.
- **Files modified:** `ui-v2/tests/host-centre.browser.jsx`
- **Commit:** 823c17f
- Note: the `Доступ` probe is as weak as the old `Access` one (it is satisfied by the hidden auth card, not by the Connectors screen); the harness' final `!queue.length` check is what proves the Connectors fetches ran. Left as it was.

**2. [Rule 3 - Blocking] extra test file not in files_modified**
- `ui-v2/tests/landing-i18n.test.mjs` was added for the plan's TDD behavior bullet (listener add/remove in the engine source); i18n.test.mjs was not touched.

**3. [Process] Task split**
- `LandingLayer.jsx` and `dict/core.js` were edited once for both tasks, so Task 1's commit (1f3bcaf) already contains the auth-card keys; Task 2's commit (823c17f) holds HostCentre, the manifest and the harness. Task 1 commit passes the full test suite on its own because the dictionary was complete.

No other deviations.

## Known Stubs

None. `dict/landing.js` stays an empty area module by design (the plan places the entries in `core.js`). Landing summary lines (UI-SPEC second line under each label) are not part of this plan.

## Threat Flags

None. T-1308-23-01 (XSS): names and errors render as React text nodes, `describeError` returns plain strings. T-1308-23-02 (listener leak): `dg-lang` listener and its pending frame are removed in `stop()`. The pre-existing module-level `dg-theme` listener in landingEngine.js is never removed (unchanged, out of scope).

## Self-Check: PASSED

- Files exist: `ui-v2/tests/i18n-swept/core.json`, `ui-v2/tests/landing-i18n.test.mjs`, modified landing and dict files.
- Commits exist: 1f3bcaf (Task 1), 823c17f (Task 2).
