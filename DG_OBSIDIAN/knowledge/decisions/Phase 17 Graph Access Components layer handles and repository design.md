---
tags: [decision]
date: 2026-07-04
---

# Phase 17: Graph Access Components — Layer Handle Model and Repository Design

## Context

Phase 17 delivers 5 Grasshopper components for read-only access to all 4 Neo4j graph layers:
- CONNECTOR (rename ports, "Connection"→"Database" output)
- GRAPH DECONSTRUCT (new, 1→4 type adapter)
- METAGRAPH (rework, add Objects output index-matched with Rules)
- ONTOGRAPH (new, read Class/ObjProperties/DataProperties)
- VALIDATION GRAPH (new, replace VALIDATION RUNS, read Run/Status/DesignState)

## Decisions

### D-01: Individual layer handle types
Each graph layer gets a distinct type: `MetagraphHandle`, `OntographHandle`, `ValidGraphHandle`, `SpecGraphHandle`. Each wraps `ConnectionInfo`. GRAPH DECONSTRUCT is the sole producer. Layer-reader components accept only their specific handle type, giving Grasshopper-level wire type safety.

### D-02: METAGRAPH Objects via Neo4j query
Objects are extracted by querying `(r:Rule)-[:HAS_BODY|HAS_HEAD]->(a:Atom)-[:REFERS_TO]->(c:Class)` directly, deduplicated by IRI. Parallel-loadable with existing Rules query. Cleaner than inferring from VariableTypeInferrer naming conventions.

### D-03/04: VALIDATION GRAPH index-matching
Run[i]↔Status[i] are 1:1 paired. DesignState output is deduplicated by StateId (separate list, not forced to match Run length).

### D-05: Status as Boolean list
Status[i] = `IReadOnlyList<bool>` — per-ObjState bools. Overall pass = AND(all), derived at read time. Matches Phase 14 D-01 contract.

### D-06: Per-layer repository + interface
- `IRuleRepository` — extend with `GetObjectsAsync`
- `IOntoGraphRepository` / `Neo4jOntoGraphRepository` — queries `graph='OntoGraph'`
- `IValidGraphRepository` / `Neo4jValidGraphRepository` — queries `graph='ValidGraph'`, returns Run + Status + DesignState

**Why:** Testability via mock repositories. Follows existing `IRuleRepository` pattern.

## Status
- CONTEXT.md written: `17-CONTEXT.md`
- Ready for planning via `/gsd-plan-phase 17`
