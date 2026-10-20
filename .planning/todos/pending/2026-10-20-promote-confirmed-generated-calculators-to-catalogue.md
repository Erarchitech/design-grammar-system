---
created: 2026-10-20T20:30:00.000Z
title: Promote confirmed generated calculators to the catalogue
area: planning
severity: major
files:
  - data-service/property_scripts.py
  - data-service/property_calculator_llm.py
  - data-service/property_calculator_store.py
  - data-service/property_calculators/catalogue.json
  - data-service/dg_knowledge.py
  - .planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md
---

## Problem

The property-calculator catalogue of plan 1303-15 (`data-service/property_calculators/catalogue.json` plus templates) is static. It grows only when someone edits it by hand.

A calculator the LLM writes for an uncovered property:
- is checked for safety only, through the AST contract in `property_calculator_llm.validate_function`;
- is not checked for correctness;
- stays in one project (`PropertyCalculator`, `origin: generated`).

The ingest vocabulary lists catalogue properties only, so new concepts get invented, inconsistent names. Seen live: `hasMinHostOpeningClearanceMm`.

## Solution

Owner decision D-54 (2026-10-20, `1303-CONTEXT.md`): **promotion after confirmation.**

1. After a run, show the operator each generated calculator: its source, the values on sample boxes, the rule verdicts. Offer confirm / reject in the Web UI Mapping panel and in a DeGram `degram_property_check` action.
2. On confirm, copy it into a shared Neo4j catalogue, e.g. `(:CatalogueCalculator)`. Store source, sha256, property name, unit, read categories, and provenance: project, run, confirmedBy/At.
3. Add its property to `SWRL_CONVENTIONS.computable_form.computable_properties` (`dg_knowledge`) so that ingest reuses the name.
4. On reject, set `status: rejected` and regenerate the property or report it unsupported.
5. New resolution order in `property_scripts.resolve`: file catalogue → shared catalogue → project-stored → LLM.
6. Schema propagation for the new node and its relationships: `spec/DATABASE.md`, `spec/LPG-OWL-MAPPING.md`. Route rows in `route_policy.py` and `spec/SECURITY-BOUNDARY.md`.

Start with `/gsd-plan-phase 1303` as a new plan 1303-16, in the worktree `C:\Users\Admin\source\repos\dg-mapping` on branch `feature/mapping-mvp`.
