---
tags: [debugging, css, flexbox, grid, layout, model-viewer]
date: 2026-05-10
---

# Layout Overflow Guards Required for Resizable Flex Children

## Problem

The bottom Validation Runs strip in the Model Viewer was given a draggable resize handle that updates inline `style.height` via React state. The `mv-bottom-strip` element correctly received the new height, BUT visually:

- The handle (positioned at `top: 0` of the strip) appeared **pinned** to the same screen Y while dragging.
- Only the inner `.mv-strip-content` scrollbar reacted (got shorter as content area grew).
- The 3D viewport above the strip retained its original size.

## Symptoms

User reports during UAT:
1. "*The control element remains pinned in the window, only scroller changes.*"
2. "*The 3D viewport above remains with older boundaries.*"

## Root Cause

The page layout had no overflow constraints:

```css
.mv-page {
  display: grid;
  grid-template-columns: 320px 1fr;
  height: 100%;
  /* missing: grid-template-rows, overflow */
}

.mv-right-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  /* missing: min-height: 0, overflow */
}
```

Without these:

- `grid-template-rows` defaulted to `auto` — the row sized to content. Because children had `height: 100%` (a circular dependency with the auto row), the row could grow with the content's intrinsic height.
- The flex container `.mv-right-col` had no `min-height: 0`, so its `flex: 1` child (`.mv-canvas-wrap` holding the 3D viewport) refused to shrink below its content's intrinsic minimum.
- No `overflow: hidden` anywhere meant the strip could simply grow DOWN past the viewport bottom rather than displacing siblings upward.

Net effect: the strip's height value was changing in React state, but it was extending below the viewport. Its top edge stayed where it was (at the bottom of the unchanged canvas-wrap), so the handle appeared pinned. The inner `.mv-strip-content` (`flex: 1` inside the strip) DID get more space, which is why the scrollbar reacted.

## Fix

```css
.mv-page {
  display: grid;
  grid-template-columns: 320px 1fr;
  grid-template-rows: 100%;     /* ← lock the row to viewport height */
  height: 100%;
  overflow: hidden;             /* ← children can't overflow downward */
}

.mv-right-col {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;                /* ← allow flex: 1 child to shrink */
  height: 100%;
  overflow: hidden;             /* ← belt & suspenders */
}
```

After this:
- Strip height grows → `.mv-canvas-wrap` (`flex: 1`, `min-height: 0`) shrinks to make room.
- Strip's top edge moves UP, taking the resize handle with it (so it tracks the cursor).
- The `ResizeObserver` on `viewerHostRef` then fires, calling `viewer.resize()` so the WebGL canvas matches the new container size.

## Lesson

**Any flex child with explicit dynamic height needs the parent flex container to have `min-height: 0` AND `overflow: hidden`.** Otherwise the child wins the size contest and the supposedly-flexible siblings refuse to shrink. CSS Grid containers with `height: 100%` similarly need `grid-template-rows: <explicit>` + `overflow: hidden` to prevent grid rows from inflating to content.

This is the same family of issue as ["why won't my flex child shrink"](https://www.w3.org/TR/css-flexbox-1/#min-size-auto), which by spec defaults `min-height: auto` for flex items.

## Related

- [[ResizeObserver wires Speckle viewer.resize on host element]]
- [[ValidationRunsStrip component with per-project localStorage persistence]]
- [[Browser cache prevents seeing UI updates after rebuild]]
