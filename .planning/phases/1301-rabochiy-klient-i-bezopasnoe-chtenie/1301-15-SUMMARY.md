---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 15
subsystem: degram-installer-and-clean-install
tags: [degram, nsis, installer, revit-mcp-resource, clean-install-protocol, first-launch-isolation, packaged-identity, stop-rule]
requires: ["1301-09", "1301-14"]
provides:
  - "degram extraResources carry the read-only revit-mcp adapter as resources/revit-mcp (no tests/.git/bytecode/.venv); DEGRAM_REVIT_MCP_SOURCE overrides the source path"
  - "NSIS is an admitted prepared packaging format on win32 (run-electron-builder, prepare-packaging-tools, prepared-packaging); the NSIS toolset comes from electron-builder's own pinned supplier"
  - "silk and daytona are opt-in extras so the payload builds without a C or Rust toolchain"
  - "Fix: the packaged electron-main bundle bakes the DeGram identity from the stamp (component 910a060d, local only)"
  - "docs/degram/CLEAN-INSTALL.md (D-12 protocol with one check per bridge state and an identity gate)"
  - "1301-BUILD.md: build command, artifact hash, launch listings and attribution"
affects: [1301-16]
key-files:
  created:
    - docs/degram/CLEAN-INSTALL.md
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-BUILD.md
    - apps/degram/tests/degram/test_payload_extras.py
  modified:
    - apps/degram/apps/desktop/electron-builder.config.cjs
    - apps/degram/apps/desktop/scripts/{degram-build.test.mjs,run-electron-builder.mjs,prepare-packaging-tools.mjs,prepared-packaging.mjs,bundle-electron-main.mjs}
    - apps/degram/pyproject.toml
requirements-completed: []
requirements-partial: [DGCL-01, DGCL-04]
status: partial
---

# Phase 1301 Plan 15: Installer, clean-install protocol and first-launch isolation Summary

**Status: PARTIAL, STOPPED BY THE ISOLATION RULE.** An unsigned NSIS installer with the bundled agent payload and the read-only `revit-mcp` adapter was built and the clean-PC protocol is written, but the one authorized launch showed the built app running as stock Hermes Desktop: it attached to the owner's live Hermes backend and caused writes in `%LOCALAPPDATA%\hermes`. Per the stop rule nothing was pushed and no gitlink was bumped. The root cause (packaged identity not baked) is fixed and tested in the component, locally; a rebuild and a second, separately authorized launch are needed before the push.

## Authorization

Task 1 (checkpoint:decision) was presented to the owner on 2026-10-05 and resolved. Recorded verbatim:

- Selected option: **all (a)-(d)**: (a) local payload + NSIS build of variant degram on this PC; (b) ONE launch of the built DeGram on this PC after all isolation tests are green, with the before/after Hermes listing; (c) `git push` of branch degram/phase-1301 to https://github.com/Erarchitech/degram and of the revit-mcp branch degram/phase-1301 to https://github.com/Erarchitech/revit-mcp-server (public forks, component source only); (d) framework gitlink bump commit for apps/degram and apps/revit-mcp.
- Additional owner decision: **authorized** extending format admission (run-electron-builder.mjs / prepare-packaging-tools.mjs admit only dir/msix/zip on win32 today; plan 04 finding) and acquiring the NSIS toolset through electron-builder's own pinned download mechanism as part of the build. No new package.json dependency; no other package installs.
- Date: 2026-10-05.
- Still NOT authorized: `hermes update`; any write to %LOCALAPPDATA%\hermes, ~/.hermes or the user's installed Hermes profile/userData; pushing anything other than the two named branches (no force push, no tags, no other branches, never to upstream remotes); Docker/service operations; signing certificates; installing the produced installer on this PC; real LLM/provider calls; signing in to DG; entering any credential; reading .secrets.

What was and was not exercised under it: (a) done; (b) done once, and it tripped the stop rule; (c) and (d) not done; the installer was only built, never installed; no credential, provider, Docker or `.secrets` access.

## Outcome by task

| Task | Result |
|---|---|
| 1 decision | recorded above |
| 2 payload, installer, protocol, launch | installer built (exit 0), protocol written, **launch isolation FAILED** (see below) |
| 3 push and gitlink bump | **not done** (stop rule); `workspace.py verify` still reports gitlink != child HEAD for both children |

## Commits

Component `apps/degram`, local branch `degram/phase-1301` (committing repository: component), base `0ee2d12f`, **not pushed**:

| Commit | Message |
|---|---|
| `6e2b4889` | feat(1301-15): degram ships the revit-mcp adapter resource and NSIS is an admitted prepared format |
| `386bd704` | build(1301-15): silk and daytona are opt-in extras so the DeGram payload builds without a native toolchain |
| `910a060d` | fix(1301-15): bake the DeGram identity into the packaged main bundle |

Component `apps/revit-mcp`: unchanged at `937384f`. Framework (master): the `docs(1301-15)` commit with this SUMMARY, `1301-BUILD.md`, `docs/degram/CLEAN-INSTALL.md`, STATE.md and ROADMAP.md. No gitlink in it.

## What was built

- **revit-mcp as a resource (tests first, RED then GREEN).** `electron-builder.config.cjs` adds `{from: <apps/revit-mcp>, to: 'revit-mcp', filter: [...]}` for degram only; the filter excludes `tests`, `.git`, `.github`, `__pycache__`, `*.pyc`, `.venv`, caches. The built installer carries `resources\revit-mcp` (source, `pyproject.toml`, `uv.lock`, `extension.json`, `startup.py`). The existing `resolveRevitAdapter` already looks exactly there; a test pins the layout.
- **NSIS admission (tests first).** `nsis` recognised by `run-electron-builder` (Windows default for degram, msix for every other variant), supported on win32 only by `prepare-packaging-tools` (`supportedPackagingFormats`, `defaultPackagingFormats`), `prepareNsisToolset` copies the pinned toolset into the work directory, `readPackagingInputs` refuses nsis inputs without it. The real run acquired `nsis@1.2.1` through the builder's own supplier.
- **Build (D-04).** `desktop.py --commit=<sha> --variant=degram` from a clean clone, exit 0 after 39.5 min: `DeGram-Setup-0.0.0.exe`, 1,931,722,535 bytes, SHA-256 `46845872fa2646e1ec30935e42f29dcbe9cae99df6783d0abda5612192d4b13f` (details, environment and obstacles in `1301-BUILD.md`).
- **`docs/degram/CLEAN-INSTALL.md` (D-12).** Prerequisites, pyRevit 6.5.3, the pyRevit extension step, `[routes]` with `host = "127.0.0.1"`, the DG CANVAS LISTENER, DG origin, install and the SmartScreen prompt, the adapter interpreter gap, operator steps (company, relay, provider-export policy), one check per bridge state with the UI-SPEC copy, and an identity gate before the first start.

## The launch failure (D-02) - the main result of this plan

One launch, no sign-in, 75 s, closed cleanly, no process left. Hermes was live (5 `Hermes.exe`), so a control window was taken: 12 heartbeat/sidecar modifications with no DeGram running, versus **10 created and 22 modified (0 deleted)** in the launch window. The Hermes logs name the DeGram process as a client at the launch second: `[attach] attached to the running Hermes backend on http://127.0.0.1:62917 (pid 40472 ...); spawning nothing`, a WebSocket held for 76 s with 43 messages that closed one second after `CloseMainWindow`, and server-side effects 1.5 to 7 s after launch: `bot_relay\`, `desktop-plugins\jev`, two lazily compiled `.pyc` in `hermes-agent`, appended logs, and **`owner-backfill: stamped 11 legacy NULL-profile session row(s)`** (a write to the owner's session store; possibly a first-connect migration any GUI client would trigger) plus a failed wake-word microphone start. `%LOCALAPPDATA%\DeGram` was not created; `%APPDATA%\HermesBundledCommit386bd70` was. The window title was `Hermes`. Full evidence: `1301-BUILD.md`.

**Root cause.** `bundle-electron-main.mjs::productIdentity` derived the identity baked into the packaged main from the stamp `payload` (`bundled`) and ignored `variant: "degram"`, so the packaged app carried the stock bundled+commit identity (`com.erarchitech.degram` occurs 0 times in the built `electron-main.mjs`): no isolation, host-backend attach on, `HERMES_HOME` inherited. This is a defect of plan 04, whose identity tests set `HERMES_DESKTOP_VARIANT` in the environment, which a packaged app never has. Fixed in `910a060d` with a RED-first end-to-end test (the bundled `electron-main.mjs` of a degram stamp must contain `com.erarchitech.degram`; a bundled stamp must not). **The built installer predates the fix; do not launch or distribute it.**

## Deviations from Plan

**1. [Rule 3 - Blocking] Build from a clean clone on D:.** `desktop.py` refuses an unclean checkout (8 untracked pytest artifacts that must not be touched) and the shell's Node 20 violates the engines. The build ran from a clean local clone at `D:\dgb\src` with PM's own Node 26.7.0 and a scrubbed environment.

**2. [Rule 3 - Blocking] PM Node staging `WinError 5`.** After two failures the Node and npm store entries were copied (read-only use) from the installed Hermes store into the build-owned store with their `facts.json` records (artifact SHA-256 equal to `pm/lock.json`).

**3. [Rule 3 - Blocking] Opt-in extras `silk` and `daytona` (commit `386bd704`).** `pilk` needs MSVC plus the Windows SDK (absent) and `obstore` has no CPython 3.14 Windows wheel; installing a compiler is outside the authorization. The extras stay declared, locked and installable on demand; neither belongs to the read-only agent. A pyproject line in the fork: note it for upstream merges.

**4. [Rule 3 - Blocking] Disk.** `C:` was 100% full; the first run hit `ENOSPC`. Moved to `D:\dgb`, `C:\dgb` deleted.

**5. [Rule 1 - Bug in plan 04] Packaged identity not baked.** See above (`910a060d`).

**6. [Plan interpretation] `docs/degram/CLEAN-INSTALL.md` states the adapter interpreter as a manual step.** The payload cannot carry an interpreter for the locked adapter: `mcp` 1.9.0 pins `pydantic-core` 2.33.2, whose wheels cover CPython 3.11 to 3.13 only (verified in `uv.lock`), the payload is CPython 3.14, and a venv binds to a host Python. Shipping a relocatable CPython 3.13 would need another download that was not authorized. The installer ships source and lock; the protocol runs `uv sync --frozen --python 3.13` once.

**7. [Disclosure] Possible Hermes cache touch by my first attempt.** The very first `npm run payload` (18:35-18:37 UTC) ran before I scrubbed the environment, with the shell's inherited `HERMES_HOME=C:\Users\Admin\AppData\Local\hermes`. Three Hermes entries have mtimes inside that window (`cache\uv\interpreter-v4\...msgpack`, `cache\uv`, `installs\...\pm-runtime\generations\...\.leases`); they may be mine or the live Hermes's. All later build commands ran scrubbed. Listing evidence in `1301-BUILD.md`.

## Findings for the owner and plan 16 (recorded, NOT changed here)

- **Plan 14 open decisions.** (a) *Sign-out has no entry point* (`requestDegramSignOut()` is wired, no control): recommend a "Sign out of DG..." item in the application menu and in the scope strip's user/company popover. (b) *Profile switcher, profile rail and the shared-metrics consent dialog are not gated*: recommend adding all three to the hidden-surface list (DeGram has one scope-bound profile per user, company and project and no telemetry). (c) *Stock resubmit, queue and steer surfaces bypass the Context card gate* (plain `prompt.submit`, no snapshot, no consent): recommend hiding queue, steer and the per-message retry in variant degram (like `stock-error-retry`) for v1, so D-17's "every send shows its card" holds without a second gate path.
- **Window title.** The launched stock shell titled itself `Hermes`; confirm the DeGram identity titles its windows `DeGram` in the rebuild (the page `<title>` can override the BrowserWindow title).
- **Payload size.** 5.9 GB staged and a 1.9 GB installer, mostly llama.cpp (cpu/cuda/hip/vulkan), chromium and ffmpeg that the read-only agent never uses: recommend a DeGram payload tool selection.
- **Disk and AV.** `C:` is at 100%; the PM and `dist` rename failures are Windows/antivirus handle races that passed on retry.
- **Plan 12 note.** `resolveProfilesInvocation` against the real payload: `tools\python-3.14.7...\python.exe` exists and imports `degram_variant.profiles` with `PYTHONPATH=<hermes-agent>;<venv\Lib\site-packages>`. Not exercised: the bridge client import (`mcp.server.stdio` needs the `pywin32.pth` site processing that the launcher does and a bare `PYTHONPATH` does not).
- **Live Hermes makes an empty diff impossible.** Any D-02 listing proof on this PC needs the Hermes Desktop closed, or the control-window method used here.

## Not verified (honest limits)

The fixed identity is proven by tests and by inspecting the bundle, not by a second launch or a rebuild. The NSIS installer was never run (not authorized). The adapter was never started from the packaged resource; no pyRevit or Revit session; the clean-PC protocol was not executed. Whether `owner-backfill` is triggered by any new GUI client is inferred from timing, not proven.

## Known Stubs

None.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: info-disclosure-local | apps/desktop/scripts/bundle-electron-main.mjs | T-1301-15-02 (first launch alters the user's Hermes) materialised: a packaged app with the stock identity wrote to the Hermes home. Mitigated by `910a060d` and the identity gate; the proof must be repeated on the rebuild. |

## Self-Check: PARTIAL

- FOUND: `docs/degram/CLEAN-INSTALL.md` with `[routes]`, `127.0.0.1`, `6.5.3`, `DG CANVAS LISTENER`; `1301-BUILD.md`; component commits `6e2b4889`, `386bd704`, `910a060d`; installer `D:\dgb\src\apps\desktop\release\DeGram-Setup-0.0.0.exe` (SHA-256 recorded).
- NOT MET: empty Hermes before/after diff (failed, attributed); push of the two branches; gitlink bump; `workspace.py verify` exit 0 on the exact pair.
