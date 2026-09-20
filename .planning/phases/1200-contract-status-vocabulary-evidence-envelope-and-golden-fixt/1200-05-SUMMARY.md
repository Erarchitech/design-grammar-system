---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 05
subsystem: testing
tags: [de01, evidence-contract, cross-service-verification, python, csharp, dotnet, jsonschema]

# Dependency graph
requires:
  - phase: 1200-01
    provides: spec/evidence-contract.schema.json, spec/EVIDENCE-CONTRACT.md
  - phase: 1200-02
    provides: fixtures/golden/fixture.json, fixtures/golden/seed.cypher, fixtures/golden/MANIFEST.md
  - phase: 1200-03
    provides: data-service/evidence_contract.py, data-service/canonical_json.py
  - phase: 1200-04
    provides: DG.Core/Contracts/EvidenceEnvelope.cs, EvidenceEnvelopeFactory.cs, EvidenceStatus.cs, CanonicalJsonWriter.cs
provides:
  - DE-01, the standalone four-leg cross-service evidence comparison runner
  - DG.De01Harness, the C# leg's console entry point
  - Owner acceptance (frozen) of the status vocabulary and evidence envelope shape
affects: [1201, 1202, 1203, 1204, 1205, v11.0 Phase 1105]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Never-raises leg adapter house style (derive_valid_status precedent) — every DE-01 leg adapter returns a typed LegResult, never propagates an exception"
    - "compare_legs total classification: agreement | declared_non_equivalence (typed status + non-empty warning) | silent_disagreement, with no branch that loses a difference"

key-files:
  created:
    - DG/tools/DG.De01Harness/DG.De01Harness.csproj
    - DG/tools/DG.De01Harness/Program.cs
    - tools/de01/legs.py
    - tools/de01/report.py
    - tools/de01/run_de01.py
    - tools/de01/report_schema.json
    - tools/de01/README.md
    - tools/de01/tests/test_de01_runner.py
    - tools/de01/tests/conftest.py
    - tools/de01/__init__.py
  modified:
    - DG/DG.sln
    - .gitignore

key-decisions:
  - "Owner approved (2026-09-20): spec/EVIDENCE-CONTRACT.md §1 (status vocabulary), §3 (envelope fields), and §10 (v11.0 Phase 1105 ownership split) are accepted and frozen — the contract's status semantics are locked for phases 1201-1205 and the v11.0 propagation work"
  - "The prior executor's Task 4 checkpoint text misdescribed the ObjectPropertyAtom declared non-equivalence as the one live in .de01/de01-report.json; the actual report's 3 declared_non_equivalences all carry 'leg unavailable' (connection timeout) reasons for data-service/dg-reasoner/replay, not the ObjectPropertyAtom semantic gap — see Deviations below"
  - "The live four-leg comparison (all four legs actually agreeing/diverging on the same fixture) remains undemonstrated in this environment because Docker Desktop is not running; only the csharp leg executed against the running stack"

requirements-completed: [ALGN12-04]

coverage:
  - id: D1
    description: "DG.De01Harness console app builds in the DG.sln solution and emits one schema-valid canonical envelope for the C# leg, mapping NotSupportedException to unsupported and zero-binding rows to no_population without inferring from the legacy boolean"
    requirement: "ALGN12-04"
    verification:
      - kind: integration
        ref: "dotnet build DG/DG.sln -c Release && dotnet run --project DG/tools/DG.De01Harness -- fixtures/golden/fixture.json | jsonschema.validate against spec/evidence-contract.schema.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "tools/de01/ runner drives the golden fixture through four leg adapters (data-service, dg-reasoner, csharp, replay), validates every envelope against the contract schema, and classifies every cross-leg difference as agreement, declared non-equivalence, or silent disagreement with no lost differences"
    requirement: "ALGN12-04"
    verification:
      - kind: unit
        ref: "tools/de01/tests/test_de01_runner.py -x -q -k 'not live' (12 tests, all synthetic LegResult-based)"
        status: pass
      - kind: integration
        ref: "python tools/de01/run_de01.py --fixture fixtures/golden/fixture.json --out-dir .de01 — produced .de01/de01-report.json + .de01/de01-report.md, silent_disagreement_count == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "tools/de01/README.md documents invocation, per-leg preconditions, the acceptance rule, the ObjectPropertyAtom by-design non-equivalence, environment caveats, and the fixture freeze rule"
    requirement: "ALGN12-04"
    verification:
      - kind: other
        ref: "grep checks for silent_disagreement_count, ObjectPropertyAtom, 1201, seed.cypher, 'no CI' all present"
        status: pass
    human_judgment: false
  - id: D4
    description: "Owner acceptance of status and evidence semantics — spec/EVIDENCE-CONTRACT.md sections 1, 3, and 10 accepted and frozen (ROADMAP gate)"
    requirement: "ALGN12-04"
    verification: []
    human_judgment: true
    rationale: "This is the ROADMAP gate's explicit 'accepted by the owner' condition — a semantic judgement (whether the vocabulary and envelope shape are the ones to freeze for phases 1201-1205) that cannot be automated. Resolved via user response 'approved' on this continuation."
  - id: D5
    description: "Live four-leg agreement demonstration on the golden fixture — data-service, dg-reasoner, csharp, and replay all producing comparable canonical statuses on the same fixture run"
    verification: []
    human_judgment: true
    rationale: "Docker Desktop's daemon is not running in this environment, so data-service, dg-reasoner, and the replay leg (which depends on data-service + a seeded Neo4j) all time out and report typed error rows. Only the csharp leg actually executed. The comparison logic is proven correct by infrastructure-independent unit tests and by the one leg that did run (no_population correctly distinguished from failed), but a live run where all four legs are reachable has not been demonstrated. Outstanding — see 'Outstanding: Live Four-Leg Run' below."

# Metrics
duration: ~10min (Task 4 continuation only; Tasks 1-3 executed by prior agent, see 1200-05-PLAN.md task table)
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 05: DE-01 Cross-Service Evidence Runner Summary

**DE-01 — a standalone Python+C# runner that drives the golden fixture through four legs (data-service, dg-reasoner, csharp, replay), validates every envelope against the evidence contract schema, and classifies every cross-leg status difference as agreement, declared non-equivalence, or silent disagreement — owner-approved and frozen, with the live four-leg run still outstanding pending a running Docker stack.**

## Performance

- **Tasks:** 4/4 complete (Tasks 1-3 by the initial executor; Task 4 resolved on this continuation)
- **Files modified:** 8 created, 2 modified (DG.sln, .gitignore) — see key-files above

## Accomplishments

- Built `DG.De01Harness`, a minimal .NET 9 console app that gives the runner a C# leg: reads the golden fixture, evaluates each object through `RuleEvaluator.EvaluateRule`, and maps outcomes (including the `ObjectPropertyAtom` case's `NotSupportedException`) to typed `EvidenceStatus` values at its own boundary, without touching `RuleEvaluator.cs`.
- Built the DE-01 Python runner (`tools/de01/`): four never-raises leg adapters, a `compare_legs` comparison core with a total (agreement / declared / silent) classification, dual JSON+Markdown report emission, and a wrapper test asserting `silent_disagreement_count == 0`.
- Wrote `tools/de01/README.md` documenting invocation, per-leg preconditions, the acceptance rule, the pre-declared `ObjectPropertyAtom` non-equivalence, environment caveats (host/container Python version split, `neo4j` hostname resolution), and the no-CI / fixture-freeze rules.
- **Task 4 — owner acceptance obtained.** The owner responded "approved" to the checkpoint. `spec/EVIDENCE-CONTRACT.md` §1 (status vocabulary), §3 (evidence envelope shape), and §10 (v11.0 Phase 1105 ownership split — 1200 owns definition, 1105 owns propagation) are accepted and frozen for phases 1201-1205 and the v11.0 propagation work.

## Task Commits

Tasks 1-3 (prior executor, verified present in `git log`):

1. **Task 1: Build the C# leg harness — DG.De01Harness console app** - `00a1aa4` (feat)
2. **Task 2: Build the DE-01 runner — four leg adapters, comparison, dual-format report** - `bbaa9ea` (feat)
3. **Task 3: Write tools/de01/README.md** - `af01dfe` (docs)

Task 4 has no code changes — it is an acceptance gate, recorded here and in STATE.md rather than as a source commit. Per the plan's own instruction ("Do not proceed past this task ... until the owner responds"), the checkpoint closes via this SUMMARY plus the plan-level metadata commit, following the same precedent as Phase 823 Plan 06 and Phase 29 Plan 03 (`checkpoint:human-verify` closed via a recorded "approved" response with no code changes).

**Plan metadata:** committed alongside this SUMMARY (docs commit, see below).

## Files Created/Modified

- `DG/tools/DG.De01Harness/DG.De01Harness.csproj` - net9.0 console project, references DG.Core only
- `DG/tools/DG.De01Harness/Program.cs` - single-envelope emitter for the C# leg
- `DG/DG.sln` - adds DG.De01Harness to the solution
- `tools/de01/legs.py` - four leg adapters (`run_leg_data_service`, `run_leg_dg_reasoner`, `run_leg_csharp`, `run_leg_replay`), each never-raises
- `tools/de01/report.py` - `compare_legs`, `emit_json_report`, `emit_markdown_report`
- `tools/de01/run_de01.py` - CLI entry point
- `tools/de01/report_schema.json` - DE-01's own report schema, `$ref`-ing the contract schema's `CanonicalStatus` enum
- `tools/de01/README.md` - operator documentation
- `tools/de01/tests/test_de01_runner.py`, `tools/de01/tests/conftest.py`, `tools/de01/__init__.py` - unit tests and package scaffolding
- `.gitignore` - excludes `.de01/` runtime output directory

## Decisions Made

- Owner approval recorded verbatim: "approved" — accepting the status vocabulary (§1), evidence envelope shape (§3), and v11.0 handoff split (§10) as frozen.
- See `key-decisions` in frontmatter for the full decision list, including the two corrections below.

## Deviations from Plan

### Correction to the prior agent's Task 4 checkpoint framing

The initial executor's checkpoint text (Task 4 `<what-built>`/`<how-to-verify>`, and by extension its framing to the user) stated that the `ObjectPropertyAtom` row should be inspected as **the** declared non-equivalence naming `SwrlRuleParser.ResolveAtomType` / Phase 1201. This is only partially accurate against the actual `.de01/de01-report.json` produced in this environment:

- The report's `declared_non_equivalences` array has exactly 3 entries (`OBJ_GOLD_EMPTY`, `OBJ_GOLD_FAIL`, `OBJ_GOLD_PASS`). **All three carry a "leg unavailable" (connection timeout) reason** for data-service, dg-reasoner, and/or replay — not the `ObjectPropertyAtom` semantic gap.
- The `ObjectPropertyAtom` warning **does appear**, but only nested inside the `OBJ_GOLD_FAIL` row's `perLeg.csharp` detail (as a second `unsupported` row alongside the csharp leg's `failed` row for that object) and inside that row's combined `reason` string (which concatenates all differing legs' warnings). It is folded into a declared non-equivalence that is dominated by the three unavailable legs, not standing alone as "the" declared non-equivalence the checkpoint described.
- `status_tally_by_leg.csharp` does show `unsupported: 1` (confirming the csharp leg itself correctly typed the `ObjectPropertyAtom` case), but the cross-leg **comparison** did not surface it as an isolated non-equivalence in this run, because three of the four legs were unavailable and their `error` status is what actually drove each row's classification to `declared_non_equivalence`.

This SUMMARY records the actual report state accurately rather than repeating the prior agent's framing. The underlying code (per Task 2's `compare_legs` acceptance criteria and its unit tests, which run with synthetic `LegResult` objects independent of live services) is still correctly proven to classify an `unsupported`-plus-warning difference as declared rather than silent — that guarantee does not depend on this particular live run's leg availability.

### No auto-fixed issues

Tasks 1-3 were executed and verified by the prior agent and the orchestrator (8 key files exist, 3 commits present, 12 unit tests pass, both report files produced) before this continuation began. No Rule 1/2/3 auto-fixes were needed on this continuation — Task 4 required only recording the owner's decision.

## Outstanding: Live Four-Leg Run

**Status: NOT demonstrated in this environment.** The plan's `<verification>` block calls for "a full DE-01 run against the live stack ... four legs recorded" with agreement/typed-divergence across all four. The actual `.de01/de01-report.json` generated during Task 2 shows:

- `silent_disagreement_count == 0` (the hard gate — holds).
- `status_tally_by_leg`: `csharp = {no_population: 1, failed: 1, unsupported: 1, passed: 1}` (all 3 fixture objects correctly typed, including `OBJ_GOLD_EMPTY` reading `no_population` and never `failed` — the contract's central deliverable, holding on the one leg that ran); `data-service = {error: 3}`; `dg-reasoner = {error: 3}`; `replay = {error: 3}`.
- Every leg's `available` flag is `false` except `csharp`, each recording a typed "connection error: timed out" — because **Docker Desktop's daemon is not running in this environment**, a blocker first disclosed in 1200-02 and persisting through 1200-03, 1200-04, and this plan.

This means: the comparison logic (`compare_legs`) is proven correct by infrastructure-independent unit tests (12/12 passing with synthetic `LegResult`s), and the one leg that could run emits provably correct semantics — but **four legs actually agreeing (or typedly diverging) on the same live fixture has not been demonstrated**, because three of the four legs never got to run at all.

This is recorded as coverage item **D5** above with `human_judgment: true`, and should surface as an outstanding UAT/verification item for Phase 1200 — it is the one thing this phase promised (ALGN12-04: "DE-01 compares Python, dg-reasoner, C#, and persisted replay against the same fixture") that the environment prevented fully demonstrating.

**Commands a human should run once Docker Desktop is up, in order:**

```bash
docker compose up -d
# apply the golden fixture seed (idempotent, per fixtures/golden/seed.cypher's own header):
cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f fixtures/golden/seed.cypher
# re-run DE-01 against the now-live stack:
python tools/de01/run_de01.py --fixture fixtures/golden/fixture.json --out-dir .de01
```

Expected on success: `.de01/de01-report.json` and `.de01/de01-report.md` regenerated with all 4 legs `available: true` (or a subset intentionally stopped per the plan's own degrade-gracefully acceptance criterion), `silent_disagreement_count == 0`, and the `ObjectPropertyAtom` declared non-equivalence appearing cleanly against real (not timed-out) data-service/dg-reasoner/replay statuses rather than being masked by three unavailable legs.

## Issues Encountered

- Docker Desktop unavailable in this execution environment (disclosed blocker, carried from 1200-02) — prevented live data-service, dg-reasoner, and replay leg execution during Task 2's live run. Documented above rather than worked around; the runner's typed-degradation behavior (T-1200-25) is itself evidence this was handled correctly at the code level.

## User Setup Required

None - no external service configuration required beyond the outstanding Docker Desktop startup noted above.

## Next Phase Readiness

- The status vocabulary and evidence envelope contract (`spec/EVIDENCE-CONTRACT.md` §1, §3, §10) are owner-approved and frozen. Phases 1201-1205 and v11.0 Phase 1105 can proceed against them.
- Phase 1201 (ALGN12-05/ALGN12-06) has a concrete, evidence-backed starting point: `SwrlRuleParser.ResolveAtomType` needs an `ObjectPropertyAtom` branch, and `RuleEvaluator.cs`'s zero-binding/no-result collapse-to-`false` behaviors need the `no_population`/`not_evaluated` split this contract defines.
- **Blocker carried forward:** the live four-leg DE-01 run should be re-executed once Docker Desktop is available, to confirm the `ObjectPropertyAtom` declared non-equivalence and cross-service agreement hold when all four legs are actually reachable — not just typed-degraded. This does not block Phase 1200's completion (the owner approved the contract on the evidence available), but it is open work, not silently resolved.

---
*Phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt*
*Completed: 2026-09-20*
