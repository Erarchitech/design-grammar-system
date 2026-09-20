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
| 01-T1 | 1200-01 | 1 | ALGN12-01, ALGN12-02 | T-1200-02 | Contract states the boolean→canonical direction is forbidden | doc assertion | grep gate on all 8 status names + section count in `spec/EVIDENCE-CONTRACT.md` | ❌ W0 | ⬜ pending |
| 01-T2 | 1200-01 | 1 | ALGN12-01 | T-1200-01, T-1200-05 | Schema enum is the single vocabulary authority; `additionalProperties: false` | unit | `Draft202012Validator.check_schema` + set-equality on `$defs.CanonicalStatus.enum` | ❌ W0 | ⬜ pending |
| 01-T3 | 1200-01 | 1 | ALGN12-02 | T-1200-03 | Propagation bounded to 3 files (D-16) | source assertion | grep gate on `spec/DATABASE.md`, `CLAUDE.md`, `.planning/REQUIREMENTS.md` | ❌ W0 | ⬜ pending |
| 02-T1 | 1200-02 | 1 | ALGN12-03 | T-1200-10 | Golden-vector digests recomputed, not trusted | fixture-content assertion | python shape check: 4 atom types, mixed outcomes, 3-kind Design State, geometry ref, ordering, digest recompute | ❌ W0 | ⬜ pending |
| 02-T2 | 1200-02 | 1 | ALGN12-03 | T-1200-06, T-1200-07 | Every seeded node carries `project`; static literal Cypher | source assertion | python parse of `fixtures/golden/seed.cypher` statements | ❌ W0 | ⬜ pending |
| 02-T3 | 1200-02 | 1 | ALGN12-03 | T-1200-08 | Narrow read-only fixture mount, not a repo-root mount | integration | `docker compose exec -T dg-reasoner test -f /app/fixtures/golden/fixture.json` | ❌ W0 | ⬜ pending |
| 03-T1 | 1200-03 | 2 | ALGN12-02 (D-07) | T-1200-16 | Canonical form byte-identical to C# | unit (golden vectors) | `docker compose exec -T data-service pytest tests/test_canonical_json.py -x -q` | ❌ W0 | ⬜ pending |
| 03-T2 | 1200-03 | 2 | ALGN12-01, ALGN12-02, ALGN12-03 | T-1200-14, T-1200-16 | Enum schema-pinned; no boolean→canonical function | unit + schema validation | `docker compose exec -T data-service pytest tests/test_evidence_contract.py tests/test_golden_fixture_shape.py -x -q` | ❌ W0 | ⬜ pending |
| 03-T3 | 1200-03 | 2 | ALGN12-02 | T-1200-11, T-1200-12, T-1200-13 | Parameterized write; never-raises read; publish path protected | unit | `docker compose exec -T data-service pytest tests/test_evidence_contract.py -x -q` + full-suite baseline | ❌ W0 | ⬜ pending |
| 04-T1 | 1200-04 | 2 | ALGN12-01 | T-1200-20 | C# wire forms schema-pinned by test | unit | `dotnet test DG/tests/DG.Tests/DG.Tests.csproj --filter FullyQualifiedName~EvidenceContractTests` | ❌ W0 | ⬜ pending |
| 04-T2 | 1200-04 | 2 | ALGN12-02 (D-07) | T-1200-17, T-1200-18 | Ordinal key sort, no serializer defaults; parity with Python | unit (golden vectors) | `dotnet test ... --filter FullyQualifiedName~CanonicalJsonWriterTests` | ❌ W0 | ⬜ pending |
| 04-T3 | 1200-04 | 2 | ALGN12-02 | T-1200-19, T-1200-21 | Roll-up precedence mirrors Python; no boolean→status | unit | `dotnet test ... --filter FullyQualifiedName~EvidenceContractTests` + `dotnet build DG/DG.sln -c Release` | ❌ W0 | ⬜ pending |
| 05-T1 | 1200-05 | 3 | ALGN12-04 | T-1200-24 | Harness envelope schema-validated; evaluator untouched | integration | `dotnet run --project DG/tools/DG.De01Harness` + `jsonschema.validate` on stdout | ❌ W0 | ⬜ pending |
| 05-T2 | 1200-05 | 3 | ALGN12-04 | T-1200-23, T-1200-25, T-1200-28 | No dropped/coerced difference; per-leg graceful degradation | unit + integration (live stack) | `pytest tools/de01/tests/test_de01_runner.py -x -q -k "not live"` + full DE-01 run asserting `silent_disagreement_count == 0` | ❌ W0 | ⬜ pending |
| 05-T3 | 1200-05 | 3 | ALGN12-04 | — | N/A | doc assertion | grep gate on `tools/de01/README.md` | ❌ W0 | ⬜ pending |
| 05-T4 | 1200-05 | 3 | ALGN12-01, ALGN12-02, ALGN12-04 | T-1200-23 | Comparison code reviewed for silent-difference paths | manual (blocking checkpoint) | none — `checkpoint:human-verify`, see Manual-Only Verifications below | n/a | ⬜ pending |

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
