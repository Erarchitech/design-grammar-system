# Phase 35 F1 — Recognition output-token truncation, no graceful degradation

## Issue
Cold `POST /computgraph/recognize` on a large untagged canvas (221 untagged nodes out of 236 total) makes the LLM output a proposal array that exceeds the adapter's hardcoded `max_tokens: 4096` cap ([llm_gateway.py:171, 232](../../data-service/llm_gateway.py#L171)). The response is truncated mid-JSON → `bad_json` parsing fails → the bounded retry loop appends corrective feedback and re-attempts, 3 times total. The validator's `too_many_proposals` violation (cg_recognition.py:128) DOES advise "scope to a single procedure_index", but it can only fire *after* valid JSON parses, so a user hitting truncation-before-parse never sees the hint.

## Root cause
LLM response size is not bounded by the prompt's complexity. Large canvases with no anchors cause `_filtered_untagged_node_ids` to return ALL untagged nodes when `procedure_index` is null or empty, exploding the scoped set. The 4096-token cap on the *output* then truncates mid-string.

## Evidence (2026-07-25)
- UrbanBlock: 221 untagged nodes
- `deepseek-chat` → `bad_json` ×3, "Unterminated string starting at: line 1 column 6611 (char 6610)"
- Same call scoped to `procedure_index=12` (which had 10 tagged members) → `valid:true, attempts:1` on first try (output fit the budget)

## Fix suggestion
Detect truncated JSON (unterminated string at end-of-response) and surface the scoping hint directly in the violation, rather than waiting for a full parse + schema validation. Alternatively, increase `max_tokens` or make it configurable per-request (currently hardcoded in the adapter).

## Severity
Medium. Real large-canvas UX gap for users without named anchors. The Frame fixture (34 nodes, highly tagged) is small enough to never hit this. Mitigated by the standard workflow (tag some anchors before recognition, then scope to a procedure).

## Related
[[Phase 35 F2 — Silent full-scope fallback]], [[Phase 35 F4 — Re-preview undo crash]]
