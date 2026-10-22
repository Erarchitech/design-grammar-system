---
phase: 1303-pravilo-gh-obekt
plan: "22"
subsystem: property-calculator-participants
tags: [d-62, dgopn-06, property-scripts, reads-class, participants, generation-prompt]
requires:
  - phase: 1303-pravilo-gh-obekt
    provides: "1303-17 (resolve order, shared/blocked inputs, warnings list, _Session fake); 1303-19 (RuleVariableRoles definition); 1303-20 (participants written by ingest)"
provides:
  - "property_scripts.load_rules: per rule subject {iri, label} and participants [{iri, label, relation, relationIri, relatedTo}]"
  - "resolve/generate/ensure_rule_classes keyed on the subject class; BOX_CLASS_AMBIGUOUS only for different subject classes"
  - "READS_CLASS written from the participants (relation, relatedTo on the edge), categories from the class side"
  - "warnings CALCULATOR_PARTICIPANT_MISMATCH and CALCULATOR_PARTICIPANTS_DIFFER (structured dicts in the warnings list)"
  - "property_calculator_llm.build_prompt(participants) with a Participants: block"
affects: [1303-23]
tech-stack:
  added: []
  patterns:
    - "Python mirror of the C# RuleVariableRoles in one helper (rule_roles), second read query keeps load_rules' first session call"
    - "participants travel to the generator inside the request dp copy, so the 3-argument Generator contract is unchanged"
    - "warnings list may hold strings and structured dicts; de-duplication by canonical JSON"
key-files:
  created: []
  modified:
    - data-service/property_scripts.py
    - data-service/property_calculator_store.py
    - data-service/property_calculator_llm.py
    - data-service/app.py
    - data-service/tests/test_property_scripts.py
    - data-service/tests/test_property_calculator_store.py
    - data-service/tests/test_property_calculator_llm.py
    - spec/DATABASE.md
key-decisions:
  - "Subject = class of the head atom's position-1 variable; a rule with no head, no variable subject or no ClassAtom on it has subject None and no participants (strict, no fallback to a single ClassAtom class)."
  - "Participants are context-only ClassAtoms in body order; relation = the first ObjectPropertyAtom between the participant and the subject or another participant, relatedTo = the class of the other end."
  - "Revit categories of a participant: inverse catalogue categoryClasses united with the stored revitCategories of same-concept project classes (Slab ~ Floor -> OST_Floors)."
  - "Per rule, entry.contextClasses are that rule's participants (exact for rule_context_categories); the calculator's READS_CLASS set is the union over the rules with participants."
  - "Mismatch compares class labels, not categories, with same-concept folding; the subject class and GenericModel are never 'extra'."
  - "save_context_classes never folds a class whose exact label exists (before: any same-concept sibling won, so Slab could be redirected to Floor although Slab existed)."
requirements-completed: []
requirements_partial: [DGOPN-06]
duration: ~1h30m
completed: 2026-10-22
status: complete
---

# Phase 1303 Plan 22: Participants reach the property calculator Summary

The classes a rule names now decide what its property calculator is linked to: the head variable's class is the box class, the context participants (with their `hostedBy` / `projectsOnto` relation) become `READS_CLASS`, the script's own read categories are only checked against them, and one multi-participant rule no longer stops script generation for the whole project.

## Performance

- Tasks: 3 of 3, each with a RED test commit and a GREEN commit. Commits: `a7cedcc` (test) / `2fd96e5` (Task 1), `beee628` / `6ac2153` (Task 2), `3e36e76` / `41b31b2` (Task 3).
- Focused tests (cwd `data-service`): `python -m pytest tests/test_property_scripts.py tests/test_property_calculator_store.py tests/test_property_calculator_llm.py -q -p no:cacheprovider` -> 177 passed (baseline before the plan: 151 for the same three files). Wider set with `test_property_calculator_routes`, `test_property_calculator_review`, `test_route_inventory`, `test_cypher_allowlist`: 2146 passed, 16 skipped.
- Full data-service suite: 6477 passed, 35 skipped, 8 deselected, 4 failed, 25 errors; all failures and errors are the recorded baseline (below).
- `tools/de01`: 173 passed, 1 failed (`test_de01_runner_against_golden_fixture_has_zero_silent_disagreements`, REPRODUCIBILITY drift, same as before the plan).

## Accomplishments

### Task 1: subject, participants, subject-based box class (commits a7cedcc, 2fd96e5)
- `RULE_STRUCTURE_QUERY` (second session call of `load_rules`, `load_rules` stays first; same project and `SUPERSEDED_BY` corpus filter as `RULE_ATOMS_QUERY`) reads head and body atoms with their referent and ARG edges. `rule_roles` mirrors `DG/src/DG.Core/Parsing/RuleVariableRoles.cs` (comment links the C# class). `rules_from_rows(rows, structure_rows=())` adds `subject` and `participants` to every rule; `classes` and `dataProperties` are unchanged.
- `resolve`: box class = the subject classes of the requested rules; `BOX_CLASS_AMBIGUOUS` only when they differ (acceptance rule Opening/Slab/Column/Wall resolves, four one-class OpeningBox rules plus the acceptance rule on OpeningBox generate together).
- `ensure_rule_classes`: groups by subject class, no longer skips rules with several ClassAtoms; a rule with DataProperties and no subject lands in `unsupported` with reason `no subject`.

### Task 2: participants as READS_CLASS, mismatch warning (commits beee628, 6ac2153)
- `participant_classes`, `merge_participants`, `assign_context_classes`, `participant_mismatch` in `property_scripts`; `load_class_categories`, `PARTICIPANT_CLASS_QUERY`, `CLASS_CATEGORIES_QUERY` in the store. The edge carries `relation` and `relatedTo` (`relatedTo` follows a same-concept fold, so Column projectsOnto Floor when the project's class is Floor). A participant-less rule keeps `context_classes` byte for byte (the base `CONTEXT_CLASS_QUERY` additionally clears stale `relation`/`relatedTo`).
- `CALCULATOR_PARTICIPANT_MISMATCH {code, ruleId, dataPropertyIri, extra, missing}`: stored script reading Wall, Column, Beam against participants Slab, Column, Wall gives `extra [Beam]`, `missing [Slab]`; nothing is saved, no `READS_CLASS` to Beam, generator never called.
- `CALCULATOR_PARTICIPANTS_DIFFER {code, dataPropertyIri, ruleIds, union, difference}` when rules with participants over one DataProperty differ; `READS_CLASS` is the union.
- `rule_context_categories` (app, unchanged consumer) now returns the participants' categories for the acceptance rule (test with the real `generate` over the fake session).
- `spec/DATABASE.md`: `READS_CLASS` edge properties and the participants-authoritative rule.

### Task 3: participants in the generation prompt (commits 3e36e76, 41b31b2)
- `build_prompt(..., participants=None)`; a `Participants:` block (`- Slab: hostedBy Opening; Revit categories: OST_Floors`) sits between the rules and `CONTEXT_API`; without participants the prompt is byte-identical to the 1303-16 pin (sha256 test). `resolve` hands the participants of the rules that use the property to the generator inside a copy of `dp` (`dp["participants"]`), `generate_calculator` forwards them; no new LLM call site, the 3-argument generator contract is unchanged.

## Deviations from Plan

### Judgement calls

**1. [Rule 2 - Critical] `save_context_classes` does not fold an existing exact label.** Before, any same-concept sibling in the project won (`e != label`), so Slab (created by the rule ingest) would have been relinked to an existing Floor and the participant lost. Now only a label the project does not have is folded. One-class behavior is identical unless both Floor and Slab exist. Commit 6ac2153.

**2. [Minor] `app.py` change limited to the `BOX_CLASS_AMBIGUOUS` hint.** The plan lists `app.py`; `rule_context_categories` needed no code change (it already reads `contextClasses`), so only the error hint text was updated to say "subject class". Commit 2fd96e5.

**3. [Minor] Structured warnings in the shared `warnings` list.** The list now mixes strings (1303-17) and dicts; `_unique` replaces `dict.fromkeys`. No consumer validates these warnings as strings (the string-array check in `app.py` is for rule-ingest warnings). The second code `CALCULATOR_PARTICIPANTS_DIFFER` is mine; the plan names only the mismatch code.

**4. [Minor] `spec/LPG-OWL-MAPPING.md` not touched.** CLAUDE.md lists it for new relationship types; `READS_CLASS` is an existing tooling link with no OWL correspondence and gains only edge properties, and the file is outside `files_modified`.

None of the above changes scope.

## Baseline comparison

Failures after this plan, none in a plan-22 file, identical to 1303-21's baseline:
- `test_dg_context.py::TestContextEndpoints::test_post_assemble_returns_200_for_valid_type`, `::test_get_debug_matches_post_assemble_body`, `TestDeterminism::test_repeated_assemble_calls_are_byte_identical`, `::test_get_debug_and_post_assemble_are_equal_for_graph_query` (endpoint 500).
- 25 errors in `test_cg_structure_checks.py` and `test_computgraph_consult.py` integration classes (`neo4j:7687` DNS).
- `tools/de01` `test_de01_runner_against_golden_fixture_has_zero_silent_disagreements`.

## Prohibitions

- No LLM in preview or on a mismatch: `generate(..., generator=_no_llm)` with a mismatching stored script passes (`test_a_stored_calculator_that_disagrees_...`, `test_the_mismatch_warning_is_stable_across_repeats`); `POST /scripts/property-calculator` still passes `llm=False` (unchanged line).
- No second class for a known concept: `test_a_participant_of_a_concept_the_project_has_reuses_that_class` (through `generate`) and the store tests for folding and the exact-label rule.
- `DG.gha`, the shell template and the `catalogue.json` calculators are unchanged (no file of those changed).

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. The new read (`RULE_STRUCTURE_QUERY`) and the class-category read bind `$project`; the new write (`PARTICIPANT_CLASS_QUERY`) is the existing class/edge merge plus two edge properties and is bound to `$project` and the calculator row.

## Open items

- `RULE_STRUCTURE_QUERY` and `CLASS_CATEGORIES_QUERY` ran only against the fake session (as the plan specifies); the live graph pass (head ARG edges, `collect` of arg maps, `hasMinProjectionClearanceMm` reading Beam against Slab/Column/Wall) is for plan 1303-23. A rule whose head atom has no readable position-1 Var now has no subject, so `resolve` finds no box class for it and `ensure_rule_classes` reports `no subject`; rules ingested before the head was written would show up there.
- The mismatch warning compares class labels only; a calculator that reads a participant implicitly (a helper such as `ctx.host_walls` without an `OST_` constant) shows that participant as `missing`.
- `spec/LPG-OWL-MAPPING.md` has no mention of the edge properties (see deviation 4).

## Self-Check: PASSED

Commits a7cedcc, 2fd96e5, beee628, 6ac2153, 3e36e76, 41b31b2 exist; all modified files present.
