"""Pure scoring functions for the four candidate-set SC1 metrics (Phase 38
plan 07, closing the Phase 35 "shipped plumbing, never measured quality"
failure mode -- 38-RESEARCH.md's Nyquist note).

No I/O, no LLM, no Neo4j -- every function here takes plain dicts/lists
already produced by `cg_input_generation.generate_inputs()` and returns a
number. Each function's docstring quotes the exact threshold it is measured
against from `spec/API.md`'s SC1 acceptance-thresholds table, so a reader
can see the target without opening the spec.

**`validate_candidate`/`normalized_distance` are imported from
`cg_input_sampler`, never reimplemented here.** SC1-a and SC1-d must use the
SAME definition of "in-domain/step-aligned" and "distance" the runtime uses
-- a second implementation of either would let this harness and the product
disagree about what "valid" means, which is exactly the gap this plan exists
to close.

SC1-c ("valid candidates returned when the LLM tier is stubbed to return
nothing usable") is a property of a whole `generate_inputs()` run (which
tier shipped, and whether that tier's candidates are non-empty and
domain-valid) rather than of a candidate set in isolation, so it is asserted
directly in `test_input_gen_eval.py` and has no `score_*` function here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# data-service/tests/input_gen_eval/scoring.py -> parents[2] == data-service/,
# where cg_input_sampler.py lives. Inserted defensively (mirrors
# recognition_eval/scoring.py's own convention) so this module imports
# correctly regardless of the invoking test's cwd/sys.path setup.
_DATA_SERVICE_ROOT = str(Path(__file__).resolve().parents[2])
if _DATA_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _DATA_SERVICE_ROOT)

from cg_input_sampler import normalized_distance, validate_candidate  # noqa: E402


def _extract_values(candidate: dict[str, Any]) -> dict[str, Any]:
    """`candidate["parameters"]` is `generate_inputs()`'s parameter-VIEW
    list (`parameterId`/`displayName`/`type`/`numberValue`/`integerValue`/
    `booleanValue`) -- flatten it to the `{parameterId: value}` shape
    `cg_input_sampler.validate_candidate`/`normalized_distance` expect."""
    values: dict[str, Any] = {}
    for row in candidate.get("parameters", []):
        ptype = row.get("type")
        if ptype == "Boolean":
            values[row["parameterId"]] = row.get("booleanValue")
        elif ptype == "Integer":
            values[row["parameterId"]] = row.get("integerValue")
        elif ptype == "Number":
            values[row["parameterId"]] = row.get("numberValue")
    return values


def score_domain_compliance(candidates: list[dict[str, Any]], bound_params: list[dict[str, Any]]) -> float:
    """SC1-a (spec/API.md SC1 table): "Candidates whose every parameter is
    in-domain and step-aligned" -- threshold **100%**, any failure is a
    validator defect, not a quality score.

    The fraction of `candidates` for which `cg_input_sampler.
    validate_candidate` returns an empty violation list. An empty
    `candidates` list scores `0.0` -- there is nothing to be compliant
    about, and a caller asserting `== 1.0` on an accidentally-empty set
    should fail loudly rather than pass vacuously.
    """
    if not candidates:
        return 0.0
    compliant = sum(
        1 for candidate in candidates if not validate_candidate(_extract_values(candidate), bound_params)
    )
    return compliant / len(candidates)


def score_rule_satisfaction(candidates: list[dict[str, Any]], classification: Any) -> "float | None":
    """SC1-b (spec/API.md SC1 table): "Candidates satisfying the rule limit,
    for `direct-parameter` and `monotone-bound` rules" -- threshold **>= 75%**
    (3 of the default 4).

    The fraction of `candidates` whose `ruleSatisfaction.claim ==
    "satisfied"`. Returns `None` -- deliberately never `0.0` -- when
    `classification.determinability == "geometry-required"`: the metric is
    UNDEFINED there, not failing. A `0.0` would read as "every candidate
    failed the rule" when in fact none could ever have satisfied it in the
    first place. Callers MUST branch on `None` explicitly rather than
    comparing it to a threshold.
    """
    if classification.determinability == "geometry-required":
        return None
    if not candidates:
        return 0.0
    satisfied = sum(
        1 for candidate in candidates if candidate.get("ruleSatisfaction", {}).get("claim") == "satisfied"
    )
    return satisfied / len(candidates)


def score_diversity(candidates: list[dict[str, Any]], bound_params: list[dict[str, Any]]) -> float:
    """SC1-d (spec/API.md SC1 table): "Minimum normalized pairwise L1
    distance across the candidate set" -- threshold **>= 0.10** (each
    parameter scaled to its own domain).

    The MINIMUM `cg_input_sampler.normalized_distance` over every pairwise
    combination of `candidates`. A single-candidate set is vacuously
    diverse (`1.0`) rather than raising or dividing by zero -- there is no
    pair for it to be a near-duplicate of.
    """
    if len(candidates) <= 1:
        return 1.0
    values = [_extract_values(candidate) for candidate in candidates]
    distances = [
        normalized_distance(values[i], values[j], bound_params)
        for i in range(len(values))
        for j in range(i + 1, len(values))
    ]
    return min(distances)


def score_overclaim(candidates: list[dict[str, Any]], classification: Any) -> int:
    """SC1-e (spec/API.md SC1 table): "Candidates claiming `satisfied` for a
    `geometry-required` rule" -- threshold **exactly 0**.

    This is the phase's credibility metric: it proves the system DECLINES
    to claim rule satisfaction on a rule it cannot check from parameters
    alone -- even when the rule's SWRL limit is perfectly readable on the
    graph (see `test_input_gen_eval.py`'s SC1-e fixture, built specifically
    so a rule with NO limit at all could never pass this test vacuously).
    For a non-`geometry-required` classification the metric does not apply
    and this returns `0` unconditionally (nothing to overclaim against).
    """
    if classification.determinability != "geometry-required":
        return 0
    return sum(1 for candidate in candidates if candidate.get("ruleSatisfaction", {}).get("claim") == "satisfied")


def score_candidate_set(
    candidates: list[dict[str, Any]], bound_params: list[dict[str, Any]], classification: Any
) -> dict[str, Any]:
    """Assemble SC1-a/b/d/e into one dict -- `domainCompliance`,
    `ruleSatisfaction`, `diversity`, `overclaimCount`, `candidateCount` --
    for a single readable assertion site and for emission into the eval's
    printed report output. SC1-c is asserted directly in
    `test_input_gen_eval.py` (see this module's docstring for why)."""
    return {
        "domainCompliance": score_domain_compliance(candidates, bound_params),
        "ruleSatisfaction": score_rule_satisfaction(candidates, classification),
        "diversity": score_diversity(candidates, bound_params),
        "overclaimCount": score_overclaim(candidates, classification),
        "candidateCount": len(candidates),
    }
