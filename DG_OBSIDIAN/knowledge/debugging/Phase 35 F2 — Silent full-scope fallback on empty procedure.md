# Phase 35 F2 — Silent full-scope fallback when procedure_index is empty

## Issue
`_filtered_untagged_node_ids(procedure_index=N)` ([cg_recognition.py:466-489](../../data-service/cg_recognition.py#L466-L489)) falls back to ALL untagged nodes when the requested procedure has zero members. A caller who explicitly passes `procedure_index=11` believes they've scoped the request and did not, silently widening the job back to the full set. Combined with [[Phase 35 F1]], this becomes a token-truncation explosion.

## Root cause
Lines 476–478:
```python
procedure_ids = _procedure_member_ids(cg_context, procedure_index)
if not procedure_ids:
    return node_ids  # <-- silently fall back to ALL
```

If the requested procedure has no members, the function returns the unfiltered `node_ids` list. No signal to the caller.

## Evidence (2026-07-25)
- UrbanBlock canvas had a tagged Procedure 11 with **0 members**
- `procedure_index=11` → silently returned all 214 untagged nodes
- Only `procedure_index=12` (10 members) produced useful scoping
- The first attempt would have hit [[Phase 35 F1]] truncation, but we didn't re-test to confirm (caught by manual inspection)

## Fix suggestion
Return a distinct signal (either a 422 validation error or an empty result) when the requested procedure exists but has no members, rather than silently widening scope. Caller can then either re-tag the procedure or re-request without scoping.

## Severity
Medium. Edge case (requires a user to tag an empty procedure), but when it happens, masks the real problem (F1 truncation).

## Related
[[Phase 35 F1 — Recognition output-token truncation]], [[Phase 35 F4 — Re-preview undo crash]]
