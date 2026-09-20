# fixtures/golden/parser/ — SWRL Parser Conformance Corpus

**Added:** Phase 1201 plan 04 (D-16), requirement ALGN12-07.

## What this is

`cases.json` is a table-driven corpus of `SwrlRuleParser.TryParse` conformance cases, covering the
eight ROADMAP parser deliverables plus one additional case (nine total — see below). It is read by
exactly one consumer: `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`, via an xunit `[Theory]` fed
by a `MemberData` source that enumerates the file. Adding a case to `cases.json` automatically adds a
test for it; a separate count-guard fact (`Corpus_EveryCaseIsExecutedByTheTheoryAbove`) asserts the
executed case count equals the corpus length, so a case present in the file but silently skipped is
impossible.

**Nothing else reads this file.** In particular, no Python leg, no n8n workflow, and no service
outside `DG.Tests` consumes it. Per 1200 D-09, per-service copies of any fixture are forbidden — this
corpus lives once, here, under the shared `fixtures/golden/` root.

## Relationship to `fixtures/golden/fixture.json`

This corpus is **separate from, and additive to,** the frozen `fixtures/golden/fixture.json`
(1200 D-11). This plan never edits `fixture.json`, `seed.cypher`, or `canonical-vectors.json` — see
`../MANIFEST.md` for that freeze policy, which this corpus does not alter in any way. The two
corpora test different things: `fixture.json` is the one cross-service golden fixture all four DE-01
legs read as the same bytes; `cases.json` here is parser-only, C#-only, unit-test-only.

## Freeze status — this corpus is NOT frozen the way `fixture.json` is

This is this phase's own deliverable, not a cross-service contract artifact. A later phase **may**
extend `cases.json` with new cases without any version-bump ceremony. However, **changing an
existing case's expectation** (its `expectedStatus`, `expectedAtomTypes`, or
`expectedDiagnosticCodes`) requires a logged reason in the Change-Reason Log below — the same
discipline `../MANIFEST.md` applies to the frozen fixture, scoped down to "log why," not "bump a
shared version number."

## Case shape

Each entry in `cases.json`'s `cases` array carries:

| Field | Meaning |
|---|---|
| `id` | Stable case identifier. |
| `description` | What the case demonstrates and why. |
| `expression` | The raw SWRL expression text to parse. |
| `resolverConfig` | A predicate-IRI-to-kind map (`"ObjectProperty"` \| `"DatatypeProperty"`). An empty map means "parse with no resolver argument" — the null-object resolver, `TryParse`'s documented default. |
| `expectedStatus` | The expected `SwrlParseResult.Status` wire name (`passed`, `unsupported`, `error`, etc.). |
| `expectedAtomTypes` | The expected atom `Type` values, in body-then-head order, or `null` when no rule is produced at all. |
| `expectedDiagnosticCodes` | The expected `ParseDiagnostic.Code` values, in order. |
| `expectedArgCount` *(optional)* | Expected argument count on the first body atom. |
| `expectedFirstAtomSecondArgValue` / `Datatype` / `Language` *(optional)* | Expected literal-argument shape on the first body atom's second argument, for the literal-parsing cases. |
| `expectRuleNull` *(optional)* | When `true`, asserts `Result.Rule` is `null` instead of checking atom types. |

## The nine cases

The eight ROADMAP cases (ObjectPropertyAtom, malformed arity, quoted commas, escaping, duplicate
arrows, datatype literals, language literals, unsupported syntax) plus a ninth: the ObjectPropertyAtom
case is present **twice** — once parsed with a resolver reporting it as an `ObjectProperty`, and once
parsed with the null-object resolver (no `resolverConfig` entries). Both are D-02's two halves and
both need locking down: the resolved case proves `ObjectPropertyAtom` is reachable at all; the
null-resolver case proves the parser's *default* behavior (no resolver supplied) never guesses.

No case in this corpus expects a thrown exception from `TryParse` — `NoCorpusCaseExpectsAThrownException`
asserts this for every case, since `TryParse` never throws by contract (D-01).

## Change-Reason Log

| Date | Reason | Changed by |
|---|---|---|
| 2026-09-20 | Initial corpus — 9 cases covering the 8 ROADMAP parser deliverables plus the null-resolver ObjectPropertyAtom counterpart (D-02's second half). | Phase 1201-04 executor |
