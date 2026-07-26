---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

+#### Modeling the semantic ontology of design criteria

- Semantic Criteria may not only represent a consensus concerning the design context, but also the ==epistemology for how to interpret the design context==, and require further validation in order to avoid contradictions.
- Semantic ontology is a knowledge representation technique used in artificial intelligence to develop semantic webs[1], which can enable search engines to understand users’ intentions.
- since architectural design must consider ==various criteria based on heterogeneous information==, developing a complete ontology for architectural design needs extremely complicated and laborious works.
- Design information in BIM consists of three types, which are ==semantic, topological, and geometric==[7], architectural design can be regarded as the conversion and processing of these three types of design information.
- ==A modular approach== therefore was proposed to allow a flexible integration of the various design information
- the complexity of detecting simple topologies, such as separated, adjacent, overlapping, and enclosing, will increase linearly with the number of relevantelements, let alone the case of other complex topologies involving multiple objects, such as surrounding, centralizing, clustering, and branching
- By employing algorithmic components in Grasshopper, simple topologies between two geometries are more easily detected than before. However, as composing algorithms within Grasshopper is usually too complex to be easily recognized by most architects, ==composing complex or multiple algorithms within a single topological class== is usually more convenient for most users.
- DCM first attempts to model invisible or non-obvious design criteria, such as minimum space requirements, view fields of openings, and geometric constraints of the building codes on design objects, rather than automatically generating optimal or possible solutions. In the “Buildable Area” example mentioned above, the visualization of “UnbuildableArea” and the implementation of “minus” topology is more important than the generated shape of “Buildable Area” when communicating design criteria with others.
- it is inevitable that conflicts will occur among different design criteria. There are two tactics for solving the conflicting criteria: (1) first rank the importance of the design criteria, then apply design criteria in the order of importance; and (2) search for more criteria which can meet all requirements of the conflicting criteria. The second tactic usually is more satisfactory than the first.
- semantic reasoner of ==SWRL==
- However, as the generative algorithms in Grasshopper become more complex, even experienced architects may have ==difficulty remembering why a specific algorithm has a certain composition==, much less be able to explain or communicate their ideas with others.
- how to represent and validate proposed criteria, especially those that are invisible or non-obvious in 3D models, and to communicate ideas involving those criteria with other stakeholders and disciplines at an early stage, is still a critical issue for architectural design