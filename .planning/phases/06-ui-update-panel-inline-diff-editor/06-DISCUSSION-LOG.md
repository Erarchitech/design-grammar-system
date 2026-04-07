# Phase 6: UI Update Panel + Inline Diff Editor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 06-ui-update-panel-inline-diff-editor
**Areas discussed:** Candidate list & selection, Diff + editor layout, Multi-note editing flow, Propose step waiting UX

---

## Candidate List & Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Checkbox list with scores | Simple vertical list — checkbox + title + relevance score badge per row | ✓ |
| Radio list (single-select only) | Same layout but radio buttons — forces picking one note at a time | |
| You decide | Claude picks the best approach | |

**User's choice:** Checkbox list with scores
**Notes:** Multi-select via checkboxes to leverage backend's multi-note Propose capability

| Option | Description | Selected |
|--------|-------------|----------|
| Title only | Keep it compact — just title + score | ✓ |
| Title + first 2 lines | Show a truncated preview | |
| You decide | Claude picks | |

**User's choice:** Title only

| Option | Description | Selected |
|--------|-------------|----------|
| Inline message in list area | "No matching notes found" shown where the list would appear | ✓ |
| Toast notification | Brief floating notification | |
| You decide | Claude picks | |

**User's choice:** Inline message in list area

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — small toggle above the list | "Select all / Deselect all" text link | ✓ |
| No — manual selection only | Keep it simple, manual checkboxes | |
| You decide | Claude picks | |

**User's choice:** Yes — select all/deselect all toggle

---

## Diff + Editor Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Stacked — diff above, textarea below | Fits narrow sidebar, matches existing vertical layout | ✓ |
| Side-by-side in sidebar | Two narrow columns, tight fit | |
| Diff replaces sidebar, textarea in modal | Full width for diff, modal for editing | |
| You decide | Claude picks | |

**User's choice:** Stacked — diff above, textarea below

| Option | Description | Selected |
|--------|-------------|----------|
| Red strikethrough + red bold (per requirement) | Deletions: red strikethrough. Additions: red bold | |
| Red/green (GitHub-style) | Deletions: red background. Additions: green background | ✓ |
| You decide | Claude picks | |

**User's choice:** Red/green (GitHub-style)
**Notes:** User chose GitHub-style over the spec's "red strikethrough + red bold" wording. Deliberate override.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — toggle to show/hide diff | Small toggle, saves vertical space | ✓ |
| No — always visible | Diff stays visible at all times | |
| You decide | Claude picks | |

**User's choice:** Collapsible diff panel with toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Proposed text | Pre-fill with LLM's proposed changes | ✓ |
| Original text | Pre-fill with original, user applies changes manually | |
| You decide | Claude picks | |

**User's choice:** Proposed text pre-populated

---

## Multi-Note Editing Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential — one note at a time | Show one note, Next/Previous buttons | ✓ |
| Accordion — all notes expandable | Collapsible sections for each note | |
| Tabbed — one tab per note | Horizontal tabs with note titles | |
| You decide | Claude picks | |

**User's choice:** Sequential — one note at a time

| Option | Description | Selected |
|--------|-------------|----------|
| Batch confirm — one button for all | Single "Confirm All" sends all notes | ✓ |
| Per-note confirm | Each note has its own Confirm button | |
| You decide | Claude picks | |

**User's choice:** Batch confirm

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Skip button per note | Skipped notes excluded from Confirm batch | ✓ |
| No — all selected notes are confirmed | Must deselect at candidate list step | |
| You decide | Claude picks | |

**User's choice:** Skip button per note

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — brief list of notes to confirm | Summary with titles + changed/skipped status | ✓ |
| No — Confirm available on last note | No separate summary step | |
| You decide | Claude picks | |

**User's choice:** Summary view before final Confirm

---

## Propose Step Waiting UX

| Option | Description | Selected |
|--------|-------------|----------|
| Step indicators like Insert/Query | Reuse Phase 5 pattern with update-specific labels | ✓ |
| Simple spinner with message | Single spinner, no step breakdown | |
| You decide | Claude picks | |

**User's choice:** Step indicators with update-specific labels

| Option | Description | Selected |
|--------|-------------|----------|
| Keep candidate list visible with overlay | List dimmed/disabled, step indicators below | ✓ |
| Immediately switch to editor area | Clear list, show empty editor with indicators | |
| You decide | Claude picks | |

**User's choice:** Keep candidate list visible with overlay during wait

| Option | Description | Selected |
|--------|-------------|----------|
| Inline success in the panel | Green message listing updated note titles | ✓ |
| Floating toast notification | Brief floating notification | |
| You decide | Claude picks | |

**User's choice:** Inline success notification

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Back button in diff/editor view | "Back to search" link at top of diff view | ✓ |
| No — only after Confirm or via mode switch | No mid-flow escape | |
| You decide | Claude picks | |

**User's choice:** Back to search button

---

## Claude's Discretion

- Exact CSS for red/green diff backgrounds
- Step indicator label wording refinements
- Textarea dimensions and auto-resize behavior
- Navigation button styling and positioning
- Summary view layout details
- Handling LLM no-change proposals (hasChanges: false)
- Note title header above each diff+editor view

## Deferred Ideas

None — discussion stayed within phase scope.
