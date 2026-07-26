---
type: keyword-index
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

#### - [[10000_General Problem Statement]]:
- [[101113_MSAS_SpatialAssisstance.pdf]]:
	- building semantic maps
	- Spatial Assistance System (SAS)
		Computational embodiment of spatial decision-making and analytical abilities that otherwise typically require extensive domain-specific training, knowledge, and expertise.
	- Qualitative Spatio-Temporal Representation and Reasoning (QSTRR)
	- Multi-Modal Data Access for Spatial Assistance Systems
	- Conceptualization
		- 6DSLAM
	- Delaunay triangulation Algorithm
		nput: image {projected cloud of points onto plane}
		Output: set of triangles
		1. Find contours
		2. Simplify found contours {converting them to polygons-approximate contour with accuracy proportional to the contour perimeter}
		3. Run Delaunay triangulation on the vertices of extracted contours
		4. Eliminate edges and faces that are not covering projected points
		5. Extract triangles from remaining edges and faces
	- MSAI (Mobile Spatial Assistive Intelligence)
- [[9000_101314_Multi-disciplinary collaborative building design]]:
	- interdisciplinary variable (IV)
	- Types of input ==interdisciplinary variables:==
		- Shared variables
		- Coupling variables (Associated)
		- Local variables
	- Pareto rank and crowding distance
	- genetic operators
	- offspring
		The genetic operators define the new individuals, called ‘offspring’, for the next generation. This starts by selecting two individuals at randomin the current generation and then choosing the one with the lowest Pareto rank or the highest crowding distance.
	- ==Multi-agent system (MAS)==
	- MDO (Multi-disciplinary Optimisation)
	- Domain Agents
	- Interface/architectural agent (IAA)
	- Specialist agents (SDA (Structural Design Agent), BSA, etc)
	- Negotiation protocol
	- information and communication technology (ICT)
	- ICT approaches:
		- Central database
		- Web-based
		- Agent-based
- [[111204_Rule-Checking and Semantic Enrichment of Graph-Based Bim Data.pdf]]:
	- RDF-based graph structure
	- ==Semantic Enrichment==
	- Schema-agnostic approach
	- Tokenizing
	- Building Data Preparation
	- ifcOWL Ontology language
	- Creating BCF
- [[9000_103117_Cloud-based Collaboration]]
	- CBIM metagraph
- Datascape
- J.P Cullen & Sons; 2008
	- Integrated Project Delivery (IPD)
#### [[20000_Data-Driven Design Systems]]:

- [[9000_205514_Swiftlet_Webinar]]
	- serialization - serializing trained ML model - is like packaging the program for end-user running


#### [[30000_Generative Design]]:

- Biomimicry and Swarm Intelligence [[30000_Generative Design]]
	Agent-based design often draws inspiration from natural systems, like ant colonies, flocking birds, or cellular growth. By simulating similar interactions, architects can generate biomimetic forms and systems.
- Diffusion Model [[30000_Generative Design]]
- Evolutionary algorithm (Non-dominated Sorting Genetic Algorithm II - NSGA-II) [[30000_Generative Design]]
- Finite Element Analysis (FEA) [[30000_Generative Design]]
- GAN (Generative Adversarial Network) [[30000_Generative Design]]
- Generative Design [[30000_Generative Design]]
	- goal-driven approach
	- system
	- autonomy
	- progressive formation and mutation, evolution
	- morphogenically recursive element generation
	- adaptive re-parameterization that can progressively lead to emergent, novel configurations.
	- incremental stages of formation dependent upon preceding steps
	- simulation
	- assessment/ evaluation of system performance
	- assisstant creating, testing, and evaluating options
- Ambient Intelligence (AmI)
- Cloud, Edge and Fog Computing
- PIDO Process Integration and ==Design== Optimization
- MDO Multidisciplinary ==Design== Optimization
- REST Representational State Transfer
- OPC UA Open Platform Communication Unified Architecture
- Holistic Systems Thinking
- Cloud BIM (CBIM)
- Convolutional Neural Networks (CNN)
- surrogate models
	A surrogate model in the context of computational design refers to a simplified representation of a complex system or process. These models are used to approximate the behavior of the original system, allowing for faster evaluations while maintaining an acceptable level of accuracy. Surrogate models are particularly useful in scenarios where running simulations or experiments is computationally expensive or time-consuming.
	- polynomial regression
	- Gaussian processes
	- radial basis functions
	- neural networks
- Unconventional techniques
- Holistic Building _Design_ (HBD)
- Computer Integrated Manufacturing (CIM)
- data space support platforms (DSSPs)
- integrated dynamic model (IDM)
- building performance simulation 
- morphological analysis
-  convergence
- modes of operandi
- Process Integration and Design Optimization (PIDO) platforms 
- Pervasive Information Systems
- distributed cognition
- mental construct 
- graph grammars
- Asynchronous Design
#### [[40000_Ontologies]]:

Spatial Ontology [[101113_MSAS_SpatialAssisstance.pdf]]
	- Concept Definition C = {S; Aqn; Aql; SL} 
		- shape (S)
		- Attributes quantitative (Aqn)
		- Attributes qualitative (Aql)
		- semantic label (SL)
	- spatio-temporal events (Est)
		Ontology should provide the mechanism for building world models that assume spatio-temporal relations in different time intervals (in other words: world models that can capture changes) for the representation of spatio-temporal knowledge used for spatiotemporal reasoning.
	- Instance Base
[[401243_Knowledge Augmented Generalizer Specializer Framework for Early Stage Design Exploration]]
	- FBS - Function-Behavior-Structure ontology
	- GoT - Graph-of-Thought (GoT) mechanism
	- KAGS - Knowledge Augmented Generalizer Specializer
[[9000_401244_Design Criteria Modeling - Use of Ontology-Based Algorithmic Modeling]]
	- DCM - Design Criteria Modeling Ontology
[[9000_405245 _Knowledge Graphs-The Semantic Web Rule Language SWRL]]
	- DIKW Pyramid - how row data becomes a Knowledge and Wisdom
