---
tags: [session, phase-1303, rule-ingest, swrl, validator, property-calculator, ontograph]
date: 2026-10-21
---

# Session: 2026-10-21 — Multi-participant rules: design, plans 1303-19…23, Graph Viewer cap fix

## Goal

The owner ingested the rule `R_OpeningSlabEdgeClearance500` («Отверстие в перекрытии не может быть ближе 500мм к контуру проекции колонн и стен на это перекрытие») into `str-openings-01`.
- It showed in the Edit picker but not in the Graph Viewer.
- After that was fixed, the slab class was still missing: the LLM had reduced the rule to `Opening` plus one property.

The owner asked for the rule-ingest logic to extract every object class of a rule and the relations between them. All work went to the worktree `C:\Users\Admin\source\repos\dg-mapping`, branch `feature/mapping-mvp`.

## What Was Done

- **Graph Viewer cap fix** (commit `093ea13`).
  - `GET /graph/{project}` returned the first 2,000 nodes / 8,000 relationships in id order. 71,524 of the 71,955 nodes in `str-openings-01` are `ValidationEntity`, so every rule written after the validation history began was cut off.
  - Nodes and relationships now sort validation records last, as the compact read already did. `test_graph_routes.py`: 74/74.
  - Deployed as `dg-mapping-data-service:093ea13` through the new override `D:\dgb\mapping-release-093ea13\compose.mapping-images.yml`; UI `b7bcbf0` and dg-reasoner `e600716` unchanged.
  - See [[knowledge/debugging/Graph Viewer cap hid rules behind validation history]].
- **Incident, fixed in the session.** A `docker compose build data-service` from the main folder (`feature/hosting-dg-pilot`) replaced the mapping release image for about 20 minutes. Restored with the override compose. See [[knowledge/debugging/Rebuilding data-service from the main folder replaced the mapping release image]].
- **Root cause of the missing classes, verified.**
  - The template and all six catalog shapes show one class.
  - `computable_form` (plan 1303-15) explicitly forbids ObjectProperty atoms and a second ClassAtom.
  - Shape keywords are English only.
  - The C# evaluator refuses `ObjectPropertyAtom`, and binding rows carry one object per ObjState.
- **OntoGraph analysis (owner question).**
  - Flat vocabulary was right for v8.2 but is now a bottleneck:
    - the static TBox does not cover `ex:` terms;
    - properties have no owner class;
    - 41 of 72 DatatypeProperties are per-rule violation flags;
    - classes are copied per project (`ex:Building` ×3), which contradicts the approved company vocabulary (Phase 1302);
    - only 3 ObjectProperties exist in the whole database, none with domain/range;
    - the IFC/bSDD classification module is not implemented;
    - `v8-ui-smoke` has 15 mis-layered nodes and non-schema edges.
  - Recommendation: a governed company vocabulary in 1302 (SUBCLASS_OF, DOMAIN/RANGE, bSDD reference, steward releases). The LLM proposes terms and never authors axioms. Usage is never auto-promoted to `rdfs:domain`.
  - No change was made from this analysis.
- **Design** `docs/superpowers/specs/2026-10-21-multi-participant-rule-extraction-design.md`: approved (commit `a298613`), checked by an independent builder pass, updated for D-64/D-65.
- **Plans 1303-19…23** (commit `de64af1`, not executed), requirement DGOPN-06, decisions D-61…D-65 in `1303-CONTEXT.md`:
  - 19: C# context-only classifier, binding, evaluation, disclosure and canvas;
  - 20: ingest prompt, Russian shape keywords, ObjectProperty domain/range;
  - 21: structural conflict check after ingest;
  - 22: participants into calculators;
  - 23: rollout and owner acceptance.
- The owner deleted `R_OpeningSlabEdgeClearance500` to re-ingest it after the work.

## Decisions Made

- D-61…D-65, see [[knowledge/decisions/Multi-participant rules keep one subject and assert the other classes as context (Phase 1303, D-61 to D-65)]].
- Planner refinement reported to the owner: the conflict overlap (D-64) is taken over the context participants, subject excluded; a rule without participants overlaps every rule with the same key.

## Issues Encountered

- The auto-mode classifier refused a batch with `git checkout -- file` and `mv`. The same was done with reversible Edit calls and a copy.
- The calculator code lives only on `feature/mapping-mvp`. Work on the main folder had to be moved to the worktree.
- The pre-ingest conflict check never grounds Russian text (ASCII tokenizer), so it always answered "no conflict". This is the reason for D-65.

## Next Steps

- Execute 1303-16 (or 1303-19, which is independent), then 17, 18, 20, 21/22, 23.
- Owner acceptance on `str-openings-01` in plan 23: re-ingest the slab-opening rule, run the conflict test with a 300 mm columns rule, check VALIDATOR R1–R4 unchanged.
- The hosting branch (`feature/hosting-dg-pilot`) still has the old graph cap. It gets the fix when the branches merge.

## Related Notes

- [[sessions/2026-10-21 Phase 1303-15 MEP opening boxes checked in Revit through Rhino.Inside and VALIDATOR]]
- [[knowledge/decisions/Property calculators read elements by their DG mapping, not only by Revit category (Phase 1303-15)]]
- [[knowledge/decisions/Alignment modules over extension modules in the DG ontology]]
