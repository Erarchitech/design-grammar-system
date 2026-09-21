---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 06
subsystem: infra
tags: [canonical-json, sha256, cross-language-parity, decimal, evidence-contract, golden-fixtures]

# Dependency graph
requires:
  - phase: 1200-02
    provides: fixtures/golden/fixture.json, canonical-vectors.json initial 5 vectors, MANIFEST.md freeze policy
  - phase: 1200-03
    provides: data-service/canonical_json.py (the reference implementation, untouched by this plan)
  - phase: 1200-04
    provides: DG.Core.Contracts.CanonicalJsonWriter.cs (the C# mirror this plan corrects)
provides:
  - Corrected WriteNumberDecimal that preserves a decimal's stored scale via decimal.GetBits + ToString("F{scale}")
  - A sixth canonicalJson golden vector proving trailing-zero-decimal cross-language parity, with a genuinely recomputed sha256Upper
  - Named regression tests in both languages guarding against the coverage gap reopening
  - EVIDENCE-CONTRACT.md section 6 rule 2 stating the scale-preservation rule explicitly
affects: [1200-08 (ALGN12-02 checkbox reconciliation depends on comparable inputHash/outputHash across legs)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "decimal.GetBits(value)[3] bits 16-23 as the canonical source of a decimal's stored scale in C#, mirroring Python's Decimal internal scale that format(Decimal, 'f') already respects"

key-files:
  created: []
  modified:
    - DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs
    - DG/tests/DG.Tests/CanonicalJsonWriterTests.cs
    - data-service/tests/test_canonical_json.py
    - fixtures/golden/canonical-vectors.json
    - fixtures/golden/MANIFEST.md
    - spec/EVIDENCE-CONTRACT.md

key-decisions:
  - "Scale is derived from decimal.GetBits rather than from any string-parsing heuristic, so the fix reads the decimal's own internal representation exactly as .NET stores it"
  - "The new golden vector's canonical string and digest were computed by running data-service/canonical_json.py itself (the normative reference) over the vector's value, then independently re-verified by reloading the saved file and recomputing a third time"
  - "The EVIDENCE-CONTRACT.md edit is declared a clarification, not a rule change: canonicalizationVersion stays 1 because Python's behavior (and the contract's stated byte-parity purpose) were never in question -- only the C# implementation was wrong"

patterns-established:
  - "A defect class that broke because a fixture lacked a specific input shape gets closed by adding that exact shape as a permanent, named-test-guarded golden vector, not just by fixing the code"

requirements-completed: [ALGN12-01, ALGN12-02]

coverage:
  - id: D1
    description: "WriteNumberDecimal preserves a decimal's stored scale (100.00m -> \"100.00\", 2.50m -> \"2.50\", 0.10m -> \"0.10\"), matching Python's format(Decimal, \"f\"); scale-0 decimals still render with no decimal point"
    requirement: "ALGN12-01"
    verification:
      - kind: unit
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#Canonicalize_ShouldPreserveTrailingZeroScale"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#Canonicalize_ShouldRenderIntegralDecimal_WithNoDecimalPoint"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#Canonicalize_ShouldRenderDecimal_AsFixedPoint (pre-existing, unmodified)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A new canonicalJson golden vector in fixtures/golden/canonical-vectors.json carries trailing-zero decimals with a genuinely recomputed sha256Upper; both language suites recompute and assert against it; the five pre-existing vectors reproduce their committed digests unchanged"
    requirement: "ALGN12-02"
    verification:
      - kind: unit
        ref: "data-service/tests/test_canonical_json.py#test_golden_vectors_canonical_json_round_trip"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_canonical_json.py#test_canonicalize_preserves_trailing_zero_decimal_scale"
        status: pass
      - kind: unit
        ref: "data-service/tests/test_canonical_json.py#test_golden_vectors_include_a_trailing_zero_decimal"
        status: pass
      - kind: unit
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#CanonicalJson_ShouldBeDeterministic_AcrossGoldenVectors"
        status: pass
    human_judgment: false
  - id: D3
    description: "fixtures/golden/MANIFEST.md records the FIXTURE_VERSION bump (1.0.0 -> 1.1.0) and a Change-Reason Log row for the additive vector, per the freeze policy"
    verification:
      - kind: other
        ref: "fixtures/golden/MANIFEST.md Change-Reason Log table, row for 1.1.0 / Phase 1200-06"
        status: pass
    human_judgment: false
  - id: D4
    description: "spec/EVIDENCE-CONTRACT.md section 6 rule 2 states the scale-preservation rule explicitly, names the Python and C# reference renderings, and holds canonicalizationVersion at 1"
    verification:
      - kind: unit
        ref: "python -c section-scoped assertions in plan's Task 3 verify block (GetBits, format(Decimal, remains **1**) all present)"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-09-20
status: complete
---

# Phase 1200 Plan 06: Cross-Language Canonical-JSON Decimal Scale Parity (CR-01) Summary

**Fixed the C# `CanonicalJsonWriter.WriteNumberDecimal` to preserve a decimal's stored scale via `decimal.GetBits`, matching Python's `format(Decimal, "f")`, and added a genuinely-computed trailing-zero golden vector that pins both legs to the same canonical string and SHA-256 digest.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 completed
- **Files modified:** 6

## Accomplishments

- `WriteNumberDecimal` now derives scale from `decimal.GetBits(value)` (bits 16-23 of the fourth int) and renders via `ToString("F" + scale, CultureInfo.InvariantCulture)` when scale > 0, or `ToString(CultureInfo.InvariantCulture)` when scale is 0 — replacing the old integral-cast + optional-digit-format-specifier body that silently discarded trailing zeros.
- Added `Canonicalize_ShouldPreserveTrailingZeroScale` and `Canonicalize_ShouldRenderIntegralDecimal_WithNoDecimalPoint` facts to `DG.Tests`.
- Added a sixth vector to `fixtures/golden/canonical-vectors.json` (`{"ruleId":"R_GOLD_HEIGHT_MAX_75_V","height":100.00,"bindingCount":3,"ratio":2.50}`) whose `canonical` string and `sha256Upper` digest were both produced by running `data-service/canonical_json.py` over the vector's own value, then independently re-verified by reloading the saved file and recomputing a third time (matches: canonical `{"bindingCount":3,"height":100.00,"ratio":2.50,"ruleId":"R_GOLD_HEIGHT_MAX_75_V"}`, digest `6EA1772055E52D43A03B942ACD8EB9FC61FC7FD5AC22E987B2700866A855C8FF`).
- Added `test_canonicalize_preserves_trailing_zero_decimal_scale` and `test_golden_vectors_include_a_trailing_zero_decimal` to `data-service/tests/test_canonical_json.py`; extended `CanonicalJson_ShouldBeDeterministic_AcrossGoldenVectors` in the C# suite with an in-loop assertion that at least one iterated vector's canonical string carries a trailing-zero decimal.
- Bumped `fixtures/golden/MANIFEST.md`'s `FIXTURE_VERSION` from `1.0.0` to `1.1.0` and added a Change-Reason Log row naming Phase 1200-06 and the CR-01 coverage gap as an additive-only change.
- Extended `spec/EVIDENCE-CONTRACT.md` section 6 rule 2 with the explicit scale-preservation statement, naming both reference renderings and declaring the non-conforming C# patterns (optional-digit specifier, integral cast) by name; declared the edit a clarification, holding `canonicalizationVersion` at 1.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make WriteNumberDecimal preserve the decimal's stored scale** - `375faec` (fix)
2. **Task 2: Add the trailing-zero golden vector with a genuinely computed digest, and bind both suites to it** - `01773ff` (test)
3. **Task 3: State the scale-preservation rule in the contract, and confirm full-suite parity** - `c54ad17` (docs)

_No separate plan-metadata commit was requested for this gap-closure plan beyond the three task commits above; STATE.md/ROADMAP.md/REQUIREMENTS.md updates are captured in the state_updates step below._

## Files Created/Modified

- `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` - `WriteNumberDecimal` rewritten to derive scale from `decimal.GetBits` and render via `F{scale}`
- `DG/tests/DG.Tests/CanonicalJsonWriterTests.cs` - two new facts (trailing-zero scale, integral no-decimal-point regression) plus an in-loop trailing-zero assertion in the golden-vector fact
- `data-service/tests/test_canonical_json.py` - two new named regression tests; `re` import added
- `fixtures/golden/canonical-vectors.json` - one new `canonicalJson` vector appended (additions only; five pre-existing vectors untouched)
- `fixtures/golden/MANIFEST.md` - `FIXTURE_VERSION` bumped to `1.1.0`; new Change-Reason Log row
- `spec/EVIDENCE-CONTRACT.md` - section 6 rule 2 extended with the explicit scale-preservation sentence and clarification declaration

## Decisions Made

- Scale is read directly from `decimal.GetBits(value)` (bits 16-23 of element 3) rather than any string-based inference, so the C# rendering is a direct function of .NET's own internal decimal representation — the most literal possible mirror of what Python's `Decimal` already carries internally and what `format(Decimal, "f")` already respects.
- The new golden vector's `canonical`/`sha256Upper` were computed by executing the Python reference implementation itself against the vector's `value` (loaded via `json.load(f, parse_float=Decimal)`, exactly as the real test loader does), then reproduced a second and third time (once during authoring, once via the plan's independent verify snippet) to guarantee no digest was invented or hand-transcribed.
- The `EVIDENCE-CONTRACT.md` change is explicitly framed as a clarification of already-intended behavior, not a rule change — Python's behavior never changed, only the contract's prose became explicit about it — so `canonicalizationVersion` correctly stays at 1 and no previously-recorded hash becomes invalid.

## Deviations from Plan

None - plan executed exactly as written. `data-service/canonical_json.py` was read for reference but not modified, as required. All five pre-existing golden vectors were verified (via automated re-verification) to still reproduce their original committed digests.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification Results

- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanonicalJsonWriterTests"`: 13 passed, 0 failed (11 pre-existing + 2 new facts from Task 1; golden-vector fact count unchanged since it iterates generically).
- `dotnet build DG/DG.sln -c Release`: 0 warnings, 0 errors.
- `python -m pytest data-service/tests/test_canonical_json.py -q`: 19 passed (17 pre-existing + 2 new).
- `python -m pytest data-service/tests/test_canonical_json.py data-service/tests/test_evidence_contract.py data-service/tests/test_golden_fixture_shape.py -q`: 48 passed, 0 failed.
- `dotnet test DG/tests/DG.Tests/ -v minimal` (full suite): 442 passed, 4 failed. The 4 failures are exactly `DG.Tests.E2E.DesignStateValidationFlowTests.{HappyPath_StatePublishAndRetrieve, LegacyNoState_FlowStillWorks, ReinstateFailureModes_ProduceActionableMessages, Filtering_StateAndRule}` — all failing with `Neo4j.Driver.ServiceUnavailableException: Failed to connect to server 'bolt://localhost:7687/'`. This is the documented pre-existing environmental baseline (Neo4j unreachable from the host), not a regression introduced by this plan.
- Independent recomputation snippet (plan's Task 2 verify block): confirmed all 3 `canonicalJson` vectors (2 pre-existing + 1 new) recompute their committed `canonical` and `sha256Upper` exactly; 1 of 3 vectors carries a trailing-zero decimal.
- `grep -c '0\.#################################' DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` -> 0; `grep -c '(long)value' ...` -> 0; `grep -c 'GetBits' ...` -> 2.
- `grep -c 'FIXTURE_VERSION: \`1.0.0\`' fixtures/golden/MANIFEST.md` -> 0; `grep -c 'FIXTURE_VERSION' ...` -> 2 (heading line + Change-Reason Log context).
- `grep -rn 'canonicalizationVersion.*2' spec/evidence-contract.schema.json` -> no match (schema's pinned version untouched).
- `git diff --name-only` scoped to this plan's declared files shows only the six files in `files_modified`; `data-service/canonical_json.py` and `spec/evidence-contract.schema.json` are absent from every task's diff, confirmed after each task.

## Next Phase Readiness

- CR-01 is closed: the two legs now produce byte-identical canonical strings and SHA-256 digests for any decimal carrying a trailing-zero scale.
- ALGN12-02's `inputHash`/`outputHash` fields are now comparable across legs, which is the precondition plan 1200-08's checkbox reconciliation depends on.
- WR-01 (the `build_envelope` empty-rows roll-up default divergence, `no_population` vs `NotEvaluated`) remains deferred as an explicit, previously-recorded assumption — not touched by this plan, and not expected to be resolved here.

---
*Phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt*
*Completed: 2026-09-20*

## Self-Check: PASSED

All six declared `files_modified` paths and the SUMMARY.md itself exist on disk; all three task commit hashes (`375faec`, `01773ff`, `c54ad17`) are present in `git log --oneline --all`.
