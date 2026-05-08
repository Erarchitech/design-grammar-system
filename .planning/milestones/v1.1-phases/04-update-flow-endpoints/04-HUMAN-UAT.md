---
status: partial
phase: 04-update-flow-endpoints
source: [04-VERIFICATION.md]
started: 2026-04-07T12:00:00Z
updated: 2026-04-07T12:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-End Propose with Live LLM
expected: Import and activate `n8n/workflows/knowledge-update.json` in n8n UI, then run `bash test/test_phase04_update_flow.sh` with all Docker services up. All 5 tests pass including propose returning HTML diff spans and confirm returning affectedNoteIds.
result: [pending]

### 2. Full-Text Index Query Routing
expected: Call `POST /knowledge/update/match` against running data-service with Neo4j notes present. Candidates array with noteId, title, score fields ordered by relevance.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
