---
tags: [decision, phase-1303, rule-ingest, swrl, validator, property-calculator]
date: 2026-10-21
status: approved, planned (plans 1303-19…23, commit de64af1), not implemented
---

# Multi-participant rules keep one subject and assert the other classes as context (Phase 1303, D-61…D-65)

**Context.** «Отверстие в перекрытии не может быть ближе 500мм к контуру проекции колонн и стен на это перекрытие» was ingested as `Opening(?o) ^ hasMinProjectionClearanceMm(?o, ?d) ^ swrlb:lessThan(?d, 500)`.
- Slab, Column, Wall and their relations never reached the graph.
- The calculator of that property read Wall, Column and Beam, chosen from its own script, not from the rule.

**Decisions (owner, 2026-10-21).**
- **D-61 (option a).** The LLM writes every participant class as a `ClassAtom` and every relation as an `ObjectProperty` plus an `ObjectPropertyAtom`.
  - A context-only variable is excluded from binding: one that appears only in body `ClassAtom`/`ObjectPropertyAtom`, has a subject in the head, and is never in a data, builtin or head atom.
  - Its atoms count as matched and are listed in the result message as asserted by the rule, not verified. There is no new status.
  - The rule must evaluate exactly like its one-class form. Multi-object joins stay `unsupported`.
- **D-62.** Every participant reaches the property calculator.
  - The subject class is the box class; participants are `READS_CLASS` with their relation.
  - A mismatch with what the script reads is reported, never silently relinked or regenerated (regeneration is paid).
- **D-63.** Tracked as requirement DGOPN-06.
- **D-64.** The conflict check covers every class.
  - Two rules conflict when subject class, property and comparator are equal and their context participants (subject excluded, planner refinement) overlap, or one of them has none.
- **D-65.** The conflict check runs on the written atoms after ingest.
  - Reason: the pre-ingest text check tokenizes ASCII only and never grounds a Russian rule.
  - Dialog actions: Replace/Update, Keep both, Cancel. Cancel deletes the new rule through the existing preview.

**Alternatives rejected.**
- Relations only in OntoGraph metadata, not in SWRL (option b).
- Exact-match conflict sets.
- A Russian lexicon for the pre-ingest check (fragile).
- `DOMAIN`/`RANGE` relationships or `USED_WITH` edges now. OntoGraph stays a flat vocabulary until the Phase 1302 company vocabulary; `domain`/`range` on ObjectProperty are annotations, never `rdfs:` axioms.

**Consequences.**
- `computable_form` (plan 1303-15) must be rewritten, because it forbids exactly this.
- `BOX_CLASS_AMBIGUOUS` and the single-class skip in `ensure_rule_classes` go.
- `spec/SWRL-SUBSET.md` §1.1/§2/§3 describe context atoms.

**Links.**
- Design: `docs/superpowers/specs/2026-10-21-multi-participant-rule-extraction-design.md`.
- Context: `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`.
- Session: [[sessions/2026-10-21 Multi-participant rules design, plans 1303-19 to 23 and Graph Viewer cap fix]].
