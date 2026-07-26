---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

According to the ISO 14050:2020 Environmental Management - Vocabulary, Life Cycle 117 Assessment is the compilation of inputs and outputs, and potential environmental impacts 118 throughout its life cycle[29]. According to the ISO 14044:2006 Environmental Management - Life 119 Cycle Assessment - Requirements and Guidelines, the Life Cycle Assessment of a product 120 system consists of the following four phases [30], [31]

There are various methodologies for conducting LCA in BIM. These are mainly based on the use of post-design processes that characterise the composite building elements once the model is complete [45]. 168 These currently available methods have several disadvantages:

1. They are generally **expensive** and are not compatible with open-source software. 
2. It is **not possible** to perform **optimisations** or pre-design studies. 
3. They are not integrated into the BIM methodology since the **results cannot be reused in the model**, they can only be exported as reports or tables.

Some studies [48], [49], [50], [51] suggest that Grasshopper is the most suitable tool for parametric design, as it would allow for the integration of a simplified version of LCA into the design process. 

OBJECTIVES AND METHODOLOGY
The following actions are carried out:
1. **==Definition of a BIM model==** with recommended LOD 300 with construction families defined by material layers. 
2. In parallel, the creation of a ==material database== that provides the characteristic values of the different products/systems, ordered, used in the model (Fig. 02) (359 complete construction solutions have been obtained that are a combination of 50 basic 293 materials in Excel)
3. Assignment of parameters associated with each product and their form values
4. Obtaining results for the control model.
5. Variation of parameters of the initial model (mainly materials and thicknesses)
6. Establishment of control parameter protocols that allow one to focus on appropriate solutions. We also define the generation configuration, which is the genetic calculation itself. Population size, generations, and seed. This process follows the **NSGA-II method** (Fig. 10)[61]
8. Generative calculation of results of the different variations made and the control protocol.
9. Comparison of solutions with the original model.