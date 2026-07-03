---
tags: [decision, ontology, v7.0, schema]
date: 2026-07-03
---

# DesignState persists to ValidGraph, not Metagraph

## Decision

A `DesignState` node's Neo4j `graph` tag moves from **`Metagraph`** (v3 `cypher_template.txt` behavior) to **`ValidGraph`** in v7.0.

- Written **only by VALIDATOR on publish**, `MERGE`'d by `StateId + project` (dedup across runs).
- **Cardinality: one DesignState ↔ many Runs.** The same DesignState (same `StateId`) validated against different rules produces multiple Run nodes, all linked to the single shared DesignState.
- **No-orphan invariant:** a DesignState exists in ValidGraph only when **≥1 Run is linked to it** — a direct consequence of the write path being Validator-only.

## Why

`ontology/GH_DesignGrammars.pdf`'s 14-component schema has two statements about DesignState that appear to conflict:

1. The `VALIDATION GRAPH` component reads `Run / Status / DesignState` from the **ValidGraph** handle (via `GRAPH DECONSTRUCT`).
2. The PDF text says *"New Design State can only pass to Metagraph through Validator."*

The current runtime (`cypher_template.txt` lines 49-50, 113-116) stores DesignState with `graph='Metagraph'` — matching statement 2 but not statement 1.

Resolution: the **destination** in statement 2 is corrected from Metagraph to ValidGraph (DesignState is run/validation data, not rule/spec data — it belongs with `Run`, not with `Rule`/`Atom`/`Var`). The **constraint** in statement 2 — *only through Validator* — is preserved exactly: there is no direct-insert path for DesignState; it only ever arrives as a side effect of a Validator publish.

## Consequences

- `cypher_template.txt` v4 (Phase 14) declares DesignState with `graph='ValidGraph'`
- `VALIDATION GRAPH` (Phase 17) reads DesignState from the ValidGraph handle — matches PDF component wiring exactly, no handle-crossing needed
- `VALIDATOR` persistence (Phase 18) must link every published Run to its DesignState (relationship type/direction left to Phase 14 cypher design)
- A migration re-tags existing `DesignState {graph:'Metagraph'}` nodes to `graph:'ValidGraph'` — folds into the SCHM-13 kind-migration script (Phase 14)
- Because one DesignState can serve many Runs, `VALIDATION GRAPH`'s DesignState output for a given Run lookup may return the same DesignState across multiple Run rows — expected, not a duplicate-data bug

## See also

- [[Run ValidStatus is a per-object boolean array]] — companion Phase 13 conflict resolution (Run status model)
- [[sessions/2026-07-03 Phase 13 discuss - ValidGraph and per-object ValidStatus|Session: Phase 13 discussion]]
- [[sessions/2026-07-02 v7.0 milestone init from GH_DesignGrammars schema|Session: v7.0 milestone init]]
- [[Graph schema v3 is the canonical data model]] — superseded by v7.0 schema v4 (this decision is part of that)
