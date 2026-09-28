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

Seeded per requirement; the planner refines to task IDs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1205-TBD | TBD | TBD | ALGN12-17 | T-1205-* | Every non-allowlisted route returns 401 without a principal | unit+integration | `pytest tests/test_route_inventory.py -x` | ❌ W0 | ⬜ pending |
| 1205-TBD | TBD | TBD | ALGN12-18 | T-1205-* | No `/neo4j/` or `/n8n/` nginx location; internal ports bind 127.0.0.1 | static | `pytest tests/test_static_proxy_boundary.py -x` | ❌ W0 | ⬜ pending |
| 1205-TBD | TBD | TBD | ALGN12-19 | T-1205-* | config.js and ui-v2/dist carry no credential keys or known defaults; multi-user refuses default secrets | unit | `pytest tests/test_config_js_no_secrets.py tests/test_default_secret_refusal.py -x` | ❌ W0 | ⬜ pending |
| 1205-TBD | TBD | TBD | ALGN12-20 | T-1205-* | Cross-project access (user and connector token) returns 403/404 on every project-scoped and id-only route | integration | `pytest tests/test_cross_project_matrix.py -x` | ❌ W0 | ⬜ pending |
| 1205-TBD | TBD | TBD | GATE12-05 | T-1205-* | Gate holds with `DG_DEPLOYMENT=multi-user` against rebuilt containers | live (human checkpoint) | `docker compose -f docker-compose.yml -f docker-compose.multi-user.yml up -d --build` then D-16 live checks | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/conftest.py` — authorized-client / connector-token / service-token fixtures (D-20)
- [ ] `data-service/tests/test_route_inventory.py` — D-14
- [ ] `data-service/tests/test_cross_project_matrix.py` — D-15 two-user/two-project fixture
- [ ] `data-service/tests/test_static_proxy_boundary.py` — D-16 static half
- [ ] `data-service/tests/test_config_js_no_secrets.py` — D-12
- [ ] `spec/SECURITY-BOUNDARY.md` — D-17 fenced allowlist block the D-14 test reads

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
