---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 12
subsystem: degram-desktop-electron-main-dg-integration
tags: [degram, electron-main, dg-session, delegated-token, partition-sign-in, webcontentsview, origin-allowlist, scope-controller, heartbeat, revocation, ipc-bridge, tdd]
requires: ["1301-04", "1301-05", "1301-10", "1301-11"]
provides:
  - "electron/degram/dg-config.ts: DG origin (env DEGRAM_DG_ORIGIN, then <degram home>/degram.json {dgOrigin}, default http://localhost:8080; bare http(s) origin only, invalid value fails closed), DEGRAM_DG_PARTITION = persist:degram-dg, relayBaseUrlFor(origin) = origin + /data-service, resolveRevitAdapter and degramBackendEnv (HERMES_DEGRAM=1, HERMES_HOME, DEGRAM_PYTHON, DEGRAM_REVIT_MCP_DIR)"
  - "electron/degram/dg-session.ts: createDgSession (/auth/me, POST /auth/delegated-token with X-DG-CSRF: 1, POST /auth/logout), createNetPartitionFetch on Electron net.request with a session cookie mode and an explicit-Cookie fallback behind one interface, DEGRAM_TOKEN_RENEW_S = 600, DEGRAM_HEARTBEAT_S = 60"
  - "electron/degram/scope.ts: createScopeController (explicit selection, profile ensure, backend, mint, degram.credentials.set, epoch per selection), signOut, checkAccess (heartbeat/focus/outcome), reportOutcome, isSettled barrier, AGENT_OUTCOME_CODES, renewal and heartbeat timers on an injected clock"
  - "electron/degram/dg-view.ts: createDgView, isAllowedDgUrl, DG_VIEW_WEB_PREFERENCES (frozen, no preload), graph/full modes, sign-in page, reset, partition wipe, http(s)-only openExternalConfirmed"
  - "electron/degram/ipc.ts + channels.ts: createDegramRuntime (renderer-safe DegramState, clear-then-notify publishing), registerDegramIpc (trusted sender, validated payloads), DEGRAM_CHANNELS (degram:*), DegramBridge type; channels.ts is import-free so the sandboxed preload can bundle it"
  - "electron/degram/main-wiring.ts: createDegramMainWiring (mounts the DG view, sends to the DeGram window only, window focus hook, dg_session cookie-change hook)"
  - "electron/degram/gateway-rpc.ts + profiles-cli.ts: one-shot JSON-RPC call to a backend /api/ws; python -m degram_variant.profiles runner with interpreter resolution (payload python or source-checkout python)"
  - "preload.ts: window.hermesDesktop.degram {getState, onState, onEvent, selectProject, signOut, setDgMode, reloadDg, setDgBounds, reportOutcome, openExternalConfirmed}; no token, credential or cookie getter; typed in src/global.d.ts"
  - "main.ts hooks: degramSpawnEnv at both backend spawn sites, lazy ensureDegramWiring attached in createWindow (DeGram identity only)"
  - "Renderer events session-ended, access-revoked {project, purged}, external-link-blocked {url}, dg-unreachable, dg-reachable"
affects: [1301-13, 1301-14, 1301-15, 1301-16]
tech-stack:
  added: []
  patterns:
    - "Every collaborator (partition fetch, native view factory, profile CLI, backend handle, gateway socket, clock, logger, renderer sender, ipcMain, cookie jar) is injected, so the suites run in the electron vitest project with no Electron"
    - "State barrier: the runtime publishes to the renderer only while scope.isSettled(); a lost session counts as unsettled from the 401 until the clearing finished, so no stale user or project is repainted ahead of the wipe"
    - "One clearing sequence at a time (runClearing); a concurrent trigger waits and is skipped, so a sign-out and its own cookie wipe never produce a session-ended event"
    - "Timers: renewal only while a scope is open, heartbeat only while a signed-in session is live; a failed renewal sets renewPending and retries on the next heartbeat tick (one attempt per tick, no burst)"
key-files:
  created:
    - apps/degram/apps/desktop/electron/degram/dg-config.ts
    - apps/degram/apps/desktop/electron/degram/dg-config.test.ts
    - apps/degram/apps/desktop/electron/degram/dg-session.ts
    - apps/degram/apps/desktop/electron/degram/dg-session.test.ts
    - apps/degram/apps/desktop/electron/degram/scope.ts
    - apps/degram/apps/desktop/electron/degram/scope.test.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.ts
    - apps/degram/apps/desktop/electron/degram/dg-view.test.ts
    - apps/degram/apps/desktop/electron/degram/ipc.ts
    - apps/degram/apps/desktop/electron/degram/ipc.test.ts
    - apps/degram/apps/desktop/electron/degram/channels.ts
    - apps/degram/apps/desktop/electron/degram/main-wiring.ts
    - apps/degram/apps/desktop/electron/degram/main-wiring.test.ts
    - apps/degram/apps/desktop/electron/degram/gateway-rpc.ts
    - apps/degram/apps/desktop/electron/degram/gateway-rpc.test.ts
    - apps/degram/apps/desktop/electron/degram/profiles-cli.ts
    - apps/degram/apps/desktop/electron/degram/profiles-cli.test.ts
    - apps/degram/apps/desktop/electron/degram/preload-degram.test.ts
    - apps/degram/apps/desktop/electron/degram/test-support.ts
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-12-SUMMARY.md
  modified:
    - apps/degram/apps/desktop/electron/main.ts
    - apps/degram/apps/desktop/electron/preload.ts
    - apps/degram/apps/desktop/src/global.d.ts
key-decisions:
  - "The agent backend env for degram is spawned from main.ts through degramSpawnEnv (HERMES_DEGRAM=1, the fixed degram home, DEGRAM_PYTHON and DEGRAM_REVIT_MCP_DIR); DEGRAM_PYTHON is resolved from env, then degram.json revitPython, then the adapter's own .venv under DEGRAM_REVIT_MCP_DIR, and is never derived from the gateway interpreter (mcp 2.0.0 lacks mcp.server.fastmcp); when none resolves the variable stays unset and the Revit group reports setup-incomplete"
  - "An invalid DG origin (env or degram.json) fails closed with DG_ORIGIN_INVALID and main creates no wiring; it is never replaced by the default, so a typo cannot send a sign-in to another server"
  - "Credentials are set (degram.credentials.set) before the scope is reported ready, and the renderer starts a new chat session only for a new scope epoch, so credentials always precede session.create; a scope switch clears the old credential first and never reuses a session"
  - "Revocation clears first, notifies second: credentials.clear, scope close, view reset and wipe, and for an access loss also backend release plus profile purge, then the renderer event; the runtime state barrier enforces that nothing about the old user or project reaches the renderer earlier"
  - "A session end wipes the whole DG partition; an access loss on one project wipes only the view's tenant storage (cookies kept) and purges only that scope's profile, so other scopes and the DG sign-in survive; explicit logout wipes the partition but keeps local profiles (history hidden, not deleted, D-19)"
  - "CREDENTIALS_EXPIRED / DELEGATED_EXPIRED / DELEGATED_AUTH_FAILED forwarded by the agent are verified against GET /auth/me and followed by a re-mint; only a DG-confirmed 401 ends the session (a laptop that slept past the 15 min token TTL must not be signed out); DELEGATED_SESSION_ENDED ends it directly, DELEGATED_SCOPE_CHANGED and ACCESS_DENIED revoke the active scope"
  - "A changed company for the active project is treated as a scope change (the scope is user + company + project): the old scope is purged like a lost membership"
  - "The DG view is never given a preload, never an iframe; will-navigate, will-redirect and window.open allow only the exact DG origin (a DG window.open navigates the same view), every permission request is denied, will-attach-webview is refused"
  - "dg_session cookie changes in the partition trigger a session re-check (sign-in finished in the DG page shows the DG page); changes made by a clearing sequence are ignored while it runs"
metrics:
  duration: ~45 min in this run (Task 1 was committed by an earlier interrupted run and re-verified here)
  completed: 2026-10-05
requirements-completed: []
requirements-partial: [DGCL-01, DGCL-02, DGCL-03, DGCL-05, DGCL-06]  # Electron-main side proven offline with injected fakes. The renderer surfaces are plans 13/14, the audit/UAT is 15, and the live checks (cookie attach, real net.request, real WebContentsView, real agent handoff) are plan 16.
status: complete
---

# Phase 1301 Plan 12: Electron-main DG integration Summary

Electron main now owns DeGram's DG session end to end: sign-in on the real DG login page in the isolated partition `persist:degram-dg`, an embedded DG `WebContentsView` with an exact-origin allowlist and no preload, explicit project selection that opens an isolated per-scope profile and hands a 15-minute delegated token to the agent in memory only, and revocation detected by any 401/403, a 60 s `/auth/me` heartbeat and a window-focus check, always clearing token, scope and view before the renderer hears about it.

## Authorization and boundaries

Per the orchestrator brief: local commits in `apps/degram` on branch `degram/phase-1301` only. No push, no `hermes update`, no Desktop launch, build, dev server or packaging, no Docker, no write to `%LOCALAPPDATA%\hermes` or the installed Hermes profile or userData, no package install, no provider or LLM call, no live DG/CAD/graph call, `.secrets` untouched. The plan is proven by offline vitest suites only; every Electron API is a fake. No gitlink bump, `apps/degram` and `apps/revit-mcp` not staged in the framework. `python tools/degram/workspace.py verify` reports `Submodule gitlink does not match the selected component HEAD`, expected until plan 15 (not worked around). The 8 untracked pytest-artifact files in the component root and `.git/modules/degram/worktrees/dgp-t` were not touched (every component commit prints `failed to delete .../worktrees/dgp-t: Permission denied` from git's post-commit housekeeping; the commit itself succeeds).

## Commits

Component repo `apps/degram`, branch `degram/phase-1301` (committing repository: component), base `7fdb4aae`:

| Task | Commit | Message |
|---|---|---|
| 1 | `a5f81317` | feat(1301-12): DG session, scope controller and delegated-token handoff for explicit project selection |
| 2 | `0be0679b` | feat(1301-12): DG WebContentsView with exact-origin allowlist, sign-out ordering and degram IPC bridge |
| 3 | `8f681b7b` | feat(1301-12): token renewal, heartbeat, focus check and revocation clearing |
| follow-up | `4f7eb136` | fix(1301-12): bind profile CLI values to their flags as --flag=value |

Task 1 (`a5f81317`) was committed by an earlier executor run that was interrupted before Task 2; this run found the tree clean at that commit, re-ran its suites (6 files, 76 tests green) and continued from Task 2. Framework repo (master): the `docs(1301-12)` commit with this SUMMARY, STATE.md and ROADMAP.md. No deletions in any commit.

## What was built

**Task 1 (tracer, earlier run, verified here).** `dg-config`, `dg-session`, `scope`, `gateway-rpc`, `profiles-cli`, `test-support` and two one-line `main.ts` hooks (`degramSpawnEnv()` spread at the pool spawn and the primary spawn). Explicit `selectProject` runs a fresh `/auth/me`, rejects a non-member, closes the previous scope (credential cleared first), ensures the profile, starts or attaches the backend, mints, calls `degram.credentials.set` with `{token, expiresAt, relayBaseUrl: origin + '/data-service', user, company, project}`, and reports `ready`. Nothing is selected implicitly. The token never appears in state, events, logger calls or fs writes (spies in the suite).

**Task 2 (view, sign-out, IPC).**
- `dg-view.ts`: web preferences are frozen and carry no `preload` (partition `persist:degram-dg`, contextIsolation and sandbox on, nodeIntegration, webviewTag and sub-frame node integration off, webSecurity on). `isAllowedDgUrl` is an exact scheme + host + port match that rejects userinfo tricks, other schemes, `blob:`, `about:` and garbage. will-navigate/will-redirect are prevented and reported as `external-link-blocked {url}`; every `window.open` is denied (a DG URL navigates the same view); permission requests are denied; a main-frame load failure reports `dg-unreachable`, a finished load `dg-reachable`. Modes: graph = `{origin}/#degram`, full = `{origin}/`; sign-in = `{origin}/` top-level in the same view. `openExternalConfirmed` opens http(s) URLs without credentials only.
- `ipc.ts`: `createDegramRuntime` composes session, view and scope and owns the renderer-safe `DegramState {auth, scope, dg}`; `registerDegramIpc` accepts calls only from the DeGram window's renderer, validates every payload (project length and control characters, mode enum, finite bounds, outcome allowlist, URL string) and has no channel that can read a credential. Sign-out order (tested): DG `/auth/logout` -> `degram.credentials.clear` -> view blank -> partition wipe -> sign-in page -> state `signed-out`; the renderer receives nothing before the wipe finished, and a DG outage during logout still clears locally.
- `main-wiring.ts` + `main.ts`: lazy `ensureDegramWiring()` (DeGram identity only) builds the net-backed partition fetch, the `WebContentsView` factory, the profile CLI runner (payload python or source-checkout python, argv array), the pool backend (`ensureBackend`, gateway RPC over `freshGatewayWsUrl`, release via `teardownPoolBackendAndWait`) and registers IPC; `createWindow` attaches the main window (view mounted hidden until the renderer reports bounds).
- `preload.ts` / `src/global.d.ts`: typed `degram` namespace; `channels.ts` is import-free because a sandboxed preload cannot `require` node modules.

**Task 3 (renewal, heartbeat, focus, revocation).** In `scope.ts`: renewal every 600 s while a scope is open (each new token goes to `degram.credentials.set`), `GET /auth/me` every 60 s while signed in, focus check coalesced within 5 s. A 401 (heartbeat, mint, forwarded `DELEGATED_SESSION_ENDED`, or `CREDENTIALS_EXPIRED` confirmed by `/auth/me`) runs credential clear -> scope close -> view reset and wipe -> `session-ended`, and stops every timer. A lost or changed membership, a 403 from the mint (`DELEGATED_SCOPE_CHANGED`) or a forwarded `ACCESS_DENIED` runs credential clear -> backend release -> profile purge for that scope only -> view tenant wipe -> `access-revoked {project, purged}`; the heartbeat keeps running, the DG sign-in and other scopes stay. A network failure emits `dg-unreachable` once and clears nothing, `dg-reachable` on recovery; one attempt per tick, a pending renewal retried on the next heartbeat tick only. The runtime adds `reportOutcome` (IPC `degram:report-outcome`) and `onWindowFocus` (hooked on the window `focus` event).

## TDD

- **Task 1:** RED/GREEN evidence belongs to the interrupted run; this run only re-verified GREEN (6 files, 76 tests).
- **Task 2:** RED observed for `dg-view.test.ts` (module missing), `ipc.test.ts` (module missing) and `preload-degram.test.ts` (`bridge.degram` undefined), then GREEN. Honest caveat: `main-wiring.test.ts` was RED (module missing) and the `resolveProfilesInvocation` tests were written in the same step as the function, without a separate RED run.
- **Task 3:** RED observed on `scope.test.ts` (24 of 38 failing before the implementation), then 36 of 38 on the first GREEN run; two failures were test-design problems (an expected `storageClears` of 0 versus the tenant wipe that is now deliberately performed, and a release-before-check race), fixed in the tests. The ipc/preload/main-wiring additions were RED (10 failures) before `reportOutcome`/`onWindowFocus` existed.

## Verification

All commands from `apps\degram\apps\desktop`; nothing launched.

| Check | Result |
|---|---|
| `npx vitest run --project electron electron/degram` | **10 files, 156 passed** (dg-config 26, dg-session 13, scope 38, dg-view 20, ipc 20, main-wiring 7, gateway-rpc 4, profiles-cli 9, preload-degram 3, isolation 16), measured after the follow-up fix |
| `npx vitest run --project electron electron/window-open-policy.test.ts electron/preload-external-open.test.ts` | pass (existing preload and window-open tests unchanged) |
| `npm run typecheck` (`tsc` for src, electron, e2e, builder config) | exit 0, no output |
| `eslint` and `prettier --check` on every touched file | clean |
| Full `npx vitest run --project electron` after Task 3 | 26 files / 44 tests failed, 3371 passed, 70 skipped. Against 1301-ENV.md: 39 of the 44 are the stable pre-existing set. The other 5 are not Phase 1301 regressions: `bundle-skew` (2, treeless-clone git fixtures), `git-worktree-ops` (1) and `updater/checkout-legacy` (1, passes when run alone) are `Test timed out in 5000ms` git-heavy cases from the documented flaky set; `payload-sign-cache` "batch cache" is an `ENOTEMPTY` temp-dir cleanup race in a file that is itself in the stable set (a rerun passes it and fails the other stable test). Four stable failures did not reproduce this time. Nothing under `electron/degram` fails. |
| Wiring checked as data | `HERMES_DEGRAM=1`, `HERMES_HOME`, `DEGRAM_PYTHON`, `DEGRAM_REVIT_MCP_DIR` (adapter interpreter from env, `degram.json` or the adapter `.venv`; never the gateway venv; unset means setup-incomplete); credentials set before `ready`; clear plus backend release plus purge on revoke; relay base = origin + `/data-service` without `/degram/v1`; http origins accepted as configured. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Revocation cannot be proven with an immediate sign-out on every expiry outcome.** The plan says a forwarded `CREDENTIALS_EXPIRED` is a 401 and runs the session-ended flow. A machine that slept past the 900 s TTL would be signed out although the DG session is fine. `CREDENTIALS_EXPIRED` (and `DELEGATED_EXPIRED`, `DELEGATED_AUTH_FAILED`) now verify against `/auth/me` and re-mint; only a DG-confirmed 401 ends the session. `DELEGATED_SESSION_ENDED` ends it directly. **Files:** `scope.ts`, `scope.test.ts`. **Commit:** `8f681b7b`.

**2. [Rule 2 - Missing critical] Value-as-option injection in the profile CLI argv.** Scope values come from the DG server; `--project --home=...` style values could be mistaken for flags. Values are now bound as `--flag=value` with a test. **Files:** `profiles-cli.ts`, `profiles-cli.test.ts`. **Commit:** `4f7eb136`.

**3. [Rule 2 - Missing critical] Permission handler on the DG partition.** Remote content in a desktop view must not get camera, microphone or geolocation by Electron's default-allow: `setPermissionRequestHandler` denies every request; `will-attach-webview` is refused. **Files:** `dg-view.ts`. **Commit:** `0be0679b`.

**4. [Rule 3 - Blocking] The state could leak ahead of the clearing.** `session.refresh` marks the session signed out the instant a 401 arrives, which would publish `signed-out` before the credential and view were cleared. `scope.isSettled()` (unsettled from an observed loss until the clearing finished) gates every publish; a cookie change caused by a clearing sequence is ignored while it runs. **Files:** `scope.ts`, `ipc.ts`. **Commit:** `0be0679b`, `8f681b7b`.

**5. [Plan interpretation] Surface additions.** The bridge gained `onEvent`, `setDgBounds` (the renderer must tell main where the DG page sits; the view stays hidden until it does) and `reportOutcome` (the renderer forwards agent outcome codes; validated against `AGENT_OUTCOME_CODES`); events gained `dg-reachable`. A changed company on the active project is treated as a scope change. An access loss wipes the view's tenant storage but keeps cookies, so the DG sign-in survives.

**6. [Plan interpretation] Where the timers live.** Renewal, heartbeat and the clearing sequences are in `scope.ts` (they need the open scope); `dg-session.ts` keeps the constants, the three DG requests and the `net.request` adapter and was not modified in Task 3.

**7. New files not in `files_modified`:** `channels.ts` (preload-safe channel names), `main-wiring.ts` and `main-wiring.test.ts` (keeps `main.ts` hooks small and testable), `ipc.test.ts`, `preload-degram.test.ts`, `gateway-rpc.ts`/`.test.ts`, `profiles-cli.ts`/`.test.ts`, `test-support.ts`.

## Findings for later plans

- **Plan 13 (renderer):** use `window.hermesDesktop.degram`. State `auth.kind` is `unknown | signed-out | signed-in`; `scope.status` is `no-project | opening | ready | error` with `scope.epoch` (start a new chat session when it changes, after `ready`); `dg.reachable` drives the unreachable ErrorState. Events: `session-ended` (show the sign-in boot state with the session-ended copy), `access-revoked {project, purged}` (toast plus project EmptyState), `external-link-blocked {url}` (notice with «Открыть в браузере» calling `openExternalConfirmed(url)` from a click), `dg-unreachable`/`dg-reachable`. The DG page must call `setDgBounds({x, y, width, height})` with its placeholder rect (window content coordinates) on mount, resize and scroll, and `setDgBounds(null)` when hidden.
- **Plan 14 (chat):** forward a turn's error code to `degram.reportOutcome(code)` when it is one of `CREDENTIALS_EXPIRED`, `DELEGATED_EXPIRED`, `DELEGATED_AUTH_FAILED`, `DELEGATED_SESSION_ENDED`, `DELEGATED_SCOPE_CHANGED`, `ACCESS_DENIED`; it returns false for any other code.
- **Plan 15 (audit):** `gitlink != child HEAD` until the bump (expected). `will-frame-navigate` is not guarded (sub-frames of the DG page are not allowlisted separately; the view has no preload and no Node, so a sub-frame cannot reach main), decide whether to add it.
- **Plan 16 (live):** record which cookie mode DG needs: `createNetPartitionFetch` defaults to the `session` mode (`useSessionCookies`); if the SameSite=Strict `dg_session` is not attached to main-process requests, switch the single `cookieMode: 'explicit'` option (reads the cookie with `session.cookies.get`). Also confirm live: `net.request` with `partition` and `session` both given, `WebContentsView` partition sharing between the view and `net`, `globalThis.WebSocket` in Electron 40 main for the gateway RPC, and `resolveProfilesInvocation` against the real bundled payload (`storePython`) and a source checkout (a launcher shim yields null on purpose).
- **Risk carried from plan 11:** the Revit adapter needs an interpreter with `mcp` 1.x. `degramBackendEnv` resolves it from `DEGRAM_PYTHON`, `degram.json` `revitPython`, or `<DEGRAM_REVIT_MCP_DIR>/.venv`; the adapter's uv environment must exist there, which no plan provisions yet.

## Not verified (honest limits)

- Nothing ran inside Electron. `net.request`, `WebContentsView`, `session.fromPartition`, `ipcMain`, the window `focus` event and the cookie `changed` event are exercised only through fakes and `tsc`. The `main.ts` composition (`ensureDegramWiring`) has no test of its own beyond typecheck.
- No real DG server, token, cookie, agent backend or gateway socket; the delegated-token and `/auth/me` shapes follow the plan 05 summary and `data-service/auth_routes.py`, exercised against a scripted fake.
- The packaged-build path of `resolveProfilesInvocation` (bundled `storePython`) is unexercised.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-1301-12-01 (DG view gains Node/preload): frozen preferences without `preload`, tested. -02 (navigation to another origin): exact-origin allowlist on navigate, redirect and `window.open`, tested including userinfo, scheme and port tricks. -03 (token to renderer, logs, disk): main-only handling, no preload getter, spies on state, events, results, logger and fs. -04 (stale data after revoke): clear-then-notify with the `isSettled` barrier, tested by ordering and by "nothing sent before the wipe". -05 (CSRF on mint): every mint sends `X-DG-CSRF: 1` through the partition (server enforcement is plan 05). -06 (openExternal abuse): http(s) without credentials only, reachable only through the validated, sender-checked IPC channel.

## Self-Check: PASSED

- FOUND (component, `apps/degram/apps/desktop`): `electron/degram/{dg-config,dg-session,scope,dg-view,ipc,channels,main-wiring,gateway-rpc,profiles-cli,test-support}.ts` and their `*.test.ts` (`preload-degram.test.ts`, `ipc.test.ts`, `main-wiring.test.ts` included); `electron/main.ts`, `electron/preload.ts`, `src/global.d.ts` modified
- FOUND commits in the component repo: `a5f81317`, `0be0679b`, `8f681b7b`, `4f7eb136` on `degram/phase-1301`; `git status` shows only the 8 known untracked pytest-artifact files
- Gitlink not bumped; `apps/degram` and `apps/revit-mcp` not staged in the framework; no deletions in any commit
