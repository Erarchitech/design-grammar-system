---
phase: 38
slug: ai-generated-grasshopper-script-inputs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-27
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `38-RESEARCH.md` § Validation Architecture (three tiers).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python, `data-service/tests/`) + xUnit (C#, `DG/tests/DG.Tests/`) |
| **Config file** | `data-service/tests/conftest.py` (no pytest.ini — rootdir-discovered) |
| **Quick run command** | `python -m pytest data-service/tests/ -q -k "cg_ or paramstate or input_gen"` |
| **Full suite command** | `python -m pytest data-service/tests/ -q` and `dotnet test .\DG\tests\DG.Tests\` |
| **Estimated runtime** | ~30 s (pytest quick), ~90 s (pytest full), ~60 s (dotnet) |

**Tiering (from RESEARCH § Validation Architecture):**

| Tier | Environment | Scope |
|------|-------------|-------|
| Tier 0 | offline, no LLM / no Neo4j / no Rhino | domain validator (property-based), type mapping, ParamState payload round-trip, determinability classifier, diversity metric, provenance completeness |
| Tier 1 | Docker stack, cassette-backed LLM (replay by default, loud on miss — Phase 35 plan 35-13 precedent) | persistence + provenance `MATCH` query, bounded-retry behaviour, GHIN-04 import-boundary assertion |
| Tier 2 | in-Rhino, human | PARAMETER REINSTATE apply + per-parameter ReStatus, JOIN A on the Frame fixture, SC3 no-canvas-mutation-before-accept |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest data-service/tests/ -q -k "cg_ or paramstate or input_gen"`
- **After every plan wave:** Run `python -m pytest data-service/tests/ -q` (+ `dotnet test .\DG\tests\DG.Tests\` for waves touching `DG/`)
- **Before `/gsd-verify-work`:** Full suite must be green (modulo the known env-dependent failures below)
- **Max feedback latency:** 30 seconds

**Known environment-dependent failures (not regressions):** 4 `DesignStateValidationFlowTests`
(xUnit) fail fast when Neo4j is down; 4 `test_dg_context.py` tests fail from the host because the
`neo4j` hostname resolves only inside compose. Expect the same shape for any Tier 1 test here.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(filled by gsd-planner — every task must map to a Tier 0/1 automated command or declare a Tier 2 manual entry below)* | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data-service/tests/test_input_generation.py` — Tier 0 stubs for GHIN-01, GHIN-02
- [ ] `data-service/tests/test_input_provenance.py` — Tier 0 stubs for GHIN-03
- [ ] `data-service/tests/test_input_generation_boundary.py` — GHIN-04 import-boundary assertion
- [ ] LLM cassette fixture for input generation, alongside `data-service/tests/consult_cassette.py`
      (record/replay, replay by default, loud on miss)

*pytest and xUnit are both already installed and configured — no framework install needed.*

---

## SC1 Quality Threshold (Nyquist gate — define before implementation)

RESEARCH flags SC1 as the only success criterion whose evidence is a **number**, and Phase 35's
lesson was that plumbing shipped without the quality ever being measured. The planner MUST fix an
explicit numeric threshold for:

> fraction of generated candidates that are (a) in-domain, (b) step-aligned, and
> (c) rule-satisfying where the rule is determinable (D-09 classification)

computed in pytest over the Frame-definition fixture, and assert on it. A plan that ships
generation without this number is not Nyquist-compliant.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Accepted candidate → PARAMETER REINSTATE moves sliders; per-parameter ReStatus matches expected report | GHIN-02 / SC2 | Requires Rhino + Grasshopper canvas — no headless harness | Open the Frame definition, accept a generated candidate in the ui-v2 review panel, run PARAMETER REINSTATE, compare ReStatus per parameter |
| JOIN A holds on a real definition — every generated `ParameterId` resolves | GHIN-01 / D-01, D-02 | Depends on a live published Computgraph from a real canvas | Publish the Frame definition, generate candidates, confirm every `reinstateParameterId` resolves against canvas parameters |
| Nothing changes on canvas until the architect accepts | GHIN-04 / SC3 | Observational — absence of a side effect in a GUI | Generate candidates without accepting; confirm canvas sliders are untouched |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] SC1 numeric threshold defined and asserted in pytest
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
