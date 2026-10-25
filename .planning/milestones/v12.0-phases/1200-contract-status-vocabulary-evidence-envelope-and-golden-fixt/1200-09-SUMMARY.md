---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
plan: 09
subsystem: contracts/canonical-hash
tags: [canonical-json, cross-language-parity, golden-fixtures, gap-closure, decimal]
status: complete
requires:
  - "1200-06 (CR-01 scale-preservation fix in WriteNumberDecimal)"
provides:
  - "Negative-zero sign preservation in DG.Core's CanonicalJsonWriter, matching Python's format(Decimal, 'f')"
  - "Golden-vector coverage for negative-zero and ordinary-negative decimals (fixture v1.2.0)"
affects:
  - "Any producer canonicalizing a decimal that can net to negative zero (evidence envelopes, DE-01 cross-leg comparison)"
tech-stack:
  added: []
  patterns:
    - "Sign re-attachment guarded by !StartsWith('-') so it fires only where ToString lost the sign"
    - "Golden-vector digests computed by running the normative implementation, then re-verified by reloading from disk"
key-files:
  created: []
  modified:
    - DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs
    - DG/tests/DG.Tests/CanonicalJsonWriterTests.cs
    - data-service/tests/test_canonical_json.py
    - fixtures/golden/canonical-vectors.json
    - fixtures/golden/MANIFEST.md
key-decisions:
  - "Scale-2 negative zero (-0.00) chosen for the golden vector instead of bare -0, because a bare -0 is a JSON integer whose sign both legs' parsers drop before canonicalization runs"
  - "canonicalizationVersion stays 1 — the six normalization rules are unchanged; only C#'s conformance to rule 2 was fixed, so recorded hashes of non-negative-zero payloads remain valid"
  - "FIXTURE_VERSION bumped 1.1.0 -> 1.2.0 (additive) rather than editing frozen vectors, per the manifest freeze policy"
requirements-completed: [ALGN12-02]
coverage:
  - deliverable: "Negative-zero decimals canonicalize with a preserved sign on the C# leg"
    verification:
      - kind: test
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#Canonicalize_ShouldPreserveNegativeZeroSign"
        status: pass
      - kind: test
        ref: "data-service/tests/test_canonical_json.py#test_canonicalize_preserves_negative_zero_sign"
        status: pass
    human_judgment: false
  - deliverable: "Ordinary negative decimals render with exactly one sign (no double-prepend regression)"
    verification:
      - kind: test
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#Canonicalize_ShouldRenderOrdinaryNegativeDecimal_WithSingleSign"
        status: pass
      - kind: test
        ref: "data-service/tests/test_canonical_json.py#test_canonicalize_renders_ordinary_negative_decimal_with_single_sign"
        status: pass
    human_judgment: false
  - deliverable: "Two new golden vectors with genuinely recomputed digests; all eight reproduce on both legs"
    verification:
      - kind: test
        ref: "DG/tests/DG.Tests/CanonicalJsonWriterTests.cs#CanonicalJson_ShouldBeDeterministic_AcrossGoldenVectors"
        status: pass
      - kind: test
        ref: "data-service/tests/test_canonical_json.py#test_golden_vector_negative_digests_are_independently_reproducible"
        status: pass
      - kind: command
        ref: "python -c 'reload canonical-vectors.json from disk; recompute every canonical string and SHA-256' -> ALL VECTORS REPRODUCE: True (8/8)"
        status: pass
    human_judgment: false
  - deliverable: "Fixture freeze discipline: version bumped, Change-Reason Log row added, six frozen vectors untouched"
    verification:
      - kind: command
        ref: "git show HEAD:fixtures/golden/canonical-vectors.json vs working copy -> first 6 vectors byte-identical: True; FIXTURE_VERSION 1.2.0"
        status: pass
    human_judgment: false
metrics:
  duration: 24 min
  completed: 2026-09-20
  tasks: 2
  files: 5
---

# Phase 1200 Plan 09: Negative-Zero Canonical-Hash Parity Summary

Closed code-review finding WR-01 by re-attaching the sign bit that `decimal.ToString("F{scale}")` silently strips from negative-zero decimals in C#, and closed IN-01 by adding the first golden vectors that exercise any negative value at all.

## What was the problem

Plan 1200-06 closed CR-01 (stored-scale preservation) for ordinary values, but left one input class diverging. C#'s `decimal.ToString("F{scale}")` normalizes negative zero's sign away, while Python's `format(Decimal, "f")` — the normative reference per `spec/EVIDENCE-CONTRACT.md` § 6 rule 2 — preserves it:

| Input | Python (normative) | C# (before this plan) |
|---|---|---|
| `-0.00` | `'-0.00'` | `"0.00"` — sign lost |
| `-0` (scale 0) | `'-0'` | `"0"` — sign lost |
| `-12.50` | `'-12.50'` | `"-12.50"` — already correct |

Because the same payload hashes differently on the two legs, this reopened exactly the cross-language hash-parity gap CR-01 existed to close. None of the six pre-existing golden vectors carried a negative value, so the gap was untested on both legs.

## Accomplishments

### Task 1 — Sign preservation in `WriteNumberDecimal` (commit `8f008c8`)

Extracted the sign bit from `decimal.GetBits(value)` (bit 31 of element 3) alongside the existing scale extraction, reusing the already-fetched `bits` array rather than calling `GetBits` twice. The rendered string is now computed once for both the scale-0 and fixed-point branches, then the sign is re-attached:

```csharp
if (isNegative && !rendered.StartsWith('-'))
{
    rendered = "-" + rendered;
}
```

The `!StartsWith('-')` guard is load-bearing, not defensive padding: `ToString` already emits the sign for every *non-zero* negative value, so an unconditional prefix would produce `"--12.50"`. Negative zero is the only input whose sign bit is set while its rendered form lacks the sign, so the branch fires for it alone.

Two tests added, matching the existing naming style:
- `Canonicalize_ShouldPreserveNegativeZeroSign` — covers the `GetBits`-constructed form, both arithmetic-derived forms (`0m - 0.00m`, `-1m * 0.00m`), scale-0 negative zero (`-0`), and positive zero as a non-regression control.
- `Canonicalize_ShouldRenderOrdinaryNegativeDecimal_WithSingleSign` — the double-sign guard, asserting `-12.50`, `-0.5`, `-7`, and a large negative all render with one sign and that the output contains no `--`.

### Task 2 — Golden vectors and fixture version bump (commit `ff1ab66`)

Two `canonicalJson` vectors appended to `fixtures/golden/canonical-vectors.json`:

| Closes | Canonical string | sha256Upper |
|---|---|---|
| WR-01 | `{"bindingCount":2,"margin":-0.00,"ruleId":"R_GOLD_HEIGHT_MAX_75_V"}` | `BB8E8891926C76987EFA9682D8D91327CA2A16E7D221A61E964F00CB65E39339` |
| IN-01 | `{"count":-7,"delta":-12.50,"offset":-0.5,"status":"failed"}` | `E7A9C3A7179A516A2CBA1C9260A5314275AF3DE42C999117D1B24B7507486824` |

Both digests were produced by actually running `data-service/canonical_json.py`'s `canonicalize` over the value and hashing the UTF-8 bytes — never hand-authored — then re-verified by reloading the saved file from disk and recomputing independently.

`FIXTURE_VERSION` bumped `1.1.0` → `1.2.0` with a Change-Reason Log row citing this plan and both review findings. Four Python tests added, including one that recomputes each negative vector's digest from the canonical string rather than trusting the recorded literal.

## Key decisions

**Scale-2 negative zero, not bare `-0`, in the fixture.** I probed both parsers before authoring the vector. A bare `-0` is an *integer* in JSON: Python's `json.loads('-0', parse_float=Decimal)` returns `int` `0` (the `parse_float` hook never fires), dropping the sign before `canonicalize` ever sees it. So a `-0` vector would have been untestable through the fixture — it would have asserted positive-zero behavior while appearing to cover negative zero. `-0.00` routes through `parse_float` and round-trips as `Decimal('-0.00')`. Scale-0 negative zero is still covered directly by the C# unit test, where it can be constructed without a JSON round-trip.

**`canonicalizationVersion` stays `1`.** The six normalization rules did not change; C#'s *conformance* to rule 2 was fixed. Recorded hashes of payloads without negative zero remain valid, so bumping would have invalidated committed evidence for no reason. The fixture version bump (coverage) and the canonicalization version (rules) are deliberately decoupled — the manifest row states this explicitly.

**`canonical_json.py` left untouched**, per the plan's prohibition — it is the normative reference and already correct.

## Verification

| Check | Result |
|---|---|
| `dotnet test --filter CanonicalJsonWriterTests` | 15/15 pass (13 pre-existing + 2 new), stable across 5 consecutive runs |
| `pytest data-service/tests/test_canonical_json.py` | 23/23 pass (19 pre-existing + 4 new) |
| All 8 vectors reproduce from the saved file | `ALL VECTORS REPRODUCE: True` |
| Six pre-existing vectors byte-identical to committed version | True (strictly additive) |
| `System.Text.Json` preserves the `-0.00` sign bit on `GetDecimal()` | Verified: scale=2, signbit=True — vector round-trips through the C# harness |
| `data-service/canonical_json.py` modified | No — `git status --short` empty |
| Files changed across both commits | Exactly the 5 declared; zero deletions |

**Negative control — the new tests are load-bearing.** Rather than trusting a green suite, I temporarily replaced the guard with `if (false && ...)` and re-ran: the C# suite then failed with exactly the WR-01 symptom (`"margin":0.00` where `"margin":-0.00` was expected), in both the new unit test and the golden-vector round-trip. The fix was then restored and confirmed byte-identical to the committed state. This proves the coverage detects the regression rather than passing vacuously.

I also confirmed the C# golden-vector test was not reading a stale fixture: the build-output copy at `bin/Debug/net9.0/Fixtures/golden/` carries all 8 vectors including both new negative ones.

## Deviations from Plan

None — plan executed exactly as written.

The plan's Task 1 action asked me to "verify this is true for at least one ordinary negative value before assuming it" regarding `ToString`'s sign handling. I did so empirically before writing the fix (`-12.50m` → `"-12.50"`, sign bit set, scale 2), which is what justifies the `!StartsWith('-')` guard shape rather than an unconditional prefix.

## Issues Encountered

**Pre-existing, not caused by this plan:** the full `dotnet test` suite shows 1-2 intermittent failures in `DG.Tests.E2E.DesignStateValidationFlowTests` (`Filtering_StateAndRule`, `HappyPath_StatePublishAndRetrieve`). These are the known environment-dependent Neo4j E2E tests — the `neo4j` hostname resolves only inside the docker compose network. They vary run-to-run, touch neither canonical JSON nor any file in this plan, and 446-448 of 448 tests pass otherwise. Not a regression from this work.

**Untracked files left deliberately untracked:** `DG/tests/DG.Tests/bin/**/Fixtures/` (build output produced by my test runs, under the repo's existing `bin/` convention) and `data-service/tests/test_rule_conflict.py` (dated Sep 19, predates this session). Neither is in this plan's declared scope.

## Next Phase Readiness

WR-01 and IN-01 are closed on both legs. CR-01's parity guarantee now covers negative zero and ordinary negatives in addition to the non-negative cases 1200-06 covered, so the Phase 1200 freeze can be acted on by downstream phases for this input class.

Worth noting for whoever reconciles the review: `1200-REVIEW.md`'s remaining findings are untouched by this plan — IN-02 (manifest log rows lack a time component, so same-day bumps aren't orderable from the manifest alone) now applies to three same-day rows rather than two, since `1.2.0` is also dated 2026-09-20. The review classified that as a traceability nicety, not a defect, and it was outside this plan's declared file scope.

## Self-Check: PASSED

- `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` — FOUND, contains the sign guard at line 238
- `DG/tests/DG.Tests/CanonicalJsonWriterTests.cs` — FOUND, 2 new tests pass
- `data-service/tests/test_canonical_json.py` — FOUND, 4 new tests pass
- `fixtures/golden/canonical-vectors.json` — FOUND, 8 vectors, all reproduce
- `fixtures/golden/MANIFEST.md` — FOUND, FIXTURE_VERSION 1.2.0 with 1.2.0 log row
- Commit `8f008c8` — FOUND in `git log`
- Commit `ff1ab66` — FOUND in `git log`
