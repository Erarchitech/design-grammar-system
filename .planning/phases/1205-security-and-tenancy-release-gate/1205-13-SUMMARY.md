---
phase: 1205-security-and-tenancy-release-gate
plan: "13"
subsystem: ui-v2 identity surface
tags: [react, vite, session-cookie, invitations, d-01, d-05, membership, api-docs]

requires:
  - phase: 1205-11
    provides: "apiClient.js (apiFetch, ApiError, AUTH_EXPIRED_EVENT, dataServiceBase)"
  - phase: 1205-12
    provides: "GET/POST /projects, members endpoints, POST /auth/invites, POST /auth/accept-invite"
provides:
  - "ui-v2/src/lib/auth.js: login, logout, currentUser, acceptInvite, changePassword, purgeLegacyLocalAuth (server-backed, no browser storage)"
  - "App.jsx: async signed-in state from /auth/me, dg-auth-expired -> signed out, stale remembered project cleared"
  - "Landing auth card: Log in / Accept invite only (Register removed)"
  - "ProjectsScreen: membership-scoped tiles with role, POST /projects create, owner members panel (list / invite / remove)"
  - "API docs: proxy rows corrected, principal-types page added"
affects: [1205-14, 1205-15, 1205-16, 1205-18]

key-decisions:
  - "currentUser() maps the server username to both email and name (fields the landing UI already renders); memberships and isAdmin ride along for the project guard"
  - "login/acceptInvite re-read /auth/me after the cookie is set so the returned user carries memberships; falls back to the login response if /auth/me is unavailable"
  - "App exposes selectProject, which refreshes memberships before setting the project, so a just-created/joined project is not cleared by the stale-project effect"
  - "Landing username field is a plain text 'Username' input (server usernames are not required to be emails); invite mode has no username field"
  - "Removed the Neo4j URI display from ProjectsScreen footer (no longer a browser-visible fact after 1205-11)"

requirements-completed: []  # ALGN12-17 spans 1205-14/15/16/18; not closed by this plan alone

coverage:
  - id: D1
    description: "D-01: auth.js is a thin client of /auth/*; nothing in localStorage, no hashing"
    requirement: "ALGN12-17"
    verification:
      - kind: other
        ref: "grep over ui-v2/src for localStorage.setItem(\"dg_users\", crypto.subtle.digest, auth.register, hashPassword -- 0 each; auth.js only removeItem on the two legacy keys"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-05: no Register mode; legacy dg_users/dg_current_user purged on mount, hashes not migrated"
    requirement: "ALGN12-17"
    verification:
      - kind: other
        ref: "LandingLayer modes login|invite; App mount effect calls purgeLegacyLocalAuth; build green"
        status: pass
    human_judgment: false
  - id: D3
    description: "T-1205-13-03: invite code rendered once from the response, held only in component state, never persisted"
    requirement: "ALGN12-17"
    verification:
      - kind: other
        ref: "ProjectsScreen.jsx: only localStorage use is the pre-existing dgv2_project_shots read; invite state cleared on project switch and Dismiss"
        status: pass
    human_judgment: false
  - id: D4
    description: "T-1205-13-05: docs no longer advertise /neo4j/* or /n8n/*"
    requirement: "ALGN12-18"
    verification:
      - kind: other
        ref: "grep -c '/neo4j/\\*\\|/n8n/\\*' 01-getting-started.js -> 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live behaviour: login, invite round trip, create project (409 message), members panel, expired-session return to login against the rebuilt stack"
    requirement: "ALGN12-17"
    verification: []
    human_judgment: true
    note: "Deferred to 1205-18 live smoke; the UI container was not rebuilt in this plan and the bootstrap admin login is the owner's step"

duration: ~20min
completed: 2026-09-29
status: complete
---

# Phase 1205 Plan 13: Login, Invitations and Membership-Scoped Projects (UI) Summary

**The V2 UI's identity is now server-owned: a thin `/auth/*` client, an asynchronous signed-in state that returns to login on any 401, an invitation-only landing card, and a Projects screen that lists only the caller's projects with roles and lets owners invite and remove members; the in-app API docs no longer advertise the removed Neo4j/n8n proxies.**

## Accomplishments

- **Task 1 (auth client, state, card):** `auth.js` rewritten to six exports on `apiFetch`; `currentUser()` returns `{email, name, isAdmin, memberships}` or null on 401. `App.jsx` starts with `user = null`, purges the legacy localStorage accounts, resolves `/auth/me`, listens for `dg-auth-expired`, and forgets a remembered project the user is not a member of (admins keep it). `LandingLayer.jsx` swaps Register for an `invite` mode (invite code + new password, 12-character client floor; login only requires non-empty since the server is the authority); sign-out awaits `auth.logout()`.
- **Task 2 (projects, docs):** tiles show `role · N nodes`; New Project posts to `/projects` and opens the project only on success (409 shown as "That project name is unavailable."). An owner/admin-only Members panel lists members, invites via `/auth/invites` (invited -> one-time code in a read-only field with the specified hint; member-added -> confirmation) and removes members (LAST_OWNER message surfaced). `01-getting-started.js`: `/neo4j/*` and `/n8n/*` rows deleted, `/reasoner/*` row added, no-direct-access sentence added. `02-authentication.js`: new "Principal Types" page (browser session, project-bound dgc_ token, internal service token for n8n only) and the requirement that VALIDATOR and COMPUTGRAPH PUBLISH receive the same dgc_ token.

## Task Commits

1. **Task 1: server-backed auth client, async state, login/accept-invite card** - `ba50a7f` (feat)
2. **Task 2: membership-scoped Projects screen, members panel, API docs** - `ddc32b6` (feat)

## Verification

| Check | Result |
|---|---|
| `npm --prefix ui-v2 run build` (after each task) | green |
| grep over `ui-v2/src`: `localStorage.setItem("dg_users"`, `crypto.subtle.digest`, `auth.register`, `hashPassword` | 0 each |
| `grep -c AUTH_EXPIRED_EVENT App.jsx` / `grep -c acceptInvite LandingLayer.jsx` | 3 / 1 |
| `grep -c '/neo4j/\*\|/n8n/\*' 01-getting-started.js` | 0 |
| `grep -c /auth/invites ProjectsScreen.jsx` | 1 |
| `localStorage` in ProjectsScreen.jsx | only the pre-existing `dgv2_project_shots` read (line 45) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale-project effect would clear a just-created project**
- **Found during:** Task 1 design
- **Issue:** the plan's "clear the remembered project when memberships lack it" effect runs against memberships fetched at sign-in; creating or joining a project then selecting it would immediately clear it.
- **Fix:** `App.selectProject` refreshes `/auth/me` before setting the project and is passed to ProjectsScreen as `onProject`; ProjectsScreen also receives `user` for the admin check.
- **Files modified:** `ui-v2/src/App.jsx`
- **Commit:** `ba50a7f`

**2. [Rule 2 - Missing critical] Removed the Neo4j URI footer**
- ProjectsScreen displayed "Neo4j connected · bolt://neo4j:7687" using a config key that `getConfig` no longer returns (recorded in 1205-11). Replaced with the project count only.
- **Commit:** `ddc32b6`

**3. [Rule 3 - Blocking] `/reasoner/*` docs row upstream**
- The plan asked for a `/reasoner/*` row without an upstream; `ui-v2/nginx.conf` proxies it to `data-service:8000`, so the row states that.

## Notes for downstream plans

- The live UI container was not rebuilt here; live smoke (login, invite round trip, members panel) belongs to 1205-18. `ui-v2/nginx.conf` still carries `/neo4j/` and `/n8n/` locations and `entrypoint.sh` still writes the legacy credential keys (1205-11 note); removal belongs to 1205-15.
- `changePassword` is exported but has no UI surface yet (plan scope was the client export only).
- Invite `expiresAt` is returned as ISO-8601; the panel shows the fixed 72-hour hint text and does not render the timestamp.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register.

## Self-Check: PASSED

Files present: `ui-v2/src/lib/auth.js`, `ui-v2/src/App.jsx`, `ui-v2/src/landing/LandingLayer.jsx`, `ui-v2/src/screens/ProjectsScreen.jsx`, `ui-v2/src/screens/apidocs/content/01-getting-started.js`, `02-authentication.js`; commits `ba50a7f` and `ddc32b6` in git log.
