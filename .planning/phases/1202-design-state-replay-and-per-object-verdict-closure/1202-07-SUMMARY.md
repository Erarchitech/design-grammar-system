---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 07
subsystem: database
tags: [de01, canonical-state-hash, cross-service-evidence, data-service, python]

requires:
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 02)
    provides: design_state_projection.compute_state_hash, the canonical DesignState projection this plan surfaces through the view endpoint
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 04)
    provides: the per-object verdict read path (evidenceEnvelopeJson) DE-01's existing comparison_rows dimension already exercises
  - phase: 1202-design-state-replay-and-per-object-verdict-closure (plan 05)
    provides: spec/DATABASE.md's canonicalStateHash property bullet this plan's app.py change fulfills
provides:
  - build_view_payload (data-service/app.py) computing and returning canonicalStateHash/canonicalizationVersion, degrading to None + logged warning on a malformed stored payload
  - LegResult.state_hash (additive, default None) and run_leg_replay populating it from the view response
  - report.compare_state_hashes -- the second DE-01 comparison dimension (agree/disagree/not_applicable), mirroring compare_legs' typed-absence idiom
  - run_de01.py wiring the new section into both reports, folding a "disagree" verdict into the existing silent_disagreement_count without adding a new exit path
  - report_schema.json's state_hash_comparison section
  - 18 new offline tests in test_de01_runner.py (32 -> 50 passing under -k "not live")
affects: []

tech-stack:
  added: []
  patterns:
    - "Second, independent comparison dimension attached to ComparisonResult as a defaulted field, computed by its own function and folded into the shared silent_disagreement_count counter at the call site -- never merged into compare_legs' own per-(rule,object) row walk"
    - "Typed-absence idiom ({'present': False, 'reason': ...}) reused verbatim for a second axis (state hash) rather than inventing a parallel convention"

key-files:
  created: []
  modified:
    - data-service/app.py
    - tools/de01/legs.py
    - tools/de01/report.py
    - tools/de01/report_schema.json
    - tools/de01/run_de01.py
    - tools/de01/tests/test_de01_runner.py

key-decisions:
  - "run_leg_csharp's state_hash stays None: DG.De01Harness's envelope carries no canonicalStateHash field today (confirmed by reading legs.py:602-741 -- only evidence envelope fields are parsed from its stdout JSON), so only run_leg_replay populates the field, exactly as the plan's conditional instruction anticipated."
  - "compare_state_hashes' agreement verdict ('agree'/'disagree'/'not_applicable') is computed independently of compare_legs' own per-row classification and folded into ComparisonResult.silent_disagreement_count at the run_de01.py call site, not inside compare_state_hashes itself -- keeps compare_legs' own documented invariant (T-1200-23, 'the single place a cross-leg difference could be silently lost') scoped to what it already owns, per the plan's explicit 'do not change the exit-code rule' instruction."
  - "state_hash_comparison was NOT added to report_schema.json's top-level 'required' array -- it is additive/optional so a pre-existing report (or an offline report with only one leg, before this plan) stays schema-valid; the section's own internal shape is still fully typed via nested 'required': ['present']."

requirements-completed: []

coverage:
  - id: D1
    description: "build_view_payload exposes canonicalStateHash/canonicalizationVersion, degrading to None+logged-warning on a malformed statePayloadJson rather than failing the view response"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "python -m pytest data-service/tests -q -- 819 passed, 4 pre-existing host-env failures, 25 pre-existing Neo4j-integration errors (unchanged baseline)"
        status: pass
    human_judgment: false
  - id: D2
    description: "run_leg_replay surfaces the canonical state hash onto LegResult.state_hash with typed absence when the view reports none; compare_state_hashes adds the second comparison dimension with agree/disagree/not_applicable verdicts and an optional fixture-expected-hash match, mirroring compare_legs' typed-absence idiom"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "python -m pytest tools/de01/tests/test_de01_runner.py -q -k \"not live\" -- 50 passed (32 baseline + 18 new)"
        status: pass
    human_judgment: false
  - id: D3
    description: "run_de01.py wires the new section into both reports; a state-hash 'disagree' folds into the existing silent_disagreement_count, 'not_applicable' does not, and no new differently-conditioned exit path was added"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "TestStateHashDisagreementFoldedIntoSilentDisagreementCount (test_de01_runner.py) -- both branches asserted directly against the shared counter"
        status: pass
      - kind: other
        ref: "Direct read of run_de01.py's exit path (lines 80-149): single return statement `return 1 if comparison.silent_disagreement_count > 0 else 0`, no new sys.exit/return added"
        status: pass
    human_judgment: false
  - id: D4
    description: "The live four-leg run and human checkpoint (Tasks 2-3) -- NOT part of this dispatch"
    verification: []
    human_judgment: true
    rationale: "Docker Desktop was down at research time; the orchestrator is coordinating bringing it up and dispatching a continuation agent for Tasks 2-3 separately. This deliverable is intentionally unstarted in this SUMMARY."

duration: ~35min (Task 1 only)
completed: 2026-09-22
status: in_progress
---

# Phase 1202 Plan 07: DE-01 Canonical State Hash Comparison Dimension Summary (Task 1 of 3 — PARTIAL)

**Task 1 only: build_view_payload now surfaces canonicalStateHash/canonicalizationVersion, and DE-01 gained a second comparison dimension (compare_state_hashes) alongside the existing per-object row comparison. Tasks 2 (Docker rebuild) and 3 (live four-leg run + human checkpoint) are PENDING — orchestrator is coordinating Docker Desktop separately and will dispatch a continuation agent.**

## STATUS: IN PROGRESS -- Tasks 2 and 3 not yet executed

This SUMMARY documents Task 1's completion only. Do not treat this phase/plan as
done. Tasks 2 (bring up Docker Desktop, `--no-cache` rebuild of `data-service`,
in-container code verification) and 3 (the live four-leg DE-01 run plus the
blocking human checkpoint that grades it) remain to be executed by a
continuation agent once Docker Desktop is confirmed up. STATE.md and
ROADMAP.md have deliberately NOT been touched by this dispatch — the
orchestrator owns those updates centrally once all three tasks are complete.

## Performance

- **Duration:** ~35 min (Task 1 only)
- **Started:** 2026-09-22 (session start, first Read)
- **Completed (Task 1 only):** 2026-09-22
- **Tasks:** 1/3 completed (Task 1 only; this is a deliberate partial dispatch)
- **Files modified:** 6

## Accomplishments (Task 1)

- `data-service/app.py`: added `_compute_canonical_state_hash` (computes the run's canonical DesignState hash from its persisted `statePayloadJson` via `design_state_projection.compute_state_hash`, degrading to `None` + a logged warning on malformed JSON or a projection/hash failure) and wired it into `build_view_payload`'s returned dict under `canonicalStateHash`/`canonicalizationVersion`, following the file's existing absence convention (explicit `None`, never an omitted key — same pattern as `shaclReport`/`evidenceEnvelope` above it).
- `tools/de01/legs.py`: added an additive `LegResult.state_hash` field (default `None`, so every existing constructor across the codebase keeps working unchanged) and populated it in `run_leg_replay` from the view response's `canonicalStateHash`/`canonicalizationVersion`, independent of envelope schema validation (a hash can be present even if the envelope fails validation, and vice versa). `run_leg_data_service`/`run_leg_dg_reasoner` are untouched — they evaluate the rule fixture and capture no Design State (Open Question 2's resolution, documented in the field's own docstring). `run_leg_csharp` was checked (read in full, lines 602-741) and confirmed to carry no state-hash field in `DG.De01Harness`'s stdout envelope today, so it also stays `None`.
- `tools/de01/report.py`: added `compare_state_hashes(leg_results, expected_canonical_state_hash=None) -> dict`, mirroring `compare_legs`' `{"present": False}` typed-absence idiom exactly. Produces per-leg entries of `{"present": True, "hash", "canonicalizationVersion", "expected_match"}` or `{"present": False, "reason"}`, plus a top-level `agreement` verdict (`agree`/`disagree`/`not_applicable`) computed only over legs that reported a hash — a non-participating leg's absence never counts toward disagreement. `ComparisonResult` gained a defaulted `state_hash_comparison` field. Both `emit_json_report` and `emit_markdown_report` were extended with the new section.
- `tools/de01/run_de01.py`: wired `compare_state_hashes` into `main()`, reading `expectedCanonicalStateHash` from the fixture when supplied. A `"disagree"` verdict increments the existing `silent_disagreement_count` (documented in-line as a deliberate fold, not a new gate); `"not_applicable"` does not. Verified by direct reading that the exit path still has exactly one `return 1 if comparison.silent_disagreement_count > 0 else 0` — no new differently-conditioned exit was added.
- `tools/de01/report_schema.json`: added the `state_hash_comparison` object (not added to the top-level `required` array, so pre-existing/older reports stay schema-valid) with its own nested `required: ["present"]` typing, plus a description explicitly naming `canonicalStateHash` as the field's data-service origin (satisfies the plan's acceptance-criteria grep).
- `tools/de01/tests/test_de01_runner.py`: added 18 new offline tests across 6 new test classes — `TestRunLegReplayStateHash` (4), `TestLegResultStateHashDefault` (2), `TestCompareStateHashes` (8), `TestStateHashDisagreementFoldedIntoSilentDisagreementCount` (2), `TestReportJsonValidatesAgainstSchemaWithStateHashSection` (2). All mock `legs.httpx.Client` the same way the existing `run_leg_dg_reasoner` tests do — no live-service dependency introduced into the `-k "not live"` subset.

## Task Commits

1. **Task 1: Surface the canonical state hash from the replay leg and add the comparison dimension** - `5aa58c5` (feat)

Tasks 2 and 3 not started. No plan-metadata commit — this is an intentionally partial dispatch; the orchestrator will commit the final plan-metadata update once all three tasks are complete.

## Files Created/Modified

- `data-service/app.py` - `_compute_canonical_state_hash` helper + `build_view_payload` wiring; new imports `design_state_projection`, `canonical_json`.
- `tools/de01/legs.py` - `LegResult.state_hash` additive field; `run_leg_replay` populates it from the view response.
- `tools/de01/report.py` - `compare_state_hashes`; `ComparisonResult.state_hash_comparison`; both report emitters extended.
- `tools/de01/report_schema.json` - `state_hash_comparison` section.
- `tools/de01/run_de01.py` - wires `compare_state_hashes` into `main()`; folds `"disagree"` into `silent_disagreement_count`.
- `tools/de01/tests/test_de01_runner.py` - 18 new offline tests.

## Decisions Made

- `run_leg_csharp`'s `state_hash` stays `None`: read the harness adapter in full (legs.py:602-741) and confirmed `DG.De01Harness`'s stdout JSON carries no state-hash field today — only `run_leg_replay` populates the field, exactly as the plan's conditional ("if the C# harness makes a Design State hash available") anticipated.
- `compare_state_hashes`'s `agree`/`disagree`/`not_applicable` verdict is computed independently of `compare_legs`' own per-row classification and folded into `silent_disagreement_count` at the `run_de01.py` call site (not inside `compare_state_hashes` itself), preserving `compare_legs`' own T-1200-23 invariant scope and honoring the plan's explicit "do not change the exit-code rule" instruction.
- `state_hash_comparison` was deliberately NOT added to `report_schema.json`'s top-level `required` array, so a report without it (or an older report format) remains schema-valid; its own internal shape is still fully typed.

## Deviations from Plan

None — plan executed exactly as written for Task 1. `run_leg_csharp` was checked per the plan's own read_first instruction and confirmed not to require a change (no state hash available from the harness today).

## Issues Encountered

None. All acceptance-criteria greps for Task 1 pass:
- `grep -c 'compare_state_hashes' tools/de01/report.py tools/de01/run_de01.py` -> 1, 1
- `grep -c '"present"' tools/de01/report.py` -> 14 (>= 2 required)
- `grep -c 'canonicalStateHash' tools/de01/legs.py tools/de01/report_schema.json` -> 2, 1
- `grep -c 'silent_disagreement_count' tools/de01/run_de01.py` -> 5 (>= 1 required); exit path read directly, no new sys.exit/return added
- `python -m pytest data-service/tests -q` -> 819 passed, 4 pre-existing failed, 25 pre-existing errors (unchanged baseline, no regression)
- `python -m pytest tools/de01/tests/test_de01_runner.py -q -k "not live"` -> 50 passed (32 baseline + 18 new), 1 deselected (the live wrapper)

## User Setup Required

None for Task 1. Tasks 2-3 require Docker Desktop to be running (confirmed down at research time, 2026-09-21) — the orchestrator is bringing it up separately before dispatching a continuation agent.

## Next Phase Readiness (for the Task 2-3 continuation agent)

- Task 1's code changes are committed (`5aa58c5`) and fully tested offline. `run_leg_replay` is ready to read a real `canonicalStateHash` from a live data-service once Task 2's rebuild lands.
- Task 2 must rebuild `data-service` `--no-cache` (it has no source volume mount — a bare restart would validate pre-change code, the 1200-08/38-06 precedent). The in-container verification should also confirm this plan's `_compute_canonical_state_hash`/`canonicalStateHash` addition is present in the deployed `app.py`, alongside the plan 05 markers Task 2's own read_first already names.
- Task 3's live run should exercise `fixtures/golden/replay/mixed-verdicts.json`'s `expectedCanonicalStateHash` (`3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428`) if that fixture (rather than the frozen `fixtures/golden/fixture.json`, which carries no `expectedCanonicalStateHash` field) is the one driven through `run_de01.py --fixture`. Note plan 02's documented caveat: the C# leg's hash currently diverges from this expected value pending D-05's `ClassIri` round-trip fix — the state-hash `agreement` verdict across `replay` vs `csharp` may legitimately show `disagree` until that lands; this is a known, already-documented condition, not a new finding.
- No blocker for Task 2/3 from this dispatch's changes — zero file overlap with what Task 2/3 need to read (Task 2 only reads, does not modify, `tools/de01/tests/test_de01_runner.py`'s live wrapper; Task 3 only writes `.de01/de01-report.json`/`.de01/de01-report.md`, files this dispatch does not touch).

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Task 1 completed: 2026-09-22 — Tasks 2-3 PENDING*

## Self-Check: PASSED

All modified files verified present on disk:
- FOUND: data-service/app.py (modified)
- FOUND: tools/de01/legs.py (modified)
- FOUND: tools/de01/report.py (modified)
- FOUND: tools/de01/report_schema.json (modified)
- FOUND: tools/de01/run_de01.py (modified)
- FOUND: tools/de01/tests/test_de01_runner.py (modified)

Commit hash verified in git log: 5aa58c5.
