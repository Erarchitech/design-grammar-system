---
tags: [debugging, rules, cypher, neo4j, stand]
date: 2026-10-29
status: fixed in 993b709 (stand deployment pending owner authorization)
---

# Rule delete kept a rule whose arguments were all shared and still answered deleted

## Symptom

- The owner could not delete the rules of `isolation-check-a` in the interface.
- A bulk delete answered `deleted` for all five rules, but three of them were still in Neo4j.

## Root cause

The `delete_rule` statement picked orphan arguments like this:

```
UNWIND (CASE WHEN args = [] THEN [null] ELSE args END) AS arg
WITH r, atoms, refs, arg WHERE arg IS NULL OR NOT EXISTS { ...another rule uses arg... }
WITH r, atoms, refs, collect(arg) AS orphans
FOREACH ... DETACH DELETE r
```

- When every Var/Literal of the rule (`?o`, `?b`, `?n`, `0`) was also used by another rule, the WHERE dropped every
  row.
- The grouped `collect` over zero rows returns zero rows, so nothing after it ran.
- The route still answered `deleted`, because it reports from the preview, not from the write.
- Rules of one project usually share variable names, so this hits nearly every rule except the last one.

## Fix

- `993b709`: the orphan pick is a `CASE WHEN arg IS NOT NULL AND NOT EXISTS {...} THEN arg END AS orphan` inside the
  row, followed by `collect(orphan)`, which skips nulls. The rule's row always survives.
- Checked on the stand's Neo4j in a rolled-back transaction: R1 and its 5 atoms were deleted, shared arguments kept.
- Test: `test_rule_deletion.py::test_a_rule_whose_args_are_all_shared_is_still_deleted`.

## Lesson

A filtering `WHERE` before an aggregation can silently remove the row a later write depends on. Use a conditional
expression plus `collect`, which skips nulls. And never report a write from the preview alone.
