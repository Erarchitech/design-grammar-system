# Port -> V7 IRI Map

**Successor of `GH-mapping.png`.** GH-mapping.png (and its shortcut `.lnk`) is a raster image of the v2.0 canvas and is not machine-greppable — this file replaces it as the authoritative, greppable component-port -> ontology-IRI contract for the v7.0 addin rebuild.

**Source of truth for ports:** `ontology/GH_DesignGrammars.pdf` (the 14-component GH_DesignGrammars schema — every component box, port, and inline `Ontology: DG.Layer....` annotation on the diagram).
**Source of truth for IRI names:** `ontology/V7-INVESTIGATION.md` (locked V6->V7 rename table + conflict resolutions (a)/(b)/(c)), materialized in `ontology/DesignGrammar-V7.owl`.

**Ontology <-> DB note (per PROJECT.md):** the Neo4j runtime DB keeps its existing labels except `Knowledge*`->`Spec*` (no wider label migration) — see PROJECT.md "DB keeps existing Neo4j labels except Knowledge*->Spec*". Where a port's value is a runtime-only construct (a Neo4j driver handle, a credential, a Boolean UI trigger, or a v2.0 VALIDATOR publish extra never in the PDF schema) there is **no ontology IRI** for it by design — that gap is documented, not enforced, per that same decision. Such rows are marked `Runtime` in the Layer column and annotated in Notes; they are not "unmapped" in the ROADMAP SC3 sense, they are intentionally outside ontology scope.

This file is consumed by Phase 14 (schema propagation), Phase 17 (graph-access components), and Phase 18 (validator rework) to wire component ports to the correct ontology IRIs.

## Master table

| Component | Port | Direction | V7 IRI | Layer | Notes |
|---|---|---|---|---|---|
| CONNECTOR | Neo4jURI | in | — (runtime credential) | Runtime | runtime/DB — no ontology IRI (Bolt connection string) |
| CONNECTOR | Neo4jUser | in | — (runtime credential) | Runtime | runtime/DB — no ontology IRI |
| CONNECTOR | Neo4jPassword | in | — (runtime credential) | Runtime | runtime/DB — no ontology IRI |
| CONNECTOR | PROJECT NAME | in | dg:project | Core (annotation) | `dg:project` is an `owl:AnnotationProperty`; matches the runtime `project` property present on every Neo4j node (PROJECT.md: "Single Neo4j DB with project isolation") |
| CONNECTOR | Database | out | — (Neo4j driver handle) | Runtime | runtime/DB — no ontology IRI (Bolt driver session handle, not an ontology entity) |
| CONNECTOR | Project | out | dg:project | Core (annotation) | passthrough of PROJECT NAME; scopes every downstream Cypher query issued by GRAPH DECONSTRUCT and its children |
| GRAPH DECONSTRUCT | Database | in | — (Neo4j driver handle) | Runtime | runtime/DB — no ontology IRI |
| GRAPH DECONSTRUCT | Metagraph | out | dgm:Metagraph | Metagraph | `DG.Layer.Metagraph; Output=Metagraph()`. `Metagraph` is NOT renamed in V7 (locked rename table) |
| GRAPH DECONSTRUCT | Ontograph | out | dg:Ontograph | Ontograph | `DG.Layer.Ontograph; Output=Ontograph()`. Renamed from `OntoGraph` (casing only) |
| GRAPH DECONSTRUCT | ValidGraph | out | dgv:Validgraph | Validgraph | `DG.Layer.Validgraph; Output=Validgraph()`. Renamed from `ValidationGraph`. PDF wire/port label is `ValidGraph`; the ontology class name is cased `Validgraph` — same entity, per locked rename table |
| GRAPH DECONSTRUCT | SpecGraph | out | dgs:SpecGraph | Specgraph | `DG.Layer.Specgraph; Output=Specgraph()`. `SpecGraph` is NOT renamed in V7 (locked rename table). Runtime `KnowledgeGraph`->`SpecGraph` rename (data-service/n8n/NeoVis/DB labels) is separate v7.0 scope, not this plan |
| METAGRAPH | Metagraph | in | dgm:Metagraph | Metagraph | handle in, from GRAPH DECONSTRUCT |
| METAGRAPH | Rules | out | dgm:Rule | Metagraph | `DG.Layer.Metagraph.Rule; Output=list(Rule())` |
| METAGRAPH | Objects | out | dg:Object | Core | `GenClass(DG.Core.Object); Output=list(GenClass())`. GenClass = LLM-generated subclass of a parent class (PDF note); base ontology class is `dg:Object` |
| ONTOGRAPH | Ontograph | in | dg:Ontograph | Ontograph | handle in, from GRAPH DECONSTRUCT |
| ONTOGRAPH | Class | out | dg:Class | Ontograph | `DG.Layer.Ontograph.Class; Output=list(class GenClass(Class))`. Base OntoGraph reification class is `dg:Class` |
| ONTOGRAPH | ObjProperties | out | dg:ObjProperty | Ontograph | `DG.Layer.Ontograph.ObjProperty; Output=list(GenClass.ObjProperty) Datatype: Property`. Renamed from `ObjectProperty` (the OntoGraph reification class — not the `owl:ObjectProperty` OWL 2 language construct, which is untouched) |
| ONTOGRAPH | DataProperties | out | dg:DataProperty | Ontograph | `DG.Layer.Ontograph.DataProperty; Output=list(GenClass.DataProperty) Datatype: Property`. Renamed from `DatatypeProperty` (reification class, not the `owl:DatatypeProperty` construct) |
| VALIDATION GRAPH | ValidGraph | in | dgv:Validgraph | Validgraph | handle in, from GRAPH DECONSTRUCT |
| VALIDATION GRAPH | Run | out | dgv:Run | Validgraph | `DG.Layer.Validgraph.Run; Output=list(Run())`. Renamed from `ValidationRun` |
| VALIDATION GRAPH | Status | out | dgv:ValidStatus | Validgraph | PDF names this port `Status` (`Output=list(Run().Status) Datatype: text`). Per V7-INVESTIGATION.md conflict (a): unified with VALIDATOR's `ValidStatus` — this is a read-back of the same `Run.ValidStatus` per-ObjState Boolean list (index-matched to ObjState order), not a separate text enum |
| VALIDATION GRAPH | DesignState | out | dg:DesignState | Core (stored in Validgraph) | `DG.Core.DesignState; Output=list(DesignState())`. Per conflict (b) D-01: DesignState is stored with `graph='ValidGraph'` (corrected from `cypher_template.txt` v3's `graph='Metagraph'`) — this component reads it off the ValidGraph handle, matching the PDF wiring |
| OBJECT STATE | Object | in | dg:Object | Core | `GenClass(DG.Core.Object); Output=list(GenClass())` |
| OBJECT STATE | Geometry | in | dg:Geometry | Computgraph | `GenClass(DG.Core.Structure.Geometry); Output=list(GenClass())` |
| OBJECT STATE | Label | in | dgv:objectRefName | Validgraph | User-supplied ObjectRef string (PROJECT.md: "ObjectRef is user-supplied string, not geometry-hash — geometry regenerates on every GH solve"). Wired via `dg:objectRef` (ObjectProperty, ObjState->Object); `dgv:objectRefName` is the string-handle datatype property |
| OBJECT STATE | ObjState | out | dg:ObjState | Core | `DG.Core.DesignState.ObjState; Output=list(ObjState())`. Renamed from `ObjectState` |
| PARAMETER STATE | Parameters | in | dgc:Parameter | Computgraph | `DG.Layer.Computgraph.Parameter; Output=list(Parameter())` (Input Parameters List) |
| PARAMETER STATE | ParamState | out | dg:ParamState | Core | `DG.Core.DesignState.ParamState; Output=list(ParamState())`. Renamed from `DefState`. Successor of the v2.0 DESIGN STATE capture role |
| PROPERTY STATE | Rule | in | dgm:Rule | Metagraph | rule under evaluation for this property capture |
| PROPERTY STATE | DataProperty | in | dg:DataProperty | Ontograph | reification class for the property being captured |
| PROPERTY STATE | PropValue | in | dgv:propValue | Validgraph | Calculated Values. Existing datatype property that already attaches per-instance validation-result values (V7-INVESTIGATION.md: PropState is "built on the existing `dgv:propValue`/`dgv:propValueOf` datatype/object properties") |
| PROPERTY STATE | PropState | out | dg:PropState | Core | `DG.Core.DesignState.PropState; Output=list(PropState())`. NEW in V7 (no V6 source); composes Rule + DataProperty + PropValue (ONTO-03/GHST-03) |
| DESIGN STATE | ObjState | in | dg:ObjState | Core | composed input; can accept many individuals (PDF note) |
| DESIGN STATE | ParamState | in | dg:ParamState | Core | composed input; can accept many individuals |
| DESIGN STATE | PropState | in | dg:PropState | Core | composed input; can accept many individuals |
| DESIGN STATE | DesignState | out | dg:DesignState | Core | `DG.Core.DesignState; Output=list(DesignState())`. Per conflict (b): stored with `graph='ValidGraph'` (D-01), written only by VALIDATOR on publish (D-03), `MERGE`'d by StateId+project (dedup), no orphan DesignStates — always has >=1 linked Run (D-05) |
| DESIGN STATE DECONSTRUCT | DesignState | in | dg:DesignState | Core | handle in |
| DESIGN STATE DECONSTRUCT | ObjState | out | dg:ObjState | Core | `DG.Core.DesignState.ObjState; Output=list(ObjState())` |
| DESIGN STATE DECONSTRUCT | ParamState | out | dg:ParamState | Core | `DG.Core.DesignState.ParamState; Output=list(ParamState())` |
| DESIGN STATE DECONSTRUCT | PropState | out | dg:PropState | Core | `DG.Core.DesignState.PropState; Output=list(PropState())` |
| OBJECT DECONSTRUCT | ObjState | in | dg:ObjState | Core | handle in |
| OBJECT DECONSTRUCT | Object | out | dg:Object | Core | `GenClass(DG.Core.Object); Output=list(GenClass())` |
| OBJECT DECONSTRUCT | Geometry | out | dg:Geometry | Computgraph | `GenClass(DG.Core.Structure.Geometry); Output=list(GenClass())` |
| OBJECT DECONSTRUCT | Label | out | dgv:objectRefName | Validgraph | `DG.Core.Structure.Geometry.Label; Output=Geometry().Label` per PDF wording. No dedicated `Geometry.Label` datatype property exists in `DesignGrammar-V7.owl` — `dgv:objectRefName` (the user-supplied ObjectRef string, PROJECT.md) is the closest existing IRI covering this role; same mapping as OBJECT STATE's `Label` input |
| PARAMETER REINSTATE | ParamState | in | dg:ParamState | Core | handle in |
| PARAMETER REINSTATE | Reinstate | in | — (Boolean trigger) | Runtime | runtime/DB — no ontology IRI (rising-edge Boolean trigger; PROJECT.md: "prevents auto-apply on wire change") |
| PARAMETER REINSTATE | Parameters | out | dgc:Parameter | Computgraph | `DG.Layer.Computgraph.Parameter; Output=list(Parameter())` |
| PARAMETER REINSTATE | StateStatus | out | dgv:ReStatusValue | Validgraph | `DG.Layer.Validgraph.ReStatus; Output=list(ReStatus())`. Class IRI is `dgv:ReStatusValue` with `rdfs:label "ReStatus"` (matches the PDF's ontology-path display name); renamed from `ReinstatementStatus(Value)`. 7 individuals: `dgv:ReStatus_Applied/MissingTarget/TypeMismatch/AmbiguousTarget/OutOfRange/Unchanged/WouldApply` |
| RULE DECONSTRUCT | Rule | in | dgm:Rule | Metagraph | handle in |
| RULE DECONSTRUCT | Objects | out | dg:Object | Core | `GenClass(DG.Core.Object)`. Objects partition of the Rule's SWRL variables (VariableTypeInferrer priority-chain: Object wins over Property) |
| RULE DECONSTRUCT | DataProperties | out | dg:DataProperty | Ontograph | DataProperties partition of the Rule's SWRL variables |
| RULE DECONSTRUCT | Rule | out | dgm:Rule | Metagraph | passthrough of the input Rule, for downstream VALIDATOR wiring |
| RULE DECONSTRUCT | SWRL | out | dgm:SWRL | Metagraph | `DG.Layer.Metagraph.SWRL; Output=Rule().SWRL Datatype: text`. Renamed from `ruleText` |
| RULE DECONSTRUCT | RuleName | out | dgm:RuleName | Metagraph | `DG.Layer.Metagraph.RuleName; Output=Rule().RuleName`. Renamed from `ruleTitle` |
| RULE DECONSTRUCT | RuleDescription | out | dgm:RuleDescription | Metagraph | `DG.Layer.Metagraph.RuleDescription; Output=Rule().Description`. NEW in V7 (no V6 source) |
| VALIDATOR | Rule | in | dgm:Rule | Metagraph | handle in |
| VALIDATOR | DesignState | in | dg:DesignState | Core | composed DesignState; binds Object/Property variables directly (CLASSIFICATOR eliminated in v7.0 — see PROJECT.md) |
| VALIDATOR | SendValid | in | — (Boolean trigger) | Runtime | runtime/DB — no ontology IRI (publish-to-Speckle/data-service trigger) |
| VALIDATOR | Run | out | dgv:Run | Validgraph | new/updated Run on publish |
| VALIDATOR | ValidStatus | out | dgv:ValidStatus | Validgraph | `DG.Layer.Validgraph.ValidStatus; Output=Run().ValidStatus Datatype: Boolean`. Per conflict (a) D-06: a per-ObjState Boolean list, index-matched to the DesignState's ObjState order — overall pass = `AND(ValidStatus)`, derived at read time, not stored |
| VALIDATOR | RuleName | out | dgm:RuleName | Metagraph | passthrough from the bound Rule |
| VALIDATOR | RuleDescription | out | dgm:RuleDescription | Metagraph | passthrough from the bound Rule |
| VALIDATOR | SendStatus | out | dgv:SendStatus | Validgraph | `DG.Layer.Validgraph.SendStatus; Output=Run().SendStatus Datatype: Boolean`. Single Boolean per Run (D-08); `true` when `SendValid=true` and the Speckle/data-service publish succeeds |
| VALIDATOR | DataServiceUrl | out | — (runtime publish param) | Runtime | Non-overlapping extra kept from the v2.0 VALIDATOR (PROJECT.md: "Component ports: update where overlapping with the new schema, keep where no overlap"). Not in the PDF schema — no ontology IRI |
| VALIDATOR | Report | out | — (runtime publish param) | Runtime | Non-overlapping extra kept from the v2.0 VALIDATOR; not in the PDF schema — no ontology IRI |
| VALIDATOR | ValidationRunId | out | — (runtime publish param) | Runtime | Non-overlapping extra kept from the v2.0 VALIDATOR; not in the PDF schema — no ontology IRI |

## Resolution check

Every ontology-IRI cell in the master table above was verified against `ontology/DesignGrammar-V7.owl` by grepping its local name in an `rdf:about="&prefix;LocalName"` position.

**25 distinct ontology IRIs referenced — all 25 resolved** (each returns >=1 match in `DesignGrammar-V7.owl`):

`dg:project`, `dg:Ontograph`, `dgm:Metagraph`, `dgv:Validgraph`, `dgs:SpecGraph`, `dgm:Rule`, `dg:Object`, `dg:Class`, `dg:ObjProperty`, `dg:DataProperty`, `dgv:Run`, `dgv:ValidStatus`, `dg:DesignState`, `dg:Geometry`, `dgv:objectRefName`, `dg:ObjState`, `dgc:Parameter`, `dg:ParamState`, `dgv:propValue`, `dg:PropState`, `dgv:ReStatusValue`, `dgm:SWRL`, `dgm:RuleName`, `dgm:RuleDescription`, `dgv:SendStatus`.

One correction made during this check: the PDF's `DG.Layer.Validgraph.ReStatus` ontology path and the locked rename table's "`ReStatus` (class label)" both name the *display label*, not the OWL IRI — the actual resolvable class IRI is `dgv:ReStatusValue` (`rdfs:label` = `"ReStatus"`). The master table's PARAMETER REINSTATE `StateStatus` row uses `dgv:ReStatusValue`, the real IRI, with a note cross-referencing the PDF's display name — this is not a 13-02 gap, both names coexist by design (IRI vs. label).

**10 runtime/DB ports annotated** (no ontology IRI, by design — see the ontology<->DB note in the header): CONNECTOR `Neo4jURI`/`Neo4jUser`/`Neo4jPassword` (in) and `Database` (out); GRAPH DECONSTRUCT `Database` (in); PARAMETER REINSTATE `Reinstate` (in); VALIDATOR `SendValid` (in) and `DataServiceUrl`/`Report`/`ValidationRunId` (out).

**Zero unmapped references** — every output port of all 14 components, and every IRI-carrying input, resolves to either a verified ontology IRI or an explicitly annotated runtime/DB construct. This satisfies ROADMAP Phase 13 success criterion 3 and ONTO-06.
