---
tags: [debugging, degram, phase-1301, grants, ux]
date: 2026-10-11
---

# DeGram refused project pick released the open project first (F-07)

## Symptom

In 0.1.10, choosing `degram-uat-c` (member `asiyagerey94@gmail.com`, role editor, **no DeGram grant**) showed no sidebar and no new-session pill; then «шлюз недоступен». The expected D-39 notice «Доступ DeGram к проекту … ещё не выдан» did not appear, and the DG page stayed on uat-c as if it were selected.

## Evidence

- data-service: `POST /auth/degram/session-exchange` 403 on every uat-c pick; `degram-grants.json` held grants only for `v12-hexagonal-facade-01` (unchanged since 21:40); `auth-memberships.json` showed the member as editor of uat-c (membership ≠ grant, D-39/D-48).
- `desktop.log` 22:43:05: v12 backend `exited (1)` right after the pick; no uat-c backend start.
- DG page: `GET /graph/degram-uat-c` 200 — the page had already switched.

## Root cause

`electron/degram/scope.ts` `selectProject` calls `closeCurrent()` (releases the open scope's backend) **before** `session.mint(project)`. A 403 `GRANT_REQUIRED` then goes to `grantRequired()` with no project left open, so the chat route points at a stopped backend. The host never tells the DG page to undo its project choice.

## Fix direction (plan 1301-37)

Mint first; only an `ok` mint closes the previous scope. A refusal keeps the open project, shows the notice over it, and sends the new host signal `#degram-project=<open project or empty>` so the ring follows the project actually open. `forbidden` for another project purges only that project's local profiles (D-19).

## Lesson

Before calling a "no access" report a defect, check grants and memberships separately: in DeGram a project member still needs an owner-issued grant.

## Related

- [[knowledge/decisions/DeGram access is granted by the project owner, not pasted by the user]]
- [[knowledge/decisions/DeGram connectors table and per-connector access requests (D-45..D-48)]]
- [[sessions/2026-10-11 DeGram 0.1.10 UAT and 0.1.11 fix round planned]]
