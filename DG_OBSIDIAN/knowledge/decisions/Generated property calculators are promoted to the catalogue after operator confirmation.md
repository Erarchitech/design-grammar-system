---
tags: [decision, phase-1303, plan-1303-15, property-calculators, llm, catalogue]
date: 2026-10-20
---

# Generated property calculators are promoted to the catalogue after operator confirmation

## Context

Plan 1303-15 (MEP opening boxes checked against structural rules) lets Design Grammars compute the properties its rules test from the Revit model. Calculators come from three sources, in this order:

1. The vetted file catalogue, `data-service/property_calculators/catalogue.json` plus `*.py.tmpl` templates. It holds 3 calculators, 6 aliases and a 6-property vocabulary.
2. A calculator stored for the project in Neo4j (`PropertyCalculator`).
3. A calculator the LLM writes for a property nothing else covers (`property_calculator_llm.py`).

The file catalogue is static and grows only by hand. A generated calculator is checked for safety only, through an AST contract: no imports, no transactions, no Revit writes. Nothing checks that it computes what the rule means, and it stays in one project.

The ingest prompt names properties from the catalogue vocabulary only. For a new concept the LLM therefore invents a name. Seen live: `hasMinHostOpeningClearanceMm` next to the vocabulary's `hasMinOpeningClearanceMm`.

## Decision (owner, 2026-10-20)

**Promotion after confirmation.** A generated calculator joins a shared catalogue only after an operator confirms its result on a real model.

1. After a run, the operator sees the calculator's source, the values it produced on sample elements and the rule verdicts, then confirms or rejects it. This happens in the Web UI or through a DeGram tool.
2. A confirmed calculator moves to a shared catalogue in Neo4j. It keeps its source, sha256, property name, unit, the Revit categories it reads and its provenance: project, run, confirmedBy/At.
3. Its property joins the ingest vocabulary (`SWRL_CONVENTIONS.computable_form.computable_properties`). Later rules and projects then reuse it by name, without asking the LLM.
4. A rejected calculator is retired (`status: rejected`). Its property is then regenerated or reported unsupported.
5. The file catalogue stays the vetted seed and the Neo4j catalogue extends it. Resolution order: file catalogue → shared catalogue → project-stored → LLM generation.

## Rationale

- An LLM-written calculator is safe to run but not proven right. A person comparing its output on a known model is the cheapest correctness check, the same check as Act 4's gold comparison.
- Without promotion every project pays the LLM again and gets differently named properties for the same concept. Promotion turns one confirmed answer into shared, deterministic vocabulary.

## Status

Not built. To be planned and executed in the next session: todo `.planning/todos/pending/2026-10-20-promote-confirmed-generated-calculators-to-catalogue.md`, decision D-54 in `.planning/phases/1303-pravilo-gh-obekt/1303-CONTEXT.md`.

Related: [[Phase 1303 mapping MVP]]
