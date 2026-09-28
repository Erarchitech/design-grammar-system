---
phase: 1205
slug: security-and-tenancy-release-gate
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-28
---

# Phase 1205 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (data-service), xUnit via `dotnet test` (DG.Tests), `npm --prefix ui-v2 run build` (no JS test runner in ui-v2) |
| **Config file** | `data-service/tests/conftest.py` (no auth fixtures yet — Wave 0 adds them, D-20) |
| **Quick run command** | `MSYS_NO_PATHCONV=1 docker exec data-service pytest tests/test_route_inventory.py tests/test_cross_project_matrix.py -x` |
| **Full suite command** | `MSYS_NO_PATHCONV=1 docker exec data-service pytest` + `dotnet test .\DG\tests\DG.Tests\` + `npm --prefix ui-v2 run build` |
| **Estimated runtime** | ~180 seconds (data-service full suite) |

In-container pytest is authoritative: the `neo4j` hostname resolves only inside compose. Rebuild
the data-service image before trusting an in-container run (stale images mask code state).

---

## Sampling Rate

- **After every task commit:** the targeted new test file for that task (or `test_route_inventory.py`)
- **After every plan wave:** full in-container data-service pytest; `dotnet test` if any C# client changed; `npm --prefix ui-v2 run build` if any `ui-v2/src` file changed
- **Before `/gsd-verify-work`:** full suite green under both `local` and `multi-user` compose invocations (D-19)
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

Refined by the planner to real plan/task IDs (2026-09-28). `pytest` paths are relative to `data-service/` when run in-container (`MSYS_NO_PATHCONV=1 docker exec data-service pytest …`) and to the repo root on the host.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1205-01-T1 | 01 | 1 | ALGN12-19 | T-1205-01-01..03 | Known-default policy (digest for the committed n8n password); checker prints names/verdicts only | unit | `python -m pytest data-service/tests/test_secrets_policy.py tools/security/tests/test_check_env_file.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-01-T2 | 01 | 1 | ALGN12-19 | T-1205-01-04 | Owner creates `.env` before enforcement (no lockout) | human-action | `git check-ignore .env` | n/a | ⬜ pending |
| 1205-02-T1/T2 | 02 | 1 | ALGN12-17 | T-1205-02-01..07 | scrypt, hashed sessions, expiry boundaries, locked atomic store, invites, bootstrap | unit+concurrency | `python -m pytest data-service/tests/test_auth_store.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-03-T1/T2 | 03 | 1 | ALGN12-17 | T-1205-03-01..04 | GH publish clients send the dgc_ Bearer token; no token in .gh/messages | unit+build | `dotnet test .\DG\tests\DG.Tests\` and `dotnet build .\DG\DG.sln -c Release` | ❌ W0 | ⬜ pending |
| 1205-04-T1..T3 | 04 | 1 | ALGN12-19, ALGN12-20 | T-1205-04-01..04 | DE-01 token never in reports; rotation script fails closed; live checker treats SPA 200 as failure | unit | `python -m pytest tools/de01/tests tools/security/tests/test_check_live_boundary.py data-service/tests/test_rotate_llm_master_secret.py -x -q -k "not live"` | ❌ W0 | ⬜ pending |
| 1205-05-T1/T2 | 05 | 1 | ALGN12-18 | T-1205-05-01..04 | Workflows ignore caller URLs/credentials, send the service token, verify the relay token, write atomically per project | static | `python -m pytest data-service/tests/test_n8n_workflow_boundary.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-06-T1/T2 | 06 | 1 | ALGN12-17 | T-1205-06-01..03 | LLM Cypher proven project-scoped; foreign literals and key collisions detected | unit | `python -m pytest data-service/tests/test_cypher_project_scope.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-07-T1 | 07 | 2 | ALGN12-17 | T-1205-07-01..06 | Tracer: login cookie, 401 no principal, 403 cross-project, no credential fallback, CSRF | integration | `python -m pytest data-service/tests/test_auth_tracer.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-07-T2 | 07 | 2 | ALGN12-19 | T-1205-07-07..08 | Multi-user refuses default secrets; heartbeat omits the Neo4j bundle | integration | `python -m pytest data-service/tests/test_deployment_profile.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-08-T1/T2 | 08 | 2 | ALGN12-20 | T-1205-08-01..04 | Existing suites authenticate through real principals (no bypass) | unit+suite | `python -m pytest data-service/tests/test_authorized_fixtures.py -x -q` then full suite | ❌ W0 | ⬜ pending |
| 1205-09-T1/T2 | 09 | 2 | ALGN12-18, ALGN12-19 | T-1205-09-01..04 | Required secrets, 127.0.0.1 bindings, multi-user `!reset`, dockerignore | static | `python -m pytest data-service/tests/test_compose_boundary.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-10-T2 | 10 | 3 | ALGN12-17, ALGN12-20 | T-1205-10-01..08 | D-14: every route classified + dependency present + denial sweeps | integration | `python -m pytest data-service/tests/test_route_inventory.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-11-T1/T2 | 11 | 3 | ALGN12-18 | T-1205-11-01..04 | No Cypher executor/credential/n8n URL in ui-v2/src/lib | build+grep | `npm --prefix ui-v2 run build` | ✅ | ⬜ pending |
| 1205-12-T1/T2 | 12 | 4 | ALGN12-17, ALGN12-18 | T-1205-12-01..05 | Membership-scoped projects, invites, named parameterised graph endpoints | integration | `python -m pytest data-service/tests/test_project_routes.py data-service/tests/test_graph_routes.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-13-T1/T2 | 13 | 4 | ALGN12-17 | T-1205-13-01..03 | Server-backed login, invite-only onboarding, legacy hashes purged | build+grep | `npm --prefix ui-v2 run build` | ✅ | ⬜ pending |
| 1205-14-T1/T2 | 14 | 5 | ALGN12-17, ALGN12-18 | T-1205-14-01..05 | Relay owner-bound; /mcp and generate-cypher enforce project scope | integration | `python -m pytest data-service/tests/test_workflow_relay.py data-service/tests/test_mcp_project_scope.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-15-T1/T2 | 15 | 5 | ALGN12-18, ALGN12-19 | T-1205-15-01..05 | nginx/vite have no /neo4j or /n8n proxy; config.js and dist carry no secret | static | `python -m pytest data-service/tests/test_static_proxy_boundary.py data-service/tests/test_config_js_no_secrets.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-16-T2 | 16 | 6 | ALGN12-17..20, GATE12-05 | T-1205-16-01..02 | Spec blocks equal code, routes and compose (both directions) | static | `python -m pytest data-service/tests/test_security_boundary_spec.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-17-T1/T2 | 17 | 6 | ALGN12-20 | T-1205-17-01..03 | D-15 cross-project matrix incl. id-only and owner-bound executions, both profiles | integration | `python -m pytest data-service/tests/test_cross_project_matrix.py -x -q` | ❌ W0 | ⬜ pending |
| 1205-18-T1..T3 | 18 | 7 | ALGN12-19, ALGN12-18 | T-1205-18-01..04 | Rotation by owner; old defaults rejected; n8n published; local live checks | live (human checkpoint) | `python tools/security/check_live_boundary.py --profile local` | n/a | ⬜ pending |
| 1205-19-T1..T3 | 19 | 8 | GATE12-05 | T-1205-19-01..04 | D-14/D-15/D-16 hold with DG_DEPLOYMENT=multi-user against rebuilt containers | live (human checkpoint) | `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d --force-recreate` then in-container gate suites and `check_live_boundary.py --profile multi-user` | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/conftest.py` + `auth_fixtures.py` — authorized-client / connector-token / service-token fixtures (D-20) — plan 1205-08
- [ ] `data-service/tests/test_secrets_policy.py` + `test_deployment_profile.py` — D-11 known defaults and multi-user refusal — plans 1205-01, 1205-07
- [ ] `data-service/tests/test_route_inventory.py` — D-14 runtime inventory and sweeps — plan 1205-10
- [ ] `data-service/tests/test_security_boundary_spec.py` — D-14/D-17 spec drift — plan 1205-16
- [ ] `data-service/tests/test_cross_project_matrix.py` — D-15 two-user/two-project fixture — plan 1205-17
- [ ] `data-service/tests/test_static_proxy_boundary.py` + `test_compose_boundary.py` — D-16 static half — plans 1205-15, 1205-09
- [ ] `data-service/tests/test_config_js_no_secrets.py` — D-12 — plan 1205-15
- [ ] `spec/SECURITY-BOUNDARY.md` — D-17 fenced blocks the drift test reads — plan 1205-16

Framework install: none — pytest, xUnit and npm are already present.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live secret rotation of every committed secret | ALGN12-19 (D-13) | Owner-entered values must never pass through a brief, commit or log | Follow the rotation runbook in `spec/SECURITY-BOUNDARY.md`; confirm the stack starts and old values are rejected |
| Live direct-proxy check against rebuilt containers | ALGN12-18/20 (D-16) | Needs the running compose stack in `multi-user` | `/neo4j/` → 404, unauthenticated API → 401, Bolt unreachable from outside |
| n8n workflows published live without caller-supplied URLs | ALGN12-18 (D-08) | Live n8n runs the published version, not the imported draft | Import, publish, restart n8n; read `execution_data.workflowData` to confirm what ran |
| Grasshopper sends connector token on publish | ALGN12-17 (D-04) | Needs Rhino/Grasshopper; Phase 40 owns live Rhino UAT (GATE12-04) | Record as deferred to Phase 40 if not run; unit-test the C# header path |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
