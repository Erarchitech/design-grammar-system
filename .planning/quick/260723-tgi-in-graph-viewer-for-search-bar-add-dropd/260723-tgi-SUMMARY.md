---
quick_id: 260723-tgi
description: "In Graph Viewer search bar, add a value dropdown that adapts to the selected field and lists all available unique values"
date: 2026-07-23
status: complete
commit: f132719
files_modified:
  - ui-v2/src/components/forms/Combobox.jsx (new)
  - ui-v2/src/components/index.js
  - ui-v2/src/screens/GraphScreen.jsx
---

# Quick Task 260723-tgi — Summary

## What was built

The Graph Viewer's persistent "Search by" filter bar now offers a dropdown of the
values that actually exist for the selected field, instead of requiring the user to
type a value blind.

### 1. `Combobox` primitive (new)

`ui-v2/src/components/forms/Combobox.jsx`, exported from the component barrel.

A searchable value picker: a text field whose chrome mirrors `SearchField`
(same search glyph, `--surface-input`, `--radius-inputs`, 36px height) plus a
chevron toggle mirroring `Select`, over a `dg-frost` popover list matching the
existing right-click search popover.

Design-system compliance: built from existing tokens only — no new colors,
radii, shadows, or fonts. Rows use `--color-signal-soft` for the active wash and
`--color-signal-ink` for the selected value, the same selection language used in
`ApiDocsScreen` and `colors.css`. Verified all tokens resolve in both light and
dark themes.

Behavior:
- `openDirection="up"` — the bar sits at the screen bottom
- empty input lists every option; typing narrows by substring
- keyboard nav (↑/↓/Enter/Escape) and outside-click dismissal
- `onPick` is distinct from `onChange`, so free text and list selection stay separable
- caps the rendered list at `maxVisible` (200) with a "+N more" hint, so a
  high-cardinality field can't render thousands of rows

### 2. Adaptive value derivation

`GraphScreen.jsx` gained a `fieldValues` `useMemo` keyed on `[ringN, searchProp]`,
so the option set recomputes whenever the field picker or active ring layer changes:

| `searchProp` | Values listed |
|---|---|
| `*` (Any field) | union of node labels + all property values |
| `__label` (Label) | node labels |
| a property key | that property's values only |

Values are de-duplicated, empty/null-filtered, and sorted with
`localeCompare(..., { numeric: true })` so numeric-ish values (75, 100) don't order
lexicographically.

### 3. Search bar wiring

The bar's `SearchField` was replaced by `Combobox` fed from `fieldValues`. Picking
a value sets `q` / `filterOn` / `filterQ` exactly as typing does, so it flows through
the unchanged `engine.computeMatches` path — no engine changes were needed. The
right-click search popover still uses `SearchField` and is untouched.

## Verification

- `npm --prefix ui-v2 run build` → clean, 948 modules transformed, built in 6.43s.
  (The >500 kB chunk warning is pre-existing and unrelated.)
- Confirmed no early returns precede the new `useMemo` in `GraphScreen` — hook
  ordering is unconditional.
- Confirmed every token used (`--color-signal-soft`, `--color-signal-ink`,
  `--surface-input`, `--radius-inputs`, `--text-primary`) is defined in
  `styles/tokens/colors.css` / `effects.css` for both themes.
- Confirmed no ancestor of the search bar sets `overflow: hidden`, so the
  upward-opening dropdown is not clipped.

## Notes / follow-ups

- Not browser-verified — validated by build + static reading of the render path.
  Worth an eyeball on a live graph to confirm the upward dropdown clears the
  session panel at small viewport heights.
- `Combobox` is generic; the mode-2 "Rule" picker in the same screen is a
  plain `Select` over rule IDs and could adopt it later if rule counts grow.
