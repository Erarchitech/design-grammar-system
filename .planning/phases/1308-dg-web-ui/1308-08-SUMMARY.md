---
phase: 1308-dg-web-ui
plan: "08"
subsystem: ops
tags: [maintenance-script, dry-run, connector-credentials, uat-cleanup, pytest, tdd]

requires:
  - phase: 1308-dg-web-ui
    provides: "connector_session store file (plan 03) and the dgk_ sign-in model that replaces dgc_ credentials"
provides:
  - "data-service/d49_store_cleanup.py: dry-run-first one-off script that retires every dgc_ credential and removes the UAT account and project from every JSON store"
  - "Status words dry-run-ok / applied / nothing-to-do / project-has-other-members / store-unreadable with exit codes 0/0/0/2/3"
affects: [1308-19, 1308-20]

tech-stack:
  added: []
  patterns:
    - "Plan every store first under auth._STORE_LOCK, abort before any write, write only stores whose content changes through the owning module's save helper"

key-files:
  created:
    - data-service/d49_store_cleanup.py
    - data-service/tests/test_d49_store_cleanup.py
  modified: []

key-decisions:
  - "Targets are module constants with no CLI override; the only flag is --apply"
  - "Rows match on normalized username OR project == uat-pw-bd30ce; invites also match created_by; the users store matches username only"
  - "nothing-to-do is reported in dry-run too when no active credential and no UAT row exists; credentials_already_revoked is informational and never counts as work"
  - "Writes run credentials first and the user row last; stores are written one at a time (each atomically), and an interrupted run is finished by re-running --apply (every step is idempotent)"
  - "Refusal (exit 2) is decided from the memberships read before the removal filter, so a non-UAT member of the UAT project always blocks"

patterns-established:
  - "Ops script docstring carries the exact 1308-20 invocation (dry-run via docker exec, apply with the service stopped) and the concurrency note"

requirements-completed: []

coverage:
  - id: D1
    description: "Credential retirement: only active credentials get revoked/revoked_at/retired D-49; already-revoked stay byte-identical; dry-run default; idempotent"
    requirement: "WEBUI-11"
    verification:
      - kind: unit
        ref: "data-service/tests/test_d49_store_cleanup.py::TestCredentialRetirement"
        status: pass
    human_judgment: false
  - id: D2
    description: "UAT user, memberships, sessions, invites, delegated tokens, connector sessions, connector-access, DeGram grants/requests, pairing, company and policy rows removed; other rows unchanged and in order"
    requirement: "WEBUI-11"
    verification:
      - kind: unit
        ref: "data-service/tests/test_d49_store_cleanup.py::TestUatAccountRemoval"
        status: pass
    human_judgment: false
  - id: D3
    description: "Refusals and hygiene: exit 2 on another project member, exit 3 on any malformed store (no writes), missing stores stay missing, stdout has counts and status words only, no graph-database import"
    requirement: "WEBUI-11"
    verification:
      - kind: unit
        ref: "data-service/tests/test_d49_store_cleanup.py::TestRefusals, TestOutputHygiene, TestCommandLine"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-12
status: complete
---

# Phase 1308 Plan 08: D-49 Store Cleanup Script Summary

**`d49_store_cleanup.py`: a dry-run-by-default, idempotent, lock-holding script that retires all `dgc_` credentials and removes the UAT account and project from 13 store files, with hard-coded targets and counts-only output.**

## Accomplishments

- `plan_changes` reads every store (credentials, connector sessions, delegated tokens, auth sessions, DeGram grants and requests, pairings, connector-access grants and requests, DeGram policy, project companies, invites, memberships, users) under `auth._STORE_LOCK` plus the credential lock, and computes counts and writers without writing.
- `run` returns `(exit, status, counts)`: exit 3 `store-unreadable` for any malformed store, exit 2 `project-has-other-members` when a non-UAT user is a member of `uat-pw-bd30ce`, `nothing-to-do` when no write is needed, `dry-run-ok` without `--apply`, `applied` otherwise. Nothing is written on exit 2 or 3.
- Active credentials get `revoked: true`, `revoked_at` (ISO-8601 UTC) and `retired: "D-49"`; already-revoked rows stay byte-identical.
- Each rewritten store goes through its own module's save helper (atomic replace); a store file that does not exist is treated as empty and is never created; unchanged stores are not rewritten.
- The module docstring carries the 1308-20 invocation (dry-run via `docker exec`, apply with `data-service` stopped), the status/exit table and the concurrency note.

## Task Commits

1. Task 1 RED: `4cb6de1` (test) - failing credential retirement and CLI tests
2. Task 1 GREEN: `b94c158` (feat) - credential retirement, `run`/`main`, `--apply`
3. Task 2 RED: `48d235c` (test) - failing UAT removal, refusal and hygiene tests
4. Task 2 GREEN: `b35391d` (feat) - removal across every store, refusals

## Verification

- `python -m pytest data-service/tests/test_d49_store_cleanup.py -q` -> 53 passed (host run; every store redirected to `tmp_path`).
- `python data-service/d49_store_cleanup.py --help` lists only `-h` and `--apply`.
- `grep -c neo4j data-service/d49_store_cleanup.py` -> 0.
- `grep -n` finds exactly one line each for `UAT_USERNAME = "uat-pw-bd30ce@dg.local"` and `UAT_PROJECT = "uat-pw-bd30ce"`.
- The script was NOT run against `data-service/data/*` or any live volume (plan 1308-20 does the dry-run there).
- Not verified: behaviour inside the container image (Docker not authorized in this plan).

## Deviations from Plan

None - plan executed as written.

Notes on interpretation: the plan names the UAT user's "memberships" without restricting the project, so memberships of the UAT user in any project are removed; the script does not check whether that leaves another project without an owner (no such case is expected for a throwaway UAT account; the 1308-20 dry-run counts show it).

## Known Stubs

None.

## Threat Flags

None. The script adds no network surface; it reads and rewrites local JSON stores. T-1308-08-01..05 are mitigated as planned (fixed targets, plan-then-write, lock plus stop-the-service note, counts-only stdout test, `retired`/`revoked_at` marker).

## Issues Encountered

None.

## Next Phase Readiness

1308-19 ships `d49_store_cleanup.py` in the data-service image; 1308-20 runs the dry-run, takes the backup and runs `--apply` behind `checkpoint:human-verify`. WEBUI-11 is only partly addressed here (the cleanup tool); the requirement is not marked complete because the live rollout is plans 19/20.

## Self-Check: PASSED

- FOUND: data-service/d49_store_cleanup.py, data-service/tests/test_d49_store_cleanup.py
- FOUND commits: 4cb6de1, b94c158, 48d235c, b35391d
