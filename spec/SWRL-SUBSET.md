# SWRL Subset — Supported Constructs and Non-Claims

## Overview

This document is the **normative boundary contract** between the schema-level SWRL atom vocabulary
(what `SwrlRuleParser` can *recognize* in an ingested rule expression) and the bounded C# evaluator
subset that `RuleEvaluator` actually *implements*. It fulfills requirement **ALGN12-07**: a
documented distinction between the two, and an explicit, machine-checked refusal to claim the C#
path is a general SWRL/OWL reasoner.

**This document does not claim more than the code does.** Every "supported" claim below is bound to
a production constant or a passing test; every "not supported" claim is bound to the typed status it
actually yields, verified against `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs`.

**Normative scope:**
1. [Supported Subset](#1-supported-subset)
2. [The Recognize-versus-Evaluate Asymmetry](#2-the-recognize-versus-evaluate-asymmetry)
3. [Non-Claims (D-14)](#3-non-claims-d-14)
4. [Relationship to the Partition Policy](#4-relationship-to-the-partition-policy)
5. [Enforcement](#5-enforcement)
6. [Consistency & Propagation](#6-consistency--propagation)

Related specs: `spec/EVIDENCE-CONTRACT.md` (the status vocabulary every outcome below is drawn from —
authoritative for what each status *means*), `spec/RULE-PARTITION-POLICY.md` (the SWRL-vs-SHACL
ownership line this document's scope sits entirely inside), `DG/src/DG.Core/Validation/SupportedBuiltins.cs`
(the production allow-list this document's builtin list is bound to by [§5](#5-enforcement)'s drift
guard).

---

## 1. Supported Subset

### 1.1 Atom types the parser emits

`SwrlRuleParser.TryParse` (Phase 1201, D-01) classifies every atom in a rule expression into exactly
one of four types:

| Atom type | When emitted |
|---|---|
| `BuiltinAtom` | Predicate has the `swrlb:` prefix (resolver never consulted). |
| `ClassAtom` | Predicate has ≤1 argument (resolver never consulted). |
| `DataPropertyAtom` | Predicate has ≥2 arguments and an injected `IPredicateKindResolver` resolves it as an `owl:DatatypeProperty`. |
| `ObjectPropertyAtom` | Predicate has ≥2 arguments and an injected `IPredicateKindResolver` resolves it as an `owl:ObjectProperty` (Phase 1201, D-02 — the first phase this atom type is reachable at all). |
| `UnsupportedAtom` | The atom's text does not match the required `predicate(args)` shape, **or** a ≥2-argument, non-`swrlb:` predicate's kind cannot be resolved (no resolver supplied, or the resolver reports it unknown). Never dropped (D-03) — always emitted alongside a diagnostic. |

`SwrlRuleParser.Parse(string)` — the pre-Phase-1201 throwing entry point — is retained as a thin
wrapper over `TryParse` for every existing caller. It still throws `ArgumentException` for an empty
expression and `FormatException` for an arity/regex failure, but it does **not** throw for an
unresolvable predicate kind: that case returns successfully with an `UnsupportedAtom` in place,
exactly as `TryParse` does. This asymmetry is intentional (documented on `Parse`'s own doc-comment)
and is itself one of the nine corpus cases in `fixtures/golden/parser/cases.json`.

### 1.2 Supported builtins

The evaluator implements exactly six `swrlb:`-prefixed comparison builtins. This is the D-15
machine-checkable allow-list — the fenced block immediately below is read verbatim by
`SwrlSubsetConformanceTests.DocumentedBuiltins_MatchSupportedBuiltinsConstant_InBothDirections`,
which asserts it matches `DG.Core.Validation.SupportedBuiltins.Names` exactly, in both directions.
Editing this block without editing the constant (or vice versa) fails that test.

<!-- swrl-subset:supported-builtins:start -->
```
swrlb:lessThan
swrlb:greaterThan
swrlb:lessThanOrEqual
swrlb:greaterThanOrEqual
swrlb:equal
swrlb:notEqual
```
<!-- swrl-subset:supported-builtins:end -->

**Numeric-versus-non-numeric applicability:** all six compare numeric (`decimal`-convertible)
arguments. Four of the six — `lessThan`, `greaterThan`, `lessThanOrEqual`, `greaterThanOrEqual` — are
numeric-comparison only and have no non-numeric meaning (a magnitude ordering requires numbers). The
remaining two — `equal` and `notEqual` — also compare non-numeric arguments (string equality), per
`DG.Core.Validation.SupportedBuiltins.NonNumericCapableNames`.

Any other `swrlb:`-prefixed predicate is parsed as a `BuiltinAtom` (predicate-name recognition alone
does not require resolving anything against the OntoGraph) but is refused by the evaluator with
`unsupported` — recognizing the atom type is not the same as implementing the comparison.

---

## 2. The Recognize-versus-Evaluate Asymmetry

This is the single most misreadable thing about this subset after Phase 1201, stated plainly and
early: **the parser can now recognize an `ObjectPropertyAtom`. The evaluator still cannot evaluate
one.** Both halves are correct and deliberate — they are not a bug in one direction or the other.

Before Phase 1201, `ResolveAtomType` had no branch for `ObjectPropertyAtom` at all; every ≥2-argument
predicate was guessed as a `DataPropertyAtom`. Phase 1201 D-02 closed that guess by adding a real
`IPredicateKindResolver`-driven branch, so an object property is now correctly *typed* rather than
mis-typed as a datatype property. That is a parsing-correctness fix, not an evaluation capability.

`RuleEvaluator.EvaluateAtom` refuses both `ObjectPropertyAtom` and `UnsupportedAtom` identically,
**before** attempting any variable-resolution check, with this exact wording (quoted verbatim from
`RuleEvaluator.cs`, Phase 1201 plan 02):

> What: this atom's predicate ('{predicate}') is an object property, which this evaluator
> recognizes but does not evaluate. Where: atom '{atom.Id}', predicate '{predicate}'. How to fix:
> express the constraint using a datatype property and one of the supported comparison builtins, or
> accept this typed non-verdict.

A fully-bound `ObjectPropertyAtom` — every variable resolvable, values present — is still refused,
never silently reported as satisfied. Implementing genuine OWL object-property evaluation semantics
is out of scope for this phase (and is the general-reasoner claim [§3](#3-non-claims-d-14)
disclaims) — it is explicitly deferred, not attempted partially.

---

## 3. Non-Claims (D-14)

**The C# evaluator path is not a general SWRL/OWL reasoner, and this document does not claim it is.**
Every construct below yields a typed, documented status — never a silent drop, never a guessed
verdict, and never an ordinary `failed`.

<!-- swrl-subset:non-claims-statuses:start -->
```
unsupported
unsupported
unsupported
unsupported
unsupported
unknown
no_population
not_evaluated
```
<!-- swrl-subset:non-claims-statuses:end -->

The machine-readable block above is the flat status list `NonClaimsStatuses_AreAllRealEvidenceStatusWireNames`
reads (each entry is checked against the frozen `EvidenceStatus` wire-name vocabulary in
`spec/EVIDENCE-CONTRACT.md` §1 so a ninth status can never be introduced by this doc alone). The
table below is the human-readable mapping the block mirrors, in the same order:

| Construct | Status it yields | Why |
|---|---|---|
| `ObjectPropertyAtom` **evaluation** (recognized, not evaluated — [§2](#2-the-recognize-versus-evaluate-asymmetry)) | `unsupported` | Genuine OWL object-property semantics are not implemented; refusing beats guessing. |
| String and date builtins beyond the six in [§1.2](#12-supported-builtins) (e.g. `swrlb:stringConcat`, `swrlb:yearGreaterThan`) | `unsupported` | Not in `SupportedBuiltins.Names`; `EvaluateBuiltin` refuses any predicate outside the allow-list. |
| Negation (SWRL has no native negation-as-failure atom, and none is emitted or evaluated here) | `unsupported` | No atom type or evaluation path exists for it; there is nothing to guess at. |
| OWL inference of any kind (subclass reasoning, property chains, equivalence, disjointness) | `unsupported` | The evaluator checks bound values against atoms as written; it performs no TBox reasoning. |
| A predicate whose kind the OntoGraph cannot resolve (Phase 1201 D-02 — no resolver, or resolver reports unknown) | `unsupported` | `UnsupportedAtom`, emitted with an `unresolvable-predicate-kind` diagnostic — never silently defaulted to `DataPropertyAtom`. |
| A variable with no value in the binding row | `unknown` | Binding resolution was attempted and failed to resolve — the rule's truth value cannot be determined, per `EVIDENCE-CONTRACT.md` §1's `unknown` definition. |
| An empty binding population (zero rows to check) | `no_population` | A real, distinguishable evaluation outcome — never `failed`, per `EVIDENCE-CONTRACT.md`'s D-05 situation table. |
| A rule in scope with no result produced at the publish boundary | `not_evaluated` | Evaluation itself never happened for this rule in this run, distinct from `unknown` (evaluation happened but did not resolve). |

**Known limitation, disclosed rather than silently accepted:** every `ParseDiagnostic` this parser
emits currently carries `Offset = -1` (not a real character position into the source expression).
The record type supports a genuine offset; none of Phase 1201's five diagnostic sites had a low-risk
way to compute one without re-deriving position tracking through the regex/split pipeline, and no
behavior in this phase depended on a real offset. This is an open item for a future phase, not a
completed-but-unverified claim.

---

## 4. Relationship to the Partition Policy

This document governs the **implemented C# evaluator subset within the SWRL side** of the boundary
`spec/RULE-PARTITION-POLICY.md` already draws between the two validation systems: the **SWRL
VALIDATOR owns architect-authored, quantitative and parametric design-compliance rules**; **SHACL
owns structural and data-integrity rules** over the ValidGraph/Metagraph instance data. Nothing in
this document reopens or restates that partition line — see `spec/RULE-PARTITION-POLICY.md` directly
for the full decision table and enforcement discipline. This document exists one level down: given
that a rule is SWRL's to evaluate, which SWRL constructs does the shipped evaluator actually support,
and which does it typedly refuse.

---

## 5. Enforcement

Enforcement here is **partly mechanical, partly documentation discipline** — narrower than
`RULE-PARTITION-POLICY.md`'s enforcement section, because this document's claims are checkable in a
way a cross-service partition line is not:

- **Mechanically enforced (drift guards):** `DG/tests/DG.Tests/SwrlSubsetConformanceTests.cs` asserts,
  in both directions, that [§1.2](#12-supported-builtins)'s fenced builtin block matches
  `DG.Core.Validation.SupportedBuiltins.Names` exactly, and that every status named in
  [§3](#3-non-claims-d-14)'s fenced block is a real member of the frozen `EvidenceStatus` wire-name
  vocabulary. Both guards were proven to actually fail on an induced mismatch before being reverted —
  see `1201-04-SUMMARY.md` for the recorded check. A change to either side that is not mirrored on
  the other fails the test suite, not silently.
- **Not mechanically enforced:** [§2](#2-the-recognize-versus-evaluate-asymmetry)'s prose and
  [§4](#4-relationship-to-the-partition-policy)'s cross-reference are documentation and review
  discipline, the same posture `RULE-PARTITION-POLICY.md` §Enforcement takes for its own decision
  table — a reviewer proposing a new atom type or builtin should consult this document, but no CI
  gate currently checks that a code change was accompanied by a doc update beyond the two guards
  above. This is a known, accepted gap, not a promise this phase makes.

---

## 6. Consistency & Propagation

This document is coupled to `spec/EVIDENCE-CONTRACT.md` (the status vocabulary every entry in
[§3](#3-non-claims-d-14) is drawn from) and `spec/RULE-PARTITION-POLICY.md` (the SWRL-vs-SHACL
ownership line this document's scope sits inside). Any change to which atom types the parser emits,
which builtins the evaluator supports, or which construct maps to which status should trigger a
review of whether this document's tables — and the two fenced machine-readable blocks in
[§1.2](#12-supported-builtins) and [§3](#3-non-claims-d-14) — need updating. See `CLAUDE.md`'s
§ Schema Change Propagation checklist, which now references this document.
