---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

[[111204_Rule-Checking and Semantic Enrichment of Graph-Based Bim Data.pdf]]

- This study presents a ==modular,== extensible framework for scripting-based Building Information Modeling (BIM) data analysis and validation, using a s==chema-agnostic approach==. While BIM is widely used to manage project information across a building's lifecycle, existing scripts for BIM data analysis are often scattered and difficult to use in practice. To address this, the proposed framework offers a portable, transparent system for rule-checking and data enrichment. It utilizes ==semantic web== technologies and an ==RDF-based graph structure== to enable customizable rule sets and data interoperability across different BIM applications. The core engine manages linked building data, supporting ==pluggable components== for rule execution and enrichment through scripting. The framework's capabilities are demonstrated through pseudo-implementations, such as parameter validation, wall thickness checks, cost inference, and energy simulation file generation. The study advocates for ==community-driven development== and suggests future work in implementing the framework and testing it with complex datasets.

![[Pasted image 20241219151955.png]]

- Inputs are parsed by appropriate component and convertined to the RDF Graph through API of System Core. 
- Input Parsers perform Tokenizing (creating tokens from input data) and Parsing (breaking inpus into usable information)
- 
![[Pasted image 20241219155104.png]]

![[Pasted image 20241219154037.png]]

- DCF report
- The system is file-based and assumes import-export