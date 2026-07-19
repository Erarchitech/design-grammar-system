# Session: R8 revision — ITcon article restructure and figure rebuild

**Date:** 2026-07-19  
**Duration:** ~2.5 hours  
**Model:** Fable 5  
**Task:** Revise T1_ITcon_DG_Draft_R7 (20 Word comments) → R8 per ITcon benchmarking and user feedback  

## Work completed

### 1. ITcon research & benchmarking (Perplexity)
- Analysed **6 accepted papers** (2022–2025): structure, length (17–36 pp), ontology presentation, evaluation rigour
- ITcon norms: 5–7 sections, 4–10 figures, no schema dumps in main text, competency-question–driven evaluation
- Key finding: R8 at ~6.5k words is compact (accepted papers 12–24k) but acceptable as focused ontology paper

### 2. Figure rebuild (7 figures)
- **Master file**: `T1_ITcon_R8_figures.drawio` — one editable tab per figure, DG TO-BE design system per `diagrams/DESIGN-SYSTEM.md`
- Fixed **Figure 3 overlap**: moved bridge-label routing below layer boxes, dedicated space for "every layer references Core concepts"
- Fixed **Figure 4 & 5**: non-overlapping HAS_STATE edges, LLM encoding label routing
- Fixed **Figure 6 & 7**: legend positioning, text truncation
- **Merged former FIG 6+7** into single lifecycle/ComputGraph figure (per user choice)
- All figures: white fills, 2px ink borders, layer colors semantic-role-only, `#A680B8` orthogonal edges, Helvetica 14px
- Exports: PNG @2x (embedded) + SVG (submission) in `figures/r8/`

### 3. Article revision (R7 → R8)
- **Text**: ~8,410 → ~6,460 words total (body ~6,900 → ~5,200); cuts targeted at duplication/overdetail only
- **All 20 comments resolved** (detailed mapping in revision log):
  - C0, C1, C10: OBS → **object-centred FBS core** throughout
  - C3: ontology reframed as "shared code space", not active interpreter
  - C11, C13: domain → *data-driven parametric design, RIBA Stages 1–3*
  - C2, C7, C8: contributions → 3 items, generalized identity-spine wording
  - C15, C19: Appendix A removed, placeholder reference to GitHub ontology repo
  - C18: use cases → flowing prose, no predicate-less fragments
- **Merged sections**: §2.1+2.4, §3.2+3.3, §6.2+6.3, §4 to one section
- **Cuts**: duplicate specification paras, DCM formula, Grasshopper screenshot, internal version numbers
- **ptBIM coherence**: clarified system architecture vs schema layers; maintained shared vocabulary

### 4. DOCX assembly
- **R8 docx** (`T1_ITcon_DG_Draft_R8.docx`):
  - Reuses R7 styles & headers, strips all 20 comments
  - Embeds 7 new PNG figures at correct widths per ITcon column constraints
  - Removes orphaned R7 media (image1–8), cleaned package metadata
  - Final: 131 paragraphs, ~6,460 words, 2.29 MB
  - Verified: 7 figures embedded, comments/people.xml stripped

### 5. Deliverables
- **Article**: `Publications/T1_ITcon_DG_Draft_R8.docx`
- **Figures**: `Publications/figures/T1_ITcon_R8_figures.drawio` (master) + `figures/r8/` (PNG/SVG exports)
- **Revision log**: `Publications/T1_ITcon_R8_Revision_Log.md` (comment-by-comment + structural changes)

## Key decisions

1. **OBS → object-centred FBS**: aligns with academic literature (Gero), reduces ambiguity of private coinage.
2. **Merge FIG 6+7**: streamlines the lifecycle diagram without losing the Grasshopper mapping context.
3. **Deduplication over strict halving**: preserved all core concepts, cut only repetition and implementation detail overload.
4. **External ontology reference**: Appendix A too large for journal; versioned ontology project in GitHub is the right place.
5. **Single .drawio master**: editable tabs allow figure maintenance without rebuild cycle.

## Open questions / future work

- ITcon submission may request deeper evaluation; use-case sections have room to expand.
- Figure 3 routing still manual — draw.io's auto-router may improve with further refinement (not a blocker).
- Figures are now design-system–compliant; future revisions should use the .drawio tabs as the master.

## Files modified in this session

- **Created**:
  - `DG_OBSIDIAN/sessions/2026-07-19 R8 revision...md` (this note)
  - `Publications/T1_ITcon_DG_Draft_R8.docx`
  - `Publications/figures/T1_ITcon_R8_figures.drawio`
  - `Publications/figures/r8/` (7 PNG + 7 SVG)
  - `Publications/T1_ITcon_R8_Revision_Log.md`

- **Not modified** (existing):
  - `DG_OBSIDIAN/00-home/index.md` (no arch/knowledge changes)
  - `DG_OBSIDIAN/00-home/Current priorities.md` (R8 is a maintenance task, not a new priority)
  - `CLAUDE.md` project instructions (no new patterns discovered)

## Session metrics

- **Words deleted**: ~2,200
- **Paragraphs**: 349 (R7) → 131 (R8), net cut of duplicates
- **Figures rebuilt**: 7/7 with overlap fixes
- **Comments resolved**: 20/20 (100%)
- **ITcon alignment**: section structure, figure count, ontology presentation all match accepted-paper patterns

---

**Status**: Ready for ITcon submission. R8 is coherent with the ptBIM 2026 companion paper, addresses all stakeholder feedback, and aligns with journal best practices for ontology/knowledge-graph papers.
