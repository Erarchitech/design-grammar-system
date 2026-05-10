---
tags: [decision, model-viewer, speckle, react, resize]
date: 2026-05-10
---

# ResizeObserver Wires Speckle viewer.resize() on Host Element

## Context

The Model Viewer hosts a Speckle `Viewer` instance inside a flex-column layout. When the bottom Validation Runs strip grew/shrank via its draggable resize handle, the host `div` updated correctly but the WebGL canvas inside kept its original pixel dimensions — the rendered scene stayed at its initial size, leaving a visible gap or overlap.

## Decision

Attach a `ResizeObserver` to `viewerHostRef.current` in `App.jsx`. Whenever the host element's box changes, call `viewer.resize()` and `viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS)`. Cleanup on unmount via `observer.disconnect()`.

```jsx
React.useEffect(() => {
  const host = viewerHostRef.current;
  if (!host || typeof ResizeObserver === "undefined") return undefined;
  const observer = new ResizeObserver(() => {
    const viewer = viewerRef.current;
    if (viewer && typeof viewer.resize === "function") {
      viewer.resize();
      if (typeof viewer.requestRender === "function") {
        viewer.requestRender(UpdateFlags.RENDER | UpdateFlags.SHADOWS);
      }
    }
  });
  observer.observe(host);
  return () => observer.disconnect();
}, []);
```

## Why This Approach

- **Centralized on the host, not on the strip.** A strip-level `onHeightChange` callback would only catch strip-driven resizes. ResizeObserver fires for any cause: window resize, sidebar collapse, dev-tools open, future panels, etc.
- **Speckle's public API.** `IViewer.resize(): void` is documented on the `IViewer` interface (`@speckle/viewer/dist/IViewer.d.ts:142`). It re-binds the renderer to the new container size.
- **Re-request render explicitly.** Some Speckle render paths are demand-driven; calling `resize()` alone doesn't always trigger a frame. Pairing it with `requestRender(RENDER | SHADOWS)` guarantees an updated paint.
- **Defensive:** `typeof ResizeObserver === "undefined"` guard for environments that lack it (very old browsers, SSR).

## Why Not Alternatives

- **Window `resize` event** — fires only on window-size changes, not on flex sibling height changes.
- **Polling** — battery- and CPU-wasteful, adds visible lag.
- **Manual `viewer.resize()` calls in every state setter** — fragile; misses any future cause.

## Related

- [[Layout overflow guards required for resizable flex children]] — the layout guards that make the host element actually shrink in the first place.
- [[Model Viewer is a Vite-built Speckle 3D viewer]]
- [[Per-run graphics state and screenshot persistence]]
