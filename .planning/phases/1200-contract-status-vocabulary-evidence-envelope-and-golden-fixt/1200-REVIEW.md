---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
reviewed: 2026-09-20T00:00:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - DG/DG.sln
  - DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs
  - DG/src/DG.Core/Contracts/EvidenceEnvelope.cs
  - DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs
  - DG/src/DG.Core/Contracts/EvidenceStatus.cs
  - DG/src/DG.Core/Contracts/EvidenceStatusNames.cs
  - DG/tests/DG.Tests/CanonicalJsonWriterTests.cs
  - DG/tests/DG.Tests/DG.Tests.csproj
  - DG/tests/DG.Tests/EvidenceContractTests.cs
  - DG/tools/DG.De01Harness/DG.De01Harness.csproj
  - DG/tools/DG.De01Harness/Program.cs
  - data-service/app.py (phase-1200 additions only)
  - data-service/canonical_json.py
  - data-service/evidence_contract.py
  - data-service/requirements.txt
  - data-service/tests/test_canonical_json.py
  - data-service/tests/test_evidence_contract.py
  - data-service/tests/test_golden_fixture_shape.py
  - dg-reasoner/requirements.txt
  - fixtures/golden/MANIFEST.md
  - fixtures/golden/canonical-vectors.json
  - fixtures/golden/fixture.json
  - fixtures/golden/seed.cypher
  - spec/DATABASE.md
  - spec/EVIDENCE-CONTRACT.md
  - spec/evidence-contract.schema.json
  - tools/de01/README.md
  - tools/de01/__init__.py
  - tools/de01/legs.py
  - tools/de01/report.py
  - tools/de01/report_schema.json
  - tools/de01/run_de01.py
  - tools/de01/tests/conftest.py
  - tools/de01/tests/test_de01_runner.py
findings:
  critical: 2
  warning: 2
  info: 1
  total: 5
status: issues_found
---

# Phase 1200: Code Review Report

**Reviewed:** 2026-09-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 32 (per `files_to_review`, `data-service/app.py` scoped to phase-1200 additions only)
**Status:** issues_found

## Summary

Reviewed the frozen evidence contract, its Python and C# canonicalization/envelope implementations, the golden fixture, and the DE-01 comparison runner. The envelope shapes, status vocabulary mapping, legacy-boolean direction (D-03/D-04), and the `app.py` sidecar's degrade-to-quiet behavior (D-08) are all correctly and defensively implemented — I verified the sidecar hook is fully wrapped in `try/except Exception` and cannot affect the publish response.

However, I found and **verified by execution** two serious defects that go directly against the phase's own stated invariants:

1. **The C# and Python canonical-JSON number formatting do not actually agree** for any decimal value carrying a non-canonical trailing-zero scale (e.g. `100.00`, `2.50`) — despite this being exactly the byte-exact cross-language guarantee the phase exists to freeze. Reproduced against both the real `DG.Core.Contracts.CanonicalJsonWriter` class and the shipped `canonical_json.py`.
2. **`tools/de01/report.py`'s `compare_legs` silently accepts a real disagreement as "declared"** when exactly one leg reports a non-declarable status (e.g. `passed` or `unknown`) and another reports a declarable status with a warning (e.g. `unsupported`). This is the exact "silent disagreement" scenario D-14 says must never happen, and it directly contradicts the module's own docstring ("every differing leg's status is one of unsupported/error/not_evaluated/indeterminate"). Reproduced by direct execution against the real `compare_legs` function.

Both findings are gaps in test coverage, not failures of existing tests — all 46 Python tests and 32 relevant C# tests pass unchanged; the golden vectors and the `compare_legs` unit tests simply never exercise these specific inputs.

## Critical Issues

### CR-01: C# and Python canonical-JSON decimal formatting diverge for any trailing-zero scale — breaks D-07 byte-exact parity

**File:** `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:212-223` (`WriteNumberDecimal`)
**Also affects:** `data-service/canonical_json.py:97-119` (`_canonicalize_number`) — Python's behavior is correct per spec and is explicitly asserted by its own test; the C# side is the one that diverges.

**Issue:** `spec/EVIDENCE-CONTRACT.md` §6 rule 2 requires non-integer numbers to be "rendered as fixed-point decimal strings via `decimal`/`Decimal` ... never via `double`/`float`," with the explicit intent that Python and C# hashes be reproducible from identical logical content. Python's `_canonicalize_number` uses `format(value, "f")` on a `Decimal`, which **preserves the Decimal's stored scale exactly** — this is standard, documented Python behavior, and `data-service/tests/test_canonical_json.py:86` explicitly pins it: `canonicalize(Decimal("2.50")) == "2.50"`.

C#'s `WriteNumberDecimal` does not preserve scale. It first checks whether the value is integral (`decimal.Round(value) == value && ... && value == Math.Truncate(value)`) and if so casts to `long` and renders with no decimal point at all; otherwise it formats with `"0.#################################"`, whose `#` specifiers strip trailing zeros from the fractional part. Both paths normalize away exactly the information Python's `format(Decimal, "f")` preserves.

**Verified by execution** (against the real shipped `DG.Core.Contracts.CanonicalJsonWriter`, referenced via a throwaway console app):
```
CanonicalJsonWriter.Canonicalize({"amount": 100.00m}) => {"amount":100}
CanonicalJsonWriter.Canonicalize({"ratio": 2.50m})    => {"ratio":2.5}
```
Python's `canonical_json.canonicalize({"amount": Decimal("100.00")})` produces `{"amount":100.00}` and `canonicalize({"ratio": Decimal("2.50")})` produces `{"ratio":2.50}` (directly per the test file's own assertion for the second case, and by the same code path for the first — `format(Decimal("100.00"), "f")` returns `"100.00"`, verified with `python3 -c "from decimal import Decimal; print(format(Decimal('100.00'),'f'))"`).

**Failure scenario:** Any producer on the C# side that builds a canonicalization input containing a `decimal` field with a non-canonical scale — e.g. a height of `82.50` meters read from a rule literal string `"82.50"`, or a `JsonNode` parsed from upstream JSON containing `"100.00"` (verified: `System.Text.Json.Nodes.JsonNode.Parse("100.00").AsValue().TryGetValue<decimal>(out var d)` yields `d == 100.00m` with scale preserved) — will silently produce a different canonical string, and therefore a different SHA-256 digest, than the Python leg would for the logically identical value. This is invisible until DE-01 (or a real cross-service hash comparison) hits such a value; the current golden vectors in `fixtures/golden/canonical-vectors.json` only exercise `82.5` and `0.1`, neither of which has a trailing zero, so this gap is untested by the existing suite on either side.

**Fix:** Preserve the `decimal`'s actual scale in C#, matching `Decimal.ToString("F{scale}")` or equivalent, rather than special-casing integral values or using an optional-digit (`#`) format specifier:
```csharp
private static void WriteNumberDecimal(decimal value, StringBuilder sb, string path)
{
    // Preserve the decimal's stored scale exactly, mirroring Python's
    // format(Decimal, "f") -- trailing zeros are semantically part of the value's
    // canonical form and must not be normalized away, only integers written with
    // no decimal point.
    int scale = new System.Data.SqlTypes.SqlDecimal(value).Scale; // or: decimal.GetBits(value)[3] >> 16 & 0xFF
    if (scale == 0)
    {
        sb.Append(value.ToString(CultureInfo.InvariantCulture));
        return;
    }
    sb.Append(value.ToString("F" + scale, CultureInfo.InvariantCulture));
}
```
Then add a golden vector exercising a trailing-zero decimal (`100.00`, `2.50`) to `fixtures/golden/canonical-vectors.json` so both legs are pinned against the same byte-exact string, and add the equivalent C# unit test in `CanonicalJsonWriterTests.cs` (`Canonicalize_ShouldPreserveTrailingZeroScale`).

---

### CR-02: `compare_legs` classifies a real passed/failed-adjacent disagreement as "declared" when only one side is non-declarable — defeats D-14's silent-disagreement guarantee

**File:** `tools/de01/report.py:151-186` (the `all_declarable_with_warning` / `non_declarable_statuses` logic inside `compare_legs`)

**Issue:** The module's own docstring (`tools/de01/report.py:12-14`) states a declared non-equivalence requires "every differing leg's status is one of `unsupported`, `error`, `not_evaluated`, or `indeterminate` AND carries a non-empty warning." The implementation does not enforce this for legs whose status is *not* in `_DECLARABLE_STATUSES` — such a leg's status is simply never checked against the declarable set at all. The only place a non-declarable status can flip the outcome to `silent_disagreement` is the `len(non_declarable_statuses) > 1` check at line 169, which only fires when **two or more distinct** non-declarable statuses are present. A single non-declarable status (e.g. a lone `passed`) sitting alongside one or more declarable+warned statuses sails through as `declared_non_equivalence`.

**Verified by execution** against the real `tools/de01/report.py::compare_legs`:
```python
leg_a: canonicalStatus = "passed"                                    # non-declarable
leg_b: canonicalStatus = "unsupported", warnings = ["builtin not supported"]  # declarable+warned

compare_legs({"python": leg_a, "csharp": leg_b})
# => classification = "declared_non_equivalence", silent_disagreement_count = 0
```
Also reproduced with `unknown` (also non-declarable) vs `unsupported`+warning — same wrong result.

By contrast, the two-non-declarable-status case (`passed` vs `failed`, or `no_population` vs `failed`) IS correctly caught as `silent_disagreement` — confirmed by execution — because that path is guarded by the `len(non_declarable_statuses) > 1` check. The bug is specifically the *single* non-declarable status case.

**Failure scenario:** This is precisely the regression DE-01 exists to catch. If the C# evaluator silently regresses from correctly evaluating a rule (`passed`) to failing to support it (`unsupported`, with any warning text at all), and the Python leg still reports `passed`, `compare_legs` reports this as a "declared non-equivalence" and `silent_disagreement_count` stays `0`. The existing test suite (`tools/de01/tests/test_de01_runner.py`) never exercises this exact shape — its silent-disagreement tests only use two non-declarable statuses (`passed`/`failed`) or (`no_population`/`not_evaluated`); its declared-non-equivalence tests only use one declarable leg against another **declarable-or-identical** leg, never one declarable leg against a lone `passed`/`unknown`/`no_population` leg.

**Fix:** Require every *differing* status, not just declarable ones, to be individually validated. A leg's status only qualifies as part of a "declared" difference if it equals the majority/reference status or is itself declarable-with-warning:
```python
# A difference is declared only if EVERY leg's status is either (a) not a genuine
# difference (equal to at least one other leg reporting the same status is not the
# right test either -- simplest correct rule: every DISTINCT status present must
# itself be declarable-with-warning, with no exception for singleton non-declarable
# statuses).
non_declarable_statuses = statuses_seen - _DECLARABLE_STATUSES
if non_declarable_statuses:
    # ANY non-declarable status differing from another status is never declarable --
    # not just when two or more distinct non-declarable statuses are present.
    all_declarable_with_warning = False
```
i.e. change `if len(non_declarable_statuses) > 1:` to `if non_declarable_statuses:` (any non-empty set, not just size > 1) at line 169. Then add the regression test the current suite is missing: one leg `passed`, another leg `unsupported` with a warning, asserting `classification == "silent_disagreement"`.

## Warnings

### WR-01: `build_envelope` (Python) and `EvidenceEnvelopeFactory.Build` (C#) default to different roll-up statuses for an empty `rows` list

**File:** `data-service/evidence_contract.py:192-209` (`_rollup_status`, defaults to `CanonicalStatus.NO_POPULATION`) vs. `DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs:106-135` (`RollupStatus`, defaults to `EvidenceStatus.NotEvaluated`)

**Issue:** Both implementations are internally consistent and each is pinned by its own test (`DG/tests/DG.Tests/EvidenceContractTests.cs:177-181` asserts `NotEvaluated` for empty rows; the Python side documents `no_population` as its default in the docstring, though no test pins it directly). Both docstrings acknowledge the divergence and argue it's each call site's own choice of "what does empty mean here" — but this means if a Python caller and a C# caller both hit the empty-rows path for the same real-world situation without explicitly passing `roll_up`, they will emit different envelope-level `canonicalStatus` values for logically identical input. This is exactly the class of silent cross-language divergence the phase exists to prevent, even though neither implementation is "wrong" against its own spec text.

**Fix:** Either (a) pick one default and make both implementations match it, or (b) make the empty-rows case a required-argument situation in both languages (raise/require `roll_up` to be supplied explicitly rather than silently defaulting), removing the ambiguity entirely. At minimum, add a cross-reference note in both docstrings warning callers that they must not rely on the implicit default across languages, and add a DE-01 test fixture case that exercises an intentionally empty-rows envelope from both legs so a mismatch there would be caught by `compare_legs` rather than only by unit tests.

### WR-02: No golden vector exercises a decimal with non-canonical trailing-zero scale

**File:** `fixtures/golden/canonical-vectors.json` (all 5 vectors)

**Issue:** This is the root cause that let CR-01 ship undetected. The frozen shared golden-vector file — whose entire purpose is to guard cross-language canonicalization parity — has zero coverage for the exact class of value (`100.00`, `2.50`, `0.10`) most likely to appear in real evidence rows carrying money/measurement-like decimals with authored trailing zeros. `82.5` and `0.1` both happen to have no trailing zero, so this gap is invisible in the current suite.

**Fix:** Add a `canonicalJson` vector with a field like `"height": Decimal("100.00")` or `"ratio": Decimal("0.50")`, freeze its expected canonical string and digest (computed once and verified, per the file's own stated convention), and require both `data-service/tests/test_canonical_json.py` and `DG/tests/DG.Tests/CanonicalJsonWriterTests.cs` to assert against it. This is also the mechanical trigger that would have caught CR-01 immediately.

## Info

### IN-01: `_build_publish_evidence_envelope` never emits a `no_population` row for a rule with zero bindings in the publish path

**File:** `data-service/app.py:2140-2192` (`_build_publish_evidence_envelope`)

**Issue:** Per spec, a rule evaluated against an empty population should read `no_population`, appearing in the envelope with zero rows but a rule-level status. `_build_publish_evidence_envelope` only iterates rule ids that appear somewhere in an entity's `ruleIds`/`failedRuleIds`/`passedRuleIds`; a rule with a genuinely empty binding population across all entities in `entity_dicts` never surfaces at all in this function, and the envelope's roll-up would fall through to `_rollup_status`'s default (`no_population`) only coincidentally, not because this rule's own zero-population outcome was explicitly recorded. This is consistent with the phase's stated scope ("this phase does not migrate the codebase onto it" — §10 of the contract explicitly defers fixing `RuleEvaluator.cs:22-34`'s zero-binding collapse to Phase 1201), so this is not a defect against this phase's actual scope, just worth flagging for whoever picks up ALGN12-06.

**Fix:** No action required within Phase 1200's scope; note for Phase 1201's `no_population` migration work that the `data-service/app.py` publish path itself will also need a source of "which rules had zero bindings" before it can emit true `no_population` rows, since `entity_dicts` alone cannot represent an empty population.

---

## Verification Performed

**Executed (not merely reasoned about):**
- `python -m pytest data-service/tests/test_canonical_json.py data-service/tests/test_evidence_contract.py data-service/tests/test_golden_fixture_shape.py -q` → 46 passed (baseline confirmed).
- `python -m pytest tools/de01/tests/test_de01_runner.py -k "not live" -q` → 11 passed (baseline confirmed).
- `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~CanonicalJsonWriterTests|FullyQualifiedName~EvidenceContractTests"` → 32 passed (baseline confirmed).
- Built a throwaway console app referencing the real `DG.Core.csproj` and called `CanonicalJsonWriter.Canonicalize` directly on `{"amount": 100.00m}` and `{"ratio": 2.50m}` → reproduced CR-01.
- Ran `python3 -c "..."` against `decimal.Decimal`/`format(v, 'f')` for the same values → confirmed Python's correct, divergent behavior.
- Imported `tools/de01/report.py::compare_legs` directly with synthetic `LegResult` objects covering: identical statuses; `passed` vs `failed`; `no_population` vs `failed`; `passed` vs `unsupported`+warning; `unknown` vs `unsupported`+warning → reproduced CR-02 and confirmed the two-non-declarable-statuses path (WR-adjacent) works correctly.
- Confirmed via `System.Text.Json.Nodes.JsonNode.Parse("100.00").AsValue().TryGetValue<decimal>()` that a real upstream JSON literal with a trailing zero preserves scale in .NET, establishing this is reachable from real inputs, not just hand-constructed `decimal` literals.

**Reasoned about statically (not executed):**
- `app.py`'s sidecar hook control flow (try/except wrapping, ordering relative to `store_validation_run`) — read directly, the `try/except Exception` wrapping is unambiguous from the source.
- Schema/prose consistency between `spec/evidence-contract.schema.json` and `spec/EVIDENCE-CONTRACT.md` — read both in full, found no discrepancy.
- `EvidenceStatusNames.cs` / `evidence_contract.py`'s `CanonicalStatus` enum — visually cross-checked against the schema's `enum` array; matches. (Also mechanically enforced by `test_evidence_contract.py` and `EvidenceContractTests.cs`, both of which pass.)
- DE-01 leg adapters (`legs.py`), harness (`DG.De01Harness/Program.cs`), and `run_de01.py` were read but not executed (require live Neo4j/dotnet stack per the task's stated constraints); no defects found in the read-through beyond what's captured above.

---

_Reviewed: 2026-09-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
