---
phase: 1308-dg-web-ui
plan: "17"
subsystem: degram-navigation
tags: [degram, electron, sidebar, projects, host-signal]
requires:
  - phase: 1308-dg-web-ui
    provides: "Plan 22 translated the hosted UI and established the EN/RU coverage gate"
provides:
  - "The DG page accepts the closed #degram-go=projects host signal"
  - "A DeGram Projects sidebar row routes through the existing dgGo bridge to the DG PROJECTS screen"
affects: [1308-18, 1308-21, degram-release-uat]
tech-stack:
  added: []
  patterns:
    - "Keep the host-page navigation vocabulary closed and matched across ui-v2, Electron main and IPC"
key-files:
  created: []
  modified:
    - ui-v2/src/lib/hostMode.js
    - ui-v2/tests/host-degram.test.mjs
    - apps/degram/apps/desktop/src/degram/sidebar-nav.ts
    - apps/degram/apps/desktop/src/degram/i18n.ts
    - apps/degram/apps/desktop/src/degram/sidebar.test.tsx
    - apps/degram/apps/desktop/electron/degram/dg-view.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.test.ts
    - apps/degram/apps/desktop/electron/degram/ipc.test.ts
key-decisions:
  - "Owner authorized two local component commits (1308-17 and later 1308-21) on degram/phase-1308 and a temporary waiver for gitlinkCommit ≠ componentHead only, until plan 1308-18."
  - "ipc.ts needed no edit: asRegion already validates against DG_REGIONS."
requirements-completed: [WEBUI-06]
coverage:
  - id: D1
    description: "Projects is accepted as a navigation signal on both sides; unknown regions remain rejected."
    requirement: WEBUI-06
    verification:
      - kind: unit
        ref: "node --test ui-v2/tests/host-degram.test.mjs ui-v2/tests/i18n.test.mjs (37/37)"
        status: pass
      - kind: unit
        ref: "Vitest ui sidebar (14/14), Electron dg-view and ipc (83/83)"
        status: pass
    human_judgment: true
    rationale: "No live Desktop or browser acceptance was authorized in this plan."
completed: 2026-10-12
status: complete-offline
---

# Phase 1308 Plan 17: DeGram Projects Navigation

**The framework accepts a Projects host signal, and the local DeGram component branch has a seven-row sidebar with «Projects» / «Проекты» between Models and Menu.**

## Accomplishments

- Added `projects` to the framework's closed `#degram-go=` parser and to the component's `DgRegion`, `DG_REGIONS` and fragment validator. Both sides still reject unknown regions such as `aiengine`.
- Added `dg-projects` after `models` in the sidebar, with the existing folder icon, `/dg` route and `dgGo('projects')` behavior. Added `nav.projects` to both DeGram catalogs and covered order, labels, click behavior and fragment handling in tests.
- Confirmed that Electron IPC's `asRegion` reads `DG_REGIONS`; no `ipc.ts` change was necessary. The component commit has six files rather than the plan's anticipated seven.

## Authorization and Repository Boundaries

- The owner replied «Подтверждаю все» to the proposed **two local component commits** (this plan and 1308-21) on the proposed `degram/phase-1308` branch, created from `degram/phase-1301` at `7edf519c`, and to the **one-check waiver**: `gitlinkCommit` may differ from `componentHead` between this child commit and plan 1308-18. It does not waive the remotes, required context hashes, absence of a competing authority, or installed component context. The owner separately authorized Vitest from `apps/degram` (fork `Erarchitech/degram`) for sidebar, dg-view and ipc tests.
- Framework implementation commit: `246d3bc feat(1308-17): accept hosted Projects navigation` (two `ui-v2` files). Component implementation commit: `5f1d3aa83a45a8d589dcda4e6f25603d50ef74ee feat(1308-17): add Projects sidebar navigation` (only six `apps/desktop` files). The component branch remains local; `origin/degram/phase-1308` is absent locally. No push or framework gitlink bump was performed.
- Before the component commit, `python tools/degram/workspace.py verify` passed with both component HEAD and gitlink at `7edf519c`. After the commit it exits 1 with **only** `Submodule gitlink does not match the selected component HEAD`, because the script checks that first. A separate read-only evaluation of its remaining guards confirmed fork/upstream remotes match, no competing authority, `componentContextInstalled` true, required context files present and hashed, and the additional `revit-mcp` component check succeeds. The new child HEAD is `5f1d3aa8`; the indexed framework gitlink remains `7edf519c`. This is the authorized temporary waiver, not a green `verify` result.

## Verification

- Framework: test-first host case failed before the parser update; afterward `node --test ui-v2/tests/host-degram.test.mjs ui-v2/tests/i18n.test.mjs` passed **37/37**.
- Component (from `apps/degram/apps/desktop`): `npx --no-install vitest run --project ui src/degram/sidebar.test.tsx` passed **14/14**; `npx --no-install vitest run --project electron electron/degram/dg-view.test.ts electron/degram/ipc.test.ts` passed **83/83**.
- Reviewed all six component file diffs, their staged file list, `git diff --check` and the committed file list. The child working tree is clean. `graphify update .` completed after the component edit with an optional missing SQL-parser warning and stale community-label notice; neither dependency installation nor LLM labeling was attempted.

## Deviations and Limits

- The `git commit --only` invocation printed a permission-denied warning while trying to delete stale `.git/modules/degram/worktrees/dgp-t` metadata, but Git created `5f1d3aa8` and the six-file commit and clean child status were independently verified. No attempt was made to remove that stale worktree metadata.
- No Desktop launch/build, installer, package installation, `hermes update`, paid inference, installed-profile write, push, live deployment or live visual acceptance occurred. The Projects row remains unshipped until separately authorized publication and gitlink alignment in plan 1308-18; owner UAT remains a separate gate.
- Other sessions' staged planning, Phase 1309 and vault changes were not included in either scoped implementation commit.

## Next Phase Readiness

The offline sidebar change is locally committed and tested. Plan 1308-21 may use the same owner-authorized branch for its separate language-setting commit; plan 1308-18 must obtain its own push/gitlink authorization and end the narrow waiver after the fork contains the child commits.

## Self-Check: PASSED (offline scope)

Both implementation commits exist in their respective repositories; tests pass and no component publication has occurred. The sole expected workspace preflight failure is explicitly waived until 1308-18, rather than reported as a pass.
