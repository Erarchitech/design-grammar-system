---
tags: [decision]
date: 2026-07-04
---

# Phase 18: Rules and Validator Rework — Design Decisions

## Context

Phase 18 replaces the CLASSIFICATOR-driven validation pipeline with DesignState-driven evaluation. Four gray areas were discussed: ValidStatus array contract, VariableBinder redistribution, RULE DECONSTRUCT edge cases, and CLASSIFICATOR removal scope.

## Decisions

### D-01: ValidStatus per-every-ObjState
ValidStatus[i] = Boolean for **every** ObjState in DesignState, index-matched. Non-matching ObjStates get `false` but are **excluded** from the overall AND pass. True=passing, False=failing, absent=not applicable.

### D-02: DesignStateBindingService
New `DesignStateBindingService` in `DG.Core.Services` replaces `VariableBinder.BuildBindings`. Pure logic, testable without GH SDK.

### D-03: Match ObjStates by Class IRI
The binding service matches ObjStates to rule Object variables by Class IRI (from METAGRAPH Objects output), not by user-supplied ObjectRef label.

### D-04: Delete entire DG.Core.Classification namespace
VariableBinder, VariableBinding, BindingContext — full purge. VariableTypeInferrer stays in DG.Core.Parsing (Phase 7, unchanged).

### D-05: RULE DECONSTRUCT error on unclassified
Variables with no REFERS_TO → runtime error (What+Where+How-to-fix). Builtin-only vars excluded from both outputs.

### D-06: CLASSIFICATOR full purge
Delete component + Classification namespace + ClassificatorState model + tests + all references. One clean commit.

**Why:** Clean break from the old pipeline. v7.0 is a breaking-change milestone — no backward compat shim needed.

**How to apply:** Planner reads CONTEXT.md for full details; the VariableBinder.BuildBindings code must be studied before creating DesignStateBindingService.
