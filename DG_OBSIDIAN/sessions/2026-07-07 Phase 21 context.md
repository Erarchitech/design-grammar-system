# Session: Phase 21 Design System Foundation - Context Gathering

**Date:** 2026-07-07
**Duration:** 1 session
**Phase:** 21 — Design System Foundation
**Status:** Context captured, ready for planning

## Summary

Discussed and locked all major implementation decisions for the V2 UI design system foundation phase. The phase will deliver a new Vite+React app with the full component library, light token CSS, self-hosted fonts, and a specimen page proving all primitives render per spec.

## Work Completed

- **Phase 21 context gathering** via discuss-phase workflow
- **4 gray areas discussed:**
  1. App architecture & build → Vite + React (JSX), single V2 app, recipes copied into src/
  2. Token & font delivery → 6-file token split, self-hosted fonts, Oswald annotation
  3. Primitive scope & proof → full 23-component set, dev-only specimen page
  4. Legacy coexistence → new top-level directory, Vite dev server only until Phase 26
- **Decision notes** captured in 21-CONTEXT.md
- **Discussion log** preserved in 21-DISCUSSION-LOG.md for audit

## Key Decisions

### Architecture (supersedes legacy "no JSX")
- **Build:** Vite + React (JSX), JavaScript — **new** instead of the retiring no-build pattern
- **App shape:** Single V2 app with layered shell (landing/graph/model/projects); old model-viewer app retires at cutover
- **Components:** Copy _ds recipes into src/components/; keep design/v2/_ds as untouched spec reference

### Tokens & fonts
- **CSS delivery:** 6-file split (tokens/fonts, colors, typography, spacing, effects, base) + styles.css entry — keeps diffs clean against spec updates
- **Font loading:** Self-host Geist/Geist Mono/Oswald woff2 (no Google CDN); fits the all-local Docker stack ethos
- **Annotation face:** Keep Oswald; swappable later via token + font files

### Primitives
- **Scope:** Full 23-component library ported now — Button through RunTile — so phases 22–25 purely compose instead of pulling dependencies ad hoc
- **Proof:** /specimen dev route renders all variants + token swatches (mirrors _ds guideline cards); verifiable in browser before phase 22

### Coexistence
- **Location:** New top-level dir (e.g. `graph-viewer-v2/`) alongside the retiring `graph-viewer/`; legacy dark UI keeps :8080 until Phase 26
- **Dev serving:** Vite dev server through phases 21–25; no Docker changes until Phase 26 cutover

## Claude's Discretion

- Exact directory name (`graph-viewer-v2/`, `ui-v2/`, etc.)
- Font sourcing (npm `geist` package vs downloaded woff2 binaries)
- Icon loading (Lucide CDN vs inlined SVGs)
- Vite proxy and internal component style organization

## Implications for Downstream Phases

- **Phase 22** (Navigation Shell, Landing, Auth) composes from the foundation; no primitive porting
- **Phase 23** (Graph Viewer) consumes canvas/panel/dialog primitives; no new components
- **Phase 24** (Model Viewer) reuses primitives for sidebar/legend/run-strip; no new components
- **Phase 25** (Projects) uses tile/grid primitives
- **Phase 26** (Cutover) replaces design-grammars container with V2 build; old model-viewer deprecated

## Canonical References for Planning

All in .planning/phases/21-design-system-foundation/21-CONTEXT.md canonical_refs section:
- `design/v2/Design Grammars V2.dc.html` — visual spec (source of truth)
- `design/v2/_ds/.../readme.md` — design system philosophy
- `design/v2/_ds/.../tokens/` — 6 token CSS files
- `design/v2/_ds/.../components/` — JSX recipes to copy
- `design/v2/_ds/.../_ds_manifest.json` — component inventory

## Next Steps

1. `/gsd-plan-phase 21` — Create the detailed execution plan
2. Plan will resolve:
   - Exact new directory name & structure
   - Vite config (proxy setup, output paths)
   - Font sourcing method
   - Specimen page design & route structure
   - Icon loading strategy
   - CSS organization within components
3. Execution will port tokens, recipes, and build the specimen page

---

*Prepared by: Claude Fable 5*
*Context source: .planning/phases/21-design-system-foundation/*
