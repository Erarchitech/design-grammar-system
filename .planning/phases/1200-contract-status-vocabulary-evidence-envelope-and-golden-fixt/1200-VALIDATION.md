---
phase: 1200
slug: contract-status-vocabulary-evidence-envelope-and-golden-fixt
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-20
---

# Phase 1200 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `1200-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

This phase spans three test stacks. There is no single command; each leg has its own.

| Property | Value |
|----------|-------|
| **Framework (Python)** | pytest — already in `data-service/requirements.txt` and `dg-reasoner/requirements.txt` |
| **Framework (C#)** | xunit 2.9.2 — `DG/tests/DG.Tests/DG.Tests.csproj` |
| **Config file** | none dedicated — pytest runs on defaults (no `pytest.ini`/`pyproject.toml` found); `DG.Tests.csproj` is the .NET equivalent |
| **Quick run command (C#)** | `dotnet test DG/tests/DG.Tests/DG.Tests.csproj --filter FullyQualifiedName~<NewTestClass>` |
| **Quick run command (Python, host-runnable)** | `pytest <new schema/fixture-shape test> -x -q` — schema and fixture-shape tests are pure-file assertions and need no live stack |
| **Quick run command (Python, in-container)** | `docker compose exec data-service pytest -x -q` · `docker compose exec dg-reasoner pytest -x -q` |
| **Full suite command** | `dotnet test .\DG\tests\DG.Tests\` + in-container pytest per Python service |
| **Estimated runtime** | quick ~5–30s (single filtered test); full suite minutes (412 C# + 772 data-service + 39 dg-reasoner) |

**Regression baselines** (from STATE.md, carried forward — *not* re-run during research):
data-service 772 passed / 1 skipped / 8 deselected · dg-reasoner 39 passed · DG .NET 412 passed.

**Environment caveat (drives D-13):** 4 `DesignStateValidationFlowTests` and 4 `test_dg_context.py`
tests fail from the host because the `neo4j` hostname resolves only inside the compose network.
Environment-dependent, not regressions. Any leg needing Neo4j runs in-container.

---

## Sampling Rate

- **After every task commit:** run the specific new unit test(s) for that task — schema-validation
  and fixture-shape tests run host-side without Docker; the C#-leg envelope test runs via plain
  `dotnet test --filter`.
- **After every plan wave:** full DE-01 run against the live Docker stack, plus the full
  pytest/xunit suites to protect the 772 / 39 / 412 baselines.
- **Before `/gsd-verify-work`:** full suites green on every stack the phase touched, and a DE-01
  report present with `silent_disagreement_count == 0`.
- **Max feedback latency:** ~30s for per-task quick runs; full-stack DE-01 is a per-wave cost.

---

## Per-Task Verification Map

Task IDs are assigned by the planner; this table is seeded at the requirement level and is
refined once PLAN.md files exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | ALGN12-01 | — | N/A | unit | schema-driven set-equality on `$defs.Status.enum` (8 values exactly) — `dotnet test --filter EvidenceContractTests` / `pytest test_evidence_contract.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ALGN12-02 | T-1200-V5 | Envelope input validated mechanically by the schema, not by reading | unit + schema validation | `jsonschema.validate(envelope, schema)` per leg | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ALGN12-03 | — | N/A | fixture-content assertion (unit) | `pytest test_golden_fixture_shape.py` — asserts 4 atom types, 2 mixed-outcome objects, Design State, geometry reference | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ALGN12-04 | T-1200-V6 | SHA-256 integrity hashes detect cross-leg divergence | integration (live stack) | DE-01 runner + thin wrapper asserting `silent_disagreement_count == 0` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | ALGN12-02 (D-07) | T-1200-V6 | Canonical form is byte-identical across Python and C# | unit (cross-language golden vectors) | shared canonical-JSON test-vector file asserted by BOTH pytest and xunit | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

These are largely the phase's own deliverables restated from the test-infrastructure angle —
nothing can be asserted until they exist.

- [ ] JSON Schema annex (e.g. `spec/evidence-contract.schema.json`) — nothing is schema-validatable before it
- [ ] Golden fixture + seed script (e.g. `fixtures/golden/fixture.json`, `fixtures/golden/seed.cypher`) — ALGN12-03 and ALGN12-04 both depend on it
- [ ] `jsonschema` pin added to `data-service/requirements.txt` and `dg-reasoner/requirements.txt` (4.26.0 available ambiently, not pinned)
- [ ] `docker-compose.yml` — fixture volume mount for `dg-reasoner` (it has only `./ontology:/app/ontology:ro`; data-service already reaches the repo root via `.:/mnt/repo:ro`)
- [ ] DE-01 runner (e.g. `tools/de01/`) — no existing cross-service harness to extend
- [ ] Shared canonical-JSON golden-vector file, consumed as literal data by both the C# and Python suites (precedent: `DgIdMintingService` golden vectors)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Status and evidence semantics accepted by the owner | ALGN12-01, ALGN12-02 | The ROADMAP gate says "accepted by the owner" — whether `no_population` *means* the right thing is a semantic judgement, not a green/red assertion | Read `spec/EVIDENCE-CONTRACT.md` prose + the DE-01 report; confirm each of the 8 statuses is distinguishable and correctly assigned in the report; record acceptance |
| DE-01 report is readable evidence, not just a pass/fail | ALGN12-04 | D-12's value is the artifact being *readable*; legibility is not machine-assertable | Open the DE-01 Markdown report; confirm per-leg, per-(rule,object) rows carry status, warnings, hashes, service+version |
| Typed non-equivalence is genuinely *declared*, not coerced | ALGN12-04 | "Silent disagreement is a failure; a declared one is not" — distinguishing a declared divergence from a normalized-away one needs review of the runner's comparison logic | Review the comparison code path for any place a difference could be dropped, coerced, or normalized away; confirm the C#-leg `ObjectPropertyAtom` result surfaces as typed `unsupported`, by design (1201 owns the fix) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for per-task quick runs
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
