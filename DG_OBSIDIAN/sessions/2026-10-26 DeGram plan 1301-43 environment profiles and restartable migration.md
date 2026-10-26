---
tags: [session, degram, dgmodes, profiles, migration]
date: 2026-10-26
---

# DeGram plan 1301-43 — environment profiles and restartable migration

## Outcome

Executed `/gsd-execute-phase 1301 --wave 2 --no-transition` inline on the current checkout. GSD places plan 43 in **computed DAG wave 2**, despite declared wave 30; plans 04/07/08 in the same wave were already complete. Plan 42's implementation/SUMMARY already existed at session start.

Plan 43 is offline complete: origin-owned profiles/manifests, scoped purge/revoke, and journaled local migration which preserves history and retained bindings. Source changes remain uncommitted in `apps/degram` on `degram/milestone13`; child HEAD/framework gitlink still `b619e02e3725869b1ab5125951d3311e3656dc9a`.

## Implementation and findings

- Profile identity is SHA-256 over UTF-8 `dg-profile-v2`, canonical origin, user/company/project joined with U+001F; 32 lowercase hex suffix. Python/Electron shared vector: `https://dg.example.test`, alice/acme/tower → `scope-d882f6d4f1a222fd5d31569011e990ef`.
- Version-2 manifests bind origin/environmentId and scope. All four profile CLI paths carry explicit environment argv; adapter rejects conflicting scope or an unexpected profile result.
- Migration uses proven Developer ownership, stops candidate backends, writes pending journal before local rename, then manifest and complete stage; interrupted migration resumes. Collision/malformed/unowned data remain preserved, not assigned to Demo or uploaded.
- Fixed adjacent main-wiring environment forwarding and a backend gate which recognized only legacy 16-hex names. New 32-hex names must receive the same inactive-scope start refusal. See [[knowledge/debugging/Environment-owned profile names must remain covered by the scope backend gate]].
- Migration failure blocks selection/ensure; heartbeat consumes its rejection without skipping revocation checks.
- Main settings reader distinguishes ENOENT from read/permission errors rather than silently claiming a default target.

## Verification

- Python focused filesystem tests, existing child venv: **69 passed**, zero skips.
- Exact Electron selector (profiles-cli/scope): **79 passed**.
- Expanded Electron selector (`electron/degram/` plus desktop-profile): **295 passed**, 16 files.
- Desktop typecheck: passed; workspace verify: passed; diff whitespace check: passed.
- Changed sources: UTF-8 without BOM, consistently LF or CRLF per file.
- Schema/UI gates do not block. Codebase-drift tool skipped with `git-diff-failed`, not a verified PASS.
- Offline AST refresh finished **exit 0**, manifest `2026-10-26T00:31:49Z`; SQL grammar is unavailable, optional SQL index remains incomplete. No paid inference.
- PATH Python lacked ruamel.yaml and initially produced 65 setup errors; used existing venv without installing anything. Intermediate test/typecheck defects were fixed and all named final checks passed.

Canonical execution evidence: `.planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-43-SUMMARY.md`.

## Git and authority

Framework session-end save includes only this session's tracking hunks and new notes/SUMMARY, not unrelated dirty work. Component commits remain separately gated by plan 43; no component commit/push or gitlink bump. Pre-existing plan-42 source/SUMMARY and unrelated framework modifications are not swept into this session commit. Generated graph outputs remain uncommitted.

No builds, installs, Desktop launches, installed-home reads, secret reads, live stand calls, package installs, worktrees or delegation. Main runtime still uses the fixed cookie partition until plan 44; profile tests do not prove runtime/cookie isolation. DGMODE requirements, DGCL, HOST-05, plan 1301-16 and Phase 1301 acceptance remain open. Primary Phase 1303 state/counters are preserved.

## Continue

```text
/gsd-execute-phase 1301 --wave 3 --no-transition
```

Next incomplete plan in that wave: **1301-44**, safe target-switch coordinator and real main/session/view/backend lifecycle. Do not use historical declared waves 29–34 as execution selectors: the installed GSD tool computes the waves from dependencies. Later: 45 selector/renderer, 46 composed offline acceptance, 47 separately authorized publication/build/install/live acceptance.

Related: [[sessions/2026-10-25 DeGram dual mode plans 42-47 prepared]], [[knowledge/decisions/DeGram dual mode is an additive plan slice with explicit runtime gates]], [[00-home/Current priorities]].
