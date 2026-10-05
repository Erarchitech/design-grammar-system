---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 03
subsystem: workspace-components
tags: [revit-mcp, submodule, fork, workspace-verify, fail-closed, tdd]
requires: []
provides:
  - "apps/revit-mcp pinned submodule (fork Erarchitech/revit-mcp-server, gitlink 74a8ddca)"
  - "additionalComponents manifest entry and multi-component workspace.py verify"
  - "local component branch degram/phase-1301 in apps/revit-mcp for plan 07"
affects: [1301-07, 1301-11, 1301-15]
tech-stack:
  added: []
  patterns: ["generic verify_component(root, path, fork, upstream) shared by apps/degram and additional components"]
key-files:
  created:
    - tools/degram/tests/test_workspace_revit_mcp.py
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-03-SUMMARY.md
  modified:
    - .gitmodules
    - apps/revit-mcp
    - integration/degram/workspace.json
    - tools/degram/workspace.py
    - spec/degram/WORKSPACE.md
key-decisions:
  - "Additional components use a strict competing-authority check (.planning/, ROADMAP.md, DG_OBSIDIAN); apps/degram keeps its original narrower check and messages"
  - "Missing remote now yields a ValueError (fail closed) instead of a raw CalledProcessError"
requirements-completed: []
requirements-partial: [DGCL-04]  # enabler only: fork/submodule/verify; the read-only allowlist and relay arrive in plans 07 and 11
duration: ~25 min
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 03: Revit adapter fork as second pinned component Summary

The owner fork `Erarchitech/revit-mcp-server` (public fork of `Demolinator/revit-mcp-server`) is registered as pinned submodule `apps/revit-mcp` at upstream commit `74a8ddca6ee5119063dc685f8dad7e8b52b0a769`, and `workspace.py verify` now checks it fail-closed alongside `apps/degram`.

## Authorization

Task 1 (checkpoint:decision) was presented to the owner on 2026-10-04 and resolved: option **authorize**. Recorded verbatim: authorized (a) `gh repo fork Demolinator/revit-mcp-server --org Erarchitech --clone=false` (public fork, upstream content only), (b) `git submodule add https://github.com/Erarchitech/revit-mcp-server.git apps/revit-mcp` pinned to 74a8ddca, (c) local `upstream` remote, (d) `uv sync` in apps/revit-mcp (lockfile restore), (e) local commits in apps/revit-mcp on new local branch degram/phase-1301 for plan 07 (no push; push is plan 15). No push of any DG material to the fork. Date: 2026-10-04.

Pre-checks: `gh auth status` showed an authenticated session as account `Erarchitech`; `gh repo view Erarchitech/revit-mcp-server` confirmed no fork existed before this plan.

## What was done

- RED: `tools/degram/tests/test_workspace_revit_mcp.py` (9 cases, temporary git repos) written first and run against the old `workspace.py` (10 failures, 3 errors across the module).
- GREEN: `workspace.py` refactored into a shared `verify_component()` (gitlink = child HEAD, `origin`/`upstream` equal to manifest, competing authority absent). `verify_workspace()` verifies `apps/degram` exactly as before (same messages, same report keys) and then every entry of `additionalComponents`, adding a `components` list to the report. Component paths go through `safe_path`.
- Public fork created: `https://github.com/Erarchitech/revit-mcp-server` (visibility PUBLIC, isFork true, parent Demolinator).
- `git submodule add` registered `apps/revit-mcp`; the clone's default tip was already `74a8ddca6ee5119063dc685f8dad7e8b52b0a769` (full sha recorded as `upstreamBaseCommit`), so no checkout was needed.
- Local `upstream` remote added: `https://github.com/Demolinator/revit-mcp-server.git`.
- `uv sync --frozen` in `apps/revit-mcp` (uv 0.11.1, Python 3.13 per `.python-version`): environment restored strictly from the upstream `uv.lock`; no lock change, `git -C apps/revit-mcp status --short` is empty (`.venv` ignored).
- Local branch `degram/phase-1301` created in `apps/revit-mcp` at 74a8ddca. No commit inside the child, nothing pushed.
- `manifest` gained an additive `additionalComponents` array; all existing `apps/degram` fields and `schemaVersion: 1` are unchanged. WORKSPACE.md has a new "Revit adapter component" section.

## Verification

- `python -m unittest discover -s tools/degram/tests -v`: 14 tests, OK (5 pre-existing plus 9 new).
- `python tools/degram/workspace.py verify`: exit 0; `components` lists `degram` and `revit-mcp`, both gitlink == HEAD.
- `git -C apps/revit-mcp rev-parse HEAD` = `74a8ddca6ee5119063dc685f8dad7e8b52b0a769`; `remote get-url upstream` = `https://github.com/Demolinator/revit-mcp-server.git`; branch `degram/phase-1301`.

## Deviations from Plan

**1. [Rule 3 - Blocking] `gh repo fork --org Erarchitech` rejected**
- **Found during:** fork creation.
- **Issue:** GitHub returned HTTP 422: `Erarchitech` is a user account, not an organization (the existing `Erarchitech/degram` fork is also a user-account fork).
- **Fix:** ran the same authorized command without `--org`, `gh repo fork Demolinator/revit-mcp-server --clone=false`, authenticated as `Erarchitech`. The result is the exact authorized target `https://github.com/Erarchitech/revit-mcp-server` (public fork, upstream content only); no other hosting route, owner, or visibility was used.
- **Files modified:** none.

**2. [Rule 2 - Missing critical] Missing remote raised raw CalledProcessError**
- **Issue:** a missing `upstream` remote in a component would surface as an unhandled git error rather than a named verify failure.
- **Fix:** `verify_component` converts git failures for HEAD/gitlink/remotes into `ValueError` (covered by tests).
- **Files modified:** `tools/degram/workspace.py`, `tools/degram/tests/test_workspace_revit_mcp.py`.

## Known Stubs

None.

## Threat Flags

None. T-1301-03-01: fork holds upstream content only, nothing pushed. T-1301-03-02: gitlink pinned to 74a8ddca, verify fails on drift (tested). T-1301-03-SC: `uv sync --frozen` lockfile restore only.

## Commits

- Framework: `b41afdf` feat(1301-03): register revit-mcp fork as second pinned workspace component
- Component: none (no commit inside `apps/revit-mcp`)

## Self-Check: PASSED

- Files exist: `tools/degram/tests/test_workspace_revit_mcp.py`, `tools/degram/workspace.py`, `integration/degram/workspace.json`, `spec/degram/WORKSPACE.md`, `.gitmodules`, `apps/revit-mcp`.
- Commit `b41afdf` exists; the commit made no file deletions.
- Unit suite and `workspace.py verify` re-run green after the commit's content was staged.
