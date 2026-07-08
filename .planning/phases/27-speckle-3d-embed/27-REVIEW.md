---
phase: 27-speckle-3d-embed
reviewed: 2026-07-08T12:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - ui-v2/src/components/speckle/SpeckleViewport.jsx
  - ui-v2/package.json
  - ui-v2/src/screens/ModelScreen.jsx
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-07-08T12:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Speckle 3D embed implementation: a new `SpeckleViewport.jsx` component wrapping `@speckle/viewer`, modifications to `ModelScreen.jsx` adding 3D/Map toggle and Speckle viewport rendering, and the `package.json` dependency update.

**Primary finding:** The SpeckleViewport component combines viewer lifecycle and event handler registration in a single `useEffect` whose dependency array includes inline callback props (`onEntityClick`, `onReady`, `onError`). Because `ModelScreen.jsx` passes these as inline arrow functions (new reference every render), the Speckle viewer is disposed and re-created on **every** parent re-render. This defeats the purpose of embedding a 3D viewport -- the viewer will flicker, reset camera state, and re-fetch all Speckle resources on every state change in ModelScreen. The legacy viewer (`graph-viewer/model-viewer/src/App.jsx`) handles this correctly by separating viewer lifecycle (`[manifestRunId, project]`) from event registration (`[viewerReady]`).

Remaining findings cover a race window in viewer disposal, missing 3D retry path, incomplete hook dependency array, and several code quality items.

---

## Critical Issues

### CR-01: Inline callback functions cause Speckle viewer re-creation on every parent render

**File:** `ui-v2/src/screens/ModelScreen.jsx:490-499` (root cause)
**File:** `ui-v2/src/components/speckle/SpeckleViewport.jsx:190` (contributing factor)

**Issue:**

`ModelScreen.jsx` passes all SpeckleViewport callbacks as inline arrow functions:

```jsx
<SpeckleViewport
  readToken={speckleToken}
  resourceUrls={speckleResourceUrls}
  project={project}
  runId={runId}
  onEntityClick={(id) => pick(id)}          // new reference every render
  onReady={() => setSpeckleReady(true)}     // new reference every render
  onError={(msg) => { setSpeckleError(msg); setViewMode("map"); }}  // new reference every render
  ...
/>
```

`SpeckleViewport.jsx` includes these callbacks in its `useEffect` dependency array (line 190):

```jsx
}, [resourceUrls, readToken, project, runId, onEntityClick, onReady, onError]);
```

Because every render of `ModelScreen` creates new function references for all three callbacks, SpeckleViewport's effect detects "changes" on every parent render. This triggers:

1. **Effect cleanup** runs: the previous viewer is disposed, click handler unregistered, host children cleared
2. **Effect re-runs**: a new `Viewer` instance is created, initialized, all resources reloaded, entity mapping re-done

Every `setState` call in `ModelScreen` (run selection, picking an entity, toggling filters, changing alpha sliders, etc.) causes a full Speckle viewer rebuild. The user will see the 3D viewport blank out and reload constantly during normal interaction. Camera position is lost on every re-initialization.

**The legacy viewer in `graph-viewer/model-viewer/src/App.jsx` solves this correctly:**
- Viewer lifecycle effect depends only on `[manifestRunId, project]` (line 760) -- no callback references
- Click handler registration is a **separate** effect (lines 763-799) with dependency `[viewerReady]` only
- The `viewerReady` state gate ensures the handler is only registered after the viewer is ready

**Fix (two parts):**

**Part A -- `SpeckleViewport.jsx`:** Store callbacks in refs instead of including them in the effect dependency array. This prevents the effect from re-running when only callback references change.

```jsx
// Near the top of the component, after refs:
const onEntityClickRef = React.useRef(onEntityClick);
const onReadyRef = React.useRef(onReady);
const onErrorRef = React.useRef(onError);

// Keep refs current on every render (before the effect)
onEntityClickRef.current = onEntityClick;
onReadyRef.current = onReady;
onErrorRef.current = onError;
```

Then use the refs inside the effect instead of the closure-captured props:

```jsx
const handleClick = (payload) => {
  const hit = payload?.hits?.[0];
  const raw = hit?.node?.model?.raw || {};
  const dgEntityId = raw.dgEntityId || "";
  if (dgEntityId && onEntityClickRef.current) {
    onEntityClickRef.current(dgEntityId);
  }
};
```

And change the dependency array to exclude callbacks:

```jsx
// eslint-disable-next-line react-hooks/exhaustive-deps
}, [resourceUrls, readToken, project, runId]);
```

**Part B -- `ModelScreen.jsx`:** Alternatively, stabilize the callbacks with `useCallback` (less invasive but still fragile if deps expand):

```jsx
const handleEntityClick = React.useCallback((id) => pick(id), [pick]);
```

The ref-based approach (Part A) is preferred as it makes `SpeckleViewport` resilient regardless of how the parent passes callbacks.

---

## Warnings

### WR-01: Race window during async viewer initialization before viewerRef assignment

**File:** `ui-v2/src/components/speckle/SpeckleViewport.jsx:108-135`

**Issue:**

The `initViewer` async function creates a `Viewer` instance at line 121 and calls `await viewer.init()` at line 126, but does not assign it to `viewerRef.current` until **after** initialization succeeds (line 135). The viewer also sets up extensions and begins loading resources before `viewerRef.current` is non-null.

If component dependencies change during the await window (between lines 121-135):

1. The effect cleanup runs immediately (synchronously on dep change)
2. Cleanup checks `viewerRef.current` -- it is still `null` (or points to the old/disposed viewer)
3. Cleanup does **not** dispose the new viewer because `viewerRef.current` doesn't reference it yet
4. The stale `initViewer` resumes, checks `if (disposed)` at line 128, and calls `viewer.dispose()` manually

The `disposed` closure flag mitigates this (the viewer does get disposed at step 4), but only because every `await` point checks the flag. If a future code path adds an `await` without a `disposed` check, the viewer leaks. The legacy code has the same pattern but also top-level `.catch()` on the init promise, which the new code lacks (line 175 uses bare `void initViewer()`).

**Fix:**

Assign `viewerRef.current = viewer` immediately after `new Viewer(...)` (and adjust the cleanup to handle partially-initialized viewers):

```jsx
const viewer = new Viewer(host, { ... });
viewerRef.current = viewer;   // track immediately
await viewer.init();          // now cleanup will dispose it if deps change
```

Or at minimum, add a top-level `.catch()`:

```jsx
void initViewer().catch((err) => {
  if (!disposed) {
    onErrorRef.current?.(err.message || "Speckle viewer initialization failed");
  }
});
```

Note: if `viewer.init()` throws after `viewerRef.current = viewer`, the cleanup (which also calls `viewer.dispose()`) would attempt a second dispose. To handle this, make cleanup check `viewerRef.current` against the known disposed instance, or make the viewer's `dispose()` idempotent. Alternatively, keep the ref assignment after `init()` but add a `.catch()` chain.

---

### WR-02: No retry mechanism for 3D view after initialization failure

**File:** `ui-v2/src/screens/ModelScreen.jsx:466-468,497`

**Issue:**

When `SpeckleViewport` initialization fails (network error, missing token, etc.), the `onError` handler auto-switches to map mode and sets `speckleError`:

```jsx
onError={(msg) => { setSpeckleError(msg); setViewMode("map"); }}
```

The "3D" button then becomes permanently disabled:

```jsx
<Button ... disabled={!!speckleError}>
  {speckleError && viewMode === "3d" ? "3D (err)" : "3D"}
</Button>
```

There is no way for the user to retry the 3D view without a full page reload, even if the error condition was transient (e.g., temporary network glitch). Once in the error state, `speckleError` is never cleared, and the `SpeckleViewport` component (which is conditionally rendered only when `viewMode === "3d"`) is never re-mounted.

**Fix:**

Add a retry mechanism that clears the error state and attempts re-initialization:

```jsx
const retry3d = () => {
  setSpeckleError(null);
  setViewMode("3d");
};

// In the 3D button:
<Button
  variant="outline"
  size="sm"
  selected={viewMode === "3d"}
  onClick={() => { if (speckleError) retry3d(); else setViewMode("3d"); }}
  disabled={false}  // always clickable
>
  {speckleError ? "Retry 3D" : "3D"}
</Button>
```

---

### WR-03: `fetchValidationView` not in useEffect dependency array (stale closure)

**File:** `ui-v2/src/screens/ModelScreen.jsx:124-149`

**Issue:**

The effect at line 124 calls `fetchValidationView(project, runId)` but does not list `fetchValidationView` in its dependency array:

```jsx
React.useEffect(() => {
  if (!runId) { ... return; }
  let gone = false;
  fetchValidationView(project, runId)
    .then((v) => { ... })
    .catch(...);
  return () => { gone = true; };
}, [runId, project]);
```

While module-level imports are typically stable for the component lifecycle, this violates the `react-hooks/exhaustive-deps` rule. If `fetchValidationView` were to change at runtime (e.g., due to hot-module replacement in dev, or a dynamic import swap), the effect would capture a stale reference. The same pattern also affects the effects at lines 152-164 (`fetchRuleDetails`) and lines 167-179 (`fetchEntityStatuses`).

**Fix:**

Add the imported functions to the dependency arrays. Since they are stable module imports, they will not cause unnecessary effect re-runs in production:

```jsx
}, [runId, project, fetchValidationView]);
```

---

## Info

### IN-01: SVG interactive elements lack keyboard accessibility

**File:** `ui-v2/src/screens/ModelScreen.jsx:515-528`

**Issue:**

SVG `<path>` elements with `onClick` handlers (line 523-524) are not keyboard-accessible. They lack `role`, `tabIndex`, and `onKeyDown` handlers. Users relying on keyboard navigation (Tab, Enter/Space) cannot interact with the map entities.

**Fix:**

Add `tabIndex={0}`, `role="button"`, and an `onKeyDown` handler:

```jsx
<path
  key={b.id}
  d={b.d}
  onClick={() => { if (!panRef.current || panRef.current.moved < 5) pick(b.id); }}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') pick(b.id); }}
  role="button"
  tabIndex={0}
  ...
/>
```

---

### IN-02: High state count in single component

**File:** `ui-v2/src/screens/ModelScreen.jsx:67-94`

**Issue:**

`ModelScreen` contains 26 `useState` calls, 3 `useRef` calls, 3 `useMemo` calls, 1 `useCallback`, and 8 `useEffect` blocks -- all in a single function component. The JSX spans over 350 lines. This makes the component difficult to test, reason about, and maintain.

**Suggestion:**

Split into smaller sub-components:
- `ValidationRunsSidebar` (left panel -- design states, run list)
- `MapViewport` (SVG map with zoom/pan/minimap -- move boxPath, onWheel, onPointerDown, etc.)
- `PropertiesSidebar` (right panel with run/instance property display)
- `Toolbar` (filter checkboxes, alpha sliders, search, view mode toggle)

---

### IN-03: SpeckleViewport's effect retains viewer lifecycle concern mixed with event binding

**File:** `ui-v2/src/components/speckle/SpeckleViewport.jsx:98-190`

**Issue:**

The single `useEffect` at line 98 handles:
1. Viewer creation and disposal
2. Resource loading
3. Entity mapping
4. Click handler registration
5. `onReady` / `onError` callbacks

The legacy viewer (`App.jsx:671-799`) cleanly separates these into three effects: lifecycle, event registration, and resize. Combining them makes the code harder to reason about and forces all five concerns to re-run together on any dep change.

**Suggestion:** Extract the click handler registration into a separate effect gated by a `viewerReady`-style state:

```jsx
// Viewer lifecycle (no callback deps)
React.useEffect(() => { ... }, [resourceUrls, readToken, project, runId]);

// Click handler (separate registration, no lifecycle impact)
React.useEffect(() => {
  const viewer = viewerRef.current;
  if (!viewer || typeof viewer.on !== 'function') return;
  const handler = (payload) => { ... };
  viewer.on('object-clicked', handler);
  return () => { if (typeof viewer.off === 'function') viewer.off('object-clicked', handler); };
}, [/* stable deps only */]);
```

---

## Additional Observations

### package.json

Dependencies are clean. The `@speckle/viewer` version `^2.31.14` is newer than the legacy `^2.28.0` -- verify that the higher minor version is backward-compatible with the API usage (particularly `UrlHelper.getResourceUrls` and `SpeckleLoader` constructor signature). A minor-version bump in the Speckle viewer could introduce breaking changes if they do not follow strict semver.

---

_Reviewed: 2026-07-08T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
