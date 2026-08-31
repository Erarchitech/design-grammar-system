---
type: session
date: 2026-08-31
title: "C45 closure — what's left for R15"
tags: [t1, dissemination, writing, design-state, c45, figure-5]
---

# C45 Closure — What's Left for R15

## Status

**Prose closed.** All three sections (§§ 2.2, 3.3, 6.1) carry the non-linear model. C45 comment resolved and removed (58 → 55 comments). **Figure 5 redesigned.** But the manuscript is **not yet consistent** — old Figure 5 and its caption still embedded.

## What remains, in priority order

### 1. Embed Figure 5 (the blocker for manuscript consistency)

**What:** Replace the binary image `word/media/image5.png` inside the docx with the new partition diagram.

**Where:** [R14.3](Publications/figures/R14.3/fig04_design_state.png) holds the new render at 3420 × 1727 px, exported from [the editable source](Publications/figures/R14.3/fig04_design_state.drawio).

**Method:** The docx carries Word image metadata in `word/document.xml`. The old image extent is `cx="5760000"` (width, EMUs) — the new render may need different `cy` height if it's taller or shorter. Procedure:
1. Extract the old `image5.png` from the docx (test that it matches `figures/R14.2/fig04_design_state.png`).
2. Replace it with the new `fig04_design_state.png`.
3. Measure the new PNG and adjust `cy` if needed (the old docx used `cy="2131300"`; the new one may differ since the layout is taller).
4. Re-package and verify opens.

No Cypher / programmatic method exists yet for this — it's a manual docx surgery step.

### 2. Update Figure 5's caption (the second blocker)

**Current text:** *"…and longitudinal tracking along the lifecycle axis"* (from R14.2).

**Needed:** A caption that reflects the partition model and the precondition in § 6.1. Two options:

**Option A (stronger):** Explicitly name the partition model  
> **Figure 5:** Design State composition (ObjState, ParamState, PropState), its consumption by validation Runs. A collection of states is partitioned by design space and typology: facade alternatives (glazed, structural) and plan layout alternatives belong to separate partitions, even if time-ordered. States within a partition are comparable for movement typing; across partitions, temporal order alone does not establish movement. The lifecycle-phase sequence (concept → parametric → detailing → validation) is a separate axis.

**Option B (lighter, defers to § 6.1):** Signal that the diagram shows state grouping without naming the partition formally  
> **Figure 5:** Design State composition (ObjState, ParamState, PropState), its consumption by validation Runs. Design states accumulate in groupings (shown dashed) — alternatives within a facade typology, typologies within one design space, separate design spaces for one building. Partitioning determines which states are comparable for typing movement (section 6.1).

**Recommendation:** **Option B** — it stays at the figure's scope (visual groupings), defers the formal treatment to § 6.1, and preserves the precondition framing (what the schema **must record**, not what it does).

### 3. Write a reply letter to C45 (or port the R14.4 thread)

**Status:** The R14.4 reply thread exists only in R14.4 (grep count 0 in R14.3). It cannot be reused verbatim — it claims *"specified in section 6.1"* and describes a derivation rule that was rejected.

**What a reply must say:**
- **T1 fixes a pre-implementation stage.** The paper grounds the ontology, not the other way around.
- **Design State trails are non-linear.** States partition by design space and typology. A pairwise diff cannot distinguish reformulation (partition change) from refinement (movement within partition).
- **The schema must record membership.** § 6.1 states this as a precondition: which design space and partition each state belongs to. Recording it is what would unlock future movement typing (in T3/T4).
- **Figure 5 shows the grouping visually.** The diagram replaced the single chain with dashed partition containers.

**Register:** neutral, no negation-led framing, no `rather than`. The author's register from the tone pass applies.

### 4. Adjacent fixes (lower priority)

- **`Behavior` → `Behaviour`** at [P64]. Lone US spelling; everywhere else is British.
- **Remaining linearity vocabulary** — low risk, but worth a sweep: *"longitudinal record"*, *"evolves"* at [P79]. Check whether these conflict with the partition framing in the context they appear. (They likely don't, but a final pass is safe.)

## Open questions (for the author)

1. **Figure 5 caption — which option?** Option A names the partition model explicitly; Option B stays lighter and defers to § 6.1. The figure itself is partition-forward now.
2. **Reply letter — write new or copy from R14.4 and edit?** The thread exists in R14.4 but claims a § 6.1 specification we rejected. Copy + revise, or write fresh?
3. **§ 3.3 scope with T3 — settle now or later?** The coherence map assigns Design State to T1 as a dash, but R14.3's whole § 3.3 is about it. This is a real boundary question (T1 ↔ T3). Not blocking R15, but it will recur.

## What's verified

- ✅ All three sections (§§ 2.2, 3.3, 6.1) carry the non-linear, partition-based model.
- ✅ C45 comment removed (issue closed in the document).
- ✅ Figure 5 redrawn: partition containers (dashed) with interleaving state indices, no arrows (schema declares none).
- ✅ Print size consistent (1200 / 12 → 4.82 pt, matching Figures 3–7).
- ✅ Figure sources saved to `figures/R14.3/` (drawio + PNG + SVG).
- ✅ `FIGURES.md` updated with R14.3 section and R14.4 superseded label.
- ✅ No T4 vocabulary introduced; no forward reference added.
- ✅ No new linearity presumptions contradicting the model.

## Related

- [[../dissemination/revisions/T1 R14.3 — R14.4 package port and C45 resolution]]
- [[../knowledge/decisions/DesignState movement typing requires design-space membership]]
- [[2026-08-31 T1 R14.3 — R14.4 package port, FBS mapping and C45|Earlier session today]]
- [Publications/figures/FIGURES.md](Publications/figures/FIGURES.md) — § 1c (R14.3 section)
- [Publications/figures/R14.3/fig04_design_state.drawio](Publications/figures/R14.3/fig04_design_state.drawio) — editable source
