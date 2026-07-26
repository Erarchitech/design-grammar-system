---
type: keyword-index
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

- ArcGIS CityEngine
Procedural computing for Urban Design. VPL Environment
- GPLAN
	[Data-driven Interior Plan Generation for Residential Buildings](http://staff.ustc.edu.cn/~fuxm/projects/DeepLayout/index.html)
- Archistar 
	Web urban platform to analyse and estimate site design investments based on chosen plot
	https://www.archistar.ai/
- Google Earth Delve
	[Build sustainably with Google Earth – Google Earth](https://www.google.com/earth/about/design/)
	web-based massing urban generative site planning and evaluation based on spatial, financial, and energy models
- TestFit
	https://www.testfit.io/
- Spacemaker
- AGORUS Revit AI Assissstant
	https://www.linkedin.com/feed/update/urn:li:activity:7223874115969957889/
- QGIS
- PyTorch
- IfcOpenShell
- KREO
- Digital Blue Foam
- XGBoost
- CONFIGRAPHICS
- Galapagos
- Rplan
- G2PLAN
- Refinary
- WallaceiX
- GraphXR
- Neo4j
- py2neo
- Speckle

#### APIs
- FastAPI
#### Databases
- SQLite
- sqalchemy

#### Tools for Agent-based Design
- **Processing**: A programming language often used for visual simulations.
- **Grasshopper + Rhino**: Plugins like **Kangaroo**, **Anemone**, or **Swarm** allow agent-based simulations.
- **NetLogo**: A platform for simulating agent-based models.
- **Unity or Unreal Engine**: Used for more dynamic simulations involving interactive agents.

Web Requests (loading web datasets and using ML for Grasshopper codes)
- Swiftlet
- Postman
### Literature Review Analysis

#### - Visualisation
- Papers
- VOS Viewer
	##### Workflow
	- Export txt list of publictions from specific databases like Web of Schience, Scopus, Lens, PubMed
	- Import in standalone VOSviewer application
	- Setup type of data (Network, bibliographic data, text data)
	- Select data source (API request (eg. Wikidata), bibliographic database file, ref manager file (RIS, EndNote, RefWorks))
	- Select type of analysis (Co-occurrence, Citation etc) and counting method (full, fractional), unit of analysis (all keywords, author keywords, automatic keywords)
	- Option to add thesaurus file - helps to group similar terms together
	- Select threshold for building a link between publications (min number of occurences of keywords)
	- Create map with clusters from keywords that are often used in the same papers and control clusters through parametrisation like analysis method, resolution, min cluster size etc
	
	##### Types of links
	- **Co-authorship Links**: Represent collaborations between authors, institutions, or countries.
	- **Co-citation Links**: Indicate that two items (e.g., articles, authors) are cited together in other works.
	- **Bibliographic Coupling Links**: Show that two documents cite one or more common references.
	- **Keyword Co-occurrence Links**: Reflect relationships between keywords that appear together in the same documents.
	- **Citations**: Highlight direct citation relationships between documents.
	
	##### Link Strength**
	- Links are weighted by their **strength**, which is a quantitative measure of the relationship between nodes. For example:
    - A strong co-authorship link means frequent collaboration.
    - A strong co-citation link means two documents are often cited together

	##### **Nodes and Labels**
	- **Nodes** represent entities such as authors, documents, journals, or keywords.
	- **Labels** on nodes indicate the names of these entities (e.g., an author’s name or a keyword).
	- Larger nodes typically signify greater importance (e.g., higher frequency of occurrence or more connections).

	##### **Link Lines**
	- **Lines** between nodes represent the relationships (links). Their thickness or opacity reflects the strength of the connection. Thicker lines indicate stronger or more frequent relationships.