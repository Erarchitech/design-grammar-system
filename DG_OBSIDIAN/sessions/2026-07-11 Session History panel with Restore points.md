---
tags: [session]
date: 2026-07-11
---

# Session: Session History panel with Restore points

## Summary
Built a proper Session History panel for the V2 Graph Viewer with graph restore points. The feature was previously missing — the legacy `graph-viewer/index.html` had a filterable collapsible panel with badge/prompt/date/Restore actions that was never ported to the V2 `ui-v2/` codebase.

## Commits (6)
1. `0a8abe2` — Strip Cypher from Session History panel results
2. `5b2de22` — Return the always-visible Restore action to rows
3. `ccf3f87` — Three actions: Restore, Reuse prompt, Repeat
4. `f832711` — Remove duplicated action bar from expanded detail
5. `7e0c489` — Remove Repeat buttons, rename "Reuse prompt" → "Reuse"
6. `d336065` — Add Confirm button to restore-point banner

## Key Decisions
- **D-01:** Checkpoints persisted to localStorage (capped at 4, quota-safe) so Restore survives reloads
- **D-02:** Expanded detail shows only Prompt/Result/Time — actions are inline only (no duplication)
- **D-03:** Confirm button commits the restored state and hides the banner permanently (Return to live no longer possible after Confirm)
- **D-04:** Restore only available on turns with a checkpoint (ingest/edit); Reuse always available

## Files Changed
- `ui-v2/src/components/display/SessionHistory.jsx` — new reusable component
- `ui-v2/src/lib/graphApi.js` — saveDrSession now returns server sessionId
- `ui-v2/src/screens/GraphScreen.jsx` — snapshot checkpoint/restore, panel wiring

## Verification
- Live test on project TestA (7 sessions): Restore/Repeat/Reuse all rendered correctly
- Injected checkpoint verified: Restore rewinds graph, banner shows Confirm + Return to live
- `vite build` clean across all commits
- Model Viewer skipped (no session data — RunTile strip serves as run history)

## Related
- Previous wrong approach: localStorage viewport/rule persistence (reverted in spirit by this proper implementation)
