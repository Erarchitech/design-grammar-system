---
phase: 1201-rule-parser-and-evaluator-conformance
plan: 03
subsystem: DG.Core parser
tags: [swrl, parser, evidence-contract, csharp, neo4j]
dependency-graph:
  requires: ["1201-01", "1201-02"]
  provides: ["SwrlRuleParser.TryParse (D-01)", "IPredicateKindResolver + NullPredicateKindResolver + Neo4jPredicateKindResolver (D-02)", "ObjectPropertyAtom emission, UnsupportedAtom emission (D-02, D-03)", "ParseDiagnostic (D-04)", "quote-aware SplitArgs/SplitAtomChain, datatype/language literals (Task 3)"]
  affects: ["1201-04 (fixtures/golden/parser/ corpus and spec/SWRL-SUBSET.md)", "1201-06 (DE-01 re-run)"]
tech-stack:
  added: []
  patterns: ["Try*-shape non-throwing entry point over an existing throwing method (RecognitionMarker.TryParse precedent)", "injected resolver interface with a null-object default (IRuleRepository/Neo4jRuleRepository precedent)", "single-pass quote-aware linear scanner instead of regex for a client-text-adjacent split (DoS avoidance)"]
key-files:
  created:
    - DG/src/DG.Core/Parsing/ParseDiagnostic.cs
    - DG/src/DG.Core/Parsing/IPredicateKindResolver.cs
    - DG/src/DG.Core/Parsing/SwrlParseResult.cs
    - DG/src/DG.Core/Data/Neo4jPredicateKindResolver.cs
    - DG/tests/DG.Tests/SwrlRuleParserTryParseTests.cs
  modified:
    - DG/src/DG.Core/Parsing/SwrlRuleParser.cs
    - DG/src/DG.Core/Models/AtomArg.cs
    - DG/tests/DG.Tests/RuleEvaluatorTests.cs
decisions:
  - "Combined the SplitArgs (Task 2 scope: SplitArgs is untouched by Task 2's own action text, but Task 3 rewrites it) and TryParseQuotedLiteral changes into the same SwrlRuleParser.cs edit as the Task 2 TryParse/ResolveAtomType rewrite, since both land in one file and are tightly coupled -- committed as one feat commit rather than artificially splitting Task 2 and Task 3 into separate commits with an intermediate broken state."
  - "SplitAtomChain (new, not named in the plan) replaces the naive chain.Split('^') in ParseAtoms with a quote-aware linear scanner, because Task 3's own '^^' datatype-suffix literal ("75.5\"^^xsd:decimal) collides with SWRL's '^' atom-conjunction separator otherwise -- a real bug the plan's own fixture case would have hit, not a speculative addition."
  - "TryParseQuotedLiteral now also handles the plain (no ^^/@ suffix) quoted-literal case, not only the two suffixed forms -- necessary so a backslash-escaped quote inside an unsuffixed string literal is honored (Task 3's escaping requirement) instead of falling through to the old naive Trim('\"','\\'') fallback, which does not unescape."
metrics:
  duration: "~55 minutes"
  completed: 2026-09-20
status: complete
---

# Phase 1201 Plan 03: Rule Parser TryParse, IPredicateKindResolver, and Literal Parsing Conformance Summary

`SwrlRuleParser.TryParse` never throws and resolves `ObjectPropertyAtom` vs `DataPropertyAtom` via an
injected `IPredicateKindResolver` (Neo4j-backed bulk snapshot, null-object default) instead of
guessing; quoted commas, backslash escaping, and `^^`/`@lang` literal suffixes are now parsed
correctly by single-pass linear scanners with no regex backtracking risk.

## What shipped

### Task 1 — `ParseDiagnostic`, `IPredicateKindResolver` with null-object default, `SwrlParseResult`

- `ParseDiagnostic` (sealed record): `Code` (from a nested `Codes` static class — `EmptyExpression`,
  `ArrowArity`, `AtomRegexMiss`, `UnresolvablePredicateKind`, `UnterminatedQuotedLiteral`), `Message`
  (What+Where+How-to-fix), `Offset` (currently always `-1` — none of this plan's diagnostic sites had
  a natural single-character offset to report; see Deviations), `Status` (`EvidenceStatus`).
- `PredicateKind` enum (`ObjectProperty`, `DatatypeProperty`) and `IPredicateKindResolver` interface
  with a single synchronous `TryGetKind(string, out PredicateKind)`. Doc-comment states the
  bulk-snapshot granularity decision verbatim from the plan.
- `NullPredicateKindResolver.Instance`: always returns `false`. Doc-comment states bluntly that this
  is the entire point of the type.
- `SwrlParseResult` (sealed record): `Status`, `Rule` (nullable), `Diagnostics`. `Create` factory
  rolls up via `StatusRollup.Rollup` — empty diagnostics + a produced rule is `Passed`; anything else
  routes through the one shipped precedence table. No second table authored.

### Task 2 — `TryParse`, resolver-driven `ResolveAtomType`, `Parse` as thin wrapper (D-01, D-02, D-03)

- `TryParse(string?, IPredicateKindResolver? = null)`: `resolver ??= NullPredicateKindResolver.Instance`
  as the first line. Empty/whitespace input and non-exactly-one-arrow input each produce one `Error`
  diagnostic and return with `Rule = null`, never throwing. A per-atom regex miss produces an
  `Unsupported` diagnostic **and** emits an `UnsupportedAtom` for that atom (predicate = the raw
  unmatched text) — the atom is kept, not dropped, and parsing continues with the remaining atoms.
- `ResolveAtomType` dispatch order: `swrlb:` prefix → `BuiltinAtom` (resolver never consulted);
  ≤1 arg → `ClassAtom` (resolver never consulted); otherwise `resolver.TryGetKind` —
  `ObjectProperty` → `ObjectPropertyAtom` (**reachable for the first time**), `DatatypeProperty` →
  `DataPropertyAtom`, a `false` return → `UnsupportedAtom` plus an `UnresolvablePredicateKind`
  diagnostic. **There is no code path that returns `DataPropertyAtom` for an unresolved predicate** —
  verified by `grep -n "DataPropertyAtom" DG/src/DG.Core/Parsing/SwrlRuleParser.cs`, which shows
  exactly one production site, gated by `PredicateKind.DatatypeProperty`.
- `Parse` is now a thin wrapper: calls `TryParse` with the default resolver, and re-throws the same
  exception type/message as before for `EmptyExpression` (`ArgumentException`, param name
  `swrlExpression`), `ArrowArity` (`FormatException`), and `AtomRegexMiss` (`FormatException`, using
  the new diagnostic's message text — functionally equivalent to the old inline message). Critically,
  an `UnresolvablePredicateKind` diagnostic does **not** make `Parse` throw: before this plan such a
  predicate silently became `DataPropertyAtom` and `Parse` returned successfully, so throwing now
  would be a breaking change for every current caller. `Parse`'s doc-comment states this asymmetry
  explicitly and points to `TryParse`.

### Task 3 — quoted commas, escaping, `^^` datatype and `@lang` literals

- `SplitArgs` rewritten as a single-pass linear scanner (`StringBuilder` + `activeQuote`/`escapeNext`
  state), never a regex, per RESEARCH's explicit DoS-avoidance instruction. Honors a backslash escape
  for the active quote character; an unterminated quoted literal at end-of-input emits an
  `UnterminatedQuotedLiteral` diagnostic and returns cleanly (no throw, no silent mis-split, no
  trailing partial token emitted).
- `TryParseQuotedLiteral` (new): recognizes a quoted literal's explicit datatype suffix (`"75.5"^^xsd:decimal`
  → `Datatype = "xsd:decimal"` verbatim, not re-inferred) and language tag (`"Tower"@en` →
  `Datatype = "xsd:string"`, `Language = "en"`), and — see Deviations — also now handles the plain
  unsuffixed quoted-literal case through the same quote-aware unescaping path, so a
  backslash-escaped quote inside an ordinary string literal (`"Tower \"North\""`) unescapes to
  `Tower "North"` instead of leaving the backslashes in the value.
- `AtomArg.Language` (new, nullable, additive-only, defaults to `null`): every existing construction
  site is unaffected.
- Existing inference for unsuffixed boolean/integer/decimal/string literals is byte-identical —
  `TryParseQuotedLiteral` only intercepts tokens that start with a quote character; the
  bool/decimal/fallback-string chain runs unchanged for everything else.

**Deviation (not in the plan's action text, required for correctness): `SplitAtomChain`.**
`ParseAtoms`'s chain-level split (`chain.Split('^', ...)`, the SWRL atom-conjunction separator) is
naive and collides with Task 3's own `^^` datatype-suffix syntax — `"75.5"^^xsd:decimal` contains a
literal `^^` that the old naive split would treat as two atom separators, breaking the atom in half.
This is not a hypothetical: the plan's own Task 3 behavior spec requires `"75.5"^^xsd:decimal` to
parse correctly, and it does not without this fix (verified: the `TryParse_ExplicitDatatypeSuffix_RecordsDatatypeVerbatim_NotReinferred`
test failed with "the collection contained 2 items" before this fix, `Assert.Single` after). Added
`SplitAtomChain`, a quote-aware linear scanner mirroring `SplitArgs`'s approach: consumes `^^` as a
unit (never splits inside it) and honors quoted literals, so a lone unquoted `^` still conjoins two
atoms but a `^^` datatype-suffix marker inside or after a literal never does. Rule 1 (auto-fix bug) —
this is a genuine defect in the naive pre-existing split, surfaced by this plan's own new literal
syntax, fixed inline, verified by the full parser test suite.

### Task 4 — `Neo4jPredicateKindResolver`

- `Neo4jPredicateKindResolver.LoadAsync(ConnectionInfo, CancellationToken)`: one Cypher query
  (`MATCH (p) WHERE (p:ObjectProperty OR p:DatatypeProperty) AND p.project = $project RETURN p.iri AS
  iri, p:ObjectProperty AS isObjectProperty`) scoped by the `project` property per the repo-wide
  isolation convention, mirroring `Neo4jRuleRepository`'s connection-handling style (`GraphDatabase.Driver`
  + `AsyncSession` + `QueryTimeout` via `WaitAsync`). Returns a resolver wrapping an in-memory
  `Dictionary<string, PredicateKind>` (`StringComparer.Ordinal` — IRIs are case-sensitive).
- `TryGetKind` is a synchronous dictionary lookup — no I/O, safe to call from
  `RuleEvaluator.EvaluateRules`' per-rule parse loop without incurring N round trips.
- `FromSnapshotForTesting` (internal): constructs a resolver directly from a map, used by three unit
  tests (known `ObjectProperty`, known `DatatypeProperty`, absent IRI) — no live Neo4j connection, per
  the plan's explicit instruction that the `neo4j` hostname resolves only inside compose.

### Task 5 — full suite regression check

Ran `dotnet test DG/tests/DG.Tests/` three times consecutively: **489 passed, 0 failed, 489 total**
each time (test count moved from plan 02's 465 to 489 — this plan added 24 tests: 22 new facts in
`SwrlRuleParserTryParseTests.cs`, 2 net-new named helper facts folded into the rewritten
`RuleEvaluatorTests.HeightRule` fixture). No flake observed across the three runs this session
(unlike plan 02's session, which saw one intermittent `DesignStateValidationFlowTests` failure in 5
runs — see Deviations for the concrete regression this plan did hit and fix, which is unrelated to
that Neo4j E2E flake).

## Verification (actual command output)

| Check | Command | Result |
|---|---|---|
| Release build, both TFMs | `dotnet build DG/DG.sln -c Release` | **0 Warning(s), 0 Error(s)** — `DG.Core -> ...\net7.0\DG.Core.dll` and `DG.Core -> ...\net9.0\DG.Core.dll` both emitted |
| SwrlRuleParser tests | `dotnet test --filter "FullyQualifiedName~SwrlRuleParser"` | **25 passed, 0 failed, 25 total** |
| Full suite (run 1) | `dotnet test DG/tests/DG.Tests/` | **489 passed, 0 failed, 489 total** |
| Full suite (run 2) | `dotnet test DG/tests/DG.Tests/` | **489 passed, 0 failed, 489 total** |
| Full suite (run 3) | `dotnet test DG/tests/DG.Tests/` | **489 passed, 0 failed, 489 total** |
| Exactly one precedence table | `grep -rn "EvidenceStatus.Indeterminate," DG/src/DG.Core/ --include=*.cs \| wc -l` | **1** |
| Frozen fixture untouched | `git diff --stat fixtures/golden/fixture.json` | **empty** |
| No `DataPropertyAtom` guessing fallback | `grep -n "DataPropertyAtom" DG/src/DG.Core/Parsing/SwrlRuleParser.cs` | one production site only, at `PredicateKind.DatatypeProperty => "DataPropertyAtom"`; the accompanying comment names the removed guess explicitly |

## Guards held

- Exactly one rollup precedence table (`StatusRollup.Precedence`), used verbatim via `SwrlParseResult.Create`.
- `fixtures/golden/fixture.json` zero-diff.
- `net7.0`/`net9.0` both build clean — no .NET 8+-only API introduced (verified: no `ThrowIfNullOrWhiteSpace`,
  no collection expressions, no frozen collections in any new/changed file).
- `SwrlRuleParser` remains a `public static class`; `TryParse(string?, IPredicateKindResolver? = null)`
  is an additive optional-parameter overload — no existing `Parse(string)` call site required a change.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ParseAtoms`'s naive `chain.Split('^')` collided with Task 3's own `^^` datatype-suffix syntax**
- **Found during:** Task 3, first test run (`TryParse_ExplicitDatatypeSuffix_RecordsDatatypeVerbatim_NotReinferred` failed with "the collection contained 2 items" — the atom was split in half on the `^^` marker).
- **Issue:** `chain.Split('^', ...)` treats every `^` character as an atom-conjunction separator, including the two carets inside a `"75.5"^^xsd:decimal` literal datatype suffix that Task 3 itself introduces support for.
- **Fix:** Added `SplitAtomChain`, a single-pass quote-aware linear scanner (same style as `SplitArgs`) that consumes a `^^` pair as a unit and honors quoted literals, so only a lone unquoted `^` conjoins two atoms.
- **Files modified:** `DG/src/DG.Core/Parsing/SwrlRuleParser.cs`
- **Commit:** `4850aa2`

**2. [Rule 1 - Bug] `TryParseQuotedLiteral` did not handle the plain (no-suffix) quoted-literal case, so a backslash-escaped quote in an ordinary string literal was not unescaped**
- **Found during:** Task 3, first test run (`TryParse_BackslashEscapedQuote_DoesNotTerminateLiteral` asserted `Tower "North"` but got `Tower \"North\"` — backslashes retained).
- **Issue:** `TryParseQuotedLiteral` only returned `true` (a parsed arg) for the two suffixed forms (`^^datatype`, `@lang`); a plain quoted literal with no suffix fell through to the pre-existing naive `trimmed.Trim('"', '\'')` fallback at the bottom of `ParseArg`, which strips only the outermost quote characters and does not process backslash escapes.
- **Fix:** Extended `TryParseQuotedLiteral` to also return the unescaped value (via the same `Unescape` helper the suffixed forms already used) for a plain quoted literal with no suffix, so all three forms (plain, datatype-suffixed, language-tagged) share one quote-aware, escape-aware code path.
- **Files modified:** `DG/src/DG.Core/Parsing/SwrlRuleParser.cs`
- **Commit:** `4850aa2`

### Pre-existing tests updated (named per deviation protocol, explicitly expected by the plan)

**`RuleEvaluatorTests`: `EvaluateRule_ShouldFailWhenHeightExceedsLimit`, `EvaluateRule_ShouldMatchBindingsWithoutQuestionMarkPrefix`, `EvaluateRule_ShouldReturnUnknownWhenVariableIsMissing`, `EvaluateRule_ShouldReturnUnknownForBuiltinArgumentMissingFromBinding`, `EvaluateRule_ShouldRollUpToFailedWhenOneBindingUnresolvableAndOneViolates`, `EvaluateRule_ShouldRollUpToUnknownWhenOneBindingUnresolvableAndOneSatisfied` (6 tests, `RuleEvaluatorTests.cs`).**

This is exactly the scenario the plan's own instructions named as expected. `RuleEvaluator.EvaluateRule`'s
`rule.BodyAtoms.Count == 0` fallback path (`RuleEvaluator.cs:59`, owned by plan 01/02, **not** modified
by this plan) calls `SwrlRuleParser.Parse(rule.Swrl)` with no resolver. Before this plan, the 2-arg
predicate `hasHeightM(?b,?h)` in these tests' `Swrl` text was silently guessed as `DataPropertyAtom`
there, so the height rule genuinely evaluated. After this plan's D-02 fix, the same call correctly
produces `UnsupportedAtom` (no resolver was ever injected at this call site — that is out of this
plan's file scope, since `RuleEvaluator.cs` belongs to plan 02), so all six tests started failing with
`EvidenceStatus.Unsupported` instead of their expected `Failed`/`Unknown`/`Passed`.

This is **not** the literal "asserts `DataPropertyAtom` for a 2-arg predicate parsed without a
resolver" case the plan anticipated (none of these tests assert `atom.Type` directly — they assert
`RuleEvaluationResult.Status`/`Passed`/`FailingBindings`), but it is the same root cause: a test
relying on the old guessing behavior via indirect SWRL-text auto-parsing. Per the plan's instruction
not to quietly edit such a test, the fix and its rationale are named here explicitly, not folded
silently into the parser commit.

**Fix:** rewrote `HeightRule()` (the shared fixture used by all 6 tests) to pre-populate
`rule.BodyAtoms` directly with hand-built `ClassAtom`/`DataPropertyAtom`/`BuiltinAtom` instances —
the same direct-construction pattern the file's own pre-existing D-14 dispatch tests
(`EvaluateRule_ShouldReturnUnsupportedForObjectPropertyAtomEvenWhenFullyBound` etc.) already use —
instead of relying on `EvaluateRule`'s implicit, resolver-less SWRL-text parsing. This exercises
`RuleEvaluator`'s evaluation logic without depending on parser behavior this plan deliberately
changed, and does not touch `RuleEvaluator.cs` (out of scope).

**Files modified:** `DG/tests/DG.Tests/RuleEvaluatorTests.cs`
**Commit:** `6611c10` (separate commit from the parser change, per deviation protocol — named explicitly, not folded in)

No other pre-existing test required rewriting. No architectural deviations (no Rule 4 triggers) —
adding a resolver-injection point to `RuleEvaluator.EvaluateRule` itself was considered and explicitly
rejected as out of scope (that file belongs to plan 02, and the plan's own text states the compounding
defect at that call site is a known, accepted consequence of this plan's D-02 fix, to be handled by
whichever future plan wires a resolver into the evaluator's parse call — not named as this plan's job).

## Threat Flags

None new. The threat model's four `mitigate`-disposition items (T-1201-06 DoS via quoted-literal
handling, T-1201-07 DoS via `Parse` throw sites, T-1201-08 Spoofing via guessed `DataPropertyAtom`,
T-1201-09 Information Disclosure via cross-project resolver reads) are exactly the four things this
plan implements as mitigations:

- T-1201-06: `SplitArgs` and the new `SplitAtomChain` are both single-pass linear scanners, no regex,
  no backtracking risk.
- T-1201-07: `TryParse` never throws for any input.
- T-1201-08: `ResolveAtomType` has no fallback branch that yields `DataPropertyAtom` for an
  unresolved predicate.
- T-1201-09: `Neo4jPredicateKindResolver`'s snapshot query is scoped by `p.project = $project`.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced.
`Neo4jPredicateKindResolver.LoadAsync` is a genuine, complete implementation — not called from any
production code path yet (that wiring, if any, belongs to a future plan), which is consistent with
this plan's scope being the parser and resolver infrastructure, not their production call sites.

## For plan 1201-04 (fixtures/golden/parser/ corpus and spec/SWRL-SUBSET.md)

**Exact parser outcomes to document, verbatim from this plan's shipped behavior:**

1. **Empty/whitespace expression** → `SwrlParseResult.Status = Error`, one `ParseDiagnostic` with
   `Code = ParseDiagnostic.Codes.EmptyExpression` (`"empty-expression"`), `Rule = null`.
2. **Not exactly one `->`** → `Status = Error`, one diagnostic with `Code = ArrowArity`
   (`"arrow-arity"`), `Rule = null`.
3. **An atom that does not match `predicate(args)`** → the atom is emitted as `Type = "UnsupportedAtom"`
   (its `PredicateIri`/`PredicateLabel` set to the raw unmatched text), one diagnostic with
   `Code = AtomRegexMiss` (`"atom-regex-miss"`), `Status = Unsupported`. **The rule is still produced**
   with the surrounding well-formed atoms intact (D-03: never dropped).
4. **A ≥2-arg, non-`swrlb:` predicate resolved as `ObjectProperty`** → `Type = "ObjectPropertyAtom"`
   (first time this type is reachable from the parser).
5. **...resolved as `DatatypeProperty`** → `Type = "DataPropertyAtom"`.
6. **...unresolvable** (no resolver, or resolver returns `false`) → `Type = "UnsupportedAtom"`, one
   diagnostic with `Code = UnresolvablePredicateKind` (`"unresolvable-predicate-kind"`),
   `Status = Unsupported`. **This is the default behavior of `Parse()`/`TryParse()` with no resolver
   argument** — the single most important fixture case, since it is the parser's new default.
7. **1-arg non-`swrlb:` predicate** → `Type = "ClassAtom"`, resolver never consulted.
8. **`swrlb:`-prefixed predicate** → `Type = "BuiltinAtom"`, resolver never consulted.
9. **Quoted literal with an embedded comma** (`"Tower, North"`) → splits into the correct arg count,
   comma preserved inside the value.
10. **Backslash-escaped quote inside a literal** (`"Tower \"North\""`) → unescapes to `Tower "North"`
    (the escape is consumed, not left in the value).
11. **Unterminated quoted literal** → one diagnostic with `Code = UnterminatedQuotedLiteral`
    (`"unterminated-quoted-literal"`), `Status = Unsupported`, no throw, no mis-split; the malformed
    argument list contributes no further args past the unterminated point.
12. **Explicit datatype suffix** (`"75.5"^^xsd:decimal`) → `Value = "75.5"`, `Datatype = "xsd:decimal"`
    **verbatim as given**, not re-inferred from the lexical form.
13. **Language tag** (`"Tower"@en`) → `Value = "Tower"`, `Datatype = "xsd:string"`, `Language = "en"`.
14. **Unsuffixed literals** (unchanged): `true`/`false` → `xsd:boolean`; a numeric with no `.` →
    `xsd:integer`; a numeric with `.` → `xsd:decimal`; anything else (quoted or not) → `xsd:string`,
    `Language = null`.
15. **`Parse(string)` (throwing wrapper)**: throws `ArgumentException` (param `swrlExpression`) for
    case 1, `FormatException` for case 2, `FormatException` (message = the diagnostic's message) for
    case 3. **Does NOT throw for case 6** (unresolvable predicate kind) — returns successfully with an
    `UnsupportedAtom` in place. This asymmetry (documented in `Parse`'s doc-comment) is itself worth a
    fixture/spec case, since it is easy to assume `Parse` throws on anything `TryParse` flags.

**Diagnostic code set** (from `ParseDiagnostic.Codes`, all string constants, all currently emitted
with `Offset = -1` — see the open item below): `empty-expression`, `arrow-arity`, `atom-regex-miss`,
`unresolvable-predicate-kind`, `unterminated-quoted-literal`.

**Open item for plan 04 to note in `spec/SWRL-SUBSET.md` if relevant:** every `ParseDiagnostic` this
plan emits carries `Offset = -1` (not positional). The record type supports a real character offset,
but none of this plan's five diagnostic sites had a clean, low-risk way to compute one without
re-deriving position tracking through the regex/split pipeline, and the plan's `<behavior>` spec for
each diagnostic never required a real offset — only "a message" and, implicitly, a diagnostic object.
If `spec/SWRL-SUBSET.md` or a future consumer needs real offsets, that is net-new work, not a
completed-but-unverified claim from this plan.

**`IPredicateKindResolver`/`SwrlParseResult` signatures for plan 04's fixture-driven tests to consume:**

```csharp
public enum PredicateKind { ObjectProperty = 0, DatatypeProperty = 1 }

public interface IPredicateKindResolver
{
    bool TryGetKind(string predicateIri, out PredicateKind kind);
}

public sealed class NullPredicateKindResolver : IPredicateKindResolver
{
    public static readonly NullPredicateKindResolver Instance;
}

public sealed record SwrlParseResult(
    EvidenceStatus Status,
    ParsedSwrlRule? Rule,
    IReadOnlyList<ParseDiagnostic> Diagnostics);

public sealed record ParseDiagnostic(string Code, string Message, int Offset, EvidenceStatus Status)
{
    public static class Codes { /* five string constants, see above */ }
}

public static class SwrlRuleParser
{
    public static ParsedSwrlRule Parse(string swrlExpression); // throws, unchanged signature
    public static SwrlParseResult TryParse(string? swrlExpression, IPredicateKindResolver? resolver = null); // new
}
```

## For plan 1201-06 (DE-01 re-run)

This plan does not touch `dg-reasoner`, `data-service`, `tools/de01`, or `ontology/dg-shapes.ttl` —
its file scope is entirely `DG.Core` parser/data/tests. `ObjectPropertyAtom` is now genuinely
reachable from `SwrlRuleParser.TryParse` when a resolver is supplied and resolves the predicate as an
`ObjectProperty` — but no production call site in this codebase yet constructs and injects a
`Neo4jPredicateKindResolver` into a `TryParse`/`Parse` call (that wiring is out of this plan's scope).
`RuleEvaluator.EvaluateRule`'s fallback path (`SwrlRuleParser.Parse(rule.Swrl)`, no resolver) still
uses the null-object resolver, so any live rule with a ≥2-arg predicate not already present as
`Rule.BodyAtoms` in the graph will evaluate as `Unsupported` today, not `ObjectPropertyAtom`-typed —
this is the D-02 recognize/evaluate-input asymmetry the plan's objective section calls out, now
also an asymmetry between "resolver exists" and "resolver is wired into the hot evaluation path."
If DE-01's golden fixture relies on `Rule.BodyAtoms` being pre-populated from Neo4j (via
`Neo4jRuleRepository.GetRulesAsync`, which does populate atoms from the graph directly, bypassing
`SwrlRuleParser.Parse` entirely for rules that already have `HAS_BODY`/`HAS_HEAD` edges), this
asymmetry does not affect it. It would only surface for a rule relying on `Rule.Swrl` text re-parsing
with no atoms already materialized in the graph.

## Self-Check: PASSED

All five files this plan created were confirmed present on disk:
- `DG/src/DG.Core/Parsing/ParseDiagnostic.cs` — FOUND
- `DG/src/DG.Core/Parsing/IPredicateKindResolver.cs` — FOUND
- `DG/src/DG.Core/Parsing/SwrlParseResult.cs` — FOUND
- `DG/src/DG.Core/Data/Neo4jPredicateKindResolver.cs` — FOUND
- `DG/tests/DG.Tests/SwrlRuleParserTryParseTests.cs` — FOUND

All four commit hashes were confirmed present in `git log --oneline --all`:
- `f4c3cd5` — FOUND
- `4850aa2` — FOUND
- `6611c10` — FOUND
- `ab43bc3` — FOUND
