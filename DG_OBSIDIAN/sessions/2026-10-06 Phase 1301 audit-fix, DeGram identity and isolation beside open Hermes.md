---
tags: [session, degram, phase-1301, audit-fix, isolation, installer, relay, connectors]
date: 2026-10-06
---

# Session: 2026-10-06 — Phase 1301 audit-fix: Gena lessons, DeGram identity, isolation beside an open Hermes, relay from Web UI settings, pairing connector planned

Model: claude-opus-5-5. Command: `/gsd-audit-fix` for phase 1301, with the instruction to study the Genpro «Гена» Hermes fork (`GenproMM/MastermindServices/12_GenproAI_HermesFork`, installed here as `Gena.exe`, shortcut «Мастермайнд») and adapt its lessons to DeGram.

## Goal

Find what DeGram still lacks to run as a fully separate product beside the original Hermes (own name, icon, data folders), fix it, and close the plan 15 leftovers from the previous session.

## What Was Done

- **Gena study.** Gena gets its own `%APPDATA%\Gena` from a distinct `productName`, its own agent home `%LOCALAPPDATA%\gena` (env `GENA_HOME`, never an inherited `HERMES_HOME`), stamps the exe with rcedit, replaces the icon files in place, and keeps upstream edits narrow. Gena's own bugs (AUMID left as Hermes, finish stage overwriting the user `HERMES_HOME`, kills by image name) are already avoided by DeGram. Lessons recorded in `spec/degram/WORKSPACE.md` (identity and isolation surface + six rules).
- **Audit-fix findings F-01..F-10, all closed:**
  - F-01 window title `Hermes` → `DeGram` (`05d7eee8`); F-02 exe vendor → Erarchitech (`df584929`, completed in `a9e56d7e`); F-03 WORKSPACE surface (`f4e1c74`).
  - F-04 owner-supplied halftone-hexagon icon (91 dots, lattice measured to 0.08 px), redrawn by `apps/desktop/scripts/generate_degram_icons.py` over the upstream filenames, 19-dot reduced mark at 16–32 px (`2103d06c`).
  - F-05 pilot version `0.1.0`, patch +1 per installer build, never reused (`a0ec2d2e`).
  - F-06 preload answers REST paths the backend locks with the same 403 and sends nothing (`43658b61`): 0 `DEGRAM_LOCKED` lines at launch (was a flood).
  - F-07 DeGram put its own `hermes.cmd` first in the user PATH; fixed in `69eb9a1d`, PC cleaned. See [[knowledge/debugging/DeGram first launch put its own hermes command first in the user PATH|debug note]].
  - F-08 `%APPDATA%\HermesBundledCommit386bd70` deleted; 8 + 1 `hermes-pytest` user-PATH entries removed.
  - F-09 both `degram/phase-1301` branches pushed (`Erarchitech/degram` `a9e56d7e`, `Erarchitech/revit-mcp-server` `937384f`) after a secret scan; gitlinks bumped (`f83938c`); `workspace.py verify` passes; tools/degram tests 19/19.
  - F-10 launch beside an **open** Hermes Desktop: control window 2 created/23 modified (Hermes alone), launch window 0 created/0 deleted/13 modified of the same kinds; no attach line, no DeGram pid in Hermes' spawn ledger, PATH and `HERMES_HOME` byte-identical, title `DeGram`, clean close.
- **Installer.** Rebuild 1 from `69eb9a1d` still shipped the red commit-badge Nous icon, version 0.0.0 and vendor Nous Research — the build driver overrode the committed fixes; never launched, deleted. Fixed in `a9e56d7e`. See [[knowledge/debugging/Commit build driver overrode the DeGram icon, version and vendor|debug note]]. Rebuild 2: `DeGram-Setup-0.1.0.exe`, SHA-256 `70a73670…14f9a`, DeGram icon/version/vendor verified on the packaged exe and `app.asar`. Record: `1301-BUILD.md`.
- **Plan 16 preparation.** Provider-export policy set for `v12-hexagonal-facade-01` (export allowed, whole definition not), written through `degram_policy.set_policy` in the container with `updatedBy: operator:claude-code (owner-approved 2026-10-06)`. The project has no company assignment yet.
- **Relay config source (D-24).** Owner chose that the relay takes endpoint, model and key from the Web UI LLM settings: `degram-llm.json` and `PUT /degram/admin/llm-config` removed, only provider `openai` is runnable, no fallback (`c5966d4`, specs SECURITY-BOUNDARY/API/OPERATIONAL-OUTCOMES, route table 96→95, 881 tests). data-service rebuilt; live relay reads `router.genproagent.ru/v1`, model `gena-mid` (the owner's own Web UI setting). See [[knowledge/decisions/DeGram relay takes its model and key from the Web UI LLM settings|decision]].
- **DeGram connector (D-25, D-26).** Owner wants DeGram's token created in the Connectors tab. Planned as `1301-17-PLAN.md` (wave 8; plan 16 moved to wave 9): user-bound pairing token `dgp_`, stored by DeGram with `safeStorage`, exchanged for the existing 15-minute `dgd_`; accepted by no other route; revocation cascades (`df62f9e`). See [[knowledge/decisions/DeGram connects through a user-bound pairing connector in the Connectors tab|decision]].

## Decisions Made

- Owner: CompanyName Erarchitech; all icon recommendations; version scheme 0.x; F-06 filter; F-07 no PATH command; F-08/F-09/F-10 authorized; pytest PATH entries removed.
- Owner: Genpro and Gena are **reference only** — no URLs, keys or config from them may be used to connect DeGram. The relay's Web UI source is the owner's own DG setting.
- D-24 (relay from Web UI LLM settings), D-25 (pairing connector), D-26 (user-bound) in `1301-CONTEXT.md`. See [[knowledge/decisions/DeGram product identity follows the Gena fork lessons|identity decision]].

## Issues Encountered

- Upstream `tests/hermes_cli/test_hermes_home_shared_launchers.py` writes the real user PATH on Windows; one entry added by this session's run was removed at once. Two upstream launcher tests are flaky on this host (pass in isolation, with and without the F-07 change).
- I read Gena's `config.yaml` for a base URL before the owner said Genpro/Gena are reference only; nothing from it was used.
- ui-v2 has no test runner; plan 17 checks the Connectors card by build + live check (adding a runner needs a package install).

## Next Steps

1. `/gsd-execute-phase 1301` → plan 17 starts with the owner checkpoint: keep the in-app DG sign-in for the DG page? does a pairing expire?
2. After plan 17: create a pairing in Connectors, run `relay_probe.py` with it, then plan 16 (two-PC UAT with the next installer `0.1.1`).
3. Optional: assign a company to `v12-hexagonal-facade-01` (`PUT /projects/{project}/company`).

## Related Notes

- [[sessions/2026-10-06 Phase 1301 plan 15 rebuild and DeGram isolation proven beside Hermes]]
- [[knowledge/debugging/Packaged DeGram ignored the degram variant and attached to the live Hermes]]
