---
status: testing
phase: 34-ontology-tagging-components
source: [34-VERIFICATION.md]
started: 2026-07-18T22:38:40Z
updated: 2026-07-18T22:38:40Z
---

## Current Test

number: 1
name: DG OBJECT MARKER — create, idempotent re-run, ValueTable persistence
expected: |
  Load DG.gha (Release build) in Rhino 8 / Grasshopper. On a blank canvas place DG OBJECT MARKER,
  ObjectName="BRIDGE", AlgorithmIndex=1 → two scribbles appear top-left: "OBJECT - BRIDGE" and
  "1_ALGORITHM" in large font. Recompute → NO duplicate scribbles; Status reports existing markers read.
  Wire a Class IRI, save the .gh, reopen → binding persists (ValueTable key dg.objectClassIri survived).
awaiting: user response

## Tests

### 1. DG OBJECT MARKER — create, idempotent re-run, ValueTable persistence
expected: Blank canvas → "OBJECT - BRIDGE" + "1_ALGORITHM" scribbles top-left; recompute creates no duplicates and reports existing markers; Class IRI binding survives .gh save/reopen via ValueTable key dg.objectClassIri
result: [pending]

### 2. DG OBJECT MARKER — icon and scribble styling vs Frame reference (aesthetic)
expected: ObjectMarker24 icon and scribble font size/placement (Microsoft Sans Serif 30f at PointF(10,10)/(10,60)) are placeholders — compare against the Frame reference screenshot and note adjustments needed (low functional risk)
result: [pending]

### 3. DG ENTITY TAG — tag→parse→undo round-trip, nesting, guard rails
expected: Kind value list auto-appears wired (Proc/Pat/Var/Const/Emg/IntF). Select a slider, Kind=Var, Name="SpansCount", ProcIndex=11, press Tag → PINK group "11_Var_SpansCount" wraps the slider. Phase 32 extractor (get_canvas_context) reports it as CgParameter kind:Variable source:tagged. Ctrl+Z removes the group cleanly. Tagging a selection inside an existing 11_Pat_* group renders PURPLE nested with HostPatternId. Empty selection → Warning, no group. Name="Foo_Var_Bar" (reserved infix) → Warning, no group.
result: [pending]

### 4. DG ENTITY TAG — group colors and icon vs Frame reference (aesthetic)
expected: CanvasAnnotationStyles palette (Procedure near-white, Pattern orange, NestedPattern purple, Parameter pink, Interface near-white) and EntityTag24 icon are [ASSUMED] placeholders — compare against the Frame reference and note hex adjustments (low functional risk)
result: [pending]

### 5. Fix-chain regression check (WR-10/WR-11) — re-tag a child-hosting Pattern
expected: Create a Pattern group that hosts a nested tagged entity (child group). Re-tag the SAME core selection (label-only change) → the existing group is updated in place (no duplicate, no self-nest) AND the nested child group stays nested (purple, still a member of the host). Also: a Pattern consisting only of nested groups is not hijacked by an unrelated group-only selection.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
