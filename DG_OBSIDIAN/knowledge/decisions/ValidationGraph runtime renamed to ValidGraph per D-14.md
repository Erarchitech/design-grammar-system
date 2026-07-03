---
tags: [decision, phase-14, v7.0, schema-v4, graph-layer, migration]
date: 2026-07-03
status: locked
---

# ValidationGraph runtime renamed to ValidGraph per D-14

## Context

Phase-13 D-01 locked the DesignState layer literal as `graph='ValidGraph'`. But the **shipped runtime** (`data-service/app.py`, `DG/src/DG.Core/Services/ValidationRunsQueryService.cs`, `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs`) already uses `graph='ValidationGraph'` on **1169 live nodes** (ValidationEntity ×1148, ValidationRun ×20, IntegrationConfig ×1, confirmed via live Cypher against the dev Neo4j).

The researcher recommended **Option A** (keep `'ValidationGraph'`, document the ontology↔DB gap — same pattern already used for the `ValidationRun`-vs-`Run` label mismatch documented in REQUIREMENTS Out-of-Scope). The user overrode and chose **Option B**.

## Decision

**Rename the runtime literal from `'ValidationGraph'` to `'ValidGraph'` everywhere** (honoring D-01 literally).

## Scope (6 sub-items, all in Phase 14)

1. **Data migration** — `MATCH (n {graph:'ValidationGraph'}) SET n.graph='ValidGraph'` on 1169 live nodes. Dry-run count first, dev-only guard (`migrations/2026-07-03_designstate_kind_and_validgraph_layer_migration.cypher`).
2. `data-service/app.py:41` — `VALIDATION_GRAPH = "ValidationGraph"` → `"ValidGraph"`.
3. `DG/src/DG.Core/Services/ValidationRunsQueryService.cs:15` — `private const string ValidationGraph = "ValidationGraph"` → `"ValidGraph"`.
4. `DG/tests/DG.Tests/E2E/DesignStateValidationFlowTests.cs` — 5 hardcoded `graph: 'ValidationGraph'` → `'ValidGraph'` (lines 78, 127, 187, 204, 221).
5. Kind-migration layer-move targets `graph='ValidGraph'` (consistent with D-14, per D-09).
6. **Node labels unchanged** — `ValidationRun`/`ValidationEntity`/`IntegrationConfig` labels stay as-is (label renames are out of scope).

## Rationale

User chose consistency with the ontology-facing name (Phase-13 D-01) over the researcher's recommended backward-compatible approach. The cost is a 1169-node data migration folded into a propagation phase, but it prevents a silent graph-partition split in Phase 18 when DesignState writes would target `'ValidGraph'` while Run reads stay at `'ValidationGraph'`.

## Consequences

- **+** Single canonical layer value — no silent partition split risk in Phase 17/18
- **+** Matches the ontology PDF port label `ValidGraph` (port-iri-map-V7.md) exactly
- **−** 1169-node data migration with risk of accidental production execution (mitigated by dry-run + dev-only guard)
- **−** Expands Phase 14 beyond pure mechanical propagation into data-migration territory
- **−** Overrode researcher's recommendation (kept documented for transparency)

## References

- [[../sessions/2026-07-03 Phase 14 discuss - schema v4 propagation decisions|Phase 14 discuss session]]
- [[../sessions/2026-07-03 Phase 14 planning - 7 plans across 3 waves|Phase 14 planning session]]
- [[DesignState persists to ValidGraph not Metagraph|Phase 13 D-01 — DesignState layer placement]]
- [[ontology/port-iri-map-V7.md|V7 port↔IRI map]] — line 25, Validgraph class
