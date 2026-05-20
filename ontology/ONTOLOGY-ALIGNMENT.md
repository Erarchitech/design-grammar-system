# Ontology Alignment Map — Design Grammar System

> Cross-walk between the Design Grammar (DG) ontology and established public vocabularies from the [Linked Open Vocabularies (LOV)](https://lov.linkeddata.es/dataset/lov/vocabs) catalog and W3C standards.

## File structure (v4.0)

As of v4.0 the alignments live in a **separate facade ontology** following the W3C core-plus-extension pattern (SOSA / SSN, FOAF / RDFa Core, DCAT / DCAT-AP):

| File | Role | Contents |
|---|---|---|
| `[DesignGrammar.owl](DesignGrammar.owl)` | **Core ontology (v4.0)** | Pure DG content: 42 classes, properties, instances, internal axioms. **No `owl:imports`**, no cross-vocab alignment axioms. Open this for lean Protégé view, schema editing, fast load. |
| `[DesignGrammar-aligned.owl](DesignGrammar-aligned.owl)` | **Aligned facade (v4.0)** | Imports DG core + 7 external vocabularies + the 38 cross-vocab alignment axioms + 17 external annotation enrichments. Open this for HermiT cross-vocab reasoning, PROV-aware tooling, SOSA-aware tooling, etc. |
| `[catalog-v001.xml](catalog-v001.xml)` | Resolution catalog | Maps both ontology IRIs to local files + redirects 7 external imports to canonical RDF URLs. |

**Pick by use case:**

| Goal | File to open |
|---|---|
| Edit DG entities, add new classes, see clean hierarchy | `DesignGrammar.owl` |
| Verify alignments with HermiT, query across vocabs, integrate with PROV/SHACL/etc. | `DesignGrammar-aligned.owl` |
| Inspect just the DG ontology in NotebookLM | `[DesignGrammar.md](DesignGrammar.md)` (auto-generated from core) |

**Compiled:** 2026-05-15
**Method:** Each DG class/property was checked against canonical W3C vocabularies and the LOV catalog. Alignment strength is annotated as **≡** (semantic equivalence), **⊑** (DG entity is subclass/subproperty), **⊒** (DG entity is superclass/superproperty), or **≈** (partial / overlapping intent).

---

## Executive Summary

The DG ontology overlaps with **9 established vocabularies**. Three layers have particularly strong external alignment:

| DG Layer | Strongest External Alignment | Alignment Strength |
|---|---|---|
| **OntoGraph** | OWL / RDFS itself | ≡ (full equivalence — DG reifies OWL meta-schema for Neo4j storage) |
| **Metagraph** | SWRL (W3C Submission, 2004) | ≡ for Rule/Atom subtypes; DG is a structural subset |
| **ValidationGraph** | PROV-O + SOSA + SHACL (composite) | ≈ — each external vocab covers different facets |
| **KnowledgeGraph** | SKOS + Dublin Core + SIOC | ≈ for KnowledgeNote/Tag; ⊑ for KnowledgeSession |

**Practical recommendations** (see [§7 Recommendations](#7-recommendations)):

1. **Declare SWRL alignment.** Add `owl:equivalentClass` between `dgm:Rule` and `swrl:Imp`, etc. Zero data migration cost — DG already follows SWRL structure.
2. **Declare PROV-O alignment** on `ValidationRun`/`ValidationEntity`. Free interop with PROV-aware tooling (Speckle's audit log, Apache Atlas, Trino).
3. **Reuse SOSA pattern** for `ValidationEntity ↔ ObjectInstance ↔ PropertyVariable ↔ propValue` chain — it's literally Observation/FeatureOfInterest/ObservableProperty/Result.
4. **Reuse `geo:hasGeometry`** instead of `dgv:hasGeoRef` — GeoSPARQL is the LOD-native pattern for object↔geometry.
5. **Reuse `dcterms:title`/`dcterms:created`/`skos:prefLabel`** in the Knowledge layer.
6. **Defer BOT alignment.** DG's domain classes (Building, LivingUnit, Street) are *dynamically generated* and project-specific — they don't fit BOT's fixed-topology approach. BOT is for **building topology**, not parametric design rules.

---

## Table of Contents

1. [Vocabulary Reference Card](#1-vocabulary-reference-card)
2. [Layer 1: OntoGraph ↔ OWL / RDFS](#2-layer-1-ontograph--owl--rdfs)
3. [Layer 2: Metagraph ↔ SWRL](#3-layer-2-metagraph--swrl)
4. [Layer 3: ValidationGraph ↔ PROV-O + SOSA + SHACL + GeoSPARQL](#4-layer-3-validationgraph--prov-o--sosa--shacl--geosparql)
5. [Layer 4: KnowledgeGraph ↔ SKOS + Dublin Core + SIOC](#5-layer-4-knowledgegraph--skos--dublin-core--sioc)
6. [Cross-cutting properties](#6-cross-cutting-properties)
7. [Recommendations](#7-recommendations)
8. [Why DG doesn't reuse these vocabs directly](#8-why-dg-doesnt-reuse-these-vocabs-directly)
9. [Sources](#9-sources)

---

## 1. Vocabulary Reference Card

The vocabularies referenced throughout this document. All namespaces verified against LOV (May 2026).

| Prefix | Namespace | Status | Relevance to DG |
|---|---|---|---|
| `owl` | `http://www.w3.org/2002/07/owl#` | W3C REC (2012) | Meta-schema for OntoGraph layer |
| `rdfs` | `http://www.w3.org/2000/01/rdf-schema#` | W3C REC (2014) | Class/property meta-schema |
| `swrl` | `http://www.w3.org/2003/11/swrl#` | W3C Submission (2004) | Rule structure — direct match for Metagraph |
| `prov` | `http://www.w3.org/ns/prov#` | W3C REC (2013) | Validation run as provenance Activity |
| `sosa` | `http://www.w3.org/ns/sosa/` | W3C REC (2017) | Validation as Observation pattern |
| `shacl` / `sh` | `http://www.w3.org/ns/shacl#` | W3C REC (2017) | Shape-based validation reports |
| `skos` | `http://www.w3.org/2004/02/skos/core#` | W3C REC (2009) | KnowledgeTag as Concept |
| `dcterms` | `http://purl.org/dc/terms/` | DCMI standard | Metadata (title, created, source) |
| `geo` | `http://www.opengis.net/ont/geosparql#` | OGC standard (2012) | GeoRef as Feature/Geometry |
| `bot` | `https://w3id.org/bot#` | W3C-LBD-CG draft | Building topology — partial overlap only |
| `time` | `http://www.w3.org/2006/time#` | W3C REC (2017) | Time concepts (deferred) |

---

## 2. Layer 1: OntoGraph ↔ OWL / RDFS

The OntoGraph layer **reifies** the OWL meta-schema as data in Neo4j (so the LLM can query "what classes exist in project X?"). Every entity here has an exact OWL counterpart.

| DG entity | External equivalent | Strength | Notes |
|---|---|---|---|
| `dg:Class` | `owl:Class` | **≡** | DG reifies the OWL class concept as a Neo4j node so dynamic domain classes (Building, UrbanBlock) are query-able |
| `dg:DatatypeProperty` | `owl:DatatypeProperty` | **≡** | Same reification pattern |
| `dg:ObjectProperty` | `owl:ObjectProperty` | **≡** | Same |
| `dg:iri` | `rdf:about` (the IRI itself) | **≈** | DG stores the IRI as a string property; OWL stores it as the resource identifier |
| `dg:label` | `rdfs:label` | **≡** | Should be replaced with `rdfs:label` directly |
| `dg:range` | `rdfs:range` | **≡** | DG stores the range datatype as a string; rdfs:range is a relation to a Datatype |
| `dg:GraphLayer` | no direct equivalent | — | DG-specific 4-layer partition concept |

**Alignment opportunity:** Declare in OWL:
```turtle
dg:Class           owl:equivalentClass    owl:Class .
dg:DatatypeProperty owl:equivalentClass   owl:DatatypeProperty .
dg:ObjectProperty   owl:equivalentClass   owl:ObjectProperty .
dg:label           owl:equivalentProperty rdfs:label .
```

**Caveat:** OntoGraph entities are *first-order data*, not the OWL TBox itself. Declaring equivalence would make every OntoGraph Class instance be inferred as `owl:Class`, which is correct semantically but may surprise reasoners that expect OWL classes to be schema-level. Use `rdfs:subClassOf` (⊑) if you want a softer alignment.

---

## 3. Layer 2: Metagraph ↔ SWRL

DG's Metagraph implements a **bespoke regex parser** for a subset of SWRL (see `DG_OBSIDIAN/knowledge/decisions/SWRL parsing is bespoke regex not vendor OWL library.md`). Structurally, DG entities are direct counterparts to SWRL classes.

| DG entity | SWRL equivalent | Strength | Notes |
|---|---|---|---|
| `dgm:Rule` | `swrl:Imp` (implication) | **≡** | A SWRL rule IS an implication (body → head) |
| `dgm:Atom` | `swrl:Atom` | **≡** | Abstract atom base |
| `dgm:ClassAtom` | `swrl:ClassAtom` | **≡** | Direct match |
| `dgm:DataPropertyAtom` | `swrl:DatavaluedPropertyAtom` | **≡** | DG uses shorter name |
| `dgm:ObjectPropertyAtom` | `swrl:IndividualPropertyAtom` | **≡** | DG uses shorter name |
| `dgm:BuiltinAtom` | `swrl:BuiltinAtom` | **≡** | Direct match |
| `dgm:Variable` | `swrl:Variable` | **≡** | Direct match |
| `dgm:ObjectVariable` | (none — SWRL doesn't distinguish) | **⊑** | DG refinement (VTYP-01 — Object vs Property variable typing) |
| `dgm:PropertyVariable` | (none) | **⊑** | DG refinement |
| `dgm:BuiltinVariable` | (none) | **⊑** | DG refinement (variables bound only in built-ins) |
| `dgm:Literal` | `rdfs:Literal` | **≡** | SWRL spec uses RDF literals directly |
| `dgm:Builtin` | `swrl:Builtin` | **≡** | Direct match |
| `dgm:hasBody` | `swrl:body` | **≡** | DG renamed for camelCase consistency |
| `dgm:hasHead` | `swrl:head` | **≡** | Same |
| `dgm:hasArg` | `swrl:argument1` / `swrl:argument2` | **⊒** | DG generalizes to an ordered `pos` property; SWRL uses positional argument1/2 |
| `dgm:refersTo` | `swrl:classPredicate` / `propertyPredicate` / `builtin` | **⊒** | DG generalizes the "what does this atom reference" pattern |
| `dgm:DesignRuleSession` | no SWRL equivalent | — | DG-specific (LLM ingest audit log) |

**Alignment opportunity:**
```turtle
dgm:Rule              owl:equivalentClass     swrl:Imp .
dgm:ClassAtom         owl:equivalentClass     swrl:ClassAtom .
dgm:DataPropertyAtom  owl:equivalentClass     swrl:DatavaluedPropertyAtom .
dgm:ObjectPropertyAtom owl:equivalentClass    swrl:IndividualPropertyAtom .
dgm:BuiltinAtom       owl:equivalentClass     swrl:BuiltinAtom .
dgm:Variable          owl:equivalentClass     swrl:Variable .
dgm:Builtin           owl:equivalentClass     swrl:Builtin .
dgm:hasBody           owl:equivalentProperty  swrl:body .
dgm:hasHead           owl:equivalentProperty  swrl:head .
```

**Caveat:** Adding these makes the DG ontology importable into SWRL-aware reasoners. But DG's `ObjectVariable`/`PropertyVariable`/`BuiltinVariable` trichotomy is *richer* than SWRL — they're subclasses, not equivalents.

---

## 4. Layer 3: ValidationGraph ↔ PROV-O + SOSA + SHACL + GeoSPARQL

This layer has the **most overlap** with external vocabs — three different W3C standards each cover one facet of "validation":

- **PROV-O** — *who did what, when* (provenance of validation runs)
- **SOSA/SSN** — *observation of a feature's property* (the validation event itself)
- **SHACL** — *constraint violation reports* (the pass/fail outcome)
- **GeoSPARQL** — *spatial features and geometry* (ObjectInstance / GeoRef)

### 4.1 ValidationRun — PROV Activity + SHACL ValidationReport

| DG entity | PROV-O | SHACL | Strength | Notes |
|---|---|---|---|---|
| `dgv:ValidationRun` | `prov:Activity` | `sh:ValidationReport` | **≈** | A run is BOTH an activity (provenance) AND a report (validation outcome) |
| `dgv:runId` | (PROV uses IRI directly) | — | **≈** | PROV identifies activities by IRI; DG stores a separate string ID |
| `dgv:status` (= `Status_Completed`) | (PROV has no terminal state) | `sh:conforms` (boolean) | **≈** | SHACL conforms ≈ DG passing; DG's `Status_Completed` is the run-level "finished" |
| `dgv:capturedAtUtc` | `prov:startedAtTime` | — | **≡** | PROV-O activity timestamp |
| `dgv:rulesJson` | `prov:used` (the rules) | `sh:shapesGraph` | **⊑** | Both express "what input this run consumed" |
| `dgv:statePayloadJson` | `prov:used` (the design state) | `sh:dataGraph` | **⊑** | Same |
| `dgv:hasEntity` | `prov:wasGeneratedBy` (inverse) | `sh:result` | **≈** | DG: Run → Entity; SHACL: Report → Result |

### 4.2 ValidationEntity — PROV Entity + SOSA Observation + SHACL ValidationResult

| DG entity | PROV-O | SOSA | SHACL | Strength | Notes |
|---|---|---|---|---|---|
| `dgv:ValidationEntity` | `prov:Entity` | `sosa:Observation` | `sh:ValidationResult` | **≈** | A row in the run's result table = the observation of a property on a feature |
| `dgv:validatesInstance` | — | `sosa:hasFeatureOfInterest` | `sh:focusNode` | **≡** | All three name "the thing being checked" |
| `dgv:propValueOf` | — | `sosa:observedProperty` | `sh:resultPath` | **≡** | "Which property was checked" |
| `dgv:propValue` | — | `sosa:hasSimpleResult` | `sh:value` | **≡** | "The value observed/measured" |
| `dgv:ruleId` (on Entity) | `prov:wasInformedBy` (the rule) | — | `sh:sourceShape` | **⊑** | "Which rule produced this result" |
| `dgv:status = Status_Passed` | — | — | `sh:Conforms` (boolean true) | **≈** | SHACL uses boolean conforms; DG uses enum |
| `dgv:status = Status_Failed` | — | — | `sh:Violation` (severity) | **≈** | SHACL severity ≠ enum, but semantics align |
| `dgv:displayName` | `dcterms:title` | `rdfs:label` | — | **≡** | Human-readable label |
| `dgv:dgEntityId` | (PROV uses IRI) | — | — | **≈** | Internal ID, no direct match |

### 4.3 ObjectInstance — GeoSPARQL Feature + SOSA FeatureOfInterest + BOT Element

| DG entity | GeoSPARQL | SOSA | BOT | Strength | Notes |
|---|---|---|---|---|---|
| `dgv:ObjectInstance` | `geo:Feature` | `sosa:FeatureOfInterest` | `bot:Element` | **≈** | A validated geometric thing |
| `dgv:hasObjectState` → `dgv:ObjectState` | — | — | — | — | DG-specific binding snapshot |
| `dgv:instanceId` | — | — | — | — | Internal ID, no direct match |

### 4.4 GeoRef — GeoSPARQL Geometry

| DG entity | GeoSPARQL | Strength | Notes |
|---|---|---|---|
| `dgv:GeoRef` | `geo:Geometry` | **≈** | DG: handle to source-system geometry; GeoSPARQL: actual geometric data (WKT/GML) |
| `dgv:hasGeoRef` | `geo:hasGeometry` | **≡** | Same role — "object has this geometry" |
| `dgv:geoRefId` | — | — | DG stores source-system handle (Speckle objectId); GeoSPARQL stores serialized geometry inline via `geo:asWKT` |

**Caveat:** DG's GeoRef is a *reference* to externally-stored geometry (in Speckle); GeoSPARQL Geometry is *the data*. They're related but not identical. Closest alignment: `geo:hasGeometry` as the property, with DG's geometry deliberately stored externally.

### 4.5 ObjectState — DG-specific binding pattern

| DG entity | External equivalent | Strength | Notes |
|---|---|---|---|
| `dgv:ObjectState` | no direct equivalent | — | The (ObjectInstance, ObjectVariable, GeoRef[]) binding is DG-specific |
| `dgv:hasObjectVariable` | `sosa:observedProperty` | **≈** | Tenuous — variable binding is structurally similar to "which thing this observation is about" |
| `dgv:objectRef` | `sosa:applicationId`-like pattern (Speckle convention) | **≈** | Stable string handle |

### 4.6 DesignState / DefState / IdRef — parametric snapshot

| DG entity | PROV-O | SOSA | Strength | Notes |
|---|---|---|---|---|
| `dgv:DesignState` | `prov:Entity` | `sosa:Sample` | **≈** | A snapshot used by an activity. SOSA Sample is the better match — it's a captured slice of reality |
| `dgv:DefState` | `prov:Entity` | `sosa:Sample` | **≈** | Same |
| `dgv:DesignStateParameter` | — | `sosa:Observation` (per parameter) | **⊑** | A single parameter capture is like a single observation |
| `dgv:hasParameter` | `prov:hadMember` | `sosa:hasMember` | **≈** | Composition relation |
| `dgv:IdRef` | `prov:identifier` | — | **⊑** | DG-specific auto-regenerating ID concept; PROV doesn't have an exact match |
| `dgv:idRefValue` | `prov:atTime` (similar role — versioning) | — | **≈** | IdRef changes are version-like |
| `dgv:resolvesTo` | `prov:specializationOf` | — | **⊑** | "This ID refers to that entity over time" |

### 4.7 IntegrationConfig — DCAT-ish

| DG entity | DCAT | Strength | Notes |
|---|---|---|---|
| `dgv:IntegrationConfig` | `dcat:DataService` | **≈** | Both describe a configured endpoint |
| `dgv:provider` | `dcat:endpointDescription` | **≈** | Identifies the external service |
| `dgv:speckleProjectId` | `dcat:identifier` (on a dcat:Dataset for the model) | **≈** | Foreign ID into Speckle |

### 4.8 Status enums — SHACL severity levels

| DG individual | SHACL equivalent | Strength |
|---|---|---|
| `dgv:Status_Completed` | (no SHACL equivalent — run-level not result-level) | — |
| `dgv:Status_Passed` | `sh:Info` or `sh:conforms = true` | **≈** |
| `dgv:Status_Failed` | `sh:Violation` | **≈** |
| `dgv:ReinstatementStatus_*` | DG-specific | — | No external equivalent |

---

## 5. Layer 4: KnowledgeGraph ↔ SKOS + Dublin Core + SIOC

The Knowledge layer is mostly note-and-tag organization — well-trodden ground in linked data.

| DG entity | External equivalent | Strength | Notes |
|---|---|---|---|
| `dgk:KnowledgeNote` | `sioc:Post` / `foaf:Document` | **≈** | A text artifact with title, content, source |
| `dgk:KnowledgeTag` | `skos:Concept` | **≡** | A tag IS a concept in a tag taxonomy |
| `dgk:KnowledgeClass` | `skos:ConceptScheme` | **⊒** | DG hub node aggregates type instances; SKOS scheme aggregates concepts |
| `dgk:KnowledgeSession` | `prov:Activity` (insert/query/update) | **≈** | An interaction event with a tool |
| `dgk:title` | `dcterms:title` | **≡** | Direct match |
| `dgk:content` | `sioc:content` / `rdf:value` | **≡** | Body text |
| `dgk:source` | `dcterms:source` | **≡** | Source reference |
| `dgk:tagName` | `skos:prefLabel` | **≡** | Canonical tag name |
| `dgk:taggedWith` | `skos:related` (looser) / `dcterms:subject` (tighter) | **≈** | Note → Tag connection |
| `dgk:noteId` | `dcterms:identifier` | **≡** | Identifier |
| `dgk:knowledgeSessionId` | `dcterms:identifier` | **≡** | Same |
| `dgk:createdAt` | `dcterms:created` | **≡** | Creation timestamp |
| `dgk:updatedAt` | `dcterms:modified` | **≡** | Modification timestamp |
| `dgk:mode` (insert/query/update) | `prov:Activity` subclasses | **⊑** | Could be modeled as PROV sub-activity types |
| `dgk:sessionPrompt` | `prov:value` | **≈** | The text input that drove the session |
| `dgk:sessionResult` | `prov:generated` | **≈** | The output generated |

**Alignment opportunity (highest-value):**
```turtle
dgk:KnowledgeTag  owl:equivalentClass     skos:Concept .
dgk:tagName       owl:equivalentProperty  skos:prefLabel .
dgk:title         owl:equivalentProperty  dcterms:title .
dgk:source        owl:equivalentProperty  dcterms:source .
dgk:createdAt     owl:equivalentProperty  dcterms:created .
dgk:updatedAt     owl:equivalentProperty  dcterms:modified .
dgk:noteId        owl:equivalentProperty  dcterms:identifier .
```

---

## 6. Cross-cutting properties

DG-defined annotation properties used across all layers:

| DG property | External equivalent | Strength | Notes |
|---|---|---|---|
| `dg:graph` (layer tag) | no external equivalent | — | DG's 4-layer partition is DG-specific |
| `dg:project` (project isolation key) | `dcterms:isPartOf` | **≈** | "This entity belongs to project X" |
| `dg:SWRL_label` (display in SWRL syntax) | `rdfs:label` (with language tag) | **⊑** | Specialized label |
| `dg:createdAt` (cross-layer) | `dcterms:created` | **≡** | Direct match |
| `dgm:order` (atom position in body/head) | `rdf:_n` (RDF container index) | **≈** | Both express ordinal position |
| `dgm:pos` (argument position in atom) | `rdf:_n` | **≈** | Same |

---

## 7. Recommendations

Listed in priority order — start at the top, stop when the cost outweighs the benefit for your use case.

### R1. Highest value — declare SWRL alignment

**Cost:** ~10 `owl:equivalentClass` / `owl:equivalentProperty` axioms.
**Benefit:** Any SWRL-aware tool (Protégé's SWRL tab, vendor reasoners with SWRL support, the WebProtege rule editor) can read and edit DG rules directly. Removes the "bespoke parser" tax for external integrations.

### R2. High value — declare PROV-O alignment on ValidationRun + ValidationEntity

**Cost:** ~6 axioms.
**Benefit:** PROV-aware lineage tools (Apache Atlas, Marquez, OpenLineage) can ingest DG validation events without custom adapters. Valuable when DG runs need to participate in a wider data-platform audit trail.

```turtle
dgv:ValidationRun    rdfs:subClassOf  prov:Activity .
dgv:ValidationEntity rdfs:subClassOf  prov:Entity .
dgv:capturedAtUtc    rdfs:subPropertyOf  prov:startedAtTime .
dgv:hasEntity        rdfs:subPropertyOf  prov:wasInfluencedBy .
```

### R3. High value — declare SOSA alignment for the observation pattern

**Cost:** ~5 axioms.
**Benefit:** Makes the "validate a property on a feature" semantics machine-readable in IoT / building-monitoring ecosystems. Critical if DG ever ingests live sensor data alongside design rules.

```turtle
dgv:ValidationEntity  rdfs:subClassOf       sosa:Observation .
dgv:ObjectInstance    rdfs:subClassOf       sosa:FeatureOfInterest .
dgv:validatesInstance owl:equivalentProperty sosa:hasFeatureOfInterest .
dgv:propValueOf       owl:equivalentProperty sosa:observedProperty .
dgv:propValue         rdfs:subPropertyOf    sosa:hasSimpleResult .
```

### R4. Medium value — declare SHACL alignment for validation reports

**Cost:** ~4 axioms.
**Benefit:** SHACL is the modern W3C answer to "validation results." Aligning lets DG runs be consumed by SHACL tooling. Less critical because SHACL's TBox-driven shapes don't translate to DG's rule-by-natural-language flow — but the *report* model maps cleanly.

```turtle
dgv:ValidationRun    rdfs:subClassOf  sh:ValidationReport .
dgv:ValidationEntity rdfs:subClassOf  sh:ValidationResult .
dgv:validatesInstance owl:equivalentProperty sh:focusNode .
dgv:propValueOf      owl:equivalentProperty sh:resultPath .
```

### R5. Medium value — reuse SKOS + DCTerms in KnowledgeGraph

**Cost:** ~7 axioms.
**Benefit:** Standard, idiomatic linked-data for note/tag taxonomies. Knowledge tools (SkosMos, VocBench, PoolParty) become read-compatible with DG knowledge.

See Section 5 for the axiom list.

### R6. Medium value — reuse `geo:hasGeometry`

**Cost:** 1 axiom (subPropertyOf) plus optional `geo:asWKT` if geometry is ever serialized.
**Benefit:** GeoSPARQL-compatible spatial queries. Critical only if DG integrates with GIS tooling (QGIS, ArcGIS, geo-Triplestore).

```turtle
dgv:hasGeoRef  rdfs:subPropertyOf  geo:hasGeometry .
dgv:ObjectInstance  rdfs:subClassOf  geo:Feature .
dgv:GeoRef     rdfs:subClassOf  geo:Geometry .
```

### R7. Low value — declare OWL meta-schema alignment (OntoGraph)

**Cost:** 4 axioms.
**Benefit:** Mostly cosmetic — the OntoGraph layer reifies OWL into Neo4j for query-ability. Declaring `owl:equivalentClass` between `dg:Class` and `owl:Class` is correct but may confuse reasoners that expect to operate on OWL classes directly, not their data-level reifications.

**Recommendation:** Use `rdfs:subClassOf` (⊑) instead of `owl:equivalentClass` (≡) here to avoid pulling OntoGraph data instances into the OWL meta-schema.

### Defer / skip

| Vocabulary | Why deferred |
|---|---|
| **BOT** (Building Topology Ontology) | DG's domain classes are dynamically generated per-project — they don't fit BOT's fixed building/storey/space hierarchy. Aligning would force a rigid schema DG deliberately avoids. |
| **IFC-OWL** | Even larger and more specific than BOT. Same rejection rationale. |
| **OWL-Time** | DG only needs simple xsd:dateTime; the full Time Ontology (Instant, Interval, ProperInterval, TemporalUnit) is overkill. |
| **DCAT-AP / VOID** | `IntegrationConfig` is too small a surface to justify a Dataset/Distribution/DataService alignment. Re-evaluate if Speckle integration grows. |
| **FOAF** | DG has no `Person` / `Agent` model yet. Add if/when authentication and authorship arrive. |

---

## 8. Why DG doesn't reuse these vocabs directly

Important context for anyone reading this map and asking "why didn't you just *use* SWRL/PROV-O/SOSA?"

### 8.1 Neo4j storage model — not a triplestore

DG persists everything in Neo4j as a property graph, not RDF triples. Most of the alignment recommendations would be **annotations declaring equivalence** in the OWL file (`DesignGrammar.owl`) — they don't change how data is stored. The benefit is for *external* tools that ingest the OWL file, not for DG's own runtime.

### 8.2 Bespoke SWRL parser (intentional)

See `DG_OBSIDIAN/knowledge/decisions/SWRL parsing is bespoke regex not vendor OWL library.md`. DG parses a deliberate **subset** of SWRL (ClassAtom + DataPropertyAtom + BuiltinAtom only) to keep the LLM Cypher generation tractable. Declaring SWRL equivalence in OWL is fine; importing a vendor SWRL library would break the LLM prompt design.

### 8.3 Project-specific domain ontologies

DG's domain classes (Building, Street, LivingUnit) are **dynamically generated** per project. BOT/IFC-OWL/Brick assume a fixed building topology — they're wrong tools for parametric design rules where the architect *defines* what classes exist for their project. DG's OntoGraph layer **is** the per-project domain ontology.

### 8.4 LLM-friendly schema

The 4-layer Neo4j structure with `graph` and `project` properties is optimized for LLM Cypher generation (small, focused schema slices). Re-using SHACL/PROV-O directly would force the LLM to learn a larger, more abstract vocabulary — degrading rule-generation accuracy.

---

## 9. Sources

### W3C / OGC Standards (canonical specifications)

- **OWL 2 Web Ontology Language** — https://www.w3.org/TR/owl2-overview/ (W3C REC, 2012)
- **RDF Schema 1.1** — https://www.w3.org/TR/rdf-schema/ (W3C REC, 2014)
- **SWRL W3C Submission** — https://www.w3.org/Submission/SWRL/ (2004) — namespace `http://www.w3.org/2003/11/swrl#`
- **PROV-O: The PROV Ontology** — https://www.w3.org/TR/prov-o/ (W3C REC, 2013) — namespace `http://www.w3.org/ns/prov#`
- **SOSA/SSN Ontology** — https://www.w3.org/TR/vocab-ssn/ (W3C REC, 2017) — namespace `http://www.w3.org/ns/sosa/`
- **SHACL Shapes Constraint Language** — https://www.w3.org/TR/shacl/ (W3C REC, 2017) — namespace `http://www.w3.org/ns/shacl#`
- **SKOS Reference** — https://www.w3.org/TR/skos-reference/ (W3C REC, 2009) — namespace `http://www.w3.org/2004/02/skos/core#`
- **GeoSPARQL** — https://www.ogc.org/standards/geosparql (OGC, 2012) — namespace `http://www.opengis.net/ont/geosparql#`
- **OWL-Time** — https://www.w3.org/TR/owl-time/ (W3C REC, 2017) — namespace `http://www.w3.org/2006/time#`

### Catalogs

- **Linked Open Vocabularies (LOV)** — https://lov.linkeddata.es/dataset/lov/vocabs — 900+ vocabularies, searchable cross-reference of namespaces, classes, properties.
- **W3C Linked Building Data Community Group** — https://www.w3.org/community/lbd/ — home of BOT and related building-data ontologies.

### Domain vocabularies (deferred but referenced)

- **Building Topology Ontology (BOT)** — https://w3id.org/bot — W3C-LBD-CG draft, namespace `https://w3id.org/bot#`
- **Dublin Core Terms** — https://www.dublincore.org/specifications/dublin-core/dcmi-terms/ — namespace `http://purl.org/dc/terms/`
- **FOAF** — http://xmlns.com/foaf/spec/ — namespace `http://xmlns.com/foaf/0.1/`
- **DCAT** — https://www.w3.org/TR/vocab-dcat-3/ — namespace `http://www.w3.org/ns/dcat#`

### Internal references

- `[DesignGrammar.owl](DesignGrammar.owl)` — DG ontology v3.1
- `[REQUIREMENTS.md](../.planning/REQUIREMENTS.md)` — v3.0 requirements driving the ontology shape
- `DG_OBSIDIAN/knowledge/decisions/SWRL parsing is bespoke regex not vendor OWL library.md` — rationale for parser subset
- `DG_OBSIDIAN/atlas/Graph schema v3 is the canonical data model.md` — canonical Neo4j schema

---

*Last updated: 2026-05-15 — initial alignment audit covering v3.1 ontology against LOV catalog and 9 external vocabularies.*
