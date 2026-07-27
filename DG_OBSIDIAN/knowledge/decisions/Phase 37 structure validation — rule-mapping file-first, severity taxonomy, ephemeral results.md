---
name: phase-37-open-planning-resolutions
description: Three CONTEXT.md "Open for Planning" items resolved during Phase 37 planning
metadata:
  type: decision
  phase: 37
  context_items: 3
  decision_date: 2026-07-27
---

# Phase 37: Open-for-Planning Items — Design Decisions

During /gsd-plan-phase 37, three deliberate "Open for planning" items in 37-CONTEXT.md were resolved by the planner. Recorded here as binding design decisions.

## Decision 1: Rule-Mapping File Location and Shape

**Decided:** File-first approach via `llm/structure_rules.json`

**Why:** 
- Versioned alongside existing `llm/cypher_catalog.json`, exploits existing ecosystem pattern
- Simpler MVP shape: JSON envelope with rule-id mapping to Computgraph structural requirements (e.g., `requiresProcedure: Footer`)
- Extension point for v10 growth without ontology churn
- Loadable via existing Python config loader pattern (mirrors `config.template.js` style)

**How to apply:** 
- v9.0 Phase 37 persists the file-first decision; v10 may move to graph-native (Neo4j nodes) if workflows need schema-driven rule discovery or versioning per definitionId
- Do not create per-project Neo4j rule nodes; keep centralized in the JSON file

**Related:** [[Phase 37 research — validation architecture]] notes this as a deferral candidate; file-first proven sufficient through SC2 and SC4 testing.

---

## Decision 2: Severity Taxonomy Alignment

**Decided:** Reuse existing SHACL severity levels (`violation`, `warning`, `info`)

**Why:**
- ValidGraph Run nodes and their structural validation reports already use SHACL's three-tier severity
- No new taxonomy reduces cognitive overhead and API surface
- Aligns `/computgraph/validate` responses with ValidGraph semantics (user expects consistent severity interpretation)

**How to apply:** 
- All structural checks (SVAL-01) and rule-mapped checks (SVAL-02) report via the three SHACL levels
- No custom severity strings or numeric levels
- Report builder in 37-05 enforces this enum in Pydantic `CheckResult.severity`

**Related:** See RULE-PARTITION-POLICY.md (Phase 37-02 addendum) for how the Computgraph checks sit alongside ValidGraph checks without conflict.

---

## Decision 3: Results Persistence — Ephemeral for MVP

**Decided:** Structure validation results are ephemeral; no persistent Run-like record in v9.0

**Why:**
- MVP scope: `/computgraph/validate` is a synchronous response endpoint, not a run-tracking system
- Persistence adds: database write contention, schema for run metadata, historical query patterns (not yet needed)
- v10 workflows may request history (e.g., "show me all times this procedure was flagged"); defer then
- Lower cognitive load for v9 users: one report per query, no accumulation

**How to apply:** 
- 37-05 and 37-06 produce JSON responses only; do not write to ValidGraph or persist
- `checkedAt` timestamp is the only temporal marker in the response
- If v10 needs historical reports, add a persistence layer (new Neo4j node type or separate log database) at that time

**Related:** 37-CONTEXT.md "Open for planning" item; wave-0 validation requires checking via repeated calls with determinism assertions (SC4), not history replay.

---

## Addendum: RULE-PARTITION-POLICY.md Documentation Gap

**Scope decision:** RULE-PARTITION-POLICY.md update is a real deliverable (37-02), not an afterthought.

**Finding:** The policy as written names SWRL vs SHACL partition; it does not address the Computgraph partition. The Computgraph is a Neo4j LPG (property graph) with no RDF projection — SHACL (which works over RDF/OWL) literally cannot reach it. Cypher-native structural checks over the LPG are architecturally correct and do not conflict with the SWRL or SHACL partitions.

**Action:** 37-02 Task 1 adds an addendum section documenting the three-partition model:
- SWRL: Metagraph rule bodies (ontology-level constraints)
- SHACL: ValidGraph RDF export (design-state and ontology validation)
- **Cypher (LPG-native):** Computgraph structure (script composition constraints)

**Impact:** Future phases adding validation categories must consult this updated policy. CLAUDE.md already mandates this practice (§ Schema Change Propagation Checklist).
