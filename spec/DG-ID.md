# DG ID — Cross-Platform Identity Specification

**Version:** 1.0
**Status:** Normative (Phase 32.1)
**Date:** 2026-07-18
**Requirements:** DGID-01 (documented format/minting/rename/collision), DGID-06 (ADR positioning)
**ADR:** `DG_OBSIDIAN/knowledge/decisions/DG ID cross-platform identity scheme.md`

---

## Overview

`dgId` is the durable, platform-neutral identity anchor for every design object extracted from the Grasshopper canvas into the Computgraph. It is the single token that makes the *same conceptual design object* one object across platforms: a parametric wall defined in Grasshopper and the BIM wall generated from it in Revit share **one** `dgId`.

Native platform identifiers (Grasshopper instance GUID, Revit `UniqueId`, IFC `GlobalId`, Speckle `applicationId`) are **representations bound to** a `dgId` in a registry — never a stand-in for identity itself. This is the converged lesson across every system surveyed (see [State of the Art](#state-of-the-art) and the ADR): identity is a separate, durable token; native ids are bindings tracked alongside it, not folded into the object.

This document is the normative contract. The implementation plans (`DG.Core.Models.Identity`, `data-service/dg_identity.py`, the schema-propagation sweep in Plan 07) implement exactly what is written here.

---

## Purpose & Scope

- `dgId` is the durable identity spine. It survives platform boundaries by design; no native id does.
- **Normative same-dgId contract (LOCKED):** counterpart objects across platforms share ONE `dgId` *within one Design State*. A Grasshopper parametric wall and the Revit BIM wall generated from it MUST resolve to the same `dgId` when observed through the DesignState that captured both representations.
- **In scope (32.1):** the identity format, deterministic minting, rename/stability rules, cross-project collision policy, the binding model (`Representation` nodes), shared-property semantics with conflict direction, and the graph-partition placement.
- **Out of scope (deferred):** the real Revit connector (proven here against a simulated consumer), bidirectional per-platform conflict resolution, IFC export carrying `dgId`, and the member-GUID rename escape hatch (see [Rename & Stability](#rename--stability-rules) and the ADR).

---

## Format & Minting

`dgId` = the literal prefix `dg:` followed by the **first 16 uppercase hexadecimal characters** of the SHA-256 digest over the UTF-8 bytes of the length-prefix-encoded string:

```
dgId = "dg:" + UPPER(HEX(SHA-256(UTF-8( EncodeHashInput(project, definitionId, cgId) ))))[0..16]
```

- **Hash input (exact order):** `project`, `definitionId`, `cgId` — three components, in that order, combined through the **length-prefix encoding contract** below (Phase 1203, D-09/CR-02) rather than a naive pipe-join.
- **Example shape:** `dg:9F2A4C1E7B03D5A8` (prefix + 16 hex chars).
- The mechanism reuses the `HashToHex16` pattern already shipped in `DG.Core.Services.DesignStateIdGenerator` (`Convert.ToHexString(SHA256.HashData(...))[..16]`) — zero new dependency, byte-identical to the existing house pattern.

### Length-prefix hash-input encoding (Phase 1203, D-09 / CR-02)

**This is the single normative encoding contract for every dgId and every DesignState id in this system.** It replaced a naive pipe-join (`"{a}|{b}|{c}"`) that allowed a pipe character embedded in any one component to shift the boundary between components, producing a hash collision between two semantically different input tuples (CR-02).

**Rule, precise enough to reimplement byte-for-byte:** for each component, in order, emit the component's character length in invariant decimal, then a colon, then the component's raw text; join the resulting units with a single pipe (`|`) character.

- A component that is present (even as an empty string) emits `{length}:{text}` — an empty string emits the unit `0:` (length zero, colon, no trailing text).
- A component that is **absent** (`null` / `None`) emits the literal unit `-1:` — this is how a null component is distinguished from an empty one: `0:` (empty string, length 0) and `-1:` (null, sentinel length -1) can never collide, and neither can collide with any real length-prefixed unit, because a real component's length is always ≥ 0.
- Length is counted in UTF-16 characters on the C# side (`string.Length`) and in Unicode code points on the Python side (`len(str)`) — the two counting conventions agree for every input this system's identity components actually carry (ASCII/BMP project names, definitionIds, and cgIds); no astral-plane characters are expected here.
- Because every unit is preceded by an unambiguous length, a pipe (or any other character) inside a component's raw text can never be mistaken for a component boundary — this is what closes CR-02.

**Worked example (the canonical adversarial pair from the CR-02 regression tests):** the two triples `("a|b", "c", "d")` and `("a", "b|c", "d")` both naively join to the identical string `a|b|c|d` under the old scheme. Under the length-prefix encoding they diverge: `("a|b","c","d")` → `3:a|b|1:c|1:d`, while `("a","b|c","d")` → `1:a|3:b|c|1:d` — distinct strings, distinct hashes.

**Twinned implementations (must never drift independently):**

| Language | Symbol |
|---|---|
| C# | `DG.Core.Models.Identity.DgIdMintingService.EncodeHashInput` and `DG.Core.Services.DesignStateIdGenerator.EncodeHashInput` (identical copies of the same rule) |
| Python | `data-service.dg_identity._encode_hash_input` |

A **shared golden vector** (a fixed `(project, definitionId, cgId)` triple and its expected `dgId`) and a shared collision regression (the worked adversarial pair above) guard parity across both languages; any edit to the encoding rule in one language MUST be mirrored in the other.

**Known, deliberately out-of-scope divergence:** `canonical_json.hash_scalar_tuple` (Python) and `DG.Core.Contracts.CanonicalJsonWriter.HashScalarTuple` (C#) are a **third, independent** hashing implementation that still uses the pre-CR-02 naive pipe-join. Their doc-comments claim byte-for-byte parity with `Mint`/`compute_dg_id`; that claim is now **false** and is recorded here as a known open gap (Phase 1203 Plan 02), not resolved by this document or this phase. A future plan must either extend the length-prefix encoding to that third implementation or explicitly document the two conventions as intentionally divergent and correct the stale claim in both doc-comments.

### Single source of truth (cross-language parity anchor)

> The hash-input contract (component set `project`, `definitionId`, `cgId`, in that order, combined via the length-prefix encoding above) is the **SINGLE source of truth** that BOTH implementations follow:
>
> - `DG.Core.Models.Identity.DgIdMintingService` (C#, mints at canvas-extraction time inside the plugin), and
> - the data-service `compute_dg_id` (Python, mints/verifies on the publish and `/identity/mint` paths).
>
> A **shared golden vector** (a fixed `(project, definitionId, cgId)` triple and its expected `dgId`) guards parity: both a C# xUnit test and a Python pytest assert the same triple produces the same `dgId`. Any drift in field set, order, encoding rule, hash, casing, or truncation length breaks the golden vector and fails CI in both runners.

### The `definitionId` ambiguity — resolved (WR-04)

**`definitionId` is the GH document id (`CgDefinition.DocumentId`, sourced from `doc.DocumentID.ToString()` at canvas extraction), NOT the file name (`CgDefinition.FileName` / `doc.DisplayName`).** Confirmed directly in `DG.Core.Services.CgContextDgIdAssigner.AssignDgIds`, which reads `context.Definition.DocumentId` (never `FileName`) into the local `definitionId` used for every `DgIdMintingService.Mint` call in that method. `CgDefinition` (`DG.Core.Models.Computgraph.CgContext.cs`) carries both fields side by side — `DocumentId` and `FileName` are genuinely distinct properties on the same object, populated from different GH document accessors (`doc.DocumentID` vs. `doc.DisplayName`) — so the ambiguity is a real one this spec must pin, not a naming accident.

The golden-vector and collision-regression test constants in both languages use filename-shaped literals (e.g. `"frame.gh"`, `"wall.gh"`) as the `definitionId` argument. These are opaque test literals chosen for readability, not evidence that production code passes a file name — the test helper functions (`Mint`, `compute_dg_id`) accept `definitionId` as an untyped string and mint identically regardless of which real-world field a caller supplies. The production caller (`CgContextDgIdAssigner`) is the authority on what `definitionId` actually is at runtime, and it is the document id.

### Relationship to `cgId`

`dgId` **extends** Phase 32's `cgId` — it hashes *over* `cgId` (`cg:<alg>:<kind>:<conventionName>`), it does not replace or parallel-mint it. There is one deterministic-input contract to maintain (Phase 32's annotation grammar → `cgId`), and `dgId` is a pure function of it plus `project` and `definitionId`. Minting `dgId` independently of `cgId` is an explicit anti-pattern (see the ADR's rejected alternatives).

### Persistence seam (normative for Phase 36)

The identity API's `mint_identity` anchors on the node match pattern `(cgId, definitionId, project)`:

```cypher
MERGE (e {cgId: $cgId, definitionId: $definitionId, project: $project})
SET   e.dgId = $dgId
```

> **Phase 36 constraint (normative):** the Computgraph publish MERGE key MUST include `cgId` — alongside `definitionId` + `project`, consistent with CGPD-02's "definition id + convention name" contract — so that a pre-minted registry node (created via `/identity/mint` ahead of a full publish) and the node written by Phase 36's publish path **coincide as ONE node**, never duplicate. A publish MERGE keyed on `definitionId`+`project` alone would create a second node and orphan the pre-minted `dgId`.

---

## Rename & Stability Rules

**Default (normative for Phase 32.1): rename re-mints.**

| Change | Effect on `cgId` | Effect on `dgId` |
|--------|------------------|------------------|
| Re-extract an **unchanged** definition (no convention-name changes) | identical `cgId` | **identical `dgId`** (determinism — the free re-extraction stability property) |
| **Rename** a convention group (e.g. `11_Var_SpansCount` → `11_Var_Count`) | `cgId` changes (name-derived per Phase 32) | **`dgId` re-mints** by default |

Determinism means no first-write persistence step is needed for two extractions to agree on the same `dgId` — this directly satisfies the "identical dgIds across re-extractions" success criterion.

### Stability escape hatch — FUTURE, out of scope for 32.1

A **member-instance-GUID carry-forward** escape hatch is recorded here as a documented seam only, **not implemented in 32.1**: if the minting service detects that the member instance GUIDs of a renamed entity exactly match a previously-minted `dgId`'s last-known member set, it could carry the old `dgId` forward (recording the rename in an audit trail) rather than re-minting. This is analogous to Rhino.Inside.Revit's `Enabled:Update` tracking mode (match a prior binding, update in place) versus `Release` (forget, mint new). It is deferred future refinement — see the ADR's *Open / deferred* section for rationale.

---

## Collision Policy

Cross-project `dgId` collisions are prevented by **belt-and-suspenders** defense:

1. **`project` is folded into the hash input** (length-prefix-encoded `project, definitionId, cgId`), so two different projects tagging structurally identical definitions with the same convention name produce **distinct** `dgId`s.
2. **Every registry Cypher query includes `project` in its `MATCH`/`MERGE` key** — defense in depth, never relying on the hash alone.

This applies the lesson of the shipped v2.0/v3.0 `Var` cross-project merge-key collision bug (`migrations/2026-06-23_var_project_merge_key.cypher`), whose fix added `project` to the merge key. Folding `project` into the hash *and* scoping every query is the more defensive of the two precedents already in this codebase. `DgIdMintingService` unit tests assert two projects with an identical `cgId` produce different `dgId`s.

### Project-in-hash for DesignState ids (Phase 1203, D-08) — which functions receive it, and why some do not

The same belt-and-suspenders defense extends to DesignState id minting, restoring the two-layer collision defense for that surface. `project` is an **optional trailing parameter** on the three per-member minting functions that can legitimately obtain one:

| Function | Takes `project`? | Reason |
|---|---|---|
| `ComputeParamStateId` | Yes (optional, default `null`) | Folded into the hash when supplied |
| `ComputeObjectStateIdFromRef` | Yes (optional, default `null`) | Folded into the hash when supplied — this is the canvas-capture-authoritative form (see [ObjState Authority Contract](#objstate-authority-contract-d-07) below) |
| `ComputePropStateId` | Yes (optional, default `null`) | Folded into the hash when supplied |
| `ComputeObjectStateId` (3-arg) | **No** — and this is correct, not an oversight | Its project-in-hash obligation is already satisfied by its existing `projectId` argument (one of its original three parameters), so it takes no *additional* parameter |
| `ComputeDesignStateId` (aggregate) | No | Concatenates sorted member StateIds with no separator at all — not pipe-joined, so CR-02 does not apply, and `project` reaches it transitively through its members' own StateIds |
| `ComputeCaptureEventStateId` (aggregate) | No | Same aggregate reasoning as `ComputeDesignStateId`; project reaches it transitively through members |

**Honestly, which functions do NOT receive a project, and why:** none of the three shipping Grasshopper capture components (`ObjectStateComponent`, `ParameterStateComponent`, `PropertyStateComponent`) has a Project input port or a project field in its `SolveInstance` scope (confirmed on disk, Phase 1203-02). Each currently calls its minting function with `project` left `null` — synthesizing a fake project value to fill the parameter would satisfy the signature in name while destroying its meaning, since a wrong project value is worse than an honestly-absent one. Wiring a Project input port into these components is a Grasshopper canvas/UX change requiring re-wiring and live Rhino verification; that work is explicitly routed to a later phase (GATE12-04 / v9.0 Phase 40), not done here.

---

## Binding Model

A native platform identifier is bound to a `dgId` as a dedicated **`Representation`** node — not as a flat property on the owning entity. One entity may eventually bind N platforms simultaneously (Revit *and* IFC *and* Speckle), and each binding carries its own provenance.

### `Representation` node

```
(:Representation {
   platform: "Revit",              // Grasshopper | Revit | IFC | Speckle
   nativeIdKind: "UniqueId",       // InstanceGuid | UniqueId | GlobalId | ApplicationId
   nativeId: "<native id string>",
   connector: "revit-sim",
   boundAt: datetime(),
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `platform` | enum | `Grasshopper` \| `Revit` \| `IFC` \| `Speckle` |
| `nativeIdKind` | enum | `InstanceGuid` \| `UniqueId` \| `GlobalId` \| `ApplicationId` |
| `nativeId` | string | The platform-native identifier value |
| `connector` | string | The connector that created the binding (provenance) |
| `boundAt` | datetime | When the binding was created (provenance) |
| `graph` | string | Always `Computgraph` (see [Partition Decision](#partition-decision)) |
| `project` | string | Project isolation key |

### Platform ↔ nativeIdKind

| Platform | `nativeIdKind` | Notes |
|----------|----------------|-------|
| Grasshopper | `InstanceGuid` | The GH document instance GUID |
| **Revit** | **`UniqueId`** | **Never `ElementId`** — see below |
| IFC | `GlobalId` | The 22-char compressed base64 GUID from `IfcRoot` |
| Speckle | `ApplicationId` | The stable per-application id, not the content-hash `id` |

> **Revit binds `UniqueId`, never `ElementId` (load-bearing).** Revit's `ElementId` is an integer that is **not stable** across upgrades and workset operations (e.g. Save To Central) and may change; `UniqueId` (episode GUID + element-id tail) is the durable identifier. Any Revit `Representation` MUST set `nativeIdKind = UniqueId`. A Revit `nativeId` that is a plain integer is a specification violation.

### Binding relationship & immutability

```
(:Computgraph entity {dgId})  -[:HAS_REPRESENTATION]->  (:Representation)
```

**Attach and detach never rewrite `dgId`.** Binding a representation (`bind`) and later unbinding it (`detach`) are registry-row operations on the `HAS_REPRESENTATION` edge and the `Representation` node — they never mutate the owning entity's `dgId`.

---

## Shared-Property Semantics

A property computed on one platform becomes readable from any representation bound to the same `dgId`. This is the locked acceptance scenario: the Grasshopper panel computes an insulation value with Ladybug components and writes it to the Computgraph; through the shared `dgId`, that property becomes available to the panel's Revit representation, which could not compute it natively.

### `SharedProperty` node

Keyed by `dgId` + `propertyName` + `project`:

```
(:SharedProperty {
   dgId: "dg:9F2A4C1E7B03D5A8",
   propertyName: "insulation",
   value: 2.4,
   platform: "Grasshopper",
   connector: "gh-plugin",
   writtenAt: datetime(),
   graph: "Computgraph",
   project: "1"
})
```

| Property | Type | Description |
|----------|------|-------------|
| `dgId` | string | Identity the property is attached to (key part) |
| `propertyName` | string | The shared property name (key part) |
| `value` | any | The computed value |
| `platform` | string | Platform that computed the value (provenance) |
| `connector` | string | Connector that wrote it (provenance) |
| `writtenAt` | datetime | Write timestamp (provenance) |
| `graph` | string | Always `Computgraph` |
| `project` | string | Project isolation key (key part) |

```
(:Computgraph entity {dgId})  -[:HAS_SHARED_PROPERTY]->  (:SharedProperty)
```

A read is keyed by `dgId` and is **platform-agnostic**: a value written from Grasshopper is read identically "as Revit," and the returned provenance shows `platform = Grasshopper` — proving cross-platform visibility.

### Conflict-policy direction

**MVP is last-write-wins.** A `MERGE` on `(dgId, propertyName, project)` followed by `SET` means the most recent write for a given property replaces the prior value. Full bidirectional, per-platform authoritative conflict resolution (two platforms competing to write the same property) is **explicitly deferred** — see the ADR's *Open / deferred* section and the phase Deferred Ideas. This document pins only the *direction* (last-write-wins), which is all Phase 32.1 requires.

---

## Partition Decision

`Representation` and `SharedProperty` nodes live under **`graph:'Computgraph'`** — **not** a new graph partition.

This is a **locked Phase 32.1 decision** (resolving RESEARCH Open Question 2). Rationale: identity is an extension of the Computgraph layer, and keeping these labels within the existing partition minimizes the schema-propagation surface (no fifth graph partition to thread through `cypher_template.txt`, `dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md schema tables, and the Cypher-validator allow-lists). Plan 32.1-07 propagates these two new labels, their two relationships, and the two enums across those schema surfaces.

### New schema surface introduced by this spec

| Kind | Name | Under `graph` |
|------|------|---------------|
| Node label | `Representation` | `Computgraph` |
| Node label | `SharedProperty` | `Computgraph` |
| Relationship | `HAS_REPRESENTATION` (entity → Representation) | — |
| Relationship | `HAS_SHARED_PROPERTY` (entity → SharedProperty) | — |
| Enum | `platform` = `Grasshopper` \| `Revit` \| `IFC` \| `Speckle` | — |
| Enum | `nativeIdKind` = `InstanceGuid` \| `UniqueId` \| `GlobalId` \| `ApplicationId` | — |

Every Computgraph entity additionally gains a `dgId` property (strictly additive, nullable on pre-32.1 nodes).

---

## DesignState Identity (Phase 1202/1203)

This section extends this document's authority (ALGN12-12) beyond `dgId` to cover **DesignState id minting** — the `OS_`/`DS_`/`PS_`-prefixed StateIds produced by `DG.Core.Services.DesignStateIdGenerator`. Before this section, these minting functions were governed by nothing but their own doc-comments; this document is now the one place that answers how any identity in this system is minted, not only `dgId`.

### The four DesignState id families and their two aggregate functions

| Prefix | Kind | Minting function(s) | Content |
|---|---|---|---|
| `OS_` | ObjState | `ComputeObjectStateId` (3-arg, per-rule-variable) and `ComputeObjectStateIdFromRef` (canvas-capture, per-geometry-instance) — see [ObjState Authority Contract](#objstate-authority-contract-d-07) below | Object + Geometry + Label |
| `DS_` | ParamState | `ComputeParamStateId` | Parameters list (sliders, toggles) |
| `PS_` | PropState | `ComputePropStateId` | Rule + DataProperty + PropValue |
| `DS_` | DesignState (aggregate) | `ComputeDesignStateId` (content-addressed, Layer 2) and `ComputeCaptureEventStateId` (capture-event node key, Layer 1) | Sorted member StateIds (+ capture timestamp for the capture-event form) |

Note that `ParamState` and the aggregate `DesignState` share the `DS_` prefix; they are distinguished by hash-input domain (parameter-list content vs. member-StateId concatenation), not by prefix, exactly as `DesignStateIdGenerator`'s own doc-comment records.

### ObjState Authority Contract (D-07)

**Both ObjState minting forms are retained — neither is deleted, deprecated, or scheduled for removal.** They serve genuinely different cases:

- **`ComputeObjectStateIdFromRef(objectRef, classIri, project=null)` is authoritative for canvas-captured, per-geometry-instance ObjStates** — this is the shipping path used by the OBJECT STATE Grasshopper component. It hashes what that component actually has on its canvas (an `objectRef` and a resolved `classIri`), with `project` folded in when supplied. A null `classIri` (captured before a class is wired) hashes against a stable sentinel rather than crashing or hashing an empty string, so the id stays deterministic. Label is deliberately NOT folded in — renaming an object's display Label no longer changes its ObjState identity; only its structural `objectRef`/`classIri` do.
- **`ComputeObjectStateId(projectId, objectInstanceId, variableName)` (3-arg) is the per-rule-variable form (CMPST-07)** — Object variables shared across rules, keyed by project + instance + variable name. It is retained and documented here, **currently with no production caller**. It exists for a different addressing scheme than the capture path and is not a legacy artifact awaiting removal.

**Why both are needed, not just one:** the shipping `ObjectStateComponent` has no Project input port and no per-geometry per-rule variable-name concept in its canvas scope. Synthesizing fake values for either input would satisfy the 3-arg form's signature in name while destroying the meaning its own doc-comment promises (a specific per-rule-variable addressing scheme). `ComputeObjectStateIdFromRef` is the form actually shaped to what the capture component has available; the 3-arg form remains the correct tool for a future caller that genuinely has project + instance + variable-name inputs.

### Encoding contract

Every DesignState minting function that was previously pipe-joined (`ComputeObjectStateId`, `ComputeObjectStateIdFromRef`, `ComputePropStateId`, `ComputeParamStateId`) now routes through the same length-prefix `EncodeHashInput` contract documented in [Format & Minting](#length-prefix-hash-input-encoding-phase-1203-d-09--cr-02) above — see that section for the precise, reimplementable rule (including null-vs-empty handling) and the twinned C#/Python implementation table. `ComputeDesignStateId` and `ComputeCaptureEventStateId` are the two exceptions: they concatenate sorted member StateIds with no separator at all (not pipe-joined in the first place), so the CR-02 fix does not apply to them, and their pinned test literal (`DS_3C3C50530BE1DED0`) is genuinely byte-unchanged by Phase 1203, not merely re-asserted for convenience.

**SHA-256 here is content-addressing, not an authenticity control** — this framing, already normative for `dgId` above, extends unchanged to every DesignState id: none of these hashes are a signature or MAC, and none should be treated as tamper-evident.

### Migration policy — pre-1203 ids are pre-contract, and are NOT rewritten

**IDs minted before Phase 1203 used the pre-length-prefix (naive pipe-join) encoding and did not fold `project` into the DesignState hash.** They remain valid, are documented here as **pre-contract**, and are explicitly **NOT migrated**:

- No migration script is added by this phase or any phase referencing this document, for either `dgId` or DesignState ids.
- A recapture of the *same* design under the new contract yields a **different** id than the pre-1203 capture did — this is expected, not a defect. The old id and the new id both remain individually valid and resolvable; they are simply not the same id, because they were minted under two different, explicitly-versioned contracts.
- This mirrors the same additive, no-rewrite treatment `DesignStateIdGenerator`'s own doc-comment already establishes for the two-layer capture-event vs. content-hash distinction (D-01/D-03): historical rows stay as-is, only new writes adopt the new contract.

### Confirmation, not re-specification (ALGN12-13)

Per D-12, the platform authority, detach, provenance, and conflict policies documented above ([Binding Model](#binding-model), [Shared-Property Semantics](#shared-property-semantics)) are already normative in this file, and Phase 1203 Plan 03 added test coverage that holds them (`test_mint_then_bind_then_publish_preserves_binding`, `test_mint_identity_tags_graph_computgraph`, `test_ambiguous_bind_rejected`). No prose in those sections needed amendment — none of Plan 03's tests proved any existing statement wrong. Per D-13, richer per-platform conflict resolution (two platforms competing to write the same shared property) remains **explicitly deferred** — this document does not specify it, and no reader should infer it is implemented.

### `/identity/mint` and `entity_kind` (CR-01, Phase 1203 Plan 03)

`mint_identity`'s anchor MERGE is now **label-aware**: it upserts on `(:<entity_kind> {cgId, definitionId, project})`, where `entity_kind` must be one of `ENTITY_KINDS = (Object, Procedure, Pattern, Parameter, Interface)` — confirmed directly against `computgraph_publish.py`'s five publish writers, each of which MERGEs on the identical labelled three-part key. Before this fix the anchor was label-less (`MERGE (e {cgId, definitionId, project})`), so a pre-publish mint and the later publish MERGE addressed two different nodes, silently orphaning any binding attached before publish (CR-01, closed). Minted nodes also now carry `graph = 'Computgraph'` (WR-01, closed). The full request/response contract for `POST /identity/mint`, including `entity_kind`'s allowed values, is documented in `spec/API.md`.

---

## State of the Art

`dgId` is not a novel invention — it is DG's instance of a pattern the entire BIM/VPL interop space has converged on: **identity is separate from native id.** Each surveyed system keeps a durable identity token distinct from the volatile native identifier. Full rationale and citations are in the ADR (`DG ID cross-platform identity scheme.md`).

| System | Durable identity | Volatile / native id | DG's position |
|--------|------------------|----------------------|---------------|
| **Rhino.Inside.Revit** | tracked binding (`UniqueId`) via Element Tracking | `ElementId` (session/project-local, unstable) | `dgId` is the durable anchor; native ids are tracked bindings — DG mirrors the split |
| **Speckle** | `applicationId` (stable, external); proxies reference by it | `id` (content hash — changes on content change) | `dgId` is analogous to `applicationId`; the `Representation` registry is analogous to Speckle proxies |
| **IFC** | `GlobalId` (22-char compressed base64 GUID in every `IfcRoot`) | — | DG treats IFC `GlobalId` as one `nativeIdKind`, not as DG's own identity |
| **Revit `UniqueId`** | `UniqueId` (episode GUID + element-id tail, durable) | `ElementId` (unstable across upgrades/workset ops) | DG binds `UniqueId`, never `ElementId` |
| **BHoM** | `RevitIdentifiers` fragment / `PersistentId` (kept out of the geometry object) | in-model element id | DG's `Representation` node is the same separation — identity metadata off the object |

**Convergent lesson:** every mature system keeps identity separate from native id. The one thing this spec **forecloses** is ever treating a native platform id (GH instance GUID, Revit `ElementId`) as a stand-in for durable identity in future connector work.

---

## Valid Until / Propagation

- **Valid until:** the schema surface changes. Any change to the node labels, relationships, enums, or the `dgId` property is a **schema change** subject to the CLAUDE.md schema-propagation checklist.
- **Propagation owner:** Plan 32.1-07 syncs `cypher_template.txt`, `dataset_schema.json`, n8n workflow prompts (where applicable), `spec/DATABASE.md`, CLAUDE.md schema tables, `ontology/dg-shapes.ttl` SHACL shapes, and the Phase 29 Cypher-validator allow-lists to match this spec.
- **Cross-language parity:** the golden vector (see [Format & Minting](#single-source-of-truth-cross-language-parity-anchor)) must remain green in both the C# and Python test suites whenever the minting contract is touched.
- **Single identity authority (ALGN12-12, Phase 1203):** this document is the one place that governs BOTH id families — `dgId` (Computgraph entity identity) and DesignState ids (`OS_`/`DS_`/`PS_` StateIds) — including the shared length-prefix encoding contract both are built on, the ObjState dual-form authority split, and the no-rewrite migration policy for pre-1203 ids. No second identity specification document exists or should be created; any future identity-related decision extends this file.
