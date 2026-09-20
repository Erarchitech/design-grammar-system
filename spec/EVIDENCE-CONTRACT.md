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

`EVIDENCE_CONTRACT_VERSION = "1.0.0"` — the version of this prose contract and its field table.
`CANONICALIZATION_VERSION = 1` — the version of the canonical-JSON normalization rules in
[§6](#6-canonical-json-and-hashing-d-07). Both are carried in every evidence envelope
(`contractVersion`, `canonicalizationVersion`) so a consumer can tell which rules produced a given
hash or status without re-deriving it from context.

**This phase defines and proves the contract. It does not migrate the codebase onto it.** Legacy
boolean outcome surfaces (`Passed`, `Run.ValidStatus`, `conforms`) are retained unchanged and keep
being written by every existing code path; adopting the canonical status across those producers is
the business of Phase 1201–1205 (see [§10](#10-v110-phase-1105-handoff-d-15)).

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

This section names, with file and line, the places in the current codebase where distinct
statuses above collapse into a single boolean today. **This phase does not fix these** — it makes
the distinction expressible. Fixing them is Phase 1201's **ALGN12-06**.

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
`spec/evidence-contract.schema.json` `$defs.EvidenceEnvelope`; the table below is this document's
semantic description of that same shape (schema is authoritative for exact types/required-ness
per D-01).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `contractVersion` | string | yes | The `EVIDENCE_CONTRACT_VERSION` this envelope was produced against |
| `canonicalizationVersion` | integer | yes | The `CANONICALIZATION_VERSION` (§6) used to compute any hashes in this envelope |
| `project` | string | yes | The project scope this evidence belongs to (matches the repo-wide `project` node property convention) |
| `definitionId` | string | yes | The Computgraph/design definition this evidence was produced for |
| `serviceName` | string | yes | The producing service (e.g. `dg-grasshopper-evaluator`, `data-service`, `dg-reasoner`) |
| `serviceVersion` | string | yes | The producing service's version identifier |
| `emittedAt` | string (RFC 3339 UTC, `Z` suffix) | yes | When this envelope was produced |
| `stage` | string | yes | The pipeline stage boundary this envelope was emitted at (§ D-06 — every stage that produces or transforms a verdict emits one, not only final persistence) |
| `canonicalStatus` | `CanonicalStatus` | yes | The envelope-level roll-up status (e.g. worst-case across `rows`) |
| `rows` | array of `EvidenceRow` | yes | The per-(rule, object) result rows (§4) |
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

**D-06 — emission point.** The envelope is emitted at **every stage boundary** where a verdict is
produced or transformed, not only at final persistence. A stage that reads an upstream verdict and
re-emits a transformed one (e.g. a replay leg re-deriving status from a persisted payload) emits
its own envelope. This is what makes a mid-pipeline divergence localizable in DE-01 (§8) rather
than only visible as an unexplained terminal mismatch.

---

## 4. Ordering and Identity of Evidence Rows

`rows` is ordered **lexicographically ascending by `objectId`, ties broken lexicographically by
`ruleId`**. This ordering is normative, not incidental: it is what keeps an envelope's `rows`
comparable, position-by-position, against the legacy `Run.ValidStatus` index-matched Boolean list
(`spec/DATABASE.md:112`) across different legs and different runs.

Evidence rows are addressed by the **`(ruleId, objectId)` pair** as their identity, not by value.
Two fixture atoms or objects that are value-equal but are distinct entities (distinct identity)
remain **separately addressable** in evidence and are **never merged, collided, or deduplicated**
on value equality alone. Only an exact `(ruleId, objectId)` match refers to the same row.

An **empty population** (zero bindings for a rule) produces no per-object rows for that rule and
the rule's own status is `no_population` — this is never represented as a `failed` row and is
never silently omitted from the envelope; the rule still appears with its `no_population` status
even though it contributes zero `EvidenceRow` entries.

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

**Per-leg graceful degradation (D-13).** When a leg is unavailable (dg-reasoner down, Neo4j
unreachable from the host), that leg records a typed `error` or `unsupported` outcome in the
report. The runner neither hard-crashes nor silently drops the unavailable leg from the
comparison — its absence is itself evidence, recorded as a typed outcome like any other.

---

## 9. Enforcement

The only mechanical enforcement this contract has is:

**(a)** JSON Schema validation of every leg's output against `spec/evidence-contract.schema.json`
(`jsonschema.Draft202012Validator` / equivalent), and

**(b)** the DE-01 runner's cross-leg comparison (§8).

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
