---
phase: 1205-security-and-tenancy-release-gate
plan: "19"
subsystem: security
tags: [multi-user, release-gate, live-boundary, n8n, gate12-05]
status: complete
requires:
  - phase: 1205-18
provides:
  - "GATE12-05 judged in the multi-user profile against rebuilt containers (D-18)"
  - "Multi-user live boundary evidence: in-container gate suites, host checker, heartbeat"
  - "Owner GATE12-05 verdict recorded verbatim: gate-pass"
  - "Published n8n version (Verify Relay Token) confirmed on the most recent post-publish executions"
  - "Stack returned to the local profile with the heartbeat bundle back (D-19)"
affects: []
key-files:
  created:
    - .planning/phases/1205-security-and-tenancy-release-gate/live-evidence/multi-user-boundary-check.json
    - .planning/phases/1205-security-and-tenancy-release-gate/live-evidence/multi-user-gate-summary.md
  modified: []
decisions:
  - "Owner verdict gate-pass recorded verbatim; Task-1 findings kept as OPEN non-blocking follow-ups, not as owner-accepted"
  - "n8n execution check used the most recent post-publish rows because the owner supplied no run timestamps; the match to the owner's runs is presumed, not proven"
metrics:
  tasks: 3
  completed: 2026-09-29
---

# Phase 1205 Plan 19: Multi-User Release Gate Summary

GATE12-05 was judged with DG_DEPLOYMENT=multi-user against rebuilt containers: 1657 gate-suite tests pass in-container, the host live checker passes, the owner replied "gate-pass", the published n8n version with Verify Relay Token ran the latest ingest and query, and the stack is back in the local profile. No code, config or fixture was changed. Evidence is status-only.

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Multi-user bring-up, in-container gate suites, live boundary check | a1f7e39 (checkpoint state df1e1f2) |
| 2 | Owner multi-user smoke and GATE12-05 verdict | no commit (owner review) |
| 3 | n8n published-version check, restore local profile | this plan's final commit |

### Task 1 (summary of a1f7e39)
Profile printed from the container as `multi-user`; `require_principal` present; image ids equal 1205-18. Static gate suites (D-14/D-15/D-16): 1657 passed, 0 failed. `check_live_boundary.py --profile multi-user`: exit 0, passed, including the three port-refusal checks (7687, 7474, 5678). Heartbeat with the connector token: HTTP 200, `neo4j` value null (no bundle). Details in `live-evidence/multi-user-gate-summary.md`.

### Task 2 - Owner verdict
Verdict, verbatim: **"gate-pass"** (2026-09-29). The owner did not supply the timestamps of their ingest and query runs, so the plan's acceptance wording "timestamps of their ingest and query runs are recorded" is NOT met as written; the substitute is below. The owner did not comment on the two Task-1 findings.

### Task 3 - n8n version check and local restore
- n8n database (with -wal/-shm) copied to the session scratchpad; only node names, `Verify Relay Token` presence, start time and status were read; scratch copies deleted (0 remain).
- Most recent rows after the 1205-18 publish (~2026-09-29 19:15Z), not matchable to owner-supplied times:
  - Graph query ("DG Graph Query (MCP)"): execution 273, started 2026-09-29 20:09:47, webhook, success, `Verify Relay Token` present.
  - Rules ingest ("DG Rules -> Metagraph"): execution 274, started 2026-09-29 20:11:26, webhook, success, `Verify Relay Token` present.
  - Pre-publish executions (2026-09-19) lack the node, confirming the published version changed. Those two executions are presumed, not proven, to be the owner's runs.
- Local profile restored with `docker compose up -d --force-recreate` (base file only). data-service exited with code 3 at cold start again (Neo4j Bolt not ready); restarted once with `docker compose up -d data-service`.
- `printenv DG_DEPLOYMENT` -> `local`; heartbeat `neo4j bundle present: True`; all 15 containers Up.
- Token-shape grep over `live-evidence/`: 0 secret-shaped matches (the generic 40+ character pattern hits only pytest test names).

## Deviations from Plan

None in execution. Two acceptance wordings are not met literally and are recorded as findings, not fixed:
1. Task 1 acceptance "heartbeat response has no neo4j key": observed a `neo4j` key with a null value (D-07 no-bundle behaviour holds).
2. Task 2 acceptance "timestamps of the owner's runs are recorded": none supplied; most recent post-publish executions recorded instead.

## Open follow-ups (non-blocking, recorded under the owner's gate-pass; not accepted by the owner)
1. Five multi-user-only full-suite failures: `tests/test_connectors.py::TestHeartbeatBundle` (2) hard-code the local-profile bundle; `tests/test_designstate_capture.py` lifespan tests (3) fail only in the full run with the D-11 refusal on `LLM_MASTER_SECRET(too-short)` (pass 22/22 alone; suspected env leak from an earlier test, unverified). Also the literal full-suite command stops at the known collection error for `tests/recognition_eval/test_freeze_rule_ingest_prompts.py` (unmounted fixtures).
2. Multi-user heartbeat keeps a `neo4j` key with a null value versus "no neo4j key".
3. From 1205-18: DG.Tests E2E `DesignStateValidationFlowTests` (3) fail with 401 (C# E2E fixture needs a connector token); data-service cold-start race (exit code 3 before Neo4j Bolt is ready; no healthcheck/restart policy), seen again in both profile switches here.

## Requirements disposition
This plan's frontmatter lists GATE12-05, ALGN12-18, ALGN12-20; with the owner's gate-pass and the multi-user evidence above these are marked complete. ALGN12-17 and ALGN12-19 were built in earlier plans of this phase (17 and 19 were exercised by the 1205-18 rotation and live checks and by the in-container suites here); they are not in this plan's frontmatter and were not marked here, to be settled by phase verification (/gsd-verify-work).

## Self-Check
Files exist: multi-user-boundary-check.json, multi-user-gate-summary.md, this SUMMARY. Commits a1f7e39 and df1e1f2 exist in history. Live-evidence token-shape grep: 0.
