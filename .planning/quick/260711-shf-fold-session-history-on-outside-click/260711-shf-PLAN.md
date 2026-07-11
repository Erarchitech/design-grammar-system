---
quick_id: 260711-shf
status: complete
---

# Quick Task: Fold Session History panel on outside click

## Description

Update interface behavior for Graph Viewer so opened Session History folds down when user clicks anywhere beyond it.

## Task

- **Files:** `ui-v2/src/screens/GraphScreen.jsx`
- **Action:** Add a `historyPanelRef` on the Session History wrapper `div` and a `mousedown` document listener (active only while `historyOpen` is true) that calls `setHistoryOpen(false)` when the click target falls outside the ref.
- **Verify:** `npm --prefix ui-v2 run build` succeeds; clicking inside the panel (rows, filter, Restore/Reuse) keeps it open; clicking elsewhere on the Graph Viewer closes it.
- **Done:** Panel collapses on outside click without affecting existing toggle/row/restore interactions.
