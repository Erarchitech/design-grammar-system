# Phase 1301 Build record (plan 15)

Recorded 2026-10-05. Committing repository for this file: framework.

**Verdict: the build exists, but the first launch FAILED the D-02 isolation proof.** The installer built here ran as stock
"Hermes Agent <commit>", attached to the user's running Hermes backend and caused writes in `%LOCALAPPDATA%\hermes`. Nothing was
pushed and no gitlink was bumped (orchestrator stop rule). The root cause is fixed in the component (`910a060d`, local only,
tests green) but the fix is not in this artifact: the installer below must not be distributed or launched again.

## Artifact (built from the pre-fix commit)

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.0.0.exe` |
| Size | 1,931,722,535 bytes |
| SHA-256 | `46845872fa2646e1ec30935e42f29dcbe9cae99df6783d0abda5612192d4b13f` |
| Unpacked app (launched once) | `D:\dgb\src\apps\desktop\release\win-unpacked\DeGram.exe` |
| Built from component commit | `386bd704bc148ac6b1810615c0b32d28d6bd610f` (clean checkout, `dirty: false`, stamp `variant: degram`, `payload: bundled`, `updateMechanism: external`) |
| Signing | none (`[batch-sign] AZURE_SIGN_* not set - payload binaries will be UNSIGNED`), as designed (D-04) |
| NSIS | `target=nsis file=release\DeGram-Setup-0.0.0.exe archs=x64 oneClick=false perMachine=false`; NSIS toolset from electron-builder's own pinned supplier (`nsis@1.2.1`, `nsis-bundle-3.12.tar.gz`), copied to `packager\nsis` |
| `revit-mcp` resource | present at `resources\revit-mcp` (source, `pyproject.toml`, `uv.lock`, `extension.json`, `startup.py`; no `tests`, no `.git`, no `.venv`, no bytecode) |
| Payload | `resources\agent-payload`, 5.9 GB staged (includes llama.cpp cpu/cuda/hip/vulkan, chromium, ffmpeg, git, gh, ripgrep, node, npm, uv) |

## Command and exit code

Run from a clean local clone of the component at `D:\dgb\src` (`git clone --no-hardlinks apps/degram`, HEAD = `386bd704`, tree clean),
because the component working tree carries 8 untracked pytest artifacts and `desktop.py` refuses an unclean checkout. Environment
scrubbed by `D:\dgb\run-build.sh`: `ELECTRON_RUN_AS_NODE`, `HERMES_HOME`, `HERMES_PYTHON`, `HERMES_NODE`, `HERMES_PROFILE`,
`HERMES_REAL_HOME` unset; `HERMES_HOME=D:\dgb\parent-home`; `TEMP`/`TMP` on D:; `PATH` limited to Git and Windows; the build's own
`bootstrap_environment` then moves `HOME`/`LOCALAPPDATA`/`APPDATA`/`HERMES_HOME` under `.build\desktop-job`.

```
python scripts/bundles/desktop.py --commit=386bd704bc148ac6b1810615c0b32d28d6bd610f --variant=degram
```

| Run | Window (UTC) | Exit | Result |
|---|---|---|---|
| final | 19:36:58 - 20:16:25 (39.5 min) | **0** | installer built |

Earlier runs that did not finish (all recorded in `D:\dgb\c-logs\` and `D:\dgb\build.log`): see "Build obstacles".

Tests before the build (component, `apps\degram\apps\desktop`): `npx vitest run --project electron scripts/degram-build.test.mjs electron/degram/isolation.test.ts`
(degram-build 22, isolation 16: all pass at `910a060d`); `scripts/prepared-packaging.test.mjs`, `prepare-dmgbuild.test.mjs`, `prepared-windows-tools.test.mjs` pass;
`run-electron-builder.test.mjs` has only the stable 1301-ENV.md baseline failure; `npm run typecheck` exit 0.

## First launch (D-02 proof) - FAILED

Unset for the launch only: `ELECTRON_RUN_AS_NODE` (inherited `1`, makes Electron exit silently). Everything else inherited, including
`HERMES_HOME=C:\Users\Admin\AppData\Local\hermes` (the owner's real Hermes home; the isolation design must ignore it).
One launch, no sign-in, no input, 75 s idle, closed through `CloseMainWindow`, no process left (`Get-Process DeGram*` = 0).

| Time (UTC) | Event |
|---|---|
| 20:19:49 | `DeGram.exe` pid 44852 launched |
| 20:21:05 | main window title `Hermes` (not `DeGram`); 4 processes under `win-unpacked`, no Python backend |
| 20:21:05 | `CloseMainWindow` sent; all processes gone by 20:21:08 |

### Listings

Roots: `%LOCALAPPDATA%\hermes` and `%USERPROFILE%\.hermes` (303,128 entries; path, size, mtime ticks, read-only). The owner's Hermes is
**live** (5 `Hermes.exe`, gateway, cron, kanban), so a literally empty diff is impossible on this PC. A control window was taken with DeGram not running.

Control A -> B (29 s, no DeGram): 12 modified, 0 created, 0 deleted: only heartbeats and database sidecars (`cron\*`, `gateway_state.json`,
`kanban.db-shm/-wal`, `state.db-wal`, `state\*.heartbeat`).

Launch B -> C (2.5 min incl. launch): **10 created, 22 modified, 0 deleted**.

```
C bot_relay\ (claimed, outbox, replies, roster.json)         roster.json mtime 20:19:56
C desktop-plugins\jev\ (.hermes-package.json, plugin.js)
C hermes-agent\tools\__pycache__\voice_live.cpython-314.pyc  20:19:51
C hermes-agent\tui_gateway\__pycache__\profile_roster_cache.cpython-314.pyc  20:19:56
M logs\desktop.log (+1,149 bytes)  logs\gui.log  logs\agent.log  logs\errors.log
M provider_models_cache.json  auth.lock  spawn-ledger.json  channel_directory.json
M (control-type churn) cron\*  gateway_state.json  kanban.db-*  state.db-wal  state\*.heartbeat  (+ the parent directories)
```

### Attribution: the launched binary behaved as stock Hermes Desktop

The Hermes logs show the DeGram process as a Hermes client at the launch second (local time = UTC+1):

```
desktop.log 21:19:50,678 [hermes] [attach] attached to the running Hermes backend on http://127.0.0.1:62917 (pid 40472, registered by profile "default"); spawning nothing
desktop.log 21:19:50,678 [hermes] [boot] Attached to the running Hermes backend
gui.log     21:19:50,668 tui_gateway.ws: ws accepted peer=127.0.0.1:54704   (closed at once)
gui.log     21:19:51,616 tui_gateway.ws: ws accepted peer=127.0.0.1:49972
gui.log     21:19:55,079 hermes_cli.web_server: owner-backfill: stamped 11 legacy NULL-profile session row(s) with profile 'default'
errors.log  21:19:57,098 tui_gateway.server: wake.start(gui): failed to start listener: Failed to open the wake-word microphone.
gui.log     21:21:06,730 ws closed peer=127.0.0.1:49972 reason=client_disconnect(code=1001) messages=43
```

The WebSocket closed at 20:21:06Z, one second after `CloseMainWindow`, after 43 messages. The created files were written 1.5 to 7 s after the launch.
`%LOCALAPPDATA%\DeGram` was **not** created; `%APPDATA%\HermesBundledCommit386bd70` was (3.5 MB: Chromium caches, `connections.json`,
`backend-ownership.json`, `desktop-installation.json`): the userData of the stock `bundled` commit-build identity, not DeGram's.

What this changed in the owner's Hermes (all caused by this launch's client; the 22 modified entries also include the control-type churn
that happens with no DeGram running):
- new directories/files listed above (`bot_relay`, `desktop-plugins\jev`, two `.pyc`);
- append-only log lines in `desktop.log`, `gui.log`, `agent.log`, `errors.log`;
- **a database write**: `owner-backfill: stamped 11 legacy NULL-profile session row(s) with profile 'default'` in the owner's session store, 5 s after the launch
  (it may be a first-connect migration that any new GUI client triggers; it is a write all the same);
- a microphone start attempt on the owner's backend (`wake.start(gui)`, failed);
- no deletion, nothing was moved, no credential was read or entered, no provider call was made.

### Root cause

`scripts/bundle-electron-main.mjs::productIdentity` derived the product identity baked into the packaged `electron-main.mjs`
(`__HERMES_PRODUCT_IDENTITY__`) from the stamp's `payload` (`bundled`) and ignored `variant: "degram"`. The packaged main therefore
carried the stock `bundled` + commit identity (`com.erarchitech.degram` occurs 0 times in `dist\electron-main.mjs`), `degram` was false, so
`isolatedBackendRequired` was false, host-backend attach was on, and `HERMES_HOME` was inherited. Plan 04 proved the identity through
`HERMES_DESKTOP_VARIANT` only, which a packaged app never has at run time. The offline suites could not see it; only a real launch could.

Fix, component commit **`910a060d`** (local, not pushed): `productIdentity` is exported and selects `degram` from the stamp (payload must be
`bundled`). New tests, RED before the fix: the baked identity of a degram stamp, the unchanged identity of every other stamp, and an end-to-end
check that the bundled `electron-main.mjs` of a degram stamp contains `com.erarchitech.degram` and a bundled stamp does not
(`degram-build.test.mjs` 22/22). The artifact above predates the fix. Cheap pre-launch gate added to `docs/degram/CLEAN-INSTALL.md`
(step 6.3): the unpacked `dist\electron-main.mjs` must contain `com.erarchitech.degram`.

## Build obstacles (what had to be worked around)

1. **Node.** The shell's Node 20.20.0 violates the repo engines (`^22.22 || ^24.11 || >=26`); the build uses its own PM-pinned Node 26.7.0.
2. **Windows rename failures.** PM's Node staging failed twice with `[WinError 5]` renaming `node_modules` after extraction (a standalone rename of the same tree
   works). Workaround: the Node and npm store entries were copied from the installed Hermes store into the build-owned store with their own `facts.json`
   records (same artifact SHA-256 as `pm/lock.json`, read-only use of the Hermes tree). A later `dist` publication rename failed once with `EPERM` in one run and
   passed in another (flaky, antivirus/handle related).
3. **Native extras.** `pilk` (extra `silk`) needs MSVC plus the Windows SDK (no `Windows Kits\10\Include` on this PC) and `obstore` (extra `daytona`) has no
   CPython 3.14 Windows wheel: `uv sync --all-extras` failed. Component commit `386bd704` makes both opt-in extras (installed on demand, still declared and locked).
4. **Disk.** `C:` was at 100% (0.4 GB free of 953 GB). The first staged build filled it (`ENOSPC` while copying the payload into `win-unpacked`). Everything was
   moved to `D:\dgb` (the full tree is about 22 GB, the installer 1.9 GB), the `C:\dgb` scratch was deleted. `C:` now has about 16.7 GB free.
5. **Inherited environment.** The shell exports `HERMES_HOME=C:\Users\Admin\AppData\Local\hermes`, `HERMES_CA_BUNDLE`, and the Hermes `node`/`bin` directories
   on `PATH`. The very first attempt (`npm run payload`, 18:35-18:37 UTC, before any scrubbing) ran with that environment and failed on the Node engine check.
   Hermes files whose mtime falls in that window are `cache\uv\interpreter-v4\0de9bff94b993286\96bc665fdb70c6be.msgpack` (and its parent `cache\uv`) at 18:36:41/18:36:49
   and `installs\1f298275253120d6\pm-runtime\generations\e3bef59e2ae54ed898fd1da3e7b0440c\.leases` at 18:37:01: these coincide with that run and may be mine (uv interpreter
   cache entry, lease touch); the live Hermes may also have written them. Nothing else from that run is in the Hermes tree. Every later build command ran scrubbed.

## Pushed commits and gitlinks

Nothing pushed (stop rule). No `git push`, no tag, no remote change. Gitlinks not bumped. `apps/degram` local branch `degram/phase-1301`:
`0ee2d12f` (plan 14) -> `6e2b4889` (revit-mcp resource, NSIS admission) -> `386bd704` (opt-in extras) -> `910a060d` (identity fix). `apps/revit-mcp` unchanged at `937384f`.
`python tools/degram/workspace.py verify` therefore still reports gitlink != child HEAD for both children (expected until the pair is pushed).

## What the owner must decide next

1. Rebuild from `910a060d` (or later): about 40 min, about 22 GB on D:, reuses `D:\dgb\src\.cache`.
2. Authorize a **second** launch. Recommended protocol: before launching, run the identity gate (step 6.3); take listings before and after as here, with a control window;
   run with the same inherited environment only if the owner accepts a second exposure of the live Hermes, otherwise close the Hermes Desktop first or launch with
   `HERMES_HOME` removed from the process environment (isolation must not depend on it). An empty diff is only achievable while no Hermes process is running.
3. Only then push the two branches and bump the gitlinks.

## Rebuild and second launch (2026-10-06, Hermes Desktop closed by the owner)

Rebuilt from component `910a060d` (clean clone `D:\dgb\src`, scrubbed build env, exit 0 at 23:31Z): `DeGram-Setup-0.0.0.exe`, 1,931,719,493 bytes,
SHA-256 `4fa89e7e56c31f2e7d0ff100e9a6dd56145f0ca334b9bef8b7780ad65398e9a4`. Identity gate: `com.erarchitech.degram` occurs 1 time in
`app.asar.unpacked\dist\electron-main.mjs` (0 before the fix). The first rebuild attempt failed on a stale read-only payload folder in the
build clone; it was cleared inside `D:\dgb\src` and the build re-run.

Launch: unpacked `DeGram.exe`, child environment without `ELECTRON_RUN_AS_NODE`, **`HERMES_HOME` still inherited** (`C:\Users\Admin\AppData\Local\hermes`),
about 40 s, closed through `CloseMainWindow`, no process or listener left. Hermes Desktop was closed; its background gateway/MCP python processes were still running.

| Check | Result |
|---|---|
| DeGram home and userData | `%LOCALAPPDATA%\DeGram\home` (own `state.db`, `skills` 12 entries, `memories`, `spawn-ledger.json`) and `\userData`; `%LOCALAPPDATA%\hermes` has no `degram` entry |
| Backend | own `degram.exe`/python child, own port (127.0.0.1:64449); no "attached to the running Hermes backend" line; Hermes logs hold no DeGram client |
| Hermes folders A->B control (no DeGram) | 0 created, 0 deleted, 4 modified (`hermes-agent\.git`, `kanban.db-shm/-wal`, `state\gateway.heartbeat`) |
| Hermes folders B->C launch window | **0 created, 0 deleted, 20 modified**: all are files written by Hermes's own background gateway (cron ticker, kanban, `gateway_state.json`, model catalog caches, `agent/errors/gateway.log`, `spawn-ledger.json`). The log lines are its 10-minute MCP reconcile (09:41:55 -> 09:52:05), `spawn-ledger.json` entries are all spawned by Hermes pid 59536. Attribution is by timing and ownership, not a clean empty diff |
| Locked surfaces | `/api/config`, `/api/profiles`, `/api/model/info` ... answer `DEGRAM_LOCKED` (403) as designed |

Open findings: the window title read `Hermes` (the product name is not applied to the title); the DG page load failed with `ERR_CONNECTION_REFUSED` on `localhost:8080` (Docker Desktop was not running at that moment);
the renderer still polls locked endpoints and floods stderr with `DEGRAM_LOCKED`. Leftover from the first launch: `%APPDATA%\HermesBundledCommit386bd70` (stock identity userData, not removed).
Not yet done: launch while Hermes Desktop itself is open; push of the two branches and gitlink bump (pending owner decision).

## Audit-fix rebuilds (2026-10-06, `/gsd-audit-fix 1301`, Gena fork lessons)

Owner decisions (AskUserQuestion, 2026-10-06): child commits without push for F-01/F-02/F-03; CompanyName `Erarchitech`;
owner-supplied icon (halftone hexagon) with all icon recommendations; version scheme `0.1.0`, patch +1 per installer build,
never reused; F-06 request filter; F-07 no PATH command; F-08 delete leftover; F-09 push + gitlink; F-10 launch beside an
open Hermes Desktop; remove the 8 `hermes-pytest` user-PATH entries.

Component commits on `degram/phase-1301` (local): `05d7eee8` F-01 window title, `df584929` F-02 vendor, `2103d06c` F-04 icon set
(`apps/desktop/scripts/generate_degram_icons.py`), `a0ec2d2e` F-05 version, `43658b61` F-06 preload REST lock,
`69eb9a1d` F-07 no user-PATH command, `a9e56d7e` F-02/F-04/F-05 through the build driver.

**Rebuild 1, from `69eb9a1d`** (10:00-10:52Z, exit 0): `DeGram-Setup-0.0.0.exe`. Inspection of the packaged artifact, not the
repo, showed three fixes had not reached it: `resources\icon.ico` and the exe icon were upstream's red commit-build icon with the
Nous art and a `69eb9a1` badge, the version was `0.0.0`, and CompanyName was `Nous Research` with copyright `DeGram`. Causes, all in
the build path: `scripts/bundles/desktop.py` renders upstream icons for a commit build and stages them over `apps/desktop/assets`
while packaging; it passes `-c.extraMetadata.version=<request version>`, which overrides the config; electron-builder reads
`author.name`, so a string `extraMetadata.author` leaves companyName empty. Fixed in `a9e56d7e` with tests. This artifact was
deleted, never launched. Every earlier DeGram build (plan 15 included) carried the same commit-badge icon.

**Rebuild 2, from `a9e56d7e`** (10:58-11:46Z, exit 0, clean clone `D:\dgb\src`, scrubbed env, clone clean afterwards):

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.0.exe`, 1,931,560,440 bytes |
| SHA-256 | `70a73670d58090145e3a540cbc07f399548ff365ff9a5e6a4e1e7aa5f7914f9a` |
| Exe version resource | ProductName/FileDescription `DeGram`, CompanyName `Erarchitech`, `Copyright © 2026 Erarchitech`, version `0.1.0` |
| Icons | `resources\icon.ico` byte-identical to the committed `assets/icon.ico`; exe icon is the DeGram mark (19-dot frame at 32 px); `dist/nous-girl{,-dark}.png` and `dist/apple-touch-icon.png` in `app.asar` byte-identical to the committed files |

Pilot-PC cleanup (owner-approved): DeGram's `%LOCALAPPDATA%\DeGram\home\bin` was first in the user PATH with a `hermes.cmd`
pointing at the build clone (a new shell's `hermes` ran DeGram); the entry and the stale `hermes.cmd`/`hermes-acp.cmd` were removed.
Eight `%TEMP%\hermes-pytest\...\bin` entries left by earlier runs of the upstream suite were removed; one more, added by this
session's run of `tests/hermes_cli/test_hermes_home_shared_launchers.py`, was removed at once (that test writes the real user PATH).
`%APPDATA%\HermesBundledCommit386bd70` (3.5 MB, all files from the 2026-10-05 21:19-21:21 stock-identity launch) was deleted.

### F-10: launch beside an open Hermes Desktop (2026-10-06, artifact from `a9e56d7e`)

Hermes Desktop opened by the owner (main window pid 31760, 5 `Hermes.exe`). Snapshots of `%USERPROFILE%\.hermes`,
`%LOCALAPPDATA%\hermes` and `%APPDATA%\Hermes` (`D:\dgb\listing.ps1`, 303,673 entries); launch by `D:\dgb\launch3.ps1`
(child env without `ELECTRON_RUN_AS_NODE`, **`HERMES_HOME` inherited** = the owner's Hermes home), evidence in `D:\dgb\run3\`.

| Check | Result |
|---|---|
| Control A->B (Hermes alone, 120 s) | 2 created, 0 deleted, 23 modified (cron ticker, gateway heartbeat, kanban, spawn-ledger, state.db-wal, MCP schema cache, Desktop `SharedStorage-wal`/Preferences/cache) |
| Launch B->C (DeGram 11:58:47-12:00:23Z beside Hermes) | **0 created, 0 deleted, 13 modified**, all of the control set's kinds; `channel_directory.json` last written 11:58:17Z, before the launch |
| Hermes logs | `agent.log` 11:55:51Z and `desktop.log` 11:55:28Z, both last written before the launch; no attach line, no DeGram client |
| `spawn-ledger.json` | 14 entries, none for a DeGram pid (25128, 27976, 12568) and no `degram` string |
| DeGram run | window title `DeGram`; 7 processes under the build output incl. `agent-payload\bin\degram.exe` -> python; own listener 127.0.0.1:61543; clean close in 2.5 s, 0 processes left |
| Hermes Desktop | 5 `Hermes.exe` before, during and after |
| Renderer locked-endpoint flood (F-06) | 0 `DEGRAM_LOCKED` lines in DeGram stdout+stderr (was a flood) |
| User environment | user PATH and user `HERMES_HOME` byte-identical before/after; `%LOCALAPPDATA%\DeGram\home\bin` not created (F-07) |

Verdict: DeGram runs in parallel with an open Hermes Desktop without creating, deleting or modifying any Hermes file of its own;
every modification in the launch window is of the kinds Hermes writes alone in the control window.

### Publication (F-09)

Pushed with owner authorization after a scan of all unpushed commits (no `.secrets`/`DG_OBSIDIAN`/`Publications` paths, no
key-like strings, no personal names or local paths; author `Evgenii <erarchitech@gmail.com>`): `Erarchitech/degram`
`degram/phase-1301` = `a9e56d7e` (29 commits over `8b66a510`), `Erarchitech/revit-mcp-server` `degram/phase-1301` = `937384f`.
Framework gitlinks bumped to the same pair; `python tools/degram/workspace.py verify` passes on it (componentContextInstalled
true), `tools/degram/tests` 19/19.

## Plan 17 build: DeGram 0.1.1 with the DG pairing (2026-10-06)

Owner authorization (AskUserQuestion, 2026-10-06): child commit, push + gitlink bump, installer 0.1.1 build. Component
`degram/phase-1301` = `97e158f2` on the fork (`e2fb6ffb` pairing store/exchange/panel, `97e158f2` version 0.1.1); framework
gitlink bumped, `workspace.py verify` passes on the pair.

Run 1 (13:39Z) failed after 3 min: `PermissionError [WinError 5]` deleting `build\agent-payload\...\__pycache__\auth.cpython-314.pyc`.
Cause: 26,758 files of the previous build's gitignored `apps/desktop/build/agent-payload` carry the Windows ReadOnly attribute,
which the payload step's tree delete cannot remove; no process held them. The ReadOnly flag was cleared on that directory only
(clone still clean), the same scrubbed `D:\dgb\run-build.sh` re-run.

Run 2 (13:43-14:35Z, exit 0, clean clone `D:\dgb\src` at `97e158f2`, clean afterwards):

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.1.exe`, 1,931,571,333 bytes |
| SHA-256 | `e18533e1e64c962738fd17dadbf099be82cf8f973511f4575e96a931dcd44b25` |
| Exe version resource | ProductName `DeGram`, CompanyName `Erarchitech`, `Copyright © 2026 Erarchitech`, version `0.1.1.0` |
| Packaged identity | `com.erarchitech.degram` in `app.asar.unpacked\dist\electron-main.mjs` |
| Pairing code in the artifact | `electron-main.mjs` (`degram:pairing:set`, `/auth/degram/exchange`, `degram-pairing.bin`), `electron-preload.js` (`degram:pairing:clear`), renderer `index-*.js` (`degram-pairing` panel) and `i18n-*.js` (`Токен сопряжения`) |

Not launched yet: the plan 17 Task 6 live pairing is the owner's step (launch with Hermes handling per the plan 15 recipe).

### Install of 0.1.1 on PC1 (owner request, 2026-10-06): not completed

1. `DeGram-Setup-0.1.1.exe /S` (default per-user dir `%LOCALAPPDATA%\Programs\DeGram`, 44 chars), 15:25-15:40Z: exit code 5,
   no uninstall entry, 103,991 of 115,546 files written. Four payload files exceed 260 chars at that dir (longest relative path
   234 chars, so an install dir must be at most 25 chars): one in `resources\agent-payload\uv-cache\archive-v0\...` and three
   `elevenlabs\...\__pycache__\*.pyc`. NSIS is not long-path aware even with `LongPathsEnabled=1`. **Finding F-11 (component):**
   the payload ships `uv-cache` and long `__pycache__` names; the default install dir cannot hold them. Fix in the build
   (exclude `uv-cache` and `__pycache__` from `agent-payload`, then re-check the longest path), not by moving the install dir.
   Not proven that the long paths alone caused the abort: see 3. The partial dir was deleted.
2. Re-run with `/S /D=C:\DeGram` did not start: the installer file was gone from `D:\dgb\src\apps\desktop\release` (removed
   16:42 local; the blockmap, `builder-debug.yml` and the 0.1.0 installer remain). Nothing in this session deleted it.
3. Kaspersky Total Security 21.3 is the active antivirus (Defender off); it already blocks network use of
   `tools\degram\relay_probe.py` on this PC (1301-UAT.md). Quarantine of the installer, and interference with the first
   install, are likely but unconfirmed: `avp.com QUARANTINE list` returns nothing without elevation. Owner to check Kaspersky
   Quarantine / Reports. DeGram not launched.

### F-11 analysis (2026-10-06, measured on the 0.1.1 `win-unpacked`)

`uv-cache` (899 MB, offline per-install venv rebuilds) and the baked read-only `__pycache__` (warm first launch; also the
cause of the run-1 PermissionError) are deliberate upstream features (`scripts/bundles/native.py`, `bytecode.py`).
Longest relative path and the longest install dir NSIS can take (259 - longest):

| Payload | Longest relative path | Install dir limit |
|---|---|---|
| as built | 234 | 25 |
| without `uv-cache` | 234 | 25 |
| without `uv-cache` and `__pycache__` | 209 | 50 (default dir is 44 for `Admin`, 50 for `e.ermolenko`: borderline) |
| without `uv-cache` and the `elevenlabs`/`mistralai` SDKs | 191 | 68 |

The plain "drop uv-cache and __pycache__" fix is not robust (fails for user names longer than ~10 chars) and loses the warm
start. DeGram cannot use the TTS and direct-provider SDKs (D-22 lockdown, LLM only through the relay), so excluding those
extras from the degram venv plus `uv-cache` gives a 68-char margin and keeps baked bytecode. Not implemented: owner choice
and a build authorization pending.

## Build 0.1.2: G-1 and F-11 (2026-10-07)

Owner authorization 2026-10-06 (AskUserQuestion): component commits, push + gitlink, container rebuild, "only build" 0.1.2
(no install). F-11 fix chosen by the owner: no unused SDKs (uv-cache kept, see the F-11 analysis above).

Run 1 (from `4eb1a697`, 2026-10-06 21:58-22:09Z) failed: the explicit degram extras list also selected the opt-in extras
(`[tool.hermes] opt-in-extras`: silk, kittentts, daytona) that an all-extras bundle never installs; silk's native `pilk`
sdist needs MSVC. Fixed in `7f9c33c1` (list = declared - opt-in - excluded, test against the real pyproject).

Run 2 (from `7f9c33c1`, 2026-10-07 06:47-07:44Z, exit 0, clean clone, clean afterwards):

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.2.exe`, 1,926,121,274 bytes |
| SHA-256 | `772e8f257750ffee93b2de2185a9657f16ce07fe2d563bf6f969ab5a14fac3bd` |
| Exe version resource | ProductName `DeGram`, CompanyName `Erarchitech`, version `0.1.2.0` |
| Payload | 110,348 files (0.1.1: 115,546); longest relative path 191 chars, so any install dir up to 68 chars fits (default `%LOCALAPPDATA%\Programs\DeGram` = 44 for `Admin`) |
| F-11 | no `elevenlabs`/`mistralai` package in venv or uv-cache (one hit is `skills/creative/popular-web-designs/templates/elevenlabs.md`, a markdown template) |
| G-1 | `degram_variant/dg_client.py` reads `?compact=true`; `tools/degram_tools.py` reads rules independently |
| Pairing (plan 17) | `degram:pairing:set` present in `electron-main.mjs` |

Not installed (owner: build only). On PC1 Kaspersky removed the 0.1.1 installer after an install attempt; keep a copy of
this one or add an exclusion before installing.

### Install of 0.1.2 on PC1 (owner, 2026-10-07): stopped by Kaspersky

Owner started `DeGram-Setup-0.1.2.exe` at 09:36:35 local. It wrote files until 09:59:14 and exited at 09:59:23 with
98,791 of 110,348 files, no uninstaller and no uninstall entry, the same truncation point as the 0.1.1 attempt. Longest
missing full path 207 chars, so not the 260-char limit (F-11 holds). Application log at 09:59:23: two `avp` events 4662 for
`ProcessPath d:\dgb\src\apps\desktop\release\degram-setup-0.1.2.exe` (detection numbers `28808cb6` conf 6, `32d87a95`
conf 0). Kaspersky Total Security 21.3 terminated the installer; the 0.1.1 failure (exit 5) was most likely the same
cause, not the long paths alone. The installer file was still present after this run. Partial dir left at
`%LOCALAPPDATA%\Programs\DeGram`. Needs an owner-made Kaspersky exclusion (trusted application / scan exclusion);
unsigned (self-signed) installer of 1.9 GB writing ~110k files is the likely heuristic trigger.

### Install of 0.1.2 on PC1, second attempt (owner, 2026-10-07): completed; F-11 verified

Kaspersky turned off by the owner. Installer started 10:29:05 local into the default per-user dir
`%LOCALAPPDATA%\Programs\DeGram` (44 chars) over the partial dir of the first attempt. It looked hung: electron-builder's
NSIS first extracts `app-64.7z` (1.8 GB) to `%TEMP%\nsm*.tmp\7z-out` (all 110,348 files, 7.8 GB), then copies into the
install dir; while it overwrote the ~98,750 files left by the first attempt the file count did not move for minutes
(one CPU core busy, ~0.17-4 MB/s). New files then appeared at ~4,100/min. Result: 110,350 files (110,348 + uninstaller),
`Uninstall DeGram.exe`, HKCU uninstall entry `DeGram 0.1.2`, publisher `Erarchitech`; the wizard reached «Установка DeGram
выполнена». **F-11 closed live**: the default dir now holds the whole payload. Install duration on this PC: ~30 min, most
of it in the copy phase; a slow but not broken step, recorded for CLEAN-INSTALL.md (expect up to 30 min, do not cancel).

### Installed 0.1.2 cannot reach DG on PC1: per-path network block (2026-10-07)

Owner report: «пустое окно без подключения к DG». nginx log: the installed DeGram/0.1.2 did reach DG at 11:21-11:23Z
(`/auth/me` 401, not yet signed in; `/auth/options` 200). From its restarts at 11:23:40Z and 11:24:20Z on, no request
arrived; `desktop.log`: `DG unreachable during /auth/me`, `ERR_CONNECTION_RESET` / `ERR_SOCKET_NOT_CONNECTED loading
http://localhost:8080/`. DG itself answered every other client (curl, PowerShell, IPv4 and IPv6).

Probe (`ELECTRON_RUN_AS_NODE=1 DeGram.exe -e "http.get('http://localhost:8080/data-service/auth/me')"`), same 0.1.2 binary:
`%LOCALAPPDATA%\Programs\DeGram\DeGram.exe` → `ECONNRESET`; `D:\dgb\src\apps\desktop\release\win-unpacked\DeGram.exe` → 401.
Connections are reset by executable path, the same pattern as `tools\degram\relay_probe.py` (1301-UAT.md). `avp`
(Kaspersky Total Security 21.3) is running. Not a DeGram defect; needs an owner-made Kaspersky rule for the installed
`DeGram.exe` (and `resources\agent-payload\bin\degram.exe` plus its python, which call the relay). Add to CLEAN-INSTALL.md:
security software must trust the installed DeGram executables, or DG is unreachable from DeGram.

## Build 0.1.3: slim payload, no Hermes name, graph tool budget (2026-10-07)

Owner decisions 2026-10-07: payload option 1 (only what variant degram can use, offline) and "remove all Hermes logos
and names". Component `0cb15c9c` (`75e65495` slim payload, branding commit, `0614b41e` graph tool budget, 0.1.3); framework
gitlink `909c45c`. Pre-build smoke on a venv with exactly the degram extras: `serve` reached `HERMES_BACKEND_READY` in
variant degram and 24 runtime modules imported. Owner closed DeGram and emptied `release\` before the build.

Build (clean clone at `0cb15c9c`, exit 0, 2026-10-07 14:10Z):

| Item | 0.1.2 | 0.1.3 |
|---|---|---|
| Installer | 1,926 MB | **490 MB** (`DeGram-Setup-0.1.3.exe`, 490,505,146 bytes) |
| SHA-256 | | `3459b2074da7abb1ec7448f447bacb8c8c0d3c1fc9fdda5ee5c1f05ba857b8ae` |
| Unpacked | 6,123 MB, 110,348 files | 1,619 MB, 32,130 files, longest path 168 |
| `agent-payload\tools` | 3,592 MB (16 tools) | 748 MB: ffmpeg, node, npm, python, ripgrep, uv |
| `venv` | 1,122 MB (all extras) | 199 MB, 91 dists (extras acp, cron, mcp, pty, vision, web) |
| `uv-cache` | 892 MB | 155 MB |
| Exe version | 0.1.2.0 | 0.1.3.0, DeGram, Erarchitech |

Inside: `GRAPH_RESULT_SHARE` in `tools/degram_tools.py` (G-1 budget fix), rebrand module `brand-*.js` in the renderer,
tray product name in `electron-main.mjs`; no lark_oapi/discord/slack/boto3/elevenlabs/mistralai/telegram in the venv.
Not installed (owner runs `win-unpacked\DeGram.exe`). Remaining big tool: ffmpeg 427 MB (pm-required; DeGram uses no
media tool): candidate for a later cut with a drift-skip for variant degram.

## Build 0.1.4: DEGRAM wordmark, language without the config API (2026-10-07)

Owner findings on 0.1.3: red "HERMES AGENT" wordmark on a new session; language change failed with
`403 DEGRAM_LOCKED /api/config`. Fixed in component `c541b229` (framework gitlink `970aee0`). Owner asked to build.

Build (clean clone at `c541b229`, exit 0, 2026-10-07 20:21Z): `DeGram-Setup-0.1.4.exe`, 490,507,051 bytes, SHA-256
`5a5177f7089b5d2a64d5fc954fe402ca08ae75b8dec4bbcaa42812cf2f2fa307`, exe version 0.1.4.0 (DeGram, Erarchitech), unpacked
1,619 MB. Inside: the new-session wordmark is `text: productMark('HERMES AGENT')` (DEGRAM in variant degram, module
`brand-*.js` with the uppercase pattern), and the renderer keeps the language under `degram.display.language`.
Not installed; owner runs `win-unpacked\DeGram.exe`.

## Build 0.1.5: breathing DeGram mark on a new session (2026-10-08)

Owner request 2026-10-07: replace the red DEGRAM lettering of a fresh draft with a motion version of the DeGram logo,
motion tuned by the owner in a preview page (pulse 3.6 s, ring delay 0.32 s, stretch 0.09, centre growth 1.35, 0.04 less
per ring). Component `ac65e101` (`DegramAnimatedMark`, 91-dot halftone hexagon from the icon generator's geometry) and
`2da8a2aa` (version 0.1.5), pushed to the fork by the owner; framework gitlink `a2cacb5`, `workspace.py verify` exit 0.
Tests before the build: intro 3/3, degram-build + isolation 40/40, typecheck and lint clean.

Run 1 (23:32Z) failed after 2 min with the run-1 obstacle of 0.1.3: `PermissionError [WinError 5]` deleting
`build\agent-payload\...\__pycache__\auth.cpython-314.pyc`. The ReadOnly flag was cleared on that gitignored directory only
(6,261 files; clone still clean) and the same `D:\dgb\run-build.sh` re-run.

Run 2 (23:34-23:46Z, exit 0, clean clone at `2da8a2aa`, clean afterwards): `DeGram-Setup-0.1.5.exe`, 490,510,493 bytes,
SHA-256 `9081563b4852effb301466bc111a257d7ef3631da0d23a92baa0d900365ca348`, exe version 0.1.5 (DeGram, Erarchitech),
unpacked 1,619 MB in 32,131 files. Inside: `app.asar.unpacked\dist\assets\index-*.css` carries
`.degram-mark{--pulse:3.6s;--ring-lag:.32s;...}` and the renderer bundle the `degram-mark__dot` groups.
Not installed; owner runs `win-unpacked\DeGram.exe`.

## 0.1.6 build: gap round G-3..G-17 and committed revit-mcp adapter (2026-10-09)

Gap plans 18-22 shipped as component commits on the fork (`d0d69691`, `199ef7cd`, `9457d72b`, `02993674`, version
`c3e8f2e8`) and revit-mcp `d8f0f24`; the owner asked for the push on 2026-10-09 and both `degram/phase-1301` branches
were pushed (degram `2da8a2aa..c3e8f2e8`, revit-mcp `937384f..d8f0f24`). Framework gitlinks bumped, `workspace.py verify`
exit 0. Tests before the build: degram-build + isolation 40/40, typecheck, lint 0 errors, electron 218/218, ui
`src/degram` 211/211, pytest `tests/degram` 400/400.

Adapter source: `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'` added to `D:\dgb\run-build.sh` (outside the repo). It is a
`--no-hardlinks` clone of `apps/revit-mcp` checked out detached at `d8f0f24`, clean; `D:\dgb\revit-mcp` (stale 0.1.5
adapter) was left untouched. 0.1.0-0.1.5 bundled that stale adapter.

Run 1 (18:33Z) was stopped by the orchestrator: the first edit of `run-build.sh` had put a carriage return into the
adapter path. The script was rewritten, the 66 icon files the interrupted `flavored_assets` step had left modified were
restored with `git checkout -- apps/desktop/assets` in the throwaway clone (clean at `c3e8f2e8` again), the ReadOnly flag
on `build\agent-payload` was cleared, and the build re-run.

Run 2 (18:43-18:55Z, exit 0, clean clone at `c3e8f2e8`): `DeGram-Setup-0.1.6.exe`, 490,528,570 bytes,
SHA-256 `39C9EFCE5E472FDF1BA34A1FD8959BC55C52351E363646CAB89C058AA721F018`, exe ProductVersion 0.1.6.0,
unpacked 1,698,015,532 bytes (1,619 MB class) in 32,131 files. Installer: `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.6.exe`.

Artifact checks on `release\win-unpacked` (all pass):

| Check | Result |
|---|---|
| `resources\revit-mcp\extension.json` has `"default_enabled": "True"` | pass |
| `resources\revit-mcp\main.py` contains `json_body` | pass |
| `resources\revit-mcp\revit_mcp\views.py` contains `urllib.parse` | pass |
| `app.asar.unpacked\dist\electron-main.mjs` contains `com.erarchitech.degram` | pass |
| no `tests\` directory under `resources\revit-mcp` | pass |

Not installed and not launched. Live recheck of the gap rows runs in plan 16 Task 3 after the owner installs.

## 0.1.7 build: gap round G-18..G-24, D-31, D-33..D-35 (2026-10-10)

Component `degram/phase-1301` was published at `d2054ae59c0bad9d5bcf7feac3926eeda62f4444`; the framework gitlink was updated to that remote commit before the build. `apps/revit-mcp` remained at `d8f0f24d2d29c8115f1e21b6573f52a360b34cad`. `python tools/degram/workspace.py verify` passed on the exact pair.

The clean no-hardlinks build checkout `D:\dgb\src` was detached at `d2054ae59c0bad9d5bcf7feac3926eeda62f4444`; `D:\dgb\revit-mcp-src` was clean at the identical `apps/revit-mcp` gitlink. The isolated driver retained `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'` and used a scrubbed Hermes environment. The build initially exposed Windows read-only payload and frontend publication races; permanent published component fixes reset the staged payload from a clean root and retry bounded transient frontend-directory rename failures. The successful build completed at 15:12:57Z.

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.7.exe` |
| Installer size | 490,533,308 bytes |
| Installer SHA-256 | `2825491ced4bd045cf16179d09b8ca70490ab906393957993db74fabdbcb5b7d` |
| Component commit / gitlink | `d2054ae59c0bad9d5bcf7feac3926eeda62f4444` |
| `revit-mcp` commit | `d8f0f24d2d29c8115f1e21b6573f52a360b34cad` |
| ProductVersion | `0.1.7` |
| Unpacked path | `D:\dgb\src\apps\desktop\release\win-unpacked` |
| Unpacked payload | 1,698,030,663 bytes in 32,136 files |
| Adapter source | `D:\dgb\revit-mcp-src` via `DEGRAM_REVIT_MCP_SOURCE` |

Artifact checks — all passed:

| Check | Result |
|---|---|
| `resources\revit-mcp\extension.json` contains `"default_enabled": "True"` | pass |
| `resources\revit-mcp\main.py` contains `json_body` | pass |
| `resources\revit-mcp\revit_mcp\views.py` contains `urllib.parse` | pass |
| `app.asar.unpacked\dist\electron-main.mjs` contains `com.erarchitech.degram` | pass |
| `app.asar.unpacked\dist\electron-main.mjs` contains `degram-select` | pass |
| `app.asar.unpacked\dist\electron-main.mjs` contains `host=degram` | pass |
| `resources\revit-mcp\tests` is absent | pass |

The installer was built only. It was not installed or launched; installation and live UAT remain the owner checkpoint in plan 1301-28 Task 5.

## 0.1.8 build: F-01 host-mode start screen (2026-10-11)

The 0.1.7 live UAT stopped at project open (start screen showed the `#degram` slice; see `1301-UAT.md`). Component fix `67ac0f84` and version bump `35d53793` were pushed by the owner to `degram/phase-1301`; framework gitlink `7e6e2e5` → `35d53793`, `python tools/degram/workspace.py verify` exit 0. `apps/revit-mcp` unchanged at `d8f0f24d2d29c8115f1e21b6573f52a360b34cad`.

Same procedure as 0.1.7: `D:\dgb\src` (no-hardlinks clone) detached at `35d53793e3df05b9104ade4ed05a52c9e4068e63`, clean before and after; `D:\dgb\run-build.sh` with the scrubbed environment and `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'`. Build 07:53:04Z → 07:59:06Z, exit 0. D: free space after the build: 5.4 GB (older installers 0.1.3–0.1.7 kept).

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.8.exe` |
| Installer size | 490,531,422 bytes |
| Installer SHA-256 | `7796e6fbd7b04df1d3e3946c006bd63456298c382f93066da701128b56658a49` |
| Unpacked `app.asar` SHA-256 | `7e23300d88a0dc03d01918c879985b8d33dcc3f2c11894a1b6d714f44e839e47` |
| Component commit / gitlink | `35d53793e3df05b9104ade4ed05a52c9e4068e63` |
| ProductVersion / ProductName / CompanyName | `0.1.8.0` / `DeGram` / `Erarchitech` |

Artifact checks — all passed: `electron-main.mjs` contains `com.erarchitech.degram`, `degram-select`, `host=degram` and the new `showStart`; `resources\revit-mcp\extension.json` `"default_enabled": "True"`, `main.py` `json_body`, `revit_mcp\views.py` `urllib.parse`; `resources\revit-mcp\tests` absent.

Built only: not installed or launched. Installation and the live recheck (sign-in → project choice in PROJECTS on the start screen → full workspace; then `v12 → B → C → v12`, revoke/pairing notices, rate-limit copy) are the owner's checkpoint.

## 0.1.9 build: F-02 session history after a project switch (2026-10-11)

0.1.8 live recheck: earlier chats reopened without messages after a project switch (REST transcript read locked in DeGram; see `1301-UAT.md` F-02). Component fix `e49c5d6a` and version bump `40bbd47f` pushed by the owner; framework gitlink `187ac62` → `40bbd47f8bc6467f79fefd056b597c9423a33155`, `workspace.py verify` exit 0; `apps/revit-mcp` unchanged at `d8f0f24d`.

Same procedure: build clone detached at `40bbd47f`, clean before and after; same driver and adapter source. Build 08:56:03Z → 09:01:44Z, exit 0. D: free after the build: 4.4 GB.

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.9.exe` |
| Installer size | 490,533,572 bytes |
| Installer SHA-256 | `b4998c6bc542a1fd95a5d5bd6e073312396b2b3712f62935a9234e6d2038a3bd` |
| Unpacked `app.asar` SHA-256 | `d9946c3e1732cdde101ab685c020dcc6be67398fd191472f8f531aa767ee6827` |
| ProductVersion | `0.1.9.0` |

Artifact checks — all passed: the 0.1.8 list (`com.erarchitech.degram`, `degram-select`, `host=degram`, `showStart`, revit-mcp `default_enabled`/`json_body`/`urllib.parse`, no `tests`), plus the F-02 cold-resume parameters in the packaged renderer `dist/assets/index-MWv2WNum.js` (`defer_history:!n&&s`, `s?{omit_messages:!0}:{}`). Built only; owner test guide: `1301-0.1.9-TEST-GUIDE.md`.

## 0.1.10 build: grant-backed access, DeGram shell, Models screen (2026-10-11)

Gap round plans 30-35 (D-39..D-44, G-25). Component commits `03785f3e` (33), `c3318b2d` (34), `38728957` (35) and version bump `93aa2b99` were pushed by the owner to `degram/phase-1301`; framework gitlink `40bbd47f` → `93aa2b99a2538efadf038f7e0b59a1545f1f863c` (commit `8c4dc7c`), `python tools/degram/workspace.py verify` exit 0; `apps/revit-mcp` unchanged at `d8f0f24d2d29c8115f1e21b6573f52a360b34cad`.

**Services (owner consent "rebuild ok").** `data-service` and `design-grammars` were rebuilt with `docker build --no-cache` from a `git archive` export of framework HEAD `dee60a9`, not from the working tree: the working tree holds other sessions' uncommitted edits in `data-service/cypher_allowlist.py`, `dg_context.py`, `ui-v2/src/lib/auth.js` and `ProjectsScreen.jsx`, which therefore are **not** in the running images. Images were tagged `design-grammar-system-data-service` / `-design-grammars` and the two containers were recreated with `docker compose up -d --no-build`. Both containers run the freshly built image ids. Probes: `POST /auth/degram/session-exchange` without a session → 401 `AUTH_REQUIRED`; `POST /auth/degram/exchange` with a `dgp_` bearer → 401 `PAIRING_RETIRED`; UI on :8080 → 200. `403 GRANT_REQUIRED` with a signed-in user was not exercised (no credentials used).

**Installer.** `D:\dgb\src` (clean clone) detached at the gitlink commit, clean before and after; `D:\dgb\run-build.sh` with the scrubbed environment and `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'` (clone at `d8f0f24d`). Build exit 0 (log end 2026-10-11T19:36:43Z). D: free after the build: 3.4 GB (older installers 0.1.3–0.1.9 kept).

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.10.exe` |
| Installer size | 490,529,803 bytes |
| Installer SHA-256 | `b13d10efd776f83c000ec3c75f91fe03706b72c94e6b3d0beec1fef4bab40e88` |
| Unpacked `app.asar` SHA-256 | `1c60ec706219bf9058b585d7c5481d991699c3485af84822dd17324bb9db8900` |
| Component commit / gitlink | `93aa2b99a2538efadf038f7e0b59a1545f1f863c` |
| ProductVersion / ProductName / CompanyName | `0.1.10` / `DeGram` / `Erarchitech` |

Artifact checks (all passed): `app.asar.unpacked\dist\electron-main.mjs` contains `com.erarchitech.degram`, `degram-select`, `host=degram`, `showStart`, `session-exchange`, `GRANT_REQUIRED`, `degram-new-session`, `degram-state=` and does **not** contain `auth/degram/exchange`; the packaged renderer `dist\assets\index-CovAaKx-.js` contains `degram.nav` and `/degram/models`, no `pairing-panel`; the i18n chunk has the new «Граф проекта» and «Модели» copy (the string «Подключение к DG» that remains is the sign-in state label, not the pairing panel); `resources\revit-mcp\extension.json` `"default_enabled": "True"`, `main.py` `json_body`, `revit_mcp\views.py` `urllib.parse`; `resources\revit-mcp\tests` absent.

Built only: not installed or launched. Installation and live UAT are the owner's checkpoint; guide: `1301-0.1.10-TEST-GUIDE.md`.

## 0.1.11 build: 0.1.10 UAT fix round, per-connector access (2026-10-12)

Gap round plans 37-40 (F-03, F-04, F-05, F-07; D-45..D-48). Component commits `45db5237` (37), `14bb25d2` (38), `52a09980` (39) and version bump `7edf519cd2c3e98f8274f2d45aa2926d8a30c60b` (41) were pushed by the owner to `degram/phase-1301` (`git -C apps/degram ls-remote origin degram/phase-1301` = `7edf519c`, equal to local HEAD). Framework gitlink `93aa2b99` → `7edf519c`, commit `4bb6e38`, `python tools/degram/workspace.py verify` exit 0 before the build. `apps/revit-mcp` unchanged at `d8f0f24d2d29c8115f1e21b6573f52a360b34cad`.

**Services (owner consent "rebuild ok", limited to `data-service` and `design-grammars`).** Docker Desktop was down at the start of the session (`docker ps`: npipe dockerDesktopLinuxEngine not found); it was started from `C:\Program Files\Docker\Docker\Docker Desktop.exe` and the engine answered in about 20 s. Both images were rebuilt with `docker build --no-cache` from a `git archive` export of framework HEAD `4bb6e38` (`data-service/` and `ui-v2/` only, exported to `C:\dgsrc41b`), not from the working tree, so other sessions' uncommitted edits (`data-service/cypher_allowlist.py`, `dg_context.py`, `ui-v2/src/lib/auth.js`, `ProjectsScreen.jsx`) are **not** in the running images. Tagged `design-grammar-system-data-service` (`sha256:85ab2c31e575…`) and `design-grammar-system-design-grammars` (`sha256:1c7a4a5b6465…`); both containers recreated with `docker compose up -d --no-build --no-deps`, and `docker inspect` shows them on those image ids. Stale-image check: `docker exec data-service grep -c connector_access /app/app.py` = 21 and `POST /connector-access-requests` is present at `app.py:4881`; the served UI bundle `App-DAE11p7y.js` contains `connector-access-requests` and «Запросить доступ», the CSS contains `status-on`, and `DeGramWorkspace-KdCbZGkZ.js` contains `degram-project`.

Side effect to note: the Docker restart left `neo4j` and `n8n` stopped (restart policy `no`), and `data-service` exits at startup without Neo4j (`Failed to DNS resolve address neo4j:7687`). `docker start neo4j` was run on the existing container (no data, config or image change) so `data-service` could come up; I did not run any command for `n8n`; it was found running (started 06:33:46Z, two minutes after neo4j) when the stack was checked at the end, so something else (compose dependency handling or the owner) started it.

Probes (no credentials used; run against `127.0.0.1:8000`): `POST /connector-access-requests` without a session → 401 `AUTH_REQUIRED` (direct and through the UI proxy `:8080/data-service`); `POST /auth/degram/session-exchange` without a session → 401 `AUTH_REQUIRED`; `GET /connectors?project=x` without a session → 401 `AUTH_REQUIRED`; UI on `:8080` → 200. **Not exercised:** `GET /connectors?project=…` returning `access` for a member, and `403 GRANT_REQUIRED` for a signed-in user without a grant (both need a signed-in session; no credentials were used). They are covered by the TestClient suite (plan 40) and are steps 2, 5 and 6 of the owner guide.

**Installer.** `D:\dgb\src` (clean no-hardlinks clone, ReadOnly cleared on `apps\desktop\build\agent-payload` first) fetched from the local component repo and detached at `7edf519cd2c3e98f8274f2d45aa2926d8a30c60b`, clean before and after (`git status` 0 entries); `D:\dgb\run-build.sh` with the scrubbed environment and `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'` (clone at `d8f0f24d`). Build 2026-10-12T06:35:56Z → 06:50:06Z, exit 0. D: free after the build: 17 GB (older installers 0.1.9, 0.1.10 kept).

| Item | Value |
|---|---|
| Installer | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.11.exe` |
| Installer size | 490,531,811 bytes |
| Installer SHA-256 | `938305fb499e2866064dd26840b43dc37d82c7e9f3f7c28bd7dec830a0d904fa` |
| Unpacked `app.asar` SHA-256 | `a4f7ec637910f097d917270247472865fdfed051547aa0065c13c7e788996985` |
| Component commit / gitlink | `7edf519cd2c3e98f8274f2d45aa2926d8a30c60b` |
| ProductVersion / ProductName / CompanyName | `0.1.11` / `DeGram` / `Erarchitech` |

Artifact checks (all passed): `app.asar.unpacked\dist\electron-main.mjs` contains `com.erarchitech.degram`, `degram-select`, `host=degram`, `showStart`, `session-exchange`, `GRANT_REQUIRED`, `degram-new-session`, `degram-state=`, the new `degram-project` and `ignoreProfile` (scope-profile preference guard), and the G-25 gate message `refused to start the backend of a scope profile`; it does **not** contain `auth/degram/exchange`; `resources\revit-mcp\extension.json` `"default_enabled": "True"`, `main.py` `json_body`, `revit_mcp\views.py` `urllib.parse`; `resources\revit-mcp\tests` absent. The HostedConnectorsTable code lives in the DG UI (`ui-v2`, served by the rebuilt `design-grammars` container), not in the installer: its presence is the bundle check above (the minified bundle keeps strings, not component names).

Built only: not installed, DeGram not launched, the installed Hermes profile untouched, nothing pushed. Installation and live UAT are the owner's checkpoint; guide: `1301-0.1.11-TEST-GUIDE.md`.

## 1308 UAT build: Projects sidebar row and single language setting (2026-10-13)

Owner-authorized local build of `win-unpacked` for the Phase 1308 group F UAT (DeGram sidebar «Projects», Settings → Appearance → Language). Component `c476c236ad04be8aa28f42410ed20f2e1372858e` (`degram/phase-1308`: `5f1d3aa8` 1308-17 + `c476c236` 1308-21), on the fork and pinned by the framework gitlink (`workspace.py verify` exit 0). `apps/revit-mcp` unchanged at `d8f0f24d`. The builder config still sets version `0.1.11`, so the 0.1.11 artifacts of `7edf519c` were renamed first, not overwritten: `release\DeGram-Setup-0.1.11-7edf519c.exe` (+ `.blockmap`) and `release\win-unpacked-0.1.11-7edf519c\`.

**Build.** `D:\dgb\src` (clean clone) fetched from the local component repo and detached at `c476c236`, 0 `git status` entries before and after; ReadOnly cleared on `apps\desktop\build\agent-payload`; `D:\dgb\run-build.sh` with the scrubbed environment and `DEGRAM_REVIT_MCP_SOURCE='D:\dgb\revit-mcp-src'` (clone at `d8f0f24d`, clean). Build 2026-10-13T21:23:06Z → 21:35:19Z, exit 0. D: free after the build: 15 GB.

| Item | Value |
|---|---|
| Unpacked app | `D:\dgb\src\apps\desktop\release\win-unpacked\DeGram.exe` (1.7 GB, 32,136 files) |
| Unpacked `app.asar` SHA-256 | `ea34886f3aff6d066b4194fdd92b8e674e80734b48dfdac3545cc24b143c9d62` |
| Installer (by-product, same version name) | `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.1.11.exe`, 490,542,483 bytes, SHA-256 `9fbe6bb8dc9191a3315dc2be7a64abb629895f5c915da543aafb6728f215440f` |
| `resources\install-stamp.json` | commit `c476c236ad04be8aa28f42410ed20f2e1372858e`, `dirty: false` |
| ProductVersion / ProductName / CompanyName | `0.1.11.0` / `DeGram` / `Erarchitech` |

Artifact checks (all passed): `app.asar.unpacked\dist\electron-main.mjs` contains `com.erarchitech.degram`, `degram-select`, `host=degram`, `showStart`, `session-exchange`, `GRANT_REQUIRED`, `degram-new-session`, `degram-state=`, `degram-project`, `ignoreProfile` and the new `degram-lang`; it does **not** contain `auth/degram/exchange`. The packaged `app.asar` (extracted to a temp dir on D:, then deleted) has the `degram-go=(landing|graph|model|connectors|projects)` fragment (1308-17), `degram-lang`, «Русский», «Проекты» and spot-checked RU catalog strings added in `c476c236` («Подключить», «Удаление…»). `resources\revit-mcp\extension.json` `"default_enabled": "True"`; `resources\revit-mcp\tests` absent.

This supersedes the 1308-21 in-tree test package (`apps/degram/apps/desktop/release/win-unpacked`, dirty stamp `5f1d3aa8`) for UAT. Built only: not installed, DeGram not launched, the installed Hermes profile untouched, nothing pushed. D-54 completeness test still 1 failed / 65 passed (deferred to the in-app review).
