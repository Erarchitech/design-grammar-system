---
tags: [bug, shacl, phase-823, validation, confirmed]
date: 2026-07-12
status: unverified
severity: high
---

# CR-01: `_mint_run_individual` truthy check causes false-positive SHACL violations on empty ValidStatus

## Description

`dg-reasoner/valid_graph_export.py:_mint_run_individual` (line ~127) uses a truthy check (`if valid_status:`) for the `ValidStatus` list instead of `is not None`:

```python
valid_status = row.get("validStatus")
if valid_status:                      # <-- truthy check (BUG)
    bool_literals = [RDFLiteral(bool(v), datatype=XSD.boolean) for v in valid_status]
    graph.add((run_iri, DGV.validStatus, make_argument_list(graph, bool_literals)))
```

The adjacent `sendStatus` correctly uses `is not None` (so `False` gets a triple).

## Impact

A legitimately empty `ValidStatus == []` (produced when a DesignState has zero ObjStates — a supported, already-shipped scenario in `ValidatorComponent.cs`, line 87-98) is treated identically to `None`/absent. No `dgv:validStatus` triple is emitted.

This trips `ontology/dg-shapes.ttl`'s `dgsh:RunStatusShape_valid` (`sh:minCount 1` on `dgv:validStatus`, `sh:severity sh:Violation`) — **false-positive SHACL Violation** surfaced through the entire pipeline into the SHACL Data Integrity UI panel on the Model screen, for runs that did nothing wrong.

## Fix

```python
valid_status = row.get("validStatus")
if valid_status is not None:
    bool_literals = [RDFLiteral(bool(v), datatype=XSD.boolean) for v in valid_status]
    graph.add((run_iri, DGV.validStatus, make_argument_list(graph, bool_literals)))
```

Add a regression test with `"validStatus": []` asserting:
1. `dgv:validStatus` triple IS emitted (as `RDF.nil`)
2. `run_shacl` does NOT flag this run under `RunStatusShape_valid`

## Evidence

- Code review CR-01 in `.planning/phases/823-shacl-validation-layer/823-REVIEW.md`
- Test gap: `test_validgraph_export.py` covers `[true, false]` and all-`None` "missing row" case but NOT `[]`
- No test in `test_shacl_report.py` exercises the empty-list → no-violation path

## How to reproduce

1. Publish a validation run whose DesignState has zero ObjStates (e.g., a parameter-only rule)
2. View the run in the Model screen
3. "SHACL Data Integrity" panel shows "1 Violation: A validation Run is missing its ValidStatus list"

## Why it wasn't caught

- The ValidGraph ABox exporter tests use a fixture with `"validStatus": [true, false]` — never the empty-list boundary
- The commit that shipped the exporter (`d51558f`) predated the SHACL shapes — no integration test existed at that point

## Related notes

- [[Phase 823 SHACL validation layer design decisions#D-823-08|D-823-08: validStatus truthy check]]
- [[sessions/2026-07-12 Phase 823 SHACL Validation Layer execution]]

## Resolution

**Status:** Unverified — fix pending
**Assigned to:** next bug-fix or gap-closure phase
