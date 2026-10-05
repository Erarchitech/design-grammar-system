---
tags: [debugging, ingest, llm, n8n, metagraph, open]
date: 2026-10-05
status: open
---

# Rule ingest blends a rule invented from a bare Rule_Id into the existing rule (F13, with F6/F9/F11/F12)

## Symptom (test v12-hexagonal-facade-01, step 3c)

A delete command reached the pipeline in **Ingest** mode as the bare string `R_OUTLINE_HASGAPCOUNT_MAX_0_V`. Ingest did not reject it:

- the LLM invented a rule from the ID (`Facade(?f) ^ hasGapCount(?f, ?val) ^ greaterThan(?val, 0)`);
- the generated Cypher `MERGE`d onto the existing `Rule_Id`;
- result: atom `_A1` had two `REFERS_TO` (Facade **and** HexagonalUnit), every atom had duplicated `ARG`s (`?e` and `f`), new Vars had no `?`, the SWRL was overwritten, and the atom types were kept from the old rule;
- the preview/conflict check did not stop it.

The UI delete (Graph → Edit → `delete <id>`, `DELETE /rules/{project}/{ruleId}`) cleaned the blended rule completely: 4 atoms plus 2 orphan Vars, with shared args kept. The delete is not logged in `DesignRuleSession`.

## Related ingest findings from the same run

- **F6:** ingest writes `MERGE (r:Rule {Rule_Id, project})`, so any `Rule_Id` collision silently merges two rules. F13 is the real-world case.
- **F9:** an explicit Rule ID in the rule text is ignored. The LLM invents its own, and the threshold format is unstable (`1.3`, `0_01`, `0p005`). Heads are invented DatatypeProperties (`aspectRatioBelowMin(?x, true)`) instead of `violation(?x)` and land in the OntoGraph.
- **F10:** the Edit-mode delete-by-name regex `\bR_[A-Z0-9_]+\b` (`GraphScreen.jsx:637`) cuts IDs containing a dot.
- **F11:** the LLM adds redundant builtins (`≥ 0 ∧ > 0`). This is harmless but breaks "exactly 3 body atoms" checks.
- **F12:** without hints, "ground floor module" was matched to the existing `HexagonalUnit` by the shared word "module". The pipeline prefers reusing a class to creating one and does not warn. With both classes present (R11), recognition was correct.

## Proposed fixes

1. Reject ingest input with no rule content.
2. When writing to an existing `Rule_Id`, delete the old atoms first or refuse, instead of `MERGE`.
3. Put `?` on Var names.
4. Honour an explicit Rule ID in the text.
5. Include dots in the UI regex.

## Related

- [[sessions/2026-10-05 v12 hexagonal facade test steps 2-8 and five DG fixes]]
- [[knowledge/decisions/Architect rules are reshaped to the v12 evaluator boundary before ingest]]
