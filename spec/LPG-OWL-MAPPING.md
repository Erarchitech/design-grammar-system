# LPG to OWL Mapping (Neo4j Property Graph to RDF/OWL)

## Overview

This document is the **normative mapping contract** between DG's Neo4j labelled-property graph (LPG) and the standard RDF/OWL/SWRL representation used for OWL 2 DL reasoning and external-tool interoperability (Protégé, OWL API).

**Normative scope** (these sections are the binding contract Phase 821 implements):
- [Metagraph -> SWRL RDF](#metagraph-to-swrl-rdf-mapping) -- every Metagraph node/relationship maps onto the W3C SWRL RDF vocabulary
- [OntoGraph -> OWL](#ontograph-to-owl-mapping) -- domain vocabulary maps to standard OWL terms
- [Edge-Property Reification](#edge-property-reification) -- `ARG.pos`, `HAS_BODY.order`, `HAS_HEAD.order` are preserved through rdf:List and numbered argument slots
- [IRI Minting Strategy](#iri-minting-strategy) -- deterministic IRIs for all named entities
- [Export Scoping](#export-scoping) -- label-based Cypher scoping (not `graph`-property)
- [Unique Name Assumption](#unique-name-assumption-una) -- `owl:AllDifferent` for future ABox exports

**Informative scope** (forward-looking sketch, non-normative):
- [ValidGraph -> RDF Sketch](#validgraph-to-rdf-sketch-informative) -- preliminary mapping for Phase 823

The authoritative node/label/property definitions for each graph layer are in **`spec/DATABASE.md`** (see [§ Graph Separation](spec/DATABASE.md#graph-separation)). This document adds only the RDF-mapping columns -- it does not duplicate the base schema.

---

## Namespaces & Terminology

| Prefix | Namespace IRI | Scope |
|--------|---------------|-------|
| `dg:` | `http://example.org/design-grammar#` | Meta-schema: graph-layers, SWRL-label, project annotations |
| `dgm:` | `http://example.org/design-grammar/meta#` | Meta-schema: Metagraph-layer entity definitions |
| `dgv:` | `http://example.org/design-grammar/valid#` | Meta-schema: ValidGraph-layer entity definitions |
| `dgs:` | `http://example.org/design-grammar/spec#` | Meta-schema: SpecGraph-layer entity definitions |
| `dgc:` | `http://example.org/design-grammar/comp#` | Meta-schema: Computgraph-layer entity definitions |
| `ex:` | `http://example.org/design-grammar/ex#` | **Per-project dynamically-generated domain vocabulary** (NOT part of the static meta-schema; unioned only at reasoning time) |
| `swrl:` | `http://www.w3.org/2003/11/swrl#` | W3C SWRL RDF submission vocabulary |
| `swrlb:` | `http://www.w3.org/2003/11/swrlb#` | SWRL builtin vocabulary |
| `rdf:` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` | RDF core |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` | RDF Schema |
| `owl:` | `http://www.w3.org/2002/07/owl#` | OWL 2 Web Ontology Language |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` | XML Schema datatypes |

The `dg/dgm/dgv/dgs/dgc:` meta-schema namespaces are defined by `ontology/DesignGrammar-V7.owl` (the static TBox). The `ex:` domain-vocabulary namespace is **explicitly separate** -- the V7 file's own comment states that domain-specific classes "are dynamically generated from user prompts ... and are NOT part of this ontology." The two namespace families are unioned only at reasoning time in the hybrid export.

---

## Metagraph to SWRL RDF Mapping

### Node Mapping Table

Every Metagraph node maps to a standard W3C SWRL RDF vocabulary term. The mapping reuses the node's stored `iri` where present (Builtin); deterministic IRIs are minted for all other entities per the [IRI Minting Strategy](#iri-minting-strategy).

| DG (Neo4j) | RDF/OWL Term | Notes |
|---|---|---|
| `Rule` node | `swrl:Imp` | `rdfs:label` = `Rule_Id`. `Rule.kind`, `Rule.RuleName`, `Rule.RuleDescription` become `dg:`-namespace annotation properties (no SWRL equivalent). |
| `Atom {type: 'ClassAtom'}` | `swrl:ClassAtom` | `swrl:classPredicate` points to the `REFERS_TO` target (an `owl:Class`). `ARG pos:1` => `swrl:argument1` (the individual variable). |
| `Atom {type: 'DataPropertyAtom'}` | `swrl:DatavaluedPropertyAtom` | `swrl:propertyPredicate` points to the `REFERS_TO` target (`owl:DatatypeProperty`). Arguments: `swrl:argument1` (entity), `swrl:argument2` (value). |
| `Atom {type: 'ObjectPropertyAtom'}` | `swrl:IndividualPropertyAtom` | `swrl:propertyPredicate` points to the `REFERS_TO` target (`owl:ObjectProperty`). Arguments: `swrl:argument1` (subject), `swrl:argument2` (object). No `ObjectProperty` nodes exist in `v8-ui-smoke` live data, but the mapping is schema-legal per `cypher_template.txt`. |
| `Atom {type: 'BuiltinAtom'}` | `swrl:BuiltinAtom` | `swrl:builtin` points to the `REFERS_TO` target (a `swrl:Builtin`). Arguments via `swrl:arguments` (an `rdf:List`) -- universally, not `argument1`/`argument2` -- because builtin arity varies (see [BuiltinAtom subsection](#builtinatom-and-swrlarguments) below). |
| `Var` node | `swrl:Variable` | Minted individual IRI. The leading `?` is stripped from `Var.name` for the IRI local part. |
| `Literal` node | RDF typed literal | Becomes an `xsd:`-typed literal value, not a named individual. `Literal.lex` is the lexical form; `Literal.datatype` maps to `xsd:` matching (see [XSD type map](#literal-to-typed-literal)). |
| `Builtin` node | `swrl:Builtin` | Reuses the stored `iri` verbatim (e.g. `swrlb:greaterThan`). Declared as `swrl:Builtin` in the RDF graph. |

**Example: Complete rule as `swrl:Imp` (Turtle)**

```turtle
@prefix ex:    <http://example.org/design-grammar/ex#> .
@prefix owl:   <http://www.w3.org/2002/07/owl#> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix swrl:  <http://www.w3.org/2003/11/swrl#> .
@prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/design-grammar/project/v8-ui-smoke/rule/R_BUILDING_MAX_STOREY_9_V>
    a swrl:Imp ;
    rdfs:label "R_BUILDING_MAX_STOREY_9_V" ;
    swrl:body ( [ a swrl:ClassAtom ; swrl:classPredicate ex:Building ;
                  swrl:argument1 <http://example.org/design-grammar/project/v8-ui-smoke/var/b> ]
                [ a swrl:DatavaluedPropertyAtom ; swrl:propertyPredicate ex:hasStoreyCount ;
                  swrl:argument1 <http://example.org/design-grammar/project/v8-ui-smoke/var/b> ;
                  swrl:argument2 <http://example.org/design-grammar/project/v8-ui-smoke/var/h> ]
                [ a swrl:BuiltinAtom ; swrl:builtin swrlb:greaterThan ;
                  swrl:arguments ( <http://example.org/design-grammar/project/v8-ui-smoke/var/h>
                                   "9"^^xsd:integer ) ] ) ;
    swrl:head ( [ a swrl:DatavaluedPropertyAtom ; swrl:propertyPredicate ex:violatesMaxStoreyCount ;
                  swrl:argument1 <http://example.org/design-grammar/project/v8-ui-smoke/var/b> ;
                  swrl:argument2 true ] ) .
```

### BuiltinAtom and `swrl:arguments`

BuiltinAtom MUST use the `swrl:arguments` `rdf:List` form universally, NOT `swrl:argument1`/`swrl:argument2`. The list form is strictly more general (it costs nothing for binary builtins) and handles the general case where a builtin can have 3 or more arguments.

**Live arity verification (v8-ui-smoke, 2026-07-11):** The following builtins exist in the live database. Their observed `ARG`-edge counts per atom are listed.

| Builtin | Observed Arity (per atom) | Notes |
|---------|--------------------------|-------|
| `swrlb:greaterThan` | 2 (max across atoms) | One atom (`R_CORRIDOR_MAX_LENGTH_14_V_A3`) shows arity 1 -- incomplete data in live graph, not a real arity. |
| `swrlb:lessThan` | 2 | Used in 3 atoms, all binary. |
| `swrlb:or` | 2 | Used in 1 atom. |
| `swrlb:equalTo` | 2 | Used in 1 atom. |
| `swrlb:continuousFromTo` | 0 (incomplete) | The atom `R_COLUMN_CONTINUITY_V_A3` exists but has zero `ARG` edges -- the export captures it as a `dgm:SkippedAtom` (SWRL-incomplete). Expected arity: 3 (value, from, to). |
| `swrlb:fillet` | (not used) | Builtin node exists but no BuiltinAtom references it via `REFERS_TO` in `v8-ui-smoke`. |
| `swrlb:notEqual` | (not used) | Builtin node exists but not referenced by any BuiltinAtom in `v8-ui-smoke`. |
| `swrlb:towards` | (not used) | Builtin node exists but not referenced by any BuiltinAtom in `v8-ui-smoke`. Expected arity: 3+ (directional comparison with target). |

**Key takeaway:** The list form is mandatory because (a) `continuousFromTo` and `towards` are semantically 3-argument builtins, and (b) the live graph's real observed arity for `greaterThan` includes an incomplete 1-arg case that the export must handle defensively rather than silently dropping arguments.

### Literal to Typed Literal

The `Literal` node's `datatype` property (stored as `xsd:decimal`, `xsd:integer`, `xsd:boolean`, `xsd:string`) maps to the corresponding XSD datatype IRI. The `lex` property becomes the lexical form.

| Stored `datatype` | RDF Datatype IRI |
|---|---|
| `xsd:decimal` | `xsd:decimal` |
| `xsd:integer` or `xsd:int` | `xsd:integer` |
| `xsd:boolean` | `xsd:boolean` |
| `xsd:string` | `xsd:string` |
| `xsd:float` | `xsd:float` |
| `xsd:double` | `xsd:double` |
| `xsd:dateTime` | `xsd:dateTime` |
| (none / null) | `xsd:string` |

---

## Edge-Property Reification

This section documents how edge-level properties (which have no native RDF/OWL equivalent) are preserved through the LPG->RDF translation. This is the core deliverable of requirement **REAS-04**.

### `ARG.pos` Reification

The `ARG` relationship carries a `pos` property (integer, 1-indexed) representing the argument position in a SWRL atom. The mapping strategy differs by atom kind:

**Binary atom kinds (ClassAtom, DatavaluedPropertyAtom, IndividualPropertyAtom):**

`pos: 1` maps to `swrl:argument1`, `pos: 2` maps to `swrl:argument2`.

```turtle
# Source atom in Cypher: (a1)-[:ARG {pos:1}]->(:Var {name: "?b"})
#                    (a1)-[:ARG {pos:2}]->(:Var {name: "?h"})
# Maps to:
[] a swrl:DatavaluedPropertyAtom ;
    swrl:propertyPredicate ex:hasHeight ;
    swrl:argument1 <http://example.org/design-grammar/project/v8-ui-smoke/var/b> ;
    swrl:argument2 <http://example.org/design-grammar/project/v8-ui-smoke/var/h> .
```

**BuiltinAtom (variable arity):**

All `ARG` edges to a BuiltinAtom are collected, sorted by `pos`, and encoded as an `rdf:List` via `swrl:arguments`. This preserves positional order regardless of arity.

```turtle
# Source atom in Cypher:
#   (a3)-[:ARG {pos:1}]->(:Var {name: "?h"})
#   (a3)-[:ARG {pos:2}]->(:Literal {lex: "75", datatype: "xsd:decimal"})
# Maps to:
[] a swrl:BuiltinAtom ;
    swrl:builtin swrlb:greaterThan ;
    swrl:arguments ( <http://example.org/design-grammar/project/v8-ui-smoke/var/h>
                     "75"^^xsd:decimal ) .
```

### `HAS_BODY` / `HAS_HEAD` `order` Reification

The `HAS_BODY` and `HAS_HEAD` relationships carry an `order` property (integer, 1-indexed) representing the atom sequence in the rule's body or head.

In the SWRL RDF vocabulary, atom sequence is expressed through a typed `rdf:List` chain using `swrl:AtomList`:

- `swrl:body` points from the `swrl:Imp` to the head of a `swrl:AtomList`
- `swrl:head` points from the `swrl:Imp` to the head of a `swrl:AtomList`
- Each list cell is typed `swrl:AtomList` and carries `rdf:first` (the atom) and `rdf:rest` (the next cell, or `rdf:nil`)
- The `order` property becomes **implicit list position**: atoms sorted by `order` in ascending sequence produce the corresponding first/rest chain

```turtle
# Source Cypher relationships for R_BUILDING_MAX_STOREY_9_V:
#   (r)-[:HAS_BODY {order: 1}]->(a1)   -- ClassAtom
#   (r)-[:HAS_BODY {order: 2}]->(a2)   -- DatavaluedPropertyAtom
#   (r)-[:HAS_BODY {order: 3}]->(a3)   -- BuiltinAtom
#
# The Turtle shorthand `( ... )` expands to the swrl:AtomList chain:
<http://example.org/design-grammar/project/v8-ui-smoke/rule/R_BUILDING_MAX_STOREY_9_V>
    swrl:body ( [ a swrl:ClassAtom ; ... ]
                [ a swrl:DatavaluedPropertyAtom ; ... ]
                [ a swrl:BuiltinAtom ; ... ] ) .
```

---

## IRI Minting Strategy

IRIs are minted according to the following rules:

### Entities that Reuse the Stored `iri`

| Node Label | Stored `iri` Example | RDF IRI | Rationale |
|---|---|---|---|
| `Class` | `ex:Building` | `http://example.org/design-grammar/ex#Building` | Domain ontology term with stable identity |
| `DatatypeProperty` | `ex:hasHeight` | `http://example.org/design-grammar/ex#hasHeight` | Domain ontology term with stable identity |
| `ObjectProperty` | `ex:locatedIn` | `http://example.org/design-grammar/ex#locatedIn` | Domain ontology term with stable identity |
| `Builtin` | `swrlb:greaterThan` | `http://www.w3.org/2003/11/swrlb#greaterThan` | Standard SWRL builtin IRI |

The stored `iri` CURIE is expanded via prefix lookup (`ex:` -> `http://example.org/design-grammar/ex#`, `swrlb:` -> `http://www.w3.org/2003/11/swrlb#`).

### Entities that Get Minted IRIs

Base IRI: `http://example.org/design-grammar` (matches `xml:base` in `ontology/DesignGrammar-V7.owl`).

Path scheme: `{base}/project/{project}/{kind}/{local-part}` where:

| Entity | `kind` | `local-part` | Example |
|--------|--------|-------------|---------|
| `Rule` | `rule` | `Rule_Id` | `http://example.org/design-grammar/project/v8-ui-smoke/rule/R_BUILDING_MAX_STOREY_9_V` |
| `Atom` | `atom` | `Atom_Id` | `http://example.org/design-grammar/project/v8-ui-smoke/atom/R_BUILDING_MAX_STOREY_9_V_A1` |
| `Var` | `var` | `name` with leading `?` stripped | `http://example.org/design-grammar/project/v8-ui-smoke/var/b` |

`Literal` nodes are NOT minted as IRIs -- they become typed RDF literal values.

### Namespace Separation Principle

The base IRI namespace `http://example.org/design-grammar` hosts both the static meta-schema (the `dg/dgm/dgv/dgs/dgc:` sub-namespaces from `DesignGrammar-V7.owl`) and the dynamically generated project entities (under `project/` path segments). However, the `ex:` domain-vocabulary namespace (`http://example.org/design-grammar/ex#`) is **conceptually and operationally separate** from the meta-schema:

- **Meta-schema** (`dg:`, `dgm:`, `dgv:`, `dgs:`, `dgc:`): defined once in `DesignGrammar-V7.owl`, never modified by the export. Contains graph-layer classes, annotation properties, and the abstract data-model classes.
- **Domain vocabulary** (`ex:`): per-project, dynamically generated by LLM rule-ingest. Contains domain classes like `ex:Building`, `ex:Facade`, `ex:hasHeight`. The V7 ontology explicitly disclaims these.
- **Project entities** (minted under `{base}/project/`): the RDF individuals representing Rule, Atom, Var -- per-project, dynamically generated by the export.

These three groups are unioned (merged into a single RDFLib Graph/Owlready2 ontology) only at reasoning time. The separation ensures the static TBox can be version-controlled and curated independently of live project data.

---

## Export Scoping

### Mandate: Scope by Label, Not by the `graph` Property

Every Cypher query that extracts Metagraph or OntoGraph nodes for RDF translation MUST scope by node **label**, not by the `graph` property. The `graph` property is informational and **not authoritative**.

**Correct patterns:**

```cypher
// Metagraph -- scope by label
MATCH (n)
WHERE n.project = $project
  AND (n:Rule OR n:Atom OR n:Var OR n:Literal OR n:Builtin)
RETURN n

// OntoGraph -- scope by label
MATCH (n)
WHERE n.project = $project
  AND (n:Class OR n:DatatypeProperty OR n:ObjectProperty)
RETURN n
```

**Incorrect pattern (forbidden):**

```cypher
// INCORRECT -- will silently drop nodes with mistagged graph property
MATCH (n {project: $project, graph: 'Metagraph'})
RETURN n
```

### Why This Matters (Confirmed Data-Quality Finding)

This requirement is not theoretical. A live-data audit on 2026-07-11 confirmed that `v8-ui-smoke` has two `Atom` nodes (`R_DOOR_ORIENTATION_V_A1` and `R_DOOR_ORIENTATION_V_A2`) carrying `graph:'OntoGraph'` instead of the schema-mandated `graph:'Metagraph'`. Any export scoped by `{project, graph: 'Metagraph'}` silently drops these two atoms.

The same audit found broader, systemic tagging drift: `phase14-smoke` has six `DesignState` and two `Run` nodes tagged `graph:'Metagraph'` instead of `graph:'ValidGraph'`. Label-based scoping is the only reliable defense.

---

## OntoGraph to OWL Mapping

### Node Mapping Table

| DG (Neo4j) | RDF/OWL Term | IRI Source | Notes |
|---|---|---|---|
| `Class` node | `owl:Class` | Reuses stored `iri` | Domain concept declaration. |
| `DatatypeProperty` node | `owl:DatatypeProperty` | Reuses stored `iri` | Data-valued attribute declaration. |
| `ObjectProperty` node | `owl:ObjectProperty` | Reuses stored `iri` | Object-relationship declaration. |

### Flatness of the Live OntoGraph

The live Neo4j database has been empirically verified (2026-07-11) to contain **zero** `SUBCLASS_OF`, `DOMAIN`, `RANGE`, or `DISJOINT_WITH` relationship types across all 14 distinct relationship types in the database. The OntoGraph is a **flat vocabulary** -- it declares terms, not axioms.

This means the live RDF export contributes only `owl:Class`, `owl:DatatypeProperty`, and `owl:ObjectProperty` declarations. All subsumption, domain, range, and disjointness axioms come from the **static `DesignGrammar-V7.owl` TBox**, not from the dynamic export. The hybrid union at reasoning time combines:

1. **Static TBox** (DesignGrammar-V7.owl): 68 `rdfs:subClassOf`, 105 `rdfs:domain`, 112 `rdfs:range`, 0 `owl:disjointWith` (rdflib-parsed counts, 2026-07-11)
2. **Live OntoGraph**: project-scoped class/property declarations
3. **Curated disjointness**: design-time `owl:disjointWith` axioms added to the static TBox (the V7 export has zero, so consistency checking cannot meaningfully fail without them)

ObjectPropertyAtom mapping is normatively specified (schema-legal per `cypher_template.txt`) even though no `ObjectProperty` nodes exist in `v8-ui-smoke` live data.

---

## Unique Name Assumption (UNA)

### The Problem

OWL 2 DL reasoners (including HermiT) do **not** assume the Unique Name Assumption by default. Two individuals with different IRIs can be inferred to be the same individual if the reasoner finds evidence to merge them. In contrast, Neo4j treats every node as intrinsically distinct (nodes are never merged unless explicitly `MERGE`d on a key property).

When Phase 823 exports ValidGraph entities (DesignState, Run) as named OWL individuals, any reasoner invocation over the merged graph could merge instances the Neo4j database treats as distinct, producing spurious inferences.

### Normative Requirement

The LPG->RDF translator MUST emit, for every project export batch that includes **named individuals** (future ABox export), exactly one `owl:AllDifferent` declaration enumerating every minted named individual via `owl:distinctMembers`.

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .

[] a owl:AllDifferent ;
    owl:distinctMembers (
        <http://example.org/design-grammar/project/v8-ui-smoke/var/b>
        <http://example.org/design-grammar/project/v8-ui-smoke/var/h>
        <http://example.org/design-grammar/project/v8-ui-smoke/atom/R_BUILDING_MAX_STOREY_9_V_A1>
        <http://example.org/design-grammar/project/v8-ui-smoke/atom/R_BUILDING_MAX_STOREY_9_V_A2>
        <http://example.org/design-grammar/project/v8-ui-smoke/atom/R_BUILDING_MAX_STOREY_9_V_A3>
        <!-- ... all minted named individuals in this project's export batch ... -->
    ) .
```

**Scope:** Phase 820's spike and current TBox-only reasoning do not need this (no individuals are minted). The requirement is forward-looking normative for Phase 823's ValidGraph->RDF (ABox) translator.

**Implementation:** The `owl:distinctMembers` list is populated by collecting every `URIRef` that was minted (Rule, Atom, Var) and, in Phase 823, every DesignState and Run URI. The list is the concatenation of all named individuals in the export batch.

---

## ValidGraph to RDF Sketch (Informative)

> **Status:** Informative. This section is a forward-looking sketch for Phase 823. It is NOT normative -- the details will be finalized when the ValidGraph->RDF translator is built.

The ValidGraph layer stores validation execution state: design states (3-part composition of object, parameter, and property snapshots) and runs (with their Boolean pass/fail lists). This section sketches how these would map to RDF individuals in a future ABox export.

### DesignState

A `DesignState` node with `kind` field (`ObjState`, `ParamState`, `PropState`) represents a fragment of design state captured during validation. Each maps to an `owl:NamedIndividual` with `rdf:type` reflecting its kind:

| `kind` | RDF Type | Description |
|--------|----------|-------------|
| `ObjState` | `dgv:ObjState` | Object + Geometry + Label snapshot |
| `ParamState` | `dgv:ParamState` | Parameter list (sliders, toggles) |
| `PropState` | `dgv:PropState` | Rule + DataProperty + PropValue composition |

IRI: `{base}/project/{project}/state/{StateId}` (e.g. `http://example.org/design-grammar/project/v8-ui-smoke/state/OS_abc123`)

The `HAS_STATE` relationship that composes a parent `DesignState` from its `ObjState`/`ParamState`/`PropState` children would map to a `dgv:hasState` object property.

### Run

A `Run` node records one validation execution:

- `owl:NamedIndividual` with `rdf:type` `dgv:Run`
- IRI: `{base}/project/{project}/run/{Run_Id}`
- `Run.ValidStatus` (Boolean list per ObjState): serialized as an `rdf:List` of `xsd:boolean` literals, attached via a `dgv:validStatus` annotation or object property
- `Run.SendStatus` (single Boolean): attached as `dgv:sendStatus` `xsd:boolean` datatype property

The relationship to `DesignState` (represented in Cypher as `(:Run)-[:VALIDATES]->(:DesignState)`) maps to `dgv:validates` object property.

### UNA Interaction

Because ValidGraph nodes are named individuals, the `owl:AllDifferent` requirement (see [UNA section](#unique-name-assumption-una)) becomes critical: every DesignState and Run IRI must be listed in the project's `owl:distinctMembers` declaration, alongside the Metagraph individuals, to prevent the reasoner from merging e.g. two distinct `dgv:ObjState` individuals with overlapping property values.

---

## SWRL Builtin Exclusion from Reasoner Input

**Status:** Implementation note, not a mapping rule.

HermiT (the reasoner bundled by Owlready2) **rejects any ontology containing SWRL builtin atoms**. DG's violation pattern is builtin-centric -- nearly every rule has a `swrl:BuiltinAtom` in its body. Attempting to pass a full SWRL mapping to HermiT fails with "built-in atoms are not supported yet" (`java.lang.IllegalArgumentException`).

Therefore, the reasoning pipeline MUST strip `swrl:BuiltinAtom`-containing rules from the RDF graph before passing it to the reasoner. The stripping procedure is:

1. Find all `swrl:BuiltinAtom` subjects
2. For each `swrl:Imp` whose `swrl:body` or `swrl:head` transitively (via `swrl:AtomList` `rdf:first`/`rdf:rest`) references a builtin atom: remove the entire `swrl:Imp` and all its constituent atoms/list-nodes
3. Prune unreferenced `swrl:Variable` and `swrl:Builtin` declarations

This is a **known limitation**: the consistency check operates on the TBox (class/property axioms) plus any SWRL rules that use only ClassAtom/DatavaluedPropertyAtom/IndividualPropertyAtom. Rules using builtins are excluded from the reasoning input. The canonical Turtle export files retain the full mapping (including builtins); only the reasoner input is filtered.

---

## Consistency & Propagation

### Schema Change Propagation

This mapping specification is coupled to the Neo4j graph schema (defined in `cypher_template.txt`, `training/dataset_schema.json`, and `spec/DATABASE.md`). Any change to:

- Node labels or key properties
- Relationship types or their properties (`order`, `pos`)
- The set of recognized `Atom.type` values
- Builtin vocabulary (`Builtin.iri`)
- Graph-layer conventions (`graph` property values)

MUST trigger a review and update of this document. See `CLAUDE.md` for the full schema-change propagation checklist.

### Normative Downstream Consumption

This specification is the binding contract for Phase 821's `ontology_export.py`. That translator must:

1. Implement every mapping row in the [Metagraph -> SWRL RDF](#metagraph-to-swrl-rdf-mapping) and [OntoGraph -> OWL](#ontograph-to-owl-mapping) tables
2. Use label-scoped Cypher queries per [Export Scoping](#export-scoping)
3. Encode edge properties per [Edge-Property Reification](#edge-property-reification)
4. Mint IRIs per the [IRI Minting Strategy](#iri-minting-strategy)
5. Include `owl:AllDifferent` when named individuals are present
6. Strip `swrl:BuiltinAtom` rules from reasoner input per the [Builtin exclusion](#swrl-builtin-exclusion-from-reasoner-input) note

The spike export scripts at `.planning/phases/820-reasoning-stack-architecture-decision-ontograph-axiom-scopin/spike/export.py` demonstrate the label-scoped Cypher pattern and the SWRL RDF mapping mechanics. Phase 821's implementation builds clean against this spec, not by porting the spike code.
