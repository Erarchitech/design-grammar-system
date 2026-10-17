---
phase: 1303-pravilo-gh-obekt
plan: "01"
status: complete
completed: 2026-10-17
requirements: [DGMAP-01, DGMAP-02, DGMAP-03, DGMAP-04, DGMAP-05]
executor: controller (inline; wave-1 subagent for this plan stopped on a rate limit before writing anything)
---

# 1303-01 Summary — deterministic mapping engine

## What was built

`data-service/mapping_engine.py` (standard library only, no Neo4j/HTTP/clock/random/LLM) with:

- constants `ENGINE_VERSION = "dgmap-0.1"`, `CONFIG` (values exactly as planned: prior −1.0, satisfied rule 2.5 capped at 4.0, violated −1.5, candidate 0.6, clear 0.8, margin 0.3, profile auto 0.8, α 4, β 1), `SELECTOR_FEATURES`, `DROP_ORDER`, `PROPERTY_ALIASES`, `BUILTIN_TO_REQUIRED` (violation-pattern inversion incl. `equal → !=`);
- `ClassInfo`, `Constraint`, `Evidence`, `MappingInputError(code, detail, status)`;
- evidence: profiles (with excluded roles), name tokens (acronym, subsequence, word/synonym tokens, capped), rule consistency, IFC hints, population match at base-group level;
- `compute(...)`, `decide(...)`, `induce_profile(...)`, `merge_profiles(...)`, `partition(...)`, `populations_of(...)`, `evaluate_against_gold(...)`, `profile_confidence(...)`, `constraints_from_rows(...)`, `constraints_from_swrl(...)`, `canonical_json(...)`.

## Public API (for plan 1303-02)

```python
compute(descriptors, classes, constraints, profiles=(), disjoint=(), populations=None,
        platform_default="grasshopper", config=None, decided=None, splits=None,
        rule_classes=None) -> dict
# returns {engineVersion, platform, summary, questions, groups, elements, decided, splits}
#   decided: nativeId -> [classIri] confirmed by a human in this session ([] = none)
#   splits:  nativeId -> [feature] requested by a split answer
#   rule_classes: class -> [ruleId] for rules without numeric constraints (rule impact)

decide(result, descriptors, question_id, option_id, actor, at, classes,
       group_ids=None, roles=None, profiles=(), project=None,
       platform_default="grasshopper", config=None) -> dict
# returns {decisions: [MappingDecision], profiles: [new/updated MappingProfile],
#          decided: {nativeId: [classIri]}, splits: {nativeId: [feature]}}
# The caller merges `decided`/`splits` into the stored result, merges profiles
# (merge_profiles), and recomputes with compute(..., decided=..., splits=...).
# option "custom" + roles is accepted for explicit role lists.

partition(result) -> {applied, byClass, elements, skipped}       # MappingApplyResult body
populations_of(result) -> {classLocal: count}                    # for context.populationsFromSessionId
```

Deviations from the plan text (shape only, behaviour as planned): `decide` returns a dict instead of a tuple, because the caller also needs the `decided` and `splits` additions; `compute` takes `decided`, `splits` and `rule_classes`; the result echoes `decided` and `splits` so a stored result is enough to recompute. Decisions additionally carry `memberIds`. Design signals carry an extra `accepted` flag.

## Behaviour verified

- V1 cold start: exactly 2 questions — `batch-assign` over BottomTriangularPanel 125 / GlassPanel 125 / HexagonalUnit 100 / Facade 1 and `mapping-or-design` for the 25 pentagons (options `class:ex:GroundFloorUnit`, `design-error:ex:HexagonalUnit`, `both`, `none`); EN text "25 elements from HU (5 vertices). As HexagonalUnit: R_HEX_HASVERTEXCOUNT_REQ_6_V violated ×25, … As GroundFloorUnit: … passes ×25. Mapping error or design error?" and the RU equivalent.
- After both answers: 376 confirmed; 5 learned profiles; a fresh session maps all 376 `auto`, precision/recall 1.0 per class.
- V2 (57 narrow, 12 steep panels): 0 questions, all `auto`, width/aspect violations only as design signals.
- Window/Wall with equal evidence: `disambiguate` with `both`; declared disjoint → no `both`, stays ambiguous until one class is chosen.
- Revit-like read (all Generic Models / IfcBuildingElementProxy): 5 groups by family, ≤ 5 questions, hex modules get `both` = FacadeModule + HexagonalUnit; a second read with the learned profiles: 0 questions, P/R 1.0.
- Profile confidence 5/6 auto, 5/7 queued; a contradicting answer adds a rejection to the matching profile and the design-error profile records `acceptsViolations`.
- Determinism (including shuffled input), robustness and error codes.

## Verification

- `python -m pytest data-service/tests/test_mapping_engine.py -q` → **15 passed** (host Python 3.14.2).
- `python -m pytest tools/de01/tests/test_reproducibility_scope_drift.py -q` → **8 passed** (no new LLM call site).
- `py -3.11` AST parse of the three files and a runtime `compute` on V1 → OK (container version).

## Files

- `data-service/mapping_engine.py` (new)
- `data-service/tests/mapping_fixtures.py` (new; rule rows embedded; `test_fixture_rules_match_rules_approved_json` checks them against `test/v12-hexagonal-facade-01/rules-approved.json` and skips when that file is not mounted, e.g. in the container)
- `data-service/tests/test_mapping_engine.py` (new)

## Refinement after review (2026-10-17, same day)

While writing the Grasshopper intake (plan 03) it became clear that class-agnostic measurement gives range-only classes (GlassPanel: four range rules) more satisfied rules than a class with one exact signature (BottomTriangularPanel: vertex count = 3). Rule evidence is therefore weighted by specificity: equality satisfied +2.5 / violated −1.5, range satisfied +0.75 / violated −2.0 (cap 4.0); and a `mapping-or-design` question is raised whenever, of the two leading candidates within the margin, one violates its rules while the other is rule-consistent (either order). New regression test `test_range_rules_do_not_outvote_a_signature`; all engine tests still pass (16).

## Open issues

- Real Revit family names are unknown; Revit synonyms are configuration (`context.vocabulary`) to be authored in plan 06 from the actual model.
- Rule impact lists every rule of a class; very large rule sets would make question text long (not an issue for the facade's 12 rules).
