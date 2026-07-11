# Presentation Improvement Plan

## Deck Summary
- Purpose: Explain and justify the Design Grammars approach for carrying design intent across openBIM workflows, and show prototype feasibility.
- Audience: Mixed PT Beam session (about 70% practitioners, 30% academics, low ontology literacy).
- Core story (1-2 lines): Current BIM exchange preserves model state but loses design logic; Design Grammars adds a shared semantic layer to carry and validate that logic across tools.
- Overall strengths: Strong technical depth, clear research contribution, complete pipeline narrative.
- Top risks: Audience-level mismatch, abstraction overload early, text density, inconsistent slide numbering, and limited visual simplification.

## Global Style and Narrative Fixes
- Priority 1: Restructure to Scope -> Gap -> Solution. First third must level ontology/graph basics with plain-language examples.
- Priority 2: Aggressively reduce text density. Enforce one message per slide, max 3 bullets, move explanatory paragraphs to speaker notes.
- Priority 3: Increase readability baseline: minimum 14-15 font size everywhere (including figure labels/captions).
- Priority 4 (Slide numbering for Q&A): Add visible slide numbers on every slide in one consistent location and style.
- Priority 5 (Minimalism and de-cluttering): Remove bottom explanatory blocks, remove redundant labels, remove non-essential citations from content slides.

## Slide-by-Slide Plan
### Slide 1 - Title and Positioning
- Scorecard (1-5):
- coherence: 3
- clarity: 3
- visual hierarchy: 2
- graphics quality: 3
- Current issue(s): Too much metadata on opening slide; weak audience hook; title line is long and hard to parse quickly.
- Narrative fix: Open with a concise problem-first headline and one subtitle that states the practical value.
- Visual/graphics fix: Keep only title, presenter, affiliation, and one visual motif; move grant/reference details to final or backup slide.
- Exact edit actions: Shorten title to one line; add one-line value proposition subtitle; remove ORCID blocks from main slide body.
- Rewrite suggestions:
- headline: Why BIM Loses Design Intent and How Design Grammars Restores It
- body copy: A shared semantic core that carries parametric rules across openBIM handovers.
- De-clutter action (what to remove/split): Remove long funding and affiliation paragraph blocks from the visible canvas.
- Priority: High
- Estimated effort: M

### Slide 2 - Agenda
- Scorecard (1-5):
- coherence: 3
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Agenda reflects technical sequence, not audience learning sequence.
- Narrative fix: Reorder agenda to Scope -> Gap -> Solution -> Evidence -> Limits.
- Visual/graphics fix: Convert to 5 short agenda items with numbering and timing cue.
- Exact edit actions: Replace current list with 5-part storyline; highlight where practical takeaway appears.
- Rewrite suggestions:
- headline: Talk Roadmap
- body copy: 1) Why current BIM handovers fail to carry intent 2) What knowledge layer is missing 3) Proposed system 4) Prototype evidence 5) Limits and next steps
- De-clutter action (what to remove/split): Remove secondary subtitle repetition from this slide.
- Priority: High
- Estimated effort: S

### Slide 3 - Design Knowledge Definition
- Scorecard (1-5):
- coherence: 4
- clarity: 2
- visual hierarchy: 2
- graphics quality: 3
- Current issue(s): Definition is accurate but too long; too many clauses for spoken delivery.
- Narrative fix: Keep one formal definition sentence plus one plain-language translation.
- Visual/graphics fix: Split into two zones: Definition and In Plain Terms.
- Exact edit actions: Keep technical definition in smaller callout; replace long paragraph with 3 key nouns: intent, constraints, generation.
- Rewrite suggestions:
- headline: Design Knowledge: The Logic Behind the Model
- body copy: Design knowledge is the machine-readable intent, constraints, and generative logic that produce a model, not just the model's final geometry.
- De-clutter action (what to remove/split): Remove repeated lifecycle sentence from this slide and place in speaker notes.
- Priority: High
- Estimated effort: M

### Slide 4 - FBS Framing
- Scorecard (1-5):
- coherence: 3
- clarity: 2
- visual hierarchy: 2
- graphics quality: 2
- Current issue(s): Consultation conflict confirmed here: BIM/IFC appears as Structure only; dense explanatory text; divisive diagram framing.
- Narrative fix: Explain FBS as complementary layers, then state DG focus is function + logic capture.
- Visual/graphics fix: Remove vertical dividing lines; remove BIM/IFC labels from FBS categorization per consultation decision.
- Exact edit actions: Keep one compact FBS diagram; add one sentence: IFC captures state, DG captures intent and rules.
- Rewrite suggestions:
- headline: FBS as a Lens for What Is Captured vs Lost
- body copy: IFC represents realized structure. Design Grammars represent the function and rule logic that generated it.
- De-clutter action (what to remove/split): Remove bottom descriptive paragraph and all repeated IFC object lists.
- Priority: High
- Estimated effort: M

### Slide 5 - Design State
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Definition is still technical and hash footnote competes with main message.
- Narrative fix: Emphasize that Design State is a timestamped snapshot, not the full design rationale.
- Visual/graphics fix: Use one simple timeline or snapshot icon; move SHA detail to backup slide.
- Exact edit actions: Reduce text to one sentence and one implication bullet.
- Rewrite suggestions:
- headline: Design State = Snapshot, Not Design Reasoning
- body copy: A design state captures parameter values and geometry assignments at a moment in time; it does not preserve the full rule logic.
- De-clutter action (what to remove/split): Remove cryptographic standard footnote from visible content.
- Priority: Medium
- Estimated effort: S

### Slide 6 - Three Pillars
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Message is conceptually strong but written as dense prose.
- Narrative fix: Convert to three short claims tied to practitioner value.
- Visual/graphics fix: 3-column card layout with icon per pillar.
- Exact edit actions: Replace paragraph with 3 cards: Formalized, Shared, Executable.
- Rewrite suggestions:
- headline: Three Pillars of Design Knowledge
- body copy: Formalized in ontology, shared across tools, executable for generation and validation.
- De-clutter action (what to remove/split): Move VPE definition to notes.
- Priority: Medium
- Estimated effort: M

### Slide 7 - Lifecycle Loss Problem
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Good thematic slide but lacks concrete consequence.
- Narrative fix: Add one quantified question and one example of loss at handover.
- Visual/graphics fix: Use funnel/erosion graphic from concept to maintenance.
- Exact edit actions: Keep only one sentence and one visual; remove extra caption text.
- Rewrite suggestions:
- headline: Each Handover Preserves Data but Loses Intent
- body copy: Standards govern what is delivered, not why the design is valid.
- De-clutter action (what to remove/split): Remove secondary explanatory line if repeated verbally.
- Priority: Medium
- Estimated effort: S

### Slide 8 - Knowledge Gap
- Scorecard (1-5):
- coherence: 4
- clarity: 2
- visual hierarchy: 2
- graphics quality: 2
- Current issue(s): Too many bullets and nested technical details; audience overload risk is high.
- Narrative fix: Collapse into 3 pain points: IFC limits, IDS scope, parametric silo.
- Visual/graphics fix: Use one comparison table (Today vs Needed) with max 3 rows.
- Exact edit actions: Delete long bullet prose; keep concise statements with one practical example.
- Rewrite suggestions:
- headline: The Knowledge Gap in Today’s BIM Exchange
- body copy: We exchange model outcomes, not reusable design rules. IFC and IDS verify delivery, but do not carry generative intent.
- De-clutter action (what to remove/split): Split deep technical caveats into backup slides.
- Priority: High
- Estimated effort: M

### Slide 9 - Proposed System Intro
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Intro card is brief but does not bridge from gap to solution explicitly.
- Narrative fix: Add one transition sentence: therefore we propose.
- Visual/graphics fix: Add single architecture thumbnail and one-line promise.
- Exact edit actions: Keep title and add one sentence connecting Slide 8 to system proposal.
- Rewrite suggestions:
- headline: Proposed Response: Design Grammars
- body copy: To close the knowledge gap, we introduce a shared rule-centric semantic core across tools.
- De-clutter action (what to remove/split): Remove duplicated branding text if repeated elsewhere.
- Priority: Medium
- Estimated effort: S

### Slide 10 - Goal
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Goal is clear but long sentence and example line are text-heavy.
- Narrative fix: Keep one goal sentence plus one relatable example.
- Visual/graphics fix: Use before/after graphic (file exchange vs object-level knowledge sharing).
- Exact edit actions: Tighten wording to one line each for goal and example.
- Rewrite suggestions:
- headline: Goal: Reuse Design Intent Across BIM Handover
- body copy: Build a shared knowledge core that carries reusable rules across platforms for generation and validation.
- De-clutter action (what to remove/split): Remove decorative uppercase transition block if shown on multiple slides.
- Priority: Medium
- Estimated effort: S

### Slide 11 - Approach
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 2
- graphics quality: 3
- Current issue(s): Bullet list is long and partially repetitive.
- Narrative fix: Distill to 3 approach components: core-periphery model, semantic identity, edge adapters.
- Visual/graphics fix: Replace bullets with triangular or hub-and-spoke diagram.
- Exact edit actions: Keep max 3 bullets and one small explanatory line.
- Rewrite suggestions:
- headline: Approach: Core Knowledge, Tool-Specific Edges
- body copy: A shared ontology core maintains identity and rules while each platform keeps its native representation.
- De-clutter action (what to remove/split): Remove parenthetical lists of edge tools from main text.
- Priority: High
- Estimated effort: M

### Slide 12 - Positioning in openBIM Stack
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 4
- Current issue(s): Useful comparison but row labels are dense and hard to scan quickly.
- Narrative fix: Keep this as the key positioning slide, but simplify language and highlight one takeaway.
- Visual/graphics fix: Use check/cross matrix with 4 concern rows max and bold takeaway annotation.
- Exact edit actions: Reduce concern list; enlarge table text to minimum 14-15; add takeaway callout.
- Rewrite suggestions:
- headline: Design Grammars Complements IFC and IDS
- body copy: IFC captures product structure, IDS checks delivery requirements, and Design Grammars carries executable generative logic upstream.
- De-clutter action (what to remove/split): Remove secondary standards labels that do not change decision-making.
- Priority: High
- Estimated effort: M

### Slide 13 - Relation to State of the Art
- Scorecard (1-5):
- coherence: 3
- clarity: 2
- visual hierarchy: 2
- graphics quality: 3
- Current issue(s): Citation-heavy prose prevents comprehension during live talk.
- Narrative fix: Reframe as 3 comparisons: code-checking, semantic checking, grammars.
- Visual/graphics fix: Use 3-column "Existing -> Limitation -> DG Addition" matrix.
- Exact edit actions: Replace sentence citations with compact tags (Author, Year) and move full references to final slide.
- Rewrite suggestions:
- headline: What Exists and What DG Adds
- body copy: Prior work checks compliance or models semantics; DG adds executable generative rule flow across BIM and parametric environments.
- De-clutter action (what to remove/split): Remove long parenthetical author strings from main body.
- Priority: High
- Estimated effort: M

### Slide 14 - System Framework (5 Layers)
- Scorecard (1-5):
- coherence: 3
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Layer labels are abstract without immediate meaning.
- Narrative fix: Introduce with one guiding sentence: from semantics to validation outcome.
- Visual/graphics fix: Add directional flow arrows and one verb per layer.
- Exact edit actions: Keep layer labels but add short action verbs.
- Rewrite suggestions:
- headline: Five-Layer Framework from Semantics to Validation
- body copy: The stack links knowledge definition, rule logic, execution, and integration into one reusable workflow.
- De-clutter action (what to remove/split): Remove non-essential sublabels and repeated branding.
- Priority: Medium
- Estimated effort: M

### Slide 15 - DG Ontology Mapping
- Scorecard (1-5):
- coherence: 3
- clarity: 1
- visual hierarchy: 1
- graphics quality: 2
- Current issue(s): Extremely dense symbolic mapping; high risk of immediate audience disengagement.
- Narrative fix: Either convert to high-level summary or move to backup; keep only key message in main deck.
- Visual/graphics fix: Show 4 layer names and one mapping example, not full equivalence list.
- Exact edit actions: Create simplified version for main talk; retain full table in backup appendix.
- Rewrite suggestions:
- headline: Ontology Alignment: Four Layers, One Semantic Backbone
- body copy: DG aligns ontology, rule, validation, and knowledge layers to established semantic web standards.
- De-clutter action (what to remove/split): Remove full line-by-line symbol mappings from live slide.
- Priority: High
- Estimated effort: L

### Slide 16 - Prototype Architecture
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Text extraction suggests mostly visual slide; clarity depends on labeling quality.
- Narrative fix: Add one explicit outcome line: what this architecture enables in practice.
- Visual/graphics fix: Ensure directional arrows, numbered flow, and readable labels >=14.
- Exact edit actions: Add 3-step legend (input, transformation, output).
- Rewrite suggestions:
- headline: Prototype Architecture
- body copy: Rule authoring, semantic processing, and validation feedback are connected in one operational loop.
- De-clutter action (what to remove/split): Remove minor component labels that are not discussed orally.
- Priority: Medium
- Estimated effort: M

### Slide 17 - Use Case Overview
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Good bridge to evidence but title is long and generic.
- Narrative fix: Frame as one end-to-end story from brief to validated state.
- Visual/graphics fix: Use numbered timeline with 4 phases and one outcome marker.
- Exact edit actions: Add a short use-case statement with project type and expected check.
- Rewrite suggestions:
- headline: Use Case: From Client Brief to Validated Design State
- body copy: We translate natural-language requirements into executable rules and validate iterative design states.
- De-clutter action (what to remove/split): Remove repeated prototype branding on this slide.
- Priority: Medium
- Estimated effort: S

### Slide 18 - Phase 1-2 (Rule Authoring)
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Potentially tool-centric rather than value-centric explanation.
- Narrative fix: State user action and value: author rules once, reuse many times.
- Visual/graphics fix: Show before/after screenshot annotation with one focal highlight.
- Exact edit actions: Add one key metric or qualitative result from phase.
- Rewrite suggestions:
- headline: Phase 1-2: Author Rules from Client Brief
- body copy: The Grammar Viewer captures requirements as reusable machine-readable rules.
- De-clutter action (what to remove/split): Remove interface details not needed for audience understanding.
- Priority: Medium
- Estimated effort: S

### Slide 19 - Phase 3 (Design Bootstrap)
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Needs explicit linkage from authored rules to parametric generation.
- Narrative fix: Emphasize rule activation in design environment.
- Visual/graphics fix: Add one simple sequence: rule set -> add-in -> generated/checked state.
- Exact edit actions: Include one concrete design rule example shown in Grasshopper context.
- Rewrite suggestions:
- headline: Phase 3: Bootstrap Design with Rule-Aware Add-in
- body copy: Grasshopper consumes rule knowledge to guide and test design alternatives.
- De-clutter action (what to remove/split): Remove tool labels that are not referenced verbally.
- Priority: Medium
- Estimated effort: S

### Slide 20 - Phase 4 (Validation & Communication)
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 3
- graphics quality: 3
- Current issue(s): Phase value is implied, not explicitly measured.
- Narrative fix: Clarify who receives validation output and how decisions are improved.
- Visual/graphics fix: Add output artifact thumbnail (report/view) with pass-fail indicators.
- Exact edit actions: Insert one outcome bullet: faster review, clearer traceability, fewer reinterpretations.
- Rewrite suggestions:
- headline: Phase 4: Validate and Communicate Design State
- body copy: The Design State Viewer reports rule compliance and supports cross-discipline decision-making.
- De-clutter action (what to remove/split): Remove minor UI annotations and keep one hero screenshot.
- Priority: Medium
- Estimated effort: S

### Slide 21 - Conclusion and Contribution
- Scorecard (1-5):
- coherence: 4
- clarity: 3
- visual hierarchy: 2
- graphics quality: 3
- Current issue(s): Contains too many bullets and placeholder metrics (R/A/P/Q/S), reducing credibility in live delivery.
- Narrative fix: Conclude with 3 claims: contribution, evidence, limits.
- Visual/graphics fix: Use 3 blocks with icon headings instead of dense bullets.
- Exact edit actions: Replace placeholders with either real values or remove quantitative placeholders.
- Rewrite suggestions:
- headline: Contribution, Evidence, and Next Step
- body copy: We demonstrate a working prototype that captures and reuses design rules across generation and validation; next step is broader SWRL and production-scale testing.
- De-clutter action (what to remove/split): Remove placeholder metric line unless final numbers are available.
- Priority: High
- Estimated effort: M

### Slide 22 - Thank You
- Scorecard (1-5):
- coherence: 4
- clarity: 5
- visual hierarchy: 4
- graphics quality: 4
- Current issue(s): Effective closure but lacks clear Q&A prompt and contact option.
- Narrative fix: Add one invitation line for questions linked to numbered slides.
- Visual/graphics fix: Keep minimal and add contact/QR if appropriate.
- Exact edit actions: Add "Questions? Please refer to slide number" subtitle.
- Rewrite suggestions:
- headline: Thank You
- body copy: Questions are welcome. Please reference the slide number for quick navigation.
- De-clutter action (what to remove/split): Keep only logo, thanks line, and Q&A prompt.
- Priority: Low
- Estimated effort: S

### Slide 23 - References
- Scorecard (1-5):
- coherence: 3
- clarity: 2
- visual hierarchy: 2
- graphics quality: 2
- Current issue(s): Very dense and likely unreadable at conference distance.
- Narrative fix: Keep full references for record, but show a reduced "Key References" set in live mode.
- Visual/graphics fix: Split into 2 backup slides or provide QR link to full bibliography.
- Exact edit actions: Keep 6-8 primary references on visible slide; move full list to appendix/backup.
- Rewrite suggestions:
- headline: Key References
- body copy: Full bibliography available in backup slides or QR-linked handout.
- De-clutter action (what to remove/split): Split long list into backup material not shown in timed talk.
- Priority: Medium
- Estimated effort: M

## Rewrite Snippets (Required)
- Slide 1 headline alternatives: 1) From BIM State Exchange to Design Logic Exchange 2) Preserving Design Intent Across openBIM 3) Design Grammars for Rule-Carrying BIM Workflows
- Slide 8 tighter body copy: BIM exchanges preserve geometry and properties, but lose reusable rule logic. IFC describes products; IDS verifies delivery; neither carries executable generative intent.
- Slide 12 chart caption rewrite: Design Grammars complements IFC and IDS by preserving upstream design logic while remaining compatible with downstream compliance checks.

## 30-60-90 Minute Execution Plan
- 30 min: Global cleanup pass (apply slide numbers to all slides, enforce min font size, remove bottom descriptive text blocks, remove vertical divider lines).
- 60 min: Narrative pass (reorder storyline to Scope -> Gap -> Solution, compress Slides 3-8, simplify Slides 11-15, tighten conclusion).
- 90 min: Visual and rehearsal pass (replace dense bullets with diagrams/cards, run 12-minute rehearsal, verify one-takeaway-per-slide and Q&A navigation by slide number).

## Validation Checklist
- Story arc is coherent end-to-end
- Styles are consistent across all slides
- Slide numbers are visible and consistent for Q&A reference
- No slide is overloaded with text or too many messages
- Graphics/charts are legible and support the message
- Each slide has one clear takeaway
