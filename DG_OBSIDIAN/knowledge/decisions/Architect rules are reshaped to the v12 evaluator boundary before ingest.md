---
tags: [decision, swrl, validator, test, facade]
date: 2026-10-03
status: accepted
---

# Architect rules are reshaped to the v12 evaluator boundary before ingest

## Context

During the guided full-cycle test `v12-hexagonal-facade-01`, the architect supplied six facade rules (A1, A2, B1, B2, C1, D1). They were written as general SWRL, mixing generative, classification and validation rules. The shipped C# evaluator is a bounded subset (`spec/SWRL-SUBSET.md`). When rules were ingested as written, they either got a typed refusal (`unsupported`) or, worse, false `failed` verdicts.

## Decision

Before ingest, every rule is rewritten into the single shape the evaluator can actually decide:

`Class(?x) ^ dataProperty(?x, ?v) ^ swrlb:<comparison>(?v, literal) -> violation(?x)`

| Rule as written | What happens if ingested as written | Rewrite |
|---|---|---|
| Range `2 ≤ x ≤ 4` (D1 plus a lower bound) | The body has no OR, so the range cannot be expressed in one rule | **Two** violation rules: `x < 2` and `x > 4` |
| Relational atoms (`hasVertex(?u,?v)`, B1) | ObjectPropertyAtom → `unsupported` | Numeric deviation per object (`hasLevelOffsetM`) |
| Informal constraint (B2 symmetry) | Not formalized | Numeric deviation per object (`hasSymmetryDeviationM`) |
| String literal inside a data atom (C1 `"TriangularBottom"`) | The literal is never compared, so **every** panel `failed`. PROPERTY STATE also cannot carry strings | Integer proxy: `hasVertexCount ≠ 3` |
| Generative rules (A1, A2) | `unsupported` / nothing to evaluate | Excluded from Metagraph. They belong to Computgraph. A1 is kept only as a control that must show `unsupported` |

Further constraints observed in code (`DesignStateBindingService`):
- **One object variable per rule.** Each ObjState builds its own binding row.
- **Class names must match exactly across rules.** Each class is its own OBJECT STATE fed from METAGRAPH `OntologyClass`.
- **PropState is bound to a single rule.** A value shared by two rules needs two PROPERTY STATEs.

## Consequences

- The approved set is 8 rules over 4 classes: `test/v12-hexagonal-facade-01/RULES.md`, `rules-approved.json`.
- Thresholds are calibrated on the baseline variant **before** ingest (test step order 3a → 3b → 3c).
- This rewrite is manual. If the ingest LLM itself warned about the five cases in the table, it would remove a class of silent false verdicts. That is a candidate feature for the rule-ingest preview.

Related: [[sessions/2026-10-04 v12 hexagonal facade full-cycle test setup]], [[knowledge/decisions/Evidence v2 preserves rule outcomes and keeps legacy projections separate]]
