---
date: 2026-07-11
type: session
status: complete
tags: [quick-task, ui-v2, landing, hero-title, css]
---

# Session: Landing Hero Title Shrink — Quick Task 260711-gtz

**Duration:** ~6 minutes execution (planner + executor in background)
**Mode:** Quick task `/gsd-quick` (no discussion, research, or validation gates)
**Completed:** Yes

## What Was Done

Fixed the landing page hero title size so it fits inside the animated particle ring.

### Problem
The landing hero title ("Design Grammars." and "Encode your design intent.") was too large and spilled outside the particle ring on wide/short viewport windows.

**Root cause:** Title used `clamp(32px, 5.2vw, 76px)` — scaling off viewport **width** (`vw`). The particle ring is sized off `Math.min(vw, vh) * 0.365` — the smaller viewport dimension. On wide windows, width is large, so the title grew beyond what the ring constrained.

### Solution (CSS-only)

**File modified:** `ui-v2/src/landing/landing.css`

```css
/* Before */
.dgl-hero-l1 { font-size: clamp(32px, 5.2vw, 76px); }
.dgl-hero-l2 { font-size: clamp(15px, 2.2vw, 32px); }

/* After */
.dgl-hero-l1 { font-size: clamp(26px, 4.6vmin, 58px); }
.dgl-hero-l2 { font-size: clamp(13px, 1.95vmin, 25px); }
```

**Key insight:** The `landingEngine.js` reads computed font-size from the DOM title via `getComputedStyle(heroL1).fontSize`, then reuses it for the particle-text sampler. So one CSS file fix drives both the rendered title *and* the canvas-rendered ring text.

### Commits
- `c60f541`: fix(quick-260711-gtz): shrink hero title clamps and switch vw to vmin
- `c678e84`: docs(quick-260711-gtz): Decrease the size of title in the landing page so it fits the ring

### Verification Status
- **Code:** ✓ CSS values grep-verified; git status confirms only `landing.css` changed
- **Build:** ✓ Dev server started cleanly with no errors
- **Visual:** Pending — requires browser view of dev server on wide/short window to confirm title sits inside ring

## Decision Log

| Area | Decision |
|------|----------|
| **Unit change** | Switch from `vw` (viewport width) to `vmin` (smaller viewport dimension) to match ring's controlling dimension |
| **Clamp values** | Reduced min/max: `26px`/`58px` for L1 (was `32px`/`76px`), `13px`/`25px` for L2 (was `15px`/`32px`) |
| **Architecture** | CSS-only fix; no component restructuring or JavaScript changes needed |

## Next Steps

1. Run `npm --prefix ui-v2 run dev` and visually verify on a wide/short browser window
2. If title is still too large or too small, adjust the `4.6vmin` / `1.95vmin` coefficients or the `58px` / `25px` max clamps
3. If verified, task is complete; otherwise iterate on the CSS values

## Files & Impact

- **Modified:** `ui-v2/src/landing/landing.css` (2 font-size declarations)
- **Planning artifacts:** `.planning/quick/260711-gtz-decrease-the-size-of-title-in-the-landin/` (PLAN.md, SUMMARY.md)
- **State:** `.planning/STATE.md` updated with quick task row + last activity
