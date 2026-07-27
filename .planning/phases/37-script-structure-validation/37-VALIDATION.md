---
phase: 37
slug: script-structure-validation
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-07-27
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `37-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing data-service standard — no new framework install) |
| **Config file** | none dedicated — suites live in `data-service/tests/` |
| **Quick run command** | `python -m pytest data-service/tests/test_cg_structure_checks.py -q` (unit tier, no Neo4j) |
| **Full suite command** | `docker compose exec data-service python -m pytest tests/ -q` (integration tier, live Neo4j) |
| **Measured runtime** | unit tier (host, `python -m pytest data-service/tests/ -q`): 492 passed / 4 failed (pre-existing `test_dg_context.py` Neo4j-dependent, expected on host) / 1 skipped / 1 deselected in 25.93s. Integration tier (`docker compose exec data-service python -m pytest tests/ -q`): 474 passed / 1 skipped / 1 deselected in 6.70s (real 8.2s). See `data-service/tests/README.md` for the full run story, including the container-image-staleness gotcha the integration-tier count reveals. |

**Two-tier split is mandatory, not stylistic.** Research Pitfall 2: `test_computgraph_publish.py`'s `FakeGraph` duck-type only simulates fixed MERGE writes — it cannot validate arbitrary Cypher pattern-matching. SVAL-01/02 correctness therefore requires a real Neo4j inside the compose network. The `neo4j` hostname does not resolve from the host (same constraint already documented for `test_dg_context.py`'s 4 Neo4j-dependent tests).

---

## Sampling Rate

- **After every task commit:** `python -m pytest data-service/tests/test_cg_structure_checks.py -q` (unit tier — pure-Python convention-compliance checks, no container needed)
- **After every plan wave:** `docker compose exec data-service python -m pytest tests/ -q` (full integration tier against live Neo4j)
- **Before `/gsd-verify-work`:** Full suite green **and** the SC1 human-verify checkpoint explicitly logged
- **Max feedback latency:** target < 30s for the unit tier; integration tier measured at Wave 0

---

## Per-Task Verification Map

*Task-level rows are populated after `/gsd-plan-phase` emits PLAN.md files (task IDs do not exist yet). The requirement-level contract below is the binding interim map — every task the planner writes must trace to one of these rows.*

| Req / SC | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| SVAL-01 | Orphan Pattern, Procedure-without-Interface, dangling `PARAM_LINK`, Algorithm-without-Procedure — each detected with exact entity references | integration (live Neo4j) | `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k structural -q` | ❌ W0 | ⬜ pending |
| SVAL-01 | Convention compliance (`Emg`/`Emr` normalization) surfaced from `Algorithm.contextJson.warnings` — **not** a live Cypher pattern match | unit (synthetic contextJson string) | `python -m pytest data-service/tests/test_cg_structure_checks.py -k convention -q` | ❌ W0 | ⬜ pending |
| SVAL-02 | Rule-mapped check passes on full Frame, fails on a copy missing `12_Proc` | integration (two published Frame variants) | `docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k rule_mapped -q` | ❌ W0 | ⬜ pending |
| SVAL-03 | `/consult` answer cites `11_Var_HTotal`, grounded not hallucinated | integration w/ cassette LLM adapter (no live LLM in CI) | `python -m pytest data-service/tests/test_computgraph_consult.py -q` | ❌ W0 | ⬜ pending |
| SVAL-01/02 | **Determinism** — repeated `/computgraph/validate` calls produce byte-identical findings | integration, run twice, assert equality | folded into the structural-check integration test | ❌ W0 | ⬜ pending |
| SC2 | Rule mapped to `*Footer*` passes on full Frame, fails on the `12_Proc`-less copy | automated (two synthetic `_frame_cg_context()` envelopes published to test Neo4j) | folded into `-k rule_mapped` | ❌ W0 | ⬜ pending |
| SC3 | `/consult` cites `11_Var_HTotal` | automated (cassette fixture) | folded into the consult integration test | ❌ W0 | ⬜ pending |
| SC4 | Validate path is LLM-free; `/consult` is the only gateway caller | automated grep gate | `grep -c "llm_gateway\|adapter.generate" data-service/cg_structure_checks.py` → expect `0` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `data-service/tests/test_cg_structure_checks.py` — covers SVAL-01/SVAL-02. Needs **both** a FakeGraph-style route-shape tier and a live-Neo4j integration tier (Pitfall 2: FakeGraph cannot substitute for real Cypher pattern-match correctness) — (closed by `cg_fixtures.py`'s parser-faithful envelope builders, which every later `test_cg_structure_checks.py` publishes; the check module itself is a later Phase 37 plan's artifact, out of this plan's scope)
- [x] Second published Frame variant fixture — Interface removed from `11_Proc`, and/or `12_Proc` group absent. Reuse `test_computgraph_publish.py`'s `_frame_cg_context()` builder, mutating the entity out before `publish_structure()` — (closed by `cg_fixtures.frame_without_interface()` and `cg_fixtures.frame_without_footer_procedure()`)
- [x] Cassette/fixture LLM response for `/consult` — mirror `data-service/tests/recognition_eval/cassette.py`'s record/replay pattern so SC3 is testable without a live LLM call — (closed by `consult_cassette.ConsultCassetteAdapter`, citing both a grounded `11_Var_HTotal` and an ungrounded `11_Var_HGhost` token)
- [x] **Confirm the integration-test run story.** Determine whether `data-service/tests/` run against live Neo4j in any standing job, or only ad hoc via `docker compose exec`. If there is no standing runner, this phase's integration tier needs a documented manual/local run step — same status as `test_dg_context.py`'s existing 4 Neo4j-dependent tests — (closed by `data-service/tests/README.md`: no standing CI job exists — `.github/` has no `workflows/` directory — both tiers are measured, timed, and documented as manual pre-PR steps)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Deleting an Interface tag from the Frame structure and re-publishing makes `/computgraph/validate` flag Procedure-without-Interface, naming the exact procedure | SC1 | Requires a live Grasshopper canvas edit and a re-publish through the real DG plugin — the automated tier publishes synthetic envelopes directly, which proves the check but not the end-to-end canvas→publish→validate loop | 1. Open the Frame definition in Rhino/GH. 2. Delete an Interface tag from `11_Proc`. 3. Re-publish via DG COMPUTGRAPH PUBLISH. 4. `POST /computgraph/validate {project, definitionId}`. 5. Assert the response flags Procedure-without-Interface and names `11_Proc`. |

**Note:** SC2 and SC3 were initially scoped as manual but research established both are automatable (SC2 via two synthetic published envelopes; SC3 via a cassette LLM fixture). Only SC1 is genuinely human-verify. Precedent: Phases 33, 34-02, and 34-03 all deferred live-Rhino UAT to phase-level `/gsd-verify-work` rather than self-approving.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [x] Feedback latency measured and recorded (replaces the placeholder runtime row above)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
