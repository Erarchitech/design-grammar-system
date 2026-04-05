---
tags: [decision, architecture, ui, react]
date: 2026-04-05
---

# Single-File React SPA Avoids Build Tooling for Main UI

## Decision

The main Design Grammars UI (`graph-viewer/index.html`) is a single HTML file with inline CSS and JS using `React.createElement` directly — no JSX, no Webpack, no Vite, no npm.

## Rationale

- **Zero build step** — edit HTML, rebuild Docker container, done
- **No node_modules for main UI** — reduces container size and complexity
- **CDN-loaded React 18** — always latest patch, no version lock file
- **Rapid prototyping** — no toolchain friction for UI experiments

## Trade-offs

- **No JSX** — all components use `React.createElement(tag, props, ...children)` which is verbose
- **No tree shaking** — entire React loaded from CDN
- **Single large file** — `index.html` contains all components (1500+ lines); harder to navigate
- **No TypeScript** — no compile-time type checking for UI code
- **No hot reload** — requires Docker rebuild + hard refresh

## Contrast with Model Viewer

The Model Viewer (`graph-viewer/model-viewer/`) uses Vite + JSX because it depends on `@speckle/viewer` which requires npm packaging. It's built in Docker stage 1 and served as static files.

## Related

- [[UI is a single-file React 18 SPA with no build step]]
- [[Docker layer caching can serve stale index.html]]
- [[Config injection via entrypoint.sh sed replacement]]
