---
tags: [decision, v9.0, phase-32.1, identity, computgraph]
date: 2026-07-13
---

# Phase 32.1: DG ID cross-platform identity design

## Context

v9.0's Computgraph pipeline (Phases 32–37) gives Design Grammars its first Grasshopper-canvas-native data layer. But the moment a downstream connector (Revit, IFC, Speckle) generates or receives a counterpart of a GH-authored object, the system needs a way to say "this Revit wall *is* that Grasshopper wall" — and to let properties computed on one platform (e.g. a Ladybug-derived insulation value, computable only in Grasshopper) become visible from the other platform's representation. No existing DG identifier (the Phase 32 `cgId`, Neo4j node ids, native GUIDs) survives a platform boundary by design.

## Decision

Introduce a durable, platform-neutral **`dgId`** as the identity spine for every Computgraph entity, with native platform ids demoted to *representations* bound to it.

1. **`dgId` wraps `cgId`, doesn't replace it.** Minted as `dg:` + SHA-256-hex16 of `project|definitionId|cgId`, reusing the exact `HashToHex16` pattern already shipped in `DesignStateIdGenerator` (DS_/OS_/PS_ prefixes). `project` is folded directly into the hash input, not just a composite Cypher MERGE key — this repo already shipped and had to fix a cross-project Var-collision bug from exactly this class of mistake (v2.0/v3.0 era).
2. **Representations live in a registry, not on the entity.** A dedicated `Representation` node (platform, `nativeIdKind`, native id value, connector, `boundAt`) related via `HAS_REPRESENTATION` to the owning entity — not flat properties on the Computgraph node. Every system surveyed (Speckle's applicationId-as-join-key, BHoM's `RevitIdentifiers` fragment, IFC GlobalId as the sole persistent token) independently converges on "identity tracking is separate from the native id," never folded into the object itself.
3. **Attach and detach are both first-class.** A representation binds to a dgId (`bind`) and can later unbind (`detach`) without ever mutating the dgId — modeled directly on Rhino.Inside.Revit's tracking-mode semantics (Enabled:Update vs. "Release," which forgets a binding without deleting the underlying identity concept).
4. **Revit binds via `UniqueId`, never `ElementId`.** Revit's `ElementId` is session/project-local and can change on model operations (central-model reload, etc.); `UniqueId` (episode GUID + element-id tail) is the durable identifier — the `nativeIdKind` default for the Revit platform in the registry.
5. **Shared properties are provenanced records, not overwrites.** A `SharedProperty` keyed by `dgId` carries `platform`/`connector`/timestamp per write — the Ladybug-insulation scenario (GH computes it, Revit reads it) needs to know *where* a value came from, not just its current value. Conflict resolution across simultaneous platform writes is deliberately deferred — only the policy *direction* is documented in this phase.
6. **Rename re-mints by default.** If a convention-tagged entity's name changes, its `dgId` is re-minted (not preserved) unless a future escape hatch (member-GUID matching, à la Rhino.Inside's tracking) is built — explicitly out of this phase's MVP, but the spec documents the seam for a later phase.
7. **`Representation`/`SharedProperty` nodes live under `graph:'Computgraph'`** — no new graph partition introduced for identity.
8. **Real Revit connector is out of scope.** This phase proves the full contract (mint → bind → resolve → shared-property read/write → detach) against a *simulated* second-platform consumer (a fabricated Revit UniqueId, no live Rhino/Revit). The actual Revit-side connector is future-milestone work (dedicated connector milestone, or the v4.0 BOT Ontology Bridge).

## Rationale

Researched against the state of the art via Perplexity MCP (two user-named targets: Rhino.Inside.Revit, Speckle) plus the surrounding landscape (IFC GlobalId, Revit UniqueId internals, BHoM adapter fragments):

- **Rhino.Inside.Revit** proves output-level binding + explicit release semantics is a workable UX for GH↔Revit tracking, and that `ElementId` is the wrong stability anchor.
- **Speckle** demonstrates the content-hash-vs-stable-id split (`id` vs `applicationId`) is the right shape for update-in-place across versions — but also exposes the gap DG ID must close: Speckle's own Grasshopper connector cannot reliably supply a stable `applicationId`, because Grasshopper has no native persistent-id concept to draw from. DG ID must mint one deterministically instead of relying on the platform to provide it.
- **BHoM/IFC** confirm the two-layer "canonical pipeline id + registry of native bindings" pattern as the safer general design versus deterministic-only minting, especially once derived/generated counterpart objects (the GH→Revit generation case) enter the picture — derived objects should bind to an *existing* identity, not mint a fresh one that happens to look similar.

## Consequences

- Phase 36 (Computgraph Persistence) inherits a normative constraint: its publish MERGE key must include `cgId` (alongside `definitionId`+`project`) so pre-minted registry nodes (created via `/identity/mint` ahead of a full publish) and Phase 36's published nodes coincide as one node rather than duplicating. Recorded in `spec/DG-ID.md` and in Plan 32.1-03's `mint_identity` docstring for Phase 36 planning to pick up.
- `cgContextJson v1` and `statePayloadJson v2` both gain `dgId` as a strictly additive, nullable field — no version bump, no breakage of pre-32.1 readers.
- Schema-propagation checklist (CLAUDE.md standing rule) gets an explicit Wave-3 plan (32.1-07) rather than being left implicit, covering `cypher_template.txt`, `dataset_schema.json`, `spec/DATABASE.md`, CLAUDE.md schema tables, `ontology/dg-shapes.ttl` SHACL shapes, and the Phase 29 Cypher-validator allow-lists.

## Related

- [[sessions/2026-07-13 Phase 32.1 DG ID cross-platform identity planning|session log]]
- [[decisions/Phase 16 DesignState aggregate and statePayloadJson v2|Phase 16: statePayloadJson v2 — the additive-envelope precedent this phase reuses]]
- [[DCM ComputationGraph as 5th ontology layer|Computgraph as the 5th ontology layer — the layer this identity scheme is anchored to]]
