---
tags: [decision, swrl, semantics, violation]
date: 2026-04-05
---

# Violation Rules Invert the Constraint in SWRL Body

## Decision

In the Design Grammar System, violation-type SWRL rules use **inverted conditions** in the body: the body fires when the rule is *broken*, and the head sets a violation flag to `true`.

## Example

**NL**: "Maximum building height is 75 meters"

**SWRL**: `Building(?b) ^ hasHeightM(?b,?h) ^ swrlb:greaterThan(?h,75) -> violatesMaxHeight(?b,true)`

The body checks `greaterThan(?h, 75)` — the violation condition. When it matches, the head asserts the violation.

## Mapping Table

| NL Constraint | Body Builtin (fires on violation) |
|---------------|-----------------------------------|
| "at most X" | `swrlb:greaterThan(?val, X)` |
| "at least X" | `swrlb:lessThan(?val, X)` |
| "equal to X" | `swrlb:notEqual(?val, X)` |

## Rule Separation Principle

Each distinct constraint must be a **separate Rule node** with its own Atom subgraph. Multiple constraints in one sentence (e.g., "at least 2 toilets AND at least 1 kitchen") produce N separate rules. Shared Class/Property nodes are reused via MERGE.

## Related

- [[Graph schema v3 is the canonical data model]]
- [[LLM prompts embed schema constraints instead of fine-tuning]]
- [[SWRL parsing is bespoke regex not vendor OWL library]]
