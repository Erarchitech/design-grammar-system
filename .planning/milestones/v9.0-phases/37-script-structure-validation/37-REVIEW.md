---
phase: 37-script-structure-validation
reviewed: 2026-07-27T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - data-service/app.py
  - data-service/cg_structure_checks.py
  - data-service/dg_context.py
  - data-service/tests/README.md
  - data-service/tests/cg_fixtures.py
  - data-service/tests/conftest.py
  - data-service/tests/consult_cassette.py
  - data-service/tests/test_cg_fixtures.py
  - data-service/tests/test_cg_structure_checks.py
  - data-service/tests/test_computgraph_consult.py
  - llm/structure_rules.json
  - spec/API.md
  - spec/RULE-PARTITION-POLICY.md
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 37: Code Review Report

**Reviewed:** 2026-07-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 37 adds two new read-only endpoints (`POST /computgraph/validate`, `POST /computgraph/consult`), a new deterministic Cypher-based structural checker module (`cg_structure_checks.py`), a declarative rule-mapping artifact (`llm/structure_rules.json`), a live-subgraph consult pipeline in `dg_context.py`, and the associated test/fixture infrastructure. The actual diff against `069e8f8` (confirmed via `git diff --stat`/`git diff`) is scoped exactly to what the file list implies: ~95 new lines in `app.py` (two routes), ~900 new lines in `cg_structure_checks.py` (new file), ~440 new lines appended to `dg_context.py`, plus the new test/spec files.

Security posture is solid: every Cypher statement in the new code is parameterized (no f-string/`.format`/`%` interpolation of `project`/`definitionId`/`label`/`namePattern` into query text), the `forbidsOrphan` `label` parameter is checked against a fixed allow-list before it ever reaches a bound Cypher parameter, and the consult pipeline never executes anything derived from the LLM's output. Determinism guarantees (byte-identical `findings`/`ruleResults` across repeated calls) are also correctly implemented and covered by both host-tier and integration-tier tests.

The one real functional defect is that the report's `counts.warning` bucket is effectively dead code: no structural check ever emits `SEVERITY_WARNING`, and `ruleResults` (the rule-mapped SVAL-02 results) are never rolled into `counts` at all — despite `spec/RULE-PARTITION-POLICY.md`'s own new "Computgraph Structural Checks" section explicitly declaring "a rule-mapped structural requirement that fails" to be `warning` severity, and `spec/API.md`'s own worked example showing `"warning": 1` for a payload that, run through the real code, would always compute `"warning": 0`. There is also a validation gap in the structure-rule-mapping loader that lets a malformed mapping entry silently evaluate to an always-passing (rather than rejected) result.

## Critical Issues

### CR-01: `counts.warning` never reflects rule-mapped check failures — contradicts the documented severity model

**File:** `data-service/cg_structure_checks.py:33, 887-901`
**Also affects:** `spec/API.md:79-114`, `spec/RULE-PARTITION-POLICY.md:80-83`

**Issue:** `SEVERITY_WARNING = "warning"` is defined (line 33) but is never assigned to any finding produced by any of the seven `check_*` functions — only `SEVERITY_VIOLATION` (checks 1–6) and `SEVERITY_INFO` (`check_annotation_conventions`) are ever used. `build_validation_report()`'s `counts` dict is computed exclusively from `findings[]`:

```python
counts = {SEVERITY_VIOLATION: 0, SEVERITY_WARNING: 0, SEVERITY_INFO: 0}
for finding in findings:
    severity = finding["severity"]
    if severity in counts:
        counts[severity] += 1
```

`ruleResults[]` (the SVAL-02 rule-mapped results) is not consulted here at all, and a `ruleResults` entry doesn't even carry a `severity` field — only `passed: bool`. The practical effect: **`counts.warning` is always `0` in every real response, no matter how many rule-mapped requirements fail.**

This is inconsistent with two other files in this same review:
- `spec/RULE-PARTITION-POLICY.md`'s new "Computgraph Structural Checks (Phase 37)" section states plainly: `` `warning` -- a rule-mapped structural requirement that fails while the graph itself is well-formed `` (line 82) — i.e. the normative policy doc asserts rule-mapped failures ARE warning-severity and should surface as such.
- `spec/API.md`'s worked example response for `POST /computgraph/validate` shows one failing `ruleResults` entry (`"passed": false`) alongside `"counts": {"violation": 1, "warning": 1, "info": 0}` (line 104) — implying the failing rule result is what produced `warning: 1`. Run the real code against an equivalent report and `counts.warning` would be `0`, not `1` (nothing in `findings[]` in that example has `severity: "warning"`).

A future consumer (the deferred ui-v2 panel `spec/API.md` names, or a Grasshopper canvas badge) that trusts `counts.warning` as a "how many rule-mapped requirements are failing" signal will silently see `0` even when `ruleResults` contains failures — the kind of quietly-wrong aggregate that is worse than an error, because nothing signals it's wrong.

**Fix:** Either (a) roll `ruleResults` failures into `counts.warning` inside `build_validation_report()` so the documented behavior is actually implemented:

```python
counts = {SEVERITY_VIOLATION: 0, SEVERITY_WARNING: 0, SEVERITY_INFO: 0}
for finding in findings:
    severity = finding["severity"]
    if severity in counts:
        counts[severity] += 1
counts[SEVERITY_WARNING] += sum(1 for r in rule_results if not r["passed"])
```

or (b) if `counts` is intentionally findings-only (as `spec/API.md:114`'s prose — "aggregated over `findings[]`" — actually already says), fix the two docs instead: drop the "warning" severity claim for rule-mapped failures from `RULE-PARTITION-POLICY.md`'s addendum (or reword it to state clearly that rule-mapped failures are NOT reflected in `counts`), and fix `spec/API.md`'s worked example so `counts.warning` is `0`, matching what the code actually returns. Either way, the current state — a normative policy doc, a worked API example, and the implementation all disagreeing with each other — needs to be resolved to one true behavior before this ships.

## Warnings

### WR-01: Structure-rule mapping validation doesn't require the operation-specific param a mapping needs to be meaningful

**File:** `data-service/cg_structure_checks.py:418-444` (`_mapping_rejection_reason`), `539-596` (`_eval_requires_procedure`/`_eval_requires_parameter`), `625-646` (`_eval_forbids_orphan`)

**Issue:** `_mapping_rejection_reason()` validates `ruleId`, `operation`, that `params` (if present) is a dict, that no forbidden value-threshold key is present, and — only for `forbidsOrphan` and only when a `label` key is actually present in `params` — that `label` is in the allow-list. It never checks that:
- `requiresProcedure` / `requiresParameter` mappings actually supply a non-empty `namePattern`
- `forbidsOrphan` mappings actually supply a `label` at all (an entry that omits the `params.label` key entirely, or the whole `params` object, skips the allow-list check because the check is nested inside `if label is not None`)

Downstream, both evaluators use `.get(..., "")`-style defaults for these:
```python
name_pattern = params.get("namePattern", "")   # _eval_requires_procedure / _eval_requires_parameter
label = params.get("label", "")                 # _eval_forbids_orphan
```
- `requiresProcedure`/`requiresParameter` with a missing `namePattern`: the Cypher template does `WHERE pr.procedureName CONTAINS $namePattern` — `CONTAINS ''` is true for every string in Cypher, so the rule silently **passes as long as any Procedure/Parameter at all exists** in the definition, regardless of what the rule was actually supposed to require.
- `forbidsOrphan` with a missing `label`: the Cypher template does `WHERE $label IN labels(n)` with `label = ""` — no node ever has an empty-string label, so the rule silently **always passes**, i.e. the orphan check that was supposed to run never actually checks anything.

Neither case is surfaced as a rejected mapping (`_rejected_mapping_result`) the way an invalid `operation` or a forbidden `params` key is — it just quietly produces a wrong-but-plausible-looking `passed: true` result. The real, shipped `llm/structure_rules.json` happens to supply these params correctly for all four mappings today, so this isn't currently live-firing, but it's an unguarded footgun for the very next mapping someone adds by hand.

**Fix:** Extend `_mapping_rejection_reason()` to require the operation-specific mandatory param:
```python
if operation in ("requiresProcedure", "requiresParameter"):
    if not isinstance(params, dict) or not (params.get("namePattern") or "").strip():
        return f"operation {operation!r} requires a non-empty params.namePattern"
if operation == "forbidsOrphan":
    label = params.get("label") if isinstance(params, dict) else None
    if not label:
        return "operation 'forbidsOrphan' requires params.label"
    if label not in _COMPUTGRAPH_ORPHAN_LABELS:
        return f"label {label!r} is not a recognized Computgraph entity label"
```

### WR-02: `spec/API.md`'s `/computgraph/validate` worked example doesn't match what the implementation actually produces

**File:** `spec/API.md:79-101`

**Issue:** Three separate mismatches between the documented example JSON and the real response shape:
1. The `ruleResults[0].message` text — `"Rule R_STRUCT_FRAME_TRUSS requires a Procedure matching 'Truss' under Algorithm 1, none found."` — is not a format any evaluator in `cg_structure_checks.py` produces. Every real message goes through `_compose_message(what, where, how_to_fix)`, e.g. `_eval_requires_procedure`'s real failure message reads `"No Procedure matching 'Truss' was found. Where: Procedures scoped to definitionId=frame.gh. How to fix: tag a Procedure whose name contains 'Truss' and re-publish."` — a completely different sentence structure than the doc example.
2. `offendingEntities[0]` in the example (`{"label": "Algorithm", "cgId": null, "name": "1"}`) is missing the `conventionName` key — but the prose two lines above (line 113) documents `ruleResults[]`'s entities as using the same shape the `findings[]` section (line 108) already pins as `label, cgId, name, conventionName`, and every real entity dict built by `_entity()`/`_offending_algorithms()` always includes all four keys.
3. `cgId: null` in that same example entity contradicts `_entity()`'s actual contract, which always returns a string (`""` for Algorithm entities, which carry no cgId in the Phase 36 contract — never `null`/`None`).

**Fix:** Regenerate the worked example from an actual `POST /computgraph/validate` response (e.g. adapt `test_cg_structure_checks.py`'s `_canned_report()`/`_canned_rule_result()` fixtures, which already use the real message format and entity shape) so a reader copying this example gets a structurally accurate contract.

## Info

### IN-01: Two module-level constants are computed/defined but never used anywhere

**File:** `data-service/cg_structure_checks.py:37-45` (`CHECK_IDS`), `469` (`STRUCTURE_RULE_IDS`)

**Issue:** `CHECK_IDS` (the seven checkId strings) and `STRUCTURE_RULE_IDS` (derived ruleId index, computed once at import time via `structure_rule_ids()`) are both defined with descriptive docstrings implying they're meant to be consulted (mirroring `dg_context.py`'s `CYPHER_SHAPE_IDS` / `reasoner.py`'s `REASONER_IDS` precedent they explicitly cite), but neither is imported or referenced anywhere else in `data-service/` or `data-service/tests/` (confirmed via project-wide grep). They're currently dead exports.

**Fix:** Either wire them into an actual consumer (e.g. a request-time validation that a submitted `checkId`/`ruleId` filter is one of the known values), or drop them if they're not needed yet — a constant computed at import time purely for symmetry with a sibling module's pattern, with no reader, is a maintenance trap (it'll silently go stale the next time a check or mapping is added/removed).

### IN-02: `except ValueError` branch in `post_computgraph_validate` is presently unreachable

**File:** `data-service/app.py:1458-1464`

**Issue:** `post_computgraph_validate()`'s `except ValueError` clause mirrors `post_computgraph_publish()`'s error-handling shape (`ComputgraphValidateRequest`'s own docstring says as much: "matching `ComputgraphPublishRequest`'s plainness"), but unlike `computgraph_publish.publish_structure()` (which does raise `ValueError` for malformed input), neither `cg_structure_checks.build_validation_report()` nor anything it calls (`resolve_definition_id`, `run_structural_checks`, `evaluate_rule_mappings`) ever raises `ValueError` — the only structured error path out of that delegate is `DefinitionResolutionError`, already caught above it. This branch is currently dead unless the underlying `neo4j` driver itself happens to raise a bare `ValueError`.

**Fix:** No action required if this is intentional forward-compatibility (matching the sibling route's shape in case a future validator is added). If not, it can be removed, or a comment could note it's deliberately defensive/currently unreachable so a future reader doesn't waste time tracing a path that never fires.

---

_Reviewed: 2026-07-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
