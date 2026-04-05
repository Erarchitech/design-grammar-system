---
tags: [debugging, n8n, edit-mode, atoms]
date: 2026-04-05
---

# Edit Mode Requires Cleanup of Old Atoms Before Re-Creation

## Problem

When editing an existing rule, simply MERGEing new atoms leaves the old atom subgraph orphaned. This creates duplicate atoms and stale relationships.

## Root Cause

The ingest workflow's default flow MERGE+SET is idempotent for node creation, but doesn't remove atoms that should no longer exist (e.g., when a rule's structure changes).

## Solution

The "Prepare Graph Payload" node in the ingest workflow detects edit mode and generates **cleanup statements** before the new Cypher:

1. **Match the existing rule** by `Rule_Id`
2. **Delete old atoms**: `MATCH (r:Rule {Rule_Id:$id})-[:HAS_BODY|HAS_HEAD]->(a:Atom) DETACH DELETE a`
3. **Clean orphaned Vars/Literals** (post-processing)
4. **Create new atom subgraph** with updated thresholds/structure

## Edit Mode Detection

Keywords: `edit`, `update`, `change`, `modify`, `set`, `increase`, `decrease`  
Rule_Id extraction: explicit mention in prompt, or keyword scoring against existing rules.

## Property Reuse on Edit

When editing, the prompt instructs the LLM to:
- Preserve the same `DatatypeProperty` IRI and `SWRL_label`
- Only change `Literal.lex` values for numeric threshold changes

## Related

- [[n8n orchestrates LLM-powered rule ingestion and graph queries]]
- [[Cypher MERGE idempotent node creation pattern]]
- [[Graph schema v3 is the canonical data model]]
