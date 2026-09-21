# Phase 1202: Design State Replay and Per-Object Verdict Closure - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish **one canonical replay contract** for Design State and validation outcomes: a Design
State that survives `publish → query → replay` reproducing a canonical state hash, and per-object
verdicts that stay distinct instead of collapsing into one run-level aggregate.

Five deliverables, from `.planning/ROADMAP.md` Phase 1202:

1. **Explicit decision** on content-equivalence versus capture-event identity.
2. **v2 serializer/readers aligned** for geometry, ClassIri, lists, enums, and schema version —
   *or an explicit exclusion contract*.
3. **Canonical per-object `ValidationEntity` replay path** with a mixed pass/fail fixture.
4. **Canonical state hash** and membership manifest.
5. **Explicit separation** of snapshot identity from mutable run/operational status.

**Requirements:** ALGN12-08, ALGN12-09, ALGN12-10, ALGN12-11 (`.planning/REQUIREMENTS.md`).
**Packages:** `ALIGN-P05`, `ALIGN-P06`.
**Requires:** 1200 (frozen contract) and 1201 (typed parser/evaluator status) — **both complete
and verified.**
**Blocks:** v9.1 shared-surface gate; v10.0 activation gate; future state-dependent
generation/editing.

**Gate:** `publish → query → replay` reproduces the canonical state hash and preserves mixed
object verdicts, **or** every excluded member is formally documented.

This phase **consumes** the 1200 contract; it does not redefine the status vocabulary, the
envelope shape, or the canonicalization rules.

</domain>

<upstream_corrections>
## Two planning-corpus claims that do NOT survive contact with disk

Both were verified directly by the orchestrator on 2026-09-21. **Plan against the disk facts, not
the inherited prose.**

### Correction 1 — "current IDs exclude label and capture time" is FALSE for the shipping path

`.planning/milestones/v12.0-CONTEXT.md` open question #3 asserts "Current IDs exclude label and
capture time". That is true of `DesignStateIdGenerator.ComputeObjectStateId`
(`DG/src/DG.Core/Services/DesignStateIdGenerator.cs:57-61`, hashing
`projectId|objectInstanceId|variableName`) — but **that function has zero production call sites.**

The ObjState ID that actually ships is minted by a *private duplicate* in
`DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:190-196`:

```csharp
var input = $"{objectRef}|{label ?? ""}";   // L192
```

So the live ObjState ID **includes Label** and **omits project and variableName** — the opposite
of the documented contract on both counts. `DesignStateCompositionComponent.cs:156` folds those
member IDs into the aggregate, so DesignState identity transitively inherits Label-sensitivity.

`CapturedAtUtc` does exist on the model (`DesignState.cs:19`) and is set at composition
(`DesignStateCompositionComponent.cs:162`), but is **identity-inert** — it never feeds a hash.

### Correction 2 — `RunsQuery` does not "repeat an aggregate"; it never reads the data at all

Prior phases (1200 `<deferred>`, 1201 `<deferred>`) describe
`Neo4jValidGraphRepository.RunsQuery` as "repeats run-level aggregate across objects". True, but
it **understates the defect and mis-sizes the fix**:

- `Neo4jValidGraphRepository.cs:13-22` — `RunsQuery` selects `runId, project, createdAt,
  rulesJson, statePayloadJson`. **`run.ValidStatus` is not in the projection.** The index-matched
  Boolean list that `spec/DATABASE.md:112` defines, and that `data-service/app.py:586` actually
  writes, is never read by C#.
- `Neo4jValidGraphRepository.cs:65-66` — `var overallPass = results.All(r => r);` — a single AND
  over *rules*, not objects.
- `Neo4jValidGraphRepository.cs:73-75` — the defect verbatim:
  ```csharp
  var statusList = objStateCount > 0
      ? Enumerable.Repeat(overallPass, objStateCount).ToList()
      : new List<bool> { overallPass };
  ```

The list is **fabricated**, not mis-indexed. This is a **missing feature, not a mapping bug**, and
the fix is correspondingly larger than the inherited description implies.

### Third disk fact worth stating plainly

**No state-hash concept exists anywhere in the repo.** A grep for
`stateHash|state_hash|canonicalStateHash|contentHash` across `DG/src`, `data-service`, `spec`,
`tools`, `.planning/phases` returns zero hits. D-05 below is new construction (an *extension* of
1200's hasher, not a new crypto primitive).

</upstream_corrections>

<decisions>
## Implementation Decisions

Three gray areas were discussed interactively (Identity semantics, Replay membership, Per-object
verdict path). Partway through the third area the user instructed:
*"Принимай все рекомендованные варианты самостоятельно"* (accept all recommended options
yourself). **D-01 … D-12 are user-selected; D-13 … D-17 are Claude-selected under that
instruction**, each recording the evidence it rests on. A planner may flag any Claude-selected
decision for reconsideration if research contradicts the cited evidence.

### Identity semantics (ALGN12-08)

- **D-01:** Design State identity is **both layers**: a **capture-event identity as the node key**,
  plus a **content hash stored as a `canonicalStateHash` property**.
  **Rationale:** satisfies ALGN12-08's "explicitly classified" requirement and delivers
  ALGN12-09's canonical state hash in the same move, instead of two separate mechanisms. Content
  equivalence remains *queryable* (by hash) without being *identity-bearing*.
  **Consequence the planner must handle:** capture-event keying means recapture no longer dedupes
  by MERGE. `DesignStateIdGenerator.cs:10-12` documents dedup-across-runs as the current
  intent, and `data-service/cg_paramstate_store.py:336` MERGEs on `StateId`+`project`. The graph
  grows per capture; the idempotent re-accept path must be re-examined, **not** silently broken.
  — **Reversibility:** one-way — changing the node key after states are written needs a Cypher
  migration, and 1202's own gate is written against the hash-plus-key pair.

- **D-02:** The canonical state hash **extends the Phase 1200 hasher**: a canonical DesignState
  projection is fed into `CanonicalJsonWriter.HashCanonical` (C#) /
  `data-service/canonical_json.py:hash_canonical` (Python).
  **Rationale:** inherits 1200's cross-language parity, already hardened by CR-01 (decimal scale)
  and WR-01 (negative zero), and its `CanonicalizationVersion`. Authoring a separate state hasher
  would introduce a **fourth** hashing regime beside `DesignStateIdGenerator.HashToHex16`,
  `DgIdMintingService.HashToHex16`, and `CanonicalJsonWriter`.
  **Forbidden:** inventing a second canonicalization. If the projection needs a rule 1200's
  canonicalization cannot express, that is a finding against `spec/EVIDENCE-CONTRACT.md`, not a
  local fix.
  — **Reversibility:** one-way — a recorded hash becomes meaningless if the canonicalization
  changes; the contract version must bump.

- **D-03:** Historical states are treated **additively — no rewrite**. New captures use the new
  keying and carry `canonicalStateHash`; existing rows stay as-is and are documented as
  pre-contract.
  **Rationale:** matches the repo's additive house style and Phase 823's rule that *absence means
  "not recorded", never an error*. Avoids adding a second unapproved migration — the repo already
  carries `migrations/2026-07-07_validationgraph_to_validgraph.cypher` unapproved and unrun.
  — **Reversibility:** reversible.

- **D-04:** ObjState minting **converges on `DesignStateIdGenerator`**. The private duplicate at
  `ObjectStateComponent.cs:190-196` is deleted and the component routes through the documented
  generator, so one function mints every ObjState ID.
  **Rationale:** a phase whose stated goal is a canonical identity contract cannot ship two
  disagreeing minting paths. Under D-03 the divergent keying of new captures is already accepted.
  **Planner note:** requires a Grasshopper plugin rebuild; Label stops being identity-bearing, so
  renaming an object no longer changes its identity.
  — **Reversibility:** costly — reverting means restoring a duplicated implementation that the
  contract will by then name as removed.

### Replay membership (ALGN12-09, milestone open question #4)

- **D-05:** **`ClassIri` becomes a normative serialized member** of the v2 payload —
  added to `ObjStateDto` (`DesignStatePayloadV2Serializer.cs:472-483`).
  **Rationale:** `ObjState.ClassIri` (`ObjState.cs:18`) is load-bearing — its own doc-comment says
  `DesignStateBindingService` uses it for Class IRI matching per D-05. Today it is absent from the
  DTO, so **a replayed Design State cannot re-bind to its ontology class.** Excluding a member the
  binding service actually needs would make "replay" mean materially less. Deriving it from
  `dgId → (:Object).classIri` was rejected: it adds a graph round-trip to every replay, makes
  offline replay impossible, and `classIri` is optional on `:Object` (`spec/DATABASE.md:57`) so it
  can return null.
  — **Reversibility:** costly — once persisted payloads carry it, readers assume it.

- **D-06:** **Geometry is formally excluded** from the normative payload and from the state hash;
  it is referenced by `dgId` / Speckle `objectId` instead.
  **Rationale:** this is the roadmap's own "or an explicit exclusion contract" escape hatch, taken
  deliberately and documented. Rhino geometry has no stable JSON form; serializing it would force
  a floating-point canonicalization decision that extends 1200's hasher into genuinely hard
  territory and inflates every payload. Defensible under `spec/DG-ID.md:15` — native ids are
  bindings, not folded into the object.
  **Must be stated plainly in the contract:** replay **cannot** reconstruct a viewable state
  offline. That is the accepted cost, not an oversight.
  — **Reversibility:** reversible — adding geometry later is additive.

- **D-07:** The payload **stays at `version: "2"`**; `ClassIri` is an **optional additive member**
  whose absence means "not recorded, never an error" (Phase 823 rule). Old payloads keep reading.
  **Bundled fix — mandatory, not optional:** `Neo4jValidGraphRepository.TryParseDesignState`
  (`:167-170`) currently does **structural sniffing** on the presence of
  `objStates`/`paramStates`/`propStates` and **never checks `version` at all**, while the
  serializer enforces it strictly (`:66-69`). A future v3 payload would be silently misread. This
  phase closes that hole regardless of the version decision.
  — **Reversibility:** reversible.

- **D-08:** **Canonical StateId-sorted order is the contract.** The payload and the hash use the
  serializer's existing sort (`DesignStatePayloadV2Serializer.cs:28/32/36`); **wiring order is
  explicitly not preserved** and is documented as such.
  **Rationale:** makes the state hash stable and order-independent — two identical designs wired
  differently hash identically, which is what a *content* hash must mean. Today the round-trip is
  already lossy here: `Serialize` sorts, `Deserialize` appends in document order (`:83-96`), while
  `DesignStateCompositionComponent.cs:165-170` deliberately preserves wiring order. That order is
  lost on first serialize today, silently.
  **Direct consequence — the planner must carry this into D-09:** `spec/DATABASE.md:112` defines
  `ValidStatus` as **index-matched to ObjState order**. With canonical sort normative, **positional
  verdict matching is formally dead.** Per-object verdicts must be identity-addressed.
  — **Reversibility:** one-way — the hash definition depends on it.

- **D-09:** The **two independent payload readers converge on one.**
  `Neo4jValidGraphRepository.TryParseDesignState` delegates to
  `DesignStatePayloadV2Serializer.Deserialize`, giving one reader, one version check, one
  membership contract.
  **Rationale:** the phase's stated goal is a single canonical replay contract; shipping two
  readers of the same payload is the exact drift class this milestone exists to eliminate. Only
  the serializer's reader is covered by the serializer's tests today.
  **Planner note — the quirk that forced the fork:** `ParamState.Parameters` is a getter-only
  `Collection<T>` that `System.Text.Json` silently skips, which is why
  `Neo4jValidGraphRepository.cs:181-190` documents a hand-rolled converter plus a manual backfill
  loop at `:194-223`. The shared path must handle this — do not assume the serializer already does.
  — **Reversibility:** costly — callers of both readers must agree.

### Per-object verdict path (ALGN12-10)

**Starting position, verified on disk:** the per-object truth is **live end-to-end in Python** and
**completely absent in C#**. `ValidationEntity` nodes are written at `data-service/app.py:633-656`
(one per `(runId, ruleId, dgEntityId)`), read at `:849-870` with failed-wins dedup, counted at
`:790`, deleted at `:836`. A grep for `ValidationEntity`/`HAS_ENTITY` across `DG/src` returns
**zero hits**; `IValidGraphRepository`'s entire surface is
`GetRunsAsync → {Runs, StatusList, DesignStates}` (`IValidGraphRepository.cs:5-25`).

- **D-10:** The **1200 evidence envelope's per-`(rule, object)` rows are the canonical per-object
  verdict source.** `Run.ValidStatus` and `ValidationEntity` are demoted to legacy and
  non-authoritative.
  **Rationale:** one contract across all four DE-01 legs, and it directly satisfies the 1200
  ROADMAP gate *"no downstream gate treats legacy booleans as authoritative"*. The alternatives
  each leave two answers to the same question.
  — **Reversibility:** one-way — 1202's gate is written against it.

- **D-11:** When `evidenceEnvelopeJson` is **absent** (pre-1200 runs, per `spec/DATABASE.md:116`),
  every object reports **`not_evaluated`. There is no fallback.**
  **Rationale:** absence means the per-object verdict was never canonically recorded. Inferring a
  canonical status from a legacy boolean is **explicitly forbidden by 1200 D-04** (canonical →
  boolean is lossy and defined; boolean → canonical is undefined and forbidden).
  **Accepted cost, state it in the contract:** existing runs visibly lose their canvas colors
  until re-run. That is honest reporting, not a regression.
  — **Reversibility:** reversible.

- **D-12:** Per-object rollup uses the **shipped Phase 1201 precedence verbatim**:
  `error > failed > indeterminate > unsupported > unknown > not_evaluated > no_population > passed`
  — `EvidenceEnvelopeFactory.RollupPrecedence` (`DG/src/DG.Core/Contracts/
  EvidenceEnvelopeFactory.cs:25-35`) / `_ROLLUP_PRECEDENCE` (`data-service/evidence_contract.py:87-96`).
  **Rationale:** 1201's context is explicit — *"the planner MUST adopt the shipped order verbatim
  and MUST NOT introduce a second table"*. It is already byte-identical in both languages.
  **Note the difference from today's Python behavior:** `app.py:864-869` uses **failed-wins**,
  under which `error` loses to `failed`. The shipped precedence puts `error` first. Reconciling
  this is in scope — and it is a **behavior change on the Python side**, not a no-op.
  **Preserve the implementation property:** 1201 records that the roll-up is an ordered list,
  "never by boolean arithmetic or a max/min over enum ordinal values".
  — **Reversibility:** one-way — a second precedence table is exactly the drift being eliminated.

### Claude-selected under the user's blanket-accept instruction

- **D-13:** `IValidGraphRepository` gains an **additive** method returning typed per-object
  verdicts (`EvidenceStatus`-valued). `GetRunsAsync` and its `StatusList` are **retained** and
  documented non-authoritative — 1200 D-03's additive-not-breaking rule applied to the C# read
  model.
  — **Reversibility:** costly — removing the legacy surface later touches every reader.

- **D-14:** The fabricated list at `Neo4jValidGraphRepository.cs:73-75` (`Enumerable.Repeat`) is
  **removed**, not patched in place. Per correction 2 above this is a missing feature; the read
  path is built, and the fabrication deleted rather than made "more accurate".
  — **Reversibility:** reversible.

- **D-15:** **ALGN12-11 takes the cheapest defensible option** (the user did not select this area
  for discussion): immutable snapshot properties are written **write-once via `ON CREATE SET`**,
  plus an explicit declaration in the contract of which `:ValidationRun` properties are immutable
  and which are mutable. **No physical node split, no migration.**
  **Rationale:** `data-service/app.py:573-588` currently uses an unconditional `SET` that writes
  immutable content (`statePayloadJson` `:584`, `rulesJson` `:583`, `createdAt` `:588`) and
  mutable status (`status` `:585`, `ValidStatus` `:586`, `SendStatus` `:587`) onto one node, with
  later independent mutations at `:2137` (`evidenceEnvelopeJson`), `:2245` (`shaclReportJson`),
  `:2272` (`SendStatus`). A physical split would trigger the full `CLAUDE.md` § Schema Change
  Propagation sweep plus a migration — disproportionate to the requirement's wording, which asks
  for *separation*, not relocation.
  **Planner note:** the MERGE key is `(graph, project, runId)`, so re-publishing the same `runId`
  currently overwrites the snapshot. `ON CREATE SET` is what makes the immutability real rather
  than declared.
  — **Reversibility:** reversible — a physical split remains available to a later phase.

- **D-16:** **DE-01 is extended as this phase's exit evidence**, mirroring 1201's D-11 pattern:
  per-object comparison plus canonical-state-hash verification across the legs. Unit tests alone
  are **not** sufficient exit evidence.
  **Rationale:** the ROADMAP gate is `publish → query → replay reproduces the canonical state
  hash and preserves mixed object verdicts` — that is a cross-service claim, and
  `tools/de01/legs.py:run_leg_replay` (~`:747`) is the existing replay leg. It currently reads
  **only** `evidenceEnvelope` (its docstring: *"never `ValidStatus` (D-04)"*) and has no state
  hash and no per-object comparison.
  **Requires a live compose stack** — plan for it explicitly, as 1201-06 had to.
  — **Reversibility:** one-way — this is a gate definition.

- **D-17:** `fixtures/golden/fixture.json` **stays frozen** (1200 D-11). The mixed pass/fail
  per-object fixture required by deliverable 3 is built from the **existing** `OBJ_GOLD_PASS` /
  `OBJ_GOLD_FAIL` objects. Any new fixture material goes in a **sibling path**, never by editing
  the frozen file.
  **Precedent:** 1201 did exactly this with `fixtures/golden/parser/` (its D-16), and 1200-06/09
  added vectors to `canonical-vectors.json` — a sibling — without touching `fixture.json`.
  — **Reversibility:** reversible.

### Claude's Discretion

Within the decisions above, the planner retains discretion on:

- the concrete name and shape of the capture-event key (a run nonce vs `capturedAtUtc` vs a
  composite) — D-01 locks *both layers*, not the key's spelling;
- the exact shape of the canonical DesignState projection fed to `HashCanonical` (D-02), provided
  it is stated explicitly and excludes geometry per D-06;
- the name and signature of the additive `IValidGraphRepository` method (D-13);
- whether the membership manifest is a separate artifact or a section inside the state payload;
- how `PropState`'s missing `CapturedAtUtc` (absent from `PropState.cs` while ObjState/ParamState/
  DesignState all carry one) is treated — normalize or document as excluded;
- the file split for any new fixture material under the D-17 sibling path;
- test-framework split between pytest and xunit for the D-16 wrapper.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contract this phase consumes (Phases 1200 + 1201 output)
- `spec/EVIDENCE-CONTRACT.md` — semantic authority for what each status asserts; the envelope
  definition D-10 makes canonical
- `spec/evidence-contract.schema.json` — shape authority for the wire-form literal set
- `spec/SWRL-SUBSET.md` — 1201's normative subset/non-claims doc
- `DG/src/DG.Core/Contracts/EvidenceStatus.cs` — the frozen 8-member enum (wire form in
  `EvidenceStatusNames.cs`)
- `DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs:25-35` — **`RollupPrecedence`, adopted
  verbatim by D-12**
- `data-service/evidence_contract.py:87-96` — `_ROLLUP_PRECEDENCE`, the Python mirror
- `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs` — `CanonicalizationVersion` (`:40`),
  `HashScalarTuple` (`:48`), `Canonicalize` (`:90`), `HashCanonical` (`:98`) — **D-02 extends this**
- `data-service/canonical_json.py` — `canonicalize` (`:161`), `hash_canonical` (`:180`) — the
  cross-language pair
- `fixtures/golden/` — `fixture.json` (**frozen, do not edit — D-17**), `canonical-vectors.json`,
  `seed.cypher`, `MANIFEST.md`, `parser/`
- `.planning/phases/1200-.../1200-CONTEXT.md` — D-01..D-16; especially **D-05 status table**,
  **D-03/D-04 additive + forbidden boolean→canonical inference**, **D-11 fixture freeze**
- `.planning/phases/1201-.../1201-CONTEXT.md` — the shipped rollup precedence correction block;
  D-11's "DE-01 re-run as exit evidence" pattern D-16 mirrors

### Milestone-level source of truth
- `.planning/ROADMAP.md` — Phase 1202 deliverables and gate wording (lines 113–129)
- `.planning/REQUIREMENTS.md` — ALGN12-08/09/10/11
- `.planning/milestones/v12.0-CONTEXT.md` — `<open_questions>` **#3 (identity), #4 (geometry/
  ClassIri normativity), #5 (who owns per-object verdicts)** — all three owned by this phase and
  answered by D-01, D-05/D-06, D-10 respectively; `<constraints>` (Alternative A locked);
  `<success_criteria>` items 3 and 4 are this phase's

### Schema and contract surfaces this phase must respect
- `spec/DATABASE.md` — `Run.ValidStatus` Boolean-list, **index-matched to ObjState order**
  (`:112`) — the contract D-08 formally retires; `statePayloadJson`/`shaclReportJson`/
  `evidenceEnvelopeJson` sidecars (`:114-116`); **`:116` = envelope absent on pre-1200 runs
  (D-11)**; `:ValidationRun` vs `:Run` label drift (`:111`); `:Object.classIri` optional (`:57`);
  run `status` transition table + `attempts`/`lastError`/`completedAt` (`:118-124`) — the mutable
  set D-15 separates; `:99` amended-Phase-38 MERGE-on-StateId+project (D-01/D-03 touch this)
- `spec/DG-ID.md` — normative `dgId`; **`:15`** (native ids are bindings, not folded into the
  object) is D-06's justification; **`:24`** (one dgId per counterpart set *within one Design
  State*) presupposes the identity contract D-01 establishes
- `spec/RULE-PARTITION-POLICY.md` — SWRL-validator vs SHACL ownership
- `spec/API.md` — existing response envelopes
- `CLAUDE.md` § Schema Change Propagation — **mandatory** list for any structural change;
  `spec/DATABASE.md` and `ontology/dg-shapes.ttl` are both named there

### Code this phase changes (all line numbers verified 2026-09-21)
- `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs`
  - `:13-22` `RunsQuery` — **does not select `run.ValidStatus`**
  - `:65-66` `overallPass = results.All(r => r)` — run-level AND over *rules*
  - **`:73-75` `Enumerable.Repeat(overallPass, objStateCount)` — the fabrication D-14 removes**
  - `:157` `TryParseDesignState`; `:167-170` structural sniffing, **no version check** (D-07);
    `:181-190` getter-only `Collection<T>` note; `:194-223` manual `Parameters` backfill (D-09)
- `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs`
  - `:15` `Serialize`, `:23` writes `version "2"`, `:28/32/36` StateId sorts (D-08)
  - `:44` `Deserialize`, `:66-69` strict version enforcement, `:83-96` document-order append
  - `:455` `DesignStatePayloadV2Dto`; **`:472-483` `ObjStateDto` — no `Geometry`, no `ClassIri`**
  - `:296/302/308` enum lowercase wire form; `:374-398` case-insensitive parse
- `DG/src/DG.Core/Models/ObjState.cs` — `:9` `Geometry` (D-06 excludes), **`:18` `ClassIri` with
  the doc-comment naming `DesignStateBindingService` (D-05 adds)**
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — `:10-12` content-addressed intent;
  `:31-50` `ComputeParamStateId`; **`:57-61` `ComputeObjectStateId` — zero production callers**;
  `:70-88` `ComputePropStateId`; `:97-106` `ComputeDesignStateId`; `:108-112` `HashToHex16`
- **`DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:190-196`** — the private duplicate
  D-04 deletes (`:192` folds `label` into the ID)
- `DG/src/DG.Grasshopper/Components/DesignStateCompositionComponent.cs` — `:156` aggregate fold,
  `:162` `CapturedAtUtc`, `:165-170` wiring-order preservation (D-08 retires)
- `DG/src/DG.Core/Data/IValidGraphRepository.cs:5-25` — the read surface D-13 extends additively
- `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` — `:17-21` deliberate-duplication
  rationale, `:41-42` mint, `:45-49` `HashToHex16` (third hashing regime — D-02 does *not* unify)
- `data-service/app.py`
  - `:573-588` the single MERGE+`SET` mixing immutable and mutable (D-15); `:586` `ValidStatus`
    write
  - `:609-631` per-entity rows; **`:633-656` `ValidationEntity` writes**; `:790` `entityCount`;
    `:836` delete; **`:849-870` `get_validation_entity_sets` with failed-wins at `:864-869`
    (D-12 reconciles)**
  - `:744` `_project_state_summary` (partial projection only); `:923-946` `build_view_payload` —
    the DE-01 replay target, returns `objectSets` + `evidenceEnvelope`, **not** `ValidStatus`
  - `:2137` `evidenceEnvelopeJson` SET; `:2245` `shaclReportJson` SET; `:2272` `SendStatus` SET
- `data-service/cg_paramstate_store.py` — `:132` v2 envelope write; `:336` MERGE on
  `StateId`+`project` (D-01/D-03)
- `tools/de01/legs.py` — `:112` `_validated_leg_result`, `:68` `_synthesize_error_envelope`,
  **`:747` `run_leg_replay`** (envelope-only, no state hash, no per-object compare — D-16 extends)

</canonical_refs>

<code_context>
## Existing Code Insights

### The asymmetry that defines this phase

Per-object verdicts are **live end-to-end in Python** and **absent in C#**:

| Concern | Python | C# |
|---|---|---|
| Per-object write | `app.py:633-656` `ValidationEntity` | — |
| Per-object read | `app.py:849-870`, failed-wins dedup | **zero hits for `ValidationEntity`** |
| Replay payload | `build_view_payload:923-946` → `objectSets` + `evidenceEnvelope` | — |
| Run read | — | `GetRunsAsync` → fabricated `StatusList` (`:73-75`) |

So ALGN12-10 is **not** "fix an index bug in C#" — it is "build a per-object read path in C# that
did not exist", against a source (the envelope) that D-10 makes canonical.

### Three hashing regimes coexist (D-02 deliberately does not unify them)

- `DesignStateIdGenerator.HashToHex16` (`:108-112`) — SHA-256 → 16 hex, unversioned
- `DgIdMintingService.HashToHex16` (`:45-49`) — same shape, **duplication documented as
  deliberate** at `:17-21`
- `CanonicalJsonWriter.HashCanonical` (`:98`) — versioned (`CanonicalizationVersion = 1`),
  cross-language-verified

D-02 extends the third and leaves the first two alone. Unifying was considered and rejected as a
blast radius disproportionate to this phase (re-minting `dgId`s). **The planner should not
quietly unify them either** — that is a deliberate scope line, not an oversight.

### Reusable Assets
- **`DG.Core.Contracts`** (1200) — `EvidenceStatus`, `EvidenceEnvelope`,
  `EvidenceEnvelopeFactory` (incl. `RollupPrecedence`), `CanonicalJsonWriter`. This phase
  **consumes**; it defines no new status or hash primitive.
- **`data-service/evidence_contract.py`** — the Python mirror, incl. `_ROLLUP_PRECEDENCE`.
- **`ValidationEntity` write path** (`app.py:633-656`) — already produces per-`(runId, ruleId,
  dgEntityId)` rows; useful prior art for the envelope's row shape even though D-10 demotes it.
- **Sidecar JSON property pattern** — `statePayloadJson`, `shaclReportJson`,
  `evidenceEnvelopeJson`; "absence means not-recorded, never an error" (Phase 823) is exactly
  D-11's rule.
- **`fixtures/golden/parser/`** (1201 D-16) — the precedent for D-17's sibling-path fixture.
- **`tools/de01/`** — the runner D-16 extends; `_synthesize_error_envelope` (`:68`) and
  `_validated_leg_result` (`:112`) give graceful degradation for free.

### Established Patterns
- **Additive-not-breaking** — Phase 823 `shaclReportJson`, Phase 824 heartbeat, Phase 38 nullable
  `reinstateParameterId`, 1200 D-03, 1201 D-01/D-05. D-03, D-07, D-13 follow it.
- **Single-source-of-truth constants shared by prod and test** — 1201 D-15's builtin allow-list,
  Phase 35-12's `GRAMMAR_CITATION_PATTERNS`. The rollup precedence (D-12) is already such a
  constant — import it, never retype it.
- **Conditional compilation** — `#if GRASSHOPPER_SDK` guards GH code. D-04 touches
  `DG.Grasshopper` (guarded); everything else is `DG.Core` and testable from `DG.Tests`.
- **Multi-targeting** — `DG.Core` targets **net7.0 and net9.0**. No net8+-only APIs
  (`ArgumentException.ThrowIfNullOrWhiteSpace`, `JsonObjectCreationHandling.Populate` both bit
  earlier phases).

### Integration Points
- `Neo4jValidGraphRepository` — the per-object read (D-10/D-13/D-14) and reader convergence (D-09)
- `DesignStatePayloadV2Serializer` — ClassIri member (D-05), version check (D-07), sort contract
  (D-08)
- `ObjectStateComponent` + `DesignStateIdGenerator` — minting convergence (D-04); **GH rebuild**
- `data-service/app.py` publish path — `ON CREATE SET` immutability (D-15), rollup reconciliation
  (D-12)
- `tools/de01/legs.py:run_leg_replay` — exit evidence (D-16)

### Test baselines (from `1201-VERIFICATION.md:92-95`, status `passed` — not re-run this session)

| Suite | Command | Baseline |
|---|---|---|
| DG .NET | `dotnet test DG/tests/DG.Tests/ -v minimal` | **502 passed, 0 failed** |
| DE-01 runner | `python -m pytest tools/de01/tests/test_de01_runner.py -q -k "not live"` | **33 passed** |
| data-service | `python -m pytest data-service/tests -q` | **823 passed, 1 skipped, 1 failed (pre-existing)** |
| dg-reasoner | — | **36 passed, 3 failed (pre-existing)** |

**Environment caveat (known, not a regression):** up to 4 `DesignStateValidationFlowTests` fail
fast when Neo4j is down, and 4 `test_dg_context.py` tests fail from the host — the `neo4j`
hostname resolves only inside compose. **D-16's DE-01 run needs the compose stack up; plan for it
explicitly.**

**Docker caveat (bit Phase 38-06, 1200-08):** `data-service` has no source volume mount. A stale
image silently runs pre-change code — 1200-08 had to rebuild mid-plan for exactly this reason.
D-12/D-15 touch `data-service`; **rebuild before measuring.**

</code_context>

<specifics>
## Specific Ideas

- **The governing sentence, inherited from 1200 and 1201 and binding here:** *"Silent disagreement
  is a failure; a declared one is not."* D-06 (geometry) and D-11 (legacy runs) are both
  *declared* exclusions — that is what makes them acceptable rather than gaps.
- **Positional verdict matching is dead as of D-08.** `spec/DATABASE.md:112`'s index-matched
  `ValidStatus` contract cannot survive a canonical sort. Per-object verdicts are
  identity-addressed from here on. Any plan task that reaches for an index is a defect.
- **`not_evaluated` on legacy runs is the honest answer, not a regression.** Users will see
  existing runs lose canvas colors. The contract must say so plainly, because the alternative —
  inferring status from a legacy boolean — is forbidden by 1200 D-04.
- **Two disagreeing rollups exist today.** Python's failed-wins (`app.py:864-869`) puts `failed`
  above `error`; the shipped precedence puts `error` first. D-12 resolves this toward the shipped
  table, which means **a real behavior change on the Python side** — not a documentation exercise.
- **Do not trust the inherited description of the `RunsQuery` defect.** See
  `<upstream_corrections>`: the data is not read at all. A planner sizing this as a one-line fix
  will under-plan the phase.

</specifics>

<deferred>
## Deferred Ideas

| Idea | Owner | Note |
|---|---|---|
| Physical `:StateSnapshot` / `:Run` node split | Later phase (not scheduled) | D-15 takes `ON CREATE SET` + declaration; the split remains available and would need a full schema-propagation sweep plus migration |
| Unifying the three hashing regimes (`DesignStateIdGenerator`, `DgIdMintingService`, `CanonicalJsonWriter`) | Not this phase | D-02 extends only the third; `DgIdMintingService.cs:17-21` documents the duplication as deliberate. Re-minting `dgId`s is 1203-adjacent blast radius |
| Serializing geometry / floating-point canonicalization rules | Not this phase | D-06 formally excludes; adding it later is additive |
| Python symmetric full-DesignState reader | Not this phase | Python only *projects* (`app.py:744`) and *writes* (`cg_paramstate_store.py:132`); no consumer needs full reconstruction yet |
| Backfilling `canonicalStateHash` onto historical states | Not this phase | D-03 is additive-no-rewrite; historical payloads may predate v2 and lack the members the hash needs |
| `ATTRIBUTE_OF` vs `PARAM_LINK` | **1203** | Milestone D8 / open question #1 |
| Identity authority across GH/Revit/IFC/Speckle; conflict/detach/provenance policy | **1203** | Open question #7; ALGN12-12/13. D-04 converges *minting*, not cross-platform *authority* |
| LLM reproducibility / provider snapshots | **1204** | Open question #10 |
| Authorization, project isolation, direct-proxy exposure | **1205** | Open question #9 |
| Full envelope propagation across the `CLAUDE.md` schema list | **v11.0 1105** | 1200 owns definition, 1105 owns propagation — coordinate, do not duplicate |
| `ComputGraph` structural-trace vs executable Behaviour/FBS semantics; five-layer model | **v11.0 1106** | Open questions #6 and #8 — explicitly not v12.0 |
| F-39-01 (auto-runs SHACL-validated before their own `ValidStatus` is written) | Not this phase | Pre-existing disclosed finding; the contract may describe it, fixing it is out of scope |
| `:ValidationRun` / `:Run` label and `Run_Id`/`runId` drift | Not this phase | Documented in `spec/DATABASE.md:111`; note, do not fix |
| Unapproved `migrations/2026-07-07_validationgraph_to_validgraph.cypher` | Not this phase | Pre-existing; D-03 deliberately avoids adding a second migration |
| Live Rhino/LLM/Speckle UAT | **v9.0 Phase 40** | GATE12-04 — v12.0 cannot mark these passed |

</deferred>

---

*Phase: 1202-Design State Replay and Per-Object Verdict Closure*
*Context gathered: 2026-09-21*
