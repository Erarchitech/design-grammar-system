// ============================================================================
// Migration: 2026-06-23_var_project_merge_key.cypher
// ============================================================================
//
// PURPOSE
//   Fixes PITFALLS.md Pitfall 4 / REQUIREMENTS.md SCHM-02 — the v2.0/v3.0
//   `cypher_template.txt` historically MERGEd `:Var` nodes on `name` alone
//   (`MERGE (v:Var {name: '?x'})`), with `project` applied afterward via a
//   separate `SET`. Because `project` was never part of the MERGE key, a
//   `?x` variable created by project-A and a `?x` variable created by
//   project-B could silently resolve to the SAME underlying `Var` node —
//   a cross-project identity/isolation violation. `cypher_template.txt` has
//   already been fixed (see SCHEMA VERSION: v3.1) so all NEW ingests now
//   MERGE on `{name, project}` together. This script is the one-time
//   backfill for EXISTING `Var` nodes that predate that fix and are
//   missing the `project` property entirely (untagged orphans).
//
// EXECUTION METHOD
//   This script is NOT invoked automatically by any application code. Run
//   it manually against the live Neo4j instance using one of:
//     - cypher-shell -a bolt://localhost:7687 -u neo4j -p <password> -f migrations/2026-06-23_var_project_merge_key.cypher
//     - Neo4j Browser: paste the MATCH/SET statement below and execute it directly.
//
// ============================================================================
// WARNING — SCOPE LIMITATION (read before running)
// ============================================================================
//   This script does NOT retroactively split already-merged cross-project
//   Var nodes apart. It only tags currently-UNTAGGED orphans (nodes missing
//   `project` entirely) with a default value via `coalesce()`.
//
//   Nodes that are ALREADY incorrectly shared between two or more projects
//   (the actual collision case described in Pitfall 4) are NOT auto-resolved
//   by this script — there is no audit trail in the existing data to
//   reconstruct which project a contaminated node "should" belong to, so
//   any such split must be done manually after identifying the affected
//   nodes (see the audit query below). This is a known, accepted
//   migration-window limitation (see 07-03-PLAN.md threat_model T-07-07).
// ============================================================================

// --- Step 1: Backfill missing `project` on existing Var nodes -------------
// Only touches nodes where `project` does not exist at all. Never overwrites
// an already-tagged node's project (coalesce keeps the existing value if
// present, so this is also safe to re-run idempotently).
MATCH (v:Var)
WHERE NOT EXISTS(v.project)
SET v.project = coalesce(v.project, 'default-project');

// ============================================================================
// AUDIT QUERY (read-only, documentation only — not auto-executed)
// ============================================================================
// Use this to manually identify Var nodes that are ALREADY cross-contaminated
// across two or more projects (the collision case this script does not fix).
// Each row returned requires manual investigation: decide which project the
// node should belong to, then re-ingest the affected rule(s) under the fixed
// `cypher_template.txt` MERGE key so a correctly-scoped node is created, and
// re-point the affected ARG relationships before removing the old shared node.
//
// MATCH (v:Var) WITH v.name AS name, collect(DISTINCT v.project) AS projects
// WHERE size(projects) > 1
// RETURN name, projects

// ============================================================================
// VERIFICATION QUERY (run after applying Step 1 above)
// ============================================================================
// Verify: MATCH (v:Var) WHERE NOT EXISTS(v.project) RETURN count(v) — expect 0
