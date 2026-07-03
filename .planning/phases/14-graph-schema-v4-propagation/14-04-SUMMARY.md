---
phase: 14-graph-schema-v4-propagation
plan: 04
subsystem: n8n-workflows
tags: [n8n, v4, prompts, rules-ingest, graph-query, SCHM-09, SCHM-10]
requires: [14-01-cypher-template, 14-03-test-fixtures]
provides: [v4-ingest-prompt, v4-query-prompt]
affects: [n8n-workflows, rules-ingest-pipeline, graph-query-pipeline]
tech-stack:
  added: []
  patterns:
    - "coalesce(newProp, oldProp, default) for backward-compat reads in all read-side Cypher"
key-files:
  created: []
  modified:
    - n8n/workflows/rules-to-metagraph.json
    - n8n/workflows/graph-query-mcp.json
decisions: []
status: complete
---

# Phase 14 Plan 04: n8n Workflow Prompt v4 Propagation

**One-liner:** Update both n8n workflow prompts (rules-to-metagraph ingest and graph-query-mcp query) to the v4 schema — SWRL, RuleName, RuleDescription, no DesignState in ingest, coalesce backward-compat — with a paused human-verify gate for Docker re-import and live smoke testing.

## Task Summary

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Update rules-to-metagraph.json prompts to v4 (SCHM-09) | Done | `80b682c` |
| 2 | Update graph-query-mcp.json Build Cypher Prompt to v4 (SCHM-10) | Done | `708c6f9` |
| 3 | Re-import both workflows and run the live SC#2/SC#3 smoke | **CHECKPOINT** | — |

## Task Details

### Task 1: rules-to-metagraph.json v4 (SCHM-09)

Four edits applied to three nodes:

**Build LLM Prompt (Function node):**
- Bumped `SCHEMA CONSTRAINTS (v3)` to `(v4)`
- Removed `DesignState` from the allowed-node-labels list (D-03)
- Removed the `'- DesignState key: StateId + project. Props: kind (DefState|ObjectState).'` bullet entirely
- Changed the embedded few-shot `SET r.text = ...` to `SET r.SWRL = ...` to mirror 14-01's v4 template

**Fetch Existing Entities (HTTP node):**
- Changed `coalesce(r.text, '') AS text` to `coalesce(r.SWRL, r.text, '') AS text` for backward-compat with the 5 live v3 Rule nodes that only have `r.text`

**Annotate Graph Props (HTTP node):**
- Added `r.RuleDescription = $description` alongside the existing `r.description` backfill — new rules get both lowercase and PascalCase description properties populated

### Task 2: graph-query-mcp.json v4 (SCHM-10)

Eleven edits applied to the Build Cypher Prompt and Parse Cypher nodes:

**Build Cypher Prompt (Function node):**
- `Data model (v3 schema)` to `(v4 schema)`
- Rule properties: `text (SWRL expression), kind, title` to `SWRL (SWRL expression), kind, RuleName, RuleDescription`
- `Rule.text` to `Rule.SWRL` in the numeric-constraints line
- `Key property names (v3)` to `(v4)`
- Added backward-compat guidance: `coalesce(r.SWRL, r.text)` for SWRL body and `coalesce(r.RuleName, r.title)` for display name
- Guidance: `query Rule.text` to `query coalesce(r.SWRL, r.text)`
- Guidance: `toLower(r.text)` to `toLower(coalesce(r.SWRL, r.text, ''))`
- List-all guidance: `r.Rule_Id, r.text, r.kind` to `r.Rule_Id, coalesce(r.SWRL, r.text, '') AS swrl, r.kind`
- Both Example lines: updated `toLower(r.text)` and `r.text AS text` to coalesce forms

**Parse Cypher (Function node) [Deviation R2]:**
- Updated the listAll fallback Cypher to use `coalesce(r.SWRL, r.text, '') AS text` instead of bare `r.text AS text`

### Task 3: Checkpoint

Not executed — requires human verification of n8n re-import and live smoke test.

## Deviations from Plan

### Rule 2 - Missing critical functionality

**1. Parse Cypher hardcoded `r.text` in listAll fallback**
- **Found during:** Task 2 execution
- **Issue:** The Parse Cypher node's listAll fallback (`if (listAll) ...`) overrides the LLM-generated Cypher with a hardcoded version using `r.text AS text` — this would silently defeat the v4 prompt change for list-all rule queries, returning no data from newly-ingested v4 rules that only have `r.SWRL` set.
- **Fix:** Updated the listAll fallback to `coalesce(r.SWRL, r.text, '') AS text` — same backward-compat pattern used everywhere else.
- **Files modified:** `n8n/workflows/graph-query-mcp.json`
- **Commit:** `708c6f9`

## Verification Checks

| Check | Result |
|-------|--------|
| rules-to-metagraph.json has `SET r.SWRL` | PASS |
| rules-to-metagraph.json has `coalesce(r.SWRL, r.text` | PASS |
| rules-to-metagraph.json has `RuleDescription` | PASS |
| rules-to-metagraph.json has `SCHEMA CONSTRAINTS (v4)` | PASS |
| rules-to-metagraph.json no `DesignState key` bullet | PASS |
| rules-to-metagraph.json no `Literal, DesignState` in allowed list | PASS |
| graph-query-mcp.json has `r.SWRL` | PASS |
| graph-query-mcp.json has `v4` in data model | PASS |
| All bare `r.text` references in graph-query-mcp.json are inside `coalesce(r.SWRL, r.text, ...)` | PASS |

## Known Stubs

None.

## Threat Flags

None — only prompt-text edits in n8n workflow JSON files; no new network endpoints, auth paths, or file access patterns introduced.

## Next

Proceed to Task 3: re-import both workflows into n8n, warm Ollama, and run live smoke tests per the checkpoint instructions.
