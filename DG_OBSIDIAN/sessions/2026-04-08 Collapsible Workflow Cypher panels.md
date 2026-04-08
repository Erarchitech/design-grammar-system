---
tags: [session]
date: 2026-04-08
---

# Session: 2026-04-08 — Collapsible Workflow Cypher panels

## Goal

Make the "Workflow Cypher" textarea sections collapsible in all tabs (Design Rules and Specs & Notes / Knowledge).

## What Was Done

- Added `.workflow-cypher-header` and `.workflow-cypher-chevron` CSS classes (matching Session History visual pattern)
- Added two new state variables: `workflowCypherOpen` (Design Rules tab) and `knowledgeCypherOpen` (Knowledge tab), both default `false` (collapsed)
- Replaced plain `e("div", null, e("label"...), e("textarea"...))` blocks in both tabs with:
  - A clickable header bar with chevron SVG + "Workflow Cypher" label
  - Conditional rendering of the textarea only when open
- Keyboard accessibility: Enter/Space toggles, `aria-expanded` attribute
- Rebuilt and redeployed: `docker compose build --no-cache design-grammars && docker compose up -d design-grammars`

### Files changed

- `graph-viewer/index.html` — CSS (~line 301), state variables (~line 1523), Design Rules block (~line 3180), Knowledge block (~line 3502)

## Decisions Made

- Reused the same visual pattern as Session History collapsible header (dark bg, border, hover accent on chevron)
- Default state: collapsed — the Workflow Cypher content is secondary/debug info

## Issues Encountered

- PowerShell `String.Replace()` failed on multiline blocks due to whitespace; solved with line-based `ArrayList` manipulation

## Next Steps

- Human verification in browser (Ctrl+Shift+R to clear cache)

## Related Notes

- [[UI is a single-file React 18 SPA with no build step]]
- [[Docker layer caching can serve stale index.html]]
