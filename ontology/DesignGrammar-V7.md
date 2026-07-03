# Design Grammar System — Ontology Reference

**Version:** 7.0  
**Source:** `[DesignGrammar-V7.owl](DesignGrammar-V7.owl)`  
**Format:** Human-readable export for NotebookLM ingestion (mind maps, audio overviews, Q&A).  

> This document is a one-to-one rendering of the OWL ontology in plain markdown. Every class, property, enum, axiom, and example instance is listed with its label, comment, parent classes/properties, OWL characteristics, domain, range, and disjointness relations. Use the source OWL file for any reasoner-bound work; use this document for human review and AI ingestion.

## Ontology overview

> System-level ontology for the Design Grammar System (DG).
> Defines the common classes that control data flow in the DG Grasshopper
> plugin and Neo4j database. Domain-specific classes (Building, UrbanBlock, etc.)
> are dynamically generated from user prompts via the Grammar Viewer and are NOT
> part of this ontology.
> Graph layers:
> 1. Ontograph — dynamically generated domain classes and properties (not defined here)
> 2. Metagraph — SWRL rule structure (Rule, Atom, Variable, Literal, Builtin)
> 3. Validgraph — validation runs, entity results, integration config
> 4. SpecGraph — project specification notes and tags
> 5. Computgraph — DCM parametric design model (Algorithm, Procedure, Pattern, Parameter, Interface)
> Schema version: v7

## Contents

- [Graph layers](#graph-layers)
- [Classes by layer](#classes-by-layer)
- [Object properties by layer](#object-properties-by-layer)
- [Datatype properties by layer](#datatype-properties-by-layer)
- [Enumerated value classes (closed sets)](#enumerated-value-classes-closed-sets)
- [Disjointness axioms](#disjointness-axioms)
- [Example instances (ABox)](#example-instances-abox)
- [Namespace reference](#namespace-reference)

## Graph layers

The DG ontology partitions its content into a Core band plus five logical layers, each tagged with a `dg:graph` annotation on every class. All four layers persist into a single Neo4j database, isolated by the `dg:project` annotation.

| Prefix | Namespace | Layer | Role |
|---|---|---|---|
| `dg` | `http://example.org/design-grammar#` | Core (over-layer) + Ontograph | Gero FBS Object/Function/Behavior/Structure, Geometry, Topology, DesignState{ObjState,ParamState,PropState}, Session; and the reified OWL Class/DataProperty/ObjProperty meta-schema |
| `dgm` | `http://example.org/design-grammar/meta#` | Metagraph | SWRL rule structure: Rule, Atom subtypes, Variable subtypes, Literal, Builtin, RuleSet |
| `dgv` | `http://example.org/design-grammar/valid#` | Validgraph | Validation runs, entity results, integration config, Reasoner (= GH Validator) |
| `dgs` | `http://example.org/design-grammar/spec#` | SpecGraph | Project specification notes and tags (formerly KnowledgeGraph) |
| `dgc` | `http://example.org/design-grammar/comp#` | Computgraph | DCM parametric model: Algorithm, Procedure, Pattern, Parameter, Interface |

## Classes by layer

### Layer dg — 0. Core + Ontograph (over-layer entities + dynamic domain meta-schema)

#### `dg:Behavior` — Behavior

How the design achieves its function — the computational process. Described by an Algorithm (Grasshopper definition). Behavior produces Structure (geometric form). In DCM: Behavior IS the parametric definition that generates design output.

- **Parent class(es):** `dg:Core`

#### `dg:Class` — Class

A dynamically generated OWL class in the Ontograph layer. Created from user prompts (e.g. Building, UrbanBlock). Key property: iri. Aligned with: owl:Class (R7, subClassOf rather than equivalentClass — DG reifies the OWL meta-schema as Neo4j data, so dg:Class instances are also conceptually owl:Class instances, but using subClassOf keeps the meta-level reification clear).

- **Parent class(es):** `owl:Class`, `dg:Ontograph`

#### `dg:Core` — Core

Top-level grouping for the main Design Grammar entities considered over the layer structure: Object, Function, Behavior, Structure (Gero FBS), Geometry, Topology, DesignState (with ObjState/ParamState), and the shared Session. Core entities are referenced by the five graph layers but belong to none of them — they carry no dg:graph annotation (cross-cutting, like dg:LayerEntity). An Object has Function, Behavior, and Structure; its Function is covered by the Ontograph layer (dg:definesFunction), and its Design State is validated by the Metagraph layer (dgm:validates).


#### `dg:DataProperty` — DataProperty

A dynamically generated datatype property in the Ontograph layer. Represents measurable attributes (e.g. hasHeightM) and violation flags (e.g. violatesMaxHeight). Key property: iri. Aligned with: owl:DatatypeProperty (R7).

- **Parent class(es):** `owl:DatatypeProperty`, `dg:Ontograph`

#### `dg:DesignState` — DesignState

A snapshot of design parameters captured from Grasshopper. Every DesignState individual is necessarily one of ParamState, ObjState, or PropState (owl:disjointUnionOf below) — mutually exclusive, never more than one. ID prefixes: DS_ (ParamState), OS_ (ObjState), PS_ (PropState). Composed by DESIGN STATE and persisted in validation runs (v7.0: CLASSIFICATOR is eliminated; VALIDATOR binds directly from the composed DesignState). STORAGE NOTE: In the Neo4j layer (SCHM-01), this discrimination is materialized as a `kind` property with values "ParamState" | "ObjState" | "PropState" on a single :DesignState node label — a runtime convenience because Cypher does not infer subclass membership. The OWL ontology does not include the kind property because rdf:type plus disjointUnionOf already discriminate (v4.1).

- **Parent class(es):** `dg:Core`

#### `dg:Function` — Function

What the design object is supposed to achieve — its purpose or design intent. Rules enforce Functions. A Function is realized through Behavior (the computation that achieves it). Connected to Reasoner (as the mechanism evaluating design intent).

- **Parent class(es):** `dg:Core`

#### `dg:Geometry` — Geometry

Typed geometric data flowing through the parametric definition. Represents GH geometry types (Line, Point, Vector, Brep, Mesh, etc.). Connected to Structure as the physical form output. Distinct from dgv:ObjectInstance (which is a validated entity in Validgraph).

- **Parent class(es):** `dg:Core`

#### `dg:GraphLayer` — GraphLayer

A logical partition of the single Neo4j database. The Design Grammar System organizes all persisted nodes into exactly four layers (closed enumeration via owl:oneOf below, v4.1): Ontograph, Metagraph, Validgraph, SpecGraph. The four layer IRIs are punned per OWL 2 — each is both a class (parent of the layer's DG entities, under LayerEntity) and an individual (member of this GraphLayer enum). Every DG class carries a `dg:graph` annotation pointing at its layer.

- **Closed enum (owl:oneOf):** `dg:Ontograph`, `dgm:Metagraph`, `dgv:Validgraph`, `dgs:SpecGraph`, `dgc:Computgraph`

#### `dg:LayerEntity` — LayerEntity

Abstract root for DG entities that belong to one of the four graph layers. Direct subclasses are the four layer hubs: dg:Ontograph, dgm:Metagraph, dgv:Validgraph, dgs:SpecGraph. Each hub IRI is simultaneously a class (grouping its layer's DG entities) AND a NamedIndividual of dg:GraphLayer via OWL 2 punning (v3.4 unified structure). dg:LayerEntity itself is intentionally NOT tagged with a dg:graph annotation because it is cross-cutting — it is the parent of all four layer hubs, not a member of any single layer.


#### `dg:ObjProperty` — ObjProperty

A dynamically generated object property in the Ontograph layer. Represents relationships between domain classes (e.g. locatedIn). Key property: iri. Aligned with: owl:ObjectProperty (R7).

- **Parent class(es):** `owl:ObjectProperty`, `dg:Ontograph`

#### `dg:ObjState` — ObjState

Object state — associates an Object variable reference (from SWRL ClassAtom) with geometry elements. Created by the OBJECT STATE component by wiring ObjectRef + GeoRef. Composed into DESIGN STATE alongside ParamState to produce stable IdRefs. ID prefix: OS_. NEVER has an IdRef — carries its own stateId (OS_ prefix). Enforced via SubClassOf (hasIdRef max 0).

- **Parent class(es):** `dg:DesignState`
- **Restrictions:** dgv:hasIdRef max 0 of dgv:IdRef

#### `dg:Object` — Object

A design entity described through its Function, Behavior, and Structure (FBS framework). Represents a parametric design object whose behavior is defined by Grasshopper algorithms. Example: a Frame object whose algorithm generates a 2D truss. Bridges to dg:Class instances (a Building IS an Object in DCM terms).

- **Parent class(es):** `dg:Core`

#### `dg:Ontograph` — Ontograph

Hub class for the Ontograph layer (dynamic domain ontology meta-schema). Top-level subclasses: Class, DatatypeProperty, ObjectProperty.

- **Parent class(es):** `dg:LayerEntity`

#### `dg:ParamState` — ParamState

Definition state — a named set of Number/Integer/Boolean parameters captured from Grasshopper sliders and toggles. Represents the current parametric configuration. When ParamState changes, dependent IdRefs regenerate. ID prefix: DS_.

- **Parent class(es):** `dg:DesignState`

#### `dg:PropState` — PropState

Property state — the third DesignState kind (v7.0), composing a Rule's DataProperty result and its validated PropValue for a specific ObjectInstance. Built on the existing dgv:propValue / dgv:propValueOf datatype/object properties, which already attach per-instance validation-result values to ValidationEntity — PropState generalises that per-cell value into a first-class DesignState kind alongside ObjState and ParamState (ONTO-03, GHST-03). ID prefix: PS_.

- **Parent class(es):** `dg:DesignState`

#### `dg:Session` — Session

A unified interaction-log entity common to all layers (v6.0 — unifies the former Metagraph rule-session and Spec knowledge-session logs). Records an LLM-driven interaction (the user prompt and generated result); the sessionMode discriminates the operation (ingest/query/edit for rule sessions, insert/query/update for spec sessions). Aligned with: prov:Activity (see standards extension).

- **Parent class(es):** `dg:Core`

#### `dg:Structure` — Structure

What the design IS — its physical/geometric form resulting from Behavior. Connects to Geometry (data) and Topology (spatial decomposition). Represents the output of parametric computation.

- **Parent class(es):** `dg:Core`

#### `dg:Topology` — Topology

Spatial topology of geometric structure — decomposition via Topologic library (Cluster, CellComplex, Cell, Shell, Face, Wire, Edge, Vertex). Used for spatial analysis of design output. Alignment with external Topologic vocabulary defined in DesignGrammar-Topologic-extension.owl.

- **Parent class(es):** `dg:Core`

### Layer dgm — 2. Metagraph (SWRL rule structure)

#### `dgm:Atom` — Atom

An individual SWRL atom — a single predicate assertion within a rule. Types: ClassAtom, DataPropertyAtom, ObjectPropertyAtom, BuiltinAtom. Key property: Atom_Id.

- **Parent class(es):** `dgm:Metagraph`

#### `dgm:Builtin` — Builtin

A SWRL builtin comparison or arithmetic operator. Referenced by BuiltinAtom via REFERS_TO. Key property: iri (swrlb: prefix).

- **Parent class(es):** `dgm:Metagraph`

#### `dgm:BuiltinAtom` — BuiltinAtom

An atom invoking a SWRL builtin comparison operator (e.g. swrlb:greaterThan(?h, 75)). Takes two arguments for comparison.

- **Parent class(es):** `dgm:Atom`

#### `dgm:BuiltinVariable` — BuiltinVariable

A variable bound only inside BuiltinAtom arguments (e.g. an arithmetic intermediate). Not surfaced on the Grasshopper canvas — the VariableTypeInferrer recognizes this category to keep RULE DECONSTRUCT outputs clean (VTYP-01 priority chain step 3).

- **Parent class(es):** `dgm:Variable`

#### `dgm:ClassAtom` — ClassAtom

An atom asserting class membership (e.g. Building(?b)). Takes one variable argument at pos 1.

- **Parent class(es):** `dgm:Atom`

#### `dgm:DataPropertyAtom` — DataPropertyAtom

An atom asserting a datatype property value (e.g. hasHeightM(?b, ?h)). Takes two arguments: entity variable (pos 1) and value variable/literal (pos 2).

- **Parent class(es):** `dgm:Atom`

#### `dgm:Literal` — Literal

A constant value used as an atom argument (e.g. 75, true). Key properties: lex (lexical form) + datatype (xsd type).

- **Parent class(es):** `dgm:Metagraph`

#### `dgm:Metagraph` — Metagraph

Hub class for the Metagraph layer (SWRL rule structure). Top-level subclasses: Rule, Atom (with ClassAtom/DataPropertyAtom/ObjectPropertyAtom/BuiltinAtom children), Variable (with ObjectVariable/PropertyVariable/BuiltinVariable children), Literal, Builtin, RuleSet, VariableScopeValue. (Reasoner moved to Validgraph and sessions unified into Core in v6.0.)

- **Parent class(es):** `dg:LayerEntity`

#### `dgm:ObjectPropertyAtom` — ObjectPropertyAtom

An atom asserting an object property relationship (e.g. locatedIn(?b, ?block)). Takes two variable arguments.

- **Parent class(es):** `dgm:Atom`

#### `dgm:ObjectVariable` — ObjectVariable

A variable representing a domain entity instance (e.g. ?b for Building). Inferred from ClassAtom arguments (VTYP-01). Object variables are cross-rule scoped: the same variable name maps to the same entity across all rules in a project (VTYP-02). Can be wired to OBJECT STATE component to create ObjState (CMPST-01). The cross-rule scope is inferred by reasoner via the SubClassOf restriction below (v4.1).

- **Parent class(es):** `dgm:Variable`

#### `dgm:PropertyVariable` — PropertyVariable

A variable representing a datatype property value (e.g. ?h for height). Inferred from DataPropertyAtom arg-2 position (VTYP-01). Property variables are rule-scoped: the same name in different rules represents independent variables (VTYP-03). The rule-local scope is inferred by reasoner via the SubClassOf restriction below (v4.1).

- **Parent class(es):** `dgm:Variable`

#### `dgm:Rule` — Rule

A design grammar rule expressed as a SWRL implication. Contains body atoms (conditions) and head atoms (conclusions). Key property: Rule_Id. Format: R_<DOMAIN>_<PROPERTY>_<LIMIT>_V

- **Parent class(es):** `dgm:Metagraph`

#### `dgm:RuleSet` — RuleSet

A named collection of design grammar rules applied together as a regulatory package (e.g. "BuildingCode2024"). A RuleSet is NOT a sequence — rules within it have no precedence order. Rules can only host each other (nesting). Contains Rules via dgm:hasRule. Linked to a Reasoner via dgm:usesReasoner.

- **Parent class(es):** `dgm:Metagraph`

#### `dgm:Variable` — Variable

A SWRL variable (e.g. ?b, ?h). Key property: name (prefixed with '?'). Every Variable individual is necessarily an ObjectVariable, PropertyVariable, OR BuiltinVariable (owl:disjointUnionOf below — VTYP-01 priority chain). MERGE key includes project to prevent cross-project collision (SCHM-02). STORAGE NOTE: In the Neo4j layer, variable kind is inferred at read time by VariableTypeInferrer.Infer() — not stored on the Var node. The OWL ontology uses rdf:type plus disjointUnionOf to discriminate; no separate kind property exists (v4.1).

- **Parent class(es):** `dgm:Metagraph`

#### `dgm:VariableScopeValue` — VariableScope

Enumeration of variable scoping semantics derived from VariableKind. SCHM-06: enum class mirroring DesignStateParameterTypeValue pattern. Closed via owl:oneOf.

- **Parent class(es):** `dgm:Metagraph`
- **Closed enum (owl:oneOf):** `dgm:VariableScope_CrossRule`, `dgm:VariableScope_RuleLocal`

### Layer dgv — 3. Validgraph (validation runs, integration, Reasoner)

#### `dgv:DesignStateParameter` — DesignStateParameter

A single measurable parameter within a ParamState snapshot. Has a parameterId, displayName, type (Number/Integer/Boolean), and the corresponding typed value.

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:DesignStateParameterTypeValue` — DesignStateParameterType

Enumeration of supported parameter value types for DesignState snapshots. Corresponds to C# enum DG.Core.Models.DesignStateParameterType. Closed via owl:oneOf.

- **Parent class(es):** `dgv:Validgraph`
- **Closed enum (owl:oneOf):** `dgv:ParameterType_Number`, `dgv:ParameterType_Integer`, `dgv:ParameterType_Boolean`

#### `dgv:GeoRef` — GeoRef

Geometry reference — a handle to a geometry primitive in the source model (an external source-system object handle) wired into the OBJECT STATE component (CMPST-01, CTRCT-09). One ObjState may reference multiple GeoRefs (the geometry elements that compose the ObjectInstance). Aligned with: geo:Geometry (R6) — note that DG stores a source-system handle (geoRefId) rather than serialized geometry (geo:asWKT).

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:IdRef` — IdRef

Auto-generated DesignState identifier (CMPST-08). IdRef = DesignState ID — NOT ObjState ID. Regenerates whenever ParamState changes (CMPST-05). Persisted in statePayloadJson for cross-run object identity tracking (INTG-03). Resolves to one or more ObjectInstance(s). ID prefix: IDR_.

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:IntegrationConfig` — IntegrationConfig

Configuration node linking a DG project to its external geometry/viewer integration. Stores the external project ID, base model, and validation model references. One per project per provider.

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:ObjectInstance` — ObjectInstance

Cross-rule identity of a validated geometric element (CMPST-06). The noun — the actual thing in the model that gets validated. Stable across geometry edits. Each ObjectInstance has exactly one ObjState (its current binding snapshot). ID prefix: OI_. Both ObjectInstance and ObjState live above rule scope. Aligned with: sosa:FeatureOfInterest (R3) and geo:Feature (R6).

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:ReStatusValue` — ReStatus

Outcome status for a single parameter during design state reinstatement. Corresponds to C# enum DG.Core.Models.ReStatus. Used by the REINSTATE component to report per-parameter results. Closed via owl:oneOf.

- **Parent class(es):** `dgv:Validgraph`
- **Closed enum (owl:oneOf):** `dgv:ReStatus_Applied`, `dgv:ReStatus_MissingTarget`, `dgv:ReStatus_TypeMismatch`, `dgv:ReStatus_AmbiguousTarget`, `dgv:ReStatus_OutOfRange`, `dgv:ReStatus_Unchanged`, `dgv:ReStatus_WouldApply`

#### `dgv:Reasoner` — Reasoner

An evaluation engine concept representing the strategy used to apply rules to design state. Different reasoners may process rules differently (SWRL forward-chaining, Grasshopper constraint solver, parametric propagation). Linked from RuleSet (dgm:usesReasoner) and from Core Function (dg:evaluatedBy, as the mechanism that evaluates design intent). Corresponds to the Grasshopper "Validator" add-in component. Reconsidered as part of the Validgraph layer in v6.0.

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:Run` — Run

A single execution of rule evaluation against design state. Records which rules were evaluated, the external model version created, and entity-level pass/fail results. Created by the DG Grasshopper plugin's validation workflow. Aligned with: prov:Activity (R2) and sh:ValidationReport (R4).

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:ValidationEntity` — ValidationEntity

A BIM entity evaluated in a validation run. Records the entity's DG ID, display name, and overall pass/fail status for the specific run and rule. Aligned with: prov:Entity (R2), sosa:Observation (R3), and sh:ValidationResult (R4) — the cell (Run × Rule × ObjectInstance) is simultaneously a provenance entity, an observation of a property on a feature, and a validation result.

- **Parent class(es):** `dgv:Validgraph`

#### `dgv:ValidationStatusValue` — ValidationStatus

Status values for validation runs and entity results. Closed via owl:oneOf — value space is fixed at Completed, Passed, Failed.

- **Parent class(es):** `dgv:Validgraph`
- **Closed enum (owl:oneOf):** `dgv:Status_Completed`, `dgv:Status_Passed`, `dgv:Status_Failed`

#### `dgv:Validgraph` — Validgraph

Hub class for the Validgraph layer (validation runs, design state, integration config). Top-level subclasses: Run, ValidationEntity, Reasoner, DesignStateParameter, IntegrationConfig, ObjectInstance, GeoRef, IdRef, and three enum value classes (DesignStateParameterTypeValue, ValidationStatusValue, ReStatusValue). (The design-state classes moved to Core in v6.0.)

- **Parent class(es):** `dg:LayerEntity`

### Layer dgs — 4. SpecGraph (project specification notes, tags)

#### `dgs:SpecClass` — SpecClass

Parent hub node connecting all instances of a knowledge type. Acts as a type discriminator (e.g. SpecNote, Session).

- **Parent class(es):** `dgs:SpecGraph`

#### `dgs:SpecGraph` — SpecGraph

Hub class for the SpecGraph layer (project specification notes and tags). Top-level subclasses: SpecClass, SpecNote, SpecTag. (Renamed in v6.0; sessions unified into Core.)

- **Parent class(es):** `dg:LayerEntity`

#### `dgs:SpecNote` — SpecNote

A project knowledge entry (from folder ingest or NL prompt). Contains title, content, tags, and source reference.

- **Parent class(es):** `dgs:SpecGraph`

#### `dgs:SpecTag` — SpecTag

A tag label shared across knowledge notes for categorization. Aligned with: skos:Concept (R5) — a Tag IS a concept in a project's tag taxonomy.

- **Parent class(es):** `dgs:SpecGraph`

### Layer dgc — 5. Computgraph (DCM parametric design model)

#### `dgc:Algorithm` — Algorithm

A complete parametric definition — the top-level container for the computational process. Maps to a Grasshopper definition file (the whole canvas). Contains Procedures. Example: '1_Algorithm' generating a Frame object.

- **Parent class(es):** `dgc:Computgraph`

#### `dgc:Computgraph` — Computgraph

Hub class for the Computgraph layer (DCM parametric design model). Contains: Algorithm, Procedure, Pattern, Parameter, Interface. (FBS Object/Function/Behavior/Structure, Geometry and Topology moved to Core; ParametricState dropped; in v6.0.) Conceptual layer for future Grasshopper integration — enables translation of design grammars into/from parametric definitions.

- **Parent class(es):** `dg:LayerEntity`

#### `dgc:ConstantParam` — ConstantParam

A fixed configuration value — preset and not intended for user adjustment. Example: '11_Const_ptZero' (origin point), '11_Const_TrussConfig' (Truss Web Configuration).

- **Parent class(es):** `dgc:Parameter`

#### `dgc:EmergentParam` — EmergentParam

A computed output value — emerges from Pattern execution. Not directly set by user; derived from computation. Example: '11_Emg_LineSDL' (computed line), '12_Emg_FooterFrame' (generated frame geometry).

- **Parent class(es):** `dgc:Parameter`

#### `dgc:Input` — Input

An input port on an Interface — receives data into a Procedure or Pattern.

- **Parent class(es):** `dgc:Interface`

#### `dgc:Interface` — Interface

An inter-procedure connector — exposes data between Procedures. Maps to Grasshopper connection points at procedure boundaries. Has InterfaceType (Input/Output) and optional ListStructure for data tree management. Example: '11_IntF_ParSplitAt', '11_IntF_MergeRes'. Every Interface is necessarily an Input OR an Output (owl:disjointUnionOf).

- **Parent class(es):** `dgc:Computgraph`

#### `dgc:ListStructureValue` — ListStructure

Enumeration of Grasshopper data tree management operations applicable to Interfaces. Closed via owl:oneOf.

- **Parent class(es):** `dgc:Computgraph`
- **Closed enum (owl:oneOf):** `dgc:ListStructure_Flatten`, `dgc:ListStructure_Graft`, `dgc:ListStructure_Simplify`, `dgc:ListStructure_Reverse`

#### `dgc:Output` — Output

An output port on an Interface — emits data from a Procedure or Pattern.

- **Parent class(es):** `dgc:Interface`

#### `dgc:ParamDataTypeValue` — ParamDataType

Enumeration of parameter data types in the computation graph. Maps to Grasshopper data types. Closed via owl:oneOf.

- **Parent class(es):** `dgc:Computgraph`
- **Closed enum (owl:oneOf):** `dgc:ParamDataType_Float`, `dgc:ParamDataType_Integer`, `dgc:ParamDataType_Text`, `dgc:ParamDataType_Boolean`, `dgc:ParamDataType_Geometry`

#### `dgc:Parameter` — Parameter

A typed value in a parametric definition — data flowing through the computation graph. Distinct from dgm:Variable (which is a SWRL runtime binding): Parameter is a GH definition-time concept. Has ParameterType (Var/Const/Emergent) and ParamDataType. Bridge: Atoms can reference Parameters via dgc:attributeOf. Every Parameter is necessarily a VariableParam, ConstantParam, OR EmergentParam (owl:disjointUnionOf).

- **Parent class(es):** `dgc:Computgraph`

#### `dgc:Pattern` — Pattern

The atomic unit of parametric computation — a single operation node. Maps to a Grasshopper Component (a node on the canvas). Has Interfaces (I/O ports) and receives Parameters. Patterns can host other Patterns (nesting). Example: '11_Pat_DivideLine', '11_Pat_TopChord', '12_Pat_1 - Create footer bottom lines'.

- **Parent class(es):** `dgc:Computgraph`

#### `dgc:Procedure` — Procedure

A grouped sequence of Patterns within an Algorithm — an organizational unit of computation. Maps to a Grasshopper Cluster or Group. Contains Patterns and exposes Interfaces for inter-procedure data flow. Example: '11_Proc - 2D Truss Configuration', '12_Proc - 2D Footer Configuration'.

- **Parent class(es):** `dgc:Computgraph`

#### `dgc:VariableParam` — VariableParam

A user-adjustable input parameter (GH slider, number input, toggle). Value can be changed by the user at design time. Example: '11_Var_SpansCount' (Count of spans), '12_Var_HFooter' (Footer Height).

- **Parent class(es):** `dgc:Parameter`

## Object properties by layer

### Layer dg — 0. Core + Ontograph (over-layer entities + dynamic domain meta-schema)

#### `dg:definesFunction` — DEFINES_FUNCTION

Connects an Ontograph entity (Class, ObjProperty, or DataProperty) to the Core Function it realises for an Object. The Ontograph layer defines, from NL input, what classes and properties exist and links them to the Function of a specific Object — so one Object may have many Functions, and a group of Objects may share some Functions while differing in others.

- **Domain:** `dg:Class ∪ dg:ObjProperty ∪ dg:DataProperty`
- **Range:** `dg:Function`

#### `dg:evaluatedBy` — EVALUATED_BY

Connects a Function to the Reasoner that evaluates design rules against it. Links design intent (Function) to rule evaluation strategy (Reasoner).

- **Domain:** `dg:Function`
- **Range:** `dgv:Reasoner`

#### `dg:hasBehavior` — HAS_BEHAVIOR

Connects an Object to its Behavior (computational process achieving the function).

- **Domain:** `dg:Object`
- **Range:** `dg:Behavior`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dg:hasFunction` — HAS_FUNCTION

Connects an Object to its Function (design intent). An Object may have multiple Functions.

- **Domain:** `dg:Object`
- **Range:** `dg:Function`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dg:hasGeometry` — HAS_GEOMETRY

Connects a Structure to its Geometry data (the physical form representation).

- **Domain:** `dg:Structure`
- **Range:** `dg:Geometry`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dg:hasPart` — HAS_PART

Generic composition (part-whole) relation. Transitive super-property of the ERD containment hierarchy: Object hasPart {Function, Behavior, Structure}; Structure hasPart {Geometry, Topology}; RuleSet hasPart Rule; Algorithm hasPart Procedure; Procedure hasPart Pattern; Pattern hasPart {Parameter, Interface}. Transitivity yields the full decomposition, e.g. Object hasPart Geometry and Algorithm hasPart Parameter. Inverse: dg:partOf. Not used in cardinality restrictions (kept simple-property-safe for OWL 2 DL).

- **Domain:** `—`
- **Range:** `—`
- **Characteristics:** Transitive

#### `dg:hasStructure` — HAS_STRUCTURE

Connects an Object to its Structure (physical/geometric form).

- **Domain:** `dg:Object`
- **Range:** `dg:Structure`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dg:hasTopology` — HAS_TOPOLOGY

Connects a Structure to its Topology (spatial decomposition via Topologic).

- **Domain:** `dg:Structure`
- **Range:** `dg:Topology`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dg:objectRef` — OBJECT_REF

Connects an ObjState to the Core Object it instantiates (the ERD 'ObjectRef' edge). The ObjState binds geometry to a specific design Object whose Function/Behavior/Structure are defined across the layers. (The string handle for the SWRL Object-variable name is dgv:objectRefName.)

- **Domain:** `dg:ObjState`
- **Range:** `dg:Object`

#### `dg:partOf` — PART_OF

Inverse of dg:hasPart — a component is part of its container. Transitive.

- **Domain:** `—`
- **Range:** `—`
- **Characteristics:** Transitive
- **Inverse of:** `dg:hasPart`

### Layer dgm — 2. Metagraph (SWRL rule structure)

#### `dgm:hasArg` — ARG

Connects an Atom to its arguments (Variable or Literal). Property: pos (integer, 1-indexed position). Characteristics: none (Atoms have multiple args; same Variable may appear in multiple Atoms). Range: union of {Variable, Literal}.

- **Domain:** `dgm:Atom`
- **Range:** `dgm:Variable ∪ dgm:Literal`

#### `dgm:hasBody` — HAS_BODY

Connects a Rule to its body (condition) atoms. The body checks the condition that breaks the rule in violation mode. Property: order (integer, 1-indexed). Characteristics: InverseFunctional — each Atom belongs to exactly one Rule's body. Disjoint with hasHead: no Atom may simultaneously be a body and head atom of the same Rule. Equivalent to swrl:body.

- **Domain:** `dgm:Rule`
- **Range:** `dgm:Atom`
- **Characteristics:** InverseFunctional
- **Disjoint with (property):** `dgm:hasHead`

#### `dgm:hasHead` — HAS_HEAD

Connects a Rule to its head (conclusion) atoms. The head sets the violation flag to true when the body fires. Property: order (integer, 1-indexed). Characteristics: InverseFunctional — each Atom belongs to exactly one Rule's head. Disjoint with hasBody (declared on hasBody side). Equivalent to swrl:head.

- **Domain:** `dgm:Rule`
- **Range:** `dgm:Atom`
- **Characteristics:** InverseFunctional

#### `dgm:hasRule` — HAS_RULE

Connects a RuleSet to the Rules it contains. A RuleSet groups multiple Rules as a regulatory package.

- **Domain:** `dgm:RuleSet`
- **Range:** `dgm:Rule`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dgm:refersTo` — REFERS_TO

Connects an Atom to the ontology entity it references (Class, DataProperty, ObjProperty, or Builtin). Each Atom has exactly one REFERS_TO. Characteristics: Functional. Range: union of {Class, DataProperty, ObjProperty, Builtin}.

- **Domain:** `dgm:Atom`
- **Range:** `dg:Class ∪ dg:DataProperty ∪ dg:ObjProperty ∪ dgm:Builtin`
- **Characteristics:** Functional

#### `dgm:usesReasoner` — USES_REASONER

Connects a RuleSet to the Reasoner used to evaluate its rules. Characteristics: Functional — a RuleSet uses exactly one Reasoner.

- **Domain:** `dgm:RuleSet`
- **Range:** `dgv:Reasoner`
- **Characteristics:** Functional

#### `dgm:validates` — VALIDATES

Connects a Metagraph Rule to the Core DesignState (the ERD 'STATE') it validates. The Ontograph-defined classes and properties referenced by the rule's atoms are evaluated against the captured Design State.

- **Domain:** `dgm:Rule`
- **Range:** `dg:DesignState`

#### `dgm:variableScope` — variableScope

Scoping semantics (enum-valued): VariableScope_CrossRule for Object variables (shared identity across rules in a project, VTYP-02) or VariableScope_RuleLocal for Property variables (independent per rule, VTYP-03). Derived from variableKind. Characteristics: Functional.

- **Domain:** `dgm:Variable`
- **Range:** `dgm:VariableScopeValue`
- **Characteristics:** Functional

### Layer dgv — 3. Validgraph (validation runs, integration, Reasoner)

#### `dgv:hasEntity` — HAS_ENTITY

Connects a Run to its evaluated ValidationEntity results. Characteristics: InverseFunctional — each ValidationEntity belongs to exactly one Run. Aligned with: prov:generated (R2) — a ValidationEntity is generated by the run.

- **Domain:** `dgv:Run`
- **Range:** `dgv:ValidationEntity`
- **Characteristics:** InverseFunctional

#### `dgv:hasGeoRef` — HAS_GEO_REF

Connects an ObjState to its geometry handles wired into the GeoRef input of OBJECT STATE (CTRCT-09). One ObjState may have many GeoRefs (the geometry elements composing the ObjectInstance). Characteristics: InverseFunctional — each GeoRef belongs to exactly one ObjState. Aligned with: geo:hasGeometry (R6) — the GeoSPARQL pattern for object↔geometry linking.

- **Domain:** `dg:ObjState`
- **Range:** `dgv:GeoRef`
- **Characteristics:** InverseFunctional

#### `dgv:hasIdRef` — HAS_ID_REF

Connects a ParamState to its auto-generated IdRef. Characteristics: Functional + InverseFunctional — IdRef IS the ParamState-generated DesignState ID, so strict 1:1 cardinality (CMPST-08). Domain restricted to ParamState (NOT all DesignState): per CMPST-05, only ParamState triggers IdRef regeneration. ObjState carries its own stateId (OS_ prefix) and never has an IdRef — see the ObjState SubClassOf (hasIdRef max 0) restriction below.

- **Domain:** `dg:ParamState`
- **Range:** `dgv:IdRef`
- **Characteristics:** Functional, InverseFunctional

#### `dgv:hasObjState` — HAS_OBJECT_STATE

Connects an ObjectInstance to its current ObjState (the geometry + variable binding snapshot). Characteristics: Functional + InverseFunctional — strict 1:1 cardinality per CMPST-06. Inverse of representsInstance.

- **Domain:** `dgv:ObjectInstance`
- **Range:** `dg:ObjState`
- **Characteristics:** Functional, InverseFunctional
- **Inverse of:** `dgv:representsInstance`

#### `dgv:hasObjectVariable` — HAS_OBJECT_VARIABLE

Connects an ObjState to the SWRL Object Variable wired into the ObjectRef input of OBJECT STATE (CTRCT-08). The ObjectVariable is cross-rule (VTYP-02) — same variable name identifies the same ObjectInstance across all rules in a project. Characteristics: Functional — one canonical variable per ObjState.

- **Domain:** `dg:ObjState`
- **Range:** `dgm:ObjectVariable`
- **Characteristics:** Functional

#### `dgv:hasParameter` — HAS_PARAMETER

Connects a DesignState snapshot to its individual parameters. Characteristics: InverseFunctional — each DesignStateParameter belongs to exactly one DesignState.

- **Domain:** `dg:DesignState`
- **Range:** `dgv:DesignStateParameter`
- **Characteristics:** InverseFunctional

#### `dgv:parameterType` — parameterType

Type discriminator for parameter value (enum-valued): ParameterType_Number, ParameterType_Integer, or ParameterType_Boolean. Characteristics: Functional.

- **Domain:** `dgv:DesignStateParameter`
- **Range:** `dgv:DesignStateParameterTypeValue`
- **Characteristics:** Functional

#### `dgv:propValueOf` — PROP_VALUE_OF

Connects a ValidationEntity to the PropertyVariable whose value the rule checked (SCHM-05). The "main attribute being validated" — determines which property's value is shown in the Model Viewer's passing/failing list. Characteristics: Functional — one main property per ValidationEntity cell. Aligned with: sosa:observedProperty (R3, equivalent) and sh:resultPath (R4, subProperty).

- **Domain:** `dgv:ValidationEntity`
- **Range:** `dgm:PropertyVariable`
- **Characteristics:** Functional

#### `dgv:refersToGeometry` — REFERS_TO_GEOMETRY

Connects a GeoRef to the Core Geometry it points at. Completes the ERD chain ObjState -hasGeoRef-> GeoRef -refersToGeometry-> Geometry, i.e. Geometry is linked to ObjState through the GeoRef handle. Geometry is part of Structure (Structure -hasGeometry-> Geometry).

- **Domain:** `dgv:GeoRef`
- **Range:** `dg:Geometry`

#### `dgv:representsInstance` — REPRESENTS_INSTANCE

Connects an ObjState back to the ObjectInstance it captures. Characteristics: Functional + InverseFunctional — strict 1:1 cardinality. Inverse of hasObjState.

- **Domain:** `dg:ObjState`
- **Range:** `dgv:ObjectInstance`
- **Characteristics:** Functional, InverseFunctional

#### `dgv:resolvesTo` — RESOLVES_TO

Connects an IdRef to the ObjectInstance(s) it tracks across runs (INTG-03). Characteristics: none — an IdRef may resolve to many ObjectInstances (the run's full object set), and an ObjectInstance is referenced by many IdRefs over time (one per ParamState configuration).

- **Domain:** `dgv:IdRef`
- **Range:** `dgv:ObjectInstance`

#### `dgv:status` — status

Status of a validation run (Status_Completed) or entity result (Status_Passed / Status_Failed). Domain union: Run ∪ ValidationEntity. Characteristics: Functional.

- **Domain:** `dgv:Run ∪ dgv:ValidationEntity`
- **Range:** `dgv:ValidationStatusValue`
- **Characteristics:** Functional

#### `dgv:validatesInstance` — VALIDATES_INSTANCE

Connects a ValidationEntity result cell to the ObjectInstance it describes. Characteristics: Functional — each ValidationEntity describes exactly one ObjectInstance. Inverse direction is NOT functional: an ObjectInstance has many ValidationEntities (one per rule per run). Aligned with: sosa:hasFeatureOfInterest (R3, equivalent) and sh:focusNode (R4, subProperty). The SOSA mapping is the stronger semantic match; SHACL is a sibling subPropertyOf to avoid asserting transitive equivalence between sosa:hasFeatureOfInterest and sh:focusNode.

- **Domain:** `dgv:ValidationEntity`
- **Range:** `dgv:ObjectInstance`
- **Characteristics:** Functional

### Layer dgs — 4. SpecGraph (project specification notes, tags)

#### `dgs:instanceOf` — INSTANCE_OF

Connects a SpecNote or Session to its parent SpecClass hub node. Characteristics: Functional — each Note/Session has exactly one parent hub.

- **Domain:** `—`
- **Range:** `dgs:SpecClass`
- **Characteristics:** Functional

#### `dgs:taggedWith` — TAGGED_WITH

Connects a SpecNote to its SpecTag nodes. Characteristics: none (many-to-many — a Note has multiple Tags, a Tag is reused across Notes).

- **Domain:** `dgs:SpecNote`
- **Range:** `dgs:SpecTag`

### Layer dgc — 5. Computgraph (DCM parametric design model)

#### `dgc:attributeOf` — ATTRIBUTE_OF

Cross-layer bridge connecting a Metagraph Atom to a Computgraph Parameter. This is the semantic link enabling bidirectional translation between SWRL rules and Grasshopper parametric definitions: a rule atom can reference a parametric parameter. Follows the same cross-layer pattern as dgm:refersTo (Metagraph → Ontograph).

- **Domain:** `dgm:Atom`
- **Range:** `dgc:Parameter`

#### `dgc:hasAlgorithm` — HAS_ALGORITHM

Connects a Behavior to its Algorithm (the complete parametric definition describing it). Characteristics: Functional — one Behavior has one Algorithm.

- **Domain:** `dg:Behavior`
- **Range:** `dgc:Algorithm`
- **Characteristics:** Functional

#### `dgc:hasInterface` — HAS_INTERFACE

Connects a Pattern (or Procedure) to its Interface connector. Interfaces expose data at procedure boundaries.

- **Domain:** `dgc:Pattern ∪ dgc:Procedure`
- **Range:** `dgc:Interface`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dgc:hasParameter` — HAS_PARAMETER

Connects a Pattern to its Parameters (input values consumed by the component).

- **Domain:** `dgc:Pattern`
- **Range:** `dgc:Parameter`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dgc:hasPattern` — HAS_PATTERN

Connects a Procedure to its constituent Patterns. A Procedure contains multiple Patterns (GH components).

- **Domain:** `dgc:Procedure`
- **Range:** `dgc:Pattern`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dgc:hasProcedure` — HAS_PROCEDURE

Connects an Algorithm to its constituent Procedures. An Algorithm contains multiple Procedures.

- **Domain:** `dgc:Algorithm`
- **Range:** `dgc:Procedure`
- **Sub-property of:** `dg:hasPart`, `dg:hasPart`

#### `dgc:listStructure` — listStructure

Data tree management operation applied to an Interface (Flatten, Graft, Simplify, Reverse).

- **Domain:** `dgc:Interface`
- **Range:** `dgc:ListStructureValue`

#### `dgc:paramDataType` — paramDataType

Data type of a Parameter (Float, Integer, Text, Boolean, Geometry). Characteristics: Functional.

- **Domain:** `dgc:Parameter`
- **Range:** `dgc:ParamDataTypeValue`
- **Characteristics:** Functional

#### `dgc:paramLink` — PARAM_LINK

Connects a Parameter to the Interface it flows through. Models data wiring between Parameters and Interface connectors.

- **Domain:** `dgc:Parameter`
- **Range:** `dgc:Interface`

#### `dgc:patternHostTo` — PATTERN_HOST_TO

Nesting relationship — a Pattern can host (contain) other Patterns. Models GH component grouping within a procedure.

- **Domain:** `dgc:Pattern`
- **Range:** `dgc:Pattern`

## Datatype properties by layer

### Layer dg — 0. Core + Ontograph (over-layer entities + dynamic domain meta-schema)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dg:createdAt` | createdAt | `—` | `xsd:dateTime` | — | ISO 8601 UTC timestamp of node creation. Used across all graph layers. Aligned with: dcterms:created (R5/R7 — cross-cutting Dublin Core creation timestamp). |
| `dg:iri` | iri | `—` | `xsd:string` | — | IRI identifier for ontology entities. Format: ex:<Name> (e.g. ex:Building, ex:hasHeightM). Aligned with: dcterms:identifier (R7-adjacent) — the IRI IS the canonical identifier. |
| `dg:label` | label | `—` | `xsd:string` | — | Human-readable display label for Class and ObjectProperty nodes. Aligned with: rdfs:label (R7). |
| `dg:objectName` | name | `dg:Object` | `xsd:string` | Functional | Display name of a DCM Object (e.g. 'Frame', 'Truss'). Characteristics: Functional. |
| `dg:range` | range | `dg:DataProperty` | `xsd:string` | — | XSD datatype range for DatatypeProperty nodes (e.g. xsd:decimal, xsd:integer, xsd:boolean). |
| `dg:sessionId` | sessionId | `dg:Session` | `xsd:string` | Functional | Unique identifier for a Session (e.g. drs-<hex12> for rule sessions, ks-<hex12> for spec sessions). Characteristics: Functional. |
| `dg:sessionMode` | mode | `dg:Session` | `xsd:string` | — | Interaction mode of a Session: 'ingest' \| 'query' \| 'edit' (rule sessions) or 'insert' \| 'query' \| 'update' (spec sessions). |
| `dg:sessionPrompt` | prompt | `dg:Session` | `xsd:string` | — | The user's natural-language prompt that triggered this Session. |
| `dg:sessionResult` | result | `dg:Session` | `xsd:string` | — | The LLM-generated result of the Session (Cypher, answer text, or update summary). |

### Layer dgm — 2. Metagraph (SWRL rule structure)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dgm:RuleDescription` | RuleDescription | `dgm:Rule` | `xsd:string` | — | Natural-language description of a rule's intent — a longer explanation than RuleName's short title, distinct from SWRL's machine expression string. NEW in v7.0 (no V6 predecessor); matches the GH_DesignGrammars.pdf schema (DG.Layer.Metagraph.RuleDescription; Output=Rule().Description). Exposed by RULE DECONSTRUCT and VALIDATOR. |
| `dgm:RuleName` | RuleName | `dgm:Rule` | `xsd:string` | — | Optional human-readable title for a rule. v7.0 rename of the V6 rule-title property to match the GH_DesignGrammars.pdf schema (DG.Layer.Metagraph.RuleName). |
| `dgm:SWRL` | SWRL | `dgm:Rule` | `xsd:string` | — | The SWRL expression string for a rule (e.g. Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)). v7.0 rename of the V6 rule-text property to match the GH_DesignGrammars.pdf schema (DG.Layer.Metagraph.SWRL). |
| `dgm:atomId` | Atom_Id | `dgm:Atom` | `xsd:string` | Functional | Unique identifier for an atom. Body: {Rule_Id}_A{n}, Head: {Rule_Id}_H{n}. Characteristics: Functional. |
| `dgm:atomIri` | iri | `dgm:Atom` | `xsd:string` | — | IRI of the ontology entity referenced by this atom (e.g. ex:Building, swrlb:greaterThan). |
| `dgm:atomSwrlLabel` | SWRL_label | `dgm:Atom` | `xsd:string` | — | Display label for the atom in SWRL notation. |
| `dgm:atomType` | type | `dgm:Atom` | `xsd:string` | — | Atom type discriminator: ClassAtom, DataPropertyAtom, ObjectPropertyAtom, BuiltinAtom. |
| `dgm:builtinIri` | iri | `dgm:Builtin` | `xsd:anyURI` | Functional | IRI of the SWRL builtin (e.g. swrlb:greaterThan). Characteristics: Functional. |
| `dgm:builtinLabel` | label | `dgm:Builtin` | `xsd:string` | — | Display label for the builtin (e.g. greaterThan, lessThan). |
| `dgm:inferredDatatype` | inferredDatatype | `dgm:Variable` | `xsd:string` | — | XSD datatype inferred for this variable from SWRL atom context (e.g. xsd:decimal for a variable used in hasHeightM). Set by VariableTypeInferrer. |
| `dgm:literalDatatype` | datatype | `dgm:Literal` | `xsd:string` | — | XSD datatype of the literal (e.g. xsd:decimal, xsd:integer, xsd:boolean, xsd:string). |
| `dgm:literalLex` | lex | `dgm:Literal` | `xsd:string` | — | Lexical form of the literal value (e.g. "75", "true", "2.8"). |
| `dgm:order` | order | `—` | `xsd:integer` | — | Ordinal position of an atom within a rule's body or head (1-indexed). Stored on HAS_BODY and HAS_HEAD relationships. |
| `dgm:pos` | pos | `—` | `xsd:integer` | — | Positional index of an argument within an atom (1-indexed). Stored on ARG relationships. |
| `dgm:ruleId` | Rule_Id | `dgm:Rule` | `xsd:string` | Functional | Unique identifier for a rule. Format: R_<DOMAIN>_<PROPERTY>_<LIMIT>_V (e.g. R_URB_HEIGHT_MAX_75_V). Characteristics: Functional. |
| `dgm:ruleKind` | kind | `dgm:Rule` | `xsd:string` | — | Rule kind: 'violation' (body fires on constraint breach) or 'compliance' (body fires on constraint satisfaction). |
| `dgm:ruleSetName` | name | `dgm:RuleSet` | `xsd:string` | Functional | Display name of a RuleSet (e.g. 'BuildingCode2024', 'ZoningRegulation'). Characteristics: Functional. |
| `dgm:variableName` | name | `dgm:Variable` | `xsd:string` | Functional | Variable name prefixed with '?' (e.g. ?b, ?h, ?lu). Characteristics: Functional. |

### Layer dgv — 3. Validgraph (validation runs, integration, Reasoner)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dgv:SendStatus` | SendStatus | `dgv:Run` | `xsd:boolean` | Functional | NEW in v7.0 (no V6 predecessor). Single Boolean per Run: whether publishing this run's results to the external geometry/viewer platform succeeded (D-08). Orthogonal to ValidStatus — set true when the publish operation completes successfully, independent of the rule pass/fail outcome. Publishing is one operation per run, so SendStatus is not per-object. Characteristics: Functional. Matches the GH_DesignGrammars.pdf schema (DG.Layer.Validgraph.SendStatus; Output=Run().SendStatus Datatype: Boolean). |
| `dgv:ValidStatus` | ValidStatus | `dgv:Run` | `xsd:boolean` | — | NEW in v7.0 (no V6 predecessor). Boolean LIST per Run, one element per ObjState in the validated DesignState, index-matched to the DesignState's ObjState order (D-06). Each element is that object's pass/fail against the rule. Overall pass = AND(ValidStatus), derived at read time, never stored as a separate field (D-07) — unifies the PDF's VALIDATOR-port ValidStatus(Boolean) and VALIDATION GRAPH-port Status(text) naming split into this one field. Not declared FunctionalProperty (multiple values per Run form the list). Population semantics (which ObjStates the list covers) are Phase 18 scope (VALIDATOR variable binding), not locked here. Matches the GH_DesignGrammars.pdf schema (DG.Layer.Validgraph.ValidStatus). |
| `dgv:baseModelId` | baseModelId | `dgv:IntegrationConfig` | `xsd:string` | — | ID of the base geometry model in the external platform. Stored on the IntegrationConfig node. |
| `dgv:baseModelName` | baseModelName | `dgv:IntegrationConfig` | `xsd:string` | — | Display name of the base geometry model in the external platform. |
| `dgv:baseVersionId` | baseVersionId | `dgv:Run` | `xsd:string` | — | Version ID of the base model (in the external platform) used in this validation run. |
| `dgv:capturedAtUtc` | capturedAtUtc | `dg:DesignState ∪ dgv:Run` | `xsd:dateTime` | Functional | UTC timestamp when a design state or validation run was captured. Characteristics: Functional — one capture time per snapshot. Domain union: DesignState ∪ Run. Aligned with: prov:startedAtTime (R2) — semantically, the moment an activity started / a sample was captured. |
| `dgv:dgEntityId` | dgEntityId | `dgv:ValidationEntity` | `xsd:string` | Functional | Unique DG identifier for a BIM entity in a validation run. Characteristics: Functional. |
| `dgv:displayName` | displayName | `dgv:ValidationEntity` | `xsd:string` | — | Human-readable name for a validation entity. |
| `dgv:externalProjectId` | externalProjectId | `dgv:IntegrationConfig` | `xsd:string` | — | ID of the linked project in the external geometry/viewer platform. Stored on the IntegrationConfig node for the project. |
| `dgv:geoRefId` | geoRefId | `dgv:GeoRef` | `xsd:string` | Functional | Source-system handle for a geometry primitive (an external source-system object handle). The value wired into the GeoRef input of OBJECT STATE per CTRCT-09. Characteristics: Functional. |
| `dgv:idRefValue` | idRefValue | `dgv:IdRef` | `xsd:string` | Functional | The auto-regenerated identifier string produced by DESIGN STATE (CMPST-03, CMPST-05). Changes whenever ParamState changes. Note: IdRef is the DesignState's ID, NOT ObjState's ID — ObjState carries its own stateId (OS_ prefix). Characteristics: Functional. |
| `dgv:instanceId` | instanceId | `dgv:ObjectInstance` | `xsd:string` | Functional | Stable cross-rule identifier of an ObjectInstance. Format: OI_<hash>. Persists across geometry edits (CMPST-06). Characteristics: Functional. |
| `dgv:modelViewerUrl` | modelViewerUrl | `dgv:Run` | `xsd:string` | — | URL to view the validation results in the Model Viewer. |
| `dgv:objectRefName` | objectRef | `dg:ObjState` | `xsd:string` | — | Object variable reference string for an ObjState (e.g. the variable name from a ClassAtom). Links this ObjState to the SWRL Object variable it represents. |
| `dgv:parameterId` | parameterId | `dgv:DesignStateParameter` | `xsd:string` | Functional | Identifier of a design state parameter (maps to a DatatypeProperty iri in the Ontograph). Characteristics: Functional. |
| `dgv:propValue` | propValue | `dgv:ValidationEntity` | `xsd:string` | — | The validated property value for this ValidationEntity (SCHM-05). One value per (Run, Rule, ObjectInstance) cell — the "main attribute" the rule checked. Shown in the Model Viewer's passing/failing item list per rule. Lex form (xsd:string) for display; actual typed value lives on the DesignStateParameter. Aligned with: sosa:hasSimpleResult (R3) — the validated value IS the observation's simple result. |
| `dgv:provider` | provider | `dgv:IntegrationConfig` | `xsd:string` | — | Integration provider name identifying the external geometry/viewer platform. |
| `dgv:reasonerName` | name | `dgv:Reasoner` | `xsd:string` | Functional | Display name of a Reasoner (e.g. 'SWRLForwardChainer', 'GrasshopperSolver'). Characteristics: Functional. |
| `dgv:ruleId` | ruleId | `dgv:ValidationEntity` | `xsd:string` | Functional | Rule ID associated with a validation entity result. Characteristics: Functional — each ValidationEntity references exactly one rule. |
| `dgv:rulesJson` | rulesJson | `dgv:Run` | `xsd:string` | — | JSON-serialized array of rules evaluated in this run. |
| `dgv:runId` | runId | `dgv:Run` | `xsd:string` | Functional | Unique identifier for a validation run. Characteristics: Functional. |
| `dgv:stateId` | stateId | `dg:DesignState` | `xsd:string` | Functional | Unique identifier for a DesignState snapshot. Characteristics: Functional. |
| `dgv:statePayloadJson` | statePayloadJson | `dgv:Run` | `xsd:string` | — | JSON-serialized DesignState snapshot used as input to this run. |
| `dgv:validationModelId` | validationModelId | `dgv:IntegrationConfig` | `xsd:string` | — | ID of the validation overlay model in the external platform. Stored on the IntegrationConfig node. |
| `dgv:validationVersionId` | validationVersionId | `dgv:Run` | `xsd:string` | — | Version ID of the validation overlay (in the external platform) created by this run. |

### Layer dgs — 4. SpecGraph (project specification notes, tags)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dgs:content` | content | `dgs:SpecNote` | `xsd:string` | — | Full text content of a knowledge note. Aligned with: skos:note (R5) — the SKOS pattern for the textual body of a concept-related artifact. |
| `dgs:createdAt` | createdAt | `—` | `xsd:dateTime` | — | ISO 8601 UTC timestamp of creation. Aligned with: dcterms:created (R5). |
| `dgs:noteId` | noteId | `dgs:SpecNote` | `xsd:string` | Functional | Unique identifier for a knowledge note. Characteristics: Functional. Aligned with: dcterms:identifier (R5). |
| `dgs:source` | source | `dgs:SpecNote` | `xsd:string` | — | Source file path or reference for a knowledge note (e.g. notes/site.md). Aligned with: dcterms:source (R5). |
| `dgs:tagName` | name | `dgs:SpecTag` | `xsd:string` | Functional | Tag name string (e.g. "zoning", "structural"). Characteristics: Functional — one canonical name per Tag. Aligned with: skos:prefLabel (R5) — the SKOS canonical label for a concept. |
| `dgs:tags` | tags | `dgs:SpecNote` | `xsd:string` | — | Array of tag names associated with a knowledge note (stored as Neo4j list property). |
| `dgs:title` | title | `dgs:SpecNote` | `xsd:string` | — | Title of a knowledge note. Aligned with: dcterms:title (R5). |
| `dgs:updatedAt` | updatedAt | `—` | `xsd:dateTime` | — | ISO 8601 UTC timestamp of last update. Aligned with: dcterms:modified (R5). |

### Layer dgc — 5. Computgraph (DCM parametric design model)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dgc:algorithmName` | name | `dgc:Algorithm` | `xsd:string` | Functional | Display name of an Algorithm (e.g. '1_Algorithm'). Characteristics: Functional. |
| `dgc:interfaceName` | name | `dgc:Interface` | `xsd:string` | Functional | Display name of an Interface (e.g. '11_IntF_ParSplitAt'). Characteristics: Functional. |
| `dgc:parameterDisplayName` | displayName | `dgc:Parameter` | `xsd:string` | — | Human-readable label for a Parameter (e.g. 'Count of spans', 'Footer Height'). |
| `dgc:parameterName` | name | `dgc:Parameter` | `xsd:string` | Functional | Display name of a Parameter (e.g. '11_Var_SpansCount', '11_Const_ptZero'). Characteristics: Functional. |
| `dgc:patternName` | name | `dgc:Pattern` | `xsd:string` | Functional | Display name of a Pattern (e.g. '11_Pat_DivideLine'). Characteristics: Functional. |
| `dgc:procedureName` | name | `dgc:Procedure` | `xsd:string` | Functional | Display name of a Procedure (e.g. '11_Proc - 2D Truss Configuration'). Characteristics: Functional. |
| `dgc:procedureOrder` | order | `dgc:Procedure` | `xsd:integer` | — | Ordinal position of a Procedure within its Algorithm (numeric prefix, e.g. 11, 12). |

## Enumerated value classes (closed sets)

Six enum classes are closed via `owl:oneOf` — their value space is fixed. Any individual asserted as a member that is not one of the listed individuals triggers an inconsistency.

### `dgm:VariableScopeValue` — VariableScope

Enumeration of variable scoping semantics derived from VariableKind. SCHM-06: enum class mirroring DesignStateParameterTypeValue pattern. Closed via owl:oneOf.

**Allowed values:**

- `dgm:VariableScope_CrossRule` — **cross-rule**: Shared identity across all rules in a project. Applies to Object variables (VTYP-02).
- `dgm:VariableScope_RuleLocal` — **rule-scoped**: Independent variable per rule. Applies to Property variables (VTYP-03).

### `dgv:DesignStateParameterTypeValue` — DesignStateParameterType

Enumeration of supported parameter value types for DesignState snapshots. Corresponds to C# enum DG.Core.Models.DesignStateParameterType. Closed via owl:oneOf.

**Allowed values:**

- `dgv:ParameterType_Number` — **Number**: Floating-point parameter value (double). From Number Sliders in Grasshopper.
- `dgv:ParameterType_Integer` — **Integer**: Integer parameter value (long). From Integer Sliders in Grasshopper.
- `dgv:ParameterType_Boolean` — **Boolean**: Boolean parameter value. From Boolean Toggles in Grasshopper.

### `dgv:ReStatusValue` — ReStatus

Outcome status for a single parameter during design state reinstatement. Corresponds to C# enum DG.Core.Models.ReStatus. Used by the REINSTATE component to report per-parameter results. Closed via owl:oneOf.

**Allowed values:**

- `dgv:ReStatus_Applied` — **Applied**: Parameter value was successfully applied to the target slider/toggle.
- `dgv:ReStatus_MissingTarget` — **MissingTarget**: No matching slider/toggle found on the canvas for this parameter.
- `dgv:ReStatus_TypeMismatch` — **TypeMismatch**: Target slider type does not match parameter type (e.g. Number param wired to Integer slider).
- `dgv:ReStatus_AmbiguousTarget` — **AmbiguousTarget**: Multiple matching sliders/toggles found — cannot determine which to reinstate.
- `dgv:ReStatus_OutOfRange` — **OutOfRange**: Parameter value exceeds the target slider's min/max range.
- `dgv:ReStatus_Unchanged` — **Unchanged**: Target slider already has the requested value — no change needed.
- `dgv:ReStatus_WouldApply` — **WouldApply**: Dry-run mode — parameter would be applied if reinstatement were executed.

### `dgv:ValidationStatusValue` — ValidationStatus

Status values for validation runs and entity results. Closed via owl:oneOf — value space is fixed at Completed, Passed, Failed.

**Allowed values:**

- `dgv:Status_Completed` — **completed**: Validation run finished successfully.
- `dgv:Status_Passed` — **passed**: Validation entity passed all rules — no violations detected.
- `dgv:Status_Failed` — **failed**: Validation entity failed one or more rules — violations detected.

### `dgc:ListStructureValue` — ListStructure

Enumeration of Grasshopper data tree management operations applicable to Interfaces. Closed via owl:oneOf.

**Allowed values:**

- `dgc:ListStructure_Flatten` — **Flatten**
- `dgc:ListStructure_Graft` — **Graft**
- `dgc:ListStructure_Simplify` — **Simplify**
- `dgc:ListStructure_Reverse` — **Reverse**

### `dgc:ParamDataTypeValue` — ParamDataType

Enumeration of parameter data types in the computation graph. Maps to Grasshopper data types. Closed via owl:oneOf.

**Allowed values:**

- `dgc:ParamDataType_Float` — **Float**
- `dgc:ParamDataType_Integer` — **Integer**
- `dgc:ParamDataType_Text` — **Text**
- `dgc:ParamDataType_Boolean` — **Boolean**
- `dgc:ParamDataType_Geometry` — **Geometry**

## Disjointness axioms

Each group below is `owl:AllDisjointClasses` — no individual may simultaneously belong to two classes in the same group.

1. `dg:ParamState`, `dg:ObjState`, `dg:PropState`
2. `dgv:ObjectInstance`, `dg:ObjState`, `dgv:IdRef`, `dgv:GeoRef`
3. `dgv:Run`, `dgv:ValidationEntity`, `dgv:Reasoner`, `dgv:DesignStateParameter`, `dgv:IntegrationConfig`, `dgv:ObjectInstance`, `dgv:GeoRef`, `dgv:IdRef`
4. `dgm:ClassAtom`, `dgm:DataPropertyAtom`, `dgm:ObjectPropertyAtom`, `dgm:BuiltinAtom`
5. `dgm:ObjectVariable`, `dgm:PropertyVariable`, `dgm:BuiltinVariable`
6. `dgm:Rule`, `dgm:Atom`, `dgm:Variable`, `dgm:Literal`, `dgm:Builtin`, `dgm:RuleSet`
7. `dg:Class`, `dg:DataProperty`, `dg:ObjProperty`
8. `dgs:SpecClass`, `dgs:SpecNote`, `dgs:SpecTag`
9. `dgm:VariableScopeValue`, `dgv:DesignStateParameterTypeValue`, `dgv:ValidationStatusValue`, `dgv:ReStatusValue`, `dgc:ParamDataTypeValue`, `dgc:ListStructureValue`
10. `dgc:Algorithm`, `dgc:Procedure`, `dgc:Pattern`, `dgc:Parameter`, `dgc:Interface`
11. `dgc:VariableParam`, `dgc:ConstantParam`, `dgc:EmergentParam`
12. `dgc:Input`, `dgc:Output`
13. `dg:Object`, `dg:Function`, `dg:Behavior`, `dg:Structure`, `dg:Geometry`, `dg:Topology`, `dg:DesignState`, `dg:Session`

## Example instances (ABox)

The ontology ships with a representative ABox of named individuals demonstrating each class and binding pattern. Listed below by layer.

### Layer dg — 0. Core + Ontograph (over-layer entities + dynamic domain meta-schema)

#### Type: `dg:Behavior` (1 individual)

- **`dg:Behavior_Frame`** — Frame Behavior
  - `dg:graph`: dgc:Computgraph
  - `dgc:hasAlgorithm`: dgc:Algorithm_1

#### Type: `dg:Class` (4 individuals)

- **`dg:Class_Building`** — Building
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:Building"
  - `dg:label`: "Building"
  - `dg:project`: "UrbanBlock"
- **`dg:Class_LivingUnit`** — LivingUnit
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:LivingUnit"
  - `dg:label`: "LivingUnit"
  - `dg:project`: "TestA"
- **`dg:Class_Street`** — Street
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:Street"
  - `dg:label`: "Street"
  - `dg:project`: "TestA"
- **`dg:Class_Unit`** — Unit
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:Unit"
  - `dg:label`: "Unit"
  - `dg:project`: "Test Project"

#### Type: `dg:DataProperty` (6 individuals)

- **`dg:DProp_hasHeightM`** — hasHeightM
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:hasHeightM"
  - `dg:project`: "UrbanBlock"
  - `dg:range`: "xsd:decimal"
- **`dg:DProp_hasWidthM`** — hasWidthM
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:hasWidthM"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:decimal"
- **`dg:DProp_hasWindowCount`** — hasWindowCount
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:hasWindowCount"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:integer"
- **`dg:DProp_violatesMaxHeight`** — violatesMaxHeight
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:violatesMaxHeight"
  - `dg:project`: "UrbanBlock"
  - `dg:range`: "xsd:boolean"
- **`dg:DProp_violatesMinWidth`** — violatesMinWidth
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:violatesMinWidth"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:boolean"
- **`dg:DProp_violatesMinWindowCount`** — violatesMinWindowCount
  - `dg:graph`: dg:Ontograph
  - `dg:iri`: "ex:violatesMinWindowCount"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:boolean"

#### Type: `dg:ObjState` (1 individual)

- **`dg:OS_b1_var_b`** — ObjState: OI_Building_b1 ↔ ?b
  - _Comment:_ Binding snapshot pairing OI_Building_b1 with Object variable ?b (var_b) and its current GeoRef set. State_Id computed as OS_<SHA256(projectId + objectInstanceId + variableName)> per CMPST-07.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:hasGeoRef`: dgv:GR_geom_1, dgv:GR_geom_2
  - `dgv:hasObjectVariable`: dgm:var_b
  - `dgv:objectRefName`: "obj-9f3e2a"
  - `dgv:representsInstance`: dgv:OI_Building_b1
  - `dgv:stateId`: "OS_a1b2c3d4"

#### Type: `dg:Object` (1 individual)

- **`dg:Object_Frame`** — Frame
  - `dg:graph`: dgc:Computgraph
  - `dg:hasBehavior`: dg:Behavior_Frame
  - `dg:hasStructure`: dg:Structure_Frame
  - `dg:objectName`: "Frame"

#### Type: `dg:ParamState` (1 individual)

- **`dg:DS_def_h25_w12`** — ParamState: height=25, width=12
  - _Comment:_ Parametric capture of a Building configuration. Changes in this ParamState regenerate the linked IdRef per CMPST-05.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:hasIdRef`: dgv:IDR_DS_def_h25_w12
  - `dgv:stateId`: "DS_def_h25_w12"

#### Type: `dg:Session` (9 individuals)

- **`dg:Session_ks_1d599d7a40a1`** — Update session
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "ks-1d599d7a40a1"
  - `dg:sessionMode`: "update"
- **`dg:Session_ks_mnoom0r3`** — Insert: Parking is 300 slots
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "ks-mnoom0r3"
  - `dg:sessionMode`: "insert"
- **`dg:Session_ks_mnoon96l`** — Insert: building has 3 staircases
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "ks-mnoon96l"
  - `dg:sessionMode`: "insert"
- **`dg:Session_ks_mnp1jw35`** — Insert: Address of the building is Portugal, Guimaraes...
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "ks-mnp1jw35"
  - `dg:sessionMode`: "insert"
- **`dg:Session_ks_mnq4ixld`** — Query: Where buidling is located
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "ks-mnq4ixld"
  - `dg:sessionMode`: "query"
- **`dg:drs_4cab136231cf`** — drs-4cab136231cf
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "drs-4cab136231cf"
  - `dg:sessionMode`: "ingest"
  - `dg:sessionPrompt`: "Street minimum width is 15 meters."
- **`dg:drs_79ba197cc693`** — drs-79ba197cc693
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "drs-79ba197cc693"
  - `dg:sessionMode`: "edit"
  - `dg:sessionPrompt`: "Street minimum width is 18 meters."
- **`dg:drs_96d1ebd8dc8a`** — drs-96d1ebd8dc8a
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dg:sessionId`: "drs-96d1ebd8dc8a"
  - `dg:sessionMode`: "ingest"
  - `dg:sessionPrompt`: "All building must be maximum 75 meters high"
- **`dg:drs_ac4c176afeeb`** — drs-ac4c176afeeb
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dg:sessionId`: "drs-ac4c176afeeb"
  - `dg:sessionMode`: "query"
  - `dg:sessionPrompt`: "list all rules"

#### Type: `dg:Structure` (1 individual)

- **`dg:Structure_Frame`** — Frame Structure
  - `dg:graph`: dgc:Computgraph

### Layer dgm — 2. Metagraph (SWRL rule structure)

#### Type: `dgm:Builtin` (6 individuals)

- **`dgm:equal`** — equal
  - _Comment:_ swrlb:equal — checks if two arguments are equal.
- **`dgm:greaterThan`** — greaterThan
  - _Comment:_ swrlb:greaterThan — checks if first arg is strictly greater than second. Used for maximum constraints (violation when value exceeds limit).
- **`dgm:greaterThanOrEqual`** — greaterThanOrEqual
  - _Comment:_ swrlb:greaterThanOrEqual — checks if first arg is greater than or equal to second.
- **`dgm:lessThan`** — lessThan
  - _Comment:_ swrlb:lessThan — checks if first arg is strictly less than second. Used for minimum constraints (violation when value below limit).
- **`dgm:lessThanOrEqual`** — lessThanOrEqual
  - _Comment:_ swrlb:lessThanOrEqual — checks if first arg is less than or equal to second.
- **`dgm:notEqual`** — notEqual
  - _Comment:_ swrlb:notEqual — checks if two arguments are not equal. Used for equality constraints (violation when value differs).

#### Type: `dgm:BuiltinAtom` (2 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_A3`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_A3
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_A3"
  - `dgm:atomIri`: "swrlb:greaterThan"
  - `dgm:atomSwrlLabel`: "greaterThan"
  - `dgm:atomType`: "BuiltinAtom"
  - `dgm:hasArg`: dgm:var_h, dgm:literal_75
  - `dgm:refersTo`: dgm:greaterThan
- **`dgm:R_STREET_MIN_WIDTH_18_V_A3`** — dgm:R_STREET_MIN_WIDTH_18_V_A3
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_A3"
  - `dgm:atomIri`: "swrlb:lessThan"
  - `dgm:atomSwrlLabel`: "lessThan"
  - `dgm:atomType`: "BuiltinAtom"
  - `dgm:refersTo`: dgm:lessThan

#### Type: `dgm:ClassAtom` (2 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_A1`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_A1
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_A1"
  - `dgm:atomIri`: "ex:Building"
  - `dgm:atomSwrlLabel`: "Building"
  - `dgm:atomType`: "ClassAtom"
  - `dgm:hasArg`: dgm:var_b
- **`dgm:R_STREET_MIN_WIDTH_18_V_A1`** — dgm:R_STREET_MIN_WIDTH_18_V_A1
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_A1"
  - `dgm:atomIri`: "ex:Street"
  - `dgm:atomSwrlLabel`: "Street"
  - `dgm:atomType`: "ClassAtom"

#### Type: `dgm:DataPropertyAtom` (4 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_A2`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_A2
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_A2"
  - `dgm:atomIri`: "ex:hasHeightM"
  - `dgm:atomSwrlLabel`: "hasHeightM"
  - `dgm:atomType`: "DataPropertyAtom"
  - `dgm:hasArg`: dgm:var_b, dgm:var_h
- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_H1`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_H1
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_H1"
  - `dgm:atomIri`: "ex:violatesMaxHeight"
  - `dgm:atomSwrlLabel`: "violatesMaxHeight"
  - `dgm:atomType`: "DataPropertyAtom"
  - `dgm:hasArg`: dgm:var_b, dgm:literal_true
- **`dgm:R_STREET_MIN_WIDTH_18_V_A2`** — dgm:R_STREET_MIN_WIDTH_18_V_A2
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_A2"
  - `dgm:atomIri`: "ex:hasWidthM"
  - `dgm:atomSwrlLabel`: "hasWidthM"
  - `dgm:atomType`: "DataPropertyAtom"
- **`dgm:R_STREET_MIN_WIDTH_18_V_H1`** — dgm:R_STREET_MIN_WIDTH_18_V_H1
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_H1"
  - `dgm:atomIri`: "ex:violatesMinWidth"
  - `dgm:atomSwrlLabel`: "violatesMinWidth"
  - `dgm:atomType`: "DataPropertyAtom"

#### Type: `dgm:Literal` (5 individuals)

- **`dgm:literal_18`** — 18
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:decimal"
  - `dgm:literalLex`: "18"
- **`dgm:literal_2`** — 2
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:integer"
  - `dgm:literalLex`: "2"
- **`dgm:literal_75`** — 75
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:literalDatatype`: "xsd:decimal"
  - `dgm:literalLex`: "75"
- **`dgm:literal_80`** — 80
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:decimal"
  - `dgm:literalLex`: "80"
- **`dgm:literal_true`** — true
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:boolean"
  - `dgm:literalLex`: "true"

#### Type: `dgm:ObjectVariable` (3 individuals)

- **`dgm:var_b`** — ?b
  - _Comment:_ Object variable representing a Building instance. Inferred from ClassAtom Building(?b). Cross-rule scoped (VTYP-02).
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:variableName`: "?b"
- **`dgm:var_s`** — ?s
  - _Comment:_ Object variable representing a Street instance. Inferred from ClassAtom Street(?s). Cross-rule scoped (VTYP-02).
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:variableName`: "?s"
- **`dgm:var_u`** — ?u
  - _Comment:_ Object variable representing a LivingUnit/Unit instance. Inferred from ClassAtom. Cross-rule scoped (VTYP-02).
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:variableName`: "?u"

#### Type: `dgm:PropertyVariable` (2 individuals)

- **`dgm:var_h`** — ?h
  - _Comment:_ Property variable representing height. Inferred from DataPropertyAtom hasHeightM(?b,?h) arg-2. Rule-scoped (VTYP-03).
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:inferredDatatype`: "xsd:decimal"
  - `dgm:variableName`: "?h"
- **`dgm:var_w`** — ?w
  - _Comment:_ Property variable representing width/window count. Inferred from DataPropertyAtom arg-2. Rule-scoped (VTYP-03).
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:variableName`: "?w"

#### Type: `dgm:Rule` (5 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V`** — R_BUILDING_MAX_HEIGHT_75_V
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "UrbanBlock"
  - `dgm:SWRL`: "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)"
  - `dgm:hasBody`: dgm:R_BUILDING_MAX_HEIGHT_75_V_A1, dgm:R_BUILDING_MAX_HEIGHT_75_V_A2, dgm:R_BUILDING_MAX_HEIGHT_75_V_A3
  - `dgm:hasHead`: dgm:R_BUILDING_MAX_HEIGHT_75_V_H1
  - `dgm:ruleId`: "R_BUILDING_MAX_HEIGHT_75_V"
  - `dgm:ruleKind`: "violation"
- **`dgm:R_BUILDING_MAX_HEIGHT_80_V`** — R_BUILDING_MAX_HEIGHT_80_V
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:SWRL`: "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,80)->violatesMaxHeight(?b,true)"
  - `dgm:ruleId`: "R_BUILDING_MAX_HEIGHT_80_V"
  - `dgm:ruleKind`: "violation"
- **`dgm:R_LIVINGUNIT_MIN_WINDOW_2_V`** — R_LIVINGUNIT_MIN_WINDOW_2_V
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:SWRL`: "LivingUnit(?u)^hasWindowCount(?u,?w)^swrlb:lessThan(?w,2)->violatesMinWindowCount(?u,true)"
  - `dgm:ruleId`: "R_LIVINGUNIT_MIN_WINDOW_2_V"
  - `dgm:ruleKind`: "violation"
- **`dgm:R_STREET_MIN_WIDTH_18_V`** — R_STREET_MIN_WIDTH_18_V
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "TestA"
  - `dgm:SWRL`: "Street(?s)^hasWidthM(?s,?w)^swrlb:lessThan(?w,18)->violatesMinWidth(?s,true)"
  - `dgm:ruleId`: "R_STREET_MIN_WIDTH_18_V"
  - `dgm:ruleKind`: "violation"
- **`dgm:R_UNIT_MIN_WINDOW_2_V`** — R_UNIT_MIN_WINDOW_2_V
  - `dg:graph`: dgm:Metagraph
  - `dg:project`: "Test Project"
  - `dgm:SWRL`: "Unit(?u)^hasWindowCount(?u,?w)^swrlb:lessThan(?w,2)->violatesMinWindowCount(?u,true)"
  - `dgm:ruleId`: "R_UNIT_MIN_WINDOW_2_V"
  - `dgm:ruleKind`: "violation"

#### Type: `dgm:VariableScopeValue` (2 individuals)

- **`dgm:VariableScope_CrossRule`** — cross-rule
  - _Comment:_ Shared identity across all rules in a project. Applies to Object variables (VTYP-02).
- **`dgm:VariableScope_RuleLocal`** — rule-scoped
  - _Comment:_ Independent variable per rule. Applies to Property variables (VTYP-03).

### Layer dgv — 3. Validgraph (validation runs, integration, Reasoner)

#### Type: `dgv:DesignStateParameterTypeValue` (3 individuals)

- **`dgv:ParameterType_Boolean`** — Boolean
  - _Comment:_ Boolean parameter value. From Boolean Toggles in Grasshopper.
- **`dgv:ParameterType_Integer`** — Integer
  - _Comment:_ Integer parameter value (long). From Integer Sliders in Grasshopper.
- **`dgv:ParameterType_Number`** — Number
  - _Comment:_ Floating-point parameter value (double). From Number Sliders in Grasshopper.

#### Type: `dgv:GeoRef` (2 individuals)

- **`dgv:GR_geom_1`** — GeoRef: obj:xyz1
  - _Comment:_ External source-system object handle for the primary mass geometry of Building #1.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:geoRefId`: "obj:xyz1"
- **`dgv:GR_geom_2`** — GeoRef: obj:xyz2
  - _Comment:_ External source-system object handle for the roof geometry of Building #1.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:geoRefId`: "obj:xyz2"

#### Type: `dgv:IdRef` (1 individual)

- **`dgv:IDR_DS_def_h25_w12`** — IdRef for DS_def_h25_w12
  - _Comment:_ Auto-generated identifier for ParamState DS_def_h25_w12 (CMPST-08). Resolves to OI_Building_b1 for cross-run tracking (INTG-03). Will regenerate if any slider value in the ParamState changes.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:idRefValue`: "IDR_a1b2c3d4e5f6"
  - `dgv:resolvesTo`: dgv:OI_Building_b1

#### Type: `dgv:IntegrationConfig` (1 individual)

- **`dgv:Integration_TestA`** — External Integration (TestA)
  - _Comment:_ Integration config from Neo4j Validgraph. Connects project TestA to an external geometry/viewer platform for 3D validation overlay.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:baseModelId`: "4c546c0771"
  - `dgv:externalProjectId`: "44088eefc6"
  - `dgv:provider`: "ExternalViewer"
  - `dgv:validationModelId`: "a6d1e0c5da"

#### Type: `dgv:ObjectInstance` (1 individual)

- **`dgv:OI_Building_b1`** — ObjectInstance: Building #1
  - _Comment:_ Cross-rule identity for the first Building in the TestA model. Bound to Object variable ?b via its ObjState.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:hasObjState`: dg:OS_b1_var_b
  - `dgv:instanceId`: "OI_Building_b1"

#### Type: `dgv:ReStatusValue` (7 individuals)

- **`dgv:ReStatus_AmbiguousTarget`** — AmbiguousTarget
  - _Comment:_ Multiple matching sliders/toggles found — cannot determine which to reinstate.
- **`dgv:ReStatus_Applied`** — Applied
  - _Comment:_ Parameter value was successfully applied to the target slider/toggle.
- **`dgv:ReStatus_MissingTarget`** — MissingTarget
  - _Comment:_ No matching slider/toggle found on the canvas for this parameter.
- **`dgv:ReStatus_OutOfRange`** — OutOfRange
  - _Comment:_ Parameter value exceeds the target slider's min/max range.
- **`dgv:ReStatus_TypeMismatch`** — TypeMismatch
  - _Comment:_ Target slider type does not match parameter type (e.g. Number param wired to Integer slider).
- **`dgv:ReStatus_Unchanged`** — Unchanged
  - _Comment:_ Target slider already has the requested value — no change needed.
- **`dgv:ReStatus_WouldApply`** — WouldApply
  - _Comment:_ Dry-run mode — parameter would be applied if reinstatement were executed.

#### Type: `dgv:Run` (5 individuals)

- **`dgv:VRun_27b121d78c73`** — Validation Run 27b121d78c73
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:runId`: "27b121d78c73"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_63ffbff1f928`** — Validation Run 63ffbff1f928
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:runId`: "63ffbff1f928"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_a5671cb1bd30`** — Validation Run a5671cb1bd30
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:runId`: "a5671cb1bd30"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_ac0d62f1332c`** — Validation Run ac0d62f1332c
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:runId`: "ac0d62f1332c"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_f8678448d4e7`** — Validation Run f8678448d4e7
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:runId`: "f8678448d4e7"
  - `dgv:status`: dgv:Status_Completed

#### Type: `dgv:ValidationEntity` (2 individuals)

- **`dgv:VEntity_a5671cb1bd30_b1_height`** — Entity: Building #1 height check (passed)
  - _Comment:_ Per-rule, per-instance validation result cell. Records that Building #1 passed R_BUILDING_MAX_HEIGHT_75_V with a measured height value of 25 (the propValue — SCHM-05). Belongs to run a5671cb1bd30.
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:dgEntityId`: "VE_a5671cb1bd30_b1_height"
  - `dgv:displayName`: "Building #1"
  - `dgv:propValue`: "25"
  - `dgv:propValueOf`: dgm:var_h
  - `dgv:ruleId`: "R_BUILDING_MAX_HEIGHT_75_V"
  - `dgv:status`: dgv:Status_Passed
  - `dgv:validatesInstance`: dgv:OI_Building_b1
- **`dgv:VEntity_a5671cb1bd30_b1_overflow`** — Entity: Building #1 height check (failed example)
  - _Comment:_ Illustrative failing case: same ObjectInstance, different parametric run, height exceeded the 75m limit (value 80). Shows that ObjectInstance can be referenced by multiple ValidationEntities — one per (Run × Rule).
  - `dg:graph`: dgv:Validgraph
  - `dg:project`: "TestA"
  - `dgv:dgEntityId`: "VE_a5671cb1bd30_b1_overflow"
  - `dgv:displayName`: "Building #1"
  - `dgv:propValue`: "80"
  - `dgv:propValueOf`: dgm:var_h
  - `dgv:ruleId`: "R_BUILDING_MAX_HEIGHT_75_V"
  - `dgv:status`: dgv:Status_Failed
  - `dgv:validatesInstance`: dgv:OI_Building_b1

#### Type: `dgv:ValidationStatusValue` (3 individuals)

- **`dgv:Status_Completed`** — completed
  - _Comment:_ Validation run finished successfully.
- **`dgv:Status_Failed`** — failed
  - _Comment:_ Validation entity failed one or more rules — violations detected.
- **`dgv:Status_Passed`** — passed
  - _Comment:_ Validation entity passed all rules — no violations detected.

### Layer dgs — 4. SpecGraph (project specification notes, tags)

#### Type: `dgs:SpecClass` (2 individuals)

- **`dgs:KC_Session`** — Session
  - _Comment:_ Hub node for knowledge sessions. Neo4j SpecGraph, project: UrbanBlock.
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
- **`dgs:KC_SpecNote`** — SpecNote
  - _Comment:_ Hub node for knowledge notes. Neo4j SpecGraph, project: UrbanBlock.
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"

#### Type: `dgs:SpecNote` (10 individuals)

- **`dgs:Note_BIG_Architects`** — BIG Architects
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:taggedWith`: dgs:Tag_architects, dgs:Tag_studio
  - `dgs:tags`: "architects,studio"
  - `dgs:title`: "BIG Architects"
- **`dgs:Note_BuildingAddress`** — Building Address
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:taggedWith`: dgs:Tag_portugal, dgs:Tag_guimaraes, dgs:Tag_rua_do_avelino_germano
  - `dgs:tags`: "portugal,guimaraes,rua-d0-avelino-germano"
  - `dgs:title`: "Building Address"
- **`dgs:Note_BuildingHeightRegulations`** — Building Height Regulations
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:title`: "Building Height Regulations"
- **`dgs:Note_BuildingStaircaseCount`** — Building Staircase Count
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:taggedWith`: dgs:Tag_building, dgs:Tag_staircase
  - `dgs:tags`: "building,staircase"
  - `dgs:title`: "Building Staircase Count"
- **`dgs:Note_GreenAreaRatio`** — Green Area Ratio
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:title`: "Green Area Ratio"
- **`dgs:Note_MaxFloorToFloorHeightZoneA`** — Maximum floor-to-floor height Zone A
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
  - `dgs:taggedWith`: dgs:Tag_height, dgs:Tag_residential, dgs:Tag_zone_a, dgs:Tag_compliance
  - `dgs:tags`: "height,residential,zone-a,compliance"
  - `dgs:title`: "Maximum floor-to-floor height Zone A"
- **`dgs:Note_ParkingCapacity`** — Parking Capacity
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:taggedWith`: dgs:Tag_parking, dgs:Tag_capacity
  - `dgs:tags`: "parking,capacity"
  - `dgs:title`: "Parking Capacity"
- **`dgs:Note_ProjectLocation`** — Project Location
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:taggedWith`: dgs:Tag_guimaraes, dgs:Tag_braga, dgs:Tag_portugal
  - `dgs:tags`: "guimaraes,braga,portugal"
  - `dgs:title`: "Project Location"
- **`dgs:Note_SetbackRequirements`** — Setback Requirements
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:title`: "Setback Requirements"
- **`dgs:Note_TestUpdateNote`** — Test Update Note
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "test-update-flow"
  - `dgs:title`: "Test Update Note"

#### Type: `dgs:SpecTag` (18 individuals)

- **`dgs:Tag_architects`** — dgs:Tag_architects
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "architects"
- **`dgs:Tag_braga`** — dgs:Tag_braga
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "braga"
- **`dgs:Tag_building`** — dgs:Tag_building
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "building"
- **`dgs:Tag_capacity`** — dgs:Tag_capacity
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "capacity"
- **`dgs:Tag_compliance`** — dgs:Tag_compliance
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
  - `dgs:tagName`: "compliance"
- **`dgs:Tag_corridor`** — dgs:Tag_corridor
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "test-phase03"
  - `dgs:tagName`: "corridor"
- **`dgs:Tag_evacuation`** — dgs:Tag_evacuation
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "test-phase03"
  - `dgs:tagName`: "evacuation"
- **`dgs:Tag_guimaraes`** — dgs:Tag_guimaraes
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "guimaraes"
- **`dgs:Tag_height`** — dgs:Tag_height
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
  - `dgs:tagName`: "height"
- **`dgs:Tag_parking`** — dgs:Tag_parking
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "parking"
- **`dgs:Tag_portugal`** — dgs:Tag_portugal
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "portugal"
- **`dgs:Tag_residential`** — dgs:Tag_residential
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
  - `dgs:tagName`: "residential"
- **`dgs:Tag_rua_do_avelino_germano`** — dgs:Tag_rua_do_avelino_germano
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "rua-d0-avelino-germano"
- **`dgs:Tag_staircase`** — dgs:Tag_staircase
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "staircase"
- **`dgs:Tag_studio`** — dgs:Tag_studio
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "TestA"
  - `dgs:tagName`: "studio"
- **`dgs:Tag_width`** — dgs:Tag_width
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "test-phase03"
  - `dgs:tagName`: "width"
- **`dgs:Tag_zone_a`** — dgs:Tag_zone_a
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
  - `dgs:tagName`: "zone-a"
- **`dgs:Tag_zone_b`** — dgs:Tag_zone_b
  - `dg:graph`: dgs:SpecGraph
  - `dg:project`: "UrbanBlock"
  - `dgs:tagName`: "zone-b"

### Layer dgc — 5. Computgraph (DCM parametric design model)

#### Type: `dg:GraphLayer` (1 individual)

- **`dgc:Computgraph`** — Computgraph
  - _Comment:_ Named individual for the Computgraph layer (OWL 2 punning: simultaneously a class and an individual of dg:GraphLayer).

#### Type: `dgc:Algorithm` (1 individual)

- **`dgc:Algorithm_1`** — 1_Algorithm
  - `dg:graph`: dgc:Computgraph
  - `dgc:algorithmName`: "1_Algorithm"
  - `dgc:hasProcedure`: dgc:Proc_11, dgc:Proc_12

#### Type: `dgc:ConstantParam` (4 individuals)

- **`dgc:Const_11_TrussConfig`** — 11_Const_TrussConfig
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Integer
  - `dgc:parameterDisplayName`: "Truss web configuration"
  - `dgc:parameterName`: "11_Const_TrussConfig"
- **`dgc:Const_11_ptZero`** — 11_Const_ptZero
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Geometry
  - `dgc:parameterDisplayName`: "Origin point"
  - `dgc:parameterName`: "11_Const_ptZero"
- **`dgc:Const_12_IndList_1`** — 12_Const_IndList_1
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Integer
  - `dgc:parameterDisplayName`: "Index list 1"
  - `dgc:parameterName`: "12_Const_IndList_1"
- **`dgc:Const_12_TrussConfig`** — 12_Const_TrussConfig
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Integer
  - `dgc:parameterDisplayName`: "Truss configuration (footer)"
  - `dgc:parameterName`: "12_Const_TrussConfig"

#### Type: `dgc:EmergentParam` (4 individuals)

- **`dgc:Emg_11_LineSDL`** — 11_Emg_LineSDL
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Geometry
  - `dgc:parameterDisplayName`: "Line SDL (computed)"
  - `dgc:parameterName`: "11_Emg_LineSDL"
- **`dgc:Emg_11_UpperChord`** — 11_Emr_UpperChord
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Geometry
  - `dgc:parameterDisplayName`: "Upper chord geometry"
  - `dgc:parameterName`: "11_Emr_UpperChord"
- **`dgc:Emg_12_BottomLn`** — 12_Emg_BottomLn
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Geometry
  - `dgc:parameterDisplayName`: "Footer bottom lines"
  - `dgc:parameterName`: "12_Emg_BottomLn"
- **`dgc:Emg_12_FooterFrame`** — 12_Emg_FooterFrame
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Geometry
  - `dgc:parameterDisplayName`: "Footer frame geometry"
  - `dgc:parameterName`: "12_Emg_FooterFrame"

#### Type: `dgc:ListStructureValue` (4 individuals)

- **`dgc:ListStructure_Flatten`** — Flatten
- **`dgc:ListStructure_Graft`** — Graft
- **`dgc:ListStructure_Reverse`** — Reverse
- **`dgc:ListStructure_Simplify`** — Simplify

#### Type: `dgc:Output` (4 individuals)

- **`dgc:IntF_11_MergeRes`** — 11_IntF_MergeRes
  - `dg:graph`: dgc:Computgraph
  - `dgc:interfaceName`: "11_IntF_MergeRes"
- **`dgc:IntF_11_ParSplitAt`** — 11_IntF_ParSplitAt
  - `dg:graph`: dgc:Computgraph
  - `dgc:interfaceName`: "11_IntF_ParSplitAt"
- **`dgc:IntF_11_TrussConfig`** — 11_IntF_TrussConfig
  - `dg:graph`: dgc:Computgraph
  - `dgc:interfaceName`: "11_IntF_TrussConfig"
- **`dgc:IntF_12_FooterFrame`** — 12_IntF_FooterFrame
  - `dg:graph`: dgc:Computgraph
  - `dgc:interfaceName`: "12_IntF_FooterFrame"

#### Type: `dgc:ParamDataTypeValue` (5 individuals)

- **`dgc:ParamDataType_Boolean`** — Boolean
- **`dgc:ParamDataType_Float`** — Float
- **`dgc:ParamDataType_Geometry`** — Geometry
- **`dgc:ParamDataType_Integer`** — Integer
- **`dgc:ParamDataType_Text`** — Text

#### Type: `dgc:Pattern` (3 individuals)

- **`dgc:Pat_11_DivideLine`** — 11_Pat_DivideLine
  - `dg:graph`: dgc:Computgraph
  - `dgc:hasParameter`: dgc:Var_11_SpansCount, dgc:Const_11_ptZero
  - `dgc:patternName`: "11_Pat_DivideLine"
- **`dgc:Pat_11_TopChord`** — 11_Pat_TopChord
  - `dg:graph`: dgc:Computgraph
  - `dgc:hasParameter`: dgc:Var_11_HTotal, dgc:Const_11_TrussConfig
  - `dgc:patternName`: "11_Pat_TopChord"
- **`dgc:Pat_12_FooterBottomLines`** — 12_Pat_1 - Create footer bottom lines
  - `dg:graph`: dgc:Computgraph
  - `dgc:hasParameter`: dgc:Var_12_HFooter, dgc:Const_12_IndList_1
  - `dgc:patternName`: "12_Pat_1 - Create footer bottom lines"

#### Type: `dgc:Procedure` (2 individuals)

- **`dgc:Proc_11`** — 11_Proc - 2D Truss Configuration
  - `dg:graph`: dgc:Computgraph
  - `dgc:hasInterface`: dgc:IntF_11_ParSplitAt, dgc:IntF_11_TrussConfig, dgc:IntF_11_MergeRes
  - `dgc:hasPattern`: dgc:Pat_11_DivideLine, dgc:Pat_11_TopChord
  - `dgc:procedureName`: "11_Proc - 2D Truss Configuration"
  - `dgc:procedureOrder`: "11"
- **`dgc:Proc_12`** — 12_Proc - 2D Footer Configuration
  - `dg:graph`: dgc:Computgraph
  - `dgc:hasInterface`: dgc:IntF_12_FooterFrame
  - `dgc:hasPattern`: dgc:Pat_12_FooterBottomLines
  - `dgc:procedureName`: "12_Proc - 2D Footer Configuration"
  - `dgc:procedureOrder`: "12"

#### Type: `dgc:VariableParam` (4 individuals)

- **`dgc:Var_11_HTotal`** — 11_Var_HTotal
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Float
  - `dgc:parameterDisplayName`: "Total height"
  - `dgc:parameterName`: "11_Var_HTotal"
- **`dgc:Var_11_SpansCount`** — 11_Var_SpansCount
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Integer
  - `dgc:parameterDisplayName`: "Count of spans"
  - `dgc:parameterName`: "11_Var_SpansCount"
- **`dgc:Var_12_FooterCount`** — 12_Var_FooterCount
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Integer
  - `dgc:parameterDisplayName`: "Footer count"
  - `dgc:parameterName`: "12_Var_FooterCount"
- **`dgc:Var_12_HFooter`** — 12_Var_HFooter
  - `dg:graph`: dgc:Computgraph
  - `dgc:paramDataType`: dgc:ParamDataType_Float
  - `dgc:parameterDisplayName`: "Footer height"
  - `dgc:parameterName`: "12_Var_HFooter"

## Namespace reference

```
dg   = http://example.org/design-grammar#  (Core + Ontograph)
dgm  = http://example.org/design-grammar/meta#
dgv  = http://example.org/design-grammar/valid#
dgs  = http://example.org/design-grammar/spec#
dgc  = http://example.org/design-grammar/comp#
owl  = http://www.w3.org/2002/07/owl#
rdf  = http://www.w3.org/1999/02/22-rdf-syntax-ns#
rdfs = http://www.w3.org/2000/01/rdf-schema#
xsd  = http://www.w3.org/2001/XMLSchema#
```

---

*Auto-generated from `[DesignGrammar-V7.owl](DesignGrammar-V7.owl)` v7.0. Counts: 62 classes, 43 object properties, 67 datatype properties, 142 named individuals, 13 disjointness axioms.*