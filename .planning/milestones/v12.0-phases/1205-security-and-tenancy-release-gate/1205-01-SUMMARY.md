---
phase: 1205-security-and-tenancy-release-gate
plan: "01"
subsystem: security
tags: [secrets-management, env-config, dotenv, python, csprng]

# Dependency graph
requires: []
provides:
  - "data-service/secrets_policy.py — single in-code known-default secret policy (KNOWN_DEFAULT_LITERALS, KNOWN_DEFAULT_PREFIXES, KNOWN_DEFAULT_SHA256, MIN_LENGTHS, PENDING_ROTATION_KEYS, classify_secret, enforce_startup_secrets)"
  - ".env.example — committed placeholder-only secret inventory (17 keys)"
  - "tools/security/check_env_file.py — owner-run .env completeness/known-default checker, prints key+verdict only"
  - "Owner-created, gitignored .env holding the bootstrap admin identity, DG_SERVICE_TOKEN, and current live values for the ten pre-existing secrets"
affects: ["1205-07 (lifespan startup hook imports enforce_startup_secrets)", "1205-09 (compose wiring of new env vars)", "1205-16 (spec/SECURITY-BOUNDARY.md drift-test mirror of the known-default list)", "1205-18 (rotation of the ten PENDING_ROTATION_KEYS live values)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Known-default classification returns reason codes only (missing/known-default/too-short), never the value itself, in return values, exceptions, or log lines"
    - "PENDING_ROTATION_KEYS + --allow-pending-rotation lets a pre-existing live secret pass a fail-closed checker until its scheduled rotation plan runs, without pretending rotation already happened"

key-files:
  created:
    - .env.example
    - data-service/secrets_policy.py
    - data-service/tests/test_secrets_policy.py
    - tools/security/check_env_file.py
    - tools/security/tests/test_check_env_file.py
  modified:
    - tools/security/check_env_file.py (Rule-1 fix, continuation session)
    - tools/security/tests/test_check_env_file.py (regression tests, continuation session)

key-decisions:
  - "D-05/D-13 (executed, not decided here): owner-created .env merges a pre-existing gitignored .env (already held SPECKLE_*/LLM_MASTER_SECRET) with newly generated DG_SERVICE_TOKEN/DG_BOOTSTRAP_ADMIN_PASSWORD and values read from running containers via docker inspect — no value crossed into this conversation"
  - "Plan's PENDING_ROTATION_KEYS subset rule was under-specified for keys carrying both a MIN_LENGTHS entry and a live known-default value (LLM_MASTER_SECRET) — corrected to a non-empty subset of {known-default, too-short}, excluding missing"

patterns-established:
  - "Owner-run checker output is recorded in plan SUMMARYs as status-only lines (KEY: verdict), never as raw .env content"

requirements-completed: []  # ALGN12-19 spans 8 plans in this phase (04,07,09,11,15,16,18 also declare it) — NOT marked complete; see Decisions Made below.

coverage:
  - id: D1
    description: "Known-default secret policy module + .env.example + owner-run checker (Task 1)"
    requirement: "ALGN12-19"
    verification:
      - kind: unit
        ref: "data-service/tests/test_secrets_policy.py, tools/security/tests/test_check_env_file.py -- 35 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Owner-created gitignored .env with bootstrap admin identity, DG_SERVICE_TOKEN, and live values merged in (Task 2 checkpoint)"
    requirement: "ALGN12-19"
    verification:
      - kind: manual_procedural
        ref: "owner-run: python tools/security/check_env_file.py --allow-pending-rotation -- exit 0, every key ok or pending-rotation"
        status: pass
    human_judgment: true
    rationale: "Claude never opens .env; only the owner (via docker inspect and the checker's status-only output) can confirm the real values exist and classify correctly."
  - id: D3
    description: "Rule-1 fix: pending-rotation classification for a key that is simultaneously known-default and too-short"
    verification:
      - kind: unit
        ref: "tools/security/tests/test_check_env_file.py::test_pending_rotation_key_known_default_and_too_short_passes_with_flag (+2 companion regression tests) -- pass"
      - kind: manual_procedural
        ref: "python tools/security/check_env_file.py --allow-pending-rotation against the live .env -- exit 0"
        status: pass
    human_judgment: false

duration: ~20min (continuation session; Task 1 executed in a prior session)
completed: 2026-09-28
status: complete
---

# Phase 1205 Plan 01: Known-Default Secret Policy, .env.example, and Owner-Created .env Summary

**Single-source known-default secret policy (`data-service/secrets_policy.py`) backing a committed `.env.example` and an owner-run status-only checker, with the owner's gitignored `.env` now populated and passing `--allow-pending-rotation` end to end.**

## Performance

- **Tasks:** 2 (Task 1: auto, executed prior session, commit 42d679c; Task 2: checkpoint:human-action, resolved this session) + 1 continuation fix task (Rule-1 bug)
- **Files modified (this continuation session):** 2 (`tools/security/check_env_file.py`, `tools/security/tests/test_check_env_file.py`)
- **Files created (Task 1, prior session):** 5 (`.env.example`, `data-service/secrets_policy.py`, `data-service/tests/test_secrets_policy.py`, `tools/security/check_env_file.py`, `tools/security/tests/test_check_env_file.py`)

## Accomplishments

- `secrets_policy.classify_secret` / `enforce_startup_secrets` implemented per D-11 with reason-code-only output; 20 unit tests cover every behavior bullet plus boundary cases.
- `.env.example` commits a 17-key placeholder inventory (10 pre-existing + `DG_SERVICE_TOKEN`/`DG_BOOTSTRAP_ADMIN_USER`/`DG_BOOTSTRAP_ADMIN_PASSWORD`/`DG_DEPLOYMENT`/`DG_COOKIE_SECURE`/2 optional Speckle scoping keys), every placeholder classified `known-default` (fail-closed proven by test).
- Owner created the gitignored repo-root `.env` in their own terminal: merged a pre-existing `.env` (already holding `SPECKLE_WRITE_TOKEN`, `SPECKLE_READ_TOKEN`, `SPECKLE_PROJECT_ID`, `SPECKLE_BASE_MODEL_ID`, `LLM_MASTER_SECRET`) with values read from the running containers via `docker inspect` (`NEO4J_PASSWORD`, `N8N_USER`/`N8N_PASSWORD`, `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`, `SPECKLE_SESSION_SECRET`) plus freshly generated `DG_SERVICE_TOKEN` (48 random bytes) and `DG_BOOTSTRAP_ADMIN_PASSWORD` (18 random bytes). `DG_BOOTSTRAP_ADMIN_USER` reuses the stack's existing n8n basic-auth user; `DG_DEPLOYMENT=local` and `DG_COOKIE_SECURE=false` fixed. Backed up to gitignored `.secrets/env.backup-2026-09-28T20-57-41-823Z` before merge. No value was read, printed, or copied by Claude at any point.
- Fixed a Rule-1 bug in `check_env_file.classify()` that made `--allow-pending-rotation` unsatisfiable for `LLM_MASTER_SECRET` (the one pending-rotation key with both a live known-default value and a `MIN_LENGTHS` entry) — see Deviations below.
- Live owner `.env` now passes: `python tools/security/check_env_file.py --allow-pending-rotation` exits 0 with every key `ok` or `pending-rotation`.

## Task Commits

Each task committed atomically:

1. **Task 1: Known-default secret policy, .env.example, and the owner-run .env checker** — `42d679c` (feat) — prior session
2. **Task 2: Owner creates the gitignored .env** — checkpoint resolved this session; no commit (untracked, gitignored file, never touched by Claude)
3. **Rule-1 fix: pending-rotation classification bug** — `751264c` (fix)

**Plan metadata:** (this commit)

## Files Created/Modified

- `.env.example` - committed 17-key placeholder inventory (Task 1, prior session)
- `data-service/secrets_policy.py` - known-default constants + `classify_secret`/`enforce_startup_secrets` (Task 1, prior session)
- `data-service/tests/test_secrets_policy.py` - 20 unit tests (Task 1, prior session)
- `tools/security/check_env_file.py` - owner-run checker CLI; Rule-1 fix to `classify()`'s pending-rotation subset logic (this session)
- `tools/security/tests/test_check_env_file.py` - checker tests; 3 new regression tests for the Rule-1 fix (this session)
- `.env` - owner-created, untracked, gitignored; not read, opened, or modified by Claude (Task 2)

## Checkpoint Resolution (Task 2)

The owner instructed Claude to populate `.env` from the running stack's live values; this was carried out by an orchestrator step that never printed values to this conversation.

- A pre-existing, gitignored repo-root `.env` **already existed** before this plan ran (a prior executor's "does not exist" claim was incorrect — gitignored files never appear in `git status`). It held `SPECKLE_WRITE_TOKEN`, `SPECKLE_READ_TOKEN`, `SPECKLE_PROJECT_ID`, `SPECKLE_BASE_MODEL_ID`, and `LLM_MASTER_SECRET`; `docker-compose.yml` already loads it. It was backed up to `.secrets/env.backup-2026-09-28T20-57-41-823Z` (gitignored) and merged: existing lines kept verbatim, only missing keys appended.
- Added from the running containers (`docker inspect`): `NEO4J_PASSWORD` (neo4j's `NEO4J_AUTH`), `N8N_USER`/`N8N_PASSWORD` (n8n basic auth), `POSTGRES_PASSWORD` (speckle-postgres), `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` (speckle-server's `S3_ACCESS_KEY`/`S3_SECRET_KEY`), `SPECKLE_SESSION_SECRET` (speckle-server's `SESSION_SECRET`).
- Generated fresh: `DG_SERVICE_TOKEN` (48 random bytes, 64 chars), `DG_BOOTSTRAP_ADMIN_PASSWORD` (18 random bytes, 24 chars). `DG_BOOTSTRAP_ADMIN_USER` reuses the stack's existing admin identity (the n8n basic-auth user). Fixed: `DG_DEPLOYMENT=local`, `DG_COOKIE_SECURE=false`.
- Checker output after the merge (`python tools/security/check_env_file.py --allow-pending-rotation`), **before** the Rule-1 fix: exit 1 — every key `ok` or `pending-rotation` except `LLM_MASTER_SECRET: known-default` (the bug this continuation session fixed). **After** the fix: exit 0, every key `ok` or `pending-rotation`, including `LLM_MASTER_SECRET: pending-rotation`.
- Step 6 (change the reused n8n password anywhere else it is reused, outside this repo) is the owner's out-of-repo action. **Handed to the owner, not independently verifiable here** — recorded as acknowledged, not as done.

## Decisions Made

- **ALGN12-19 requirement checkbox intentionally NOT marked complete.** `ALGN12-19` is declared in this plan's frontmatter but also in 1205-04, -07, -09, -11, -15, -16, and -18 — it spans the whole phase (hardening, rotation, and browser-exclusion of secrets). Running `requirements mark-complete ALGN12-19` now would flip the single global checkbox in REQUIREMENTS.md to done after only the first of 8 contributing plans, which is a false-positive completion claim. Deferred to whichever of those later plans closes the requirement's last open sub-goal.
- Rotation of the ten `PENDING_ROTATION_KEYS` live values is deliberately deferred to plan 1205-18 (D-13) — this plan only copies current live values so the running stack keeps working.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `check_env_file.classify()` made `--allow-pending-rotation` unsatisfiable for `LLM_MASTER_SECRET`**
- **Found during:** Task 2 checkpoint resolution (owner ran the checker against the real, merged `.env`)
- **Issue:** `classify()` granted `pending-rotation` status only when `reasons == ["known-default"]`. `LLM_MASTER_SECRET` is the only `PENDING_ROTATION_KEYS` member with a `MIN_LENGTHS` entry (32), and its pre-existing live value is shorter than that, so its reasons were `["known-default", "too-short"]` — a strict-equality check against `["known-default"]` can never match a two-element list, so `--allow-pending-rotation` could never pass on the live stack for this key, contradicting the flag's documented purpose (the comment above `PENDING_ROTATION_KEYS` in `secrets_policy.py`).
- **Fix:** Under `--allow-pending-rotation`, a key in `PENDING_ROTATION_KEYS` whose reasons are a non-empty subset of `{"known-default", "too-short"}` (i.e. not `"missing"`) now reports `pending-rotation`. `secrets_policy.enforce_startup_secrets` (the multi-user startup refusal) was left untouched and stays strict — this fix is scoped to the owner-run checker's flag semantics only.
- **Files modified:** `tools/security/check_env_file.py` (docstring + `classify()`), `tools/security/tests/test_check_env_file.py` (3 new regression tests: known-default+too-short pending key passes only with the flag; a non-pending too-short key never passes via the flag; a missing pending key never passes via the flag).
- **Verification:** `python -m pytest data-service/tests/test_secrets_policy.py tools/security/tests/test_check_env_file.py -x -q` → 35 passed. `python tools/security/check_env_file.py --allow-pending-rotation` against the live owner `.env` → exit 0, every key `ok`/`pending-rotation`.
- **Committed in:** `751264c`

### Documentation-only deviation (noted by the prior executor, recorded here)

- **Plan acceptance criterion regex mismatch:** `grep -Ec "^[A-Z_]+=" .env.example` returns 14, not "at least 17" as the plan's acceptance criteria stated — the plan's regex has no digit class, so key names containing digits (`NEO4J_PASSWORD`, `N8N_USER`, `N8N_PASSWORD`) don't match `^[A-Z_]+=`. The corrected regex `^[A-Z0-9_]+=` returns 17, matching the file's actual key count and the plan's intent. No file change required — the file is correct; the acceptance command as literally written undercounts.

---

**Total deviations:** 1 auto-fixed (1 bug), 1 documentation-only note (no code change).
**Impact on plan:** The bug fix was necessary for the checker's own stated contract to hold on the real stack; it does not touch `enforce_startup_secrets`'s strict multi-user refusal. No scope creep.

## Issues Encountered

None beyond the Rule-1 bug documented above.

## User Setup Required

None — Task 2 (owner-created `.env`) was the user setup, and it is complete: `git check-ignore .env` confirms the file stays gitignored, and the owner-run checker exits 0.

## Next Phase Readiness

- `secrets_policy.enforce_startup_secrets` is ready for 1205-07 to wire into the FastAPI lifespan hook.
- `.env.example`'s new env vars (`DG_SERVICE_TOKEN`, `DG_BOOTSTRAP_ADMIN_USER`, `DG_BOOTSTRAP_ADMIN_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `POSTGRES_PASSWORD`, `DG_DEPLOYMENT`, `DG_COOKIE_SECURE`) are ready for 1205-09 to wire into `docker-compose.yml`.
- The owner's `.env` exists with a working bootstrap admin identity and service token before any of 1205-07/1205-10's enforcement lands — the lockout risk named in D-05/orchestrator fact 5 is closed.
- Rotation of the ten `PENDING_ROTATION_KEYS` live values (including the compromised committed n8n password, step 6) remains open for 1205-18, as designed.

---
*Phase: 1205-security-and-tenancy-release-gate*
*Completed: 2026-09-28*

## Self-Check: PASSED

All created files found on disk; commits `42d679c` and `751264c` found in git log.
