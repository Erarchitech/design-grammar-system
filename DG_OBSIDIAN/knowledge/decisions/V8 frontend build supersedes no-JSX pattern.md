# Decision: V8.0 frontend build (Vite+React) supersedes the no-JSX pattern

**Date:** 2026-07-07
**Phase:** 21 — Design System Foundation
**Status:** Locked
**Impact:** Frontend architecture for v8.0; model-viewer and v9.0 onwards inherit this

## Summary

The v7.0 "no JSX build for main UI" decision is **explicitly retired** for the V8.0 UI rebuild. The V2 design system (Design Grammars V2) is implemented as a **new Vite + React (JSX)** app in JavaScript.

## Context

### The Legacy Decision (v2.0–v7.0)
- Single-file React 18 SPA without a build step: `graph-viewer/index.html`
- JSX replaced with `React.createElement()` calls
- Minimized the JavaScript toolchain
- **Worked for:** A single dashboard app (dark-themed, 188KB single file)
- **Became:** A blocker for modular component composition and team scaling

### The V8.0 Context
- The dark UI is **retiring** at Phase 26 cutover
- The V2 design system includes **~23 ready-made JSX recipes** in the design artifact
- Phases 21–25 build a new product with four screen layers, layered transitions, and shared primitives
- The existing `model-viewer/` app (Vite + React + JSX) proved the pattern works in this repo

### The Decision (Phase 21)
**Vite + React (JSX, JavaScript)** because:

1. **_ds recipes are JSX** — they drop in nearly verbatim; no hand-translation of 23 components
2. **Modular, composable** — each phase (22–25) purely composes; no ad-hoc component porting
3. **DX precedent** — the existing model-viewer app validates the approach in the repo
4. **Toolchain is mature** — Vite is the team's standard; npm/node already present for Docker builds
5. **Modernization** — the "no-build" decision was specific to v1–v7's single dark UI; retiring it is scope-appropriate

## Implications

### In scope (v8.0)
- New V2 app: Vite + React, single JavaScript codebase for all four screens
- Phase 21 ports the full component library (23 components)
- Phases 22–25 compose; no architecture changes

### Out of scope (v8.0)
- TypeScript — JavaScript stays the repo language
- Monorepo — one Vite app, one codebase
- Breaking changes to model-viewer — it retires at Phase 26, not refactored mid-milestone

### Future (v9.0+)
- The model-viewer component/Vite pattern becomes standard for the repo
- Any new frontend work post-v8.0 uses Vite + React + JSX
- The no-JSX pattern is archived as a v1–v7 historical choice

## Reversibility

**Not reversible without major rework.** The _ds recipes are JSX; adopting them requires a build step.
- If Vite proves problematic mid-phase: could switch to CRA or webpack, but the component source remains the same
- If pure vanilla JS becomes required: would need to hand-translate all 23 recipes (days of work)

## Validation

- Phase 21 context discusses and locks the decision
- Phase 21 planning will validate Vite config and build output
- Phase 21 execution will prove the specimen page renders
- Phase 22 onward will iteratively validate screen composition
