---
tags: [decision, ontology, dcm, architecture]
date: 2026-05-30
---

# DCM ComputationGraph as 5th ontology layer

## Context

Need to extend DG ontology to cover parametric design definitions in Grasshopper for future bidirectional translation (design grammars ↔ GH definitions). ERD diagram (04_MAPPING) shows DCM entities mapped to GH components.

## Decision

Add a 5th graph layer `dgc:ComputationGraph` to the core ontology (DesignGrammar.owl v5.0) based on the FBS framework (Gero 1990):
- **Function** — design intent (what rules enforce)
- **Behavior** — computational process (GH algorithm)
- **Structure** — physical output (geometry/topology)

Algorithm hierarchy: Algorithm → Procedure → Pattern (maps to GH Definition → Cluster → Component)

## Alternatives considered

1. **Separate OWL file for DCM** — rejected; ComputationGraph should be a first-class layer in the core ontology to enable cross-layer bridges (Atom → Parameter) without circular imports.
2. **Extend existing Metagraph** — rejected; DCM is semantically distinct from SWRL rule structure. Only RuleSet and Reasoner belong in Metagraph (they relate to rule evaluation, not parametric design).
3. **Reify BODY/HEAD as classes** — rejected; existing `dgm:hasBody`/`dgm:hasHead` properties already model the Rule→Atom relationship correctly. Adding classes would create redundancy.

## Consequences

- GraphLayer enum grows from 4 to 5 members (owl:oneOf updated)
- No impact on current runtime (purely conceptual/additive)
- Cross-layer bridge `dgc:attributeOf` connects SWRL atoms to GH parameters
- Extension files follow `DesignGrammar-*-extension.owl` naming pattern
- BOT and Topologic vocabularies aligned via separate extension files (not in core)
