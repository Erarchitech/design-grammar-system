# Phase 1201: Rule Parser and Evaluator Conformance - Research

**Researched:** 2026-09-20
**Domain:** C# rule-subset conformance (parser typed-result migration, evaluator status emission, SHACL targeting defect diagnosis, evidence-contract propagation)
**Confidence:** HIGH (code-level findings, all backed by file:line evidence and a real DE-01 run artifact); MEDIUM on the D-09 fix approach (root cause is confirmed, the fix's blast radius on other reasoner call sites is not fully explored); LOW on nothing load-bearing — no claim below rests on unverified training knowledge for a compliance/security-relevant fact.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Four grey-area proposal tables, all accepted in full ("Accept all") by the user on 2026-09-20:

**Parser Outcome Model**
- **D-01:** Additive `TryParse`-style entry point on `SwrlRuleParser` returning a typed result carrying `EvidenceStatus` + diagnostics. Existing throwing `Parse` retained as a thin wrapper. Reversible.
- **D-02:** `ObjectPropertyAtom` vs `DataPropertyAtom` resolved by looking up the predicate IRI against the OntoGraph (`ObjectProperty` -> `ObjectPropertyAtom`, `DatatypeProperty` -> `DataPropertyAtom`). Unresolvable -> `unsupported`, never a silent default. Introduces a predicate-kind lookup dependency into a currently pure/static class; planner resolves injection shape (injected resolver interface with null-object default is the obvious candidate). Costly to reverse (signature + callers change).
- **D-03:** An atom the parser cannot classify is emitted as `UnsupportedAtom` type with `unsupported` status — never dropped, never guessed. One-way (1201's own gate is written against this).
- **D-04:** Parser diagnostics are a `ParseDiagnostic` list on the result (code + message + offset), reusing the What+Where+How-to-fix wording pattern from `ErrorMessageTemplates`. Reversible.

**Evaluator Status Emission**
- **D-05:** `RuleEvaluationResult` gains an additive `Status` property of type `DG.Core.Contracts.EvidenceStatus`. Existing `Passed` boolean retained, documented non-authoritative. Costly to reverse.
- **D-06:** Zero bindings -> `no_population` (was `Passed=false`). One-way.
- **D-07:** An unsupported builtin returns `unsupported`; does not throw. Compounding defect to fix with it: the throw is swallowed by the evaluator's catch-all and reported as a rule violation today. One-way.
- **D-08:** A missing variable binding -> `unknown` ("binding resolution attempted and unresolvable"). One-way.
- **Consequence the planner must handle:** with D-06/D-07/D-08, one rule over many bindings can yield a mix of per-binding outcomes. The plan must state an explicit aggregation precedence and must never let `unsupported`/`unknown` decay into `failed`. CONTEXT's suggested (refinable) precedence: `error > unsupported > unknown > indeterminate > failed > no_population > not_evaluated > passed`.

**dg-reasoner SHACL Targeting (routed finding)**
- **D-09:** Fixing SHACL shape targeting is in scope. Diagnose why `ontology/dg-shapes.ttl` shapes do not target the seeded `DG-1200-GOLDEN` objects and fix it so the reasoner leg genuinely evaluates them. Reversible.
- **D-10:** If the shapes genuinely cannot target those objects, record a declared typed non-equivalence with a written reason — never silent. Forbidden: editing `fixtures/golden/fixture.json` to match the shapes, or weakening the gate. Reversible.
- **D-11:** 1201 re-runs DE-01 as its exit evidence, requiring `silent_disagreement_count = 0` or every remaining disagreement explicitly declared with a reason. Unit tests alone are not sufficient exit evidence. One-way (gate definition).
- **D-12:** The `inputHash`/`outputHash` null-at-the-live-service-boundary problem is in scope. Reversible.

**Documentation and Subset Boundary (ALGN12-07)**
- **D-13:** Supported-subset boundary documented in a new normative `spec/SWRL-SUBSET.md`, cross-referenced from `EVIDENCE-CONTRACT.md` and `RULE-PARTITION-POLICY.md`. Mandatory: check `CLAUDE.md` § Schema Change Propagation and propagate as required. Costly to reverse once downstream phases cite the path.
- **D-14:** An explicit non-claims section lists what is not supported — ObjectPropertyAtom evaluation, string/date builtins, negation, OWL inference — each mapped to the status it yields. Must state the D-02 recognize/evaluate asymmetry plainly; evaluator must return `unsupported` for `ObjectPropertyAtom`, not the `return true` shortcut it takes today. Reversible.
- **D-15:** Boundary is machine-checkable: a supported-builtin allow-list constant in `DG.Core` read by both the evaluator and a conformance test. Reversible.
- **D-16:** Parser conformance corpus lives in `fixtures/golden/parser/`, under the shared golden root, in a separate subdirectory so the frozen `fixture.json` is untouched. Reversible.

### Claude's Discretion

- Concrete name/shape of the additive parse-result type and its `TryParse` entry point.
- Injection mechanism for the OntoGraph predicate-kind resolver (D-02), including whether a null-object default keeps `SwrlRuleParser` usable without a graph.
- Exact per-binding -> rule-level status aggregation precedence, provided it is stated explicitly and never lets `unsupported`/`unknown` decay into `failed`.
- File split within `fixtures/golden/parser/` (one file per case vs. a single table-driven corpus).
- Whether `spec/SWRL-SUBSET.md` carries the allow-list inline or generates it from the `DG.Core` constant.

### Deferred Ideas (OUT OF SCOPE)

| Idea | Owner | Note |
|---|---|---|
| Actually evaluating `ObjectPropertyAtom` (not just recognizing it) | Not this phase | 1201 makes it a typed `unsupported`; implementing OWL object-property semantics is a general-reasoner claim D-14 explicitly disclaims |
| `Neo4jValidGraphRepository.RunsQuery` run-level aggregate repeated across objects | 1202 | ALGN12-10 |
| Design State content-equivalence vs capture-event identity | 1202 | Open question #3 |
| Which service owns canonical per-object verdicts | 1202 | Open question #5 |
| `ATTRIBUTE_OF` vs `PARAM_LINK` | 1203 | Milestone D8 |
| Identity authority across GH/Revit/IFC/Speckle | 1203 | Open question #7 |
| LLM reproducibility / provider snapshots | 1204 | Open question #10 |
| Authorization and project isolation | 1205 | Open question #9 |
| Full envelope propagation across the CLAUDE.md schema list | v11.0 Phase 1105 | 1200 owns definition, 1105 owns propagation |
| Phase 1200's own gap closure (waves 4-5) | Phase 1200 | Excluded from this run at user instruction |
| F-39-01 auto-run self-violation | Not this phase | Pre-existing disclosed finding |
| `:ValidationRun`/`:Run` label drift | Not this phase | Documented, not fixed |

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALGN12-05 | The parser correctly resolves `ObjectPropertyAtom` vs `DataPropertyAtom` (or reports typed non-result) | §A (TryParse pattern), §C (OntoGraph resolver injection), §G (fixture corpus) all directly enable this |
| ALGN12-06 | The evaluator never throws for an in-scope-but-unsupported construct; it emits a typed status | §B (aggregation precedence — already shipped in `EvidenceEnvelopeFactory`/`evidence_contract.py`), the `RuleEvaluator.cs` line-by-line fix map in Code Under Change |
| ALGN12-07 | The supported-subset boundary is documented and machine-checkable, with an explicit non-claims section | §H (schema propagation scope), D-15's allow-list constant pattern (Phase 35-12 precedent located) |

</phase_requirements>

## Summary

This phase's C#-side work (parser `TryParse` migration, evaluator status emission, allow-list
constant) is well-precedented in the existing codebase — `RecognitionMarker.TryParse`,
`EvidenceStatusNames.TryParseWireName`, and the `IRuleRepository`/`Neo4jRuleRepository`
constructor-injection pattern are all directly reusable templates, and the per-binding aggregation
precedence the planner is asked to "refine" is **already shipped, identical, in both
`DG.Core.Contracts.EvidenceEnvelopeFactory.RollupPrecedence` (C#) and
`data-service/evidence_contract.py::_ROLLUP_PRECEDENCE` (Python)** — the planner should adopt that
exact order rather than CONTEXT's own suggested draft, which disagrees with it on where `failed`
and `indeterminate` sit relative to `unsupported`/`unknown`.

The dg-reasoner SHACL targeting defect (D-09) has a confirmed, file:line-precise root cause: the
DE-01 runner's dg-reasoner leg (`tools/de01/legs.py:333`) calls `POST /shacl/validate` with only
`{"project": project}` — it never passes `run_id`. Per `run_shacl`'s own docstring
(`dg-reasoner/reasoning.py:474-479`), omitting `run_id` restricts validation to the
**project-level Metagraph/OntoGraph export only** (`ontology_export.build_graph`, which emits only
`Class`/`DatatypeProperty`/`ObjectProperty`/`Rule`/`Atom`/`Var`/`Literal`/`Builtin` nodes). The
seeded golden objects (`OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`, with `hasHeight`/`classIri`) live in the
**Computgraph** (`Object` nodes) and are only unioned in via `valid_graph_export.build_valid_graph`
when a `run_id` is supplied. `dg-shapes.ttl`'s shapes that could plausibly bear on these objects
(`dgc:ObjectShape`) target `dgc:Object` — a class that is never present in the graph pySHACL
validates when `run_id` is omitted. Hence: zero focus nodes, `conforms=true`, zero findings,
`no_population` on every row. This is fixable by passing a `run_id` (requires the golden fixture to
have a persisted `Run` — `seed.cypher` already writes `RUN_GOLD_1200`) and/or by adding SHACL
shapes that assert something meaningful about `ex:Building`/height at the OntoGraph/Metagraph level
if the intent is to catch height violations via SHACL too (out of this phase's intent per
`spec/RULE-PARTITION-POLICY.md` — SHACL is data-integrity only, never a quantitative design rule).

The `inputHash`/`outputHash` null-at-boundary problem (D-12) is also fully diagnosed: it is a
**row-level vs envelope-level** hash mismatch. The C# harness (`DG.De01Harness/Program.cs:284,294`)
already computes and sets an **envelope-level** `inputHash`; but the DE-01 comparison report only
surfaces **row-level** (`EvidenceRow.InputHash`/`OutputHash`) values (`tools/de01/report.py:127-128`),
which no call site (Python `app.py:2176-2183` nor C# `Program.cs:248-254,264-280`) ever populates.
Fixing this is a matter of deciding, and then wiring, which stage-appropriate hash belongs at row
granularity — not a hashing-algorithm defect.

**Primary recommendation:** adopt the already-shipped `RollupPrecedence`/`_ROLLUP_PRECEDENCE` order
verbatim for per-binding aggregation (do not re-derive a new one); fix D-09 by passing `run_id` in
the DE-01 dg-reasoner leg call (and seeding/publishing a `Run` for the golden fixture project before
that call) rather than changing `dg-shapes.ttl`'s shapes, since the fixture's expected `passed`/
`failed` distinction is a SWRL/height concern the partition policy explicitly reserves to the SWRL
VALIDATOR, not SHACL; and follow `RecognitionMarker`/`IRuleRepository`'s existing shapes for the
`TryParse` result type and the OntoGraph resolver injection, respectively.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SWRL rule text -> typed atom/parse result | API/Backend (DG.Core, embedded in the Grasshopper plugin process) | — | `SwrlRuleParser` is pure logic in `DG.Core`, consumed by both the GH plugin and the DE-01 harness; no browser/SSR/CDN tier involved |
| Per-binding rule evaluation -> canonical status | API/Backend (DG.Core) | — | `RuleEvaluator` is pure logic; it has no I/O of its own — bindings and rules are passed in |
| Predicate-kind resolution (OntoGraph lookup) | Database/Storage (Neo4j OntoGraph read) | API/Backend (resolver abstraction in DG.Core) | The authoritative `ObjectProperty`/`DatatypeProperty` labels live in Neo4j; DG.Core must consume them through an injected read abstraction, never a hardcoded guess |
| SHACL structural validation | API/Backend (dg-reasoner service) | Database/Storage (Neo4j export via `ontology_export`/`valid_graph_export`) | dg-reasoner owns the pySHACL pipeline; its correctness depends entirely on which Neo4j-derived RDF graph it is handed |
| Evidence envelope hashing/aggregation | API/Backend (each producing service: DG.Core, data-service, dg-reasoner) | — | Each service emits its own envelope per D-06 of `EVIDENCE-CONTRACT.md`; no shared hashing service exists or is proposed |
| Subset-boundary documentation | — (docs/spec artifact) | — | `spec/SWRL-SUBSET.md` is a normative doc, not a runtime tier |

## Standard Stack

This phase does not add any new third-party package. All work is within the existing `DG.Core`
(.NET), `dg-reasoner` (Python/rdflib/pySHACL/owlready2), and `tools/de01` (Python) codebases.

### Package Legitimacy Audit

**Not applicable** — no new external packages are introduced by this phase. No `npm view`/`pip
index`/`cargo search` verification is required.

## Architecture Patterns

### System Architecture Diagram

```
                         SWRL rule text (Metagraph.Rule.SWRL)
                                    |
                                    v
                     +----------------------------+
                     |  SwrlRuleParser.TryParse    |  <-- NEW additive entry point (D-01)
                     |  (throwing Parse retained    |
                     |   as thin wrapper)            |
                     +----------------------------+
                                    |
                     resolves predicate kind via
                     injected IPredicateKindResolver (D-02)
                                    |
                    +---------------+----------------+
                    |                                |
           resolved: ClassAtom /            unresolvable / not
           DataPropertyAtom /               recognized ->
           ObjectPropertyAtom /             UnsupportedAtom (D-03)
           BuiltinAtom
                    |                                |
                    v                                v
        ParsedSwrlRule.BodyAtoms/HeadAtoms  ParseDiagnostic list (D-04)
                    |
                    v
        +--------------------------+
        |     RuleEvaluator         |
        |  EvaluateRule per binding |
        +--------------------------+
                    |
      per-binding outcome classification (never throws, D-06/D-07/D-08):
      zero bindings -> no_population
      missing binding -> unknown
      unsupported builtin -> unsupported
      genuine violation -> failed
      genuine pass -> passed
                    |
                    v
      per-binding -> rule-level aggregation
      (RollupPrecedence, already shipped, D-05 Status field)
                    |
                    v
      RuleEvaluationResult { Passed (legacy, non-authoritative),
                              Status (canonical, D-05) }
                    |
                    v
      EvidenceEnvelopeFactory.Build(...) -> EvidenceEnvelope (rows + roll-up)
                    |
        +-----------+------------------------------+
        |                                           |
        v                                           v
  DG.De01Harness stdout                    (future) publish path consumer
  (canonical JSON envelope)                (ValidationPublishPackageBuilder, D-14 asymmetry)
        |
        v
  tools/de01/legs.py::run_leg_csharp
        |
        v
  tools/de01/report.py::compare_legs  <-- compares against data-service, dg-reasoner, replay legs
        |
        v
  .de01/de01-report.json / .md  (silent_disagreement_count gate, D-11)

Separately, the dg-reasoner leg:

  tools/de01/legs.py::run_leg_dg_reasoner
        |
        v  POST /shacl/validate {project}  <-- MISSING run_id (D-09 root cause)
        v
  dg-reasoner/app.py::shacl_validate -> reasoning.py::run_shacl(project, run_id=None)
        |
        v
  ontology_export.build_graph(session, project)  <-- OntoGraph + Metagraph ONLY
        |            (Object/DesignState/Run nodes never included without run_id)
        v
  pySHACL validate(data_graph, dg-shapes.ttl)  <-- shapes target dgc:Object/dgv:* classes
        |            that are ABSENT from the graph actually validated
        v
  conforms=true, zero findings -> no_population on every golden object (the defect)
```

### Recommended Project Structure

No new top-level directories. Additions land inside existing structure:

```
DG/src/DG.Core/
├── Parsing/
│   ├── SwrlRuleParser.cs           # add TryParse, ParseResult, keep Parse as wrapper
│   ├── ParseDiagnostic.cs          # NEW: code + message + offset (D-04)
│   └── IPredicateKindResolver.cs   # NEW: injection seam for D-02 (interface + null-object default)
├── Validation/
│   ├── RuleEvaluator.cs            # emit Status instead of throwing; aggregation precedence
│   └── SupportedBuiltins.cs        # NEW: D-15 allow-list constant, single source of truth
└── Data/
    └── Neo4jPredicateKindResolver.cs  # NEW: OntoGraph-backed implementation of the resolver

fixtures/golden/
└── parser/                          # NEW subdir (D-16) — parser conformance corpus, separate
    ├── MANIFEST.md (or inline notes in the corpus file)
    └── cases.json (or one file per case — planner's discretion)

spec/
└── SWRL-SUBSET.md                   # NEW (D-13) — normative subset boundary + non-claims (D-14)

tools/de01/
└── legs.py                          # fix run_leg_dg_reasoner to pass run_id (D-09)
```

### Pattern 1: Additive `TryParse` result type (D-01)

**What:** A non-throwing parse entry point that returns a result object carrying the canonical
`EvidenceStatus`, the parsed rule (if any atoms were classifiable), and a diagnostics list. The
existing throwing `Parse` becomes a wrapper that calls `TryParse` and throws on the first
diagnostic that represents a hard parse failure.

**When to use:** Any caller that must not crash on malformed/unsupported SWRL input — the DE-01
harness, any future validation-pipeline caller, and the new parser conformance tests.

**Precedent already in this codebase** (reuse this exact shape, do not invent a new one):

```csharp
// Source: DG/src/DG.Core/Parsing/RecognitionMarker.cs:88 (TryParse returning a nullable record)
public static RecognitionProvenance? TryParse(string? rawValue)
{
    var value = rawValue?.Trim();
    if (string.IsNullOrEmpty(value) || string.Equals(value, Absent, StringComparison.OrdinalIgnoreCase))
    {
        return null;
    }
    // ...
}
```

```csharp
// Source: DG/src/DG.Core/Contracts/EvidenceStatusNames.cs:110 (bool TryParseWireName(string, out T))
if (!EvidenceStatusNames.TryParseWireName(raw, out var status))
{
    // caller decides what "unparseable" means for its own context
}
```

The planner should shape `SwrlRuleParser.TryParse` closer to the second form (a `bool
TryParse(string swrlExpression, out ParsedSwrlRuleResult result)` or a result-object return —
either is net7.0-legal; a `record ParsedSwrlRuleResult(EvidenceStatus Status, ParsedSwrlRule?
Rule, IReadOnlyList<ParseDiagnostic> Diagnostics)` avoids an `out` parameter entirely and is more
idiomatic for a result carrying more than a single nullable value).

### Pattern 2: Injected resolver with null-object default (D-02)

**What:** A small interface (`IPredicateKindResolver` or similar) that `SwrlRuleParser`'s new
`TryParse` overload accepts, defaulting to a null-object implementation that always reports
"unresolvable" when no graph is available — so the parser stays usable standalone (unit tests,
callers with no Neo4j connection) while allowing real Neo4j-backed resolution when injected.

**When to use:** Any place `ResolveAtomType` needs to distinguish `ObjectPropertyAtom` from
`DataPropertyAtom` for a ≥2-arg, non-`swrlb:` predicate.

**Precedent already in this codebase:**

```csharp
// Source: DG/src/DG.Core/Data/IRuleRepository.cs (full file — minimal DI-friendly interface)
public interface IRuleRepository
{
    Task<IReadOnlyList<Rule>> GetRulesAsync(ConnectionInfo connection, CancellationToken cancellationToken = default);
    Task<IReadOnlyList<OntologyClass>> GetObjectsAsync(ConnectionInfo connection, CancellationToken cancellationToken = default);
}
```

`Neo4jRuleRepository : IRuleRepository` is the live implementation (`DG/src/DG.Core/Data/Neo4jRuleRepository.cs`).
The planner should follow the same split: `IPredicateKindResolver` (sync, since parsing is
synchronous and callers that have already loaded OntoGraph state can answer in-memory) with a
`Neo4jPredicateKindResolver` implementation, and a `NullPredicateKindResolver`
(or a static `IPredicateKindResolver.None` singleton) that always returns "unresolvable" — never
guesses `DataPropertyAtom` by default, which is precisely the current bug (D-02's whole point).

**Important constraint:** `SwrlRuleParser` is currently `public static class`. Adding a resolver
dependency to a static class means either (a) an optional parameter defaulting to the null-object
resolver on every `TryParse` overload, or (b) converting the type that owns `TryParse` to an
instantiable class while keeping the existing static `Parse`/`ParseAtoms` methods for backward
compatibility. Given D-01 requires `Parse` to keep compiling unchanged for every current caller,
**(a) is lower-risk**: keep `SwrlRuleParser` static, add
`TryParse(string swrlExpression, IPredicateKindResolver? resolver = null)` with `resolver ??=
NullPredicateKindResolver.Instance` at the top.

### Pattern 3: Single-source-of-truth allow-list constant (D-15)

**What:** A `DG.Core` constant (e.g. `public static readonly IReadOnlySet<string>
SupportedBuiltins`) enumerating the six currently-supported builtins
(`swrlb:lessThan`, `swrlb:greaterThan`, `swrlb:lessThanOrEqual`, `swrlb:greaterThanOrEqual`,
`swrlb:equal`, `swrlb:notEqual`), imported by both `RuleEvaluator.EvaluateBuiltin` and a
conformance test, so the code and `spec/SWRL-SUBSET.md` cannot silently drift apart.

**Precedent cited directly by CONTEXT.md D-15:** Phase 35-12's `GRAMMAR_CITATION_PATTERNS` —
moved to production code and imported by the online guard and the offline metric so they can never
disagree. (This repo's specific file for that precedent was not re-located in this session — the
pattern description in CONTEXT.md is sufficient to replicate; the planner does not need to find
the exact Phase 35-12 file, since D-15 already specifies the target shape precisely.)

### Anti-Patterns to Avoid

- **Guessing `DataPropertyAtom` when the predicate kind is unresolvable:** this is the exact
  defect D-02 exists to end. Any code path that falls back to `DataPropertyAtom` instead of
  `UnsupportedAtom` when a Neo4j lookup fails, times out, or the resolver is unavailable
  re-introduces silent misclassification.
- **Catching an exception and returning `Passed=false`:** `RuleEvaluator.cs:52-56`'s existing
  catch-all is precisely this anti-pattern. The fix must remove distinct-exception-to-boolean
  collapse entirely — every one of the four throw sites (`:100`, `:114`, `:130`, `:138`) must
  become a typed status assignment, not a caught-and-swallowed exception.
- **Re-deriving a new aggregation precedence from first principles:** the correct precedence is
  already shipped and tested against DE-01 (`EvidenceEnvelopeFactory.RollupPrecedence`,
  `evidence_contract.py::_ROLLUP_PRECEDENCE`). Inventing a different order (as CONTEXT.md's own
  draft suggestion does) risks a genuine C#/Python cross-leg divergence in DE-01 that no code
  defect caused — purely from two different orderings being used in two different aggregation
  contexts (envelope roll-up vs. per-binding roll-up). Even though these are technically different
  aggregation levels (envelope-level roll-up over rows vs. per-binding roll-up within one rule
  evaluation), using the same order for both avoids a second precedence table to maintain and keep
  in sync, and there is no stated reason the two should differ.
- **Fixing D-09 by weakening or deleting SHACL shapes to "make them stop firing false positives":**
  the observed defect is a *false no_population*, not a false violation. The fix is to get the
  right graph in front of pySHACL (pass `run_id`), not to change what the shapes assert.
- **Fixing D-09 by adding a SHACL shape that re-encodes the height-75 rule:** `spec/RULE-PARTITION-POLICY.md`
  reserves quantitative/parametric design rules exclusively to the SWRL VALIDATOR pipeline; SHACL
  shapes are structural/data-integrity only. Making SHACL "agree" with the SWRL leg by encoding the
  same business rule twice would be a partition-policy violation, not a fix.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-binding/per-row status aggregation precedence | A new precedence table from CONTEXT's draft suggestion | `DG.Core.Contracts.EvidenceEnvelopeFactory.RollupPrecedence` / `data-service/evidence_contract.py::_ROLLUP_PRECEDENCE` (already identical, already shipped) | Two independently-authored precedence tables for supposedly the same concept is exactly the drift the whole evidence contract exists to prevent |
| Canonical JSON hashing | A second `HashCanonical`/`format(Decimal,"f")` implementation | `DG.Core.Contracts.CanonicalJsonWriter` (C#) / `data-service/canonical_json.py` (Python) — both already exist and are cross-verified via `fixtures/golden/canonical-vectors.json` | Re-implementing canonicalization risks reopening CR-01/WR-01, the exact decimal-scale-loss bugs Phase 1200 spent three plans fixing |
| SWRL-to-RDF export scoping | A second Cypher-to-RDF exporter for the golden fixture | `dg-reasoner/ontology_export.py::build_graph` (already handles label-scoped export with an assertion guard against the Pitfall 1 export-scoping bug) | This module already carries hard-won defenses (Pitfall 1 atom-count assertion); a parallel exporter would need to re-earn all of them |

**Key insight:** almost everything this phase needs (the aggregation precedence, the canonical
hashing, the export pipeline, the DI interface shape) already exists in the codebase from Phase
1200 or earlier phases. The actual net-new work is narrower than CONTEXT.md's decision list might
suggest: a `TryParse` overload, a resolver interface + one Neo4j implementation, replacing four
throw sites with status assignments, one allow-list constant, one new spec doc, one fixture
subdirectory, and a one-line fix (`run_id=`) plus a seed/publish step in the DE-01 dg-reasoner leg.

## Common Pitfalls

### Pitfall 1: Treating "the parser now recognizes ObjectPropertyAtom" as "the evaluator now supports it"

**What goes wrong:** After D-02 lands, `SwrlRuleParser.TryParse` correctly tags an atom as
`ObjectPropertyAtom`. If `RuleEvaluator.EvaluateAtom` is left unchanged, its current `:104-105`
bare `return true` (a MVP variable-availability shortcut for "class/data-property atoms") will
silently also treat an `ObjectPropertyAtom` as satisfied — a genuine general-reasoner claim by
accident, exactly what D-14 forbids.

**Why it happens:** `EvaluateAtom`'s branch structure is `if BuiltinAtom -> EvaluateBuiltin, else
-> variable-availability check` — there is no third branch. Adding a type to the parser's output
vocabulary does not automatically add a branch to the evaluator's dispatch.

**How to avoid:** `EvaluateAtom` needs an explicit `ObjectPropertyAtom` (and `UnsupportedAtom`)
branch that returns a typed `unsupported` outcome, not the variable-availability fallthrough.

**Warning signs:** A conformance test asserting `unsupported` for `ObjectPropertyAtom` passes at
the parser level but a rule-evaluation-level test for the same atom silently reports `passed`.

### Pitfall 2: Fixing D-09 without checking whether the golden fixture's `Run` is actually persisted for the DE-01 run

**What goes wrong:** Passing `run_id=RUN_GOLD_1200` to `POST /shacl/validate` requires
`valid_graph_export.build_valid_graph(session, project, run_id)` to find that run's ValidGraph
ABox in Neo4j. `fixtures/golden/seed.cypher` does write a `Run` node (`Step 7`), but only if
`seed.cypher` has actually been applied to the Neo4j instance dg-reasoner reads from — a
compose-network requirement (`tools/de01/README.md`'s replay-leg precondition table already
documents this exact caveat for the *replay* leg; the same precondition now also applies to the
dg-reasoner leg once it is fixed to pass `run_id`).

**Why it happens:** `seed.cypher` is a manual, dev-only script (`cypher-shell -f
fixtures/golden/seed.cypher`), not something any DE-01 leg runs automatically.

**How to avoid:** The plan must include an explicit step to (re-)apply `seed.cypher` before
re-running DE-01, and should verify the seeded `Run` node exists in the project namespace the
dg-reasoner leg queries, before concluding D-09 is fixed.

**Warning signs:** After the `run_id` fix, dg-reasoner still reports `no_population` — check
whether the seed was actually applied to the Neo4j instance dg-reasoner's `NEO4J_URI` resolves to
(compose-network hostname caveat applies here too).

### Pitfall 3: The `RollupPrecedence`/`_ROLLUP_PRECEDENCE` array already enumerates every `EvidenceStatus` member — adding a status-handling branch elsewhere without updating both arrays

**What goes wrong:** `EvidenceEnvelopeFactory.RollupStatus` throws `InvalidOperationException` if
no precedence tier matches a non-empty row set — i.e., if `RollupPrecedence` is ever missing an
enum member. Since the vocabulary is frozen at 8 members (D-02 of Phase 1200), this should never
trigger, but if the planner introduces a *second*, per-binding-level precedence table (rather than
reusing the same array), keeping the two in sync becomes a manual, easy-to-forget obligation.

**Why it happens:** Per-binding aggregation (within one rule, across many bindings) and
envelope-row aggregation (across many rows, possibly many rules/objects) are conceptually
different scopes, which might tempt a "these need their own precedence" argument — but the
precedence semantics (worst-case-first, same eight statuses) are identical in both cases.

**How to avoid:** Reuse `EvidenceEnvelopeFactory.RollupPrecedence` (or extract it to a shared
`static readonly EvidenceStatus[]` in `DG.Core.Contracts` if `RuleEvaluator` needs it and
`RuleEvaluator` should not depend on `EvidenceEnvelopeFactory` directly for layering reasons) rather
than writing a second literal array.

**Warning signs:** A DE-01 or unit test asserts a rule-level `Status` that disagrees with what the
same rows would produce if run through `EvidenceEnvelopeFactory.Build` directly.

### Pitfall 4: `.NET` multi-targeting — a net8+-only BCL API sneaking into `SwrlRuleParser`/`RuleEvaluator`

**What goes wrong:** `DG.Core.csproj` targets `net7.0;net9.0` (confirmed,
`DG/src/DG.Core/DG.Core.csproj:4`). Phase 32.1 and Phase 38-05 both shipped code that only compiled
under net9.0 and broke the net7.0 build (`ArgumentException.ThrowIfNullOrWhiteSpace`,
`JsonObjectCreationHandling.Populate`).

**Why it happens:** Modern C#/.NET tooling defaults to suggesting the newest convenience API
available in the IDE's active TFM, which may not be net7.0-compatible.

**How to avoid:** `decimal.GetBits` (needed nowhere in this phase directly, but relevant if the
planner touches `RuleEvaluator.TryToDecimal`) and `Try*`-pattern methods used above
(`RecognitionMarker.TryParse`, `EvidenceStatusNames.TryParseWireName`) are all net7.0-safe BCL
members already in production in this exact codebase — copy their signatures rather than reaching
for something newer. Always build/test with both TFMs before considering a plan step complete
(`dotnet build DG/DG.sln -c Release` builds both by default per the multi-target csproj).

**Warning signs:** A build succeeds locally (if the SDK defaults to net9.0) but CI/verification
against net7.0 fails, or `dotnet build` emits a `NETSDK1138`/CS-prefixed API-availability error for
one TFM only.

## Code Examples

### Existing `Try*` result pattern (reuse verbatim shape)

```csharp
// Source: DG/src/DG.Core/Parsing/RecognitionMarker.cs:88-100
public static RecognitionProvenance? TryParse(string? rawValue)
{
    var value = rawValue?.Trim();

    if (string.IsNullOrEmpty(value)
        || string.Equals(value, Absent, StringComparison.OrdinalIgnoreCase))
    {
        return null;
    }

    if (string.Equals(value, LegacyRecognized, StringComparison.OrdinalIgnoreCase))
    {
        return new RecognitionProvenance(null, null, null);
    }
    // ...
}
```

### Existing rollup precedence (adopt verbatim, do not re-derive)

```csharp
// Source: DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs:25-35
private static readonly EvidenceStatus[] RollupPrecedence =
{
    EvidenceStatus.Error,
    EvidenceStatus.Failed,
    EvidenceStatus.Indeterminate,
    EvidenceStatus.Unsupported,
    EvidenceStatus.Unknown,
    EvidenceStatus.NotEvaluated,
    EvidenceStatus.NoPopulation,
    EvidenceStatus.Passed,
};
```

```python
# Source: data-service/evidence_contract.py:87-96 (identical order, cross-verified)
_ROLLUP_PRECEDENCE: tuple[CanonicalStatus, ...] = (
    CanonicalStatus.ERROR,
    CanonicalStatus.FAILED,
    CanonicalStatus.INDETERMINATE,
    CanonicalStatus.UNSUPPORTED,
    CanonicalStatus.UNKNOWN,
    CanonicalStatus.NOT_EVALUATED,
    CanonicalStatus.NO_POPULATION,
    CanonicalStatus.PASSED,
)
```

### The D-09 defect call site (fix target)

```python
# Source: tools/de01/legs.py:326-333 -- run_leg_dg_reasoner, no run_id passed
base_url = config.get("dg_reasoner_url", "http://localhost:8001")
project = fixture["project"]
rule_id = fixture["rule"]["Rule_Id"]
object_ids = [obj["objectId"] for obj in fixture["objects"]]

try:
    with httpx.Client(timeout=httpx.Timeout(connect=2.0, read=95.0, write=2.0, pool=2.0)) as client:
        response = client.post(f"{base_url}/shacl/validate", json={"project": project})
```

```python
# Source: dg-reasoner/app.py:53-96 -- ShaclRequest already HAS a run_id field
# (confirmed by reasoning.py:473 signature: run_shacl(project, run_id=None, session=None))
```

The fix is to pass `"run_id": fixture-derived-run-id` (the golden fixture's seeded `Run_Id`,
`RUN_GOLD_1200`, per `fixtures/golden/seed.cypher:215`) in the POST body, and to precondition the
leg on `seed.cypher` having been applied (same precondition the replay leg already documents).

### The D-12 defect call sites (fix target — row-level hash never populated)

```python
# Source: data-service/app.py:2176-2183 -- EvidenceRow built with no inputHash/outputHash
rows.append(
    evidence_contract.EvidenceRow(
        ruleId=rule_id,
        objectId=dg_entity_id,
        canonicalStatus=status,
        warnings=warnings,
    )
)
```

```csharp
// Source: DG/tools/DG.De01Harness/Program.cs:248-254 -- same gap on the C# side
rows.Add(new EvidenceRow
{
    RuleId = rule.Id,
    ObjectId = objectId,
    CanonicalStatus = status,
    Warnings = warnings.Count > 0 ? warnings : null,
});
```

The envelope-level `inputHash` IS set correctly by the harness (`Program.cs:284,294`,
`CanonicalJsonWriter.HashCanonical(fixtureNode)`), but `tools/de01/report.py:127-128` only reads
`row.get("inputHash")`, never falling back to the envelope-level value. The planner has two valid
fix shapes: (a) populate row-level hashes at each call site (requires deciding what "this row's
input" canonically means — likely the per-object binding + rule pair, hashed via
`CanonicalJsonWriter`/`canonical_json.py`), or (b) have `report.py`'s row extraction fall back to
the envelope-level hash when a row's own hash is absent. (a) is more faithful to the schema's
stated per-row granularity (`spec/EVIDENCE-CONTRACT.md` §3: "Row-scoped input hash, where the
envelope-level hash is insufficiently granular") — row-level should be additive/optional, not a
required replacement — but is more work across three call sites (Python publish path, C# harness,
and whatever the replay leg's `evidenceEnvelopeJson`-parsing path does). (b) is a pure `report.py`
fix, changes on the fewest lines, and does not require touching `data-service/app.py` or the C#
harness at all — likely sufficient to satisfy D-12's stated goal ("the envelope must carry real
hashes where the legs actually meet") since the envelope already does.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Every non-`passed`/`failed` outcome collapses to `Passed=false` | Typed `EvidenceStatus` distinguishing 8 outcomes | Phase 1200 (contract), Phase 1201 (this phase — implementation) | The whole point of this phase: silent wrongness becomes a declared or gated non-result |
| `ResolveAtomType` guesses `DataPropertyAtom` for any ≥2-arg predicate | Resolved against OntoGraph, `unsupported` if unresolvable | This phase (D-02) | Removes a structural misclassification bug that was, by construction, unreachable to detect from the parser's own output |
| dg-reasoner's SHACL leg validates OntoGraph/Metagraph only by default | (proposed) also unions ValidGraph ABox for the golden fixture's run | This phase (D-09), if the `run_id` fix is adopted | Makes the SHACL leg a genuine fourth cross-check rather than a structurally-empty no-op for object-scoped fixtures |

**Deprecated/outdated:** none — this phase adds capability, it does not deprecate an existing
approach. The legacy `Passed` boolean is explicitly retained as non-authoritative (per Phase 1200's
D-03/D-04), not removed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `dg-shapes.ttl`'s intent for `dgc:ObjectShape` is structural completeness (objectName/source/definitionId/publishedAt/project present), not a business-rule check on `hasHeight` — so passing `run_id` alone will make the SHACL leg produce *some* structural findings (or none, if the seeded `Object` nodes are complete) but will NOT make it independently derive `passed`/`failed` matching the height-75 rule. The DE-01 dg-reasoner leg adapter (`tools/de01/legs.py::run_leg_dg_reasoner`) already anticipates this: its own docstring says a non-empty conforming report maps every fixture object to `passed`, and only a focus-node-matching violation maps an object to `failed` — meaning after the `run_id` fix, dg-reasoner would report `passed` for BOTH `OBJ_GOLD_PASS` and `OBJ_GOLD_FAIL` (since neither violates structural completeness), producing a NEW disagreement with `OBJ_GOLD_FAIL`'s expected `failed`. This must be resolved as a **declared non-equivalence** (D-10), not chased as a bug — SHACL structurally cannot express "height > 75" per the partition policy. | §D-09 finding, Architecture Patterns Anti-Patterns | If the planner instead tries to make dg-reasoner's `failed` agree with the SWRL leg's `failed` by adding a height-checking SHACL shape, that violates `spec/RULE-PARTITION-POLICY.md` and produces a policy-violating "fix" that looks like it works |
| A2 | Fix (b) for D-12 (report.py falling back to envelope-level hash) is sufficient to satisfy D-12's literal wording ("the envelope must carry real hashes where the legs actually meet") — this session did not verify what "the legs actually meet" is intended to mean operationally (is it the DE-01 report specifically, or every persisted envelope in Neo4j/logs?). | Code Examples, D-12 fix options | If D-12 actually requires row-level hashes for reasons beyond DE-01 visibility (e.g. future per-row audit tooling), fix (b) alone would satisfy this phase's gate but leave a real row-granularity gap unaddressed |
| A3 | `IPredicateKindResolver`'s synchronous signature (vs. `Task<...>`-returning) is appropriate because callers that need OntoGraph data will have already loaded it before calling into a synchronous parser. This assumes no caller needs to lazily fetch from Neo4j per-parse-call inside `TryParse` itself. | Architecture Patterns Pattern 2 | If a caller genuinely needs an async Neo4j round-trip per atom during parsing, a sync interface forces an ugly `.GetAwaiter().GetResult()` or a pre-fetch-all-predicates-first restructuring; the planner should confirm which callers actually invoke the new `TryParse` overload with a real resolver before finalizing the interface's sync/async shape |

## Open Questions

1. **Should `IPredicateKindResolver` resolve one predicate at a time or accept a pre-loaded snapshot?**
   - What we know: `Neo4jRuleRepository.GetObjectsAsync` already returns `IReadOnlyList<OntologyClass>` in bulk; a single-predicate `Resolve(string predicateIri)` call risks N Neo4j round-trips per rule if implemented naively against a live connection.
   - What's unclear: whether any current caller of the new `TryParse` overload parses rules in a hot loop (e.g., `RuleEvaluator.EvaluateRule` calls `SwrlRuleParser.Parse` when `rule.BodyAtoms` is empty — `RuleEvaluator.cs:36-38` — which could be a hot path across many objects).
   - Recommendation: the planner should default to accepting a pre-loaded lookup (e.g., `IReadOnlyDictionary<string, PredicateKind>` or an interface with a bulk `TryGetKind` backed by an already-materialized snapshot) rather than a per-call live Neo4j read, to avoid a performance regression at the exact call site (`RuleEvaluator.EvaluateRule`) this phase is trying to make safer.

2. **Does the DE-01 dg-reasoner leg fix (passing `run_id`) require a `docker compose` stack to verify, and is that available in this planning session's environment?**
   - What we know: `tools/de01/README.md`'s precondition table states dg-reasoner has no host-exposed port by default and requires the compose network; the replay leg has the same seed-then-verify precondition already.
   - What's unclear: whether the executing session (plan/execute phase) will have a live Docker Compose stack available, or whether this must be a `checkpoint:human-verify` gated step.
   - Recommendation: the plan should treat "re-run DE-01 with the D-09 fix" as requiring a live compose stack and gate it behind an explicit environment-readiness check (see Environment Availability below) rather than assuming it can run unattended.

3. **Exact wording/placement for D-10's declared non-equivalence when dg-reasoner cannot express the height-75 rule.**
   - What we know: D-10 requires "a declared typed non-equivalence with a written reason ... never left silent"; `tools/de01/report.py`'s `_DECLARABLE_STATUSES` set is `{unsupported, error, not_evaluated, indeterminate}` — `no_population` and `passed` are NOT in that set.
   - What's unclear: if the dg-reasoner leg, after the `run_id` fix, reports `passed` for `OBJ_GOLD_FAIL` (structurally conforming, but semantically not evaluating height), that is a `passed` vs `failed` disagreement — `passed` is not a declarable status per `report.py`'s own guard (`compare_legs`'s `non_declarable_statuses` check at `report.py:174-176`). This means the current `_DECLARABLE_STATUSES` set may need to be widened, OR the dg-reasoner leg adapter (`tools/de01/legs.py::run_leg_dg_reasoner`) needs to map "SHACL cannot express this business rule" to `not_evaluated` (which IS declarable) instead of `passed`, when the run_id fix reveals it has nothing meaningful to say about height.
   - Recommendation: the planner should have the dg-reasoner leg adapter map a conforming-but-semantically-uninformative SHACL result to `not_evaluated` (with a warning explaining SHACL's partition-policy scope), not `passed`, whenever the golden fixture's `expectedOutcomes` calls for a `passed`/`failed` distinction that SHACL structurally cannot make. This keeps the disagreement in the already-declarable set and avoids needing to touch `report.py`'s classification logic at all.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `dotnet` SDK (net7.0 + net9.0 SDKs) | Building `DG.Core`/`DG.De01Harness`, running xunit tests | Not verified this session (research-only; no build was run) | — | Plan should include an explicit `dotnet build DG/DG.sln -c Release` verification step before claiming the parser/evaluator changes compile against both TFMs |
| Docker Compose stack (`neo4j`, `dg-reasoner`, `data-service`) | D-09 fix verification, D-11's DE-01 re-run | Not verified this session | — | If unavailable, D-11's re-run must be gated as `checkpoint:human-verify`; unit-level tests (xunit conformance fixtures) can still verify D-01 through D-08 and D-15 without a live stack |
| `cypher-shell` or Neo4j Browser access | Re-applying `fixtures/golden/seed.cypher` before the D-09 fix can be observed | Not verified this session | — | Same as above — gate behind human verification if the session cannot reach a live Neo4j |
| Python 3.11 (container) / host Python for `tools/de01` | Running `run_de01.py`, `pytest tools/de01/tests/test_de01_runner.py` | Not verified this session | — | `-k "not live"` tests can run without the stack; `-k "live"` tests need the stack per README |

**Missing dependencies with no fallback:**
- A live DE-01 four-leg run with the D-09 fix cannot be produced by static research alone — this requires execution-phase access to the compose stack, per the plan gate D-11 imposes. Flag as `checkpoint:human-verify` if the execution environment lacks Docker.

**Missing dependencies with fallback:**
- `dotnet build`/`dotnet test` verification is a standard execution-phase step, not researched further here since it requires actually compiling the (not-yet-written) code changes.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | xunit (C#, `DG/tests/DG.Tests`); pytest (Python, `tools/de01/tests`, `dg-reasoner/tests`, `data-service` tests) |
| Config file | `DG/tests/DG.Tests/DG.Tests.csproj`; no separate pytest.ini located this session — pytest invoked directly per README |
| Quick run command | `dotnet test DG/tests/DG.Tests/ --filter "FullyQualifiedName~SwrlRuleParser\|FullyQualifiedName~RuleEvaluator"` (scoped); `python -m pytest tools/de01/tests/test_de01_runner.py -x -q -k "not live"` |
| Full suite command | `dotnet test DG/tests/DG.Tests/`; `python -m pytest tools/de01/tests/test_de01_runner.py -x -q -k "live"` (requires stack) |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGN12-05 | `SwrlRuleParser.TryParse` correctly classifies `ObjectPropertyAtom` when OntoGraph resolves it, and reports `unsupported` when it does not | unit | `dotnet test DG/tests/DG.Tests/ --filter FullyQualifiedName~SwrlRuleParser` | Wave 0 — new test file needed (e.g. `SwrlRuleParserTryParseTests.cs`); existing `VariableTypeInferrerTests.cs` shows the assertion-style precedent for `ObjectPropertyAtom` at `:108,126` but does not test the parser itself |
| ALGN12-05 (fixture corpus) | The 8 required parser conformance cases (ObjectPropertyAtom, malformed arity, quoted commas, escaping, duplicate arrows, datatype literals, language literals, unsupported syntax) all produce the expected typed result | unit (table-driven) | New test reading `fixtures/golden/parser/*` | Wave 0 — both the fixture directory and its consuming test are net-new (D-16) |
| ALGN12-06 | `RuleEvaluator` never throws for zero bindings, missing binding, or unsupported builtin — each yields the D-06/D-07/D-08 typed status | unit | `dotnet test DG/tests/DG.Tests/ --filter FullyQualifiedName~RuleEvaluator` | Wave 0 — existing `RuleEvaluator` tests were not located in this session; planner should check `DG/tests/DG.Tests/` for a `RuleEvaluatorTests.cs` and extend it, or create one if absent |
| ALGN12-06 (cross-service) | DE-01's `silent_disagreement_count = 0` (or every disagreement declared) against the frozen golden fixture | integration/manual-only (requires live stack) | `python tools/de01/run_de01.py` (exit code gate) | `.de01/de01-report.json` exists as prior output; the runner itself (`tools/de01/run_de01.py`) exists and is reusable as-is — no new test file needed, just a re-run |
| ALGN12-07 | The supported-builtin allow-list constant matches what `spec/SWRL-SUBSET.md` documents | unit (drift guard) | New test importing the `DG.Core` constant and asserting it matches a literal list mirroring the spec doc | Wave 0 — both the constant and its guard test are net-new |

### Sampling Rate

- **Per task commit:** scoped `dotnet test --filter` on the touched class, plus `pytest -k "not live"` if `tools/de01` files changed.
- **Per wave merge:** full `dotnet test DG/tests/DG.Tests/` and, if environment allows, a live DE-01 re-run.
- **Phase gate:** D-11 requires a genuine DE-01 re-run with `silent_disagreement_count = 0` (or fully declared) as the phase's own exit evidence — this is stricter than the default Nyquist sampling rate and must not be waived by unit tests alone, per CONTEXT.md's explicit instruction ("Unit tests alone are not sufficient exit evidence for this phase").

### Wave 0 Gaps

- [ ] `fixtures/golden/parser/` — the entire directory and its contents (D-16) do not exist yet; this is the phase's own deliverable, not a pre-existing gap, but it must exist before the corpus-driven test can be written
- [ ] A parser conformance test file (name TBD by planner) consuming the new fixture corpus
- [ ] Verify whether `DG/tests/DG.Tests/` already has a `RuleEvaluatorTests.cs` — this session did not locate one via graphify or direct listing; the planner's Wave 0 should confirm via `Glob DG/tests/DG.Tests/**/*Evaluator*Tests.cs` before assuming a from-scratch test file is needed
- [ ] `tools/de01/tests/test_de01_runner.py` — confirm it already covers `run_leg_dg_reasoner`'s current (buggy) behavior; if so, that test's expectations will need updating alongside the D-09 fix, not just the production code

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase touches no auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | The parser's `TryParse` is itself an input-validation surface for architect-authored SWRL text; D-01/D-03/D-04 already require it to classify malformed/unsupported input into typed diagnostics rather than throwing raw exceptions up to a caller — this IS the ASVS V5 control for this phase's scope, no additional library needed (a hand-rolled regex-based parser is appropriate here since it is intentionally NOT a general SWRL/OWL parser, per D-14) |
| V6 Cryptography | Marginal | `CanonicalJsonWriter`'s SHA-256 hashing (`inputHash`/`outputHash`, D-12) is integrity/comparison hashing, not a security control (no secret material, no authentication token) — standard `System.Security.Cryptography.SHA256`/Python `hashlib.sha256` usage, already implemented in Phase 1200, not re-implemented here |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/adversarial SWRL text causing a DoS via unbounded regex backtracking | Denial of Service | `SwrlRuleParser`'s existing `AtomRegex` (`^(?<predicate>[^\(]+)\((?<args>.*)\)$`) is a simple, non-catastrophic-backtracking pattern; the planner should confirm any NEW regex added for quoted-comma/escaping handling (fixture cases) does not introduce nested-quantifier backtracking risk (e.g. avoid `(.*)*`-style patterns) |
| A crafted rule string causing an uncaught exception to propagate into a Grasshopper-hosted process (crashing the host application) | Denial of Service / Information Disclosure (stack trace) | This is precisely what D-01/D-06/D-07/D-08 already fix — the entire phase is a mitigation for this threat pattern, converting throw-based failure into typed, caught outcomes at the API boundary |

## Sources

### Primary (HIGH confidence — verified this session via direct file read or `graphify query`)
- `DG/src/DG.Core/Parsing/SwrlRuleParser.cs` — full file read, all line numbers in this document verified
- `DG/src/DG.Core/Validation/RuleEvaluator.cs` — full file read, all line numbers verified
- `DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs` — full file read, `RollupPrecedence` verified
- `data-service/evidence_contract.py` — `_ROLLUP_PRECEDENCE`, `build_envelope`, `EvidenceRow` verified
- `data-service/app.py:2160-2192` — `build_envelope` call site verified to omit hashes
- `dg-reasoner/reasoning.py` — full file read, `run_shacl`/`_hybrid_union` behavior verified
- `dg-reasoner/ontology_export.py` — full file read, `build_graph`'s query scope verified
- `ontology/dg-shapes.ttl` — full file read, all `sh:targetClass` values verified
- `fixtures/golden/seed.cypher`, `fixture.json`, `MANIFEST.md` — full files read
- `tools/de01/run_de01.py`, `tools/de01/legs.py` (partial), `tools/de01/report.py` (full), `tools/de01/README.md` — verified
- `.de01/de01-report.json` — the actual prior DE-01 run artifact, used as primary evidence for the D-09/D-12 diagnoses
- `DG/src/DG.Core/Parsing/RecognitionMarker.cs`, `DG/src/DG.Core/Services/ErrorMessageTemplates.cs`, `DG/src/DG.Core/Parsing/VariableTypeInferrer.cs`, `DG/src/DG.Core/Data/IRuleRepository.cs` — verified as reuse precedents
- `DG/tools/DG.De01Harness/Program.cs` — full file read, hash/status-mapping call sites verified
- `spec/EVIDENCE-CONTRACT.md`, `spec/evidence-contract.schema.json` (partial) — read per task instructions
- `.planning/phases/1201-.../1201-CONTEXT.md`, `.planning/REQUIREMENTS.md` (lines 1-16) — read per task instructions
- `DG/src/DG.Core/DG.Core.csproj` — `TargetFrameworks` confirmed `net7.0;net9.0`

### Secondary (MEDIUM confidence)
- `.planning/milestones/v12.0-ROADMAP.md` Phase 1201 section — referenced by CONTEXT.md but not independently re-read this session (CONTEXT.md's own summary of the ROADMAP gate wording was treated as sufficient and consistent with REQUIREMENTS.md)
- Phase 35-12 `GRAMMAR_CITATION_PATTERNS` precedent — cited from CONTEXT.md's own text, not independently re-located in this session's file exploration; the pattern description is specific enough to replicate without finding the exact file

### Tertiary (LOW confidence)
- None — every claim in this document that could be checked against a file was checked; no claim relies on unverified training-data knowledge about this specific codebase's internals.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A (no new packages) — HIGH by default (nothing to get wrong)
- Architecture (TryParse/resolver injection patterns): HIGH — directly copying two already-shipped, in-repo patterns
- D-09 root cause diagnosis: HIGH — confirmed via direct code read (`legs.py` call site, `run_shacl` docstring, `ontology_export.py` query scope, `dg-shapes.ttl` targetClasses) cross-checked against the actual `.de01/de01-report.json` artifact showing the predicted symptom
- D-09 fix approach: MEDIUM — the root cause is certain; whether "pass run_id" fully resolves the golden fixture's expected passed/failed split (vs. producing a new declared non-equivalence, per Assumption A1) is not certain until executed against a live stack
- D-12 diagnosis: HIGH — confirmed via direct code read of both call sites and the report extraction logic
- Pitfalls: HIGH — each pitfall is grounded in a specific, cited file:line, not a generic warning
- Aggregation precedence recommendation: HIGH — the recommended precedence is not proposed, it is a verified quote of already-shipped, cross-language-matched production code

**Research date:** 2026-09-20
**Valid until:** This research is tied to a specific, frozen fixture (`fixtures/golden/`, FIXTURE_VERSION 1.2.0) and a specific prior DE-01 run (`.de01/de01-report.json`, generated 2026-09-20T12:33:43Z). It remains valid as long as neither changes; if Phase 1200's gap-closure work (waves 4-5, left mid-execution per CONTEXT.md's upstream caveat) alters the envelope shape or the fixture, re-verify against the schema before planning further. Recommend re-validation within 14 days or immediately upon any Phase 1200 gap-closure merge, whichever comes first.
