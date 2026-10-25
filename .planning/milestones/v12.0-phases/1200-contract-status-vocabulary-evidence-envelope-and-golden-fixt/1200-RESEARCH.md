# Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture - Research

**Researched:** 2026-09-20
**Domain:** Cross-service (Python/C#/RDF) evidence-contract design; canonical JSON hashing; JSON Schema tooling; cross-service test-fixture sharing
**Confidence:** HIGH for verified-evidence sections (line citations, dependency inventories, Docker build contexts); MEDIUM for canonical-JSON library recommendation (no repo precedent, cross-ecosystem judgment call); LOW/ASSUMED flagged inline where training knowledge substitutes for verification

## Summary

CONTEXT.md's 16 decisions (D-01..D-16) are complete and evidence-backed; this research does not
re-derive them. It verifies the cited defect evidence is still accurate in the working tree
(it is, with only line-number drift of a few lines — never a changed conclusion), and resolves
the eleven implementation unknowns the decisions leave open: canonical-JSON hashing across
Python/C#, JSON Schema dialect and tooling, the golden-fixture directory's Docker build-context
reachability, the real shape of the four SWRL atom types (only three exist in the C# parser
today), the DE-01 runner's invocation model given zero CI infrastructure, the exhaustive list of
`Run.ValidStatus` readers, and the Nyquist validation architecture for a phase with no existing
test-framework precedent for what it produces.

The single highest-value finding: **the repo already has a working, shipped precedent for
cross-language deterministic hashing** — `data-service/dg_identity.py:52` (`compute_dg_id`)
mirrors `DG.Core.Models.Identity.DgIdMintingService.Mint` byte-for-byte by hashing a **pipe-joined
string of scalar fields** (`f"{project}|{definition_id}|{cg_id}"`), not canonical JSON of an
object graph. This is a materially simpler and already-proven pattern than adopting RFC 8785 (JSON
Canonicalization Scheme) from scratch, and D-07's hashing rule should follow it wherever the
hashed content is a bounded, ordered set of scalar fields. Full canonical JSON is still needed
for the sections of the envelope that are open-ended nested payloads (e.g. a Design State graph
or a SHACL result set) — for those, this research recommends a explicit, versioned normalization
spec (documented below) rather than pulling in an unverified third-party package for either leg,
because no `[VERIFIED]` npm/PyPI/NuGet package for RFC 8785 was found that is actively maintained
enough to trust for a "byte-identical forever" contract; hand-rolling ~40 lines per leg against a
written spec is lower-risk than adopting a small, rarely-updated dependency for this one purpose.

The second highest-value finding: **the golden fixture's shared-directory design (D-09) has a
real Docker build-context hazard.** `data-service`'s Dockerfile does `COPY . .` from `./data-service`
as build context, but the running container also bind-mounts the **entire repo** read-only at
`/mnt/repo` (`docker-compose.yml`: `.:/mnt/repo:ro`, `DG_KNOWLEDGE_REPO_ROOT=/mnt/repo`) — an
established, already-used escape hatch (`dg_knowledge.py`, `dg_context.py`,
`cg_structure_checks.py` all resolve real repo-relative paths through it today). **dg-reasoner has
no equivalent mount** — only `./ontology:/app/ontology:ro`. A top-level `fixtures/golden/`
directory is reachable by data-service today with zero Dockerfile change, but dg-reasoner needs
one new `docker-compose.yml` volume line (`./fixtures:/app/fixtures:ro` or reuse the `/mnt/repo`
pattern) before DE-01 can exercise dg-reasoner against the shared fixture from inside its
container.

The third finding materially affects fixture design: **the C# rule parser implements only three
of the four schema-level SWRL atom types today.** `SwrlRuleParser.cs:82-92`'s `ResolveAtomType`
returns `BuiltinAtom`, `ClassAtom`, or `DataPropertyAtom` — there is no `ObjectPropertyAtom`
branch. The milestone CONTEXT and ROADMAP both name "adding the `ObjectPropertyAtom` branch" as
Phase **1201**'s deliverable (ALGN12-05), not 1200's. This means Phase 1200's golden fixture
must contain an atom of `type: "ObjectPropertyAtom"` at the **data level** (Metagraph node
property, per `training/dataset_schema.json`'s Atom node contract, which is schema-agnostic
about which types exist) so that 1201 has something to parse against, but the fixture cannot
assume the C# leg of DE-01 will produce anything but a typed non-result (`unsupported` or
`error`) for that atom in 1200's own DE-01 run — which is exactly what D-13 (graceful
degradation) and D-05's `unsupported` status exist to make representable, not a runner bug.

**Primary recommendation:** adopt scalar pipe-joined hashing (dgId precedent) for envelope fields
that are themselves scalar/short tuples; write one explicit canonical-JSON normalization spec
(ASCII-only escaping, NFC, sorted keys by ordinal/UTF-16 code unit, no insignificant whitespace,
integers without decimal points, decimals rendered via `decimal.ToString("G", InvariantCulture)`
on the .NET side and Python's `Decimal` `str()` with a matching fixed-point convention — detailed
below) for the envelope's structured payload hash, implemented by hand in both legs (~30-50 LOC
each) rather than adopting an unverified third-party package; mount `fixtures/golden/` into
dg-reasoner via a new compose volume line; and design the fixture's `ObjectPropertyAtom` as a
data-only atom that 1200's own DE-01 run is expected to report as `unsupported` on the C# leg,
by design, not as a fixture defect.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Canonical status vocabulary definition | Contract/spec (no runtime tier) | — | A prose+schema document (`spec/EVIDENCE-CONTRACT.md`); consumed by all four runtime legs but owned by none |
| Evidence envelope shape | Contract/spec | — | Same as above; the JSON Schema annex is the shape authority per D-01 |
| Rule evaluation (SWRL) | API/Backend — C# `DG.Core.Validation` (in-process, invoked by Grasshopper) | — | `RuleEvaluator` runs inside the Grasshopper plugin process, not a hosted API, but functionally the "evaluator" tier |
| Structural/SHACL validation | API/Backend — `dg-reasoner` sidecar (FastAPI) | Database/Storage (Neo4j read) | `dg-reasoner` reads Neo4j via `ontology_export.build_graph`, runs pySHACL in-process, returns HTTP JSON |
| Rule-mapped structure checks | API/Backend — `data-service/cg_structure_checks.py` | Database/Storage (Cypher) | Pure Cypher pattern-matches over Computgraph, no LLM, no RDF |
| Persisted validation replay | Database/Storage — Neo4j `:Run`/`:ValidationEntity` nodes | API/Backend (`data-service` read routes, C# `Neo4jValidGraphRepository`) | The "fourth leg" of DE-01 is a stored-then-read round trip, not a live service call |
| DE-01 runner itself | New: standalone script/harness (language TBD by planner; not a hosted service) | Test tier (pytest/xunit wrapper) | D-12 locks "standalone runner + thin CI-invocable wrapper"; it orchestrates calls into the four tiers above, it does not own business logic |
| Golden fixture storage | File-based (repo top level) | Database/Storage (scripted Neo4j seed for persistence leg) | D-09/D-10: file is source of truth; Neo4j seed is a documented projection, not a second source of truth |
| Canonical-JSON hashing implementation | Duplicated in each producing tier (C#, Python data-service, Python dg-reasoner) | — | No shared runtime between C#/.NET and Python exists in this stack; the hash algorithm must be reimplemented per language against one written spec, mirroring the existing `dg_identity.py` / `DgIdMintingService` precedent |

## Standard Stack

### Core

No new runtime framework is introduced by this phase — it is a contract/spec/fixture/harness
phase layered on the existing stack. The "stack" here is tooling for schema validation and
canonical hashing.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jsonschema` (Python) | 4.26.0 confirmed installed in this environment `[VERIFIED: pip show]`; **not yet in `data-service/requirements.txt` or `dg-reasoner/requirements.txt`** `[VERIFIED: grep of both requirements.txt files]` | Validate data-service and dg-reasoner envelope JSON against the JSON Schema annex | De facto standard Python JSON Schema validator; actively maintained, python-jsonschema org |
| `System.Text.Json` (C#) | Already in use, part of .NET 9 BCL `[VERIFIED: grep — DG.Core uses System.Text.Json exclusively, zero Newtonsoft references found]` | Serialize/deserialize the envelope DTO in C# | Already the sole JSON library in `DG.Core` (`CanvasBridgeProtocol.cs`, `Neo4jValidGraphRepository.cs`, `ComputgraphContextSerializer.cs`, `DesignStateJsonSerializer.cs`) — introducing Newtonsoft or a third JSON schema validator for one phase would be a new dependency for no proven benefit |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `hashlib` (Python stdlib) | stdlib, no version | SHA-256 hashing of canonical strings | Already the exclusive hashing library across `app.py`, `cg_input_generation.py`, `cg_paramstate_store.py`, `connectors.py`, `dg_identity.py` `[VERIFIED: grep]` |
| `System.Security.Cryptography.SHA256` (C#) | .NET BCL | SHA-256 hashing of canonical strings | Already used in `DesignStateIdGenerator.cs:110` (`SHA256.HashData`) — same pattern to reuse for envelope hashes |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled canonical-JSON normalization spec | `rfc8785` (PyPI 0.1.4) `[ASSUMED — package existence checked via `pip index versions`, but not verified against official docs/Context7; provenance and maintenance activity unconfirmed]` | PyPI package exists and matches the exact spec name, but there is **no equivalent .NET-side JCS/RFC-8785 package verified in this session** — adopting it only for the Python legs would still leave the C# leg needing a hand-rolled implementation, defeating the purpose of a single canonicalization law; also a young/low-signal package for a "byte-identical forever" contract is a risk this phase's own philosophy (`failed` must become expensive to say / no manufactured false non-equivalence) argues against |
| Hand-rolled canonical-JSON normalization spec | `canonicaljson` (PyPI 2.0.0, Matrix.org-maintained) `[ASSUMED — not verified against official docs/Context7]` | More mature and widely used (Matrix protocol reference implementation) than `rfc8785`, but implements the **Matrix/JCS variant with its own number-formatting rules**, not necessarily bit-identical to what a hand-rolled .NET implementation would produce without careful joint testing; still leaves the C#-side gap |
| Draft 2020-12 JSON Schema | Draft-07 | Draft-07 has broader legacy tool support but `jsonschema` 4.26.0 (already installed) fully supports 2020-12; no compatibility reason found to use the older draft in a phase starting from zero JSON Schema usage in this repo |

**Installation:**
```bash
# data-service/requirements.txt — add:
jsonschema>=4.20,<5

# dg-reasoner/requirements.txt — add (only if dg-reasoner's leg of DE-01 validates its own
# {conforms, results, counts} envelope against the schema in-process; otherwise the DE-01
# runner alone needs it and this is skippable for dg-reasoner):
jsonschema>=4.20,<5
```

**Version verification:** `pip show jsonschema` in this session returned `4.26.0` (installed in
the ambient Python 3.13 environment, not yet a pinned dependency of either service)
`[VERIFIED: pip show jsonschema, this session]`. `canonicaljson` PyPI latest is `2.0.0`
`[VERIFIED: pip index versions canonicaljson]`. `rfc8785` PyPI latest is `0.1.4`
`[VERIFIED: pip index versions rfc8785]`. Neither canonical-JSON package's C#/.NET equivalent was
found in this session — no NuGet lookup tool was available in this shell (`nuget` CLI absent);
this is a gap the planner should either accept (hand-roll only) or have a task verify via
`dotnet add package <name> --version <x> --dry-run` before deciding.

## Package Legitimacy Audit

No package is being newly *installed* by 1200's own required deliverables — `jsonschema` is
already present in the ambient environment and is a long-standing, extremely widely used Python
package (the project would need to add it to `requirements.txt` to pin it, which is a
configuration change, not a new supply-chain risk). No `[SLOP]` or `[SUS]` packages are proposed.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `jsonschema` | PyPI | Long-established (originally released ~2013) `[ASSUMED — age from training knowledge, not re-verified this session]` | Extremely high (tens of millions/week, project used by pip itself as a transitive dependency) `[ASSUMED]` | github.com/python-jsonschema/jsonschema `[VERIFIED: pip show — Home-page field]` | OK | Approved — pin in `data-service/requirements.txt` |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none. If the planner chooses to adopt `rfc8785` or
`canonicaljson` instead of hand-rolling, both should go through the full Package Legitimacy Gate
(`gsd-tools query package-legitimacy check`) before being pinned, and are tagged `[ASSUMED]` in
this document pending that check — they were discovered via `pip index versions`, not an
authoritative source.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────┐
                         │   fixtures/golden/ (file-based,  │
                         │   single source of truth, D-09)  │
                         └───────────────┬───────────────────┘
                                         │ read (all 4 legs, same bytes)
              ┌──────────────────────────┼──────────────────────────┬─────────────────────┐
              ▼                          ▼                          ▼                     ▼
     ┌──────────────────┐     ┌────────────────────┐      ┌──────────────────┐   ┌──────────────────────┐
     │ C# RuleEvaluator  │     │ data-service        │      │ dg-reasoner       │   │ Neo4j (seeded via     │
     │ (DG.Core, in-     │     │ cg_structure_checks │      │ (SHACL/OWL,       │   │ scripted seed path,   │
     │ process; no HTTP) │     │ + validation publish │      │ FastAPI, port     │   │ D-10) → persisted      │
     │ emits: Passed bool│     │ routes (FastAPI,      │      │ 8000 internal)    │   │ `:Run.ValidStatus`     │
     │ + (post-1200) a   │     │ port 8000)            │      │ emits: {conforms, │   │ read back via          │
     │ typed envelope    │     │ emits: mixed bool/str │      │ results, counts}  │   │ data-service /         │
     └─────────┬─────────┘     │ status fields today   │      └─────────┬──────────┘   │ C# repository          │
               │               └───────────┬───────────┘                │              └───────────┬────────────┘
               │                           │                            │                          │
               │ each emits an evidence envelope (D-06: at EVERY stage boundary, not just terminal) │
               ▼                           ▼                            ▼                          ▼
     ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
     │                             DE-01 runner (new, standalone; D-12)                                   │
     │  - drives the fixture through all 4 legs                                                            │
     │  - collects each leg's envelope (rule ID, object ID, canonical status, hashes, service+version)     │
     │  - compares canonical statuses per (rule, object) pair                                              │
     │  - per-leg graceful degradation on failure (D-13): typed error/unsupported, never a hard crash       │
     │  - emits: structured JSON report + human-readable Markdown (discretion item)                        │
     └──────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                          │
                                                          ▼
                                        Acceptance (D-14): identical canonical status per
                                        supported (rule, object) pair across legs; explicit
                                        typed non-equivalence for unsupported cases;
                                        SILENT disagreement = failure.
```

### Recommended Project Structure

```
spec/
├── EVIDENCE-CONTRACT.md          # D-01: normative prose (status semantics, envelope fields,
│                                  #   canonical-JSON hashing rule, v11.0 1105 handoff section D-15)
├── evidence-contract.schema.json # D-01: machine-readable JSON Schema annex (draft 2020-12)
│                                  #   — recommend ONE file with $defs for {Status, Envelope},
│                                  #   not three separate files, since D-01 already keeps
│                                  #   prose+schema as a two-artifact pair; a third split
│                                  #   (schema-of-schemas) adds propagation surface for no
│                                  #   proven benefit at this size (~2 top-level shapes)

fixtures/
└── golden/                       # D-09: single top-level fixture dir, all 4 legs read same bytes
    ├── fixture.json               # the frozen cross-service fixture (rule + 4 atom types +
    │                               #   2 objects mixed outcome + Design State + geometry ref)
    ├── seed.cypher                 # D-10: scripted Neo4j seed path (precedent: test/seed_*.cypher)
    └── MANIFEST.md                  # D-11: version + freeze date + reason-for-change log

tools/de01/ (or scripts/de01/ — planner's call)
├── run_de01.py (or .cs)          # D-12: standalone runner
├── report_schema.json             # shape of the DE-01 comparison report (reuses envelope schema)
└── README.md                      # invocation instructions, per-leg availability preconditions
```

### Pattern 1: Additive sidecar-JSON envelope (D-08)

**What:** Persist the evidence envelope as a new JSON string property on the existing `:Run`
node, sibling to `statePayloadJson` and `shaclReportJson`, rather than new node labels.
**When to use:** Any time a new structured artifact needs to travel with a `:Run` without
triggering the full schema-propagation list.
**Example:**
```cypher
// Source: spec/DATABASE.md:108,114-115 (existing sidecar pattern, D-08 reuses directly)
MERGE (run:Run {Run_Id: $runId, graph: 'ValidGraph', project: $project})
SET run.evidenceEnvelopeJson = $envelopeJson   // new sidecar property, absence = "not recorded"
```

### Pattern 2: Cross-language deterministic hash from scalar fields (existing precedent, extend for D-07)

**What:** For envelope fields that are a small, fixed, ordered tuple of scalars (e.g.
`project|definition|dgId|contractVersion`), hash the pipe-joined string directly — no JSON
canonicalization needed because there is no nested structure or key-ordering ambiguity.
**When to use:** Any envelope hash whose input is fully enumerable as an ordered list of scalar
strings. NOT for hashing an entire nested payload (e.g. full Design State JSON) — see the
canonical-JSON section below for that case.
**Example:**
```python
# Source: data-service/dg_identity.py:52-63 (existing shipped precedent, verified this session)
def compute_dg_id(project: str, definition_id: str, cg_id: str) -> str:
    input_str = f"{project}|{definition_id}|{cg_id}"
    digest = hashlib.sha256(input_str.encode("utf-8")).hexdigest().upper()
    return DGID_PREFIX + digest[:16]
```
```csharp
// Source: DG.Core.Models.Identity.DgIdMintingService.Mint (mirrored by the Python function above,
// per data-service/dg_identity.py:17 docstring — exact file path not independently re-read this
// session; the Python docstring is the verification anchor for parity intent)
// Convert.ToHexString produces UPPERCASE hex; Python uppercases to match.
```

### Anti-Patterns to Avoid

- **Raw-byte hashing of serialized JSON (D-07's explicit rejection):** Python `json.dumps`,
  C# `JsonSerializer.Serialize`, and dg-reasoner's RDF-derived dict-to-JSON path will not produce
  byte-identical output for logically identical content (key order, float formatting, whitespace
  all differ by default). Hashing the raw serialized bytes manufactures false non-equivalence in
  DE-01 — exactly what D-07 exists to prevent.
- **Treating `Run.ValidStatus` boolean as an input to canonical status (D-04's explicit
  prohibition):** the mapping is one-directional (canonical → boolean). No code in 1200 or later
  phases may read a legacy boolean and infer a canonical status from it — this would silently
  resurrect the exact defect D-05 fixes (three distinct statuses collapsing into one boolean).
- **Assuming `ObjectPropertyAtom` is parseable today:** the fixture may declare an atom of this
  type at the data level (Neo4j `Atom.type` property, per `training/dataset_schema.json`'s
  schema-agnostic Atom node shape), but `SwrlRuleParser.cs:82-92`'s `ResolveAtomType` cannot
  produce or consume this type yet — 1201 adds it. DE-01 in 1200 must expect and correctly type
  (not silently drop) whatever the C# leg reports for this atom.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation (Python) | A custom recursive shape-checker | `jsonschema` 4.26.0 | Already installed, de facto standard, handles `$ref`, `$defs`, format validators, and the 2020-12 draft's full vocabulary — a hand-rolled checker would under-cover edge cases (e.g. `additionalProperties: false`, `oneOf`) that matter for a contract meant to be mechanically enforced (per D-01: "DE-01 validates every leg's output against the schema mechanically rather than by reading") |
| SHA-256 hashing | Anything other than stdlib/BCL `hashlib`/`SHA256` | `hashlib.sha256` (Python) / `System.Security.Cryptography.SHA256` (C#) | Already the exclusive hashing primitive across both languages in this repo (`dg_identity.py`, `connectors.py`, `cg_input_generation.py`, `cg_paramstate_store.py`, `DesignStateIdGenerator.cs`) — no reason to introduce a second hash library for one phase |

**Key insight:** the repo has already solved "make a hash byte-identical across Python and C#"
once, for `dgId` minting, using the simplest possible technique (pipe-joined scalar string, not
canonical JSON). D-07's hazard is real but narrower than "full RFC 8785 adoption" — it only
applies to the *nested/structured* parts of the envelope (e.g. warnings arrays, a Design State
payload snapshot). Reusing the scalar-join technique wherever possible minimizes the surface
area that needs a from-scratch canonicalization spec at all.

## Canonical JSON Hashing Specification (D-07 — the phase's highest-risk unknown)

This section is the concrete, implementable normalization spec the research_focus requested.

**Scope of the problem:** the evidence envelope's scalar fields (project, definition, dgId,
service name, service version, contract version, timestamps) can be hashed via the existing
pipe-join pattern with zero ambiguity. The problem is narrower than "canonicalize the whole
envelope" — it is specifically: **how do we hash the `warnings` array (list of strings) and any
future nested structured field (e.g. an embedded Design State snapshot) identically across
Python `json`/`pydantic`, C# `System.Text.Json`, and whatever dg-reasoner emits (plain Python
dicts from RDF query results)?**

**Recommended normalization rule set** (to be written verbatim into
`spec/EVIDENCE-CONTRACT.md`'s canonicalization section, itself versioned per D-07):

1. **Key ordering:** sort object keys by Unicode code point (ordinal) ascending. Python:
   `json.dumps(obj, sort_keys=True)` already does this correctly for `str` keys. C#:
   `JsonSerializer` does NOT sort keys by default — the envelope DTO's property order must
   either be alphabetized in the class declaration (fragile) or a `JsonConverter` must
   explicitly sort keys before writing (`System.Text.Json.Nodes.JsonObject`, iterate
   `.OrderBy(p => p.Key, StringComparer.Ordinal)`, re-emit). This is the single largest
   cross-language gotcha and must be an explicit, tested C# helper (`CanonicalJsonWriter` or
   similar), not left to default serializer behavior.
2. **Number formatting:** **avoid emitting non-integer numbers in any canonically-hashed field
   at all** where possible — route numeric comparisons through the scalar pipe-join pattern
   instead. Where a nested payload unavoidably contains numbers (e.g. a captured parameter
   value inside a Design State snapshot), require: integers with no decimal point and no
   leading zeros; non-integers rendered as fixed-point decimal strings (not floats) using
   `decimal` (C#) / `Decimal` (Python) types end-to-end — never `double`/`float` — because
   IEEE-754 double formatting ("shortest round-trip" in modern .NET vs Python's `repr`) is a
   known cross-language divergence source. This mirrors the codebase's own existing convention:
   `RuleEvaluator.cs`'s `TryToDecimal` and `ParseLiteral` already route all numeric rule
   evaluation through C# `decimal`, never `double`, and Python's `cg_input_generation.py`'s
   candidate hashing pins a `[16-char upper hex]` digest of a string payload — no numeric
   formatting concerns are hashed today, and the envelope contract should preserve that
   property rather than introduce one.
3. **Whitespace:** no insignificant whitespace — the canonical form is the minimal `json.dumps`
   with `separators=(",", ":")` in Python and `JsonSerializerOptions { WriteIndented = false }`
   in C# (the .NET default).
4. **Unicode form:** normalize all string values to NFC before hashing
   (`unicodedata.normalize("NFC", s)` in Python; `s.Normalize(NormalizationForm.FormC)` in C#).
   This repo's data is architect-authored natural language (rule descriptions, display names)
   which may arrive in either NFC or NFD depending on client OS/input method — this is a real,
   not theoretical, risk for this specific dataset.
5. **String escaping:** escape only the JSON-mandatory characters (`"`, `\`, control characters
   < 0x20); do NOT escape non-ASCII characters (`ensure_ascii=False` in Python's `json.dumps`;
   C#'s default `JsonSerializer` escaping is broader by default — `Encoder =
   JavaScriptEncoder.UnsafeRelaxedJsonEscaping` must be set explicitly to match, with a
   documented note that this is a deliberate, tested choice, not an oversight, since relaxing
   escaping has its own well-known security caveats in general web contexts — acceptable here
   because this JSON is never rendered into HTML).
6. **NaN/Infinity:** forbidden in canonical form; the envelope's own status vocabulary
   (`indeterminate`, `error`) exists precisely so a non-finite numeric result never needs to be
   serialized as a number at all — a producer that would otherwise emit `NaN` must instead emit
   a typed status.

**Implementation recommendation:** hand-roll a small canonicalization helper per leg (~30-50 LOC
each) against this written spec, rather than adopting `rfc8785` or `canonicaljson` — see
Alternatives Considered above for why (no verified, jointly-tested cross-language package pair
exists, and the existing `dgId` precedent shows the repo already prefers minimal hand-rolled
determinism over dependency adoption for exactly this class of problem). Golden-vector tests
(mirroring `DgIdMintingService`'s "golden vector" test convention, per STATE.md:
`(p1|frame.gh|cg:1:proc:11_Proc) -> dg:BC8E62EE137E2B56`) should pin at least 3-5 fixed
input/output pairs shared as literal test data across the C# and Python test suites, so any
future divergence in either implementation is caught immediately by a failing assertion rather
than only by a DE-01 report mismatch.

## Golden Fixture — Four Atom Types (research_focus item 6)

**Source of truth:** `training/dataset_schema.json`'s `metagraph.nodes[].label: "Atom"` entry
(schema is type-agnostic — `Atom_Id`/`type` is a free-text property, not a constrained enum in
the ingestion schema itself). The actual enumeration of **which** types are meaningful comes from
the C# parser, `DG/src/DG.Core/Parsing/SwrlRuleParser.cs:82-92` (`ResolveAtomType`):

```csharp
// Source: DG/src/DG.Core/Parsing/SwrlRuleParser.cs:82-92 (read this session)
private static string ResolveAtomType(string predicate, int argCount)
{
    if (IsBuiltinPredicate(predicate))
        return "BuiltinAtom";
    return argCount switch
    {
        <= 1 => "ClassAtom",
        _ => "DataPropertyAtom",
    };
}
```

Only three types are producible by the parser: `BuiltinAtom`, `ClassAtom`, `DataPropertyAtom`.
**`ObjectPropertyAtom` does not exist in the C# evaluator today** — confirmed independently by
the milestone ROADMAP naming "ObjectPropertyAtom and malformed/unsupported syntax" as Phase
1201's deliverable (ALGN12-05), and by `dg-reasoner/tests/fixtures/metagraph_fixture.json`
(read this session) which itself only contains `ClassAtom`, `DataPropertyAtom`, and
`BuiltinAtom` instances — no dg-reasoner-side fixture in the repo has ever exercised
`ObjectPropertyAtom` either.

**Implication for the golden fixture:** the fixture must contain a fourth Atom node with
`type: "ObjectPropertyAtom"` at the **data level** (this satisfies ALGN12-03's literal
requirement — "all four atom types" — as a graph/fixture-content fact) but the fixture's
accompanying documentation (in `fixtures/golden/MANIFEST.md`) must record, up front, that DE-01's
C#-leg result for this atom is *expected* to be `unsupported` (or `error`, if the parser
throws rather than returns a typed non-result before 1201 lands) — this is by design per D-05's
vocabulary and is not a fixture defect to "fix" within 1200's scope.

## Common Pitfalls

### Pitfall 1: Docker build-context blindness for the golden fixture (D-09)

**What goes wrong:** a top-level `fixtures/golden/` directory is invisible inside the
`dg-reasoner` container because its Dockerfile's build context is `./dg-reasoner` and its
`COPY . .` only copies that subdirectory; there is no volume mount bringing in the rest of the
repo.
**Why it happens:** `docker-compose.yml`'s `dg-reasoner` service (lines 19-30, read this session)
only mounts `./ontology:/app/ontology:ro` — unlike `data-service`, which additionally mounts
`.:/mnt/repo:ro`.
**How to avoid:** add one line to `docker-compose.yml`'s `dg-reasoner` service:
`- ./fixtures:/app/fixtures:ro` (matching the existing `./ontology:/app/ontology:ro` pattern), or
the broader `.:/mnt/repo:ro` if dg-reasoner is expected to need other repo-root paths later.
**Warning signs:** a dg-reasoner-side DE-01 leg that raises `FileNotFoundError` or silently
returns an empty/default result when pointed at `/app/fixtures/golden/fixture.json` inside the
container, while the identical path resolves fine on the host or inside data-service.

### Pitfall 2: C#-side canonical-JSON key sorting is not automatic

**What goes wrong:** `System.Text.Json.JsonSerializer.Serialize` preserves declared property
order (or `[JsonPropertyOrder]` if set) — it does **not** sort keys alphabetically by default,
unlike Python's `json.dumps(sort_keys=True)`. A canonical-JSON hash computed naively on each
side will differ even for logically identical envelopes.
**Why it happens:** the two ecosystems' "default" JSON serialization philosophies differ —
Python's stdlib historically treats key order as significant-by-default-unless-asked, .NET's
`System.Text.Json` treats declaration order as significant by design (for readability/diffing).
**How to avoid:** write one explicit `CanonicalJsonWriter` helper in `DG.Core` that walks a
`JsonNode`/`JsonObject` tree and re-emits keys in ordinal-sorted order before hashing — never
rely on the DTO's declared property order.
**Warning signs:** DE-01 reports identical logical envelopes (same status, same warnings, same
everything visible) but different `outputHash` values across legs — this is the signature of a
canonicalization bug, not a real disagreement, and must not be misreported as D-14's "silent
disagreement."

### Pitfall 3: `unsupported` currently has no representable outcome — it is a thrown exception

**What goes wrong:** `RuleEvaluator.cs:130` throws `NotSupportedException` for an unrecognized
builtin predicate. If DE-01's C#-leg caller does not wrap this specific call in a try/catch that
maps the exception to a typed `unsupported` status in the *evidence envelope* (not just log it),
the DE-01 run for that leg will crash rather than degrade gracefully, violating D-13.
**Why it happens:** 1200 does not migrate the codebase (per its own boundary statement) — it
must therefore let this exception happen and catch it at the DE-01-runner boundary, not inside
`RuleEvaluator` itself (that fix is 1201's ALGN12-06).
**How to avoid:** the DE-01 runner's C#-leg invocation wraps the call to `RuleEvaluator` in a
try/catch that specifically distinguishes `NotSupportedException` (→ `unsupported`) from any
other exception (→ `error`), per D-05's table.
**Warning signs:** the DE-01 runner crashes entirely (not just one leg's row) when it reaches the
`ObjectPropertyAtom` or any deliberately-unsupported-builtin atom in the fixture.

### Pitfall 4: `SUPERSEDED_BY` filter (uncommitted working-tree change) is unrelated but must not be reverted

**What goes wrong:** a planner or executor sees the uncommitted diff on
`Neo4jRuleRepository.cs` (`git status`/`git diff` both confirmed this session — 9 insertions, a
`WHERE NOT EXISTS { (r)-[:SUPERSEDED_BY]->() }` filter with an explanatory comment dated
2026-09-19 from a different debug session named `rule-ingest-no-conflict-check`) and either
reverts it as "unexpected" or assumes it is part of 1200's scope.
**Why it happens:** the milestone CONTEXT's working-tree caveat flagged this file without
resolving what the change is.
**How to avoid:** this change is confirmed **unrelated to Phase 1200** — it belongs to a
different, already-referenced feature (`spec/RULE-PARTITION-POLICY.md`'s "Corpus-Level
Authoring-Time Conflict Check" section, added same day). It should be left as-is (or committed
separately by whoever owns that feature) and Phase 1200 plans should neither touch nor depend on
it. It does not affect the RuleEvaluator/ValidationPublishPackageBuilder defect evidence (D-05),
which lives in different files entirely.
**Warning signs:** a 1200 plan task that includes "revert Neo4jRuleRepository.cs" or "resolve
the uncommitted change" — this indicates scope confusion, not a real 1200 requirement.

### Pitfall 5: no CI workflow exists — DE-01's "thin CI-invocable wrapper" (D-12) has no CI to invoke it from yet

**What goes wrong:** planning a DE-01 wrapper as "a test CI runs on every push" when
`.github/workflows/` does not exist in this repo (`Glob` returned zero files this session).
**Why it happens:** the repo's test discipline today is manual (`dotnet test`,
in-container `pytest`) run by the developer or GSD execution agent, not automated CI.
**How to avoid:** D-12's "thin CI-invocable test" should be read as "a test **runnable** by a
future CI, and easy to invoke manually today" — not as evidence a CI pipeline exists to wire it
into. The planner should not create a task to "add a GitHub Actions workflow" unless the user
explicitly wants one; that is out of this phase's stated scope (DE-01 runner + wrapper, not CI
infrastructure).
**Warning signs:** a plan task referencing `.github/workflows/` as an existing file to modify.

## Code Examples

### Existing sidecar-JSON pattern (D-08 to extend)

```python
# Source: spec/DATABASE.md:108-115 (read this session) — the Run node's existing sidecar fields
# (:Run {Run_Id: "VRUN_abc123", ValidStatus: [true, false, true], SendStatus: true,
#        statePayloadJson: '{...}', shaclReportJson: '{...}', graph: "ValidGraph", project: "1"})
```

### Existing degrade-never-raise precedent (D-13's philosophical anchor)

```python
# Source: data-service/dsav_watcher.py:311-333 (derive_valid_status, read this session)
# "Never raises." Empty/unparseable input returns ([], 0) rather than throwing. This is the
# established house style D-13's per-leg graceful degradation should match: a typed empty/
# non-result, never an unhandled exception surfacing at the DE-01 runner boundary.
```

### dg-reasoner's own already-typed timeout envelope (a precedent for typed non-results)

```python
# Source: dg-reasoner/reasoning.py:511-512 (read this session)
if result.get("timeout"):
    return {"conforms": None, "error": "timeout", "timeout_seconds": DG_REASONER_TIMEOUT_SECONDS}
```
This is dg-reasoner's own pre-existing "typed non-result, not a crash" pattern — D-13's
philosophy is not new to this repo, it is being generalized from one already-shipped instance.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Three incompatible outcome dialects (bool `Passed`, mixed bool/string `passed`/`"unknown"`, `{conforms: bool\|None}`) | One canonical 8-value status vocabulary, additive alongside legacy fields | Phase 1200 (this phase, not yet executed) | Every later v12.0 phase and the v9.1/v10.0 activation gates can compare outcomes across services without dialect translation bugs |
| No shared cross-service fixture | One frozen `fixtures/golden/` fixture, file-based source of truth | Phase 1200 | 1201-1205 verify against one stable input instead of drifting per-service fixtures |
| Raw-byte or ad-hoc hashing for cross-service comparison | Canonical-JSON-normalized hashing per a written spec | Phase 1200 | DE-01 can distinguish real content divergence from serialization-format noise |

**Deprecated/outdated:**
- Boolean `Passed`/`ValidStatus`/`conforms` fields as an authority signal for pass/fail — retained
  for backward compatibility per D-03/D-04, but no new gate may read them as authoritative
  starting with this phase's downstream consumers.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rfc8785` (PyPI) and `canonicaljson` (PyPI) are legitimate, appropriately-maintained packages | Standard Stack / Alternatives Considered | Low — this research recommends NOT adopting either without a full Package Legitimacy Gate check; the assumption only affects whether the planner considers them as an option at all |
| A2 | `jsonschema`'s PyPI package age/downloads are as stated (long-established, extremely high downloads) | Package Legitimacy Audit | Very low — `jsonschema` is one of the most widely-known Python packages; a planner or executor can trivially re-verify via `pip show`/PyPI page if doubted |
| A3 | No .NET/NuGet package implementing RFC 8785 was found, because no NuGet lookup tool was available in this session's shell (the `nuget` CLI is absent) — this is a **tooling gap in this research session**, not a confirmed absence in the NuGet ecosystem | Canonical JSON Hashing Specification | Medium — if such a package exists and is well-maintained, hand-rolling may be unnecessary duplicate effort. The planner should have a task verify via `dotnet add package <candidate> --dry-run` or the NuGet website before committing to the hand-rolled approach if this matters to them |
| A4 | `DG.Core.Models.Identity.DgIdMintingService.Mint`'s exact file path and implementation were not independently re-read this session — the claim that it mirrors `dg_identity.py` byte-for-byte rests on `dg_identity.py`'s own docstring plus STATE.md's recorded golden-vector test, not a fresh read of the C# file itself | Architecture Patterns / Pattern 2 | Low — if the C# implementation has since diverged from its own docstring's claim, the golden-vector test referenced in STATE.md would already be failing; the planner should still spot-check the actual `DgIdMintingService.cs` file before writing 1200's hashing spec text |

**If this table is empty:** N/A — see rows above.

## Open Questions (RESOLVED)

> Both questions were resolved by the Phase 1200 planner (plans committed `0dd066b`).
> The original analysis is retained below, each question annotated with its resolution.

1. **Does the C# leg's canonicalization helper live in `DG.Core` as new shared infrastructure, or
   inline in the DE-01 runner only?**
   - What we know: `DG.Core` already hosts `DesignStateIdGenerator`'s SHA-256 pattern and would
     be the natural home if the envelope DTO itself is a `DG.Core` type (consistent with the
     "contract types belong in `DG.Core`, no GH deps" established pattern).
   - What's unclear: whether 1200 intends the evidence envelope type to be a first-class
     `DG.Core.Validation` (or new `DG.Core.Contracts`) type at all, or whether the DE-01 runner
     constructs it out-of-band by calling into `RuleEvaluator` and wrapping the result itself
     without touching `DG.Core`'s public surface.
   - Recommendation: planner should decide this explicitly as a task-0 design decision, since it
     determines whether 1200 touches `DG.Core.csproj` (a "real" code change) or stays entirely in
     a new `tools/de01/` harness (contract + fixture + harness only, zero product-code change) —
     the latter reading is more consistent with "1200 does not migrate the codebase," but D-06
     ("envelope emitted at every stage boundary") arguably requires *some* code path in `DG.Core`
     to actually construct the envelope object, even if evaluation logic itself is untouched.
   - **RESOLVED (plan `1200-04-PLAN.md`, "Planner decision — RESEARCH.md Open Question 1"):**
     the canonicalization helper and envelope DTO live in **`DG.Core/Contracts/`**, not the
     harness. D-06 (envelope emitted at every stage boundary) needs the evaluator's own
     emission path, and contract types belong in `DG.Core` per house style. Scope-bounded:
     the types are added; the evaluator is **not** migrated onto them (that is 1201's).

2. **Where does the DE-01 runner physically live and in what language?**
   - What we know: D-12 locks "standalone runner + thin CI-invocable wrapper"; no existing
     cross-service harness exists to extend (confirmed — no `.github/workflows`, no existing
     `tools/` or `scripts/` cross-service test driver found).
   - What's unclear: Python (natural for calling data-service/dg-reasoner in-process or via HTTP,
     and for driving `dotnet test`/`dotnet run` as a subprocess for the C# leg) vs. a mixed
     shell+pytest+xunit orchestration.
   - Recommendation: Python is the pragmatic choice — it can call data-service/dg-reasoner
     in-process or over HTTP (both already run as FastAPI services with existing routes) and can
     shell out to a small C# console harness (a new minimal `DG.Core`-referencing console app,
     or `dotnet test --filter` against a dedicated DE-01 xunit test) for the C# leg, then read its
     JSON stdout. This keeps the "structured comparison report" (D-12) in one place.
   - **RESOLVED (plan `1200-05-PLAN.md`, "Planner decision — RESEARCH.md Open Question 2"):**
     a Python orchestrator at `tools/de01/` drives the data-service and dg-reasoner legs over
     HTTP and shells out to a new minimal `DG/tools/DG.De01Harness/` console app for the C#
     leg, reading its JSON stdout. Report is a JSON + Markdown pair under `.de01/`. No CI
     workflow is created (`.github/workflows/` is absent — Pitfall 5).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker / Docker Compose | dg-reasoner, data-service, Neo4j legs of DE-01 | Yes `[VERIFIED: docker --version, docker compose version]` | Docker 29.1.3, Compose v2.40.3 | — |
| All 12+ compose services | Full-stack DE-01 run including Speckle legs (not required for 1200's core deliverable) | Yes, running `[VERIFIED: docker compose ps — all listed containers Up]` | — | — |
| .NET SDK | C# leg of DE-01, `DG.Tests` | Yes `[VERIFIED: dotnet --version]` | 10.0.301 | — |
| Python (host) | Any host-side script authoring/testing before containerization | Yes `[VERIFIED: python3 --version]` | 3.13.7 (host) — NOTE: containers use `python:3.11-slim` per both Dockerfiles; do not assume host Python behavior matches container Python 3.11 exactly for anything version-sensitive | Containers are the source of truth for actual service behavior |
| `jsonschema` (Python) | JSON Schema validation of envelope/fixture (D-01) | Installed ambiently, **not yet pinned** in either service's `requirements.txt` `[VERIFIED: pip show + grep of requirements.txt]` | 4.26.0 ambient | Add to `requirements.txt`; trivial, no fallback needed |
| `neo4j` hostname resolution | Persisted-replay DE-01 leg | Only inside Docker Compose network; fails from host `[ASSUMED — carried forward from CONTEXT.md/STATE.md's documented environment caveat, not independently re-tested this session]` | — | D-13's graceful degradation; D-10's scripted seed path assumes in-container execution for this leg |

**Missing dependencies with no fallback:** none identified.

**Missing dependencies with fallback:**
- `jsonschema` pin — trivial `requirements.txt` addition, no risk.
- Host-vs-container Python version mismatch (3.13 host / 3.11 container) — any DE-01 script that
  needs to exercise the *actual* data-service/dg-reasoner behavior must run inside the relevant
  container or via its HTTP API, not by importing its modules directly from the host Python.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest, already in both `data-service/requirements.txt` and `dg-reasoner/requirements.txt` |
| Framework (C#) | xunit 2.9.2, `DG.Tests.csproj` |
| Config file | none dedicated (`data-service`/`dg-reasoner` have no `pytest.ini`/`pyproject.toml` found this session — pytest runs on defaults; `DG.Tests.csproj` is the .NET equivalent config) |
| Quick run command (Python, in-container) | `docker compose exec data-service pytest -x -q` / `docker compose exec dg-reasoner pytest -x -q` |
| Quick run command (C#) | `dotnet test DG/tests/DG.Tests/DG.Tests.csproj --filter FullyQualifiedName~<NewTestClass>` |
| Full suite command | `dotnet test .\DG\tests\DG.Tests\` (baseline: 412 passed per STATE.md); in-container `pytest` for each Python service (baselines: data-service 772 passed/1 skipped/8 deselected, dg-reasoner 39 passed, per STATE.md — **not re-run this session**, carried forward as reported) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGN12-01 | Canonical status vocabulary is exactly the 8 named values, no more/fewer | unit | New: `dotnet test --filter EvidenceContractTests` / `pytest test_evidence_contract.py` (schema-driven: enumerate `$defs.Status.enum` from `evidence-contract.schema.json` and assert set equality) | ❌ Wave 0 — schema file and both test files do not exist yet |
| ALGN12-02 | Evidence envelope has all required fields (project, definition, dgId/source rep, input/output hash, versions, service/version, provider/model where applicable, timestamps, warnings, status) | unit + schema validation | `jsonschema.validate(envelope, schema)` per leg | ❌ Wave 0 — schema + at least one real envelope-producing code path per leg needed |
| ALGN12-03 | Golden fixture contains all 4 atom types, 2 mixed-outcome objects, a Design State, a geometry reference | fixture-content assertion (unit) | `pytest test_golden_fixture_shape.py` — asserts fixture JSON structurally satisfies the enumerated content requirements (counts, type sets) | ❌ Wave 0 — fixture file and this test do not exist yet |
| ALGN12-04 | DE-01 compares 4 legs; supported cases agree; unsupported cases are typed, not silently divergent | integration (requires live stack) | `python tools/de01/run_de01.py --fixture fixtures/golden/fixture.json` wrapped by a thin pytest/xunit assertion on the report's `silent_disagreement_count == 0` | ❌ Wave 0 — the DE-01 runner itself is this phase's deliverable; the wrapper test is new |

### Sampling Rate

- **Per task commit:** run the specific new unit test(s) for the task just completed (schema
  validation test, fixture-shape test, or a single-leg envelope-construction test) — these run
  without a live Docker stack for the schema/shape tests; the C#-leg envelope test can run via
  plain `dotnet test`.
- **Per wave merge:** full DE-01 run against the live Docker stack (`docker compose up -d` already
  satisfied — all services confirmed running this session) plus the full pytest/xunit suites for
  regression safety on the existing 772/39/412 baselines.
- **Phase gate:** DE-01's structured report reviewed by a human (`checkpoint:human-verify`,
  matching the ROADMAP gate's "accepted by the owner" wording — this is NOT a green/red
  automatable gate by itself; a human must read the report and accept the status/evidence
  semantics, per the ROADMAP's own gate text) before `/gsd-verify-work` closes the phase.

### Wave 0 Gaps

- [ ] `spec/evidence-contract.schema.json` — the JSON Schema annex itself; nothing can be
  schema-validated until this exists
- [ ] `fixtures/golden/fixture.json` + `fixtures/golden/seed.cypher` — the golden fixture; ALGN12-03
  and ALGN12-04 both depend on it
- [ ] `data-service/requirements.txt` and `dg-reasoner/requirements.txt` — add `jsonschema` pin
- [ ] `docker-compose.yml` — add a fixture volume mount to the `dg-reasoner` service (Pitfall 1)
- [ ] `tools/de01/` (or equivalent) — the DE-01 runner itself; no existing harness to extend
- [ ] A canonical-JSON test-vector file shared (as literal data, not just prose) between the C#
  and Python test suites, per the "golden vector" precedent named in STATE.md for `DgIdMintingService`

*(These are the phase's own primary deliverables, not incidental gaps — Wave 0 here largely
restates the phase's deliverable list from the test-infrastructure angle.)*

## Security Domain

> `security_enforcement` status not found explicitly set to `false` in `.planning/config.json`
> — treated as enabled per the instruction default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no new authenticated endpoint; DE-01 runs against the existing dev-stack services with existing (weak, pre-Phase-1205) auth posture, unchanged |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | No new access-control surface; project-scoping conventions (existing `project` property discipline) are inherited, not introduced |
| V5 Input Validation | Yes | The JSON Schema annex itself IS the input-validation control for the evidence envelope — `jsonschema.validate` mechanically enforces required fields/types per D-01 |
| V6 Cryptography | Yes (narrow) | SHA-256 via stdlib `hashlib`/BCL `SHA256` for the envelope's content hashes — this is integrity hashing (detecting divergence), not a security/authentication cryptographic control; no key management, no secrets are introduced by 1200 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via fixture seed script parameters | Tampering | The existing pattern (`dg_identity.py:34-36`, verified this session — "every `session.run` receives parameters as a dict... NEVER f-string/%/`.format` interpolated into query text") must be followed for `fixtures/golden/seed.cypher`'s executing code; the `.cypher` file itself is static and checked in, so the injection risk is only in whatever Python/C# code executes it with fixture-derived parameters |
| Fixture directory path traversal via `DG_KNOWLEDGE_REPO_ROOT`-style resolution | Tampering / Information Disclosure | If the DE-01 runner or dg-reasoner resolves a fixture path from any request-supplied input (it should not — the fixture path is fixed and checked in, not user-configurable), the existing `data-service/app.py:916-917` pattern (`candidate.resolve()` + `startswith` containment check against `KNOWLEDGE_REPO_ROOT.resolve()`) is the established mitigation to reuse if any such resolution is ever needed |

This phase introduces no externally-reachable new attack surface — it is fixture/contract/harness
work exercised by developers and CI-equivalent scripts, not a new user-facing endpoint. Phase
1205 (Security and Tenancy Release Gate) is the correct owner for the broader authorization work;
1200 should not attempt to anticipate it.

## Sources

### Primary (HIGH confidence)
- `DG/src/DG.Core/Validation/RuleEvaluator.cs` — read in full this session; lines 24-34
  (zero-bindings → `Passed=false`), 108-140 (`EvaluateBuiltin`, line 130 throw), confirmed
  against CONTEXT.md's citations with only ±2 line drift, no semantic drift
- `DG/src/DG.Core/Validation/ValidationPublishPackageBuilder.cs` — read in full; lines 34-41
  (no-result → `Passed=false`) confirmed
- `data-service/app.py` (lines 260-289, 605-667, 778-791), `data-service/speckle_validation.py`
  (165-179), `data-service/dsav_watcher.py` (305-364), `data-service/cg_structure_checks.py`
  (690-749) — all read this session, all cited line numbers confirmed accurate or within ±5 lines
- `dg-reasoner/reasoning.py` (475-521) — the `{conforms, results, counts}` envelope and the
  `{conforms: None, error: "timeout", ...}` shape, both confirmed at cited lines
- `spec/DATABASE.md` (105-129) — `Run.ValidStatus`/`statePayloadJson`/`shaclReportJson` sidecar
  pattern and F-39-01 note, confirmed
- `data-service/dg_identity.py` (1-70, read in full) — the cross-language hashing precedent this
  research's primary recommendation is built on
- `docker-compose.yml` (read in full) — service topology, volume mounts, confirming the
  dg-reasoner fixture-mount gap
- `DG/tests/DG.Tests/DG.Tests.csproj` — confirmed fixture copy-to-output-directory convention
- `git status` / `git diff -- DG/src/DG.Core/Data/Neo4jRuleRepository.cs` — confirmed the
  uncommitted change is a `SUPERSEDED_BY` filter unrelated to Phase 1200
- `pip show jsonschema`, `pip index versions canonicaljson`, `pip index versions rfc8785`,
  `dotnet --version`, `docker --version`, `docker compose ps` — all run this session

### Secondary (MEDIUM confidence)
- `training/dataset_schema.json` (1-80, read this session) — Atom node contract, confirming it
  is type-agnostic at the ingestion-schema level
- `dg-reasoner/tests/fixtures/metagraph_fixture.json` — confirmed existing fixture only exercises
  3 of 4 atom types, supporting the "no repo fixture has ever included ObjectPropertyAtom" finding
- `spec/RULE-PARTITION-POLICY.md` (1-60) — structural-doc precedent informing recommended
  `spec/EVIDENCE-CONTRACT.md` structure
- `spec/DG-ID.md` section headings (grep only, not full read) — structural precedent for a
  normative cross-language-parity spec document

### Tertiary (LOW confidence)
- RFC 8785 (JSON Canonicalization Scheme) general knowledge and the specific hazards it addresses
  (number formatting, key ordering, Unicode normalization) — `[ASSUMED]`, training knowledge, not
  independently re-verified against the RFC text or Context7 this session
- `rfc8785`/`canonicaljson` PyPI package quality/maintenance claims — `[ASSUMED]`, existence
  verified via `pip index versions` but no deeper legitimacy check performed (recommended
  explicitly NOT to adopt them without running the full Package Legitimacy Gate first)
- .NET/NuGet ecosystem's lack of an equivalent package — `[ASSUMED]` due to a tooling gap in this
  session (no `nuget` CLI available), not a confirmed negative

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — `jsonschema`/`System.Text.Json` recommendations are HIGH confidence
  (already verified in-repo), but the canonical-JSON library alternatives are LOW/ASSUMED
- Architecture: HIGH — the responsibility map and pattern recommendations are grounded in
  directly-read, verified source files and an already-shipped cross-language precedent
- Pitfalls: HIGH — all five pitfalls are backed by direct verification this session (Docker
  compose file, C# source, git diff, `.github/workflows` absence)

**Research date:** 2026-09-20
**Valid until:** 30 days (2026-10-20) — this is a fast-moving milestone (v12.0 is the current
active frontier per STATE.md), and the working-tree caveats verified here (uncommitted
`Neo4jRuleRepository.cs` change, exact line numbers) should be re-checked if planning is deferred
past a handful of subsequent commits.
