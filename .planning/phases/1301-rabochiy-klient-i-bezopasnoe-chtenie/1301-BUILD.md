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
