---
phase: 15-specgraph-runtime-rename
plan: 02
subsystem: api
tags: data-service, rename, cypher, labels

requires:
  - phase: 15-01
    provides: DB migration end-state (SpecGraph literal, Spec* labels, spec_note_search index)
provides:
  - data-service/app.py renamed Knowledge*->Spec* end-to-end in Cypher labels, graph constant, index name, startup hook
  - spec_schema.cypher renamed and Spec*-clean (replaces knowledge_schema.cypher)
  - test_update_flow.py assertion updated to SpecSession
affects:
  - 15-03 n8n workflow rename (will reference Spec* labels)
  - 15-04 UI/NeoVis rename (will reference Spec* labels)

tech-stack:
  added: []
  patterns:
    - Rename pattern: mechanical Knowledge*->Spec* across Cypher string literals, Python identifiers, and index names
    - Hub MERGE key agreement: SpecNote/SpecSession hub names match 15-01 migration normalization

key-files:
  modified:
    - data-service/app.py (50 edits: constant, function, ~40 Cypher label refs, fulltext index, hub MERGE)
    - spec_schema.cypher (renamed from knowledge_schema.cypher, 16 insertions/16 deletions)
    - data-service/tests/test_update_flow.py (assertion + docstring update)

key-decisions:
  - "Knowledge*->Spec* rename is purely mechanical string replacement — no logic changes"
  - "/knowledge/ endpoint route paths preserved unchanged (SPEC-02)"
  - "spec_schema.cypher stays a comment-only idempotent reference doc (same structure, Spec* content)"

requirements-completed: [SPEC-02]

duration: 8min
completed: 2026-07-03
status: complete
---

# Phase 15 Plan 02: SpecGraph Runtime Rename — data-service code and schema reference

**Mechanical Knowledge*->Spec* rename across data-service/app.py Cypher labels, constant, function name, and index name; git-mv knowledge_schema.cypher -> spec_schema.cypher with Spec* content; test_update_flow.py assertion aligned. Endpoint URLs preserved.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-03T16:00:00Z
- **Completed:** 2026-07-03T16:08:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- data-service/app.py: all 50 Knowledge* graph-layer references renamed to Spec* (constant `SPEC_GRAPH = "SpecGraph"`, function `ensure_spec_indexes`, index `spec_note_search`, labels SpecNote/SpecTag/SpecSession/SpecClass across ~40 CRUD Cypher queries, hub MERGEs, startup hook)
- knowledge_schema.cypher renamed to spec_schema.cypher via git mv (history preserved), content fully Spec*-clean with updated header and graph-isolation prose
- test_update_flow.py: `"KnowledgeSession"` assertion and docstring updated to `"SpecSession"`
- Zero Knowledge* graph-layer tokens remain across all three files
- `/knowledge/` endpoint routes preserved (SPEC-02)
- All three files parse as valid Python

## Task Commits

1. **Task 1: Rename Knowledge*->Spec* across data-service/app.py** - `a914f2b` (feat)
2. **Task 2: Rename knowledge_schema.cypher -> spec_schema.cypher** - `a4d9069` (feat)
3. **Task 3: Update update-flow test assertion** - `5700d41` (test)

## Files Created/Modified
- `data-service/app.py` — Knowledge*->Spec* rename (constant, function, fulltext index, all Cypher labels/hubs)
- `knowledge_schema.cypher` -> `spec_schema.cypher` — renamed with git mv, content fully Spec*-clean
- `data-service/tests/test_update_flow.py` — assertion and docstring updated to SpecSession

## Decisions Made
- Followed plan exactly: mechanical string replacement only
- docstring in test_update_flow.py also updated (caught by case-insensitive grep in verification)
- KNOWLEDGE_REPO_ROOT and all lowercase `knowledge_*` function names left untouched — they are not graph-layer identifiers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

All artifacts verified: SUMMARY.md present, all 3 commits present in git history.

## Next Phase Readiness
- data-service now reads/writes Spec* labels matching 15-01 migration end-state
- spec_schema.cypher is the canonical SpecGraph reference document
- Ready for 15-03 (n8n workflow rename) and 15-04 (UI/NeoVis rename)

---
*Phase: 15-specgraph-runtime-rename*
*Completed: 2026-07-03*
