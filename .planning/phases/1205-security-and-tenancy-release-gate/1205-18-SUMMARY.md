---
phase: 1205-security-and-tenancy-release-gate
plan: "18"
subsystem: security
tags: [secret-rotation, n8n, live-boundary, de-01, docker, stale-image-guard]
status: complete
requires:
  - phase: 1205-03
  - phase: 1205-04
  - phase: 1205-15
  - phase: 1205-16
  - phase: 1205-17
provides:
  - "Local stack rebuilt --no-cache and proven to hold the 1205 code"
  - "Every committed secret rotated (D-13); old Neo4j and Postgres public defaults rejected"
  - "Five hardened n8n workflows published live with the Verify Relay Token node (D-08)"
  - "Local live boundary check green (D-16 local half) and DE-01 legs reachable with the connector token (D-20)"
affects: [1205-19]
key-files:
  created:
    - .planning/phases/1205-security-and-tenancy-release-gate/live-evidence/local-boundary-check.json
    - .planning/phases/1205-security-and-tenancy-release-gate/live-evidence/local-live-summary.md
  modified: []
decisions:
  - "n8n workflows imported with the live workflow ids injected into temporary copies, not the repo files (4 of 5 repo files carry no id; a plain import would duplicate workflows on the same webhook paths)"
  - "Postgres old-default rejection is checked over the compose network, not via docker exec on localhost (pg_hba trusts 127.0.0.1 in the container)"
metrics:
  tasks: 3
  completed: 2026-09-29
---

# Phase 1205 Plan 18: Local Live Release Gate Summary

The rebuilt, secret-rotated local stack now runs the 1205 boundary live: n8n publishes the five hardened workflows, the local boundary checker passes, and DE-01 reaches all legs with the owner-minted connector token. All evidence is status-only.

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Preflight: green suites, --no-cache rebuild, stale-image guard | 37a3c55 (checkpoint state c7b4e55) |
| 2 | Owner rotation checkpoint | no commit (untracked secret files only) |
| 3 | Post-rotation live checks, n8n publish, evidence | fa414ac |

### Task 1 - Preflight
Host suites at baseline (data-service 2973 passed / 4 known failures / 25 known neo4j-hostname errors; de01+security 152 passed; ui-v2 build ok). `docker compose build --no-cache` of data-service, design-grammars, dg-reasoner; `require_principal` present in-container; all three container image ids match the fresh builds; config.js exposes only dataServiceUrl and speckleBaseUrl. In-container suite shows only the known baseline failures.

### Task 2 - Owner rotation checkpoint (resolved, automated at owner's choice)
The owner chose automated rotation. A status-only script run by the orchestrator followed `spec/SECURITY-BOUNDARY.md` section 9; values were generated locally and never printed, with backups in the gitignored `.secrets/`. Rotated and verified: NEO4J_PASSWORD, POSTGRES_PASSWORD, MINIO_ROOT_USER/PASSWORD, LLM_MASTER_SECRET (dry-run then real; stored keys decrypt under the new secret), SPECKLE_SESSION_SECRET, N8N_PASSWORD (.env), DG_SERVICE_TOKEN (new accepted, old rejected), DG_BOOTSTRAP_ADMIN_PASSWORD (new login ok, old refused). The DE-01 connector token was minted as admin for DG-1200-GOLDEN and saved to `.de01/connector-token`. `check_env_file.py` (no flag): all 17 keys ok, exit 0 (re-run by the executor).

### Task 3 - Post-rotation live checks
- Full `--force-recreate`; data-service exited once (started before Neo4j accepted Bolt) and was brought up after Neo4j was ready; all services running.
- n8n 2.4.8: five workflows imported in place, `publish:workflow` each, n8n restarted; exactly the five active; `Verify Relay Token` present in 5/5 by node-name check; `activeVersionId == versionId` for 5/5. Unauthenticated direct webhook calls are rejected by the node (`relay token rejected` in the n8n log). Relay round trip (admin login 200, POST /workflows/graph-query 202 with executionId, execution-result 200) proves n8n accepts the rotated service token via env.
- Old defaults rejected: Neo4j (exit 1, unauthorized); Speckle Postgres (password authentication failed, exit 2, checked over the compose network).
- `check_live_boundary.py --profile local`: exit 0, passed (10 pass + 3 info trusted-local port rows).
- `run_de01.py`: exit 0, legs data-service, dg-reasoner, csharp, replay all available, no 401, silent_disagreement_count 0.
- Token-shape grep over `live-evidence/`: 0 in every file.

## Deviations from Plan

**1. [Rule 1 - Bug in plan] Postgres old-default check invalid as written.** The literal `docker exec speckle-postgres psql postgresql://speckle:speckle@localhost/speckle` succeeds regardless of password (pg_hba trusts TCP from 127.0.0.1 inside the official image). Replaced with a check over the compose network from a separate container; it fails authentication as required. Recorded in `local-live-summary.md`.

**2. [Rule 3 - Blocking] n8n import would duplicate workflows.** Four of the five repo workflow files have no `id`, so `import:workflow` would create new workflows on already-occupied webhook paths (the instance already holds many archived duplicates). Temporary copies with the live ids injected were imported (updating in place); repo files untouched. Scratch exports containing workflow bodies were deleted from the scratchpad.

**3. [Rule 3 - Blocking] data-service raced Neo4j on full recreate.** Exited with code 3 (Bolt refused during Neo4j start). Restarted with `docker compose up -d data-service` once Neo4j was up. No code change. Consider a compose `depends_on` health condition as a follow-up if this recurs.

**4. Orchestrator deviation (checkpoint resolution):** the first rotation script run's admin step failed because POST /auth/login needs the `X-DG-CSRF: 1` header (script bug, no state changed); fixed and re-run.

**5. Auth gate resolution:** Task 2 was a human-action checkpoint; the owner elected script-driven rotation (values still never seen by Claude).

## Findings and follow-ups

- **DG.Tests E2E (Task 1):** `DesignStateValidationFlowTests` (3 tests: `HappyPath_StatePublishAndRetrieve`, `Filtering_StateAndRule`, `LegacyNoState_FlowStillWorks`) now fail with 401 from the enforcing live data-service because the fixture calls it without a connector token. Failure count is unchanged versus baseline (577/580 passing shape); the cause changed from Neo4j-down to auth-enforced. Follow-up: the C# E2E fixture should present a connector token.
- **Unauthenticated n8n webhook answers HTTP 200 with an empty body** (responseNode mode on a thrown error) rather than 401. The workflow does not execute and no executionId is issued, so the relay contract holds; external clients probing status codes will not see a 401.
- Host port 5678 (n8n) remains published in the local profile by design (trusted-local, D-07/D-09).

## Owner-only remainders (NOT done)

- Change the n8n owner-account password in the n8n UI (n8n 2.4.8 ignores `N8N_BASIC_AUTH_*`, so `N8N_PASSWORD` in `.env` is not the effective n8n login).
- Rotate the reused n8n password anywhere else it is used outside this repository.
- Optional runbook step 11: rotate Speckle API tokens (never committed) and revoke old connector credentials.
- Git history was not rewritten (per D-13); the previously committed values remain in history and are now dead.

## Threat model status

T-1205-18-01 mitigated (no values read or printed; token-shape grep 0). T-1205-18-02 mitigated (--no-cache rebuild, in-container symbol grep, image-id match). T-1205-18-03 mitigated (import + publish + restart, node-name check on active versions). T-1205-18-04 mitigated (old Neo4j and Postgres defaults rejected). T-1205-18-05 accepted (one transient data-service start race, recovered).

## Known Stubs

None.

## Requirements

ALGN12-18, ALGN12-19, ALGN12-20 are not marked complete by this plan: they span the multi-user profile half of D-16 and the plan 1205-19 release gate, and the owner-only remainders above are open.

## Self-Check: PASSED

- live-evidence/local-boundary-check.json and local-live-summary.md exist; commits 37a3c55 and fa414ac present.
