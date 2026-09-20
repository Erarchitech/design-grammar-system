---
phase: 1201-rule-parser-and-evaluator-conformance
plan: 04
subsystem: SWRL subset documentation and conformance tests
tags: [swrl, parser, conformance, spec, drift-guard, csharp]
dependency-graph:
  requires: ["1201-01", "1201-02", "1201-03"]
  provides: ["fixtures/golden/parser/ conformance corpus (D-16)", "spec/SWRL-SUBSET.md normative doc (D-13, D-14)", "bidirectional drift guard binding doc to SupportedBuiltins and EvidenceStatusNames (D-15)"]
  affects: ["1201-06 (DE-01 re-run exit gate)"]
tech-stack:
  added: []
  patterns: ["MemberData-driven [Theory] over a JSON corpus with a separate count guard (precedent: table-driven test corpus in canonical-vectors.json)", "fenced machine-readable doc block read by a drift-guard test (precedent: Phase 35-12 GRAMMAR_CITATION_PATTERNS)"]
key-files:
  created:
    - fixtures/golden/parser/cases.json
    - fixtures/golden/parser/README.md
    - spec/SWRL-SUBSET.md
    - DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs
  modified:
    - CLAUDE.md
    - spec/EVIDENCE-CONTRACT.md
    - spec/RULE-PARTITION-POLICY.md
    - fixtures/golden/MANIFEST.md
decisions:
  - "Combined the corpus-driven [Theory]/count-guard/no-throw-guard test code (Task 1) with the two drift-guard tests (Task 2) into one commit, because the drift guards read spec/SWRL-SUBSET.md directly -- splitting Task 1's test-file work from Task 2's would leave an intermediate commit whose tests reference a file that does not yet exist. Same combining rationale 1201-03 used for its own tightly-coupled edits."
  - "Made ParserCase/ParserCorpus public (not private/internal) nested classes, required by xunit: a [Theory]'s MemberData-yielded parameter type must be at least as accessible as the test method itself (CS0051), which the plan's action text did not call out."
  - "resolverConfig empty map means 'call TryParse with no resolver argument at all' (exercises the parser's actual default), not 'construct an empty FakePredicateKindResolver' -- so the null-resolver corpus case genuinely covers TryParse's documented zero-argument default path, not just an equivalent-but-distinct resolver instance."
metrics:
  duration: "~50 minutes"
  completed: 2026-09-20
status: complete
---

# Phase 1201 Plan 04: SWRL Subset Boundary — Corpus, Spec Doc, and Drift Guard Summary

Nine table-driven parser conformance cases in `fixtures/golden/parser/cases.json`, a new normative
`spec/SWRL-SUBSET.md` with an explicit non-claims section, and a bidirectional drift guard proven —
by deliberately breaking it and watching it fail — to actually bind the doc's builtin/status claims
to `DG.Core.Validation.SupportedBuiltins` and the frozen `EvidenceStatus` vocabulary.

## What shipped

### Task 1 — Table-driven parser conformance corpus (D-16)

`fixtures/golden/parser/cases.json`: nine cases in a single JSON array (`cases`), each carrying `id`,
`description`, `expression`, `resolverConfig` (predicate-IRI→kind map; empty map means "call
`TryParse` with no resolver argument," exercising the parser's actual documented default), the
expected `EvidenceStatus` wire name, expected per-atom types in body-then-head order (or `null` when
no rule is produced), and expected diagnostic codes in order. Covers exactly the eight ROADMAP cases
(ObjectPropertyAtom, malformed arity, quoted commas, escaping, duplicate arrows, datatype literals,
language literals, unsupported syntax) plus the ninth: ObjectPropertyAtom parsed a second time under
the null-object resolver, since 1201-03-SUMMARY's own guidance names this as D-02's second half that
also needs locking down.

`fixtures/golden/parser/README.md`: what the corpus is for, that it is read by exactly
`SwrlSubsetConformanceTests` and nothing else, that it is additive to (never a replacement for) the
frozen `fixture.json` and does not alter that freeze policy, and a Change-Reason Log table mirroring
`MANIFEST.md`'s own — explicitly stated as lighter-weight than the frozen fixture's ceremony (a
logged reason, not a version bump) since this corpus is this phase's own deliverable, not a
cross-service contract.

`DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`: an xunit `[Theory]` (`ParserCase_ProducesExactlyTheDocumentedOutcome`)
fed by a `MemberData` source (`Cases()`) that deserializes and enumerates `cases.json` at test-run
time — adding a case to the JSON automatically adds a test, no test-side code change required. A
separate `[Fact]` (`Corpus_EveryCaseIsExecutedByTheTheoryAbove`) asserts the executed case count
equals the corpus length, making a silently-skipped case structurally impossible. A second `[Fact]`
(`NoCorpusCaseExpectsAThrownException`) drives every corpus case through `TryParse` directly and
asserts no exception is thrown, documenting D-01's never-throws contract as an explicit,
corpus-wide invariant rather than leaving it implicit in the theory's assertions. Used
`System.Text.Json` (already a dependency), and the same `FindRepoRoot()` repo-relative path
resolution pattern `EvidenceContractTests`/`CanonicalJsonWriterTests` already use, so the corpus
resolves correctly regardless of build configuration or working directory.

### Task 2 — `spec/SWRL-SUBSET.md` with non-claims section and bidirectional drift guard (D-13, D-14, D-15)

`spec/SWRL-SUBSET.md`, structured after `spec/RULE-PARTITION-POLICY.md`: an overview naming ALGN12-07,
a supported-subset section (the five atom types the parser emits, the six supported builtins with
their numeric-vs-non-numeric applicability carried inline per CONTEXT's discretion), a
recognize-versus-evaluate asymmetry section stating plainly — and quoting `RuleEvaluator`'s actual
refusal wording from 1201-02-SUMMARY.md verbatim — that the parser can now recognize an
`ObjectPropertyAtom` while the evaluator still cannot evaluate one, an explicit non-claims section
mapping every unsupported construct to the status it yields, a relationship-to-partition-policy
section that links to `spec/RULE-PARTITION-POLICY.md` rather than restating it, and enforcement /
consistency-propagation sections honest about what is and is not mechanically checked.

Two fenced, machine-readable blocks make the doc's claims checkable:

- `<!-- swrl-subset:supported-builtins:start/end -->` — one builtin name per line, read by
  `DocumentedBuiltins_MatchSupportedBuiltinsConstant_InBothDirections`, which asserts set equality
  (case-insensitive) against `DG.Core.Validation.SupportedBuiltins.Names` in **both** directions and
  names, in the failure message, which side has the extra entry.
- `<!-- swrl-subset:non-claims-statuses:start/end -->` — one status wire name per line, mirroring the
  human-readable non-claims table's status column in the same order, read by
  `NonClaimsStatuses_AreAllRealEvidenceStatusWireNames`, which asserts every entry parses via
  `EvidenceStatusNames.TryParseWireName`.

**Guard verification (recorded per the plan's explicit instruction — an unverified guard is not a
guard):** added `swrlb:fakeInducedDriftTest` to the doc's fenced builtin block, re-ran the filtered
test suite, and confirmed `DocumentedBuiltins_MatchSupportedBuiltinsConstant_InBothDirections` failed
with message `"...Documented-but-not-in-code: [swrlb:fakeInducedDriftTest]. In-code-but-not-documented:
[]. Edit whichever side is missing an entry so the two match exactly."` (12 passed, 1 failed, 13
total). Reverted the addition; the suite returned to 13/13 passed. See the Verification table below
for the exact commands run.

### Task 3 — Scoped propagation per `CLAUDE.md` § Schema Change Propagation

Followed the plan's own explicit scoping (not a literal "RESEARCH question H" — no such labeled
question exists verbatim in `1201-RESEARCH.md`; the plan's own Task 3 action text carries the actual
scoping instruction, which was followed directly): added a cross-reference line to `CLAUDE.md`'s
propagation list (same shape as the existing `RULE-PARTITION-POLICY.md`/`EVIDENCE-CONTRACT.md`
lines), an additive line in `spec/EVIDENCE-CONTRACT.md`'s top-level related-specs list and its § 11
Consistency & Propagation, an additive line in `spec/RULE-PARTITION-POLICY.md`'s related-specs line,
and a pointer to the new `parser/` subdirectory in `fixtures/golden/MANIFEST.md` explicitly stating
it is additive and does not alter the freeze policy (no `FIXTURE_VERSION` bump — confirmed still
`1.2.0`).

**No propagation-list entry outside the plan's own scoping was found genuinely implicated.**
`cypher_template.txt`, `training/dataset_schema.json`, the n8n workflow prompts, and
`config.template.js` all govern graph *schema* (node labels, properties, Cypher shapes); this phase
adds a documentation and status-emission boundary with zero graph-schema change, so none of those
four were touched, matching the plan's explicit instruction not to sweep the full list.

### Task 4 — Full .NET suite regression check

## Verification (actual command output)

| Check | Command | Result |
|---|---|---|
| Corpus + drift-guard tests (baseline) | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~SwrlSubsetConformance"` | **13 passed, 0 failed, 13 total** |
| Induced drift-guard failure | (added `swrlb:fakeInducedDriftTest` to `spec/SWRL-SUBSET.md`'s fenced block, re-ran the same filter) | **12 passed, 1 failed, 13 total** — `DocumentedBuiltins_MatchSupportedBuiltinsConstant_InBothDirections` failed with `"...Documented-but-not-in-code: [swrlb:fakeInducedDriftTest]..."` |
| Drift-guard reverted | (removed the fake entry, re-ran the same filter) | **13 passed, 0 failed, 13 total** |
| Task 3 propagation check | `grep -c "SWRL-SUBSET" CLAUDE.md spec/EVIDENCE-CONTRACT.md spec/RULE-PARTITION-POLICY.md; grep -c "1.2.0" fixtures/golden/MANIFEST.md; git diff --stat fixtures/golden/fixture.json \| wc -l` | `CLAUDE.md:1`, `spec/EVIDENCE-CONTRACT.md:2`, `spec/RULE-PARTITION-POLICY.md:1`, `2`, `0` |
| Release build, both TFMs | `dotnet build DG/DG.sln -c Release` | **0 Warning(s), 0 Error(s)** — `net7.0` and `net9.0` both emitted for `DG.Core` |
| Full suite (run 1) | `dotnet test DG/tests/DG.Tests/` | **502 passed, 0 failed, 502 total** |
| Full suite (run 2) | `dotnet test DG/tests/DG.Tests/` | **502 passed, 0 failed, 502 total** |
| Exactly one precedence table | `grep -rn "EvidenceStatus.Indeterminate," DG/src/DG.Core/ --include=*.cs \| wc -l` | **1** |
| Frozen fixtures untouched | `git diff --stat fixtures/golden/fixture.json fixtures/golden/seed.cypher fixtures/golden/canonical-vectors.json` | **empty** |

Test count moved from plan 03's reported 489 to **502**, so this plan added 13 tests (9 theory cases
+ 4 facts: the count guard, the no-throw guard, and the two drift guards). No `DesignStateValidationFlowTests`
failure was observed in either full-suite run this session (this environment did not have the compose
stack's Neo4j/data-service reachable, consistent with those tests either being skipped or fast-failing
identically both times — no regression attributable to this plan's changes either way, since this
plan touched zero files those tests exercise).

## Guards held

- Exactly one rollup precedence table in the codebase (unchanged from plan 03 — this plan added no
  new precedence logic).
- `fixtures/golden/fixture.json`, `seed.cypher`, `canonical-vectors.json` all zero-diff.
- `net7.0`/`net9.0` both build clean — no .NET 8+-only API introduced (the new test file uses only
  `System.Text.Json`, LINQ, and `File`/`Path`/`DirectoryInfo`, all available on both TFMs; the new
  spec doc introduces no code).
- The bidirectional drift guard was **observed failing** on a real induced mismatch before being
  reverted — not merely asserted to work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `ParserCase`/`ParserCorpus` needed to be `public`, not `private`, nested classes**
- **Found during:** Task 1, first build (`dotnet build DG/DG.sln -c Release`).
- **Issue:** `CS0051` — a `[Theory]`'s `MemberData`-yielded parameter type must be at least as
  accessible as the test method itself; `ParserCase` was declared `private sealed class` while
  `ParserCase_ProducesExactlyTheDocumentedOutcome(ParserCase testCase)` is `public`.
- **Fix:** Changed both `ParserCase` and `ParserCorpus` to `public sealed class`.
- **Files modified:** `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`
- **Commit:** `f6e56dc`

No other auto-fixes were needed — the corpus's expected outcomes were derived by direct inspection
of `SwrlRuleParser.cs`'s dispatch order (traced line-by-line during planning of this plan's own
corpus content, not guessed), and every one of the nine cases passed on the first test run once the
accessibility fix above was applied.

No Rule 4 (architectural) triggers. No auth gates. No package installs.

## For plan 1201-06 (DE-01 re-run exit gate)

This plan touches only `DG.Core` test/doc/fixture surfaces (`fixtures/golden/parser/`,
`spec/SWRL-SUBSET.md`, `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`) plus four cross-reference
lines in `CLAUDE.md`/`spec/EVIDENCE-CONTRACT.md`/`spec/RULE-PARTITION-POLICY.md`/
`fixtures/golden/MANIFEST.md`. It does **not** touch `dg-reasoner`, `data-service`, `tools/de01`, or
`ontology/dg-shapes.ttl` — the D-09 SHACL-targeting fix, the D-11 DE-01 re-run, and the D-12
inputHash/outputHash live-boundary fix are all still open and are 1201-06's job, not this plan's.

**What plan 06 can rely on from this plan:** the C# leg's parser-level behavior for every one of the
eight ROADMAP cases (plus the null-resolver ObjectPropertyAtom counterpart) is now locked down by a
passing, drift-guarded test suite. If DE-01's re-run surfaces a C#-leg parser disagreement that does
not match one of the nine documented outcomes in `fixtures/golden/parser/cases.json` or
`spec/SWRL-SUBSET.md`'s non-claims table, that is a genuine new finding for plan 06 to investigate —
not something this plan's corpus already covers by a different name.

**One thing plan 06 should NOT do:** widen `spec/SWRL-SUBSET.md`'s supported-builtin list or
non-claims section to make a DE-01 disagreement disappear. Per this plan's own governing instruction
("do not write documentation that claims more than the code does"), any doc change to accommodate a
DE-01 finding must be accompanied by the matching `SupportedBuiltins.Names`/`EvidenceStatus` code
change the drift guard would then require — the guard exists precisely to prevent a doc-only "fix."

## Threat Flags

None new. The threat model's two `mitigate`-disposition items for this plan are exactly what Tasks 1
and 2 implement:

- T-1201-10 (Spoofing, doc capability claims): the bidirectional drift guard, proven to actually fail
  on an induced mismatch, is the mitigation.
- T-1201-11 (Repudiation, corpus completeness): `Corpus_EveryCaseIsExecutedByTheTheoryAbove` is the
  mitigation.

## Known Stubs

None. No hardcoded empty values, placeholder text, or unwired data sources were introduced. Every
corpus case's expected outcome was verified against the parser's actual behavior via a passing test,
not asserted speculatively.

## Self-Check: PASSED

All four created files confirmed present on disk:
- `fixtures/golden/parser/cases.json` — FOUND
- `fixtures/golden/parser/README.md` — FOUND
- `spec/SWRL-SUBSET.md` — FOUND
- `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs` — FOUND

All three commit hashes confirmed present in `git log --oneline`:
- `c4b347a` — FOUND
- `f6e56dc` — FOUND
- `d65e7d7` — FOUND
