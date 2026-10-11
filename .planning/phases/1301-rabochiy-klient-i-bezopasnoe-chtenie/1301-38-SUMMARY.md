---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 38
subsystem: degram-desktop-sidebar
status: complete
completed: 2026-10-12
requires: [1301-37]
provides:
  - listed DeGram scope sessions carry the ready scope's profile, so the sidebar profile filter keeps them (F-04)
  - F-04 regression sequences (fresh open, A-B-A, A-refused C-A, A-Menu-A) through the real follow, request and refresh
affects: [1301-41]
tech-stack:
  patterns:
    - rows tagged from the renderer's own scope state, never from a backend-sent field
key-files:
  modified:
    - apps/degram/apps/desktop/src/degram/session-list.ts
    - apps/degram/apps/desktop/src/degram/session-list.test.ts
    - apps/degram/apps/desktop/src/degram/scope-route.test.ts
requirements-completed: []
---

# Phase 1301 Plan 38: stored sessions of a project stay visible in the sidebar (F-04)

**The sidebar showed «Сеансов пока нет» because `listScopeSessions` returned rows with no `profile`, an untagged row normalizes to `default`, and the sidebar profile filter drops every row whose profile is not the active scope profile. Rows are now tagged with the ready scope's own profile.**

## Root cause (systematic-debugging, evidence before fix)

The plan's hypothesis (no refresh on the `agreed` path of `followScopeRoute`) was not the cause. Reproduction in the plan-37 tree:

- A new `F-04` block in `scope-route.test.ts` drives the real `followScopeRoute`, the real `listSidebarSessions` DeGram branch (`$degramEnabled`, `setDegramGatewayForTests`), and the real `useSessionListActions().refreshSessions` against a fake backend that answers `session.list` for the active route only. It asserts what the sidebar shows: `filterSessionsByProfileScope($sessions, $profileScope)`.
- Before the fix 4 of 5 sequences failed, including the plain **fresh open** (visible list `[]`). Debug output at the failing point: `$sessions` held `[["a-2233", null], ["a-2210", null]]` while `$profileScope` was `scope-00000000000000aa`. The rows were fetched and stored, then hidden by `filterSessionsByProfileScope` (`normalizeProfileKey(undefined)` = `default` is not the scope profile).
- Why it looked intermittent live: a chat created in the running session is stored with its profile (optimistic row), so the list was visible until a wipe (`wipeSessionListsForGatewaySwitch` on a route switch) or a restart emptied the store; the refresh that refills it always returned untagged rows. The member's 2 sessions were on disk and returned by `session.list`, but never painted.

## What was built

- `session-list.ts`: `mapRow` takes the scope profile and tags each row with `state.scope.profile` when the scope is ready (route agreement is already enforced by the guard above it, so the rows are the scope profile's own). The backend's own `profile` field is still never copied. With no ready scope the row stays untagged (previous behaviour).
- `session-list.test.ts`: the tag is the scope profile, not the profile the backend sent.
- `scope-route.test.ts`: F-04 regression block (5 tests): fresh open, A to B to A (no row of B), A to refused C to A, A to Menu to A (route back on primary, state idle), and a G-25 check that every request is made on the ready scope's route only.

The profile filter (`profile-scope.ts`), the route follow (`scope-route.ts`), `use-background-sync.ts` and `gateway-switch.ts` are unchanged: the plan listed them as the expected fix location, but the reproduction showed they already refresh correctly.

## Verification (real output)

- Before the fix: `npx vitest run --project ui src/degram/scope-route.test.ts` 4 failed / 18 passed (F-04 sequences). After: 26/26 with `session-list.test.ts`.
- `npx vitest run --project ui src/degram src/app/chat/sidebar src/app/session`: 155 files, 1814/1814 passed (includes `backend-churn.test.ts`, G-25 green).
- `npx vitest run --project electron electron/degram`: 13 files, 251/251 passed.
- `npx vitest run --project ui` (whole): 10816 passed, 4 failed = the 3 known baseline (2 `voice-prefs.test.ts`, 1 `plugins/hermes-bots/cron-detail.test.tsx`) plus `floating-mode-memory.test.tsx`, a timing flake under full-suite load: it passes alone (2/2) and the file is untouched by this plan.
- `npm run typecheck` (apps/desktop): exit 0. ESLint on the 3 touched files: 0 errors, 3 padding-line warnings on lines this plan did not add.
- `python tools/degram/workspace.py verify`: fails with "Submodule gitlink does not match the selected component HEAD", the expected state while the local child commits (plans 37, 38, ...) are not bumped (plan 41's owner checkpoint).

## Deviations from Plan

### Auto-fixed Issues
**1. [Rule 1 - Bug] Fix site differs from the plan's expected direction**
- **Found during:** Task 1 reproduction.
- **Issue:** the plan expected a missing refresh in `scope-route.ts` / `use-background-sync.ts` / `gateway-switch.ts`; the defect is the untagged rows in `session-list.ts`.
- **Fix:** tag rows in `session-list.ts`; `session-list.test.ts` was edited (not in the plan's `files_modified`). The listed trio and `backend-churn.test.ts` were not changed.
- **Commit:** component `14bb25d2`.

**2. Task 1 test location:** the sequences live in `scope-route.test.ts` (as the plan's artifact says) and drive the real hook and request path rather than the `backend-churn.test.ts` socket harness, since the defect is downstream of the socket layer. `backend-churn.test.ts` is unchanged and green.

## Known Stubs
None.

## Threat Flags
None. T-1301-38-01 (a refill must not paint another scope's or user's rows): the tag is the ready scope's own profile, applied only after the route-agrees guard; tests assert no row of B after A to B to A, and the backend-sent `profile` is ignored. T-1301-38-02 (no re-dial of a released scope): the new test records every request route, all on the ready scope; `backend-churn.test.ts` green.

## Limits
- Not live-tested: the v12 to `degram-uat-b` to v12 and refused-pick scenarios need an installed build (plan 41 ships it).
- A refill on the `agreed` follow path and a wipe on release of the active scope were not added: the reproduction did not need them. If a live recheck still shows an empty list, those are the next candidates.
- Component commit `14bb25d2` is local only; nothing pushed, framework gitlink not bumped.

## Commits
- component `14bb25d2` fix(1301-38): tag listed scope sessions with the scope profile so the sidebar filter keeps them (F-04)

## Self-Check: PASSED
