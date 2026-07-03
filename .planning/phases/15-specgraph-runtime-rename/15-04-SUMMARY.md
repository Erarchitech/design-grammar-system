---
phase: 15-specgraph-runtime-rename
plan: 04
subsystem: "graph-viewer UI (NeoVis config + SPA)"
tags:
  - rename
  - KnowledgeGraph
  - SpecGraph
  - NeoVis
  - config
  - UI
requires: []
provides: ["SPEC-04: NeoVis Specs&Notes view queries graph:'SpecGraph' and styles Spec* labels"]
affects: ["graph-viewer/config.template.js", "graph-viewer/index.html"]
tech-stock:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - graph-viewer/config.template.js
    - graph-viewer/index.html
decisions: []
metrics:
  duration: ~5 min
  completed_date: "2026-07-03"
status: complete
---

# Phase 15 Plan 04: SpecGraph NeoVis Config + View Key Rename — Summary

Renamed the four NeoVis label/visGroups keys in `config.template.js` (KnowledgeNote->SpecNote, KnowledgeTag->SpecTag, KnowledgeSession->SpecSession, KnowledgeClass->SpecClass) keeping all display-property values and color hex values byte-for-byte unchanged, and renamed the four KnowledgeGraph view-key/Cypher sites in `index.html` to SpecGraph, preserving all out-of-scope notes-panel identifiers and user-facing labels.

## Tasks

| # | Name | Type | Status | Commit |
|---|------|------|--------|--------|
| 1 | Rename NeoVis label + visGroups keys in config.template.js | auto | Done | `86c68fa` |
| 2 | Rename the 4 KnowledgeGraph view-key/Cypher sites in index.html | auto | Done | `0c40635` |

## Results

### Task 1 — config.template.js (8 keys)

**What changed:**
- `labels` block: `KnowledgeNote: { label: "title" }` -> `SpecNote: { label: "title" }` (and same for Tag/Session/Class)
- `visGroups` block: `KnowledgeNote: { ... color: "#4ecdc4" ... }` -> `SpecNote: { ... color: "#4ecdc4" ... }` (and same for Tag/Session/Class)
- Zero Knowledge* tokens remain. All 4 Spec* keys present in both blocks.
- All 4 color hex values preserved: `#4ecdc4` (teal, Note), `#ffe66d` (yellow, Tag), `#a78bfa` (purple, Session), `#f472b6` (pink, Class).

### Task 2 — index.html (4 sites)

**What changed:**
1. `if (view === "KnowledgeGraph")` -> `view === "SpecGraph")` (L1439)
2. `"MATCH (n {graph:'KnowledgeGraph'"` -> `'SpecGraph'` (L1441)
3. `"OPTIONAL MATCH (n)-[r]-(m {graph:'KnowledgeGraph'"` -> `'SpecGraph'` (L1442)
4. `const q = buildCypher("KnowledgeGraph");` -> `buildCypher("SpecGraph")` (L2916)

**Preserved (out-of-scope, D-10/D-11):**
- `knowledgeMode` / `setKnowledgeMode` / `knowledgePromptText` etc. (~80 lowercase knowledge* React state identifiers)
- "Insert Knowledge", "Query Knowledge", "Update Knowledge" button labels
- "Specs&Notes" tab label (already Spec*-aligned per D-10)
- Workflow polling keys: `"knowledge-ingest"`, `"knowledge-query"`
- `/knowledge/*` route paths (lowercase, stay for URL compatibility)

## Deviations from Plan

None. Plan executed exactly as written.

## Verification

Both files pass the automated verification:
- `config.template.js`: zero Knowledge* tokens in labels or visGroups; four Spec* keys present; all 4 color hexes preserved.
- `index.html`: zero Knowledge* graph-layer tokens; `view === "SpecGraph"`, `buildCypher("SpecGraph")`, and `graph:'SpecGraph'` present; out-of-scope identifiers (`knowledgeMode`, `Insert Knowledge`, `knowledge-ingest`) still present.

## Self-Check

```
PASS: config.template.js — 0 Knowledge* tokens, 4 Spec* keys, 4 colors preserved
PASS: index.html — 0 Knowledge* graph tokens, SpecGraph view/Cypher, out-of-scope preserved
```

## Success Criteria

SPEC-04 satisfied: the NeoVis "Specs&Notes" view queries `graph:'SpecGraph'` and styles the four `Spec*` labels with unchanged colors, while the notes-panel UI naming and user-facing labels are intentionally preserved (D-10/D-11).
