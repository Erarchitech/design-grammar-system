---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 22
subsystem: revit-adapter
tags: [degram, revit-mcp, pyrevit, ironpython, gap-closure, g-8, g-9, g-10, g-11, g-12]

requires:
  - phase: 1301-17
    provides: pairing connector (wave 8); live run of 0.1.5 on PC1 that produced the working-tree fixes
provides:
  - "revit-mcp fork commit d8f0f24 on degram/phase-1301: pyRevit side loads on IronPython 3.4, extension enabled by default, text/plain POST bodies (G-8..G-12)"
  - "CLEAN-INSTALL step 2 enable check (disabled = false) and IronPython 3.4 note; step 9 row for an extension older than 0.1.6"
affects: [1301-16, 1301-23, DGCL-01, DGCL-04]

tech-stack:
  added: []
  patterns:
    - "pyRevit-side modules stay parseable by IronPython 3.4 and 2.7: no async/await, f-strings, annotations, walrus; explicit sibling imports (from .utils import)"
    - "JSON POST bodies cross pyRevit Routes as text/plain and are parsed by the route (parse_request_data: bytes, str or dict -> dict or None)"

key-files:
  created: []
  modified:
    - apps/revit-mcp/extension.json
    - apps/revit-mcp/degram_readonly.py
    - apps/revit-mcp/tools/__init__.py
    - apps/revit-mcp/main.py
    - apps/revit-mcp/revit_mcp/utils.py
    - apps/revit-mcp/revit_mcp/views.py
    - apps/revit-mcp/revit_mcp/documents.py
    - apps/revit-mcp/revit_mcp/colors.py
    - "apps/revit-mcp/revit_mcp/*.py (19 more route modules: explicit from .utils import)"
    - apps/revit-mcp/tests/test_degram_documents.py
    - apps/revit-mcp/tests/test_degram_readonly.py
    - docs/degram/CLEAN-INSTALL.md

key-decisions:
  - "The three line-ending-only files (revit_mcp/__init__.py, document.py, status.py) were left unstaged and unmodified in the fork working tree: restoring them with git checkout was refused by the permission classifier, and discarding working-tree state was not authorised anyway. They are empty under git diff --ignore-cr-at-eol."

patterns-established:
  - "Allowlist is untouched: the diff adds no route and no allowlist entry; structured_helper only moved module (degram_readonly -> tools) because degram_readonly is loaded by the IronPython startup.py, which cannot parse async def"

requirements-completed: []

coverage:
  - id: D1
    description: "The fork carries the live-tested G-8..G-12 fixes in one commit with its suite green"
    requirement: "DGCL-04"
    verification:
      - kind: unit
        ref: "apps/revit-mcp: uv run pytest -q (163 passed), incl. test_snapshot_accepts_a_text_plain_bytes_body, test_pyrevit_side_modules_parse_under_ironpython, test_route_modules_import_siblings_explicitly"
        status: pass
      - kind: manual_procedural
        ref: "live recheck of UAT 4.2-4.6 on the 0.1.6 install (plan 16 Task 3)"
        status: unverified
    human_judgment: false
  - id: D2
    description: "A clean install cannot end with a silently disabled extension; installer is told the engine"
    requirement: "DGCL-01"
    verification:
      - kind: grep
        ref: "docs/degram/CLEAN-INSTALL.md contains 'disabled = false' and 'IronPython 3.4'"
        status: pass
    human_judgment: false

duration: ~15m
completed: 2026-10-09
status: complete
---

# Phase 1301 Plan 22: Commit the revit-mcp fork fixes Summary

**The fixes that made the Revit bridge work live on 0.1.5 (extension enabled by default, IronPython 3.4-safe module loading, text/plain POST bodies parsed by the routes) are committed in the fork with 163 tests green, and CLEAN-INSTALL now tells the installer to check `disabled = false`.**

## Task Commits

1. Task 1 (component `apps/revit-mcp`, branch `degram/phase-1301`, local, not pushed): `d8f0f24` fix(1301-22): pyRevit side loads on IronPython 3.4; extension enabled by default; text/plain POST bodies (G-8..G-12) - 28 files, 147 insertions, 60 deletions
2. Task 2 (framework): `ae7909b` docs(1301-22): CLEAN-INSTALL pyRevit extension enable check

The framework gitlinks are not bumped and nothing was pushed: plan 23 does both once for the whole gap round.

## Review of the diff against G-8..G-12

- G-8: `extension.json` `builtin "False"`, `default_enabled "True"`.
- G-9: `structured_helper` moved from `degram_readonly.py` to `tools/__init__.py` (the only user is `tools` and the test); `degram_readonly` stays free of `async def`.
- G-10: `from .utils import` in 21 route modules.
- G-11: `views.py` takes `unquote` from `urllib.parse` with a 2.7 fallback.
- G-12: `main.json_body` for `RevitClient.post` and `DegramClient.post`; `utils.parse_request_data`, used by `documents._read_body` and `colors`.
- No write route and no new allowlist entry in the diff (T-1301-22-01); `parse_request_data` returns a dict or None (T-1301-22-02).

## Verification

- `uv run pytest -q` in `apps/revit-mcp`: 163 passed (no package install; existing lock).
- Fork `git status --untracked-files=no` after the commit: only the three line-ending-only files remain modified (see Deviations).
- `python tools/degram/workspace.py verify` reported "Submodule gitlink does not match the selected component HEAD" before any edit. This is the `apps/degram` pair (component HEAD `d0d69691` from plan 18 vs the framework gitlink), expected until plan 23 bumps the gitlink once for the gap round; this plan touched no `apps/degram` file. `revit-mcp` is not part of that pair check.
- Not run: live recheck on a 0.1.6 install (plan 16 Task 3); reported as unverified.

## Deviations from Plan

### Not done as written

**1. [Environment] Line-ending-only files not restored**
- **Plan said:** `git checkout -- revit_mcp/__init__.py revit_mcp/document.py revit_mcp/status.py`, then acceptance "status shows no tracked modification".
- **What happened:** the checkout was refused by the permission classifier (discarding working-tree changes). The three files were confirmed empty under `git diff --ignore-cr-at-eol --stat` and were simply not staged; the 28 real files were staged by explicit path.
- **Effect:** the fork working tree still lists those three files as modified (CRLF/LF only, no content change). Harmless to the build; the owner can run the checkout, or plan 23 can, if a clean fork tree is wanted before the push.

None other: no Rule 1-3 fixes were needed.

## Known Stubs

None.

## Threat Flags

None. T-1301-22-01 and T-1301-22-02 mitigations verified by diff review and the unchanged allowlist tests (green).

## Self-Check: PASSED

Commits `d8f0f24` (fork) and `ae7909b` (framework) exist; `docs/degram/CLEAN-INSTALL.md` contains "disabled = false" and "IronPython 3.4"; fork `extension.json` in HEAD has `"default_enabled": "True"`.
