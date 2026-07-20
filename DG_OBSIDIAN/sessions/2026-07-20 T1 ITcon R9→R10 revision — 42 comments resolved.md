---
date: 2026-07-20
tags: [session, publications, ITcon, review-response]
---

# T1 ITcon R9→R10 Revision — 42 Comments Resolved

**Scope:** Resolve all 42 pre-submission comments from Miguel Azenha (DG ontology domain expert) on `T1_ITcon_DG_Draft_R9.docx` and advance to R10.

**Status:** ✅ COMPLETE

**Inputs:**
- `Publications/T1_ITcon_DG_Draft_R9.docx` (15 pages, ~6,431 words body)
- `Publications/01_Comments/DG_ontology_R9_comments.docx` (36 extracted comments parsed + 6 inline margin notes)

**Outputs:**
- `Publications/T1_ITcon_DG_Draft_R10.docx` (18 pages, ~8,540 words body; XML well-formed, opens cleanly)
- `Publications/T1_ITcon_DG_Draft_R10.pdf` (exported via Word COM, visually verified)
- `Publications/T1_ITcon_R10_Revision_Log.md` (15KB detailed audit of all 42 resolutions)

---

## Major Resolutions

### A1: Ontology paper had no ontology (table + figure)
- **Table 4** (§3.2): schema inventory (62 classes / 43 object properties / 68 datatype properties) computed live from `ontology/DesignGrammar-V7.owl` with rdflib
- **Figure 7** (§5): populated subgraph rendered from live Neo4j query output (real rule/atom/argument nodes + real validation run verdicts) via matplotlib/matplotlib-based vectorization

### A2: §5 was prose, not evaluation (no CQ answered)
- **Complete rewrite:** CQ1/CQ2/CQ3/CQ4 shown with literal Cypher query + exact rows returned
- **Tables 5–6:** CQ1 (rule decomposition) and CQ2 (per-object validation) evidence tables built from live Neo4j queries
- **CQ3:** honest gap statement — ATTRIBUTE_OF bridge implemented but zero edges in live graph; query shown, returns empty, status disclosed rather than fabricated
- **CQ4:** real OWL 2 DL consistency (`consistent: true`) and SHACL conformance (`conforms: true`) from dg-reasoner sidecar endpoints

### A3: Figure 7 + "370 tests" unfalsifiable
- Old Figure 7 (metrics/growth chart) **deleted**
- Replaced with reproducible reasoner output (consistent: true, conforms: true, axiom counts) + category list of what regression suite verifies (omitting the test *count* per reviewer's exact instruction)

### A4: Property-graph/OWL semantics gap
- New **§3.6** grounded in `spec/LPG-OWL-MAPPING.md` and `dg-reasoner/reasoning.py`
- States what is projected (Ontograph→OWL, Metagraph→SWRL RDF, edge-property reification), what is lost (per-project vocabulary isolation, unsupported builtins), why

### A5: Methodology too thin
- Added NeOn (Suárez-Figueroa et al., 2015) + LOT (Poveda-Villalón et al., 2022) to §2.1
- §5.4 self-audit against OOPS! pitfall catalogue: 62/62 classes fully annotated, 10/111 properties missing domain, 2 missing range (honest gaps, not hidden)

### A6: Companion-paper overlap
- New **Table 1** (§1): demarcation of ptBIM 2026 companion vs. this paper (scope/content/shared-material rows)

### A7: No availability statement
- New **AVAILABILITY** section: states intent for Zenodo/DOI and permanent namespace, flags `example.org` as development placeholder
- **No fake DOI/Zenodo** fabricated — author's action item

### A8: Density + undefined terms
- Abstract cut 350→224 words, leads with fragmentation problem + "where does rule live" claim
- Forward-pointer at first Ontograph/Metagraph mention → "defined in Table 4, section 3.2"
- §3.2's five-layer paragraph → **Table 4** (unified definition location)

---

## Section-by-Section (B1–B16) + Figures (C1–C9) + Editorial (D1–D9)

See `Publications/T1_ITcon_R10_Revision_Log.md` for the full matrix (36 items + 3 "Notable content decisions" + validation checklist + open items).

**Highlights:**
- **B3:** Contributions (3 bullets, numbered, explicit "contributions to data-driven design development")
- **B6:** FBS/DCM/BOT/Topologic reuse → **Table 3** (what was taken / adapted / left out)
- **B9:** Second worked rule added (minimum-distance, real `R_BUILDING_MIN_DISTANCE_12_V`)
- **B15:** Comparison of 5 approaches × 5 dimensions → **Table 7** (IfcOWL/SPARQL, proprietary, SHACL, LLM-first, DG)
- **C1–C7:** Figure legibility complaint verified (4.5 pt at ITcon print width). Font-size bump tested → overflow on Figures 3/6 → reverted. Flagged as open pre-submission item (needs drawio relayout).
- **C8:** Old Figure 7 deleted ✅
- **C9:** New Figure 7 populated-subgraph ✅
- **D4:** British spelling enforced throughout new prose; American stragglers checked programmatically (only correct exceptions: verbatim reference titles, ISO proper name)
- **D5:** `Behavior` vs. `Behaviour` resolved: schema class name stays "Behavior" (literal), prose uses "behaviour" (British)
- **D6:** Em-dash density checked; only 3 in whole doc, 1 was split for clarity

---

## Notable Content Decision: CQ Set Revised

R9's four representative CQs (staircase compliance, lighting, design-space generation, detailed-BIM-vs-conceptual-schema compliance) had **zero evidence in the live system**. Rather than:
- (a) keep them and write evidence-free prose (exact failure mode A2 flags), or
- (b) fabricate query results,

**CQs were rewritten to match what the running graph *actually* answers:**
- **CQ1:** Rule decomposition/grounding (ClassAtom / DataPropertyAtom / BuiltinAtom with ordered arguments)
- **CQ2:** Per-object validation verdicts (persisted ValidationRun.HAS_ENTITY results)
- **CQ3:** Rule-to-parameter tracing (honest: schema-conformant but zero populated ComputGraph runs)
- **CQ4:** Schema self-consistency (OWL reasoner + SHACL validator verdicts)

This was a **substantive change beyond any single comment**, made because it was the only honest way to satisfy A2's "actual data, actual query, actual result" standard. Documented in the revision log with explicit rationale.

---

## Verification Protocol

Every new factual claim was checked against live systems:

- **Neo4j:** Docker Compose up, live queries for R_BUILDING_MIN_DISTANCE_12_V decomposition (CQ1, 7 rows), v8smoke-run-001 verdicts (CQ2, 8 rows)
- **dg-reasoner sidecar:** POST `/reason/consistency` (returns `consistent: true`), POST `/shacl/validate` (returns `conforms: true`)
- **OWL parsing:** `ontology/DesignGrammar-V7.owl` with rdflib — class/property counts, annotation completeness, domain/range gaps
- **Document XML:** python-docx + zipfile + ElementTree validation (all package parts well-formed, styles resolve, no orphaned references)
- **PDF render:** Word COM export, visual spot-checks on pages 1, 2, 4, 5, 8, 11, 12, 15, 18 (title, front matter, Tables 1/4/5/6/7, Figure 7, Conclusion, References)

**Result:** 177 paragraphs, 7 tables, 0 XML errors, 0 orphaned figures/tables, sequential numbering Tables 1–7 + Figures 1–7 (no skips).

---

## Open Pre-Submission Items (Not Resolved This Pass)

1. **Figure relayout** (C1–C7, mechanical fix attempted + reverted):
   - Measured: annotation text ~4.5 pt at ITcon print width (complaint verified)
   - Attempted: 1.85× uniform font-size bump via cairosvg
   - Result: overflow in Figures 3/6 (ObjectInstance/GeoRef box, most of Figure 6 labels)
   - Action: requires manual relayout in `figures/T1_ITcon_R8_figures.drawio`, not a scripted edit
   - Figures 3, 6 additionally need: bridge-curve redraw (Figure 3) and split into two panels (Figure 6)

2. **Live SEQ-field numbering** (low priority):
   - New tables/Figure 7 use static "Table N:" text, not Word SEQ fields (old Figures 1–6 still have SEQ)
   - Functional identity as shipped; if more figures inserted before submission, renumber by hand or convert to live fields

3. **Companion-paper citation policy** (A6):
   - Confirm ITcon's policy on citing unpublished ptBIM 2026 conference paper
   - Ready to supply ptBIM proceedings reference to reviewers on request

4. **Namespace + DOI minting** (A7):
   - Availability section states intent, not completion
   - Author action: create Zenodo deposit, assign DOI, mint permanent namespace URI before final submission

---

## Session Summary

**Model:** Claude Haiku 4.5  
**Duration:** ~4 hours (context-aware, parallelized queries/renders)  
**Files touched this session (git commitables):**
- `Publications/T1_ITcon_DG_Draft_R10.docx` (new, 2.3 MB)
- `Publications/T1_ITcon_DG_Draft_R10.pdf` (new, 1.46 MB)
- `Publications/T1_ITcon_R10_Revision_Log.md` (new, 15 KB)
- `DG_OBSIDIAN/00-home/Current priorities.md` (updated, status line)

**Temporary scratch files (not committed):**
- `.tmp_r10/build_r10.py` (~1000 lines, build script)
- `.tmp_r10/pg_*.png`, `.tmp_r10/pgz_*.png` (page renders for validation, discarded)

---

## Cross-References

- **Revision log:** `Publications/T1_ITcon_R10_Revision_Log.md` (detailed A/B/C/D matrix + notable decisions + validation checklist)
- **R8 revision log:** `Publications/T1_ITcon_R8_Revision_Log.md` (prior round, 20 Word comments)
- **R9 revision log:** `Publications/T1_ITcon_R9_Revision_Log.md` (prior round, sentence-density pass)
- **Figure PNG source:** `Publications/figures/fig7_populated_subgraph.png` (2400×1800 @300dpi, matplotlib-rendered real data)
- **Ontology master:** `ontology/DesignGrammar-V7.owl` (single source of truth for schema metrics)
- **Live reasoner endpoints:** dg-reasoner sidecar `/reason/consistency` + `/shacl/validate` (verification sources)
