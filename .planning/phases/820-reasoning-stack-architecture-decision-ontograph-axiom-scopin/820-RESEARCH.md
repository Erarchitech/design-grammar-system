# Phase 820: Reasoning-Stack Architecture Decision & OntoGraph Axiom Scoping - Research

**Researched:** 2026-07-11
**Domain:** OWL 2 DL reasoning scoping decision + LPG→OWL (Neo4j property-graph → RDF/OWL) mapping specification, verified against this project's live Neo4j data
**Confidence:** MEDIUM-HIGH (library/version facts VERIFIED live this session; the axiom-scoping decision itself is a project decision already locked in CONTEXT.md, not something to re-derive; live-data characterization below is VERIFIED against the running docker Neo4j instance)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Axiom-Scoping Approach**
- **Hybrid scoping**: union the static `DesignGrammar-V7.owl` TBox (real axioms: 69 subClassOf, 105 domain, 112 range, 235 class decls) with the live project-scoped OntoGraph export, plus structural/referential checks over the live graph. Extending LLM ingestion to emit axioms is explicitly deferred (avoids mid-milestone n8n prompt churn + 9-file schema propagation).
- **Curate `disjointWith` axioms into the static TBox once** — the V7 export currently has zero disjointness axioms, so consistency checking cannot meaningfully fail without them. Curated disjointness (design-time artifact) is what makes HermiT's answer non-trivial.
- **Two-part spike proof**: (a) naive flat export of live OntoGraph → HermiT reports "consistent" trivially (documents the false positive); (b) chosen hybrid approach with a seeded contradiction (e.g. class asserted under two disjoint parents) → HermiT flags the unsatisfiable class. Both outputs captured as evidence.
- **Spike runs against live docker Neo4j** using a real project's OntoGraph (pick the project with the most rules), per the success criterion's "live OntoGraph data" wording.
- **Sidecar decision confirmed, not re-litigated**: the research-recommended `dg-reasoner` sidecar (already a Pending Key Decision in PROJECT.md) is confirmed and flipped to decided, with spike evidence attached. Only re-open if the spike surfaces a blocking issue.

**LPG→OWL Mapping Spec**
- **Metagraph maps to the standard W3C SWRL RDF vocabulary**: `swrl:Imp` for Rule, `rdf:List` encodes `HAS_BODY`/`HAS_HEAD` `order`, `swrl:argument1`/`swrl:argument2` encode `ARG.pos` (research confirmed near-1:1 mapping, low risk). No custom reification vocabulary.
- **IRI strategy**: reuse the stored `iri` property where present (Class, DatatypeProperty, ObjectProperty, Builtin); mint deterministic IRIs for Rule/Atom/Var/Literal under the V7 ontology namespace with a project-scoped path segment (e.g. `{base}/project/{project}/rule/{Rule_Id}`).
- **UNA handling**: the spec mandates `owl:AllDifferent` over minted named individuals per project export, explicitly documenting OWL's no-unique-name-assumption gap (research Pitfall 5).
- **Spec location**: `spec/LPG-OWL-MAPPING.md` — durable, lives next to DATABASE.md, reviewable by Phase 821 before the translator is implemented. Normative for OntoGraph + Metagraph; includes an **informative** ValidGraph (DesignState/Run → RDF) sketch marked as Phase 823 input.

**Spike Mechanics & Deliverables**
- **Spike code is throwaway**: standalone scripts in the phase dir (`spike/` subfolder) with a pinned `requirements.txt`. Explicitly NOT the seed of dg-reasoner — Phase 821 builds clean against the spec.
- **Export tooling in spike**: direct Cypher reads via the Python neo4j driver + rdflib graph construction. No n10s install in this phase (n10s is an 821 success criterion; the spike tests semantics, not export tooling).
- **Spike runtime**: local venv + JRE 17 for HermiT (Owlready2 shells out to the bundled JAR); exact reproduction steps documented in a spike README so Phase 821 can re-run it.
- **Decision documentation**: PROJECT.md Key Decisions rows (per success criteria) + a concise `820-DECISION.md` in the phase dir capturing spike evidence (axiom counts, HermiT output before/after), linked from the PROJECT.md rationale.

### Claude's Discretion
- Choice of which real project's data the spike runs against (pick the one with the most rules/atoms in live Neo4j).
- Exact seeded-contradiction construction for the spike's part (b), as long as it demonstrates a non-trivial unsatisfiability the naive export misses.
- Internal structure/headings of `spec/LPG-OWL-MAPPING.md`, as long as edge-property reification (`ARG.pos`, `HAS_BODY/HAS_HEAD.order`), IRI minting, and UNA handling are normatively covered.

### Deferred Ideas (OUT OF SCOPE)
- Extending LLM ingestion (n8n prompts) to emit `subClassOf`/`domain`/`range`/`disjointWith` axioms on rule ingest — deferred out of v8.2; revisit if the hybrid's static-TBox curation proves insufficient in practice.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REAS-04 | The OntoGraph axiom-scoping approach is decided and documented (hybrid, per CONTEXT.md), together with an LPG→OWL mapping spec covering edge-property reification (`Atom.ARG.pos`, `Rule.HAS_BODY/HAS_HEAD.order`) | This document verifies the live data (§ Live OntoGraph Characterization) that the decision rests on, specifies the exact SWRL-vocabulary mapping table and IRI scheme (§ Architecture Patterns), designs the two-part spike with a concrete TBox-only contradiction using real project classes (§ Spike Design), and confirms current package versions for the throwaway spike (§ Standard Stack, § Package Legitimacy Audit) |

</phase_requirements>

## Summary

Phase 820 ships no production code — it ships three durable artifacts (a PROJECT.md Key Decision entry, `spec/LPG-OWL-MAPPING.md`, and a `820-DECISION.md` with spike evidence) plus one throwaway `spike/` directory. The hybrid axiom-scoping approach and the SWRL-vocabulary Metagraph mapping were already decided in CONTEXT.md and confirmed by prior milestone research (`SUMMARY.md`/`ARCHITECTURE.md`/`PITFALLS.md`) — this document does not re-litigate those, it verifies the concrete facts the decision and spec depend on and designs the spike mechanics in enough detail to plan tasks against.

Three things were verified directly against the **live** docker Neo4j instance this session (not assumed): (1) the "flat vocabulary, no axioms" claim is confirmed empirically — zero `SUBCLASS_OF`/`DOMAIN`/`RANGE`/`DISJOINT_WITH` relationship types exist anywhere in the database's 14 distinct relationship types; (2) project `v8-ui-smoke` has the most rules (16 `Rule` nodes, 10 `Class`, 25 `DatatypeProperty`, 0 `ObjectProperty`, 8 `Builtin`) of any project in the live graph, making it the correct spike target per CONTEXT.md's discretion rule; (3) a **new, concrete instance of Pitfall 1 (silent RDF-translation data loss)** was found live: two `Atom` nodes belonging to `v8-ui-smoke`'s `R_DOOR_ORIENTATION_V` rule carry `graph:'OntoGraph'` instead of the schema-mandated `graph:'Metagraph'` — a real data-quality defect in the live graph, not a hypothetical. Any Cypher export that scopes by `{project, graph}` rather than `{project, label}` will silently drop those two atoms from the Metagraph translation. This is now a normative requirement for the mapping spec and the spike's export query, not a documented risk to keep in mind for later.

`DesignGrammar-V7.owl` axiom counts were re-verified: `rdfs:subClassOf` occurs 68 times (CONTEXT.md states 69 — an off-by-one worth resolving with an `rdflib`-based count during the spike rather than trusting either grep count), `rdfs:domain` 105 times, `rdfs:range` 112 times, `owl:disjointWith` 0 times, and `owl:Class` declarations ~235-236 (both grep patterns agree closely). All three package versions the spike needs (Owlready2 0.51, RDFLib 7.6.0, pySHACL 0.40.0, plus the `neo4j` Python driver) were confirmed current on PyPI this session; the automated package-legitimacy check flagged all four as `SUS` purely because its heuristic reads *latest release date* as package age — manual PyPI JSON lookups confirm 8-16 years of continuous release history for each, and `neo4j` is already a production dependency in `data-service/requirements.txt`. No `java`/JRE is installed on the local dev machine — the spike's HermiT step needs either a manual JRE 17 install or (recommended) running inside a throwaway container matching `data-service`'s `python:3.11-slim` + `apt-get install openjdk-17-jre-headless` pattern already specified in `STACK.md`.

**Primary recommendation:** Verify the mistagged-node finding is repeatable (not a one-off), fix the spike's Cypher export to scope by `{project, label}` not `{project, graph}`, and design the spike's seeded contradiction as a pure TBox construction using two of `v8-ui-smoke`'s real classes (e.g. `ex:Door owl:disjointWith ex:Window`, then `ex:SlidingDoor rdfs:subClassOf` both) so the demonstration stays inside the milestone's confirmed TBox-only reasoning scope and needs no ABox/UNA machinery to prove the point.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Axiom-scoping decision (hybrid) | Documentation (PROJECT.md) | — | A written Key Decision, not code; gates all reasoning-related phases below it |
| LPG→OWL mapping spec | Documentation (`spec/`) | — | Durable contract Phase 821's translator implements against; not itself executable |
| Static TBox curation (`disjointWith`) | Database / Storage (ontology file, design-time artifact) | — | `DesignGrammar-V7.owl` is a hand-maintained file, not runtime-generated; curation happens here, once |
| Neo4j → RDF export (spike only) | API / Backend (throwaway script) | Database / Storage (Neo4j read) | Direct Cypher read via Python neo4j driver — same tier Phase 821's real `ontology_export.py` will occupy, but disposable this phase |
| OWL 2 DL reasoning (spike only) | API / Backend (throwaway script, local subprocess) | — | Owlready2 + HermiT run as a local Python process in this phase, not a service; Phase 822 promotes this to the `dg-reasoner` sidecar |
| Sidecar-vs-embedded confirmation | Documentation (PROJECT.md) | API / Backend (future `dg-reasoner`) | Decision recorded here; actual service stood up in Phase 821 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Owlready2 | 0.51 [VERIFIED: pip index versions, 2026-07-11] | Load merged TBox (static `.owl` + exported OntoGraph/Metagraph Turtle), run `sync_reasoner()` (HermiT) for the spike's consistency checks | Only Python library with genuine OWL 2 DL completeness; bundles HermiT as a JAR it shells out to — no separate reasoner install needed beyond a JRE |
| RDFLib | 7.6.0 [VERIFIED: pip index versions, 2026-07-11] | In-memory RDF graph the spike's Cypher→Turtle exporter builds and Owlready2/pySHACL both consume | Shared substrate between Owlready2's quadstore and any future SHACL work; first released 2010, 47 versions on PyPI |
| `neo4j` (official Python driver) | 6.2.0 latest / already unpinned in `data-service/requirements.txt` [VERIFIED: pip index versions] | Direct bolt reads for the spike's Cypher export — no `n10s` this phase per CONTEXT.md | Already a production dependency of this codebase; official Neo4j-maintained driver, compatible with the running Neo4j 5 server |
| OpenJDK headless JRE | 17 | Runtime Owlready2's bundled HermiT JAR shells out to | Debian bookworm/trixie package name `openjdk-17-jre-headless`, already the pinned choice in `STACK.md` for the future `dg-reasoner`/`data-service` Dockerfile — reuse the same version for spike/production consistency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pySHACL | 0.40.0 [VERIFIED: pip index versions, 2026-07-11] | Not needed for Phase 820's spike (SHACL is Phase 823 scope) — listed for version-pin consistency if the spike's `requirements.txt` is later reused as Phase 823's starting point | Only if the spike's throwaway venv is repurposed; not required to prove REAS-04's success criteria |
| `owlrl` | 7.6.2 (pySHACL transitive dependency) | OWL 2 RL forward-chaining — not a DL-reasoning substitute | Not used this phase; do not let it stand in for HermiT |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Owlready2 + bundled HermiT | Openllet (maintained Pellet fork) as second engine | Not needed for the spike — the spike only needs to prove the trivial-consistency/non-trivial-unsatisfiability contrast with one reasoner; HermiT is `reasoner.py`'s existing default id |
| Local venv spike run | Throwaway Docker container (`python:3.11-slim` + `openjdk-17-jre-headless`) | Recommended over local venv given no JRE is installed on this dev machine (see Environment Availability) — avoids polluting the host with a JRE install for a one-off spike |

**Installation:**
```bash
# spike/requirements.txt
owlready2==0.51
rdflib==7.6.0
neo4j==6.2.0
```

**Version verification:** All four packages (`owlready2`, `rdflib`, `pyshacl`, `neo4j`) were checked this session via `pip index versions <pkg>` against the live PyPI registry (not training-data recall) — see Package Legitimacy Audit below for the full verdict and the age/downloads correction to the automated tool's `SUS` flags.

## Package Legitimacy Audit

| Package | Registry | Age (first release, verified via PyPI JSON) | Downloads | Source Repo | Verdict (seam) | Disposition |
|---------|----------|------|-----------|-------------|---------|-------------|
| owlready2 | PyPI | 2017-05-03 (9 yrs, 51 releases) | unknown (seam couldn't fetch) | none listed on PyPI metadata (upstream: `github.com/pwin/owlready2` / `bitbucket.org/jibalamy/owlready2`) | SUS (`too-new`, `unknown-downloads`, `no-repository`) | **Approved** — false positive: seam's "too-new" reads latest-release-date (2026-06-22), not first-release-date; already the milestone's confirmed reasoner library (STACK.md/SUMMARY.md), already used in prior v8.2 research |
| rdflib | PyPI | 2010-05-13 (16 yrs, 47 releases) | unknown (seam couldn't fetch) | `github.com/RDFLib/rdflib` | SUS (`unknown-downloads`) | **Approved** — official RDFLib org project, actively maintained |
| pyshacl | PyPI | 2018-09-16 (8 yrs, 79 releases) | unknown (seam couldn't fetch) | `github.com/RDFLib/pySHACL` | SUS (`too-new`, `unknown-downloads`) | **Approved** — same false-positive pattern (latest release 2026-07-08 misread as package age); not used this phase's spike anyway |
| neo4j | PyPI | 2018-08-10 (8 yrs, 109 releases) | unknown (seam couldn't fetch) | `neo4j.com` (official vendor) | SUS (`unknown-downloads`) | **Approved** — official Neo4j-maintained driver, already a pinned production dependency in `data-service/requirements.txt` |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** all four flagged by the automated seam, but all four are corrected to Approved above based on manually verified PyPI release history (this session, via direct `pypi.org/pypi/<pkg>/json` fetch) showing 8-16 years of continuous releases and, for `rdflib`/`pyshacl`, an official GitHub org repo. **The planner should still not skip a `checkpoint:human-verify`-style sanity check before the spike's `pip install` runs**, since the seam's downloads signal is genuinely unavailable (not merely low) — treat as procedural caution, not a legitimacy doubt.

*Package names for `owlready2`, `rdflib`, `pyshacl` were originally surfaced via the prior milestone's `STACK.md` (itself WebSearch/PyPI-sourced, not Context7) — tag as `[ASSUMED]`→now `[VERIFIED: PyPI registry + release-history cross-check]` this session. `neo4j` is `[VERIFIED: already in production requirements.txt]`.*

## Architecture Patterns

### System Architecture Diagram (spike-scope only — no production service this phase)

```
┌─────────────────────────────────────────────────────────────────┐
│ Live Neo4j (bolt://localhost:7687)                               │
│   OntoGraph:  Class / DatatypeProperty / ObjectProperty          │
│               (flat — confirmed zero SUBCLASS_OF/DOMAIN/RANGE/   │
│                DISJOINT_WITH relationship types in whole DB)     │
│   Metagraph:  Rule / Atom / Var / Literal / Builtin              │
│               + HAS_BODY/HAS_HEAD (order) + ARG (pos)            │
└───────────────────────────┬───────────────────────────────────────┘
                            │ Cypher, scoped by {project, LABEL}
                            │ (NOT {project, graph} — graph property
                            │  is dirty on live data, see Pitfall below)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ spike/export.py (throwaway, this phase)                          │
│   • reads Class/DatatypeProperty/ObjectProperty → owl:Class etc. │
│   • reads Rule/Atom/Var/Literal/Builtin → SWRL RDF vocabulary    │
│   • builds one in-memory RDFLib Graph                            │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                ┌───────────┴────────────┐
                ▼                        ▼
   spike/run_naive.py          spike/run_hybrid.py
   loads: dynamic export ONLY  loads: dynamic export
   (or + static V7.owl, same    + static V7.owl
    result — no axioms          + curated disjointWith
    connect the two)            (design-time addition)
   → owlready2 sync_reasoner   → seeded contradiction
   → expect: "consistent"        (SlidingDoor ⊑ Door ⊓ Window,
     (the false positive)         Door ⊓ Window = ∅)
                                 → expect: SlidingDoor unsatisfiable
```

### Recommended Project Structure

```
.planning/phases/820-.../
├── 820-CONTEXT.md
├── 820-RESEARCH.md          (this file)
├── 820-DECISION.md          (spike evidence + decision write-up, produced by the phase)
└── spike/
    ├── requirements.txt      # pinned: owlready2==0.51, rdflib==7.6.0, neo4j==6.2.0
    ├── export.py             # Cypher → RDFLib Graph, scoped {project, label}
    ├── run_naive.py          # part (a): naive export → HermiT → "consistent"
    ├── run_hybrid.py         # part (b): + curated disjointWith + seeded contradiction → unsatisfiable
    └── README.md             # exact reproduction steps (venv/container, JRE, run order)

spec/
└── LPG-OWL-MAPPING.md        # durable spec, Phase 821 builds the real translator against this
```

### Pattern 1: SWRL RDF vocabulary mapping for Metagraph (the low-risk half)

**What:** Map every Metagraph node/relationship onto the W3C SWRL submission's RDF vocabulary (`http://www.w3.org/2003/11/swrl#`) rather than inventing custom terms.

| DG (Neo4j) | SWRL RDF term | Notes |
|---|---|---|
| `Rule` node | `swrl:Imp` | `rdfs:label` = `Rule_Id`; `Rule.kind`/`RuleName`/`RuleDescription` become DG-namespaced annotation properties (no SWRL equivalent) |
| `(Rule)-[HAS_BODY {order}]->(Atom)` | `swrl:body` → `swrl:AtomList` (`rdf:List` of atoms, ordered by `first`/`rest` chain) | `order` becomes **implicit list position** — this is the reification target for Pitfall 1/5, see below |
| `(Rule)-[HAS_HEAD {order}]->(Atom)` | `swrl:head` → `swrl:AtomList` | same pattern as body |
| `Atom {type:'ClassAtom'}` | `swrl:ClassAtom` | `swrl:classPredicate` ← `REFERS_TO` target (an `owl:Class`) |
| `Atom {type:'DataPropertyAtom'}` | `swrl:DatavaluedPropertyAtom` | `swrl:propertyPredicate` ← `REFERS_TO` target (`owl:DatatypeProperty`) |
| `Atom {type:'ObjectPropertyAtom'}` | `swrl:IndividualPropertyAtom` | Not observed in live data yet (0 `ObjectProperty` nodes in `v8-ui-smoke`) but schema-legal per `cypher_template.txt` — must still be covered normatively in the spec |
| `Atom {type:'BuiltinAtom'}` | `swrl:BuiltinAtom` | `swrl:builtin` ← `REFERS_TO` target; `swrl:arguments` → `rdf:List` (not `argument1`/`argument2` — builtins can have >2 args, e.g. `swrlb:continuousFromTo`) |
| `(Atom)-[ARG {pos:1}]->(x)`, `(Atom)-[ARG {pos:2}]->(y)` | `swrl:argument1`, `swrl:argument2` (Class/DataProperty/ObjectProperty atoms — always binary) | `pos` maps directly to the numbered SWRL argument slot for binary atom kinds |
| `(BuiltinAtom)-[ARG {pos:n}]->(x)` | `rdf:List` position within `swrl:arguments` | BuiltinAtoms need the list form, not `argument1/2`, since arity varies (confirmed live: `swrlb:greaterThan`/`lessThan`/`notEqual`/`equalTo` are binary, but `continuousFromTo`/`towards`/`or`/`fillet` may need >2 args — verify each builtin's arity against `training/dataset_schema.json` during spec-writing, don't assume all are binary) |
| `Var {name: '?x'}` | `swrl:Variable` (individual) | Mint IRI `{base}/project/{project}/var/{name-without-?}` |
| `Literal {lex, datatype}` | Plain RDF typed literal (not a named individual) | No reification needed — literals are already first-class RDF |

**Example (illustrative, not yet written — Phase 821 implements):**
```turtle
# Source: W3C SWRL Submission RDF vocabulary (2004), applied to DG's schema
:R_BUILDING_MAX_STOREY_9_V a swrl:Imp ;
    swrl:body ( [ a swrl:ClassAtom ; swrl:classPredicate ex:Building ; swrl:argument1 :var_entity ]
                [ a swrl:DatavaluedPropertyAtom ; swrl:propertyPredicate ex:hasStoreyCount ;
                  swrl:argument1 :var_entity ; swrl:argument2 :var_value ]
                [ a swrl:BuiltinAtom ; swrl:builtin swrlb:greaterThan ;
                  swrl:arguments ( :var_value "9"^^xsd:integer ) ] ) ;
    swrl:head ( [ a swrl:DatavaluedPropertyAtom ; swrl:propertyPredicate ex:violatesMaxStoreyCount ;
                  swrl:argument1 :var_entity ; swrl:argument2 true ] ) .
```

### Pattern 2: IRI minting strategy

- **Reuse stored `iri`** for `Class`, `DatatypeProperty`, `ObjectProperty`, `Builtin` — these already carry real IRI-shaped strings (`ex:Building`, `swrlb:greaterThan`) confirmed live in `v8-ui-smoke`.
- **Mint deterministic IRIs** for `Rule`/`Atom`/`Var`/`Literal` (Literal excluded — becomes a literal, not minted) under the V7 namespace (`http://example.org/design-grammar`, confirmed as `DesignGrammar-V7.owl`'s `xml:base`) with a project-scoped path segment:
  - Rule: `{base}/project/{project}/rule/{Rule_Id}`
  - Atom: `{base}/project/{project}/atom/{Atom_Id}`
  - Var: `{base}/project/{project}/var/{name-stripped-of-leading-?}`
- **The live `ex:` prefix used by OntoGraph nodes is NOT `dg:`/`dgm:`/`dgv:`/`dgs:`** (the V7 meta-schema's own namespaces) — the mapping spec must state explicitly that `ex:` denotes per-project *dynamically generated domain vocabulary* (confirmed by `DesignGrammar-V7.owl`'s own comment: "Domain-specific classes... are dynamically generated... and are NOT part of this ontology"), kept as a separate namespace from the meta-schema, unioned only at reasoning time.

### Pattern 3: UNA handling (forward-looking — no ABox exported this phase)

Phase 820's spike is **TBox-only** (see Spike Design below) and mints no individuals, so UNA does not bite this phase. The spec must still normatively require, for when Phase 823's ValidGraph→RDF (ABox) translation lands: emit one `owl:AllDifferent` per project export batch with `owl:distinctMembers` (or OWL2's `owl:members` + `rdf:parseType="Collection"`) listing every minted named individual, so DL reasoners (which do not assume UNA by default) don't merge instances Neo4j already treats as distinct.

```xml
<!-- Source: OWL 2 spec, applied per Pitfall 5 -->
<owl:AllDifferent>
  <owl:distinctMembers rdf:parseType="Collection">
    <rdf:Description rdf:about="{base}/project/{project}/atom/R_DOOR_ORIENTATION_V_A1"/>
    <rdf:Description rdf:about="{base}/project/{project}/atom/R_DOOR_ORIENTATION_V_A2"/>
    <!-- ... all minted individuals in this project's export batch -->
  </owl:distinctMembers>
</owl:AllDifferent>
```

### Anti-Patterns to Avoid

- **Scoping the export Cypher query by `{project, graph}` instead of `{project, label}`:** confirmed live this session that `v8-ui-smoke` has two `Atom` nodes (`R_DOOR_ORIENTATION_V_A1`, `_A2`) mistakenly tagged `graph:'OntoGraph'` instead of `'Metagraph'`. A query like `MATCH (n {project:$p, graph:'Metagraph'})` silently drops them. Always scope by node label (`MATCH (n:Rule|Atom|Var|Literal|Builtin {project:$p})` for Metagraph, `MATCH (n:Class|DatatypeProperty|ObjectProperty {project:$p})` for OntoGraph) and treat `graph` as informational, not authoritative.
- **Treating `ex:` (OntoGraph domain vocabulary) as if it were part of `DesignGrammar-V7.owl`'s own namespace** — the V7 file explicitly disclaims domain classes; conflating the two namespaces in the mapping spec would misrepresent what's static vs. dynamic.
- **Reasoning over an ABox for this phase's spike** — the milestone's own Out-of-Scope table states OWL DL reasoning runs "only on-demand... or on ontology-export change," not per validation run; the spike should stay TBox-only to match that architecture and avoid pulling UNA/individual-merging complexity into a phase that doesn't need it yet.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| SWRL rule structure in RDF | A custom Rule/Atom/Arg reification vocabulary | The W3C SWRL RDF vocabulary (`swrl:Imp`, `swrl:body`/`head`, `swrl:ClassAtom` etc.) | Tool-recognized (Protégé, OWL API), near-1:1 with DG's existing Metagraph shape — reinventing it would cost design effort for zero benefit and produce something no external tool understands |
| OWL 2 DL reasoning | A hand-rolled tableau/consistency checker | Owlready2 + HermiT (bundled) | No pure-Python library implements complete OWL 2 DL satisfiability; this was already settled in `STACK.md`, not re-opened here |
| Axiom counting for the decision write-up | Manual `grep` counts (already shown to disagree by ±1 with CONTEXT.md's figures) | An `rdflib`-based parse-and-count during the spike (`len(list(g.subjects(RDFS.subClassOf, None)))` style) | grep counts lines/occurrences of a string, not actual RDF/XML axiom triples — self-closing vs. child-element serialization skews the count; a real parser gives the authoritative number for `820-DECISION.md` |

**Key insight:** Everything this phase needs to build (mapping spec content, spike scripts) has either a standard vocabulary to map onto (SWRL) or a standard library to reason with (Owlready2/HermiT) — the actual net-new engineering risk is entirely in getting the *live-data scoping* right (label vs. graph-property, the exact namespace split), which is a data-fidelity problem, not a "don't hand-roll" library problem.

## Common Pitfalls

### Pitfall 1: Trusting the `graph` property for export scoping (confirmed live, not hypothetical)

**What goes wrong:** An exporter Cypher query scoped by `{project, graph:'Metagraph'}` silently omits nodes whose `graph` property is wrong, even though their label and all their relationships are otherwise correct and reachable.

**Why it happens:** `graph` is a denormalized convenience property set at ingest time (per `cypher_template.txt`'s `SET n.graph = 'OntoGraph'|'Metagraph'`); nothing enforces it stays consistent with the node's actual label, and it can drift (manual edits, partial re-ingests, or an ingest-time LLM/Cypher-generation slip).

**How to avoid:** Scope every export query by node **label**, never by the `graph` property alone. Confirmed this session: `v8-ui-smoke`'s `R_DOOR_ORIENTATION_V` rule has both its `A1` (ClassAtom) and `A2` (DatatypeProperty-typed) body atoms tagged `graph:'OntoGraph'` instead of `'Metagraph'` — real, present-tense data, not a contrived example.

**Warning signs:** Export produces fewer `Atom`/`Var`/`Rule` nodes than `MATCH (n:Atom {project:$p}) RETURN count(n)` reports independently of `graph`.

**Phase to address:** This phase (spike's `export.py` must scope by label) and Phase 821 (the real `ontology_export.py` must inherit the same discipline) — put an explicit assertion in both.

---

### Pitfall 2: Grep-based axiom counts are off-by-one from CONTEXT.md's figures

**What goes wrong:** `820-DECISION.md`'s axiom-count evidence table could inherit an unverified number if it just repeats CONTEXT.md's "69 subClassOf" without re-deriving it.

**Why it happens:** `grep -c "rdfs:subClassOf"` counts matching *lines*, not RDF axiom occurrences; RDF/XML can serialize multiple axioms per line or split one axiom across lines, so line-count and triple-count can legitimately differ by a small margin. This session's `grep -c` returned 68 (not CONTEXT's 69); `owl:Class` occurrence-count returned 236 vs. CONTEXT's 235.

**How to avoid:** During the spike, parse `DesignGrammar-V7.owl` with `rdflib` and count actual triples matching the target predicates (`RDFS.subClassOf`, `RDFS.domain`, `RDFS.range`, `OWL.disjointWith`) rather than trusting either grep count. The exact number is immaterial to the decision (both counts confirm "dozens of real axioms exist, zero disjointness") but `820-DECISION.md` should cite the parser-derived number, not a grep guess.

**Phase to address:** This phase, when writing `820-DECISION.md`'s evidence table.

---

### Pitfall 3: BuiltinAtom arity assumed binary (`argument1`/`argument2`) when some builtins take more args

**What goes wrong:** If the mapping spec (or a future translator) always emits `swrl:argument1`/`swrl:argument2` for `BuiltinAtom`, any builtin needing 3+ arguments loses data silently (extra `ARG` edges with `pos:3+` have nowhere to map).

**Why it happens:** DG's live `Builtin` vocabulary (confirmed this session: `greaterThan`, `lessThan`, `or`, `equalTo`, `continuousFromTo`, `fillet`, `notEqual`, `towards`) is a superset of trivially-binary builtins — `continuousFromTo` and `towards` read as likely 3-argument-or-more builtins by name (a "from X to Y" or directional-comparison semantic typically needs more than 2 slots), though this was not confirmed against `training/dataset_schema.json`'s exact per-builtin arity definitions this session.

**How to avoid:** Before finalizing the spec's BuiltinAtom row, check `training/dataset_schema.json` and any live `ARG {pos}` data for each of the 8 confirmed builtins to determine actual arity, and use `swrl:arguments` (an `rdf:List`) universally for BuiltinAtom rather than assuming binary `argument1/2` — the list form is strictly more general and costs nothing for binary builtins.

**Phase to address:** This phase, while writing `spec/LPG-OWL-MAPPING.md`'s Metagraph section — flagged here as an **open question** (see below) rather than resolved, since this session did not read `dataset_schema.json`'s per-builtin arity table in full.

---

### Pitfall 4: Seeding the spike's contradiction inside the ABox by accident

**What goes wrong:** The natural instinct for "seed a contradiction" is to create two individuals and assert conflicting class memberships — but that pulls UNA (Pitfall 5) into a phase whose confirmed reasoning scope is TBox-only, adding unnecessary complexity to the spike and potentially producing a demonstration that doesn't match how Phase 822 will actually invoke the reasoner ("at rule-authoring time," i.e. schema-level, per the milestone's Out-of-Scope table).

**How to avoid:** Construct the contradiction entirely in the TBox using two of `v8-ui-smoke`'s real domain classes, e.g. curate `ex:Door owl:disjointWith ex:Window` (a defensible real-world disjointness — architecturally a door opening is not a window opening), then assert a class `ex:SlidingDoor` as `rdfs:subClassOf` both `ex:Door` and `ex:Window`. HermiT will report `ex:SlidingDoor` unsatisfiable with zero individuals involved — a clean TBox-only demonstration.

**Phase to address:** This phase — this is the recommended concrete construction for CONTEXT.md's "exact seeded-contradiction construction" discretion item.

## Live OntoGraph Characterization (verified against running docker Neo4j, 2026-07-11)

Neo4j reachable at `bolt://localhost:7687` / HTTP `http://localhost:7474` (credentials: `neo4j`/`12345678`, from `docker-compose.yml`'s `NEO4J_AUTH` — **do not hardcode this in any committed spike script**; read from an env var the spike README documents).

**Node counts by `project` (all labels):**

| Project | Total nodes |
|---|---|
| TestA | 1231 |
| v8-ui-smoke | 1063 |
| URBAN_BLOCK_V7 | 16 |
| UrbanBlock | 13 |
| test-phase03 | 13 |
| phase14-smoke | 8 |
| Test Project | 6 |
| test-update-flow | 5 |

**Rule counts (the relevant metric for "most rules" per CONTEXT.md's discretion rule):**

| Project | Rule count |
|---|---|
| **v8-ui-smoke** | **16** ← spike target |
| TestA | 3 |
| Test Project | 1 |
| URBAN_BLOCK_V7 | 1 |

**`v8-ui-smoke` label breakdown:** `ValidationEntity` 875, `Atom` 50, `Var` 32, `DatatypeProperty` 25, `ValidationRun` 21, `Rule` 16, `DesignRuleSession` 15, `Class` 10, `Literal` 10, `Builtin` 8, `IntegrationConfig` 1, **`ObjectProperty` 0**.

**Sample Class nodes (`v8-ui-smoke`):** `ex:Building`, `ex:LivingUnit`, `ex:Corridor`, `ex:Block`, `ex:Facade`, `ex:Column`, `ex:FacadePanel`, `ex:Roof`, `ex:Door`, `ex:Floor` — real domain vocabulary confirming the "flat, no axioms" claim: none of these have any `SUBCLASS_OF` relationship in the live graph.

**Relationship types across the whole database (14 total, none schema-axiom-related):** `HAS_ENTITY`, `ARG`, `REFERS_TO`, `HAS_BODY`, `INSTANCE_OF`, `TAGGED_WITH`, `HAS_HEAD`, `PROPERTY_OF`, `HAS_ATOM`, `VALIDATES`, `SWRL_RULE`, `HAS_PROPERTY`, `ARGUMENT`, `BINDS_TO`. **Zero occurrences of anything resembling `SUBCLASS_OF`/`DOMAIN`/`RANGE`/`DISJOINT_WITH`** — this directly confirms `ARCHITECTURE.md`'s Critical Finding empirically, against live data, this session (not just against the static schema docs).

**Confirmed data-quality defect (feeds Pitfall 1 above):** `MATCH (n:Atom {graph:'OntoGraph'})` returns exactly 2 rows, both `project:'v8-ui-smoke'`, both belonging to rule `R_DOOR_ORIENTATION_V` (`_A1` ClassAtom, `_A2` DatatypeProperty-typed) — these should carry `graph:'Metagraph'` per schema. Separately, `phase14-smoke` has 6 `DesignState` + 2 `Run` nodes tagged `graph:'Metagraph'` instead of `'ValidGraph'` (irrelevant to the chosen spike project, but confirms this is a systemic tagging-drift issue worth a one-line callout in `820-DECISION.md`, not just a `v8-ui-smoke`-specific fluke).

**`HAS_BODY`/`ARG` ordering sample (`v8-ui-smoke`):** Confirmed `order`/`pos` properties are present and populated on every sampled edge, e.g. `R_BLOCK_MIN_FOOTPRINT_PCT_18_V` has `HAS_BODY` edges with `order` 1/2/3 to atoms of type `ClassAtom`/`DataPropertyAtom`/`BuiltinAtom` respectively — the exact ordering shape the SWRL `rdf:List` mapping (Pattern 1) needs to preserve.

**`DesignGrammar-V7.owl` axiom counts (re-verified, see Pitfall 2 on the grep-count caveat):** `rdfs:subClassOf` 68 (grep line-count) / CONTEXT.md states 69; `rdfs:domain` 105; `rdfs:range` 112; `owl:disjointWith` 0; `owl:Class` declarations 236 (occurrence count) / CONTEXT.md states 235. Base namespace confirmed as `http://example.org/design-grammar` (`xml:base`), with `dg`/`dgm`/`dgv`/`dgs`/`dgc` sub-namespaces for the five graph layers — **`ex:` (OntoGraph's domain-term prefix) is a separate namespace not defined inside `DesignGrammar-V7.owl` at all**, confirmed by the file's own comment disclaiming dynamically-generated domain classes.

## Code Examples

### Correct export scoping (avoids Pitfall 1)

```python
# Source: this session's live-data verification, not yet written as production code
# Scope by LABEL, not by the graph property (which is dirty on live data)
METAGRAPH_QUERY = """
MATCH (n)
WHERE n.project = $project
  AND (n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin)
RETURN n
"""
ONTOGRAPH_QUERY = """
MATCH (n)
WHERE n.project = $project
  AND (n:Class OR n:DatatypeProperty OR n:ObjectProperty)
RETURN n
"""
```

### Owlready2 spike skeleton (part a — naive, expect trivial "consistent")

```python
# Source: https://owlready2.readthedocs.io/en/latest/reasoning.html (Owlready2 official docs)
from owlready2 import get_ontology, sync_reasoner

onto = get_ontology("file://spike/output/naive_export.ttl").load()
with onto:
    sync_reasoner()  # HermiT, the reasoner.py default id
print("Inconsistent classes:", list(onto.inconsistent_classes()))
# Expected part (a) result: [] — trivially consistent, the documented false positive
```

### Owlready2 spike skeleton (part b — hybrid + seeded TBox contradiction)

```python
# Source: this session's design, per CONTEXT.md's spike-mechanics decision
from owlready2 import get_ontology, sync_reasoner

onto = get_ontology("file://spike/output/hybrid_export.ttl").load()
# hybrid_export.ttl = static DesignGrammar-V7.owl + live v8-ui-smoke OntoGraph/Metagraph
#   + curated: ex:Door owl:disjointWith ex:Window
#   + seeded:  ex:SlidingDoor rdfs:subClassOf ex:Door, ex:Window
with onto:
    sync_reasoner()
print("Inconsistent classes:", list(onto.inconsistent_classes()))
# Expected part (b) result: [ex:SlidingDoor] — the hybrid approach catches what naive missed
```

## State of the Art

Not applicable in the usual sense — this phase's content (SWRL RDF vocabulary, OWL 2 DL reasoning fundamentals, UNA) are all W3C-standardized and have not changed recently. The one "state of the art" note carried from prior research: HermiT's upstream has had no commits in ~6 years but remains the de facto standard (Protégé default, still bundled by Owlready2 0.51 as of its 2026-06-22 release) — acceptable for this phase's spike, re-verify at a future milestone only if reasoning becomes business-critical.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `swrlb:continuousFromTo` and `swrlb:towards` likely need >2 arguments (inferred from builtin name semantics, not confirmed against `training/dataset_schema.json`'s per-builtin arity definitions) | Common Pitfalls (Pitfall 3), Architecture Pattern 1 | If wrong (all 8 builtins are actually binary), the spec could over-engineer the BuiltinAtom mapping with `rdf:List` where `argument1/2` would have sufficed — low risk either way since `rdf:List` is a strict superset, but worth 10 minutes reading `dataset_schema.json` before finalizing the spec |
| A2 | `ex:Door`/`ex:Window` disjointness is "defensible" as a real-world curated axiom, not just a spike convenience | Pitfall 4 | Low risk — this is explicitly a spike/demonstration construct per CONTEXT.md's discretion clause, not a claim that ships to production; if the disjointness doesn't hold for some edge case (e.g. a real "sliding door-window" hybrid product exists in some project's rules), it only affects the spike's illustrative example, not the mapping spec's normative content |
| A3 | `v8-ui-smoke` (a QA/UI-smoke-test project, per STATE.md's own description) satisfies the success criterion's "a real project's live OntoGraph data" wording, versus `TestA` (fewer rules but perhaps a more "genuine" authored project) | Live OntoGraph Characterization, Summary | Low-medium risk — CONTEXT.md's discretion rule explicitly says "pick the project with the most rules/atoms," which unambiguously selects `v8-ui-smoke`; flagging only because the phrase "real project" in the success criteria could be read as excluding QA-seed data — recommend the planner confirm this reading is acceptable or note it explicitly in `820-DECISION.md` rather than silently assuming |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **Exact per-builtin arity for DG's 8 confirmed builtins**
   - What we know: 8 builtins exist in live `v8-ui-smoke` data (`greaterThan`, `lessThan`, `or`, `equalTo`, `continuousFromTo`, `fillet`, `notEqual`, `towards`); `ARG {pos}` edges exist and are populated.
   - What's unclear: whether all 8 are strictly binary (2 args) or whether some (especially `continuousFromTo`, `towards`) need 3+ — this session sampled only `greaterThan`/`lessThan`/`notEqual`/`equalTo` patterns from `cypher_template.txt`'s worked example (all binary), not the others' actual `ARG` edge counts.
   - Recommendation: during Phase 820 execution, run `MATCH (a:Atom {type:'BuiltinAtom', project:'v8-ui-smoke'})-[r:ARG]->() RETURN a.iri, count(r) AS arity` against live Neo4j (a 30-second query) before finalizing the spec's BuiltinAtom mapping row.

2. **Is the `graph`-property tagging drift (Pitfall 1's finding) worth a separate quick-fix task, or purely a spec/spike scoping note?**
   - What we know: 2 atoms in `v8-ui-smoke` and 6+2 nodes in `phase14-smoke` are mistagged; this doesn't block the spike (label-based scoping works around it) or the mapping spec (which now documents the requirement).
   - What's unclear: whether this is worth a `MATCH ... SET n.graph = correct_value` one-off Cypher fix now (cheap) versus leaving it as a known-and-documented gap for Phase 821's real exporter to handle defensively.
   - Recommendation: leave it as a documented gap this phase (don't scope-creep into a data-repair task); Phase 821's planner should decide whether to add a defensive query or a one-time cleanup migration.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Compose / Neo4j service | Spike's live-data export | ✓ | Neo4j 5 (container `neo4j`, image `neo4j:5`), reachable at `localhost:7474`/`7687` | — |
| Python 3 | Spike scripts | ✓ | 3.13.7 / 3.14.2 both present on host | — |
| pip | Package install for spike venv | ✓ | 26.1.1 | — |
| Java / JRE | Owlready2's `sync_reasoner()` (HermiT JAR subprocess) | ✗ | — (not installed on this host) | Run the spike inside a throwaway Docker container built from `python:3.11-slim` + `apt-get install openjdk-17-jre-headless` (same base `STACK.md` already specifies for the future `dg-reasoner`/`data-service`), rather than installing a JRE on the host |
| `docker compose` CLI | Confirming live services, running the spike container | ✓ | services confirmed up: `neo4j`, `data-service`, `design-grammars`, `n8n`, `ollama`, full Speckle stack | — |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:**
- Java/JRE 17 — use a throwaway container instead of a host install (recommended default for this phase's spike anyway, to keep the phase's promise that spike code is fully disposable).

## Validation Architecture

> This phase ships no production code and no automated test suite in the conventional sense — the "tests" for REAS-04 are the spike's own reasoner-output assertions plus human review of the two durable documents. `workflow.nyquist_validation` is absent from `.planning/config.json` (treated as enabled), so this section documents the phase's actual verification mechanism rather than a pytest/xUnit suite.

### Verification Mechanism
| Property | Value |
|----------|-------|
| Framework | None (no unit-test framework applies to a doc/spike phase); spike's own assertions serve as its "test" |
| Config file | none — see Wave 0 below |
| Quick run command | `python spike/run_naive.py && python spike/run_hybrid.py` (inside the recommended JRE-equipped container) |
| Full suite command | same — the spike has exactly two runs, both required |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REAS-04 (spike proof, part a) | Naive export of live OntoGraph reports "consistent" trivially | scripted assertion | `python spike/run_naive.py` — asserts `onto.inconsistent_classes() == []` | ❌ Wave 0 (script to be written this phase) |
| REAS-04 (spike proof, part b) | Hybrid + seeded contradiction flags an unsatisfiable class | scripted assertion | `python spike/run_hybrid.py` — asserts `ex:SlidingDoor in onto.inconsistent_classes()` | ❌ Wave 0 |
| REAS-04 (mapping spec) | `spec/LPG-OWL-MAPPING.md` exists and covers edge-property reification, IRI minting, UNA handling | manual review (documentation, not code) | N/A — reviewed by the planner/Phase 821 reader, not automated | ❌ Wave 0 (doc to be written) |
| REAS-04 (Key Decision) | PROJECT.md's Pending sidecar row (line 134) flips to a decided outcome, referencing spike evidence | manual review | N/A | ❌ Wave 0 (edit to existing file) |

### Sampling Rate
- **Per task commit:** re-run both `run_naive.py`/`run_hybrid.py` after any change to `export.py`'s Cypher scoping.
- **Per wave merge:** both scripts must produce their expected before/after result before `820-DECISION.md` is finalized.
- **Phase gate:** `/gsd-verify-work` should confirm both spike outputs exist as captured evidence (stdout logs or a small results file) referenced from `820-DECISION.md`, plus that `spec/LPG-OWL-MAPPING.md` and the PROJECT.md Key Decision edit exist.

### Wave 0 Gaps
- [ ] `spike/export.py` — Cypher export scoped by label (Pitfall 1 fix), not yet written
- [ ] `spike/run_naive.py` / `spike/run_hybrid.py` — the two-part spike proof scripts, not yet written
- [ ] `spec/LPG-OWL-MAPPING.md` — the durable mapping spec, not yet written
- [ ] `820-DECISION.md` — spike evidence write-up, not yet written
- [ ] JRE 17 availability for the spike run — resolve via throwaway container (see Environment Availability), not yet provisioned

## Security Domain

> `security_enforcement` is absent from `.planning/config.json` (treated as enabled). This phase ships no service/endpoint/UI, so most ASVS categories are not applicable — the two real concerns are credential handling in the spike scripts themselves and information-disclosure hygiene in the committed decision doc.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No new auth surface this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | No | Spike reads live Neo4j data it doesn't validate as untrusted input (internal dev tool, not a user-facing surface) |
| V6 Cryptography / secrets handling | Yes (narrow) | The spike's Neo4j connection uses the dev credential already present in `docker-compose.yml` (`neo4j`/`12345678`) — the spike script must read this from an environment variable, never hardcode it inline, since `spike/` is committed to git per this project's `commit_docs` convention |

### Known Threat Patterns for this phase's scope

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Neo4j dev password hardcoded into a committed spike script | Information Disclosure | Read from `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` env vars in `spike/export.py`; document the expected env vars in `spike/README.md`, don't inline the literal value even though it's already a well-known dev-only password in `docker-compose.yml` |
| `820-DECISION.md` or spike output accidentally including full rule/atom bodies from a non-test project | Information Disclosure | Since the spike targets `v8-ui-smoke` (QA/test data, per STATE.md), this risk is low this phase — but if the planner later reruns the spike against a different, real client project, the same caution about not committing raw exported RDF/Turtle containing that project's rule logic into a public-facing artifact applies |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/820-.../820-CONTEXT.md` — locked decisions this research builds on, not re-derives
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md` — direct reads, confirm REAS-04 scope and the exact Pending Key Decision row (line 134) this phase must flip
- Live Neo4j instance (`bolt://localhost:7687` / `http://localhost:7474`, verified reachable via `docker compose ps` and direct HTTP Cypher queries this session) — node/relationship counts, project rule counts, axiom-absence confirmation, mistagged-node discovery
- `ontology/DesignGrammar-V7.owl` — direct read/grep this session, axiom counts and namespace structure
- `cypher_template.txt` — direct read, confirms Metagraph/OntoGraph schema shape and the worked SWRL-mapping example
- `data-service/reasoner.py` — direct read, confirms the existing `hermit`/`pellet` id registry and JSON-settings persistence pattern this phase's decision must be consistent with
- https://owlready2.readthedocs.io/en/latest/reasoning.html — `sync_reasoner()` API, official docs
- `pip index versions owlready2/rdflib/pyshacl/neo4j` (executed this session against live PyPI) — current version confirmation
- `pypi.org/pypi/<pkg>/json` (fetched this session) — first-release-date verification correcting the package-legitimacy seam's false-positive `SUS` verdicts

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `STACK.md` — prior milestone research this phase builds on and does not re-derive (library choices, sidecar-vs-embedded resolution, Pitfalls 1/2/3/5 as originally identified)
- W3C SWRL Submission (2003/2004) RDF vocabulary — standard reference for the Metagraph mapping table (recalled from training knowledge, cross-checked against the prior `ARCHITECTURE.md`'s Pattern 3 which already identified the same vocabulary terms)

### Tertiary (LOW confidence)
- Assumed per-builtin arity for `continuousFromTo`/`towards` (Assumption A1) — not confirmed against `training/dataset_schema.json` this session, flagged as an Open Question

## Metadata

**Confidence breakdown:**
- Live-data characterization: HIGH — directly queried the running Neo4j instance this session, not recalled or assumed
- Package versions/legitimacy: HIGH — verified via `pip index versions` and direct PyPI JSON fetch this session
- SWRL vocabulary mapping: MEDIUM-HIGH — standard W3C vocabulary, cross-checked against prior `ARCHITECTURE.md` research and DG's own schema files, but the exact BuiltinAtom arity question remains open (Assumption A1)
- Spike contradiction design: MEDIUM — a reasoned, TBox-only construction using real live classes, not yet executed/proven this session (that's the phase's own work)

**Research date:** 2026-07-11
**Valid until:** Live-data facts (node/rule counts, mistagged nodes) should be re-verified if significant time passes before Phase 820 executes, since `v8-ui-smoke` and other test projects may accumulate more data or get cleaned up. Package version facts: 30 days (fast-moving PyPI ecosystem, though these specific packages have historically low release cadence).
