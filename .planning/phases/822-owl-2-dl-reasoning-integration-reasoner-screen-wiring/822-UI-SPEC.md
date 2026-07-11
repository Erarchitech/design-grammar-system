---
phase: 822
slug: owl-2-dl-reasoning-integration-reasoner-screen-wiring
status: draft
shadcn_initialized: false
preset: none
created: 2026-07-12
---

# Phase 822 — UI Design Contract

> Visual and interaction contract for wiring the HermiT card's live schema-consistency
> check into `ui-v2/src/screens/ReasonerScreen.jsx`. Grounded in the shipped `ui-v2`
> design system — this phase introduces **no new tokens, fonts, or primitives**.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (bespoke primitives in `ui-v2/src/components/`, no shadcn) |
| Preset | not applicable |
| Component library | none / custom — reuse `Button`, `Badge` from `ui-v2/src/components/index.js` |
| Icon library | none — text glyphs only (`←`, `✓`, `–`, `×`); no icon-font/SVG-set dependency |
| Font | Geist (`--font-sans`), Geist Mono (`--font-mono`), Oswald (`--font-annotation`) |

**Constraint (DSYS-01):** *"Color is absence, not expression. One chromatic hue exists — Signal Red."*
Every verdict treatment below lives inside this rule. No green, no amber, no new hue is added
regardless of the CONTEXT's shorthand ("green"/"amber") — those map onto the achromatic stack.

---

## Spacing Scale

Real tokens (`ui-v2/src/styles/tokens/spacing.css`), all multiples of 4:

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing-4` | 4px | Icon/label gaps, Badge inner gap |
| `--spacing-8` | 8px | Compact element spacing, `--element-gap` |
| `--spacing-12` | 12px | Card title-row gap |
| `--spacing-16` | 16px | Default gap between cards / header items |
| `--spacing-20` | 20px | `--card-padding` |
| `--spacing-24` | 24px | Reasoner-card padding (existing) |
| `--spacing-48` | 48px | Major section break |

**New elements this phase must sit on this grid:**
- Run/Cancel button row → `16px` (`--spacing-16`) top margin above the expanded result region.
- Result region internal stack → `12px` (`--spacing-12`) between verdict line, metadata, and list.
- Unsatisfiable-class list items → `8px` (`--spacing-8`) row gap.

Exceptions: the existing screen uses inline non-token values (`28`, `26`, `14`, `10`, `60`) for
page padding and legacy card internals. **Do not add new off-grid values.** Match the nearest token
for anything this phase adds; leave existing inline values untouched (out of scope).

---

## Typography

Real scale (`ui-v2/src/styles/tokens/typography.css`). This phase adds text only inside the HermiT
card — no new type roles:

| Role | Size | Weight | Line Height | Applied to |
|------|------|--------|-------------|------------|
| Caption | 12px | 400 | 1.33 | "Last checked …" timestamp, elapsed counter, framing disclaimer |
| Body-sm | 13px | 400 | 1.5 | Verdict body copy, unsat-class list labels (matches existing card description) |
| Body | 14px | 400 | 1.43 | — (screen note) |
| Subheading | 18px | 600 | 1.3 | Reasoner name (existing) |
| — | 34px | 600 | 1.1 | Screen title "Reasoner." (existing inline; not a token — leave as-is) |

- Verdict headline uses **Body-sm at weight 600** (semibold) — no new size, just weight bump for emphasis.
- Unsat-class labels render in `--font-sans` (human labels, per D-02) — **never** `--font-mono` and
  **never** raw IRIs.

---

## Color

60 / 30 / 10 distribution — achromatic dominant, Signal Red as the sole accent:

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--surface-canvas` (#f5f5f5 / dark #111111) | Page background |
| Secondary (30%) | `--surface-card` (#ffffff / dark #1b1b1b) + `dg-frost` panels | Cards, result region surface |
| Accent (10%) | `--color-signal` (#e7000b / dark #ff3b44) | **Selection ring + Inconsistent verdict only** |
| Destructive | `--color-signal-ink` (#b8000e / dark #ff7079) | Transport/hard error line (`loadError`/`saveError` pattern) |

**Accent (Signal Red) reserved for — explicit list:**
1. The selected-reasoner ring/wash on the HermiT card (existing selection affordance).
2. The **Inconsistent** verdict treatment (headline, Badge, unsat count/wash).
3. The transport/hard-error line (D-09).

Accent is **NOT** used for: the Run button, the Cancel button, the Consistent verdict, the Unknown
verdict, the Cancelled verdict, the in-progress spinner, or the "Last checked" timestamp. Those are all
achromatic.

### ⚠ Token correction — do not propagate phantom tokens
The current `ReasonerScreen.jsx` references **`--color-accent`** (L176, L227) and **`--surface-focus`**
(L179), which are **undefined** anywhere in `ui-v2/src/styles/` — the selection ring/wash silently
resolves to nothing today. The CONTEXT's discretion note lists `--color-accent` as an existing token;
it is not. Any selection/accent styling this phase touches must use the **real** tokens:
`--accent-selection` / `--accent-selection-bg` (both alias Signal Red) or `--color-signal` directly.
Fixing these phantom refs on the card lines this phase already edits is in-scope cleanup.

---

## Verdict State Matrix (phase core)

The run state machine: `idle → running → {consistent | inconsistent | unknown | cancelled}` plus a
separate `error` line (transport/hard failures, never a verdict). All four verdicts render **inside the
expanded HermiT card** (D-01), replacing the "Selected — will be used when integration is complete" line.

| State | Hue rule | Tokens | Glyph | Badge | Distinguisher |
|-------|----------|--------|-------|-------|---------------|
| **Idle** (never run / pre-run) | achromatic | `--text-muted` | none | none | Framing disclaimer + enabled **Run check** button |
| **Running** | achromatic | `--text-muted` | spinner | none | Live elapsed-seconds counter + **Cancel** button; Run disabled |
| **Consistent** | achromatic (NOT green) | `--color-ink` text, `Badge variant="solid"` (ink bg) | `✓` | "Consistent" (solid) | Strong ink, confident weight 600 |
| **Inconsistent** | **Signal Red** (the one hue) | `--color-signal` text, `Badge variant="signal"`, `--color-signal-soft` wash | — | "Inconsistent" (signal) | Count + labeled class list |
| **Unknown** (server timeout) | achromatic (NOT amber) | `--text-muted` (#737373), `Badge variant="outline"` | `–` | "Inconclusive" (outline) | Mid-gray + explanatory "timed out" copy |
| **Cancelled** (user abort) | achromatic, quietest | `--ink-a56` faint text | `×` | none | Fainter than Unknown, no badge, single quiet line |

**Why Consistent isn't green / Unknown isn't amber:** the palette offers no green or amber token, and
DSYS-01 forbids inventing one. The three achromatic verdicts are told apart by **weight, opacity, glyph,
and copy** — never hue: Consistent = strong ink + `✓`; Unknown = mid-gray + `–` + outline badge;
Cancelled = faint `--ink-a56` + `×` + no badge. Only failure (Inconsistent) and selection spend the hue,
exactly as `--status-fail`/`--status-pass`/`--status-base` in `colors.css` prescribe
(`fail`=signal, `pass`=ink, `base`=mid-gray).

---

## Interaction States

| Element | State → treatment |
|---------|-------------------|
| **Run check** button | `Button variant="outline" size="sm"`, achromatic. Disabled (dimmed, `pointer-events:none`) while `running`. HermiT card only; Pellet gets no button (D-04). |
| **Cancel** button | Appears only during `running`, next to spinner. `Button variant="outline" size="sm"`, achromatic (Cancel is not destructive — no Signal Red). Aborts via `AbortController` (D-07). |
| Spinner + elapsed | `--text-muted` caption; counter ticks ~1s; format `Running… {n}s`. |
| "Last checked" | Caption (12px) `--text-muted`, relative time (e.g. "Last checked 2m ago"); shown with every completed verdict; persists in-memory across revisits (D-11). |
| HermiT badge | **Drops** "Integration pending" (D-04). Keeps "Active" (`Badge variant="solid"`) when selected. |
| Pellet card | Unchanged — keeps "Integration pending" `Badge variant="outline"`, no Run button. |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | **Run check** |
| Cancel control | **Cancel** |
| Framing disclaimer (always visible in HermiT result region) | *Schema-consistency check — verifies the ontology's logical structure, not design compliance.* |
| Idle / never-run body | *No check run yet. Run a schema-consistency check against the active project.* |
| Running | *Running… {n}s* |
| Consistent | *✓ Schema consistent — no unsatisfiable classes found.* |
| Inconsistent (headline) | *Schema inconsistent — {N} unsatisfiable class{es}.* (singular "class" when N=1) |
| Inconsistent (list) | Bulleted `Class.label` values (IRI-name fallback), no raw IRIs (D-02) |
| Unknown | *– Inconclusive — the reasoner timed out before finishing. Try again.* |
| Cancelled | *× Run cancelled — no result.* |
| Error state (transport/hard, D-09) | *Reasoner unavailable · {detail}* + inline **Retry** (mirror existing `--color-signal` `loadError` line) |
| Empty unsat list edge case | If `unsatisfiable_classes` is empty but `consistent:false`, show count only, no list |
| Destructive confirmation | none — nothing is deleted; Cancel is a benign abort, no confirm dialog |

Copy rules: verdicts say **"schema consistent / inconsistent,"** never "valid," "passed," or
"compliant" (D-03). "Unknown"/"Cancelled" are never styled as errors.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable |
| third-party | none | not applicable |

No component registry is in use — all primitives are hand-rolled in `ui-v2/src/components/`. No
`shadcn view`/`diff` gate required. This phase reuses existing `Button` and `Badge` only; **no new
shared primitive is expected** (per CONTEXT code_context).

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS — verb+noun CTA, four distinct verdict copies, "schema consistency" framing enforced, error path defined
- [x] Dimension 2 Visuals: PASS — result bound inside HermiT card, reuses `dg-frost`/card styling, four states told apart by weight/opacity/glyph
- [x] Dimension 3 Color: PASS — 60/30/10 honored; Signal Red confined to selection + Inconsistent + error; green/amber explicitly rejected per DSYS-01; phantom-token correction documented
- [x] Dimension 4 Typography: PASS — no new type roles; maps to existing scale; labels in `--font-sans`, never mono/IRI
- [x] Dimension 5 Spacing: PASS — new elements on 4px grid (16/12/8); existing off-grid values left untouched
- [x] Dimension 6 Registry Safety: PASS — no registry, no gate; reuses existing primitives only

**Approval:** approved 2026-07-12
