---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 32
subsystem: ui-v2
status: complete
completed: 2026-10-11
requires: [1301-28, 1301-31]
provides:
  - Exact-vocabulary host-to-page state and navigation fragments
  - Hosted landing connecting sphere and ready-state new-session pill
  - Offline rendered coverage of project choice through host navigation
affects: [1301-33, 1301-34, 1301-36]
key-files:
  created:
    - ui-v2/src/landing/HostCentre.jsx
    - ui-v2/tests/host-centre.browser.jsx
    - ui-v2/tests/run-host-centre.mjs
    - ui-v2/tests/evidence/degram-1301-32-offline.json
  modified:
    - ui-v2/src/lib/hostMode.js
    - ui-v2/src/App.jsx
    - ui-v2/src/landing/LandingLayer.jsx
    - ui-v2/src/landing/landingEngine.js
    - ui-v2/src/landing/landing.css
    - ui-v2/tests/host-degram.test.mjs
    - ui-v2/src/degram/README.md
requirements-completed: []
---

# Phase 1301 Plan 32: hosted landing ring centre

**Project selection in the hosted DG page immediately switches the ring centre to a connecting sphere, and a fixed-vocabulary fragment channel lets DeGram signal readiness or navigate permitted screens.** The ready state restores the project hero and a new-session pill. Browser fragments are display/navigation signals, never authorization.

## Implementation

- Added exact parsing of `#degram-state=connecting|ready|idle` and `#degram-go=landing|graph|model|connectors`; accepted fragments are cleared with `history.replaceState` while preserving the `?host=degram&lang=ru` query. The pre-existing `#degram` root selector remains unchanged.
- On the Projects click, set connecting before the asynchronous membership refresh. The theme-matched thinking sphere falls back to a procedural glow if the image fails; the connecting centre and ready-state pill use the landing fade pattern. Russian host-only labels use the body font stack.
- The pill announces `#degram-new-session` transiently. No project name, user identity or token is trusted from a host signal. The host must validate page announcements and active scope.
- Production code, tests and separate offline evidence committed as `08f5635` (`feat(1301-32): DG host-mode ring centre and fixed host channel (D-41, D-44)`). No image rebuild or Desktop change was made.

## Verification

- `node ui-v2/tests/run-host-centre.mjs` — 5/5 rendered host scenarios with ReactDOM and synthetic API replies: immediate connecting before membership response, Russian/theme/fallback, ready pill, allowed navigation, idle; no unmatched network or browser errors.
- `node --test ui-v2/tests/host-degram.test.mjs` — 5/5 fixed-vocabulary and root-slice checks.
- `node --test --test-reporter=dot ui-v2/tests/*.test.mjs` — exit 0 (all tests); `npm --prefix ui-v2 run build` — exit 0, existing >500 kB chunk warning.
- `node ui-v2/tests/run-degram.mjs 1301-32-offline` — 22/22 restricted-root offline checks; evidence at `degram-1301-32-offline.json` is a whole-bundle source-hash snapshot, not execution coverage for the normal App.
- `node ui-v2/tests/run-grants.mjs host` — 6/6. A briefly introduced assertion that an already-granted user could not see the request button conflicted with D-40's button contract; it was removed and was not committed.
- `git diff --cached --check` passed before the production commit; `graphify update .` completed, generated files were not staged.

## Limits and provenance

- Hosted browser tests run with synthetic API responses on a file URL; the actual `data-service` image has not been rebuilt and DeGram Desktop has not been launched. No live acceptance or DGCL completion is claimed.
- Pre-existing dirty `auth.js`, `ProjectsScreen.jsx`, untracked API/security and panel tests, and the shared `degram-verified.json` evidence were excluded from the plan commit. The plan's evidence has its own label. A live visual/owner check of the transition and host bridge remains for Plan 36.

## Self-Check: PASSED (offline scope)

- The production commit exists; scoped tests and build passed. Next is the component-side Plan 33, subject to its own repo and publication boundaries.
