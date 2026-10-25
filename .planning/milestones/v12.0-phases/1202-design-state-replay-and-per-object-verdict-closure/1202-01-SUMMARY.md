---
phase: 1202-design-state-replay-and-per-object-verdict-closure
plan: 01
subsystem: testing
tags: [xunit, pytest, evidence-contract, design-state, fixtures, tdd-red]

requires:
  - phase: 1200-cross-service-evidence-contract-freeze
    provides: EvidenceStatus/EvidenceEnvelope/StatusRollup.Precedence contracts, CanonicalJsonWriter
  - phase: 1201-swrl-subset-and-rollup-precedence-shipping
    provides: shipped rollup precedence (StatusRollup.Precedence), fixtures/golden/parser/ sibling-path precedent
provides:
  - RED xUnit Facts naming PerObjectVerdict/VerdictSource/PerObjectVerdictResult/BuildPerObjectVerdicts/GetEvidenceQueryForTesting for plan 04 to implement verbatim
  - RED pytest module proving today's ValidationRun publish path lacks an ON CREATE SET immutability split (D-15), for plan 05 to fix
  - fixtures/golden/replay/mixed-verdicts.json + README.md — a serializer-valid mixed pass/fail/no_population sibling fixture for plans 02/04/06
affects: [1202-02, 1202-03, 1202-04, 1202-05, 1202-06, 1202-07]

tech-stack:
  added: []
  patterns:
    - "Cypher-shape RED regression via write_query monkeypatch (capture emitted query text, assert clause placement by regex on ON CREATE SET vs plain SET, not substring scan)"
    - "Named exact-signature RED Facts as a GREEN contract for a later plan (plan 04 implements PerObjectVerdict/BuildPerObjectVerdicts verbatim against these Facts)"

key-files:
  created:
    - data-service/tests/test_validation_run_immutability.py
    - fixtures/golden/replay/mixed-verdicts.json
    - fixtures/golden/replay/README.md
  modified:
    - DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs

key-decisions:
  - "Task 1 RED state is a whole-assembly compile failure (CS0117), not a runtime test failure — DG.Tests cannot build at all until plan 04 lands. This is the plan's own documented expected outcome, not a defect."
  - "Task 2 stubs Neo4j by monkeypatching app.write_query and calling app.store_validation_run directly, since test_validation_runs_state.py (the nearest analog) tests pure projection functions and has no write_query stubbing convention of its own to copy."
  - "mixed-verdicts.json reuses OBJ_GOLD_PASS/OBJ_GOLD_FAIL/OBJ_GOLD_EMPTY and R_GOLD_HEIGHT_MAX_75_V verbatim from the frozen fixture.json rather than inventing new ids, per D-17."
  - "expectedCanonicalStateHash left null with an explanatory note — plan 02 fills it in once the D-01/D-02 hasher extension exists; a placeholder value would be fabricated."

patterns-established:
  - "Sibling fixture path under fixtures/golden/replay/ mirrors the fixtures/golden/parser/ precedent (1201 D-16): frozen fixture.json/seed.cypher/canonical-vectors.json stay byte-identical, new material lives in its own subdirectory with its own lighter change-reason log."

requirements-completed: [ALGN12-09, ALGN12-10, ALGN12-11]

coverage:
  - id: D1
    description: "RED xUnit coverage for the additive per-object verdict read path (PerObjectVerdict/VerdictSource/PerObjectVerdictResult/BuildPerObjectVerdicts/GetEvidenceQueryForTesting) exists and fails to compile today, naming the missing symbols"
    requirement: "ALGN12-10"
    verification:
      - kind: unit
        ref: "dotnet test DG/tests/DG.Tests/ -v minimal (expected CS0117 on BuildPerObjectVerdicts/GetEvidenceQueryForTesting)"
        status: pass
    human_judgment: false
  - id: D2
    description: "RED pytest proving re-publishing a validation run does not yet write rulesJson/statePayloadJson/createdAt via ON CREATE SET (they land in the unconditional SET clause instead)"
    requirement: "ALGN12-11"
    verification:
      - kind: unit
        ref: "python -m pytest data-service/tests/test_validation_run_immutability.py -q (2 of 4 fail as expected: immutable-fields-on-create-only, republish-preserves-created-at)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mixed pass/fail/no_population replay fixture exists at fixtures/golden/replay/mixed-verdicts.json, serializer-shaped, non-canonically ordered, reusing frozen fixture object/rule ids, with frozen trio untouched"
    requirement: "ALGN12-09"
    verification:
      - kind: unit
        ref: "python -c one-liner validating version/objectRef set/non-canonical order/README existence (plan's own <verify> command)"
        status: pass
      - kind: other
        ref: "git status --porcelain fixtures/golden/fixture.json fixtures/golden/seed.cypher fixtures/golden/canonical-vectors.json (empty output)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-21
status: complete
---

# Phase 1202 Plan 01: Wave 0 RED Test/Fixture Contracts Summary

**Landed three RED artifacts (a non-compiling xUnit test region, a failing pytest immutability regression, and a new sibling replay fixture) that give waves 1-3 an automated GREEN target instead of an invented one.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-21T21:51:00Z (approx, first Read)
- **Completed:** 2026-09-21T22:46:31Z
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 modified, 3 created)

## Accomplishments

- Added 8 new xUnit Facts (5 active + 1 skipped placeholder, plus supporting helper) to `Neo4jValidGraphRepositoryTests.cs` naming the exact symbols (`PerObjectVerdict`, `VerdictSource`, `PerObjectVerdictResult`, `Neo4jValidGraphRepository.BuildPerObjectVerdicts`, `Neo4jValidGraphRepository.GetEvidenceQueryForTesting`) that plan 04 must implement verbatim; the whole `DG.Tests` assembly fails to build on these missing symbols today — the documented Wave 0 RED state.
- Added `data-service/tests/test_validation_run_immutability.py` (4 tests) that monkeypatches `app.write_query` to capture the Cypher `store_validation_run` emits, and asserts `rulesJson`/`statePayloadJson`/`createdAt` belong in an `ON CREATE SET` clause while `status`/`ValidStatus`/`SendStatus` stay in the unconditional `SET` clause. 2 of 4 fail today exactly as expected (no `ON CREATE SET` clause exists yet); the mutable-fields and disjoint-sets tests already pass since today's single `SET` clause does correctly write the mutable fields.
- Added `fixtures/golden/replay/mixed-verdicts.json` + `README.md`: a new sibling fixture reusing `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`/`OBJ_GOLD_EMPTY`/`R_GOLD_HEIGHT_MAX_75_V` from the frozen `fixture.json`, carrying a serializer-valid v2 `statePayloadJson` (non-canonically ordered `objStates`, a `paramStates` entry with a real parameter, a `propStates` entry, `classIri` on every ObjState per D-05), mixed `expectedPerObjectVerdicts` (`passed`/`failed`/`no_population`), and a contract-valid `evidenceEnvelopeJson` producing the same three verdicts.
- Verified the frozen `fixtures/golden/fixture.json`, `seed.cypher`, and `canonical-vectors.json` remain byte-identical (`git status --porcelain` empty for all three) — D-17 honored.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RED xUnit coverage for the additive per-object verdict read path (D-13/D-14)** - `55394fb` (test)
2. **Task 2: Add RED pytest regression proving re-publish must not overwrite immutable snapshot fields (D-15)** - `0b417e2` (test)
3. **Task 3: Build the mixed pass/fail per-object replay fixture at a sibling path (D-17)** - `f08df38` (test)

_No plan-metadata commit created by this executor — orchestrator owns STATE.md/ROADMAP.md updates centrally for this wave per the sequential-mode contract._

## Files Created/Modified

- `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs` - Appended a RED test region (5 active Facts + 1 skipped placeholder + a private envelope-JSON builder helper) naming the additive per-object verdict API plan 04 implements; insertions-only diff, no existing Fact touched.
- `data-service/tests/test_validation_run_immutability.py` - New pytest module: 4 tests, a `write_query` monkeypatch fixture, a Cypher clause-splitting helper (`ON CREATE SET` vs plain `SET` via regex, not substring scan), and the `IMMUTABLE_PROPERTIES`/`MUTABLE_PROPERTIES` module-level contract constants.
- `fixtures/golden/replay/mixed-verdicts.json` - New sibling fixture: mixed pass/fail/no_population per-object replay case built from the frozen fixture's object/rule ids.
- `fixtures/golden/replay/README.md` - New fixture doc explaining the sibling-path framing, id-reuse rationale, why the frozen stub can't round-trip, and the null `expectedCanonicalStateHash` placeholder.

## Decisions Made

- Task 1's RED state manifests as a whole-assembly `CS0117` compile failure rather than an individual failing test — this is inherent to referencing not-yet-existing types/methods in C#, and the plan's own `<verification>` section explicitly names this as the expected, non-failing Wave 0 outcome (documented, not a defect of this plan).
- Task 2 could not literally copy `test_validation_runs_state.py`'s stubbing convention because that module tests pure projection functions (`_project_state_summary`, `_format_prop_value`, `_project_prop_states`) that never call `write_query` at all. Per the plan's own fallback instruction ("If that module talks to a real driver, instead capture the emitted Cypher string by monkeypatching the module-level `write_query`"), the test drives `app.store_validation_run` directly with a monkeypatched `write_query`, capturing `(cypher, parameters)` pairs — a legitimate substitute per the plan text itself, not a deviation.
- The `RunsQuery_ShouldNotFabricateAPerObjectStatusList` Fact (item 6 in the plan's Task 1 list) is marked `[Fact(Skip=...)]` per the plan's own explicit fallback clause ("if it is not [reachable via an internal static seam], mark this Fact Skip... and convert it to an active Fact in plan 04") — no `internal static` seam exists today that exposes a per-run `StatusList` for a synthetic multi-ObjState state without a live Neo4j session.

## Deviations from Plan

None - plan executed exactly as written. The Task 1 skip and Task 2 stubbing-convention substitution above are both explicitly pre-authorized by the plan's own text, not ad hoc deviations.

## RED Failure Output (recorded verbatim per plan's `<output>` instruction)

### Task 1 — `dotnet test DG/tests/DG.Tests/ -v minimal` (excerpt)

```
DG\tests\DG.Tests\Neo4jValidGraphRepositoryTests.cs(241,48): error CS0117: "Neo4jValidGraphRepository" не содержит определение для "BuildPerObjectVerdicts". [DG.Tests.csproj]
DG\tests\DG.Tests\Neo4jValidGraphRepositoryTests.cs(264,48): error CS0117: "Neo4jValidGraphRepository" не содержит определение для "BuildPerObjectVerdicts". [DG.Tests.csproj]
DG\tests\DG.Tests\Neo4jValidGraphRepositoryTests.cs(276,48): error CS0117: "Neo4jValidGraphRepository" не содержит определение для "BuildPerObjectVerdicts". [DG.Tests.csproj]
DG\tests\DG.Tests\Neo4jValidGraphRepositoryTests.cs(287,48): error CS0117: "Neo4jValidGraphRepository" не содержит определение для "BuildPerObjectVerdicts". [DG.Tests.csproj]
DG\tests\DG.Tests\Neo4jValidGraphRepositoryTests.cs(296,47): error CS0117: "Neo4jValidGraphRepository" не содержит определение для "GetEvidenceQueryForTesting". [DG.Tests.csproj]
```
(`CS0117` = "does not contain a definition for". The whole assembly fails to build; no test in `DG.Tests` — including the pre-existing 502-test baseline — can currently run. This blocks the entire suite, not just the new Facts, until plan 04 lands.)

### Task 2 — `python -m pytest data-service/tests/test_validation_run_immutability.py -q`

```
FAILED data-service/tests/test_validation_run_immutability.py::test_publish_cypher_writes_immutable_snapshot_fields_on_create_only
  AssertionError: Expected 'createdAt' to appear in an ON CREATE SET clause (write-once
  snapshot identity, D-15), but it was not found there. on_create_props=set()
  plain_props={'status', 'modelViewerUrl', 'baseVersionId', 'validationResourceUrl',
  'validationModelId', 'rulesJson', 'baseModelId', 'speckleProjectId',
  'validationVersionId', 'createdAt', 'statePayloadJson', 'ValidStatus',
  'baseResourceUrl', 'SendStatus'}
  cypher="\n        MERGE (run:ValidationRun {graph:$graph, project:$project, runId:$runId})\n
  SET\n            run.speckleProjectId = $speckleProjectId,\n ... run.rulesJson =
  $rulesJson,\n            run.statePayloadJson = $statePayloadJson,\n
  run.status = 'completed',\n            run.ValidStatus = $validStatus,\n
  run.SendStatus = true,\n            run.createdAt = $createdAt\n        "

FAILED data-service/tests/test_validation_run_immutability.py::test_republish_same_run_id_preserves_original_created_at
  AssertionError: createdAt must be placed in an ON CREATE SET clause so MERGE's own
  semantics (fires only when the node is first created) preserve the original value
  across a re-publish with the same runId ...

2 failed, 2 passed in 5.28s
```
(The 2 passes are `test_publish_cypher_writes_mutable_status_fields_on_every_write` — already correct today since the mutable fields do live in the sole `SET` clause — and `test_immutable_and_mutable_property_sets_are_disjoint`'s constant-disjointness half, which is a static property of the two Python `set` literals independent of `app.py`'s current Cypher.)

## Baseline Regression Check

- `python -m pytest data-service/tests -q`: 797 passed, 1 skipped, 8 deselected, 6 failed, 25 errors. Of the 6 failures: 2 are this plan's intentional new RED (`test_validation_run_immutability.py`), 4 are the pre-existing, documented `test_dg_context.py` host-environment failures (`DG_OBSIDIAN`/`1202-CONTEXT.md` code_context table: "4 `test_dg_context.py` tests fail from the host — the `neo4j` hostname resolves only inside compose"). The 25 errors are all in `test_cg_structure_checks.py`/`test_computgraph_consult.py`, both pre-existing Neo4j-dependent integration suites requiring the compose stack — not touched by this plan and not new. No regression beyond the 2 intentional RED failures.
- `dotnet test DG/tests/DG.Tests/ -v minimal`: whole-assembly compile failure (documented above) — this is Wave 0's own designed outcome per the plan's `<verification>` section, not a regression against the 502-test baseline (that baseline is temporarily unreachable by design until plan 04 lands).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 has an exact GREEN target: implement `PerObjectVerdict`, `VerdictSource`, `PerObjectVerdictResult`, `Neo4jValidGraphRepository.BuildPerObjectVerdicts`, and `Neo4jValidGraphRepository.GetEvidenceQueryForTesting` against the Facts in this commit; the skipped `RunsQuery_ShouldNotFabricateAPerObjectStatusList` Fact should be converted to active once plan 04's read path exists.
- Plan 05 has an exact GREEN target: split `store_validation_run`'s single `SET` clause into `ON CREATE SET` (immutable) + `SET` (mutable) per the `IMMUTABLE_PROPERTIES`/`MUTABLE_PROPERTIES` constants this plan defines.
- Plan 02 should fill in `expectedCanonicalStateHash` in `fixtures/golden/replay/mixed-verdicts.json` once the D-01/D-02 canonical projection + hasher extension exists.
- Plan 06 (DE-01 extension, D-16) can consume `fixtures/golden/replay/mixed-verdicts.json`'s `evidenceEnvelopeJson` and `expectedPerObjectVerdicts` directly for its per-object comparison leg.
- No blockers for wave 1 (plans 02/03).

---
*Phase: 1202-design-state-replay-and-per-object-verdict-closure*
*Completed: 2026-09-21*

## Self-Check: PASSED

All created/modified files verified present on disk; all 4 commit hashes (55394fb, 0b417e2, f08df38, d674015) verified in git log.
