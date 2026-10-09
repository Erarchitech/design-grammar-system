---
tags: [debugging, DeGram, v13.0, phase-1301, renderer, gateway]
date: 2026-10-09
status: open (critical, DGCL-02), fix planned for 0.1.6
---

# DeGram chat stays on the first scope profile after a project or company change

## Symptom

- After switching to a second project every turn failed with `CREDENTIALS_MISSING: no delegated DG credential is set`; the «Сеансы» list still showed and opened the first project's session.
- After the project's company was assigned, the same failure hit the first project too, shown as «Your DG session has ended…» although the DG session was alive.
- No relay request was made in any failed turn: it fails closed, nothing crossed scopes.

## Cause

Main opens one Hermes profile and backend per scope key (user + company + project) and hands the delegated credential to that backend (`electron/degram/scope.ts`). The renderer's gateway route (`src/store/gateway.ts`, `$activeProfile`) is set once at boot to the profile it restored (`[gateway-route win=main] active key=scope-0d96…`) and never follows a new scope: no route change is logged across eight project switches. The renderer therefore chats with, and lists sessions of, a backend that holds no credential. A company change creates a new scope key, so even the original project moves away from the restored profile.

Offline tests of plans 12/14 checked the scope state and the fresh-session request, not which backend the window talks to.

## Fix direction

On a ready scope epoch switch the active gateway route to `scope.profile` before `requestFreshSession`; refuse sends while route and scope disagree; list sessions of the active scope profile only. Recheck G-3 (sessions list) and G-5 (copy) afterwards.

## Related

- [[sessions/2026-10-09 Phase 1301 live UAT on PC1 and the 0.1.6 gap list]]
- `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md` (G-3, G-5, G-7)
