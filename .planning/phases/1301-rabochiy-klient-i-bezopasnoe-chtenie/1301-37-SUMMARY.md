---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 37
subsystem: degram-desktop-scope
status: complete
completed: 2026-10-11
requires: [1301-36]
provides:
  - scope profiles never become the primary/last-used profile in variant degram (F-03)
  - grant check before the open scope is released; refused picks leave the open project running (F-07, D-48)
  - "#degram-project=<name|empty> host signal that puts the DG page back on the open project"
affects: [1301-38, 1301-41]
tech-stack:
  patterns:
    - preference option `ignoreProfile` plus one-time `normalizeOnLoad`
    - mint-before-release ordering in the scope controller
    - fixed-grammar host fragment (length cap 64, display-only)
key-files:
  modified:
    - apps/degram/apps/desktop/electron/desktop-profile.ts
    - apps/degram/apps/desktop/electron/desktop-profile.test.ts
    - apps/degram/apps/desktop/electron/main.ts
    - apps/degram/apps/desktop/src/store/profile.ts
    - apps/degram/apps/desktop/src/store/profile-select-source.test.ts
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/degram/scope.test.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.test.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts
    - apps/degram/apps/desktop/electron/degram/ipc.test.ts
    - apps/degram/apps/desktop/src/degram/degram-gate.tsx
    - apps/degram/apps/desktop/src/degram/dg-page.tsx
    - apps/degram/apps/desktop/src/degram/use-degram-state.ts
    - apps/degram/apps/desktop/src/degram/shell.test.tsx
    - ui-v2/src/lib/hostMode.js
    - ui-v2/src/App.jsx
    - ui-v2/tests/host-degram.test.mjs
requirements-completed: []
---

# Phase 1301 Plan 37: scope profile out of the primary route; grant check before release

**A stored `scope-<16 hex>` profile no longer becomes the primary route, and a selection refused for a missing grant no longer takes the open project's backend down; the DG page is told which project is actually open.**

## What was built

### F-03 (component commit `45db5237`)
- `createDesktopProfilePreferences` takes an `ignoreProfile` option. With it, `readActive()` returns null for an ignored name (the caller falls back to `default`), `remember()` of an ignored name leaves the file untouched, and `normalizeOnLoad()` rewrites a stored ignored value to `default` once (idempotent, keeps other keys).
- `main.ts` passes `ignoreProfile: isScopeProfile` only when `PRODUCT_IDENTITY.degram`, calls `normalizeOnLoad()` right after creating the preferences (before the first `primaryProfileKey()`), and refuses `hermes:profile:set` with a scope profile in variant degram.
- `src/store/profile.ts`: in variant degram `selectProfile` does not call `profile.remember` for a scope profile (defence in depth).
- Non-degram behaviour is unchanged (a test asserts a scope-shaped name is remembered when no option is given). The G-25 gate is untouched: `scope-gate.ts` and `scope-gate.test.ts` have no diff and the suite is green.

### F-07 / D-48 (component commit `45db5237`)
- `scope.ts selectProject` now mints for the requested project BEFORE `closeCurrent()`. Only an `ok` mint closes the previous scope and opens the new one. With another project open:
  - `GRANT_REQUIRED`: emits `grant-required` for the requested project; no `backend.release`, no credential clear, state stays `ready` for the open project.
  - `forbidden` (403): purges only the requested project's local profiles (`profiles.purge` plus `purgeProject`, D-19, G-15) and emits `access-revoked` for it; the open scope, backend and state stay untouched.
  - unreachable / other mint failure: nothing changes; `signed-out` ends the session through the normal clearing.
  - Re-selecting the project that is itself open, or a selection with no open project, keeps the previous behaviour (grantRequired reset / revokeActive / `fail`).
- `dg-view.ts` allows `#degram-project=<encodeURIComponent(name)>` (name matches the announcement grammar, at most 64 chars) and `#degram-project=` (none); exports `projectFragment`.
- `ipc.ts settleAfterSelection`: after any non-ok, non-SUPERSEDED selection (from the DG page announcement or the renderer IPC) signals `#degram-project=<open project or empty>` and settles `#degram-state=` (`ready` when a project stays open, else `idle`).
- Renderer: `OpenProjectNotices` (in `degram-gate.tsx`, rendered in the DG page toolbar row) shows the D-39 grant-required copy and the access-revoked copy while a project stays open, dismissible with the existing «×». The store keeps these notices until a new scope epoch opens (`openedNew`) instead of clearing them on any `ready` state.

### ui-v2 (framework commit `1f177d2`)
- `parseHostSignal` returns `{ project: name }` / `{ project: null }` for `#degram-project=...` in host mode only; over 64 chars, malformed percent-encoding, control characters, `/`, `\`, `&`, `#` return null.
- `App.jsx` applies a `project` signal with `setProject` and `localStorage dgv2_project` (key removed for null) and does not call `announceProject`.

## Verification (real output)
- Component TDD: new tests failed before the fix (desktop-profile 2, scope 4, dg-view 1, ipc 3, shell 2) and pass after.
- `electron/degram` + `electron/desktop-profile.test.ts`: 14 files, 259/259 passed (scope-gate.test.ts unchanged, green).
- `npx vitest run --project ui`: 10811 passed, 3 failed = the known baseline (2 `voice-prefs.test.ts`, 1 `plugins/hermes-bots/cron-detail.test.tsx`); `src/degram` 252/252 and `profile-select-source` 14/14.
- `npm run typecheck` (apps/desktop): exit 0. ESLint on the touched files: 0 errors (remaining padding-line warnings are on lines this plan did not touch).
- `npx vitest run --project electron` (whole project): 32 failures in 21 files, all platform/packaging tests this plan did not touch (ssh-connection, tray-host, mac-sign, bundle-electron-main, system-ca, i18n-keys out of date vs `en.ts`, ...). Not run on a clean baseline here, so not proven pre-existing; none involve the files changed.
- `node --test ui-v2/tests/host-degram.test.mjs`: 6/6. `npm --prefix ui-v2 run build`: exit 0.
- `python tools/degram/workspace.py verify`: exit 0 (before the commits; the gitlink is not bumped by this plan).

## Deviations from Plan

### Auto-fixed Issues
**1. [Rule 3 - Blocking] scope-gate.test.ts source pin on the main.ts import line**
- **Found during:** Task 1. The pin requires the exact line `import { createScopeBackendGate } from './degram/scope-gate'`; merging `isScopeProfile` into it failed the pin (and the plan forbids touching that test).
- **Fix:** a second import line `import { isScopeProfile } from './degram/scope-gate'`.
- **Files modified:** `apps/degram/apps/desktop/electron/main.ts`.

**2. [Rule 1 - Bug] TypeScript narrowing in `settleAfterSelection`**
- **Found during:** Task 4 typecheck (strictNullChecks is off, so `ok` does not discriminate `SelectResult`).
- **Fix:** `'code' in result` narrowing. Typecheck then exits 0.

### Additions beyond the listed files
- `apps/degram/apps/desktop/src/degram/use-degram-state.ts` (notice lifetime), `src/degram/dg-page.tsx` (notice placement) and `src/store/profile-select-source.test.ts` (scope-profile remember test) were edited; the plan listed `degram-gate.tsx` / `shell.test.tsx` for the notice but not these.
- `dg-view.test.ts` was extended for the new fragment grammar.
- The access-revoked notice follows the same keep-while-open rule as the grant notice (same refusal path for a revoked non-open project).

## Known Stubs
None.

## Threat Flags
None beyond the plan's register: T-1301-37-01 (scope never primary: tested), T-1301-37-02 (mint before release: tested, `released` stays empty), T-1301-37-03 (fixed fragment grammar, cap 64, tested on both sides).

## Limits
- Not live-tested: the relaunch with the old `active-profile.json` and the pick-without-grant scenario need an installed build (plan 41 ships it). The unit/integration tests cover the code paths, not the Electron window.
- Component commit `45db5237` is local only. Nothing was pushed and the framework gitlink was not bumped (plan 41's owner checkpoint); `workspace.py verify` will show gitlink behind child HEAD until then.
- The framework tree still carries other sessions' uncommitted edits (e.g. `ui-v2/src/lib/auth.js`, `ProjectsScreen.jsx`, `tests/evidence/degram-verified.json`); only this plan's three ui-v2 files were staged.
- `ui-v2` build was run on the working tree (includes those other edits); it succeeded.

## Commits
- component `45db5237` fix(1301-37): keep scope profiles out of the primary route; check the grant before releasing the open scope (F-03, F-07)
- framework `1f177d2` fix(1301-37): DG page follows the project DeGram actually opened (F-07)

## Self-Check: PASSED
