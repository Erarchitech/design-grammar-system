---
phase: 1203
slug: identity-convergence-and-attribute-of-decision
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-22
---

# Phase 1203 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `1203-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

This phase spans two languages; both suites are in scope.

| Property | Value |
|----------|-------|
| **Framework (C#)** | xUnit, via `dotnet test DG/tests/DG.Tests/` |
| **Framework (Python)** | pytest, via `python -m pytest data-service/tests -q` |
| **Config file** | `DG.Tests.csproj` (C#); none found for pytest in `data-service/` — no `pytest.ini` / `pyproject.toml` test section detected |
| **Quick run command (C#)** | `dotnet test DG/tests/DG.Tests/ -v minimal --filter "FullyQualifiedName~Identity\|FullyQualifiedName~DesignStateIdGenerator"` |
| **Quick run command (Python)** | `python -m pytest data-service/tests/test_dg_identity.py data-service/tests/test_cg_input_bindings.py data-service/tests/test_computgraph_publish.py -q` |
| **Full suite command (C#)** | `dotnet test DG/tests/DG.Tests/ -v minimal` |
| **Full suite command (Python)** | `python -m pytest data-service/tests -q` |
| **Estimated runtime** | ~60s C# / ~90s Python (full suites) |

**Known environment-dependent failures — NOT regressions:**
- 4 `DesignStateValidationFlowTests` (C#) fail fast when Neo4j is down.
- 4 `test_dg_context.py` tests (Python) fail from the host because the `neo4j` hostname
  resolves only inside compose.

**Baseline to re-establish before any work starts:** 1202-CONTEXT.md records
"823 passed / 1 skipped / 1 pre-existing-failed" for the Python suite. This may have
shifted; capture the real baseline as a Wave 0 step so D-08/D-09's re-derivation is
measured against a known-good count.

---

## Sampling Rate

- **After every task commit:** scoped quick-run filter matching the touched module
  (C# or Python per the commands above)
- **After every plan wave:** both full suites
  (`dotnet test DG/tests/DG.Tests/ -v minimal` AND `python -m pytest data-service/tests -q`)
- **Before `/gsd-verify-work`:** both full suites green (modulo the documented
  environment-dependent Neo4j-down failures), **plus** a live-stack CQ3 fixture run
  proving both query directions — this is the ROADMAP gate's own wording
- **Max feedback latency:** ~90 seconds

**Cross-language lockstep rule (D-08 + D-09):** the golden-vector pair
`dg:BC8E62EE137E2B56` for triple `(p1, frame.gh, cg:1:proc:11_Proc)` is asserted in
BOTH `DgIdMintingServiceTests.cs:60-65` and `test_dg_identity.py:36-39,235-244`.
Both must be re-derived in the SAME wave. A commit that lands one language's new
vector without the other leaves the parity harness red and is the phase's primary
self-inflicted failure mode (RESEARCH.md Pitfall 1).

---

## Per-Task Verification Map

*Task IDs are assigned by the planner; this table seeds the requirement→command mapping
the planner fills in per task.*

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| ALGN12-12 | Both ObjState minting forms retained; contract names authority per case (D-06/D-07) | doc | Manual review of `spec/DG-ID.md` new DesignState section | ❌ W0 | ⬜ pending |
| ALGN12-12 | `project` folded into DesignState hash, additively (D-08) | unit | `dotnet test ... --filter DesignStateIdGeneratorTests` | ❌ W0 (new assertions) | ⬜ pending |
| ALGN12-12 | CR-02 length-prefix fix, all six functions, both languages (D-09) | unit | `dotnet test ... --filter "FullyQualifiedName~PipeCollision"` + `pytest data-service/tests/test_dg_identity.py -k collision` | ❌ W0 | ⬜ pending |
| ALGN12-13 | Platform conflict / detach / provenance tested (D-12, D-13) | integration | `pytest data-service/tests/test_dg_identity.py -k "conflict or detach or provenance"` | ✅ partial | ⬜ pending |
| ALGN12-13 | CR-01: mint→bind→publish→binding survives (D-10) | integration | new pytest exercising publish-coincidence on `(cgId, definitionId, project)` | ❌ W0 | ⬜ pending |
| ALGN12-14 | `ATTRIBUTE_OF` written; forward direction evidenced (D-01..D-04) | integration | `pytest data-service/tests/... -k attribute_of` | ❌ W0 | ⬜ pending |
| ALGN12-14 | `ATTRIBUTE_OF` reverse direction (parameter → governing rules) evidenced (D-14) | integration (fixture) | live-stack CQ3 fixture run | ❌ W0 | ⬜ pending |
| ALGN12-14 | Full schema propagation swept (D-05) | doc audit | grep-based check that `ATTRIBUTE_OF` appears in every file on CLAUDE.md's Schema Change Propagation list | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Capture the true current baseline for both suites before any edit (D-08/D-09 measure against it)
- [ ] Verify whether `fixtures/golden/canonical-vectors.json` carries any DesignState-ID or `dgId`
      literal that D-08/D-09 would invalidate (RESEARCH.md Open Question 1 — unread this session)
- [ ] Re-grep to relocate the WR-02 defect — `spec/DATABASE.md:336` no longer contains the cited
      wrong-route/verb text (RESEARCH.md Discrepancy 2); it may have moved or already been fixed
- [ ] Re-count `sh:NodeShape` declarations in `ontology/dg-shapes.ttl` — disk shows **18**, CONTEXT.md
      D-05 says 20 (RESEARCH.md Discrepancy 1)
- [ ] `data-service/tests/test_dg_identity.py` — collision-regression test (D-09) + mint→bind→publish
      coincidence regression (D-10 / CR-01)
- [ ] `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — project-in-hash assertions (D-08) and
      pipe-collision assertions (D-09) across all four `DesignStateIdGenerator` functions
- [ ] `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs` — updated golden vector post-D-09 +
      collision regression
- [ ] New `ATTRIBUTE_OF` forward+reverse query tests mirroring `PAPER-C-032`'s shape
- [ ] New CQ3 fixture directory under a **sibling path** (`fixtures/golden/fixture.json` stays frozen
      per 1200 D-11 / 1202 D-17) following the on-disk `fixtures/golden/replay/` precedent
      (`README.md` + seed Cypher + expected-result JSON)
- [ ] Framework install: **none needed** — xUnit and pytest are both already present and configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grasshopper ObjState minting under the new contract | ALGN12-12 | Requires Rhino/Grasshopper canvas; live UAT is GATE12-04, routed to v9.0 Phase 40 — v12.0 cannot mark it passed | Rebuild plugin (`dotnet build .\DG\DG.sln -c Release`), open a canvas, capture an ObjState, confirm the ID matches the new contract |
| Schema-propagation completeness (D-05) | ALGN12-14 | Judgment call per file; the grep check proves presence, not correctness of the edit | Walk CLAUDE.md's Schema Change Propagation list file by file |
| Ontology / runtime / spec / paper ownership agreement (ROADMAP gate) | ALGN12-14 | Cross-artifact editorial agreement, not a runnable assertion | Confirm the `ATTRIBUTE_OF` semantics in `DesignGrammar-V7.owl`, the runtime derivation, `spec/DG-ID.md`, and `PAPER-C-032` all describe the same relation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] Both query directions evidenced by the CQ3 fixture (ROADMAP gate)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
