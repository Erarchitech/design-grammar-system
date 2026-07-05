---
tags: [decision, phase-19, v7.0]
date: 2026-07-05
---

# Phase 19: Deconstruct and Reinstate Components — Implementation Decisions

7 decisions captured during `/gsd-discuss-phase 19`. Full context: `19-CONTEXT.md`.

## REINSTATE Target Discovery

- **D-01:** Keep **'Target' input** — wired from PARAMETER STATE's State output. REINSTATE walks upstream wires from that component to discover connected sliders/toggles. Same proven pattern as old REINSTATE.
- **D-02:** Target input is **Required** (not optional). No fallback search from the ParamState input.
- **D-03:** Target input is **runtime/DB** concern (no ontology IRI). Annotated alongside the Reinstate trigger.

## StateStatus & Parameters Outputs

- **D-04:** **StateStatus is index-matched to ParamState.Parameters** — one ReStatus per parameter, same length/order.
- **D-05:** **Parameters output contains ALL parameters** from the captured ParamState (not just applied ones).
- **D-06:** **Keep summary Status** text output as third output ("Applied 5 parameters" / "Aborted: 2 blocked").

## DECONSTRUCT Error Contract

- **D-07:** **Warning + empty outputs** on null/missing input. Standard Grasshopper component pattern.

## Claude's Discretion

GUID assignments, icons, output typing (DesignStateParameter list vs custom goo, ReinstatementStatus enum vs int vs text), file replacement strategy, error message wording.

**Why:** These clarify implementation decisions for DESIGN STATE DECONSTRUCT, OBJECT DECONSTRUCT, and PARAMETER REINSTATE before planning.
**How to apply:** Read `19-CONTEXT.md` before planning Phase 19. All decisions are locked.
