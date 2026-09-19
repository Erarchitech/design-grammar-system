# 2026-09-19 — Theory-Implementation Alignment Cross-Milestone Planning

**Модель:** claude-haiku-4-5-20251001 (switched from Opus 5 1M)  
**Дата:** 2026-09-19  
**Изменено файлов:** 3 commits across 5 files

## Изменённые файлы

- `.planning/milestones/v12.0-CONTEXT.md` (new, 300 lines)
- `.planning/milestones/v12.0-DISCUSSION-LOG.md` (new, 113 lines)
- `docs/reviews/theory-implementation-alignment/THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md` (new, 500 lines added with §8.2 mapping section)

## Сессия: cross-milestone planning discussion against alignment review plan

### Результаты

Triaged the alignment plan's 16 work packages against existing v11.0 (1101-1109) and v9.0 Phase 40 ownership. Created new isolated milestone **v12.0 — Theory–Implementation Alignment** (phases 1200-1205) for the 7 unowned packages plus the ATTRIBUTE_OF decision.

**Eight locked decisions:**
1. New isolated milestone v12.0 (v11.0 caps at 9 slots)
2. Phase block 1200-1205 per vX.Y → X·100+Y·10 convention
3. ID disambiguation: plan's packages → ALIGN-P01..P16; gsd.md keeps GSD-ALIGN-001..013
4. Six phases, one gate boundary per phase pair (contract, replay/identity, empirical, release)
5. Cross-service golden fixture as Phase 1200 deliverable; DE-01 validates it
6. Pending live UAT stays with Phase 40, recorded unknown
7. Security/tenancy gets own Phase 1205, release-blocking
8. ATTRIBUTE_OF decision deferred to 1203 with both branches costed

**Key finding:** `dgc:attributeOf` IS declared in the ontology TBox (DesignGrammar-V7.md:414,707) with zero runtime writers/readers. PARAM_LINK is implemented. Bridge is declared-but-unimplemented, not absent — inverts the cost comparison between implementing vs. revising the paper. Verified against the working tree.

**Routing table:** 7 packages → v12.0; P09/P15/P16 → v11.0 1106/1107; P10/P11/P12 → Phase 40; P01/P02 shared.

**Sequencing prerequisite:** control-plane reconciliation (gsd.md GSD-ALIGN-001..013) runs before v12.0 planning so it is scoped against true phase status.

**Not activated:** v9.0 Phase 40 remains frontier; `.planning/phases/`, STATE.md, active REQUIREMENTS.md untouched.

### Commit log

1. **4eda963** `docs(v12.0): capture theory-implementation alignment milestone context` — v12.0-CONTEXT.md + v12.0-DISCUSSION-LOG.md
2. **44bf943** `docs(alignment): map alignment work packages to updated GSD plans` — THEORY-IMPLEMENTATION-ALIGNMENT-PLAN.md §8.2 mapping + CONTEXT.md ref tweak

Prior-session work on data-service, C#, spec files preserved as unstaged modifications (11 files from earlier session were swept into the first commit by a pre-commit hook; reset it and recommitted with explicit pathspecs).

### Деferred ideas

- Alternatives B (RDF canonical) and C (typed domain service) with DE-02/DE-03 — revisit post-milestone
- Graphify regeneration — do in separate evidence run
- v4.0 BOT Ontology Bridge — unchanged future scope

### Открытые вопросы

Routed to owning phases:
- Q1-2: missing binding semantics (1200)
- Q3-4: Design State identity, geometry/ClassIri normative membership (1202)
- Q5: canonical verdict service owner (1202)
- Q7: identity authority precedence (1203)
- Q9: project/CDE authorization model (1205)
- Q10: LLM reproducibility snapshot (1204)
- Q6, Q8: moved to v11.0 1106 (FBS behavior, five-layer contract)

### Заметки

**ID collision resolved:** the plan originally used GSD-ALIGN-01..16, colliding with gsd.md's GSD-ALIGN-001..013 control-plane register. Renamed to ALIGN-P01..P16; gsd.md's IDs are machine-consumed, so they stay unchanged. Both registers documented in v12.0-CONTEXT.md D3.

**Untracked docs/reviews/ bundle:** 70 files, 18M, ~10M downloaded PDFs and scraped HTML. Plan file committed; evidence and sources left untracked pending a separate decision on what to version.

**Context location:** this is a milestone-level CONTEXT (not phase-level) because the invoking argument was not a phase number — it was a cross-milestone investigation against a review plan.
