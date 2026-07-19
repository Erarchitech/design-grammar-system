---
status: testing
phase: 36-computgraph-persistence-display
source: [ROADMAP.md Phase 36 Success Criteria, 36-VERIFICATION.md]
started: 2026-07-20T00:00:00Z
updated: 2026-07-20T00:00:00Z
---

## Current Test

number: 1
name: Publish confirmed Frame structure yields expected Computgraph subgraph
awaiting: live in-Rhino + Neo4j verification

## Tests

### 1. Publish confirmed Frame → expected subgraph, project-scoped (SC1)
expected: Publishing the confirmed Frame structure (DG COMPUTGRAPH PUBLISH, or the confirm-then-publish output on DG STRUCTURE CONFIRM) yields the expected Neo4j subgraph — one Object–Behavior–Algorithm chain, 2 Procedures (11_Proc 2D Truss Configuration, 12_Proc 2D Footer Configuration), correct patterns/parameters (paramKind Variable/Constant/Emergent + dataType)/interfaces (ifaceType Input/Output), all with graph:'Computgraph' + project; relationships HAS_BEHAVIOR/HAS_ALGORITHM/HAS_PROCEDURE/HAS_PATTERN/PATTERN_HOST_TO/HAS_PARAMETER/HAS_INTERFACE/PARAM_LINK present; optional REFERS_TO Object→Class when a Class IRI was tagged. DEDUP: this single subgraph-shape check is the terminal integration gate — a correct subgraph transitively re-proves Phase 32 parse + Phase 34 tags + Phase 35 recognition.
result: [pending]

### 2. Re-publish is MERGE-idempotent — zero node-count change (SC2)
expected: Re-publishing the same definition changes ZERO node counts (verified by a before/after count query). MERGE keys are stable entity ids from definition id + convention name, so re-publish updates in place and never duplicates; every published node retains its Phase 32.1 dgId across the re-publish.
result: [pending]

### 3. Provenance is queryable per node (SC3)
expected: Every Computgraph node answers a provenance query — source (tagged | recognized), provider/model (when source=recognized), definitionId, and publishedAt timestamp. A MATCH over the published Frame subgraph returns these properties for each node.
result: [pending]

### 4. ui-v2 shows Computgraph layer distinctly + per-project filter (SC4)
expected: The ui-v2 graph datascape (ui-v2/src/graph + ui-v2/src/screens) shows the Computgraph layer with distinct styling for the new labels (Object/Behavior/Algorithm/Procedure/Pattern/Parameter/Interface, correct casing via buildRings.js), correct orbit/caption placement (Behavior caption shows definitionId per WR-08), and a per-project filter toggle isolating the Computgraph layer for the active project. Hard-refresh (Ctrl+Shift+R) after any design-grammars container rebuild.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

- Phase 36 shipped code-complete (4/4 plans, 36-VERIFICATION.md written) with NO UAT file. All four success criteria need live verification (Neo4j publish + ui-v2 display). Test 1 is the single transitive integration gate for Phases 32/34/35 on the Frame fixture; run as Group 4.5–4.6 of .planning/phases/v9.0-PIPELINE-UAT.md. Prior code-review fixes (WR-08 Behavior caption, WR-09 ComputgraphPublishClient 15s timeout) already closed.
