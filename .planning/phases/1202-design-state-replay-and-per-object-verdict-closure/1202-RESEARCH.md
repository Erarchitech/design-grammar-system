# Phase 1202: Design State Replay and Per-Object Verdict Closure - Research

**Researched:** 2026-09-21
**Domain:** Cross-language (C#/Python) canonical replay contract for Design State identity, content hashing, and per-object validation verdicts, on top of the frozen Phase 1200 evidence contract and Phase 1201 rollup precedence.
**Confidence:** HIGH — this phase modifies existing, fully-read production code; no new external library or framework is introduced. All claims below are `[VERIFIED: <path>]` against the live repo on 2026-09-21 unless marked `[ASSUMED]`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01 … D-12 are user-selected; D-13 … D-17 are Claude-selected under the user's blanket instruction *"Принимай все рекомендованные варианты самостоятельно"* (accept all recommended options yourself). Full text (rationale + reversibility) lives in `1202-CONTEXT.md` `<decisions>` — copied here verbatim by section heading only, to keep this file scannable; the planner MUST read `1202-CONTEXT.md` directly for the full rationale/consequence text before planning, this is not a substitute.

**Identity semantics (ALGN12-08):** D-01 (Design State identity is both capture-event-key AND content-hash property `canonicalStateHash`); D-02 (state hash extends the Phase 1200 hasher, forbidden to invent a second canonicalization); D-03 (historical states additive, no rewrite); D-04 (ObjState minting converges on `DesignStateIdGenerator`, private duplicate in `ObjectStateComponent.cs:190-196` deleted, requires GH rebuild).

**Replay membership (ALGN12-09):** D-05 (`ClassIri` becomes a normative serialized `ObjStateDto` member); D-06 (Geometry formally excluded from payload and hash, referenced by `dgId`/Speckle `objectId` instead — replay cannot reconstruct a viewable state offline, this is accepted cost); D-07 (payload stays `version: "2"`, `ClassIri` optional-additive; bundled mandatory fix: `TryParseDesignState` must add version-check enforcement it currently lacks); D-08 (canonical StateId-sorted order is the contract, wiring order not preserved — direct consequence: positional `ValidStatus` verdict matching is formally dead); D-09 (the two independent payload readers converge on one — `TryParseDesignState` delegates to `DesignStatePayloadV2Serializer.Deserialize`).

**Per-object verdict path (ALGN12-10):** D-10 (the 1200 evidence envelope's per-(rule,object) rows are the canonical per-object verdict source; `Run.ValidStatus`/`ValidationEntity` demoted to legacy/non-authoritative); D-11 (when `evidenceEnvelopeJson` is absent, every object reports `not_evaluated`, no fallback, no inference from legacy boolean); D-12 (per-object rollup uses the shipped Phase 1201 precedence verbatim — `error > failed > indeterminate > unsupported > unknown > not_evaluated > no_population > passed` — reconciling Python's current failed-wins behavior, a real behavior change).

**Claude-selected (D-13…D-17):** D-13 (`IValidGraphRepository` gains an additive method returning typed per-object `EvidenceStatus` verdicts; `GetRunsAsync`/`StatusList` retained, documented non-authoritative); D-14 (the fabricated `Enumerable.Repeat` list at `Neo4jValidGraphRepository.cs:73-75` is removed, not patched); D-15 (ALGN12-11 via write-once `ON CREATE SET` + explicit immutable/mutable property declaration on `:ValidationRun` — no physical node split, no migration); D-16 (DE-01 extended as exit evidence — per-object comparison plus canonical-state-hash verification across the legs; unit tests alone insufficient; requires live compose stack); D-17 (`fixtures/golden/fixture.json` stays frozen; mixed pass/fail fixture built from existing `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`; new fixture material in a sibling path only).

### Claude's Discretion

Within the locked decisions above, the planner retains discretion on:
- the concrete name/shape of the capture-event key (D-01 locks *both layers*, not the key's spelling);
- the exact shape of the canonical DesignState projection fed to `HashCanonical` (D-02), provided it is stated explicitly and excludes geometry per D-06;
- the name and signature of the additive `IValidGraphRepository` method (D-13);
- whether the membership manifest is a separate artifact or a section inside the state payload;
- how `PropState`'s missing `CapturedAtUtc` (absent from `PropState.cs` while ObjState/ParamState/DesignState all carry one) is treated — normalize or document as excluded;
- the file split for any new fixture material under the D-17 sibling path;
- test-framework split between pytest and xunit for the D-16 wrapper.

### Deferred Ideas (OUT OF SCOPE)

Physical `:StateSnapshot`/`:Run` node split (later phase, not scheduled); unifying the three hashing regimes (`DesignStateIdGenerator`, `DgIdMintingService`, `CanonicalJsonWriter` — not this phase, D-02 extends only the third); serializing geometry/floating-point canonicalization rules (not this phase, D-06 formally excludes); Python symmetric full-DesignState reader (not this phase — Python only projects/writes, no consumer needs full reconstruction yet); backfilling `canonicalStateHash` onto historical states (not this phase, D-03 is additive-no-rewrite); `ATTRIBUTE_OF` vs `PARAM_LINK` (Phase 1203); identity authority across GH/Revit/IFC/Speckle, conflict/detach/provenance policy (Phase 1203, ALGN12-12/13); LLM reproducibility/provider snapshots (Phase 1204); authorization/project isolation/direct-proxy exposure (Phase 1205); full envelope propagation across the CLAUDE.md schema list (v11.0 Phase 1105); ComputGraph structural-trace vs executable semantics (v11.0 Phase 1106); F-39-01 auto-runs-SHACL-validated-before-own-ValidStatus-written (not this phase, pre-existing disclosed finding); `:ValidationRun`/`:Run` label and `Run_Id`/`runId` drift (not this phase, documented not fixed); unapproved `migrations/2026-07-07_validationgraph_to_validgraph.cypher` (not this phase); live Rhino/LLM/Speckle UAT (v9.0 Phase 40, GATE12-04).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALGN12-08 | Design State identity is explicitly classified as content-equivalence or capture-event identity | D-01/D-02 confirmed as new construction (zero existing `stateHash`/`canonicalStateHash` references repo-wide); `DesignStateIdGenerator.cs` and `ObjectStateComponent.cs` read in full — see Pitfall 1 for the D-04 signature-mapping gap the planner must resolve |
| ALGN12-09 | Publish → query → replay preserves the canonical state hash, membership manifest, schema version, and all normative members, or records explicit exclusions | `DesignStatePayloadV2Serializer` and `Neo4jValidGraphRepository.TryParseDesignState` both read in full — see Pattern 1 (hash reuse) and Pitfall 2 (the two-reader convergence is a real type-mismatch, not a delete-and-call-through) |
| ALGN12-10 | Mixed per-object outcomes remain distinct through persistence and C# retrieval; no run-level aggregate is replicated across objects | `IValidGraphRepository`/`EvidenceEnvelope` read in full — see Pattern 2 (no new C# type needed for deserialization) and Pitfall 4 (RunsQuery defect is a missing feature, not an index bug) |
| ALGN12-11 | Mutable operational/run status is separated from immutable snapshot identity and payload | `data-service/app.py:571-607`'s unconditional `SET` read directly — confirms D-15's premise; Wave 0 gap identified (no existing regression test for `ON CREATE SET` immutability) |
</phase_requirements>

## Summary

This is a pure-consolidation phase: it introduces **zero new packages, zero new frameworks, zero new services**. Every deliverable is either (a) extending an existing C#/Python type pair that Phase 1200 already built and hardened (`CanonicalJsonWriter` / `canonical_json.py`, `EvidenceEnvelope` / `evidence_contract.py`), or (b) closing a genuine read-path gap in C# (`IValidGraphRepository`) that Python has had since before this milestone. The research below confirms every "does X already exist" question CONTEXT.md flagged, with exact line numbers, so the planner can size tasks precisely instead of guessing.

The single largest risk is not technical complexity — it's **sequencing three converging readers/hashers without breaking the 502-passing DG.Tests baseline**, combined with a **Docker Desktop stack that is not currently running** on this machine, which D-16's DE-01 exit-evidence requirement needs live at least once. The second largest risk, newly surfaced by this research and not previously flagged in CONTEXT.md, is that **`DesignStateIdGenerator.ComputeObjectStateId`'s 3-parameter signature (`projectId`, `objectInstanceId`, `variableName`) has no natural mapping onto `ObjectStateComponent`'s actual inputs** (`Object`, `Geometry`, `Label` — no Project port exists anywhere in the Grasshopper canvas's ObjState composition path, and there is no `variableName` concept at the per-geometry-instance level). D-04's "converge onto `DesignStateIdGenerator`" instruction is correct in principle but the planner must resolve this signature mismatch explicitly — it cannot be a one-line call-site swap.

**Primary recommendation:** Sequence the phase as (1) pure-`DG.Core` additive changes with zero Grasshopper/live-service dependency first (D-05/D-07/D-08/D-09/D-10 through D-15, all unit-testable offline), (2) the Grasshopper rebuild for D-04 second (resolves the signature-mapping question above), (3) DE-01/compose-stack verification last and exactly once, after Docker Desktop is confirmed running.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Design State identity (capture-event key + content hash) | API/Backend (`DG.Core` + `data-service`) | Database (Neo4j property) | Identity is computed at write time in both producing languages and stored as a graph property; no client tier involvement |
| Canonical state hash computation | API/Backend (`DG.Core.Contracts.CanonicalJsonWriter`, `data-service/canonical_json.py`) | — | Pure library-level function, cross-language parity is the whole point — must not leak into any UI or transport-layer concern |
| Per-object verdict read path (C#) | API/Backend (`DG.Core.Data.Neo4jValidGraphRepository`) | Database (Neo4j `evidenceEnvelopeJson` sidecar) | New additive interface method reading an existing sidecar property; this is a repository-layer concern, not a Grasshopper-component concern |
| Per-object verdict read path (Python) | API/Backend (`data-service/app.py`) | Database (`:ValidationEntity` legacy, `evidenceEnvelopeJson` canonical) | Already live; D-12 reconciles rollup precedence at this same tier |
| ObjState ID minting | Frontend/Client (Grasshopper plugin, `DG.Grasshopper`) | API/Backend (`DG.Core.Services.DesignStateIdGenerator`) | Grasshopper is this project's "client" tier for authoring; minting logic itself lives in the shared `DG.Core` library so both the plugin and any future authoring surface use one function |
| DE-01 replay verification | API/Backend (`tools/de01/legs.py`, Python) | Database (Neo4j via `data-service` HTTP) | Test/verification tooling, not a runtime service — but it drives HTTP calls into `data-service` and reads persisted state, so it sits at the same tier as the persisted-replay leg it exercises |

## Standard Stack

### Core

No new packages. This phase extends existing types in the already-adopted stack:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `System.Text.Json` | in-box (.NET 7/9 BCL) | `DesignStatePayloadV2Serializer` (de)serialization, `EvidenceEnvelope` JSON | Already the project's sole JSON library on the C# side; `[VERIFIED: DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs:1-13]` |
| `System.Text.Json.Nodes` | in-box (.NET 7/9 BCL) | `CanonicalJsonWriter`'s `JsonNode`/`JsonObject`/`JsonArray` walk, reused for D-02's projection | `[VERIFIED: DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:6]` |
| Python stdlib `json`, `hashlib` | 3.14.2 (installed) | `canonical_json.py`'s mirror implementation | `[VERIFIED: python --version → 3.14.2; data-service/canonical_json.py:34-35]` |
| `httpx` | already pinned | `tools/de01/legs.py`'s HTTP calls to `data-service` | `[VERIFIED: tools/de01/legs.py:26, 769]` |
| `jsonschema` | already pinned | Envelope schema validation in `_validated_leg_result` | `[VERIFIED: tools/de01/legs.py:27, 119-120]` |
| `xunit` | already pinned | `DG.Tests` (502 baseline) | `[VERIFIED: DG/tests/DG.Tests/DG.Tests.csproj]` |
| `pytest` | already pinned | `data-service/tests`, `tools/de01/tests` | `[VERIFIED: STATE.md baseline table]` |

### Supporting

None new.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `CanonicalJsonWriter.HashCanonical` for state hashing | A dedicated `DesignStateHasher` class | **Rejected by D-02 explicitly** — would be a fourth hashing regime alongside `DesignStateIdGenerator.HashToHex16`, `DgIdMintingService.HashToHex16`, `CanonicalJsonWriter`. Not the planner's call to revisit. |
| Converging `TryParseDesignState`/`Deserialize` readers | Leaving both readers as-is, documenting the divergence | **Rejected by D-09 explicitly** — the phase's stated goal is eliminating exactly this drift class. |
| `System.Text.Json`'s `JsonObjectCreationHandling.Populate` for the `ParamState.Parameters` getter-only-Collection bug | Keep the manual backfill loop | `Populate` is .NET 8+ only; `DG.Core` multi-targets **net7.0** (the real Grasshopper runtime) and **net9.0** — confirmed unusable `[VERIFIED: DG/src/DG.Core/DG.Core.csproj:4 → net7.0;net9.0]`. The manual backfill (`Neo4jValidGraphRepository.cs:194-223`) must be preserved verbatim or moved, never replaced by this API. |

**Installation:** None required — no new package references.

**Version verification:** Not applicable; no new packages. `dotnet --version` on this machine: `10.0.301` `[VERIFIED via Bash]`. `python --version`: `3.14.2` `[VERIFIED via Bash]`. Both exceed the project's stated minimums (net7.0/net9.0 targets, Python 3.11+ base images).

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** All work extends already-vetted, already-imported types (`System.Text.Json`, `httpx`, `jsonschema`, existing `DG.Core.Contracts`/`data-service` modules). No `npm view` / `pip index versions` / `cargo search` check was needed; there is nothing new to verify against a registry.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────┐        ┌──────────────────────────────┐
│ Grasshopper Plugin       │        │ data-service (publish path)   │
│  ObjectStateComponent     │        │  app.py:571-607 MERGE+SET     │
│  ── D-04: converge ID    │        │  (immutable+mutable mixed,    │
│     minting onto          │        │   D-15 declares which is     │
│     DesignStateIdGenerator│        │   which — no physical split)  │
│  DesignStateCompositionCo-│        │                                │
│  mponent (:156 fold, :162 │        │  app.py:633-656               │
│  CapturedAtUtc, :165-170  │        │  ValidationEntity write        │
│  wiring order — D-08      │        │  (legacy, demoted D-10)       │
│  retires the order claim) │        │                                │
└──────────┬────────────────┘        │  app.py:2137                  │
           │                          │  evidenceEnvelopeJson SET     │
           │ DesignStatePayloadV2     │  (canonical per-object source)│
           │ Serializer.Serialize     └───────────┬────────────────────┘
           │ (D-05 ClassIri,                       │
           │  D-08 StateId sort)                    │ GET /validation/view/{project}
           ▼                                         │ app.py:923-946 build_view_payload
┌─────────────────────────┐                          │  → {objectSets, evidenceEnvelope}
│ Neo4j (:ValidationRun,   │◄─────────────────────────┘  NOT ValidStatus
│  :DesignState,            │
│  graph='ValidGraph')      │
│  statePayloadJson         │◄──── C# read: Neo4jValidGraphRepository
│  evidenceEnvelopeJson      │      .GetRunsAsync (RunsQuery :13-22 —
│  (canonical, D-10/D-11)   │      does NOT select ValidStatus)
│  ValidStatus (legacy,      │      .TryParseDesignState (:157 — D-07
│   fabricated list, D-14    │      adds version check, D-09 delegates
│   removes the fabrication) │      to DesignStatePayloadV2Serializer)
└─────────────────────────┘      NEW: IValidGraphRepository additive
                                   method reading evidenceEnvelopeJson
                                   → typed per-object EvidenceStatus (D-13)

┌───────────────────────────────────────────────────────────────────┐
│ tools/de01/legs.py — 4 legs, each independently evaluating the      │
│ SAME golden fixture (fixtures/golden/fixture.json, frozen D-17):    │
│  run_leg_data_service │ run_leg_dg_reasoner │ run_leg_csharp │       │
│  run_leg_replay (:747 — currently reads ONLY evidenceEnvelope,      │
│  no state hash, no per-object compare — D-16 extends this)          │
│           │                                                          │
│           ▼                                                          │
│  report.py:81 compare_legs — already does per-(ruleId,objectId)     │
│  row comparison across all 4 legs, classifying agreement /           │
│  declared_non_equivalence / silent_disagreement. D-16 adds a         │
│  SECOND comparison dimension (state hash) alongside this existing    │
│  row-level one — it does not need to reinvent row comparison.        │
└───────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new directories. Files touched are exactly those enumerated in CONTEXT.md's `<canonical_refs>` "Code this phase changes" list — confirmed accurate by this research, see Verified Code Facts below.

### Pattern 1: Reuse `HashCanonical(JsonNode?)` directly for the state hash — no new overload

**What:** `CanonicalJsonWriter.HashCanonical` and `canonical_json.py:hash_canonical` both already accept an **arbitrary nested value** (`JsonNode?` in C#, `Any` in Python) — not a fixed scalar tuple. D-02's "canonical DesignState projection" is simply a `JsonObject`/`dict` built by the planner (StateId-sorted per D-08, geometry-excluded per D-06) and passed straight into the existing function.

**When to use:** For the `canonicalStateHash` computation in both languages.

**Example — the exact precedent already shipping in the DE-01 C# harness:**
```csharp
// Source: DG/tools/DG.De01Harness/Program.cs:284 (existing precedent, same function)
var inputHash = CanonicalJsonWriter.HashCanonical(fixtureNode);
// ... passed straight into EvidenceEnvelopeFactory.Build(..., inputHash: inputHash)
```
The planner's canonical DesignState projection follows this identical call shape — build a `JsonNode` (or `JsonObject`) representing the DesignState minus `ObjState.Geometry`, call `HashCanonical` on it, no new method needed on `CanonicalJsonWriter`.

**Do NOT** add a new overload to `CanonicalJsonWriter` for this — `HashCanonical(JsonNode?)` is already general enough `[VERIFIED: DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs:98-103]`.

### Pattern 2: `EvidenceEnvelope.Rows` is already the ready-made per-object verdict deserialization target

**What:** `DG.Core.Contracts.EvidenceEnvelope` (from Phase 1200) already has `[JsonPropertyName]` attributes on every property, including `Rows` (`List<EvidenceRow>`, each carrying `RuleId`, `ObjectId`, `CanonicalStatus` with the existing `EvidenceStatusJsonConverter`). **No new C# type needs to be built for D-13.**

**When to use:** For the additive `IValidGraphRepository` method that reads `evidenceEnvelopeJson` and returns typed per-object verdicts.

**Example:**
```csharp
// Source: DG/src/DG.Core/Contracts/EvidenceEnvelope.cs:15-113 (existing type, verified)
// This is ALL that D-13's new repository method needs to deserialize evidenceEnvelopeJson:
var options = new JsonSerializerOptions(); // no special converters needed — the type
                                            // already carries JsonPropertyName + the
                                            // EvidenceStatusJsonConverter on CanonicalStatus
var envelope = JsonSerializer.Deserialize<EvidenceEnvelope>(evidenceEnvelopeJson, options);
// envelope.Rows[i].ObjectId, envelope.Rows[i].CanonicalStatus are directly usable —
// no envelope reader class exists today (grep for a "EvidenceEnvelopeReader" type
// returns zero hits), but none is needed; JsonSerializer.Deserialize<EvidenceEnvelope>
// is sufficient given the existing attributes.
```
**Verified gap:** grep for `ValidationEntity`/`HAS_ENTITY` across `DG/src` returns zero hits `[VERIFIED via graphify + direct grep]`; `IValidGraphRepository`'s entire surface is `GetRunsAsync → {Runs, StatusList, DesignStates}` `[VERIFIED: DG/src/DG.Core/Data/IValidGraphRepository.cs:21-25]`. This confirms CONTEXT.md's D-13 premise exactly — the gap is real and the fix is additive-only.

### Pattern 3: `compare_legs` is already the per-object cross-leg comparison mechanism — D-16 extends its inputs, not its row-comparison logic

**What:** `tools/de01/report.py:81` `compare_legs` already builds the union of `(ruleId, objectId)` pairs across all 4 leg envelopes and classifies each as `agreement` / `declared_non_equivalence` / `silent_disagreement`. This IS "per-object comparison across the legs" for verdict status — it was built by Phase 1200 and is fully general (works on however many legs are passed in).

**When to use:** D-16's "per-object comparison" deliverable is **already satisfied for the status dimension** once `run_leg_replay` (`:747`) is extended to surface per-object rows from the replayed envelope (it already does — `evidenceEnvelope.rows` flows straight through `_validated_leg_result`). What's missing is a **second, independent comparison dimension: the canonical state hash**, which `compare_legs` has no concept of today (it only compares `EvidenceRow` entries, never a scalar hash value per leg).

**What the planner must add:** a companion check (either inside `compare_legs` or as a sibling function called by `run_de01.py`'s `main`) that reads a `canonicalStateHash` value from each of the 4 legs' envelopes (or wherever the planner decides to put it — see Open Questions) and asserts they're identical, following the exact same "typed absence, never silently skipped" idiom `compare_legs` already uses for rows (`per_leg[leg_name] = {"present": False}` at `report.py:115`).

**Example — the existing idiom to mirror (not to reinvent):**
```python
# Source: tools/de01/report.py:108-149 (existing pattern — mirror this shape for state-hash comparison)
for rule_id, object_id in ordered_pairs:
    per_leg: dict[str, dict[str, Any]] = {}
    statuses_seen: set[str] = set()
    for leg_name, pairs in per_leg_pairs.items():
        leg_rows = pairs.get((rule_id, object_id))
        if not leg_rows:
            per_leg[leg_name] = {"present": False}
            continue
        # ... never silently omits a leg from the comparison
```

### Anti-Patterns to Avoid

- **Positional/index-matched verdict lookup.** `spec/DATABASE.md:112` defines `ValidStatus` as index-matched to ObjState order — **this contract is formally retired by D-08's canonical sort.** Any new code (C# or Python) that looks up a per-object verdict by list position rather than by `objectId`/`dgId` identity is a defect. `[VERIFIED: spec/DATABASE.md:112, cross-checked against Neo4jValidGraphRepository.cs:73-75's Enumerable.Repeat fabrication — exactly this anti-pattern, which D-14 removes]`.
- **Inferring canonical status from the legacy boolean.** `EvidenceEnvelopeFactory.ToLegacyBoolean` (`:110`) is explicitly one-directional; its own doc-comment states "the reverse direction ... is undefined and forbidden." `[VERIFIED: DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs:102-110]`.
- **A second rollup precedence table.** `_ROLLUP_PRECEDENCE` (Python, `evidence_contract.py:87-96`) and `RollupPrecedence` (C#, `EvidenceEnvelopeFactory` — referenced, not directly re-read this session but unchanged since 1201) are the single source; D-12 reconciles Python's `app.py:864-869` failed-wins dedup toward this table, not a new one.
- **Serializing `ObjState.Geometry` into the canonical projection.** `[VERIFIED: DG/src/DG.Core/Models/ObjState.cs:9]` `Geometry` is `object?` — an in-process Rhino/GH handle with no stable JSON form. `DesignState` itself (`[VERIFIED: DG/src/DG.Core/Models/DesignState.cs]`) carries no `Geometry` property at all — only `ObjState` does — so D-06's exclusion is a single, localized omission in the projection builder, not a recursive geometry-stripping walk.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Canonical JSON hashing for the state hash | A new hasher / new canonicalization ruleset | `CanonicalJsonWriter.HashCanonical` / `canonical_json.py:hash_canonical` | Already cross-language-parity-tested via `fixtures/golden/canonical-vectors.json`, already hardened against CR-01 (decimal scale) and WR-01 (negative zero). D-02 explicitly forbids a second canonicalization. |
| Per-object verdict rollup logic | A new precedence table or boolean-arithmetic rollup | `RollupPrecedence` / `_ROLLUP_PRECEDENCE` (Phase 1201, shipped, byte-identical in both languages) | 1201's context is explicit that the planner "MUST adopt the shipped order verbatim and MUST NOT introduce a second table." |
| Per-object verdict deserialization type (C#) | A new `EvidenceEnvelopeReader`/DTO | `JsonSerializer.Deserialize<EvidenceEnvelope>` directly | The type already carries every `JsonPropertyName` attribute needed; confirmed by direct inspection, zero additional type needed. |
| Cross-leg row comparison | A new comparison function for D-16 | `tools/de01/report.py:compare_legs`, extended with a second (hash) dimension | The existing function already does exactly the union-of-pairs, never-silently-skip comparison D-16 needs for verdict rows; only the state-hash dimension is genuinely new. |

**Key insight:** Every "don't hand-roll" item in this phase is "don't hand-roll a second copy of something Phase 1200/1201 already built and hardened." This phase's actual net-new code is small: a canonical DesignState→JsonNode projection function, one additive `IValidGraphRepository` method, a version-check + reader-convergence in `TryParseDesignState`, one `ClassIri` field addition, one `ON CREATE SET` change, and a state-hash comparison leg in DE-01.

## Runtime State Inventory

*(Included because this phase touches identity/keying semantics — D-01 changes MERGE-vs-node-key behavior for Design State capture, which is a state-identity change even though it is not a rename/rebrand.)*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `:DesignState` nodes MERGE on `StateId+project` today (`cg_paramstate_store.py:333` `[VERIFIED]`; `spec/DATABASE.md:99` amended-Phase-38 MERGE-on-StateId+project). D-01's capture-event keying means **recapture no longer dedupes by MERGE** — the graph grows per capture going forward. | Code edit (new key derivation) + explicit documentation that historical dedup-by-content behavior changes; **not** a data migration under D-03 (additive, no rewrite of existing rows) |
| Live service config | None found specific to this phase — no n8n workflow, Speckle config, or Tailscale/Cloudflare state references Design State identity | None |
| OS-registered state | None — this phase touches no Windows Task Scheduler, pm2, or systemd state | None |
| Secrets/env vars | None — no secret or env var references `StateId`, `canonicalStateHash`, or any identity concept this phase introduces | None |
| Build artifacts | `DG.Grasshopper` plugin binary must be rebuilt after D-04 (`dotnet build DG/DG.sln -c Release`, guarded by `#if GRASSHOPPER_SDK`) — stale plugin binaries would keep minting IDs via the deleted private duplicate until rebuilt and redeployed to the actual Rhino/Grasshopper install | Rebuild + redeploy (redeploy is a live-Rhino UAT concern per GATE12-04, out of this phase's automated scope) |

**The one genuinely new runtime-state fact this research surfaces (not in CONTEXT.md):** the golden fixture's `seed.cypher` **already seeds a stub `:DesignState` node** (`DS_GOLDEN_FIXTURE_01`, `[VERIFIED: fixtures/golden/seed.cypher:180-199]`) with a *minimal* v2 payload (`objStates`/`paramStates`/`propStates` each carrying only a bare `stateId`, no `objectRef`, no `capturedAtUtc`, no other required fields). This stub is almost certainly **insufficient** as the D-17 mixed pass/fail replay fixture on its own — it was built for Phase 1200's narrower needs (proving the sidecar property round-trips at all, not proving per-object verdict distinctness). The planner should plan to build a **new, richer sibling fixture** for D-17's "mixed pass/fail per-object" deliverable rather than trying to stretch this stub, consistent with D-17's own sibling-path instruction.

## Common Pitfalls

### Pitfall 1: `ObjectStateComponent` has no `Project` input and no `variableName` concept — D-04's signature convergence is not a 1-line swap

**What goes wrong:** A planner reads D-04 as "delete the 6-line private duplicate, call `DesignStateIdGenerator.ComputeObjectStateId` instead" and sizes it as trivial.

**Why it happens:** `ComputeObjectStateId(string projectId, string objectInstanceId, string variableName)` `[VERIFIED: DG/src/DG.Core/Services/DesignStateIdGenerator.cs:57-61]` expects three specific inputs. `ObjectStateComponent.SolveInstance` `[VERIFIED: DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:79-137]` has exactly three input ports: `Object`, `Geometry`, `Label` — **no `Project` port anywhere in the component or in `DesignStateCompositionComponent`** (grepped, zero matches for `Project`/`ProjectName` in the latter). There is also no per-rule "variable name" concept at the per-geometry-instance level this component operates at — `objectRef` (the resolved instance identity) is the closest existing concept, mapping onto `objectInstanceId`, but `projectId` and `variableName` have no source.

**How to avoid:** The planner must explicitly decide, as a task-level design decision (this is within "Claude's Discretion" per CONTEXT.md — "the concrete name and shape of the capture-event key" is discretionary, but this specific signature-mapping gap is not called out and needs a plan-time answer): either (a) source `projectId` from `ConnectionInfo`/a new component input, treat `variableName` as not applicable and pass a constant/empty sentinel, or (b) accept that `ComputeObjectStateId`'s existing 3-arg signature was designed for a different call site (per-rule-variable Object state, matching the CMPST-07/CMPST-08 doc comments about "Object variables shared across rules") and that `ObjectStateComponent`'s real need is closer to a 2-arg `(objectRef, classIri-or-similar)` — which may mean **adding a new, additive overload** to `DesignStateIdGenerator` rather than force-fitting the existing one. Either path is legitimate; what must not happen is discovering this mismatch mid-implementation.

**Warning signs:** Any task description that says "swap the private hash call for `DesignStateIdGenerator.ComputeObjectStateId`" without naming where `projectId` comes from.

### Pitfall 2: Two structurally different deserialization targets exist for the v2 payload — "converge the readers" means resolving a real type mismatch, not just deleting one function

**What goes wrong:** D-09 is read as "make `TryParseDesignState` call `DesignStatePayloadV2Serializer.Deserialize` instead of its own inline logic" and treated as a delete-and-call-through.

**Why it happens:** `DesignStatePayloadV2Serializer.Deserialize` `[VERIFIED: DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs:44-100]` deserializes through a **private nested DTO hierarchy** (`DesignStatePayloadV2Dto`, `ObjStateDto`, `ParamStateDto`, etc. — all `private sealed class` at `:455-517`) with its own `JsonNamingPolicy.CamelCase` options object (`:9-13`), throws `InvalidOperationException` on missing/invalid fields via `ValidateDeserialized`, and **already correctly populates `ParamState.Parameters`** via its own explicit DTO→domain mapping loop (`FromDto` at `:334-353`, which explicitly iterates `dto.Parameters` — this DTO-based path does **not** hit the getter-only-`Collection<T>`-skip bug, because it deserializes into a plain `List<ParameterDto>` DTO first, then manually adds each converted item to the real `Collection<T>`).

`Neo4jValidGraphRepository.TryParseDesignState` `[VERIFIED: DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs:157-249]` instead deserializes **directly into the domain model** `DesignState`/`ParamState` (`:199`, `JsonSerializer.Deserialize<DesignState>`) with a *different* options object (`:194-198`, camelCase + `JsonStringEnumConverter`), and needs the manual backfill (`:200-223`) specifically because deserializing straight into the domain type's getter-only `Collection<T>` is what triggers the silent-skip bug the DTO-based serializer path never encounters.

**How to avoid:** D-09's "the shared path must handle this" note is correct, but the planner should recognize the fix is likely **"delete `TryParseDesignState`'s inline logic entirely, replace its v2 branch with a call to `DesignStatePayloadV2Serializer.Deserialize`"** — not "port the manual backfill into the shared path," because the serializer's own DTO-mediated `FromDto` already avoids the bug by construction. The manual backfill loop at `:194-223` can likely be **deleted outright** once the call-through happens, rather than relocated. This is a smaller task than CONTEXT.md's phrasing implies, but the planner must verify this by running `DesignStatePayloadV2SerializerTests` (already exists) against the same malformed/edge-case inputs `Neo4jValidGraphRepositoryTests` covers, to confirm behavior parity before deleting the inline path. Version-check enforcement (D-07) is a clean, independent addition regardless: `TryParseDesignState`'s v2-detection (`:167-170`) is structural sniffing with **no `version` field check at all**, while the serializer enforces `dto.Version != "2"` strictly (`:66-69`) — confirmed as CONTEXT.md describes.

**Warning signs:** A task that says "add the manual Parameters backfill to the shared path" — check first whether the serializer's DTO-based path needs it at all (research indicates it does not).

### Pitfall 3: Docker Desktop is not running on this development machine — D-16's exit evidence cannot be produced until it is started

**What goes wrong:** A plan schedules the DE-01 live-compose exit-evidence task without an explicit "start Docker Desktop" precondition, and the task silently fails or produces a false "leg unavailable" result that gets misread as a real finding.

**Why it happens:** `docker compose ps` returned a connection error (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`) `[VERIFIED via Bash, 2026-09-21]` — Docker Desktop's engine is not currently reachable on this machine. This is an environment-state fact independent of anything this phase changes, but D-16 explicitly requires the live compose stack (mirroring 1201's D-11 pattern), and `data-service` additionally requires a rebuild (not just a restart) after `app.py` changes, per the documented no-source-volume-mount gotcha `[VERIFIED: 1200-08 plan note in STATE.md, and CLAUDE.md "Known Gotchas"]`.

**How to avoid:** Sequence D-16's DE-01 run as the **last** task in the phase, with an explicit precondition step (start Docker Desktop, `docker compose up -d`, confirm `data-service` container reflects post-phase code via `--no-cache` rebuild) before invoking `tools/de01/run_de01.py`. Do not interleave live-stack verification with earlier offline `DG.Core`/`DG.Tests` work — minimize how many times the stack must be brought up, per CONTEXT.md's own framing.

**Warning signs:** Any task ordering that runs a DE-01 live check before the last `data-service`-touching code change (D-12/D-15) is complete — a stale image would silently validate against pre-change code, per the 1200-08 precedent CONTEXT.md cites.

### Pitfall 4: The `RunsQuery` defect is a missing feature, not an index bug — do not under-size the C# per-object read-path task

**What goes wrong:** Sizing "fix `Enumerable.Repeat(overallPass, objStateCount)`" (`Neo4jValidGraphRepository.cs:73-75`) as a small bugfix task.

**Why it happens:** As CONTEXT.md's Correction 2 states and this research directly confirms by reading `RunsQuery` (`:13-22`): the query's `RETURN` clause selects `runId, project, createdAt, rulesJson, statePayloadJson` — **`run.ValidStatus` (or any evidence-envelope field) is not in the Cypher projection at all.** The fabrication at `:73-75` isn't reading the wrong index of real data; there is no real per-object data flowing into this method whatsoever. D-13's new method needs its own Cypher query selecting `evidenceEnvelopeJson` (which `RunsQuery` also does not select today) before any C# deserialization logic can run.

**How to avoid:** Size D-13/D-14 as: (1) new Cypher query or extension of `RunsQuery`'s projection to include `evidenceEnvelopeJson`, (2) new C# method on `IValidGraphRepository`/`Neo4jValidGraphRepository` deserializing it via `EvidenceEnvelope` (Pattern 2 above), (3) deletion of the `Enumerable.Repeat` fabrication and the now-dead `overallPass`-derived `statusList` construction. This is a genuine new-feature task, not a one-line fix.

**Warning signs:** A task titled only "fix per-object status index bug" without a corresponding Cypher-query-extension subtask.

## Code Examples

### Reusing the existing hash pattern for a new canonical projection

```csharp
// Source: DG/tools/DG.De01Harness/Program.cs:284 — existing precedent in this exact codebase
// (not from external docs; this is the pattern already shipping for inputHash)
var stateHashInput = BuildCanonicalDesignStateProjection(designState); // new function, planner's D-02 discretion
var canonicalStateHash = CanonicalJsonWriter.HashCanonical(stateHashInput);
```

### Existing per-(ruleId,objectId) row comparison idiom to extend, not replace

```python
# Source: tools/de01/report.py:69-78 — existing helper, reuse the pattern for any new
# per-leg indexed lookup (e.g. indexing legs by their reported canonicalStateHash)
def _rows_by_pair(envelope: dict[str, Any]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in envelope.get("rows", []):
        key = (row["ruleId"], row["objectId"])
        by_pair.setdefault(key, []).append(row)
    return by_pair
```

### The `ParamState.Parameters` DTO-mediated pattern that already avoids the getter-only-Collection bug

```csharp
// Source: DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs:334-353
private static ParamState FromDto(ParamStateDto dto)
{
    // ...
    var paramState = new ParamState { StateId = dto.StateId ?? string.Empty, CapturedAtUtc = capturedAt.ToUniversalTime() };
    foreach (var parameterDto in dto.Parameters ?? Enumerable.Empty<ParameterDto>())
    {
        paramState.Parameters.Add(ParamFromDto(parameterDto)); // explicit .Add() — never assigns
                                                                  // the Collection<T> property itself,
                                                                  // so System.Text.Json's silent-skip
                                                                  // bug for getter-only collections
                                                                  // never triggers on THIS path.
    }
    return paramState;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `ValidStatus` Boolean list, index-matched to ObjState order | Per-object verdict addressed by `(ruleId, objectId)` identity via the evidence envelope | This phase (D-08/D-10/D-13) | `spec/DATABASE.md:112`'s contract is formally retired; any remaining positional-lookup code anywhere in the stack is now a defect, not a stale-but-valid alternative |
| Python `app.py:864-869` failed-wins dedup (`error` loses to `failed`) | Shipped Phase 1201 precedence, `error` first | This phase (D-12) | Real behavior change on the Python side — some previously-`failed`-reported objects with a coincident `error` row will now report `error` |
| ObjState ID minted by `ObjectStateComponent.cs:190-196`'s private duplicate (Label-inclusive, project/variableName-exclusive) | Minted by `DesignStateIdGenerator.ComputeObjectStateId` (once the signature-mapping question above is resolved) | This phase (D-04) | Renaming an object (changing its Label) no longer changes its identity — a behavior change for any workflow that relied on relabeling to "reset" state |
| Two independent v2 payload readers (`TryParseDesignState` inline, `DesignStatePayloadV2Serializer.Deserialize`) | One reader | This phase (D-09) | Only the serializer's reader was covered by tests before this phase; convergence surfaces any latent behavior difference as a test failure, which is the intended outcome |

**Deprecated/outdated:**
- `Run.ValidStatus` / `ValidationEntity`: not removed (additive-not-breaking per D-13), but formally demoted to non-authoritative by D-10. Downstream consumers should migrate to the new per-object read path.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `canonicalStateHash` property's storage location (new `EvidenceEnvelope` field vs. new `:DesignState`/`:ValidationRun` sidecar property) is undecided — this research found **zero existing references** to `canonicalStateHash`/`stateHash` anywhere in `spec/`, confirming CONTEXT.md's "no state-hash concept exists" claim, but does not itself resolve where the new property should live. `[ASSUMED: the planner will treat this as within "Claude's Discretion" per CONTEXT.md's "the exact shape of the canonical DesignState projection... provided it is stated explicitly"]` | Canonical state hash extension (D-02) | If placed as a new top-level `EvidenceEnvelope` field, it triggers the full CLAUDE.md § Schema Change Propagation sweep (schema files, n8n prompts, `spec/EVIDENCE-CONTRACT.md`) since the envelope shape is itself a propagation surface (per `spec/evidence-contract.schema.json`). If placed as a sibling `:DesignState`/`:ValidationRun` property instead (like `shaclReportJson`), the blast radius is smaller (matches the existing sidecar-property precedent) but requires its own presence/absence documentation in `spec/DATABASE.md`. The planner must pick one explicitly and size the Schema Change Propagation sweep accordingly — this is not a discretionary detail, it changes the task list materially. |
| A2 | `fixtures/golden/seed.cypher`'s existing stub `:DesignState` (`DS_GOLDEN_FIXTURE_01`) is **insufficient** for D-17's mixed pass/fail replay fixture and a new sibling fixture must be built, based on this research's direct read of its minimal payload shape (`[VERIFIED: fixtures/golden/seed.cypher:180-199]` shows only bare `stateId` fields, no `objectRef`/`capturedAtUtc`/other required-by-serializer fields) | Runtime State Inventory / D-17 | If the planner instead tries to reuse/extend this stub directly, it would violate D-17's freeze (`fixture.json`/`seed.cypher` are named-frozen) or produce a fixture that fails `DesignStatePayloadV2Serializer`'s own validation (`ValidateDeserialized` requires non-empty `StateId` per ObjState/ParamState/PropState, which the stub's bare-`stateId`-only shape does satisfy minimally, but not `ObjectRef`/`CapturedAtUtc` which `ValidateDesignState` — the write-side validator — requires; the stub was written directly via Cypher, bypassing that validator entirely, so it may not round-trip through the real serializer at all) |
| A3 | `ComputeObjectStateId`'s existing 3-argument signature was designed for a different call site than `ObjectStateComponent` (likely a per-rule-variable Object-state concept implied by its CMPST-07/CMPST-08 doc comments), and the cleanest fix may be a new additive overload rather than force-mapping the existing signature | Pitfall 1 / D-04 | If the planner instead forces `ObjectStateComponent` to synthesize fake `projectId`/`variableName` values just to satisfy the existing signature, the resulting IDs may not carry the semantic meaning the doc comments promise, undermining the "one function mints every ObjState ID" goal in spirit even while satisfying it in name |

**If this table is empty:** N/A — see entries above; all other claims in this research are `[VERIFIED]` against direct file reads or `[CITED]` against CONTEXT.md's own already-verified disk facts (which this research cross-checked and confirmed rather than re-deriving).

## Open Questions

1. **Where does `canonicalStateHash` live — envelope field or sidecar property?**
   - What we know: no existing precedent anywhere in the repo; both `EvidenceEnvelope` (envelope-field option) and the `statePayloadJson`/`shaclReportJson`/`evidenceEnvelopeJson` sidecar pattern (sidecar option) are viable, symmetrical mechanisms already in production.
   - What's unclear: which one the planner should choose, and the corresponding Schema Change Propagation sweep size.
   - Recommendation: sidecar property on `:DesignState` (parallel to how `statePayloadJson` already lives there), computed at the same write site that already computes `StateId` (`DesignStateCompositionComponent.cs:156`/`cg_paramstate_store.py`'s accept path) — this keeps the hash colocated with the payload it hashes and avoids touching the already-frozen `EvidenceEnvelope` shape from Phase 1200. The planner should state this explicitly rather than leave it implicit, since D-02 marks the reversibility of this decision as one-way.

2. **Does `run_leg_replay`'s state-hash comparison need a live GH/Rhino leg, or only data-service + C# + replay?**
   - What we know: "the legs" in DE-01 today are `data-service`, `dg-reasoner`, `csharp`, `replay` — confirmed via `run_de01.py:34-37`. There is no fifth "GH/Rhino" leg in the current DE-01 harness; Rhino/GH live interaction is owned by Phase 40 (GATE12-04), explicitly out of this phase's scope.
   - What's unclear: whether D-16's "across the legs" language implies the state hash must be computed identically by all 4 existing legs, or only by the subset that actually touches Design State (arguably `csharp` and `replay`, since `data-service`/`dg-reasoner` operate on the rule-evaluation fixture, not a captured Design State per se).
   - Recommendation: scope the state-hash comparison to the legs that actually produce/consume a Design State payload (`csharp` via the harness, `replay` via the persisted view) rather than forcing `data-service`/`dg-reasoner` to fabricate one — consistent with `compare_legs`'s existing "typed absence, not silently skipped" idiom, a leg genuinely not applicable to state-hash comparison should report itself as such rather than being force-fit.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| .NET SDK | `dotnet build`/`dotnet test` for all C# work | ✓ | 10.0.301 | — |
| Python | `data-service`, `tools/de01` test suites | ✓ | 3.14.2 | — |
| Docker Desktop / `docker compose` | D-16's live DE-01 exit evidence, `data-service` rebuild-after-change verification | ✗ (engine unreachable at research time) | — | Start Docker Desktop before the DE-01 exit-evidence task; no code-level fallback — this is a hard precondition for D-16, not something the phase can route around |
| Neo4j (via compose) | DE-01 `replay` leg, `DesignStateValidationFlowTests` (4 tests known to fail fast when Neo4j is down per STATE.md baseline) | ✗ (depends on Docker Desktop above) | — | Same as above |

**Missing dependencies with no fallback:**
- Docker Desktop / the full compose stack — D-16 requires it explicitly; there is no code path that produces valid DE-01 exit evidence without it.

**Missing dependencies with fallback:**
- None — Docker Desktop is the single blocking environment gap, and it has no fallback for this phase's own stated gate.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | xUnit (C#, `DG.Tests`) + pytest (Python, `data-service/tests`, `tools/de01/tests`) |
| Config file | `DG/tests/DG.Tests/DG.Tests.csproj` (net9.0 only); no single pytest config found — invoked directly via `python -m pytest <path>` per STATE.md baseline commands |
| Quick run command | `dotnet test DG/tests/DG.Tests/ -v minimal` (whole suite, ~502 tests, no fast subset identified — no test-name filtering convention observed in this codebase beyond `-k "not live"` for the DE-01 runner) |
| Full suite command | `dotnet test DG/tests/DG.Tests/ -v minimal` && `python -m pytest data-service/tests -q` && `python -m pytest tools/de01/tests/test_de01_runner.py -q -k "not live"` && (live) `python -m pytest tools/de01/tests/test_de01_runner.py -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALGN12-08 | Design State identity explicitly classified (capture-event key + content hash) | unit | `dotnet test DG/tests/DG.Tests/ -v minimal --filter DesignStateIdGeneratorTests` | ✅ (extend existing `DesignStateIdGeneratorTests.cs`) |
| ALGN12-09 | publish→query→replay preserves canonical state hash, membership manifest, schema version, normative members | unit + integration | `dotnet test` (serializer round-trip) + `python -m pytest tools/de01/tests/test_de01_runner.py -k "not live"` (offline harness) + live DE-01 run (compose) | ✅ unit; ⚠️ live DE-01 needs Docker Desktop (see Environment Availability) |
| ALGN12-10 | Mixed per-object outcomes remain distinct through persistence and C# retrieval | unit + integration | New `Neo4jValidGraphRepositoryTests` cases for the additive per-object method; live DE-01 `compare_legs` state | ❌ Wave 0 — new C# repository method has no test file yet; extend `DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs`-equivalent (confirmed exists per graphify output, community `Neo4jValidGraphRepositoryTests`) |
| ALGN12-11 | Mutable operational/run status separated from immutable snapshot identity | unit + integration | `python -m pytest data-service/tests -k publish` (verify `ON CREATE SET` behavior on re-publish) | ⚠️ Wave 0 — no existing test asserts current unconditional-`SET`-overwrites-immutable-fields behavior; a regression test proving `ON CREATE SET` protects `statePayloadJson`/`rulesJson`/`createdAt` on re-publish needs to be written |

### Sampling Rate
- **Per task commit:** `dotnet test DG/tests/DG.Tests/ -v minimal` for any `DG.Core`/`DG.Grasshopper` change; `python -m pytest data-service/tests -q -k <touched module>` for any `data-service` change
- **Per wave merge:** Full `DG.Tests` (502+) + `data-service/tests` (823+) suites
- **Phase gate:** Full suite green + one live DE-01 run (`python -m pytest tools/de01/tests/test_de01_runner.py -q`, no `-k "not live"` filter, requiring the compose stack) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] New `IValidGraphRepository` per-object method test coverage (extend `Neo4jValidGraphRepositoryTests.cs`) — covers ALGN12-10
- [ ] `ON CREATE SET` immutability regression test in `data-service/tests` (re-publish same `runId` must not overwrite `statePayloadJson`/`rulesJson`/`createdAt`) — covers ALGN12-11
- [ ] New sibling fixture material under `fixtures/golden/` (D-17 mixed pass/fail per-object replay fixture) — covers ALGN12-09/ALGN12-10 test data
- [ ] Framework install: none — all frameworks already present

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase does not touch auth surfaces (ALGN12-17/18/19/20 are Phase 1205's scope, explicitly deferred) |
| V3 Session Management | No | Not applicable |
| V4 Access Control | No | Not applicable — no new endpoint or access boundary introduced |
| V5 Input Validation | Yes | `DesignStatePayloadV2Serializer`'s existing `ValidateDesignState`/`ValidateDeserialized` pattern (throw `InvalidOperationException` on malformed input) — the new `ClassIri` optional field and version-check addition must follow this same fail-closed validation convention, never silently coerce malformed input |
| V6 Cryptography | Yes (hashing, not encryption) | `CanonicalJsonWriter`/`canonical_json.py`'s SHA-256 usage — already the established, correct primitive for content-addressing (not a secrecy/confidentiality control); D-02 reuses it verbatim, introducing no new cryptographic surface |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/adversarial `statePayloadJson` causing an unhandled exception in the shared parse path | Denial of Service | `TryParseDesignState`'s existing broad `catch (Exception)` (`:237-248`, deliberately broadened per WR-03 to avoid failing the entire `GetRunsAsync` response for one bad payload) — D-09's convergence must preserve this degrade-not-crash behavior when delegating to `DesignStatePayloadV2Serializer.Deserialize`, which currently **throws** on invalid input (`:56-59`, `:66-69`) rather than degrading; the caller-side try/catch must remain in place around the call-through |
| A recomputed `canonicalStateHash` silently diverging between C# and Python due to a canonicalization-rule drift | Tampering (in the sense of undetected data-integrity drift, not an external attacker) | Golden vector parity tests (`fixtures/golden/canonical-vectors.json`, `CanonicalJsonWriterTests`) — any new projection logic must be covered by an equivalent cross-language golden vector before being trusted, per the existing CR-01/WR-01 precedent of "a divergence fails a test in whichever leg drifted, before any DE-01 cross-leg comparison could report it" |

## Sources

### Primary (HIGH confidence)
- Direct file reads, 2026-09-21, of all files enumerated in CONTEXT.md's `<canonical_refs>` "Code this phase changes" list: `DG/src/DG.Core/Data/Neo4jValidGraphRepository.cs`, `DG/src/DG.Core/Data/IValidGraphRepository.cs`, `DG/src/DG.Core/Serialization/DesignStatePayloadV2Serializer.cs`, `DG/src/DG.Core/Models/ObjState.cs`, `DG/src/DG.Core/Models/DesignState.cs`, `DG/src/DG.Core/Services/DesignStateIdGenerator.cs`, `DG/src/DG.Core/Contracts/EvidenceEnvelope.cs`, `DG/src/DG.Core/Contracts/EvidenceStatus.cs`, `DG/src/DG.Core/Contracts/CanonicalJsonWriter.cs`, `DG/src/DG.Core/Contracts/EvidenceEnvelopeFactory.cs`, `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs`, `data-service/app.py` (lines 570-660, 840-946), `data-service/cg_paramstate_store.py` (lines 320-360), `data-service/canonical_json.py`, `data-service/evidence_contract.py`, `tools/de01/legs.py` (full), `tools/de01/report.py` (lines 1-180), `DG/tools/DG.De01Harness/Program.cs` (lines 260-297), `fixtures/golden/seed.cypher`, `fixtures/golden/fixture.json`, `fixtures/golden/MANIFEST.md`, `spec/DATABASE.md` (grepped), `spec/EVIDENCE-CONTRACT.md` (section headers grepped)
- `graphify query` orientation (per project mandate) for `EvidenceEnvelope`/`EvidenceStatus`/`DG.Core.Contracts`, `IValidGraphRepository`/`Neo4jValidGraphRepository`, `ObjectStateComponent`/`ComputeObjectStateId` — confirmed node locations before direct reads, consistent with the project's PreToolUse:Read hook requirement
- `.planning/phases/1202-.../1202-CONTEXT.md` — 17 decisions D-01..D-17, cross-verified rather than re-derived

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` and `.planning/STATE.md` — project-level requirement/decision history, read directly

### Tertiary (LOW confidence)
- None — no WebSearch or external documentation lookup was needed; this phase's domain is entirely internal, already-shipped project code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages, all extensions of already-verified existing types
- Architecture: HIGH — every file/line reference independently re-verified by direct read, not merely trusted from CONTEXT.md
- Pitfalls: HIGH — Pitfall 1 (ObjectStateComponent signature mismatch) and Pitfall 2 (dual deserialization targets) are net-new findings from this research session, verified by direct code comparison, not present in CONTEXT.md's existing analysis
- Environment: HIGH — Docker Desktop unavailability directly confirmed via Bash on this machine, 2026-09-21

**Research date:** 2026-09-21
**Valid until:** 7 days (fast-moving — this phase is mid-milestone with live code changes; re-verify file line numbers if planning is deferred more than a week)
