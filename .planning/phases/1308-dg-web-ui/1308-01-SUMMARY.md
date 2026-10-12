---
phase: 1308-dg-web-ui
plan: 01
subsystem: repo-hygiene
status: complete
completed: 2026-10-12
requires: []
provides:
  - clean tracked baseline for every file Phase 1308 edits (D-49)
affects: [1308-05, 1308-07, 1308-10, 1308-13, 1308-15, 1308-16]
key-files:
  modified:
    - ui-v2/src/screens/ProjectsScreen.jsx
    - ui-v2/src/lib/auth.js
    - DG/src/DG.Grasshopper/Components/ValidatorComponent.cs
    - DG/src/DG.Core/Services/ValidStatusMapper.cs
    - DG/tests/DG.Tests/ValidStatusMapperTests.cs
    - data-service/tests/test_auth_store.py
  created:
    - ui-v2/tests/api-security.test.mjs
    - ui-v2/tests/auth-security.test.mjs
    - ui-v2/tests/projects-panel.browser.jsx
    - ui-v2/tests/run-panel.mjs
requirements-completed: [WEBUI-03, WEBUI-07, WEBUI-08, WEBUI-09]
---

# Phase 1308 Plan 01: Owner WIP settled before Phase 1308

**The owner's uncommitted work on the files 1308 edits is committed verbatim as its own commit `dd895d0`, by explicit path; the tracked baseline for those files is clean.**

## Owner decision (Task 1)
Owner chose **option A: commit as its own commit**, default path list, `RuleEvaluatorBuiltinBoundaryTests.cs` excluded.

## What was done (Task 2)
- Pre-settlement `git diff` of the six modified paths saved to the session scratchpad (385 lines).
- Before committing: `node --test ui-v2/tests/*.test.mjs` 231 pass / 0 fail; `pytest data-service/tests/test_auth_store.py` 61 passed.
- Staged exactly 10 paths (6 modified, 4 untracked ui-v2 tests); no `bin/`, `obj/`, `spec/` or other data-service WIP.
- Commit `dd895d0` "chore(1308-01): settle owner WIP before Phase 1308"; `git show --stat HEAD` lists only those 10 paths (592 insertions, 17 deletions).

## Verification
- `git status --porcelain` for ProjectsScreen.jsx, auth.js, ValidatorComponent.cs, test_auth_store.py: empty (CLEAN).
- Changed-line multiset of the saved pre-settlement diff equals that of `git show HEAD` for the six modified paths (DIFF-EQUAL): nothing lost, nothing rewritten.

## Deviations
None. A transient `.git/index.lock` from GitHub Desktop appeared once and cleared on its own; no lock was removed manually.
