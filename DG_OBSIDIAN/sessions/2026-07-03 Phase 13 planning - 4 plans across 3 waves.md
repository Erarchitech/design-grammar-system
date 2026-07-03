---
tags: [session, planning, v7.0, phase-13]
date: 2026-07-03
---

# Phase 13 planning — 4 plans across 3 waves

**Milestone:** v7.0 — Update of DG Addin for Grasshopper
**Phase:** 13 — Ontology V7 and Contract Investigation
**Model:** claude-opus-4-8 (planning), claude-sonnet-5 (session save)

## What happened

Ran `/gsd-plan-phase 13` inline (no researcher/planner/checker subagents spawned — per prior guidance to write GSD artifacts inline when context is already loaded). Read the locked [[decisions/DesignState persists to ValidGraph not Metagraph|ValidGraph]] and [[decisions/Run ValidStatus is a per-object boolean array|per-object ValidStatus]] decisions from `13-CONTEXT.md`, then grounded the plan against the real `ontology/apply_v6_*.py` transform scripts and grepped the actual V6 owl for every rename-source token before committing it to a plan.

## Key groundwork (not new decisions — verification of existing ones)

- Confirmed exact V6 owl rename-source token counts: `ObjectState`×35, `DefState`×19, `ValidationRun`×21, `ReinstatementStatus`×27, `ruleText`×6, `ruleTitle`×1; version markers at owl lines 46 (`Schema version: v3` comment) and 48 (`versionInfo 6.1`).
- Resolved the ONTO-04 rule-property mapping concretely by reading the property defs: `ruleText` (line 547, holds the SWRL serialization) → `SWRL`; `ruleTitle` (line 561, human title) → `RuleName`; `RuleDescription` is new (no V6 predecessor).
- Flagged a collision hazard for Phase 14+ implementers: the OntoGraph reification classes `&dg;ObjectProperty`/`&dg;DatatypeProperty` must rename to `ObjProperty`/`DataProperty`, but the OWL constructs `owl:ObjectProperty`/`owl:DatatypeProperty` must never be touched. Baked an explicit self-check assertion for this into the 13-02 plan.

## Plans created

| Plan | Delivers | Reqs | Wave |
|------|----------|------|------|
| 13-01 | `V7-INVESTIGATION.md` — conflict resolutions (a)/(b)/(c) transcribed from CONTEXT.md + authoritative V6→V7 rename table | ONTO-04 | 1 |
| 13-02 | `apply_v7_rename.py` → `DesignGrammar-V7.owl` + `V6-to-V7-mapping.md` | ONTO-01/02/03/04 | 2 (depends 13-01) |
| 13-03 | `port-iri-map-V7.md` for all 14 GH_DesignGrammars components | ONTO-06 | 3 (depends 13-02) |
| 13-04 | V7 extension facades + `catalog-v001-V7.xml` + regenerated `DesignGrammar-V7.md` | ONTO-05 | 3 (depends 13-02, parallel to 13-03) |

All plans are generative (V6 owl asserted byte-unchanged; every artifact produced by a script, never hand-edited) and self-checking (banned-token greps, well-formed-XML parse, script exit codes) — no `RESEARCH.md`/`VALIDATION.md` exists for this phase (Nyquist Dimension 8 warned-and-continued; verification was baked into task-level acceptance criteria instead).

Verified against GSD tooling: all 4 `PLAN.md` files parse with valid frontmatter (`gsd-tools.cjs query init.execute-phase 13`); wave numbers (1/2/3/3) match what `phase.cjs`'s `depends_on` DAG would compute, so no wave-drift warnings expected at execute time.

## Files changed this session

- `.planning/phases/13-ontology-v7-and-contract-investigation/13-01-PLAN.md` (new)
- `.planning/phases/13-ontology-v7-and-contract-investigation/13-02-PLAN.md` (new)
- `.planning/phases/13-ontology-v7-and-contract-investigation/13-03-PLAN.md` (new)
- `.planning/phases/13-ontology-v7-and-contract-investigation/13-04-PLAN.md` (new)
- `.planning/ROADMAP.md` (plans + progress table)
- `.planning/STATE.md` (phase status → planned, resume pointer)

## Next

`/gsd-execute-phase 13`
