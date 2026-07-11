---
tags: [decision, phase-822, design-system, color, verdict-states]
phase: 822
date: 2026-07-12
status: approved
---

# Phase 822: Monochromatic Verdict Mapping onto DSYS-01

**Decision:** Render the four reasoner verdict states (Consistent / Inconsistent / Unknown / Cancelled) onto the strictly monochromatic design system (DSYS-01) by differentiating via **weight, opacity, glyph, and copy** — never hue.

## Problem

The Phase 822 CONTEXT uses shorthand copy: Consistent = "green," Inconsistent = "red," Unknown = "amber timed out." But the design system (DSYS-01) is achromatic by principle: *"Color is absence, not expression. One chromatic hue exists — Signal Red."*

The palette has:
- Achromatic stack: canvas, paper, surface-alt, ink, mid-gray, hairlines
- One chromatic hue: Signal Red (`--color-signal`)

No green or amber tokens exist, and DSYS-01 forbids inventing them.

## Decision

Map the four verdicts onto the monochromatic stack:

| Verdict | Hue Rule | Tokens | Glyph | Badge | Copy Distinction |
|---------|----------|--------|-------|-------|------------------|
| **Consistent** | achromatic | `--color-ink` at weight 600 | `✓` | "Consistent" (solid) | Strong, confident, full-opacity text |
| **Inconsistent** | **Signal Red** (the sole hue) | `--color-signal`, `--color-signal-soft` wash, `Badge variant="signal"` | — | "Inconsistent" (signal) | The one verdict spending the hue; count + labeled unsat list (D-02) |
| **Unknown** | achromatic, mid-gray | `--text-muted` (#737373), `Badge variant="outline"` | `–` | "Inconclusive" (outline) | Mid-gray + explanatory copy ("timed out before finishing") |
| **Cancelled** | achromatic, faintest | `--ink-a56` (faint alpha text) | `×` | none | No badge, quietest treatment (user-initiated abort is a non-event) |

**Why this works:**
- Consistent = strong ink + `✓` glyph reads as "all good" without needing green.
- Inconsistent = **only place Signal Red is spent** (besides selection + error line), making failure unmistakable per `--status-fail` semantics.
- Unknown ≠ error: mid-gray + `–` glyph + "inconclusive" copy (never "failed," never red) honors criterion 3 (timeout is honest result, not a fault).
- Cancelled = faintest, no badge, reads as a non-event (user stopped waiting).

This aligns with `colors.css` existing semantics: `--status-fail` (Signal Red) + `--status-pass` (ink) + `--status-base` (mid-gray).

## Why Not Green/Amber?

1. **No tokens exist** — `colors.css` defines only Signal Red as chromatic; a verdant or amber CSS var would have to be invented.
2. **DSYS-01 forbids it** — "One chromatic hue exists — Signal Red." Strict by design; breaking this principle cascades to other screens' color budgets.
3. **Differentiation doesn't require hue** — Weight, opacity, glyph, and copy are orthogonal, sufficient channels.

## Related Decisions

- [[decisions/DSYS-01 Monochromatic foundation with Signal Red accent|DSYS-01 color principle]] (design system root)
- [[decisions/D-03 verdict is labeled "schema consistency" not validation|Phase 822 D-03]] (copy framing)

## Notes for Phase 822 Planner & Executor

1. The four verdicts render inside the expanded HermiT card (D-01), replacing the "Selected — will be used" line.
2. Inconsistent always shows count + human-readable label list (D-02); label resolution location (sidecar vs proxy vs UI) flagged for researcher (D-49).
3. Transport/hard errors (unreachable sidecar, 5xx, malformed JSON) surface as a separate **error line** using `--color-signal` + inline Retry, mirror existing `loadError` pattern (D-09). Errors are not verdicts.
4. While running: spinner (muted) + live elapsed counter + Cancel button (D-07); Run button disabled.
5. Result persists in-memory across screen revisits within the session (D-11); timestamp "Last checked" shown with every verdict.

## Phantom Token Cleanup (Secondary Finding)

While writing the spec, discovered `ReasonerScreen.jsx` references two undefined tokens:
- `--color-accent` (lines 176, 227) — intended for selection ring/text
- `--surface-focus` (line 179) — intended for selected-card background wash

Neither is defined in `ui-v2/src/styles/`. The selection currently silently fails. The correct tokens are `--accent-selection` and `--color-signal` (both = Signal Red). Fixing these in-scope on lines the phase edits is in the UI-SPEC as a cleanup note; executor to confirm whether this is strictly in-scope or spun to a separate task.

---

**UI-SPEC:** `.planning/phases/822-owl-2-dl-reasoning-integration-reasoner-screen-wiring/822-UI-SPEC.md`
**Session:** [[sessions/2026-07-12 Phase 822 UI-SPEC|2026-07-12 Phase 822 UI-SPEC]]
