---
date: 2026-07-27
tags: [session, phase-37, planning, v9.0]
---

# 2026-07-27 — Phase 37 Planning: Script Structure Validation MVP

**Phase 37: Script Structure Validation MVP** planning completed. 6 plans across 5 waves, 17 tasks. Plan verification passed on iteration 1.

## Summary

Planned Phase 37 (v9.0 AI Workflow Intelligence, Phases 28–40). Delivers deterministic Cypher checks over the published Computgraph, Design-Rule-mapped structural requirements, and a read-only LLM consult endpoint that answers questions about script structure — the foundation v10.0 Script Intelligence builds on.

## Deliverables

- **37-01:** Wave 0 test substrate (parser-faithful Frame fixture variants, network-free consult adapter double)
- **37-02:** spec/RULE-PARTITION-POLICY.md addendum + normative JSON contracts in spec/API.md
- **37-03:** `cg_structure_checks.py` — 7 deterministic checks + two-tier tests
- **37-04:** `llm/structure_rules.json` + defensive loader + 4 operation templates + evaluator
- **37-05:** `POST /computgraph/validate`, report builder, report contract test
- **37-06:** `POST /computgraph/consult`, subgraph fetch, grounding post-check

## Key Findings

**Two catches that would have silently broken Success Criteria.** The planner verified against real source (37-PATTERNS.md analogs + inline Bash inspection) rather than trusting the roadmap:

1. **SC2 unreachable:** `_frame_cg_context()`'s procedures are named `11_Proc`/`12_Proc`, but `CanvasAnnotationParser.ProcedureRegex` captures text *after* the separator — real canvas yields `2D Footer Configuration`. A `requiresProcedure: Footer` rule would never have fired. Fixed in 37-01 (new parser-faithful fixture module, non-destructive to `test_computgraph_publish.py`'s golden vector).

2. **SC3 unreachable:** `11_Var_HTotal` isn't a graph property — `computgraph_publish.py:530` writes bare `HTotal`; convention token survives only in cgId's last segment. Fixed in 37-03 (new `convention_name_from_cg_id()`) + 37-06 (subgraph fetch renders convention tokens).

**Partition question resolved:** `spec/RULE-PARTITION-POLICY.md` names only SWRL vs SHACL; the Computgraph is a Neo4j LPG with no RDF projection — SHACL literally can't reach it. Cypher-native checks are architecturally correct. This is a *documentation gap, not a conflict*. 37-02 owns the addendum.

## Design Decisions (Open-for-Planning Items)

Three "Open for planning" CONTEXT.md items resolved:

| Decision | Rationale |
|----------|-----------|
| Rule-mapping file → `llm/structure_rules.json` (file-first) | Versioned alongside `llm/cypher_catalog.json`, extension point for v10 growth, simpler MVP |
| Severity → reuse SHACL's `violation/warning/info` | Aligns with ValidGraph Run conventions, no new taxonomy |
| Results → ephemeral (no persist for MVP) | Lightweight for now; v10 workflows will request history if needed |

Also resolved:
- RULE-PARTITION-POLICY.md placement → addendum (no new `D-NN` decision number)
- Two unreachable defensive checks → kept (trivial cost, guards future changes)
- GH-panel print → **named deferral** (not silent drop; lowest-cost MVP is JSON contract + plain HTTP)

## Verification

- **Plan checker:** VERIFICATION PASSED on iteration 1 (no revision loop)
- **Requirements coverage:** SVAL-01, SVAL-02, SVAL-03 all present in plan frontmatter
- **High-value checks:** All 10 verified (SC4 determinism gate, SC1 honesty, source-fidelity catches, two-tier tests, etc.)
- **Commits:** `ebc462f` (research + validation) → `228ec5f` (6 plans) → `069e8f8` (STATE/ROADMAP)

## Session Notes

- Concurrent phase: 0c66d0b (docs(38): add phase research) landed mid-run from parallel session
- Scope tightly scoped: left untracked files (phase 29, debug/) from earlier sessions untouched
- Model changed to haiku mid-session

## Next

Execute Phase 37 via `/gsd-execute-phase 37` or pace with `--wave 1` flag.
