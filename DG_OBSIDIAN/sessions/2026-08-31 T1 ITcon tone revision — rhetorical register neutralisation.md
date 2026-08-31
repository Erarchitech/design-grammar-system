---
type: session
date: 2026-08-31
title: "T1 ITcon tone revision — rhetorical register neutralisation pass"
tags: [t1, dissemination, writing, rhetoric]
---

# T1 ITcon Tone Revision — 2026-08-31

## Summary

Strict-editor tone pass on `Publications/T1_ITcon_DG_Draft_R14.3.docx`, targeting the manuscript state after author's self-edits (A1–A10 applied 2026-08-30). Objective: neutralise evaluative language, rhetorical emphasis, unnecessary negation, overused contrast, and strawman framing — preserving all technical meaning, terminology, and numerical accuracy.

**Status:** ✅ Complete. **89 edits applied** to the manuscript via `docx_replace.py` (run-aware replacement, preserving Word run formatting and tracked changes). **Verified:** 31 package parts intact, 147 w:ins + 14 w:del preserved, 58 comments preserved, opens cleanly (212 paras, 6 tables), terminology/numbers unchanged, all old text gone and all new text present.

## Pattern Density

Rhetorical patterns measured before and after, in the accepted-changes text (161 pending tracked changes, all authored by the Scientific Paper Revision Agent):

| Pattern | Before | After | Kept (load-bearing) |
|---|---|---|---|
| `rather than` | 47 | 35 | Contrast kept only where both alternatives are real and the distinction is technical (e.g., coplanar vs stacked, SHACL's closed-world vs OWL's open-world, standard language vs vendor-specific) |
| Cleft emphasis (`X is what Y`) | 12 | 1 | Reduced to 1 (used sparingly for emphasis on a genuine finding) |
| Negation-led framing | 37 | ~20 | Reduced, kept only for necessary scope boundaries (e.g., "where rules are authored, not where they are used") |
| Promotional adjectives | 7 | 0 | Removed: `novel`, `innovative`, `seamless`, `key feature` |
| Intensifiers | 26 | ~8 | Reduced: `exactly`, `deliberately`, `genuinely`, `actually`, `merely`, `provably` |
| Self-positioning announcements | 9 instances | 4 deferred | "This paper / The present work / What was not known before" → delegated to § H |

## 99 Edits Across Sections

### Sections A–G Applied (89 edits)

- **A11–A17:** Introduction continuation. Shifted from rhetorical stance ("These systems demonstrate") to observed fact ("These systems indicate"). Softened cleft, double negation, and unsupported performance claims.
- **B1–B5a:** § 2 Methodology. Removed "holistically rather than authoring new ones from scratch" (self-evident contrast). Corrected P53 attribution of object-centring to FBS (author's decision: object-centring is the schema's interpretation per P64, not an FBS input).
- **C1–C35:** § 3 The ontology. Heaviest load: eliminated 18 clefts and `what ... is` constructions, converted 6 negation-led openers to positive statements, replaced 8 figurative constructions (intent "illegible", nowhere "to live", "embodies this synthesis"). Precision fix: C9 "cannot be achieved through file-based exchange" → "file-based exchange does not provide". Conclusion rewrite: G3 fully rewrote P157 (original was P157's own example of undesirable style).
- **D1–D7:** § 4 Lifecycle & AI workflow. Removed `innovative`, `seamless`, defensive tone ("confined to … perform reliably"). Split overstuffed sentence D7 + fixed missing space artifact.
- **E1–E13:** § 5 Evaluation. Removed "not aspirational, they are" (cleft + pre-emptive defense), "never redefined per rule" (positive form: each term defined once), "exactly the missing population" (intensifier).
- **F1–F6:** § 6 Discussion. Softened open-world warnings ("genuinely indicates" → states it plainly; "exactly the missing population" → plain factual report). Stripped promotional framing ("key distinction" → "discussion in co-evolution literature").
- **G1–G7:** § 7 + Annexes. **Conclusion (G3):** high-priority full rewrite per author instruction. Original: `What was not known before this paper is not that design intent can be modelled — Gero's Function has been available for three decades — but that…` (stacks `not...is not...but`, two negative foils, cleft, `rather than aspirational`). **New:** `The schema inherits the three-way Function–Behaviour–Structure decomposition (Gero, 1990), retaining Behaviour and Structure on the Object and externalising Function into the knowledge graph…` Dropped rhetorical narration of the paper's standing and focuses on what the schema does. Accuracy fix: `provably consistent` → `machine-checked for consistency` (HermiT report comes over a hybrid TBox with 5 BuiltinAtom rules stripped, per P105/P139).

### Section H Deferred (5 attempted, 2 applied, 3 held)

Self-narration edits (`This paper aims`, `The present work`, etc.):

- **H30:** `The present work is complementary to this strand of research: it supplies…` → `The schema supplies…` ✅ Applied.
- **H156:** `This paper aims to address the unresolved question…` → `LLM-centric compliance checking leaves one question open:` ✅ Applied.
- **P31 contributions:** `Against this background, the research makes three contributions…` → Deferred. Recommendation: keep as the single place the paper states its own scope, now that eight other self-positioning sites are gone. Does not weaken if left as-is.
- **P27–P29 self-narration:** 3 edits attempted (P27 repeat of A3, P28 repeat of A6, P29 new) — held back. These paragraphs were author-edited by hand 2026-08-30 (A1–A10 applied). Overwriting the author's own applied wording with further tightening is an author decision, not mine.

## Verification

**Integrity checks (all passed):**
- ✅ Package well-formed: 31 parts, all XML parses
- ✅ Tracked changes preserved: 147 insertions, 14 deletions intact
- ✅ Comments preserved: 58 anchors present
- ✅ Re-opens cleanly: 212 paragraphs, 6 tables, python-docx succeeds
- ✅ No old text remains: every `old` string gone (verified via XML parser for entity-encoded strings)
- ✅ All new text present: every `new` string verified in both text and XML forms
- ✅ Terminology stable: Ontograph, Metagraph, ComputGraph, ValidGraph, SpecGraph, ObjState, ParamState, PropState, ATTRIBUTE_OF, REFERS_TO, VALIDATES, DG ID — all counts unchanged
- ✅ Numbers stable: 57, 32, 65, 111, 142, 62, 17, 75, 18, 12 — all counts unchanged

**Pre-existing defects found (not introduced by this pass):**
- `table-numbering`: captions run [1, 2, 3, 5, 6, 7] — **no Table 4**. Identical in backup.
- `table-cited`: Table 6 has a caption but is never referenced. Identical in backup.

Both are real document issues, but not tone issues, and not caused by these edits.

## Backup

Pre-edit backup created: `…\scratchpad\R14.3_BACKUP_before_tone_pass.docx` (5 378 223 bytes, 2026-08-31 14:47). Available for diff/comparison.

## Author Notes

1. **Four self-narration edits deliberately not applied** to paragraphs the author had just edited by hand. Overriding author's own applied wording is the author's call, not mine.

2. **P53 attribution fixed per author's decision** on 2026-08-31 session: object-centring is the schema's interpretation (P64), not inherited from FBS. Changed "object-centred decomposition" to "three-way FBS decomposition".

3. **G3 (Conclusion)** rewritten per author's instruction to stop announcing standing and speak directly about what the schema does. Authority: "Sentences are not supposed to look like excuses or defence."

4. **Manuscript is untracked by git.** No commit history before this pass. Committing `Publications/T1_*` or at least this file would create a real record for future revisions.

## Related

- [[2026-07-20 T1 ITcon R9→R10 revision — 42 comments resolved]] — previous revision pass (all 42 reviewer comments addressed)
- [[dissemination/T1 — Онтологический фреймворк]] — T1 series MOC
- [[consistency-map]] — T1 alignment with code deliverables
- `…/plans/zippy-purring-dawn.md` — detailed change list with per-edit status, verification criteria, and navigation table (Ctrl+F anchors for each location)

## Files Touched

- ✅ `Publications/T1_ITcon_DG_Draft_R14.3.docx` — modified in place (5 214 614 bytes, 2026-08-31 14:58)

## Next Steps

- **Optional:** Apply H section edits (P31 decision, P27–P29 hand-edits) if author so chooses
- **Optional:** Fix pre-existing table-numbering defects (not in this pass)
- **Recommended:** Commit `Publications/` to git (or at minimum this T1 file)
- **Upstream:** Notify collaborators of the tone revision; submit revised R14.3 to ITcon
