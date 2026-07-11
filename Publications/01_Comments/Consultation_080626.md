## Key Outcomes

Evgenii received extensive feedback on his PT Beam conference presentation, revealing fundamental communication gaps: slides contain excessive technical detail, assume audience knowledge of ontologies/graphs, and lack concrete examples connecting abstract concepts to BIM practice.  The presentation requires restructuring to prioritize audience leveling over comprehensive framework explanation, with Miguel and Bruno recommending a top-down approach that introduces ontological concepts before diving into implementation. 
## Decisions Made

- **Remove BIM/IFC labeling** from the Function-Behavior-Structure framework slide to avoid incorrectly positioning BIM as only addressing structure. 
- **Eliminate vertical dividing lines** in diagrams to emphasize complementary rather than oppositional relationships between concepts. 
- **Reduce text density** across all slides, removing bottom descriptive text and keeping only essential content that cannot be verbally explained. 
- **Add slide numbers** to facilitate Q&A navigation during the session. 
- **Minimum font size of 14-15** to be used throughout presentation to ensure readability. 

## Core Issues Identified

- **Assumed knowledge problem**: Presentation presumes audience familiarity with ontologies, metagraphs, SWIRL rules, and knowledge graphs—concepts unknown to ~95% of BIM practitioners and ~85% of academic attendees. 
- **Abstraction overload**: Slides like the design state schema introduce technical terms (metagraph rule, SWIRL) without foundational explanation, causing immediate audience disengagement. 
- **Text-heavy slides**: Small fonts and extensive written descriptions force attendees to choose between reading slides or listening to the speaker, reducing engagement. 
- **Missing gap articulation**: Presentation lacks clear statement of what problem society hasn't solved and why Evgenii's work matters, making it difficult for audience to understand contribution. 

## Recommended Restructure

**Three-part framework**: ccccccccc, with first third dedicated to leveling audience understanding before presenting technical work. 
**Essential introductory content**:
- Basic explanation of ontologies as knowledge representation systems, using accessible examples like "friend of a friend" relationships or Netflix's ontology for content connections. 
- Visual examples of knowledge graphs showing triplets and relationships, demonstrating how they differ from SQL databases through inference capabilities. 
- IFC-as-graph visualization showing existing BIM ontological representation (IFC-OWL), then explaining why it's insufficient for capturing function and behavior as defined in this work. 
- Clear differentiation between structural function (already in IFC) versus design rationale and parametric logic (the research focus). 

**Presentation philosophy shift**: Focus on conveying global picture and generating enthusiasm rather than comprehensive framework explanation—detailed understanding will come from paper reading and follow-up conversations. 
## Pending Confirmation

- **Presentation scope reduction**: Evgenii expressed confusion about how to simultaneously simplify slides, add ontology introduction, and maintain research contribution clarity. 
- **Ontology introduction depth**: Unclear whether 2-3 slides or 5+ slides needed to adequately level audience on semantic web concepts. 
- **Framework detail level**: Tension between showing enough technical depth to demonstrate rigor versus keeping content accessible to non-specialists. 

## Conference Context

- **Schedule**: Friday, 9:20 AM presentation in parallel session with three other rooms competing for attendance. 
- **Audience composition**: ~70% practitioners, ~30% academics, with only ~5% of academics having ontology experience. 
- **Session dynamics**: Multiple presentations in English across Wednesday (8 presentations) and Friday; audience will include people interested in diverse topics beyond architecture. 
- **Interdisciplinary requirement**: Need to attract non-architects by explaining applicability beyond architecture domain while maintaining architectural focus. 

## Philosophical Tension

Evgenii's approach reflects **bottom-up detail accumulation** (define all terms, show complete framework, ensure scientific precision), while Miguel and Bruno advocate **top-down engagement strategy** (hook audience with problem, teach prerequisites, show selective examples).  This fundamental difference in communication philosophy created frustration, with Evgenii feeling his significant revision efforts were dismissed despite attempting to follow earlier feedback. 
Miguel acknowledged this may reflect different communication styles rather than objective correctness, suggesting the conference itself will validate which approach works better with the PT Beam audience. 
## Specific Slide Guidance

**Design Knowledge definition slide**: Acceptable to keep textual definition since it establishes core terminology, though bottom explanatory text could move to presenter notes. 
**Function-Behavior-Structure framework**: Remove all BIM/IFC references and bottom descriptions; focus verbal explanation on FBS as ontological framework without forcing BIM into structural category. 
**Design state schema**: Either remove entirely or keep only header; detailed metagraph rule explanation loses audience immediately without prior ontology foundation. 
**Class hierarchy and grammar slides**: Can be shown for 10 seconds with minimal explanation ("here's how we organize validation layers") rather than detailed walkthrough—purpose is illustration not comprehension. 
## Action Items

- **Evgenii**: Add 2-3 introductory slides explaining ontologies, knowledge graphs, and SWIRL rules using non-BIM examples before presenting framework details. 
- **Evgenii**: Remove bottom descriptive text from slides, moving essential content to presenter notes accessible via presenter view. 
- **Evgenii**: Increase all font sizes to minimum 14-15 and reduce text density across presentation. 
- **Evgenii**: Add slide numbers for Q&A reference. 
- **Evgenii**: Review PT Beam conference program at [ptbeam.org](https://ptbeam.org) to understand parallel session topics and audience expectations. 
- **Evgenii**: Decide whether to implement suggested changes or present current version and learn from audience reaction. 

## Broader Implications

Bruno and Miguel emphasized that presentation effort is worthwhile regardless of outcome—even imperfect communication will convey 60-90% of ideas and provide learning for future presentations.  The session revealed ongoing challenges in translating highly technical semantic web research into language accessible to BIM practitioners, a communication gap that extends beyond this single presentation to Evgenii's broader PhD dissemination strategy. 
