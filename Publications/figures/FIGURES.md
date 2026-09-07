# ITcon T1 — figure inventory and provenance

Manifest for `Publications/figures/`. Folders are **snapshots per paper revision**;
within a folder, file names carry *that revision's* figure number plus a stable slug.
Live submission set = `R14.2/`, plus `R15.1/` for Figure 1 (see §1d).

Audited 2026-08-24 against `T1_ITcon_DG_Draft_R14.2.docx`; Figure 1 re-audited
2026-09-02 against `T1_ITcon_DG_Draft_R15.1.docx`.

---

## 1. The live set — `R14.2/`

`pt` is the effective print size of the smallest text when the figure is placed at the
full 170 mm ITcon text width (see §4 for the arithmetic).

| Paper | File | Source | Smallest text | Changed this round |
|---|---|---|---|---|
| Fig 1 | `fig01_dev_process` | own `.drawio` | 8.03 pt | **yes** — replaces the two-panel Fig 1(a)/1(b); checkpoints panel dropped (R1-C06) |
| Fig 2 | `fig02_reuse_mapping` | own `.drawio` | 8.03 pt | **new** — reuse/alignment mapping under Table 3 (R1-C08) |
| Fig 3 | `fig02_fbs_core` | own `.drawio` | 4.82 pt | **yes** — orphan "records change of" label deleted (AU-C22) |
| Fig 4 | `fig03_layers` | own `.drawio` | 4.82 pt | **yes** — three proposed bridges added, dashed, with legend (AU-C23) |
| Fig 5 | `fig04_design_state` | own `.drawio` | 4.82 pt | no |
| Fig 6 | `fig05_swrl_anatomy` | own `.drawio` | 4.82 pt | no |
| Fig 7 | `fig06_lifecycle` | own `.drawio` | 4.82 pt | no |
| Fig 8 | `fig07_validation_evidence` | own `.drawio` | 8.09 pt | **yes** — properties panel redrawn as vector; 313-node graph view dropped |
| Fig 9 | `fig08_populated_subgraph` | own `.drawio` | 8.37 pt | **yes** — rebuilt on `R_BUILDING_MAX_HEIGHT_75_V` and run `a5671cb1bd30` |
| Fig 10 | `fig09_schema_verification` | **no `.drawio` anywhere** | — | no — carried forward from `R10.1/`, cannot be edited |

Every figure now ships as `.drawio` + `.png` (300 dpi equivalent) + `.svg`, except
Figure 10, which has only `.png` + `.svg`.

**Figure numbering shifted this round.** Inserting the reuse-mapping diagram under
Table 3 in §2.2 places it before the old Figure 2, so Figures 2–9 became 3–10. All 19
in-text references and 8 captions were updated in one operation.

### The master file

`T1_ITcon_R14.2_figures.drawio` is the R12.1 master carried forward with the Figure 3 and
Figure 4 edits applied. It is retained for provenance, but the **per-figure files are
authoritative** — the paper's images are exported from those. The master's page selector
could not be driven reliably through the Draw.io CLI, which is why the pages were split.

---

## 1b. `R14.4/` — partial snapshot — ⚠️ SUPERSEDED

**Do not build on this set.** Its Fig 5 change was retired together with R14.4 itself; see §1c.

Only the figures changed since `R14.2/` live here. Everything else is carried forward from
`R14.2/`, which remains the base of the live set.

| Paper | File | Source | Smallest text | Changed this round |
|---|---|---|---|---|
| Fig 5 | `fig04_design_state` | own `.drawio`, copied from `R14.2/` | 4.82 pt | **yes** — the three lifecycle-axis transitions (`DS_t0`–`DS_tn`) drawn long-dashed (`8 8`) and labelled "typed transition (proposed)", plus a legend; per `AU-R143-C02` |

Exported at 3417 × 1367 px (`-s 3`), replacing `word/media/image5.png`. The Word drawing extent
was re-fitted — `cx` held at 5760000 EMU, `cy` 2131300 → 2304337 — because the legend makes the
figure taller; without that the image would have been squashed.

The `R14.2/` source was copied, never edited: its SHA-256 still matches `work/source-manifest.md`.

## 1a. `R15.2_proposed/` — PROPOSED, not approved

**At the gate. Nothing here is promoted to `R15.2/` until the author approves `AU-R151-TOPO`.**

| Paper | File | Source | Smallest text | Changed this round |
|---|---|---|---|---|
| Fig 2 | `fig02_reuse_mapping` | own `.drawio`, revised from `R14.3/` | **8.03 pt** | **yes** — the module architecture of `AU-R151-TOPO` |

**Revised in place — no renumbering.** Figure 2 keeps its number and slot, so none of the 19
in-text figure references or 8 captions move. That is deliberate: this document has already paid
for one renumbering cascade (§1, R12.1), and static literal numbering plus a `SEQ`-field request
open since R14.2 makes a second one expensive.

**Source of record.** `R14.3/fig02_reuse_mapping.drawio`, mtime **2026-08-31 19:02** — the author
revision this file records at §1c. It was never copied into `R15.1/`, which is the whole of that
bookkeeping gap; the artwork itself was never lost.

**What changed.**

| | Before (`R14.3/`) | After |
|---|---|---|
| BOT | a source bridged by its own *"extension module: imported and subsumed"* | **reached through the Topologic ontology**, which subsumes its building-part classes under BOT — shown as a grey subsumption edge inside the source column, with no DG-maintained bridge |
| Topologic | *"extension module: declared"* — nine classes minted in this project's namespace | the **published ontology at `w3id.org/topologicpy#`**, targeted by one **topology alignment module** |
| IFC | listed under *"Not aligned"* | a **source**, with a **classification alignment module** reaching it at its bSDD identifiers |
| Attachment points | one target, the core Topology concept | **two, and distinct** — the core **Topology** concept for relations, the **Ontograph** minted class for classification |
| The excluded set | *"**Not aligned**"* | *"**Addressed by other means**"* — now naming OMG/FOG, OPM and BPO, and stating the mechanism that covers each |

**Author revision, 2026-09-07.** The layout was reworked by hand after the first build: the
*Addressed by other means* panel moved to a left-hand column beside BOT, the source column was
compacted vertically (content height 1585 → 1144), and the BOT ↔ IFC edge label now names the
artifact itself — `IFCOWL4_ADD2Alignment.ttl`. **`.png` and `.svg` were re-exported from the
revised `.drawio`**; the two had gone stale against it.

**Print size 8.02 pt — measured, and the margin is thin.**

| Basis | Width | pt |
|---|---|---|
| §4 convention (`W` = `pageWidth`) | 1500 | **8.03** |
| As placed (`W` = content extent, what a reader actually gets) | **1502** | **8.02** |

The smallest font stays **25** and `pageWidth` stays **1500**. Content now spans `x −22 … 1480`, so
it is **1502 units wide — 2 units wider than the page it is authored on**, and the two measures have
diverged for the first time. **The 8.00 pt floor is breached past 1506 units, leaving 4 units of
headroom**: any further widening of this figure needs re-measuring, not assuming.

> **Note on the §4 convention.** `W = pageWidth` is a *conservative* estimate — it assumes the whole
> page maps to 170 mm, when draw.io exports crop to content. Where content is narrower than the page
> the real print size is larger than the table states (R14.3's Fig 2 content was 1440 units, so its
> recorded 8.03 pt was actually 8.36 pt as placed). Here content is *wider* than the page, so for the
> first time the convention **over**-states the result. The as-placed figure is the one to trust.

**Triplet complete.** `.drawio` + `.png` (scale 4, 6578 × 6251) + `.svg`. This **closes the missing
`.svg`** that `R14.3/`'s Fig 2 has carried since 2026-08-31.

## 1c. `R14.3/` — partial snapshot, the current line

Only figures changed since `R14.2/` live here; everything else is carried forward from `R14.2/`.

| Paper | File | Source | Smallest text | Changed this round |
|---|---|---|---|---|
| Fig 2 | `fig02_reuse_mapping` | own `.drawio` | 8.03 pt | **yes** — author revision, 2026-08-31 |
| Fig 4 | `fig04_layers` | `.png` only in this set | — | **yes** — author revision, 2026-08-30 |
| Fig 5 | `fig04_design_state` | own `.drawio`, redrawn from `R14.2/` | 4.82 pt | **yes** — the linear `DS_t0 → … → DS_tn` chain replaced by design-space / typology partitions; per C45 |

**Fig 5 — what changed and why.** `R14.2/` drew the states as a single arrow chain on a
"lifecycle axis". That asserts one trajectory, which §§ 3.3 and 6.1 no longer claim: a Design State
collection is partitioned — alternatives within a typology, typologies within a design space, and
separate design spaces (facade, plan layout) for one building. The chain is replaced by two dashed
partition containers holding six states whose `DS_t` indices **interleave across** them, which is
what shows that a temporal order can exist without being a movement. No relation is drawn between
states, because the schema declares none. The lifecycle-phase sequence survives as a footnote —
phases genuinely are ordered — but is no longer attached to the states.

**`R14.4/fig04_design_state` is superseded, not a base to build on.** It kept the single chain and
added long-dashed "typed transition (proposed)" arrows along it. That is the derivation rule C45's
resolution rejected: reformulation redefines a state space rather than linking two states, so a
pairwise state diff cannot type movement at all.

Page geometry is unchanged from `R14.2/` — 1200 units, smallest font 12, so still 4.82 pt — to keep
this figure consistent with Figures 3–7 rather than diverging alone. The legibility issue in §2
therefore still applies to it.

Exported at 3420 × 1727 px (`-s 3 --crop`). **Not yet embedded in the manuscript:**
`word/media/image5.png` and the Figure 5 caption both still carry the `R14.2/` linear version, and
the caption still reads "longitudinal tracking along the lifecycle axis".

**Dash vocabulary now in use on this page.** Fine-dotted (`1 1`) is the pre-existing
"persisted, never overwritten" edge; long-dashed (`8 8`) is the proposed relation. The legend says
"long-dashed" rather than "dashed" so the two cannot be conflated.

---

## 1d. `R15.1/` — Figure 1 only, current

Produced in the R15.1 round resolving reviewer cluster `BF-R15-NUM`. **Only Figure 1
was touched.** Every other figure in `R15.1.docx` remains the asset recorded in §1/§1c.

| Asset | Provenance |
|---|---|
| `fig01_dev_process.drawio` | copied from `R14.2/`, one label edited |
| `fig01_dev_process.png` | re-exported `--format png --scale 3 --crop`, 4502 x 1967 px |
| `fig01_dev_process.svg` | re-exported `--format svg --crop`, viewBox 1501 x 656 |

**The edit.** The artwork's baked-in cross-reference label read
`Figures 3-4, Tables 3-4`. R15 has **no Table 4** - the reuse/alignment table that held
that ordinal was deleted at R14.3 - so the token was stale. Changed to
`Figures 3-4, Table 3`. Nothing else in the artwork was altered; the other four
number-bearing labels (`Table 2 - competency questions`, `Figures 5-6`, `Figures 7-10`,
and the italic `Table 2` note) were each checked against `R15.1.docx` and are correct.

**This is the second time this artwork has gone stale by a renumbering.** The R14.2
validation report caught seven stale tokens in it and the round re-exported and
re-embedded the figure. Any future figure or table renumbering must treat
`fig01_dev_process` as an affected artefact - it is the one figure whose job is to
locate the paper's own artefacts.

**Embedded, with an extent correction.** `word/media/image10.png` in `R15.1.docx` was
replaced with the new export. The previously embedded raster had aspect 2.2594 while the
vector master's viewBox is 2.2881 - the `R14.2/` PNG had been cropped tighter than its own
SVG - so re-embedding at the old extent would have stretched the image 1.28% vertically.
The extent was corrected instead: `cy` 1965960 -> 1941219 EMU, height 54.61 -> 53.92 mm,
width unchanged at 123.38 mm. Effective resolution rose from 421 to 927 DPI.

**Print size - fails the §4 floor, pre-existing, not fixed.** By the §4 formula at
123.38 mm and a 1501-unit master, Figure 1's 26-unit labels print at **6.06 pt** and its
25-unit italic note at **5.83 pt**, against this project's 8 pt floor. Unchanged by this
round: the label edit altered no font size and no viewBox. Recorded, not fixed - no
reviewer comment in the approved cluster asked for legibility work, and clearing the floor
needs relayout, not a font bump. It belongs with the §2 finding for Figures 3-7 and
Miguel's R13 comment.

**`figure_print_size.py` cannot measure these masters.** It reads `<text>` elements; Draw.io
stores labels as HTML inside `<foreignObject>`. It therefore sees 1 of 14 text blocks and
reports 2.33 pt for Figure 1 - and a spurious "TOO SMALL" for every master in `R14.2/`,
including on files it has never changed. Verified by running it against the untouched
`R14.2/` masters, which return the same numbers. Use the §4 formula, not that tool, for
Draw.io figures.

---

## 2. Legibility — the outstanding issue

Figures 3–7 print at **4.82 pt**, well under the 8 pt floor this project sets for itself.
This is not new and was not raised by any comment in the R14.1 → R14.2 round, so it was
**not fixed**; it is recorded here and in §15 of the revision summary.

It is worth acting on: **Miguel's R13 review says "font sizes in other figures are too
small and should be improved", and that point has now survived two rounds without a
response.** Raising type in those five sources requires relayout, not a uniform font
increase — widening the type without loosening the boxes overflows them.

Figures 1, 2, 8 and 9 — everything authored or rebuilt this round — clear 8 pt.

---

## 3. Archived generations

| Folder | Contents | Status |
|---|---|---|
| `R14.2/` | the live set | **live** |
| `R14.2_proposed/` | the three drafts promoted into `R14.2/` | superseded |
| `R14.1/` | extracted from the R14.1 manuscript | superseded |
| `R12.1/` | `T1_ITcon_R12.1_figures.drawio` (8 pages) — the master this round was split from | source of record |
| `R10.1/` | `fig09_schema_verification.*` — **Figure 10 of the live paper still comes from here** | partly live |
| `R08/` | `T1_ITcon_R8_figures.drawio` — pages *Fig 2*–*Fig 7* are byte-identical to R12.1's | superseded |
| `R07/`, `R10/` | early raster and vector generations | superseded |
| `_scratch/` | draw.io autosave `.bkp` files | junk |

---

## 4. The legibility rule

A draw.io page is authored in abstract units. Placed at width `Wmm`, a label of `f`
units prints at

```
pt  =  f × (Wmm / W_units) × 2.8346
```

For the ITcon text width (170 mm) and an 8 pt floor this reduces to a single check on
the source file:

```
W_units / smallest_font_units  ≤  60
```

| draw.io page | W units | smallest font | ratio | pt |
|---|---|---|---|---|
| fig01_dev_process | 1500 | 25 | 60.0 | 8.03 |
| fig02_reuse_mapping | 1500 | 25 | 60.0 | 8.03 |
| fig02_fbs_core | 1200 | 12 | 100.0 | 4.82 |
| fig03_layers | 1200 | 12 | 100.0 | 4.82 |
| fig04_design_state | 1200 | 12 | 100.0 | 4.82 |
| fig05_swrl_anatomy | 1200 | 12 | 100.0 | 4.82 |
| fig06_lifecycle | 1200 | 12 | 100.0 | 4.82 |
| fig07_validation_evidence | 1490 | 25 | 59.6 | 8.09 |
| fig08_populated_subgraph | 1440 | 25 | 57.6 | 8.37 |

## 5. House style for new figures

| Token | Value |
|---|---|
| body | 26 units |
| node title | 28 units, bold |
| notes, edge labels | 25 units |
| ink | `#1A1A1A`, stroke 2.5 |
| relations | `#7A5C9E`, stroke 2.0–2.5 |
| proposed relations | as above, dashed `8 8`, with a legend saying so |
| layer containers | `#8C8C8C`, dashed `6 6` |
| verdict pass / fail | `#1B6B36` / `#A8241F` |

No figure carries a baked-in title — the caption owns it.

**Two cautions learned this round.** `dgfig.py` does *not* refuse to write a page that
fails the §4 check; the gate is advisory. And box heights must be sized to the wrapped
line count — 36 px for a title line, 34 px per body line, plus 16 px padding — or the
text silently overflows the frame in export.
