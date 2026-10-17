---
tags: [debugging, mapping, swrl, phase-1303]
date: 2026-10-17
status: resolved
---

# Rule body comparisons must be evaluated as one conjunction (R9)

**Symptom.** In the dress rehearsal on the real graph of `v12-hexagonal-facade-01`, the mapping engine marked every closed hexagon as violating R9. That produced negative rule evidence against the obvious class.

**Cause.** The live R9 body has two comparisons on the same variable: `greaterThanOrEqual(?count, 0) ^ greaterThan(?count, 0)`. DG uses the violation pattern, so the body fires when the constraint is violated. The engine inverted each comparison on its own, which turned them into a "satisfied" condition of `count < 0`. No element can meet that, so every element "violated" the rule. The synthetic fixtures had only one comparison per rule, which is why this did not show up earlier.

**Fix (`a0cead0`).** `rule_groups` in `data-service/mapping_engine.py` collects all comparisons of one rule body. A rule counts as violated only when **all** of its comparisons hold (conjunction). The test `test_rule_body_is_a_conjunction` covers this. data-service was rebuilt from a clean `git archive`.

**Rule.** Any code that derives constraints from SWRL bodies (mapping evidence, explanations, SHACL generation) must treat the body as one conjunction. It must not invert atoms one at a time. Before trusting fixtures, check the real rules (`MATCH (r:Rule {project:$p})-[:HAS_BODY]->(a:Atom)`).

Related: [[knowledge/decisions/Automated mapping MVP uses group questions and learned profiles (Phase 1303)|mapping decision]], `spec/SWRL-SUBSET.md`.
