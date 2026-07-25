---
tags: [debugging, ui-v2, css, design-system]
date: 2026-07-25
component: ui-v2/src/components/forms/Combobox.jsx
---

# Column flex + maxHeight → rows compress instead of scrolling

## Symptom

The `Combobox` value dropdown in the Graph Viewer search bar rendered its rows
**overlapping each other** once the value list grew long (e.g. the `label` field on a
populated ontology layer — ~20+ values). Text from adjacent rows collided vertically;
the list did not scroll.

## Root cause

The popover list is a column flex container with a height cap:

```js
display: "flex", flexDirection: "column", maxHeight: 260, overflowY: "auto"
```

In a **column** flex container, `flex-shrink` applies to the *height* axis, and its
default value is `1`. Once the combined natural height of the rows exceeded
`maxHeight: 260`, flex resolved the overflow by **shrinking every row** — from a
natural ~28px (12px text × 1.35 line-height + 12px padding) down to ~13px each.

The row boxes shrank but the text inside kept its line-height, so glyphs spilled out
of their boxes and overlapped their neighbours. Critically, `overflowY: auto` never
engaged: from flex's point of view the content had been made to *fit*, so there was
nothing to scroll.

## Fix

Pin every child of the list against shrinking:

```js
flex: "none"   // on rows, the empty-state label, and the "+N more" footer
```

Children keep their natural height, total content height exceeds the cap, and
`overflowY: auto` scrolls as intended.

Commit `de183fe`.

## Generalisation — check this whenever

Any **column** flex container with `maxHeight`/`height` + `overflowY: auto` and a
variable number of children. This pattern appears throughout ui-v2 (session console,
match lists, Session History, the minimap stack). It is not specific to comboboxes.

Two tells that distinguish it from ordinary overflow bugs:
- content **overlaps** rather than being clipped or scrolled
- the scrollbar never appears even though there is obviously too much content

`flex: "none"` on the children is the fix; a `min-height: 0`/`flex-basis: auto`
variant is the same idea. Note the inverse trap also exists: a flex **child** that
should scroll needs `min-height: 0`, because the default `min-height: auto` refuses
to shrink below content size.

Because `flex: "none"` on a list row looks removable during cleanup, the Combobox
carries an inline comment marking it load-bearing.

## Related

- [[Layout overflow guards required for resizable flex children]] — same family of flex
  sizing trap, seen from the container side
- [[decisions/Graph Viewer search bar adaptive value dropdown]]
- Component: `ui-v2/src/components/forms/Combobox.jsx`
