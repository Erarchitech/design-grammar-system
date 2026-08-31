# ITcon T1 — figure inventory and provenance

Manifest for `Publications/figures/`. Folders are **snapshots per paper revision**;
within a folder, file names carry *that revision's* figure number plus a stable slug.
Live submission set = `R14.2/`.

Audited 2026-08-24 against `T1_ITcon_DG_Draft_R14.2.docx`.

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
