# Phase 1203: Identity Convergence and `ATTRIBUTE_OF` Decision - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 1203-identity-convergence-and-attribute-of-decision
**Areas discussed:** ATTRIBUTE_OF branch choice, Identity minting authority, Phase 32.1 carried findings, Platform conflict/detach/provenance evidence

**Mode note:** The user selected **all four** gray areas, then instructed
*"Discuss all areas and auto accept all recommended options by yourself."*
All decisions D-01…D-14 are therefore Claude-selected under that instruction, each
recorded in CONTEXT.md with the disk evidence it rests on.

---

## Pre-discussion verification

Four inherited planning-corpus claims were checked against disk before any option was
framed. All four required correction, and two of them changed the recommendation:

| # | Inherited claim | Disk finding |
|---|---|---|
| 1 | Branch B = "adopt `PARAM_LINK`" as the accepted bridge contract | `dgc:attributeOf` is `Atom→Parameter`; `dgc:paramLink` is `Parameter→Interface`. Different relations — `PARAM_LINK` cannot carry the CQ3 claim |
| 2 | `ATTRIBUTE_OF` has no runtime counterpart | The real bridge is `llm/structure_rules.json` → `inputBindings`, resolved in memory against published `:Parameter` nodes. Semantics already shipped; only persistence is missing |
| 3 | 1202 D-04 converged ObjState minting on one function | Duplicate deleted, but a **new** `ComputeObjectStateIdFromRef` was added; the 3-arg form remains with a documented "why this exists alongside" rationale |
| 4 | CR-01/CR-02 status unstated | CR-01, CR-02 and WR-01 all still open on disk, verified line by line |

A fifth fact: no DesignState minting function folds `project` into its hash, unlike `dgId`.

---

## ATTRIBUTE_OF branch choice (ALGN12-14)

| Option | Description | Selected |
|--------|-------------|----------|
| Branch A — implement `ATTRIBUTE_OF` | Write the edge alongside `PARAM_LINK`; evidence both query directions; full schema propagation | ✓ |
| Branch B — adopt `PARAM_LINK`, retire the TBox commitment | Narrow CQ3 to `PARAM_LINK` + input-binding resolution; retract the declared property | |
| Branch C — leave `inputBindings` as the contract, document the gap | No graph edge; document that the bridge is a config file | |

**Choice:** Branch A (D-01).

**Notes / rationale, in order of weight:**
1. `PAPER-C-032` records CQ3's demonstration as an Atom→Parameter trace
   (`R_BUILDING_MIN_DISTANCE_12_V`/`A2`/`hasDistanceM` → `SepDist`). Per correction 1, neither
   `PARAM_LINK` nor a config file can express it.
2. The TBox already declares the property, so branch A needs no ontology change; branch B
   requires *retracting* a published commitment.
3. Correction 2 makes branch A cheap — it persists a resolution the system already performs.
4. Branch A leaves CQ3 unchanged, so **no manuscript edit is required**. Branch B would force
   one, and v11.0 Phase 1107 is the sole manuscript owner while v12.0 is explicitly forbidden
   from manuscript edits — a dependency this phase could neither discharge nor verify.

Branch C was rejected on the same first point: it leaves the gate's "both query directions are
evidenced" unsatisfiable, since a config file is invisible to Cypher and has no reverse direction.

**Supporting decisions:** D-02 (`inputBindings` stays the authoring source; the edge is derived,
following the `PARAM_LINK` wire-derivation precedent), D-03 (project-scoped MERGE with derivation
provenance), D-04 (atom attachment must be stated explicitly), D-05 (full schema propagation).

---

## Identity minting authority (ALGN12-12)

| Option | Description | Selected |
|--------|-------------|----------|
| Extend `spec/DG-ID.md` to cover DesignState IDs | One authority for `dgId` **and** the four DesignState minting functions | ✓ |
| New separate DesignState identity spec | A second normative document alongside `spec/DG-ID.md` | |
| Leave DesignState minting governed by doc-comments | Status quo; document only `dgId` | |

**Choice:** Extend the existing spec (D-06). A second identity spec would be exactly the drift
this milestone exists to eliminate.

| Option | Description | Selected |
|--------|-------------|----------|
| Retain both ObjState minting forms, name authority per case | Contract states which form is authoritative for which case | ✓ |
| Delete the 3-arg form, converge as 1202 D-04 described | Single function | |

**Choice:** Retain both (D-07). Correction 3 shows 1202 deliberately preserved the split on stated
evidence — the component has no Project port and no per-geometry variable-name concept, so forcing
one signature would require synthesizing fake values. Removal remains available to the planner as a
separate evidenced decision.

| Option | Description | Selected |
|--------|-------------|----------|
| Fold `project` into new DesignState hashes, additive, no rewrite | Restores the two-layer collision defense; historical IDs documented as pre-contract | ✓ |
| Fold `project` + migrate historical IDs | Rewrites existing rows | |
| Leave the gap; rely on the MERGE key alone | Status quo | |

**Choice:** Additive, no rewrite (D-08) — mirrors 1202 D-03 and avoids a second unapproved
migration. This is ALGN12-12's "migration treatment for historical IDs".

---

## Phase 32.1 carried findings (GSD-ALIGN-006)

| Finding | Options considered | Selected |
|---|---|---|
| **CR-02** (delimiter) | reject any field containing a pipe · **length-prefix encoding** · hash-per-field | length-prefix (D-09) |
| **CR-01** (anchor) | make `mint_identity` label-aware · change publish to match the label-less anchor · **forbid mint-before-publish** | label-aware (D-10) |
| WR-01 (`graph` tag) | bundle with CR-01 fix | bundled (D-11) |
| WR-02, WR-04 (doc drift) | bundle into the D-06 doc pass | bundled (D-11) |
| WR-03 (dead constant) | wire property validation into `validate_cypher` · **delete the constant** | delete (D-11) |

**Notes:**
- CR-02's fix is extended beyond `dgId` to the four `DesignStateIdGenerator` functions, which share
  the identical exposure. Length-prefixing was preferred over rejection because `cgId` derives from
  user-authored Grasshopper nicknames and `project` is externally supplied — rejection would turn a
  legal-but-awkward name into a hard runtime failure.
- CR-01's third option (forbid mint-before-publish) was rejected because `spec/DG-ID.md:55-64`
  declares that workflow **intended** — forbidding it would contradict the very spec D-06
  consolidates under.
- WR-03: wiring property-level Cypher validation is a new capability and was routed to a future
  Cypher-validator phase rather than absorbed here.
- D-08 and D-09 both change minted ID values and must be sequenced as **one** coordinated
  re-derivation, not two.

---

## Platform conflict / detach / provenance evidence (ALGN12-13)

| Option | Description | Selected |
|--------|-------------|----------|
| Treat as an evidence gap — write the tests | `spec/DG-ID.md` already specifies authority, detach, provenance and conflict direction; the requirement's "and tested" is what is missing | ✓ |
| Treat as a specification gap — write a new policy | Author a fresh platform-authority policy document | |
| Implement full bidirectional conflict resolution | Per-platform authoritative resolution | |

**Choice:** Evidence gap (D-12). Re-specifying what is already normative would create a competing
document; the phase writes tests that hold the existing spec and amends it only where a test proves
it wrong.

**Also:** full bidirectional per-platform conflict resolution stays deferred (D-13) — explicitly
deferred by `spec/DG-ID.md` and requested by no requirement. Only last-write-wins is tested.

---

## Evidence and exit criteria

| Option | Description | Selected |
|--------|-------------|----------|
| CQ3 fixture proves both directions; DE-01 leg at the planner's discretion | Fixture mirrors `PAPER-C-032`'s shape; DE-01 optional | ✓ |
| Mandate a DE-01 leg, mirroring 1202 D-16 | Cross-service run as exit evidence | |
| Unit tests only | No fixture gate | |

**Choice:** D-14. Unlike 1202, the claims here are single-service graph-query claims rather than
cross-language verdict claims, so a DE-01 leg may add cost without adding evidence — left to the
planner. New fixture material goes in a sibling path; `fixtures/golden/fixture.json` stays frozen.

---

## Claude's Discretion

Recorded in full in CONTEXT.md `<decisions>` § Claude's Discretion. Summary: the atom attachment
choice and reverse-query shape; the edge's property set beyond project scope and provenance; the
exact length-prefix format; `/identity/mint`'s entity-kind mechanism; whether the 3-arg
`ComputeObjectStateId` is ultimately removed; whether a DE-01 leg is added; fixture file split and
naming; pytest/xUnit split; plan and wave decomposition.

## Deferred Ideas

Recorded in full in CONTEXT.md `<deferred>`. Newly routed in this discussion: property-level Cypher
validation (future Cypher-validator phase) and removal of the 3-arg `ComputeObjectStateId`
(allowed here only as a separate evidenced decision). Inherited routings unchanged: manuscript
edits → v11.0 1107; ComputGraph executable semantics → v11.0 1106; determinism → 1204;
authorization → 1205; live UAT → v9.0 Phase 40.
