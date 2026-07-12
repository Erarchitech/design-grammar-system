# Roadmap: Design Grammar System

## Milestones

- 🔄 **v8.2 Connector Integration & Reasoning Engine** — Phases 820-824 (active; started 2026-07-11; wires Grasshopper CONNECTOR to platform-issued credentials and replaces Reasoner placeholders with real OWL 2 DL (HermiT) + SHACL validation via a new isolated `dg-reasoner` sidecar)
- ✅ **v8.1 Platform Setup Regions** — Phases 810-816 (completed 2026-07-11; all 7 phases executed and verified; first milestone on the vX.Y → X·100+Y·10 phase-numbering convention; formal ship via `/gsd-complete-milestone` still pending) → [requirements](milestones/v8.1-REQUIREMENTS.md) | [roadmap](milestones/v8.1-ROADMAP.md)
- ✅ **v8.0 Design Grammars V2 UI** — Phases 21-27 (shipped 2026-07-07; Phase 27 Speckle 3D Embed added post-ship, completed 2026-07-08) → [requirements](milestones/v8.0-REQUIREMENTS.md) | [roadmap](milestones/v8.0-ROADMAP.md) | [phases](milestones/v8.0-phases/)
- ⏸ **v9.0 AI Workflow Intelligence** — Phases 28-40 (paused; Phase 28 executed 2026-07-06; restructured 2026-07-08: GH canvas → Computgraph serialization pipeline elaborated into Phases 32-37; renumbered from milestone-local 1-13) → [requirements](milestones/v9.0-REQUIREMENTS.md) | [roadmap](milestones/v9.0-ROADMAP.md) | [phases](milestones/v9.0-phases/)
- 📋 **v10.0 Script Intelligence** — Phases 41-49 (planned 2026-07-08, isolated; activates after v9.0; renumbered from milestone-local 1-9) → [requirements](milestones/v10.0-REQUIREMENTS.md) | [roadmap](milestones/v10.0-ROADMAP.md)
- 📋 **v4.0 BOT Ontology Bridge** — Phases 1-4 (planned) → [requirements](milestones/v4.0-REQUIREMENTS.md) | [roadmap](milestones/v4.0-ROADMAP.md)
- ✅ **v7.0 Update of DG Addin for Grasshopper** — Phases 13-20 (shipped 2026-07-05) → [requirements](milestones/v7.0-REQUIREMENTS.md) | [roadmap](milestones/v7.0-ROADMAP.md) | [phases](milestones/v7.0-phases/)
- ⛔ **v3.0 Typed Variables and Composable Design State** — Superseded 2026-07-02 (Phase 7 shipped, carried into v7.0) → [archive](milestones/v3.0-ROADMAP.md)
- ✅ **v2.0 DG Plugin - Design State and Validation Runs** — Phases 1-6 (shipped 2026-05-10) → [archive](milestones/v2.0-ROADMAP.md)
- ✅ **v1.1 Project Knowledge Graph** — Phases 1-7 (shipped 2026-04-10) → [archive](milestones/v1.1-phases/)

---
*v8.1 Platform Setup Regions detail archived to `milestones/v8.1-ROADMAP.md` on 2026-07-11 (all 7 phases complete and verified).*

## Milestone v8.2: Connector Integration & Reasoning Engine

**Goal:** Wire the Grasshopper CONNECTOR component to the platform's new credential mechanism, and replace the Reasoner screen's HermiT/Pellet placeholders with real OWL 2 DL + SHACL validation.

**Phase numbering:** 820–824 (convention: milestone vX.Y → phases from X·100+Y·10; max 10 per milestone; block 820–829 reserved for v8.2, phases 825–829 free for later insertion).

### Phase Overview

| # | Phase | Goal | Requirements | Depends on |
|---|-------|------|--------------|------------|
| 820 | Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping | 3/3 | Complete    | 2026-07-11 |
| 821 | dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation | 4/4 | Complete    | 2026-07-11 |
| 822 | OWL 2 DL Reasoning Integration + Reasoner Screen Wiring | 2/4 | In Progress|  |
| 823 | SHACL Validation Layer | Instance data is validated via SHACL alongside the existing SWRL VALIDATOR | SHCL-01, SHCL-02 | 821 |
| 824 | CONNECTOR Credential Integration | Grasshopper CONNECTOR authenticates with a platform-issued credential | CONNG-01, CONNG-02 | — |

### Phase 820: Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping

**Goal**: OWL reasoning work in later phases builds against a documented, real interpretation of DG's ontology data — not a schema so empty that any reasoner trivially reports "consistent".

**Depends on**: Nothing (first phase of v8.2)

**Requirements**: REAS-04

**Success Criteria** (what must be TRUE):

  1. PROJECT.md Key Decisions records the chosen axiom-scoping approach (extend LLM ingestion to emit real `subClassOf`/`domain`/`range`/`disjointWith` axioms vs. scope reasoning to structural/referential checks vs. a hybrid) with rationale
  2. A written LPG→OWL mapping spec exists covering edge-property reification for `Atom.ARG.pos` and `Rule.HAS_BODY/HAS_HEAD.order`, reviewable before Phase 821 implements the translator against it
  3. A spike against a real project's live OntoGraph data confirms whether a naive export would trivially report "consistent", and shows the chosen scoping approach avoids that false-positive outcome
  4. The sidecar-vs-embedded architecture decision (dedicated `dg-reasoner` service, isolated from `data-service`'s Speckle-publish/validation-run hot path) is confirmed and recorded as a Key Decision, unblocking Phase 821

**Plans**: 3/3 plans complete
**Wave 1**

- [x] 820-01-PLAN.md — Throwaway spike: label-scoped Neo4j→RDF export + two-part HermiT proof (naive trivially-consistent vs hybrid seeded-contradiction unsatisfiable)
- [x] 820-02-PLAN.md — `spec/LPG-OWL-MAPPING.md`: SWRL-vocabulary Metagraph mapping, edge-property reification (ARG.pos, HAS_BODY/HAS_HEAD.order), IRI minting, UNA handling

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 820-03-PLAN.md — `820-DECISION.md` + PROJECT.md Key Decisions (flip sidecar row, add hybrid axiom-scoping row)

### Phase 821: dg-reasoner Sidecar & OntoGraph/Metagraph RDF Translation

**Goal**: A new isolated `dg-reasoner` service is live in docker-compose and correctly translates the live Neo4j OntoGraph/Metagraph into RDF for both the OWL and SHACL paths.

**Depends on**: Phase 820

**Requirements**: REAS-05

**Success Criteria** (what must be TRUE):

  1. `dg-reasoner` runs as its own container in docker-compose (Python + headless JRE), with the `n10s` plugin installed on the `neo4j` service enabling RDF export — its failure or a hang never blocks a concurrent Speckle-publish or validation-run call to `data-service`
  2. A project-scoped Cypher→RDF export produces valid Turtle for a real project's OntoGraph + Metagraph, with fidelity tests confirming `Atom.ARG.pos` and `HAS_BODY/HAS_HEAD.order` survive the translation per Phase 820's mapping spec
  3. `POST /reason/consistency` and `POST /shacl/validate` routes exist on the sidecar and are reachable from `data-service`
  4. A real ontology export round-trips through Cypher export → RDFLib graph → Owlready2 → HermiT without error, proving the pipeline end-to-end (not just a toy fixture)

**Plans**: 4/4 plans complete

- [x] 821-01-PLAN.md
- [x] 821-02-PLAN.md
- [x] 821-03-PLAN.md
- [x] 821-04-PLAN.md

### Phase 822: OWL 2 DL Reasoning Integration + Reasoner Screen Wiring

**Goal**: Users can run a real OWL 2 DL consistency check from the Reasoner screen and trust the result, replacing the v8.1 placeholder.

**Depends on**: Phase 821

**Requirements**: REAS-06

**Success Criteria** (what must be TRUE):

  1. User clicks "Run check" on the Reasoner screen and a real HermiT consistency check executes against the translated OntoGraph, replacing the v8.1 "integration pending" placeholder label
  2. Result displays a clear pass/fail summary with unsatisfiable-class count, labeled distinctly as "schema consistency" so it is never mistaken for a design-compliance result
  3. A long-running or hung reasoning call times out and returns a distinct "unknown" result rather than silently reporting pass or fail, and never blocks the calling request synchronously
  4. Re-running the check after an ontology export change reflects updated results, not a cached/stale answer

**Plans**: 2/4 plans executed

- [x] 822-01-PLAN.md
- [x] 822-02-PLAN.md
- [ ] 822-03-PLAN.md
- [ ] 822-04-PLAN.md

**UI hint**: yes

### Phase 823: SHACL Validation Layer

**Goal**: Every validation run also checks DesignState/Rule instance data against SHACL shapes, with results architects can read without any semantic-web background.

**Depends on**: Phase 821

**Requirements**: SHCL-01, SHCL-02

**Success Criteria** (what must be TRUE):

  1. On each validation run, DesignState/Rule instance data is translated to RDF and validated against SHACL shapes, running alongside — not replacing — the existing SWRL-based VALIDATOR
  2. A documented rule-partition/precedence policy states which rule categories are checked by SHACL vs. the SWRL VALIDATOR, so no business rule is authored twice with disagreeing verdicts
  3. SHACL violations surface through DG's existing ErrorMessageTemplates (What+Where+How-to-fix) — raw RDF/SHACL vocabulary (`sh:focusNode`, `sh:sourceShape`) never reaches the architect
  4. Violation severity (info/warning/violation) displays with a Solibri-style red/orange/yellow treatment

**Plans**: TBD

**UI hint**: yes

### Phase 824: CONNECTOR Credential Integration

**Goal**: The Grasshopper CONNECTOR component authenticates with a platform-issued credential instead of only raw Neo4j credentials, with clear in-canvas feedback when that credential fails.

**Depends on**: Nothing (independent of Phases 820–823, safe to build in parallel)

**Requirements**: CONNG-01, CONNG-02

**Success Criteria** (what must be TRUE):

  1. CONNECTOR exposes a new optional platform-credential/token input; the existing Neo4jURI/User/Password/Database inputs and the component's GUID are unchanged, so saved `.gh` canvases keep working without rewiring
  2. Pasting a valid token minted from the v8.1 Connectors screen's "Grasshopper" connector type authenticates a heartbeat call to `data-service`
  3. An invalid, revoked, or expired token produces a clear in-canvas runtime message via the existing `AddRuntimeMessage`/ErrorMessageTemplates pattern, never a silent failure or crash
  4. The raw credential/token is never persisted inside the `.gh` file or written to logs/status text in plaintext

**Plans**: TBD

---
*Roadmap created: 2026-07-11 — milestone v8.2 Connector Integration & Reasoning Engine*
