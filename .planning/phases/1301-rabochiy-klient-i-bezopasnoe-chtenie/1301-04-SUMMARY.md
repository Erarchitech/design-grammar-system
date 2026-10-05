---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 04
subsystem: degram-desktop-isolation
tags: [degram, electron, isolation, product-identity, nsis, updater-off, tdd, fail-closed]
requires: ["1301-02"]
provides:
  - "HERMES_DESKTOP_VARIANT=degram product identity (DeGram, com.erarchitech.degram, cli degram, degram:// scheme)"
  - "electron/degram/isolation.ts: resolveDegramPaths, assertNoHermesOverlap, DegramIsolationError (HOME_OVERLAP), isolatedBackendRequired, degramProcessEnv, deepLinkProtocols, updateMenuEntries"
  - "fixed DeGram home/userData under %LOCALAPPDATA%\\DeGram, inherited Hermes home sources ignored, overlap fails closed"
  - "unsigned per-user NSIS bundled builder target, publish null, updateMechanism external, renderer update poller gated off"
affects: [1301-13, 1301-15]
tech-stack:
  added: []
  patterns: ["fixedHome/fixedUserData short-circuit in the shared pure resolver (data-paths.mjs)", "product fact via feature-flags IPC -> preload -> nanostore"]
key-files:
  created:
    - apps/degram/apps/desktop/electron/degram/isolation.ts
    - apps/degram/apps/desktop/electron/degram/isolation.test.ts
    - apps/degram/apps/desktop/scripts/degram-build.test.mjs
    - apps/degram/apps/desktop/src/store/degram-flag.ts
  modified:
    - apps/degram/apps/desktop/product-identity.cjs
    - apps/degram/apps/desktop/product-identity.d.cts
    - apps/degram/apps/desktop/electron/product-identity.ts
    - apps/degram/apps/desktop/electron/data-paths.mjs
    - apps/degram/apps/desktop/electron/data-paths.d.mts
    - apps/degram/apps/desktop/electron/main.ts
    - apps/degram/apps/desktop/electron/preload.ts
    - apps/degram/apps/desktop/electron/install-stamp.ts
    - apps/degram/apps/desktop/electron-builder.config.cjs
    - apps/degram/apps/desktop/scripts/write-build-stamp.mjs
    - apps/degram/apps/desktop/scripts/before-build.mjs
    - apps/degram/apps/desktop/src/store/updates.ts
    - apps/degram/apps/desktop/src/store/updates.test.ts
    - apps/degram/apps/desktop/src/global.d.ts
    - apps/degram/scripts/bundles/desktop.py
    - apps/degram/scripts/bundles/desktop_prepare.py
    - apps/degram/tests/scripts/test_desktop_preparation.py
key-decisions:
  - "data-paths.mjs cannot import the TypeScript isolation module (the CI smoke driver runs it under Node type-stripping), so the shared resolvers take an optional fixedHome/fixedUserData that main.ts fills from isolation.ts; the pure short-circuit still lives in the one shared resolver"
  - "A failed overlap check logs the named diagnostic, calls app.exit(1) and throws: DeGram never falls back to another home; the in-window boot-failure overlay copy remains plan 13 (the process exits before any window exists)"
  - "degram stamps carry payload bundled (bundled runtime story) plus a new optional variant field set only for degram; degram builds are local commit builds (a release tag is refused by BuildRequest)"
  - "The degram feature flag is added to the hermes:feature-flags IPC reply next to guestOnboarding, not to resolveFeatureFlags, so the existing feature-flags tests stay byte-identical"
requirements-completed: []
requirements-partial: [DGCL-01]  # runtime isolation + build target config proven offline; clean-PC install protocol is plan 15
duration: ~75 min
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 04: DeGram runtime isolation and build identity Summary

`HERMES_DESKTOP_VARIANT=degram` is now a fully isolated product: its own name/appId/CLI/protocol/userData/lock, a fixed home under `%LOCALAPPDATA%\DeGram` that ignores every inherited Hermes home source and fails closed on overlap, no host-backend attach, no updater, and an unsigned per-user NSIS bundled target. All of it is proven by offline tests; nothing was built, launched or packaged.

## Authorization and boundaries

Per the orchestrator's `owner_authorization_resolved`: local commits on component branch `degram/phase-1301` only. No push, no `hermes update`, no Desktop launch/build/dev server/electron-builder, no Docker, no write to `%LOCALAPPDATA%\hermes` or the installed Hermes profile/userData (the profile directory was only existence-listed read-only), no package install, and the `apps/degram` gitlink was **not** bumped (plan 15).

## Commits (component repo `apps/degram`, branch `degram/phase-1301`, repo: component)

| Task | Commit | Message |
|---|---|---|
| 1 | `7c9e6145` | feat(1301-04): degram product identity, fixed home and fail-closed overlap |
| 2 | `a05e4894` | feat(1301-04): degram NSIS bundled target, updater off, variant lists |

`git -C apps/degram status --short` is empty after both commits. Framework commit for this SUMMARY/STATE/ROADMAP is a separate framework-repo `docs(1301-04)` commit.

## What was built

**Task 1 (tracer): identity, fixed home, fail-closed overlap, no host attach**
- `product-identity.cjs`: variant `degram` (display `DeGram`, appId `com.erarchitech.degram`, cliName `degram`, channel `null`, msix org `Erarchitech.DeGram`); allow-list error text updated; ambient canary/commit selectors never alter a degram identity. `.d.cts` gets `degram: boolean`.
- `electron/degram/isolation.ts` (pure, dependency-injected): `resolveDegramPaths` returns `<LOCALAPPDATA>\DeGram\{home,userData}` and never reads the registry or filesystem or any Hermes selector; `assertNoHermesOverlap` throws `DegramIsolationError(code 'HOME_OVERLAP', path)` when root/home/userData equals, lies inside or contains any Hermes home candidate (env `HERMES_HOME` including `profiles/`-rooted normalization, registry `HERMES_HOME`, `%LOCALAPPDATA%\hermes` and its suffixed form, `~/.hermes`), case-insensitive on Windows and independent of separators and trailing slashes.
- `data-paths.mjs`: `resolveDesktopHermesHome({fixedHome})` and `resolveDesktopUserData(default, env, fixedUserData)` return the fixed value before any env, registry or legacy `~/.hermes` lookup; all non-degram behaviour is unchanged.
- `product-identity.ts`: `applyDesktopIdentity` always pins userData to the isolation-resolved directory for degram (throws if none is supplied), so the Electron userData directory and single-instance lock are DeGram's own.
- `main.ts`: the overlap check runs before the first userData pin and before `HERMES_HOME` is read; on success `process.env.HERMES_HOME` is pinned to the fixed home, `HERMES_DESKTOP_USER_DATA_DIR`/`HERMES_DATA_DIR_SUFFIX` are dropped and `HERMES_DESKTOP_ISOLATED_BACKEND=1` is set; `ISOLATED_BACKEND` is `isolatedBackendRequired(PRODUCT_IDENTITY, env)` (always true for degram), which disables host-backend attach; the four `BrowserWindow` titles use an identity-derived title; the deep-link protocol is `degram://` (`degram-dev://` for a dev server). The AppUserModelId already resolves to `PRODUCT_IDENTITY.appId` for degram because `applyDesktopIdentity` returns its display name.

**Task 2: variant lists, updater off, NSIS bundled target**
- `electron-builder.config.cjs`: degram gets scheme `degram`, `win.target ['nsis']`, `nsis {oneClick false, perMachine false, allowToChangeInstallationDirectory true, artifactName DeGram-Setup-${version}.${ext}}`, top-level artifact name `DeGram-Setup-${version}.${ext}`, `agent-payload` extraResources, `publish` and `mac.publish` null; signing left as-is (no Azure env means no signer, i.e. unsigned).
- `write-build-stamp.mjs`: degram is bundled-semantics (payload `bundled`, completed payload contract required), `updateMechanism: 'external'` on every platform, and an optional `variant: 'degram'` stamp field (typed in `install-stamp.ts`).
- `before-build.mjs`: degram returns before any MSIX asset/extension/manifest staging.
- Renderer: `degram` added to the `hermes:feature-flags` reply, exposed by the preload as `degramEnabled`, read through nanostore `$degramEnabled`; `startUpdatePoller` returns immediately for degram, and the native "Check for Updates…" menu entries are omitted (`updateMenuEntries`).
- Python: `scripts/bundles/desktop.py` gets `VARIANTS` (with `degram`) and `package_targets()` (win32 degram -> `--win nsis`); `desktop_prepare.py` accepts `degram` as a payload-bearing variant (TUI and web workspaces built) and refuses a release tag for it.

## TDD

RED observed for each, then GREEN:
- Task 1: `isolation.test.ts` failed to import (module absent) before `isolation.ts` was written. Honest caveat: the small identity-variant edits to `product-identity.cjs`/`data-paths.mjs` were made before that RED run (their tests live in the same file, so they were not independently red).
- Task 2: `scripts/degram-build.test.mjs` run before the builder/stamp edits: 7 of 10 failed. Renderer poller gate: the new `updates.test.ts` case failed (`checkMock` called) with the gate temporarily removed, then passed with it restored. Python: 2 new tests failed (`package_targets`/`VARIANTS` absent) before the change.

## Verification

| Check | Result |
|---|---|
| `npx vitest run --project electron electron/degram/isolation.test.ts electron/product-identity.test.ts electron/data-paths.test.ts electron/singleton-lock.test.ts` | 3 files pass; `singleton-lock` has the stable baseline failure only (`removeStaleSingletonLock unlinks only a provably-dead owner`, EPERM symlink on Windows) |
| `scripts/degram-build.test.mjs`, `scripts/write-build-stamp.test.mjs`, `electron/updater/updater.test.ts` | all pass |
| `--project ui src/store/updates.test.ts` | 83 passed |
| `tests/scripts/test_desktop_preparation.py` via `scripts/run_tests.sh` (`HERMES_PYTHON` = `.venv` python) | 12 passed |
| `python scripts/bundles/desktop.py --help` | `--variant {bundled,store,light,degram}` |
| `npm run typecheck` (apps/desktop) | exit 0 (both commits) |
| `eslint` on touched electron/src files, `prettier --check` | clean |

### Full electron vitest vs 1301-ENV.md baseline

Run after the Task 2 changes: **49 failed / 3227 passed / 70 skipped (3346 tests), 29 files failed / 318 passed / 10 skipped (357 files)**, 310 s. Baseline (run 1): 43 failed / 3207 passed / 70 skipped (3320), 28 / 317 / 10 (355). Net +26 tests (new tests), +20 passes.

Comparison against the 44 stable baseline lines:
- 41 of the 44 reproduce; 3 baseline lines passed this time (`bundle-skew ... never lazy-fetches from origin`, `store-package-version ... ordinary release manifest v0.27.1`, and the `side-by-side.windows.test.mjs` file-load line is present in a different format only).
- 9 failure lines are outside the stable list, all in the documented flaky class (git/process-heavy `Test timed out in 5000ms`, or Windows temp-dir teardown EBUSY/ENOTEMPTY): `bundle-skew` x2, `desktop-plugin-install` x1, `git-worktree-ops` x2, `audit-bundle-arch` x1, `store-package-version` x1, `payload-sign-cache` "catalog trust cannot mask the embedded signature" x1 (ENOTEMPTY on cleanup). A targeted re-run of `audit-bundle-arch`, `payload-sign-cache`, `store-package-version` and `git-worktree-ops` passes everything except the stable baseline test `payload-sign-cache > native verification binds cached bytes to the publisher and timestamp`. No failure concerns identity, home resolution, updater or any file this plan touched.

## Workspace verify

`python tools/degram/workspace.py verify` now reports "Submodule gitlink does not match the selected component HEAD". This is the expected condition recorded in the orchestrator brief: the child branch `degram/phase-1301` moved ahead of the pinned gitlink `8b66a510` (child HEAD `a05e4894`) and the gitlink is intentionally not bumped until plan 15. It was not worked around.

## Deviations from Plan

### Auto-fixed / scope notes

1. **[Rule 3 - Blocking] `fixedHome`/`fixedUserData` parameters instead of data-paths.mjs importing isolation.ts.** The plan says data-paths.mjs "delegates to" isolation.ts, but data-paths.mjs is plain `.mjs` consumed by the CI smoke driver under Node type-stripping and cannot import extensionless TypeScript. The shared resolver gained an optional fixed value that main.ts supplies from isolation.ts; the early return before env/registry/legacy lookups is exactly as specified and is tested. Added `electron/data-paths.d.mts` to the touched files (types for the new option).
2. **[Rule 2 - Missing critical] Extra files beyond `files_modified`:** `electron/preload.ts`, `src/global.d.ts`, `src/store/degram-flag.ts`, `src/store/updates.test.ts`, `electron/install-stamp.ts`, `tests/scripts/test_desktop_preparation.py` (the plan's feature-flag wiring and Python acceptance require them), plus `isolation.ts` helpers `deepLinkProtocols`, `updateMenuEntries`, `degramProcessEnv` so the protocol, menu and env behaviour are unit-testable without booting Electron.
3. **Feature flag placement.** Added to the IPC reply rather than `resolveFeatureFlags` to keep `feature-flags.test.ts` (deepEqual on the flag set) unchanged.
4. **Canary/commit selectors ignored for degram** in `product-identity.cjs` (no feed exists), so ambient `HERMES_PAYLOAD_TAG`/`HERMES_BUILD_COMMIT` cannot turn the identity into a suffixed or feed-bearing one.

## Findings for later plans

- **NSIS is not admitted by the prepared-packaging pipeline (plan 15).** `scripts/run-electron-builder.mjs` (`sourceFormats`), `scripts/prepare-packaging-tools.mjs` (`supported`, default `formats`) admit only `dir`/`msix`/`zip` on win32, and the offline toolset acquisition covers makeappx/signtool/dlib, not the NSIS toolset. `desktop.py` now asks for `--win nsis`, so a real degram packaging run will fail `--validate-only` ("Package formats were not prepared: nsis") until plan 15 extends admission and acquires the NSIS toolset under its own authorization. Config-level correctness (what plan 04 owns) is proven; the packaging pipeline was deliberately not extended here (build/tool acquisition is out of scope and unauthorized).
- **Boot-failure overlay.** Overlap failure exits the process (named diagnostic on stderr: `[degram] boot refused (HOME_OVERLAP): ...`) before any window exists; plan 13 owns presenting this in the UI, which will need a different surfacing path than an in-renderer overlay or a pre-exit native dialog.
- **Linux relaunch path.** `electron/entry.ts` (Linux-only Wayland relaunch) still resolves the home from the environment; degram's target is Windows NSIS, so it was left unchanged.

## Known Stubs

None.

## Threat Flags

None. Mitigations for T-1301-04-01..04 are implemented and tested; T-1301-04-05 (unsigned NSIS) accepted per plan.

## Self-Check: PASSED

- Created files present: `electron/degram/isolation.ts`, `electron/degram/isolation.test.ts`, `scripts/degram-build.test.mjs`, `src/store/degram-flag.ts` (all under `apps/degram/apps/desktop/`).
- Commits exist in the component repo: `7c9e6145`, `a05e4894` (verified with `git -C apps/degram log`).
- `git -C apps/degram status --short` is empty; no deletions in either commit; gitlink untouched.
