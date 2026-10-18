---
tags: [debugging, mapping, grasshopper, phase-1303]
date: 2026-10-18
status: fixed, verified by dry run and placement on the open copy
---

# Clean-file mapping noise from union streams, tied outputs and a single-value fallback

On a definition without DG states, the reader cannot follow existing DG wiring. A dry run on `v12-hexagonal-facade-01-auto-mapping.gh` showed that the noise would have doubled or misplaced DG components.

| Symptom | Cause | Fix |
|---|---|---|
| Elements read twice (10 candidate streams) | «All panels» = Panels A + B + C; the «modules» surfaces lie over the 6- and 5-module contours; two Bounding Box outputs | `MappingStreamDedupe`: an exact duplicate (same kind and element bounding boxes) is dropped; a stream that contains ≥ 2 other streams (bounding boxes only) is dropped as their union. Result: 7 streams |
| Facade (bbox F) without a class | a one-letter «F» counts as an abbreviation only when it is the whole name | a calculation output votes for its stream's class: H → hasTotalHeightM, used only by the Facade rule |
| Glass planarity bound to Panels A | PD reads Panels A and B, which are all zero, and the tie went to the first input | measure rows carry `streamOptions` (tied streams); `rule_bindings` picks the tied stream of the rule's class (Panels B) |
| Glass planarity bound to «D» with 1 value | a fallback bound a stream-less output to any class with a single stream | the fallback applies only to outputs without branch-matched streams (`pathStreams`); an LLM stream counts only if the branches follow it |
| PROPERTY STATE count ≠ OBJECT STATE count | one OBJECT STATE per class merged its measured and unmeasured streams | one OBJECT STATE per (class, measured stream); unmeasured streams of a measured class are left out with a note |

**Verification.** All 11 rule bindings match the owner's hand wiring. Placement on the open copy, not saved: 5 OBJECT STATE (125/1/125/25/100) and 11 PROPERTY STATE, each with as many values as its OBJECT STATE has elements.

Related: [[sessions/2026-10-18 Phase 1303 automatic mapping in CONNECTOR with LLM proposal and placement up to VALIDATOR|session]], `DG/src/DG.Core/Mapping/MappingStreamDedupe.cs`, `MappingPlacementPlan.cs`, `data-service/mapping_engine.py`.
