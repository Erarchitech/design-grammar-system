---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 23
subsystem: release
tags: [degram, build, 0.1.6, gap-closure, g-3, g-4, g-5, g-6, g-7, g-8, g-9, g-10, g-11, g-12, g-13, g-14, g-15, g-16, g-17]

requires:
  - phase: 1301-18..22
    provides: gap-round component commits (degram d0d69691, 199ef7cd, 9457d72b, 02993674; revit-mcp d8f0f24)
provides:
  - "DeGram 0.1.6: component c3e8f2e8 and revit-mcp d8f0f24 pushed to the Erarchitech forks, framework gitlinks bumped, workspace.py verify exit 0"
  - "DeGram-Setup-0.1.6.exe built from a clean clone with the committed revit-mcp adapter, installed on PC1"
affects: [1301-16, DGCL-01, DGCL-02, DGCL-04, DGCL-05, DGCL-06, DGCL-07]

key-files:
  created:
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-23-SUMMARY.md
  modified:
    - apps/degram/apps/desktop/electron-builder.config.cjs
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-BUILD.md
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md

key-decisions:
  - "Push done on the owner's explicit request in this session (policy blocks agent pushes without it); outgoing commits had no secret-like paths"
  - "Build used DEGRAM_REVIT_MCP_SOURCE=D:\dgb\revit-mcp-src (clean --no-hardlinks clone at d8f0f24); the stale D:\dgb\revit-mcp was left untouched"

requirements-completed: []

coverage:
  - id: D1
    description: "Both fork branches pushed and framework gitlinks equal the pushed HEADs"
    requirement: "DGCL-01"
    verification:
      - kind: automated
        ref: "python tools/degram/workspace.py verify (exit 0; degram c3e8f2e8, revit-mcp d8f0f24) + git ls-remote on both forks"
        status: pass
    human_judgment: false
  - id: D2
    description: "0.1.6 installer carries the committed adapter and the gap round"
    requirement: "DGCL-04"
    verification:
      - kind: automated
        ref: "five artifact checks on release\win-unpacked (default_enabled True, json_body, urllib.parse, appId, no tests dir) - all pass; SHA-256 39C9EFCE...F018 recorded in 1301-BUILD.md"
        status: pass
      - kind: manual_procedural
        ref: "install on PC1: ProductVersion 0.1.6.0, hash match, pyRevit extension equal to resources\revit-mcp (agent read-only check), uv venv present"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gap rows G-3..G-17 and D-30 profile cleanup work live on 0.1.6"
    requirement: "DGCL-02"
    verification:
      - kind: manual_procedural
        ref: "plan 16 Task 3 live recheck on PC1 (1301-UAT.md run status 2026-10-09)"
        status: unverified
    human_judgment: true
---

# Plan 23 Summary: DeGram 0.1.6 shipped and installed

## Done

- Task 1: version 0.1.5 -> 0.1.6 (`c3e8f2e8`, one file); degram-build + isolation 40/40, typecheck, lint 0 errors,
  electron 218/218, ui `src/degram` 211/211, pytest `tests/degram` 400/400.
- Task 2: owner asked for the push in-session; `degram/phase-1301` pushed on both forks
  (degram `2da8a2aa..c3e8f2e8`, revit-mcp `937384f..d8f0f24`).
- Task 3: gitlinks bumped in the framework; `workspace.py verify` exit 0.
- Task 4: 0.1.6 built (clean clone `c3e8f2e8`), recorded in `1301-BUILD.md` (`d179df5`).
- Task 5: installed on PC1; pyRevit extension replaced and checked (`1301-UAT.md`).

## Deviations

- Build run 1 was stopped by the orchestrator: a carriage return had entered the adapter path in `D:\dgb\run-build.sh`.
  The interrupted `flavored_assets` step left 66 icon files modified in the throwaway clone; restored with
  `git checkout -- apps/desktop/assets`, then the build re-ran clean. Cost: one extra build (~12 min).
- The agent's own install/extension copy was denied by the permission classifier; the owner did both steps and the
  first owner pass left the extension half replaced (extension.json, revit_mcp, venv). The second pass was verified.

## Unverified

- Everything behavioural: G-3..G-17 and the D-30 cleanup are checked only by tests until plan 16 Task 3 runs on 0.1.6.
- No DGCL requirement is marked complete.
