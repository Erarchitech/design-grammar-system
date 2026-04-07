---
phase: 06-ui-update-panel-inline-diff-editor
plan: 02
subsystem: graph-viewer-ui
tags: [ui, update-knowledge, review-view, summary-view, confirm-handler, diff-editor]
dependency_graph:
  requires: [06-01-plan]
  provides: [update-knowledge-review-view, update-knowledge-summary-view, update-knowledge-confirm]
  affects: [graph-viewer/index.html]
tech_stack:
  added: []
  patterns: [sequential-note-review, diff-preview-panel, batch-confirm, optimistic-locking-409]
key_files:
  created: []
  modified:
    - graph-viewer/index.html
decisions:
  - Review view renders one note at a time with Previous/Next navigation per D-09
  - Skip this note excludes from Confirm batch per D-10
  - Summary view shows changed/skipped badges per D-11
  - Batch confirm sends all non-skipped notes in one call per D-12
  - 409 conflict handled with specific error message per RESEARCH.md Pattern 7
  - Success notification shows Updated titles in green per D-15
  - resetUpdateState clears all state after Confirm per RESEARCH.md Pitfall 2
metrics:
  completed: 2026-04-07
  tasks: 3
  files: 1
---

# Phase 6 Plan 02: Review View + Summary + Confirm Summary

Complete three-step Update Knowledge flow with sequential diff review editor, summary view with changed/skipped badges, and batch Confirm handler with success notification.

## What Was Built

1. **Review View** — Sequential note-by-note editor with:
   - Back to search button (resets all update state)
   - Note title header with counter ("Note 2 of 4")
   - Collapsible diff preview panel (Show diff / Hide diff toggle)
   - Server-generated diffHtml with red deletions and green additions
   - Editable textarea pre-populated with proposedContent
   - "No changes proposed" banner for unchanged notes
   - Previous note / Next note navigation buttons
   - Review Summary button on last note transitions to summary
   - Skip this note button excludes note from Confirm batch

2. **Summary View** — Review Changes panel with:
   - Note list with "changed" (green) or "skipped" (muted) status badges
   - "Confirm All (N notes)" button (disabled when all skipped)
   - "All notes skipped" message when nothing to confirm

3. **Confirm Handler** — `submitConfirm` with:
   - Batch payload: filters out skipped notes, sends editedContents + updatedAt
   - 409 conflict handling with specific error message
   - Success shows "Updated: Title1, Title2" in green in Response textarea
   - Full state reset after successful Confirm

4. **Human Verification** — All 15 verification steps approved

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Review view — diff panel, editor, navigation | 1d6a485 | graph-viewer/index.html |
| 2 | Summary view + Confirm handler + success notification | f74605a | graph-viewer/index.html |
| 3 | Human verification checkpoint | — | Manual approval |

## Known Stubs

None — all views fully wired to backend endpoints.

## Self-Check: PASSED

- [x] graph-viewer/index.html contains "submitConfirm", "Confirm All", "Review Changes", "Skip this note"
- [x] Commit 1d6a485 exists
- [x] Commit f74605a exists
- [x] Human verification approved
