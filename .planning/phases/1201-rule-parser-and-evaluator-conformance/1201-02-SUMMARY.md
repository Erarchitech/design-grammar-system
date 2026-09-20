---
phase: 1201-rule-parser-and-evaluator-conformance
plan: 02
subsystem: DG.Core evaluator and publish boundary
tags: [evidence-contract, evaluator, status-rollup, csharp]
dependency-graph:
  requires: ["1201-01"]
  provides: ["EvaluateAtom typed dispatch (D-14)", "TryResolveArg (D-08)", "ValidationPublishRuleResult.Status (not_evaluated boundary)"]
  affects: ["1201-03 (parser ObjectPropertyAtom emission)", "1201-04 (spec/SWRL-SUBSET.md wording)", "1201-06 (DE-01 re-run)"]
tech-stack:
  added: []
  patterns: ["Try*-shape resolution instead of throw-and-catch", "atom-type dispatch before variable-availability check"]
key-files:
  created: []
  modified:
    - DG/src/DG.Core/Validation/RuleEvaluator.cs
    - DG/src/DG.Core/Validation/ValidationPublishPackageBuilder.cs
    - DG/src/DG.Core/Models/ValidationPublishRuleResult.cs
    - DG/tests/DG.Tests/RuleEvaluatorTests.cs
    - DG/tests/DG.Tests/ValidationPublishPackageBuilderTests.cs
decisions:
  - "D-06/D-08/D-14 transcribed verbatim from the frozen D-05 situation table, per the plan's own instruction not to re-litigate them at execution time."
  - "Renamed and rewrote EvaluateRule_ShouldReturnFailingBindingsWhenVariableIsMissing (now EvaluateRule_ShouldReturnUnknownWhenVariableIsMissing) because it encoded the pre-1201 collapsing behavior this plan deliberately changes."
metrics:
  duration: "~40 minutes"
  completed: 2026-09-20
status: complete
---

# Phase 1201 Plan 02: Zero-bindings, unresolvable-binding, and ObjectPropertyAtom typed outcomes; publish-boundary not_evaluated Summary

Closed the three remaining evaluator collapse sites plan 01 left open (D-06 empty population,
D-08 unresolvable binding, D-14 ObjectPropertyAtom asymmetry) and carried the typed status across
`ValidationPublishPackageBuilder` to the publish boundary, so a rule that was never evaluated is
now distinguishable from one that was evaluated and violated.

## What shipped

### Task 1 — Zero bindings → `no_population`, unresolvable binding → `unknown` (D-06, D-08)

- `RuleEvaluator.EvaluateRule`'s zero-binding early return kept `Status = EvidenceStatus.NoPopulation`
  (already present from plan 01's scaffolding) and the message was reworded to
  `"Rule evaluated with an empty binding population: no bindings were provided."` — no longer reads
  as a verdict, no `violated`/`failed` wording.
- Replaced both `InvalidOperationException` throw sites (`EvaluateAtom`'s variable-availability loop
  and the old `ResolveArgValue`) with a new `TryResolveArg(AtomArg, BindingRow, out object? value,
  out string? unknownDetail)` try-shape, named after the existing `TryResolveVariableValue` in the
  same file per the plan's instruction. A missing variable now returns
  `BindingOutcome(EvidenceStatus.Unknown, detail)` with a What+Where+How-to-fix message instead of
  throwing.
- `EvaluateBuiltin`'s two calls to the old `ResolveArgValue` (wrapped in try/catch) became two direct
  `TryResolveArg` calls, each returning `Unknown` on failure — no exception path remains here either.
- `EvaluateRule` now tracks `unknownDetail` the same way it already tracked `unsupportedDetail`, and
  surfaces it in the rule-level message when the rolled-up status is `Unknown`.
- The `catch (Exception ex)` block's doc-comment was rewritten to explicitly name the four outcomes
  that used to reach it as thrown exceptions and no longer do (empty population, unresolvable
  binding, ObjectPropertyAtom/unsupported-atom-type, unsupported/malformed builtin), and states it is
  now reachable only by a genuine unexpected fault in the evaluation mechanism itself.

### Task 2 — ObjectPropertyAtom / UnsupportedAtom / unrecognized atom type → `unsupported` (D-14)

`EvaluateAtom` was restructured from a two-branch (`BuiltinAtom` / everything-else) dispatch into an
explicit four-way dispatch, in this order:

1. `BuiltinAtom` → `EvaluateBuiltin`, unchanged.
2. `ObjectPropertyAtom` or `UnsupportedAtom` (ordinal-ignore-case) → `ObjectPropertyOrUnsupportedOutcome`,
   a typed `Unsupported` refusal driven by atom type alone — it does **not** attempt to resolve the
   atom's variables first, so a fully-bound `ObjectPropertyAtom` is still refused rather than
   reported as satisfied. This is the exact assertion the plan's done-condition names as closing the
   Pitfall-1 trap.
3. Anything that is not `ClassAtom` or `DataPropertyAtom` either (an atom type string this evaluator
   does not recognize at all) → the same `ObjectPropertyOrUnsupportedOutcome` refusal.
4. `ClassAtom` / `DataPropertyAtom` → the pre-existing variable-availability check, now via
   `TryResolveArg` instead of throwing (task 1's change), otherwise byte-identical behavior.

No evaluation implementation was added for `ObjectPropertyAtom` — per the plan's explicit
instruction, that would be the general-reasoner claim D-14 disclaims. The refusal detail wording:

> What: this atom's predicate ('{predicate}') is an object property, which this evaluator
> recognizes but does not evaluate. Where: atom '{atom.Id}', predicate '{predicate}'. How to fix:
> express the constraint using a datatype property and one of the supported comparison builtins, or
> accept this typed non-verdict.

**This exact wording is what plan 04 should quote consistently in `spec/SWRL-SUBSET.md`'s
non-claims section**, per the plan's output instruction.

Constructed `Atom`/`AtomArg` instances directly in tests (not via `SwrlRuleParser`), matching the
plan's explicit instruction not to depend on plan 03's parser changes.

### Task 3 — Publish boundary carries typed status; missing result is `not_evaluated`

- `ValidationPublishRuleResult` gained an additive `Status` of `DG.Core.Contracts.EvidenceStatus`,
  with the same non-authoritative-`Passed` doc-comment pattern as `RuleEvaluationResult.Status`.
- `ValidationPublishPackageBuilder.Build`'s `resultById.TryGetValue` miss now sets
  `Status = EvidenceStatus.NotEvaluated` alongside the existing `Passed = false`, with a code comment
  citing the contract's distinction between "never evaluated" (`not_evaluated`) and "evaluated and
  could not resolve" (`unknown`).
- On the hit path, `result.Status` is copied verbatim onto `ruleResult.Status` — never recomputed
  from `result.Passed`. An `Unsupported` evaluator result now publishes as `Unsupported`, not
  disguised as an ordinary violation.
- Entity-level per-object logic (`statusByEntity`, `refByEntity`, `bindingByEntity`,
  `FailedEntityIds`/`PassedEntityIds`) was left untouched, per the plan's explicit instruction that
  per-object canonical verdicts are Phase 1202's scope (ALGN12-10).

### Task 4 — Re-proved both TFMs and the full suite

## Verification (actual command output)

| Check | Command | Result |
|---|---|---|
| RuleEvaluatorTests | `dotnet test --filter "FullyQualifiedName~RuleEvaluator"` | **11 passed, 0 failed** |
| ValidationPublishPackageBuilderTests | `dotnet test --filter "FullyQualifiedName~ValidationPublishPackageBuilder"` | **7 passed, 0 failed** |
| Release build, both TFMs | `dotnet build DG/DG.sln -c Release` | **0 warnings, 0 errors** — `net7.0` and `net9.0` both emitted for `DG.Core` |
| Full `.NET` test suite | `dotnet test DG/tests/DG.Tests/` | **run 5 times: 465/0/465, 465/0/465, 464/1/465, 4/0/4 (filtered E2E retry), 465/0/465** (see note below) |
| No `InvalidOperationException`/`NotSupportedException` left in RuleEvaluator | `grep -cE 'throw new (NotSupportedException\|InvalidOperationException)' DG/src/DG.Core/Validation/RuleEvaluator.cs` | **0** |
| Exactly one precedence table | `grep -rn "EvidenceStatus.Indeterminate," DG/src/DG.Core/ --include=*.cs \| wc -l` | **1** |
| Frozen fixture untouched | `git diff --stat fixtures/golden/fixture.json` | **empty** |

**Note on the E2E test count vs. the plan's stated baseline (451 passed / 3 failed / 454 total,
0 or exactly 4 known-Neo4j-dependent failures allowed):** I ran the full suite four times across this
session to get a true read on stability, since the compose stack is up per the plan's environment
note:

1. `465 passed, 0 failed, 465 total`
2. `465 passed, 0 failed, 465 total`
3. `464 passed, 1 failed, 465 total` — `DG.Tests.E2E.DesignStateValidationFlowTests.HappyPath_StatePublishAndRetrieve`
   failed with `Assert.True() Failure: Expected: True Actual: False` at line 93/110.
4. (filtered to only `~E2E`, immediately after run 3) `4 passed, 0 failed, 4 total` — the same test
   that failed in run 3 passed with zero code changes in between.
5. (full suite again) `465 passed, 0 failed, 465 total`.

`DesignStateValidationFlowTests` (`DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs`) opens a
live Bolt connection to `bolt://localhost:7687` and an `HttpClient` against `http://localhost:8000`
in `InitializeAsync` — a real dependency on the live compose stack's Neo4j and data-service
containers, neither of which this plan's files (`DG.Core/Validation`, `DG.Core/Models`) touch or
could affect. The intermittent single failure is consistent with the plan's own framing of this test
class as environment-dependent, not a regression: this plan changed zero lines outside
`DG.Core/Validation/RuleEvaluator.cs`, `DG.Core/Validation/ValidationPublishPackageBuilder.cs`, and
`DG.Core/Models/ValidationPublishRuleResult.cs`, none of which this E2E test's assertion path
exercises differently before/after this plan. Reporting the actual measured spread here rather than
picking the two clean runs, per this plan's "do not manufacture agreement" instruction — the honest
reading is: this plan introduced zero new failures, and the pre-existing Neo4j-dependent flakiness is
exactly what the plan's baseline already carved out (albeit manifesting as an intermittent 1-of-4
inside that test class rather than a consistent 4-of-4, which is a looser environment than the
plan anticipated, not a stricter one).

Test count moved from plan 01's reported 454 to 465, so this plan added 11 tests:
`RuleEvaluatorTests` went from 3 `[Fact]`s to 11 (8 new, 1 renamed and rewritten — see Deviations
below), and `ValidationPublishPackageBuilderTests` went from 4 `[Fact]`s to 7 (3 new).

## Guards held

- Exactly one rollup precedence table in the codebase (`StatusRollup.Precedence`, used verbatim,
  no second table authored).
- `fixtures/golden/fixture.json` zero-diff.
- `net7.0`/`net9.0` both build clean (no .NET 8+ API introduced).
- `Passed` retained on both `RuleEvaluationResult` and `ValidationPublishRuleResult`, documented
  non-authoritative; nothing in this plan infers a canonical status from a boolean anywhere.

## Final `EvaluateAtom` dispatch order (for plan 03/04 reference)

1. `atom.Type == "BuiltinAtom"` (ordinal-ignore-case) → `EvaluateBuiltin`.
2. `atom.Type == "ObjectPropertyAtom"` or `"UnsupportedAtom"` → `ObjectPropertyOrUnsupportedOutcome`
   (typed `Unsupported`, atom-type-driven, no variable resolution attempted first).
3. `atom.Type` is neither `"ClassAtom"` nor `"DataPropertyAtom"` (catch-all for any future/unknown
   atom type string) → the same `ObjectPropertyOrUnsupportedOutcome` refusal.
4. `atom.Type == "ClassAtom"` or `"DataPropertyAtom"` → variable-availability check via
   `TryResolveArg`; `Unknown` if any referenced variable is unresolved, otherwise `Failed` (matches,
   violation-pattern inversion).

This order is deliberate: branch 2/3 come **before** branch 4, so an `ObjectPropertyAtom` a future
parser emits can never fall through to the availability check and be silently reported as satisfied.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `EvaluateRule`'s message switch did not surface `Unknown`'s detail**
- **Found during:** Task 1, first test run.
- **Issue:** After replacing the throw with a typed `Unknown` outcome, the rule-level message fell
  through to the generic `$"Rule evaluation resolved to {status}."` branch instead of surfacing the
  specific "which variable is missing" detail — a new test asserting the message contained the
  missing variable name (`?h`) failed.
- **Fix:** Added an `unknownDetail` tracking variable to `EvaluateRule`, mirroring the pre-existing
  `unsupportedDetail` pattern, and added an `EvidenceStatus.Unknown` arm to the message `switch`.
- **Files modified:** `DG/src/DG.Core/Validation/RuleEvaluator.cs`
- **Commit:** `4ca902f`

### Pre-existing test updated (named per deviation protocol)

**`RuleEvaluatorTests.EvaluateRule_ShouldReturnFailingBindingsWhenVariableIsMissing` → renamed to
`EvaluateRule_ShouldReturnUnknownWhenVariableIsMissing`.** This test encoded the pre-1201 collapsing
behavior (missing variable → thrown exception → caught by the evaluator's catch-all → counted as a
failing binding, i.e. an ordinary violation). D-08 of the frozen Phase 1200 D-05 situation table
requires this to be a typed `unknown` non-verdict instead. Renamed and rewrote its assertions to
check `Status == EvidenceStatus.Unknown`, `FailingBindings` is empty, and the message still names the
missing variable. Commit `4ca902f`.

No other pre-existing test required rewriting. No architectural deviations (no Rule 4 triggers).

## Threat Flags

None. The two STRIDE items this plan's threat model named (T-1201-03 DoS via throw sites, T-1201-05
Spoofing via ObjectPropertyAtom false-satisfied) are the two behaviors this plan implements as
mitigations, not new surface introduced beyond what the plan already registered. T-1201-04
(Repudiation, the publish-boundary `not_evaluated` gap) is likewise the mitigation this plan ships,
not a new flag.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced.

## Commits

- `4ca902f` — feat(1201-02): route zero bindings, unresolvable variables, and ObjectPropertyAtom to
  typed non-verdicts (D-06, D-08, D-14)
- `1d53e7d` — feat(1201-02): carry typed evaluator status across the publish boundary; missing
  result is not_evaluated
- `c7ef148` — docs(1201-02): tighten BindingOutcome doc-comment to name all D-14 non-verdict sources
  (doc-only, no behavior change)

## For plan 1201-03 (parser ObjectPropertyAtom emission)

- The evaluator now refuses `ObjectPropertyAtom` and `UnsupportedAtom` with a typed `Unsupported`
  outcome **before** you teach the parser to emit either type. You can proceed without re-checking
  this — `EvaluateAtom`'s dispatch order (documented above) guarantees a newly-emitted
  `ObjectPropertyAtom` will be refused, not silently reported as satisfied.
- `RuleEvaluatorTests` already has four `[Fact]`s exercising `ObjectPropertyAtom`/`UnsupportedAtom`/
  unrecognized-type/`ClassAtom`+`DataPropertyAtom` behavior, built by constructing `Atom` instances
  directly. When plan 03 lands, consider adding an integration-level test that exercises the same
  path through `SwrlRuleParser.Parse` once it can actually emit `ObjectPropertyAtom`, to prove the
  two components compose correctly (not required by this plan; a suggestion for that plan's scope).

## For plan 1201-04 (spec/SWRL-SUBSET.md)

Quote the ObjectPropertyAtom refusal detail wording verbatim from `ObjectPropertyOrUnsupportedOutcome`
in `RuleEvaluator.cs` (reproduced above under Task 2) so the runtime message and the spec's
non-claims section stay consistent, per D-14's requirement.

## For plan 1201-06 (DE-01 re-run)

Per 1201-05's summary, `OBJ_GOLD_EMPTY` previously disagreed across legs: `unknown` (data-service) /
`not_evaluated` (dg-reasoner) / `no_population` (csharp) / `unknown` (replay). This plan's D-06 fix
means the **csharp leg's `no_population` for an empty-population case was already correct** — this
plan did not change that leg's answer for `OBJ_GOLD_EMPTY` (it was already right); nothing here
touches the data-service or replay legs, which are Python. If those two legs still report `unknown`
for a genuinely empty population after this plan, that is a data-service/replay-side defect outside
this plan's file scope (`DG/src/DG.Core/...` only), not something this plan closes. Re-run DE-01
live to measure the actual current cross-leg agreement before assuming this phase's other plans
(01/02) already resolved it — plan 02's scope was the C# evaluator and publish boundary only.

## Self-Check: PASSED

All five source/test files created/modified by this plan were confirmed present on disk, and all
three commit hashes (`4ca902f`, `1d53e7d`, `c7ef148`) were confirmed present in `git log --oneline
--all` after this summary was written.

