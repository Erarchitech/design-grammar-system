---
tags: [decision, adr, v9.0, phase-32.1, identity, computgraph, interop]
date: 2026-07-18
phase: 32.1
requirement: DGID-06
spec: spec/DG-ID.md
---

# DG ID cross-platform identity scheme

> ADR for DGID-06. This note positions the DG ID scheme against the surveyed state of the art with explicit rationale. It references `spec/DG-ID.md` for the normative rules (format, minting, binding, collision, shared-property semantics) and does not restate them in full. For the phase's locked design decisions see [[Phase 32.1 DG ID cross-platform identity design]].

## Context

Design Grammars becomes a cross-platform system: the same conceptual design object exists as different native representations on different platforms — a parametric wall in Grasshopper, the BIM wall in Revit generated from it, its Speckle-published copy, an IFC export. The system needs a way to say "this Revit wall *is* that Grasshopper wall," and to let a property computed on one platform (e.g. a Ladybug-derived insulation value, computable only in Grasshopper) become visible from another platform's representation. No existing DG identifier survives a platform boundary by design: the Phase 32 `cgId` is a content-addressed convention id, Neo4j node ids are storage-internal, and native GUIDs are platform-scoped.

Four external systems have already solved variants of this problem, and were surveyed for this decision (per the locked research mandate — Rhino.Inside.Revit and Speckle as the two named study targets, IFC / Revit `UniqueId` / BHoM as the neighboring art):

- **Rhino.Inside.Revit** — Element Tracking; `ElementId` (unstable) vs `UniqueId` (durable).
- **Speckle** — `id` (content hash, mutable) vs `applicationId` (stable, external); proxies referencing by `applicationId`.
- **IFC** — `GlobalId`, a 22-char compressed base64 GUID baked into every `IfcRoot`.
- **Revit `UniqueId`** — episode GUID + `ElementId` tail.
- **BHoM** — a separate `RevitIdentifiers` fragment carrying `PersistentId`, matched on push/pull, kept out of the geometry object.

**The converged industry lesson:** identity is a separate, durable token; native platform ids are *representations bound to it*, tracked in a registry / fragment / proxy — never folded into the object's own content. This is not a DG-specific invention; it is the convergent answer across the whole BIM/VPL interop space. This repo also learned the underlying lesson the hard way in v2.0/v3.0 (the `Var` cross-project merge-key collision bug): conflating identity with a native/local key causes either duplicate elements or silent cross-scope collisions.

## Decision

Introduce `dgId` as the durable, platform-neutral identity spine, with native platform ids demoted to representations bound to it. Normative detail lives in `spec/DG-ID.md`; the load-bearing choices:

- **`dgId` is deterministic and extends `cgId`.** `dgId` = `dg:` + the first 16 hex chars of `SHA-256(project|definitionId|cgId)`, reusing `DesignStateIdGenerator`'s `HashToHex16` pattern. It hashes *over* Phase 32's `cgId` rather than being independently minted — one deterministic-input contract, not two. Determinism gives re-extraction stability for free (no first-write persistence step).
- **Bindings are a registry, not flat properties.** A dedicated `Representation` node (`platform`, `nativeIdKind`, `nativeId`, `connector`, `boundAt`) related via `HAS_REPRESENTATION` — one entity can bind N platforms, each with its own provenance.
- **Shared properties are provenanced records.** A `SharedProperty` node keyed by `dgId` + `propertyName` + `project` carries `value` + `platform` / `connector` / `writtenAt`, so a cross-platform read knows *where* a value came from. MVP conflict policy is last-write-wins; bidirectional resolution deferred.
- **Identity API in data-service.** `mint` / `resolve` / `bind` / property read-write over parameterized, project-isolated Cypher — one authoritative service every current and future connector speaks, so cross-platform identity cannot silently fork.

## Positioning Against the State of the Art

### Rhino.Inside.Revit — Element Tracking, `ElementId` vs `UniqueId`

Rhino.Inside.Revit's Element Tracking makes a Grasshopper component *remember and update* the Revit elements it created across document sessions, with explicit modes (`Enabled:Update` matches a prior binding and updates in place; `Release` forgets the binding and mints fresh, causing duplicates on rerun). Critically, it anchors durability on `UniqueId`, not `ElementId`.

**DG's choice:** DG mirrors the split — `dgId` is the durable anchor, and native ids are *tracked bindings* in the `Representation` registry, exactly as Rhino.Inside tracks the Revit elements a GH component created. The Update/Release mode distinction is the direct prior art for DG's **deferred rename escape hatch**: a future "match by prior member-GUID set, carry the `dgId` forward" behavior is the analogue of `Enabled:Update`, whereas Phase 32.1's default (rename re-mints) is the analogue of `Release`. This is why the escape hatch is a documented seam, not vaporware — it has a proven UX precedent.

### Speckle — `id` (content hash) vs `applicationId` (stable) + proxies

Speckle keeps two identifiers: `id` is a content hash that **changes** whenever object content changes, while `applicationId` is a stable, externally-supplied id used to match a received object to a previously-created native element for update-in-place. Proxies are stored at the Root Collection level and reference objects by `applicationId` (not `id`), so relationships persist even when object content changes.

**DG's choice:** `dgId` is analogous to Speckle's `applicationId` — the stable identity that survives content changes — and the `Representation` registry is analogous to Speckle's proxy references. Speckle also exposes the *gap* DG ID must close: Speckle's own Grasshopper connector cannot reliably supply a stable `applicationId`, because Grasshopper has no native persistent-id concept to draw from. DG therefore **mints one deterministically** (from `project|definitionId|cgId`) instead of relying on the platform to provide it.

### IFC — `GlobalId` (22-char compressed base64 GUID in `IfcRoot`)

Every `IfcRoot` subtype carries a `GlobalId`, a 22-character compressed base64 encoding of a 128-bit GUID — a persistent, globally-unique token baked into the object at authoring time.

**DG's choice:** DG treats IFC `GlobalId` as **one `nativeIdKind`** (`GlobalId`) bound to a `dgId` via a `Representation` row — a representation of the identity, not the identity itself. DG does not adopt `GlobalId` as its own identity because DG-authored objects originate in Grasshopper, which has no `IfcRoot` to draw a `GlobalId` from; the IFC id only exists once an IFC export representation is created. (IFC export carrying `dgId` back out — e.g. into a property set — is deferred future connector work.)

### Revit `UniqueId` — episode GUID + `ElementId`

Revit's `UniqueId` is an episode GUID plus an `ElementId` tail and is **stable**; `ElementId` alone is a session/project-local integer that "is not stable across upgrades and workset operations such as Save To Central, and might change."

**DG's choice:** DG binds Revit's `UniqueId`, **never `ElementId`**. The Revit `Representation` sets `nativeIdKind = UniqueId`; a plain integer as a Revit `nativeId` is a spec violation. Binding `ElementId` would reintroduce exactly the volatility every durable-identity system was designed to avoid — the same class of mistake as treating Speckle's content-hash `id` as stable.

### BHoM — `RevitIdentifiers` fragment / `PersistentId`

BHoM keeps identity/correspondence metadata in a separate `RevitIdentifiers` **fragment** (where `PersistentId` maps to Revit's `UniqueId`), deliberately *not* folded into the geometry object; the adapter matches on push/pull using that fragment.

**DG's choice:** DG's `Representation` node is the same separation under a different name — identity/binding metadata lives off the entity, in its own node, carrying provenance. This is the direct precedent for choosing a dedicated node label over flat native-id properties on the Computgraph entity.

## Alternatives Considered & Rejected

| Alternative | Why rejected |
|-------------|--------------|
| **UUID/GUID minted once and persisted** | Requires a first-write-wins persistence step before any two extractions can agree on the same id; loses the free re-extraction stability that a deterministic hash gives (DGID-01). Deterministic minting matches the shipped `DesignStateIdGenerator` precedent. |
| **Native ids as flat properties on the entity node** (`revitUniqueId`, `ifcGlobalId`, …) | Doesn't scale past one binding per platform, can't carry per-binding provenance (`connector`, `boundAt`), and contradicts the worked example where one object may bind Revit **and** IFC **and** Speckle simultaneously. Blocks multi-platform binding; loses provenance. |
| **Minting `dgId` independently of `cgId`** | Creates a second parallel deterministic-input contract to keep in sync with Phase 32's annotation grammar — every grammar change would need updating in two places. `dgId` wraps `cgId`, it does not duplicate its logic. |
| **Writing the shared-property value directly onto the `Parameter`/entity node with a plain `SET`** | Destroys the write history needed for the conflict-policy note and for auditing *which* platform computed a value. `SharedProperty` records preserve provenance per write. |
| **Relying on a project-scoped MERGE key alone (no `project` in the hash)** | This is precisely the shape that caused the shipped v2.0 `Var` cross-project collision bug. `project` is folded into the hash **and** kept in every MERGE key — belt and suspenders. |

## Consequences

- **Cross-platform property flow becomes possible for the first time** — the Ladybug-insulation worked example (GH computes, Revit reads) is realizable; this is the identity spine every future connector milestone depends on.
- **Every future connector must resolve against the same registry** (the data-service identity API), or cross-platform identity silently forks. This is a standing constraint on all downstream connector work.
- **Phase 36 inherits a normative MERGE-key constraint:** its publish key must include `cgId` (alongside `definitionId` + `project`) so pre-minted registry nodes and published nodes coincide as one node — recorded in `spec/DG-ID.md`.
- **The one thing this forecloses:** ever treating a native platform id (GH instance GUID, Revit `ElementId`) as durable identity in future work.
- `cgContextJson v1` and `statePayloadJson v2` gain `dgId` as a strictly additive, nullable field — no version bump, no breakage of pre-32.1 readers.

## Open / Deferred

- **Rename stability escape hatch (member-GUID carry-forward)** — the `Enabled:Update`-analogue behavior that would preserve a `dgId` across a rename by matching prior member-instance-GUID sets. Documented seam only in 32.1; default remains rename-re-mints. Deferred pending a discuss-phase confirmation that the more sophisticated behavior is wanted (see `spec/DG-ID.md` §Rename & Stability and Assumptions Log A1).
- **Bidirectional per-platform conflict resolution** — two platforms writing the same shared property with authoritative-source arbitration. MVP is last-write-wins; full resolution deferred.
- **IFC export carrying `dgId`** — writing `dgId` back out into an IFC property set or `IfcGloballyUniqueId` context. Future connector work.
- **Real Revit connector** — 32.1 proves the contract (mint → bind → resolve → shared-property read/write → detach) against a *simulated* Revit-side consumer (a fabricated `UniqueId`, no live Rhino/Revit). The real connector is future-milestone work (dedicated connector milestone or the v4.0 BOT Ontology Bridge).

## Sources

- [Rhino.Inside.Revit — Revit Elements guide](https://www.rhino3d.com/inside/revit/beta/guides/revit-elements) — Element Tracking overview, `ElementId` instability vs `UniqueId` stability.
- [mcneel/rhino.inside-revit GitHub — revit-elements.md](https://github.com/mcneel/rhino.inside-revit/blob/1.x/docs/pages/_en/beta/guides/revit-elements.md) — source-of-truth tracking guide.
- [Revit API Docs — UniqueId Property](https://www.revitapidocs.com/2022/f9a9cb77-6913-6d41-ecf5-4398a24e8ff8.htm) — "`ElementId`… is not stable across upgrades and workset operations… `UniqueId` is stable."
- [Speckle Docs — Core Concepts](https://docs.speckle.systems/developers/data-schema/concepts) — `id` (content hash) vs `applicationId` (stable, cross-version); proxies referencing objects by `applicationId` at the Root Collection level.
- [Speckle Community — Object Ids are changed in different commits](https://speckle.community/t/object-ids-are-changed-in-different-commits/3065) — confirms `id` mutability on content change.
- [buildingSMART Technical — IFC GUID](https://technical.buildingsmart.org/resources/ifcimplementationguidance/ifc-guid/) — 22-character compressed base64 encoding, rationale, `IfcGloballyUniqueId` scope.
- [IFC 4.3.2 Documentation — IfcGloballyUniqueId](https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcGloballyUniqueId.htm) — formal schema definition.
- [BHoM Documentation — BHoM vs Revit Identity](https://bhom.xyz/documentation/Guides-and-Tutorials/Visual-Programming-with-BHoM/Revit%20Toolkit/Revit%20Adapter/BHoM%20vs%20Revit%20Identity/) — `RevitIdentifiers` fragment, `PersistentId` = Revit `UniqueId`, matched on push/pull.
- [BHoM Documentation — Revit Adapter Details](https://bhom.xyz/documentation/Guides-and-Tutorials/Coding-with-BHoM/Revit%20Toolkit/Revit%20Adapter%20Details/) — adapter-level identity handling context.

## Related

- [[Phase 32.1 DG ID cross-platform identity design]] — the phase decision log (the eight locked decisions this ADR positions).
- [[DCM ComputationGraph as 5th ontology layer]] — the Computgraph layer this identity scheme anchors to.
- [[Phase 16 DesignState aggregate and statePayloadJson v2]] — the additive-envelope precedent reused for the additive `dgId` field.
- `spec/DG-ID.md` — the normative specification.
