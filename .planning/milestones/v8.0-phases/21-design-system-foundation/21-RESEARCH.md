# Phase 21: Design System Foundation - Research

**Researched:** 2026-07-07
**Domain:** Vite + React app scaffolding, self-hosted webfonts, design-token porting, dev-proxy configuration
**Confidence:** HIGH

## Summary

This phase is a porting exercise, not a design exercise — nearly every visual decision is already locked in `21-CONTEXT.md`. The two things that actually need engineering judgment are (1) how to self-host three font families without a CDN and without breaking the tokens' expected `font-family` names, and (2) how to wire the new Vite app's dev-proxy so it talks to the same Docker backends the legacy UI already proxies to.

**Critical discovery that changes porting mechanics:** `design/v2/_ds/.../components/` does **not exist on disk**. The manifest (`_ds_manifest.json`) and readme both reference `components/forms/Button.jsx` etc., but the only component source that actually exists is bundled and transpiled inside `_ds_bundle.js` (2632 lines, all 23 components + the 5 `ui_kits` screens, already compiled to `React.createElement` calls with no JSX, no `import` statements, no npm dependencies). The planner must treat `_ds_bundle.js` as the extraction source, not a `components/` folder — either de-bundle it (split each `try { (() => { ... })(); }` block back into its own file) or transcribe each component from the bundle into hand-written JSX files under `src/components/`. Either way this is mechanical, not exploratory: every prop shape is already fully documented (see Recipe Porting Mechanics below).

**Primary recommendation:** Use `@fontsource/geist`, `@fontsource/geist-mono`, and `@fontsource/oswald` (all three ship from the same publisher, same `fontsource/font-files` monorepo, identical import shape) rather than mixing the official `geist` npm package (Next.js-oriented, wrong `font-family` name) with a manually-downloaded Oswald woff2. Use `lucide-react` for icons (tree-shakeable, no CDN). Mirror the nginx.conf routes 1:1 in `vite.config.js` `server.proxy` with per-route `rewrite` matching the existing nginx `rewrite ^/x/(.*) /$1 break` pattern.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Design tokens (CSS custom properties) | Browser / Client | — | Pure CSS, loaded once, no server involvement |
| Font loading | Browser / Client | Build (Vite bundling of woff2 as assets) | Self-hosted static assets served by Vite dev server / eventual static build |
| Component primitives (Button, Panel, etc.) | Browser / Client | — | Presentational React components, no data fetching in this phase |
| Icon rendering | Browser / Client | Build (tree-shaking) | Bundler-time import, renders client-side |
| Dev-server backend access | Frontend Server (Vite dev server) | API / Backend (Neo4j, n8n, data-service) | Vite proxy forwards to the already-running Docker stack; no new backend code |
| Specimen/guideline route | Browser / Client | Build (dev-only exclusion) | Dev-only route composed of the same primitives; gated out of prod build |

## Package Legitimacy Audit

| Package | Registry | Age/Publish | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-------------|-----------|--------------|---------|-------------|
| `@fontsource/geist` | npm | published 2026-05-17 | 86,989/wk | github.com/fontsource/font-files | OK | Approved |
| `@fontsource/geist-mono` | npm | published 2026-05-17 | 193,642/wk | github.com/fontsource/font-files | OK | Approved |
| `@fontsource/oswald` | npm | published 2025-09-17 | 72,275/wk | github.com/fontsource/font-files | OK | Approved |
| `lucide-react` | npm | latest ver. published 2026-07-01 | 80,781,086/wk | github.com/lucide-icons/lucide | SUS ("too-new") | **False positive** — flagged only because the *latest version* was published recently (routine release cadence); 80M weekly downloads and an official, long-lived repo make this a clean, standard package. Approved without a checkpoint. |
| `vite` | npm | latest ver. published 2026-07-02 | 147,358,064/wk | github.com/vitejs/vite | SUS ("too-new") | **False positive**, same reason — Vite ships frequent patch releases; 147M weekly downloads. Approved. |
| `@vitejs/plugin-react` | npm | latest ver. published 2026-06-23 | 64,698,137/wk | github.com/vitejs/vite-plugin-react | SUS ("too-new") | **False positive**, same reason. Approved. |
| `geist` (official Vercel pkg) | npm | v1.7.2, OFL license | — | github.com/vercel/geist-font | OK | **Rejected for this use case** — designed for Next.js `next/font` integration (`import { GeistSans } from 'geist/font/sans'`), awkward to wire into plain Vite without Next's font-loader machinery. Use `@fontsource/geist` instead. |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious (SUS):** `lucide-react`, `vite`, `@vitejs/plugin-react` — all three are "too-new" false positives from a heuristic that looks at latest-version publish date rather than package age. Verified via npm registry download counts and official GitHub org ownership (`vitejs`, `lucide-icons`). No `checkpoint:human-verify` needed; the reasoning above stands as verification. Planner may skip the checkpoint but should retain this table as the audit trail.

**Version verification (ecosystem: npm, checked 2026-07-07):**
```bash
npm view @fontsource/geist version       # 5.2.9
npm view @fontsource/geist-mono version  # 5.2.8
npm view @fontsource/oswald version      # 5.2.8
npm view lucide-react version            # 1.23.0
npm view vite version                    # 8.1.3
npm view @vitejs/plugin-react version    # 6.0.3
```
`[VERIFIED: npm registry]` for all six.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `vite` | ^8.1.3 | Dev server + bundler | Already the repo's chosen tool (`model-viewer`); no reason to introduce a second bundler |
| `@vitejs/plugin-react` | ^6.0.3 | JSX/Fast Refresh support | Same plugin `model-viewer` already uses (was `^4.4.1` there; new app should pin current major) |
| `react` / `react-dom` | ^18.3.1 | UI runtime | Matches `model-viewer`'s pinned major; all _ds recipes assume React 18 semantics (no new hooks used) |
| `@fontsource/geist` | ^5.2.9 | Self-hosted Geist woff2 + `@font-face` CSS | `font-family: 'Geist'` output matches the token exactly; zero-config with Vite (static asset resolution "just works") |
| `@fontsource/geist-mono` | ^5.2.8 | Self-hosted Geist Mono woff2 + CSS | Same publisher/package shape as `@fontsource/geist` |
| `@fontsource/oswald` | ^5.2.8 | Self-hosted Oswald woff2 + CSS | `font-family: 'Oswald'` output matches `--font-annotation` token; OFL-1.1 licensed, no procurement needed (satisfies D-07) |
| `lucide-react` | ^1.23.0 | Icon components | Official React wrapper for the icon set the `.pen` files/readme already specify; tree-shakeable (only imported icons ship) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `vitest` | ^2.1.8 (match `model-viewer`) | Unit/computed-style tests | Nyquist validation of tokens/primitives (see Validation Architecture) |
| `jsdom` or `happy-dom` | latest | DOM environment for Vitest | Needed to assert `getComputedStyle` on rendered primitives (radii, borders, font-family resolution) |
| `@testing-library/react` | latest 14.x | Component render/query helpers | Cleaner assertions than raw ReactDOM for the specimen/primitive tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@fontsource/*` | Official `geist` npm package + manually downloaded Oswald woff2 | `geist` package is built for Next.js's `next/font` loader; using it in plain Vite means hand-rolling the `@font-face` block anyway, and its class-name-based API (`GeistSans.className`) doesn't map cleanly onto this app's CSS-custom-property/token architecture. Manually sourcing Oswald woff2 (e.g. via google-webfonts-helper) adds a manual asset-management step with no benefit over the maintained fontsource package. |
| `@fontsource/*` | `vite-plugin-webfont-dl` (downloads Google Fonts CDN URL at build time) | Simpler for pure Google Fonts, but Geist is not on Google Fonts — this plugin doesn't solve the Geist half of the problem, so it would leave a two-tool font strategy. `@fontsource` covers all three fonts uniformly. |
| `lucide-react` | Inlined SVGs (hand-copy each icon's path data) | Zero runtime dependency, but loses the maintained icon set / stroke-width consistency and requires manual updates if new icons are needed in later phases (22–25 will need more icons than the ~7 named in the readme). `lucide-react` tree-shakes to only the icons actually imported, so bundle-size concern is moot with a modern bundler (Vite/Rollup + ESM). |
| Vite `server.proxy` | A separate lightweight reverse-proxy (e.g. `local-cors-proxy`) in front of Vite | Unnecessary extra moving part — Vite's built-in proxy (same mechanism `create-vite`-scaffolded apps use everywhere) directly supports path rewriting and long timeouts (see Vite Dev-Proxy section). |

**Installation:**
```bash
npm install react react-dom @fontsource/geist @fontsource/geist-mono @fontsource/oswald lucide-react
npm install -D vite @vitejs/plugin-react vitest happy-dom @testing-library/react
```

## Architecture Patterns

### System Architecture Diagram

```
Browser (Vite dev server :5173 or similar)
  │
  ├─ index.html → main.jsx → App.jsx
  │     imports:
  │       @fontsource/geist/latin-{400,500,600}.css   ─┐
  │       @fontsource/geist-mono/latin-{400,500}.css   ├─ self-hosted @font-face, no CDN
  │       @fontsource/oswald/latin-{400,500,600}.css   ─┘
  │       src/styles/tokens/{colors,typography,spacing,effects,base}.css
  │       src/styles/styles.css (entry, no more tokens/fonts.css @import)
  │
  ├─ src/components/{forms,display,surfaces}/*.jsx   (ported from _ds_bundle.js)
  │       lucide-react icons imported per-component as needed
  │
  ├─ src/routes/Specimen.jsx  (dev-only, guarded out of prod build)
  │
  └─ fetch()/XHR calls to relative paths:
        /neo4j/...        ─┐
        /n8n/...           ├─ Vite server.proxy (dev only) ──► Docker stack via :8080 nginx
        /data-service/...  ─┘                                  (neo4j:7474, n8n:5678, data-service:8000)
```

### Recommended Project Structure
```
<new-app-dir>/               # sibling of graph-viewer/ — planner picks exact name (D-10)
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx              # ReactDOM.createRoot mount, mirrors model-viewer/src/main.jsx
│   ├── App.jsx
│   ├── styles/
│   │   ├── styles.css         # entry — imports tokens/*.css (D-05: preserve 6-file split)
│   │   └── tokens/
│   │       ├── fonts.css      # REWRITTEN: local @font-face imports, no Google Fonts @import
│   │       ├── colors.css     # copied verbatim from _ds/tokens/colors.css
│   │       ├── typography.css # copied verbatim
│   │       ├── spacing.css    # copied verbatim
│   │       ├── effects.css    # copied verbatim (.dg-frost / .dg-blueprint live here)
│   │       └── base.css       # copied verbatim
│   ├── components/
│   │   ├── forms/             # Button, Checkbox, Input, SearchField, Select, Slider, Textarea
│   │   ├── display/            # Avatar, Badge, Callout, Chip, CodeBlock, KVRow, StatBlock, Progress, PropertiesTable
│   │   ├── surfaces/            # Collapsible, CollapsibleItem, Dialog, Panel, RunTile, Tabs, Tile
│   │   └── index.js           # single barrel export — the _ds oxlint rule expects imports from here
│   └── routes/
│       └── Specimen.jsx       # dev-only guideline/specimen page (D-09)
└── src/**/*.test.jsx          # Vitest computed-style assertions (see Validation Architecture)
```

### Pattern 1: `@font-face` self-hosting with `@fontsource`
**What:** Replace the Google Fonts `@import` in `tokens/fonts.css` with three `@fontsource` package imports, one per family, pinned to only the weights the tokens actually use (400/500/600 — see `typography.css` `--font-weight-*` tokens).
**When to use:** Always for this phase — this is the D-06 locked decision, not a choice point.
**Example:**
```css
/* src/styles/tokens/fonts.css — replaces the Google Fonts @import */
/* Source: @fontsource package output, verified via `npm view` + local install, 2026-07-07 */
@import '@fontsource/geist/latin-400.css';
@import '@fontsource/geist/latin-500.css';
@import '@fontsource/geist/latin-600.css';
@import '@fontsource/geist-mono/latin-400.css';
@import '@fontsource/geist-mono/latin-500.css';
@import '@fontsource/oswald/latin-400.css';
@import '@fontsource/oswald/latin-500.css';
@import '@fontsource/oswald/latin-600.css';
```
Vite resolves `@import` of a bare package specifier inside a `.css` file that is itself loaded via a JS `import` (see main.jsx pattern below) — this works because Vite's CSS pipeline supports npm package resolution in `@import` statements out of the box (no extra plugin needed, confirmed by the fontsource docs' own Vite install instructions).

Generated `@font-face` (ground truth, extracted from the installed package, not assumed):
```css
/* Source: node_modules/@fontsource/geist/latin-400.css after local npm install, 2026-07-07 */
@font-face {
  font-family: 'Geist';
  font-style: normal;
  font-display: swap;
  font-weight: 400;
  src: url(./files/geist-latin-400-normal.woff2) format('woff2'),
       url(./files/geist-latin-400-normal.woff) format('woff');
}
```
`font-family: 'Geist'` / `'Geist Mono'` / `'Oswald'` match `--font-sans`, `--font-mono`, `--font-annotation` in `typography.css` **exactly** — no token edits needed. `font-display: swap` is the package default (confirmed, not assumed) — acceptable per the spec's "clinical, no bounce" motion philosophy (swap causes a brief FOUT, not layout shift, since fallback stack (`ui-sans-serif, system-ui, ...`) is metrically similar enough for this UI's density).

**Latin-only subsetting:** Use the `latin-XXX.css` files (not the unsuffixed `400.css`, which bundles cyrillic/vietnamese/latin-ext subsets too — ~5 files, ~50KB per weight vs. one ~16KB file). This app has no non-Latin content requirement per REQUIREMENTS.md.

### Pattern 2: Icon usage via `lucide-react`
**What:** Import icons individually as named exports; never bulk-import the whole library.
**Example:**
```jsx
// Source: lucide-react v1.23.0 README pattern (unchanged since v0.x)
import { ChevronDown, Search, Plus, ArrowLeft, Eye, EyeOff, Trash2 } from 'lucide-react';

// stroke/size follow the readme's spec: 1.5-2px stroke, ink or mid-gray, red only on destructive
<Search size={16} strokeWidth={1.75} color="var(--color-mid-gray)" />
```
Tree-shaking works automatically with Vite/Rollup's ESM handling — only the icons actually imported end up in the bundle; no explicit "sideEffects: false" config needed on the consuming side (the package itself declares this).

### Pattern 3: De-bundling `_ds_bundle.js` into component files
**What:** Each component in `_ds_bundle.js` is wrapped in `// path/to/File.jsx` comment + `try { (() => { ...function body... })(); } catch (e) { ... }`. To port a component: extract the `function Name({ ...props }) { ... }` body between the comment marker and the matching `Object.assign(__ds_scope, { Name });` line, convert `React.createElement(...)` calls back to JSX (optional but recommended for readability/maintainability — the `_adherence.oxlintrc.json` rules imply the *original* authoring format was JSX, and hand-authored JSX will be easier for phases 22-25 to extend), add `export default function Name(...)`.
**When to use:** For every one of the 23 components + the `.dg-frost`/`.dg-blueprint` CSS-class primitives (already present as real CSS in `tokens/effects.css` — copy verbatim, don't re-derive) + the divergence callout (`Callout.jsx`, already in the bundle).
**Caveat:** `React.createElement` in the bundle assumes a **global `React`** (no `import React from 'react'` anywhere in the 78KB bundle) — this only worked in the design tool's own preview harness where React was loaded as a UMD global. The ported files MUST add explicit `import React from 'react'` (or rely on the new automatic JSX runtime via `@vitejs/plugin-react`, which needs no React import at all for JSX syntax — recommended, since it eliminates this whole class of bug).

### Anti-Patterns to Avoid
- **Treating `design/v2/_ds/.../components/` as if it exists on disk:** It doesn't (confirmed via `find` — only `tokens/`, `styles.css`, `readme.md`, `_ds_manifest.json`, `_ds_bundle.js` are present). Do not write a task that says "copy `components/forms/Button.jsx` to `src/components/forms/Button.jsx`" as a file-copy operation — it must be an extraction-from-bundle operation.
- **Using the unsuffixed `@fontsource/geist/index.css` or `400.css`:** These import all unicode-range subsets (5 files per weight) including cyrillic/vietnamese that this app will never render. Use `latin-400.css` etc.
- **Mixing `'Geist Variable'` (from `@fontsource-variable/geist`) with the tokens:** The token file says `--font-sans: 'Geist', ...` (no "Variable" suffix). If the variable-font package is used instead of the static one, the family name mismatches and the font silently fails to apply (falls through to the `ui-sans-serif` fallback) — a subtle, hard-to-spot bug. Stick to the static `@fontsource/geist` package, not `@fontsource-variable/geist`.
- **Rebuilding `.dg-frost`/`.dg-blueprint` from scratch:** Both already exist as real CSS classes in `tokens/effects.css` (lines 32-46) — copy the file verbatim per D-05, don't hand-roll new class definitions that might drift from the exact 78%/14px/hairline spec.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font self-hosting / subsetting | Manual woff2 download + hand-written `@font-face` for 3 families × 3 weights | `@fontsource/{geist,geist-mono,oswald}` | Maintained package already does unicode-range subsetting, `font-display` tuning, and correct `format()` fallback chains; manual approach risks getting the `font-family` string wrong (breaks token contract silently) |
| Icon SVGs | Hand-copied/inlined SVG markup per icon | `lucide-react` | Official maintained set matching the exact icon names the `.pen` files reference; consistent stroke geometry guaranteed by the library, not by hand-tracing |
| Dev-server → Docker backend routing | A custom Express/Node proxy server alongside Vite | Vite's built-in `server.proxy` | Vite already ships a proxy (based on `http-proxy`); adding a second process is unnecessary complexity for a dev-only need that retires at Phase 26 |

**Key insight:** Every "hand-roll" temptation in this phase (fonts, icons, proxying) already has an official, actively-maintained solution that exactly matches the constraint set (no CDN, no TypeScript, Vite-native). Resist introducing anything bespoke — the phase's job is disciplined adoption, not invention.

## Common Pitfalls

### Pitfall 1: Font-family name mismatch silently falls back
**What goes wrong:** Token expects `font-family: 'Geist'` but the chosen font package/CDN snippet registers a different family name (e.g. `'Geist Sans'`, `'GeistSans'`, or `'Geist Variable'`), so the browser silently falls through to the `ui-sans-serif, system-ui` fallback stack. Visually close enough that it's easy to miss in a quick glance, but fails any font-family assertion test.
**Why it happens:** Different font distribution channels (official `geist` npm, Google-Fonts-style CDN snippets, variable-font packages) use different family name conventions.
**How to avoid:** Use the static (non-variable) `@fontsource/geist` / `@fontsource/geist-mono` / `@fontsource/oswald` packages specifically — verified above to emit exactly `'Geist'` / `'Geist Mono'` / `'Oswald'`.
**Warning signs:** `document.fonts.check("14px Geist")` returns `false`, or computed style at a text node shows the fallback font's actual rendered metrics.

### Pitfall 2: `_ds_bundle.js`'s implicit global `React` doesn't survive porting
**What goes wrong:** Copy-pasting `React.createElement(...)` calls verbatim into a new file without an explicit React import (or without relying on the automatic JSX runtime) throws `ReferenceError: React is not defined` at runtime, only surfacing when that specific component first renders.
**Why it happens:** The bundle was authored for a preview harness with React as a `<script>`-tag global, which doesn't exist in a real Vite module graph.
**How to avoid:** Either (a) enable the automatic JSX runtime — `@vitejs/plugin-react` defaults to `jsx: 'automatic'`, meaning JSX syntax needs no React import at all, or (b) explicitly `import React from 'react'` in every ported file if choosing to keep `React.createElement` calls rather than converting to JSX syntax.
**Warning signs:** Component renders blank/crashes only in the real app, never in isolation if tested via a snippet that already has React in scope.

### Pitfall 3: `backdrop-filter` browser support / stacking context gotchas
**What goes wrong:** `.dg-frost`'s blur effect (`backdrop-filter: blur(14px)`) requires the element to not be inside certain CSS containment contexts, and Safari specifically needs the `-webkit-backdrop-filter` prefix (already present in `tokens/effects.css` — confirmed). If a later phase wraps a frost panel in a parent with `transform` or `filter` set, the backdrop-filter can visually "detach" from the actual background behind it (it blurs relative to its own containing block, not the whole page, in some browser implementations).
**Why it happens:** `backdrop-filter` compositing rules are stacking-context-sensitive and inconsistently implemented across engines.
**How to avoid:** Test frost panels over the actual `.dg-blueprint` canvas background (not a plain white test page) during the specimen page build, since this is the only way to visually confirm blur is compositing against the intended layer.
**Warning signs:** Frost panel looks like flat translucent white with no blur in one browser but correctly blurred in another.

### Pitfall 4: Vite proxy `rewrite` omission for routes that don't need path-stripping
**What goes wrong:** The nginx config's `/model-viewer/` and `/` locations do NOT rewrite (they're static-file serving, not proxying), but `/neo4j/`, `/data-service/`, `/n8n/` DO use `rewrite ^/x/(.*) /$1 break` to strip the prefix before forwarding upstream. Forgetting the `rewrite` function on the Vite side for these three routes means the upstream Neo4j/n8n/data-service will receive requests still carrying the `/neo4j/`/`/n8n/`/`/data-service/` prefix, which they don't recognize → 404s that look like a CORS or connectivity failure at first glance.
**Why it happens:** Vite's proxy, unlike nginx, does NOT strip the matched path prefix by default — it forwards the full incoming path unless a `rewrite` function is supplied.
**How to avoid:** Explicitly add `rewrite: (path) => path.replace(/^\/neo4j/, '')` (etc.) for each of the three backend routes, mirroring nginx's behavior exactly.
**Warning signs:** Requests reach the target host (visible in Docker logs) but return 404 for a path that should exist.

### Pitfall 5: n8n webhook timeouts under Vite's default proxy timeout
**What goes wrong:** The `/n8n/` nginx route sets 900-second read/send timeouts because LLM rule-ingestion and graph-query webhooks can run long. Vite's proxy (built on Node's `http-proxy`) has no such generous default; a long-running n8n call could be cut off by Node's default socket/keep-alive timeouts during dev.
**Why it happens:** Vite proxy config doesn't automatically inherit nginx's custom timeout values — they're two separate proxy layers with independent defaults.
**How to avoid:** This is a real risk to flag for the planner but not necessarily a blocking one for Phase 21 itself (no screens call `/n8n/` yet — that's Phase 23, GVIEW-03/04). Phase 21 should configure the proxy route to exist and forward correctly; Phase 23 should verify long-running calls don't time out and, if needed, tune `proxy.timeout`/`proxyTimeout` options in the Vite config at that point.
**Warning signs:** n8n calls that take >~2 minutes hang and eventually error with `ECONNRESET` or `socket hang up` in the browser console, but work fine when hit directly against `:8080/n8n/...` (bypassing Vite).

## Code Examples

### Vite dev-proxy config mirroring nginx.conf routes
```javascript
// Source: vite.config.js pattern per Vite official proxy docs (server.proxy),
// routes mirrored 1:1 from graph-viewer/nginx.conf (verified 2026-07-07)
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/neo4j": {
        target: "http://localhost:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/neo4j/, "/neo4j"),
        // nginx already does its own internal rewrite (^/neo4j/(.*) -> /$1) once the
        // request reaches :8080 — so from the Vite dev server's perspective we proxy
        // straight through to :8080 and let nginx do the prefix-stripping, since the
        // Docker stack's nginx is still the single source of truth for backend routing.
      },
      "/data-service": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
      "/n8n": {
        target: "http://localhost:8080",
        changeOrigin: true,
        proxyTimeout: 900000, // match nginx's 900s n8n timeout (ms) — needed once Phase 23 wires webhooks
        timeout: 900000,
      },
      "/llm": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
```
**Design note:** Because `:8080` (the existing `design-grammars` nginx container) already does the prefix-stripping rewrite internally, the simplest and lowest-risk Vite config proxies whole-cloth to `http://localhost:8080` and lets nginx keep doing what it already does — rather than duplicating nginx's `rewrite` logic in Vite and pointing directly at `neo4j:7474`/`n8n:5678`/etc. (which aren't even resolvable by hostname outside the Docker network from the host machine running Vite). This is simpler than the generic "strip prefix, point at raw service port" pattern that would be used if there were no existing nginx layer — **verify the exact backend port/hostname reachability from the host machine before finalizing**; if `neo4j:7474` etc. are only resolvable inside the Docker network (typical), proxying through `:8080` is the *only* correct approach, not just the simpler one.

### Specimen route dev-only exclusion
```javascript
// Source: Vite official docs pattern — import.meta.env.DEV
// src/App.jsx
import Specimen from './routes/Specimen';

function App() {
  const isSpecimenPath = window.location.pathname === '/specimen';
  if (import.meta.env.DEV && isSpecimenPath) {
    return <Specimen />;
  }
  return <MainApp />;
}
```
`import.meta.env.DEV` is statically replaced by Vite at build time (`false` in production builds), so Rollup's dead-code elimination drops the `<Specimen />` branch and its entire import graph from the production bundle — no manual route-guarding needed, no risk of `/specimen` shipping to `:8080` after Phase 26 cutover.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Google Fonts `@import url(...)` CDN | Self-hosted `@font-face` via `@fontsource/*` npm packages | This phase (D-06) | Removes a render-blocking third-party network request; fits the fully self-hosted Docker ethos; no external runtime dependency |
| Legacy dark UI: no JSX build, single-file `index.html` + `React.createElement` | Vite + React (JSX) app | This phase (D-01) | Enables the component-composition workflow the design system recipes assume; matches `model-viewer`'s existing precedent |

**Deprecated/outdated:**
- Google Fonts CDN `@import` in `tokens/fonts.css`: superseded by local font-face per D-06; the readme's own "Caveats" section already flags this as needing replacement ("Fonts: Geist/Geist Mono load from Google Fonts (no binaries shipped)... supply licensed binaries").

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Proxying to `localhost:8080` (the existing nginx) rather than directly to `neo4j:7474`/`n8n:5678`/`data-service:8000` is the correct Vite proxy target | Code Examples — Vite dev-proxy | If the Docker services *are* individually port-mapped to the host (not just internal Docker-network hostnames), a direct-to-service proxy might be marginally simpler/faster; planner should confirm actual `docker-compose.yml` port mappings before finalizing (not read in this research pass — `docker-compose.yml` was in scope per CLAUDE.md's service map but not re-verified against live port bindings in this session) |
| A2 | `font-display: swap` (the fontsource default) is acceptable and doesn't need to be overridden to `optional` or `fallback` | Pattern 1 — font self-hosting | If FOUT (flash of unstyled text) during the brief woff2 load is judged unacceptable for the "clinical" aesthetic, planner/executor may want `font-display: optional` instead — this is a one-line CSS override, low risk either way, flagged for awareness not because it's likely wrong |
| A3 | De-bundling `_ds_bundle.js` by hand-converting each component back to JSX is preferable to keeping `React.createElement` calls as-is | Pattern 3 — recipe porting | If the planner instead chooses to keep the transpiled `React.createElement` form (just adding imports/exports), that's also valid and slightly less work — this is a stylistic recommendation, not a hard requirement, since either form is 100% functionally equivalent |

**None of these assumptions block planning** — they're implementation-detail judgment calls the planner/executor can resolve during Wave 0, not open unknowns requiring user confirmation before the phase can start.

## Open Questions

1. **Exact Docker port-mapping for Neo4j/n8n/data-service reachability from the Vite dev server's host process**
   - What we know: `nginx.conf` proxies to `http://neo4j:7474`, `http://n8n:5678`, `http://data-service:8000` — these are Docker-network-internal hostnames, only resolvable from inside the Docker network (i.e., from within another container, not from the bare host machine running `npm run dev`).
   - What's unclear: Whether `docker-compose.yml` additionally exposes these ports to the host (e.g. `ports: ["7474:7474"]`), which would allow a Vite proxy targeting `http://localhost:7474` directly, bypassing the `:8080` nginx hop entirely.
   - Recommendation: Default to proxying through `http://localhost:8080` (confirmed reachable — that's how the legacy UI and `model-viewer` already work) unless the planner confirms individual host port mappings exist and offers a compelling reason to bypass nginx (there usually isn't one — going through `:8080` also means dev and prod hit an identical proxy path shape).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | Vite dev server, all tooling | ✓ (assumed present — `model-viewer/package.json` already requires it and is an existing working app in this repo) | not re-verified this session | — |
| Docker stack running (`docker compose up -d`) | Vite proxy targets (`:8080` → neo4j/n8n/data-service) | Not verified this session (must be running when dev server starts) | — | none — phase's UI screens are static/token-only in Phase 21 itself; live backend reachability only becomes load-bearing starting Phase 22 (auth) / 23 (graph viewer webhooks) |
| `@fontsource/*` packages | Font self-hosting | ✓ confirmed installable, versions verified via `npm view` | 5.2.9 / 5.2.8 / 5.2.8 | — |
| `lucide-react` | Icon rendering | ✓ confirmed installable | 1.23.0 | Inline SVGs (see Alternatives Considered) |

**Missing dependencies with no fallback:** none identified — this phase has no hard blockers.
**Missing dependencies with fallback:** none required for Phase 21 itself (Docker stack reachability matters starting Phase 22+).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (match `graph-viewer/model-viewer`'s existing `^2.1.8` precedent) |
| Config file | none yet — new app's `vite.config.js` needs a `test` block added (Wave 0) |
| Quick run command | `npx vitest run src/components/**/*.test.jsx` |
| Full suite command | `npx vitest run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| DSYS-01 | Achromatic surfaces + Signal Red only for selection/failure/destructive | unit (computed-style) | `vitest run src/styles/tokens.test.js` — assert `getComputedStyle` background-color of canvas/sidebar/card matches `#f5f5f5`/`#fafafa`/`#ffffff`; grep-based static test scanning rendered component source/output for any hardcoded hex outside the token file | ❌ Wave 0 |
| DSYS-02 | Geist/Geist Mono/Oswald load and apply in spec roles | unit (font resolution) | `vitest run src/styles/fonts.test.js` — `document.fonts.ready` then `document.fonts.check("14px Geist")` / `"12px Geist Mono"` / `"13px Oswald"` all `true` in jsdom-with-font-loading-shim or a headless-browser test (jsdom's `document.fonts` support is limited — consider a lightweight Playwright/Puppeteer smoke test instead if jsdom proves insufficient) | ❌ Wave 0 |
| DSYS-03 | Button/Input pill radii (18/24px), `.dg-frost` (78% white + 14px blur + hairline), `.dg-blueprint` grid, divergence callout render per recipe | unit (computed-style) | `vitest run src/components/**/*.test.jsx` — render each primitive via `@testing-library/react`, assert `getComputedStyle(el).borderRadius === '18px'` (buttons/inputs) / `'24px'` (cards), `backdropFilter` contains `blur(14px)`, `backgroundColor` resolves to `rgba(255, 255, 255, 0.78)` for frost panels | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run <changed-component>.test.jsx`
- **Per wave merge:** `npx vitest run` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`; additionally, manually open the `/specimen` route in a real browser (jsdom cannot reliably verify `backdrop-filter` visual compositing — see Pitfall 3) to confirm frost blur actually renders, since this is a case where automated computed-style assertions can pass (the CSS property is set correctly) while the visual effect is subtly wrong for engine-specific reasons.

### Wave 0 Gaps
- [ ] `vite.config.js` `test` block (environment: jsdom or happy-dom, since computed-style/font-resolution assertions need a DOM, unlike `model-viewer`'s current `environment: "node"`)
- [ ] `src/styles/tokens.test.js` — surface color assertions covering DSYS-01
- [ ] `src/styles/fonts.test.js` — font-family resolution covering DSYS-02 (flag: jsdom's `document.fonts` API support is incomplete in some jsdom versions — verify during Wave 0 whether a real headless-browser check via Playwright is needed instead; don't assume jsdom alone suffices without a quick spike)
- [ ] `src/components/*.test.jsx` — per-primitive computed-style assertions covering DSYS-03
- [ ] `@testing-library/react` + `happy-dom`/`jsdom` install (not yet a dependency anywhere in the repo)

## Security Domain

Not applicable in the traditional ASVS sense — this phase ships no authentication, no data input handling, and no new backend surface (pure static tokens/fonts/presentational components + a dev-only specimen route). The one item worth a one-line note:

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dev-only `/specimen` route accidentally shipping to production | Information Disclosure (low severity — no secrets, just internal component catalog) | `import.meta.env.DEV` guard (see Code Examples) ensures Rollup dead-code-eliminates the route entirely from the production bundle — not just hides it behind a runtime check |

## Sources

### Primary (HIGH confidence)
- Local repo files read directly: `21-CONTEXT.md`, `REQUIREMENTS.md`, `readme.md`, `_ds_manifest.json`, `_ds_bundle.js`, `tokens/{fonts,effects,base}.css`, `styles.css`, `_adherence.oxlintrc.json`, `graph-viewer/model-viewer/{vite.config.js,package.json,src/main.jsx}`, `graph-viewer/nginx.conf`
- `npm view` registry checks (2026-07-07): `@fontsource/geist`, `@fontsource/geist-mono`, `@fontsource/oswald`, `lucide-react`, `vite`, `@vitejs/plugin-react`, `geist`
- Local `npm install` + direct inspection of generated CSS (`node_modules/@fontsource/{geist,geist-mono,oswald}/latin-400.css`) — ground truth for `font-family` name and `font-display` value, not inferred from docs

### Secondary (MEDIUM confidence)
- [fontsource.org/fonts/geist/install](https://fontsource.org/fonts/geist/install) — Vite import pattern (cross-checked against the actually-installed package CSS, which matched)
- [github.com/vitejs/vite discussions #12137](https://github.com/vitejs/vite/discussions/12137) — `server.proxy` multi-route + `rewrite` pattern

### Tertiary (LOW confidence)
- WebSearch summaries for @fontsource ecosystem context (npmjs.com/@fontsource/oswald, dev.to articles) — used only for orientation, not as the basis of any specific claim in this document; all load-bearing claims (family names, font-display) were re-verified against the actually-installed package.

## Metadata

**Confidence breakdown:**
- Standard stack (fonts/icons/proxy): HIGH — every package verified via `npm view` + local install + direct CSS inspection, not training-data guesses
- Architecture (project structure, de-bundling approach): HIGH — `_ds_bundle.js` and manifest read directly; component prop shapes cross-verified against `_adherence.oxlintrc.json`'s per-component prop whitelist
- Pitfalls: MEDIUM-HIGH — font-family mismatch and global-React pitfalls are directly observed facts from this session; backdrop-filter and n8n-timeout pitfalls are well-known browser/proxy behaviors but not re-tested live in this session

**Research date:** 2026-07-07
**Valid until:** ~30 days for the architecture/porting-mechanics findings (stable); ~90 days for package versions (recheck `npm view` before executing if this research goes stale)
