---
status: testing
phase: 35-llm-recognition-canvas-preview
source: [35-VERIFICATION.md]
started: 2026-07-19T13:10:00Z
updated: 2026-07-19T13:10:00Z
---

## Current Test

number: 1
name: Frame recognition quality (ROADMAP SC1)
expected: |
  On the Frame definition with only the Object marker + 2 procedure tags present,
  POST /computgraph/recognize proposes patterns/parameters/interfaces whose member
  sets match the reference annotation for ≥ the majority of blocks, each with
  confidence + rationale; unclassifiable blocks appear in unrecognized[] with member ids.
awaiting: user response

## Tests

### 1. Frame recognition quality (ROADMAP SC1)
expected: On the Frame definition with only Object marker + 2 Proc tags, recognition proposes entities whose member sets match the reference annotation for ≥ the majority of blocks, each with confidence + rationale; unclassifiable blocks listed in unrecognized[] (needs live LLM via the gateway).
result: [pending]

### 2. Preview render + undo cleanliness (ROADMAP SC2)
expected: preview_structure draws desaturated groups named `[?] <name> (<confidence>%)` + one scribble legend; a SINGLE Ctrl+Z removes every trace; clear_preview leaves no residue (no orphan groups/scribbles).
result: [pending]

### 3. Concurrent-solve safety (Assumption A2)
expected: Triggering preview_structure while the canvas is mid-solve does not crash Rhino or corrupt the document (InvokeOnCanvasWrite marshals correctly to the UI thread).
result: [pending]

### 4. Accept / reject / partial accept (ROADMAP SC3)
expected: DG STRUCTURE CONFIRM lists pending proposals; Accept converts preview group to a permanent Phase-34-style convention group with `source: recognized` (dg.recognized.<guid> ValueTable marker) that SURVIVES save + reopen and parses identically to a hand-made tag; Reject removes cleanly; partial accept leaves the rest pending.
result: [pending]

### 5. Mixed accept/reject undo (WR-05 fix)
expected: One Apply with some proposals accepted and some rejected → a single Ctrl+Z restores the rejected preview groups (GH_RemoveObjectAction) and reverts the accepted restyles coherently.
result: [pending]

### 6. Re-preview stale undo record (IN-12)
expected: Run preview_structure twice in a row (second call auto-clears the first preview). Pressing Ctrl+Z twice walks the two undo records without leaving orphan groups or resurrecting cleared previews inconsistently.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
