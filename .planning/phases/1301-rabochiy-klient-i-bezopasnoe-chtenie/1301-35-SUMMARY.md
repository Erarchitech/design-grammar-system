---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 35
subsystem: degram-desktop
status: complete
completed: 2026-10-11
requires: [1301-34]
provides:
  - The DeGram «Модели» screen at /degram/models: per connector its status and documents, pin / unpin / refresh (D-43)
  - A status-only bottom strip (company, project, per-bridge status segments; no document segment)
  - A main-side scope gate: one DeGram scope profile owns a backend at a time; a left scope is parked before it is killed, never restarted, never retired by the pool arbiter while active (G-25)
affects: [1301-36]
key-files:
  created:
    - apps/degram/apps/desktop/src/degram/models-page.tsx
    - apps/degram/apps/desktop/src/degram/models-page.test.tsx
    - apps/degram/apps/desktop/src/degram/backend-churn.test.ts
    - apps/degram/apps/desktop/electron/degram/scope-gate.ts
    - apps/degram/apps/desktop/electron/degram/scope-gate.test.ts
  modified:
    - apps/degram/apps/desktop/electron/main.ts
    - apps/degram/apps/desktop/src/degram/document-picker.tsx
    - apps/degram/apps/desktop/src/degram/register-dg-page.tsx
    - apps/degram/apps/desktop/src/degram/scope-strip.tsx
    - apps/degram/apps/desktop/src/degram/connected-scope-strip.tsx
    - apps/degram/apps/desktop/src/degram/scope-route.ts
    - apps/degram/apps/desktop/src/degram/i18n.ts
    - apps/degram/apps/desktop/src/degram/chat.test.tsx
    - apps/degram/apps/desktop/src/degram/shell.test.tsx
requirements-completed: []
---

# Phase 1301 Plan 35: «Модели» screen and no re-dialing of left scopes (D-43, G-25)

**Documents are chosen on a DeGram «Модели» page; the strip shows only statuses. A project switch no longer restarts the backend it just left: the left scope is parked in every window before its child is killed, main refuses to start a scope profile that is not the active one, and the pool arbiter never retires the active scope.**

Committing repository: **component**, branch `degram/phase-1301`, commit `38728957` (on top of plan 34's `c3318b2d`). Not pushed. The framework gitlink is unchanged; no framework commit, STATE.md or ROADMAP.md change was made by this plan.

## Implementation

D-43 (renderer, `src/degram`):

- `document-picker.tsx`: the strip popover is gone. `GroupBody` is exported unchanged in behaviour; `DocumentsPanel` is the former popover body (refresh button, the single «no open documents» empty state, a `Command variant="menu"` list with one group per bridge, search field above 7 rows, notice rows for off/busy/setup-incomplete bridges, optimistic pin, one Unpin per group). Each group heading now also names the connector's status (dot + label, `data-bridge-state`) once its first answer is in; a pending group keeps its single «Проверка» row. Unpin no longer closes anything (it is a screen).
- `models-page.tsx` (`ModelsPage`): title «Модели» / «Models», `DocumentsPanel`, reads both bridges on open and whenever the ready scope key changes. Without a ready project it renders the same `FirstScreen` as the DG page and reads nothing. Documents of a left scope never show: `useDocuments` is scope-tagged.
- `register-dg-page.tsx`: also registers the `degram.models` route at `DEGRAM_MODELS_PATH` (the sidebar row from plan 34 already navigated there); one disposer for both routes.
- `scope-strip.tsx` / `connected-scope-strip.tsx`: the document segment, `ScopeStripDocument`, `onSelectDocument` and `documentPicker` are removed; the strip is company · project · Revit · Grasshopper. A pinned document still names itself in its own bridge segment (accent dot). The context card in the composer is untouched and still lists the pinned documents.
- `i18n.ts`: `models.title` added; `strip.documentsCount`, `cta.selectDocument` and `scope.document` removed (no longer used).

G-25 (main, renderer):

- Root cause, observed offline (systematic debugging): in `backend-churn.test.ts`, with only a socket drop on the left profile (what main's release does), the renderer registry's `reconnectSecondary` (store/gateway.ts, the reconnect ladder of a still-`wantOpen` secondary) called `getConnection(left)` again, and main's `ensureBackend` honoured it, so the left backend restarted inside the mint window. The stack of the second left dial was `reconnectSecondary -> openSecondary -> dialProfile -> getConnection`. A request for any profile also dials once through `sharedPrimaryRoute` before its own socket dial, so two refused ensures per stale request are expected.
- `electron/degram/scope-gate.ts` (`createScopeBackendGate`): the scope controller's `backend.ensure` calls `allow(profile)` (that scope becomes the single active scope profile); `backend.release` calls `release(profile, teardown)`, which unmarks it, broadcasts the existing `hermes:pool:retiring` for every pool key of the profile BEFORE the child is stopped (the renderer parks the scope: `wantOpen=false`, so the dying socket starts no ladder) and then tears down. `assertCanStart(key)` runs after `profileDeletionGate.assertCanStart` in both `ensureBackend` and the local branch of `ensureRegistryBackend`, only under `PRODUCT_IDENTITY.degram`, and throws «DeGram scope profile … no longer exists in this window» for a `scope-<16 hex>` profile (bare or `conn:local::`) that is not the active one. The wording matches `isMissingProfileError`, so a ladder that does reach it fail-stops instead of retrying. The refusal is logged once per profile and never names it. `guardPrepare` wraps the pool retirer's `prepare` step in `main.ts` (`prepare: scopeGate.guardPrepare(poolRetirementClient.prepare)`): a null token means «not retired», so the LRU eviction, the foreground-recovery reclaim and the idle reaper never pick the active scope. Profiles that are not DeGram scope profiles are never refused or protected.
- `scope-route.ts` (`followScopeRoute`): after the route lands on the new scope, `retireLocalProfileGateways(leaving)` drops the left scope's registry entry when the route was on a different `scope-…` profile (never for the stock default profile, never for the same profile, so the reconcile re-run retires nothing).

## Deviations from Plan

Files outside the plan's `files_modified` (Rule 3 / structure, no scope growth):

- `electron/degram/scope-gate.ts` and `scope-gate.test.ts` (new): the testable seat of the main-side fix; `main.ts` cannot be imported in a unit test, so the logic lives here and `main.ts` only wires it (source pins in the test).
- `src/degram/scope-route.ts` was in the list; `src/store/gateway.ts` was NOT changed: the registry already has `retireLocalProfileGateways` and `parkSecondariesForRetiredBackend`, and `use-gateway-boot` already parks on `hermes:pool:retiring`, so the fix reuses them.
- The `GroupHeading` status line, `DocumentsPanel` and the removal of `DocumentPicker` (the plan said «export GroupBody (or a DocumentsPanel)»): chose the panel and removed the popover, since nothing else used it.
- `models-page.test.tsx` carries the new page tests; the picker behaviour suite stayed in `chat.test.tsx` and now renders `ModelsPage` with the same assertions (D-29, unpin per bridge, unpin all, empty state, search above 7 rows, off bridge notice, per-bridge pending, no-identity row, optimistic pin and rollback). Two strip tests that asserted «Select document» / «Documents: n» were replaced by tests that assert the segment is absent (EN and RU); the strip test in `shell.test.tsx` likewise.
- The plan said to test `backend-churn.test.ts` «with fakes»; it drives the REAL renderer registry (`store/gateway.ts`, fake WebSocket) and `followScopeRoute` against the REAL scope gate, with only the pool and the `hermesDesktop.getConnection` door faked.

## Verification

All commands run from `apps/degram/apps/desktop` unless noted.

- `python tools/degram/workspace.py verify` (framework root) — prints `Submodule gitlink does not match the selected component HEAD`: the known state since plan 30 (child commits unpushed, gitlink bump forbidden for this run). Not related to this plan's content.
- RED first: `src/degram/models-page.test.tsx` failed at import (no `models-page`); `backend-churn.test.ts` against a pre-fix gate placeholder (release = bare teardown, no refusal) failed with `ensure(A)` accepted again after A's release (stack through `reconnectSecondary`), and the scope A re-selection and refusal tests failed.
- `npx vitest run --project ui src/degram` (Task 1 state) — 12 files, 244/244.
- `npx vitest run --project ui src/degram/backend-churn.test.ts` — 6/6 (A -> B -> C -> A: no ensure for a left profile after its release, running set is only the active scope, starts are exactly [A, B, C, A]; refusal of a stale foreground request with no ladder after 10 minutes of fake time; refusal before any scope is open; non-scope profiles untouched; the route retires the left scope only once and only a scope profile). Mutation checks, each restored: no pre-kill broadcast fails the A-B-C-A test; no refusal fails the refusal tests; no `retireLocalProfileGateways` in the route fails the retire test.
- `npx vitest run --project electron electron/degram` — 13 files, 238/238 (was 227 after plan 34; +11 in `scope-gate.test.ts`: name matching, allow/refuse, non-scope profiles, replacement, release order broadcast-before-teardown, release of a non-active profile, once-only nameless log, LRU eviction with the real `createPoolRetirer` skipping an active oldest entry, idle retirement declined for the active scope, `main.ts` source pins).
- `npx vitest run --project ui src` — 10808 passed, 3 failed: the 2 recorded `voice-prefs.test.ts` baseline failures and the recorded `src/plugins/hermes-bots/cron-detail.test.tsx` "Overdue since … ago" (Russian-locale `Intl.RelativeTimeFormat`) failure. Nothing else failed (was 10790 passed after plan 34).
- `npm run typecheck` — exit 0.
- `npx eslint` on the 14 changed `.ts/.tsx` files — 0 errors, 0 warnings after `--fix` on `document-picker.tsx` (import order) and `scope-gate.test.ts` (padding). `main.ts` produced no findings. Full `npm run lint` was not run.
- Child commit: `git -C apps/degram log --oneline -1` → `38728957 feat(1301-35): Модели screen for document choice, status-only strip; stop re-dialing left scopes (D-43, G-25)`. No file was deleted by the commit.

## Limits

- Offline only: jsdom pages, a fake WebSocket registry and a fake pool. No Desktop launch, build, install, push, Docker, `desktop.log` read or live UAT. The plan's live check («Модели» pins a Revit model and a GH definition; a project switch shows no backend restart of the left scope in `desktop.log`) is NOT done and belongs to plan 36 / the next live run.
- The root cause was reproduced offline with fakes; the 0.1.9 `desktop.log` was not read (outside the repo). The original `GET /api/status` «waiting for a free local slot» lines are consistent with the same path (a request or reconnect dialing `ensureBackend` for a left scope), but whether a status poll or roster read, rather than the reconnect ladder alone, also contributed in the live run is unproven. The gate refuses any such caller regardless of who it is.
- The refusal also applies before any scope is open: a boot-restored route naming a `scope-…` profile of the previous run is refused («no longer exists») until the scope controller starts a scope. That is intended (D-19), but how the boot path in `use-gateway-boot` reacts was not exercised live; the registry's fail-stop on that wording is covered by the churn test only.
- The pool arbiter now declines to retire the active scope for idle reaping too (a single `prepare` wrapper covers LRU, foreground recovery and idle). With a ready scope its backend therefore lives until the scope is released or the app quits.
- `main.ts` wiring is proven by source pins plus the gate's unit and integration tests, not by running `main.ts`.
- The tab title of the `/degram/models` route falls back to the humanized path (no `title` was set on the route contribution).
- The stale git worktree directory `.git/modules/degram/worktrees/dgp-t` still cannot be pruned (permission denied, as in plans 33 and 34); the commit itself succeeded.
- `graphify update .` was not run (it writes generated files into the framework tree, which this plan must not touch).

## Self-Check: PASSED (offline scope)

- Created files exist under `apps/degram/apps/desktop/`: `src/degram/models-page.tsx`, `src/degram/models-page.test.tsx`, `src/degram/backend-churn.test.ts`, `electron/degram/scope-gate.ts`, `electron/degram/scope-gate.test.ts`.
- Commit `38728957` exists on `degram/phase-1301`; subject starts with `feat(1301-35)`; `Co-Authored-By` trailer present; not pushed; no framework commit.
