---
phase: 1301-rabochiy-klient-i-bezopasnoe-chtenie
plan: 02
subsystem: component-environment
tags: [degram, npm-ci, pm-build-env, vitest, pytest, baseline, fonts]
requires: []
provides:
  - "apps/degram node_modules and .venv restored from upstream lockfiles (offline test capability)"
  - "local component branch degram/phase-1301 at gitlink 8b66a510"
  - "pre-change test baseline (vitest full; pytest hermes_cli partial, tui_gateway full)"
  - "cyrillic font subsets with SHA-256 for plan 13 (scratchpad only)"
affects: [1301-04, 1301-10, 1301-11, 1301-12, 1301-13, 1301-14]
tech-stack:
  added: []
  patterns: ["HERMES_PYTHON runner path when run-in-hermes-env cannot download uv"]
key-files:
  created:
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-ENV.md
    - .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-02-SUMMARY.md
  modified: []
key-decisions:
  - "Stable vitest baseline = the 44 failure lines that reproduce in two full runs; timing flakes are excluded from regression attribution"
  - "Use the runner's HERMES_PYTHON path instead of run-in-hermes-env, because the latter downloads uv, which is outside the authorization"
requirements-completed: []
requirements-partial: [DGCL-01]  # enabler only (test environment); not marked complete, the client requirement is delivered by later plans
duration: ~2h (execution resumed after interruption; most time spent in baseline runs)
completed: 2026-10-05
status: complete
---

# Phase 1301 Plan 02: Component environment and baseline Summary

Locked npm and Python dependencies of the DeGram fork are restored under owner authorization, a local `degram/phase-1301` branch exists at the gitlink commit, and a pre-change test baseline is recorded in `1301-ENV.md` (Desktop vitest stable set of 44 failure lines; `tests/tui_gateway` 2388 passed / 23 failed; `tests/hermes_cli` timed out at 15 min with partial counts).

## Authorization

Task 1 (checkpoint:decision) was resolved by the owner on 2026-10-04 and recorded verbatim:

- Selected option: **authorize-all** (npm ci, python -m pm.build_env, local branch degram/phase-1301 and local component commits from gitlink 8b66a510; no push, no hermes update, no Desktop launch/build, no write to %LOCALAPPDATA%\hermes).
- Item (d) fonts: **GRANTED** (npm pack of @fontsource geist-sans, geist-mono, oswald into the session scratchpad only; cyrillic 400/500 woff2 + LICENSE files only; no dependency added).
- Date: 2026-10-04.

## What was done

- `npm ci` (workspace lockfile) and `python -m pm.build_env --source . --out .venv --group dev --group test` in `apps/degram`: done earlier by the interrupted executor, verified on disk (`node_modules` 785 entries, `apps/desktop/node_modules`, `.venv` with pytest 9.1.1).
- Branch `degram/phase-1301` exists, HEAD = gitlink `8b66a510`; no component commit was made in this plan.
- Fonts fetched (3 tarballs, 5.3.0) into the session scratchpad; cyrillic 400/500 woff2 for geist-mono and oswald plus all three LICENSE files extracted; SHA-256 listed in `1301-ENV.md`.
- Baseline recorded (see `1301-ENV.md` section Baseline and the Deviations below).
- `python tools/degram/workspace.py verify` exits 0; `git -C apps/degram status --short` is empty.

## Baseline headline numbers

| Suite | Result |
|---|---|
| vitest `--project electron`, run 1 | 43 failed / 3207 passed / 70 skipped (plus 1 file that fails to load) |
| vitest `--project electron`, run 2 | 67 failed / 3183 passed / 70 skipped (24 extra timeouts: flaky) |
| pytest `tests/tui_gateway` | 2388 passed, 23 failed (12 files), 2 files with no test run; completed in about 13.5 min |
| pytest `tests/hermes_cli` | TIMED OUT after 15 min; at cut-off 82.1% visited, 10239 passed, 216 failed (counter includes retries) |
| pytest `tests/tools` | not captured (see ENV: irrelevant to Phase 1301; capture targeted in plans 10/11) |

## Deviations from Plan

### Owner-approved scope amendment (2026-10-05)

**1. [Owner amendment] Baseline narrowed**
- **Plan text:** `bash scripts/run_tests.sh tests/hermes_cli tests/tui_gateway tests/tools` plus the full vitest.
- **Change:** the owner narrowed the baseline. Reason: the full upstream Hermes pytest sets are Linux-oriented and take 45+ min on Windows (the first run was interrupted after 44 min inside tests/tools), and only the Desktop vitest baseline gates plan 04. Executed: (1) full `npx vitest run --project electron`; (2) pytest only on `tests/hermes_cli` and `tests/tui_gateway`, run separately, each with a hard 15-minute limit (`timeout 900`); (3) `tests/tools` not run, noted in 1301-ENV.md with the required sentence verbatim.
- **Outcome:** `tests/hermes_cli` hit the limit and is recorded as "TIMED OUT after 15 min" with partial counts; it was not retried or extended. `tests/tui_gateway` finished within the limit.

### Auto-fixed / handled issues

**2. [Rule 3 - Blocking] Test runner tried to download uv**
- **Found during:** first pytest invocation.
- **Issue:** `scripts/run_tests.sh` judged the environment stale and re-ran `run-in-hermes-env`, which tries to fetch a pinned `uv` from github.com (fails with a schannel revocation error here; a download is also outside the authorization).
- **Fix:** set `HERMES_PYTHON` to `apps/degram/.venv/Scripts/python.exe`, the runner's documented path for an interpreter that already has pytest. Runner isolation (per-file subprocess, env scrubbing) still applies.
- **Files modified:** none.

**3. [Rule 1/Scope - Test-environment noise] Vitest baseline is timing-sensitive**
- **Found during:** a second full vitest run (the first overlapped with pytest start-up).
- **Issue:** run 2 had 24 more timeout failures than run 1 on an otherwise idle machine.
- **Handling:** recorded both runs; the 44 failure lines of run 1 all reproduced in run 2 and form the stable baseline; the 24 extras are listed as flaky. No baseline failure was fixed (per plan).

**4. [Finding] @fontsource/geist-sans has no cyrillic subset**
- 5.3.0 ships only `latin` files (18). Only its LICENSE was extracted; Cyrillic for the Geist Sans role stays on the UI-SPEC Segoe UI fallback. Plan 13 must not expect a geist-sans cyrillic woff2.

**5. [Cleanup] Orphan processes and test junk**
- The 15-minute `timeout` left two orphaned pytest python processes; both were killed. Ignored test artifacts (`MagicMock/`, `.pytest_cache/`, `test_durations.json`) in `apps/degram` were removed; `git -C apps/degram status --short` is empty.

## Known Stubs

None (evidence-only plan; no source changed).

## Threat Flags

None. T-1301-02-SC: lockfile restore only, no new package, owner decision gate passed. T-1301-02-01: no Desktop launch, no `hermes update`; no command wrote to `%LOCALAPPDATA%\hermes` (only an existence listing).

## Commits

- Framework: evidence and summary commit (see git log, `docs(1301-02)`).
- Component: none (no commit inside `apps/degram`).

## Self-Check: PASSED

- 1301-ENV.md exists and contains `## Baseline`, the authorization, versions, branch, font SHA-256 values (all verified against the files on disk).
- `python tools/degram/workspace.py verify` exit 0; `git -C apps/degram status --short` empty.
