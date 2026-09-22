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
    description: "The live four-leg run and human checkpoint (Tasks 2-3)"
    requirement: "ALGN12-09, ALGN12-10"
    verification:
      - kind: manual
        ref: "Live pytest (tools/de01/tests/test_de01_runner.py, no -k filter) -- 51 passed. Live run_de01.py -- exit 0, silent_disagreement_count=0. Report pair retained at de01-evidence/. User responded 'approved' to the Task 3 checkpoint."
        status: pass
    human_judgment: true
    rationale: "D-16 makes this run a gate definition -- the executor cannot self-grade it. The orchestrator ran Task 2 (Docker rebuild) and Task 3 (live DE-01 run) directly, presented the full checkpoint per the plan's <how-to-verify> steps, and the user approved."

duration: ~35min (Task 1) + Docker rebuild and live run (Tasks 2-3, orchestrator-executed)
completed: 2026-09-22
status: complete
---

# Phase 1202 Plan 07: DE-01 Canonical State Hash Comparison Dimension Summary

**build_view_payload now surfaces canonicalStateHash/canonicalizationVersion; DE-01 gained a second comparison dimension (compare_state_hashes) alongside the existing per-object row comparison; the stack was rebuilt `--no-cache` and proven to hold post-phase code; and the live four-leg DE-01 run was executed against the rebuilt stack as this phase's exit evidence (D-16), with `silent_disagreement_count == 0` and user approval.**

## STATUS: COMPLETE -- all 3 tasks executed

Task 1 (code: canonical state hash surfacing + comparison dimension) was executed
and committed by the plan's primary executor. Tasks 2 (Docker Desktop rebuild) and
3 (live four-leg DE-01 run + blocking human checkpoint) were executed directly by
the orchestrator (not a subagent, since they require imperative Docker/CLI control
outside a sandboxed dispatch) once Docker Desktop was confirmed up. The Task 3
checkpoint was presented to the user in full and approved.

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

## Accomplishments (Tasks 2-3, orchestrator-executed)

### Task 2: Rebuild the stack so the live run exercises post-phase code

1. Confirmed Docker Desktop process was running; polled `docker compose ps` until the engine pipe responded (~20s) -- an earlier stale check had caught the pipe mid-restart.
2. Ran `docker compose up -d` -- all 15 services came up: `data-service`, `neo4j`, `n8n`, `design-grammars`, `dg-reasoner`, `ollama`, and 9 `speckle-*` containers. They had actually been running for 43 minutes already at that point.
3. Ran `docker compose build --no-cache data-service` -- build succeeded cleanly (BuildKit output, final line: `design-grammar-system-data-service Built`).
4. Ran `docker compose up -d data-service` -- container recreated with the fresh image.
5. Proved the running container holds post-phase code via `MSYS_NO_PATHCONV=1 docker exec data-service grep -c "<marker>" /app/app.py`:
   - `ON CREATE SET` (plan 05 Task 1) -> 4 matches
   - `canonicalStateHash` (plan 07 Task 1) -> 1 match
   - `ROLLUP_PRECEDENCE` (plan 05 Task 2) -> 2 matches
6. Confirmed `data-service` (`curl http://localhost:8000/` -> 200) and `neo4j` (`curl http://localhost:7474/` -> 200) both healthy.
7. Confirmed the golden project `DG-1200-GOLDEN` was already seeded (13 ValidationRuns, 4 DesignStates, etc., verified via a Cypher query against Neo4j using the docker-compose.yml-declared dev credential `neo4j/12345678`) -- no `seed.cypher` re-application was needed since the data pre-existed.

**Acceptance criteria met:** `docker compose ps` listed `data-service`/`neo4j` running; the in-container `ON CREATE SET` grep matched; the `--no-cache` build completed in this session with a recorded final line; the health-check curls both returned success.

### Task 3: Live four-leg DE-01 run as exit evidence (D-16)

1. Ran `python -m pytest tools/de01/tests/test_de01_runner.py -q` (no `-k` filter) -> **51 passed** (50 offline + 1 live wrapper).
2. Ran `python tools/de01/run_de01.py` against the rebuilt stack -> **exit 0**, stdout:
   ```
   DE-01: reports written to .de01/de01-report.json and .de01/de01-report.md
   DE-01: silent_disagreement_count = 0
   DE-01: canonical state hash agreement = not_applicable
   DE-01: available legs = ['data-service', 'dg-reasoner', 'csharp', 'replay']
   ```
3. Inspected `.de01/de01-report.md` in full (retained copy at `de01-evidence/de01-report.md`). Findings:
   - **Mixed per-object verdicts survive**: in the `replay` leg, OBJ_GOLD_PASS reports `passed` and OBJ_GOLD_FAIL reports `failed` -- genuinely different statuses, not collapsed into a run-level aggregate. ALGN12-10's closure criterion is met.
   - **Canonical state hash agreement = `not_applicable`**, and this was investigated and confirmed to be the CORRECT outcome, not a gap. All four legs report `{"present": False, "reason": "...does not capture or report a Design State (Open Question 2)..."}`. The live run drove the FROZEN `fixtures/golden/fixture.json` (`run_de01.py`'s default `--fixture` input), whose stub DesignState (per 1202-02's own SUMMARY finding) carries only bare `stateId` members with no `capturedAtUtc`/`objectRef` and cannot round-trip through `DesignStatePayloadV2Serializer`/`design_state_projection.compute_state_hash`. The golden project's stored run therefore genuinely has no `statePayloadJson`, and `canonicalStateHash` in the live `/validation/view/DG-1200-GOLDEN` response is correctly `None` (confirmed directly via `curl`: the key IS present, value is `None`) -- Task 1's absence convention works as designed. The cross-language hash-parity proof for this phase happened separately and successfully in plans 02/03 against the PURPOSE-BUILT `fixtures/golden/replay/mixed-verdicts.json` fixture (which has a round-trippable payload and a populated `expectedCanonicalStateHash`), but that fixture was never wired into `run_de01.py`'s CLI in this plan -- only used directly by C#/Python unit tests in plans 02/03/04. This is a known scope boundary, not a defect: Task 1's job was to build the comparison DIMENSION and wire the data-service response field, and its `<output>` section only asks to "record the state-hash agreement verdict," not to force a non-trivial one. A future phase could point `run_de01.py --fixture` at the replay fixture to get a non-`not_applicable` result.
   - **Every non-participating leg reports typed absence with a reason** -- confirmed for all 4 legs in the state-hash section (see table above/in the retained report).
   - **Pre-declared non-results still present**: the C# leg's `unsupported` row for `R_GOLD_HEIGHT_MAX_75_V_A4` (ObjectPropertyAtom) on OBJ_GOLD_FAIL, matching `fixtures/golden/MANIFEST.md`'s "expected non-results by design"; `no_population` for OBJ_GOLD_EMPTY.
   - **`silent_disagreement_count = 0`** -- notably BETTER than `tools/de01/README.md`'s own documented expectation of a pre-existing count of 1 (a dg-reasoner not_evaluated-vs-failed classification gap on OBJ_GOLD_FAIL was expected per the README's "Known, empirically-verified limit" section). This live run shows all divergences classified as `declared_non_equivalence`, not silent -- worth noting as a possibly-already-fixed condition from an earlier phase, or a nuance of how this run's data differs from the README's hypothetical. Not investigated further as out of this plan's scope.
4. Copied `.de01/de01-report.json` and `.de01/de01-report.md` into `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/` as retained exit evidence.
5. Presented the full checkpoint to the user with the what-built/how-to-verify breakdown from the plan's Task 3. **User responded: "approved."**

This satisfies Task 3's `<resume-signal>` and `<done>` condition: the live run completed with `silent_disagreement_count == 0`, the report pair is retained in the phase directory, and the user approved.

## Task Commits

1. **Task 1: Surface the canonical state hash from the replay leg and add the comparison dimension** - `5aa58c5` (feat)

Tasks 2-3 involved no source-code changes (Docker operations + a live CLI run); their evidence is the retained `de01-evidence/` report pair and this SUMMARY, committed alongside the plan-metadata update.

## Files Created/Modified

- `data-service/app.py` - `_compute_canonical_state_hash` helper + `build_view_payload` wiring; new imports `design_state_projection`, `canonical_json`.
- `tools/de01/legs.py` - `LegResult.state_hash` additive field; `run_leg_replay` populates it from the view response.
- `tools/de01/report.py` - `compare_state_hashes`; `ComparisonResult.state_hash_comparison`; both report emitters extended.
- `tools/de01/report_schema.json` - `state_hash_comparison` section.
- `tools/de01/run_de01.py` - wires `compare_state_hashes` into `main()`; folds `"disagree"` into `silent_disagreement_count`.
- `tools/de01/tests/test_de01_runner.py` - 18 new offline tests.
- `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.json` - retained live exit-evidence copy (Task 3).
- `.planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.md` - retained live exit-evidence copy (Task 3).

## Decisions Made

- `run_leg_csharp`'s `state_hash` stays `None`: read the harness adapter in full (legs.py:602-741) and confirmed `DG.De01Harness`'s stdout JSON carries no state-hash field today — only `run_leg_replay` populates the field, exactly as the plan's conditional ("if the C# harness makes a Design State hash available") anticipated.
- `compare_state_hashes`'s `agree`/`disagree`/`not_applicable` verdict is computed independently of `compare_legs`' own per-row classification and folded into `silent_disagreement_count` at the `run_de01.py` call site (not inside `compare_state_hashes` itself), preserving `compare_legs`' own T-1200-23 invariant scope and honoring the plan's explicit "do not change the exit-code rule" instruction.
- `state_hash_comparison` was deliberately NOT added to `report_schema.json`'s top-level `required` array, so a report without it (or an older report format) remains schema-valid; its own internal shape is still fully typed.
- The live run's `not_applicable` state-hash agreement verdict is accepted as the correct Task 3 outcome, not deferred or re-run against a different fixture: the plan's `<output>` section asks only to "record the state-hash agreement verdict," and the frozen `fixtures/golden/fixture.json` genuinely carries no round-trippable DesignState payload (a pre-existing, already-documented 1202-02 finding) — forcing a non-`not_applicable` result would have meant silently swapping the CLI's default fixture outside this plan's stated scope.
- Tasks 2-3 were executed directly by the orchestrator rather than dispatched to a subagent, since they require imperative control over the local Docker Desktop process and host-level CLI commands outside a sandboxed dispatch context.

## Deviations from Plan

None for Task 1 — plan executed exactly as written. `run_leg_csharp` was checked per the plan's own read_first instruction and confirmed not to require a change (no state hash available from the harness today).

None for Tasks 2-3 — the stack was rebuilt exactly per the plan's numbered steps, the live run was executed exactly as specified, and the `not_applicable` state-hash agreement verdict was investigated (see Decisions Made) and confirmed to be the correct outcome under the plan's own scope, not a deviation requiring a fix.

## Issues Encountered

None for Task 1. All acceptance-criteria greps pass:
- `grep -c 'compare_state_hashes' tools/de01/report.py tools/de01/run_de01.py` -> 1, 1
- `grep -c '"present"' tools/de01/report.py` -> 14 (>= 2 required)
- `grep -c 'canonicalStateHash' tools/de01/legs.py tools/de01/report_schema.json` -> 2, 1
- `grep -c 'silent_disagreement_count' tools/de01/run_de01.py` -> 5 (>= 1 required); exit path read directly, no new sys.exit/return added
- `python -m pytest data-service/tests -q` -> 819 passed, 4 pre-existing failed, 25 pre-existing errors (unchanged baseline, no regression)
- `python -m pytest tools/de01/tests/test_de01_runner.py -q -k "not live"` -> 50 passed (32 baseline + 18 new), 1 deselected (the live wrapper)

None for Tasks 2-3. All acceptance criteria and the human checkpoint passed on the first attempt:
- `docker compose ps` listed `data-service`/`neo4j` running.
- In-container marker greps (`ON CREATE SET` x4, `canonicalStateHash` x1, `ROLLUP_PRECEDENCE` x2) all matched.
- `docker compose build --no-cache data-service` completed with final line `design-grammar-system-data-service Built`.
- `curl http://localhost:8000/` and `curl http://localhost:7474/` both returned 200.
- Live pytest: 51 passed (no `-k` filter).
- `python tools/de01/run_de01.py` exited 0, `silent_disagreement_count = 0`.
- User checkpoint response: "approved."

## User Setup Required

None. Docker Desktop was confirmed running by the orchestrator before Task 2's rebuild steps; no manual user action was required beyond reviewing and approving the Task 3 checkpoint.

## Next Phase Readiness

- All three tasks are committed and complete. `run_leg_replay` reads a real `canonicalStateHash` from the live data-service (currently `None` against the frozen golden fixture, by design — see Decisions Made).
- The `fixtures/golden/replay/mixed-verdicts.json` fixture (with its populated `expectedCanonicalStateHash`) was never wired into `run_de01.py`'s CLI default in this plan — a future phase could point `run_de01.py --fixture` at it to exercise a non-`not_applicable` state-hash agreement verdict live, per plan 02's documented caveat that the C# leg's hash currently diverges from that fixture's expected value pending D-05's `ClassIri` round-trip fix.
- `tools/de01/README.md`'s documented expectation of a pre-existing `silent_disagreement_count` of 1 (dg-reasoner not_evaluated-vs-failed gap) did not reproduce in this live run (measured 0) — flagged as a possibly-already-fixed condition worth a follow-up look, not investigated further here as out of scope.
- No open blockers from this plan's work.

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Plan 07 completed: 2026-09-22 — all 3 tasks executed*

## Self-Check: PASSED

All modified/created files verified present on disk:
- FOUND: data-service/app.py (modified)
- FOUND: tools/de01/legs.py (modified)
- FOUND: tools/de01/report.py (modified)
- FOUND: tools/de01/report_schema.json (modified)
- FOUND: tools/de01/run_de01.py (modified)
- FOUND: tools/de01/tests/test_de01_runner.py (modified)
- FOUND: .planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.json (retained evidence)
- FOUND: .planning/phases/1202-design-state-replay-and-per-object-verdict-closure/de01-evidence/de01-report.md (retained evidence)

Commit hash verified in git log: 5aa58c5.
