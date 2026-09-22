# Phase 1203: Identity Convergence and `ATTRIBUTE_OF` Decision - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve **identity authority** and the **declared-but-unimplemented rule–parameter bridge**.

Five deliverables, from `.planning/ROADMAP.md` Phase 1203 (lines 160–176):

1. Align Grasshopper ObjState minting with the core identity contract, with migration treatment
   for historical IDs.
2. Define platform authority / conflict / detach / provenance policy.
3. A CQ3 fixture covering **forward and reverse** rule–parameter trace.
4. The decision between implementing `ATTRIBUTE_OF` alongside `PARAM_LINK`, or formally adopting
   `PARAM_LINK` and retiring/re-scoping the TBox commitment.
5. Full schema propagation **if** the bridge is implemented.

**Requirements:** ALGN12-12, ALGN12-13, ALGN12-14 (`.planning/REQUIREMENTS.md:35-37`).
**Packages:** `ALIGN-P07`, `ALIGN-P08`.
**Also owns:** the Phase 32.1 CR-01/CR-02 identity findings carried forward by `GSD-ALIGN-006`
(`.planning/PROJECT.md:63`).
**Requires:** 1200 (frozen contract) and 1202 (replay/per-object verdict) — both complete.
**Blocks:** v9.1 activation if the chatbot exposes identity/provenance; v10.0 activation and
Phase 47 rule ownership.

**Gate:** ontology, runtime, specification, and paper ownership agree; **both query directions
are evidenced**, or the narrowed contract is documented.

This phase **consumes** the 1200 evidence contract and the 1202 identity/replay decisions; it does
not redefine the status vocabulary, the envelope shape, or the canonicalization rules.

</domain>

<upstream_corrections>
## Four planning-corpus claims that do NOT survive contact with disk

All verified by the orchestrator on 2026-09-22. **Plan against the disk facts, not the inherited
prose.** Corrections 1 and 2 materially change the ALGN12-14 branch costing that
`.planning/milestones/v12.0-CONTEXT.md` D8 carried forward.

### Correction 1 — `PARAM_LINK` is NOT a substitute for `ATTRIBUTE_OF`; they are different relations

Milestone D8 frames branch B as "formally adopting `PARAM_LINK`" as the accepted contract in place
of `ATTRIBUTE_OF`. That framing assumes the two are interchangeable. **They are not:**

| Relation | Domain → Range | Source |
|---|---|---|
| `dgc:attributeOf` / `ATTRIBUTE_OF` | `dgm:Atom` → `dgc:Parameter` | `ontology/DesignGrammar-V7.owl:2621-2626`, `ontology/DesignGrammar-V7.md:707-713` |
| `dgc:paramLink` / `PARAM_LINK` | `dgc:Parameter` → `dgc:Interface` (wire-derived) | `CLAUDE.md` § Relationships; `data-service/computgraph_publish.py:415,695` |

`PARAM_LINK` connects a parameter to a *wire endpoint inside the Computgraph*. It says nothing
about rules. **It cannot express the CQ3 claim in either direction**, so branch B is not "adopt the
relation we already have" — it is "retract the rule–parameter bridge claim entirely".

### Correction 2 — the real implemented rule→parameter bridge is `inputBindings`, a config file

The bridge is neither absent nor `PARAM_LINK`. It is `llm/structure_rules.json` → `inputBindings[]`,
loaded and resolved by `data-service/cg_input_bindings.py`:

```json
{ "ruleId": "R_URB_HEIGHT_MAX_75_V",
  "determinability": "monotone-bound",
  "parameters": ["HTotal", "SpansCount"],
  "metricExpression": "HTotal + 0.1 * SpansCount",
  "monotoneIn": ["HTotal"] }
```

`classify_rule` resolves `ruleId → parameterNames`, and `cg_paramstate_store.py:296-300` filters
**published `:Parameter` nodes** by matching `parameterName` against that set
(`cg_input_bindings.py:484-524`). So the rule→parameter join **already happens at runtime, in
memory, against real graph nodes** — it is simply never persisted as an edge.

**Consequence for costing:** implementing `ATTRIBUTE_OF` is *persisting a resolution the system
already performs*, not inventing new semantics. Milestone D8 estimated branch A as requiring a
full schema-propagation sweep against unknown semantics; the semantics are known and shipped.
Branch A is materially cheaper than D8 implies. D8 already noted branch B is *more* costly than the
plan implied (it retracts a TBox commitment); Correction 1 raises that cost further.

**The gap `inputBindings` leaves:** it is a **file**, not a graph relation. It is invisible to any
Cypher query, carries no project scope, and cannot answer CQ3's reverse direction
(parameter → governing rules) at all.

### Correction 3 — 1202's D-04 did not land as written; two minting forms coexist **by design**

1202 D-04 said ObjState minting "converges on `DesignStateIdGenerator`… so one function mints every
ObjState ID", deleting the private duplicate. The duplicate **was** deleted, but convergence did
not happen. What shipped instead:

- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:141` calls a **new** overload
  `DesignStateIdGenerator.ComputeObjectStateIdFromRef(objectRef, classIri)`.
- The 3-arg `ComputeObjectStateId(projectId, objectInstanceId, variableName)` **remains**
  (`DesignStateIdGenerator.cs:94-97`) with **zero production callers** (tests only).
- `DesignStateIdGenerator.cs:98-127` carries an explicit "Why this exists alongside" doc-comment:
  the component has no Project input port and no per-geometry variable-name concept, so
  synthesizing values would "satisfy the signature in name while destroying the meaning".

**This is a defensible engineering outcome, not a defect** — but it means ALGN12-12's "one
documented authority" is **still open**, and the answer must be a *contract naming which form is
authoritative for which case*, **not** a deletion. Planning a deletion would re-break what 1202
deliberately preserved.

### Correction 4 — CR-01, CR-02 and WR-01 from Phase 32.1 are all still open on disk

`GSD-ALIGN-006` routes these here. Current state verified 2026-09-22:

| Finding | State | Evidence |
|---|---|---|
| **CR-01** — `mint_identity` anchor MERGE is label-less, so publish never coincides with it and orphans pre-publish bindings | **OPEN** | `data-service/dg_identity.py:178-181` still `MERGE (e {cgId, definitionId, project})`; `computgraph_publish.py:624` still `MERGE (p:Parameter {...})` |
| **CR-02** — unescaped `\|` delimiter in the `dgId` hash input lets distinct triples collide | **OPEN in both languages** | `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs:41`; `data-service/dg_identity.py:61` |
| **WR-01** — `mint_identity`'s anchor never gets `graph:'Computgraph'` | **OPEN** | `dg_identity.py:179` sets only `e.dgId` |
| WR-02 — `spec/DATABASE.md:336` documents a nonexistent route and wrong verb | open | doc-only |
| WR-03 — `ALLOWED_PROPERTIES` is dead code and incomplete | open | `data-service/dg_context.py:546-559` |
| WR-04 — `definitionId` ambiguous (`DocumentId` vs `FileName`) in spec + vectors | open | `spec/DG-ID.md:38` |

### Fifth disk fact worth stating plainly

**No DesignState minting function folds `project` into its hash** — not `ComputeParamStateId`
(`:68-86`), not either ObjState form, not `ComputePropStateId` (`:142-160`). They rely solely on
the Neo4j MERGE key carrying `project` (`cg_paramstate_store.py:336`). `spec/DG-ID.md`'s Collision
Policy calls for **both** layers ("belt-and-suspenders"); DesignState IDs have only one. All of them
also share CR-02's unescaped-pipe exposure.

</upstream_corrections>

<decisions>
## Implementation Decisions

The user selected **all four** gray areas and then instructed:
*"Discuss all areas and auto accept all recommended options by yourself."*
**Every decision below (D-01 … D-14) is Claude-selected under that instruction**, each recording
the evidence it rests on. A planner may flag any decision for reconsideration if research
contradicts the cited evidence.

### `ATTRIBUTE_OF` branch choice (ALGN12-14, milestone open question #1)

- **D-01: Branch A — implement `ATTRIBUTE_OF` as a real graph relation.** `ATTRIBUTE_OF` is
  written alongside (not instead of) `PARAM_LINK`, and both query directions are evidenced.
  **Rationale, in order of weight:**
  1. **The manuscript claim is Atom→Parameter and nothing else can carry it.** `PAPER-C-032`
     (`docs/reviews/theory-implementation-alignment/evidence/paper-claims.json`) records CQ3's
     demonstration as *"a single row tracing `R_BUILDING_MIN_DISTANCE_12_V`/`A2`/`hasDistanceM` to
     parameter `SepDist` of type Variable"*. That is exactly `dgc:attributeOf`'s domain and range.
     Per Correction 1, `PARAM_LINK` cannot express it.
  2. **The TBox already commits** (`DesignGrammar-V7.owl:2621`), so branch A needs **no ontology
     change** — while branch B requires *retracting* a published TBox commitment, which is the more
     invasive act on the ontology side.
  3. **The semantics are already shipped** (Correction 2): `inputBindings` resolution already joins
     rules to published `:Parameter` nodes. This persists an existing resolution.
  4. **Branch A keeps CQ3 unchanged, so no manuscript edit is needed.** v11.0 Phase 1107 is the
     sole manuscript owner (`.planning/milestones/v11.0-ROADMAP.md:176`) and v12.0 is forbidden
     from editing it (`v12.0-CONTEXT.md` `<constraints>`). Branch B would *require* a 1107 edit —
     creating a cross-milestone dependency this phase cannot discharge and its gate cannot verify.
  **This answers milestone open question #1: `ATTRIBUTE_OF` is normative.**
  — **Reversibility:** one-way — once the edge is written and the CQ3 gate is defined against it,
  reverting means a Cypher migration to remove the edges plus retracting the gate.

- **D-02: `inputBindings` remains the authoring source; `ATTRIBUTE_OF` is its derived projection.**
  `llm/structure_rules.json` stays the human-authored declaration. The `ATTRIBUTE_OF` edge is
  **derived** from it at publish/accept time by the existing resolution, exactly as `PARAM_LINK` is
  derived from wire adjacency (`computgraph_publish.py:415`).
  **Rationale:** the repo already has a derive-then-MERGE precedent for a Computgraph edge, and a
  single authoring source prevents two disagreeing declarations of the same fact — the drift class
  this milestone exists to eliminate. Making the graph edge authoritative would orphan
  `determinability` / `metricExpression` / `monotoneIn`, which have no edge representation.
  **Forbidden:** a second hand-authored list of rule→parameter pairs.
  — **Reversibility:** costly — re-pointing the authoring source later touches every writer and
  the CQ3 fixture.

- **D-03: The edge is project-scoped and carries derivation provenance.** `ATTRIBUTE_OF` is
  MERGEd only between an `:Atom` and a `:Parameter` **in the same `project`**, and records at
  minimum which `inputBindings` entry derived it.
  **Rationale:** `:Atom` is keyed by `Atom_Id` and `:Parameter` by `cgId`+`definitionId`+`project`
  — an unscoped MERGE would cross project boundaries, the exact defect
  `migrations/2026-06-23_var_project_merge_key.cypher` was written to fix and that
  `spec/DG-ID.md` Collision Policy forbids. `inputBindings` entries carry **no project field**, so
  scope must come from the publish context, never from the file.
  — **Reversibility:** reversible — additive properties on a new edge.

- **D-04: Which atom the edge attaches to is a planner decision, but it MUST be stated
  explicitly and be reverse-queryable.** A rule has several body atoms; `PAPER-C-032` attaches to
  `A2` (the `DataPropertyAtom`, `hasDistanceM`). The planner picks the attachment rule and writes
  it into the spec; it may not leave it implicit.
  **Rationale:** `read_rule_limit` (`cg_input_bindings.py:293-302`) already traverses
  `(:Rule)-[:HAS_BODY]->(:Atom {type:'BuiltinAtom'})-[:ARG]->(:Var|:Literal)`, so atom-type
  discrimination is established practice. CQ3's reverse direction (parameter → governing rules)
  only works if the attachment is predictable.
  — **Reversibility:** costly — changing attachment after fixtures exist invalidates the CQ3 gate.

- **D-05: Full schema propagation is mandatory and is this phase's largest surface.** Deliverable
  5's condition is met by D-01, so the complete `CLAUDE.md` § Schema Change Propagation list
  applies — explicitly including `ontology/dg-shapes.ttl` (20 node shapes) and
  `spec/RULE-PARTITION-POLICY.md`, both named there and both easy to miss.
  — **Reversibility:** reversible per-file, but omissions are the recurring defect class.

### Identity minting authority (ALGN12-12)

- **D-06: `spec/DG-ID.md` is extended to become the single identity authority, covering
  DesignState IDs as well as `dgId`.** Today it governs only `dgId`; the four DesignState minting
  functions are governed by nothing but their own doc-comments.
  **Rationale:** ALGN12-12 asks for "one documented authority". A second identity spec would be the
  drift this milestone eliminates. `spec/DG-ID.md` is already normative, already in the propagation
  list, and already carries the collision policy the DesignState functions need.
  — **Reversibility:** reversible — documentation consolidation.

- **D-07: Both ObjState minting forms are RETAINED, and the contract names which is
  authoritative for which case.** Per Correction 3: `ComputeObjectStateIdFromRef` is authoritative
  for **canvas-captured per-geometry-instance ObjStates** (the shipping path);
  `ComputeObjectStateId` (3-arg) is documented as the **per-rule-variable form (CMPST-07)** with no
  current production caller.
  **Explicitly reverses 1202 D-04's deletion framing** on the evidence in
  `DesignStateIdGenerator.cs:98-127`. If the 3-arg form is genuinely dead, the planner may propose
  removing it — but as a **separate, evidenced** decision, never as an assumed consequence.
  **Forbidden:** synthesizing a fake `projectId` or `variableName` to force one signature.
  — **Reversibility:** reversible.

- **D-08: The `project`-in-hash gap is CLOSED for new DesignState IDs, additively.** DesignState
  minting folds `project` into the hash input, restoring `spec/DG-ID.md`'s two-layer collision
  defense. **Historical IDs are NOT rewritten** — they stay valid and are documented as
  pre-contract.
  **Rationale:** mirrors 1202 D-03's additive-no-rewrite rule and the repo's house style; the repo
  already carries one unapproved unrun migration
  (`migrations/2026-07-07_validationgraph_to_validgraph.cypher`) and must not acquire a second.
  **This is ALGN12-12's "migration treatment for historical IDs": additive, documented, no rewrite.**
  **Consequence the planner must handle and state plainly:** every new ObjState/ParamState/PropState
  ID changes value. Under 1202 D-01 (capture-event keying) recapture no longer dedupes by MERGE
  anyway, so this compounds an accepted change rather than introducing a new class of one. The
  1200 golden fixture and any committed vectors containing DesignState IDs must be re-derived in
  lockstep — **`fixtures/golden/fixture.json` stays frozen (1200 D-11 / 1202 D-17)**; new material
  goes in a sibling path.
  — **Reversibility:** one-way — recorded IDs become unreproducible once the input contract changes.

### Phase 32.1 carried findings (GSD-ALIGN-006)

- **D-09: CR-02 is fixed by length-prefix encoding, applied identically in both languages and
  extended to every pipe-joined identity hash.** The fix covers `DgIdMintingService.Mint`,
  `compute_dg_id`, **and** the four `DesignStateIdGenerator` functions, which share the same
  unescaped-delimiter exposure (fifth disk fact).
  **Rationale:** the review offers reject-on-`|` or length-prefixing; length-prefixing is chosen
  because `cgId` derives from user-authored Grasshopper nicknames and `project` is externally
  supplied — rejecting would turn a legal-but-awkward name into a hard runtime failure, while
  length-prefixing is total. Fixing `dgId` alone would leave the identical defect in the
  DesignState family that this phase is simultaneously declaring authoritative.
  **Mandatory:** golden vectors updated in **lockstep** in both the C# xUnit and Python pytest
  suites, plus a cross-boundary-collision regression test in both.
  — **Reversibility:** one-way — every previously minted `dgId` and DesignState ID changes.
  Sequence D-08 and D-09 as **one** coordinated re-derivation, not two.

- **D-10: CR-01 is fixed by making `mint_identity` label-aware, with a regression test that mints →
  binds → publishes → asserts the published entity still carries the binding.** Of the review's
  three options, the third (forbid mint-before-publish) is rejected: `spec/DG-ID.md:55-64` declares
  pre-mint-before-publish the **intended** workflow, so forbidding it contradicts the normative
  spec this phase is consolidating under D-06.
  **Planner note:** `/identity/mint` is currently kind-agnostic, so the entity kind must become an
  input or be resolved. The review calls this "awkward" — it is the cost of honoring the spec.
  — **Reversibility:** costly — the `/identity/mint` signature is a published API surface
  (`spec/API.md`).

- **D-11: WR-01 is bundled with D-10; WR-02 and WR-04 are bundled into the D-06 doc pass; WR-03 is
  resolved by DELETING the dead constant.** `ALLOWED_PROPERTIES` (`dg_context.py:546-559`) is
  never referenced by `validate_cypher`. Wiring property-level validation into the Cypher validator
  is a **new capability** and belongs to a Cypher-validator phase, not here; deleting dead code
  whose docstring overstates what the validator does is in scope.
  — **Reversibility:** reversible.

### Platform conflict / detach / provenance evidence (ALGN12-13)

- **D-12: ALGN12-13 is treated as an EVIDENCE gap, not a specification gap.** `spec/DG-ID.md`
  already specifies platform authority (`Representation` binding model, Revit binds `UniqueId`
  never `ElementId`), detach (`HAS_REPRESENTATION` row operations that never rewrite `dgId`),
  provenance (`connector`, `boundAt`, `writtenAt`, `platform`), and conflict direction
  (last-write-wins MERGE on `(dgId, propertyName, project)`). The requirement's word
  **"and tested"** is what is missing.
  **Rationale:** re-specifying what is already normative would create a competing document. The
  phase writes the tests that hold the existing spec, and amends the spec only where a test
  proves it wrong.
  — **Reversibility:** reversible.

- **D-13: Full bidirectional per-platform conflict resolution stays DEFERRED; only last-write-wins
  is tested.** `spec/DG-ID.md` Conflict-policy direction explicitly defers it, and no requirement
  in `.planning/REQUIREMENTS.md` asks for it.
  **Rationale:** scope control — ALGN12-13 says conflict policy is "specified and tested", and the
  specified policy *is* last-write-wins. Implementing richer resolution would be a new capability.
  — **Reversibility:** reversible.

### Evidence and exit criteria (cross-cutting)

- **D-14: The CQ3 fixture is this phase's exit evidence and MUST demonstrate both directions;
  DE-01 extension is at the planner's discretion.** The fixture proves
  forward (rule/atom → governing parameter) and reverse (parameter → governing rules), project-
  scoped, mirroring `PAPER-C-032`'s shape.
  **Rationale:** the ROADMAP gate says *"both query directions are evidenced"* — that is a graph-
  query claim the fixture settles directly. Unlike 1202's D-16, a DE-01 leg is **not** obviously
  required here: identity and bridge claims are single-service (Neo4j via data-service), not
  cross-language verdict claims. The planner decides whether a DE-01 leg adds evidence or only
  cost. New fixture material goes in a **sibling path** — `fixtures/golden/fixture.json` stays
  frozen (1200 D-11, 1202 D-17).
  — **Reversibility:** one-way — this is a gate definition.

### Claude's Discretion

Within the decisions above, the planner retains discretion on:

- which body atom `ATTRIBUTE_OF` attaches to, and the reverse-query shape — D-04 requires the
  choice be **stated**, not which choice is made;
- the exact property set on the `ATTRIBUTE_OF` edge beyond D-03's project scope and derivation
  provenance;
- the precise length-prefix encoding format in D-09 (e.g. `len:value|len:value`), provided it is
  byte-identical across C# and Python and guarded by a shared golden vector;
- whether `/identity/mint` takes an explicit entity-kind argument or resolves it (D-10);
- whether the 3-arg `ComputeObjectStateId` is ultimately removed — allowed only as a separate
  evidenced decision (D-07);
- whether a DE-01 leg is added for the CQ3 fixture (D-14);
- the file split and naming for new fixture material under the sibling path;
- test-framework split between pytest and xUnit;
- plan/wave decomposition — note that D-08 and D-09 must be sequenced as one coordinated
  re-derivation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The decision this phase exists to make (ALGN12-14)
- `ontology/DesignGrammar-V7.md:707-713` — `dgc:attributeOf` TBox definition: domain `dgm:Atom`,
  range `dgc:Parameter`; bridge note at `:414`
- `ontology/DesignGrammar-V7.owl:2621-2626` — the same declaration in the OWL serialization
- `docs/reviews/theory-implementation-alignment/evidence/paper-claims.json` — **`PAPER-C-032`**
  (CQ3's single-row demonstration: `R_BUILDING_MIN_DISTANCE_12_V`/`A2`/`hasDistanceM` → `SepDist`),
  `PAPER-C-031` (bidirectional bridge claim), `PAPER-C-015` (six cross-layer bridges),
  `PAPER-C-004` (CQ1–CQ4 as acceptance criteria)
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md:36` —
  CQ3/`ATTRIBUTE_OF` finding; `:134` — the PAPER-C18 row
- `docs/reviews/theory-implementation-alignment/parts/paper.md:13,46,54` — CQ3's own disclaimers
  (records ComputGraph structure, **not** the visual-program solver) — the narrowing D-01 must
  preserve, not widen
- `spec/LPG-OWL-MAPPING.md` — TBox ↔ LPG bridge; `:186` IRI minting strategy

### The bridge as actually implemented (Correction 2)
- `llm/structure_rules.json` — `version`, `mappings`, **`inputBindings`** (2 entries today)
- `data-service/cg_input_bindings.py` — `:42-59` determinability classes and forbidden threshold
  keys; `:96-130` shape validation; `:187-215` loader; `:273-302` `read_rule_limit` Cypher;
  `:369-427` `classify_rule` → `parameterNames`; `:471-524` published-parameter filtering + WR-02
  missing-name handling
- `data-service/cg_paramstate_store.py:282-300` — accept-time re-classification and the CR-01
  override-scope note; `:336` MERGE on `StateId`+`project`
- `data-service/computgraph_publish.py:415` — `PARAM_LINK` wire-adjacency derivation (the
  derive-then-MERGE precedent D-02 follows); `:624` `:Parameter` MERGE; `:695` `PARAM_LINK` MERGE
- `data-service/cg_structure_checks.py:160-173` — dangling-`PARAM_LINK` check
- `cypher_template.txt:237-262` — `:Atom` MERGE keyed by `Atom_Id`
- `data-service/dg_context.py:1876-1881` — existing atom-type-discriminating traversal;
  `:1077-1092` `PARAM_LINK`-linked Interface resolution

### Identity contract (ALGN12-12, ALGN12-13)
- `spec/DG-ID.md` — **the authority D-06 extends.** `:15` native ids are bindings not identity;
  `:24` one `dgId` per counterpart set within one Design State; `:34-44` format/minting +
  `project|definitionId|cgId` hash input (**CR-02 target**); `:46-52` cross-language parity golden
  vector; `:55-64` **the normative pre-mint-before-publish seam CR-01 breaks**; `:70-80` rename
  re-mints; `:84-90` collision policy (belt-and-suspenders — the two-layer rule D-08 restores);
  `:94-140` `Representation` binding model, platform↔nativeIdKind, detach immutability;
  `:144-180` `SharedProperty` + last-write-wins conflict direction (D-12/D-13);
  `:184-200` partition decision + new schema surface; `:204-220` state of the art
- `DG_OBSIDIAN/knowledge/decisions/DG ID cross-platform identity scheme.md` — the ADR, including
  its *Open / deferred* section (member-GUID carry-forward escape hatch)
- `.planning/milestones/v9.0-phases/32.1-cross-platform-identity-and-mapping-dg-id/32.1-REVIEW.md`
  — **`:58-81` CR-01**, **`:84-100` CR-02**, `:102-105` WR-01, `:107-111` WR-02,
  `:113-117` WR-03, `:119-123` WR-04
- `docs/reviews/theory-implementation-alignment/gsd.md:39` — **`GSD-ALIGN-006`**, which routes
  CR-01/CR-02 here and forbids describing DGID-01..06 as unqualified release-ready

### Code this phase changes (all line numbers verified 2026-09-22)
- `DG/src/DG.Core/Models/Identity/DgIdMintingService.cs` — `:32-43` `Mint`, **`:41` the unescaped
  pipe join (CR-02)**, `:45-49` `HashToHex16`
- `data-service/dg_identity.py` — **`:53-64` `compute_dg_id`, `:61` the pipe join (CR-02)**;
  `:67-69` `PLATFORMS` / `NATIVE_ID_KINDS` enums; **`:166-191` `mint_identity`, `:178-181` the
  label-less MERGE (CR-01) with no `graph` tag (WR-01)**; `:195+` `resolve_native_id`
- `DG/src/DG.Core/Services/DesignStateIdGenerator.cs` — `:68-86` `ComputeParamStateId`;
  **`:94-97` `ComputeObjectStateId` 3-arg, no production callers (D-07)**;
  **`:98-131` `ComputeObjectStateIdFromRef` + its "why this exists alongside" rationale (D-07)**;
  `:142-160` `ComputePropStateId`; `:169-177` `ComputeDesignStateId`;
  `:198-209` `ComputeCaptureEventStateId` (1202 D-01); `:212+` `HashToHex16`.
  **None fold `project` (D-08); all share the CR-02 exposure (D-09)**
- `DG/src/DG.Grasshopper/Components/ObjectStateComponent.cs:141` — the live call site
- `data-service/dg_context.py:546-559` — `ALLOWED_PROPERTIES` dead constant (WR-03, D-11);
  `:661` `validate_cypher` which never references it
- `spec/DATABASE.md:336` — the wrong route/verb (WR-02, D-11)
- `DG/tests/DG.Tests/Identity/DgIdMintingServiceTests.cs:13` — golden vector using `"frame.gh"`
  (WR-04); `DG/tests/DG.Tests/DesignStateIdGeneratorTests.cs` — the 3-arg form's only callers

### Inherited contract this phase consumes (1200 / 1201 / 1202)
- `.planning/phases/1202-.../1202-CONTEXT.md` — **D-01 capture-event keying + `canonicalStateHash`
  (D-08 compounds this)**, D-03 additive-no-rewrite (D-08 mirrors it), **D-04 ObjState
  convergence — superseded by Correction 3 / D-07**, D-17 fixture-freeze sibling-path precedent
- `.planning/phases/1200-.../1200-CONTEXT.md` — D-03/D-04 additive + forbidden boolean→canonical
  inference; **D-11 fixture freeze**
- `.planning/phases/1201-.../1201-CONTEXT.md` — the DE-01-as-exit-evidence pattern D-14 declines
  to mandate
- `spec/EVIDENCE-CONTRACT.md`, `spec/evidence-contract.schema.json` — the frozen envelope
- `fixtures/golden/` — `fixture.json` (**frozen — do not edit**), `canonical-vectors.json`,
  `seed.cypher`, `MANIFEST.md`, `parser/`

### Milestone-level source of truth
- `.planning/ROADMAP.md:160-176` — Phase 1203 deliverables and gate wording
- `.planning/REQUIREMENTS.md:35-37` — ALGN12-12, ALGN12-13, ALGN12-14
- `.planning/milestones/v12.0-CONTEXT.md` — **D8 (both branches costed — superseded on the
  costing by Corrections 1 and 2, not on the framing)**; `<open_questions>` **#1 (`ATTRIBUTE_OF`
  normative?) and #7 (platform identity authority)** — both owned here and answered by D-01 and
  D-12; `<constraints>` (Alternative A locked; **no manuscript edits**); `<success_criteria>` item 5
- `.planning/PROJECT.md:63` — 1203 also owns the Phase 32.1 CR-01/CR-02 fixes

### Schema surfaces any structural change must sweep
- `CLAUDE.md` § Schema Change Propagation — **the mandatory list (D-05)**
- `ontology/dg-shapes.ttl` — 20 node shapes; **no `attributeOf` or `paramLink` shape exists today**
- `spec/RULE-PARTITION-POLICY.md` — SWRL-validator vs SHACL ownership
- `spec/DATABASE.md`, `spec/API.md`, `cypher_template.txt`, `training/dataset_schema.json`,
  `.github/copilot-instructions.md`, `README.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`inputBindings` resolution** (`cg_input_bindings.py:369-524`): already performs the exact
  rule→parameter join `ATTRIBUTE_OF` must persist, including published-`:Parameter` matching and
  missing-name reporting. D-02's derivation reuses it rather than reimplementing.
- **`PARAM_LINK` derive-then-MERGE** (`computgraph_publish.py:415,695`): the structural precedent
  for deriving a Computgraph edge from a non-graph source and MERGEing it project-scoped.
- **`read_rule_limit` traversal** (`cg_input_bindings.py:293-302`): established atom-type
  discrimination over `HAS_BODY`/`ARG` — the pattern D-04's attachment rule extends.
- **Cross-language golden-vector harness** (`spec/DG-ID.md:46-52`): the existing C#/Python parity
  mechanism D-09 must update in lockstep rather than invent.
- **`HashToHex16`** exists in three places (`DesignStateIdGenerator`, `DgIdMintingService`,
  plus `CanonicalJsonWriter`'s separate regime). **D-09 does not unify them** — it applies the same
  encoding fix to the two identity regimes; 1202 D-02 already ruled unification out of scope.

### Established Patterns
- **Additive-never-rewrite** (1200 D-03, 1202 D-03, Phase 823's "absence means not recorded, never
  an error") — D-08 follows it for historical IDs.
- **Project scoping on every MERGE key**, hardened by
  `migrations/2026-06-23_var_project_merge_key.cypher` — D-03 and D-08 both depend on it.
- **Frozen-fixture + sibling-path** (1200 D-11, 1201 D-16, 1202 D-17) — D-14 follows it.

### Integration Points
- `ATTRIBUTE_OF` spans the **Metagraph→Computgraph** boundary — the first bridge this milestone
  writes across layers. `REFERS_TO` (Atom→Class, Metagraph→Ontograph) is the existing analog the
  TBox comment explicitly names as the pattern to follow.
- `/identity/mint` and `/computgraph/publish` must be made to coincide (D-10) — both are live
  API surfaces documented in `spec/API.md`.
- The Grasshopper plugin requires a **dotnet rebuild** for any `DesignStateIdGenerator` change
  (D-08/D-09); ObjState IDs minted by an old plugin build against a new contract will not match.

### Environment caveats (from memory, still applicable)
- 4 `DesignStateValidationFlowTests` fail fast when Neo4j is down; 4 `test_dg_context.py` tests
  fail from the host because the `neo4j` hostname resolves only inside compose. Environment-
  dependent, **not** regressions.
- Verify the running container holds the code before trusting any live evidence run — compose
  reuses stale images.
- `docker exec` paths need `MSYS_NO_PATHCONV=1` under Git Bash.

</code_context>

<specifics>
## Specific Ideas

- **`PAPER-C-032`'s row is the fixture's shape**: `R_BUILDING_MIN_DISTANCE_12_V` / atom `A2` /
  `hasDistanceM` → parameter `SepDist`, type Variable. The CQ3 fixture should mirror this shape so
  the evidence is directly comparable to the manuscript's Table 6 claim.
- **Preserve CQ3's disclaimer.** `parts/paper.md:13,46,54` record that CQ3 deliberately claims
  representation, **not** solver equivalence. Evidence produced here must not be phrased as
  proving more than a populated, queryable bridge on one fixture.

</specifics>

<deferred>
## Deferred Ideas

| Idea | Routed to | Note |
|---|---|---|
| Property-level validation wired into `validate_cypher` | A future Cypher-validator phase | WR-03 resolved here by deletion (D-11); wiring it is a new capability |
| Full bidirectional per-platform conflict resolution | Not scheduled | Explicitly deferred by `spec/DG-ID.md`; D-13 tests last-write-wins only |
| Member-instance-GUID rename carry-forward escape hatch | Not scheduled | `spec/DG-ID.md:76` records it as a documented seam, out of scope since 32.1 |
| Removing the 3-arg `ComputeObjectStateId` | Allowed within this phase only as a separate evidenced decision | D-07 retains it by default |
| Unifying the three `HashToHex16` regimes | Not scheduled | 1202 D-02 ruled it out; D-09 fixes encoding without unifying |
| Real Revit connector; IFC export carrying `dgId` | Not scheduled | `spec/DG-ID.md` out-of-scope list since 32.1 |
| Manuscript/CQ3 wording edits | **v11.0 Phase 1107** | D-01 makes none necessary; v12.0 is forbidden from manuscript edits |
| ComputGraph structural-trace vs executable FBS semantics | **v11.0 Phase 1106** | Milestone open question #6 |
| Determinism / LLM reproducibility | **Phase 1204** | |
| Authorization, project isolation, direct-proxy exposure | **Phase 1205** | |
| Live Rhino/LLM/Speckle UAT | **v9.0 Phase 40** | GATE12-04 — v12.0 cannot mark these passed |
| `migrations/2026-07-07_validationgraph_to_validgraph.cypher` approval/run | Unowned, pre-existing | D-08 must not add a second unapproved migration |
| Graphify regeneration | Explicitly not in this milestone | Snapshot is behind HEAD (risk R-15) |

</deferred>

---

*Phase: 1203-identity-convergence-and-attribute-of-decision*
*Context gathered: 2026-09-22*
