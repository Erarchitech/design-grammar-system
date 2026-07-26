---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

# Knowledge augmented generalizer specializer: A framework for early stage design exploration

Meta-level reasoning
Reasoning mechanisms
reasoning mechanisms– problem formulation and representation, step by step decomposition, and explainability of the process at each level of abstraction.
**FBS ontology**
**Graph of Thought (GoT)**
domain-independent (domain-agnostic design reasoning)
hierarchy-independent
meta-level design reasoning approach
recursive FBS reasoning
In summary, FBS allows a comprehensive representation of the knowledge in any domain and enables recursive design reasoning, a crucial aspect in the design generation process.
Retrieval Augment Generation (RAG)

![[Pasted image 20250330190624.png]]

![[Pasted image 20250330190423.png]]
The KAGS architecture, illustrated in Fig. 5, involves a sequence of iterative querying processes performed through Python scripting, leveraging the LLM with prompt engineering methods to progressively generate the intended results. 

Problem statement:
The problem statement describes the design problem that needs to be solved. It includes ==constraints, assumptions==, available information, and other additional information that must be considered for deriving the design solutions. The ==user manually enters the problem statement== to enable the subsequent steps. 

Encoder Agent:
It derives the required functions, identifies the defined variables, determines unresolved requirements, and updates the context. This operation restructures the input into a set of solvable functions and derives the problem context from the input and associated lists of functions and requirements.
E(Q) = P(R, F, V, C)
E = Encode 
P = Updatedproblem 
F = Function 
V = Variables 
R = Requirements 
C = Context 
Q = Problem statement or root DP (Design Prototype)

Generate and Partition: 
This operation enables exploring various perspectives and approaches through finer degrees of abstraction, known as DP, through which the given problem can be solved.
- Function: Primary objective or task to be accomplished
- Behavior: Actions or operations required to achieve the functions
- Structure: Necessary architecture, methodologies, and techniques essential for supporting the identified behaviors
- Knowledge: Explanation of the relational, qualitative, computational, and contextual knowledge interlinking the function, behaviors, and structures explicitly
- Typology: Categories or classifications based on its problem-solving approach or methodology
- Context: Relevant background information or situational context elucidating the problem domain and its significance within a broader context

PROBLEM:
Despite the critical role of early conceptual decisions in shaping the eventual design outcome, most of the computational support and automation are focused on the latter stages of parametric modelling, problem-solving, and optimization. ==There is inadequate support for aiding and automating problem formulation==, variable and parameter identification and representation, and early-stage conceptual decisions.

Design is a complex problem-solving activity that requires ==diverse knowledge inputs== including domain understanding, user requirements, constraints and contextual details, problem representation and design ideation. As design problems become more complicated, ==the need for structured methodologies to simplify and navigate through the process becomes paramount.==

focus is typically not on how to formulate or decompose or approach the problem, but on the problem context and providing specific solution alternatives.

it is desirable to develop ==domain-independent reasoning mechanisms== that allow translation or interoperability between different GD representations and techniques.

![[Pasted image 20250330195340.png]]


##### 3.1 Functional reasoning and functional decomposition in design
Function-Structure mapping
Function analysis and ==function-means tree== for decomposing the problem into subfunctions and structures
==Ontologies use constructs to describe a design problem.==
**Design-Related ontologies**:
- SAPPhIRE ontology
	SAPPhIRE ontology uses seven commonly used ==constructs== – 
	State Change, Action, Part, Phenomenon, Input, Organ, and Effect to 
	describe engineering and biological systems. While SAPPhIRE details 
	and decomposes a problem in the engineering domain, it does not 
	adequately capture the recursive and iterative reasoning in the design 
	process.
- Structure–Behavior-Function ontology - Sembugamoorthy and Chandrasekaran
- Function-Behavior-State ontology
- Basic Formal Ontology
- Gero FBS
	Gero’s FBS framework provided the first algorithmic design 
	thinking framework with a clearly identified sequence of computable 
	steps.
	comprehensive explanation of the iterative and recursive design process, which decomposes the design process into eight 
	distinguishable steps. A notable elegance of Gero’s FBS framework is the 
	ability to explain the eight design steps through the co-evolving understanding of the relationships between the F (function), B (behaviour) 
	and S (structure) of the problem–solution under consideration

==Fewer constructs simplify knowledge engineering and allow greater abstraction of the problem, allowing the same set of constructs to explain the design at various levels of abstraction.== 


##### 3.2 Design thinking

Since the focus is to support the human design process, it is imperative to understand the literature on design thinking and ‘how designers 
think’
Insights on design process include: 
- problem–solution coevolution
- iterative divergence and convergence of the problem and solution space
- iterative problem formulation and reformulation
- critical role of framing and abductive reasoning in the design process
- human-centred values such as explainability

##### 3.3. Design-by-Analogy (DbA)

Analogy allows designers to creatively solve a problem by drawing upon known solutions from another context similar to the target problem. The source and target problems may have functional, behavioural or structural similarities.
text-based analogy retrieval systems
Model-based analogy approaches
ontology-based approaches have been developed to facilitate analogical design reasoning
==Case-Based Reasoning (CBR)== 4 fundamental stages — retrieve, reuse, revise, and retain
==MOLGEN program== with constraint posting and meta-planning with layered control.

While these approaches support systematic design information 
management, they typically focus on specific knowledge domains and lack generalizability
Furthermore, these systems are focused on content and information modelling, but the ==reasoning mechanisms typically remain hard coded.== There is little support in aiding the system user in 
meta-level reasoning, problem formulation and the design process.

##### 3.5. Generative design (GD) techniques and representation

The choice of the GD representation determines the set of variables, parameters and relationships available to the designer for generating the solution alternatives. The design exploration is typically constrained by the choice of representation and lack of interoperability 
between representations. 
Once a GD system is implemented, ==the meta-reasoning about solution generation typically gets hard-coded== in the GD script and programming, and they are ==not as easy to manipulate and modify.== Hence, meta-reasoning about problem formulation and the choice of GD representation still needs to be addressed in GD systems.

##### 3.6. AI-based design generation

We review the recent trends towards the use of LLMs, observing that ==LLMs provide an explainable AI system== unlike the other powerful techniques such as Deep Learning or GAN.
This explainability is important because the designers should know the relationships between the underlying constructs at each level of abstraction of the problem decomposition
Chen et al. [15] utilize the FBS framework in conjunction with LLMs 
to generate design concepts by prompting an initial breakdown of the 
design problem into F, B and S. However, they do not delve into iterative or hierarchical refinement, focusing instead on a direct application of FBS constructs.

While there is rapid growth in the use of LLMs in design generation workflows, these approaches largely f==ocus on singular design outcomes and reasoning pathways==, limiting the scope for designers to explore multiple strategies or solutions.

##### 4. Research problem definition

- A major challenge in implementing a working GD system is 
extracting and incorporating the tacit knowledge of designers and 
domain experts into the GD system. 
- Another key challenge is the ==lack of generalizability of the GD systems.==
Most GD solutions are bespoke solutions suitable for specific project typologies and domains, 
necessitating ==custom implementation for each new project type.==

This underscores the need for a ==generalized GD framework== that can accommodate diverse project contexts and enhance the adaptability of GD systems.
##### 5. Solution Ideation, design and development

The Generalizer component handles hierarchical reasoning, employing mechanisms for systematic problem decomposition and structured reasoning. The Specializer refines the 
outputs generated by the Generalizer, guiding it towards more precise solutions. 

A ==database module stores the research outcomes== to support iterative refinement and knowledge accumulation.



##### EXAMPLE of FBS ontology based framework (Chair)

For example, designing a chair decomposes into sub-functions (e.g., "support weight") mapped to structures (e.g., legs), with behavior (e.g., load capacity) mediating the relationship. This approach supports modular, transparent, and ==domain-agnostic design reasoning.==

For example, let us consider the need for a design solution that provides seating (Function). The need for seating is converted into a list of expected behaviours (Be)- for example, load capacity, comfort of seating, lightweight. Once the expected behaviours are identified, solution alternatives (Structure) are generated. Once the solutions are generated, we can assess the solutions for their actual behaviour (Bs), that is, their actual load capacity and seating comfort. The generated 
solution’s actual behaviour (Bs) is evaluated against the expected behaviour (Be). If the Bs matches the Be, the solution is accepted, and the design description (D) is generated. If the Bs does not match the Be, it should be possible to generate another alternative solution (Reformulation 1) and repeat the cycle. If Bs does not match the Be for any generated solutions, one alternative is to change the expectations (Reformulation 2). For example, if none of the generated solutions are 
able to meet all the three expectations- load capacity, comfort and lightweight, the designer may opt to relax the expectation of lightweight, reformulating her expectations. Similarly, if Bs does not match the Be for any generated solutions, another alternative is to change the target function itself (Reformulation 3). For example, the problem may be reformulated as seeking a solution to rest, rather than specifically seeking a seating. In this case, the function itself is reformulated, leading to changes in the expected behaviour. The three types of reformulations capture all the different iteration scenarios in refining the solution

LLM still relies mainly on statistical patterns and reasoning from the extensive knowledge base. In its present form, LLM is not capable of causal reasoning based on first principles, which is reflected in Gero [[26]](https://www.sciencedirect.com/science/article/pii/S1474034625000345#b0140) FBS reasoning

RESEARCH METHODOLOGY Design Science Research Process
![[Pasted image 20250413103809.png]]