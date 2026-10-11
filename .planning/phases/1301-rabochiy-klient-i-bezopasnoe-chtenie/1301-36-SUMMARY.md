---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 36
subsystem: degram-release
status: complete
completed: 2026-10-11
requires: [1301-30, 1301-31, 1301-32, 1301-33, 1301-34, 1301-35]
provides:
  - DeGram 0.1.10 installer built from the pushed gitlink commit
  - data-service and design-grammars running the committed gap-round code
  - Russian owner test guide for the 0.1.10 live checks
affects: []
key-files:
  created:
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-0.1.10-TEST-GUIDE.md
  modified:
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-BUILD.md
    - apps/degram (gitlink 40bbd47f -> 93aa2b99)
    - apps/degram/apps/desktop/electron-builder.config.cjs (version 0.1.10, component commit 93aa2b99)
requirements-completed: []
---

# Phase 1301 Plan 36: 0.1.10 publication, services, installer, owner guide

**The 0.1.10 gap round is shipped for owner testing: component pushed, gitlink bumped, services rebuilt from committed code, installer built and checked. Nothing has been installed or exercised live; D-39..D-44 and G-25 acceptance is the owner's checkpoint.**

## What was done

- Component version commit `93aa2b99` (0.1.10) made on top of plans 33-35; the owner pushed `degram/phase-1301` (checked with `ls-remote`: remote head equals local head).
- Framework gitlink bump `8c4dc7c`; `python tools/degram/workspace.py verify` exit 0.
- Services (owner consent "rebuild ok"): rebuilt with `--no-cache` from a `git archive` export of framework HEAD, **not** the working tree, because the tree has other sessions' uncommitted runtime edits (`cypher_allowlist.py`, `dg_context.py`, `auth.js`, `ProjectsScreen.jsx`) that were not part of any plan. Containers were recreated with `docker compose up -d --no-build` and run the new image ids.
- Installer built from `D:\dgb\src` (clean clone detached at `93aa2b99`): `DeGram-Setup-0.1.10.exe`, 490,529,803 bytes, SHA-256 `b13d10efd776f83c000ec3c75f91fe03706b72c94e6b3d0beec1fef4bab40e88`. Details and artifact checks in `1301-BUILD.md`.
- `1301-0.1.10-TEST-GUIDE.md` (Russian, 12 steps) covers every must-have in the plan: owner grant on Connectors, token-free sign-in, GRANT_REQUIRED notice, ring sphere and pill, the six-row sidebar and scoped pins, the four navigation rows, «Модели» pinning and status-only strip, F-02 history, grant and membership revoke, and no backend churn on switches.

## Verification

- Live probes (no credentials used): `POST /auth/degram/session-exchange` without a session -> 401 `AUTH_REQUIRED`; `POST /auth/degram/exchange` with a `dgp_` bearer -> 401 `PAIRING_RETIRED`; UI :8080 -> 200.
- Installer artifact checks pass: `electron-main.mjs` has `session-exchange`, `GRANT_REQUIRED`, `degram-new-session`, `degram-state=` and no `auth/degram/exchange`; renderer bundle has `degram.nav` and `/degram/models` and no `pairing-panel`; revit-mcp adapter fixes present, `tests` absent; clone clean before and after.
- Component suites from plans 33-35 (typecheck 0, Electron 238/238, UI 10808 passed with 3 known baseline failures) were run against the same sources before the version bump.

## Limits

- Not installed or launched; no live UAT; `403 GRANT_REQUIRED` with a real signed-in user and the G-25 `desktop.log` check are in the owner guide.
- The running images do not contain the unrelated uncommitted `data-service`/`ui-v2` edits.
- A stale git worktree directory `.git/modules/degram/worktrees/dgp-t` still cannot be pruned (permission denied); commits are unaffected.
- D: has 3.4 GB free; the next installer build needs old installers removed first (owner decision).
- The phase is not complete: plan 16 (live UAT, not gap closure) and the owner checks above remain open; DGCL requirements are not marked complete.

## Self-Check: PASSED (build and publication scope)
