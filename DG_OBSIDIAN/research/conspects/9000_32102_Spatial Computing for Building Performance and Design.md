---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

[[004_Spatial Computing for Building Performance and Design.pdf]]

==MAIN INTENT of THE WORK==
- The dissertation focuses on generative design as a lever to promote more sustainable building design, through performance prediction of spatial and technical systems in buildings.
- To support the creation of new hybrid methods, it is important that ==spatial, environmental, and structural considerations can work in parallel and inform one another.== 
- We propose the ==hybridization of the three methods==, coupled with a new set of interdisciplinary metrics and performance indicators to guide future building layout automation. Working together in an iterative loop, the strengths of the different strategies can be applied at different points in the design process.

- The built environment has long adapted to different uses and habitation patterns. Modern cities will have to adapt their existing infrastructure and housing stock many times over. Being aware of the opportunities for creating buildings that can ==**adapt to different uses during their lifetime**== is a design challenge that has yet to be solved. In the current context, both the adaptation of existing buildings, as well as the creation of adaptable new buildings, is a key design challenge. Here, ==computational design tools can help to spatially adapt and reconfigure existing building stock==, making renovations more predictable, feasible, and scalable.
- Digital tools have allowed the integration of environmental and structural analysis into the design process.  This digital toolset not only allows for design evaluation and post rationalization but can be an integral component of the design itself. Currently, although workflows seem digitized, design software mostly emulates analogue 2D drafting methods in a digital environment.
- It has been shown that coupling ==design methods with quantitative simulation feedback== in an early design stage has the potential to significantly improve design outcomes (Burnell et al., 2017).
- Architectural design has long relied on precedents, referencing and replicating aspects of existing structures in both construction techniques and spatial layouts. While ==architectural monographs== and design guides are commonly used in education and practice, this ==referential== ==approach== has not yet been fully digitized. The complexity of buildings, involving factors like spatial organization, structural systems, and wall construction, makes digital comparison difficult. Simplified representations, such as graphs, may capture spatial arrangements but fail to convey detailed construction, while detailed 3D models show material quantities but obscure organizational relationships. To bridge this gap, new digital design methods and representations are required that can operate across scales and design tasks, providing clearer understanding and comparison of architectural elements.
- ==Cloud-based parallel computation==
-  The framework merging spatial, environmental, and structural constraints in the design of buildings into integrative computational design workflows. The thesis explores how this integrative approach can be used for co-designing with computational means, automatically generating new, more efficient structures, and allow for the analysis and benchmarking of existing systems and environments.
- As of today, ==automated building-level layout tools have not made much headway into mainstream architectural practice== where, their use is mainly reserved for speculative design exercises or specific niche applications such as office furnishing and electric lighting layouts in interior design (Heuman, 2020) or complex programming exercised for hospitals, airports or large scale residential and commercial developments (Das et al., 2016; Derix, 2010; Finucane et al., 2006).
- Learning implicit geometric relationships, they are difficult to train and untransparent datasets cannot guarantee architectural quality or environmental performance (Weber et al., 2022b)
- ==Searchable database== for floor plans, where room connectivity and wall geometry are represented as graphs (Dillenburger, 2016a) exist, however they only have been used for design analysis
- ==New types of structured data, such as graph based data structures that are procedural in nature or parametrized command sequences== (Wu et al., 2021), will enable new types of machine learning and design automation (Ritchie et al., 2023).
- ==Cutting down the simulation time== of an annual raytracing simulation from hours to milliseconds enables architects to assess not one, but thousands or millions of design solutions
- Traditional structural or environmental analysis of buildings is conducted by specialists, using dedicated ==simulation software tools and workflows that are disconnected from the architectural design process==
-  Inspired by using physical models to enable efficient structural forms, form-finding explores the digital or physical process of optimizing or adjusting a set topology to create a structurally valid solution.
- “digital processes that enable interactive formal exploration can enrich the known formal vocabulary” (Rippmann, 2016)

- ==AI-enabled workflows.== In architectural design, design decisions are often hard to capture in words, especially when conventions are not followed, and new spatial or structural innovation takes place. Drawing or sketching becomes an intuitive part of the design process where spaces are explored through drawing, rather than textual descriptions. It is challenging to create designer centered, intuitive workflows for describing geometric transformations with words through text prompts or code.
- ==aRCgis cITYeNGINE== Grammar based design methods have been successfully implemented into computational workflows to procedurally compute building volumes with detailed facades. Notably Esri’s City Engine (ESRI, 2024) which integrates the CGA++ shape grammar language (Schwarz & Müller, 2015) that enables the generation of differentiated building envelopes for visualization purposes of urban design proposals.
- There is perceived real ==risk that architects further lose control of the design process== at a time when only 2% of US homes are designed by licensed architects
- A big challenge in the creation of coherent layouts is the problem of scale. As programmatic requirements get more complex it becomes more difficult to coherent layouts that can integrate layers of hierarchy. This requires either a multi-step approach where programmatic units are clustered together and subdivided individually or smaller units (such as a single apartment) are created on their own and then assembled as units into a larger buildings


- ==USE CASES for Generative design tools:==
1. Design Feedback / real-time interactive design validation
2.  Design Exploration and Optimization
3. Existing urban environment analysis and redevelopment

==Existing Generative Design approaches:==
1. ==Bottom-up methods==
	The bottom-up method proposes to work with a set of parts, such as rooms or preassembled units, and to aggregate them into a larger structure. As an exploratory tool, it allows for the fast generation of different design options. Aggregation strategies can be further coupled with heuristics to guide the assembly. However, navigating often complex constraints or boundary conditions can be very challenging in the very large design space
1. ==Top-down methods==
	offer an alternative, starting directly from geometric constraints, such as a building or site boundaries that get subdivided into smaller units. For this, different subdivision or packing strategies can be deployed.
1. ==Referential methods==
	 make use of existing buildings and datasets. Geometric properties of existing or premade layouts can be fit or adapted to a new context. Fueled by recent advances in machine learning algorithms, spatial relationships have been captured as graphs or bitmap images and encoded into neural networks, enabling lookup and synthesis.

Hybrid approach proposed. Varying in resolution, the members of a bottom-up method do not have to be defined as single rooms but could be larger units or building parts, that can be refined or filled using top-down or referential approaches.

- Many design decisions are intuitively made by architects based on prior experience or reference projects (Heckmann et al., 2018; Jocher & Loch, 2012) but without assessing their impact on building performance (Çavuşoğlu & Çağdaş, 2017) due to the time, effort, and technical sophistication required to conduct this type of analysis. However, coupling methods of design with quantitative simulation feedback in an early design stage has the potential to significantly improve design outcomes (Burnell et al., 2017).

==HYPERGRAPH==
- Hypergraph as a ==shape descriptor== for building floor plans. 
- The hypergraph represents key characteristics of the shape divisions of any given floor plan layout, enabling both the ==mapping and benchmarking== of suitable, high-performing floor plans, as well as their automatic generation
- A hypergraph is created from existing building floor plans and can be applied to new conditions.
- A hypergraph allows for translating cultural conventions and practices into new designs, and a fully transparent source attribution. 
- ==The concept of excess space==
	Based on the notion that a room with a certain program, for example, a bedroom, has minimum functional requirements in terms of furniture (bed, dresser, cabinet) and space around that furniture that supports its proper use. Areas beyond those functional requirements are then defined as excess. 

==METHOD APPLIED IN RESEARCH==

1. Residential Building Floor Plan Repository
	We assembled a reference library of ~1,444 real world floor plans. Plans are sourced as raster images.
2. Gather Reference building prototypes to benchmark the generated floor plans
3. Floor plan images are analysed in Rhino and graph inputs are retrieved automatically:
	1. Room ids
	2. Room ratios
	3. Boundary lines
	4. Facade lines
	5. Entrance location point
	6. Access adjacencies
	All inputs are collected in json database
4. The presented hypergraphs are a combination between an ==access graph and a subdivision graph==:
	1. Subdivision Graph ==(Binary Space Partition tree - BSP tree)==
		Each node corresponds to an area (or ratio) and a subdivision angle α, with (directed) edges connecting the child nodes to the parent node that was subdivided.
	2. Access (Adjacency) Graph
		 Graph is defined by lists of unique ids in the leaf nodes. Edges connect the room nodes of the subdivision graph that connect (e.g. the rooms that are accessible between one another). Different subdivisions therefore result in different hypergraphs
5. Geometric subdivision of boundary into the rooms is computed with a ==binary space partition tree - BSP tree==
1. Elaborated graph custom data-format.
2. The procedure is fully reversible, meaning that a spatial floor plan layout can be encoded in a graph and the same floor plan layout will emerge given a graph and the original boundary polygon.
3. The geometric floor plan creation process has been implemented in ==Rhino + Grasshopper== (linear algebra library Math.NET, the 2D polygon clipping and offsetting library Clipper2)
4. ==Hypergraph representation in== ==NetworkX,== visualized with the force based Kamada-Kawai algorithm
5. ==Limitations:== Failure cases of the subdivision algorithm include highly complex non-convex boundary geometries, as well as polygonal boundaries with holes
6. Apartment Validity Heuristic
	To filter geometrically valid but spatially inadequate outputs, a series of heuristics filter and rank feasible results:
	1. ==Reference perimeter differrence==: [0.001; 0.500] 0.001 - the best fit
		𝛿𝑝 = |1 − L𝑆𝐴*L𝐵/ L𝐴*L𝑆𝐵 |
		Perimeter difference score δp , where LA is the perimeter of polygon A, LSA the perimeter of the square polygon with the same area as A, LB the perimeter of polygon B, and LSB the perimeter of the square polygon with the same area as B.
	2. sDA score (spatial Daylight Autonomy) : %
		Indicating the fraction of space with more than 300 lux of daylight on average.
		A metric for interior spaces that, through a yearly illuminance simulation with physics-based raytracing and local weather data, predicts the percentage of hours per year when a minimum light level of 300 lux can be achieved with daylight
	1. Furniture Placement: true/ false
		 Minimal number of furniture blocks that need to be fit
		- Automatic version of the spatial scoring system developed by the City of Berlin’s public housing provider (Howoge, 2023)
	1.  Emission delta

![[Pasted image 20241028114034.png]]

![[Pasted image 20241027223526.png]]

![[Pasted image 20241027223343.png]]


HYPERGRAPH ANALYSIS and BENCHMARK
- Using a principal component analysis (PCA) of key attributes
- The hypergraph allows us to show and ==encapsulate architectural differences and investigate spatial configurations== that are encoded in local architectural practices, prevalent construction techniques, building codes, and climate.

- Detailed building ==energy models that can be created through the hypergraph representation== allow for automatic generation of air flow zoning models that can be used to simulate natural ventilation, replacing current practices of manual modeling or simplified assumptions (Tarkhan et al., 2022)

![[Pasted image 20241028154138.png]]

- By utilizing architecturally vetted reference designs and heuristic procedures that respond to local requirements, the hypergraph method can produce high quality spaces from virtually any boundary condition. 
- Opportunities to apply the method to ==automated benchmarking of building retrofits== including the conversions


### ==Automated Structural Modeling for Embodied Carbon Estimation==

Algorithm takes building massing and automatically dimensioned structural elements for the embodied carbon calculation, while relying on proven methods for the building envelope, creating a proxy parametric building model that serves as a simplified BIM model. 

![[Pasted image 20241028163632.png]]

For the geometric generation of a beam layout, we propose two generative methods; the Voronoi method and the cut out method. 

### Layout Automation Algorithms for Building Retrofit and Adaptive Reuse

- Policymakers have started to develop initiatives and incentive structures to convert office buildings to residential units in cities such as Boston (BPDA, 2023), DC (DC Office of Planning, 2020), New York (City of New York, 2023) and San Francisco (Breed, 2023)
- Programmatic conversions come with a change of circulation requirements, building services, and HVAC systems. 
- Focus on commercial-to-residential conversions
- ==Algorithmic methods can help predict the spatial potential== of a building retrofit through detailed geometric analysis. 
- Utilizing design automation to create apartment subdivisions and floor plans allows for the exploration of thousands of options.
- Evaluation through Daylight analysis and spatial fitting of furniture
- This research establishes a new methodology for ==systematic assessment of a building==, that could be used for both evaluation of an entire building stock, as well as during design ideation of a full floor plan of a single building or floor plate.
-  ==bijective graph mapping==

#### Generation Workflow
- Radial or linear unit subdivision
- Merging of invalid apartments
- Alignment of program with structural grid
- Internal apartment layout
	Hypergraph subdivision with predefined library
- Environmental assessment
	- Daylight (sDA for each unit)
	- Spatial analysis (spatial score for each unit)
	- Structural analysis (str layout score for each unit)

![[Pasted image 20241029144004.png]]

1. ==Unit Subdivision Algorithm==
	1. Determine ==Building Core and Structural Grid inputs== either artificially or manually
	2. ==Simplify boundary== with a snapping procedure (noise algorithm) to align with the Grid ![[Pasted image 20241029151208.png]]
	3. Determine ==Median axis== based on Voronoi subdivision algorithm and simplified boundary
		a series of curves along the center of a shape
	4. Turn median axis to circulation lines and cores.
		1. Straighten median axis for shape devision
		2. Place cores along the line based on inputs grammar
	5. Subdivide boundary mesh to unit zone faces by linear or radial algorithm
	6. Straighten polylines and cutout of circulation and cores
	7. Clean up merging faces that have no access to a facade or circulation or do not fit the min area requirements.

![[Pasted image 20241029175435.png]]
![[Pasted image 20241029175706.png]]



## CONCLUSION AND DISCUSSION

- New design environments in which designers not only interact with geometry, but also with data, are needed
 - Different metrics are not comparable or quantifiable in carbon, such as daylight, or quantifiable at all, such as architectural expression, yet are as important for the ultimate quality of a building and the life of its inhabitants. Research showed that there is typically no silver bullet for a sustainable design and many different design solutions lead to comparable results
 - the automatic and fast creation of different iterations or design options creates very large design spaces with massive amounts of data, as well as different, and often conflicting parameters. New procedures must be developed to sort, categorize, evaluate, and filter successful design solutions and create geometric computation that ensures novelty and diversity in design output.
 - there is an opportunity to optimize and create hypergraphs themselves artificially to explore new typologies or adapt a graph to a new boundary condition. Future work should address how such graph-based procedural design workflows can be augmented and automated through machine learning algorithms.
 - In the digital age, new questions regarding ownership, dissemination, and biases emerge in architecture that are already heavily debated in other disciplines. 
 - Currently there are no accessible, curated, digital databases of designs, a significant hurdle for deploying automation methods such as machine learning algorithms. Meanwhile, the databases that do exist have been collected without regard for architectural quality or location, which is highly problematic as they are used in active research.
 - With the wealth of data and new quantitative comparisons and opportunities, the discipline must rethink what good design is and how to judge it and furthermore learn from existing buildings and cities what makes them performative.
 - With models getting more and more accurate there is the risk of an increased confidence in computational simulations where designers become unaware of its limitations, such as structural simulations that use idealized material properties and do not take construction details into account or building energy models where user behavior and schedules are critical for accurately predicting energy usage.