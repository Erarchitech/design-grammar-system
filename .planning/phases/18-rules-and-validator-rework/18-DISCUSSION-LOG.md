# Phase 18: Rules and Validator Rework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** 18-rules-and-validator-rework
**Areas discussed:** ValidStatus array contract, VariableBinder redistribution, RULE DECONSTRUCT edge cases, CLASSIFICATOR removal scope

---

## ValidStatus Array Contract

| Option | Description | Selected |
|--------|-------------|----------|
| All ObjStates in DesignState | ValidStatus[i] = Boolean for DesignState.ObjStates[i] — one entry per every ObjState regardless of Class match. Non-matching = false. Simpler index-matched contract. | ✓ |
| Only rule-matching ObjStates | ValidStatus only covers ObjStates whose Class matches the rule's target. Shorter array, no fixed index-matching. | |

### Non-matching ObjState semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude from overall pass | Non-matching ObjStates filtered out before AND. True=passing, False=failing, absent=not applicable. | ✓ |
| Include as false in AND | All ObjStates contribute to overall pass — non-matching treated as false. Stricter but simpler. | |

**User's choice:** All ObjStates with non-matching excluded from overall pass.
**Notes:** ValidStatus array is index-matched to DesignState.ObjStates. Overall pass = AND of only applicable Booleans. This was deferred from Phase 13 and Phase 16 — now resolved.

---

## VariableBinder Redistribution

| Option | Description | Selected |
|--------|-------------|----------|
| New service in DG.Core | DesignStateBindingService in DG.Core.Services — pure logic, testable without GH. Old VariableBinder deleted. | ✓ |
| Inline in VALIDATOR | Binding logic inside ValidatorComponent.SolveInstance. Harder to unit-test. | |
| Extension method on DesignState | DesignState.GetBindingsFor(Rule). Puts SWRL logic in model layer. | |

### Old Classification namespace fate

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entire Classification namespace | VariableBinder, VariableBinding, BindingContext — all deleted. VariableTypeInferrer stays in Parsing. | ✓ |
| Keep VariableBinding model only | Delete binder and context, keep the data class. | |
| Keep as reference, mark obsolete | Keep all files with [Obsolete] + comment. | |

### ObjState matching strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Match by Class IRI | Rule variable REFERS_TO→Class IRI matched against ObjState's Class IRI. Precise — only matching types bind. | ✓ |
| Match by ObjectRef label | Match on user-supplied ObjectRef string. Flexible but fragile (typos). | |
| Match by both | Class IRI first, fall back to ObjectRef label. Most robust, most complex. | |

**User's choice:** New DesignStateBindingService in DG.Core.Services, delete entire Classification namespace, match by Class IRI.
**Notes:** VariableTypeInferrer already in DG.Core.Parsing (Phase 7), stays unchanged. The binding service extracts and replaces VariableBinder.BuildBindings logic.

---

## RULE DECONSTRUCT Edge Cases

| Option | Description | Selected |
|--------|-------------|----------|
| Error with clear message | Unclassified vars → runtime error with What+Where+How-to-fix message. Fail loud. | ✓ |
| Skip silently, output warning | Unclassified vars excluded from both outputs. Lenient — might hide bugs. | |
| Output to third 'Unknown' list | Add output port for unclassified vars. Changes component contract. | |

### Builtin-only variables

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude from both outputs | Builtin vars (swrlb:*) are VALIDATOR's concern. RULE DECONSTRUCT surfaces domain references only. | ✓ |
| Include in Objects | Treat builtin vars as Objects. Pollutes the Objects list. | |
| Output to RuntimeVars list | Third output port. Changes component contract. | |

### VariableTypeInferrer changes

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as-is, use directly | No changes — the Phase 7 priority chain is sufficient. | ✓ |
| Enhance with Builtin detection | Add explicit BuiltinKind. Cleaner but changes a Phase 7 artifact. | |

**User's choice:** Error on unclassified, exclude Builtins, keep VariableTypeInferrer as-is.
**Notes:** Unclassified variables indicate malformed rules — the ingestion pipeline should never produce them. Builtins (math comparisons, string ops) are internal to SWRL evaluation.

---

## CLASSIFICATOR Removal Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full purge | Delete component, entire Classification namespace, ClassificatorState model, tests, all references. One commit. | ✓ |
| Component + namespace only | Keep ClassificatorState if referenced elsewhere. Two commits. | |
| Delete component, deprecate namespace | Remove GH component, mark namespace [Obsolete], delete tests. Remove in Phase 20. | |

**User's choice:** Full purge — everything CLASSIFICATOR-related deleted.
**Notes:** Clean break. Release notes at Phase 20 document re-wiring. No backward compatibility shim needed — v7.0 is a breaking-change milestone.

---

## Claude's Discretion

- Exact method signatures for `DesignStateBindingService` (recommend: `BuildBindings(Rule, DesignState) → IEnumerable<VariableBinding>`)
- Exact error message wording for unclassified variables (follow ErrorMessageTemplates pattern)
- Whether `RuleEvaluator` needs adaptation for the new binding contract
- Exact Cypher for persisting Run with ValidStatus/SendStatus + statePayloadJson v2
- Exact `_project_state_summary` and `useValidationRunsGrouping` adaptation details
- Whether deleted Classification code needs a migration note (recommend: git history sufficient)

## Deferred Ideas

None — discussion stayed within phase scope.
