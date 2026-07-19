---
tags: [debugging, phase-36, critical, data-loss, ui]
date: 2026-07-19
title: Phase 36 CR-02 — Property truncation inline edit data loss
severity: Critical
status: fixed
---

# CR-02 — Property Truncation Data Loss on Inline Edit

## Root Cause

`ui-v2/src/screens/GraphScreen.jsx:690` truncates long property values to 200 chars for display:

```jsx
// Display layer
const displayValue = value.length > 200 ? value.substring(0, 200) + "…" : value;
```

But `PropertiesTable.jsx` (click ✎ handler) reads that **truncated** string directly:

```jsx
// Inline editor draft initialization
const draftValue = displayValue;  // BUG: Uses truncated value!
```

When user clicks Save, the truncated value is written back to Neo4j via `updateNodeProp()`, silently destroying the original data.

## Impact

**Any user editing a long property (e.g. Algorithm.contextJson > 200 chars) loses data.**

The truncation was specifically added (commit ee907c9) to improve display of large JSON blobs, but the implementation created a data-corruption path. The exact property the truncation targets (contextJson) is most vulnerable.

## Example Scenario

1. User views Algorithm node with 2KB contextJson
2. UI displays: "{ "metadata": { "source": "…" (truncated at 200 chars)
3. User clicks ✎ to edit
4. PropertiesTable opens with truncated 200-char string
5. User clicks Enter to confirm (no actual changes)
6. `updateNodeProp()` writes 200-char string back to Neo4j
7. Original 2KB JSON is now gone

## Fix

Introduced `rawValue` field that threads the untruncated source through to the inline editor:

**GraphScreen.jsx:**
```jsx
const rawValue = value;  // Keep original
const displayValue = value.length > 200 ? value.substring(0, 200) + "…" : value;
return <PropertiesTable ... rawValue={rawValue} displayValue={displayValue} />;
```

**PropertiesTable.jsx:**
```jsx
// Inline editor now drafts from untruncated source
const draftValue = rawValue || displayValue;
```

**Commit:** `bbf0127` — fix(36): CR-02 PropertiesTable inline editor truncation data corruption

## Prevention

- Display layer transformations (truncation, formatting) must never feed directly into edit operations
- Always preserve a canonical `rawValue` when displaying transformed versions
- Add snapshot tests for inline-edit round-trips (display → edit → save cycle)

## Related

- [[debugging/Phase 36 publish wire contract mismatch|CR-01 wire contract mismatch (paired critical issue)]]
- Commit ee907c9 (truncation feature) should have included this fix from the start

---

## Lessons

1. **Separation of concerns:** Display formatting should be orthogonal to data transport
2. **Canonical source:** Always preserve unmodified source when transforming for display
3. **Edit path testing:** Manual smoke test of inline edits is essential — unit tests of `updateNodeProp()` won't catch this
