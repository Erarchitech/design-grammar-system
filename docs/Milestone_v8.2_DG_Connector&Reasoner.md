# Architecture   
Create new milestone v8.2. Follow new phase numbering convention, so phases of this milestone start from 820:  
- [ ] Change inputs for “Connector” component of DG addin according to new credentials mechanism and setup in Design Grammars platform. Credentials are created in the platform as a key for accessing it from Grasshopper and become inputs for Connector component  
- [ ] Integrate reasoners to enhance validation features of Design Grammars platform.  
- [ ] For DG ontology specifically: HermiT or Pellet are the most suitable for full OWL 2 DL expressiveness. HermiT reports no warnings on standard ontologies, while ELK produces “multiple incompleteness warnings” when the ontology exceeds OWL 2 EL. Since design grammars involve complex role chains, cardinality constraints, and property restrictions (e.g., “a room must have exactly one fire exit”), we need OWL 2 DL, not EL.  
- [ ] For Design Grammars, a two-layer approach is the state of the art in BIM/AEC semantic validation:  
- [ ] Layer 1 — OWL 2 DL Reasoner (HermiT or Pellet)   
Used for ontology-level consistency: class satisfiability, property domain/range coherence, TBox integrity. Run this at design grammar authoring time, not at every design state update. Pellet’s incremental reasoning is useful here if your DG ontology evolves iteratively.   
- [ ] Layer 2 — SHACL (Shapes Constraint Language)   
Used for data-level instance validation against design rules. SHACL operates under CWA by default, making it semantically aligned with design rule enforcement. The W3C SHACL + ifcOWL combination is now proven in BIM compliance checking. SHACL shapes map directly to your “design rule” concept in DG: each shape is a formal design constraint (minimum clearances, required properties, cardinality rules, spatial topology).  
- [ ] Bridging Layer — SPARQL + SHACL-AF (Advanced Features)   
SHACL-SPARQL allows embedding SPARQL queries inside shapes, enabling graph-traversal rules that neither pure OWL nor basic SHACL can express. This is critical for DG’s design intent rules involving multi-hop relationships (e.g., “all rooms connected to a corridor must have a ceiling height ≥ room height – 0.3m”).  
  
- [ ] Practical Recommendation for DG Platform   
Given DG cross-platform architecture (web platform + connectors for authoring tools), the proposed stack is:  
1. Apache Jena as the base triple store and SPARQL endpoint — open-source, Java-based, supports both SHACL (via TopBraid SHACL API or Jena-SHACL) and OWL reasoning via integration[springer]  
2. HermiT via OWL API for ontology consistency during grammar authoring/rule ingestion in the web platform  
3. TopBraid SHACL or pySHACL for design state validation in the connector layer — pySHACL is Python-native, ideal for lightweight connector agents  
4. ELK as optional fast pre-classifier for large project ontologies when full DL completeness is not required   
5. The SBIM-Reasoner approach from AEC research confirms that semantic technologies combining OWL + SHACL are the most effective for IFC-level design verification, directly applicable to my DG connector for BIM authoring tools.  
