"""Tests for cg_input_sampler.py -- Tier 0 of the AI-generated-input
generator (Phase 38 Plan 04: GHIN-01/03/04).

Pure Tier 0 only: no LLM, no Neo4j. Property-style coverage over
`(domainMin, domainMax, domainStep)` triples is done via a deterministic
grid sweep rather than the `hypothesis` package -- `hypothesis` is not a
dependency of this project (confirmed against `data-service/requirements.txt`)
and this plan's own acceptance criteria forbid adding one just for this.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cg_input_sampler  # noqa: E402


# ── Shared fixture: Float + Integer + Boolean bound parameters ──


def _row(name: str, domain_min, domain_max, domain_step, state_type: str) -> dict:
    return {
        "cgId": f"cg:1:param:11_Var_{name}",
        "dgId": f"dg:{name}",
        "parameterName": name,
        "reinstateParameterId": name,
        "stateType": state_type,
        "domainMin": domain_min,
        "domainMax": domain_max,
        "domainStep": domain_step,
    }


def _bound() -> list[dict]:
    return [
        _row("HTotal", 0.5, 12.0, 0.1, "Number"),
        _row("SpansCount", 1, 20, 1, "Integer"),
        _row("IsCorner", None, None, None, "Boolean"),
    ]


class _Limit:
    """Duck-typed stand-in for cg_input_bindings.RuleLimit -- exposes
    .operator/.value only, so this test file never imports that module
    (cg_input_sampler.py itself never does either)."""

    def __init__(self, operator: str, value: float):
        self.operator = operator
        self.value = value


# ── step_align() / validate_candidate() -- the dynamic domain validator ──


class TestStepAlign:
    def test_no_step_returns_value_unchanged(self):
        assert cg_input_sampler.step_align(3.14159, 0.0, None) == 3.14159
        assert cg_input_sampler.step_align(3.14159, 0.0, 0) == 3.14159

    def test_snaps_to_nearest_step_index(self):
        assert cg_input_sampler.step_align(0.57, 0.5, 0.1) == 0.6
        assert cg_input_sampler.step_align(0.53, 0.5, 0.1) == 0.5

    def test_tolerant_of_float_noise(self):
        # 0.1 + 0.2 != 0.3 in raw IEEE-754 -- step_align must not choke on it.
        noisy = 0.1 + 0.2  # 0.30000000000000004
        assert cg_input_sampler.step_align(noisy, 0.0, 0.1) == 0.3


class TestValidateCandidateGridSweep:
    """Property-like coverage without hypothesis: sweep a grid of
    (domainMin, domainMax, domainStep) triples and step-index positions,
    asserting in-range + aligned <=> validate_candidate reports no
    out-of-domain/step-misaligned violation for that parameter."""

    _DOMAINS = [
        (0.0, 10.0, 1.0),
        (0.5, 12.0, 0.1),
        (-5.0, 5.0, 0.5),
        (1, 20, 1),
    ]

    def test_in_range_and_aligned_never_violates_domain_or_step(self):
        for domain_min, domain_max, domain_step in self._DOMAINS:
            bound = [_row("P", domain_min, domain_max, domain_step, "Number")]
            steps = int(round((domain_max - domain_min) / domain_step))
            for k in range(0, steps + 1, max(1, steps // 5)):
                value = domain_min + k * domain_step
                violations = cg_input_sampler.validate_candidate({"P": value}, bound)
                codes = {v["code"] for v in violations}
                assert "out-of-domain" not in codes, (domain_min, domain_max, domain_step, value)
                assert "step-misaligned" not in codes, (domain_min, domain_max, domain_step, value)

    def test_out_of_range_always_violates_out_of_domain(self):
        for domain_min, domain_max, domain_step in self._DOMAINS:
            bound = [_row("P", domain_min, domain_max, domain_step, "Number")]
            below = domain_min - (domain_step or 1.0) * 3
            above = domain_max + (domain_step or 1.0) * 3
            for value in (below, above):
                violations = cg_input_sampler.validate_candidate({"P": value}, bound)
                codes = {v["code"] for v in violations}
                assert "out-of-domain" in codes, (domain_min, domain_max, domain_step, value)

    def test_misaligned_within_range_always_violates_step_misaligned(self):
        for domain_min, domain_max, domain_step in self._DOMAINS:
            if domain_step in (0, None):
                continue
            bound = [_row("P", domain_min, domain_max, domain_step, "Number")]
            value = domain_min + domain_step * 1.3  # off-grid, still in range
            violations = cg_input_sampler.validate_candidate({"P": value}, bound)
            codes = {v["code"] for v in violations}
            assert "step-misaligned" in codes, (domain_min, domain_max, domain_step, value)


class TestValidateCandidateAllFiveCodes:
    def test_unknown_and_missing_parameter(self):
        bound = _bound()
        codes = {
            v["code"]
            for v in cg_input_sampler.validate_candidate({"HTotal": 5.0, "ghost": 1.0}, bound)
        }
        assert "unknown-parameter" in codes
        assert "missing-parameter" in codes

    def test_type_mismatch_numeric_and_boolean(self):
        bound = _bound()
        codes = {
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": "nope", "SpansCount": 5, "IsCorner": True}, bound
            )
        }
        assert codes == {"type-mismatch"}

        codes_bool = {
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": 5.0, "SpansCount": 5, "IsCorner": "yes"}, bound
            )
        }
        assert codes_bool == {"type-mismatch"}

    def test_integer_non_whole_number_is_type_mismatch(self):
        bound = _bound()
        codes = {
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": 5.0, "SpansCount": 5.5, "IsCorner": True}, bound
            )
        }
        assert "type-mismatch" in codes

    def test_out_of_domain(self):
        bound = _bound()
        codes = {
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": 50.0, "SpansCount": 5, "IsCorner": True}, bound
            )
        }
        assert "out-of-domain" in codes

    def test_step_misaligned(self):
        bound = _bound()
        codes = {
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": 0.55, "SpansCount": 5, "IsCorner": True}, bound
            )
        }
        assert "step-misaligned" in codes

    def test_all_five_codes_are_producible_across_the_fixture_set(self):
        bound = _bound()
        all_codes: set[str] = set()
        all_codes.update(v["code"] for v in cg_input_sampler.validate_candidate({"HTotal": 5.0, "ghost": 1.0}, bound))
        all_codes.update(
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": "nope", "SpansCount": 5, "IsCorner": True}, bound
            )
        )
        all_codes.update(
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": 50.0, "SpansCount": 5, "IsCorner": True}, bound
            )
        )
        all_codes.update(
            v["code"]
            for v in cg_input_sampler.validate_candidate(
                {"HTotal": 0.55, "SpansCount": 5, "IsCorner": True}, bound
            )
        )
        assert all_codes == {
            "unknown-parameter",
            "missing-parameter",
            "type-mismatch",
            "out-of-domain",
            "step-misaligned",
        }

    def test_boolean_skips_range_and_step_checks(self):
        bound = _bound()
        violations = cg_input_sampler.validate_candidate(
            {"HTotal": 5.0, "SpansCount": 5, "IsCorner": False}, bound
        )
        assert violations == []

    def test_never_mutates_input_parameters(self):
        bound = _bound()
        params = {"HTotal": 5.0, "SpansCount": 5, "IsCorner": True, "ghost": 1.0}
        before = dict(params)
        cg_input_sampler.validate_candidate(params, bound)
        assert params == before


# ── sample_tier0() -- every strategy validates clean ──


class TestSampleTier0:
    def test_every_strategy_validates_clean_no_limit(self):
        bound = _bound()
        for strategy in cg_input_sampler.STRATEGIES:
            assignment = cg_input_sampler.sample_tier0(bound, None, strategy)
            violations = cg_input_sampler.validate_candidate(assignment, bound)
            assert violations == [], (strategy, assignment, violations)

    def test_every_strategy_validates_clean_with_limit(self):
        bound = _bound()
        for operator in ("<=", "<", ">=", ">", "=="):
            limit = _Limit(operator, 6.0)
            for strategy in cg_input_sampler.STRATEGIES:
                assignment = cg_input_sampler.sample_tier0(bound, limit, strategy)
                violations = cg_input_sampler.validate_candidate(assignment, bound)
                assert violations == [], (operator, strategy, assignment, violations)

    def test_conservative_direction_flips_for_lower_bound_limit(self):
        bound = [_row("HTotal", 0.5, 12.0, 0.1, "Number")]
        ceiling = cg_input_sampler.sample_tier0(bound, _Limit("<=", 6.0), "conservative")
        floor = cg_input_sampler.sample_tier0(bound, _Limit(">=", 6.0), "conservative")
        assert ceiling["HTotal"] == 0.5
        assert floor["HTotal"] == 12.0

    def test_near_limit_clamps_to_domain_when_limit_outside_range(self):
        bound = [_row("HTotal", 0.5, 12.0, 0.1, "Number")]
        above_domain = cg_input_sampler.sample_tier0(bound, _Limit("<=", 20.0), "near-limit")
        below_domain = cg_input_sampler.sample_tier0(bound, _Limit(">=", -5.0), "near-limit")
        assert above_domain["HTotal"] == 12.0
        assert below_domain["HTotal"] == 0.5

    def test_near_limit_falls_back_to_90th_percentile_when_limit_none(self):
        bound = [_row("HTotal", 0.0, 10.0, 1.0, "Number")]
        assignment = cg_input_sampler.sample_tier0(bound, None, "near-limit")
        assert assignment["HTotal"] == 9.0

    def test_boolean_parameter_never_range_or_step_checked(self):
        bound = [_row("IsCorner", None, None, None, "Boolean")]
        for strategy in cg_input_sampler.STRATEGIES:
            assignment = cg_input_sampler.sample_tier0(bound, None, strategy)
            assert isinstance(assignment["IsCorner"], bool)

    def test_degenerate_domain_does_not_raise(self):
        bound = [_row("Fixed", 5.0, 5.0, 0.5, "Number")]
        for strategy in cg_input_sampler.STRATEGIES:
            assignment = cg_input_sampler.sample_tier0(bound, _Limit("<=", 5.0), strategy)
            assert assignment["Fixed"] == 5.0
            assert cg_input_sampler.validate_candidate(assignment, bound) == []


# ── sample_candidate_set() -- determinism + diversity (SC1-d) ──


class TestSampleCandidateSet:
    def test_determinism_two_calls_equal(self):
        bound = _bound()
        first = cg_input_sampler.sample_candidate_set(bound, _Limit("<=", 6.0), 4)
        second = cg_input_sampler.sample_candidate_set(bound, _Limit("<=", 6.0), 4)
        assert first == second

    def test_every_candidate_validates_clean(self):
        bound = _bound()
        candidates = cg_input_sampler.sample_candidate_set(bound, None, 6)
        assert len(candidates) == 6
        for candidate in candidates:
            assert cg_input_sampler.validate_candidate(candidate["parameters"], bound) == []

    def test_diversity_minimum_pairwise_distance_meets_threshold(self):
        bound = _bound()
        candidates = cg_input_sampler.sample_candidate_set(bound, None, 4)
        params = [c["parameters"] for c in candidates]
        min_distance = min(
            cg_input_sampler.normalized_distance(params[i], params[j], bound)
            for i in range(len(params))
            for j in range(i + 1, len(params))
        )
        assert min_distance >= cg_input_sampler.NEAR_DUPLICATE_THRESHOLD

    def test_fifth_candidate_is_not_a_duplicate_of_the_first(self):
        bound = _bound()
        candidates = cg_input_sampler.sample_candidate_set(bound, None, 5)
        distance = cg_input_sampler.normalized_distance(
            candidates[0]["parameters"], candidates[4]["parameters"], bound
        )
        assert distance > 0.0


# ── normalized_distance() / is_near_duplicate() ──


class TestDiversity:
    def test_degenerate_domain_contributes_zero_not_a_raise(self):
        bound = [_row("Fixed", 5.0, 5.0, 0.5, "Number")]
        distance = cg_input_sampler.normalized_distance({"Fixed": 5.0}, {"Fixed": 5.0}, bound)
        assert distance == 0.0

    def test_is_near_duplicate_false_when_no_others(self):
        bound = _bound()
        assert cg_input_sampler.is_near_duplicate({"HTotal": 1.0}, [], bound) is False

    def test_is_near_duplicate_true_below_threshold(self):
        bound = [_row("HTotal", 0.0, 10.0, 0.1, "Number")]
        a = {"HTotal": 5.0}
        b = {"HTotal": 5.05}
        assert cg_input_sampler.is_near_duplicate(a, [b], bound) is True

    def test_is_near_duplicate_false_above_threshold(self):
        bound = [_row("HTotal", 0.0, 10.0, 0.1, "Number")]
        a = {"HTotal": 1.0}
        b = {"HTotal": 9.0}
        assert cg_input_sampler.is_near_duplicate(a, [b], bound) is False
