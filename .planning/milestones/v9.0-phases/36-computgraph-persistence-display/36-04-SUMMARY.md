---
phase: 36-computgraph-persistence-display
plan: 04
subsystem: documentation, schema-propagation
tags: [schema-change, computgraph, labels, relationships, dgid, shacl, documentation]
requires: 32.1-07
provides: [cypher_template-computgraph-block, dataset_schema-computgraph-entries, DATABASE-md-computgraph-nodes, dg-shapes-ttl-computgraph-shapes, CLAUDE-md-computgraph-nodes, copilot-instructions-computgraph-sync, README-md-computgraph-section]
affects:
  - cypher_template.txt
  - training/dataset_schema.json
  - spec/DATABASE.md
  - ontology/dg-shapes.ttl
  - CLAUDE.md
  - .github/copilot-instructions.md
  - README.md
  - graph-viewer/config.template.js
tech-stack:
  added: [dgc:Object, dgc:Behavior, dgc:Algorithm, dgc:Procedure, dgc:Pattern, dgc:Parameter, dgc:Interface in dg-shapes.ttl; Computgraph runtime labels/relationships in all surfaces]
  patterns: [document-only-comment-block, additive-table-append, inline-comment-block]
key-files:
  created: []
  modified:
    - cypher_template.txt
    - training/dataset_schema.json
    - spec/DATABASE.md
    - ontology/dg-shapes.ttl
    - CLAUDE.md
    - .github/copilot-instructions.md
    - README.md
decisions:
  - "config.template.js requires no Computgraph update — Phase 36 runtime entities are persisted by data-service, not consumed by the legacy graph-viewer NeoVis config (verified no-op)"
  - "REFERS_TO is documented for both Metagraph (Atom→entity) and Computgraph (Object→Class cross-layer bridge) as separate rows in the Relationships table"
metrics:
  duration: "~15 min"
  tasks: 2
  commits: 2
  files_modified: 7
status: complete
---

# Phase 36 Plan 04: Schema Propagation — Computgraph Labels and Relationships

One-liner: Propagated the 7 Computgraph runtime node labels (Object, Behavior, Algorithm, Procedure, Pattern, Parameter, Interface) and 9 relationship types (HAS_BEHAVIOR, HAS_ALGORITHM, HAS_PROCEDURE, HAS_PATTERN, PATTERN_HOST_TO, HAS_PARAMETER, HAS_INTERFACE, PARAM_LINK, REFERS_TO cross-layer) across 7 of 8 schema-propagation surfaces, fixed the stale `dgId`-on-`:Algorithm` doc bug, and verified config.template.js as a no-op.

## Objective

Complete the CLAUDE.md standing Schema Change Propagation checklist for the 7 new Computgraph node labels and 9 relationship types Phase 36 introduces, so every schema-defining and documentation surface agrees on the labels, properties, relationships, and the exact `graph:'Computgraph'` partition string — and correct the one stale `dgId`-on-`:Algorithm` doc bug along the way.

## Task Results

### Task 1: Schema-defining surfaces — cypher_template, dataset_schema, DATABASE.md, dg-shapes.ttl

**Acceptance:** PASSED

- **cypher_template.txt:** Added a Computgraph runtime document-only block (following the DesignState/Identity-registry precedent) declaring all 7 node labels with properties and merge keys, plus all 9 relationships. Fixed the stale dgId entity list from `(Algorithm, Procedure, Pattern, Parameter, Interface)` to `(Object, Procedure, Pattern, Parameter, Interface)`. No existing MERGE blocks altered.
- **training/dataset_schema.json:** Added `note_computgraph_runtime` with entries for all 7 Computgraph node labels (Object, Behavior, Algorithm, Procedure, Pattern, Parameter, Interface) with full property schemas, plus `ComputgraphRelationships` with all 9 relationship types including the cross-layer `REFERS_TO`. JSON validated (`JSON-OK`).
- **spec/DATABASE.md:** Added 7 Computgraph node sections (Object, Behavior, Algorithm, Procedure, Pattern, Parameter, Interface) with Cypher examples and property tables following the Representation/SharedProperty precedent. Added 9 Computgraph relationships to the Relationships table. Updated the Graph Separation table. Fixed the stale dgId entity list line to list `Object` instead of `Algorithm`.
- **ontology/dg-shapes.ttl:** Added 7 SHACL node shapes (ObjectShape, BehaviorShape, AlgorithmShape, ProcedureShape, PatternShape, ParameterShape, InterfaceShape) with property datatypes, `sh:in` enum constraints for source (tagged|recognized), paramKind (Variable|Constant|Emergent), dataType (Float|Integer|Text|Boolean|Geometry), ifaceType (Input|Output), and `dgsh:howToFix` remediation per the existing style.

**Commits:** `01b8195`

### Task 2: Documentation surfaces — CLAUDE.md, copilot-instructions, README, config.template.js

**Acceptance:** PASSED

- **CLAUDE.md:** Added 7 Computgraph runtime nodes to the Node Labels table (Object, Behavior, Algorithm, Procedure, Pattern, Parameter, Interface) with key properties and display properties. Extended the Relationships line with all 9 Computgraph relationship types. Fixed the dgId entity list from Algorithm to Object.
- **.github/copilot-instructions.md:** Updated the Computgraph graph separation line to include runtime entities. Added 7 Computgraph node labels and 9 relationships to the canonical lists. Fixed the dgId entity list.
- **README.md:** Added Computgraph to the Nodes list. Added Computgraph relationships section. Added Phase 36 runtime description alongside the existing Phase 32.1 identity-registry note.
- **config.template.js:** Verified as a no-op — the file is NeoVis display configuration for the legacy graph-viewer (not the Computgraph publish path), and Phase 36 introduces no new configuration need. Documented in the summary.

**Commits:** `b8e007c`

## Deviations from Plan

None — plan executed exactly as written.

- The `REFERS_TO` relationship was duplicated in the Relationships table (once for Atom→entity, once for Object→Class). This was resolved by keeping both rows with distinct descriptions, as `REFERS_TO` genuinely serves two roles with different source labels and target types.
- `config.template.js` was verified as a no-op per the plan's explicit instruction that Phase 36 introduces no new config need.

## Verification

| Check | Result |
|-------|--------|
| `grep -rl "ComputGraph"` on all 8 files | PASS — no wrong casing |
| Every of the 8 files contains exact `Computgraph` | PASS (7 files with content; config.template.js: 0 — expected no-op) |
| `training/dataset_schema.json` valid JSON | PASS |
| spec/DATABASE.md dgId-entity list = Object/Procedure/Pattern/Parameter/Interface | PASS — Algorithm removed, Behavior absent |
| No modification to `data-service/app.py` or `data-service/dg_context.py` | PASS |

## Self-Check: PASSED

- All 7 files exist and were modified
- 2 commits recorded with correct format (`docs(36-04):...`)
- Property/label/relationship strings use `Computgraph` exact casing everywhere
- The stale dgId-on-Algorithm doc bug is corrected

## Success Criteria

- The Schema Change Propagation checklist is complete for the 7 Computgraph labels + 9 relationships across all 8 named surfaces (CGPD-04 checklist half).
- The `graph:'Computgraph'` partition string is exact and consistent everywhere.
- The stale `dgId`-on-`:Algorithm` documentation bug is corrected.
