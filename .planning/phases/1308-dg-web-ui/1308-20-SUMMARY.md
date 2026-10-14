---
phase: 1308-dg-web-ui
plan: "20"
subsystem: rollout
tags: [d-47, d-49, auth-stores, cleanup, backup]
requirements-completed: []
key-files:
  modified:
    - .planning/phases/1308-dg-web-ui/1308-ROLLOUT.md
completed: 2026-10-14
status: complete
---

# Plan 1308-20: Live D-49 credential retirement and UAT account removal

**All 13 active connector credentials on the live stack are retired (`retired: "D-49"`), the UAT user `uat-pw-bd30ce@dg.local` and its project rows are gone from every store, behind a verified backup and an owner-run apply.**

## What was done

- **Backup (Task 1):** 19 `data-service/data/*.json` → `C:/dgbackup1308/20261013T223918Z/`, count and sha256 verified, `SHA256SUMS.txt` kept beside the copy.
- **Neo4j:** read-only count for `project = 'uat-pw-bd30ce'` → 0.
- **Dry run:** `dry-run-ok`, exit 0 — 13 credentials to retire, 11 already revoked, 1 user, 1 membership, 1 pairing, every other store 0.
- **Approval / apply (Tasks 2–3):** the owner ran stop → `compose run --rm --no-deps … --apply` → start from PowerShell: `applied`, exit 0, same counts.
- **Verification:** 24 credentials, 0 active, 13 `retired: "D-49"`; no store mentions the UAT user or project; 2 users remain; data-service back on image `c1e018ee…`, unauthenticated probe 401.
- **Owner actions (D-48)** recorded in 1308-ROLLOUT.md: grant for `asiyagerey94@gmail.com` on `degram-uat-c`, plugin rebuild and canvas re-wire per `docs/RELEASE-NOTES-v13.0.md`, add-in live check, RU visual pass.

## Deviations

- The auto-mode classifier refused the agent's `docker exec … d49_store_cleanup.py` (read-only dry run), so the owner ran both the dry run and the apply; the agent verified the result from the host bind mount (counts and field names only).
- Two more active credentials than at plan time (13 vs 11): issued after 2026-10-12, retired under the same rule.
- The owner did not reply with the literal "apply ok"; running the apply after reviewing the dry-run counts and asking about scope is recorded as the approval.
- Three stores (`auth-sessions`, `degram-grants`, `auth-delegated-tokens`) differ from the backup through normal service activity between backup and apply, not through the script.
- The post-apply dry run was run by the owner and confirmed `nothing-to-do` (UAT test 8).

## Limits

Neo4j, graphs, validation runs and all non-auth stores were not touched. The backup is outside the repository and not committed.
