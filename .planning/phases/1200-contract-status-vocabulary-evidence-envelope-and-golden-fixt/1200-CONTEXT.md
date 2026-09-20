# Phase 1200: Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture - Context

**Gathered:** 2026-09-20
**Status:** Ready for planning — **GATE12-01 CLEARED 2026-09-20**

<domain>
## Phase Boundary

Freeze the shared evidence and outcome contract that every later v12.0 phase (1201–1205) and
the v9.1/v10.0 activation gates verify against.

Five deliverables, from `.planning/ROADMAP.md` Phase 1200:

1. **Canonical status vocabulary** — `passed`, `failed`, `unknown`, `not_evaluated`,
   `no_population`, `unsupported`, `indeterminate`, `error`.
2. **Evidence envelope** — project, definition, dgId/source representation, input/output hashes,
   schema/ontology/rule/shape versions, service/version, provider/model where applicable,
   timestamps, warnings, status.
3. **One frozen cross-service fixture** — one rule, all four atom types, two objects with mixed
   outcomes (one passing, one failing), a Design State, a geometry reference.
4. **DE-01 runner contract** — drives that fixture through Python data-service → dg-reasoner →
   C# evaluator → persisted replay. Silent disagreement is a failure; typed non-equivalence for
   unsupported cases is accepted.
5. **v11.0 Phase 1105 handoff specification** — without duplicating 1105's schema-propagation work.

**This phase defines and proves the contract. It does not migrate the codebase onto it.**
Adopting the contract across every producer/consumer is the business of 1201–1205 and
v11.0 1105. Phase 1200 lands the definition, the fixture, the runner, and enough wiring to
make DE-01 produce real evidence.

**Requirements:** ALGN12-01, ALGN12-02, ALGN12-03, ALGN12-04 (`.planning/REQUIREMENTS.md`).
**Packages:** `ALIGN-P01`, `ALIGN-P02`, `ALIGN-P04`.
**Blocks:** v9.1 activation, v10.0 activation, phases 1201–1205.

</domain>

<blocking_prerequisite>
## GATE12-01 — Control-plane reconciliation — **CLEARED 2026-09-20**

**Status: SATISFIED.** The standalone pass was executed on 2026-09-20.
Ledger: `.planning/reconciliation/GSD-ALIGN-RECONCILIATION.md`.

All 8 `auto`-class items are reconciled from disk evidence. The 3 `manual` items (005, 008, 013)
remain open by their own classification — they require a live environment and **do not block
Phase 1200**. The 2 `skip` items (011, 012) are unchanged.

**What changed that Phase 1200 planning depends on:**

- **GSD-ALIGN-001** — `.planning/PROJECT.md` had listed v9.0's phases 28–40 under the v12.0
  heading with "Phase 29 — next to plan"; replaced with the real v12.0 list plus a v9.0
  carry-forward block. A broken evidence chain was found and corrected: the v9.0 archive claimed
  its traceability record was "preserved unchanged" at `.planning/REQUIREMENTS.md`, but commit
  `0e46ec3` had overwritten it with v12.0's. Counts re-derived from git history: **47 / 9 / 4 = 60**,
  agreeing exactly with the archive.
- **GSD-ALIGN-002** — UAT coverage recomputed from raw scans: **17 files / 42 items /
  4 block-scalar fields**. The `audit-uat` CLI now returns **0/0** (worse than the 5/10 the
  register recorded) because it scans `.planning/phases/` only, which is empty after archival.
  The ledger's raw inventory is the authoritative coverage record until that is fixed.
- **GSD-ALIGN-003** — Phase 35 SC1 is now recorded as a **measured FAIL** (M1 = 0.031 vs the 0.60
  gate, Corpus B / arm A3, n = 32), not "blocked". `RCGN-01` reads *partial — plumbing satisfied,
  quality gate failed*. No control-plane document claims a passing recognition gate.

**Historical note — the original blocking analysis, retained:**

Before the pass, no completion marker existed on disk and `gsd-proposed-updates.json` showed all
13 items unreconciled (8 `auto`, 3 `manual`, 2 `skip`).

`.planning/milestones/v12.0-CONTEXT.md` § `<sequencing>` is explicit and says it twice:
the reconciliation runs as a **standalone pass, not as Phase 1200 task 1**, and its completion
is a **hard sequencing prerequisite** for v12.0 planning and execution.

It was **not** folded into this phase's plans. It ran first; 1200 planning follows.

**Items that bound this phase specifically — all now reconciled:**

| Item | Class | Why it blocks 1200 |
|---|---|---|
| `GSD-ALIGN-001` | auto | One status vocabulary across STATE / ROADMAP / PROJECT / REQUIREMENTS. Directly overlaps this phase's deliverable 1 — planning a canonical status vocabulary against known-drifted control-plane status would encode the drift |
| `GSD-ALIGN-002` | auto | UAT coverage register from raw per-file scans. 1200's gate wording depends on knowing true UAT status; the `audit-uat` CLI is known to undercount (5 files/10 items vs 17 raw) |
| `GSD-ALIGN-003` | auto | Phase 35 SC1 recorded as measured FAIL (M1 = 0.03125 vs 0.60 gate), not blocked. Affects what "passed" may honestly mean in control-plane docs |

`manual` items (005, 008, 013) need live observation and remain unresolved — they do **not**
block 1200. `skip` items (011, 012) were not reopened.

</blocking_prerequisite>

<decisions>
## Implementation Decisions

All eight gray areas were auto-resolved at the user's explicit instruction
("Discuss all and accept all recommended options automatically without my confirmation").
Each decision below records the recommended option and the evidence it rests on.

### Contract artifact

- **D-01:** The frozen contract is published as **both** a normative prose spec
  `spec/EVIDENCE-CONTRACT.md` **and** a machine-readable JSON Schema annex committed alongside it.
  Prose defines *meaning* (what `no_population` asserts); schema defines *shape* (field names,
  types, required-ness). On conflict: schema authoritative for shape, prose authoritative for
  semantics. DE-01 validates every leg's output against the schema mechanically rather than by
  reading.
  **Rationale:** `spec/` already holds 12 normative docs and is named in `CLAUDE.md`
  § Schema Change Propagation; `spec/RULE-PARTITION-POLICY.md` is the closest structural analog
  and is already cited as a constraint by the milestone CONTEXT. A prose-only contract cannot be
  asserted against; a schema-only contract cannot express why `unsupported` ≠ `failed`.
  — **Reversibility:** costly — once 1201–1205 and v11.0 1105 cite the path, renaming or
  restructuring the artifact means touching every downstream phase's canonical refs.

- **D-02:** The 8 status names are adopted **verbatim** from plan §7.1 / milestone CONTEXT
  `<constraints>`. No renaming, no additions, no merging in this phase. If a ninth outcome is
  discovered during DE-01, it is recorded as a finding for 1201, not silently added.
  — **Reversibility:** one-way — the vocabulary is the milestone's spine; every later phase's
  gate is written against these exact names, and v9.1/v10.0 activation gates consume them.

### Status adoption strategy

- **D-03:** **Additive, not replacing.** The canonical typed status travels in a **new parallel
  field**; existing boolean surfaces (`Passed`, `Run.ValidStatus`, `conforms`) are **retained**
  and explicitly documented as **non-authoritative**.
  **Rationale:** `Run.ValidStatus` is a persisted Boolean list committed in
  `spec/DATABASE.md:112`, with live readers in `data-service/speckle_validation.py:173`,
  `data-service/dg_context.py:192,413`, `data-service/dsav_watcher.py:314`, `app.py:660,784`,
  and C# `Neo4jValidGraphRepository`. Replacing it would cascade the full
  `CLAUDE.md` § Schema Change Propagation list into Phase 1200 and collide with v11.0 1105's
  owned propagation scope (milestone CONTEXT `<deferred>`: "1200 owns the envelope, 1105 owns
  spec propagation. Coordinate, do not duplicate").
  **Gate alignment:** satisfies the ROADMAP gate "no downstream gate treats legacy booleans as
  authoritative" — legacy booleans survive as compatibility output, but no gate may read them.
  — **Reversibility:** costly — removing the legacy booleans later is a migration across every
  reader listed above plus Model Viewer.

- **D-04:** Legacy boolean ↔ canonical status mapping is **declared in the contract**, one
  direction only: canonical → boolean is lossy and defined (e.g. `no_population` → `false`
  under the legacy field); boolean → canonical is **undefined and forbidden**. No code may
  infer a canonical status from a legacy boolean.
  — **Reversibility:** reversible.

### Status semantics — the missing-binding question

- **D-05:** **Distinguish; do not fail closed.** Resolves open question #2 from
  `.planning/milestones/v12.0-CONTEXT.md` `<open_questions>` (owner: 1200):

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

  **`failed` is reserved for an evaluated rule with a genuine violation.** Nothing else.

  **Rationale — this is the phase's central defect, verified in the working tree:**
  - `DG/src/DG.Core/Validation/RuleEvaluator.cs:22-34` returns `Passed = false` when
    `bindings.Count == 0` → that is `no_population` reported as a real failure.
  - `DG/src/DG.Core/Validation/ValidationPublishPackageBuilder.cs:34-42` returns
    `Passed = false` when no result exists for a rule → that is `not_evaluated` reported as a
    real failure.
  - `DG/src/DG.Core/Validation/RuleEvaluator.cs:130` **throws**
    `NotSupportedException("Unsupported builtin in MVP evaluator")` → `unsupported` has no
    representable outcome at all; it is an exception, not a verdict.

  Three distinct canonical statuses currently collapse into one boolean `false`, and a fourth
  cannot be expressed. This is milestone success criterion 2 verbatim: "Empty population,
  unsupported built-ins, and missing bindings are distinguishable from a genuine pass or fail
  at every layer."
  — **Reversibility:** one-way — 1201's parser-conformance gate and 1202's per-object verdict
  gate are both written against these definitions.

### Evidence envelope

- **D-06:** The envelope is emitted at **every stage boundary**, not only at final persistence.
  A stage that produces or transforms a verdict emits one.
  **Rationale:** DE-01 compares four legs. If only the terminal write carries an envelope, a
  mid-pipeline divergence is invisible and the comparison cannot localize it — exactly the
  "silent disagreement" the gate forbids.
  — **Reversibility:** costly — reducing emission points later is easy; adding them after
  consumers assume terminal-only is not.

- **D-07:** **Hashes are computed over canonical JSON of a normalized form**, not raw payload
  bytes. Normalization rules (key ordering, number formatting, whitespace, Unicode form) are
  specified in the contract and are themselves versioned.
  **Rationale:** Python, C#, and the reasoner serialize identical logical content differently.
  Raw-byte hashing would make the legs disagree on formatting alone, manufacturing false
  non-equivalence in DE-01 and discrediting the whole experiment.
  — **Reversibility:** one-way — recorded hashes in committed evidence become meaningless if
  the normalization changes; the contract version must bump.

- **D-08:** The persisted envelope follows the **established sidecar-JSON-property pattern**
  (sibling to `statePayloadJson` and `shaclReportJson` on `Run`, per `spec/DATABASE.md:114-115`),
  not a new node-label graph structure.
  **Rationale:** matches a pattern the repo already ships twice and that Phase 823 established;
  avoids new labels/relationships, which would pull the full schema-propagation list into 1200.
  Absence must be treated as "not recorded", never as an error — same rule as `shaclReportJson`.
  — **Reversibility:** costly — migrating a JSON property to first-class nodes later needs a
  Cypher migration.

### Golden fixture

- **D-09:** **One shared top-level fixture directory** (`fixtures/golden/` — exact path is the
  planner's call) holding the fixture as the single source of truth. All four legs consume the
  **same bytes**. Per-service copies are forbidden.
  **Rationale:** identical input is the entire premise of DE-01; copies reintroduce precisely
  the drift this phase exists to eliminate. Today each service has isolated fixtures
  (`dg-reasoner/tests/fixtures/`, `DG/tests/DG.Tests/Fixtures/`) and `test/` is ad-hoc
  (`fixture_geometry.json`, `fixture_rules_v7.txt`, loose `neo4j_res*.json`).
  — **Reversibility:** costly — every leg's test wiring points at the path.

- **D-10:** The fixture is **file-based as source of truth**, with a **documented, scripted seed
  path into Neo4j** for the legs that need persistence. Existing seed scripts
  (`test/seed_designstates.cypher`, `test/seed_validation_run.cypher`) are the precedent.
  **Rationale:** keeps the parse/serialize legs runnable without a live stack; the replay leg
  still gets real persistence. Directly mitigates the known environment caveat (Neo4j-dependent
  tests fail from the host because the `neo4j` hostname resolves only inside compose).
  — **Reversibility:** reversible.

- **D-11:** The fixture is **frozen** once committed: content changes require a version bump and
  a recorded reason. 1201–1205 verify against it; they do not edit it to make their own gates pass.
  — **Reversibility:** one-way — the milestone CONTEXT calls this artifact "the milestone's spine";
  every later phase's evidence is only comparable if the input is stable.

### DE-01 runner

- **D-12:** DE-01 is a **standalone runner that emits a structured comparison report**, wrapped
  by a thin CI-invocable test. The report is the evidence artifact; the wrapper makes re-running
  cheap for 1201–1205.
  **Rationale:** the ROADMAP gate is about *evidence accepted by the owner*, which needs a
  readable artifact, not just a green check. A test-only form produces pass/fail with no record
  of what the four legs actually said.
  — **Reversibility:** reversible.

- **D-13:** **Per-leg graceful degradation.** When a leg is unavailable (dg-reasoner down, Neo4j
  unreachable), that leg records a typed `error` / `unsupported` outcome in the report; the
  runner does **not** hard-crash and does **not** silently drop the leg.
  **Rationale:** consistent with the contract's own philosophy — an unavailable leg is a typed
  non-result, not an absence. Also keeps DE-01 usable from the host given the known env caveat.
  — **Reversibility:** reversible.

- **D-14:** The DE-01 report records, per leg and per (rule, object) pair: rule ID, object ID,
  canonical status, warnings, input hash, output hash, service + version — i.e. the envelope
  itself. **Acceptance:** identical canonical statuses across legs for supported cases;
  **explicitly typed** non-equivalence for unsupported cases. A silent disagreement is a
  failure; a declared one is not.
  — **Reversibility:** one-way — this is the gate definition.

### v11.0 1105 handoff

- **D-15:** The handoff is a **dedicated section inside `spec/EVIDENCE-CONTRACT.md`**, plus a
  cross-reference in `.planning/REQUIREMENTS.md`. It states the ownership line explicitly:
  **1200 owns envelope and status *definition*; v11.0 1105 owns *propagation*** across the
  `CLAUDE.md` § Schema Change Propagation list.
  **Rationale:** milestone CONTEXT `<deferred>` — "Coordinate, do not duplicate". A separate
  standalone handoff note would drift from the contract it describes.
  — **Reversibility:** reversible.

- **D-16:** Phase 1200 performs **no schema propagation beyond what its own additive changes
  require**. If a 1200 change touches the propagation list, that specific propagation happens
  in 1200 (it is mandatory per `CLAUDE.md`); anything broader is 1105's.
  — **Reversibility:** reversible.

### Claude's Discretion

The user delegated all eight areas. Within the decisions above, the planner retains discretion on:
- exact file paths and directory names (`spec/EVIDENCE-CONTRACT.md`, `fixtures/golden/` are
  recommendations, not locked paths);
- the schema dialect (JSON Schema draft version) and whether the schema is one file or several;
- the concrete new field name carrying the canonical status (D-03 locks *additive*, not the name);
- report format for DE-01 (JSON + human-readable Markdown is the obvious pairing);
- test-framework split between pytest and xunit for the wrapper.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone-level source of truth
- `.planning/milestones/v12.0-CONTEXT.md` — **read first.** The eight locked milestone decisions
  (D1–D8), `<constraints>` (Alternative A locked, status vocabulary, envelope fields),
  `<sequencing>` (GATE12-01), `<open_questions>` (#2 is this phase's, resolved here as D-05)
- `.planning/milestones/v12.0-ROADMAP.md` — Phase 1200 deliverables and gate wording
- `.planning/REQUIREMENTS.md` — ALGN12-01..04; activation gates GATE12-01..05
- `.planning/milestones/v12.0-DISCUSSION-LOG.md` — how the milestone decisions were reached

### Alignment-plan evidence base
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md` §7.1 —
  the normative source of the status vocabulary and envelope field list (line 220); §7.2 DE-01
  acceptance (line 230); §8 work packages; §11 item 3 fixture contents
- `docs/reviews/theory-implementation-alignment/parts/csharp.md` — C# parser/evaluator/replay
  findings; the evidence base for ALIGN-P03/P04
- `docs/reviews/theory-implementation-alignment/evidence/backend-inventory.json` — P1–P12
  pipeline evidence; contradictions C1–C6 at lines 209–239
- `docs/reviews/theory-implementation-alignment/gsd.md` — GSD-ALIGN-001..013 register (GATE12-01)
- `docs/reviews/theory-implementation-alignment/evidence/gsd-proposed-updates.json` —
  **authoritative** machine-readable form of the reconciliation register

### Contract and schema surfaces this phase must respect
- `spec/DATABASE.md` — `Run.ValidStatus` Boolean-list commitment (line 112); the
  `statePayloadJson` / `shaclReportJson` sidecar pattern D-08 follows (lines 114–115);
  `:ValidationRun` / `:Run` label drift (line 111); F-39-01 (line 124)
- `spec/RULE-PARTITION-POLICY.md` — governs SWRL-validator vs SHACL ownership. The status
  vocabulary **must not violate** the partition line
- `spec/DG-ID.md` — normative `dgId`; the envelope carries `dgId`/source representation
- `spec/LPG-OWL-MAPPING.md` — Cypher→RDF translation; relevant to the dg-reasoner leg of DE-01
- `spec/API.md` — existing response envelopes the new envelope must sit beside
- `CLAUDE.md` § Schema Change Propagation — the mandatory file list for any structural change

### Code the contract must describe (verified 2026-09-20)
- `DG/src/DG.Core/Validation/RuleEvaluator.cs` — `:22-34` zero-bindings → `Passed=false`;
  `:130` throws on unsupported builtin
- `DG/src/DG.Core/Validation/ValidationPublishPackageBuilder.cs` — `:34-42` no-result →
  `Passed=false`
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs` — `RunsQuery`; repeats run-level aggregate
  across objects (1202's problem, but a consumer of this contract)
- `data-service/app.py` — `:271` `overallStatus: str = "unknown"`; `:615` `"status": "passed"`;
  `:660,784` `ValidStatus` reads
- `data-service/speckle_validation.py:173` — `overallStatus` fallback to `"unknown"`
- `data-service/cg_structure_checks.py` — `:698,742` boolean `passed`; seven deterministic
  checks; a status-vocabulary consumer (ALIGN-P04)
- `data-service/dsav_watcher.py:314-358` — derives `ValidStatus` Boolean list from `conforms`
- `dg-reasoner/reasoning.py` — `:482-520` the `{conforms, results, counts}` envelope;
  `:512` timeout shape `{conforms: None, error: "timeout"}`
- `ontology/dg-shapes.ttl` — SHACL shapes; must stay in sync with any structural change

### Fixture precedent
- `test/seed_designstates.cypher`, `test/seed_validation_run.cypher` — existing seed scripts;
  the precedent for D-10's scripted seed path
- `test/fixture_geometry.json`, `test/fixture_rules_v7.txt` — existing ad-hoc fixtures

</canonical_refs>

<code_context>
## Existing Code Insights

### The divergence this phase exists to fix

The four DE-01 legs speak three incompatible outcome dialects today:

| Leg | Dialect | Evidence |
|---|---|---|
| C# evaluator | boolean `Passed`; **throws** on unsupported | `RuleEvaluator.cs:31,69,130` |
| data-service | mixes `"passed"`/`"unknown"` strings with boolean `passed` | `app.py:271,615`; `cg_structure_checks.py:742` |
| dg-reasoner | `{conforms, results, counts}`; `conforms: None` for timeout | `reasoning.py:482-520` |
| persisted replay | `Run.ValidStatus` Boolean **list**, index-matched to ObjState order | `spec/DATABASE.md:112` |

No shared vocabulary exists. No shared fixture exists.

### Reusable Assets
- **Sidecar JSON property pattern** — `statePayloadJson`, `shaclReportJson` on `Run`. D-08
  reuses it directly; Phase 823 established the "absence means not-recorded, never an error" rule
- **Seed-script pattern** — `test/seed_*.cypher` gives D-10's Neo4j seed path a precedent
- **`spec/RULE-PARTITION-POLICY.md`** — closest structural analog for the new contract doc:
  a normative policy doc that governs cross-service ownership
- **dg-reasoner canonical envelope** — `{conforms, results, counts}` already *is* a
  deliberately-designed envelope with a documented timeout shape. Its design thinking
  (`reasoning.py:381-397` on the pySHACL `conforms` caveat) is worth carrying into the new one
- **`ErrorMessageTemplates`** (`DG/src/DG.Core/Services/`) — the What+Where+How-to-fix pattern
  for the warnings field

### Established Patterns
- **Additive-not-breaking** is the repo's house style for schema change (Phase 823's
  `shaclReportJson`, Phase 824's additive heartbeat, Phase 38's nullable
  `reinstateParameterId`). D-03 follows it
- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards GH-dependent code; contract types
  belong in `DG.Core` (no GH deps), not `DG.Grasshopper`
- **Schema propagation is mandatory** — `CLAUDE.md` lists the full file set for any structural change

### Integration Points
- `DG.Core/Validation/` — where a typed outcome must replace/accompany boolean `Passed`
- `data-service` publish path — where the envelope gets persisted alongside
  `statePayloadJson`/`shaclReportJson`
- `dg-reasoner` route handlers — where `{conforms,...}` maps to canonical status
- The DE-01 runner is **new** — no existing cross-service harness exists to extend

### Test baselines (parent-reported, not re-run this session)
data-service pytest 772 passed / 1 skipped / 8 deselected; dg-reasoner 39 passed;
DG .NET 412 passed; .NET Release build 0 warnings / 0 errors.

**Environment caveat:** 4 `DesignStateValidationFlowTests` fail fast when Neo4j is down, and
4 `test_dg_context.py` tests fail from the host (`neo4j` hostname resolves only inside compose).
Environment-dependent, not regressions. D-13 exists partly because of this.

**Working-tree caveat from the milestone CONTEXT:** `DG/src/DG.Core/Data/Neo4jRuleRepository.cs`
was recorded as having an uncommitted modification — verify its state before planning.

</code_context>

<specifics>
## Specific Ideas

- **"Silent disagreement is a failure; a declared one is not"** is the phrase that governs the
  whole DE-01 design. Any place the runner could quietly drop, coerce, or normalize away a
  difference between legs is a defect.
- **`failed` must become expensive to say.** The contract's value is that three of the four
  things currently reported as `false` stop being reported as failure.
- The user's instruction for this discussion was to resolve all eight areas with the recommended
  option and no confirmation round. Decisions D-01..D-16 are therefore Claude-selected against
  repo evidence, not user-stated preferences — a planner may flag any of them for reconsideration
  if research contradicts the evidence cited.

</specifics>

<deferred>
## Deferred Ideas

| Idea | Owner | Note |
|---|---|---|
| Migrating every producer/consumer onto the canonical status | 1201–1205 + v11.0 1105 | 1200 defines and proves; it does not migrate the codebase |
| Full schema propagation of the envelope across the `CLAUDE.md` list | v11.0 **1105** | Milestone CONTEXT `<deferred>`: 1200 owns the envelope, 1105 owns propagation |
| `ObjectPropertyAtom` branch + malformed-syntax parser fixtures | **1201** | ALGN12-05/06/07 |
| Making `unsupported` a returned outcome rather than a thrown exception in `RuleEvaluator.cs:130` | **1201** | 1200 defines that `unsupported` exists; 1201 makes the parser/evaluator emit it |
| Fixing `Neo4jValidGraphRepository.RunsQuery` run-level aggregate repeated across objects | **1202** | ALGN12-10 |
| Design State content-equivalence vs capture-event identity | **1202** | Open question #3 |
| Geometry / `ClassIri` as normative v2 members | **1202** | Open question #4 |
| Which service owns canonical per-object verdicts | **1202** | Open question #5 |
| `ATTRIBUTE_OF` vs `PARAM_LINK` | **1203** | Milestone D8; both branches costed there |
| Identity authority across GH/Revit/IFC/Speckle | **1203** | Open question #7 |
| LLM provider/model/prompt snapshot for reproducibility | **1204** | Open question #10 |
| Authorization model for project isolation / CDE governance | **1205** | Open question #9 |
| F-39-01 (auto-runs SHACL-validated before their own `ValidStatus` is written, verdicts uniformly all-false) | Not 1200 | Pre-existing disclosed finding; the contract should be able to *describe* it, but fixing it is out of scope |
| `:ValidationRun` / `:Run` label and `Run_Id`/`runId` property drift | Not 1200 | Documented drift in `spec/DATABASE.md:111`; note it, do not fix it here |
| ComputGraph structural-trace vs executable Behaviour/FBS semantics | **v11.0 1106** | Open question #6 — explicitly not v12.0 |
| Five-layer model: logical partition or runtime contract | **v11.0 1106** | Open question #8 — explicitly not v12.0 |
| Live Rhino/LLM/Speckle UAT | **v9.0 Phase 40** | GATE12-04 — v12.0 cannot mark these passed |
| Graphify regeneration | Not scheduled | Milestone CONTEXT: explicitly not in this milestone (risk R-15) |
| Alternative B (RDF/OWL canonical) / DE-02, Alternative C / DE-03 | Post-milestone | Alternative A is locked; revisit only after DE-01/DE-02 quantify projection loss |
| ROADMAP progress-table drift (Phase 37 shown "Not started" though fully executed) | Reconciliation pass | Surfaced in `STATE.md`; belongs to GATE12-01, not 1200 |

</deferred>

---

*Phase: 1200-Contract, Status Vocabulary, Evidence Envelope, and Golden Fixture*
*Context gathered: 2026-09-20*
