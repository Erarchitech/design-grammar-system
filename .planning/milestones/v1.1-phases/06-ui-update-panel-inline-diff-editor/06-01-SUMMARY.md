---
phase: 06-ui-update-panel-inline-diff-editor
plan: 01
subsystem: graph-viewer-ui
tags: [ui, update-knowledge, match-view, propose-handler, diff-css]
dependency_graph:
  requires: [phase-04-update-endpoints]
  provides: [update-knowledge-match-view, update-knowledge-propose-handler, diff-css-classes]
  affects: [graph-viewer/index.html, data-service/app.py]
tech_stack:
  added: []
  patterns: [update-view-state-machine, candidate-checkbox-list, inline-step-indicators]
key_files:
  created: []
  modified:
    - graph-viewer/index.html
    - data-service/app.py
decisions:
  - Use setKnowledgeWorkflowStep for consistent step timing across all knowledge modes
  - Prompt textarea visible in match and proposing views, hidden during review/summary (Plan 02 handles those)
  - XSS mitigation via html.escape in word_diff_html (T-06-03)
metrics:
  completed: 2026-04-07
  tasks: 2
  files: 2
---

# Phase 6 Plan 01: CSS + State + Match View + Propose Handler Summary

Update Knowledge mode with Match and Propose views in sidebar — candidate checkbox list with score badges, step-indicator propose flow, and XSS-safe diff HTML generation.

## What Was Built

1. **CSS Classes** — `.diff-del` (red bg + strikethrough), `.diff-ins` (green bg + bold), `.diff-preview` (monospace panel with dark background and border)
2. **KNOWLEDGE_OPTIONS** — Added `{ value: "update", label: "Update Knowledge" }` to the mode dropdown
3. **State Variables** — 8 new `useState` hooks: `updateView`, `updateCandidates`, `selectedNoteIds`, `updateDiffs`, `currentNoteIndex`, `editedContents`, `skippedNoteIds`, `showDiff`
4. **Handlers** — `submitMatch` (fetch candidates), `toggleCandidate`, `toggleSelectAll`, `submitPropose` (synchronous fetch with step indicators), `resetUpdateState`
5. **Match View** — Prompt textarea, Search Notes button, candidate checkbox list with score badges, Select all/Deselect all toggle, Edit Selected button, empty state message
6. **Proposing View** — Back to search button, dimmed candidate list (opacity 0.4), progress bar, step indicators with elapsed timing
7. **Response Textarea** — Conditional green/red coloring for success/error messages

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Security] XSS in word_diff_html (T-06-03)**
- **Found during:** Task 1 threat model review
- **Issue:** `word_diff_html` in `data-service/app.py` did not escape HTML entities in note content words before wrapping in `<span>` tags — stored XSS vector if note content contained HTML
- **Fix:** Added `import html as html_mod` and wrapped all word outputs in `html_mod.escape(w)` before inserting into span markup
- **Files modified:** data-service/app.py
- **Commit:** 3773fbe

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | CSS + state + KNOWLEDGE_OPTIONS + Match view + Propose handler | bfed56b | graph-viewer/index.html |
| 2 | XSS fix + Back to search in proposing view | 3773fbe | graph-viewer/index.html, data-service/app.py |

## Known Stubs

None — all Match and Propose views are fully wired to backend endpoints.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: mitigated | data-service/app.py | T-06-03 XSS in word_diff_html now uses html.escape |

## Self-Check: PASSED

- [x] graph-viewer/index.html exists and contains "Update Knowledge", "diff-preview", "submitMatch", "submitPropose"
- [x] data-service/app.py contains "html_mod.escape"
- [x] Commit bfed56b exists
- [x] Commit 3773fbe exists
