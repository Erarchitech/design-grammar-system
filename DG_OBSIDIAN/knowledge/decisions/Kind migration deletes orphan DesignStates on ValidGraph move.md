---
tags: [decision, schema, v7.0, v4, migration]
date: 2026-07-03
---

# Kind-migration deletes orphan DesignStates when moving to ValidGraph

## Decision

The SCHM-13 kind-migration script is **delivered and executed** on a dev Neo4j (not deliver-only). It does two things in one pass:

1. Renames DesignState `kind` values: `DefState`→`ParamState`, `ObjectState`→`ObjState`.
2. Moves Run-linked DesignStates from `graph='Metagraph'` (v3 placement) to `graph='ValidGraph'` (Phase 13's [[DesignState persists to ValidGraph not Metagraph|corrected placement]]) — and **deletes** any DesignState with no linked Run, to satisfy the no-orphan invariant.

Because deletion is destructive, the migration must first run a **dry-run count** of what it will delete and print it, and must be **guarded to dev databases only** — it does not run unattended against anything that could be production.

## Why

Phase 13 locked a hard constraint: a DesignState in ValidGraph must have ≥1 linked Run (it can only arrive there via VALIDATOR's publish path, which always creates a Run). But historical v3 DesignState data sitting in Metagraph may include nodes with no Run link. Three options were considered: leave orphans in place with a report (safest, but permanently violates the invariant for old data), move everything and accept a temporary violation (simplest, but knowingly leaves bad data), or delete orphans outright. Deletion was chosen to keep the invariant clean going forward rather than carrying a known exception indefinitely — accepted specifically because this targets **dev** data, not production, and only after a counted dry-run.

This also breaks from the project's own precedent: the v3.0 `migrations/2026-06-23_var_project_merge_key.cypher` was written but never executed against live Neo4j. Phase 14 chose to actually run its migration and capture before/after counts as live proof, rather than repeat that unexecuted-migration pattern.

## Consequences

- The migration script needs a pre-delete dry-run report, not just a single destructive Cypher statement.
- It must never be pointed at a production-flagged database — a guard check belongs in the script itself, not just documentation.
- Research (Phase 14 planning) must confirm whether a dev Neo4j actually holds v3-kind / Metagraph-placed DesignState data to exercise this — seeding may be needed first.
- Sets a precedent: this project's migrations should be run and verified within the phase that authors them, not left pending like the still-unrun 2026-06-23 migration.

## See also

- [[sessions/2026-07-03 Phase 14 discuss - schema v4 propagation decisions|Session: Phase 14 discussion]]
- [[DesignState persists to ValidGraph not Metagraph]] — the layer-placement decision this migration executes
- [[Run ValidStatus is a per-object boolean array]] — companion Phase 13 Run-schema decision
