# Phase 19: Deconstruct and Reinstate Components - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 19-deconstruct-and-reinstate-components
**Areas discussed:** REINSTATE target discovery, StateStatus output structure, DECONSTRUCT error contract

---

## REINSTATE Target Discovery

### Question 1: Target discovery mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 'Target' input (Recommended) | Wire PARAMETER STATE's State output here. REINSTATE walks upstream wires from that component to find connected sliders/toggles. Same proven pattern as old REINSTATE. | ✓ |
| Global ParameterId match | No component wiring needed. Match ParameterId (NickName) against ALL sliders/toggles in the document. Simpler UI but fragile — renamed NickNames break silently. | |
| Explicit 'Targets' list input | Users explicitly wire individual slider/toggle references. Most explicit but requires additional wiring work per parameter. | |

**User's choice:** Keep 'Target' input (Recommended)
**Notes:** The wire-traversal approach is proven and explicit — users can see the wire and understand the relationship. The wire IS the target declaration.

### Question 2: Required vs Optional

| Option | Description | Selected |
|--------|-------------|----------|
| Required 'Target' input (Recommended) | Wire PARAMETER STATE's State output here. Clear, discoverable — the user can see the wire and understand the relationship. | ✓ |
| Optional with fallback | Like today — Target is optional, and REINSTATE also tries to find the PARAMETER STATE by walking upstream from the ParamState input. | |

**User's choice:** Required 'Target' input (Recommended)
**Notes:** No fallback complexity. Simpler contract, no ambiguity. The old approach added fallback search logic that rarely activated — users always wired the DesignState input explicitly.

### Question 3: Port-IRI map treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime annotation (Recommended) | Target input is a Grasshopper-internal wiring concern — no ontology concept for "which sliders to write to". Annotate as runtime/DB (no IRI). | ✓ |
| Add to port-IRI map | Add a new entry documenting the Target input as runtime-only. | |

**User's choice:** Runtime annotation (Recommended)
**Notes:** Consistent with how other runtime-only ports are handled (Reinstate trigger, VALIDATOR DataServiceUrl/Report/ValidationRunId). Goal is keeping the port-IRI map focused on ontology-aligned ports.

---

## StateStatus Output Structure

### Question 1: StateStatus list structure

| Option | Description | Selected |
|--------|-------------|----------|
| Index-matched to ParamState (Recommended) | One ReStatus entry for every parameter in the ParamState. Same length, same order. | ✓ |
| Only non-passing statuses | Only emit entries for non-Applied parameters (errors + warnings). Shorter list but loses positional pairing. | |
| Single overall status | A single summary ReStatus for the entire operation. Simpler but loses per-parameter granularity. | |

**User's choice:** Index-matched to ParamState (Recommended)
**Notes:** Follows the index-matched list contract pattern established by METAGRAPH Rules/Objects, VALIDATION GRAPH Run/Status, and VALIDATOR ValidStatus/ObjStates. Downstream can reliably pair Parameters[i] with StateStatus[i].

### Question 2: Parameters output content

| Option | Description | Selected |
|--------|-------------|----------|
| All parameters (Recommended) | Output all parameters from the captured ParamState, regardless of application status. Clean separation of concerns — data vs. status. | ✓ |
| Only applied parameters | Only parameters that passed validation and were written to sliders. Simpler for downstream but loses context. | |
| Raw typed values | Output typed scalars directly (doubles, ints, bools) as GH types instead of wrapped DesignStateParameter objects. | |

**User's choice:** All parameters (Recommended)
**Notes:** Clean separation: Parameters = what was captured, StateStatus = what happened. Downstream can filter by cross-referencing with StateStatus.

### Question 3: Summary Status text output

| Option | Description | Selected |
|--------|-------------|----------|
| Keep summary Status (Recommended) | Keep the summary Status text output as a third output. Ergonomic — architects see "Applied 5 parameters" directly on the component. | ✓ |
| Drop summary Status | Two outputs is cleaner. Downstream can derive summary from StateStatus. | |

**User's choice:** Keep summary Status (Recommended)
**Notes:** The old REINSTATE already does this and it's ergonomic. Architects get instant feedback ("Applied 5 parameters" / "Aborted: 2 blocked") without inspecting lists.

---

## DECONSTRUCT Error Contract

### Question 1: Null/missing input behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Warning + empty outputs (Recommended) | AddRuntimeMessage(Warning) + set all outputs to empty lists + return. Consistent with standard GH component behavior. | ✓ |
| Error + empty outputs | AddRuntimeMessage(Error) + empty outputs. Stronger signal — red bubble. | |
| Silent empty outputs | Just set empty outputs, no message. Silent — clean canvas but users might wonder why downstream gets nothing. | |

**User's choice:** Warning + empty outputs (Recommended)
**Notes:** Standard Grasshopper pattern. Empty list inputs (e.g., DesignState with no ObjStates) are valid and passthrough as empty lists without warning — only null/missing input triggers the warning.

---

## Claude's Discretion

- Exact GUID assignments for DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, and PARAMETER REINSTATE (whether old REINSTATE GUID is kept or replaced — recommended: new GUID, following VALIDATION GRAPH precedent)
- Component icons (DgIcons entries)
- Exact GH_Component layout (RegisterInputParams/RegisterOutputParams) for all 3 components
- Wire-traversal implementation details for Target input
- Deferred write scheduling implementation (ScheduleSolution pattern)
- Error message wording (follows ErrorMessageTemplates pattern)
- Output type choices for Parameters and StateStatus (DesignStateParameter wrapped vs custom goo; ReinstatementStatus enum wrapped vs int/text)
- Whether old REINSTATE file is renamed in-place or replaced with new file

## Deferred Ideas

None — discussion stayed within phase scope.
