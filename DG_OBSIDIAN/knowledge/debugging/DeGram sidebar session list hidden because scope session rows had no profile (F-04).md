---
tags: [debugging, degram, phase-1301, sidebar, sessions]
date: 2026-10-12
---

# DeGram sidebar session list hidden because scope session rows had no profile (F-04)

## Symptom

0.1.10: after returning to project v12 the sidebar said «Сеансов пока нет», while the member's profile `scope-469f6d62ed486449` held 2 stored sessions (not hidden or archived).

## Root cause (plan 1301-38, reproduced offline before the fix)

Not the hypothesis of the plan (a missing refresh). `listScopeSessions` in `apps/degram/apps/desktop/src/degram/session-list.ts` returned rows without a `profile`. An untagged row normalizes to `default`, and the sidebar filter `filterSessionsByProfileScope` drops every row whose profile differs from the active scope profile. The rows were fetched and stored, then hidden (debug output `$sessions=[["a-2233",null],["a-2210",null]]` with `$profileScope=scope-…aa`). A chat created in the running session was stored with its profile, so the list looked right until a wipe or restart; the refill that followed was always untagged.

## Fix

`mapRow` stamps each row with the ready scope's own profile (`state.scope.profile`, after the route-agrees guard). The backend-sent `profile` field is still never copied. No ready scope: the row stays untagged. Component `14bb25d2`. `use-background-sync.ts` and `gateway-switch.ts` already refreshed correctly and are unchanged.

## Verification

Five reproduction tests drive the real `followScopeRoute`, `listSidebarSessions` and `refreshSessions` (4 of 5 failed before the fix). UI 1814/1814 in the touched areas; owner passed the live step on 0.1.11 (2026-10-12).

## Related

- [[sessions/2026-10-12 Phase 1301 gap plans 37-41 executed, DeGram 0.1.11 built and UAT result]]
- [[knowledge/debugging/DeGram chat stays on the first scope profile after a project or company change]]
