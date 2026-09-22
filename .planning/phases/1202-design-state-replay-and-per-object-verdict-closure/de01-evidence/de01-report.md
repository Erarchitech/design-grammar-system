# DE-01 Cross-Service Evidence Report

**Verdict:** PASS
**silent_disagreement_count:** 0
**Fixture version:** 1.0.0
**Contract version:** 1.0.0
**Generated:** 2026-09-22T13:02:04Z

Acceptance rule (spec/EVIDENCE-CONTRACT.md section 8, D-14): a silent disagreement is a failure; a declared non-equivalence is not.

## Per-leg availability

| Leg | Available | Service | Version | Stage | Error |
|---|---|---|---|---|---|
| csharp | True | dg-core-evaluator | 1.0.0.0 | de01.csharp-leg.evaluate |  |
| data-service | True | data-service | 1.0.0 | validation.publish |  |
| dg-reasoner | True | dg-reasoner | unknown | shacl.validate |  |
| replay | True | data-service | 1.0.0 | validation.view.replay |  |

## Comparison rows

| ruleId | objectId | csharp | data-service | dg-reasoner | replay | classification | reason |
|---|---|---|---|---|---|---|---|
| R_GOLD_HEIGHT_MAX_75_V | OBJ_GOLD_EMPTY | no_population | no_population | not_evaluated | no_population | declared_non_equivalence | dg-reasoner: What: SHACL validated structural conformance for OBJ_GOLD_EMPTY and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems. |
| R_GOLD_HEIGHT_MAX_75_V | OBJ_GOLD_FAIL | failed, unsupported | failed | not_evaluated | failed | declared_non_equivalence | dg-reasoner: What: SHACL validated structural conformance for OBJ_GOLD_FAIL and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems.; csharp: What: atom 'R_GOLD_HEIGHT_MAX_75_V_A4' (ObjectPropertyAtom, belongsToDistrict(?b, ?d)) has no resolvable type on the C# leg. Where: DG.Core.Parsing.SwrlRuleParser.ResolveAtomType has no ObjectPropertyAtom branch (returns only BuiltinAtom/ClassAtom/DataPropertyAtom). How to fix: Phase 1201's ALGN12-05 adds the missing branch. This is a pre-declared, by-design non-result -- see fixtures/golden/MANIFEST.md 'Expected non-results by design' -- not a fixture defect or a DE-01 failure. |
| R_GOLD_HEIGHT_MAX_75_V | OBJ_GOLD_PASS | passed | passed | not_evaluated | passed | declared_non_equivalence | dg-reasoner: What: SHACL validated structural conformance for OBJ_GOLD_PASS and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems. |

## Declared non-equivalences

| ruleId | objectId | statuses | reason |
|---|---|---|---|
| R_GOLD_HEIGHT_MAX_75_V | OBJ_GOLD_EMPTY | no_population, not_evaluated | dg-reasoner: What: SHACL validated structural conformance for OBJ_GOLD_EMPTY and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems. |
| R_GOLD_HEIGHT_MAX_75_V | OBJ_GOLD_FAIL | failed, not_evaluated, unsupported | dg-reasoner: What: SHACL validated structural conformance for OBJ_GOLD_FAIL and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems.; csharp: What: atom 'R_GOLD_HEIGHT_MAX_75_V_A4' (ObjectPropertyAtom, belongsToDistrict(?b, ?d)) has no resolvable type on the C# leg. Where: DG.Core.Parsing.SwrlRuleParser.ResolveAtomType has no ObjectPropertyAtom branch (returns only BuiltinAtom/ClassAtom/DataPropertyAtom). How to fix: Phase 1201's ALGN12-05 adds the missing branch. This is a pre-declared, by-design non-result -- see fixtures/golden/MANIFEST.md 'Expected non-results by design' -- not a fixture defect or a DE-01 failure. |
| R_GOLD_HEIGHT_MAX_75_V | OBJ_GOLD_PASS | not_evaluated, passed | dg-reasoner: What: SHACL validated structural conformance for OBJ_GOLD_PASS and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems. |

## Status tally by leg

| Leg | Tally |
|---|---|
| csharp | failed=1, no_population=1, passed=1, unsupported=1 |
| data-service | failed=1, no_population=1, passed=1 |
| dg-reasoner | not_evaluated=3 |
| replay | failed=1, no_population=1, passed=1 |

## Canonical state hash comparison

**Agreement:** agree
**Fixture expected hash:** 3D2D5EDF750FEA213CFB564E424C61F029220F2BF93B0B227EE6FEEC4F55A428

| Leg | Present | Hash | Canonicalization version | Matches expected | Reason |
|---|---|---|---|---|---|
| csharp | True | 69D4289C722DE31B42D57E5F3C41BAB39272BE7DAC8957870512EC86C0707A84 | 1 | False | |
| data-service | False | | | | the data-service leg does not capture or report a Design State (Open Question 2 -- see LegResult.state_hash's docstring) |
| dg-reasoner | False | | | | the dg-reasoner leg does not capture or report a Design State (Open Question 2 -- see LegResult.state_hash's docstring) |
| replay | True | 69D4289C722DE31B42D57E5F3C41BAB39272BE7DAC8957870512EC86C0707A84 | 1 | False | |

## Warnings appendix

- **dg-reasoner** / R_GOLD_HEIGHT_MAX_75_V / OBJ_GOLD_EMPTY:
  - What: SHACL validated structural conformance for OBJ_GOLD_EMPTY and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems.
- **csharp** / R_GOLD_HEIGHT_MAX_75_V / OBJ_GOLD_FAIL:
  - What: atom 'R_GOLD_HEIGHT_MAX_75_V_A4' (ObjectPropertyAtom, belongsToDistrict(?b, ?d)) has no resolvable type on the C# leg. Where: DG.Core.Parsing.SwrlRuleParser.ResolveAtomType has no ObjectPropertyAtom branch (returns only BuiltinAtom/ClassAtom/DataPropertyAtom). How to fix: Phase 1201's ALGN12-05 adds the missing branch. This is a pre-declared, by-design non-result -- see fixtures/golden/MANIFEST.md 'Expected non-results by design' -- not a fixture defect or a DE-01 failure.
- **dg-reasoner** / R_GOLD_HEIGHT_MAX_75_V / OBJ_GOLD_FAIL:
  - What: SHACL validated structural conformance for OBJ_GOLD_FAIL and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems.
- **dg-reasoner** / R_GOLD_HEIGHT_MAX_75_V / OBJ_GOLD_PASS:
  - What: SHACL validated structural conformance for OBJ_GOLD_PASS and found no violation, but has no opinion on rule R_GOLD_HEIGHT_MAX_75_V's quantitative condition. Where: spec/RULE-PARTITION-POLICY.md assigns quantitative rules (e.g. this fixture's 'height > 75') to the SWRL VALIDATOR, not SHACL -- dg-reasoner/reasoning.py::run_shacl's pySHACL pipeline cannot express this comparison. How to fix: nothing to fix here -- this is a declared non-equivalence, not a defect. Encoding the height rule as a SHACL shape to force agreement with the other legs would violate the rule-partition policy by evaluating the same business rule twice in two systems.
