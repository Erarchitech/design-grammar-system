# Phase 1202: Design State Replay and Per-Object Verdict Closure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-21
**Phase:** 1202-design-state-replay-and-per-object-verdict-closure
**Areas discussed:** Identity semantics, Replay membership, Per-object verdict path

**Area selection:** Four gray areas were offered. The user selected three; **Snapshot vs run
status (ALGN12-11)** was not selected and was resolved under Claude's discretion (see D-15).

**Mid-discussion instruction (recorded verbatim):** partway through the third area the user wrote
*"Принимай все рекомендованные варианты самостоятельно"* — accept all recommended options
independently. Decisions from that point (D-13 … D-17) are Claude-selected under that instruction.

---

## Identity semantics (ALGN12-08)

### Q1 — Which identity semantics should the contract declare?

| Option | Description | Selected |
|--------|-------------|----------|
| Both layers | Capture-event identity as node key + content hash as `canonicalStateHash` property. Satisfies ALGN12-08 and yields the ALGN12-09 hash in one move. Cost: schema propagation; recapture stops deduping | ✓ |
| Keep content-equivalence | Declare today's behavior normative; route ObjState minting through `DesignStateIdGenerator` so Label stops feeding the ID. Every historical `OS_`/`DS_` changes; migration mandatory | |
| Move to capture-event | Fold `capturedAtUtc`/nonce into `ComputeDesignStateId`. Preserves history; breaks idempotent re-accept (`spec/DATABASE.md:99`); no content hash to compensate | |

**User's choice:** Both layers → **D-01**

### Q2 — How should the canonical state hash be computed?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend 1200 hasher | Feed a canonical DesignState projection into existing `HashCanonical`. Inherits proven cross-language parity (CR-01 decimal scale, WR-01 negative zero) and `CanonicalizationVersion` | ✓ |
| New dedicated state hasher | Purpose-built hash. Full control; adds a **fourth** hashing regime and must re-earn cross-language parity | |
| Extend and unify all three | Also fold `DesignStateIdGenerator`/`DgIdMintingService` onto it. Strongest "one contract" outcome; `DgIdMintingService.cs:17-21` documents the duplication as deliberate, and re-minting `dgId`s is a much wider blast radius | |

**User's choice:** Extend 1200 hasher → **D-02**

### Q3 — How should historical states be treated?

| Option | Description | Selected |
|--------|-------------|----------|
| Additive, no rewrite | New captures use new keying + `canonicalStateHash`; existing rows stay and are documented pre-contract. Matches Phase 823's "absence = not recorded" rule; no migration to approve | ✓ |
| Backfill hash only | Leave keys, compute `canonicalStateHash` on existing states. Requires a migration over payloads that may predate v2 — partial backfill with gaps | |
| Full migration | Re-key historical states. Cleanest end state; largest blast radius, and would add a second migration beside the unapproved 2026-07-07 one | |

**User's choice:** Additive, no rewrite → **D-03**

### Q4 — What about the duplicate ObjState minting site?

| Option | Description | Selected |
|--------|-------------|----------|
| Converge on generator | Delete the private duplicate at `ObjectStateComponent.cs:190-196`; route through `DesignStateIdGenerator`. One documented minting function. Requires GH plugin rebuild | ✓ |
| Document the fork, defer | Record that two paths exist. Zero code risk; leaves a known identity inconsistency live while the phase claims a canonical identity contract | |
| Adopt the shipped behavior | Make the label-inclusive form normative and update the generator. Preserves every existing `OS_`; bakes in Label-sensitivity so renaming silently changes identity | |

**User's choice:** Converge on generator → **D-04**

**Notes:** This area was opened with a verified correction — the inherited claim that "current IDs
exclude label and capture time" is false for the path that actually ships. The user chose
convergence knowing new captures would key differently from old ones, which D-03 already accepts.

---

## Replay membership (ALGN12-09, milestone open question #4)

### Q1 — How should `ClassIri` be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Add to payload | Normative serialized member. Replay becomes self-contained and re-binding works offline. Forces the version question | ✓ |
| Derive from `dgId` at replay | Look up `(:Object).classIri`. Payload unchanged; adds a graph round-trip per replay, kills offline replay, and `classIri` is optional (`spec/DATABASE.md:57`) so it can return null | |
| Formally exclude | Declare outside the normative contract. Cheapest, and the roadmap permits an exclusion contract — but excluding a member the binding service needs makes "replay" mean less | |

**User's choice:** Add to payload → **D-05**

### Q2 — How should geometry be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude, reference by id | Formally exclude from payload and hash; reference by `dgId`/Speckle `objectId`. Defensible per `spec/DG-ID.md:15`; avoids inventing float canonicalization. Replay cannot reconstruct a viewable state offline — stated plainly | ✓ |
| Serialize geometry too | Fully self-contained replay. Requires floating-point canonicalization extending 1200's hasher into hard territory; inflates every payload | |
| Hash a geometry digest | Exclude bytes, fold a digest into the hash so changes are detectable but not reproducible. Still needs float-canonicalization rules for cross-language stability | |

**User's choice:** Exclude, reference by id → **D-06**

### Q3 — How should versioning work?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay v2, additive optional | `ClassIri` optional; absence = "not recorded, never an error" (Phase 823). Old payloads keep reading. Also fixes `TryParseDesignState` to actually check version | ✓ |
| Bump to v3 | Cleanest semantics for "a complete state"; every reader must handle both, and structural sniffing would misread v3 as v2 unless fixed anyway | |
| Stay v2, `ClassIri` required | Strongest guarantee for new payloads; every existing v2 payload becomes invalid on read — a breaking change to persisted data | |

**User's choice:** Stay v2, additive optional → **D-07**

### Q4 — How should ordering be contracted?

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical sort is the contract | StateId-sorted order normative for payload and hash; wiring order explicitly not preserved. Hash becomes order-independent | ✓ |
| Preserve wiring order | Keeps index-matched `ValidStatus` meaningful; makes the hash sensitive to authoring order — identical designs wired differently would hash differently | |
| Carry both | Sort canonically for the hash, persist an explicit order index. Most information preserved; adds a field and a second ordering concept to keep in sync | |

**User's choice:** Canonical sort is the contract → **D-08**

### Q5 — What about the two independent payload readers?

| Option | Description | Selected |
|--------|-------------|----------|
| Converge on one reader | `TryParseDesignState` delegates to `DesignStatePayloadV2Serializer.Deserialize`. One reader, one version check, one membership contract | ✓ |
| Keep both, add a parity test | Pin them together on the golden fixture. Cheaper and lower risk; two implementations remain against the phase's stated goal | |
| Document as excluded | Note the divergence and leave it. Lowest effort; knowingly ships the drift class the milestone exists to eliminate | |

**User's choice:** Converge on one reader → **D-09**

**Notes:** Q4's answer has a direct downstream consequence that shaped the next area — with
canonical sort normative, `spec/DATABASE.md:112`'s index-matched `ValidStatus` contract is
formally dead, so per-object verdicts must be identity-addressed rather than positional.

---

## Per-object verdict path (ALGN12-10)

**Opening position presented to the user (verified on disk):** the per-object truth is live
end-to-end in Python (`ValidationEntity` written `app.py:633-656`, read `:849-870` with
failed-wins dedup) and **completely absent in C#** — zero hits for `ValidationEntity` across
`DG/src`.

### Q1 — Where should the canonical per-object verdict read land?

| Option | Description | Selected |
|--------|-------------|----------|
| Evidence envelope rows | Read 1200's per-`(rule, object)` envelope rows as canonical; demote `ValidStatus` and `ValidationEntity` to legacy. One contract across all four DE-01 legs; satisfies 1200's "no gate treats legacy booleans as authoritative". Pre-1200 runs carry no envelope | ✓ |
| C# `ValidationEntity` read | Keyed by `dgEntityId`, matching what Python writes. Identity-addressed and works for existing runs; leaves two answers to the same question | |
| Fix `RunsQuery` positionally | Smallest diff, fixes the fabricated list; re-commits to positional matching that the canonical-sort decision just invalidated | |

**User's choice:** Evidence envelope rows → **D-10**

### Q2 — What should legacy (pre-1200) runs show per object?

| Option | Description | Selected |
|--------|-------------|----------|
| `not_evaluated`, no fallback | Absent envelope = never canonically recorded. Refuses to infer canonical status from a legacy boolean, which 1200 D-04 forbids. Existing runs visibly lose canvas colors until re-run | ✓ |
| Fall back to `ValidationEntity` | Preserves per-object detail for recent legacy runs; reintroduces the demoted surface and only carries `passed`/`failed`, not the full 8-status vocabulary | |
| Fall back to `ValidStatus` | Maximum backward compatibility; directly violates 1200 D-04 and re-legitimizes the surface being retired | |

**User's choice:** `not_evaluated`, no fallback → **D-11**

### Q3 — Which precedence governs per-object aggregation?

| Option | Description | Selected |
|--------|-------------|----------|
| Shipped 1201 precedence | `EvidenceEnvelopeFactory.RollupPrecedence` / `_ROLLUP_PRECEDENCE` verbatim. One table, already cross-language verified; 1201's context forbids a second. Differs from failed-wins: `error` outranks `failed` | ✓ |
| Keep failed-wins for objects | Matches shipped Python behavior exactly, no Python change; two disagreeing precedence rules would coexist | |
| No rollup, keep rows distinct | Most faithful to the evidence; the canvas needs one color per object, so the decision just moves to the UI unspecified and untested | |

**User's choice:** Shipped 1201 precedence → **D-12**

**Notes:** The user's blanket-accept instruction arrived immediately after this question. Q3's
answer implies a **real behavior change on the Python side** — `app.py:864-869` currently puts
`failed` above `error` — not merely a documentation exercise.

---

## Claude's Discretion

Resolved under the user's instruction *"Принимай все рекомендованные варианты самостоятельно"*:

| Ref | Decision | Recommended option taken |
|---|---|---|
| **D-13** | C# read surface | `IValidGraphRepository` gains an **additive** typed per-object method; `GetRunsAsync`/`StatusList` retained as non-authoritative (1200 D-03 applied to the read model) |
| **D-14** | The fabricated list | `Enumerable.Repeat` at `Neo4jValidGraphRepository.cs:73-75` is **removed**, not patched — it is a missing feature, not a mapping bug |
| **D-15** | ALGN12-11 (area not selected for discussion) | Cheapest defensible option: `ON CREATE SET` write-once for immutable properties + explicit contract declaration. **No physical node split, no migration** |
| **D-16** | Exit evidence | DE-01 extended with per-object comparison + canonical-state-hash verification, mirroring 1201's D-11. Unit tests alone insufficient. **Requires a live compose stack** |
| **D-17** | Fixture handling | `fixtures/golden/fixture.json` stays frozen (1200 D-11); mixed pass/fail built from existing `OBJ_GOLD_PASS`/`OBJ_GOLD_FAIL`; new material in a sibling path (1201 D-16 precedent) |

Further discretion explicitly left to the planner is listed in CONTEXT.md `<decisions>` →
"Claude's Discretion" (capture-event key spelling, projection shape, method signature, membership
manifest placement, `PropState.CapturedAtUtc` treatment, fixture file split, test framework).

---

## Deferred Ideas

Recorded in full in CONTEXT.md `<deferred>`. Raised or reaffirmed during this discussion:

- **Physical `:StateSnapshot` / `:Run` node split** — D-15 takes the cheaper route; the split
  remains available to a later phase (full schema-propagation sweep + migration).
- **Unifying the three hashing regimes** — considered in Identity Q2 and explicitly rejected;
  `DgIdMintingService.cs:17-21` documents the duplication as deliberate.
- **Serializing geometry / float canonicalization** — D-06 excludes; additive to add later.
- **Backfilling `canonicalStateHash` onto historical states** — out under D-03.
- **Python symmetric full-DesignState reader** — no consumer needs full reconstruction yet.
- Inherited routings unchanged: `ATTRIBUTE_OF` vs `PARAM_LINK` and cross-platform identity
  authority → **1203**; LLM reproducibility → **1204**; authorization/tenancy → **1205**;
  envelope propagation → **v11.0 1105**; ComputGraph/five-layer semantics → **v11.0 1106**.

## Scope creep

None — the discussion stayed inside the phase boundary. No new capabilities were proposed by the
user.
