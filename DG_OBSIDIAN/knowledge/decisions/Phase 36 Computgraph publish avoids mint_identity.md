---
tags: [decision, computgraph, publish, dg-id]
date: 2026-07-19
---

# Phase 36 Computgraph publish avoids mint_identity

**Status:** Locked (CGPD-01/02/03)

## Decision

`publish_structure()` in `computgraph_publish.py` computes dgId server-side via `dg_identity.compute_dg_id(project, definition_id, cg_id)` and **never calls `mint_identity()`**.

## Why

`mint_identity()` issues a label-less anchor MERGE: `MERGE (e {cgId:$cgId, definitionId:$definitionId, project:$project})`. But the publish endpoint's own typed MERGE is `MERGE (n:Pattern {cgId:$cgId, definitionId:$definitionId, project:$project})`. Neo4j MERGE matches on **label + properties together**, so the labeled `Pattern` MERGE and the label-less `mint_identity()` anchor MERGE never coincide — creating a **silent duplicate orphan node** on every publish.

## How to Apply

- Always import `compute_dg_id` from `dg_identity` — never import `mint_identity`.
- Algorithm and Behavior have no cgId/dgId per DGID-01 scope (Behavior uses `{definitionId, project}`; Algorithm uses `{algIndex, definitionId, project}`).
- The property value `dgId` is recomputed server-side on every publish — the client-stamped dgId in the envelope is NOT trusted (the ui-v2 detail panel exposes an inline-edit path over dgId).

## Related

- [[debugging/Phase 36 schema doc bugs — HAS_INTERFACE PARAM_LINK Algorithm merge key]]
