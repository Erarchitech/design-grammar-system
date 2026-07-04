---
tags: [session, planning, phase-17]
date: 2026-07-04
phase: 17
---

# Phase 17 Planning — 4 plans, 3 iterations, 0 blockers

## Summary

Planned Phase 17 "Graph Access Components" with research → plan → check → revision loop (3 iterations). Final state: 0 blockers, 2 advisory warnings.

## Plan Structure

| Plan | Wave | Tasks | Files | Requirements |
|------|------|-------|-------|-------------|
| 17-01 | 1 | 3 | 22 | GHGA-01, GHGA-02 |
| 17-02 | 2 | 3 | 4 | GHGA-03 |
| 17-03 | 2 | 3 | 4 | GHGA-04 |
| 17-04 | 2 | 4 | 6 | GHGA-05 |

**Wave 1:** Foundation — 4 handle types (MetagraphHandle, OntographHandle, ValidGraphHandle, SpecGraphHandle), 2 ontology models (OntologyClass, OntologyProperty), icons, error messages, CONNECTOR update, GRAPH DECONSTRUCT component.

**Wave 2 (parallel):** METAGRAPH extension (IRuleRepository.GetObjectsAsync + Objects output), ONTOGRAPH (IOntoGraphRepository + component), VALIDATION GRAPH (IValidGraphRepository + component + VALIDATION RUNS removal).

## Revision History

| Iteration | Blockers | Warnings | Action |
|-----------|----------|----------|--------|
| 1 | 2 | 4 | RESEARCH.md (RESOLVED) markers, VALIDATION.md created, 4 planner warnings addressed |
| 2 | 1 | 2 | VSTest `OR`→`|` filter fix |
| 3 | 0 | 2 | Accepted — warnings are advisory only |

## Key Decisions Embedded in Plans

- **D-01:** Individual handle types per graph layer — type-safe Grasshopper wires
- **D-02:** METAGRAPH Objects via direct REFERS_TO→Class Cypher query (not VariableTypeInferrer)
- **D-03:** Run↔Status 1:1 paired index-matched lists
- **D-04:** DesignState deduplicated by StateId (DistinctBy)
- **D-05:** Status[i] = IReadOnlyList\<bool\> per-ObjState
- **D-06:** Per-layer repository + interface (IOntoGraphRepository, IValidGraphRepository)

## Advisory Warnings (accepted)

1. **GHGA-03 "index-matched" wording** — Requirement says "index-matched lists" but D-02 DISTINCT dedup makes positional pairing impossible. Plans deliver independently stable lists joinable by IRI.
2. **OntologyClass public wrapper** — Plan 17-02 references `DG.OntologyClass` in PublicTypes.cs; Plan 17-01 only adds handle type wrappers. Inline corrective note exists in 17-02.

## Artifacts

- [[../.planning/phases/17-graph-access-components/17-RESEARCH.md|RESEARCH.md]] — Technical research
- [[../.planning/phases/17-graph-access-components/17-VALIDATION.md|VALIDATION.md]] — Nyquist validation strategy
- [[../.planning/phases/17-graph-access-components/17-01-PLAN.md|17-01-PLAN.md]] — Foundation
- [[../.planning/phases/17-graph-access-components/17-02-PLAN.md|17-02-PLAN.md]] — METAGRAPH
- [[../.planning/phases/17-graph-access-components/17-03-PLAN.md|17-03-PLAN.md]] — ONTOGRAPH
- [[../.planning/phases/17-graph-access-components/17-04-PLAN.md|17-04-PLAN.md]] — VALIDATION GRAPH

## Model

claude-opus-4-8 (planner), claude-sonnet-5 (researcher + checker)
