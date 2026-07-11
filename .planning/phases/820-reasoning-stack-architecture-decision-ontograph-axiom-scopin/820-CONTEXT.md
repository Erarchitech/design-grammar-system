# Phase 820: Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping - Context

**Gathered:** 2026-07-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 820 produces the decisions and specifications the rest of v8.2's reasoning work builds against — it ships documents and spike evidence, not production code. Deliverables: (1) the axiom-scoping decision recorded in PROJECT.md Key Decisions, (2) a written LPG→OWL mapping spec covering edge-property reification, (3) a spike against live OntoGraph data proving the naive-export false-positive and showing the chosen scoping avoids it, (4) the sidecar-vs-embedded decision confirmed. No dg-reasoner service, no n10s install, no UI changes — those are Phases 821+.

</domain>

<decisions>
## Implementation Decisions

### Axiom-Scoping Approach
- **Hybrid scoping**: union the static `DesignGrammar-V7.owl` TBox (real axioms: 69 subClassOf, 105 domain, 112 range, 235 class decls) with the live project-scoped OntoGraph export, plus structural/referential checks over the live graph. Extending LLM ingestion to emit axioms is explicitly deferred (avoids mid-milestone n8n prompt churn + 9-file schema propagation).
- **Curate `disjointWith` axioms into the static TBox once** — the V7 export currently has zero disjointness axioms, so consistency checking cannot meaningfully fail without them. Curated disjointness (design-time artifact) is what makes HermiT's answer non-trivial.
- **Two-part spike proof**: (a) naive flat export of live OntoGraph → HermiT reports "consistent" trivially (documents the false positive); (b) chosen hybrid approach with a seeded contradiction (e.g. class asserted under two disjoint parents) → HermiT flags the unsatisfiable class. Both outputs captured as evidence.
- **Spike runs against live docker Neo4j** using a real project's OntoGraph (pick the project with the most rules), per the success criterion's "live OntoGraph data" wording.
- **Sidecar decision confirmed, not re-litigated**: the research-recommended `dg-reasoner` sidecar (already a Pending Key Decision in PROJECT.md) is confirmed and flipped to decided, with spike evidence attached. Only re-open if the spike surfaces a blocking issue.

### LPG→OWL Mapping Spec
- **Metagraph maps to the standard W3C SWRL RDF vocabulary**: `swrl:Imp` for Rule, `rdf:List` encodes `HAS_BODY`/`HAS_HEAD` `order`, `swrl:argument1`/`swrl:argument2` encode `ARG.pos` (research confirmed near-1:1 mapping, low risk). No custom reification vocabulary.
- **IRI strategy**: reuse the stored `iri` property where present (Class, DatatypeProperty, ObjectProperty, Builtin); mint deterministic IRIs for Rule/Atom/Var/Literal under the V7 ontology namespace with a project-scoped path segment (e.g. `{base}/project/{project}/rule/{Rule_Id}`).
- **UNA handling**: the spec mandates `owl:AllDifferent` over minted named individuals per project export, explicitly documenting OWL's no-unique-name-assumption gap (research Pitfall 5).
- **Spec location**: `spec/LPG-OWL-MAPPING.md` — durable, lives next to DATABASE.md, reviewable by Phase 821 before the translator is implemented. Normative for OntoGraph + Metagraph; includes an **informative** ValidGraph (DesignState/Run → RDF) sketch marked as Phase 823 input.

### Spike Mechanics & Deliverables
- **Spike code is throwaway**: standalone scripts in the phase dir (`spike/` subfolder) with a pinned `requirements.txt`. Explicitly NOT the seed of dg-reasoner — Phase 821 builds clean against the spec.
- **Export tooling in spike**: direct Cypher reads via the Python neo4j driver + rdflib graph construction. No n10s install in this phase (n10s is an 821 success criterion; the spike tests semantics, not export tooling).
- **Spike runtime**: local venv + JRE 17 for HermiT (Owlready2 shells out to the bundled JAR); exact reproduction steps documented in a spike README so Phase 821 can re-run it.
- **Decision documentation**: PROJECT.md Key Decisions rows (per success criteria) + a concise `820-DECISION.md` in the phase dir capturing spike evidence (axiom counts, HermiT output before/after), linked from the PROJECT.md rationale.

### Claude's Discretion
- Choice of which real project's data the spike runs against (pick the one with the most rules/atoms in live Neo4j).
- Exact seeded-contradiction construction for the spike's part (b), as long as it demonstrates a non-trivial unsatisfiability the naive export misses.
- Internal structure/headings of `spec/LPG-OWL-MAPPING.md`, as long as edge-property reification (`ARG.pos`, `HAS_BODY/HAS_HEAD.order`), IRI minting, and UNA handling are normatively covered.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ontology/DesignGrammar-V7.owl` (182KB) — static meta-schema TBox with real axioms (69 subClassOf, 105 domain, 112 range, 235 owl:Class), the anchor of the hybrid union; zero disjointWith today
- `data-service/reasoner.py` — v8.1 JSON-settings pattern (`GET/PUT /reasoner/settings`), the persistence precedent later phases extend
- `cypher_template.txt` + `training/dataset_schema.json` — schema v4 single source of truth the mapping spec must stay consistent with
- Research corpus at `.planning/research/` (STACK/ARCHITECTURE/FEATURES/PITFALLS/SUMMARY) — library choices (Owlready2 0.51, pySHACL 0.40.0, RDFLib 7.6.0), pitfalls, and the sidecar-vs-embedded tradeoff analysis already done

### Established Patterns
- Graph schema v4: OntoGraph nodes carry `iri` (Class/DatatypeProperty/ObjectProperty), Metagraph nodes keyed by `Rule_Id`/`Atom_Id`; relationships `HAS_BODY`/`HAS_HEAD` carry `order`, `ARG` carries `pos`
- Project isolation via `project` property on every node — any export must be project-scoped
- Key Decisions live in PROJECT.md as table rows with Decision/Rationale/Outcome columns
- Schema changes propagate across 9 files (CLAUDE.md list) — a reason to avoid touching LLM ingestion this milestone

### Integration Points
- PROJECT.md Key Decisions table — two v8.2 rows already Pending (sidecar; CONNECTOR additive credential): Phase 820 confirms the sidecar row
- `spec/` directory — where the durable LPG→OWL mapping spec lands
- Live Neo4j (docker compose, ports 7474/7687) — spike data source
- Phase 821 consumes: the mapping spec + confirmed sidecar decision + spike reproduction steps

</code_context>

<specifics>
## Specific Ideas

- The spike must produce before/after HermiT evidence: naive export = trivially consistent; hybrid + seeded disjointness violation = unsatisfiable class detected. This evidence is what makes the Key Decision defensible.
- Disjointness curation happens in the static TBox (one-time design artifact), not in the ingestion pipeline.

</specifics>

<deferred>
## Deferred Ideas

- Extending LLM ingestion (n8n prompts) to emit `subClassOf`/`domain`/`range`/`disjointWith` axioms on rule ingest — deferred out of v8.2; revisit if the hybrid's static-TBox curation proves insufficient in practice.

</deferred>
