---
phase: quick-260711-gtz
plan: 01
subsystem: ui-v2/landing
tags: [css, landing, hero-title]
dependency-graph:
  requires: []
  provides: [landing-hero-title-vmin-scaling]
  affects: [ui-v2/src/landing/landing.css]
tech-stack:
  added: []
  patterns: ["vmin-based fluid typography tied to min(vw, vh) viewport dimension"]
key-files:
  created: []
  modified:
    - ui-v2/src/landing/landing.css
decisions:
  - "Switched .dgl-hero-l1 / .dgl-hero-l2 font-size clamps from vw to vmin to track the particle ring radius (Math.min(vw, vh) * 0.365 in landingEngine.js), preventing title overflow on wide/short viewports"
metrics:
  duration: ~10min
  completed: 2026-07-11
status: complete
---

# Quick Task 260711-gtz: Decrease Landing Hero Title Size Summary

Reduced and re-scaled the landing hero title (`.dgl-hero-l1`) and subline (`.dgl-hero-l2`) font-size clamps in `ui-v2/src/landing/landing.css`, switching from `vw`-based to `vmin`-based scaling so the title tracks the particle ring radius (which is driven by `Math.min(vw, vh)` in `landingEngine.js`) instead of viewport width alone.

## What Changed

**Task 1 — CSS clamp edits (commit `c60f541`)**

| Rule | Before | After |
|------|--------|-------|
| `.dgl-hero-l1` font-size | `clamp(32px, 5.2vw, 76px)` | `clamp(26px, 4.6vmin, 58px)` |
| `.dgl-hero-l2` font-size | `clamp(15px, 2.2vw, 32px)` | `clamp(13px, 1.95vmin, 25px)` |

Only these two `font-size` declarations were changed. No other CSS properties (line-height, letter-spacing, white-space, font-family, positioning) were touched. `ui-v2/src/landing/landingEngine.js` was not modified — `heroMetrics()` reads the title's computed font-size via `getComputedStyle`, so the particle-sampling text automatically follows the new CSS values.

## Verification

**Automated (completed):**
- `grep -n "4.6vmin" ui-v2/src/landing/landing.css` → found at line 31
- `grep -n "1.95vmin" ui-v2/src/landing/landing.css` → found at line 40
- `git status --short ui-v2/src/landing/` confirmed only `landing.css` modified, `landingEngine.js` untouched

**Dev server smoke test (completed):**
- `npm --prefix ui-v2 run dev` started cleanly with Vite 5.4.21, no build/compile errors, ready in ~627ms, served at `http://localhost:5173/`
- Server was stopped cleanly after the check (no processes left running)

**Visual checkpoint (Task 2 — NOT verified, no human present):**
This plan's Task 2 is a `checkpoint:human-verify` gate requiring visual confirmation that the "Design Grammars." title and "Encode your design intent." subline render fully inside the particle ring, including at wide/short window aspect ratios, and a judgment call on whether the new size looks right.

This execution environment has no browser/screenshot automation tool available, and the hero title is rendered via an animated canvas particle system (`landingEngine.js` `.drawHero()`), not static HTML — so `curl`-ing the dev server or inspecting raw markup cannot substitute for an actual rendered view. This visual/subjective check could not be completed in this run.

**What a human still needs to do:**
1. Run `npm --prefix ui-v2 run dev`, open `http://localhost:5173`
2. Watch the hero title materialize from the particle ring and confirm both lines stay fully inside the ring
3. Resize the browser to a wide/short shape and re-confirm
4. If too small, increase `.dgl-hero-l1`'s vmin coefficient/cap (e.g. `clamp(28px, 5vmin, 64px)`); if it still overflows, decrease further

## Deviations from Plan

None - Task 1 executed exactly as written. Task 2 (human-verify checkpoint) could not be completed due to lack of visual/browser tooling in this execution environment; documented above per the orchestrator's instruction to note what was and wasn't verified rather than block indefinitely.

## Self-Check: PASSED

- FOUND: ui-v2/src/landing/landing.css (clamp values confirmed via grep at lines 31 and 40)
- FOUND: commit c60f541 (`git log --oneline` confirms `fix(quick-260711-gtz): shrink hero title clamps and switch vw to vmin`)
