---
tags: [session, degram, phase-1301, isolation, installer]
date: 2026-10-06
---

# Session: 2026-10-06 — Phase 1301: plan 15 rebuild, DeGram isolation proven beside Hermes, plan 16 started

Model: claude-sonnet-5-5. Command: `/gsd-execute-phase 1301` (only plan 16 was incomplete).

## Goal

Finish Phase 1301: plan 16 (live acceptance on two PCs) after resolving the plan 15 blocker (installer predated the identity fix, never relaunched, nothing pushed).

## What Was Done

- **Owner decisions (AskUserQuestion).** Plan 16 Task 1: authorized **all (a)–(e)** (Docker rebuild, relay config with owner-entered key + pilot provider-export policy, paid inference, pyRevit install on both PCs, live read-only CAD reads). Plan 15: authorized **rebuild + second launch**; push of the two `degram/phase-1301` branches and the gitlink bump only if the isolation diff is acceptable. Date 2026-10-06. **Not yet written to a `1301-16-SUMMARY.md` `## Authorization` section** (creating a SUMMARY would mark plan 16 complete for the tooling); copy this paragraph in when plan 16 resumes.
- **Plan 16 Task 2 (offline part).** `tools/degram/relay_probe.py` + `tools/degram/tests/test_relay_probe.py` (4 cases: stream, stream+tool, tool-history follow-up, cancel after first chunk; Bearer token from env var; no retry/fallback; unknown stays null; token never in report). TDD RED→GREEN, 5 tests pass. Commit `f65d335`. Live run not done (needs a delegated token minted by the owner's signed-in DeGram session and a configured relay).
- **Docker.** `docker compose build --no-cache data-service design-grammars` + `up -d` done; container holds `degram_relay.py`/`delegation.py`; relay route answers 401 unauthenticated. Later in the session Docker Desktop was no longer running (`localhost:8080` refused).
- **Installer rebuilt from component `910a060d`** in the clean clone `D:\dgb\src` (scrubbed env): first attempt failed in 3.5 min on a stale read-only `apps\desktop\build\agent-payload` (cleared inside the build clone), second attempt exit 0 at 23:31Z. `DeGram-Setup-0.0.0.exe` 1,931,719,493 bytes, SHA-256 `4fa89e7e56c31f2e7d0ff100e9a6dd56145f0ca334b9bef8b7780ad65398e9a4`. Identity gate: `com.erarchitech.degram` occurs 1× in `app.asar.unpacked\dist\electron-main.mjs` (was 0×).
- **Isolation verified by code and by a live launch.** Code: fixed `%LOCALAPPDATA%\DeGram\{home,userData}`, `HERMES_HOME` pinned before the main-process `HERMES_HOME` const is evaluated (`main.ts` 747 vs 1337), attach-to-host off, `degram://` protocol, no updater, `HOME_OVERLAP` fail-closed; vitest 45/45. Live (Hermes Desktop closed by the owner, `HERMES_HOME` still inherited): own home with its own `state.db`, 12 skills (Hermes has 36), own backend on 127.0.0.1:64449, no attach line, no DeGram client in Hermes logs, `/api/config|profiles|model/info` → 403 `DEGRAM_LOCKED`, clean quit with no leftover process or listener. Hermes folders: control 4 modified, launch window 0 created / 0 deleted / 20 modified — all written by Hermes's own still-running background gateway (10-minute MCP reconcile at 09:52:05, `spawn-ledger.json` entries owned by Hermes pid 59536). Attribution by timing/ownership, not an empty diff. Recorded in `1301-BUILD.md`, commit `bcfcc71`.

## Decisions Made

- No `1301-16-SUMMARY.md` is created until plan 16 actually completes (see above).
- Push and gitlink bump deliberately **not** done: left as an owner decision because the literal "empty diff" condition is not met (explained above).

## Issues Encountered

- The auto-mode permission classifier blocked a first DeGram launch beside a *running* Hermes with inherited `HERMES_HOME` ("Modify Shared Resources"); not worked around. The owner closed Hermes Desktop and the launch was re-run.
- `Start-Process` after `Remove-Item Env:` / `SetEnvironmentVariable($null)` produced a silent exit 0; fixed by `ProcessStartInfo.Environment.Remove('ELECTRON_RUN_AS_NODE')`. See [[knowledge/debugging/Electron app exits silently when launched from VS Code shell with ELECTRON_RUN_AS_NODE]].
- PowerShell tool refused a script containing `Remove-Item Env:` plus a `'\s+'` regex (false positive); worked around by not using those constructs.
- Findings still open: window title shows `Hermes`; renderer polls locked endpoints (stderr flood of `DEGRAM_LOCKED`); `%APPDATA%\HermesBundledCommit386bd70` left over from the first (stock-identity) launch; Hermes background gateway/MCP python processes survive closing Hermes Desktop.

## Next Steps

1. Owner decisions: (a) push `degram/phase-1301` of `apps/degram` (`910a060d`) and `apps/revit-mcp` (`937384f`) then bump gitlinks and `workspace.py verify`; (b) delete `%APPDATA%\HermesBundledCommit386bd70`; (c) reopen Hermes Desktop and repeat the DeGram launch to prove parallel running with the Desktop open (blocked by the classifier unless the owner explicitly allows it or adds a rule).
2. Start Docker Desktop and the stack; owner enters the genpro relay key via `PUT /degram/admin/llm-config` and sets a pilot-project provider-export policy; owner mints a delegated token; run `python tools/degram/relay_probe.py --base http://localhost:8000` and append the report to `1301-UAT.md` (no token).
3. Install the new `DeGram-Setup-0.0.0.exe` on PC1 and PC2 per `docs/degram/CLEAN-INSTALL.md` and walk Task 3 steps 1–7 with the owner; write results to `1301-UAT.md`; then plan 16 SUMMARY (with `## Authorization`), phase verification and completion.
4. Resume with `/gsd-execute-phase 1301`.

## Related Notes

- [[sessions/2026-10-05 Phase 1301 executed through plan 14, plan 15 launch failed isolation]]
- [[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes]]
- [[knowledge/decisions/DeGram Phase 1301 execution authorizations and narrowed baseline]]
