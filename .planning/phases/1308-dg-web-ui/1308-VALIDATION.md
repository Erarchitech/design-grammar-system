---
phase: 1308
slug: dg-web-ui
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-12
---

# Phase 1308 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `1308-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (data-service); `node:test` (ui-v2); vitest 4.1.10 (fork `apps/degram/apps/desktop`); xUnit (`DG.Tests`) |
| **Config file** | none for ui-v2 (Wave 0 adds `"test": "node --test tests/*.test.mjs"`); `apps/degram/apps/desktop/vitest.config.ts` |
| **Quick run command** | `node --test ui-v2/tests/*.test.mjs` (≈2 s) or the single pytest file touched |
| **Full suite command** | `python -m pytest data-service/tests -q` + `node --test ui-v2/tests/*.test.mjs` + `npm --prefix ui-v2 run build` + `dotnet test .\DG\tests\DG.Tests\` |
| **Estimated runtime** | ~240 seconds (full); quick < 30 s |

Baselines: data-service in-container 1130 pass + 13 env failures (anything else is a regression); `DG.Tests` 4 Neo4j E2E tests are env-dependent; ui-v2 231 pass; fork sidebar vitest 14 pass.

---

## Sampling Rate

- **After every task commit:** the single relevant quick command from the map below
- **After every plan wave:** `node --test ui-v2/tests/*.test.mjs` + touched data-service test files + `test_route_inventory.py` + `test_security_boundary_spec.py`
- **Before `/gsd-verify-work`:** full suite green, `npm --prefix ui-v2 run build`, `python tools/degram/workspace.py verify`
- **Max feedback latency:** 30 seconds (quick)

---

## Per-Task Verification Map

Requirement-level map; the planner/executor fills task IDs.

| Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|-----------------|-----------|-------------------|-------------|--------|
| WEBUI-01 | `?lang=` allowlisted (en/ru) | unit | `node --test ui-v2/tests/i18n.test.mjs` | ❌ W0 | ⬜ pending |
| WEBUI-02 | text nodes only, no server HTML interpolated | unit | `node --test ui-v2/tests/i18n.test.mjs` | ❌ W0 | ⬜ pending |
| WEBUI-03 | owner/admin only, `LAST_OWNER` under lock, CSRF | integration | `python -m pytest data-service/tests/test_member_roles.py -q`; `node --test ui-v2/tests/member-roles-api.test.mjs` | ❌ W0 | ⬜ pending |
| WEBUI-04 | admin-only route (existing), UI hidden for non-admin | unit | `node --test ui-v2/tests/project-settings-api.test.mjs`; `python -m pytest data-service/tests/test_degram_policy.py -q` | ❌ W0 / ✅ | ⬜ pending |
| WEBUI-05 | summary project-scoped, counts only | integration + unit | `python -m pytest data-service/tests/test_project_summary.py -q`; `node --test ui-v2/tests/landing-summary.test.mjs` | ❌ W0 | ⬜ pending |
| WEBUI-06 | host signal regex allowlist | unit | `node --test ui-v2/tests/host-degram.test.mjs`; `npx vitest run --project ui src/degram/sidebar.test.tsx` (cwd `apps/degram/apps/desktop`) | ✅ extend | ⬜ pending |
| WEBUI-07 | `dgk_` hash-only, TTL, live grant re-check, `dgc_` rejected, 410 | integration | `python -m pytest data-service/tests/test_connector_session.py data-service/tests/test_connector_access.py data-service/tests/test_connectors.py data-service/tests/test_cross_project_matrix.py data-service/tests/test_designstate_capture.py -q` | ❌ W0 / ✅ rewrite | ⬜ pending |
| WEBUI-08 | no password persisted/logged, refuse remote http | unit | `dotnet test .\DG\tests\DG.Tests\ --filter "FullyQualifiedName~ConnectorSessionClient\|FullyQualifiedName~DataServiceRequestAuth\|FullyQualifiedName~ErrorMessageTemplate"` | ❌ W0 | ⬜ pending |
| WEBUI-09 | no token UI or API calls | unit + build | `node --test ui-v2/tests/connector-access-api.test.mjs ui-v2/tests/api-security.test.mjs`; `npm --prefix ui-v2 run build` | ✅ update | ⬜ pending |
| WEBUI-10 | spec blocks equal route table | integration | `python -m pytest data-service/tests/test_security_boundary_spec.py data-service/tests/test_route_inventory.py -q` | ✅ update | ⬜ pending |
| WEBUI-11 | image equals HEAD, tokens retired, UAT account gone | live/manual | hash compare (`sha256sum` after `tr -d '\r'`); ops script `--dry-run` then real | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `ui-v2/tests/i18n.test.mjs` + `"test"` script in `ui-v2/package.json` — WEBUI-01/02
- [ ] `data-service/tests/test_member_roles.py`, `test_project_summary.py`, `test_connector_session.py` — WEBUI-03/05/07
- [ ] `data-service/tests/auth_fixtures.py::connector_token_for()` moved onto `connector_session.issue`; `test_connectors.py` rewritten — WEBUI-07
- [ ] `ui-v2/tests/{member-roles-api,project-settings-api,landing-summary}.test.mjs` — WEBUI-03/04/05
- [ ] `DG/tests/DG.Tests/ConnectorSessionClientTests.cs` — WEBUI-08
- [ ] One-off ops script + dry-run fixture — WEBUI-11
- [ ] Owner settles dirty `ui-v2` / `data-service` working tree (CONTEXT D-49)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grasshopper add-in signs in and publishes with the user account | WEBUI-08 | needs owner's Rhino 8 session | wire CONNECTOR (Username/Password/Connect) → Session → VALIDATOR / COMPUTGRAPH PUBLISH; confirm «Вкл» on Connectors screen, then Connect=false → «Выкл» |
| DeGram sidebar «Projects» row | WEBUI-06 | Desktop launch not authorized in 1308 | accepted in the next DeGram release under separate authorization |
| Russian UI visual pass | WEBUI-02 | layout overflow in RU | switch badge to RU, walk landing + each screen |
| Live rollout steps | WEBUI-11 | destructive live store and restarts | each behind `checkpoint:human-verify` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
