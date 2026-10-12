---
phase: 1308-dg-web-ui
plan: "22"
subsystem: ui
tags: [i18n, react, degram, typography, coverage]
requires:
  - phase: 1308-dg-web-ui
    provides: "Plans 05, 10–16 and 23 supply the language store, area dictionaries and previously swept UI surfaces"
provides:
  - "Translated App shell, DeGram read-only workspace and primitive-owned default copy"
  - "Exact-once manifest coverage, raw-text, obsolete-copy and font-fallback test gates"
affects: [1308-17, 1308-18, 1308-19, 1308-20, web-ui-uat]
tech-stack:
  added: []
  patterns:
    - "Keep DeGram status state as stable codes; translate at render time to follow live host-language changes"
    - "Translate primitive defaults only when the caller does not supply copy"
key-files:
  created:
    - ui-v2/tests/i18n-swept/shell.json
  modified:
    - ui-v2/src/App.jsx
    - ui-v2/src/shell/ScreenHeader.jsx
    - ui-v2/src/degram/DeGramWorkspace.jsx
    - ui-v2/src/degram/ReadOnlyGraph.jsx
    - ui-v2/src/degram/inspection.js
    - ui-v2/src/components/forms/Combobox.jsx
    - ui-v2/src/components/forms/SearchField.jsx
    - ui-v2/src/components/surfaces/Dialog.jsx
    - ui-v2/src/i18n/dict/screens.js
    - ui-v2/tests/i18n.test.mjs
key-decisions:
  - "Retain inspectionGraph's sanitized value contract and translate only its unavailable-value display sentinel."
  - "Do not add font assets or packages: existing system fallbacks serve Cyrillic pending visual review."
patterns-established:
  - "Manifest union must equal the non-excluded JS/JSX source set, with exactly one owner per file."
requirements-completed: [WEBUI-02, WEBUI-01]
coverage:
  - id: D1
    description: "Every non-excluded JS/JSX source file is listed exactly once and the raw-text guard finds no untranslated copy."
    requirement: WEBUI-02
    verification:
      - kind: unit
        ref: "ui-v2/tests/i18n.test.mjs#every source file is covered by exactly one manifest; raw-text guard passes every swept file"
        status: pass
    human_judgment: false
  - id: D2
    description: "App shell, DeGram workspace and shared primitive defaults render Russian copy from the shared language store while retaining caller and graph data."
    requirement: WEBUI-01
    verification:
      - kind: unit
        ref: "node --test ui-v2/tests/*.test.mjs (281/281)"
        status: pass
      - kind: automated_ui
        ref: "node ui-v2/tests/run-degram.mjs (22/22 offline harness cases)"
        status: pass
    human_judgment: true
    rationale: "The harness checks the read-only flow, but a live host-language switch, caller-data presentation and visual RU/EN review were not accepted in a real browser."
  - id: D3
    description: "Font stacks provide system fallbacks for Cyrillic even though the nine bundled font files contain Latin subsets only."
    requirement: WEBUI-02
    verification:
      - kind: unit
        ref: "ui-v2/tests/i18n.test.mjs#font stacks fall back to Cyrillic-capable system faces"
        status: pass
    human_judgment: true
    rationale: "A source-level stack check cannot establish legibility of the hero, landing labels and body text in light and dark themes."
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 22: Whole-UI Translation Coverage

**Shell and DeGram-hosted copy use shared EN/RU translations; a complete source manifest now enforces whole-UI sweep coverage.**

## Accomplishments

- Translated App theme titles, ScreenHeader back control and the read-only DeGram workspace/inspector. DeGram status uses internal codes translated on render, so an active message follows the language store; node labels, property names, project names and user names remain data. The inspection sentinel is translated only for display, not in the sanitized projection.
- Translated the Dialog close control, SearchField placeholder and Combobox default placeholder, empty state, titles and truncation hint. Explicit caller-provided placeholder/empty copy is unchanged; primitives without owned literals were listed but not edited.
- Added `shell.json` for the five shell/host files, components barrel and twenty primitives. The new exact-once manifest test covers every non-excluded JS/JSX file. Added gates for obsolete “AI Engine” text and `toLocale*` calls, plus an informational list of the nine Latin-only bundled font files and assertions for all four system fallback stacks.

## Task Commits

- `8b6df93` — shell, host, primitive defaults, dictionary, manifest and coverage tests (Tasks 1–3 combined).

## Verification

- `python tools/degram/workspace.py verify`: passed; DeGram gitlink equals component HEAD and component context is installed.
- `node --test ui-v2/tests/*.test.mjs`: **281 passed, 0 failed**. Focused i18n test re-run after the final diagnostic edit: **30 passed, 0 failed**.
- `node ui-v2/tests/run-degram.mjs`: **22 passed, 0 failed** in the offline browser harness.
- `npm --prefix ui-v2 run build`: passed with the existing >500 kB chunk-size warning. `git diff --cached --check` passed before the scoped implementation commit.
- `graphify update .`: passed; optional SQL parser was absent for one SQL file, and community labels were reported stale. No optional dependency was installed.

## Deviations and Limits

- The raw-text guard initially found English status strings held in DeGram state. They were replaced with stable status codes and translated at render time; the focused and full tests then passed.
- The self-hosted Geist, Geist Mono, Oswald and Michroma files are Latin-only. Cyrillic relies on Segoe UI/system-ui, Consolas/monospace and Arial Narrow/sans-serif stack fallbacks. Visual checks of «Грамматика.», landing labels and body text in both themes remain an owner UAT backstop; no visual pass is claimed.
- No live deployment, Desktop operation, add-in acceptance or paid inference was performed. The tests verify source coverage and offline behavior, not a whole-app visual audit of every screen after a live language switch.
- Concurrent staged Phase 1309, planning and vault changes, plus pre-existing harness evidence, were excluded from the implementation commit.

## Next Phase Readiness

Offline plan-22 gates are green. Subsequent Phase 1308 work must preserve the separate owner-authorization checkpoint for plan 17 and perform its own live/human acceptance.

## Self-Check: PASSED (offline scope)

The manifest exists, the scoped implementation commit contains eleven planned files, and all automated plan-level verification commands passed. Visual and live checks are explicitly deferred.
