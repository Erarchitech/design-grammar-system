---
phase: 1200-contract-status-vocabulary-evidence-envelope-and-golden-fixt
reviewed: 2026-09-20T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs
  - DG/tests/DG.Tests/CanonicalJsonWriterTests.cs
  - data-service/tests/test_canonical_json.py
  - fixtures/golden/MANIFEST.md
  - fixtures/golden/canonical-vectors.json
  - spec/EVIDENCE-CONTRACT.md
  - tools/de01/report.py
  - tools/de01/tests/test_de01_runner.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 1200: Code Review Report

**Reviewed:** 2026-09-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the gap-closure diffs for CR-01 (C# `CanonicalJsonWriter.WriteNumberDecimal` decimal-scale
loss) and CR-02 (`compare_legs`'s non-declarable-status guard under-reporting silent disagreements).

**CR-01 verification.** I independently recomputed all six `sha256Upper` digests in
`fixtures/golden/canonical-vectors.json` (both `scalarTuple` and `canonicalJson` kinds) against
their accompanying `joined`/`canonical` strings using Python's `hashlib.sha256` — all six match
exactly. I also compiled and ran the actual `WriteNumberDecimal` logic (scale extracted from
`decimal.GetBits`, rendered via `ToString("F{scale}")`) against negative values, scale 0, scale 28,
and `decimal.MaxValue`, confirming the fix is correct for those cases and that the trailing-zero
regression (`100.00m` → `"100.00"`, `2.50m` → `"2.50"`) is genuinely fixed. However, I found and
proved a **new, untested divergence the fix introduces for negative zero** — see WR-01. This is the
same bug class CR-01 exists to close (a decimal rendering divergence between the C# and Python
legs), just a different input than the one CR-01's regression tests cover.

**CR-02 verification.** I traced `compare_legs`'s branch logic by hand and against its own test
suite. The fix (`if non_declarable_statuses:` replacing a `len(...) > 1` guard) correctly closes
the reported gap without over-correcting: two differing *declarable-and-warned* statuses (e.g.
`unsupported` vs `error`, both warned) still classify as `declared_non_equivalence`
(`test_two_declarable_warned_statuses_differing_is_still_declared`), while a lone non-declarable
status paired with a declarable-and-warned one (the exact CR-02 shape, plus the `unknown`-vs-
`unsupported` variant) now correctly classifies as `silent_disagreement`. No legitimate declared
non-equivalence is collapsed into silent by this change. I did not find a correctness defect in
the `compare_legs` fix itself.

**Other findings.** One quality issue in `CanonicalJsonWriter.WriteValue`'s type-dispatch order
(dead code for two branches under a realistic input path) and a minor documentation/consistency
gap in the manifest are noted below as INFO.

## Warnings

### WR-01: Negative-zero decimal breaks cross-language hash parity (unfixed by CR-01)

**File:** `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:212-231` (`WriteNumberDecimal`)
**Issue:**

The CR-01 fix correctly preserves stored scale for ordinary values, but C#'s
`decimal.ToString("F{scale}")` silently drops the sign of a negative-zero decimal, while Python's
`format(Decimal, "f")` — the explicitly-cited reference rendering
(`spec/EVIDENCE-CONTRACT.md` §6 rule 2) — preserves it. I verified this directly:

```
# Python (data-service/canonical_json.py:118 calls format(value, "f") on a Decimal)
>>> format(Decimal('-0.00'), 'f')
'-0.00'
>>> format(Decimal('-0'), 'f')
'-0'
```

```csharp
// C# — compiled and run against the actual WriteNumberDecimal logic
var negZero = new decimal(0, 0, 0, true, 2); // -0.00, sign bit set via decimal.GetBits
negZero.ToString("F2", CultureInfo.InvariantCulture);   // => "0.00"  (sign lost)

var negZeroScale0 = new decimal(0, 0, 0, true, 0);       // -0
negZeroScale0.ToString(CultureInfo.InvariantCulture);    // => "0"    (sign lost)
```

A negative-zero `decimal` is a realistic runtime value, not a contrived edge case — it arises from
subtraction (`0m - 0.00m`), multiplication by a negative factor (`-1m * 0.00m`), or any rule
evaluation whose computed delta nets to exactly zero at a given scale while carrying a negative
sign bit (e.g. a height-margin calculation that computes `actual - limit` and rounds to `0.00`
from the negative side). Because `CanonicalJsonWriter` is documented as "byte-identical in
behavior to `data-service/canonical_json.py`" and this exact divergence is the class of bug CR-01
was created to close, this is a real (if narrow) re-opening of the parity gap the gap-closure plan
was meant to fully close. None of the six golden vectors in `canonical-vectors.json` exercise a
negative value at all (let alone negative zero), so this gap is currently untested on both legs.

**Fix:** Detect and preserve the sign explicitly before formatting, since `ToString("F{scale}")`
normalizes negative zero away:

```csharp
private static void WriteNumberDecimal(decimal value, StringBuilder sb, string path)
{
    var bits = decimal.GetBits(value);
    var scale = (bits[3] >> 16) & 0xFF;
    var isNegative = (bits[3] & unchecked((int)0x80000000)) != 0;

    var rendered = scale == 0
        ? value.ToString(CultureInfo.InvariantCulture)
        : value.ToString("F" + scale.ToString(CultureInfo.InvariantCulture), CultureInfo.InvariantCulture);

    // decimal.ToString normalizes negative zero's sign away (e.g. -0.00m -> "0.00"), but
    // Python's format(Decimal, "f") preserves it ("-0.00"). Re-attach the sign to match.
    if (isNegative && !rendered.StartsWith('-'))
    {
        rendered = "-" + rendered;
    }

    sb.Append(rendered);
}
```

Add a golden vector covering `Decimal("-0.00")` (and ideally `Decimal("-0")`) to
`fixtures/golden/canonical-vectors.json`, bump `fixtures/golden/MANIFEST.md`'s
`FIXTURE_VERSION`, and add regression facts to both `CanonicalJsonWriterTests.cs` and
`test_canonical_json.py` mirroring the existing `Canonicalize_ShouldPreserveTrailingZeroScale`
pattern, before considering CR-01 fully closed.

### WR-02: `WriteValue`'s `long`/`int` branches are unreachable for any parsed JSON input

**File:** `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:172-210`
**Issue:**

`WriteValue` checks `TryGetValue<decimal>` (line 186) before `TryGetValue<long>` (line 197) and
`TryGetValue<int>` (line 203). I verified by compiling and running the actual dispatch that for any
`JsonNode` produced by `JsonNode.Parse` (i.e., real JSON text, as opposed to a hand-constructed
`JsonValue.Create(3L)`), a bare integer literal like `1` satisfies `TryGetValue<decimal>` and is
always claimed by the decimal branch first:

```csharp
var node = JsonNode.Parse("{\"b\":1}");
var val = node!["b"]!.AsValue();
val.TryGetValue<decimal>(out var d);  // true, d == 1
val.TryGetValue<long>(out var l);     // also true, but never reached — decimal already matched
```

This happens to still produce the correct output (`"1"`, since a scale-0 decimal renders with no
decimal point) but means the `long`/`int` branches at lines 197-207 are dead code for the realistic
input path — any producer that builds its `JsonNode` tree via `JsonNode.Parse` (as
`CanonicalJsonWriterTests.ParseAsDecimalPreservingNode` explicitly does — it converts every JSON
number to `JsonValue.Create(element.GetDecimal())`, never to `long`/`int`) will never exercise
them. This is a code-quality issue (dead branches, misleading dispatch order suggesting `long`/`int`
are live alternatives) rather than a correctness bug today, but it means a future refactor "cleaning
up" the apparently-unused `long`/`int` branches would be safe from a test-coverage standpoint yet
could silently remove behavior some other, non-test caller depends on (e.g. a hand-built
`JsonValue.Create(3L)` node from a future producer) without any test catching the regression.

**Fix:** Either remove the dead `long`/`int` branches and document that `decimal` and `JsonElement`-
backed numeric `JsonValue`s are the only supported numeric representations (matching the class's
comment that "non-integers only from `decimal`"), or add an explicit test that constructs a
`JsonValue.Create(3L)` / `JsonValue.Create(3)` node directly (not via `JsonNode.Parse`) to prove the
`long`/`int` branches are actually reachable and intentionally retained.

## Info

### IN-01: No golden vector exercises a negative number of any kind

**File:** `fixtures/golden/canonical-vectors.json`
**Issue:** All six vectors use only non-negative values (`82.5`, `3`, `100.00`, `2.50`, `0.1`, `0`).
The task's own review brief asked specifically about "negative decimals" as an edge case; none of
the current vectors would have caught WR-01, and none would catch a simpler negative-value
regression (e.g. an implementation that mishandles the sign for an ordinary negative fixed-point
value, not just negative zero).
**Fix:** Add at least one ordinary negative value (e.g. `-12.50`) alongside the negative-zero
vector recommended in WR-01, per the freeze policy in `fixtures/golden/MANIFEST.md` (version bump
+ Change-Reason Log entry).

### IN-02: `MANIFEST.md`'s freeze date and phase's own git history are same-day but out of visible order

**File:** `fixtures/golden/MANIFEST.md:4,58-59`
**Issue:** The manifest's header states a single "Freeze date: 2026-09-20" and the Change-Reason Log
records both the `1.0.0` initial freeze and the `1.1.0` CR-01 amendment as the same date. This is
consistent with the actual commit timestamps I found (`e0059a8`, `375faec` both dated
2026-09-20), so this is not a factual error — flagging only because a freeze policy document that
allows same-day version bumps without a time component in the log makes it harder to audit *order*
of changes purely from the manifest (only `git log` disambiguates). Not a defect, just a
minor traceability gap.
**Fix:** Optional: add a timestamp (not just date) to Change-Reason Log rows, or reference the
commit hash, to make same-day amendments independently orderable from the manifest alone.

---

_Reviewed: 2026-09-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
