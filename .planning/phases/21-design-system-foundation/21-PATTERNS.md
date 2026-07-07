# Phase 21: Design System Foundation - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** ~40 (scaffold: 5, tokens: 7, components: 23, specimen: 1, tests: ~5+)
**Analogs found:** 12 / ~40 (scaffold + tokens have strong analogs; components are greenfield-from-bundle)

## Context Correction (from RESEARCH.md)

`design/v2/_ds/.../components/` does **NOT exist on disk** — confirmed via `Glob` in this pass (only `tokens/`, `styles.css`, `readme.md`, `_ds_manifest.json`, `_ds_bundle.js` exist). Every "port `components/forms/Button.jsx`" task is actually an **extraction-from-`_ds_bundle.js`** operation, not a file copy. `_ds_bundle.js` wraps each component as:

```js
// components/forms/Button.jsx
try { (() => {
  function Button({ ... }) { ... return React.createElement(...); }
  Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "...", error: ... }); }
```

Extraction recipe: find the `// <sourcePath>` comment marker (`_ds_manifest.json`'s `components[].sourcePath` gives the exact list), read from there to the matching `})(); } catch (e) ...` line, strip the `try`/IIFE/`Object.assign(__ds_scope, ...)` wrapper, keep the inner `function Name({ props }) { ... }`, convert `React.createElement` calls to JSX (recommended, optional), add `export default function Name(...)`. No `import React` needed if using `@vitejs/plugin-react`'s automatic JSX runtime.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `<app>/package.json` | config | build | `graph-viewer/model-viewer/package.json` | exact |
| `<app>/vite.config.js` | config | build/proxy | `graph-viewer/model-viewer/vite.config.js` | role-match (needs new proxy block + test env change) |
| `<app>/index.html` | config | static entry | `graph-viewer/model-viewer/index.html` | exact |
| `<app>/src/main.jsx` | provider | mount/bootstrap | `graph-viewer/model-viewer/src/main.jsx` | exact (ErrorBoundary pattern reusable) |
| `<app>/src/App.jsx` | component | request-response (dev-only, mostly static in Ph.21) | `graph-viewer/model-viewer/src/App.jsx` | partial (structure/state-hook conventions only; App.jsx there is data-heavy, this one is presentational) |
| `<app>/src/styles/styles.css` | config | static import graph | `_ds/styles.css` | exact (copy verbatim) |
| `<app>/src/styles/tokens/fonts.css` | config | static | `_ds/tokens/fonts.css` | exact analog, **content REWRITTEN** (Google Fonts `@import` → `@fontsource` imports) |
| `<app>/src/styles/tokens/colors.css` | config | static | `_ds/tokens/colors.css` | exact (copy verbatim) |
| `<app>/src/styles/tokens/typography.css` | config | static | `_ds/tokens/typography.css` | exact (copy verbatim) |
| `<app>/src/styles/tokens/spacing.css` | config | static | `_ds/tokens/spacing.css` | exact (copy verbatim) |
| `<app>/src/styles/tokens/effects.css` | config | static | `_ds/tokens/effects.css` | exact (copy verbatim — `.dg-frost`/`.dg-blueprint` already here) |
| `<app>/src/styles/tokens/base.css` | config | static | `_ds/tokens/base.css` | exact (copy verbatim) |
| `<app>/src/components/forms/Button.jsx` | component | presentational | `_ds_bundle.js` lines 427-495 (`components/forms/Button.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/forms/Checkbox.jsx` | component | presentational | `_ds_bundle.js` (`components/forms/Checkbox.jsx` block, locate via grep) | greenfield-from-bundle |
| `<app>/src/components/forms/Input.jsx` | component | presentational | `_ds_bundle.js` (`components/forms/Input.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/forms/SearchField.jsx` | component | presentational | `_ds_bundle.js` (`components/forms/SearchField.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/forms/Select.jsx` | component | presentational | `_ds_bundle.js` (`components/forms/Select.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/forms/Slider.jsx` | component | presentational | `_ds_bundle.js` (`components/forms/Slider.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/forms/Textarea.jsx` | component | presentational | `_ds_bundle.js` (`components/forms/Textarea.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/Avatar.jsx` | component | presentational | `_ds_bundle.js` (`components/display/Avatar.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/Badge.jsx` | component | presentational | `_ds_bundle.js` (`components/display/Badge.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/Callout.jsx` | component | presentational | `_ds_bundle.js` lines 83-155 (`components/display/Callout.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/Chip.jsx` | component | presentational | `_ds_bundle.js` (`components/display/Chip.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/CodeBlock.jsx` | component | presentational | `_ds_bundle.js` (`components/display/CodeBlock.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/KVRow.jsx` | component | presentational | `_ds_bundle.js` (`components/display/KVRow.jsx` block; also source for `StatBlock`) | greenfield-from-bundle |
| `<app>/src/components/display/StatBlock.jsx` | component | presentational | `_ds_bundle.js` — manifest maps `StatBlock`'s `sourcePath` to the SAME file as KVRow (`components/display/KVRow.jsx`) — both functions live in one bundle block | greenfield-from-bundle (shared source block) |
| `<app>/src/components/display/Progress.jsx` | component | presentational | `_ds_bundle.js` (`components/display/Progress.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/display/PropertiesTable.jsx` | component | presentational | `_ds_bundle.js` (`components/display/PropertiesTable.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/surfaces/Collapsible.jsx` | component | presentational | `_ds_bundle.js` (`components/surfaces/Collapsible.jsx` block; also source for `CollapsibleItem`) | greenfield-from-bundle |
| `<app>/src/components/surfaces/CollapsibleItem.jsx` | component | presentational | same bundle block as `Collapsible` | greenfield-from-bundle (shared source block) |
| `<app>/src/components/surfaces/Dialog.jsx` | component | presentational | `_ds_bundle.js` (`components/surfaces/Dialog.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/surfaces/Panel.jsx` | component | presentational | `_ds_bundle.js` (`components/surfaces/Panel.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/surfaces/RunTile.jsx` | component | presentational | `_ds_bundle.js` (`components/surfaces/RunTile.jsx` block); also see `ValidationRunsStrip.jsx`'s `.mv-tile` markup for a live in-repo "run tile" concept (structurally similar but dark-theme/different CSS — style reference only, not a code source) | greenfield-from-bundle |
| `<app>/src/components/surfaces/Tabs.jsx` | component | presentational | `_ds_bundle.js` (`components/surfaces/Tabs.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/surfaces/Tile.jsx` | component | presentational | `_ds_bundle.js` (`components/surfaces/Tile.jsx` block) | greenfield-from-bundle |
| `<app>/src/components/index.js` | utility | barrel export | none in-repo (model-viewer has no barrel file) | greenfield — new pattern per D-04/oxlint expectation |
| `<app>/src/routes/Specimen.jsx` | component | presentational (dev-only route) | `_ds_manifest.json`'s `cards[]` (guideline-card grouping: Colors/Type/Foundations/Components) as the ORGANIZATION reference; no in-repo JSX analog | greenfield |
| `<app>/src/styles/tokens.test.js` | test | unit/computed-style | `graph-viewer/model-viewer/src/useValidationRunsGrouping.test.js` (only existing Vitest file in repo — for `describe`/`it` conventions, not content) | role-match (style/assertion pattern is new — jsdom computed-style, model-viewer's test is pure-function logic) |
| `<app>/src/styles/fonts.test.js` | test | unit/font-resolution | none (new territory — `document.fonts.check` has no in-repo precedent) | no analog |
| `<app>/src/components/**/*.test.jsx` | test | unit/computed-style + RTL render | none (`@testing-library/react` not yet used anywhere in repo) | no analog |

## Pattern Assignments

### `<app>/package.json` (config, build)

**Analog:** `graph-viewer/model-viewer/package.json` (full file, 22 lines — read verbatim above)

Copy structure, bump versions per RESEARCH.md's Standard Stack table, and add the new dependencies:
```json
{
  "name": "dg-<new-app-name>",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@fontsource/geist": "^5.2.9",
    "@fontsource/geist-mono": "^5.2.8",
    "@fontsource/oswald": "^5.2.8",
    "lucide-react": "^1.23.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^6.0.3",
    "vite": "^8.1.3",
    "vitest": "^2.1.8",
    "happy-dom": "latest",
    "@testing-library/react": "^14.x"
  }
}
```
Note: model-viewer's `package.json` has NO `"dev"` script (it's build-only, served via nginx) — Phase 21 needs `vite` (dev server) added since D-11 mandates running via Vite dev server only.

### `<app>/vite.config.js` (config, build/proxy)

**Analog:** `graph-viewer/model-viewer/vite.config.js` (full file, 15 lines — read verbatim above)

**Base pattern to copy:**
```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  },
  test: {
    environment: "node",   // model-viewer uses "node" — Phase 21 MUST change to "jsdom"/"happy-dom"
    include: ["src/**/*.test.js", "src/**/*.test.jsx"]
  }
});
```
**Deltas required for the new app:**
- Remove `base: "/model-viewer/"` (not a subpath-mounted app in dev; D-11 says Vite dev server only, no compose changes yet)
- Change `test.environment` from `"node"` to `"jsdom"` or `"happy-dom"` — computed-style/font assertions need a DOM (model-viewer's tests are pure-logic, hence `"node"` there)
- Add `server.proxy` block — see Shared Patterns → Dev Proxy below (RESEARCH.md's Code Examples section has the full config, cross-verified against `nginx.conf`)

### `<app>/index.html` (config, static entry)

**Analog:** `graph-viewer/model-viewer/index.html` (full file, 14 lines — read verbatim above)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Design Grammars</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```
Note: model-viewer's `<head>` loads `<script src="/config.js"></script>` (runtime env-var injection via `entrypoint.sh` sed substitution) — **not needed in Phase 21** since D-11 defers Docker/compose wiring to Phase 26; drop that script tag for now.

### `<app>/src/main.jsx` (provider, mount/bootstrap)

**Analog:** `graph-viewer/model-viewer/src/main.jsx` (full file, 46 lines — read verbatim above)

The `ErrorBoundary` class + `window.addEventListener("error"...)` / `unhandledrejection` global handlers are a solid, reusable pattern — copy near-verbatim, just retarget style props to light-theme tokens (the analog's error screen uses dark hardcoded colors `#0c1018`/`#ffb0b1`; new app should use `var(--color-canvas)`/`var(--color-signal)` etc. once tokens are loaded):
```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "@fontsource/geist/latin-400.css";
import "@fontsource/geist/latin-500.css";
import "@fontsource/geist/latin-600.css";
import "@fontsource/geist-mono/latin-400.css";
import "@fontsource/geist-mono/latin-500.css";
import "@fontsource/oswald/latin-400.css";
import "@fontsource/oswald/latin-500.css";
import "@fontsource/oswald/latin-600.css";
import "./styles/styles.css";

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error("[DG-ErrorBoundary]", error, info?.componentStack); }
  render() {
    if (this.state.error) { /* light-theme error screen */ }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary><App /></ErrorBoundary>
  </React.StrictMode>
);
```

### `<app>/src/App.jsx` (component, presentational shell)

**Analog:** `graph-viewer/model-viewer/src/App.jsx` (partial match — only the outer structural conventions apply)

Model-viewer's `App.jsx` is heavily data-fetching (Speckle viewer init, `fetchJson`, validation-run state) — **not a content match** for Phase 21's App.jsx, which should just be a thin router shell:
```jsx
import Specimen from './routes/Specimen';

function App() {
  const isSpecimenPath = window.location.pathname === '/specimen';
  if (import.meta.env.DEV && isSpecimenPath) {
    return <Specimen />;
  }
  return <div className="dg-blueprint" style={{ minHeight: '100vh' }}>{/* placeholder shell — screens land in Phases 22-25 */}</div>;
}
export default App;
```
Reuse only: JSX conventions (`React.useState`/`useCallback` hook style — consistent throughout `App.jsx` if any local state is needed later), and the `className`-driven styling approach (no CSS-in-JS library, no styled-components — plain `className` + CSS custom properties, matching `ValidationRunsStrip.jsx`'s `mv-*` BEM-ish class naming convention, which the new app's components should mirror with a `dg-*` prefix).

### Token CSS files (config, static import graph)

**Analog:** `design/v2/_ds/.../tokens/{colors,typography,spacing,effects,base}.css` + `styles.css` — copy verbatim (D-05), only `fonts.css` is rewritten.

**`styles.css` entry** (copy exactly, only the relative import base path changes — already relative, no edit needed):
```css
@import url('tokens/fonts.css');
@import url('tokens/colors.css');
@import url('tokens/typography.css');
@import url('tokens/spacing.css');
@import url('tokens/effects.css');
@import url('tokens/base.css');
```

**`tokens/fonts.css`** — REWRITE per D-06 (source original for context, then replacement):
```css
/* ORIGINAL — design/v2/_ds/.../tokens/fonts.css (7 lines) */
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&family=Oswald:wght@400;500;600&display=swap');
```
```css
/* REPLACEMENT — src/styles/tokens/fonts.css */
@import '@fontsource/geist/latin-400.css';
@import '@fontsource/geist/latin-500.css';
@import '@fontsource/geist/latin-600.css';
@import '@fontsource/geist-mono/latin-400.css';
@import '@fontsource/geist-mono/latin-500.css';
@import '@fontsource/oswald/latin-400.css';
@import '@fontsource/oswald/latin-500.css';
@import '@fontsource/oswald/latin-600.css';
```

**`tokens/effects.css`** (copy verbatim — full file, 47 lines, already read above) — contains `.dg-frost`/`.dg-blueprint` (do not hand-roll), radii tokens (`--radius-buttons: 18px`, `--radius-cards: 24px`, etc.), and motion tokens (`--ease-out`, `--duration-fast/base`).

`colors.css`, `typography.css`, `spacing.css`, `base.css` — not yet read in this pass (not needed: D-05 says copy verbatim, no edits, so no pattern extraction is meaningful beyond "copy the file"). Token names for planner cross-reference are fully enumerated in `_ds_manifest.json`'s `tokens[]` array (already captured above) — e.g. `--color-canvas: #f5f5f5`, `--font-sans: 'Geist', ...`, `--text-body: 14px`, `--spacing-4: 4px` through `--spacing-48: 48px`, `--sidebar-width: 394px`.

### Component recipes (component, presentational) — greenfield-from-bundle

**No in-repo JSX component-library analog exists.** Source is `_ds_bundle.js` (2632 lines total), extraction mechanics demonstrated on two components read in full:

**`Button.jsx`** (bundle lines 427-495) — variant/size prop-driven inline-style pattern:
```jsx
function Button({ variant = 'primary', size = 'md', selected = false, disabled = false, children, style, ...rest }) {
  const heights = { sm: 28, md: 36, lg: 40 };
  const h = heights[size] || 36;
  const variants = {
    primary: { background: 'var(--color-ink)', color: 'var(--text-inverse)', border: '1px solid transparent' },
    secondary: { background: 'var(--color-canvas)', color: 'var(--color-ink)', border: '1px solid transparent' },
    outline: { background: 'transparent', color: 'var(--color-ink)', border: '1px solid var(--color-hairline)' },
    destructive: { background: 'transparent', color: 'var(--color-signal-ink)', border: '1px solid var(--color-signal-mid)' }
  };
  const v = variants[variant] || variants.primary;
  const sel = selected ? { boxShadow: 'var(--focus-ring-selected)', background: 'var(--accent-selection-bg)', color: 'var(--color-signal-ink)', border: '1px solid transparent' } : null;
  return (
    <button disabled={disabled} style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
      height: h, padding: size === 'sm' ? '0 12px' : '0 16px',
      borderRadius: 'var(--radius-buttons)',
      font: `500 ${size === 'sm' ? 13 : 14}px/1 var(--font-sans)`,
      cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.45 : 1,
      transition: 'background var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out)',
      ...v, ...sel, ...style
    }} {...rest}>{children}</button>
  );
}
export default Button;
```
**Note the token dependency chain:** this component references `--color-ink`, `--text-inverse`, `--color-canvas`, `--color-hairline`, `--color-signal-ink`, `--color-signal-mid`, `--focus-ring-selected`, `--accent-selection-bg`, `--radius-buttons`, `--font-sans`, `--duration-fast`, `--ease-out` — all must resolve from the token CSS files, so token files must load before any component renders.

**`Callout.jsx`** (bundle lines 83-155) — the "divergence callout" signature pattern (hexagon marker via inline SVG `<polygon>`, hairline leader via `borderLeft`, Oswald condensed caption via `var(--font-annotation)`):
```jsx
function Callout({ date, title, subtitle, detail, signal = false, marker = false, style }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'flex-start', gap: 14, ...style }}>
      {marker && (
        <svg width="34" height="34" viewBox="0 0 34 34" style={{ flex: 'none', marginTop: 2 }}>
          <polygon points="17,3 29,10 29,24 17,31 5,24 5,10" fill="none"
            stroke={signal ? 'var(--color-signal)' : 'var(--ink-a32)'} strokeWidth="1" />
          <circle cx="17" cy="17" r="2.5" fill={signal ? 'var(--color-signal)' : 'var(--color-ink)'} />
        </svg>
      )}
      <div style={{ borderLeft: `1px solid ${signal ? 'var(--color-signal)' : 'var(--ink-a32)'}`, paddingLeft: 12, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {date && <span style={{ font: '400 12px/1.4 var(--font-annotation)', letterSpacing: '1.2px', color: 'var(--text-muted)' }}>{date}</span>}
        <span style={{ font: '500 18px/1.2 var(--font-annotation)', letterSpacing: 'var(--tracking-annotation-lg)', textTransform: 'uppercase', color: 'var(--color-ink)' }}>
          {title}{subtitle && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> : {subtitle}</span>}
        </span>
        {detail && <span style={{ font: '400 12px/1.5 var(--font-annotation)', letterSpacing: '1.4px', textTransform: 'uppercase', color: signal ? 'var(--color-signal-ink)' : 'var(--color-ink-soft)' }}>{detail}</span>}
      </div>
    </div>
  );
}
export default Callout;
```

**Extraction procedure for the remaining 21 components** (Avatar, Badge, Chip, CodeBlock, KVRow, StatBlock, Progress, PropertiesTable, Checkbox, Input, SearchField, Select, Slider, Textarea, Collapsible, CollapsibleItem, Dialog, Panel, RunTile, Tabs, Tile):
1. `grep -n "// <sourcePath>" _ds_bundle.js` to find the start line (exact `sourcePath` strings are in `_ds_manifest.json`'s `components[]` array, already enumerated in File Classification above).
2. Read from that line to the matching `})(); } catch (e) ...` line for that same `path:` value (each block is self-contained, non-overlapping — same shape as the two blocks read above).
3. Strip `try { (() => {` / `Object.assign(__ds_scope, { Name });\n})(); } catch...` wrapper; keep the inner `function Name(...) { ... }`.
4. Convert `React.createElement(tag, props, ...children)` → JSX (recommended per RESEARCH.md Pattern 3) or leave as-is (also valid, less work).
5. Add `export default function Name(...)`.
6. **Special case — `KVRow`/`StatBlock` and `Collapsible`/`CollapsibleItem` share one bundle block each** (manifest shows identical `sourcePath` for the pair) — extract both functions from the single matched block, write into two separate files (`KVRow.jsx` + `StatBlock.jsx`, `Collapsible.jsx` + `CollapsibleItem.jsx`) per the target `src/components/**` structure, OR keep them co-located in one file if the planner prefers (functionally equivalent either way — this is a file-organization choice, not a correctness issue).

### `<app>/src/components/index.js` (utility, barrel export) — greenfield

No in-repo barrel-export precedent exists (model-viewer imports each file directly: `import ValidationRunsStrip from "./ValidationRunsStrip.jsx"`). D-04 / the `_adherence.oxlintrc.json` rule (referenced in RESEARCH.md, not directly read this pass) expects imports from a single barrel:
```js
// src/components/index.js
export { default as Button } from './forms/Button';
export { default as Checkbox } from './forms/Checkbox';
// ... one line per component, forms/ then display/ then surfaces/, matching _ds_manifest.json's components[] order
export { default as Tile } from './surfaces/Tile';
```

### `<app>/src/routes/Specimen.jsx` (component, dev-only route) — greenfield

No in-repo analog. Visual/organizational reference is `_ds_manifest.json`'s `cards[]` array — group by `group` field: `Brand`, `Colors`, `Components`, `Foundations`, `Type`, plus the `startingPoints[]` entries (`Callout`, `Button`) as featured/lead examples. Gate via `import.meta.env.DEV` (RESEARCH.md's Code Examples section has the full pattern — Rollup dead-code-eliminates the whole import graph in production).

## Shared Patterns

### Dev-server → Docker backend proxy
**Source:** `graph-viewer/nginx.conf` (full file, 57 lines — read verbatim above)
**Apply to:** `<app>/vite.config.js`'s `server.proxy` block

nginx's exact route/rewrite shape that the Vite proxy must mirror:
```nginx
location /neo4j/ {
  set $neo4j_upstream http://neo4j:7474;
  rewrite ^/neo4j/(.*) /$1 break;
  proxy_pass $neo4j_upstream;
}
location /data-service/ {
  set $ds_upstream http://data-service:8000;
  rewrite ^/data-service/(.*) /$1 break;
  proxy_pass $ds_upstream;
}
location /n8n/ {
  set $n8n_upstream http://n8n:5678;
  rewrite ^/n8n/(.*) /$1 break;
  proxy_pass $n8n_upstream;
  proxy_read_timeout 900s; proxy_send_timeout 900s; proxy_connect_timeout 60s; send_timeout 900s;
}
location /llm/ {
  set $ds_upstream http://data-service:8000;
  proxy_pass $ds_upstream;  # NOTE: /llm/ does NOT rewrite/strip prefix — data-service must handle /llm/ paths directly
}
```
Per RESEARCH.md's recommendation (validated by nginx already terminating all four routes at `:8080`, which is the only host-reachable entrypoint — `neo4j`/`n8n`/`data-service` hostnames are Docker-internal only), the Vite proxy should point whole-cloth at `http://localhost:8080` and let nginx keep doing the prefix-stripping, rather than duplicating the rewrite logic in Vite:
```javascript
server: {
  proxy: {
    "/neo4j": { target: "http://localhost:8080", changeOrigin: true },
    "/data-service": { target: "http://localhost:8080", changeOrigin: true },
    "/n8n": { target: "http://localhost:8080", changeOrigin: true, proxyTimeout: 900000, timeout: 900000 },
    "/llm": { target: "http://localhost:8080", changeOrigin: true },
  }
}
```

### Token-driven styling (no CSS-in-JS)
**Source:** `_ds_bundle.js` component blocks (Button, Callout, all others) + `tokens/effects.css`
**Apply to:** All component files under `src/components/**`

Every component uses inline `style={{ ... }}` objects referencing `var(--token-name)` — never hardcoded hex/px values for anything token-covered (color, radius, spacing, font). This is the DSYS-01 achromatic-discipline enforcement mechanism: Signal Red (`--color-signal` / `#e7000b`) must only appear via `selected`/`signal`/`destructive` prop branches, never as a default/neutral state.

### Global React import / JSX runtime
**Source:** `graph-viewer/model-viewer/src/main.jsx` (uses explicit `import React from "react"`) vs. bundle's implicit global `React`
**Apply to:** All ported component files

The bundle's `React.createElement` calls assume a global `React` (design-tool preview harness artifact) that does not exist in a real Vite module graph. Since `@vitejs/plugin-react` defaults to the automatic JSX runtime, converting to JSX syntax (recommended) means **no React import needed at all**. If keeping `React.createElement` form instead, an explicit `import React from 'react'` is mandatory per component file (`model-viewer/src/main.jsx` already demonstrates this explicit-import style for the one file in-repo that still uses `React.createElement` directly, in its `ErrorBoundary.render()` fallback).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `<app>/src/components/index.js` | utility | barrel export | No barrel-export file exists anywhere in the repo; model-viewer imports each component by direct relative path |
| `<app>/src/routes/Specimen.jsx` | component | presentational | Dev-only guideline/showcase page has no precedent; use `_ds_manifest.json`'s `cards[]` grouping as the organizational reference instead of a code analog |
| `<app>/src/styles/fonts.test.js` | test | unit/font-resolution | `document.fonts.check(...)` assertions have zero precedent in the repo's one existing test file (`useValidationRunsGrouping.test.js`, which is pure-function logic, not DOM/font assertions) |
| `<app>/src/components/**/*.test.jsx` | test | unit/computed-style | `@testing-library/react` is not yet a dependency anywhere in the repo; no RTL-based component test exists to pattern-match against |
| All 21 remaining `_ds_bundle.js`-sourced components (Avatar, Badge, Chip, CodeBlock, KVRow, StatBlock, Progress, PropertiesTable, Checkbox, Input, SearchField, Select, Slider, Textarea, Collapsible, CollapsibleItem, Dialog, Panel, RunTile, Tabs, Tile) | component | presentational | Not individually re-read in this pass (Button + Callout were read in full as representative extraction samples); all follow the identical bundle-block extraction mechanic demonstrated above — no separate analog needed, just repeat the procedure per `_ds_manifest.json`'s `sourcePath` list |

## Metadata

**Analog search scope:** `graph-viewer/model-viewer/` (full src + config), `graph-viewer/nginx.conf`, `design/v2/_ds/design-grammars-v2-design-system-8522e352-87a8-4e0c-a54d-bcb6fb25e4f9/` (tokens, manifest, bundle — targeted reads of Button/Callout blocks as representative samples)
**Files scanned:** ~12 fully read, `_ds_bundle.js` grepped for all 23 component markers (2632-line file, not read in full — targeted extraction per RESEARCH.md's guidance)
**Pattern extraction date:** 2026-07-07
