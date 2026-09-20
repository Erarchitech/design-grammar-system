# Phase 1201: Rule Parser and Evaluator Conformance - Context

**Gathered:** 2026-09-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the implemented C# rule subset **explicit and safe**: every construct the evaluator cannot
handle must produce a *typed non-verdict outcome* drawn from the frozen Phase 1200 vocabulary,
never a thrown exception and never an ordinary `failed`.

Four deliverables, from `.planning/milestones/v12.0-ROADMAP.md` Phase 1201:

1. **Typed parser fixtures** — ObjectPropertyAtom, malformed arity, quoted commas, escaping,
   duplicate arrows, datatype/language literals, unsupported syntax.
2. **Explicit `unsupported`/`indeterminate` outcomes** for unsupported built-ins and predicate forms.
3. **Documented distinction** between schema-level SWRL atom types and the bounded C# evaluator subset.
4. **No general-reasoner claim** for the C# path.

**Requirements:** ALGN12-05, ALGN12-06, ALGN12-07 (`.planning/REQUIREMENTS.md`).
**Package:** `ALIGN-P03`.
**Requires:** 1200 (the frozen contract — see the caveat below).
**Blocks:** v9.1 activation where shared parser/status surfaces are consumed; v10.0 semantic-boundary gate.

**Gate:** supported fixtures pass; unsupported fixtures return typed non-verdict outcomes; no
unsupported construct becomes an ordinary failure.

</domain>

<upstream_caveat>
## Phase 1200 is not gap-closed — planning proceeds against a contract that may still shift

Recorded at the user's explicit instruction (2026-09-20): autonomous execution runs
**1201–1205 with 1200 left mid-execution**. Phase 1200 currently reads
`verification_status: gaps_found` with gap-closure plans 1200-06/07/08 created; waves 4–5 were
unexecuted at the time this context was gathered.

**What is nonetheless safe to build on** (verified on disk, 2026-09-20):

- `spec/EVIDENCE-CONTRACT.md` exists (24,980 bytes).
- `spec/evidence-contract.schema.json` is the shape authority (cited by `EvidenceStatus.cs`).
- `DG/src/DG.Core/Contracts/` ships `EvidenceStatus.cs`, `EvidenceStatusNames.cs`,
  `EvidenceEnvelope.cs`, `EvidenceEnvelopeFactory.cs`, `CanonicalJsonWriter.cs`.
- `EvidenceStatus` is the frozen 8-member enum: `Passed, Failed, Unknown, NotEvaluated,
  NoPopulation, Unsupported, Indeterminate, Error` — wire form lives in `EvidenceStatusNames`.
- `fixtures/golden/` holds `fixture.json`, `canonical-vectors.json`, `seed.cypher`, `MANIFEST.md`.
- `ALGN12-01` and `ALGN12-03` are recorded as genuinely satisfied.

**What is still open and could move under this phase's feet:**

- `ALGN12-02` was re-closed by plan 1200-06 (CR-01 decimal-scale parity fixed), but
  `ALGN12-04` **stays open** — DE-01's acceptance condition "supported cases agree canonically"
  is not yet met.
- `inputHash` / `outputHash` were `null` on every leg for every row in the last DE-01 run, so
  CR-01's fix is unobserved at the live service boundary.

**Planner instruction:** treat the `EvidenceStatus` enum and `EVIDENCE-CONTRACT.md` semantics as
stable (D-02 declares the vocabulary one-way/frozen). Do **not** edit `fixtures/golden/fixture.json`
(D-11 freeze). If a 1200 gap-closure lands mid-phase and changes envelope *shape*, re-verify
against the schema rather than re-deriving intent.

</upstream_caveat>

<routed_finding>
## Finding routed into this phase by Phase 1200's verification

`.planning/REQUIREMENTS.md` line 16 records, verbatim, that plan 1200-08 executed DE-01's first
genuine four-leg run (all four legs `available: true`) and it reported
**`silent_disagreement_count = 3`**:

> dg-reasoner returned `no_population` (pySHACL `conforms=true` with zero findings — an empty
> target set, not a real evaluation) on all three golden objects, disagreeing with
> data-service / csharp / replay's real `passed`/`failed` verdicts on two of them.
>
> **Finding routed to Phase 1201:** dg-reasoner's SHACL shapes are not targeting the seeded
> `DG-1200-GOLDEN` objects (`OBJ_GOLD_PASS` / `OBJ_GOLD_FAIL`).

This is explicitly distinguished, in the same note, from the **pre-declared, by-design**
`ObjectPropertyAtom` / `SwrlRuleParser.ResolveAtomType` non-result (ALGN12-05), which behaved as
expected in that run. Two separate things; this phase owns both.

Also routed here by decision (Area 3 Q4): the `inputHash`/`outputHash` `null`-at-the-live-boundary
problem from the same run.

</routed_finding>

<decisions>
## Implementation Decisions

Four grey areas were presented as batch proposal tables and **all four were accepted in full**
("Accept all" on each) by the user on 2026-09-20.

### Parser Outcome Model

- **D-01:** The parser gains an **additive `TryParse`-style entry point returning a typed result**
  that carries an `EvidenceStatus` plus diagnostics. The existing throwing `Parse` is **retained**
  as a thin wrapper over it.
  **Rationale:** matches the repo's additive-not-breaking house style and Phase 1200's own D-03
  (canonical status travels in a new parallel surface; legacy surfaces retained, documented
  non-authoritative). Every current caller of `Parse` keeps compiling.
  **Evidence:** `SwrlRuleParser.Parse` throws at `:17` (empty), `:23` (arrow arity), and
  `ParseAtoms` throws at `:55` (atom regex miss) — three distinct malformed-input classes that
  today are indistinguishable to a caller that only sees an exception type.
  — **Reversibility:** reversible.

- **D-02:** `ObjectPropertyAtom` is distinguished from `DataPropertyAtom` by **resolving the
  predicate IRI against the OntoGraph**: present as `ObjectProperty` → `ObjectPropertyAtom`,
  present as `DatatypeProperty` → `DataPropertyAtom`. **Unresolvable → `unsupported`, never a
  silent default.**
  **Rationale:** arity cannot distinguish them — both are 2-argument. `ResolveAtomType`
  (`SwrlRuleParser.cs:82-94`) currently returns `"DataPropertyAtom"` for *every* predicate with
  ≥2 args, so `ObjectPropertyAtom` is unreachable by construction. Guessing is precisely the
  silent-misclassification this milestone exists to end.
  **Planner note:** this introduces a predicate-kind lookup dependency into a class that is
  currently pure/static. Resolve the injection shape during planning (an injected resolver
  interface with a null-object default is the obvious candidate); a hard dependency on a live
  Neo4j read from inside the parser would be wrong.
  — **Reversibility:** costly — the parser's signature and its callers change.

- **D-03:** An atom the parser cannot classify is **emitted with an `UnsupportedAtom` type and
  `unsupported` status. It is never dropped and never guessed at.**
  **Rationale:** directly satisfies the ROADMAP gate "no unsupported construct becomes an ordinary
  failure". Dropping loses evidence; guessing manufactures a false verdict.
  — **Reversibility:** one-way — 1201's own gate is written against this.

- **D-04:** Parser diagnostics are a **`ParseDiagnostic` list on the result** (code + message +
  offset), reusing the **What+Where+How-to-fix** wording pattern from
  `DG/src/DG.Core/Services/ErrorMessageTemplates`.
  — **Reversibility:** reversible.

### Evaluator Status Emission

- **D-05:** `RuleEvaluationResult` gains an **additive `Status` property of type
  `DG.Core.Contracts.EvidenceStatus`** (the frozen 1200 enum). The existing `Passed` boolean is
  **retained and documented as non-authoritative**, per 1200's D-03/D-04 — canonical → boolean is
  lossy and defined; boolean → canonical is forbidden.
  — **Reversibility:** costly — removing `Passed` later is a migration across every reader.

- **D-06:** **Zero bindings → `no_population`.** `RuleEvaluator.cs:24-34` currently returns
  `Passed = false` with "No variable bindings were provided." — an empty population reported as a
  genuine failure. This is 1200's D-05 table applied verbatim.
  — **Reversibility:** one-way.

- **D-07:** **An unsupported builtin returns `unsupported`; it does not throw.**
  `RuleEvaluator.cs:130` throws `NotSupportedException("Unsupported builtin in MVP evaluator")`
  and `:138` throws `NotSupportedException("Builtin requires numeric arguments…")`. Both become
  typed outcomes. This is ALGN12-06's whole content.
  **Compounding defect to fix with it:** the throw at `:130` is swallowed by the catch at
  `:52-56`, which adds the binding to `failingBindings` — so an unsupported builtin is today
  reported as *a rule violation*. That is the exact failure mode the gate forbids.
  — **Reversibility:** one-way.

- **D-08:** **A missing variable binding → `unknown`** ("binding resolution attempted and
  unresolvable", 1200 D-05 table). Today `EvaluateAtom:100` and `ResolveArgValue:148` throw
  `InvalidOperationException("Missing binding for variable …")`, caught at `:52` and counted as a
  failing binding — a third distinct outcome collapsed into `failed`.
  — **Reversibility:** one-way.

**Consequence the planner must handle:** with D-06/D-07/D-08, a single rule evaluated over many
bindings can yield a *mix* of per-binding outcomes. The plan must decide and document how
per-binding statuses aggregate to one rule-level `Status` — and the aggregation rule must not let
an `unsupported` or `unknown` binding silently become `failed`. Suggested precedence
(planner may refine, but must state it): `error` > `unsupported` > `unknown` > `indeterminate` >
`failed` > `no_population` > `not_evaluated` > `passed`.

### dg-reasoner SHACL Targeting (routed finding)

- **D-09:** **Fixing the SHACL shape targeting is in scope for 1201.** Diagnose why
  `ontology/dg-shapes.ttl` shapes do not target the seeded `DG-1200-GOLDEN` objects
  (`OBJ_GOLD_PASS` / `OBJ_GOLD_FAIL`), and fix it so the reasoner leg genuinely evaluates them.
  **Rationale:** 1200 routed it here by name, and 1201's gate is precisely about typed-vs-silent
  outcomes.
  — **Reversibility:** reversible.

- **D-10:** If the shapes genuinely **cannot** target those objects, the outcome is recorded as a
  **declared typed non-equivalence with a written reason** in the contract — never left silent.
  *"Silent disagreement is a failure; a declared one is not."*
  **Forbidden:** editing `fixtures/golden/fixture.json` to match the shapes (violates 1200's D-11
  freeze), or weakening the gate.
  — **Reversibility:** reversible.

- **D-11:** **1201 re-runs DE-01 as its exit evidence**, and requires
  **`silent_disagreement_count = 0`** — or every remaining disagreement explicitly declared with a
  reason. Unit tests alone are not sufficient exit evidence for this phase.
  — **Reversibility:** one-way — this is a gate definition.

- **D-12:** The **`inputHash` / `outputHash` `null`-at-the-live-service-boundary** problem is in
  scope. The envelope must carry real hashes where the legs actually meet, otherwise 1200's CR-01
  decimal-scale fix remains unobservable outside unit tests.
  — **Reversibility:** reversible.

### Documentation and Subset Boundary (ALGN12-07)

- **D-13:** The supported-subset boundary is documented in a **new normative `spec/SWRL-SUBSET.md`**,
  cross-referenced from `spec/EVIDENCE-CONTRACT.md` and `spec/RULE-PARTITION-POLICY.md`.
  **Rationale:** matches the repo's one-concern-per-spec-doc pattern; `RULE-PARTITION-POLICY.md`
  is the closest structural analog and already governs SWRL-vs-SHACL ownership.
  **Mandatory:** adding a spec doc triggers `CLAUDE.md` § Schema Change Propagation — the planner
  must check that list and propagate as required.
  — **Reversibility:** costly once downstream phases cite the path.

- **D-14:** The "not a general SWRL/OWL reasoner" assertion is an **explicit non-claims section**
  listing what is *not* supported — ObjectPropertyAtom **evaluation**, string/date builtins,
  negation, OWL inference — **each mapped to the status it yields**.
  **Note the asymmetry D-02 creates:** after this phase the parser can *recognize* an
  `ObjectPropertyAtom`, while the evaluator still cannot *evaluate* one. The doc must state that
  split plainly, and the evaluator must return `unsupported` for it rather than the
  `return true` variable-availability shortcut it takes today (`RuleEvaluator.cs:104-105`).
  — **Reversibility:** reversible.

- **D-15:** The boundary is **machine-checkable**: a **supported-builtin allow-list constant in
  `DG.Core`** that both the evaluator and a conformance test read, so the document and the code
  cannot drift.
  **Precedent:** Phase 35-12's `GRAMMAR_CITATION_PATTERNS` — moved to production and imported by
  the test so the online guard and the offline metric can never disagree.
  **Current implicit list** (from `RuleEvaluator.cs:124-129` / `:136-137`): `swrlb:lessThan`,
  `swrlb:greaterThan`, `swrlb:lessThanOrEqual`, `swrlb:greaterThanOrEqual`, `swrlb:equal`,
  `swrlb:notEqual` — numeric comparison for all six, plus `equal`/`notEqual` on non-numerics.
  — **Reversibility:** reversible.

- **D-16:** The parser conformance corpus lives in **`fixtures/golden/parser/`** — under the
  shared golden root (1200's D-09: one shared fixture directory, per-service copies forbidden),
  in a **separate subdirectory** so the frozen `fixture.json` is untouched (D-11).
  — **Reversibility:** reversible.

### Claude's Discretion

The user accepted all recommendations without override. Within the decisions above, the planner
retains discretion on:

- the concrete name and shape of the additive parse-result type and its `TryParse` entry point;
- the injection mechanism for the OntoGraph predicate-kind resolver (D-02) — including whether a
  null-object default keeps `SwrlRuleParser` usable without a graph;
- the exact per-binding → rule-level status aggregation precedence, provided it is **stated
  explicitly** and never lets `unsupported`/`unknown` decay into `failed`;
- file split within `fixtures/golden/parser/` (one file per case vs a single table-driven corpus);
- whether `spec/SWRL-SUBSET.md` carries the allow-list inline or generates it from the `DG.Core`
  constant.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contract this phase consumes (Phase 1200 output)
- `spec/EVIDENCE-CONTRACT.md` — semantic authority for what each status asserts
- `spec/evidence-contract.schema.json` — shape authority for the wire-form literal set
- `DG/src/DG.Core/Contracts/EvidenceStatus.cs` — the frozen 8-member enum (wire form lives in
  `EvidenceStatusNames.cs`, **not** on the enum)
- `DG/src/DG.Core/Contracts/EvidenceEnvelope.cs`, `EvidenceEnvelopeFactory.cs`,
  `CanonicalJsonWriter.cs` — envelope emission and canonical-JSON hashing
- `fixtures/golden/` — `fixture.json` (**frozen, do not edit**), `canonical-vectors.json`,
  `seed.cypher`, `MANIFEST.md`
- `.planning/phases/1200-.../1200-CONTEXT.md` — D-01..D-16, especially the **D-05 status table**
  that D-06/D-07/D-08 here apply verbatim

### Milestone-level source of truth
- `.planning/milestones/v12.0-CONTEXT.md` — locked milestone decisions, constraints, open questions
- `.planning/milestones/v12.0-ROADMAP.md` — Phase 1201 deliverables and gate wording
- `.planning/REQUIREMENTS.md` — ALGN12-05/06/07; **line 16** carries the routed finding verbatim

### Alignment-plan evidence base
- `docs/reviews/theory-implementation-alignment/parts/csharp.md` — the C# parser/evaluator/replay
  findings; the primary evidence base for `ALIGN-P03`
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md` §8 —
  work packages

### Code this phase changes (verified 2026-09-20)
- `DG/src/DG.Core/Parsing/SwrlRuleParser.cs`
  - `:13-44` `Parse` — throws at `:17` (empty), `:23` (arrow arity ≠ exactly one `->`)
  - `:46-80` `ParseAtoms` — throws at `:55` on atom-regex miss
  - `:82-94` `ResolveAtomType` — **`ObjectPropertyAtom` unreachable**; every ≥2-arg non-`swrlb:`
    predicate returns `"DataPropertyAtom"`
  - `:96-107` `SplitArgs` — naive `Split(',')`; **quoted commas are not honored** (fixture case)
  - `:109-152` `ParseArg` — strips quotes at `:149`; **no language-tag or explicit-datatype
    (`"x"^^xsd:…`, `"x"@en`) handling** (fixture case)
- `DG/src/DG.Core/Validation/RuleEvaluator.cs`
  - `:22-34` zero bindings → `Passed = false` (→ D-06 `no_population`)
  - `:52-56` catch-all that turns *any* exception into a **failing binding** (the collapse point)
  - `:89-106` `EvaluateAtom` — `:100` throws on missing binding (→ D-08 `unknown`);
    `:104-105` class/data-property atoms are a bare `return true` variable-availability check
  - `:108-140` `EvaluateBuiltin` — `:114` throws on arity < 2; **`:130` and `:138` throw
    `NotSupportedException`** (→ D-07 `unsupported`)
  - `:124-129`, `:136-137` — the six supported builtins; the implicit allow-list D-15 makes explicit
- `ontology/dg-shapes.ttl` — SHACL shapes; **the D-09 targeting defect lives here or in the
  export/seed path**
- `dg-reasoner/reasoning.py` — `run_shacl` and the `{conforms, results, counts}` envelope;
  `conforms=true` with zero findings is what produced the false `no_population`
- `dg-reasoner/ontology_export.py` — `build_graph`, `strip_hermit_unsupported` (`:406`);
  relevant if the golden objects are not reaching the export at all

### Propagation obligation
- `CLAUDE.md` § Schema Change Propagation — **mandatory** file list; `spec/EVIDENCE-CONTRACT.md`
  and `ontology/dg-shapes.ttl` are both named there, and D-13 adds a new spec doc

</canonical_refs>

<code_context>
## Existing Code Insights

### The three-into-one collapse, precisely located

`RuleEvaluator` has exactly one place where distinct outcomes become the same boolean — the catch
at `:52-56`:

```
catch (Exception ex) { firstError ??= ex.Message; failingBindings.Add(binding); }
```

Every throw upstream of it lands here and becomes **a failing binding**:

| Throw site | True meaning | Today | D-05 target |
|---|---|---|---|
| `EvaluateAtom:100` / `ResolveArgValue:148` | binding unresolvable | failing binding | `unknown` |
| `EvaluateBuiltin:114` | builtin arity < 2 | failing binding | `unsupported` (malformed) |
| `EvaluateBuiltin:130` | builtin not implemented | failing binding | `unsupported` |
| `EvaluateBuiltin:138` | builtin needs numerics | failing binding | `unsupported` |
| `EvaluateRule:24-34` (no throw) | empty population | `Passed=false` | `no_population` |

Four of the five never reach the boolean as a *verdict* at all — they arrive as exceptions and are
reinterpreted as violations.

### Parser gaps the fixtures must cover

Mapping ROADMAP deliverable 1 to verified parser behavior:

| Fixture case | Current behavior | Site |
|---|---|---|
| ObjectPropertyAtom | **unreachable** — classified `DataPropertyAtom` | `:82-94` |
| malformed arity | throws `FormatException` | `:55` (atom), `:114` (builtin) |
| quoted commas | **split mid-literal** — naive `Split(',')` | `:104` |
| escaping | no escape handling | `:96-107`, `:109-152` |
| duplicate arrows | throws `FormatException` "exactly one '->'" | `:21-24` |
| datatype literals | inferred only (`xsd:boolean`/`integer`/`decimal`/`string`); **no `^^` form** | `:122-151` |
| language literals | **not handled** — `@en` would fall through to `xsd:string` | `:145-151` |
| unsupported syntax | throws | `:55` |

### Reusable Assets
- **`DG.Core.Contracts`** (Phase 1200) — `EvidenceStatus`, `EvidenceStatusNames`,
  `EvidenceEnvelope`, `EvidenceEnvelopeFactory`, `CanonicalJsonWriter`. This phase **consumes**
  these; it does not define new status types.
- **`ErrorMessageTemplates`** (`DG/src/DG.Core/Services/`) — What+Where+How-to-fix wording pattern
  that D-04 reuses for `ParseDiagnostic`.
- **`VariableTypeInferrer`** — already reasons about `ObjectPropertyAtom` positions
  (`DG/tests/DG.Tests/VariableTypeInferrerTests.cs:108,126` test that exact atom type), so the
  concept exists in the type system even though the parser never emits it. Useful prior art for
  D-02's resolution logic.
- **`fixtures/golden/`** — the shared-fixture root D-16 extends with a `parser/` subdir.

### Established Patterns
- **Additive-not-breaking** is house style: Phase 823's `shaclReportJson`, Phase 824's additive
  heartbeat, Phase 38's nullable `reinstateParameterId`, Phase 1200's D-03. D-01 and D-05 follow it.
- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards GH-dependent code. All work here is
  `DG.Core` (no Grasshopper dependency), which is also what makes it testable from `DG.Tests`.
- **Multi-targeting** — `DG.Core` targets **net7.0 and net9.0**. Phase 32.1 hit this: no `net8+`-only
  APIs (`ArgumentException.ThrowIfNullOrWhiteSpace`), and Phase 38-05 hit it again
  (`JsonObjectCreationHandling.Populate` is .NET 8+). Constrain to net7.0-compatible APIs.
- **Single-source-of-truth constants shared by prod and test** — Phase 34-01's grammar extraction
  and Phase 35-12's `GRAMMAR_CITATION_PATTERNS`. D-15 follows it.

### Integration Points
- `DG.Core/Parsing/SwrlRuleParser.cs` — additive `TryParse` + `ResolveAtomType` rework
- `DG.Core/Validation/RuleEvaluator.cs` — `Status` emission; the `:52` catch-all is the fulcrum
- `DG.Core/Validation/ValidationPublishPackageBuilder.cs` — `:34-42` returns `Passed=false` for
  *no result exists* (→ `not_evaluated`); 1200's context names it, and it is the natural consumer
  of this phase's typed status
- `ontology/dg-shapes.ttl` + `dg-reasoner/` — the D-09 targeting fix
- The DE-01 runner (built in 1200) — D-11 re-runs it as exit evidence

### Test baselines (parent-reported in 1200-CONTEXT, not re-run this session)
data-service pytest 772 passed / 1 skipped / 8 deselected; dg-reasoner 39 passed;
DG .NET 412 passed; .NET Release build 0 warnings / 0 errors.

**Environment caveat (known, not a regression):** 4 `DesignStateValidationFlowTests` fail fast when
Neo4j is down, and 4 `test_dg_context.py` tests fail from the host — the `neo4j` hostname resolves
only inside compose. D-11's DE-01 re-run needs the compose stack up; plan for that explicitly.

**Docker caveat (bit Phase 38-06 and 1200-08):** `data-service` has no source volume mount. A
stale image silently runs pre-change code. 1200-08 had to rebuild it mid-plan for exactly this
reason. If D-09/D-12 touch data-service or dg-reasoner, rebuild before measuring.

</code_context>

<specifics>
## Specific Ideas

- **The governing sentence, inherited from 1200 and binding here:** *"Silent disagreement is a
  failure; a declared one is not."* Any place this phase could quietly coerce, drop, or normalize
  away a difference is a defect.
- **`failed` must become expensive to say.** 1200 defined that; 1201 is the phase that actually
  takes three things currently reported as `false` and stops calling them failures.
- **Two different `ObjectPropertyAtom` problems, do not conflate them.** 1200's verification note
  is explicit: the parser's inability to *emit* `ObjectPropertyAtom` (ALGN12-05, by design,
  behaved as expected in the DE-01 run) is **separate** from dg-reasoner's shapes not *targeting*
  the golden objects. This phase fixes both, but they are distinct defects with distinct evidence.
- **D-02 creates a recognize/evaluate asymmetry on purpose.** After this phase the parser can
  classify an `ObjectPropertyAtom`; the evaluator still cannot evaluate one and must say
  `unsupported`. D-14 requires that split be stated plainly rather than papered over.

</specifics>

<deferred>
## Deferred Ideas

| Idea | Owner | Note |
|---|---|---|
| Actually *evaluating* `ObjectPropertyAtom` (not just recognizing it) | Not this phase | 1201 makes it a typed `unsupported`; implementing OWL object-property semantics is a general-reasoner claim D-14 explicitly disclaims |
| `Neo4jValidGraphRepository.RunsQuery` run-level aggregate repeated across objects | **1202** | ALGN12-10; inherited from 1200's deferred table |
| Design State content-equivalence vs capture-event identity | **1202** | Open question #3 |
| Which service owns canonical per-object verdicts | **1202** | Open question #5 — 1201 emits status; who arbitrates across services is 1202's |
| `ATTRIBUTE_OF` vs `PARAM_LINK` | **1203** | Milestone D8 |
| Identity authority across GH/Revit/IFC/Speckle | **1203** | Open question #7 |
| LLM reproducibility / provider snapshots | **1204** | Open question #10 |
| Authorization and project isolation | **1205** | Open question #9 |
| Full envelope propagation across the `CLAUDE.md` schema list | **v11.0 1105** | 1200 owns definition, 1105 owns propagation — coordinate, do not duplicate |
| Phase 1200's own gap closure (waves 4–5, plans 1200-06/07/08) | **Phase 1200** | Deliberately excluded from this autonomous run at user instruction; resume via `/gsd-plan-phase 1200 --gaps` |
| F-39-01 (auto-runs SHACL-validated before their own `ValidStatus` is written) | Not this phase | Pre-existing disclosed finding; the contract may describe it, fixing it is out of scope |
| `:ValidationRun` / `:Run` label and `Run_Id`/`runId` drift | Not this phase | Documented in `spec/DATABASE.md:111`; note, do not fix |

</deferred>

---

*Phase: 1201-Rule Parser and Evaluator Conformance*
*Context gathered: 2026-09-20*
