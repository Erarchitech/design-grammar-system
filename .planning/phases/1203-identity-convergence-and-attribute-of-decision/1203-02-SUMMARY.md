---
phase: 1203-identity-convergence-and-attribute-of-decision
plan: 02
subsystem: identity
tags: [sha256, hash-encoding, dgid, design-state, cr-02, d-08, d-09, grasshopper]

# Dependency graph
requires:
  - phase: 1203-01
    provides: preflight test-suite baselines and the identity-literal blast-radius inventory this plan re-derives against
provides:
  - Length-prefix hash-input encoding (EncodeHashInput / _encode_hash_input) closing CR-02 in both DgIdMintingService.Mint, compute_dg_id, and every pipe-joined DesignState minting function
  - project folded into ComputeParamStateId / ComputeObjectStateIdFromRef / ComputePropStateId as an optional trailing parameter
  - Re-derived golden dgId literal and DesignState regression literal, kept in lockstep across C#/Python
  - Re-derived frozen fixture Object dgIds (fixture.json, seed.cypher, and the Phase 1202 sibling replay fixture) under the new encoding
  - A discovered, unresolved gap: canonical_json.hash_scalar_tuple / CanonicalJsonWriter.HashScalarTuple still use the naive pipe-join and have silently diverged from DgIdMintingService.Mint/compute_dg_id
affects: [1203-03, 1203-05, any future phase touching fixtures/golden/canonical-vectors.json or canonical_json.py/CanonicalJsonWriter.cs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Length-prefix hash-input encoding: {len}:{text} per component, joined by |, null -> -1:, empty -> 0: — replaces naive delimiter-joins wherever a caller-controlled string could contain the delimiter"
    - "Optional trailing parameter for project-in-hash: existing call sites keep compiling and mint deterministically when the parameter is omitted (null)"

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Models/Identity/DgIdMintingService.cs
    - DG/src/DG.Core/Services/DesignStateIdGenerator.cs
    - DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs
    - DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs
    - DG/src/DG.Grasshopper/Components/PropertyStateComponent.cs
    - DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs
    - DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs
    - data-service/dg_identity.py
    - data-service/tests/test_dg_identity.py
    - data-service/tests/test_computgraph_publish.py
    - fixtures/golden/fixture.json
    - fixtures/golden/seed.cypher
    - fixtures/golden/MANIFEST.md
    - fixtures/golden/replay/mixed-verdicts.json
    - fixtures/golden/replay/seed-replay.cypher

key-decisions:
  - "Length-prefix encoding format: {charLength}:{text} per component, pipe-joined, null -> -1:, empty -> 0: — per CONTEXT.md's Claude's Discretion grant"
  - "3-arg ComputeObjectStateId keeps its exact arity (D-07) but now routes through EncodeHashInput; its own regression pin was re-derived, not left stale"
  - "ComputeDesignStateId and ComputeCaptureEventStateId are left untouched — they concatenate sorted member StateIds with no separator at all (not pipe-joined), so CR-02 does not apply, and project reaches them transitively through members. Their pinned literal (DS_3C3C50530BE1DED0) is genuinely unchanged, not merely re-asserted."
  - "Scope-extension authorized by the user: fixture.json/seed.cypher's three frozen Object dgIds re-derived under the new encoding, MANIFEST.md FIXTURE_VERSION bumped 1.2.0 -> 1.3.0 with a Change-Reason Log row"
  - "canonical-vectors.json was explicitly named in the user's authorized scope extension but was NOT edited: doing so broke two unrelated, out-of-scope tests (test_canonical_json.py, CanonicalJsonWriterTests.cs) that verify those same vectors against a third, separate hash_scalar_tuple/HashScalarTuple implementation still using the naive pipe-join. Reverted and documented as an open gap rather than silently expanding scope further."
  - "Two additional fixture consumers beyond the named trio were discovered and updated in the same commit: fixtures/golden/replay/mixed-verdicts.json and seed-replay.cypher (Phase 1202's sibling replay fixture, which documents reusing the Object ids/dgIds verbatim)"

patterns-established:
  - "Pattern: when a shared literal changes, grep every consumer before editing any one file — a fixture literal can be asserted by a test the plan's files_modified list never mentions"

requirements-completed: [ALGN12-12]

coverage:
  - id: D1
    description: "CR-02 closed: length-prefix hash-input encoding in DgIdMintingService.Mint and compute_dg_id, plus a cross-language collision regression test proving the canonical adversarial pair no longer collides"
    requirement: "ALGN12-12"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs#Mint_PipeBoundaryShift_ProducesDifferentDgId"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_compute_dg_id_pipe_boundary_shift_does_not_collide"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cross-language golden dgId vector re-derived and kept identical across C#/Python/the computgraph-publish test in the same commit"
    requirement: "ALGN12-12"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs#Mint_KnownVector_MatchesExpectedDgId"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_dg_identity.py#test_compute_dg_id_matches_dotnet_golden_vector"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_computgraph_publish.py#test_dgid_matches_golden_vector"
        status: pass
    human_judgment: false
  - id: D3
    description: "project folded into ComputeParamStateId/ComputeObjectStateIdFromRef/ComputePropStateId as an optional parameter; null-omitted call shape stays backward compatible; 3-arg ComputeObjectStateId's arity and pin re-verified"
    requirement: "ALGN12-12"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs#ComputeObjectStateIdFromRef_ShouldChange_WhenProjectDiffers"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs#ComputeParamStateId_ShouldChange_WhenProjectDiffers"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs#ComputePropStateId_ShouldChange_WhenProjectDiffers"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs#ComputeObjectStateId_ShouldHaveExactlyThreeStringParameters_ProvingCrossRuleIdentity"
        status: pass
    human_judgment: false
  - id: D4
    description: "Release build of DG.sln succeeds, regenerating the Grasshopper plugin against the new minting contract"
    verification:
      - kind: other
        ref: "dotnet build DG/DG.sln -c Release"
        status: pass
    human_judgment: false
  - id: D5
    description: "Frozen fixture Object dgIds (fixture.json, seed.cypher, and the Phase 1202 sibling replay fixture) re-derived under the new encoding, with MANIFEST.md's freeze-amendment procedure followed"
    verification:
      - kind: unit
        ref: "data-service/tests/test_golden_fixture_shape.py (7 passed, shape-only, no literal assertions)"
        status: pass
      - kind: unit
        ref: "DG.Tests.EvidenceContractTests (21 passed, no literal assertions on the re-derived dgIds)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Discovered gap: canonical_json.hash_scalar_tuple / CanonicalJsonWriter.HashScalarTuple still use the naive pipe-join and now silently diverge from Mint/compute_dg_id's documented byte-for-byte parity claim"
    verification: []
    human_judgment: true
    rationale: "This is an architectural decision (extend the length-prefix fix to a third implementation outside this plan's files_modified, or explicitly document the two conventions as intentionally divergent) that only the user/planner can make — not something safe to guess through inside this plan's authorized scope."

# Metrics
duration: 55min
completed: 2026-09-22
status: complete
---

# Phase 1203 Plan 02: Length-Prefix Identity Encoding (CR-02) + Project-in-Hash (D-08) Summary

**Closed CR-02 (pipe-collision in dgId/DesignState hash inputs) via a shared length-prefix encoder in both languages, folded `project` into every DesignState minting function that can legitimately obtain one, and re-derived every pinned identity literal — including three frozen `fixtures/golden/` Object dgIds — in lockstep across both commits.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-22T~21:00Z
- **Completed:** 2026-09-22T21:53:06Z
- **Tasks:** 2 (plus the user-authorized fixture-amendment work folded into Task 2)
- **Files modified:** 14 (9 in Task 1's commit, 9 in Task 2's commit, with `DesignStateIdGenerator.cs` counted once as it landed in Task 1)

## Accomplishments

- Added `EncodeHashInput` (C#, twinned in both `DgIdMintingService.cs` and `DesignStateIdGenerator.cs`) and `_encode_hash_input` (Python, `dg_identity.py`): length-prefix encoding (`{charLength}:{text}`, pipe-joined, `-1:` for null, `0:` for empty) that makes every component boundary unambiguous, closing CR-02.
- `DgIdMintingService.Mint` and `dg_identity.compute_dg_id` now build their hash input through the encoder instead of naive `"{a}|{b}|{c}"` interpolation.
- Every DesignState minting function that was pipe-joined (`ComputeObjectStateId` 3-arg, `ComputeObjectStateIdFromRef`, `ComputePropStateId`, `ComputeParamStateId`) now routes through the same encoder, closing CR-02 for the whole DesignState surface, not only the dgId minting path.
- `project` added as an optional trailing parameter to `ComputeParamStateId`, `ComputeObjectStateIdFromRef`, and `ComputePropStateId`. Confirmed on disk that none of the three Grasshopper capture components (`ObjectStateComponent`, `ParameterStateComponent`, `PropertyStateComponent`) has a Project input port or project field in scope, so no synthesized value is passed — each call site now carries a comment pointing to the minting function's own doc-comment and the GATE12-04 / v9.0 Phase 40 pointer for wiring a project port later.
- Cross-language collision regression tests added in both suites (`Mint_PipeBoundaryShift_ProducesDifferentDgId` / `test_compute_dg_id_pipe_boundary_shift_does_not_collide`, plus `ComputeObjectStateId_PipeBoundaryShift_ProducesDifferentId` for the DesignState 3-arg form), each proving the canonical adversarial pair `("a|b","c","d")` vs `("a","b|c","d")` — identical under the old naive join, distinct under the new encoding.
- Golden dgId vector and the 3-arg `ComputeObjectStateId` regression pin re-derived and kept identical across C#, Python, and a third live consumer (`test_computgraph_publish.py`) discovered during the sweep — all updated in the same commit as the encoder change, so the cross-language parity harness was never left red between commits.
- `ComputeDesignStateId`'s pinned literal (`DS_3C3C50530BE1DED0`) is unchanged — verified this is factually correct (not merely convenient) because that function never called the naive pipe-join and does not call `EncodeHashInput` either; it concatenates sorted member StateIds with no separator at all.
- Release build of `DG.sln` succeeds (0 warnings, 0 errors), regenerating `DG.Grasshopper` against the new contract.
- Frozen `fixtures/golden/fixture.json`/`seed.cypher` Object dgIds re-derived per the user's authorized scope extension, with `MANIFEST.md`'s `FIXTURE_VERSION` bumped and a new Change-Reason Log row. Two additional consumers of the same three literals — Phase 1202's sibling replay fixture (`mixed-verdicts.json`, `seed-replay.cypher`) — were discovered and kept in sync.
- Discovered and deliberately did NOT paper over: `canonical_json.hash_scalar_tuple` / `CanonicalJsonWriter.HashScalarTuple` are a third, independent implementation of the same naive-pipe-join pattern, explicitly documented to mirror `Mint`/`compute_dg_id` "byte-for-byte" — that claim is now false and is flagged as an open gap rather than silently fixed by expanding this plan's scope further.

## Task Commits

1. **Task 1: Add length-prefix encoding helpers and their collision regression tests in both languages** - `d9bf302` (feat)
2. **Task 2: Fold project into DesignState hashes where legitimately available, and re-derive every pinned literal in lockstep** (includes the user-authorized fixture amendment) - `aacf487` (feat)

_Note: per the plan's own prohibition ("MUST NOT land the C# golden vector without the Python golden vector in the same commit"), Task 1's commit includes both languages' encoder change AND the re-derived golden vector together — deviating slightly from the plan's literal task-boundary text ("Do not update the golden vector literal in this task; task 2 does that") in favor of never leaving the cross-language parity harness red between commits, which is the prohibition's actual intent. See Deviations below._

## Files Created/Modified

- `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` - Added `EncodeHashInput`; `Mint` now uses it
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` - Added twinned `EncodeHashInput`; `ComputeObjectStateId`, `ComputeObjectStateIdFromRef`, `ComputePropStateId`, `ComputeParamStateId` now use it; the latter three gained an optional `project` parameter
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs` - Comment noting `project` left null (no Project input port in scope)
- `DG/src/DG.Grasshopper/Components/ParameterStateComponent.cs` - Same
- `DG/src/DG.Grasshopper/Components/PropertyStateComponent.cs` - Same
- `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs` - Re-derived golden vector; added `Mint_PipeBoundaryShift_ProducesDifferentDgId`
- `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` - Re-derived 3-arg `ComputeObjectStateId` pin; added its collision test and the three project-sensitivity tests; annotated the unchanged `ComputeDesignStateId` pin
- `data-service/dg_identity.py` - Added `_encode_hash_input`; `compute_dg_id` now uses it
- `data-service/tests/test_dg_identity.py` - Re-derived `GOLDEN_DG_ID`; added `test_compute_dg_id_pipe_boundary_shift_does_not_collide`
- `data-service/tests/test_computgraph_publish.py` - Re-derived `GOLDEN_DG_ID` (discovered live consumer of the same golden vector, not originally in `files_modified`)
- `fixtures/golden/fixture.json` - Re-derived `OBJ_GOLD_PASS`/`FAIL`/`EMPTY` dgIds; `fixtureVersion` bumped to `1.3.0`
- `fixtures/golden/seed.cypher` - Re-derived matching `obj_*.dgId` literals; header note added
- `fixtures/golden/MANIFEST.md` - `FIXTURE_VERSION` bumped `1.2.0` → `1.3.0`; new Change-Reason Log row documenting the re-derivation and the `canonical-vectors.json` gap
- `fixtures/golden/replay/mixed-verdicts.json` - Re-derived the same three dgIds (discovered consumer, reuses them "verbatim" per its own docstring)
- `fixtures/golden/replay/seed-replay.cypher` - Re-derived the same three dgIds; header note added

## Decisions Made

- Length-prefix format is `{charLength}:{text}` per component, joined by `|`, with `-1:` for null and `0:` for empty — matches the plan's Claude's-Discretion grant exactly, verified with the worked collision example (`("a|b","c","d")` vs `("a","b|c","d")`, both naively joining to `a|b|c|d`, encoding to `3:a|b|1:c|1:d` vs `1:a|3:b|c|1:d`).
- All four pipe-joined DesignState minting functions (not only `Mint`) were routed through `EncodeHashInput`, since CR-02's boundary-shift defect is present in each of them independently, not only in the dgId minting path the plan's title emphasizes.
- `ComputeDesignStateId`/`ComputeCaptureEventStateId` left untouched, per the plan's own instruction — but the SUMMARY records this as **factually verified**, not merely policy: neither function ever called a pipe-join, so there was nothing for `EncodeHashInput` to fix in them, and their pinned literal is genuinely unchanged rather than coincidentally re-asserted.
- Fixture-amendment scope extension executed exactly as user-authorized for `fixture.json`/`seed.cypher`, plus two additional discovered consumers (`mixed-verdicts.json`, `seed-replay.cypher`) updated for consistency and logged.
- `canonical-vectors.json` — explicitly named in the user's authorization — was **not** edited. See Deviations below for the full reasoning; this is the one point where the executor stopped short of the full authorized scope because doing so would have silently broken two out-of-scope tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated a live golden-vector consumer not listed in `files_modified`**
- **Found during:** Task 1
- **Issue:** `data-service/tests/test_computgraph_publish.py::test_dgid_matches_golden_vector` asserts `proc["dgId"] == GOLDEN_DG_ID` where `GOLDEN_DG_ID = "dg:BC8E62EE137E2B56"` — the same shared golden vector `DgIdMintingServiceTests.cs`/`test_dg_identity.py` assert, computed inline via `computgraph_publish.publish_structure` → `compute_dg_id`. Changing the encoding without updating this file would have left the Python suite red.
- **Fix:** Updated `GOLDEN_DG_ID` (and its docstring reference) to `dg:0F31CD18542F0252` in the same commit as the encoder change.
- **Files modified:** `data-service/tests/test_computgraph_publish.py`
- **Verification:** `python -m pytest data-service/tests/test_computgraph_publish.py -q` — 39/39 pass (combined with `test_dg_identity.py` in the same run)
- **Committed in:** `d9bf302` (Task 1 commit)

**2. [Rule 4 → resolved by prior explicit user decision] Fixture-amendment scope extension**
- **Found during:** Task 2, and pre-declared by the user's own task framing before execution began
- **Issue:** Task 1's encoding change invalidates `fixture.json`/`seed.cypher`'s three frozen Object dgIds, which `fixtures/golden/MANIFEST.md`'s freeze policy normally forbids editing without an explicit amendment procedure (version bump + Change-Reason Log row).
- **Fix:** Followed the user's explicit authorization exactly: re-derived the three dgIds under the new encoding using the SAME input tuples, bumped `FIXTURE_VERSION` `1.2.0` → `1.3.0`, added a Change-Reason Log row, and checked for (and updated) additional consumers beyond the named trio.
- **Files modified:** `fixtures/golden/fixture.json`, `fixtures/golden/seed.cypher`, `fixtures/golden/MANIFEST.md`, plus the two discovered consumers `fixtures/golden/replay/mixed-verdicts.json` and `fixtures/golden/replay/seed-replay.cypher`
- **Verification:** `python -m pytest data-service/tests/test_golden_fixture_shape.py -q` (7 passed) and `dotnet test --filter EvidenceContractTests` (21 passed) — neither asserts on the specific dgId literal values, only shape, so both stayed green through the re-derivation
- **Committed in:** `aacf487` (Task 2 commit)

**3. [Not auto-fixed — stopped and documented per the user's own instruction] `canonical-vectors.json` reverted, not edited**
- **Found during:** Task 2's fixture amendment
- **Issue:** `canonical-vectors.json` was explicitly named in the user's authorized scope extension. An initial edit re-derived its three `scalarTuple` vectors' `joined`/`sha256Upper` under the new length-prefix encoding — but this broke two tests entirely outside this plan's scope: `data-service/tests/test_canonical_json.py::test_golden_vectors_scalar_tuple_round_trip` and `DG.Tests.CanonicalJsonWriterTests.ScalarTupleHash_ShouldMatchShippedDgIdVector`. Both verify these same vectors against `canonical_json.hash_scalar_tuple` / `CanonicalJsonWriter.HashScalarTuple` — a THIRD, independent implementation of the exact naive-pipe-join pattern CR-02 targets, explicitly documented in both files' own doc-comments to mirror `Mint`/`compute_dg_id` "byte-for-byte." That claim is now false (the two implementations have diverged), but fixing it would require editing `canonical_json.py` and `DG.Core.Contracts.CanonicalJsonWriter.cs` — files entirely outside this plan's `files_modified` and outside the user's stated fixture-amendment authorization (which covered `fixture.json`/`seed.cypher`/`canonical-vectors.json`/"any other consumer of these three literals", not a fourth hashing implementation).
- **Resolution:** Reverted `canonical-vectors.json` to its pre-Task-2 state (`git checkout -- fixtures/golden/canonical-vectors.json`) before committing. Documented the gap explicitly in `MANIFEST.md`'s 1.3.0 Change-Reason Log row and here, per the user's own instruction: "If anything about the fixture amendment turns out to be more ambiguous than described above... stop and report back rather than guessing further." This is exactly that case.
- **Files affected (reverted, not committed):** `fixtures/golden/canonical-vectors.json`
- **Verification:** `python -m pytest data-service/tests/test_canonical_json.py -q` (23/23 pass after revert) and `dotnet test --filter CanonicalJsonWriterTests` (15/15 pass after revert)
- **Follow-up needed:** A future plan/decision must choose between (a) extending the length-prefix encoding to `hash_scalar_tuple`/`HashScalarTuple` too (re-opening `canonical-vectors.json`'s freeze with its own Change-Reason Log row and re-deriving those three vectors AND `fixture.json`'s dgIds against the now-shared encoding), or (b) explicitly documenting the two hashing conventions (`Mint`/`compute_dg_id` vs. `hash_scalar_tuple`/`HashScalarTuple`) as intentionally divergent and removing the stale "byte-for-byte" claim from both files' doc-comments.

**4. [Documentation correction, not a code deviation] Plan text's `DS_3C3C50530BE1DED0` instruction did not match the correct implementation**
- **Found during:** Task 2
- **Issue:** The plan's action text says to "Update the two pinned DesignState literals... `OS_493B9A7153D92072`... `DS_3C3C50530BE1DED0` on the aggregate fact" — implying both change. But the plan's own preceding instruction says to leave `ComputeDesignStateId`/`ComputeCaptureEventStateId` (the aggregate functions) without a project parameter and without touching their hash path, since they are aggregates. Implementing that correctly (not calling `EncodeHashInput` in `ComputeDesignStateId`) means its output is byte-identical to before, so `DS_3C3C50530BE1DED0` does NOT change — updating it to a different value would have asserted a factually wrong literal.
- **Fix:** Left `DS_3C3C50530BE1DED0` unchanged; added a doc-comment explaining why on both the function and the test, verified by running the test before and after all other changes to confirm it never broke.
- **Files modified:** `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` (comment only)
- **Verification:** `dotnet test --filter ComputeDesignStateId_ShouldRemainByteIdentical` passes both before and after Task 2's other changes
- **Committed in:** `aacf487` (Task 2 commit)

---

**Total deviations:** 4 (1 Rule 3 auto-fix, 1 pre-authorized Rule 4 resolution, 1 stop-and-report per explicit user instruction, 1 documentation correction)
**Impact on plan:** All four were necessary for correctness — none represent unauthorized scope creep. Deviation 3 is the one place this plan's authorized scope was NOT fully executed (`canonical-vectors.json` left unedited), and that is deliberate: completing it would have required an additional, unauthorized architectural change to a third hashing implementation.

## Issues Encountered

`fixtures/golden/replay/seed-replay.cypher`'s `obj_pass.dgId` literal was already inconsistent with its own `(project, definitionId, cgId)` triple even before this plan (it copies `fixture.json`'s dgId verbatim despite using a different `definitionId` — `def-replay-1202-01` vs. `def-golden-01`). This is a pre-existing data-authoring quirk from Phase 1202, not introduced by this plan; the re-derivation preserved the same "copy fixture.json's value verbatim" convention rather than attempting to fix the pre-existing inconsistency, since that fix is out of scope here.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-02 is closed with cross-language regression coverage; the `project`-in-hash gap is closed for every DesignState minting function that can legitimately obtain a project.
- Both ObjState minting forms (3-arg `ComputeObjectStateId`, `ComputeObjectStateIdFromRef`) survive with re-derived pins.
- Every pinned identity literal in `DG.Tests`/`data-service/tests` and the frozen `fixture.json`/`seed.cypher`/replay-sibling fixtures was re-derived in the same wave, so the cross-language and cross-fixture parity harnesses are all green simultaneously — not left red between commits.
- **Blocker for a future phase, not this one:** `canonical_json.hash_scalar_tuple` / `CanonicalJsonWriter.HashScalarTuple` and `fixtures/golden/canonical-vectors.json`'s three `scalarTuple` vectors still encode the pre-CR-02 naive pipe-join. This is a real, live divergence from `DgIdMintingService.Mint`/`compute_dg_id` that a future plan should resolve explicitly (extend the fix, or document the split) rather than leave silently drifting.

---
*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/1203-identity-convergence-and-attribute-of-decision/1203-02-SUMMARY.md`
- FOUND: `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs`
- FOUND: `DG/src/DG.Core/Services/DesignStateIdGenerator.cs`
- FOUND: `data-service/dg_identity.py`
- FOUND: `fixtures/golden/fixture.json`
- FOUND commit: `d9bf302` (Task 1)
- FOUND commit: `aacf487` (Task 2 + fixture amendment)
