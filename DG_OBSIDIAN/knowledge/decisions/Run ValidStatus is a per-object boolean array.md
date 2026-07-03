---
tags: [decision, ontology, v7.0, schema]
date: 2026-07-03
---

# Run.ValidStatus is a per-object boolean array, not a single overall flag

## Decision

`Run.ValidStatus` is a **Boolean list** (Neo4j list property on the `Run` node), **one element per `ObjState`** in the validated `DesignState`, **index-matched** to that DesignState's ObjState order.

- No separate `Run.Status` text enum — `VALIDATION GRAPH`'s `Status` output reads back the **same** `ValidStatus` field; the PDF's differing names at VALIDATOR (Boolean) vs VALIDATION GRAPH (text) are treated as one cosmetic naming inconsistency, resolved to the single name `ValidStatus`.
- Overall pass/fail is **derived**, not stored: `AND(ValidStatus)`.
- `Run.SendStatus` stays a **single Boolean** per Run (publish-to-Speckle success) — orthogonal to `ValidStatus`, since publishing is one operation per run, not per object.

## Why

`ontology/GH_DesignGrammars.pdf` shows `ValidStatus` as Boolean at the `VALIDATOR` component but as text at `VALIDATION GRAPH` — flagged as ONTO-04's conflict (a). The originally proposed fix (`Run.ValidStatus` Boolean overall + `Run.Status` text enum, two fields) was reshaped during Phase 13 discussion: the user wants **per-object granularity** instead of a single overall value, matching how validation actually evaluates each object in a DesignState against a rule individually.

A single overall boolean or text enum would collapse per-object detail that both the Grasshopper canvas and the Model Viewer need to show (which specific objects failed, not just "some failed").

## Consequences

- `cypher_template.txt` v4 (Phase 14) declares `Run.ValidStatus` as a list property; no `Run.Status` property
- `VALIDATOR` (Phase 18) outputs and persists `ValidStatus` as an array index-matched to the DesignState's ObjState list it validated
- `VALIDATION GRAPH` (Phase 17) reads `ValidStatus` directly — its `Status` output name from the PDF is unified to `ValidStatus` in the actual component contract
- **Open for Phase 18:** the *population* rule — does `ValidStatus` cover **every** ObjState in the DesignState, or only those matching the rule's target Class? Phase 13 only locks the array **shape** and **index-matching mechanism**; the binding/population semantics belong to VALIDATOR's variable-binding rework (GHVL-04)
- Consumers must zip `ValidStatus` with the DesignState's ObjState list by position — reuses the index-matched list contract already used by OBJECT STATE / DESIGN STATE

## See also

- [[DesignState persists to ValidGraph not Metagraph]] — companion Phase 13 conflict resolution (DesignState layer)
- [[sessions/2026-07-03 Phase 13 discuss - ValidGraph and per-object ValidStatus|Session: Phase 13 discussion]]
- [[Graph schema v3 is the canonical data model]] — superseded by v7.0 schema v4 (this decision is part of that)
