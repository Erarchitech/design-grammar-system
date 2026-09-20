---
status: testing
phase: 37-script-structure-validation
source: [37-VERIFICATION.md]
started: 2026-07-27T00:00:00Z
updated: 2026-07-27T00:00:00Z
audit_acknowledged:
  milestone: v9.0
  at: 2026-09-19
  gap_snapshot: "testing::scenarios=1"
---

## Current Test

number: 1
name: Delete an Interface tag from Procedure 11_Proc on the real Frame Grasshopper canvas, re-publish through the DG COMPUTGRAPH PUBLISH component, then POST /computgraph/validate {project, definitionId}
expected: |
  Response flags the procedure_without_interface check and names the exact procedure (11_Proc / 2D Truss Configuration) in the finding's entities
awaiting: user response

## Tests

### 1. Delete an Interface tag from Procedure 11_Proc on the real Frame Grasshopper canvas, re-publish through the DG COMPUTGRAPH PUBLISH component, then POST /computgraph/validate {project, definitionId}

expected: Response flags the procedure_without_interface check and names the exact procedure (11_Proc / 2D Truss Configuration) in the finding's entities
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
