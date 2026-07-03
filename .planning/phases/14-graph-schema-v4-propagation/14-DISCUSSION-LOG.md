# Phase 14: Graph Schema v4 Propagation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 14-graph-schema-v4-propagation
**Areas discussed:** Status field conflict, Rule property names, kind-migration scope, NeoVis reconciliation

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Status field conflict | Resolve ROADMAP/SCHM-07 "Status text" vs Phase-13 D-07 removal | ✓ |
| Rule property names | text/title → SWRL/RuleName + RuleDescription | ✓ |
| kind-migration scope | run vs deliver-only; kind rename + layer move + orphans | ✓ |
| NeoVis reconciliation | duplicate DatatypeProperty/DataProperty + state colors | ✓ |

**User's choice:** All four selected.

---

## Status field conflict

| Option | Description | Selected |
|--------|-------------|----------|
| Follow Phase 13 | Only ValidStatus (Boolean list) + SendStatus; no Status text; overall pass = AND(ValidStatus) derived; flag roadmap/SCHM-07 as stale | ✓ |
| Keep a Status text too | Store redundant Run.Status text enum for cheap Model Viewer display; reopens Phase-13 conflict | |

**User's choice:** Follow Phase 13 (Recommended).
**Notes:** Confirms D-07 and the port→IRI map win over the stale roadmap/SCHM-07 wording. → CONTEXT D-01/D-02.

### Template scope (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Document-only | Keep Run + DesignState in the GRAPH SCHEMA reference section but remove from the emitted CYPHER TEMPLATE BLOCK; ingest writes OntoGraph + Metagraph only | ✓ |
| Keep emitting a block | Preserve an updated DesignState/Run MERGE block in the emitted template | |

**User's choice:** Document-only (Recommended).
**Notes:** Drops the vestigial DesignState MERGE block (v3 lines 113–116). → CONTEXT D-03.

---

## Rule property names

| Option | Description | Selected |
|--------|-------------|----------|
| Full rename now | Write SWRL/RuleName/RuleDescription; readers coalesce(new, old) | ✓ |
| SWRL only, minimal | Add only SWRL; defer RuleName/RuleDescription to Phase 18 | |
| Document-only mapping | Keep text/title; document text↔SWRL mapping only | |

**User's choice:** Full rename now (Recommended).
**Notes:** Grep showed Neo4jRuleRepository.cs already coalesces r.swrl→r.text and r.title→r.name; data-service/app.py doesn't touch Rule text/title — small blast radius. → CONTEXT D-04.

### Casing (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Ontology PascalCase + patch C# | Write SWRL/RuleName/RuleDescription; patch the two Neo4jRuleRepository coalesce lines to prepend new names | ✓ |
| lowercase swrl, no C# change | Write lowercase swrl to slot into existing coalesce; diverges from dgm:SWRL casing | |
| PascalCase, defer C# to Ph17/18 | Write PascalCase, accept interim empty-SWRL reads for new rules | |

**User's choice:** Ontology PascalCase + patch C# (Recommended).
**Notes:** DB property names match the port→IRI contract exactly; one-line coalesce patches keep interim validation reads alive. → CONTEXT D-05/D-06.

---

## kind-migration scope

| Option | Description | Selected |
|--------|-------------|----------|
| Deliver-only + verifiable script | Ship idempotent self-verifying migration + documented dev-run procedure; matches unrun-migration precedent | |
| Deliver AND execute on dev | Also spin up Neo4j, run the migration, capture before/after counts as live SC#5 proof | ✓ |

**User's choice:** Deliver AND execute on dev.
**Notes:** Pulls Docker/integration work into the phase; research must confirm dev DB holds v3-kind data (may need seeding). → CONTEXT D-08.

### Orphan policy (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Non-destructive report | Move only Run-linked DesignStates; leave + report orphans | |
| Delete orphans | Move linked ones; DELETE DesignStates with no Run link | ✓ |
| Move all, accept temp violation | Set graph='ValidGraph' on all; log orphans as known exception | |

**User's choice:** Delete orphans.
**Notes:** Destructive — CONTEXT D-10 requires a dry-run count + dev-only guard before the delete. → CONTEXT D-09/D-10.

---

## NeoVis reconciliation

| Option | Description | Selected |
|--------|-------------|----------|
| Reconcile to DatatypeProperty + inherit colors | Drop dead DataProperty entries; ParamState→blue, ObjState→orange, PropState→new hue (Claude's pick) | ✓ |
| Same reconcile, user picks colors | User specifies the three hex colors | |
| Keep both labels defensively | Keep both DatatypeProperty + DataProperty entries | |

**User's choice:** Reconcile to DatatypeProperty + inherit colors (Recommended).
**Notes:** NeoVis reads DB labels; DataProperty entries are dead config. → CONTEXT D-11/D-12/D-13.

---

## Claude's Discretion

- Exact hex for the new PropState color (harmonious green/teal, avoid clashing with Class green #78c38a).
- Run→DesignState relationship type/direction/label in the v4 schema reference (contract: many-Runs-to-one-DesignState).
- v4 successor filename for updated_cypher_reference_examples_v3.cypher (prefer new v4 file).

## Deferred Ideas

- Research flag: confirm n8n source-of-truth files (rules-to-metagraph.json / graph-query-mcp.json) vs. `_active-graph-query.json` / `_all-workflows-export.json` exports before editing.
- Research flag: confirm a dev Neo4j holds v3-kind / Metagraph-placed DesignState data to exercise the migration; seed if not.
- No out-of-scope capabilities surfaced — discussion stayed within phase scope.
