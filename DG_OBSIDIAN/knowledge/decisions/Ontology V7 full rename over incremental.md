---
tags: [decision, ontology, v7.0]
date: 2026-07-02
---

# Ontology V7 is a full rename of V6, not an incremental patch

## Decision

`DesignGrammar-V6.owl` is fully renamed to `DesignGrammar-V7.owl` to match the notation used in the new `ontology/GH_DesignGrammars.pdf` Grasshopper component schema exactly — layer hubs become `Ontograph`/`Validgraph`/`Computgraph`, `ObjectProperty`→`ObjProperty`, `DatatypeProperty`→`DataProperty`, `ValidationRun`→`Run`, `ObjectState`→`ObjState`, `ReinstatementStatusValue`→`ReStatus`; `DefState` becomes `ParamState`; a new `PropState` class is added.

A **`V6-to-V7-mapping.md`** file records every renamed IRI (old → new) as a recovery-only reference — it is not consumed by any tooling, purely a lookup for humans.

## Why

The ontology (`ontology/*.owl`) has **no runtime consumer** — confirmed by search: no `.owl`/`rdflib`/`owlready` reference exists in any Python/C#/JS runtime file. It's read only by the authoring scripts (`apply_v6_*.py`, `make_docs_v6.py`) that transform it and export markdown docs. Its only real-world usage is the PhD publication series (T1–T4 in `knowledge/publications/`), which cites V6 class/property names directly.

Given zero runtime coupling, matching the ontology 1:1 to the Grasshopper schema's notation removes an entire class of translation bugs (the alternative — keeping V6 canonical names and maintaining a permanent port↔IRI alias table — was rejected as needless indirection for a system with no other consumer to protect). The mapping file exists purely so a published paper's IRI can still be traced forward if someone re-reads it years later.

## Consequences

- V6 stays untouched (`DesignGrammar-V6.owl`, `-standards-`, `-BOT-`, `-Topologic-extension-V6.owl`) — publications keep citing it as-is
- V7 becomes the new canonical ontology consumed by the port↔IRI map (Phase 13 deliverable) and by the Neo4j↔ontology consistency doc
- The DB itself is **not** relabeled to match V7 (see [[Graph schema v3 is the canonical data model]] — v7.0 keeps existing Neo4j labels except the Knowledge→Spec rename); the ontology-to-DB mapping is documented separately rather than forcing full label parity, since Neo4j labels have real runtime cost to rename (n8n prompts, NeoVis config, C# repositories) that the ontology rename does not

## See also

- [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|Session: v7.0 milestone init]]
- [[sessions/2026-06-01 Ontology v6.1 vendor-neutralization|Prior rename: v6.1 vendor-neutralization]]
- [[DCM ComputationGraph as 5th ontology layer]]
