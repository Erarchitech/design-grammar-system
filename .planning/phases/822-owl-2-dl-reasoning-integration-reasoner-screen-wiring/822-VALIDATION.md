---
phase: 822
slug: owl-2-dl-reasoning-integration-reasoner-screen-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-12
---

# Phase 822 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `822-RESEARCH.md` §Validation Architecture. Backend behavior is
> unit/integration-tested with pytest; the React run-state machine has **no automated
> test infrastructure** and is verified by manual conversational UAT — consistent with
> the existing `ui-v2` convention (zero JS test files across all screens; introducing a
> frontend test runner for one screen is out of this phase's boundary).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 7.x — already configured in `dg-reasoner/tests/` and `data-service/tests/` |
| **Framework (frontend)** | none — `ui-v2` has no test script / no vitest·jest·testing-library dependency; manual UAT only |
| **Config file** | `dg-reasoner/tests/conftest.py` (integration marker + Neo4j-availability skip helper, from Phase 821) |
| **Quick run command** | `pytest dg-reasoner/tests -m "not integration"` and `pytest data-service/tests/test_reasoner.py` |
| **Full suite command** | `pytest dg-reasoner/tests` (docker stack up — includes integration tier) |
| **Estimated runtime** | ~5–15 s quick (mocked); integration tier depends on live HermiT (~2 s per real check on the current fixture) |

---

## Sampling Rate

- **After every task commit (backend):** Run `pytest dg-reasoner/tests -m "not integration"` and `pytest data-service/tests/test_reasoner.py`
- **After every plan wave:** Run full `pytest dg-reasoner/tests` (stack up, integration tier) **+** manual click-through of all four verdict states in the running dev UI
- **Before `/gsd-verify-work`:** Backend suite green **and** all four verdict states (Consistent / Inconsistent / Unknown / Cancelled) manually exercised against the live stack
- **Max feedback latency:** ~15 s (backend quick run)

---

## Per-Task Verification Map

> Task IDs are assigned by the planner. This map is completed after PLAN.md exists
> (planner or `gsd-nyquist-auditor` fills the rows); the requirement→behavior→test
> mapping below is the source the planner lifts from.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (sidecar label enrichment) | TBD | 1 | REAS-06 (crit 2, D-02/D-13) | — | `unsatisfiable_classes` entries are `{iri,label}`; label falls back to local IRI name, never null, never a raw full IRI | unit | `pytest dg-reasoner/tests/test_routes.py -k label -x` | ❌ W0 | ⬜ pending |
| TBD (proxy timeout branch) | TBD | 1 | REAS-06 (crit 3) | T-822-01 (info-leak) | sidecar timeout/connect-error → distinct 504/502 with pre-written `detail` body, never a silent pass/fail; never blocks caller past bounded timeout | unit | `pytest data-service/tests/test_reasoner.py -k timeout -x` | ❌ W0 | ⬜ pending |
| TBD (D-10 contract regression) | TBD | 1 | REAS-06 (crit 1) | — | `/reason/consistency` returns the D-10 envelope with the new label shape | unit | `pytest dg-reasoner/tests/test_routes.py::test_reason_consistency_returns_d10_contract -x` | ✅ (extend existing, Phase 821) | ⬜ pending |
| TBD (live HermiT round-trip) | TBD | 2 | REAS-06 (crit 1, true E2E) | — | real HermiT verdict returned end-to-end via the proxy | integration | `pytest dg-reasoner/tests/test_roundtrip_integration.py -m integration` (stack up) | ✅ (existing, Phase 821) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `dg-reasoner/tests/test_routes.py` (or a new sibling file) — label-enrichment `{iri,label}` shape + fallback test (REAS-06 criterion 2 / D-02 / D-13)
- [ ] `data-service/tests/test_reasoner.py` — proxy timeout / connect-error response-shape test asserting the distinct `detail.code` bodies that disambiguate Unknown (D-08) vs hard error (D-09) (REAS-06 criterion 3)
- [x] Frontend: **no** test framework install planned — manual UAT accepted per existing `ui-v2` convention (decision recorded; not a gap to close)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Run-state machine: idle → running → consistent / inconsistent / unknown / cancelled / error | REAS-06 (crit 1, 3) | No frontend test infra in `ui-v2`; introducing one is out of phase scope | In the running dev UI, click **Run check** on the HermiT card; confirm spinner + live elapsed counter, then each terminal verdict renders with its distinct treatment |
| Timeout → **Unknown** (amber, "inconclusive"), distinct from a fail and from Cancelled | REAS-06 (crit 3) | Timeout cannot be forced without a slow real project | Temporarily lower the sidecar timeout (`docker compose run -e DG_REASONER_TIMEOUT_SECONDS=1 …`) or stub a 504-timeout-body `/reasoner/consistency` response; confirm the card shows Unknown, never green/red |
| Cancel via AbortController mid-run → **Cancelled** (quiet/gray), never read as a verdict | REAS-06 (crit 3) | Client-abort timing is interactive | Start a run against a slow response and click **Cancel**; confirm Cancelled state, distinct from Unknown |
| Re-run reflects fresh result, no stale/cached answer | REAS-06 (crit 4) | POST-not-cached is verified by inspection | `grep -n "Cache-Control\|memo" ui-v2/src/lib/reasonerApi.js` → expect no matches; re-run after an export change and confirm the verdict updates |
| Selecting Pellet offers **no** run path | D-04 / D-06 | UI affordance check | Confirm Pellet keeps its placeholder badge and exposes no Run button |

---

## Validation Sign-Off

- [ ] All backend tasks have `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive backend tasks without automated verify
- [ ] Wave 0 covers both MISSING backend references (label shape, proxy timeout)
- [ ] Frontend behaviors enumerated in Manual-Only Verifications and exercised before `/gsd-verify-work`
- [ ] No watch-mode flags
- [ ] Feedback latency < 15 s (backend)
- [ ] `nyquist_compliant: true` set in frontmatter (after per-task map is completed against final PLAN.md)

**Approval:** pending
