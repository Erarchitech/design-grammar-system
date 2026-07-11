# ptBIM 2026 — BIM-Context Improvement Plan

**Deck:** `01_ptBIM26_R2.pdf` — *Management of the Design Knowledge Core in a Cross-Platform Environment of the BIM Project* (Design Grammars / DG)
**Audience:** BIM experts and AEC academics (ptBIM is Portugal's national BIM conference; the room knows IFC, ISO 19650, openBIM and the automated code-compliance literature)
**Author:** Evgenii Ermolenko, UMinho (Lab2PT / ISISE)
**Date:** 2026-06-04

---

## 1. Executive read

The deck tells a clean, generic *knowledge-management* story — "files travel, rules don't; let's share objects not files." That framing is correct but pitched one notch below where this audience lives. For ptBIM, the persuasive frame is not "knowledge gets lost," it is **"the existing openBIM information-delivery stack (IFC, IDS, bSDD, ISO 19650) cannot carry parametric design intent or machine-checkable design rules — here is how DG closes that specific gap."**

The single biggest risk: a BIM expert in the room will ask *"Why not just use IDS?"* or *"How does this round-trip to IFC?"* and the current deck only mentions IDS once, as deferred future work (slide 13). The improvements below re-anchor the talk in named BIM standards and the model-checking literature, without changing the underlying contribution.

Three themes drive every recommendation:

1. **Name the standards.** Replace generic terms ("files," "platforms," "the schema") with the vocabulary the audience checks for: IFC4 / IFC4.3, IDS, bSDD, mvdXML, BCF, ISO 19650 / LOIN / EIR, BOT and the W3C Linked Building Data stack.
2. **Position against prior art.** Automated Code Compliance Checking (ACC), semantic rule checking (Pauwels, Beach, Solibri/SMC) and shape grammars (Stiny) are the lineages this work sits in. Show you know them and how DG differs.
3. **Show evidence.** Academics want numbers: how many rules, how many SWRL atoms, encoding accuracy, case-study scale. The conclusion currently claims "academic evaluation" with zero metrics on screen.

---

## 2. Slide-by-slide gaps and fixes

### Slide 1 — Title
- **Gap:** Subtitle "cross-platform environment of the BIM project" is vague; the dual name "Design Grammars / Generative Copilot System" mixes a scholarly lineage (grammars) with hype ("Copilot").
- **Fix:** Add a one-line standfirst positioning the work against openBIM, e.g. *"Carrying parametric design intent and machine-checkable rules across the openBIM lifecycle."* Pick one primary name for the talk; keep "Generative Copilot" as a subtitle at most. Keep ORCID/funding line — good academic hygiene.

### Slide 2 — Table of contents
- **Gap:** Fine as structure, but "five layers, two domains" reads as internal jargon.
- **Fix:** Rename agenda item 3 to tie to BIM, e.g. *"System architecture — a semantic knowledge core alongside the BIM model."* Add a 6th item: *"Positioning — relation to IFC, IDS and ISO 19650"* (even 30 seconds explicitly addressing this de-risks the Q&A).

### Slide 3 — Hook ("How much design intent survives the next handover?")
- **Gap:** Strong rhetorical hook, but "handover" is exactly ISO 19650 territory and the deck doesn't claim it.
- **Fix:** Sharpen the subtitle with the standard's own language: design intent = the *rationale* behind the model that EIR / LOIN never formally capture; handovers transfer geometry + properties but not constraints. One added clause ("ISO 19650 governs *what* information is delivered, not the *design logic* that produced it") instantly raises the register for this room.

### Slide 5 — The problem (4 bullets)
This is the most important slide to upgrade because it states the BIM thesis.
- **Gaps:**
  - "IFC handles physical components well, but parametric relationships and abstract constraints fall outside its schema" — true but imprecise for experts. They will want the *specific* gap named.
  - No mention of IDS / mvdXML / bSDD, which is where "machine-checkable requirements" already live — the audience will assume you don't know them.
  - "Parametric tools (Grasshopper/Dynamo) replicate logic per platform" is a good point but undersold.
- **Fixes:**
  - Be precise about IFC: IFC4/IFC4.3 is a **product/object model** optimised for as-designed/as-built physical components and properties (Psets); it has no first-class representation for **design rules, parametric dependencies, or generative constraints**. `IfcConstraint`/`IfcMetric` exist but are descriptive, not executable. Say this explicitly.
  - Add a bullet acknowledging the existing checkable-requirement stack — **IDS** (buildingSMART Information Delivery Specification), **mvdXML**, **bSDD** — and state precisely what they *do* (presence/value checks on delivered models) versus what they *do not* (express generative/parametric design logic or relational design rules that produce the geometry). This is the slide that pre-empts "why not IDS?".
  - Reframe the Grasshopper/Dynamo point as **logic siloing**: the design rules live as opaque node graphs, are not interoperable, and die at export. That's the parametric analogue of the IFC gap.

### Slide 6 — Goal ("Shared Knowledge Core")
- **Gap:** "carries design intent across tools and phases — not just geometry" is good; the circuit-board DG icon adds nothing for this audience and the slide is 80% empty.
- **Fix:** Add a small inset contrasting **file-based exchange (IFC/BCF round-trips)** vs **object-level semantic reference**. Tie "design intent" to a concrete, BIM-legible example (e.g. "min. habitable-room area ≥ X m²" travels as a rule, not as a frozen wall position). Drop or shrink the decorative icon.

### Slide 6b — Approach (Core–Periphery)
- **Gap:** "Core–Periphery data model" with "BIM, parametric, analysis at the edge" is the heart of the contribution but stated abstractly.
- **Fix:** Map the periphery to **named, recognised representations**: BIM edge = IFC / native authoring model; parametric edge = Grasshopper definition; analysis edge = IDA/energy/structural. Make explicit that the **core is an ontology** (your DG ontology, aligned to BOT / Topologic / SOSA per the vault) and the edges are *views*. The academic version of this idea is **Linked Building Data**: say so and cite BOT.

### Slide 7 — System framework, five layers (radial diagram)
- **Gaps:** This is the weakest slide for the audience. The radial figure is dense and unreadable at projection size; labels use internal terms with no BIM anchor — "DAG Layer," "GAE," "Analysis Layer / Ontology control," "Communication Layer / Linking Data models." Nothing connects a layer to a BIM concept.
- **Fixes:**
  - **Redraw as a clean left-to-right stack** (5 horizontal bands), not a busy concentric ring. Reserve the ring for the paper.
  - For each layer add a **"BIM equivalent / standard" column**: Data Layer ↔ federated model / CDE; Communication Layer ↔ IFC + IDS + APIs; Analysis Layer (ontology) ↔ semantic model / LBD; Integration Layer ↔ MCP / connectors; DAG/Computation ↔ the generative (Grasshopper) logic.
  - Expand acronyms on first use (DAG = directed acyclic graph of the algorithm; GAE = generative algorithm environment). Unexplained acronyms read as unfinished work to reviewers.

### Slide 8 — Two interfaces, one knowledge core
- **Gaps:** The Model-Domain / Grammar-Domain split is a genuinely strong idea, but the right-hand architecture screenshot is illegible (tiny n8n/Neo4j flow). "Parsed by constrained LLM" will draw scrutiny without a reliability claim.
- **Fixes:**
  - Keep the two-column text; **replace the screenshot with a clean schematic**: Grammar Domain (NL rule → constrained LLM → SWRL atoms → Neo4j metagraph) on top of Model Domain (IFC-aligned classes → geometry/properties), joined by the Bridge.
  - State the **constraint mechanism** plainly: the LLM emits SWRL restricted to a fixed schema (ClassAtom / DataPropertyAtom / BuiltinAtom) and output is validated against the ontology before commit — this is your guard against hallucination and the audience will want it named.
  - Note IFC alignment concretely: which IFC classes map to your `Class` nodes (e.g. `IfcSpace`, `IfcWall`), so "IFC-aligned" is demonstrable, not asserted.

### Slide 9 — Data layer (multi-DB ring)
- **Gaps:** Polyglot-persistence diagram (Graph/Relational/Time-series/Spatial/NoSQL) is engineering-facing; for a BIM-research audience the relevant claim is **single source of truth per object**, which maps directly to the **CDE / federated-model** concept in ISO 19650 — but that link is missing. Risks looking like an implementation slide.
- **Fixes:** Lead with the BIM idea: "one authoritative definition per object, referenced — not copied — across disciplines" is the semantic-web answer to model federation and clash of duplicated data. Name the parallel to a **CDE** and to **linked data** (IRIs as the object identity). Consider demoting the multi-DB detail to a backup slide.

### Slides 10–11 — Use case 1, plan-layout generation
- **Gaps:** Visually rich but unguided. The raw room-schedule table and the spatial-relationship graph are shown without a worked thread; the BIM audience can't see the **rule → result** chain. "Solution space of valid alternatives" is asserted, not shown with a constraint.
- **Fixes:**
  - Walk **one** concrete spatial rule end-to-end: e.g. "kitchen must be adjacent to dining" or "every habitable room needs exterior daylight access" → encoded once in the graph → drives generation → invalid layouts pruned. Show *before/after*.
  - Tie the room program to a **recognised classification** (Uniclass spaces, or IFC `IfcSpace` + space-type Pset) so the "spatial program" is grounded in BIM data, not an ad-hoc table.
  - State the scale: how many rooms, relationships, generated alternatives. Numbers make it research, not a demo.

### Slide 12 — Use case 2, design-state validation
- **Gaps:** The five-step pipeline (Client Brief → Rule Authoring → Bootstrap → Validate → Communicate) is the clearest BIM story in the deck but is rendered as a dense screenshot wall; the colour-coded validation result (the payoff) is too small to read.
- **Fixes:**
  - Blow up the **validation payoff**: the colour-coded 3D model (pass/fail per element) is the money shot for this audience — give it a full half-slide.
  - Show the actual **rule text → SWRL → graph → coloured element** for one rule, ideally a **regulation-style constraint** (e.g. a height limit or fire-egress width) so it reads as compliance checking, which is the ACC literature they know.
  - Name the result-communication channel in BIM terms — issues as **BCF**-style topics if applicable; if not, say why your overlay approach differs.

### Slide 13 — Conclusion
- **Gaps:** Honest limitations (good), but **no quantitative results anywhere**, and **IDS appears for the first and only time as deferred future work** — which inadvertently confirms the gap a reviewer worries about. "LLM Cypher output still needs human review" is stated without an accuracy figure.
- **Fixes:**
  - Add **metrics**: # rules encoded, # SWRL atoms, encoding precision/recall or accuracy (the T1 draft's "точность кодирования" — surface that number), case-study size. Even modest numbers beat none.
  - Reframe **IDS** from "future work" to a **positioning statement**: "DG complements IDS — IDS verifies delivered information; DG carries the generative design logic upstream and can *export* IDS-checkable requirements." That turns a perceived weakness into an interoperability roadmap.
  - Keep the SWRL-coverage and human-in-the-loop limitations — honesty plays well — but pair each with a next step.

### Slide 14 — References
- **Gap:** Strong on design theory (Gero, Cross, Dorst, Schön) and semantic web (Sack, BOT, Topologic), but **thin on contemporary BIM/AEC compliance-checking and openBIM standards** — the literature this audience publishes in.
- **Fix:** Add the standards and ACC anchors listed in §5 below.

---

## 3. Recommended new / restructured slides

Insert two short slides; they directly neutralise the hardest audience questions.

**New Slide A — "Where DG sits in the openBIM stack" (after slide 5).**
A single comparison table:

| Concern | IFC4 / IFC4.3 | IDS / mvdXML / bSDD | ISO 19650 / LOIN | **Design Grammars** |
|---|---|---|---|---|
| Physical components & properties | ✓ | — | (governs) | references |
| Machine-checkable *delivered* requirements | — | ✓ | (specifies) | exports to |
| Parametric / generative design logic | — | — | — | **✓** |
| Relational design rules (SWRL) | descriptive only | value/presence checks | — | **✓ executable** |
| Cross-tool object identity (linked data) | partial | — | — | **✓ (ontology/IRIs)** |

This one table is the highest-value addition in the whole plan.

**New Slide B — "Relation to prior art" (before or within conclusion).**
Three short rows: (1) Automated Code Compliance Checking (Solibri/SMC, Beach et al., Eastman survey) — DG differs by encoding rules from NL via LLM into an open ontology rather than hard-coded checkers; (2) Semantic rule checking / LBD (Pauwels, BOT, SHACL) — DG adds the *generative* (grammar) side, not just checking; (3) Shape/design grammars (Stiny) — DG operationalises grammar rules in a live BIM/parametric pipeline. Shows scholarly self-location.

---

## 4. Anticipated Q&A (prepare backup slides)

1. **"Why not just use IDS / mvdXML?"** → New Slide A; IDS checks delivered models, DG carries upstream generative logic and can emit IDS.
2. **"How does this round-trip to IFC? Is it openBIM or locked to Grasshopper/Speckle?"** → Per the vault's vendor-neutrality decision, the ontology is platform-neutral (only Grasshopper + IFC named); Speckle/Rhino are swappable implementation. Say this; it's a real strength.
3. **"How reliable is the LLM rule encoding?"** → Constrained SWRL schema + ontology validation + human review; give the accuracy metric from T1.
4. **"How does this scale beyond a single dwelling?"** → Be honest (academic eval only) but state the federation/CDE path.
5. **"Isn't SWRL/OWL reasoning a known performance/expressivity bottleneck?"** → Acknowledge; note you use a restricted atom set (ClassAtom/DataPropertyAtom/BuiltinAtom) deliberately for decidability and LLM tractability.
6. **"How do results get back to the team?"** → Coloured model overlay today; BCF/issue export as a roadmap item.

---

## 5. References to add

- buildingSMART — **IDS (Information Delivery Specification)** technical documentation; **mvdXML**; **bSDD**.
- **ISO 16739-1** (IFC4.3) and **ISO 19650-1/-2** (information management); **LOIN / ISO 7817**.
- Eastman, C., Lee, J., Jeong, Y., Lee, J. (2009). *Automatic rule-based checking of building designs.* Automation in Construction.
- Beach, T., Rezgui, Y., et al. — regulatory/compliance knowledge representation for BIM.
- Pauwels, P., Zhang, S., Lee, Y.-C. (2017). *Semantic web technologies in AEC: A literature overview.* Automation in Construction.
- Solibri Model Checker (SMC) — as the representative commercial ACC baseline.
- Stiny, G. (1980). *Introduction to shape and shape grammars* — anchor the "grammar" lineage explicitly.
- (Already present and good: BOT [14,17], Topologic [15,16], SWRL [19], IFC-graph [22].)

---

## 6. Priorities (do these first)

1. **New Slide A — openBIM positioning table.** Highest impact, lowest effort; pre-empts the killer question. *(High / Low)*
2. **Slide 5 rewrite — name IFC4.3, IDS, mvdXML, bSDD precisely.** *(High / Low)*
3. **Slide 13 — add metrics + reframe IDS as complement not gap.** *(High / Low)*
4. **Slide 7 — redraw five layers as a legible stack with a "BIM equivalent" column.** *(High / Medium)*
5. **Slide 12 — enlarge the coloured validation payoff; show one regulation-style rule end-to-end.** *(High / Medium)*
6. **Slide 3 + 9 — adopt ISO 19650 / CDE language for the handover and single-source-of-truth claims.** *(Medium / Low)*
7. **New Slide B — prior-art positioning (ACC, LBD, shape grammars).** *(Medium / Low)*
8. **References top-up (§5).** *(Medium / Low)*
9. **Slides 10–11 — one worked spatial rule, with scale numbers and Uniclass/IfcSpace grounding.** *(Medium / Medium)*

Effort is roughly *content edits* (1–3, 6–8) vs *redraw a figure* (4, 5, 9). Items 1–3 alone shift the talk decisively toward the BIM-expert register.

---

*Sources: deck `Publications/01_ptBIM26_R2.pdf`; DG knowledge vault — `knowledge/publications/index.md` (T1–T4 series, ptBIM as the T1 base paper), `knowledge/decisions/DG ontology must be vendor-neutral except Grasshopper and IFC.md`, `sessions/2026-06-01 Ontology v6.0 restructure`.*
