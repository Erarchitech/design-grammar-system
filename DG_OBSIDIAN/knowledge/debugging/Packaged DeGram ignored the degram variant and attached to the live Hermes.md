---
tags: [debugging, DeGram, v13.0, phase-1301, electron, isolation]
date: 2026-10-05
status: fix committed locally (child 910a060d); not rebuilt, not relaunched
---

# Packaged DeGram ignored the `degram` variant and attached to the live Hermes

## Symptom

Plan 1301-15's single authorized launch of the built installer app (from commit `386bd704`):

- window title `Hermes`; `desktop.log`: "attached to the running Hermes backend on 127.0.0.1:62917 … spawning nothing"; a WebSocket stayed open ~76 s;
- `%LOCALAPPDATA%\DeGram` was never created; `%APPDATA%\HermesBundledCommit386bd70` (stock identity userData) was created instead;
- Hermes listing before/after: 10 created, 22 modified, 0 deleted (a no-DeGram control window showed 12 heartbeat/sidecar modifications, so part is noise because Hermes was live); Hermes log `owner-backfill: stamped 11 legacy NULL-profile session row(s)`.

## Cause

1. `bundle-electron-main.mjs::productIdentity` baked the identity from the stamp `payload` (`bundled`) and ignored `variant: "degram"`; `com.erarchitech.degram` occurred 0 times in the packaged `electron-main.mjs`.
2. Plan 04's tests (and the plan's 38 green tests) set `HERMES_DESKTOP_VARIANT` in the environment — a packaged app never has it, so only a real launch could expose the gap.
3. The shell exports `HERMES_HOME=C:\Users\Admin\AppData\Local\hermes` and `ELECTRON_RUN_AS_NODE=1`; Hermes Desktop was running (5 `Hermes.exe`). With the stock identity, the inherited home and the existing backend were used.
4. An earlier `npm run payload` ran with the same unscrubbed environment; three `cache\uv` / `installs\…\.leases` entries in the Hermes home have mtimes in that window (may be the live Hermes).

## Fix

Child commit `910a060d` bakes the DeGram identity into the packaged main bundle (written test-first, RED end-to-end test that the packaged main contains `com.erarchitech.degram`); `degram-build.test.mjs` 22/22, `isolation.test.ts` 16/16, typecheck 0. The installer built before the fix must not be launched or distributed.

## Prevention

- Identity gate before any launch (documented in `docs/degram/CLEAN-INSTALL.md`): unpacked `app.asar.unpacked\dist\electron-main.mjs` must contain `com.erarchitech.degram`.
- Launch only with `HERMES_HOME` removed and `ELECTRON_RUN_AS_NODE` unset, ideally with Hermes Desktop closed (an empty before/after diff is impossible while it runs); scrub the environment for payload/build commands too.
- Offline tests that set the variant through the environment do not prove the packaged identity: always check the built artifact.

Related: [[sessions/2026-10-05 Phase 1301 executed through plan 14, plan 15 launch failed isolation|session]], [[knowledge/decisions/DeGram Phase 1301 client isolation, auth relay and Revit MCP fork|D-01..D-19 isolation decisions]].
