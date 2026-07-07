---
phase: 14-graph-schema-v4-propagation
plan: 01
subsystem: database
tags: [neo4j, cypher, schema, dataset, v4, swrl]
requires:
  - phase: 13-ontology-v7-and-contract-investigation
    provides: V7 IRI names (SWRL/RuleName/RuleDescription), D-01..D-10 locked decisions
provides:
  - cypher_template.txt v4.0 (canonical schema contract for LLM prompts)
  - training/dataset_schema.json v4.0 (mirrors template 1:1)
affects:
  - 14-02 (NeoVis config + index.html Cypher)
  - 14-03 (C# coalesce patch + smoke harness)
  - 14-04 (n8n ingest/query prompt v4)
  - 14-07 (v4 cypher reference + test fixtures)

tech-stack:
  added: []
  patterns:
    - Document-only schema reference for VALIDATOR-owned nodes (DesignState/Run) outside emitted CYPHER TEMPLATE BLOCK
    - PascalCase Rule property names matching ontology IRIs (D-05)

key-files:
  modified:
    - cypher_template.txt (v3.1 -> v4.0)
    - training/dataset_schema.json (v3.1 -> v4.0)

key-decisions:
  - "Rule properties renamed: text->SWRL, title->RuleName, added RuleDescription (optional) — PascalCase per D-05"
  - "DesignState MERGE block (//2b) removed from emitted CYPHER TEMPLATE BLOCK per D-03"
  - "DesignState/Run documented as document-only reference with graph='ValidGraph' (D-14), three kinds {ObjState,ParamState,PropState}, Run ValidStatus/SendStatus (no Status text field)"
  - "Version bumped from v3.1 to v4.0 in both files"

requirements-completed: [SCHM-07, SCHM-08]

duration: 3min
completed: 2026-07-03
status: complete
---

# Phase 14 Plan 01: v4 Schema Contract Summary

**Rewrote cypher_template.txt and training/dataset_schema.json from v3.1 to v4.0 — Rule props renamed to SWRL/RuleName/RuleDescription (PascalCase), DesignState MERGE block removed, Run/DesignState moved to document-only reference section with no Status text field.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-03T10:09:10Z
- **Completed:** 2026-07-03T10:12:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `cypher_template.txt` rewritten to v4: header version, Rule props (SWRL/RuleName/RuleDescription), removed DesignState MERGE block (//2b), added document-only DesignState/Run reference with ValidGraph layer placement, added quality check for SWRL property name
- `training/dataset_schema.json` mirrored to v4: rule_node.props renamed, DesignState removed from nodes[] and added as schema_reference with kinds + Run props, metadata.version bumped to v4.0
- Both files agree 1:1 on Rule props and state kinds (SCHM-08 parity)
- No remaining `r.text`/`r.title`/`SET r.text` in the emitted CYPHER TEMPLATE BLOCK
- No `DefState`/`ObjectState` kind values remain
- SEMANTIC MAPPING, RULE SEPARATION, IDENTIFIERS prose sections untouched (no renamed tokens)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite cypher_template.txt to v4** - `e532cb6` (feat)
2. **Task 2: Mirror training/dataset_schema.json to v4** - `a75dc4d` (feat)

## Files Created/Modified

- `cypher_template.txt` - Rewritten to v4.0: header, Rule props, document-only DesignState/Run reference, removed //2b block, added SWRL quality check
- `training/dataset_schema.json` - Mirrored to v4.0: rule_node.props, removed DesignState from nodes[], added schema_reference, version bump

## Decisions Made

- **PascalCase Rule properties (D-05):** `SWRL`, `RuleName`, `RuleDescription` match `dgm:SWRL`/`dgm:RuleName`/`dgm:RuleDescription` ontology IRIs exactly. Neo4j properties are case-sensitive.
- **Document-only Run/DesignState (D-03):** DesignState MERGE block removed from the emitted CYPHER TEMPLATE BLOCK. These nodes are written by VALIDATOR-on-publish, not by LLM ingest.
- **graph='ValidGraph' (D-14):** The document-only section references `graph='ValidGraph'` per the user's chosen Option B (rename runtime literal from ValidationGraph to ValidGraph).
- **Many-Runs-to-one-DesignState:** Run->DesignState relationship typed as `(:Run)-[:VALIDATES]->(:DesignState)`.
- **No Status text field (D-01/D-02):** Run has only ValidStatus (Boolean list) and SendStatus (single Boolean). Overall pass = AND(ValidStatus), derived at read time. The ROADMAP SC#1 and REQUIREMENTS SCHM-07 mention of "Status text" is stale.

## Deviations from Plan

None - plan executed exactly as written. Both files match the RESEARCH.md Artifact 1 and 2 targets. All automated verifications pass.

## Issues Encountered

- Trailing comma in `dataset_schema.json` after removing DesignState from `nodes[]` — fixed by removing the comma from the former second-to-last array entry (now the last entry). Validated JSON parses correctly.

## Stub Tracking

No stubs identified — both files are complete schema contract definitions with no placeholder values, empty defaults, or "coming soon" text.

## Threat Surface Scan

No new threat surface introduced — this plan edited two text/schema-contract files only. No new network endpoints, auth paths, or schema changes at trust boundaries.

## Next Phase Readiness

- `cypher_template.txt` v4.0 and `dataset_schema.json` v4.0 are now the canonical schema contract
- Ready for 14-02 (NeoVis config + index.html Cypher) and 14-04 (n8n prompt mirroring) which copy from these two files
- Ready for 14-07 (v4 cypher reference examples + test fixtures) which derive from the template

---
*Phase: 14-graph-schema-v4-propagation*
*Completed: 2026-07-03*
