---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 33
subsystem: degram-desktop
status: complete
completed: 2026-10-11
requires: [1301-30]
provides:
  - Grant-backed credential mint through POST /auth/degram/session-exchange
  - GRANT_REQUIRED handling without opening or purging a project
  - Pairing store, panel, probe and IPC removed; retired degram-pairing.bin deleted once on start
affects: [1301-34, 1301-35, 1301-36]
key-files:
  modified:
    - apps/degram/apps/desktop/electron/degram/dg-session.ts
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts
    - apps/degram/apps/desktop/electron/degram/main-wiring.ts
    - apps/degram/apps/desktop/electron/degram/pairing-store.ts
    - apps/degram/apps/desktop/src/degram/degram-gate.tsx
    - apps/degram/apps/desktop/src/degram/use-degram-state.ts
    - apps/degram/apps/desktop/src/degram/i18n.ts
  deleted:
    - apps/degram/apps/desktop/src/degram/pairing-panel.tsx
    - apps/degram/apps/desktop/src/degram/pairing-panel.test.tsx
requirements-completed: []
---

# Phase 1301 Plan 33: DeGram access through the session exchange (D-39)

**DeGram mints every scope credential from the signed-in DG session; no token is pasted, read, stored or probed.** Access follows the owner/admin grant (plan 30/31). A project without a grant shows the grant-required notice on the start screen and does not open.

## Implementation

- `mint(project)` posts `/auth/degram/session-exchange {project}` through the DG partition with `X-DG-CSRF: 1`; `403 GRANT_REQUIRED` yields a distinct `grant-required` outcome, other 403 keeps the access-revoked path, 401 signed-out, network/5xx/429 unreachable.
- `scope.ts` opens a project directly on announcement; a grant revoked mid-scope closes the scope without a purge (membership intact, like D-27) and emits the same event.
- Pairing IPC channels and preload exposure removed; start-up deletes a stored `degram-pairing.bin` once and never writes it again.
- The start screen has no token field; the grant-required notice persists until dismissed (RU/EN copy per plan).
- Two retired files (`pairing-panel.tsx`, `pairing-panel.test.tsx`) were deleted after the owner named them in an explicit authorization (2026-10-11).
- Component commit `03785f3e` on `degram/phase-1301`, not pushed. The framework gitlink is unchanged (still `40bbd47f`).

## Verification

- `python tools/degram/workspace.py verify` — passed before the work.
- `npm run typecheck` — exit 0 (the 14 errors from the previously retained pairing-panel files are gone).
- `npx vitest run --project electron electron/degram` — 214/214.
- `npx vitest run --project ui src/degram src/api src/app src/store` — 6268 passed; 2 failures, both the recorded voice-prefs baseline.
- Acceptance greps: `auth/degram/exchange` / `Bearer dgp_` in non-test `electron/degram/*.ts` = 0; `PairingPanel` in `src` = 0.

## Limits

- Offline tests with a fake DG; no Desktop launch, build, install, push or live UAT. Live grant acceptance remains for plan 36.
- A stale git worktree directory (`.git/modules/degram/worktrees/dgp-t`) could not be pruned after the commit (permission denied); the commit itself succeeded.

## Self-Check: PASSED (offline scope)
