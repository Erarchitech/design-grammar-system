---
tags: [decision, ui-v2, design-system, graph-viewer]
date: 2026-07-25
quick_task: 260723-tgi
---

# Graph Viewer search bar — adaptive value dropdown (Combobox primitive)

## Context

The Graph Viewer's persistent filter bar was a two-part control: a `Select` picking the
**field** (`searchProp` — `Any field` / `Label` / any property key in the active ring)
and a `SearchField` holding a free-text substring query (`q`), matched by
`graphEngine.computeMatches`.

Nothing surfaced *which values actually existed* for the chosen field. The user had to
know the value in advance and type it blind — on an ontology layer that means guessing
at exact class labels.

## Decision

Turn the value input into a **combobox**: keep type-to-filter, and add a dropdown listing
every unique value present in the active ring for the currently-selected field.

### 1. New primitive, not an inline one-off

Added `ui-v2/src/components/forms/Combobox.jsx` to the design system (22 → 23 primitive
files) rather than inlining the dropdown in `GraphScreen`.

Rationale: the same "pick from data-derived values" need already exists elsewhere (the
mode-2 Rule picker is a plain `Select` over rule IDs and will not scale as rule counts
grow). A primitive keeps the interaction consistent when that day comes.

### 2. Combobox is distinct from Select — open-ended, not constrained

`Select` constrains input to its option set. `Combobox` does **not**: the option list is
a discovery shortcut, and typed free text outside the list still filters. This preserves
the pre-existing substring-filter behaviour exactly — the change is purely additive.

Consequence: `onPick` is deliberately a separate prop from `onChange`, so callers can
distinguish "user chose a known value" from "user is typing".

### 3. Values are derived, not configured

A `useMemo` keyed on `[ringN, searchProp]` recomputes the option set whenever the field
picker **or** the active ring layer changes — this is what makes it "adapt under the
selected field":

| `searchProp` | Values listed |
|---|---|
| `*` (Any field) | union of node labels + all property values |
| `__label` (Label) | node labels |
| a property key | that property's values only |

De-duplicated, empty/null-filtered, sorted with `localeCompare(..., { numeric: true })`
so numeric-ish values (75, 100) do not order lexicographically — relevant because
DG rules are full of numeric limits.

### 4. No engine changes

Picking a value sets `q` / `filterOn` / `filterQ` exactly as typing does, so it flows
through the unchanged `computeMatches` path. The graph engine was not touched.

Note the consequence: picking a value applies it as a **substring** filter, not an exact
match, consistent with typed behaviour. Selecting `Floor` also matches `Floor panel`.
Accepted as consistent-with-existing; revisit only if exact-match is requested.

### 5. Design-system compliance

Built from existing tokens only — no new colors, radii, shadows or fonts. Field chrome
mirrors `SearchField` (search glyph, `--surface-input`, `--radius-inputs`, 36px), the
chevron mirrors `Select`, the list is a `dg-frost` popover matching the existing
right-click search popover, and row selection uses the established
`--color-signal-soft` / `--color-signal-ink` pair. All verified to resolve in both
light and dark themes.

`openDirection="up"` because the bar is anchored to the screen bottom. The component
owns `Escape` only while its list is open, so the screen-level Escape precedence
(close search → clear selection → back to landing) is preserved.

## Commits

- `f132719` — Combobox primitive + barrel export + GraphScreen wiring
- `de183fe` — flex-shrink overlap fix (see [[debugging/Column flex dropdown rows overlap instead of scrolling]])

## Related

- [[sessions/2026-07-25 Graph Viewer search bar adaptive value dropdown]]
- `.planning/quick/260723-tgi-in-graph-viewer-for-search-bar-add-dropd/`
