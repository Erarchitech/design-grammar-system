---
phase: 21-design-system-foundation
plan: "21-01"
status: complete
completed: 2026-07-07
commits:
  - 1baf5b0 feat(21-01) scaffold app + tokens + fonts
  - 03712f2 feat(21-01) 23-component primitive library
  - f3f7a3a feat(21-01) specimen page
duration: ~35min
---

# Summary 21-01: Design System Foundation

## What shipped

- **`ui-v2/`** — new Vite 5 + React 18 (JSX, JS) app, the single V2 app that will host all four screen layers (D-01/D-02/D-03). Dev server proxies `/neo4j`, `/n8n`, `/data-service` to the live nginx at :8080.
- **Tokens** — `src/styles/tokens/{fonts,colors,typography,spacing,effects,base}.css` + `styles.css` entry, copied from `design/v2/_ds` preserving the 6-file split (D-05).
- **Fonts self-hosted** (D-06) — 8 woff2 binaries (latin) vendored from @fontsource into `src/styles/tokens/fonts/`; `fonts.css` Google-CDN import replaced with local `@font-face`. Oswald retained as `--font-annotation` (D-07).
- **23 primitives** in `src/components/{forms,display,surfaces}` reconstructed as clean JSX from `_ds_bundle.js` (original `.jsx` sources are not on disk — bundle-only). Barrel export at `src/components/index.js`.
- **Specimen page** (dev-only, `/#specimen`) rendering token swatches and every component variant; root path shows a blueprint placeholder until the Phase 22 shell.

## Decisions made (Claude's discretion / deviations)

- **Directory name**: `ui-v2/` (D-10 left to planner).
- **Status token alignment**: on-disk `colors.css` had `--status-fail: var(--color-ink)` with a "SELECTION ONLY" comment — contradicting DSYS-01/MVIEW-03, the `_ds_manifest.json` token catalog, and the recipes (destructive Button is red). Aligned: `--status-fail: var(--color-signal)`, `--status-pass: ink`, `--status-base: mid-gray`, `--status-destructive: signal-ink`. The reference spec files stay untouched.
- **No router library** — specimen gated by `import.meta.env.DEV` + `#specimen` hash; the V2 app is layer-based, not URL-routed.
- **Icons**: recipes inline their few SVGs (search, chevron, check); no Lucide dependency needed yet — revisit if later phases need more glyphs.

## Verification results

- `npm run build` clean (54 modules, no warnings).
- Browser (Vite dev): zero console errors; computed checks — body bg `#f5f5f5`, button 18px/36px pill, frost 78% white + 14px blur + hairline, `document.fonts` lists Geist 400/500/600, Geist Mono 400/500, Oswald 400/500/600 all loaded locally; annotation captions Oswald uppercase, +1.2px tracking; the only chromatic renders are signal-red affordances. DSYS-01/02/03 ✓ (screenshots reviewed in-session).

## Notes for later phases

- Phase 22 replaces `App.jsx` placeholder with the layered shell; keep the `#specimen` dev gate.
- `design/v2/Design Grammars V2.dc.html` + `support.js` hold the landing/particle/transition behaviour to port next.
