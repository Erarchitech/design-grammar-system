---
tags: [session, phase-14, v7.0, schema, discuss]
date: 2026-07-03
model: claude-opus-4-8
---

# 2026-07-03 — Phase 14 discussion: graph schema v4 propagation decisions

## Context

Ran `/gsd-discuss-phase 14` (Graph Schema v4 Propagation). This phase's job is to make every artifact that hard-codes the Neo4j graph schema (`cypher_template.txt`, `training/dataset_schema.json`, both n8n prompts, NeoVis `config.template.js`/`index.html`, `data-service/app.py`, a kind-migration script, training/test fixtures) speak v4 — the three DesignState kinds and the Phase-13 Run validation model — before any Grasshopper component code changes in Phases 16–20. Most names were already locked by [[sessions/2026-07-03 Phase 13 discuss - ValidGraph and per-object ValidStatus|Phase 13]]; this session resolved the genuine HOW-to-propagate choices plus one real contradiction between the roadmap text and Phase 13's own resolution.

## What was done

1. Loaded PROJECT.md / REQUIREMENTS.md / STATE.md / ROADMAP.md, `13-CONTEXT.md`, and scouted `cypher_template.txt`, `training/dataset_schema.json`, `config.template.js`, `ontology/port-iri-map-V7.md` directly.
2. Found a real contradiction: ROADMAP SC#1 and REQUIREMENTS SCHM-07 both still say the v4 Run schema needs a `Status` text property — but Phase 13 D-07 killed that field (unified to `ValidStatus`). Flagged for the planner to amend the stale wording rather than build a field Phase 13 explicitly removed.
3. Also caught a roadmap bug: the Phase 14 detail section shows "4/4 plans complete" listing 13-01..13-04 — a copy-paste of Phase 13. Phase 14 is genuinely not started.
4. Grepped the C# read-side before proposing the Rule-property rename — found `Neo4jRuleRepository.cs` already coalesces `r.swrl→r.text` and `r.title→r.name`, so the read-side was already half-migrated. This shrank the blast radius of "full rename now" considerably.
5. Presented 4 gray areas; user selected all four: Status field conflict, Rule property names, kind-migration scope, NeoVis reconciliation.
6. Wrote `14-CONTEXT.md` + `14-DISCUSSION-LOG.md` in `.planning/phases/14-graph-schema-v4-propagation/`.

## Key decisions (user-confirmed)

- **No `Status` text field, ever.** v4 declares only `Run.ValidStatus` (Boolean list) + `Run.SendStatus` (single Boolean); overall pass = `AND(ValidStatus)` derived at read time. Confirms Phase 13 D-07 over the stale roadmap/SCHM-07 wording.
- **Run/DesignState become document-only in the template** — they're written by VALIDATOR-on-publish, not LLM ingest, so they stay in the schema reference section but drop out of the emitted CYPHER TEMPLATE BLOCK (removes the vestigial DesignState MERGE block at v3 lines 113-116).
- **Rule properties get a full rename now**, not deferred: `text`→`SWRL`, `title`→`RuleName`, +new `RuleDescription`, in ontology-exact **PascalCase** (matching `dgm:SWRL` etc. from the port↔IRI map). Readers keep `coalesce(new, old)` — this phase patches the two coalesce lines in `Neo4jRuleRepository.cs` so interim validation reads don't break.
- **kind-migration script is delivered AND executed** on dev Neo4j (not deliver-only, breaking from the still-unrun v3.0 precedent) — renames kind values, moves Run-linked DesignStates from `graph='Metagraph'` to `graph='ValidGraph'`, and **deletes orphan DesignStates** (no Run link) to enforce Phase 13's no-orphan invariant. Because deletion is destructive, the migration must dry-run-count first and be guarded to dev databases only.
- **NeoVis config reconciles to `DatatypeProperty`** (drops the dead duplicate `DataProperty` entries — DB keeps the `DatatypeProperty` label); `ParamState` inherits the old DefState blue, `ObjState` inherits the old ObjectState orange, `PropState` gets a new hue (Claude's discretion).

→ Full decision rationale: [[decisions/Rule properties renamed to SWRL RuleName RuleDescription in v4|Rule properties renamed to SWRL RuleName RuleDescription in v4]], [[decisions/Kind migration deletes orphan DesignStates on ValidGraph move|Kind migration deletes orphan DesignStates on ValidGraph move]]

## Result

`.planning/phases/14-graph-schema-v4-propagation/14-CONTEXT.md` + `14-DISCUSSION-LOG.md` written (not yet committed — `commit_docs: false` in this project's GSD config, session-end commit handles it). `.planning/STATE.md` updated via `state.record-session`.

**Research flags for the planner:** (1) confirm which n8n JSON files are source-of-truth vs. exports/backups (`_active-graph-query.json`, `_all-workflows-export.json`) before editing; (2) confirm a dev Neo4j actually holds v3-kind DesignState data to exercise the migration — seed if not.

**Next:** `/gsd-plan-phase 14`.

## Graph connections

- [[sessions/2026-07-03 Phase 13 discuss - ValidGraph and per-object ValidStatus|Prior session: Phase 13 discuss]] — locked the names this phase propagates
- [[decisions/Run ValidStatus is a per-object boolean array|Run ValidStatus is a per-object boolean array]] — the decision this session confirms wins over stale roadmap text
- [[decisions/DesignState persists to ValidGraph not Metagraph|DesignState persists to ValidGraph not Metagraph]] — the layer move the kind-migration executes
- [[decisions/Rule properties renamed to SWRL RuleName RuleDescription in v4|Rule properties renamed to SWRL RuleName RuleDescription in v4]]
- [[decisions/Kind migration deletes orphan DesignStates on ValidGraph move|Kind migration deletes orphan DesignStates on ValidGraph move]]
- [[Graph schema v3 is the canonical data model]] — superseded by the v4 schema this phase implements
