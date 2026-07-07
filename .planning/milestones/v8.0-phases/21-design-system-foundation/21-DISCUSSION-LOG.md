# Phase 21: Design System Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 21-design-system-foundation
**Areas discussed:** App architecture & build, Token & font delivery, Primitive scope & proof, Legacy coexistence

---

## App architecture & build

| Option | Description | Selected |
|--------|-------------|----------|
| Vite + React (JSX) | New Vite app like model-viewer; _ds JSX recipes drop in nearly verbatim | ✓ |
| No-build single-file React | Keep prior 'no JSX build' pattern; hand-translate recipes into React.createElement | |
| Plain HTML/CSS/JS | Mirror the mockup's .dc.html vanilla approach | |

**User's choice:** Vite + React (JSX)

| Option | Description | Selected |
|--------|-------------|----------|
| Single V2 app | One Vite app hosting all four screen layers; old model-viewer retires at cutover | ✓ |
| V2 app + existing model-viewer | Keep model-viewer separate and reskin it | |

**User's choice:** Single V2 app

| Option | Description | Selected |
|--------|-------------|----------|
| JavaScript (JSX) | Matches model-viewer and .jsx recipes | ✓ |
| TypeScript (TSX) | Stronger contracts but recipe conversion needed | |
| You decide | Claude picks during planning | |

**User's choice:** JavaScript (JSX)

| Option | Description | Selected |
|--------|-------------|----------|
| Copy & adapt into src/ | App owns component copies; _ds stays untouched reference | ✓ |
| Import _ds directly | Vite sources from the spec directory | |
| Rewrite from scratch | Recipes as visual reference only | |

**User's choice:** Copy & adapt into src/

---

## Token & font delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Copy 6 files as-is | Preserve the tokens/{fonts,colors,typography,spacing,effects,base}.css split for diffability | ✓ |
| Consolidate into one file | Single tokens.css | |
| You decide | Claude picks during planning | |

**User's choice:** Copy 6 files as-is

| Option | Description | Selected |
|--------|-------------|----------|
| Self-hosted in image | Vendor woff2, serve from the container; offline-safe | ✓ |
| Google Fonts CDN | Keep the @import as shipped in tokens | |
| You decide | Claude picks during planning | |

**User's choice:** Self-hosted in image

| Option | Description | Selected |
|--------|-------------|----------|
| Keep Oswald | Free substitute, already tokenized as --font-annotation | ✓ |
| Licensed condensed face | DIN Condensed / Tungsten; requires procurement | |

**User's choice:** Keep Oswald

---

## Primitive scope & proof

| Option | Description | Selected |
|--------|-------------|----------|
| Full recipe set | Port all ~23 _ds components now; phases 22–25 purely compose | ✓ |
| DSYS-03 five only | Just Button, Input, frost, blueprint, callout | |
| Five + likely-needed | The five plus phase-22 guesses | |

**User's choice:** Full recipe set

| Option | Description | Selected |
|--------|-------------|----------|
| Specimen dev page | Dev-only /specimen route with all variants + token swatches | ✓ |
| Storybook | Full Storybook tooling | |
| Verified in phase 22 | No demo surface | |

**User's choice:** Specimen dev page

---

## Legacy coexistence

| Option | Description | Selected |
|--------|-------------|----------|
| New top-level dir | Sibling of graph-viewer/; legacy serves :8080 untouched until Phase 26 | ✓ |
| Inside graph-viewer/ | e.g. graph-viewer/v2/ next to model-viewer | |
| Replace immediately | Rewrite graph-viewer/index.html now | |

**User's choice:** New top-level dir

| Option | Description | Selected |
|--------|-------------|----------|
| Vite dev server only | npm run dev against Docker backends; no new container until Phase 26 | ✓ |
| Parallel Docker container | design-grammars-v2 service on :8081 from phase 21 | |
| You decide | Claude picks during planning | |

**User's choice:** Vite dev server only

---

## Claude's Discretion

- Exact new directory name (e.g. `graph-viewer-v2/` or `ui-v2/`)
- Vite proxy configuration details
- Font-file sourcing method (npm `geist` package vs downloaded woff2)
- Icon loading approach (Lucide CDN vs inlined SVGs)
- Internal styles organization within components

## Deferred Ideas

None — discussion stayed within phase scope.
