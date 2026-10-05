---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 13
subsystem: degram-desktop-renderer-shell
tags: [degram, renderer, i18n-ru-first, theme-preset, bundled-fonts, hidden-surfaces, scope-strip, project-picker, dg-page, sign-in, isolation-failure, tdd]
requires: ["1301-04", "1301-12"]
provides:
  - "src/degram/use-degram-state.ts: single renderer mirror of window.hermesDesktop.degram (one subscription, startDegramSync, refreshDegramState, DegramActionsContext), boot-error parser for HOME_OVERLAP"
  - "src/degram/i18n.ts: every UI-SPEC copy row as t.degram (en base, ru overlay via defineLocale; fr/de/es/ja/zh/ar fall back to en); first-run-locale.ts: ru for variant degram only"
  - "scope-strip.tsx (statusBar.left contribution), project-picker.tsx, sign-in-state.tsx, isolation-boot-failure.tsx, degram-gate.tsx (--z-setup surface), shell-host.tsx (the one mount, behind the degram flag), dg-page.tsx + register-dg-page.tsx (route /dg and sidebar row via the routes / sidebar.nav registry areas), use-dg-bounds.ts"
  - "hidden-surfaces.ts: HIDDEN_SURFACES (15 listed + model/billing/gateway settings pages), isSurfaceHidden, HIDDEN_SETTINGS_VIEWS, isSettingsViewHidden; applied at every upstream entry point"
  - "theme preset degram (exact UI-SPEC values) in apps/shared theme-presets.ts and themes/presets.ts, default skin of variant degram only; bundled Geist / Geist Mono / Oswald woff2 + licenses; fonts.css without any URL"
affects: [1301-14, 1301-15, 1301-16]
tech-stack:
  added: []
  patterns:
    - "Mount once, behind the flag: DegramShellHost in ContribController; the statusbar strip, the DG route and the sidebar row are registry contributions, so no sidebar/router code was forked"
    - "Hide the entry, not the action: one gate (isSurfaceHidden) read at each upstream entry point; a source-audit test pins every id to its mount site because the upstream shell cannot be rendered offline"
    - "Bridge state is a cache of main: clear-then-notify on the main side, a module store with one subscription on the renderer side, an `painted` flag that withholds the native view until the page painted"
key-files:
  created:
    - apps/degram/apps/desktop/src/degram/{use-degram-state.ts,host-actions.ts,use-dg-bounds.ts,i18n.ts,first-run-locale.ts,scope-strip.tsx,project-picker.tsx,sign-in-state.tsx,isolation-boot-failure.tsx,degram-gate.tsx,shell-host.tsx,dg-page.tsx,register-dg-page.tsx,hidden-surfaces.ts,fonts.css,test-harness.tsx}
    - apps/degram/apps/desktop/src/degram/{shell.test.tsx,hidden-surfaces.test.tsx,presets-fonts.test.ts}
    - apps/degram/apps/desktop/src/assets/fonts/degram/ (10 woff2, 3 LICENSE-*.txt, NOTICE.md)
  modified:
    - apps/degram/apps/shared/src/theme-presets.ts
    - apps/degram/apps/desktop/src/themes/presets.ts
    - apps/degram/apps/desktop/src/i18n/{types.ts,en.ts,ru.ts,context.tsx}
    - apps/degram/apps/desktop/src/app/{contrib/controller.tsx,contrib/wiring.tsx,settings/index.tsx,settings/fallback-models-field.tsx,chat/composer/controls.tsx,chat/composer/status-stack/index.tsx,chat/sidebar/local-device-switch.tsx,shell/hooks/use-statusbar-items.tsx,shell/model-catalog-menu.tsx}
    - apps/degram/apps/desktop/src/components/boot-failure-overlay.tsx
    - apps/degram/apps/desktop/electron/degram/{ipc.ts,ipc.test.ts}
    - apps/degram/locales/_keys.desktop.json
key-decisions:
  - "Geist Sans has no Cyrillic subset in @fontsource 5.3.0 (1301-ENV.md): the Geist Sans role renders Cyrillic with Segoe UI through the font stack. Cyrillic is native in Geist Mono (400/500) and Oswald (400/500 declared, 500 used for the wordmark). Latin Geist Sans/Mono/Oswald come from the ui-v2 vendored files"
  - "The preset font stacks are literal (`'Geist', <SYSTEM_SANS>` and `'Geist Mono', <SYSTEM_MONO>`), not `var(--dt-font-sans)` as UI-SPEC wrote: a theme's typography is what sets --dt-font-sans, so referencing it from itself is a CSS variable cycle. The literal tail still ends in Segoe UI, emoji and bundled JetBrains Mono, which the existing preset tests require"
  - "DG view bounds are withheld until the page painted, so the Connecting-to-DG Loader is never covered by a blank native view; `painted` is true at the first state when the view is not blank, so a missed paint event cannot deadlock the view"
  - "Sign-out has no entry point yet: UI-SPEC specifies its confirmation copy (catalogued) but no control, so none was invented"
  - "Statusbar bridge segments and the document segment take props with 'Checking' defaults; plan 14 feeds them"
requirements-completed: []
requirements-partial: [DGCL-01, DGCL-02, DGCL-03]  # renderer surfaces proven offline in jsdom; the live checks (native view placement, real sign-in page, fonts painting, zoom factor math) are plan 16
duration: two sessions (the first cut off by an API rate limit after Task 1 and most of Task 2's code)
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 13: DeGram renderer shell Summary

The DeGram variant now has its renderer shell: a ru-first copy catalog, the DG theme preset on locally bundled fonts, a gate that stands in for the app until the user is signed in with an explicitly chosen project, a scope strip and project picker, the DG page next to Chat, the runtime-isolation failure screen, and every provider, model, key, billing, update and remote-setup entry point removed behind one gate. All of it is proven offline (jsdom and source audits); nothing was launched.

## Authorization and boundaries

Per the orchestrator brief: local commits in `apps/degram` on `degram/phase-1301` only. No push, no `hermes update`, no Desktop launch, build, dev server or packaging, no Docker, no write to `%LOCALAPPDATA%\hermes` or the Hermes profile, no dependency added, no `npm install`. The only network use was `npm pack` of three @fontsource packages into the session scratchpad (item d). No gitlink bump, `apps/degram` and `apps/revit-mcp` not staged in the framework. `workspace.py verify` reports gitlink != child HEAD, expected until plan 15 (not worked around). The 8 untracked pytest-artifact files and `.git/modules/degram/worktrees/dgp-t` were not touched (every component commit prints the harmless `dgp-t: Permission denied`).

## Commits

Component repo `apps/degram`, branch `degram/phase-1301` (committing repository: component), base `4f7eb136`:

| Task | Commit | Message |
|---|---|---|
| 1 | `30533c10` | feat(1301-13): DeGram shell tracer with sign-in gate, scope strip and explicit project picker |
| 1 (fix) | `e709572f` | fix(1301-13): keep the product-identity store out of the copy catalog import chain |
| 2 | `e2c04d24` | feat(1301-13): hidden upstream surfaces, degram theme preset, bundled fonts and the DG page |
| 2 (follow-up) | `955215a3` | chore(1301-13): regenerate locales/_keys.desktop.json for the degram copy catalog |

Framework repo (master): the `docs(1301-13)` commit with this SUMMARY, STATE.md and ROADMAP.md. No deletions in any commit.

## What was built

**Task 1 (tracer).** `use-degram-state.ts` is the one renderer mirror of the bridge (`getState` once, then `onState`/`onEvent`); toasts for `access-revoked` (project name) and `external-link-blocked` (action opens the browser from the click only) fire once, from the store, not per consumer. `startDegramSync(bridge, onNewScope)` calls back once per newly ready scope epoch (a scope already ready at mount is only recorded), and the host turns it into a fresh chat (D-19). `i18n.ts` holds every row of the UI-SPEC Copywriting Contract (en base, ru overlay; functions for interpolations). Components: `SignInState` (wordmark, session-ended copy above the login view, Connecting-to-DG loader, unreachable ErrorState with Retry request), `IsolationBootFailure` (full path in mono `break-all`, LogView, no button), `ScopeStrip` (company, project, document, Revit, Grasshopper; 24-char ellipsis with OverflowTip; neutral dots, accent dot only for pinned), `ProjectPicker` (Popover + Command variant menu, Loader while the list refreshes, compact ErrorState, search above 7, never auto-selects one project, Stop and switch / Keep working ConfirmDialog while a response runs), `DegramGate` (isolation failure, then sign-in, then project choice, else nothing; sits on `--z-setup` and portals popovers into itself), `DegramShellHost` (one mount in `ContribController` behind `$degramEnabled`; contributes the strip to `statusBar.left`; first-run locale ru for degram only; the stock boot-failure overlay yields to the isolation error).

**Task 2.** Hidden surfaces: `hidden-surfaces.ts` plus one-line conditionals at the wiring overlays (onboarding, onboarding chat gate, free-tier dialog, model picker overlay, model visibility, updates overlay), composer model pill, status-stack billing banner and free-tier strip, statusbar free-tier chip, version items and gateway switcher, `ModelCatalogMenu`, `FallbackModelsField`, remote setup in the device switch, and the Settings page (route enum without the hidden views, nav filter, default view `config:chat`, billing queries disabled). Preset `degram` (exact UI-SPEC values) is the default skin only for variant degram. Fonts: ten woff2 plus licenses and a NOTICE with provenance and hashes; `fonts.css` has no URL. DG page: segmented Project graph / Full DG, reload icon with `aria-label`, EmptyState before sign-in or project, Loader until paint, ErrorState with Reload page, bounds reported to main (CSS px times the window zoom factor), view hidden on unmount; route `/dg` and a sidebar row through the `routes` / `sidebar.nav` registry areas (the label follows the runtime locale).

## Fonts

Re-ran `npm pack` of `@fontsource/geist-mono@5.3.0`, `oswald@5.3.0` and `geist-sans@5.3.0` (LICENSE only) into this session's scratchpad `fonts13/`. All three tarball SHA-256 values and all four Cyrillic woff2 and three LICENSE hashes equal the values in 1301-ENV.md, so the font step was not aborted. Which faces render Cyrillic natively: Geist Mono (400, 500) and Oswald (400, 500) yes; Geist Sans no (Segoe UI fallback, decision above). Latin files come from `ui-v2/src/styles/tokens/fonts`; its Geist Mono latin files differ from the 5.3.0 package (older build) and were kept on purpose to stay inside the authorization (Cyrillic files only from the package); the two subsets use disjoint unicode-ranges, so mixing builds is safe.

## TDD

- **Task 1:** RED observed (`shell.test.tsx` failed to import: `degram-gate` etc. missing), then GREEN (22 tests at that point, 30 after the DG page and scope-epoch cases) after one test-design correction (first-state `painted` semantics).
- **Task 2:** honest caveat: the implementation of hidden-surfaces, DG page, preset and fonts was written before its tests (the first session was cut off mid-task and the order was lost). The tests are real: a mutation check removed the `model-pill` gate and `hidden-surfaces.test.tsx` failed on exactly that case, then passed after restoring; the new `ipc.test.ts` case ("shows the DG page again after a revocation blanked the view") failed with the `ipc.ts` fix disabled and passed with it. RED for the DG-page and preset tests themselves was not observed separately.
- **Rate-limit gap:** nothing was lost; Task 1 was committed, Task 2 was re-verified from disk (typecheck, lint, prettier, touched vitest files) before committing.

## Verification

All commands from `apps\degram\apps\desktop`; nothing launched.

| Check | Result |
|---|---|
| `npx vitest run --project ui src/degram` | 3 files, 60 passed (shell 30 incl. DG page and locale, hidden-surfaces 22 including source-audit rows, presets-fonts 8) |
| touched areas `--project ui src/degram src/i18n src/themes src/store/updates.test.ts src/components/boot-failure-overlay.test.tsx src/app/settings src/app/chat/composer src/app/shell` | 179 files, 1534 tests passed |
| `npx vitest run --project electron electron/degram` | 10 files, 158 passed (ipc.test.ts 22, +2 new) |
| `npm run typecheck` | exit 0 |
| eslint on touched files | 0 errors (the 6 warnings are in untouched `src/i18n/context.test.tsx`/`use-statusbar-items.tsx` lines) |
| prettier --check | clean |
| `rg https?:// src/degram/fonts.css` | no match |

**Full `--project ui`** (1183 files, 10522 tests, run before the e709572f fix): 3 files failed, 3 tests failed plus one file-level load failure. `src/store/updates.test.ts` was MINE (a hoisted `vi.mock` of `degram-flag` collided with the catalog importing the store); fixed in `e709572f` and green in the targeted rerun. The other two are unrelated to anything touched and reproduce in isolation: `src/store/voice-prefs.test.ts` (2 tests, localStorage `'false'` vs `null`) and `src/plugins/hermes-bots/cron-detail.test.tsx` (1 test, "Overdue since" label). They import none of the changed files. No ui baseline was recorded in 1301-ENV.md, so "pre-existing" is inferred from the import graph, not measured on the base commit.

**Full `--project electron`** after `e2c04d24` (1301-ENV.md baseline: run 1 43 failed / 3207 passed / 70 skipped of 3320, 28/317/10 files; stable set 44 lines): **40 failed / 3378 passed / 70 skipped of 3488, 26 failed / 330 passed / 10 skipped of 366 files**. 38 of the 40 failures are lines of the stable baseline set. The two others: `scripts/i18n-keys.test.mjs` was MINE (committed `locales/_keys.desktop.json` out of date after the new catalog keys) and is fixed in `955215a3` by `npm run i18n:keys` (the test then passes, 2 of 2); `payload-sign-cache > catalog trust cannot mask the embedded signature` is the documented flaky ENOTEMPTY temp-dir race. Nothing under `electron/degram` fails.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Catalog import chain broke `store/updates.test.ts`.** `degram/i18n.ts` imported the identity store, which en.ts/ru.ts load. Moved `degramFirstRunLocale` to `first-run-locale.ts`. Commit `e709572f`.

**2. [Rule 1 - Bug] `locales/_keys.desktop.json` out of date.** New English keys require the generated key list. Regenerated with the local script. Commit `955215a3`.

**3. [Rule 1 - Bug] Blank DG view after a revocation (plan 12 gap).** `reset()` blanks the view and no sign-in transition follows, so a project chosen afterwards met a blank DG page. `setDgMode` in `electron/degram/ipc.ts` now also shows the DG page when the view is blank and the session is signed in; the DG page calls it only while the view is blank. New tests in `ipc.test.ts`. Commit `e2c04d24`.

**4. [Plan interpretation] Font stacks are literal**, not `var(--dt-font-sans)` (cycle), see decisions.

**5. [Plan interpretation] More files than `files_modified`:** `host-actions.ts`, `use-dg-bounds.ts`, `first-run-locale.ts`, `degram-gate.tsx`, `shell-host.tsx`, `register-dg-page.tsx`, `test-harness.tsx`, `presets-fonts.test.ts`, plus one-line edits in `controller.tsx`, `wiring.tsx`, `boot-failure-overlay.tsx`, status-stack, statusbar items, `model-catalog-menu.tsx`, `fallback-models-field.tsx`, `local-device-switch.tsx`, `i18n/{types,en,ru,context}`, `locales/_keys.desktop.json`. `HIDDEN_SURFACES` has three extra ids (`model-settings`, `billing-settings`, `gateway-settings`) for the settings pages; the Settings default view for degram is `config:chat`.

**6. [Plan interpretation] Hidden-surface proof is partly a source audit.** The upstream shell (wiring, statusbar, status stack) cannot be rendered offline, so `hidden-surfaces.test.tsx` pins each id to its mount site in the source and renders the components that can be (`ModelCatalogMenu`, `FallbackModelsField`, gate, strip, DG page) asserting no `genpro`/`mimo` text. Not proven: the full rendered shell DOM.

## Findings for later plans

- **Profile switcher and rail are not gated.** The statusbar `profile-switcher`, the profile rail and the sessions sidebar still let a user move between local profiles, i.e. between per-scope profiles, without a DG selection. Not in the plan's list; plan 15 should decide (it touches D-19).
- **Shared-metrics consent** (`SharedMetricsConsentDialog` / strip, telemetry to Nous) is still mounted in degram. Not in the plan's list; decide in plan 15.
- **Boot failure surfacing:** main still calls `app.exit(1)` on HOME_OVERLAP before any window exists (plan 04), so `IsolationBootFailure` is reachable only if the failure arrives through the boot state (`$desktopBoot.error`, parsed by `parseIsolationBootError`). A window-less path (native dialog before exit, or a minimal error window) remains open for plan 15/16.
- **Plan 14:** `ScopeStrip` takes `document`, `bridges` and `onSelectDocument` props; the host does not yet feed them. `DegramActions.stopResponse` interrupts the active session over the gateway (`session.interrupt`); main-side cancellation of in-flight CAD reads is plan 14. Forward turn error codes to `degram.reportOutcome`.
- **Plan 16 (live):** native view placement (CSS px times `webFrame` zoom factor, UI Scale 90%), that the opaque native view really covers the placeholder, font painting (Geist Mono/Oswald Cyrillic), the `--z-setup` gate versus the titlebar drag region and window controls, the popover portalling into the gate, the `statusBar.left` order (900), and the `/dg` sidebar row on the real shell.
- Sign-out has no control yet (copy and bridge exist).

## Not verified (honest limits)

No pixels: nothing ran in Electron or a browser, so layout rules marked "backstop" in UI-SPEC (strip collapse order at narrow widths, 24-char ellipsis with Cyrillic, statusbar height stability) are covered only by class assertions. jsdom has no layout, so bounds are reported with zero size in tests. Fonts are verified by file presence, hashes and CSS declarations, not by painting.

## Known Stubs

None. (`ScopeStrip` document and bridge segments intentionally show "Select document" / "Checking" until plan 14 supplies data; documented above.)

## Threat Flags

None beyond the register. T-1301-13-01 (model pair disclosure): gate, source audit, and DOM-text tests (catalog dump and four rendered surfaces). -02 (re-enabling providers via settings): nav and route enum drop the pages, a stale `?tab=` coerces to chat settings, the fallback field and catalog menu render nothing. -03 (font CDN): no URL in `fonts.css`, preset has no `fontUrl`. -04 (implicit project selection): single-membership test, nothing selected on mount.

## Self-Check: PASSED

- FOUND (component, `apps/degram/apps/desktop`): `src/degram/{use-degram-state.ts,i18n.ts,scope-strip.tsx,project-picker.tsx,sign-in-state.tsx,isolation-boot-failure.tsx,dg-page.tsx,hidden-surfaces.ts,fonts.css,shell.test.tsx,hidden-surfaces.test.tsx}`, `src/assets/fonts/degram/` (13 files)
- FOUND commits in the component repo on `degram/phase-1301`: `30533c10`, `e709572f`, `e2c04d24`, `955215a3`; `git status` shows only the 8 known untracked pytest-artifact files
- Gitlink not bumped; `apps/degram` and `apps/revit-mcp` not staged in the framework; no deletions in any commit
