---
phase: 1301
slug: rabochiy-klient-i-bezopasnoe-chtenie
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-04
---

# Phase 1301 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 1301-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.10 (Desktop, projects electron/ui); pytest (agent via `scripts/run_tests.sh`, data-service host tier, revit-mcp via uv); node:test + headless Chrome (ui-v2); xUnit (DG); unittest (tools/degram) |
| **Config file** | `apps/degram/apps/desktop/vitest.config.ts`, `apps/degram/pyproject.toml`, `data-service/tests/conftest.py`, `apps/revit-mcp/pyproject.toml` — Desktop/agent/revit-mcp environments need the authorized installs of plans 02/03 |
| **Quick run command** | the `<automated>` command of each task (table below) |
| **Full suite command** | `python -m pytest data-service/tests -q` · `node --test ui-v2/tests/*.test.mjs` · `npm --prefix ui-v2 run build` · `npx vitest run` (apps/degram/apps/desktop) · `bash scripts/run_tests.sh` (apps/degram) · `uv run pytest -q` (apps/revit-mcp) · `dotnet test .\DG\tests\DG.Tests\` · `python -m unittest discover -s tools/degram/tests -v` · `python tools/degram/workspace.py verify` |
| **Estimated runtime** | quick ≤ 60 s per task; full suite ~10 min |

---

## Sampling Rate

- **After every task commit:** run the task quick command
- **After every plan wave:** run the full suite of every area touched in that wave + `workspace.py verify`
- **Before `/gsd-verify-work`:** full suite green and plan 16 live UAT recorded
- **Max feedback latency:** 60 seconds per task command

Known baselines (not regressions): data-service host-tier environment failures, 4 DG.Tests Neo4j E2E tests when Neo4j is down, Desktop/agent baseline recorded by plan 02 in 1301-ENV.md.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------|-------------------|-------------|--------|
| 1301-02-01 | 02 | 1 | DGCL-01 | T-1301-02-SC | checkpoint decision | `grep -c "## Authorization" .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-02-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 1301-02-02 | 02 | 1 | DGCL-01 | T-1301-02-01 | check | `python tools/degram/workspace.py verify` | ❌ W0 | ⬜ pending |
| 1301-03-01 | 03 | 1 | DGCL-04 | T-1301-03-01 | checkpoint decision | `grep -c "## Authorization" .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-03-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 1301-03-02 | 03 | 1 | DGCL-04 | T-1301-03-02 | unit/integration | `python -m unittest discover -s tools/degram/tests -v` | ❌ W0 | ⬜ pending |
| 1301-04-01 | 04 | 2 | DGCL-01 | T-1301-04-01 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project electron electron/degram/isolation.test.ts electron/product-identity.test.ts electron/data-paths.test.ts electron/singleton-lock.test.ts` | ❌ W0 | ⬜ pending |
| 1301-04-02 | 04 | 2 | DGCL-01 | T-1301-04-02 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project electron scripts/degram-build.test.mjs scripts/write-build-stamp.test.mjs electron/updater/updater.test.ts` | ❌ W0 | ⬜ pending |
| 1301-05-01 | 05 | 1 | DGCL-02, DGCL-05 | T-1301-05-01 | unit/integration | `python -m pytest data-service/tests/test_company_scope.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` | ❌ W0 | ⬜ pending |
| 1301-05-02 | 05 | 1 | DGCL-02, DGCL-05 | T-1301-05-02 | unit/integration | `python -m pytest data-service/tests/test_delegated_token.py data-service/tests/test_auth_tracer.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py data-service/tests/test_cross_project_matrix.py -q` | ❌ W0 | ⬜ pending |
| 1301-06-01 | 06 | 1 | DGCL-04, DGCL-06 | T-1301-06-01 | unit/integration | `dotnet test .\DG\tests\DG.Tests\ --filter "FullyQualifiedName~CanvasBridge\|FullyQualifiedName~CanvasDocumentIdentity"` | ❌ W0 | ⬜ pending |
| 1301-06-02 | 06 | 1 | DGCL-04, DGCL-06 | T-1301-06-02 | unit/integration | `dotnet test .\DG\tests\DG.Tests\ --filter "FullyQualifiedName~CanvasBridge\|FullyQualifiedName~CanvasDocumentIdentity"` | ❌ W0 | ⬜ pending |
| 1301-07-01 | 07 | 2 | DGCL-04, DGCL-06 | T-1301-07-01 | unit/integration | `cd apps/revit-mcp && uv run pytest tests/test_degram_readonly.py tests/test_offline.py -q` | ❌ W0 | ⬜ pending |
| 1301-07-02 | 07 | 2 | DGCL-04, DGCL-06 | T-1301-07-02 | unit/integration | `cd apps/revit-mcp && uv run pytest tests/test_degram_documents.py tests/test_degram_readonly.py tests/test_offline.py -q` | ❌ W0 | ⬜ pending |
| 1301-08-01 | 08 | 2 | DGCL-02, DGCL-05, DGCL-06, DGCL-07 | T-1301-08-01 | unit/integration | `python -m pytest data-service/tests/test_degram_relay.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` | ❌ W0 | ⬜ pending |
| 1301-08-02 | 08 | 2 | DGCL-02, DGCL-05, DGCL-06, DGCL-07 | T-1301-08-02 | unit/integration | `python -m pytest data-service/tests/test_degram_policy.py data-service/tests/test_degram_relay.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` | ❌ W0 | ⬜ pending |
| 1301-08-03 | 08 | 2 | DGCL-02, DGCL-05, DGCL-06, DGCL-07 | T-1301-08-03 | unit/integration | `python -m pytest data-service/tests/test_degram_relay.py data-service/tests/test_static_proxy_boundary.py tools/de01/tests/test_reproducibility_scope_drift.py -q` | ❌ W0 | ⬜ pending |
| 1301-09-01 | 09 | 3 | DGCL-03, DGCL-05 | T-1301-09-01 | unit/integration | `python -m pytest data-service/tests/test_speckle_proxy.py data-service/tests/test_route_inventory.py data-service/tests/test_security_boundary_spec.py -q` | ❌ W0 | ⬜ pending |
| 1301-09-02 | 09 | 3 | DGCL-03, DGCL-05 | T-1301-09-02 | unit/integration | `node --test ui-v2/tests/speckle-proxy.test.mjs ui-v2/tests/api-security.test.mjs ui-v2/tests/auth-security.test.mjs && npm --prefix ui-v2 run build` | ❌ W0 | ⬜ pending |
| 1301-10-01 | 10 | 3 | DGCL-02, DGCL-05, DGCL-06 | T-1301-10-01 | unit/integration | `cd apps/degram && bash scripts/run_tests.sh tests/degram/test_credentials_provider.py` | ❌ W0 | ⬜ pending |
| 1301-10-02 | 10 | 3 | DGCL-02, DGCL-05, DGCL-06 | T-1301-10-02 | unit/integration | `cd apps/degram && bash scripts/run_tests.sh tests/degram/test_lockdown.py` | ❌ W0 | ⬜ pending |
| 1301-10-03 | 10 | 3 | DGCL-02, DGCL-05, DGCL-06 | T-1301-10-03 | unit/integration | `cd apps/degram && bash scripts/run_tests.sh tests/degram/test_profiles.py` | ❌ W0 | ⬜ pending |
| 1301-11-01 | 11 | 4 | DGCL-02, DGCL-04, DGCL-06, DGCL-07 | T-1301-11-01 | unit/integration | `cd apps/degram && bash scripts/run_tests.sh tests/degram/test_gh_bridge.py tests/degram/test_context_composer.py` | ❌ W0 | ⬜ pending |
| 1301-11-02 | 11 | 4 | DGCL-02, DGCL-04, DGCL-06, DGCL-07 | T-1301-11-02 | unit/integration | `cd apps/degram && bash scripts/run_tests.sh tests/degram/test_revit_bridge.py tests/degram/test_lockdown.py` | ❌ W0 | ⬜ pending |
| 1301-11-03 | 11 | 4 | DGCL-02, DGCL-04, DGCL-06, DGCL-07 | T-1301-11-03 | unit/integration | `cd apps/degram && bash scripts/run_tests.sh tests/degram` | ❌ W0 | ⬜ pending |
| 1301-12-01 | 12 | 4 | DGCL-01, DGCL-02, DGCL-03, DGCL-05, DGCL-06 | T-1301-12-01 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project electron electron/degram/dg-session.test.ts electron/degram/scope.test.ts` | ❌ W0 | ⬜ pending |
| 1301-12-02 | 12 | 4 | DGCL-01, DGCL-02, DGCL-03, DGCL-05, DGCL-06 | T-1301-12-02 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project electron electron/degram/dg-view.test.ts electron/window-open-policy.test.ts` | ❌ W0 | ⬜ pending |
| 1301-12-03 | 12 | 4 | DGCL-01, DGCL-02, DGCL-03, DGCL-05, DGCL-06 | T-1301-12-03 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project electron electron/degram` | ❌ W0 | ⬜ pending |
| 1301-13-01 | 13 | 5 | DGCL-01, DGCL-02, DGCL-03 | T-1301-13-01 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project ui src/degram/shell.test.tsx` | ❌ W0 | ⬜ pending |
| 1301-13-02 | 13 | 5 | DGCL-01, DGCL-02, DGCL-03 | T-1301-13-02 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project ui src/degram` | ❌ W0 | ⬜ pending |
| 1301-14-01 | 14 | 6 | DGCL-04, DGCL-06, DGCL-07, DGCL-02 | T-1301-14-01 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project ui src/degram/chat.test.tsx` | ❌ W0 | ⬜ pending |
| 1301-14-02 | 14 | 6 | DGCL-04, DGCL-06, DGCL-07, DGCL-02 | T-1301-14-02 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project ui src/degram` | ❌ W0 | ⬜ pending |
| 1301-15-01 | 15 | 7 | DGCL-01, DGCL-04 | T-1301-15-01 | checkpoint decision | `grep -c "## Authorization" .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-15-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 1301-15-02 | 15 | 7 | DGCL-01, DGCL-04 | T-1301-15-02 | unit/integration | `cd apps/degram/apps/desktop && npx vitest run --project electron scripts/degram-build.test.mjs electron/degram/isolation.test.ts` | ❌ W0 | ⬜ pending |
| 1301-15-03 | 15 | 7 | DGCL-01, DGCL-04 | T-1301-15-03 | check | `python tools/degram/workspace.py verify` | ❌ W0 | ⬜ pending |
| 1301-16-01 | 16 | 8 | DGCL-01, DGCL-02, DGCL-03, DGCL-04, DGCL-05, DGCL-06, DGCL-07 | T-1301-16-01 | checkpoint decision | `grep -c "## Authorization" .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-16-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 1301-16-02 | 16 | 8 | DGCL-01, DGCL-02, DGCL-03, DGCL-04, DGCL-05, DGCL-06, DGCL-07 | T-1301-16-02 | unit/integration | `python -m pytest tools/degram/tests/test_relay_probe.py -q` | ❌ W0 | ⬜ pending |
| 1301-16-03 | 16 | 8 | DGCL-01, DGCL-02, DGCL-03, DGCL-04, DGCL-05, DGCL-06, DGCL-07 | T-1301-16-03 | checkpoint human-verify | `grep -c "DGCL-07" .planning/phases/1301-rabochiy-klient-i-bezopasnoe-chtenie/1301-UAT.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Owner-authorized `npm ci` + `pm.build_env` in apps/degram (plan 02) — Desktop vitest and agent pytest
- [ ] Owner-authorized fork + submodule + `uv sync` for apps/revit-mcp (plan 03) — revit-mcp pytest
- [ ] New test files are created by their own tasks first (TDD): `electron/degram/*.test.ts`, `scripts/degram-build.test.mjs`, `data-service/tests/test_{company_scope,delegated_token,degram_relay,degram_policy,speckle_proxy}.py`, `DG.Tests/CanvasDocumentIdentityTests.cs`, `apps/revit-mcp/tests/test_degram_{readonly,documents}.py`, `apps/degram/tests/degram/*.py`, `src/degram/*.test.tsx`, `ui-v2/tests/speckle-proxy.test.mjs`, `tools/degram/tests/test_{workspace_revit_mcp,relay_probe}.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Clean-PC install, sign-in, explicit project | DGCL-01 | Needs a clean physical PC and a real DG account | Plan 16 Task 3 step 1 with docs/degram/CLEAN-INSTALL.md |
| Live Revit/GH snapshots on two PCs, busy/off/not-loopback | DGCL-04 | Needs Revit 2024 / Rhino 8 sessions | Plan 16 Task 3 step 4 |
| Live revoke/logout deny across chat, web, tools | DGCL-05 | Needs real sessions and admin actions | Plan 16 Task 3 step 5 |
| Listener release, reconnect after outage | DGCL-06 | OS process/port state | Plan 16 Task 3 step 6 (netstat) |
| System pair streaming/tool capability | DGCL-02/06/07 | Paid inference, owner-entered key | Plan 16 Task 2 live probe |
| First-launch isolation of installed Hermes | DGCL-01 | Real installed profile | Plan 15 Task 2 before/after listing |
| UI-SPEC backstop truths (4) | DGCL-02/04/07 | Visual layout at given widths | Plan 16 Task 3 visual review |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
