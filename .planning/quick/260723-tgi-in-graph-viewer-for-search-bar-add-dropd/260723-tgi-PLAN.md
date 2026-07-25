---
quick_id: 260723-tgi
description: "In Graph Viewer search bar, add a value dropdown that adapts to the selected field and lists all available unique values"
created: 2026-07-23
mode: quick
status: complete
files_modified:
  - ui-v2/src/components/forms/Combobox.jsx (new)
  - ui-v2/src/components/index.js
  - ui-v2/src/screens/GraphScreen.jsx
---

# Quick Task 260723-tgi: Adaptive value dropdown for the Graph Viewer search bar

## Problem

The Graph Viewer's persistent "Search by" filter bar (`GraphScreen.jsx`, bottom-right
frost panel) is a two-part control:

- a `Select` — the **field** picker (`searchProp`): `Any field`, `Label`, or any node
  property key present in the active ring layer;
- a `SearchField` — a free-text substring filter (`q`) matched by
  `graphEngine.computeMatches`.

There is no way to see which values actually exist for the chosen field. The user must
know the value ahead of time and type it blind. Request: add a dropdown of possible
values that **adapts under the selected field** and lists **all available unique values**,
using the same design system.

## Approach

Turn the free-text filter into a **combobox**: keep type-to-filter, and add an anchored
dropdown of the unique values for the currently-selected field. Empty input shows the full
value set ("all available unique values"); typing narrows it; picking a value applies it as
the filter. No new dependencies — built from the same design tokens as `SearchField` /
`Select`.

1. **New primitive** `components/forms/Combobox.jsx` — a searchable value dropdown:
   text input (search icon, mirrors `SearchField` styling) + a chevron toggle (mirrors
   `Select`) + a frost popover list. Supports `openDirection="up"` (this bar sits at the
   screen bottom), keyboard nav (Arrow/Enter/Escape), outside-click dismissal, and
   `onPick(value)` distinct from `onChange`.
2. **Barrel** — export `Combobox` from `components/index.js`.
3. **GraphScreen** — compute `fieldValues` (unique, de-duped, natural-sorted) for the
   active `searchProp` via `useMemo`, and swap the search-bar `SearchField` for `Combobox`,
   feeding it those values. `Any field` (`*`) unions labels + all property values;
   `Label` (`__label`) uses node labels; a specific key uses that property's values.

## Tasks

### Task 1 — Combobox primitive + barrel export
- **files:** `ui-v2/src/components/forms/Combobox.jsx` (new), `ui-v2/src/components/index.js`
- **action:** Add the Combobox component; export it from the barrel.
- **verify:** `Combobox` importable from `../components/index.js`.
- **done:** Component renders field + dropdown from design tokens only.

### Task 2 — Wire adaptive values into the Graph Viewer search bar
- **files:** `ui-v2/src/screens/GraphScreen.jsx`
- **action:** Add `fieldValues` useMemo keyed on `[ringN, searchProp]`; replace the
  search-bar `SearchField` with `Combobox` (options=fieldValues, openDirection="up",
  onPick sets q/filterOn/filterQ).
- **verify:** Selecting a field repopulates the dropdown; picking a value filters the graph.
- **done:** Dropdown adapts to the field and lists all unique values; free-text still works.

### Task 3 — Build verification
- **files:** —
- **action:** `npm --prefix ui-v2 run build`.
- **verify:** Vite build succeeds with no errors.
- **done:** Clean production build.

## must_haves

- **truths:**
  - The value dropdown reflects the currently-selected `searchProp` (adapts under field).
  - The dropdown lists every unique value available for that field (empty input = full set).
  - Picking a value applies it as the active filter; typed free-text filtering is preserved.
  - Styling uses only existing design-system tokens/primitives (no new visual language).
- **artifacts:** `ui-v2/src/components/forms/Combobox.jsx`, edits to `index.js` + `GraphScreen.jsx`.
- **key_links:** `GraphScreen.jsx` search-bar block (`Search by` Select + filter field);
  `graphEngine.computeMatches`; `SearchField.jsx` / `Select.jsx` token usage.
