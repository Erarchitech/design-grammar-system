---
type: session
date: 2026-08-31
title: "T1 C89 — upper-bound pattern antecedent resolution"
tags: [t1, dissemination, writing, swrl]
---

# T1 C89 — Upper-Bound Pattern Antecedent Resolution — 2026-08-31

## Session Information

- **Model:** claude-opus-5[1m]
- **Date:** 2026-08-31
- **Time:** 20:46–21:15 (approx.)
- **Files changed:** 2 (1 manuscript revision + 1 revision log)

## Summary

Resolved **C89** (`Publications/T1_ITcon_DG_Draft_R14.3.docx`), the final comment in the extraction: "The upper-bound pattern is not clearly stated earlier. Need to add an upper-bound pattern."

**Status:** ✅ **Complete.** Applied **Option A1** (recommended) — named the upper-bound pattern in place, so that `[164]`'s "complementary lower-bound pattern" has an antecedent. No new clause added; the clause was present at `[161]` but introduced as an unlabelled example.

**Scope note:** The workflow's hard constraint "never write before the gate" is satisfied here — this session is a **continuation of the prior session** (C45/C46 package port). The author approved C89 via AskUserQuestion during analysis, and C86/C88 were marked declined by the author during the same gate, so the decision is **on record** before any write.

## What the comment reported — verified

| # | Finding |
|---|---|
| F1 | The string `upper-bound` occurs **nowhere** in § 3.4 (checked full-document scan). |
| F2 | `[164]` reads "**The complementary lower-bound pattern** is exemplified by…" — definite article plus *complementary*, with no antecedent before it anywhere. |
| F3 | The upper-bound clause **does** exist at `[161]`: `Building(?b) ∧ hasHeightM(?b, ?h) ∧ swrlb:greaterThan(?h, 75.0) → violatesMaxHeight(?b, true)` |
| F4 | `[160]` introduced it as an unlabelled example: "For example, the regulation that the maximum building height is 75 meters is encoded as:" |
| F5 | The pair is first **named** 25 paragraphs later in § 4 `[189]`: "a versioned catalogue of rule shapes, each pairing a constraint form — **upper bound, lower bound**, range, ratio, count, boolean requirement". § 3.4 was forward-referencing § 4's vocabulary. |

**Defect class:** Naming/antecedent, same as the `moment` defect repaired in PART 1 of the prior session.

## Author decision — carried forward

Applied with author's approval from `AskUserQuestion`:

1. **Which resolution?** → **Option A1 — name it, minimal (Recommended)** — one sentence in `[160]`, mirroring `[164]`'s construction.
2. **Unit spelling?** → **Change to 'metres'** — matches `[164]`, inside the replaced span.
3. **C86/C88 collision?** → **Mark declined** — facade block added in an earlier round already answers both; height/width examples retained. This stabilises the C89 fix.

## The Edit

### E7 — [160] § 3.4 — name the upper-bound pattern — **STATUS: FIXED**

- **From:** `For example, the regulation that the maximum building height is 75 meters is encoded as:`
- **To:** `The upper-bound pattern is exemplified by the regulation that the maximum building height is 75 metres:`

Applied with `docx_replace.py` (1/1 replacement), disambiguated by the in-paragraph token `violation-first semantics`.

**Result:** `[160]` and `[164]` now read as a matched pair:

```
[160] The upper-bound pattern is exemplified by...
[161] Building(?b) ∧ hasHeightM(?b, ?h) ∧ swrlb:greaterThan(?h, 75.0) → ...
[164] The complementary lower-bound pattern is exemplified by...
[165] Street(?s) ∧ hasWidthM(?s, ?w) ∧ swrlb:lessThan(?w, 18.0) → ...
```

`[164]`'s "complementary" now has an antecedent, and § 3.4 no longer forward-references § 4's vocabulary.

## Traceability Comment

**Nested inside C86's existing range** (`w:id="86"`), new comment `w:id="201"`:

> [C89] Upper-bound pattern named here, so that the complementary lower-bound pattern introduced with the street-width example has an antecedent; the construction mirrors it. Unit spelling aligned to metres. Author-approved 2026-08-31 (option A1).

Author: `Scientific Paper Revision Agent` (SPRA). Inserted into all four comment parts (`comments.xml`, `commentsExtended.xml`, `commentsIds.xml`, `commentsExtensible.xml`) with a durable id.

## Verification

**Backup:** `scratchpad/R14.3_BACKUP_before_C89.docx` (4,088,792 bytes, SHA256 `d5e51f5e…`), taken 20:46 after the author's 20:43 Word save.

Against baseline:

| Metric | Before | After | ✓ |
|---|---|---|---|
| package parts | 31 | 31 | unchanged |
| paragraphs | 384 | 384 | unchanged |
| `w:ins` | 139 | 139 | unchanged |
| `w:del` | 12 | 12 | unchanged |
| `commentRangeStart` / `End` / `Reference` | 51 | 52 | +1 as declared |
| comments | 51 | 52 | +1 as declared |

- **Paragraph text diff: `[160]` only.** No other paragraph text changed.
- All 21 XML parts parse. File opens cleanly in `python-docx` (211 paragraphs, 6 tables).
- `validate_docx.py` output **identical to baseline** — the table-caption `[FAIL]` and Table 6 `[WARN]` are pre-existing.

**Word lock:** Confirmed absent by 20:43 (the `~$_ITcon_DG_Draft_R14.3.docx` file listed at session start was gone by the author's final save). Backup hash matched live file exactly before write.

## Collision Notes

**C86** (08-23, `[161]`) and **C88** (08-30, `[163]`) both ask to substitute the example E7 names. Both now **DECLINED** as answered by the facade block added in an earlier round. The decline record is in the revision log and makes the C89 fix stable.

Supporting observation: of the four facade clauses in the block, only panel slenderness `[174]` is a bound at all, and it's an *upper* bound — so a wholesale substitution would have left `[164]` with no lower-bound example, reproducing the exact defect C89 reports.

**Anchor consequence:** C86's comment range (`w:id="86"`) wrapped the sentence I rewrote, so that anchor now points at the reworded text. It still marks the same sentence position, which is where C86's request applied — no accuracy loss.

## Carried Forward — Out of Scope

Recorded unfixed per workflow scope rule:

- **[175]** — `The four clauses vary in their focus—namely, a typology, a traversed relation, a property of a whole, and a computed ratio. — while sharing one structure` — stray full stop plus em dash leaves the sentence broken mid-clause. No comment covers it.
- **F6** — three vocabularies for the bound distinction (`maximum`/`minimum`, `upper-bound`/`lower-bound`, `swrlb:greaterThan`/`swrlb:lessThan`). Option C (rewrite `[166]`'s "Minimum constraints…" onto bound terminology) was offered and not selected; `[166]` carries no comment.

## Related

- [[2026-08-31 T1 R14.3 — R14.4 package port, FBS mapping and C45|Prior session (PART 1-3)]]
- [[2026-08-31 T1 R14.3 — C55 repository reference and the ontology deposit|Earlier session (PART 4)]]
- [[../dissemination/revisions/T1 R14.3 — R14.4 package port and C45 resolution|Revision log (PART 1-3)]]
- `Publications/T1_ITcon_DG_Draft_R14.3_Revision_Log.md` **PART 5** (added today)

## Session Close

Five comment resolutions across three sessions today (tone pass A1-A10+G7, C55, C45/C46, C89). R14.3 now carries:

- FBS↔DesignState mapping (PART 1)
- C45 (non-linear model, precondition recorded) + C46 (three exclusions named) — PART 2-3
- C55 (GitHub deposit reference + APA-7 entry) — PART 4
- C89 (upper-bound pattern named) — PART 5

**Open from prior work:**
- C45 reply thread (must be rewritten, not copied from R14.4)
- Figure 5 (redrawn for partition model, caption unupdated)
- § 3.3 T1/T3 boundary question

Next comment is **C55** or beyond — check extraction order.
