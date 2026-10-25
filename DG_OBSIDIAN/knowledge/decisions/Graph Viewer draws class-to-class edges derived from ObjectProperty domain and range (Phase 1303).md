---
tags: [decision, phase-1303, graph-viewer, schema]
date: 2026-10-25
---

# Graph Viewer draws class-to-class edges derived from ObjectProperty domain and range

## Context

After ingest of the multi-participant rule the Graph Viewer showed the ObjectProperty `hostedBy` with a single `REFERS_TO` edge (from the atom). The owner expected `Opening —hostedBy→ Slab`. In Neo4j the relation is only the node properties `domain: ex:Opening`, `range: ex:Slab`; the OntoGraph is a flat vocabulary (`spec/LPG-OWL-MAPPING.md`: no `DOMAIN`, `RANGE`, `SUBCLASS_OF`).

## Decision (owner, 2026-10-25)

The viewer renders a derived edge from the `domain` and `range` properties of an ObjectProperty. Nothing is written to Neo4j and the schema does not change.

## Why real edges were rejected

Code reading showed no consumer needs them: mapping uses `ASSIGNS_ROLE`; calculators take participants and relations from rule atoms (`property_scripts.py`) and write their own `READS_CLASS`; the C# evaluator treats `ObjectPropertyAtom` as unsupported and only reads `iri` and the predicate kind; the canvas reads rules through atoms and `REFERS_TO`. `domain`/`range` are read only by `dg_context.py` and the LLM prompt in `dg_knowledge.py`.

Costs of stored edges: contradicts the flat-vocabulary rule (a domain/range axiom would infer class membership), second source of truth, rule deletion would need to count class edges (`orphanedOntology` in `app.py`), new relationship types in `cypher_allowlist.py` `WRITE_REL_TYPES`, schema propagation over `cypher_template.txt`, `dataset_schema.json`, n8n prompts, `DATABASE.md`, `LPG-OWL-MAPPING.md`, `dg-shapes.ttl`, and the repeatability cassettes would need re-recording.

## Consequences

Plan 1303-24 item: derived-edge rendering in `ui-v2/src/graph`, with its own label (relation name) so it is not mistaken for a stored relationship.

## Related

[[Multi-participant rules keep one subject and assert the other classes as context (Phase 1303, D-61 to D-65)]], [[sessions/2026-10-25 Phase 1303 live acceptance of 18 and 23 — stack rolled to f0e27a1, acts 1-4, findings]]
