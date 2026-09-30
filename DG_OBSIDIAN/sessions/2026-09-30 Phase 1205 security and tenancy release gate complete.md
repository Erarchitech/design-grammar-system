---
tags: [session, v12.0, phase-1205, security]
date: 2026-09-30
---

# Session: 2026-09-28 → 2026-09-30 — Phase 1205 Security and Tenancy Release Gate complete

## Goal

Run `/gsd-autonomous phase 1205` end to end: discuss, plan, execute, review, verify. The aim is server-side authorization and fail-closed project boundaries. Unauthorized cross-project and direct-proxy access must fail closed, and secret handling must be deployment-safe (ALGN12-17..20, GATE12-05).

## What Was Done

- **Smart discuss.** 20 decisions (D-01..D-20) across 4 areas, all accepted, plus 8 on-disk corrections:
  - the browser held the Neo4j admin credentials and ran arbitrary Cypher through `/neo4j/`;
  - 62 of 65 data-service routes had no auth;
  - the heartbeat handed the Neo4j admin password to connectors;
  - secrets were literal in compose;
  - n8n webhooks accepted a caller-supplied `mcp_url`.
- **Planning.** Research, pattern map, 19 plans in 8 waves, and the plan checker passed. Claude GSD subagents were used rather than DSH, because the phase handles secrets.
- **Execution, 19/19 plans:**
  - `auth.py`: scrypt users, hashed session cookie, CSRF header, memberships, invites.
  - A deny-by-default `require_principal` over 82 classified routes, with connector (`dgc_`) and service-token principals.
  - The Grasshopper clients send tokens.
  - The browser moved to named endpoints; nginx `/neo4j` and `/n8n` now return 404; `config.js` holds no secrets.
  - Compose requires every secret via `${VAR:?}`, internal ports bind to 127.0.0.1, and a `docker-compose.multi-user.yml` override exists.
  - n8n workflows are guarded by the service token; the relay to n8n binds polling to its owner.
  - `spec/SECURITY-BOUNDARY.md` has 4 machine-checked blocks and a rotation runbook.
  - Route inventory: 588 tests. Cross-project matrix: 887 tests.
- **Live checkpoints:**
  - `.env` was merged from the running containers.
  - Automated rotation of Neo4j, Postgres, MinIO, `LLM_MASTER_SECRET` (keys re-encrypted), Speckle session, service token and admin password, with values never printed.
  - n8n published live.
  - Multi-user gate: the owner gave the verdict "gate-pass".
- **Code review.** 4 fix iterations plus a final deep review:
  - Iteration 1: 5 critical and 21 warning findings.
  - Iterations 2 and 3: the LLM-Cypher project-scope guard was bypassed repeatedly.
  - Iteration 4: replaced with the grammar allowlist `cypher_allowlist.py`, checked by a differential probe against a disposable two-tenant Neo4j (17/17, 0 leaks).
- **UAT with the owner.** 3 pass, 1 issue:
  - the evidence was enough;
  - both design trade-offs are kept;
  - the n8n password was not rotated (accepted as open);
  - the sign-out → other-user pass succeeded.
- **Owner request.** Self-registration was restored for the local profile only (D-05 amended).
- **Final results:**
  - In-container: 3923 passed plus 12 known environmental failures.
  - C#: 588/592 (the 4 known E2E failures).
  - Phase marked complete. v12.0 is 100% executed.

## Decisions Made

- [[knowledge/decisions/Self-registration is local-profile only, invite-only in multi-user|Self-registration is local-profile only]] (D-05 amendment).
- [[knowledge/decisions/LLM-written Cypher is guarded by a grammar allowlist, not a blocklist|LLM-written Cypher is guarded by a grammar allowlist]].
- Owner decisions:
  - Keep CR-05/D-07: in the local profile the heartbeat returns the Neo4j bundle.
  - Keep D-12: a server-wide Speckle read token goes to user principals.
  - Leave N8N_PASSWORD open.

## Issues Encountered

- [[knowledge/debugging/Blocklist checks over LLM-written Cypher were bypassed three times|The Cypher blocklist was bypassed three times]].
- The official Postgres image trusts TCP from 127.0.0.1 inside the container, so an "old password must fail" check has to run over the compose network.
- n8n 2.4.8 ignores `N8N_BASIC_AUTH_*`; the effective login is the owner account in the n8n UI.
- A pre-existing gitignored `.env` was invisible to `git status`. The plan 01 executor wrongly reported that it did not exist.
- `POST /auth/login` needs `X-DG-CSRF: 1`. The first rotation-script run failed on this; no state changed.
- data-service cold-start race: it exits with code 3 when Neo4j Bolt is not ready. There is no healthcheck or restart policy.

## Next Steps

- `/gsd-audit-milestone`, then `/gsd-complete-milestone v12.0`.
- Open follow-ups:
  - Rotate the n8n password (n8n UI plus `.env`).
  - 5 multi-user-only test failures.
  - The DG.Tests E2E fixture needs a connector token.
  - Heartbeat `neo4j: null` versus the key being absent.
  - Add a cold-start healthcheck.
- Commit the owner's `CLAUDE.md` diff. It carries the SECURITY-BOUNDARY pointer added this session, next to the owner's earlier uncommitted DSH section.

## Related Notes

- `.planning/phases/1205-security-and-tenancy-release-gate/` (CONTEXT, 19 PLAN/SUMMARY, REVIEW, REVIEW-FIX, VERIFICATION, UAT)
- `spec/SECURITY-BOUNDARY.md`
- [[sessions/2026-09-28 Phase 1204 execution complete — determinism and LLM reproducibility benchmark|Previous: Phase 1204]]
