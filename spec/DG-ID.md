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

`dgId` = the literal prefix `dg:` followed by the **first 16 uppercase hexadecimal characters** of the SHA-256 digest over the UTF-8 bytes of the pipe-joined string:

```
dgId = "dg:" + UPPER(HEX(SHA-256(UTF-8( project | definitionId | cgId ))))[0..16]
```

- **Hash input (exact order):** `project | definitionId | cgId` — three fields joined by the literal pipe character `|`, in that order, with no surrounding whitespace.
- **Example shape:** `dg:9F2A4C1E7B03D5A8` (prefix + 16 hex chars).
- The mechanism reuses the `HashToHex16` pattern already shipped in `DG.Core.Services.DesignStateIdGenerator` (`Convert.ToHexString(SHA256.HashData(...))[..16]`) — zero new dependency, byte-identical to the existing house pattern.

### Single source of truth (cross-language parity anchor)

> The hash-input contract `project|definitionId|cgId` (this exact field set, order, and pipe delimiter) is the **SINGLE source of truth** that BOTH implementations follow:
>
> - `DG.Core.Models.Identity.DgIdMintingService` (C#, mints at canvas-extraction time inside the plugin), and
> - the data-service `compute_dg_id` (Python, mints/verifies on the publish and `/identity/mint` paths).
>
> A **shared golden vector** (a fixed `(project, definitionId, cgId)` triple and its expected `dgId`) guards parity: both a C# xUnit test and a Python pytest assert the same triple produces the same `dgId`. Any drift in field set, order, delimiter, hash, casing, or truncation length breaks the golden vector and fails CI in both runners.

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

1. **`project` is folded into the hash input** (`project|definitionId|cgId`), so two different projects tagging structurally identical definitions with the same convention name produce **distinct** `dgId`s.
2. **Every registry Cypher query includes `project` in its `MATCH`/`MERGE` key** — defense in depth, never relying on the hash alone.

This applies the lesson of the shipped v2.0/v3.0 `Var` cross-project merge-key collision bug (`migrations/2026-06-23_var_project_merge_key.cypher`), whose fix added `project` to the merge key. Folding `project` into the hash *and* scoping every query is the more defensive of the two precedents already in this codebase. `DgIdMintingService` unit tests assert two projects with an identical `cgId` produce different `dgId`s.

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
