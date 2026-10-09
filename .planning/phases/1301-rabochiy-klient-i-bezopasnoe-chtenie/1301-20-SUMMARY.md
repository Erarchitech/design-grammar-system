---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 20
subsystem: desktop-client
tags: [degram, membership-revoke, scope-manifest, dg-unreachable, tray, sign-out, electron, python]

requires:
  - phase: 1301-19
    provides: hidden-surface ids, outcome copy, error-path cards (same renderer files area)
  - phase: 1301-12
    provides: scope controller, DG session, DG view, runtime IPC
provides:
  - "degram-scope.json manifest (user, company, project, createdAt; never a token) written by every ensure; purge_project_profiles(user, project) removes that user's profiles of the project under every company key (G-15, D-19)"
  - "profiles CLI purge-project and cleanup-legacy; profiles-cli.ts purgeProject() and cleanupLegacy(); one-time D-30 legacy cleanup with back-fill, marker degram-legacy-cleanup.done"
  - "selectProject 403 (mint or pairing exchange) takes the revoke path: purge by project, access-revoked, no-project state (G-15)"
  - "Revoke toast above the full-window gate: --z-degram-toast 1500 above --z-setup 1400, applied by notifications.tsx under $degramEnabled (G-15)"
  - "Honest boot: runtime.start reports dg-unreachable on a failed /auth/me and loads no page; runtime.retryDg() (single flight) re-runs /auth/me then shows sign-in or the DG page; channel degram:retry-dg; window focus calls it while unreachable (G-16, D-08)"
  - "did-finish-load no longer reports DG reachable after a failed main-frame load or on a non-DG URL (G-16)"
  - "Sign out of DG: project picker command (separated, survives search) and tray entry between Show and Quit, both through requestDegramSignOut(); channels degram:set-tray-labels and degram:request-sign-out; i18n degram.actions.signOut (G-17, DGCL-05)"
affects: [1301-16, 1301-23, DGCL-05, DGCL-06]

tech-stack:
  added: []
  patterns:
    - "A profile directory names its owner in a manifest, so access loss purges by user + project instead of by a one-way hash key"
    - "Native menu text is renderer-owned: main keeps a default label, the renderer sends the localized one over a validated channel and main rebuilds the menu"
    - "Single-flight re-check (retryDg) shared by the Retry button and window focus"

key-files:
  created: []
  modified:
    - apps/degram/degram_variant/profiles.py
    - apps/degram/tests/degram/test_profiles.py
    - apps/degram/apps/desktop/electron/degram/profiles-cli.ts
    - apps/degram/apps/desktop/electron/degram/profiles-cli.test.ts
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/degram/scope.test.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts
    - apps/degram/apps/desktop/electron/degram/ipc.test.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.test.ts
    - apps/degram/apps/desktop/electron/degram/channels.ts
    - apps/degram/apps/desktop/electron/degram/main-wiring.ts
    - apps/degram/apps/desktop/electron/degram/main-wiring.test.ts
    - apps/degram/apps/desktop/electron/degram/preload-degram.test.ts
    - apps/degram/apps/desktop/electron/main.ts
    - apps/degram/apps/desktop/electron/preload.ts
    - apps/degram/apps/desktop/electron/minimize-to-tray.ts
    - apps/degram/apps/desktop/electron/minimize-to-tray.test.ts
    - apps/degram/apps/desktop/src/components/notifications.tsx
    - apps/degram/apps/desktop/src/styles.css
    - apps/degram/apps/desktop/src/degram/degram-gate.tsx
    - apps/degram/apps/desktop/src/degram/dg-page.tsx
    - apps/degram/apps/desktop/src/degram/sign-in-state.tsx
    - apps/degram/apps/desktop/src/degram/project-picker.tsx
    - apps/degram/apps/desktop/src/degram/sign-out-confirm.tsx
    - apps/degram/apps/desktop/src/degram/i18n.ts
    - apps/degram/apps/desktop/src/degram/test-harness.tsx
    - apps/degram/apps/desktop/src/degram/shell.test.tsx
    - apps/degram/apps/desktop/src/degram/chat.test.tsx

key-decisions:
  - "D-30 implemented as chosen (backfill-and-cleanup): ensure back-fills a manifest into an existing manifest-less profile of the scope being opened; the first sign-in of a 0.1.6 run calls cleanup-legacy once, which back-fills the signed-in user's current scopes and then deletes every scope-* profile still without a manifest, then writes degram-legacy-cleanup.done"
  - "The cleanup's keep list is the signed-in user's current memberships (user, company, project), so a profile the user can open keeps its history; without it a cleanup that runs at sign-in, before any project is opened, would be the wipe-all option the owner rejected"
  - "An unreachable /auth/me at start loads no page: the renderer shows the DG-unreachable ErrorState and Retry loads the sign-in or DG page once DG answers"
  - "Extra tray entries are a minimize-to-tray option (extraItems), read each time the menu is built; refreshMenu() rebuilds it when the renderer sends the locale label"
  - "The sign-out command in the project picker is forceMount (group and item) so the project search never hides it"

patterns-established:
  - "Manifest per local profile; purge by owner identity"
  - "Renderer-owned labels for native menus through a validated, length-limited IPC channel"

requirements-completed: []

coverage:
  - id: D1
    description: "Losing access to a project (403 on mint, exchange, renewal; membership removed; company changed) removes every local scope profile of that user + project, under any company key"
    requirement: "DGCL-05"
    verification:
      - kind: unit
        ref: "tests/degram/test_profiles.py TestManifest, TestPurgeProject (two company keys + a third), TestLegacyCleanup, TestCliPlan20; scope.test.ts revoke cases now assert purgeProject, selectProject 403 mint and exchange"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 5.5 on 0.1.6 (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D2
    description: "The access-revoked toast is visible above the full-window DegramGate surface in variant degram; other variants keep the over-modal rung"
    requirement: "DGCL-05"
    verification:
      - kind: unit
        ref: "shell.test.tsx 'the access-revoked toast is rendered above the full-window gate surface' and 'outside variant degram the toast stays on the over-modal rung' (class check; jsdom computes no z-index)"
        status: pass
      - kind: manual_procedural
        ref: "visual check of the toast over the gate on 0.1.6 (plan 16 Task 3)"
        status: unverified
    human_judgment: true
  - id: D3
    description: "DG resetting or refusing connections at start shows the E7 DG-unreachable ErrorState with Retry request, never a blank window; Retry re-runs /auth/me and reloads the view; an error page's load-finished does not report DG reachable"
    requirement: "DGCL-06"
    verification:
      - kind: unit
        ref: "ipc.test.ts (start unreachable, retryDg x6 incl. single flight and focus), dg-view.test.ts (3 reachability cases), shell.test.tsx (gate ErrorState, Retry through retryDg x4)"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 5.7 on 0.1.6 with DG down at start (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D4
    description: "Sign out of DG exists in the project picker menu and the tray menu and runs requestDegramSignOut(), so a running response shows the existing Stop and sign out confirmation"
    requirement: "DGCL-05"
    verification:
      - kind: unit
        ref: "shell.test.tsx picker (sign-out last row, separator, signs out, survives search), chat.test.tsx (tray request with and without a running response, label to the tray), minimize-to-tray.test.ts (order, refreshMenu, upstream unchanged), main-wiring.test.ts, ipc.test.ts, preload-degram.test.ts"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 5.6 on 0.1.6 (tray sign-out, locale label) (plan 16 Task 3)"
        status: unverified
    human_judgment: false

duration: ~1h 45m
completed: 2026-10-09
status: complete
---

# Phase 1301 Plan 20: Membership revoke, DG outage at start, sign-out Summary

**A lost project now purges every local profile of that user and project under any company key (each profile carries a degram-scope.json manifest), a 403 at project selection takes the same revoke path, a DG outage at start shows the unreachable state with a working single-flight Retry instead of a blank window, and DeGram has a Sign out of DG command in the project menu and the tray.**

## Performance

- **Completed:** 2026-10-09
- **Tasks:** 4/5 executed by this run. Task 1 (checkpoint:decision D-30, the owner chose `backfill-and-cleanup`) was done by the orchestrator, framework commit `746dc8c`. Tasks 2-4 are one component commit and Task 5 is that commit, as the plan prescribes.
- **Execution:** sequential executor; one decision checkpoint resolved before this run

## Accomplishments

- **G-15, purge by owner.** `ensure_scope_profile` writes `degram-scope.json` atomically before anything else; `purge_project_profiles(home, user, project)` scans `scope-*` directories under `<home>/profiles` (never following a junction that leads elsewhere) and removes those whose manifest names that user and project. `teardown` now runs `profiles.purge(key)` (the current hash key, T-1301-20-02) and then `profiles.purgeProject(user, project)`; a failure of either reports `purged: false`.
- **G-15, selection 403.** `selectProject` on a mint or pairing-exchange `forbidden` calls `revokeActive()` (credential cleared, backend released, profiles purged, view reset, `access-revoked` emitted) and returns `ACCESS_DENIED` with a `no-project` state instead of a bare error.
- **G-15, visible toast.** `--z-degram-toast: 1500` sits above `--z-setup: 1400`; `notifications.tsx` uses it for both regions under `$degramEnabled`.
- **D-30 legacy handling.** `ensure` back-fills a manifest into an existing manifest-less directory of the scope being opened. `cleanup_legacy_profiles` (CLI `cleanup-legacy --keep-json`) back-fills the keep list, removes every remaining manifest-less `scope-*` profile, and writes `degram-legacy-cleanup.done` only when nothing failed. `scope.ts` runs it once per run, before the first selection's `ensure` and from the heartbeat/focus access check, never blocking a selection on failure.
- **G-16.** `runtime.start` publishes `dg.reachable=false` and emits `dg-unreachable` when `/auth/me` is unreachable and loads no page. `runtime.retryDg()` (one in flight) re-runs `/auth/me`, then shows the sign-in page, loads the DG page (first sign-in through the auth listener, an already signed-in session explicitly), or stays unreachable. `onWindowFocus` calls it while unreachable (D-08, no polling). Channel `degram:retry-dg`, preload `degram.retryDg()`. `dg-view.ts` marks a failed main-frame navigation (reset on `did-start-loading`) and `did-finish-load` reports reachable only for a clean navigation that committed a DG-origin URL. Every Retry in the sign-in state, the project choice and the DG page calls `retryDg()`.
- **G-17.** i18n `degram.actions.signOut` (en "Sign out of DG", ru "Выйти из DG"). The project picker ends with a separated, force-mounted command that closes the popover and calls `requestDegramSignOut()`. The tray menu takes `extraItems` (Show, separator, Sign out, separator, Quit); main-wiring supplies the entry, which shows the window and sends `degram:request-sign-out`; `DegramSignOutConfirm` subscribes (`onRequestSignOut`) and sends its locale label through `degram:set-tray-labels` (validated: string, 1-80 chars, no control characters), after which main rebuilds the tray menu. Default label is Russian until the renderer answers.

## Task Commits

1. Task 1 (D-30 decision record): `746dc8c` docs(1301-20): D-30 legacy DeGram profiles (framework, by the orchestrator)
2. Tasks 2-5, component repo `apps/degram`, branch `degram/phase-1301`, local, not pushed, gitlink not bumped (plan 23): `9457d72b` fix(1301-20): purge by project on revoke, honest DG-unreachable boot, sign-out entries (G-15, G-16, G-17)

## Verification

- `apps/degram/.venv/Scripts/python.exe -m pytest tests/degram -q`: 381 passed (50 in `test_profiles.py`, 28 of them new).
- `npm run typecheck` (renderer, electron, e2e, builder config): pass.
- `npx vitest run --project electron electron/degram electron/minimize-to-tray.test.ts`: 13 files, 230 tests pass.
- `npx vitest run --project ui src/degram src/components`: 241 files, 1675 tests pass.
- `npx vitest run --project ui` (whole project): 3 failures, the same three plan 18 reported, so they DO recur: `src/store/voice-prefs.test.ts` x2 ("expected 'false' to be null") and `src/plugins/hermes-bots/cron-detail.test.tsx` x1 (the "Overdue since" label). This plan touches nothing in `src/store` or `src/plugins`, but the failures were not re-run against a clean checkout, so "pre-existing" is not verified here.
- eslint on all touched TS/TSX files: clean after `--fix` (import order in `shell.test.tsx`). prettier clean on the touched source and on `ipc.test.ts` / `profiles-cli.test.ts` (reformatted); `chat.test.tsx` and `shell.test.tsx` were already prettier-dirty at the base commit and were left as they were.
- Not run: live recheck of UAT 5.5, 5.6, 5.7 on 0.1.6 (plan 16 Task 3), and any Desktop launch (not authorized). Unverified.
- `workspace.py verify`: only the tolerated "Submodule gitlink does not match the selected component HEAD".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] D-30 cleanup needed a keep list**
- **Found during:** Task 2
- **Issue:** D-30 says profiles matching a scope the user opens are back-filled and the remaining manifest-less ones are deleted once on the first sign-in of 0.1.6. Run at sign-in, before any project is opened, "the remaining" would be every legacy profile, which is the wipe-all option the owner rejected (it would delete the current v12 history).
- **Fix:** `cleanup-legacy` takes the signed-in user's current memberships as scopes to keep and back-fills their manifests first. Profiles of scopes the user can no longer open (including the same project under a stale company key, the G-15 `scope-dee1...` case) are still deleted. This is an interpretation of D-30, not a change of it; the owner may want to confirm.
- **Files modified:** `degram_variant/profiles.py`, `electron/degram/profiles-cli.ts`, `electron/degram/scope.ts`
- **Commit:** `9457d72b`

**2. [Rule 3 - Blocking] Existing tests encoded the old behaviour**
- **Found during:** Tasks 2-4
- **Issue:** the DG-unreachable start test asserted that the sign-in page was loaded and that `did-finish-load` flips reachable back; two picker tests counted every option as a project; the Retry tests expected `reloadDg`; the selection log in `scope.test.ts` did not list the cleanup call.
- **Fix:** updated to the new contract (nothing loaded at an unreachable start; the last picker row is the sign-out command; Retry goes through `retryDg`; cleanup first in the selection log).
- **Files modified:** `ipc.test.ts`, `shell.test.tsx`, `scope.test.ts`
- **Commit:** `9457d72b`

### Design adjustments within the plan

- Files beyond `files_modified`: `electron/main.ts` (tray `extraItems`, wiring `showWindow` / `onTrayLabelsChanged`), `electron/degram/main-wiring.test.ts`, `electron/degram/preload-degram.test.ts`, `src/degram/test-harness.tsx` (new bridge methods, `emitRequestSignOut`), plus `src/components/notifications.tsx` and `styles.css` as listed. `DESIGN.md` (which documents the overlay ladder) was not updated; the new rung is commented in `styles.css`.
- The ScopeDeps `profiles` contract gained required `purgeProject` and `cleanupLegacy`; all test fakes were updated.
- `purge-project` prints a JSON list (as the plan says); the Electron wrapper accepts arrays for that command only.
- Plan Task 3 listed `main-wiring.ts` indirectly; the tray hook lives there because the tray entry belongs to the DeGram wiring, not to `ipc.ts`.
- Tests were written together with the implementation in one pass per task; no separate RED run was recorded.
- Plan tasks 2-4 end with "Do not commit yet" and Task 5 commits once, so the three tasks share one component commit.

## Deferred Issues

- A membership that disappears for a project that is **not** the open scope is not purged until that scope is opened or the legacy cleanup is relevant: only the active project's access loss is observable by the scope controller. Out of this plan's scope (G-15 is the active-project revoke); noted for plan 23 / the 0.1.6 recheck.
- `DESIGN.md` overlay-ladder prose does not yet mention `--z-degram-toast`.

## Known Stubs

None.

## Threat Flags

None. T-1301-20-01 (purge by user + project across company keys), -02 (the current hash key is purged as well as the manifest scan), -03 (retryDg single flight, focus only while unreachable), -04 (manifest has four fixed fields; test asserts no token text) are implemented. The tray-labels channel is new IPC surface: sender-checked like every `degram:*` channel and payload-validated (string, 1-80 chars, no control characters).

## Self-Check: PASSED

Commit `9457d72b` found in `apps/degram` (branch `degram/phase-1301`); no tracked file in `apps/degram` is modified after the commit; `test_profiles.py`, `profiles.py`, `scope.ts`, `ipc.ts`, `project-picker.tsx`, `minimize-to-tray.ts` present with the new symbols.
