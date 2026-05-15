# Design Grammar System — Ontology Reference

**Version:** 3.1  
**Source:** `[DesignGrammar.owl](DesignGrammar.owl)`  
**Format:** Human-readable export for NotebookLM ingestion (mind maps, audio overviews, Q&A).  

> This document is a one-to-one rendering of the OWL ontology in plain markdown. Every class, property, enum, axiom, and example instance is listed with its label, comment, parent classes/properties, OWL characteristics, domain, range, and disjointness relations. Use the source OWL file for any reasoner-bound work; use this document for human review and AI ingestion.

## Ontology overview

> System-level ontology for the Design Grammar System (DG).
> Defines the common classes that control data flow in the DG Grasshopper
> plugin and Neo4j database. Domain-specific classes (Building, UrbanBlock, etc.)
> are dynamically generated from user prompts via the Grammar Viewer and are NOT
> part of this ontology.
> Graph layers:
> 1. OntoGraph — dynamically generated domain classes and properties (not defined here)
> 2. Metagraph — SWRL rule structure (Rule, Atom, Variable, Literal, Builtin)
> 3. ValidationGraph — validation runs, entity results, integration config
> 4. KnowledgeGraph — project knowledge notes, tags, sessions
> Schema version: v3

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

The DG ontology partitions its content into four logical layers, each tagged with a `dg:graph` annotation on every class. All four layers persist into a single Neo4j database, isolated by the `dg:project` annotation.

| Prefix | Namespace | Layer | Role |
|---|---|---|---|
| `dg` | `http://example.org/design-grammar#` | Cross-cutting + OntoGraph (dynamic domain ontology meta-schema) | Reifies OWL Class/DatatypeProperty/ObjectProperty as Neo4j nodes for query-ability |
| `dgm` | `http://example.org/design-grammar/metagraph#` | Metagraph | SWRL rule structure: Rule, Atom subtypes, Variable subtypes, Literal, Builtin |
| `dgv` | `http://example.org/design-grammar/validation#` | ValidationGraph | Validation runs, entity results, design state composition, integration config |
| `dgk` | `http://example.org/design-grammar/knowledge#` | KnowledgeGraph | Project notes, tags, knowledge sessions |

## Classes by layer

### Layer dg — 0. Core / Cross-cutting

#### `dg:Class` — Class

A dynamically generated OWL class in the OntoGraph layer. Created from user prompts (e.g. Building, UrbanBlock). Key property: iri.

- **Graph layer annotation:** OntoGraph

#### `dg:DatatypeProperty` — DatatypeProperty

A dynamically generated datatype property in the OntoGraph layer. Represents measurable attributes (e.g. hasHeightM) and violation flags (e.g. violatesMaxHeight). Key property: iri.

- **Graph layer annotation:** OntoGraph

#### `dg:GraphLayer` — GraphLayer

A logical partition of the single Neo4j database. The Design Grammar System organizes all persisted nodes into four layers: OntoGraph, Metagraph, ValidationGraph, KnowledgeGraph. Every node carries a `graph` property identifying its layer.


#### `dg:ObjectProperty` — ObjectProperty

A dynamically generated object property in the OntoGraph layer. Represents relationships between domain classes (e.g. locatedIn). Key property: iri.

- **Graph layer annotation:** OntoGraph

### Layer dgm — 2. Metagraph (SWRL rule structure)

#### `dgm:Atom` — Atom

An individual SWRL atom — a single predicate assertion within a rule. Types: ClassAtom, DataPropertyAtom, ObjectPropertyAtom, BuiltinAtom. Key property: Atom_Id.

- **Graph layer annotation:** Metagraph

#### `dgm:Builtin` — Builtin

A SWRL builtin comparison or arithmetic operator. Referenced by BuiltinAtom via REFERS_TO. Key property: iri (swrlb: prefix).

- **Graph layer annotation:** Metagraph

#### `dgm:BuiltinAtom` — BuiltinAtom

An atom invoking a SWRL builtin comparison operator (e.g. swrlb:greaterThan(?h, 75)). Takes two arguments for comparison.

- **Parent class(es):** `dgm:Atom`
- **Graph layer annotation:** Metagraph

#### `dgm:BuiltinVariable` — BuiltinVariable

A variable bound only inside BuiltinAtom arguments (e.g. an arithmetic intermediate). Not surfaced on the Grasshopper canvas — the VariableTypeInferrer recognizes this category to keep RULE DECONSTRUCT outputs clean (VTYP-01 priority chain step 3).

- **Parent class(es):** `dgm:Variable`
- **Graph layer annotation:** Metagraph

#### `dgm:ClassAtom` — ClassAtom

An atom asserting class membership (e.g. Building(?b)). Takes one variable argument at pos 1.

- **Parent class(es):** `dgm:Atom`
- **Graph layer annotation:** Metagraph

#### `dgm:DataPropertyAtom` — DataPropertyAtom

An atom asserting a datatype property value (e.g. hasHeightM(?b, ?h)). Takes two arguments: entity variable (pos 1) and value variable/literal (pos 2).

- **Parent class(es):** `dgm:Atom`
- **Graph layer annotation:** Metagraph

#### `dgm:DesignRuleSession` — DesignRuleSession

An interaction log for rule ingest/query/edit operations. Stores the user prompt and LLM result for audit and undo capability.

- **Graph layer annotation:** Metagraph

#### `dgm:Literal` — Literal

A constant value used as an atom argument (e.g. 75, true). Key properties: lex (lexical form) + datatype (xsd type).

- **Graph layer annotation:** Metagraph

#### `dgm:ObjectPropertyAtom` — ObjectPropertyAtom

An atom asserting an object property relationship (e.g. locatedIn(?b, ?block)). Takes two variable arguments.

- **Parent class(es):** `dgm:Atom`
- **Graph layer annotation:** Metagraph

#### `dgm:ObjectVariable` — ObjectVariable

A variable representing a domain entity instance (e.g. ?b for Building). Inferred from ClassAtom arguments (VTYP-01). Object variables are cross-rule scoped: the same variable name maps to the same entity across all rules in a project (VTYP-02). Can be wired to OBJECT STATE component to create ObjectState (CMPST-01).

- **Parent class(es):** `dgm:Variable`
- **Graph layer annotation:** Metagraph

#### `dgm:PropertyVariable` — PropertyVariable

A variable representing a datatype property value (e.g. ?h for height). Inferred from DataPropertyAtom arg-2 position (VTYP-01). Property variables are rule-scoped: the same name in different rules represents independent variables (VTYP-03).

- **Parent class(es):** `dgm:Variable`
- **Graph layer annotation:** Metagraph

#### `dgm:Rule` — Rule

A design grammar rule expressed as a SWRL implication. Contains body atoms (conditions) and head atoms (conclusions). Key property: Rule_Id. Format: R_<DOMAIN>_<PROPERTY>_<LIMIT>_V

- **Graph layer annotation:** Metagraph

#### `dgm:Variable` — Variable

A SWRL variable (e.g. ?b, ?h). Key property: name (prefixed with '?'). Variable kind (Object vs Property) is inferred at read-time from atom structure (VTYP-01). MERGE key includes project to prevent cross-project collision (SCHM-02).

- **Graph layer annotation:** Metagraph

#### `dgm:VariableKindValue` — VariableKind

Enumeration of variable kinds inferred by VariableTypeInferrer per VTYP-01 priority chain. Corresponds to C# enum DG.Core.Models.VariableKind. Closed via owl:oneOf — the value space is fixed.

- **Closed enum (owl:oneOf):** `dgm:VariableKind_Object`, `dgm:VariableKind_Property`, `dgm:VariableKind_Builtin`
- **Graph layer annotation:** Metagraph

#### `dgm:VariableScopeValue` — VariableScope

Enumeration of variable scoping semantics derived from VariableKind. SCHM-06: enum class mirroring DesignStateParameterTypeValue pattern. Closed via owl:oneOf.

- **Closed enum (owl:oneOf):** `dgm:VariableScope_CrossRule`, `dgm:VariableScope_RuleLocal`
- **Graph layer annotation:** Metagraph

### Layer dgv — 3. ValidationGraph (validation runs, design state, integration)

#### `dgv:DefState` — DefState

Definition state — a named set of Number/Integer/Boolean parameters captured from Grasshopper sliders and toggles. Represents the current parametric configuration. When DefState changes, dependent IdRefs regenerate. ID prefix: DS_.

- **Parent class(es):** `dgv:DesignState`
- **Graph layer annotation:** ValidationGraph

#### `dgv:DesignState` — DesignState

A snapshot of design parameters captured from Grasshopper. Single Neo4j label :DesignState with a `kind` property discriminating between DefState and ObjectState. ID prefixes: DS_ (DefState), OS_ (ObjectState). Used as input to CLASSIFICATOR and persisted in validation runs.

- **Graph layer annotation:** ValidationGraph

#### `dgv:DesignStateKindValue` — DesignStateKind

Enumeration of DesignState subtype discriminators per SCHM-01. Single :DesignState Neo4j label uses this enum's individuals as values of the kind property. Closed via owl:oneOf.

- **Closed enum (owl:oneOf):** `dgv:DesignStateKind_DefState`, `dgv:DesignStateKind_ObjectState`
- **Graph layer annotation:** ValidationGraph

#### `dgv:DesignStateParameter` — DesignStateParameter

A single measurable parameter within a DefState snapshot. Has a parameterId, displayName, type (Number/Integer/Boolean), and the corresponding typed value.

- **Graph layer annotation:** ValidationGraph

#### `dgv:DesignStateParameterTypeValue` — DesignStateParameterType

Enumeration of supported parameter value types for DesignState snapshots. Corresponds to C# enum DG.Core.Models.DesignStateParameterType. Closed via owl:oneOf.

- **Closed enum (owl:oneOf):** `dgv:ParameterType_Number`, `dgv:ParameterType_Integer`, `dgv:ParameterType_Boolean`
- **Graph layer annotation:** ValidationGraph

#### `dgv:GeoRef` — GeoRef

Geometry reference — a handle to a geometry primitive in the source model (Speckle objectId, Rhino GUID, etc.) wired into the OBJECT STATE component (CMPST-01, CTRCT-09). One ObjectState may reference multiple GeoRefs (the geometry elements that compose the ObjectInstance).

- **Graph layer annotation:** ValidationGraph

#### `dgv:IdRef` — IdRef

Auto-generated DesignState identifier (CMPST-08). IdRef = DesignState ID — NOT ObjectState ID. Regenerates whenever DefState changes (CMPST-05). Persisted in statePayloadJson for cross-run object identity tracking (INTG-03). Resolves to one or more ObjectInstance(s). ID prefix: IDR_.

- **Graph layer annotation:** ValidationGraph

#### `dgv:IntegrationConfig` — IntegrationConfig

Configuration node linking a DG project to its Speckle integration. Stores Speckle project ID, base model, and validation model references. One per project per provider.

- **Graph layer annotation:** ValidationGraph

#### `dgv:ObjectInstance` — ObjectInstance

Cross-rule identity of a validated geometric element (CMPST-06). The noun — the actual thing in the model that gets validated. Stable across geometry edits. Each ObjectInstance has exactly one ObjectState (its current binding snapshot). ID prefix: OI_. Both ObjectInstance and ObjectState live above rule scope.

- **Graph layer annotation:** ValidationGraph

#### `dgv:ObjectState` — ObjectState

Object state — associates an Object variable reference (from SWRL ClassAtom) with geometry elements. Created by the OBJECT STATE component by wiring ObjectRef + GeoRef. Composed into DESIGN STATE alongside DefState to produce stable IdRefs. ID prefix: OS_. NEVER has an IdRef — carries its own stateId (OS_ prefix). Enforced via SubClassOf (hasIdRef max 0).

- **Parent class(es):** `dgv:DesignState`
- **Restrictions:** dgv:hasIdRef max 0 of dgv:IdRef
- **Graph layer annotation:** ValidationGraph

#### `dgv:ReinstatementStatusValue` — ReinstatementStatus

Outcome status for a single parameter during design state reinstatement. Corresponds to C# enum DG.Core.Models.ReinstatementStatus. Used by the REINSTATE component to report per-parameter results. Closed via owl:oneOf.

- **Closed enum (owl:oneOf):** `dgv:ReinstatementStatus_Applied`, `dgv:ReinstatementStatus_MissingTarget`, `dgv:ReinstatementStatus_TypeMismatch`, `dgv:ReinstatementStatus_AmbiguousTarget`, `dgv:ReinstatementStatus_OutOfRange`, `dgv:ReinstatementStatus_Unchanged`, `dgv:ReinstatementStatus_WouldApply`
- **Graph layer annotation:** ValidationGraph

#### `dgv:ValidationEntity` — ValidationEntity

A BIM entity evaluated in a validation run. Records the entity's DG ID, display name, and overall pass/fail status for the specific run and rule.

- **Graph layer annotation:** ValidationGraph

#### `dgv:ValidationRun` — ValidationRun

A single execution of rule evaluation against design state. Records which rules were evaluated, the Speckle version created, and entity-level pass/fail results. Created by the DG Grasshopper plugin's validation workflow.

- **Graph layer annotation:** ValidationGraph

#### `dgv:ValidationStatusValue` — ValidationStatus

Status values for validation runs and entity results. Closed via owl:oneOf — value space is fixed at Completed, Passed, Failed.

- **Closed enum (owl:oneOf):** `dgv:Status_Completed`, `dgv:Status_Passed`, `dgv:Status_Failed`
- **Graph layer annotation:** ValidationGraph

### Layer dgk — 4. KnowledgeGraph (project notes, tags, sessions)

#### `dgk:KnowledgeClass` — KnowledgeClass

Parent hub node connecting all instances of a knowledge type. Acts as a type discriminator (e.g. KnowledgeNote, KnowledgeSession).

- **Graph layer annotation:** KnowledgeGraph

#### `dgk:KnowledgeNote` — KnowledgeNote

A project knowledge entry (from folder ingest or NL prompt). Contains title, content, tags, and source reference.

- **Graph layer annotation:** KnowledgeGraph

#### `dgk:KnowledgeSession` — KnowledgeSession

An interaction log for knowledge operations (insert, query, update). Records the user prompt and LLM result.

- **Graph layer annotation:** KnowledgeGraph

#### `dgk:KnowledgeTag` — KnowledgeTag

A tag label shared across knowledge notes for categorization.

- **Graph layer annotation:** KnowledgeGraph

## Object properties by layer

### Layer dgm — 2. Metagraph (SWRL rule structure)

#### `dgm:hasArg` — ARG

Connects an Atom to its arguments (Variable or Literal). Property: pos (integer, 1-indexed position). Characteristics: none (Atoms have multiple args; same Variable may appear in multiple Atoms). Range: union of {Variable, Literal}.

- **Domain:** `dgm:Atom`
- **Range:** `dgm:Variable ∪ dgm:Literal`

#### `dgm:hasBody` — HAS_BODY

Connects a Rule to its body (condition) atoms. The body checks the condition that breaks the rule in violation mode. Property: order (integer, 1-indexed). Characteristics: InverseFunctional — each Atom belongs to exactly one Rule's body. Disjoint with hasHead: no Atom may simultaneously be a body and head atom of the same Rule.

- **Domain:** `dgm:Rule`
- **Range:** `dgm:Atom`
- **Characteristics:** InverseFunctional
- **Disjoint with (property):** `dgm:hasHead`

#### `dgm:hasHead` — HAS_HEAD

Connects a Rule to its head (conclusion) atoms. The head sets the violation flag to true when the body fires. Property: order (integer, 1-indexed). Characteristics: InverseFunctional — each Atom belongs to exactly one Rule's head. Disjoint with hasBody (declared on hasBody side).

- **Domain:** `dgm:Rule`
- **Range:** `dgm:Atom`
- **Characteristics:** InverseFunctional

#### `dgm:refersTo` — REFERS_TO

Connects an Atom to the ontology entity it references (Class, DatatypeProperty, ObjectProperty, or Builtin). Each Atom has exactly one REFERS_TO. Characteristics: Functional. Range: union of {Class, DatatypeProperty, ObjectProperty, Builtin}.

- **Domain:** `dgm:Atom`
- **Range:** `dg:Class ∪ dg:DatatypeProperty ∪ dg:ObjectProperty ∪ dgm:Builtin`
- **Characteristics:** Functional

#### `dgm:variableKind` — variableKind

Variable kind discriminator (enum-valued): VariableKind_Object (inferred from ClassAtom arg, cross-rule scoped per VTYP-02), VariableKind_Property (inferred from DataPropertyAtom arg-2, rule-scoped per VTYP-03), or VariableKind_Builtin (only in BuiltinAtom args, not exposed on canvas). Inferred at read-time by VariableTypeInferrer.Infer() — not stored on the Neo4j Var node (VTYP-01). Characteristics: Functional.

- **Domain:** `dgm:Variable`
- **Range:** `dgm:VariableKindValue`
- **Characteristics:** Functional

#### `dgm:variableScope` — variableScope

Scoping semantics (enum-valued): VariableScope_CrossRule for Object variables (shared identity across rules in a project, VTYP-02) or VariableScope_RuleLocal for Property variables (independent per rule, VTYP-03). Derived from variableKind. Characteristics: Functional.

- **Domain:** `dgm:Variable`
- **Range:** `dgm:VariableScopeValue`
- **Characteristics:** Functional

### Layer dgv — 3. ValidationGraph (validation runs, design state, integration)

#### `dgv:hasEntity` — HAS_ENTITY

Connects a ValidationRun to its evaluated ValidationEntity results. Characteristics: InverseFunctional — each ValidationEntity belongs to exactly one ValidationRun.

- **Domain:** `dgv:ValidationRun`
- **Range:** `dgv:ValidationEntity`
- **Characteristics:** InverseFunctional

#### `dgv:hasGeoRef` — HAS_GEO_REF

Connects an ObjectState to its geometry handles wired into the GeoRef input of OBJECT STATE (CTRCT-09). One ObjectState may have many GeoRefs (the geometry elements composing the ObjectInstance). Characteristics: InverseFunctional — each GeoRef belongs to exactly one ObjectState.

- **Domain:** `dgv:ObjectState`
- **Range:** `dgv:GeoRef`
- **Characteristics:** InverseFunctional

#### `dgv:hasIdRef` — HAS_ID_REF

Connects a DefState to its auto-generated IdRef. Characteristics: Functional + InverseFunctional — IdRef IS the DefState-generated DesignState ID, so strict 1:1 cardinality (CMPST-08). Domain restricted to DefState (NOT all DesignState): per CMPST-05, only DefState triggers IdRef regeneration. ObjectState carries its own stateId (OS_ prefix) and never has an IdRef — see the ObjectState SubClassOf (hasIdRef max 0) restriction below.

- **Domain:** `dgv:DefState`
- **Range:** `dgv:IdRef`
- **Characteristics:** Functional, InverseFunctional

#### `dgv:hasObjectState` — HAS_OBJECT_STATE

Connects an ObjectInstance to its current ObjectState (the geometry + variable binding snapshot). Characteristics: Functional + InverseFunctional — strict 1:1 cardinality per CMPST-06. Inverse of representsInstance.

- **Domain:** `dgv:ObjectInstance`
- **Range:** `dgv:ObjectState`
- **Characteristics:** Functional, InverseFunctional
- **Inverse of:** `dgv:representsInstance`

#### `dgv:hasObjectVariable` — HAS_OBJECT_VARIABLE

Connects an ObjectState to the SWRL Object Variable wired into the ObjectRef input of OBJECT STATE (CTRCT-08). The ObjectVariable is cross-rule (VTYP-02) — same variable name identifies the same ObjectInstance across all rules in a project. Characteristics: Functional — one canonical variable per ObjectState.

- **Domain:** `dgv:ObjectState`
- **Range:** `dgm:ObjectVariable`
- **Characteristics:** Functional

#### `dgv:hasParameter` — HAS_PARAMETER

Connects a DesignState snapshot to its individual parameters. Characteristics: InverseFunctional — each DesignStateParameter belongs to exactly one DesignState.

- **Domain:** `dgv:DesignState`
- **Range:** `dgv:DesignStateParameter`
- **Characteristics:** InverseFunctional

#### `dgv:kind` — kind

DesignState kind discriminator (enum-valued): DesignStateKind_DefState (parameter snapshot from sliders/toggles) or DesignStateKind_ObjectState (object variable + geometry association). Stored on the single :DesignState Neo4j label per SCHM-01. Characteristics: Functional.

- **Domain:** `dgv:DesignState`
- **Range:** `dgv:DesignStateKindValue`
- **Characteristics:** Functional

#### `dgv:parameterType` — parameterType

Type discriminator for parameter value (enum-valued): ParameterType_Number, ParameterType_Integer, or ParameterType_Boolean. Characteristics: Functional.

- **Domain:** `dgv:DesignStateParameter`
- **Range:** `dgv:DesignStateParameterTypeValue`
- **Characteristics:** Functional

#### `dgv:propValueOf` — PROP_VALUE_OF

Connects a ValidationEntity to the PropertyVariable whose value the rule checked (SCHM-05). The "main attribute being validated" — determines which property's value is shown in the Model Viewer's passing/failing list. Characteristics: Functional — one main property per ValidationEntity cell.

- **Domain:** `dgv:ValidationEntity`
- **Range:** `dgm:PropertyVariable`
- **Characteristics:** Functional

#### `dgv:representsInstance` — REPRESENTS_INSTANCE

Connects an ObjectState back to the ObjectInstance it captures. Characteristics: Functional + InverseFunctional — strict 1:1 cardinality. Inverse of hasObjectState.

- **Domain:** `dgv:ObjectState`
- **Range:** `dgv:ObjectInstance`
- **Characteristics:** Functional, InverseFunctional

#### `dgv:resolvesTo` — RESOLVES_TO

Connects an IdRef to the ObjectInstance(s) it tracks across runs (INTG-03). Characteristics: none — an IdRef may resolve to many ObjectInstances (the run's full object set), and an ObjectInstance is referenced by many IdRefs over time (one per DefState configuration).

- **Domain:** `dgv:IdRef`
- **Range:** `dgv:ObjectInstance`

#### `dgv:status` — status

Status of a validation run (Status_Completed) or entity result (Status_Passed / Status_Failed). Domain union: ValidationRun ∪ ValidationEntity. Characteristics: Functional.

- **Domain:** `dgv:ValidationRun ∪ dgv:ValidationEntity`
- **Range:** `dgv:ValidationStatusValue`
- **Characteristics:** Functional

#### `dgv:validatesInstance` — VALIDATES_INSTANCE

Connects a ValidationEntity result cell to the ObjectInstance it describes. Characteristics: Functional — each ValidationEntity describes exactly one ObjectInstance. Inverse direction is NOT functional: an ObjectInstance has many ValidationEntities (one per rule per run).

- **Domain:** `dgv:ValidationEntity`
- **Range:** `dgv:ObjectInstance`
- **Characteristics:** Functional

### Layer dgk — 4. KnowledgeGraph (project notes, tags, sessions)

#### `dgk:instanceOf` — INSTANCE_OF

Connects a KnowledgeNote or KnowledgeSession to its parent KnowledgeClass hub node. Characteristics: Functional — each Note/Session has exactly one parent hub.

- **Domain:** `—`
- **Range:** `dgk:KnowledgeClass`
- **Characteristics:** Functional

#### `dgk:taggedWith` — TAGGED_WITH

Connects a KnowledgeNote to its KnowledgeTag nodes. Characteristics: none (many-to-many — a Note has multiple Tags, a Tag is reused across Notes).

- **Domain:** `dgk:KnowledgeNote`
- **Range:** `dgk:KnowledgeTag`

## Datatype properties by layer

### Layer dg — 0. Core / Cross-cutting

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dg:createdAt` | createdAt | `—` | `xsd:dateTime` | — | ISO 8601 UTC timestamp of node creation. Used across all graph layers. |
| `dg:iri` | iri | `—` | `xsd:string` | — | IRI identifier for ontology entities. Format: ex:<Name> (e.g. ex:Building, ex:hasHeightM). |
| `dg:label` | label | `—` | `xsd:string` | — | Human-readable display label for Class and ObjectProperty nodes. |
| `dg:range` | range | `dg:DatatypeProperty` | `xsd:string` | — | XSD datatype range for DatatypeProperty nodes (e.g. xsd:decimal, xsd:integer, xsd:boolean). |

### Layer dgm — 2. Metagraph (SWRL rule structure)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
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
| `dgm:ruleText` | text | `dgm:Rule` | `xsd:string` | — | The SWRL expression string for a rule (e.g. Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)). |
| `dgm:ruleTitle` | title | `dgm:Rule` | `xsd:string` | — | Optional human-readable title for a rule. |
| `dgm:sessionId` | sessionId | `dgm:DesignRuleSession` | `xsd:string` | Functional | Unique identifier for a DesignRuleSession (format: drs-<hex12>). Characteristics: Functional. |
| `dgm:sessionMode` | mode | `dgm:DesignRuleSession` | `xsd:string` | — | Interaction mode: 'ingest', 'query', or 'edit'. |
| `dgm:sessionPrompt` | prompt | `dgm:DesignRuleSession` | `xsd:string` | — | The user's natural-language prompt that triggered this session. |
| `dgm:sessionResult` | result | `dgm:DesignRuleSession` | `xsd:string` | — | The LLM-generated Cypher result of the session. |
| `dgm:variableName` | name | `dgm:Variable` | `xsd:string` | Functional | Variable name prefixed with '?' (e.g. ?b, ?h, ?lu). Characteristics: Functional. |

### Layer dgv — 3. ValidationGraph (validation runs, design state, integration)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dgv:baseModelId` | baseModelId | `dgv:IntegrationConfig` | `xsd:string` | — | ID of the base geometry model in Speckle. Stored on the IntegrationConfig node. |
| `dgv:baseModelName` | baseModelName | `dgv:IntegrationConfig` | `xsd:string` | — | Display name of the base geometry model in Speckle. |
| `dgv:baseVersionId` | baseVersionId | `dgv:ValidationRun` | `xsd:string` | — | Speckle version ID of the base model used in this validation run. |
| `dgv:capturedAtUtc` | capturedAtUtc | `dgv:DesignState ∪ dgv:ValidationRun` | `xsd:dateTime` | Functional | UTC timestamp when a design state or validation run was captured. Characteristics: Functional — one capture time per snapshot. Domain union: DesignState ∪ ValidationRun. |
| `dgv:dgEntityId` | dgEntityId | `dgv:ValidationEntity` | `xsd:string` | Functional | Unique DG identifier for a BIM entity in a validation run. Characteristics: Functional. |
| `dgv:displayName` | displayName | `dgv:ValidationEntity` | `xsd:string` | — | Human-readable name for a validation entity. |
| `dgv:geoRefId` | geoRefId | `dgv:GeoRef` | `xsd:string` | Functional | Source-system handle for a geometry primitive (e.g. Speckle objectId, Rhino GUID). The value wired into the GeoRef input of OBJECT STATE per CTRCT-09. Characteristics: Functional. |
| `dgv:idRefValue` | idRefValue | `dgv:IdRef` | `xsd:string` | Functional | The auto-regenerated identifier string produced by DESIGN STATE (CMPST-03, CMPST-05). Changes whenever DefState changes. Note: IdRef is the DesignState's ID, NOT ObjectState's ID — ObjectState carries its own stateId (OS_ prefix). Characteristics: Functional. |
| `dgv:instanceId` | instanceId | `dgv:ObjectInstance` | `xsd:string` | Functional | Stable cross-rule identifier of an ObjectInstance. Format: OI_<hash>. Persists across geometry edits (CMPST-06). Characteristics: Functional. |
| `dgv:modelViewerUrl` | modelViewerUrl | `dgv:ValidationRun` | `xsd:string` | — | URL to view the validation results in the Model Viewer. |
| `dgv:objectRef` | objectRef | `dgv:ObjectState` | `xsd:string` | — | Object variable reference string for an ObjectState (e.g. the variable name from a ClassAtom). Links this ObjectState to the SWRL Object variable it represents. |
| `dgv:parameterId` | parameterId | `dgv:DesignStateParameter` | `xsd:string` | Functional | Identifier of a design state parameter (maps to a DatatypeProperty iri in the OntoGraph). Characteristics: Functional. |
| `dgv:propValue` | propValue | `dgv:ValidationEntity` | `xsd:string` | — | The validated property value for this ValidationEntity (SCHM-05). One value per (Run, Rule, ObjectInstance) cell — the "main attribute" the rule checked. Shown in the Model Viewer's passing/failing item list per rule. Lex form (xsd:string) for display; actual typed value lives on the DesignStateParameter. |
| `dgv:provider` | provider | `dgv:IntegrationConfig` | `xsd:string` | — | Integration provider name (e.g. 'Speckle'). |
| `dgv:ruleId` | ruleId | `dgv:ValidationEntity` | `xsd:string` | Functional | Rule ID associated with a validation entity result. Characteristics: Functional — each ValidationEntity references exactly one rule. |
| `dgv:rulesJson` | rulesJson | `dgv:ValidationRun` | `xsd:string` | — | JSON-serialized array of rules evaluated in this run. |
| `dgv:runId` | runId | `dgv:ValidationRun` | `xsd:string` | Functional | Unique identifier for a validation run. Characteristics: Functional. |
| `dgv:speckleProjectId` | speckleProjectId | `dgv:IntegrationConfig` | `xsd:string` | — | ID of the linked Speckle project. Stored on the IntegrationConfig node for the project. |
| `dgv:stateId` | stateId | `dgv:DesignState` | `xsd:string` | Functional | Unique identifier for a DesignState snapshot. Characteristics: Functional. |
| `dgv:statePayloadJson` | statePayloadJson | `dgv:ValidationRun` | `xsd:string` | — | JSON-serialized DesignState snapshot used as input to this run. |
| `dgv:validationModelId` | validationModelId | `dgv:IntegrationConfig` | `xsd:string` | — | ID of the validation overlay model in Speckle. Stored on the IntegrationConfig node. |
| `dgv:validationVersionId` | validationVersionId | `dgv:ValidationRun` | `xsd:string` | — | Speckle version ID of the validation overlay created by this run. |

### Layer dgk — 4. KnowledgeGraph (project notes, tags, sessions)

| Property | Label | Domain | Range | Characteristics | Description |
|---|---|---|---|---|---|
| `dgk:content` | content | `dgk:KnowledgeNote` | `xsd:string` | — | Full text content of a knowledge note. |
| `dgk:createdAt` | createdAt | `—` | `xsd:dateTime` | — | ISO 8601 UTC timestamp of creation. |
| `dgk:knowledgeSessionId` | sessionId | `dgk:KnowledgeSession` | `xsd:string` | Functional | Unique identifier for a knowledge session (format: ks-<hex12>). Characteristics: Functional. |
| `dgk:mode` | mode | `dgk:KnowledgeSession` | `xsd:string` | — | Knowledge session mode: 'insert', 'query', or 'update'. |
| `dgk:noteId` | noteId | `dgk:KnowledgeNote` | `xsd:string` | Functional | Unique identifier for a knowledge note. Characteristics: Functional. |
| `dgk:source` | source | `dgk:KnowledgeNote` | `xsd:string` | — | Source file path or reference for a knowledge note (e.g. notes/site.md). |
| `dgk:tagName` | name | `dgk:KnowledgeTag` | `xsd:string` | Functional | Tag name string (e.g. "zoning", "structural"). Characteristics: Functional — one canonical name per Tag. |
| `dgk:tags` | tags | `dgk:KnowledgeNote` | `xsd:string` | — | Array of tag names associated with a knowledge note (stored as Neo4j list property). |
| `dgk:title` | title | `dgk:KnowledgeNote` | `xsd:string` | — | Title of a knowledge note. |
| `dgk:updatedAt` | updatedAt | `—` | `xsd:dateTime` | — | ISO 8601 UTC timestamp of last update. |

## Enumerated value classes (closed sets)

Six enum classes are closed via `owl:oneOf` — their value space is fixed. Any individual asserted as a member that is not one of the listed individuals triggers an inconsistency.

### `dgm:VariableKindValue` — VariableKind

Enumeration of variable kinds inferred by VariableTypeInferrer per VTYP-01 priority chain. Corresponds to C# enum DG.Core.Models.VariableKind. Closed via owl:oneOf — the value space is fixed.

**Allowed values:**

- `dgm:VariableKind_Object` — **Object**: Variable representing a domain entity instance. Inferred from ClassAtom arg-1 (VTYP-01 step 1). Cross-rule scoped (VTYP-02).
- `dgm:VariableKind_Property` — **Property**: Variable representing a datatype property value. Inferred from DataPropertyAtom arg-2+ (VTYP-01 step 2). Rule-scoped (VTYP-03).
- `dgm:VariableKind_Builtin` — **Builtin**: Variable bound only inside BuiltinAtom args. Not exposed on the Grasshopper canvas (VTYP-01 step 3).

### `dgm:VariableScopeValue` — VariableScope

Enumeration of variable scoping semantics derived from VariableKind. SCHM-06: enum class mirroring DesignStateParameterTypeValue pattern. Closed via owl:oneOf.

**Allowed values:**

- `dgm:VariableScope_CrossRule` — **cross-rule**: Shared identity across all rules in a project. Applies to Object variables (VTYP-02).
- `dgm:VariableScope_RuleLocal` — **rule-scoped**: Independent variable per rule. Applies to Property variables (VTYP-03).

### `dgv:DesignStateKindValue` — DesignStateKind

Enumeration of DesignState subtype discriminators per SCHM-01. Single :DesignState Neo4j label uses this enum's individuals as values of the kind property. Closed via owl:oneOf.

**Allowed values:**

- `dgv:DesignStateKind_DefState` — **DefState**: Parametric capture snapshot from Grasshopper sliders/toggles. ID prefix: DS_.
- `dgv:DesignStateKind_ObjectState` — **ObjectState**: Object variable to geometry binding snapshot. 1:1 with an ObjectInstance. ID prefix: OS_.

### `dgv:DesignStateParameterTypeValue` — DesignStateParameterType

Enumeration of supported parameter value types for DesignState snapshots. Corresponds to C# enum DG.Core.Models.DesignStateParameterType. Closed via owl:oneOf.

**Allowed values:**

- `dgv:ParameterType_Number` — **Number**: Floating-point parameter value (double). From Number Sliders in Grasshopper.
- `dgv:ParameterType_Integer` — **Integer**: Integer parameter value (long). From Integer Sliders in Grasshopper.
- `dgv:ParameterType_Boolean` — **Boolean**: Boolean parameter value. From Boolean Toggles in Grasshopper.

### `dgv:ReinstatementStatusValue` — ReinstatementStatus

Outcome status for a single parameter during design state reinstatement. Corresponds to C# enum DG.Core.Models.ReinstatementStatus. Used by the REINSTATE component to report per-parameter results. Closed via owl:oneOf.

**Allowed values:**

- `dgv:ReinstatementStatus_Applied` — **Applied**: Parameter value was successfully applied to the target slider/toggle.
- `dgv:ReinstatementStatus_MissingTarget` — **MissingTarget**: No matching slider/toggle found on the canvas for this parameter.
- `dgv:ReinstatementStatus_TypeMismatch` — **TypeMismatch**: Target slider type does not match parameter type (e.g. Number param wired to Integer slider).
- `dgv:ReinstatementStatus_AmbiguousTarget` — **AmbiguousTarget**: Multiple matching sliders/toggles found — cannot determine which to reinstate.
- `dgv:ReinstatementStatus_OutOfRange` — **OutOfRange**: Parameter value exceeds the target slider's min/max range.
- `dgv:ReinstatementStatus_Unchanged` — **Unchanged**: Target slider already has the requested value — no change needed.
- `dgv:ReinstatementStatus_WouldApply` — **WouldApply**: Dry-run mode — parameter would be applied if reinstatement were executed.

### `dgv:ValidationStatusValue` — ValidationStatus

Status values for validation runs and entity results. Closed via owl:oneOf — value space is fixed at Completed, Passed, Failed.

**Allowed values:**

- `dgv:Status_Completed` — **completed**: Validation run finished successfully.
- `dgv:Status_Passed` — **passed**: Validation entity passed all rules — no violations detected.
- `dgv:Status_Failed` — **failed**: Validation entity failed one or more rules — violations detected.

## Disjointness axioms

Each group below is `owl:AllDisjointClasses` — no individual may simultaneously belong to two classes in the same group.

1. `dgv:DefState`, `dgv:ObjectState`
2. `dgv:ObjectInstance`, `dgv:ObjectState`, `dgv:IdRef`, `dgv:GeoRef`
3. `dgv:ValidationRun`, `dgv:ValidationEntity`, `dgv:DesignState`, `dgv:DesignStateParameter`, `dgv:IntegrationConfig`, `dgv:ObjectInstance`, `dgv:GeoRef`, `dgv:IdRef`
4. `dgm:ClassAtom`, `dgm:DataPropertyAtom`, `dgm:ObjectPropertyAtom`, `dgm:BuiltinAtom`
5. `dgm:ObjectVariable`, `dgm:PropertyVariable`, `dgm:BuiltinVariable`
6. `dgm:Rule`, `dgm:Atom`, `dgm:Variable`, `dgm:Literal`, `dgm:Builtin`, `dgm:DesignRuleSession`
7. `dg:Class`, `dg:DatatypeProperty`, `dg:ObjectProperty`
8. `dgk:KnowledgeClass`, `dgk:KnowledgeNote`, `dgk:KnowledgeTag`, `dgk:KnowledgeSession`
9. `dgm:VariableKindValue`, `dgm:VariableScopeValue`, `dgv:DesignStateKindValue`, `dgv:DesignStateParameterTypeValue`, `dgv:ValidationStatusValue`, `dgv:ReinstatementStatusValue`

## Example instances (ABox)

The ontology ships with a representative ABox of named individuals demonstrating each class and binding pattern. Listed below by layer.

### Layer dg — 0. Core / Cross-cutting

#### Type: `dg:Class` (4 individuals)

- **`dg:Class_Building`** — Building
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:Building"
  - `dg:label`: "Building"
  - `dg:project`: "UrbanBlock"
- **`dg:Class_LivingUnit`** — LivingUnit
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:LivingUnit"
  - `dg:label`: "LivingUnit"
  - `dg:project`: "TestA"
- **`dg:Class_Street`** — Street
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:Street"
  - `dg:label`: "Street"
  - `dg:project`: "TestA"
- **`dg:Class_Unit`** — Unit
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:Unit"
  - `dg:label`: "Unit"
  - `dg:project`: "Test Project"

#### Type: `dg:DatatypeProperty` (6 individuals)

- **`dg:DProp_hasHeightM`** — hasHeightM
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:hasHeightM"
  - `dg:project`: "UrbanBlock"
  - `dg:range`: "xsd:decimal"
- **`dg:DProp_hasWidthM`** — hasWidthM
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:hasWidthM"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:decimal"
- **`dg:DProp_hasWindowCount`** — hasWindowCount
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:hasWindowCount"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:integer"
- **`dg:DProp_violatesMaxHeight`** — violatesMaxHeight
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:violatesMaxHeight"
  - `dg:project`: "UrbanBlock"
  - `dg:range`: "xsd:boolean"
- **`dg:DProp_violatesMinWidth`** — violatesMinWidth
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:violatesMinWidth"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:boolean"
- **`dg:DProp_violatesMinWindowCount`** — violatesMinWindowCount
  - `dg:graph`: "OntoGraph"
  - `dg:iri`: "ex:violatesMinWindowCount"
  - `dg:project`: "TestA"
  - `dg:range`: "xsd:boolean"

#### Type: `dg:GraphLayer` (4 individuals)

- **`dg:KnowledgeGraphLayer`** — KnowledgeGraph
  - _Comment:_ Project knowledge storage layer. Contains KnowledgeNote, KnowledgeTag, KnowledgeSession, and KnowledgeClass nodes. Stores architectural knowledge ingested from project documentation or NL prompts.
- **`dg:Metagraph`** — Metagraph
  - _Comment:_ SWRL rule structure layer. Contains Rule, Atom, Variable (Object/Property), Literal, Builtin, and DesignRuleSession nodes. Rules reference OntoGraph entities via REFERS_TO. Per CTRCT-01: exposes Objects, DesignStates, and Runs as first-class outputs.
- **`dg:OntoGraph`** — OntoGraph
  - _Comment:_ Dynamic domain ontology layer. Contains Class, DatatypeProperty, and ObjectProperty nodes generated from user prompts via LLM. These represent the project-specific domain vocabulary (e.g. Building, hasHeightM). Domain classes are NOT part of the system ontology — they are created at runtime.
- **`dg:ValidationGraphLayer`** — ValidationGraph
  - _Comment:_ Validation data flow layer. Contains IntegrationConfig, ValidationRun, ValidationEntity, DesignState (DefState/ObjectState), and DesignStateParameter nodes. Manages the lifecycle from parameter capture through rule evaluation to Speckle publication.

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
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_A3"
  - `dgm:atomIri`: "swrlb:greaterThan"
  - `dgm:atomSwrlLabel`: "greaterThan"
  - `dgm:atomType`: "BuiltinAtom"
  - `dgm:hasArg`: dgm:var_h, dgm:literal_75
  - `dgm:refersTo`: dgm:greaterThan
- **`dgm:R_STREET_MIN_WIDTH_18_V_A3`** — dgm:R_STREET_MIN_WIDTH_18_V_A3
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_A3"
  - `dgm:atomIri`: "swrlb:lessThan"
  - `dgm:atomSwrlLabel`: "lessThan"
  - `dgm:atomType`: "BuiltinAtom"
  - `dgm:refersTo`: dgm:lessThan

#### Type: `dgm:ClassAtom` (2 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_A1`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_A1
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_A1"
  - `dgm:atomIri`: "ex:Building"
  - `dgm:atomSwrlLabel`: "Building"
  - `dgm:atomType`: "ClassAtom"
  - `dgm:hasArg`: dgm:var_b
- **`dgm:R_STREET_MIN_WIDTH_18_V_A1`** — dgm:R_STREET_MIN_WIDTH_18_V_A1
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_A1"
  - `dgm:atomIri`: "ex:Street"
  - `dgm:atomSwrlLabel`: "Street"
  - `dgm:atomType`: "ClassAtom"

#### Type: `dgm:DataPropertyAtom` (4 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_A2`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_A2
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_A2"
  - `dgm:atomIri`: "ex:hasHeightM"
  - `dgm:atomSwrlLabel`: "hasHeightM"
  - `dgm:atomType`: "DataPropertyAtom"
  - `dgm:hasArg`: dgm:var_b, dgm:var_h
- **`dgm:R_BUILDING_MAX_HEIGHT_75_V_H1`** — dgm:R_BUILDING_MAX_HEIGHT_75_V_H1
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:atomId`: "R_BUILDING_MAX_HEIGHT_75_V_H1"
  - `dgm:atomIri`: "ex:violatesMaxHeight"
  - `dgm:atomSwrlLabel`: "violatesMaxHeight"
  - `dgm:atomType`: "DataPropertyAtom"
  - `dgm:hasArg`: dgm:var_b, dgm:literal_true
- **`dgm:R_STREET_MIN_WIDTH_18_V_A2`** — dgm:R_STREET_MIN_WIDTH_18_V_A2
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_A2"
  - `dgm:atomIri`: "ex:hasWidthM"
  - `dgm:atomSwrlLabel`: "hasWidthM"
  - `dgm:atomType`: "DataPropertyAtom"
- **`dgm:R_STREET_MIN_WIDTH_18_V_H1`** — dgm:R_STREET_MIN_WIDTH_18_V_H1
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:atomId`: "R_STREET_MIN_WIDTH_18_V_H1"
  - `dgm:atomIri`: "ex:violatesMinWidth"
  - `dgm:atomSwrlLabel`: "violatesMinWidth"
  - `dgm:atomType`: "DataPropertyAtom"

#### Type: `dgm:DesignRuleSession` (4 individuals)

- **`dgm:drs_4cab136231cf`** — drs-4cab136231cf
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:sessionId`: "drs-4cab136231cf"
  - `dgm:sessionMode`: "ingest"
  - `dgm:sessionPrompt`: "Street minimum width is 15 meters."
- **`dgm:drs_79ba197cc693`** — drs-79ba197cc693
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:sessionId`: "drs-79ba197cc693"
  - `dgm:sessionMode`: "edit"
  - `dgm:sessionPrompt`: "Street minimum width is 18 meters."
- **`dgm:drs_96d1ebd8dc8a`** — drs-96d1ebd8dc8a
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:sessionId`: "drs-96d1ebd8dc8a"
  - `dgm:sessionMode`: "ingest"
  - `dgm:sessionPrompt`: "All building must be maximum 75 meters high"
- **`dgm:drs_ac4c176afeeb`** — drs-ac4c176afeeb
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:sessionId`: "drs-ac4c176afeeb"
  - `dgm:sessionMode`: "query"
  - `dgm:sessionPrompt`: "list all rules"

#### Type: `dgm:Literal` (5 individuals)

- **`dgm:literal_18`** — 18
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:decimal"
  - `dgm:literalLex`: "18"
- **`dgm:literal_2`** — 2
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:integer"
  - `dgm:literalLex`: "2"
- **`dgm:literal_75`** — 75
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:literalDatatype`: "xsd:decimal"
  - `dgm:literalLex`: "75"
- **`dgm:literal_80`** — 80
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:decimal"
  - `dgm:literalLex`: "80"
- **`dgm:literal_true`** — true
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:literalDatatype`: "xsd:boolean"
  - `dgm:literalLex`: "true"

#### Type: `dgm:ObjectVariable` (3 individuals)

- **`dgm:var_b`** — ?b
  - _Comment:_ Object variable representing a Building instance. Inferred from ClassAtom Building(?b). Cross-rule scoped (VTYP-02).
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:variableKind`: dgm:VariableKind_Object
  - `dgm:variableName`: "?b"
  - `dgm:variableScope`: dgm:VariableScope_CrossRule
- **`dgm:var_s`** — ?s
  - _Comment:_ Object variable representing a Street instance. Inferred from ClassAtom Street(?s). Cross-rule scoped (VTYP-02).
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:variableKind`: dgm:VariableKind_Object
  - `dgm:variableName`: "?s"
  - `dgm:variableScope`: dgm:VariableScope_CrossRule
- **`dgm:var_u`** — ?u
  - _Comment:_ Object variable representing a LivingUnit/Unit instance. Inferred from ClassAtom. Cross-rule scoped (VTYP-02).
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:variableKind`: dgm:VariableKind_Object
  - `dgm:variableName`: "?u"
  - `dgm:variableScope`: dgm:VariableScope_CrossRule

#### Type: `dgm:PropertyVariable` (2 individuals)

- **`dgm:var_h`** — ?h
  - _Comment:_ Property variable representing height. Inferred from DataPropertyAtom hasHeightM(?b,?h) arg-2. Rule-scoped (VTYP-03).
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:inferredDatatype`: "xsd:decimal"
  - `dgm:variableKind`: dgm:VariableKind_Property
  - `dgm:variableName`: "?h"
  - `dgm:variableScope`: dgm:VariableScope_RuleLocal
- **`dgm:var_w`** — ?w
  - _Comment:_ Property variable representing width/window count. Inferred from DataPropertyAtom arg-2. Rule-scoped (VTYP-03).
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:variableKind`: dgm:VariableKind_Property
  - `dgm:variableName`: "?w"
  - `dgm:variableScope`: dgm:VariableScope_RuleLocal

#### Type: `dgm:Rule` (5 individuals)

- **`dgm:R_BUILDING_MAX_HEIGHT_75_V`** — R_BUILDING_MAX_HEIGHT_75_V
  - `dg:graph`: "Metagraph"
  - `dg:project`: "UrbanBlock"
  - `dgm:hasBody`: dgm:R_BUILDING_MAX_HEIGHT_75_V_A1, dgm:R_BUILDING_MAX_HEIGHT_75_V_A2, dgm:R_BUILDING_MAX_HEIGHT_75_V_A3
  - `dgm:hasHead`: dgm:R_BUILDING_MAX_HEIGHT_75_V_H1
  - `dgm:ruleId`: "R_BUILDING_MAX_HEIGHT_75_V"
  - `dgm:ruleKind`: "violation"
  - `dgm:ruleText`: "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)"
- **`dgm:R_BUILDING_MAX_HEIGHT_80_V`** — R_BUILDING_MAX_HEIGHT_80_V
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:ruleId`: "R_BUILDING_MAX_HEIGHT_80_V"
  - `dgm:ruleKind`: "violation"
  - `dgm:ruleText`: "Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,80)->violatesMaxHeight(?b,true)"
- **`dgm:R_LIVINGUNIT_MIN_WINDOW_2_V`** — R_LIVINGUNIT_MIN_WINDOW_2_V
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:ruleId`: "R_LIVINGUNIT_MIN_WINDOW_2_V"
  - `dgm:ruleKind`: "violation"
  - `dgm:ruleText`: "LivingUnit(?u)^hasWindowCount(?u,?w)^swrlb:lessThan(?w,2)->violatesMinWindowCount(?u,true)"
- **`dgm:R_STREET_MIN_WIDTH_18_V`** — R_STREET_MIN_WIDTH_18_V
  - `dg:graph`: "Metagraph"
  - `dg:project`: "TestA"
  - `dgm:ruleId`: "R_STREET_MIN_WIDTH_18_V"
  - `dgm:ruleKind`: "violation"
  - `dgm:ruleText`: "Street(?s)^hasWidthM(?s,?w)^swrlb:lessThan(?w,18)->violatesMinWidth(?s,true)"
- **`dgm:R_UNIT_MIN_WINDOW_2_V`** — R_UNIT_MIN_WINDOW_2_V
  - `dg:graph`: "Metagraph"
  - `dg:project`: "Test Project"
  - `dgm:ruleId`: "R_UNIT_MIN_WINDOW_2_V"
  - `dgm:ruleKind`: "violation"
  - `dgm:ruleText`: "Unit(?u)^hasWindowCount(?u,?w)^swrlb:lessThan(?w,2)->violatesMinWindowCount(?u,true)"

#### Type: `dgm:VariableKindValue` (3 individuals)

- **`dgm:VariableKind_Builtin`** — Builtin
  - _Comment:_ Variable bound only inside BuiltinAtom args. Not exposed on the Grasshopper canvas (VTYP-01 step 3).
- **`dgm:VariableKind_Object`** — Object
  - _Comment:_ Variable representing a domain entity instance. Inferred from ClassAtom arg-1 (VTYP-01 step 1). Cross-rule scoped (VTYP-02).
- **`dgm:VariableKind_Property`** — Property
  - _Comment:_ Variable representing a datatype property value. Inferred from DataPropertyAtom arg-2+ (VTYP-01 step 2). Rule-scoped (VTYP-03).

#### Type: `dgm:VariableScopeValue` (2 individuals)

- **`dgm:VariableScope_CrossRule`** — cross-rule
  - _Comment:_ Shared identity across all rules in a project. Applies to Object variables (VTYP-02).
- **`dgm:VariableScope_RuleLocal`** — rule-scoped
  - _Comment:_ Independent variable per rule. Applies to Property variables (VTYP-03).

### Layer dgv — 3. ValidationGraph (validation runs, design state, integration)

#### Type: `dgv:DefState` (1 individual)

- **`dgv:DS_def_h25_w12`** — DefState: height=25, width=12
  - _Comment:_ Parametric capture of a Building configuration. Changes in this DefState regenerate the linked IdRef per CMPST-05.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:hasIdRef`: dgv:IDR_DS_def_h25_w12
  - `dgv:kind`: dgv:DesignStateKind_DefState
  - `dgv:stateId`: "DS_def_h25_w12"

#### Type: `dgv:DesignStateKindValue` (2 individuals)

- **`dgv:DesignStateKind_DefState`** — DefState
  - _Comment:_ Parametric capture snapshot from Grasshopper sliders/toggles. ID prefix: DS_.
- **`dgv:DesignStateKind_ObjectState`** — ObjectState
  - _Comment:_ Object variable to geometry binding snapshot. 1:1 with an ObjectInstance. ID prefix: OS_.

#### Type: `dgv:DesignStateParameterTypeValue` (3 individuals)

- **`dgv:ParameterType_Boolean`** — Boolean
  - _Comment:_ Boolean parameter value. From Boolean Toggles in Grasshopper.
- **`dgv:ParameterType_Integer`** — Integer
  - _Comment:_ Integer parameter value (long). From Integer Sliders in Grasshopper.
- **`dgv:ParameterType_Number`** — Number
  - _Comment:_ Floating-point parameter value (double). From Number Sliders in Grasshopper.

#### Type: `dgv:GeoRef` (2 individuals)

- **`dgv:GR_speckle_xyz1`** — GeoRef: speckle:xyz1
  - _Comment:_ Speckle objectId handle for the primary mass geometry of Building #1.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:geoRefId`: "speckle:obj:xyz1"
- **`dgv:GR_speckle_xyz2`** — GeoRef: speckle:xyz2
  - _Comment:_ Speckle objectId handle for the roof geometry of Building #1.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:geoRefId`: "speckle:obj:xyz2"

#### Type: `dgv:IdRef` (1 individual)

- **`dgv:IDR_DS_def_h25_w12`** — IdRef for DS_def_h25_w12
  - _Comment:_ Auto-generated identifier for DefState DS_def_h25_w12 (CMPST-08). Resolves to OI_Building_b1 for cross-run tracking (INTG-03). Will regenerate if any slider value in the DefState changes.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:idRefValue`: "IDR_a1b2c3d4e5f6"
  - `dgv:resolvesTo`: dgv:OI_Building_b1

#### Type: `dgv:IntegrationConfig` (1 individual)

- **`dgv:SpeckleIntegration_TestA`** — Speckle Integration (TestA)
  - _Comment:_ Integration config from Neo4j ValidationGraph. Connects project TestA to Speckle for 3D validation overlay.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:baseModelId`: "4c546c0771"
  - `dgv:provider`: "Speckle"
  - `dgv:speckleProjectId`: "44088eefc6"
  - `dgv:validationModelId`: "a6d1e0c5da"

#### Type: `dgv:ObjectInstance` (1 individual)

- **`dgv:OI_Building_b1`** — ObjectInstance: Building #1
  - _Comment:_ Cross-rule identity for the first Building in the TestA model. Bound to Object variable ?b via its ObjectState.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:hasObjectState`: dgv:OS_b1_var_b
  - `dgv:instanceId`: "OI_Building_b1"

#### Type: `dgv:ObjectState` (1 individual)

- **`dgv:OS_b1_var_b`** — ObjectState: OI_Building_b1 ↔ ?b
  - _Comment:_ Binding snapshot pairing OI_Building_b1 with Object variable ?b (var_b) and its current GeoRef set. State_Id computed as OS_<SHA256(projectId + objectInstanceId + variableName)> per CMPST-07.
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:hasGeoRef`: dgv:GR_speckle_xyz1, dgv:GR_speckle_xyz2
  - `dgv:hasObjectVariable`: dgm:var_b
  - `dgv:kind`: dgv:DesignStateKind_ObjectState
  - `dgv:objectRef`: "rhino-guid-9f3e2a"
  - `dgv:representsInstance`: dgv:OI_Building_b1
  - `dgv:stateId`: "OS_a1b2c3d4"

#### Type: `dgv:ReinstatementStatusValue` (7 individuals)

- **`dgv:ReinstatementStatus_AmbiguousTarget`** — AmbiguousTarget
  - _Comment:_ Multiple matching sliders/toggles found — cannot determine which to reinstate.
- **`dgv:ReinstatementStatus_Applied`** — Applied
  - _Comment:_ Parameter value was successfully applied to the target slider/toggle.
- **`dgv:ReinstatementStatus_MissingTarget`** — MissingTarget
  - _Comment:_ No matching slider/toggle found on the canvas for this parameter.
- **`dgv:ReinstatementStatus_OutOfRange`** — OutOfRange
  - _Comment:_ Parameter value exceeds the target slider's min/max range.
- **`dgv:ReinstatementStatus_TypeMismatch`** — TypeMismatch
  - _Comment:_ Target slider type does not match parameter type (e.g. Number param wired to Integer slider).
- **`dgv:ReinstatementStatus_Unchanged`** — Unchanged
  - _Comment:_ Target slider already has the requested value — no change needed.
- **`dgv:ReinstatementStatus_WouldApply`** — WouldApply
  - _Comment:_ Dry-run mode — parameter would be applied if reinstatement were executed.

#### Type: `dgv:ValidationEntity` (2 individuals)

- **`dgv:VEntity_a5671cb1bd30_b1_height`** — Entity: Building #1 height check (passed)
  - _Comment:_ Per-rule, per-instance validation result cell. Records that Building #1 passed R_BUILDING_MAX_HEIGHT_75_V with a measured height value of 25 (the propValue — SCHM-05). Belongs to run a5671cb1bd30.
  - `dg:graph`: "ValidationGraph"
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
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:dgEntityId`: "VE_a5671cb1bd30_b1_overflow"
  - `dgv:displayName`: "Building #1"
  - `dgv:propValue`: "80"
  - `dgv:propValueOf`: dgm:var_h
  - `dgv:ruleId`: "R_BUILDING_MAX_HEIGHT_75_V"
  - `dgv:status`: dgv:Status_Failed
  - `dgv:validatesInstance`: dgv:OI_Building_b1

#### Type: `dgv:ValidationRun` (5 individuals)

- **`dgv:VRun_27b121d78c73`** — Validation Run 27b121d78c73
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:runId`: "27b121d78c73"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_63ffbff1f928`** — Validation Run 63ffbff1f928
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:runId`: "63ffbff1f928"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_a5671cb1bd30`** — Validation Run a5671cb1bd30
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:runId`: "a5671cb1bd30"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_ac0d62f1332c`** — Validation Run ac0d62f1332c
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:runId`: "ac0d62f1332c"
  - `dgv:status`: dgv:Status_Completed
- **`dgv:VRun_f8678448d4e7`** — Validation Run f8678448d4e7
  - `dg:graph`: "ValidationGraph"
  - `dg:project`: "TestA"
  - `dgv:runId`: "f8678448d4e7"
  - `dgv:status`: dgv:Status_Completed

#### Type: `dgv:ValidationStatusValue` (3 individuals)

- **`dgv:Status_Completed`** — completed
  - _Comment:_ Validation run finished successfully.
- **`dgv:Status_Failed`** — failed
  - _Comment:_ Validation entity failed one or more rules — violations detected.
- **`dgv:Status_Passed`** — passed
  - _Comment:_ Validation entity passed all rules — no violations detected.

### Layer dgk — 4. KnowledgeGraph (project notes, tags, sessions)

#### Type: `dgk:KnowledgeClass` (2 individuals)

- **`dgk:KC_KnowledgeNote`** — KnowledgeNote
  - _Comment:_ Hub node for knowledge notes. Neo4j KnowledgeGraph, project: UrbanBlock.
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
- **`dgk:KC_KnowledgeSession`** — KnowledgeSession
  - _Comment:_ Hub node for knowledge sessions. Neo4j KnowledgeGraph, project: UrbanBlock.
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"

#### Type: `dgk:KnowledgeNote` (10 individuals)

- **`dgk:Note_BIG_Architects`** — BIG Architects
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:taggedWith`: dgk:Tag_architects, dgk:Tag_studio
  - `dgk:tags`: "architects,studio"
  - `dgk:title`: "BIG Architects"
- **`dgk:Note_BuildingAddress`** — Building Address
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:taggedWith`: dgk:Tag_portugal, dgk:Tag_guimaraes, dgk:Tag_rua_do_avelino_germano
  - `dgk:tags`: "portugal,guimaraes,rua-d0-avelino-germano"
  - `dgk:title`: "Building Address"
- **`dgk:Note_BuildingHeightRegulations`** — Building Height Regulations
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:title`: "Building Height Regulations"
- **`dgk:Note_BuildingStaircaseCount`** — Building Staircase Count
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:taggedWith`: dgk:Tag_building, dgk:Tag_staircase
  - `dgk:tags`: "building,staircase"
  - `dgk:title`: "Building Staircase Count"
- **`dgk:Note_GreenAreaRatio`** — Green Area Ratio
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:title`: "Green Area Ratio"
- **`dgk:Note_MaxFloorToFloorHeightZoneA`** — Maximum floor-to-floor height Zone A
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
  - `dgk:taggedWith`: dgk:Tag_height, dgk:Tag_residential, dgk:Tag_zone_a, dgk:Tag_compliance
  - `dgk:tags`: "height,residential,zone-a,compliance"
  - `dgk:title`: "Maximum floor-to-floor height Zone A"
- **`dgk:Note_ParkingCapacity`** — Parking Capacity
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:taggedWith`: dgk:Tag_parking, dgk:Tag_capacity
  - `dgk:tags`: "parking,capacity"
  - `dgk:title`: "Parking Capacity"
- **`dgk:Note_ProjectLocation`** — Project Location
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:taggedWith`: dgk:Tag_guimaraes, dgk:Tag_braga, dgk:Tag_portugal
  - `dgk:tags`: "guimaraes,braga,portugal"
  - `dgk:title`: "Project Location"
- **`dgk:Note_SetbackRequirements`** — Setback Requirements
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:title`: "Setback Requirements"
- **`dgk:Note_TestUpdateNote`** — Test Update Note
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "test-update-flow"
  - `dgk:title`: "Test Update Note"

#### Type: `dgk:KnowledgeSession` (5 individuals)

- **`dgk:Session_ks_1d599d7a40a1`** — Update session
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:knowledgeSessionId`: "ks-1d599d7a40a1"
  - `dgk:mode`: "update"
- **`dgk:Session_ks_mnoom0r3`** — Insert: Parking is 300 slots
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:knowledgeSessionId`: "ks-mnoom0r3"
  - `dgk:mode`: "insert"
- **`dgk:Session_ks_mnoon96l`** — Insert: building has 3 staircases
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:knowledgeSessionId`: "ks-mnoon96l"
  - `dgk:mode`: "insert"
- **`dgk:Session_ks_mnp1jw35`** — Insert: Address of the building is Portugal, Guimaraes...
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:knowledgeSessionId`: "ks-mnp1jw35"
  - `dgk:mode`: "insert"
- **`dgk:Session_ks_mnq4ixld`** — Query: Where buidling is located
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:knowledgeSessionId`: "ks-mnq4ixld"
  - `dgk:mode`: "query"

#### Type: `dgk:KnowledgeTag` (18 individuals)

- **`dgk:Tag_architects`** — dgk:Tag_architects
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "architects"
- **`dgk:Tag_braga`** — dgk:Tag_braga
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "braga"
- **`dgk:Tag_building`** — dgk:Tag_building
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "building"
- **`dgk:Tag_capacity`** — dgk:Tag_capacity
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "capacity"
- **`dgk:Tag_compliance`** — dgk:Tag_compliance
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
  - `dgk:tagName`: "compliance"
- **`dgk:Tag_corridor`** — dgk:Tag_corridor
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "test-phase03"
  - `dgk:tagName`: "corridor"
- **`dgk:Tag_evacuation`** — dgk:Tag_evacuation
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "test-phase03"
  - `dgk:tagName`: "evacuation"
- **`dgk:Tag_guimaraes`** — dgk:Tag_guimaraes
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "guimaraes"
- **`dgk:Tag_height`** — dgk:Tag_height
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
  - `dgk:tagName`: "height"
- **`dgk:Tag_parking`** — dgk:Tag_parking
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "parking"
- **`dgk:Tag_portugal`** — dgk:Tag_portugal
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "portugal"
- **`dgk:Tag_residential`** — dgk:Tag_residential
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
  - `dgk:tagName`: "residential"
- **`dgk:Tag_rua_do_avelino_germano`** — dgk:Tag_rua_do_avelino_germano
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "rua-d0-avelino-germano"
- **`dgk:Tag_staircase`** — dgk:Tag_staircase
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "staircase"
- **`dgk:Tag_studio`** — dgk:Tag_studio
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "TestA"
  - `dgk:tagName`: "studio"
- **`dgk:Tag_width`** — dgk:Tag_width
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "test-phase03"
  - `dgk:tagName`: "width"
- **`dgk:Tag_zone_a`** — dgk:Tag_zone_a
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
  - `dgk:tagName`: "zone-a"
- **`dgk:Tag_zone_b`** — dgk:Tag_zone_b
  - `dg:graph`: "KnowledgeGraph"
  - `dg:project`: "UrbanBlock"
  - `dgk:tagName`: "zone-b"

## Namespace reference

```
dg   = http://example.org/design-grammar#
dgm  = http://example.org/design-grammar/metagraph#
dgv  = http://example.org/design-grammar/validation#
dgk  = http://example.org/design-grammar/knowledge#
owl  = http://www.w3.org/2002/07/owl#
rdf  = http://www.w3.org/1999/02/22-rdf-syntax-ns#
rdfs = http://www.w3.org/2000/01/rdf-schema#
xsd  = http://www.w3.org/2001/XMLSchema#
```

---

*Auto-generated from `[DesignGrammar.owl](DesignGrammar.owl)` v3.1. Counts: 37 classes, 21 object properties, 56 datatype properties, 116 named individuals, 9 disjointness axioms.*