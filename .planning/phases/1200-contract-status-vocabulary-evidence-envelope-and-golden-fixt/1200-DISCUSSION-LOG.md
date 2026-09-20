# Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-20
**Phase:** 1200-Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture
**Areas discussed:** Contract artifact form, Status adoption strategy, Missing-binding semantics, Evidence envelope scope, Fixture location + format, DE-01 runner shape, GATE12-01 handling, v11.0 1105 handoff

**Mode note:** The user selected all eight areas and instructed: *"Discuss all and accept all
recommended options automatically without my confirmation."* Every option below was therefore
resolved by Claude against repo evidence rather than chosen by the user. The user did **not**
request auto-advance into plan-phase, and plan-phase is independently blocked by GATE12-01.

**Pre-answered by the milestone CONTEXT (not re-asked):** Alternative A stack locked; the 8
status names; the envelope field list; fixture contents; silent-disagreement-is-failure; no
manuscript edits; schema propagation mandatory; ATTRIBUTE_OF deferred to 1203.

---

## Contract artifact form

| Option | Description | Selected |
|--------|-------------|----------|
| Prose spec only | A normative `spec/` markdown doc, like the other 12 | |
| JSON Schema only | Machine-readable, mechanically assertable | |
| Both, schema as authoritative annex | Prose defines meaning, schema defines shape | ✓ |

**Choice:** Both (D-01). Prose authoritative for semantics, schema authoritative for shape.
**Notes:** `spec/RULE-PARTITION-POLICY.md` is the structural analog and is already cited as a
constraint by the milestone CONTEXT. Prose-only cannot be asserted against by DE-01;
schema-only cannot express why `unsupported` ≠ `failed`.

---

## Status adoption strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Additive — new typed field, legacy booleans retained as non-authoritative | Lowest blast radius | ✓ |
| Replace boolean surfaces outright | Cleanest end state, largest migration | |

**Choice:** Additive (D-03, D-04).
**Notes:** Decisive evidence — `Run.ValidStatus` is a persisted Boolean **list** committed in
`spec/DATABASE.md:112` with live readers in `speckle_validation.py:173`, `dg_context.py:192,413`,
`dsav_watcher.py:314`, `app.py:660,784`, and C# `Neo4jValidGraphRepository`. Replacing it pulls
the full `CLAUDE.md` propagation list into 1200 and collides with v11.0 1105's owned scope.
The ROADMAP gate ("no downstream gate treats legacy booleans as authoritative") is satisfied by
retaining the booleans as compatibility output that no gate may read — not by deleting them.
Mapping is one-directional: canonical → boolean is defined and lossy; boolean → canonical is
forbidden.

---

## Missing-binding semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Fail closed — missing binding is `failed` | Conservative; preserves current behaviour | |
| Single `unknown` for all non-determinations | Simple; loses the distinctions | |
| Distinguish `no_population` / `not_evaluated` / `unknown` by cause | Matches the vocabulary's intent | ✓ |

**Choice:** Distinguish by cause (D-05). `failed` reserved for an evaluated rule with a genuine
violation.
**Notes:** Resolves open question #2, which the milestone CONTEXT assigns to 1200. Verified in
the working tree that three distinct statuses currently collapse into one boolean, and a fourth
cannot be expressed at all:
- `RuleEvaluator.cs:22-34` — zero bindings → `Passed=false` (should be `no_population`)
- `ValidationPublishPackageBuilder.cs:34-42` — no result → `Passed=false` (should be `not_evaluated`)
- `RuleEvaluator.cs:130` — **throws** `NotSupportedException` on unsupported builtin
  (`unsupported` has no representable outcome)

This is milestone success criterion 2 stated verbatim. Fail-closed was rejected because it
preserves exactly the defect the phase exists to remove.

---

## Evidence envelope scope

| Option | Description | Selected |
|--------|-------------|----------|
| Emit at every stage boundary; canonical-JSON hashes; sidecar JSON property | Localizes divergence | ✓ |
| Emit only at final persistence | Cheaper, but divergence becomes invisible | |
| Raw-byte hashing | Simpler, but legs differ on formatting alone | |
| New node-label graph structure | First-class, but pulls in full schema propagation | |

**Choice:** Every stage boundary + canonical-JSON-over-normalized-form hashes + sidecar JSON
property (D-06, D-07, D-08).
**Notes:** Terminal-only emission would make a mid-pipeline divergence invisible, which is the
"silent disagreement" the gate forbids. Raw-byte hashing would manufacture false non-equivalence
in DE-01 because Python, C#, and the reasoner serialize identical content differently — the
normalization rules are themselves versioned. The sidecar property reuses the
`statePayloadJson` / `shaclReportJson` pattern from `spec/DATABASE.md:114-115`, including
Phase 823's "absence means not-recorded, never an error" rule.

---

## Fixture location + format

| Option | Description | Selected |
|--------|-------------|----------|
| One shared top-level dir, file-based SoT + scripted Neo4j seed | Same bytes for all legs | ✓ |
| Per-service copies | Convenient; reintroduces drift | |
| Extend `test/` | Existing location; currently ad-hoc and unstructured | |
| Live-Neo4j-only fixture | Realistic; unusable from host | |

**Choice:** Shared top-level directory, file-based source of truth, documented seed path
(D-09, D-10, D-11).
**Notes:** Identical input bytes is the entire premise of DE-01; copies reintroduce the drift the
phase exists to eliminate. Today `dg-reasoner/tests/fixtures/` and `DG/tests/DG.Tests/Fixtures/`
are isolated and `test/` is ad-hoc (`fixture_geometry.json`, `fixture_rules_v7.txt`, loose
`neo4j_res*.json`). File-based keeps parse/serialize legs runnable without a live stack, which
matters given the known env caveat. `test/seed_designstates.cypher` and
`test/seed_validation_run.cypher` are the precedent for the seed path. The fixture is frozen once
committed — later phases verify against it, they do not edit it to pass their own gates.

---

## DE-01 runner shape

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone runner emitting a comparison report + thin CI test wrapper | Evidence artifact + cheap re-runs | ✓ |
| Test-suite only | Green/red, no record of what the legs said | |
| Script only, no CI hook | Report but expensive for 1201-1205 to re-run | |

**Choice:** Standalone runner + report, wrapped by a CI-invocable test (D-12, D-13, D-14).
**Notes:** The ROADMAP gate is about evidence accepted by the owner, which needs a readable
artifact. Per-leg graceful degradation was added deliberately: an unavailable leg records a typed
`error`/`unsupported` outcome rather than crashing the runner or being silently dropped — which
is the contract's own philosophy applied to itself, and keeps DE-01 usable from the host where 4
`DesignStateValidationFlowTests` and 4 `test_dg_context.py` tests already fail on the `neo4j`
hostname.

---

## GATE12-01 handling

| Option | Description | Selected |
|--------|-------------|----------|
| Record as blocking prerequisite in CONTEXT.md; run separately | Matches milestone sequencing | ✓ |
| Run it now as part of this discussion | Out of scope for discuss-phase | |
| Fold into Phase 1200 plans as task 1 | Explicitly forbidden by milestone CONTEXT | |
| Narrow to items that bind 1200 only | Partially adopted — named within the blocking note | |

**Choice:** Blocking prerequisite recorded, not executed here (D — see `<blocking_prerequisite>`).
**Notes:** Verified NOT done — no completion marker on disk; `gsd-proposed-updates.json` shows 13
items unreconciled (8 `auto`, 3 `manual`, 2 `skip`). `.planning/milestones/v12.0-CONTEXT.md`
§ `<sequencing>` states twice that this runs as a standalone pass, **not** as Phase 1200 task 1.
The three items that specifically bind 1200 are named in CONTEXT.md: `GSD-ALIGN-001` (status
vocabulary across control-plane docs — directly overlaps deliverable 1), `GSD-ALIGN-002` (UAT
register undercount), `GSD-ALIGN-003` (Phase 35 SC1 as measured FAIL). The `manual` items do not
block; the `skip` items must not be reopened.

---

## v11.0 1105 handoff

| Option | Description | Selected |
|--------|-------------|----------|
| Section inside the contract spec + requirements cross-reference | Stays with what it describes | ✓ |
| Separate standalone handoff note | Drifts from the contract | |
| Requirements cross-reference only | Too thin to define an ownership line | |

**Choice:** Dedicated section in `spec/EVIDENCE-CONTRACT.md` plus a requirements cross-reference
(D-15, D-16).
**Notes:** Milestone CONTEXT `<deferred>` is explicit — "1200 owns the envelope, 1105 owns spec
propagation. Coordinate, do not duplicate." Phase 1200 performs no schema propagation beyond
what its own additive changes mandate under `CLAUDE.md`.

---

## Claude's Discretion

The user delegated all eight areas wholesale. Within the locked decisions, the planner retains
discretion on: exact file paths (`spec/EVIDENCE-CONTRACT.md` and `fixtures/golden/` are
recommendations, not locked); JSON Schema dialect and file count; the concrete name of the new
canonical-status field (D-03 locks *additive*, not the name); DE-01 report format; and the
pytest/xunit split for the test wrapper.

Because these decisions are Claude-selected rather than user-stated, a planner or researcher may
flag any of them for reconsideration if research contradicts the cited evidence.

## Deferred Ideas

Fifteen-plus items routed to named owners — full table in CONTEXT.md `<deferred>`. Headlines:

- **Migrating producers/consumers onto the canonical status** → 1201–1205 + v11.0 1105.
  1200 defines and proves the contract; it does not migrate the codebase.
- **Making `unsupported` a returned outcome instead of a thrown exception** (`RuleEvaluator.cs:130`)
  → 1201.
- **Run-level aggregate repeated across objects** (`Neo4jValidGraphRepository.RunsQuery`) → 1202.
- **Full schema propagation of the envelope** → v11.0 1105.
- **F-39-01** (auto-runs SHACL-validated before their own `ValidStatus` is written) → not 1200;
  the contract should be able to describe it, not fix it.
- **`:ValidationRun` / `:Run` label drift** → documented in `spec/DATABASE.md:111`; note, don't fix.
- **Open questions #6 and #8** (ComputGraph semantics, five-layer model) → v11.0 1106, explicitly
  not v12.0.
- **Live Rhino/LLM/Speckle UAT** → v9.0 Phase 40 (GATE12-04 — v12.0 cannot mark these passed).
- **ROADMAP progress-table drift** (Phase 37 shown "Not started" though fully executed) →
  belongs to the GATE12-01 reconciliation pass.
