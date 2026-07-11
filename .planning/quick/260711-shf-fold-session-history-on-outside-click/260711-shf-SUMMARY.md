---
quick_id: 260711-shf
status: complete
---

# Summary: Fold Session History panel on outside click

## What changed

`ui-v2/src/screens/GraphScreen.jsx`:
- Added `historyPanelRef` ref, attached to the Session History wrapper `div` (the `dg-frost` panel containing `<SessionHistory>`).
- Added a `React.useEffect` keyed on `historyOpen` that, while the panel is open, listens for `mousedown` on `document` and calls `setHistoryOpen(false)` when the event target is outside `historyPanelRef.current`. Listener is removed on cleanup / when `historyOpen` becomes false.

## Verification

- `npm --prefix ui-v2 run build` completes with no errors.
- Behavior: clicks on the header/rows/filter/Restore/Reuse buttons inside the panel do not close it (they're inside the ref'd container); any click elsewhere in the Graph Viewer closes it.

## Commit

Committed as part of this quick task per project CLAUDE.md conventions.
