# ptBIM 2026 — PowerPoint Editing Instructions

**Target file:** `Publications/01_ptBIM26_R2.pptx` (the source of `01_ptBIM26_R2.pdf`)
**Goal:** Raise the deck's BIM register for a ptBIM / AEC-academic audience by naming openBIM standards (IFC4.3, IDS, mvdXML, bSDD, ISO 19650/LOIN, BOT/LBD), positioning against the automated code-compliance literature, and adding evidence. Contribution and narrative stay the same.

> **How to use this file:** Open the .pptx, then apply the edits below slide by slide. Each block gives the slide's current title so you can locate it, what to change, and **exact text to paste**. Text inside `«…»` is copy-paste-ready. Do not restyle the deck — keep existing fonts (Space Grotesk headings, Inter body), colours, and master layouts. Only change text and the figures explicitly named. After editing, re-export the PDF and skim for overflow.

**Current slide order (14 slides + 3 new = 17):**
1. Title · 2. Table of Contents · **New Slide C ("What we mean by 'Design Knowledge'")** · 3. Hook ("design intent survives the next handover") · 4. The Problem · **New Slide A (openBIM positioning)** · 5. Goal · 6. Approach (Core–Periphery) · 7. System Framework — Five Layers · 8. Two Interfaces, One Knowledge Core · 9. Data Layer · 10. Use Case 1 (intro) · 11. Use Case 1 (room schedule) · 12. Use Case 2 (validation) · 13. Conclusion · 14. References

---

## Global rules for the editor
- Preserve master, theme colours, and fonts. Match the size/weight of the text already on each slide.
- When asked to "add a bullet," append it in the same list style as existing bullets.
- Do not delete the author/ORCID/funding line on the title slide.
- Three **new slides** are specified (New Slide C after slide 2 / Table of Contents; New Slide A after slide 4; New Slide B before slide 13). Insert using the same layout as a standard content slide (title top-left, body below).
- Keep edits concise — this is a conference talk, not a paper.

---

## Slide 1 — Title
**Add a one-line standfirst** under the existing subtitle (same style as subtitle, slightly smaller):

«Carrying parametric design intent and machine-checkable design rules across the openBIM lifecycle.»

Keep both names but make "Design Grammars" primary and "Generative Copilot System" a subtitle. No other change.

---

## Slide 2 — Table of Contents
Replace agenda item 3 text with:

«3. System architecture — a semantic knowledge core alongside the BIM model»

Add a new agenda item 6:

«6. Positioning — relation to IFC, IDS and ISO 19650»

---

## NEW SLIDE C — "What we mean by 'Design Knowledge'"
**Insert immediately after slide 2 (Table of Contents), before the Hook.** This is a definition slide — it anchors the term the whole talk depends on, so the audience reads the rest of the deck with the right mental model. Use a content layout: title top-left, one definition line set larger, then a short two-part contrast.

Title: «What we mean by "Design Knowledge"»

**Lead definition** (set larger / emphasised, same heading font family as other titles but body weight):

«Design knowledge is the explicit, machine-readable body of functions, constraints, rules and generative relationships that justify and produce a design — its logic and intent — as distinct from the realised building objects, their relationships and properties that a BIM/IFC model records as the finished state.»

**Contrast strip** (two short columns or two stacked lines, same bullet style as other slides):

«BIM / IFC describes the building as **objects, their relationships and their properties** — `IfcSpace`, `IfcWall`, `IfcElement`, their spatial containment, aggregation and connectivity, and their attributes. This is the realised *what* — the Structure.»

«Design knowledge is the *why* and *how* upstream of that artefact: functional intent, the prescriptive rules and constraints a valid design must satisfy, the parametric/generative logic that drives form, and the rationale linking intent to geometry.»

**Three defining properties** (compact bullets, small body text):

«• Explicit & machine-readable — encoded as ontology + SWRL atoms, not implicit in a designer's head or a tool file.»

«• Generative & prescriptive — it produces and tests designs, rather than describing a finished one.»

«• Tool- & file-independent — it lives in a shared semantic core referenced by all disciplines, not locked inside one platform's export.»

**Caption / one-liner for the speaker (bottom of slide, small):**

«In FBS terms: IFC carries the building's **Structure** — its objects, relationships and properties. Design Grammars carries its **Design Knowledge** — the Function, the rules and the generative logic that produced it.»

> **Note on framing:** Do **not** say "IFC is just geometry." IFC is a semantic, object-oriented model of building *objects, their relationships and their properties*. The gap DG fills is not geometry vs. data — it is that IFC/BIM has no first-class, executable representation of design rules, constraints, parametric logic or rationale. State the gap precisely; it is a stronger claim.

---

## Slide 3 — Hook ("How much design intent survives the next handover?")
Keep the hook line. **Edit the sub-line** to adopt ISO 19650 language. Replace the current subtitle ("We exchange files. The rules behind them do not travel.") with:

«We exchange files. The rules behind them do not travel. ISO 19650 governs *what* information is delivered — never the design logic that produced it.»

No change to the 5-stage sketch→BIM graphic.

---

## Slide 4 — The Problem: design knowledge gets lost in translation
**Replace the 4 bullets with these 5** (keep the existing bullet style):

«• BIM automates information — but design knowledge stays fragmented across files, platforms and disciplines.»

«• Each handover transfers only the final state — the geometry and properties — not the rules and constraints that produced it.»

«• IFC (IFC4 / IFC4.3) is a product model for physical components and properties. It has no first-class, *executable* representation of design rules or parametric dependencies — `IfcConstraint` / `IfcMetric` are descriptive only.»

«• The checkable-requirement stack — IDS, mvdXML, bSDD — verifies *delivered* models (presence and values). It does not express the generative, parametric logic that creates the geometry.»

«• Parametric tools (Grasshopper / Dynamo) silo that logic as opaque, non-interoperable node graphs that die at export — the rules are replicated per platform, never shared.»

(Leave the "Data fragmentation" diagram as is, or shrink slightly to fit 5 bullets.)

---

## NEW SLIDE A — "Where Design Grammars sits in the openBIM stack"
**Insert immediately after slide 4.** This is the highest-value addition — it pre-empts the "why not just use IDS?" question. Use a content layout with a title and a 5-column table.

Title: «Where Design Grammars sits in the openBIM stack»

Table (5 columns × 6 rows; header row bold):

| Concern | IFC4 / IFC4.3 | IDS / mvdXML / bSDD | ISO 19650 / LOIN | Design Grammars |
|---|---|---|---|---|
| Physical components & properties | ✓ | — | governs | references |
| Machine-checkable *delivered* requirements | — | ✓ | specifies | exports to |
| Parametric / generative design logic | — | — | — | ✓ |
| Relational design rules (SWRL) | descriptive only | value / presence checks | — | ✓ executable |
| Cross-tool object identity (linked data) | partial | — | — | ✓ (ontology / IRIs) |

Caption under the table:

«DG complements the openBIM stack — it does not replace it. It carries the upstream design logic that IFC and IDS were never designed to hold, and can export IDS-checkable requirements downstream.»

---

## Slide 5 — Goal (Shared Knowledge Core)
Keep the goal text. **Add a one-line concrete example** beneath it (small body text):

«Example: "habitable rooms ≥ X m² with exterior daylight access" travels as a reusable rule — not as a frozen set of wall positions.»

Optionally shrink the decorative circuit-board "DG" icon; it adds no information for this audience.

---

## Slide 6 — Approach (Core–Periphery)
Keep the 4 bullets. **Append two bullets** grounding the model in named representations and the LBD literature:

«• Periphery = recognised views: BIM edge (IFC / authoring model), parametric edge (Grasshopper definition), analysis edge (energy / structural).»

«• Core = an ontology aligned to open vocabularies (BOT, Topologic, SOSA) — the Linked Building Data approach to one shared object model.»

---

## Slide 7 — System Framework — Five Layers
The radial figure is unreadable at projection size and uses internal acronyms. Two changes:

1. **Replace the concentric-ring figure with a clean left-to-right (or top-down) 5-band stack.** Reserve the ring for the paper. Each band keeps its name and gains a "BIM equivalent" tag:

   - Data Layer → «BIM equivalent: federated model / CDE»
   - Communication Layer → «BIM equivalent: IFC + IDS + APIs»
   - Analysis Layer (ontology) → «BIM equivalent: semantic model / Linked Building Data»
   - Integration Layer → «BIM equivalent: MCP / connectors»
   - DAG / Computation Layer → «BIM equivalent: generative (Grasshopper) logic»

2. **Expand acronyms on first use** in the layer labels: «DAG (directed acyclic graph of the algorithm)», «GAE (generative algorithm environment)». Unexplained acronyms read as unfinished work.

---

## Slide 8 — Two Interfaces, One Knowledge Core
Keep the Model / Grammar / Bridge text columns. Two changes:

1. **Replace the tiny n8n/Neo4j screenshot** with a clean schematic of the pipeline:
   «NL rule → constrained LLM → SWRL atoms → Neo4j metagraph» sitting above «IFC-aligned classes → geometry & properties», joined by the Bridge (n8n + MCP).

2. **Add one line** under the Grammar Domain column stating the reliability guard:

«The LLM emits SWRL restricted to a fixed schema (ClassAtom / DataPropertyAtom / BuiltinAtom); output is validated against the ontology before commit.»

3. Under Model Domain, make IFC alignment concrete:

«IFC-aligned: DG `Class` nodes map to IFC classes (e.g. IfcSpace, IfcWall).»

---

## Slide 9 — Data Layer — Single-Source Object Integrity
**Lead with the BIM idea, not the database engineering.** Add/strengthen the top line to:

«One authoritative definition per object, referenced — not copied — across disciplines. This is the linked-data answer to model federation: a single source of truth in the CDE, with IRIs as stable object identity.»

The polyglot multi-DB ring can move to a backup slide; if kept, it should sit below this framing, not above it.

---

## Slides 10–11 — Use Case 1, Residential Plan-Layout Generation
Keep the visuals but **guide the audience through one worked rule.** Add a short caption strip across both slides:

«Worked example: the rule "kitchen must be adjacent to dining" is encoded once in the graph, drives generation, and prunes layouts that violate it.»

On slide 11, **add scale numbers** near the room schedule (real figures from the case study):

«Program: N rooms · M adjacency rules · K valid alternatives generated.»

And ground the spatial program in a classification:

«Spaces typed via IfcSpace / Uniclass, not an ad-hoc table.»

(Replace N / M / K with the actual counts.)

---

## Slide 12 — Use Case 2, Design-State Validation
This is the clearest BIM story; make the payoff readable. Three changes:

1. **Enlarge the colour-coded validation result** (pass/fail per element) to roughly half the slide — it is the money shot for this audience.
2. **Show one rule end-to-end** in a small strip: rule text → SWRL → graph → coloured element. Use a **regulation-style constraint** (e.g. height limit, or fire-egress width) so it reads as compliance checking.
3. **Name the result channel in BIM terms**: if issues are exportable as BCF topics, say so; if the overlay differs, state why.

Suggested caption:

«One rule, end-to-end: "max building height ≤ 75 m" → SWRL body fires on violation → element highlighted red in the federated model.»

---

## NEW SLIDE B — "Relation to prior art"
**Insert immediately before the Conclusion (slide 13).** Content layout, title + 3 short rows.

Title: «Relation to prior art»

«• Automated Code Compliance Checking (Solibri / SMC; Eastman et al. 2009; Beach et al.) — DG encodes rules from natural language into an open ontology via a constrained LLM, instead of hard-coded checkers.»

«• Semantic rule checking / Linked Building Data (Pauwels et al.; BOT; SHACL) — DG adds the *generative* (grammar) side, not only checking.»

«• Shape / design grammars (Stiny 1980) — DG operationalises grammar rules inside a live BIM + parametric pipeline.»

---

## Slide 13 — Conclusion
Two changes:

1. **Add a metrics line** under "What works" (use real figures from the T1 draft — "точность кодирования" / encoding accuracy):

«Evidence: R rules encoded · A SWRL atoms · encoding accuracy P % (precision) / Q % (recall) · case study of S spaces.»

2. **Reframe the IDS bullet** in "Limitations & next steps." Replace «IDS integration left for future work» with:

«IDS is a complement, not a gap: DG can export IDS-checkable requirements — verification downstream, generative logic upstream. Full IDS round-trip is the next step.»

Keep the honest SWRL-coverage and human-in-the-loop limitations; pair each with its next step.

---

## Slide 14 — References
**Append** these (the deck is strong on design theory and semantic web but thin on BIM/compliance standards):

«[25] buildingSMART. Information Delivery Specification (IDS) — technical documentation; mvdXML; bSDD.»
«[26] ISO 16739-1 (IFC4.3); ISO 19650-1/-2 (information management); LOIN / ISO 7817.»
«[27] Eastman, C., Lee, J., Jeong, Y., Lee, J. (2009). Automatic rule-based checking of building designs. Automation in Construction 18(8), 1011–1033.»
«[28] Pauwels, P., Zhang, S., Lee, Y.-C. (2017). Semantic web technologies in AEC industry: A literature overview. Automation in Construction 73, 145–165.»
«[29] Beach, T., Rezgui, Y., et al. Building compliance / regulatory knowledge representation for BIM.»
«[30] Stiny, G. (1980). Introduction to shape and shape grammars. Environment and Planning B 7(3), 343–351.»
«[31] Solibri Model Checker (SMC) — commercial automated code-compliance baseline.»

---

---

## Figure improvements from drawio source files

Source file: `Publications/900_00_Procedural Design Ontology.drawio`

These two existing schemas can be repurposed and improved to serve the BIM-context narrative. Both require redesign against the current **v6.1 ontology state** (5 layers + Core FBS band, vendor-neutral except Grasshopper and IFC).

---

### Schema 1 — "IFC integrated" (tab `IFC integrated`)

#### What the current schema shows

A **Venn/overlap diagram**: IFC Schema at the centre, surrounded by five overlapping generic ontology circles:
- Product Modeling Ontology — "Closely related"
- Process Ontology — "Related"
- Topological Ontology — "Related"
- Material Ontology — "Partially related"
- Human-Centered Design Ontology — "Partially related"

Each annotation describes a generic conceptual overlap (e.g. "IFC defines processes such as scheduling, resource allocation…").

#### Problems against the v6.1 ontology and ptBIM audience

1. **Wrong level of analysis.** The five circles are irrelevant generic ontology categories, not DG's actual layers. A ptBIM audience will ask "where is SWRL? where is IDS? where is SHACL?" and find nothing.
2. **The core gap is absent.** The whole DG argument rests on IFC having *no first-class executable design rules* — `IfcConstraint`/`IfcMetric` are descriptive only. The current diagram does not show this gap anywhere.
3. **No DG layers shown.** The v6.1 ontology has five layers (OntoGraph, Metagraph, ValidationGraph, SpecGraph, ComputationGraph) and a Core FBS band. None appear.
4. **Material and Human-Centered circles are off-topic** for this talk and dilute the message.
5. **Missing IDS/mvdXML/bSDD** — the checkable-requirement stack the audience considers standard knowledge.
6. **No complement relationship.** The diagram shows IFC as a central sun; it should show DG as a *complement* that fills specific gaps and can export to IDS downstream.

#### What v6.1 now makes possible (ontology evidence for the redesign)

| v6.1 fact | Implication for the figure |
|---|---|
| `dg:Class` nodes map to IFC classes (e.g. `IfcSpace`, `IfcWall`) — OntoGraph IS an IFC-class-aligned dynamic domain ontology | Show OntoGraph ↔ IFC as a bridge, not a gap |
| `dgv:ObjectInstance` aligns with `bot:Element` / `sosa:FeatureOfInterest` / `geo:Feature` — the validated geometric entity corresponds to an IFC element | Show ValidationGraph ↔ IFC element layer as a bridge |
| `dgm:Rule` ≡ `swrl:Imp`; SWRL rule structure has no IFC equivalent (`IfcConstraint` is descriptive only) | Mark Metagraph/SWRL layer as the **key IFC gap** |
| `dgc:ComputationGraph` (Algorithm → Procedure → Pattern) models parametric logic — no equivalent in IFC | Mark ComputationGraph as the **second IFC gap** |
| `dgv:ValidationRun` aligns with `prov:Activity` + `sh:ValidationReport` — can produce BCF-ready results | Show ValidationGraph → BCF/IDS output as a downstream bridge |
| Vendor-neutral design (v6.1): only Grasshopper and IFC named | Positions DG as platform-agnostic — stress this for the openBIM audience |

#### Recommended redesign

Replace the generic Venn diagram with a **two-column bridge diagram** (vertical alignment, clean lines):

```
openBIM stack (left)                DG v6.1 layers (right)
─────────────────────               ──────────────────────
IFC4.3 product model        ←→     OntoGraph
(IfcSpace, IfcWall, IfcElement)      (IFC-class-aligned Class nodes)

IFC4.3 IfcConstraint/IfcMetric  ✗   Metagraph / SWRL
(descriptive only — no execution)     (executable rules: ClassAtom,
 ← IFC GAP #1 →                       DataPropertyAtom, BuiltinAtom)

IDS / mvdXML / bSDD             ←   ValidationGraph
(delivered-model verification)         (exports IDS-checkable requirements)
                                       ValidationRun → BCF-ready results

ISO 19650 / EIR / LOIN          ≈    SpecGraph
(what information is required)         (project specification notes/tags)

No parametric representation    ✗   ComputationGraph
in IFC/IDS                            (Algorithm → Procedure → Pattern;
 ← IFC GAP #2 →                       Grasshopper parametric logic)
```

**Bridge annotations:**
- `←→` = DG bridges to / aligns with this IFC concept
- `←` = DG outputs downstream to this standard
- `✗ IFC GAP` = DG fills a gap that IFC does not address
- `≈` = partial alignment / complementary coverage

**Caption:** «DG is not an IFC replacement. OntoGraph speaks IFC class vocabulary; ValidationGraph produces IDS-checkable outputs and BCF-ready results. Metagraph and ComputationGraph fill the two gaps IFC deliberately leaves: executable design rules and parametric generative logic.»

#### Where to place in the slide deck

**Primary placement — New Slide A** (openBIM positioning): Use the redesigned figure as the *visual* on the left half of the slide; keep the 5×5 comparison table as the *textual* summary on the right half. Together they give both visual and analytical coverage of the same argument.

**Secondary placement — Slide 8** (Two Interfaces, One Knowledge Core): Use a simplified version (just the bridge column, without the full stack) to replace the unreadable n8n/Neo4j screenshot. Shows the Grammar Domain (Metagraph/SWRL) above, the Model Domain (OntoGraph/IFC classes) below, joined by the Bridge.

---

### Schema 2 — "Data Flow in Data-Driven Design" (tab `3_GenerativeSystems`)

#### What the current schema shows

A **three-column layered data-flow diagram**:
- **Comm. layer** (left): Web Services (GoogleMaps, OSM, EPW, TransitLand, Social Web), Cloud Services
- **DAG layer** (centre): Graph definition, Training Datasets, WebApps; labelled "AI assistance & ML Analysis", "Real-time Datasets integration", "GUI User–System Interaction"
- **Data layer** (right): Database
- Bidirectional arrows connecting the layers; data-type annotations listing: geospatial, weather, public transport, social data

#### Problems against the v6.1 ontology and ptBIM audience

1. **No BIM data sources.** The inputs are GoogleMaps, OSM, EPW, TransitLand — none of which are the actual data sources in DG. The real inputs are an IFC/BIM model, natural-language rule text, and a Grasshopper parametric definition. This looks like a smart-city system, not architectural compliance checking.
2. **"DAG" is unexplained** — the presentation instructions already flag this as a credibility problem. The v6.1 `ComputationGraph` layer (Algorithm → Procedure → Pattern) is the conceptual answer but is not shown.
3. **The rule pipeline is absent.** DG's most distinctive data flow — NL text → constrained LLM → SWRL atoms → Neo4j Metagraph — does not appear at all.
4. **Outputs are invisible.** The diagram ends at "Database"; the actual outputs (validation overlay in external 3D viewer, BCF-ready issues, IDS-checkable rule export) are missing.
5. **Training Datasets shown as a runtime flow component.** These are offline artefacts, not part of the live data pipeline; showing them here conflates LLM training with runtime operation.
6. **Three layers don't map clearly to the five DG layers.** The architecture the slides describe has five named layers; the diagram shows three with different names, creating inconsistency.

#### What v6.1 now makes possible (ontology evidence for the redesign)

| v6.1 fact | Implication for the figure |
|---|---|
| n8n runs two webhook workflows: `rules-ingest` (NL → SWRL → Neo4j) and `graph-query` (NL → Cypher → answer) | The "Comm. layer" should show these two named pipelines, not generic Web Services |
| `dgm:Rule`/`dgm:Atom` (Metagraph) are created by the rules-ingest workflow from constrained LLM output | Show the NL → LLM → SWRL → Metagraph path explicitly |
| `dg:Class` / `dg:DatatypeProperty` nodes in OntoGraph are dynamically created from user prompts | Show IFC model / user input → OntoGraph as the schema-creation path |
| `dgv:ValidationRun` → `dgv:ValidationEntity` → `dgv:ObjectInstance` → `dgv:GeoRef` tracks validated geometry | Show Grasshopper → DesignState → ValidationRun → output as the validation path |
| `dgc:ComputationGraph` (Algorithm → Procedure → Pattern → Parameter) is the formalized "DAG" | Replace the generic "DAG layer" label with "ComputationGraph (parametric definition)" |
| `dgv:IntegrationConfig` links to the external platform (vendor-neutral since v6.1) | Show the output as "external 3D viewer overlay" + "IDS-checkable export" |

#### Recommended redesign

Replace the generic data-sources diagram with a **four-column BIM-grounded data flow**, left to right:

```
INPUT               INGEST              CORE                OUTPUT
──────              ──────              ────                ──────
IFC / BIM model  → OntoGraph        →  Neo4j             → Validation
(IfcSpace, Wall,   (dynamic IFC-       (4 layers:          overlay
 Element geometry)  aligned classes     OntoGraph,          (ext. 3D viewer,
                    from NL prompts)    Metagraph,          BCF-ready)
NL rule text     → n8n rules-ingest    ValidationGraph,
                   + LLM (SWRL)     →  SpecGraph)        → IDS-checkable
                   → Metagraph                             requirement
                     (Rule/Atom)                           export

Grasshopper      → ComputationGraph → Reasoner           → Coloured
definition          (Algorithm →       (rule evaluation)   pass/fail
(parametric)        Procedure →      → ValidationRun       per element
                    Pattern →          → ValidationEntity
                    Parameter)         → ObjectInstance
```

**Layer label fix:** Replace "DAG layer" with **"ComputationGraph layer (Algorithm / Procedure / Pattern)"**. Expand on first use: «DAG (directed acyclic graph of the parametric algorithm)».

**Remove from the diagram:** Training Datasets, GoogleMaps, OSM, EPW, TransitLand, Social Web — these are not part of DG's data pipeline. Move Training Datasets to a footnote or backup slide if the LLM training context is needed.

**Caption:** «DG's data flow connects three authoring environments (BIM model, natural-language rules, parametric definition) through a shared Neo4j knowledge core to a single validation output per design state. The core is platform-neutral; only Grasshopper and IFC are named at the edges.»

#### Where to place in the slide deck

**Primary placement — Slide 7** (System Framework — Five Layers): Use the redesigned four-column flow as the main visual, replacing the unreadable concentric-ring radial diagram. The ring is dense at projection size and uses unexplained acronyms; the column flow is readable, maps the five layers visibly, and gives each layer a BIM-equivalent tag as the slide already requests.

**Secondary placement — backup slide**: Keep the original three-column version (after cleaning up the off-topic data sources) as a backup slide for the Q&A question "How does the system actually work at runtime?" — it shows the live data pipeline at a glance.

---

### How the two schemas complement each other in the talk

| Schema | Question it answers | Recommended slide |
|---|---|---|
| IFC integration bridge diagram | "Where does DG fit in the openBIM world?" (structural / standards positioning) | New Slide A (primary); Slide 8 (simplified) |
| Data Flow four-column diagram | "How does data actually move through DG?" (operational / pipeline view) | Slide 7 (primary); backup slide |

Together they address the two hardest audience questions in one visual pass: the structural positioning question (IFC bridge) and the "how does it actually work?" question (data flow). Neither currently in the deck provides a clear answer to both.

---

### Drawio source edit instructions

Both improved schemas should be drafted in `Publications/900_00_Procedural Design Ontology.drawio`:

- **IFC integration bridge diagram:** Edit the `IFC integrated` tab. Remove the five generic ontology Venn circles. Replace with the two-column bridge layout described above. Use the existing colour scheme (blue for IFC/openBIM side, green/orange for DG layers). Add red dashed borders labelled "IFC GAP #1" and "IFC GAP #2" around the Metagraph and ComputationGraph boxes.
- **Data Flow four-column diagram:** Edit the `3_GenerativeSystems` tab. Replace the three columns (Comm./DAG/Data) with four columns (Input/Ingest/Core/Output). Remove the generic data-source annotations (GoogleMaps etc.) and substitute BIM-specific labels. Rename the "DAG layer" band to "ComputationGraph layer". Keep the existing colour band style (pink/orange/blue backgrounds); assign: Input = blue (IFC/BIM register), Ingest = orange (communication/workflow layer), Core = green (knowledge core), Output = purple (results/standards).

---

## Priority order (if time is limited, do 1–4)
1. **New Slide C** (Design Knowledge definition) — anchors the term the whole talk depends on; cheap to add, high clarity payoff. Place right after the Table of Contents.
1. **New Slide A** (openBIM positioning table + IFC bridge figure) — pre-empts the killer question; add the redesigned IFC integration schema as the visual alongside the table.
2. **Slide 4** — name IFC4.3, IDS, mvdXML, bSDD precisely.
3. **Slide 13** — add metrics + reframe IDS as complement.
4. **Slide 7** — replace radial diagram with the redesigned four-column data-flow figure; add "BIM equivalent" band labels.
5. **Slide 12** — enlarge validation payoff; one regulation-style rule end-to-end.
6. Slides 3 + 9 — ISO 19650 / CDE language. 7. New Slide B (prior art). 8. References. 9. Slides 10–11 worked rule + numbers. 10. Finalise drawio edits and export both figures as PNG/SVG for insertion.

## Editor's final checklist
- [ ] No text overflow after edits (re-export PDF and skim).
- [ ] Fonts/colours unchanged from master.
- [ ] New Slides C, A and B match content-slide layout and numbering updated.
- [ ] New Slide C (Design Knowledge definition) inserted after the Table of Contents; framing avoids "IFC is just geometry" and states the gap as "no executable design rules / parametric logic" instead.
- [ ] Placeholder counts (N, M, K, R, A, P, Q, S) replaced with real case-study figures.
- [ ] IDS now appears as a *complement* (slides 4, A, 13), not only as future work.
- [ ] IFC integration bridge figure added to New Slide A (from `IFC integrated` tab, redesigned).
- [ ] Data flow four-column figure added to Slide 7 (from `3_GenerativeSystems` tab, redesigned).
- [ ] "DAG" expanded on first use in Slide 7 figure and speaker notes.
- [ ] Generic data sources (GoogleMaps, OSM, EPW) removed from the data-flow figure or moved to a backup slide.
- [ ] Both drawio tabs edited and figures exported before inserting into pptx.
