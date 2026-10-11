---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 34
subsystem: degram-desktop
status: complete
completed: 2026-10-11
requires: [1301-32, 1301-33]
provides:
  - Host-to-page state and region fragments and the new-session request, in main, on the exact vocabulary of ui-v2 hostMode.js
  - DeGram stays on the DG ring after a project is chosen; chats open from the pill, the sidebar row or the history
  - Six-row DeGram sidebar, DeGram-only pane/section gating, scope-keyed pins
affects: [1301-35, 1301-36]
key-files:
  created:
    - apps/degram/apps/desktop/src/degram/sidebar-nav.ts
    - apps/degram/apps/desktop/src/degram/sidebar.test.tsx
    - apps/degram/apps/desktop/src/degram/ring-route.test.tsx
  modified:
    - apps/degram/apps/desktop/electron/degram/dg-view.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts
    - apps/degram/apps/desktop/electron/degram/channels.ts
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/preload.ts
    - apps/degram/apps/desktop/src/app/chat/sidebar/index.tsx
    - apps/degram/apps/desktop/src/app/contrib/wiring.tsx
    - apps/degram/apps/desktop/src/degram/shell-host.tsx
    - apps/degram/apps/desktop/src/degram/use-degram-state.ts
    - apps/degram/apps/desktop/src/degram/scope-route.ts
    - apps/degram/apps/desktop/src/degram/dg-page.tsx
    - apps/degram/apps/desktop/src/degram/register-dg-page.tsx
    - apps/degram/apps/desktop/src/degram/sign-in-state.tsx
    - apps/degram/apps/desktop/src/degram/i18n.ts
    - apps/degram/apps/desktop/src/lib/connection-scoped.ts
    - apps/degram/apps/desktop/src/store/layout.ts
    - apps/degram/apps/desktop/src/store/profile.ts
    - apps/degram/apps/desktop/src/plugins/hermes-bots/plugin.tsx
requirements-completed: []
---

# Phase 1301 Plan 34: the DeGram shell on the DG ring (D-41, D-42, D-44)

**After the project choice DeGram stays on the DG page showing the ring; the sidebar carries exactly the six DeGram rows; main tells the page connecting/ready/idle and steers its regions.** The start screen has no «DEGRAM» heading.

Committing repository: **component**, branch `degram/phase-1301`, commit `c3318b2d` (on top of plan 33's `03785f3e`). Not pushed. The framework gitlink is unchanged (still `40bbd47f`); no framework commit was made by this plan.

## Implementation

Main (`electron/degram`):

- `dg-view.ts`: `signal(fragment)` accepts only `#degram-state=connecting|ready|idle` and `#degram-go=landing|graph|model|connectors` (anything else throws) and loads it as a hash-only change of the loaded host page URL, never a reload and never on the `#degram` slice or a blank view. `setHostState` remembers the ring state synchronously and every later full page load carries it in its initial hash (the page parses the initial hash), so a reload or a revoke-and-restore never shows a stale ring. `setLocale('ru'|'en')` appends `&lang=` to the next host-page load; a fragment never changes the loaded page's query. `did-navigate-in-page` forwards the exact `#degram-new-session` (main frame, allowlisted origin) to `onNewSessionRequested`; `#degram-select=` handling is unchanged.
- `ipc.ts`: an announcement signals `connecting`, the scope state maps `opening`/`ready`/anything else to `connecting`/`ready`/`idle`, and a refused announcement settles back to `idle` when the call returns (a refusal never changes the scope state). `new-session-requested` is emitted to the renderer only while `scope.status === 'ready'`. New request channels `degram:dg-go` (region validated against the vocabulary) and `degram:set-locale` (`ru|en`), both behind the trusted-sender guard; exposed in preload as `dgGo` / `setLocale`. `scope.ts` gains the `new-session-requested` event type.

Renderer (`src/`):

- Start screen: the wordmark is no longer rendered above `SignInState` (component kept); the brand stays in the window title.
- Routing: `handleNewScope` now calls `actions.showRing` (reset the draft with `preserveRoute`, navigate to `/dg`) instead of opening a chat. `requestFreshSession({ preserveRoute })` (store/profile) feeds the wiring effect, which passes it to `startFreshSessionDraft`. The `new-session-requested` event runs the existing `startNewChat` (fresh draft, navigate to the chat) in the ready scope. `DgPage` lost the graph/full switch; the view is always the whole DG app (a `graph` or blank view is set to `full`). The shell host sends the DeGram locale to main on mount and on change.
- Sidebar (`sidebar-nav.ts`, `sidebar/index.tsx`): under `$degramEnabled`, `navItems` is exactly «Новая сессия», «Граф проекта», «Валидатор», «Коннекторы», «Модели», «Меню» (EN: New session, Graph Viewer, Model Viewer, Connectors, Models, Menu). Graph/Model/Connectors/Menu navigate to `/dg` and call `dgGo(graph|model|connectors|landing)`; the active highlight follows the last region sent while on `/dg`; Новая сессия is the stock new-session action (Ctrl+N hint and drag source unchanged); Модели navigates to `/degram/models`. Stock rows, contributed rows and `sidebarNav.prefs` do not apply; the messaging and cron sections, the blank state, the profile rail, the list-header «+» (new session/new project) are not rendered; project grouping is off. The old «DG» row registration is removed (the `/dg` route stays).
- BOTS: `hermes-bots` registers no `pane`, `routines` or `screen-portal` when `isDegramVariant()`, so the sessions zone has no БОТЫ tab.
- Pins: `$pinnedSessionIds` is a `scopeTagged` connection-scoped atom (new `setConnectionScopeTag` in `connection-scoped.ts`). `use-degram-state` sets the tag from `degramScopeTag(state)` = JSON of `[user, company, project]` for a ready scope, else a fixed `no-scope` tag, before painting the new state. The tag change fires the existing scope-change listeners first, so pin-sync forgets the previous scope's mirror and never PATCHes its rows to unpinned. Without a tag (every other variant) the storage key is unchanged.

## Deviations from Plan

Files outside the plan's `files_modified` that were required to carry it (Rule 3, no scope growth):

- `electron/preload.ts` (bridge methods `dgGo`, `setLocale`) and `electron/degram/preload-degram.test.ts` (exact-keys test).
- `src/store/profile.ts` and `src/app/contrib/wiring.tsx`: the route-preserving fresh-session reset the plan names has no existing parameter on `requestFreshSession`.
- `src/lib/connection-scoped.ts`: scope-tagged keys for the pins; chosen over a second pin atom so the existing pin-sync reset hook (`onConnectionScopeChange`) covers a scope swap.
- `src/degram/test-harness.tsx`, `hidden-surfaces.test.tsx`, `ring-route.test.tsx` (new): harness bridge fields, a hidden-surfaces assertion that relied on the wordmark text, and the shell-host routing tests.
- The DG page's nav-row id `degram.nav` is no longer registered (plan: "register-dg-page drops its nav row"); `DG_PAGE_PATH` moved to `sidebar-nav.ts` and is re-exported from `register-dg-page.tsx`.

The «Модели» row navigates to `/degram/models`, a route that does not exist yet: plan 35 registers the page. Until then the row opens whatever the router shows for an unknown path.

## Verification

All commands run from `apps/degram/apps/desktop` unless noted.

- `python tools/degram/workspace.py verify` (framework root) — prints `Submodule gitlink does not match the selected component HEAD`. That is the known state since plan 30: the child has unpushed commits and the orchestrator forbids a gitlink bump, so the check cannot pass until publication. It reports nothing about this plan's content.
- `npm run typecheck` — exit 0 (src, electron, e2e, electron-builder config).
- `npx eslint` on the 30 changed `.ts/.tsx` files — 0 errors. 16 warnings remain, all `padding-line-between-statements` on pre-existing lines of `dg-view.ts` (did-fail-load block), `scope.ts` and `use-degram-state.ts`, and none introduced by this plan (a `no-restricted-globals` warning and the import-order errors in the new files were fixed). Full `npm run lint` was not run.
- `npx vitest run --project electron electron/degram` — 227/227 (was 214 after plan 33; +13 new: fragments in order and no reload, rejected fragments, state remembered across loads, locale, graph slice untouched, exact new-session hash with malformed / sub-frame / wrong-origin / userinfo / case / suffix variants, announce→connecting→ready, refused announcement settles to idle, malformed hashes signal nothing, new-session only while ready, reload carries ready state, dg-go/set-locale validation).
- `npx vitest run --project ui src` — 10790 passed, 3 failed: 2 are the recorded `voice-prefs.test.ts` baseline; 1 is `src/plugins/hermes-bots/cron-detail.test.tsx > labels a next run parked past the scheduler grace` (expects an English "…ago" but `Intl.RelativeTimeFormat` in `src/lib/time.ts` follows the machine's Russian locale: "7 ч назад"). It fails run alone, touches no file of this plan, and plan 33's run did not reach it (it ran `src/degram src/api src/app src/store` only). Treated as a pre-existing, environment-dependent failure; not verified on a clean checkout.
- New UI tests: `sidebar.test.tsx` 14 (row set/order in EN and RU catalogs, six rows rendered with a ready scope, upstream/contributed/`prefs` rows absent, no «New project»/«+»/blank state, stock sidebar unchanged outside degram with a positive control, region routing and `dgGo`, highlight, Модели route, pins by project / user / company / no-scope / storage keys, source pins of the gates), `ring-route.test.tsx` 5 (ready scope lands on `/dg` with a preserved-route reset, boot restore keeps the route, new-session event opens the chat route, ignored without a ready scope, locale sent), plus 6 in `shell.test.tsx`/`scope-route.test.ts`/`plugin-panes.test.tsx`. A mutation check (shell host calling `startNewChat` for a new scope) failed the two routing tests, as intended.
- Child commit: `git -C apps/degram log --oneline -1` → `c3318b2d feat(1301-34): DeGram shell stays on the DG ring, sidebar set, new-session pill (D-41, D-42, D-44)`. No file was deleted by the commit.

## Limits

- Offline tests only: fake `WebContentsView`, jsdom sidebar. No Desktop launch, build, install, push, Docker or live UAT; the end-to-end sequence (choose a project → sphere → pill on the ring → chat) is plan 36's check. DG-side behavior of the fragments was proven in plan 32's rendered tests, not here.
- The sidebar highlight follows the last region the sidebar sent; a region change the user makes inside the DG page is not reported back (no page-to-host region message exists, by design of the vocabulary), so the highlight can lag until the next sidebar click.
- `setLocale` takes effect on the next host-page load (a locale switch while the page is shown does not reload it, to keep the page's state); the first load can precede the locale message and then shows the page's default language until the next load.
- Pins made in this window before this change live under the bare, untagged key and are not adopted by any scope (by design: ownership is unknowable).
- The stale git worktree directory `.git/modules/degram/worktrees/dgp-t` still cannot be pruned (permission denied, same as plan 33); the commit itself succeeded.
- `graphify update .` was not run (it writes generated files into the framework tree, which this plan must not touch).

## Self-Check: PASSED (offline scope)

- Created files exist: `sidebar-nav.ts`, `sidebar.test.tsx`, `ring-route.test.tsx` under `apps/degram/apps/desktop/src/degram/`.
- Commit `c3318b2d` exists on `degram/phase-1301`; subject starts with `feat(1301-34)`; trailer present; not pushed.
