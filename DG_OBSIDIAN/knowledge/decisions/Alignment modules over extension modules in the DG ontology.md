---
tags: [decision, ontology, alignment, T1, IFC, BOT, Topologic]
date: 2026-09-07
status: approved at the gate — paper leads, ontology/ follows
supersedes: the three-extension-module architecture of R14.x–R15.1
---

# Alignment modules over extension modules

**Decision.** The Design Grammar ontology is delivered as a core module plus **three
alignment modules and no extension module**. Every external vocabulary is referenced at its
published identifier and retains its own namespace; the project deposits only the mapping
axioms it authors.

## The terminology, and why it changed

The paper cites **Janowicz et al. (2019)** for its core-plus-extension pattern while using the
wrong term from that very source. SOSA/SSN distinguishes:

- **core module** — the minimal domain vocabulary
- **extension module** — *adds* vocabulary to the core
- **alignment module** — carries **mapping axioms only**, separately named and versioned

By §2.2's own description the DG modules *"carry the alignment axioms to external
vocabularies"* — they are alignment modules. Calling them extension modules conflated two
kinds the cited source deliberately separates, and that conflation is what made the deposit
question look hard.

## The architecture

| Module | Vocabulary | Question it answers | Attaches at |
|---|---|---|---|
| **Topology** | `top:` — `http://w3id.org/topologicpy#` | how does this relate spatially? | the core's **Topology** concept |
| **Classification** | **IFC**, referenced through **bSDD** | what kind of entity does this term denote? | the minted **Ontograph** class |
| **Standards** | W3C / OGC — SWRL, PROV-O, SOSA, SHACL, SKOS, DCTERMS, GeoSPARQL | how is this expressed and provenanced? | core and rule layer |

**Two attachment points, not merely two vocabularies.** That is what makes the split
non-overlapping: even if both vocabularies contained a "Wall", one types the *topological
entity* at the core band while the other classifies the *vocabulary term* at the Ontograph.

**Declared non-alignments**, each with its reason: geometry (OMG/FOG — geometry travels as a
platform representation), property states (OPM — the Design State is a whole-configuration
checkpoint, not per-property history), and classification via BPO (IFC is reached instead).

## Why BOT is subsumed rather than bridged or removed

`top:` carries **25 `rdfs:subClassOf` + 4 `rdfs:subPropertyOf`** axioms to BOT, so a DG→BOT
bridge would be a second path to a vocabulary the topology module already reaches. BOT remains
**cited** — as the layer `top:` extends, and as the origin of the topology/classification
division the schema adopts. That division is BOT's own: its scope statement limits it to
*"referential topological concepts"*, `bot:Element` is left unconstrained by design, and
classification is delegated to a named sibling module, PRODUCT/BPO.

## Why IFC takes classification and not relations

**BOT exists because ifcOWL's relationship model is unusable for lightweight linked data.**
ifcOWL reifies every relation into `IfcRel*` objects; 1,331 classes and 1,599 properties
against BOT's 7 and 14. Giving IFC the *relational* role would reintroduce the full
serialisation that **Table 1 [P71]** — *"Low — no full IfcOWL serialisation required"* — sells
as the paper's differentiator.

**The size objection has two halves, and only one is dissolved by an LLM.** Search over ~800
IFC 4.3 entities is tractable through bSDD's keyword search (`SearchList`, GraphQL
`classSearch`) — that is the *authoring* half. The *reasoning* half is dissolved by
**reference, not import**: bSDD identifiers add one annotation triple per aligned class.

## Deposit rule

> The project deposits the modules it authors — the core and its alignment modules. External
> vocabularies are referenced at their published identifiers and remain external to the deposit.

## Known risks, recorded

- **`top:` is unversioned** — no `owl:versionInfo`, `owl:versionIRI` or `dcterms` date, served
  from GitHub Pages behind a `w3id.org` redirect at package version 0.9.x. The alignment records
  a retrieval date instead. Stated in §6.1 as a handled risk.
- **`skos:closeMatch` is not subsumption.** No reasoner infers `dg:X ⊑ bot:Space` from a SKOS
  match plus `top:Space ⊑ bot:Space`. The paper claims **resolvability, never inference** — do
  not strengthen that verb.
- **`top:` declares no transitive or symmetric characteristics**, where `bot:containsZone` is
  transitive and `bot:adjacentZone` symmetric. The schema evaluates containment and adjacency as
  GQL/Cypher paths, so little is lost.

## Consequence for the repository

`ontology/` does **not** implement this and must be rebuilt to match: dissolve the BOT bridge
and the locally-declared Topologic module, add the IFC classification alignment, rename modules
by kind. **The direction of fit is paper → artifacts** — see [[T1 — Онтологический фреймворк]].
A stale claim in the manuscript — *"thereby adapting Topologic to formal OWL"* — is removed by
this decision, since a published OWL Topologic exists.

## Links

- [[2026-09-07 T1 R15.2 — AU-R151-TOPO alignment-module architecture]]
- Plan: `Publications/T1_ITcon_DG_Draft_R15.2_revision-plan.md` §6A.2–6A.5
