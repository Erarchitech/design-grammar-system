# Evidence and Outcome Contract

## Overview

This document is the **normative contract** for how every validation-producing service in Design
Grammar System reports the outcome of evaluating a rule against a design: the closed **status
vocabulary** every leg must emit, the **evidence envelope** shape that carries a verdict across a
stage boundary, the **canonical-JSON hashing rules** that make cross-language hashes comparable,
the **golden-fixture freeze policy**, and the **DE-01 cross-service acceptance rule**. It fulfills
requirements **ALGN12-01** (canonical status vocabulary), **ALGN12-02** (evidence envelope),
**ALGN12-03** (empty-population / ordering / adjacency semantics), and **ALGN12-04** (DE-01
acceptance: silent disagreement is a failure).

`EVIDENCE_CONTRACT_VERSION = "1.0.0"` remains the legacy factory/harness baseline.
`EVIDENCE_CONTRACT_VERSION_V2 = "2.0.0"` identifies the current opt-in shape with
rule-scoped results (Phase 1205.1). These are exact string tokens, not normalized semver.
`CANONICALIZATION_VERSION = 1` — the version of the canonical-JSON normalization rules in
[§6](#6-canonical-json-and-hashing-d-07). Both are carried in every evidence envelope
(`contractVersion`, `canonicalizationVersion`) so a consumer can tell which rules produced a given
hash or status without re-deriving it from context.

**Current source contract (Phase 1205.1):** the production GH publish mapper explicitly selects
`evidenceContractVersion: "2.0.0"`; Python persists that shape and both Python/C# readers support
it. This is local source integration, not deployment. Legacy boolean outcome surfaces (`Passed`,
`Run.ValidStatus`, `conforms`) and passed/failed entity lists remain independently written by
their existing algorithms. Other producers and old factories are not globally migrated.

**Normative scope:**
1. [Status Vocabulary](#1-status-vocabulary)
2. [Current Non-Conforming Behavior (informative)](#2-current-non-conforming-behavior-informative)
3. [Evidence Envelope](#3-evidence-envelope)
4. [Ordering and Identity of Evidence Rows](#4-ordering-and-identity-of-evidence-rows)
5. [Legacy Boolean Compatibility (D-03/D-04)](#5-legacy-boolean-compatibility-d-03d-04)
6. [Canonical JSON and Hashing (D-07)](#6-canonical-json-and-hashing-d-07)
7. [Golden Fixture and Freeze Policy (D-09/D-10/D-11)](#7-golden-fixture-and-freeze-policy-d-09d-10d-11)
8. [DE-01 Acceptance (D-12/D-13/D-14)](#8-de-01-acceptance-d-12d-13d-14)
9. [Enforcement](#9-enforcement)
10. [v11.0 Phase 1105 Handoff (D-15)](#10-v110-phase-1105-handoff-d-15)
11. [Consistency & Propagation](#11-consistency--propagation)

Related specs: `spec/evidence-contract.schema.json` (the machine-readable annex — authoritative for
**shape**; this document is authoritative for **meaning**, per D-01), `spec/DATABASE.md`
(§`:Run` node — the `evidenceEnvelopeJson` sidecar), `spec/DG-ID.md` (the `dgId` format the
envelope's identity fields reference), `spec/RULE-PARTITION-POLICY.md` (this document's structural
analog and the closest existing normative cross-service contract), `spec/SWRL-SUBSET.md` (the
implemented C# SWRL parser/evaluator subset boundary — Phase 1201, which subset of this document's
status vocabulary each unsupported SWRL construct actually yields).

---

## 1. Status Vocabulary

The canonical status vocabulary is exactly **eight** names, lower snake_case, adopted **verbatim**
per decision D-02: `passed`, `failed`, `unknown`, `not_evaluated`, `no_population`, `unsupported`,
`indeterminate`, `error`. No renaming, no additions, no merging in this phase. If a ninth outcome
is discovered during DE-01 execution, it is recorded as a finding for Phase 1201 and is **never**
silently added to this list.

`$defs.CanonicalStatus.enum` in `spec/evidence-contract.schema.json` is the single mechanical
authority for this vocabulary. No other file may hardcode a second copy of the eight names.

**`failed` is reserved for an evaluated rule with a genuine violation — nothing else.** An empty
population, an unresolvable binding, an unsupported construct, or an infrastructure fault are all
distinct situations and must never be reported as `failed`.

### D-05 situation table

| Situation | Canonical status |
|---|---|
| Rule evaluated, population non-empty, constraint satisfied | `passed` |
| Rule evaluated, population non-empty, constraint violated | `failed` |
| Rule evaluated, **population empty** (zero bindings) | `no_population` |
| Rule in scope but **never evaluated** (no result produced) | `not_evaluated` |
| Binding resolution **attempted and unresolvable** | `unknown` |
| Construct outside the implemented evaluator subset | `unsupported` |
| Evaluation attempted, result not determinable | `indeterminate` |
| Evaluation raised / infrastructure fault | `error` |

### Normative meaning of each status

- **`passed`** — the rule was evaluated against a non-empty population and every binding satisfied
  the constraint. This is the only status that maps to legacy boolean `true` (§5).
- **`failed`** — the rule was evaluated against a non-empty population and at least one binding
  violated the constraint. A genuine, evaluated violation — the one situation this vocabulary
  exists to isolate from every other collapse-to-`false` case.
- **`unknown`** — binding resolution was attempted for the rule's variables but at least one
  binding could not be resolved (e.g. a referenced entity or property value is missing from the
  design). The rule's truth value cannot be determined because its inputs are incomplete.
- **`not_evaluated`** — the rule was in scope for this run but no evaluation was ever attempted or
  no result was produced for it (e.g. it was silently dropped from a result set). Distinct from
  `unknown`: here evaluation itself never happened, rather than happening and failing to resolve.
- **`no_population`** — the rule was evaluated but its binding population was empty (zero rows to
  check). An empty population is a real, distinguishable evaluation outcome, not a failure and not
  a non-evaluation. **An empty population always maps to `no_population`, never to `failed`.**
- **`unsupported`** — the rule (or one of its atoms/builtins) uses a construct outside what the
  evaluator implements. This is a typed capability gap, not an error and not a violation.
- **`indeterminate`** — evaluation was attempted and did not raise, but the result cannot be
  rendered as a definite verdict (for example, a computation that would otherwise produce `NaN` or
  `Infinity`, per §6 rule 6). Distinct from `unknown`: here the inputs resolved but the *result*
  itself has no definite value.
- **`error`** — evaluation raised an exception, or the evaluating infrastructure itself faulted
  (timeout, unreachable dependency, unhandled exception). A typed non-result caused by failure of
  the evaluation mechanism, not of the design under evaluation.

---

## 2. Current Non-Conforming Behavior (informative)

The table below is the **historical Phase 1200 baseline**, not a description of current canonical
outputs. Phase 1201 added typed outcomes; Phase 1205.1 preserves genuine binding outcomes through
the production GH mapper, persistence and readers. The old boolean fields still cannot express
these distinctions and are intentionally retained. Historical line references are not current
navigation coordinates.

| Location | Current behavior | Should be |
|---|---|---|
| `DG/src/DG.Core/Validation/RuleEvaluator.cs:22-34` | Zero bindings (`bindings.Count == 0`) returns `Passed = false` | `no_population` |
| `DG/src/DG.Core/Validation/ValidationPublishPackageBuilder.cs:34-42` | No result exists for a rule (`resultById.TryGetValue` misses) — returns `Passed = false` | `not_evaluated` |
| `DG/src/DG.Core/Validation/RuleEvaluator.cs:130` | Unsupported SWRL builtin **throws** `NotSupportedException("Unsupported builtin in MVP evaluator")` — no result value at all | `unsupported` |

Two further pre-existing, disclosed behaviors that this contract can *describe* but does not fix:

- **F-39-01** (`spec/DATABASE.md:124`) — auto-validation runs are SHACL-validated before their own
  `ValidStatus` is written, so every auto-run self-violates `RunStatusShape_valid` and the
  conservative unmapped fallback flips every `ObjState` to `false`, regardless of the design's
  actual state. Not repaired here.
- **`:ValidationRun` / `:Run` label drift** (`spec/DATABASE.md:111`) — auto-validation code writes
  `:ValidationRun` nodes with a `runId` property spelling, while the manual VALIDATOR path and this
  document's convention use `:Run` with `Run_Id`. A known, pre-existing drift; noted, not widened,
  and not fixed by this phase.

---

## 3. Evidence Envelope

An **Evidence Envelope** is the artifact a stage emits to report the outcome of evaluating one or
more rules against a design. Its shape is normatively fixed in
`spec/evidence-contract.schema.json`: its root union selects `$defs.EvidenceEnvelope` for exact
old tokens `"1.0.0"`/`"1"` and `$defs.EvidenceEnvelopeV2` for exact `"2.0.0"`.
The table below describes shared fields; §3.1 defines the version-specific field and admission
policy (schema is authoritative for exact types/required-ness per D-01).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `contractVersion` | string | yes | Exact supported token; old factory `1.0.0`, historical literal `1`, or opt-in `2.0.0` (§3.1) |
| `canonicalizationVersion` | integer | yes | The `CANONICALIZATION_VERSION` (§6) used to compute any hashes in this envelope |
| `project` | string | yes | The project scope this evidence belongs to (matches the repo-wide `project` node property convention) |
| `definitionId` | string | yes | The Computgraph/design definition this evidence was produced for |
| `serviceName` | string | yes | The producing service (e.g. `dg-grasshopper-evaluator`, `data-service`, `dg-reasoner`) |
| `serviceVersion` | string | yes | The producing service's version identifier |
| `emittedAt` | string (RFC 3339 UTC, `Z` suffix) | yes | When this envelope was produced |
| `stage` | string | yes | The pipeline stage boundary this envelope was emitted at (§ D-06 — every stage that produces or transforms a verdict emits one, not only final persistence) |
| `canonicalStatus` | `CanonicalStatus` | yes | Envelope roll-up; v2 includes both rows and ruleResults, never an object-verdict substitute |
| `rows` | array of `EvidenceRow` | yes | The per-(rule, object) result rows (§4) |
| `ruleResults` | array of `EvidenceRuleResult` | v2 only, required | Rule-scoped outcomes, including rules with no object rows; forbidden with old tokens |
| `dgId` | string | no | The `dg:`-prefixed identity (`spec/DG-ID.md`) of the subject entity, where resolvable |
| `sourceRepresentation` | object or null | no | The native-platform representation this evidence traces back to (Grasshopper/Revit/IFC/Speckle), where applicable |
| `inputHash` | string (64 uppercase hex) | no | SHA-256 hex digest of this stage's canonicalized input (§6) |
| `outputHash` | string (64 uppercase hex) | no | SHA-256 hex digest of this stage's canonicalized output (§6) |
| `schemaVersion` | string | no | Version of the graph schema in effect (`CLAUDE.md` § Graph Schema v4) |
| `ontologyVersion` | string | no | `owl:versionInfo` of the OWL ontology in effect |
| `ruleVersion` | string | no | Version/identity marker of the rule corpus evaluated |
| `shapeVersion` | string | no | Version of the SHACL shapes (`ontology/dg-shapes.ttl`) in effect, where applicable |
| `provider` | string | no | LLM provider, where an LLM was involved in producing this stage's evidence |
| `model` | string | no | LLM model identifier, where applicable |
| `warnings` | array of string | no | Non-fatal, human-readable warnings in the What+Where+How-to-fix style (`ErrorMessageTemplates`) |

Each element of `rows` is an **EvidenceRow**:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `ruleId` | string | yes | The Metagraph `Rule_Id` this row evaluates |
| `objectId` | string | yes | The identity of the object/entity this row evaluates the rule against |
| `canonicalStatus` | `CanonicalStatus` | yes | This row's status, from the §1 vocabulary |
| `warnings` | array of string | no | Row-scoped warnings |
| `inputHash` | string (64 uppercase hex) | no | Row-scoped input hash, where the envelope-level hash is insufficiently granular |
| `outputHash` | string (64 uppercase hex) | no | Row-scoped output hash |
| `detail` | string | no | Free-text elaboration (e.g. which binding failed, or which builtin was unsupported) |

### 3.1 Exact versions, strict construction and bounded historical read

| Input | Full schema / `parse_envelope_model` admission | Python/C# persisted read |
|---|---|---|
| Full `1.0.0` or literal `1`, old shape | Accepted, original token retained | Accepted |
| Partial `1.0.0` or literal `1`, no ruleResults | Rejected for missing required metadata/rows | Bounded exception below |
| Full `2.0.0`, required rows and ruleResults | Accepted; models also enforce unique, ordinal-sorted ruleIds | Strict admission, no partial exception |
| Old token with ruleResults; v2 without ruleResults | Rejected | Absent evidence |
| Missing, numeric, null, unknown or nonexact token | Rejected, no coercion | Absent evidence |

Full construction forbids unknown root/row/rule-result fields. The root schema has ten required
old fields; v2 adds required `ruleResults`. An **EvidenceRuleResult** has required string `ruleId`,
recognized `canonicalStatus`, required string-array `warnings` (empty when none), and optional
non-null string `detail`. It has **no objectId**. Rule IDs are unique and sorted by UTF-16 ordinal
order by the named builders; models/readers reject duplicate or unordered rule-result identities.
The JSON Schema supplies record shape; identity uniqueness/order are additional model checks.

Historical read is deliberately not full writer admission. With exact old tokens only, root
metadata may be missing or have extra fields. `canonicalStatus`, when present, must be recognized;
`ruleResults` is forbidden. **Absent rows** is admitted; present rows must be a valid array of
existing strict EvidenceRow records (null, wrong type and invalid status reject). Python returns
the original decoded dict without inserting rows, timestamps, metadata or a normalized version.
C# reports EnvelopePresent=true and empty verdicts/collisions for admitted no-rows inputs: an
empty projection is not a synthesized row collection or a `no_population` assertion. A summary
of passed/failed never manufactures an object verdict.

The original C# literal-`1` fixture is a **full** ten-field envelope. The original Python
`{"contractVersion":"1.0.0","canonicalStatus":"passed"}` fixture is **partial, with no rows**.
Neither is rewritten. Newly added partial controls for both tokens are tests, not evidence that
historical missing metadata existed for the literal-`1` fixture.

`build_envelope` / `EvidenceEnvelopeFactory.Build` and their old version constants, empty-input
defaults and override APIs remain unchanged (Python empty rows default `no_population`; C# empty
rows default `not_evaluated`, an existing declared difference). New `build_envelope_with_rule_results` /
`BuildWithRuleResults` explicitly select v2 and derive the aggregate across the union of row and
rule-result statuses using existing precedence (error > failed > indeterminate > unsupported >
unknown > not_evaluated > no_population > passed). Empty union is `not_evaluated`; aggregate
override is not allowed for v2. An independently constructed empty envelope is valid; GH publish
additionally requires a nonempty declared rule set and exact result coverage.

### 3.1.1 Raw JSON and resource admission (review correction 1205.1)

Schema validation starts **after** JSON decoding. It cannot detect duplicate object members,
non-JSON numeric constants, or impose a nesting limit on arbitrary metadata. The publish route
and persisted evidence readers therefore apply the following additional technical boundary **before
version dispatch/model coercion** (including historical tokens):

- Each object must have unique decoded member names, including escaped-equivalent names and
  arbitrary nested metadata. Repeated identities in the `rows` **array** are different: they remain
  admitted and collision-reported, with the established status rollup; never last-member-wins.
- Numbers must be representable as finite binary64 values: NaN, Infinity, -Infinity, exponent
  overflow (e.g. `1e400`) and integer magnitudes overflowing binary64 are rejected. No conversion
  to null, no metadata stripping and no fabricated verdict. Ordinary decimal/exponent JSON numbers
  use the existing binary64 decoding semantics; this is not a change to canonical hashing.
- At most **128 nested containers**, counting the root object as 1 and each object/array as one
  more; scalar leaves do not add depth. This explicit operational bound replaces Python's accidental
  recursion limit and C#'s implicit 64-container default. Depth 70 now works in both readers;
  127/128 work, 129 and the previously crashing 700-array input reject. This is a newly documented
  resource constraint, not something JSON Schema alone guarantees, nor a general payload-size/DoS limit.
- Full envelope `canonicalizationVersion` uses JSON Schema integer semantics (integral numeric
  values including `1.0` and `1e0`, not strings/booleans), in **[-9007199254740991,
  9007199254740991]**, the interoperable safe-integer range. The schema now states that range
  explicitly rather than silently inheriting C# Int32. `1099511627776` is admitted. Writers still
  emit `1`; no canonicalization version/algorithm is changed. Historical projection still ignores
  unused root metadata types/ranges as in §3.1, but not raw syntax/finite/depth guards.
- Hashes are exactly 64 uppercase hex characters, and `dgId` exactly `dg:` plus 16 uppercase hex
  characters. Schema patterns now have an absolute end check plus exact lengths, rejecting a final
  newline; C# remains strict. No case, whitespace or version-token normalization.

Python applies iterative resource validation to raw-decoded **and in-memory** admission before
recursive normalization/schema/model/response operations. Persisted read failure returns None;
C# returns absent evidence with no verdicts. POST `/validation/publish` alone uses the rejecting
raw decoder and returns 422 before any Speckle/graph writes. Unrelated API decoders are unchanged.
The SHACL view sibling uses the same guarded JSON decoder because arbitrary report metadata can
otherwise fail actual JSON response serialization; state hash/projection algorithms are unchanged.
Old `1`/`1.0.0` no-rows dictionaries remain unmodified. Direct legacy constructor defaults/coercions
remain distinct from strict full admission; use `parse_envelope_model`/`IsStrictEnvelope` for that gate.

### 3.2 Production publish, diagnostics and rollout

Only **absence** of request `evidenceContractVersion` selects the old-client publish path, including
its existing absent/null/invalid supplied-map fallback. Explicit `"2.0.0"` selects the new path;
null, numeric, old, unknown and nonexact request tokens reject with validation error. Presence of
new fields does not activate v2. New requests require unique declared rules/results, exact rule
coverage, unique entity identities, unique in-scope entity ruleIds and canonicalStatuses keys equal
to those ruleIds. Canonical maps are authoritative; contradictory legacy lists cannot add canonical
rows. See `spec/API.md` for request fields.

Core associates typed outcomes with the **original BindingRow reference**, then aggregates by
exact ordinal `(ruleId, objectId)` using existing rollup. Rule aggregate is never copied to every
object. Null typed collection, nonempty population with empty typed list, or missing expected
association means `unknown` plus `typed_binding_outcome_unavailable`, not an inferred boolean
verdict. Inconsistent duplicate/foreign coverage carries `typed_binding_outcome_inconsistent`;
only genuine matching contributions affect the pair. No result for a supplied rule is
`not_evaluated`, associated only with refs in its explicit supplied population. Nonempty bindings
with no ElementRefs retain their actual rule outcome without fabricated object rows.

Genuine evaluator/builder rule warnings/detail flow through GH ruleResults to envelope.ruleResults;
pair warnings/detail flow through entity canonicalWarnings/canonicalDetails to EvidenceRow.
Warnings are string arrays, details are optional non-null strings. No empty-default-only diagnostic
claim is sufficient. The C# verdict projection has no diagnostic DTO field; diagnostics remain in
the accepted raw envelope. Missing/corrupt stored JSON (including decoder RecursionError) returns
None / absent evidence, never passed. SHACL/state sibling decode boundaries preserve their safe
fallbacks without changing hash/projection algorithms.

**Reader-first rollout is mandatory:** deploy compatible Python and C# readers before enabling
new GH writes. Source activation/Release build and offline captured-I/O tests are not deployment,
live Rhino geometry/Speckle/Neo4j UAT, historical backfill or runtime input/output-hash completeness.

**D-06 — emission point.** The envelope is emitted at **every stage boundary** where a verdict is
produced or transformed, not only at final persistence. A stage that reads an upstream verdict and
re-emits a transformed one (e.g. a replay leg re-deriving status from a persisted payload) emits
its own envelope. This is what makes a mid-pipeline divergence localizable in DE-01 (§8) rather
than only visible as an unexplained terminal mismatch.

---

## 4. Ordering and Identity of Evidence Rows

`rows` is ordered **lexicographically ascending by `objectId`, ties broken lexicographically by
`ruleId`**. Existing row ordering is unchanged. Ordering aids reproducible comparison; it does not
create positional equivalence with legacy `Run.ValidStatus` (that framing was retired in
`spec/DATABASE.md`). Per-object verdicts are identity-addressed, not list-position addressed.

Evidence rows are addressed by the **`(ruleId, objectId)` pair** as their identity, not by value.
Two fixture atoms or objects that are value-equal but are distinct entities (distinct identity)
remain **separately addressable** in evidence and are **never merged, collided, or deduplicated**
on value equality alone. Only an exact `(ruleId, objectId)` match refers to the same row. See §5.1
below for where this identity rule is enforced (detected and reported, not silently merged) on the
canonical C# per-object read path.

An **empty population** (zero bindings for a rule) produces no per-object rows for that rule and
the rule's own status is `no_population` — this is never represented as a `failed` row and is
never silently omitted from the envelope; the rule still appears with its `no_population` status
even though it contributes zero `EvidenceRow` entries. In `2.0.0` this is an explicit ruleResults
record, allowing multiple zero-row rules to survive independently; old shapes cannot encode that
collection and are not silently relabelled. A zero-row rule may raise envelope severity but never
changes another object's verdict. Merely having no resolvable object refs is not empty population.

---

## 5. Legacy Boolean Compatibility (D-03/D-04)

`canonicalStatus` is a **new, additive, parallel field**. The existing legacy boolean outcome
surfaces are retained unchanged and keep being written exactly as before:

- `RuleEvaluationResult.Passed` (C#, `DG.Core.Validation`)
- `Run.ValidStatus` (Neo4j, per-ObjState Boolean list, `spec/DATABASE.md:112`)
- `conforms` (dg-reasoner SHACL envelope, `reasoning.py`)

All three are **non-authoritative**. No downstream gate may read a legacy boolean as the
authoritative verdict once a canonical status is available for the same evaluation.

**The mapping is one-directional: canonical → boolean, lossy, and defined:**

| Canonical status | Legacy boolean |
|---|---|
| `passed` | `true` |
| `failed` | `false` |
| `unknown` | `false` |
| `not_evaluated` | `false` |
| `no_population` | `false` |
| `unsupported` | `false` |
| `indeterminate` | `false` |
| `error` | `false` |

**The reverse direction is undefined and forbidden.** No code may infer a canonical status from a
legacy boolean — a legacy `false` is compatible with seven of the eight canonical statuses, and
guessing which one collapses exactly the distinction this contract exists to preserve.

### 5.1 Canonical per-object verdict source (Phase 1202 plan 05, D-10, ALGN12-10)

The envelope's per-`(rule, object)` **`rows`** (§3/§4 above) are the **canonical per-object verdict
source**. `Run.ValidStatus` and `:ValidationEntity` (`spec/DATABASE.md` §`:Run`) are **demoted to
legacy and non-authoritative** — retained for backward compatibility (additive-not-breaking), but
no downstream gate or consumer may treat either as the authoritative per-object outcome once an
envelope is available for the same run.

When the envelope is **absent** for a run (every pre-1200 run), every object on that run reports
`not_evaluated` with **no inference** from any legacy boolean — the same one-directional
canonical→boolean-only rule §5 states above applies here without exception. See `spec/DATABASE.md`
§`:Run` (Phase 1202 plan 05) for where this is stored (`evidenceEnvelopeJson`, sibling to
`statePayloadJson`/`shaclReportJson`) and for the full declared-exclusion statement for legacy runs.

**Duplicate `(ruleId, objectId)` row detection (Phase 1202 plan 10, CR-01 gap closure).** The
canonical C# per-object read path (`IValidGraphRepository.GetPerObjectVerdictsAsync` →
`Neo4jValidGraphRepository.BuildPerObjectVerdicts`) rolls a single object's rows from **distinct**
rules up through the shipped worst-case-first precedence (§4 above, D-12) — this is the intended
cross-rule behavior and is unchanged by this plan.

When two or more rows share ONE `(ruleId, objectId)` pair, that is a producer-side violation of
§4's identity rule above, and the reader **detects and reports** it on its result rather than
merging it away: `PerObjectVerdict.HasDuplicateRuleObjectRows` flags the affected object, and
`PerObjectVerdictResult.CollidingRuleObjectPairs` names every colliding pair.

A reported collision does **not** mean the envelope is absent or malformed: the verdict list is
complete and the rolled-up status still includes every duplicate row via the same `StatusRollup`
call. Absence keeps its D-11 meaning exclusively — a duplicate-pair envelope is well-formed and is
flagged, not degraded, and never thrown.

The Python leg holds the matching posture: `tools/de01/report.py`'s `compare_legs` retains all
rows per pair (`_rows_by_pair`), so both legs now decline to deduplicate on this identity boundary
— this is what closes the asymmetry `1202-REVIEW.md` CR-01 identified, and closes
`1202-VERIFICATION.md` gap 1.

### 5.2 Declared non-alignment: `parameters[]` wire shapes (Phase 1202 plan 09, D-09, ALGN12-09)

The v2 `statePayloadJson` payload's `parameters[]` member has two shipping wire shapes with two
readers, each authoritative for its own producer. This is a **declared** non-alignment under
ALGN12-09's "or an explicit exclusion contract" wording — this phase's governing rule that a
declared disagreement is acceptable while a silent one is not, which is precisely why it is written
here. See `spec/DATABASE.md`'s "Declared exclusion: `parameters[]` has two wire shapes and two
readers" subsection (`:Run` section) for the full contract: both shapes named, which reader is
authoritative for which producer, the asymmetric failure modes, and the pinning regression Facts.

---

## 6. Canonical JSON and Hashing (D-07)

Hashes recorded in an evidence envelope (`inputHash`, `outputHash`) must be computed over a
**canonical form** of the hashed content, not raw serialized bytes, so that Python, C#, and
dg-reasoner (which serializes plain Python dicts from RDF query results) produce identical hashes
for identical logical content.

### Scalar-tuple hashing

For hash inputs that are a fixed, ordered list of scalar strings (for example, minting a `dgId` or
a Design-State id), hash the **pipe-joined UTF-8 string** with SHA-256 and render the digest as
**uppercase hex**. This is the shipped precedent in `data-service/dg_identity.py`'s `compute_dg_id`
and `DG.Core.Models.Identity.DgIdMintingService` (`spec/DG-ID.md` §Format & Minting): e.g.
`dgId = "dg:" + UPPER(HEX(SHA-256(UTF-8(project | definitionId | cgId))))[0..16]`. No canonical-JSON
step is needed for this class of hash — the ordered pipe-join already is the canonical form.

### Nested-payload canonicalization

For a hash input that is a nested JSON payload (arrays, objects, not a flat scalar tuple — for
example a `warnings` array or an embedded Design State snapshot), the following six rules apply,
in order, and are versioned by `canonicalizationVersion`:

1. **Key ordering.** Object keys are sorted ascending by Unicode code point (ordinal). Python's
   `json.dumps(obj, sort_keys=True)` does this correctly for `str` keys. C#'s `JsonSerializer`
   does **not** sort keys by default — an explicit helper must re-order
   `System.Text.Json.Nodes.JsonObject` properties via
   `.OrderBy(p => p.Key, StringComparer.Ordinal)` before writing.
2. **Number formatting.** Integers are rendered with no decimal point and no leading zeros.
   Non-integers are rendered as fixed-point decimal strings via `decimal` (C#) / `Decimal`
   (Python) — never via `double`/`float` — because IEEE-754 "shortest round-trip" formatting
   diverges between .NET and Python. This mirrors `RuleEvaluator.cs`'s existing `TryToDecimal`
   convention, which already routes all numeric rule evaluation through C# `decimal`. A
   decimal's **stored scale is preserved exactly**: trailing zeros in the fractional part are
   part of the canonical rendering and are never trimmed (`100.00` stays `100.00`, `2.50` stays
   `2.50`), and a value with scale zero renders with no decimal point at all. The two reference
   renderings are Python's `format(Decimal, "f")` and C#'s
   `ToString("F" + scale, CultureInfo.InvariantCulture)` with `scale` taken from
   `decimal.GetBits(value)`. An optional-digit format specifier (e.g. `"0.#####"`) and an
   integral-value fast-path cast (e.g. casting to `long` when the value is mathematically whole)
   are both **non-conforming** on the C# side, because both discard the stored scale — this was
   CR-01, a defect in which the C# leg's canonical rendering silently dropped trailing zeros and
   diverged from the Python leg for the same logical decimal value. This is a **clarification of
   this rule's existing intent, not a change to it**: Python has preserved scale since this
   contract was written, and this rule's stated purpose is byte-parity between legs — therefore
   `canonicalizationVersion` remains **1**, and no already-recorded hash is invalidated by this
   clarification.
3. **Whitespace.** No insignificant whitespace. The canonical form uses the minimal separators:
   Python `json.dumps(..., separators=(",", ":"))`; C# `JsonSerializerOptions { WriteIndented =
   false }` (the .NET default).
4. **Unicode form.** All string values are normalized to **Unicode NFC** before hashing
   (`unicodedata.normalize("NFC", s)` in Python; `s.Normalize(NormalizationForm.FormC)` in C#).
   Architect-authored natural-language text (rule descriptions, display names) may arrive in
   either NFC or NFD depending on client OS/input method.
5. **Escaping.** Escape only the JSON-mandatory characters — `"`, `\`, and control characters
   below `0x20`. Non-ASCII characters are **not** escaped (`ensure_ascii=False` in Python;
   C#'s `JavaScriptEncoder.UnsafeRelaxedJsonEscaping` must be set explicitly to match the Python
   default, since `System.Text.Json`'s default escaping is broader). This is a deliberate, tested
   choice for this internal evidence JSON, not an oversight — it is never rendered into HTML.
6. **NaN and Infinity are forbidden.** A producer whose computation would otherwise emit `NaN` or
   `Infinity` in a canonically-hashed field must instead emit the `indeterminate` or `error`
   canonical status for that result — a non-finite number never appears in canonical form.

Changing any of these six rules requires bumping `canonicalizationVersion`, because a recorded
hash in already-committed evidence becomes meaningless if the rules that produced it change
silently underneath it.

---

## 7. Golden Fixture and Freeze Policy (D-09/D-10/D-11)

`fixtures/golden/` is the **single source of truth** for the one frozen cross-service fixture (one
rule, all four atom types, two objects with mixed outcomes, a Design State, a geometry reference).
All four DE-01 legs read the **same bytes** from this location. **Per-service copies of the
fixture are forbidden** — the existing per-service fixtures (`dg-reasoner/tests/fixtures/`,
`DG/tests/DG.Tests/Fixtures/`, ad-hoc files under `test/`) are not migrated by this phase and must
not be duplicated further for DE-01 purposes.

The fixture is **file-based** as its source of truth. Legs that require live Neo4j persistence
consume it via a **documented, scripted seed path** (following the precedent of
`test/seed_designstates.cypher` / `test/seed_validation_run.cypher`) rather than a second
independently-authored fixture.

**The fixture is frozen once committed.** A content change requires a version bump recorded in
`fixtures/golden/MANIFEST.md` together with the reason for the change. Phases 1201–1205 verify
their own work against this fixture; they **do not edit it** to make their own gates pass.

---

## 8. DE-01 Acceptance (D-12/D-13/D-14)

DE-01 is the standalone runner that drives the golden fixture through all four legs — Python
data-service, dg-reasoner, the C# evaluator, and the persisted-replay path — and emits a structured
comparison report (JSON plus a human-readable summary) as its evidence artifact, wrapped by a thin
CI-invocable test for cheap re-runs.

**Acceptance rule:** identical canonical statuses across legs for supported cases; **explicitly
typed non-equivalence** for unsupported cases. **A silent disagreement is a failure. A declared one
is not.** Any place the runner could quietly drop, coerce, or normalize away a difference between
legs is itself a defect in the runner, independent of what the legs report.

**Version metadata:** `tools/de01/report.py` report-level `contractVersion` remains `1.0.0`, the
legacy harness baseline, not a declaration that every embedded leg emitted that token. Each leg
retains its own exact `1`, `1.0.0` or `2.0.0` token after full root-schema admission. Partial
historical read inputs are not admissible DE-01 leg output. Report schema, frozen fixture verdicts,
canonicalizationVersion=1 and typed disagreement rules are unchanged; mixed-version tests do not
constitute a new live four-leg run or global relabelling of history.

**Per-leg graceful degradation (D-13).** When a leg is unavailable (dg-reasoner down, Neo4j
unreachable from the host), that leg records a typed `error` or `unsupported` outcome in the
report. The runner neither hard-crashes nor silently drops the unavailable leg from the
comparison — its absence is itself evidence, recorded as a typed outcome like any other.

---

## 9. Enforcement

Mechanical enforcement includes:

**(a)** JSON Schema validation of every leg's output against `spec/evidence-contract.schema.json`
(`jsonschema.Draft202012Validator` / equivalent), and

**(b)** the DE-01 runner's cross-leg comparison (§8), and

**(c)** strict versioned Python/C# admission and offline source-linked production-wire regression
tests (Phase 1205.1). A passing HTTP response alone is not persistence evidence: tests require the
actual persist-function capture, readback equality and same-byte C# input checksum.

There is **no linter and no CI pipeline** in this repository that enforces this contract
automatically on every commit. This is a known, accepted gap — the same honest posture
`spec/RULE-PARTITION-POLICY.md` § Enforcement takes for its own domain. Enforcement today is
documentation and review discipline: a reviewer adding a new status-producing code path, a new
envelope-shaped payload, or a new hashed field consults this document and the schema annex before
merging.

---

## 10. v11.0 Phase 1105 Handoff (D-15)

**Phase 1200 owns the evidence envelope and status vocabulary *definition*.** **v11.0 Phase 1105
owns *propagation*** of that definition across the full `CLAUDE.md` § Schema Change Propagation
file list. This split exists so the two efforts do not duplicate or drift from each other —
"coordinate, do not duplicate" (per the v12.0 milestone CONTEXT `<deferred>` section).

**What Phase 1200 propagated itself (D-16 — bounded to what 1200's own additive changes require):**

- `spec/DATABASE.md` — added the `evidenceEnvelopeJson` sidecar property on `:Run`, beside
  `statePayloadJson` and `shaclReportJson`.
- `CLAUDE.md` § Schema Change Propagation — added a cross-reference to this document, in the same
  shape as the existing `spec/RULE-PARTITION-POLICY.md` line.

**What remains for v11.0 Phase 1105** — propagating the canonical status vocabulary and envelope
shape across the rest of the `CLAUDE.md` § Schema Change Propagation list, none of which Phase 1200
touches:

- `cypher_template.txt`
- `training/dataset_schema.json`
- the n8n workflow prompts (`n8n/workflows/rules-to-metagraph.json`,
  `n8n/workflows/graph-query-mcp.json`)
- `ui-v2` config (`config.template.js`)
- `.github/copilot-instructions.md`
- `README.md`
- `ontology/dg-shapes.ttl`
- `llm/structure_rules.json`

Phase 1105 should treat this document, not a separate note, as the source of truth for what to
propagate — a standalone handoff document would itself drift from the contract it describes.

---

## 11. Consistency & Propagation

This contract is coupled to `spec/DATABASE.md` (the `:Run` node's `evidenceEnvelopeJson`
sidecar), `spec/evidence-contract.schema.json` (the machine-readable shape annex),
`spec/DG-ID.md` (the `dgId` format referenced by the envelope's identity fields), and
`spec/SWRL-SUBSET.md` (which SWRL constructs map to which status in this vocabulary — Phase 1201).
Any change to the
status vocabulary, the envelope field table, or the canonicalization rules in this document should
trigger a review of whether `spec/evidence-contract.schema.json` needs a matching update (and vice
versa — per D-01, a shape/prose conflict is resolved schema-wins-for-shape,
prose-wins-for-semantics, but the two must not simply diverge unnoticed).

See `CLAUDE.md`'s § Schema Change Propagation checklist, which now references this document
directly. A schema change that adds or reshapes evidence fields, adds a ninth canonical status, or
changes the canonicalization rules should also trigger a review of whether v11.0 Phase 1105's
propagation list ([§10](#10-v110-phase-1105-handoff-d-15)) needs a new entry.
