"""Tier 0 of the two-tier AI-generated-input generator (Phase 38: GHIN-01/03/04).

Pure functions only: no LLM, no Neo4j, no I/O, no wall-clock reads, no
`random` without a fixed seed. Same determinism contract as
`cg_topology.py` -- **the same input must always produce the same output**
(`cg_topology.py:414`'s note on `merge()`, restated here for this module).

This module answers two questions, and the second is the one that carries
D-14's whole weight:

1. `sample_tier0()` / `sample_candidate_set()`: given a bound parameter set
   and an optional numeric rule limit, deterministically produce candidate
   assignments that are ALWAYS in-domain and step-aligned. This is the
   guaranteed floor D-12 requires -- so a useless Tier 1 (LLM) degrades the
   result rather than emptying it, the exact Phase 35 failure this phase
   was chartered to avoid recurring.

2. `validate_candidate()`: the dynamic domain validator, built fresh per
   request from the actual bound parameter set (never a static schema --
   `to_strict_json_schema()` strips `minimum`/`maximum` by design, and the
   real bounds are per-parameter and dynamic anyway, per D-17). It reports
   every way a value can be wrong. It **never repairs one**: clamping is
   semantic distortion that hides model failure behind a valid-looking
   result. There is no clamp helper anywhere in this module, and there
   never should be one added.

Tier 0's `limit` parameter is a duck-typed object exposing `.operator` and
`.value` attributes (matching `cg_input_bindings.RuleLimit`, without
importing that module -- this module's dependency surface stays at zero
first-party imports). Tier 0 does NOT evaluate a rule's `metricExpression`;
it has no visibility into which of several bound parameters a monotone-bound
rule's metric actually combines. Instead it applies the limit's direction as
a uniform best-effort bias across every numeric bound parameter (see
`_conservative_value`/`_near_limit_value`) -- correct and exact for a
`direct-parameter` rule's single parameter, an honest heuristic (not a
guarantee) for a `monotone-bound` rule's several. The only guarantee Tier 0
makes is domain validity: every value `sample_tier0` produces passes
`validate_candidate` with an empty violation list, by construction. Whether
a Tier-0 candidate actually SATISFIES the rule is computed authoritatively,
after the fact, by `cg_input_generation.py`'s post-processing step -- never
assumed here.
"""

from __future__ import annotations

from typing import Any

# ── Constants (D-13, D-15) ──

STRATEGIES: tuple[str, ...] = ("conservative", "balanced", "exploratory", "near-limit")
DEFAULT_CANDIDATE_COUNT = 4
MAX_CANDIDATE_COUNT = 8
NEAR_DUPLICATE_THRESHOLD = 0.10

_EPS = 1e-9
_STEP_TOLERANCE = 1e-6


# ── step_align() -- snap to the domain's step grid, tolerant of float noise ──


def step_align(value: float, domain_min: "float | None", domain_step: "float | None") -> float:
    """Snap `value` to the nearest `domain_min + k * domain_step`.

    Returns `value` unchanged when `domain_step` is falsy (`None` or `0`) --
    there is no step grid to snap to. `domain_min` defaults to `0.0` when
    absent so a step grid still has an origin.

    Rounds the step INDEX (`(value - domain_min) / domain_step`), not the
    raw value -- `domainStep` is commonly `10**-decimalPlaces` and exact
    float equality on the raw value would fail on inputs that are actually
    correct (R7, 38-RESEARCH.md). The result is additionally rounded to a
    sane number of decimal places derived from `domain_step`'s own textual
    precision, so the response never carries floating-point residue like
    `1.0999999999999999`.
    """
    if not domain_step:
        return value
    base = domain_min if domain_min is not None else 0.0
    k = round((value - base) / domain_step)
    aligned = base + k * domain_step
    decimals = _decimals_for_step(domain_step)
    return round(aligned, decimals) if decimals is not None else aligned


def _decimals_for_step(domain_step: float) -> "int | None":
    step_str = repr(float(domain_step))
    if "e" in step_str or "E" in step_str:
        return 10
    if "." in step_str:
        return min(len(step_str.split(".")[1]), 10)
    return 0


def _clip(value: float, domain_min: "float | None", domain_max: "float | None") -> float:
    if domain_min is not None and value < domain_min:
        value = domain_min
    if domain_max is not None and value > domain_max:
        value = domain_max
    return value


# ── validate_candidate() -- the dynamic per-request domain validator (D-14) ──


def _domain(row: dict[str, Any]) -> dict[str, Any]:
    return {"min": row.get("domainMin"), "max": row.get("domainMax"), "step": row.get("domainStep")}


def _violation(parameter_id: str, code: str, what: str, how_to_fix: str, domain: "dict | None") -> dict[str, Any]:
    return {
        "parameterId": parameter_id,
        "code": code,
        "message": f"{what} Where: candidate.parameters[{parameter_id!r}]. How to fix: {how_to_fix}",
        "domain": domain,
    }


def _validate_one(parameter_id: str, value: Any, row: dict[str, Any]) -> list[dict[str, Any]]:
    state_type = row.get("stateType")
    domain = _domain(row)

    if state_type == "Boolean":
        if not isinstance(value, bool):
            return [
                _violation(
                    parameter_id,
                    "type-mismatch",
                    f"Value {value!r} is not a boolean.",
                    "supply true or false.",
                    domain,
                )
            ]
        return []

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [
            _violation(
                parameter_id,
                "type-mismatch",
                f"Value {value!r} is not numeric.",
                f"supply a {state_type} value.",
                domain,
            )
        ]

    if state_type == "Integer" and not float(value).is_integer():
        return [
            _violation(
                parameter_id,
                "type-mismatch",
                f"Value {value!r} is not a whole number.",
                "supply an Integer value.",
                domain,
            )
        ]

    domain_min = row.get("domainMin")
    domain_max = row.get("domainMax")
    domain_step = row.get("domainStep")

    if domain_min is not None and value < domain_min - _EPS:
        return [
            _violation(
                parameter_id,
                "out-of-domain",
                f"Value {value} is below domainMin {domain_min}.",
                f"choose a value >= {domain_min}.",
                domain,
            )
        ]
    if domain_max is not None and value > domain_max + _EPS:
        return [
            _violation(
                parameter_id,
                "out-of-domain",
                f"Value {value} is above domainMax {domain_max}.",
                f"choose a value <= {domain_max}.",
                domain,
            )
        ]
    if domain_step:
        base = domain_min if domain_min is not None else 0.0
        k = (value - base) / domain_step
        if abs(k - round(k)) > _STEP_TOLERANCE:
            return [
                _violation(
                    parameter_id,
                    "step-misaligned",
                    f"Value {value} is not aligned to domainStep {domain_step}.",
                    "snap to the nearest domainMin + k * domainStep.",
                    domain,
                )
            ]
    return []


def validate_candidate(parameters: "dict[str, Any] | None", bound_params: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """**The** dynamic domain validator, built fresh per request from the
    actual `bound_params` set (never a static schema). Returns a violation
    list; an empty list means valid.

    For each supplied parameter, checks and emits a violation dict
    `{parameterId, code, message, domain}` for: a parameter not in
    `bound_params` (`unknown-parameter`); a type mismatch against
    `stateType` (`type-mismatch`); `value < domainMin` or `value >
    domainMax` (`out-of-domain`); a value not step-aligned within tolerance
    (`step-misaligned`). Every bound parameter absent from `parameters`
    emits `missing-parameter`. Boolean parameters skip the range and step
    checks entirely -- they have no numeric domain.

    This function **never modifies `parameters`**. Clamping a value into
    range is semantic distortion that hides a model's failure behind a
    valid-looking result (D-14) -- report the violation and let the caller
    reject-and-retry (or fall back to the Tier 0 floor) instead. There is no
    clamp/coerce/repair helper anywhere in this module.
    """
    by_id: dict[str, dict[str, Any]] = {
        row["reinstateParameterId"]: row for row in bound_params if row.get("reinstateParameterId")
    }
    violations: list[dict[str, Any]] = []

    for parameter_id, value in (parameters or {}).items():
        row = by_id.get(parameter_id)
        if row is None:
            violations.append(
                _violation(
                    parameter_id,
                    "unknown-parameter",
                    f"Parameter {parameter_id!r} is not one of the bound parameters for this rule.",
                    f"only supply one of the bound parameter ids: {sorted(by_id)}.",
                    None,
                )
            )
            continue
        violations.extend(_validate_one(parameter_id, value, row))

    supplied = set((parameters or {}).keys())
    for parameter_id, row in by_id.items():
        if parameter_id not in supplied:
            violations.append(
                _violation(
                    parameter_id,
                    "missing-parameter",
                    f"Parameter {parameter_id!r} is required by this rule's bound parameter set "
                    f"but was not supplied.",
                    f"include a value for {parameter_id!r} within its stated domain.",
                    _domain(row),
                )
            )

    return violations


# ── sample_tier0() -- one deterministic, guaranteed-valid assignment per strategy ──

_CEILING_OPS = ("<=", "<")
_FLOOR_OPS = (">=", ">")

_BOOLEAN_BY_STRATEGY: dict[str, bool] = {
    # No inherent "low"/"high" ordering for a boolean, so strategy diversity
    # here is just a fixed, documented split (no RNG) -- conservative/
    # balanced default False, exploratory/near-limit default True.
    "conservative": False,
    "balanced": False,
    "exploratory": True,
    "near-limit": True,
}


def _limit_operator(limit: Any) -> "str | None":
    if limit is None:
        return None
    return limit.get("operator") if isinstance(limit, dict) else getattr(limit, "operator", None)


def _limit_value(limit: Any) -> "float | None":
    if limit is None:
        return None
    return limit.get("value") if isinstance(limit, dict) else getattr(limit, "value", None)


def _domain_bounds(domain_min: "float | None", domain_max: "float | None") -> tuple[float, float]:
    if domain_min is None and domain_max is None:
        return 0.0, 1.0
    if domain_min is None:
        return float(domain_max), float(domain_max)
    if domain_max is None:
        return float(domain_min), float(domain_min)
    return float(domain_min), float(domain_max)


def _conservative_value(lo: float, hi: float, operator: "str | None") -> float:
    # "Conservative" always means "furthest inside the constraint": the low
    # end of the domain by default, or the high end when the rule limit is
    # a lower bound (>=/>) -- exceeding a floor is what a >= rule forbids
    # from below, so staying HIGH is the safe direction there.
    return hi if operator in _FLOOR_OPS else lo


def _near_limit_value(lo: float, hi: float, limit_value: "float | None") -> float:
    if limit_value is None:
        # No rule limit to aim at -- the 90th-percentile point of the domain.
        return lo + 0.9 * (hi - lo)
    # The domain-clamped point closest to the limit. Clamping is symmetric
    # regardless of ceiling/floor direction -- direction only matters for
    # `_conservative_value`, and for whether the clamped point technically
    # SATISFIES a strict (`<`/`>`) operator, which is Task 3's job to
    # compute after the fact, not this function's to guarantee.
    return max(lo, min(hi, limit_value))


def _sample_numeric(strategy: str, index: int, n: int, lo: float, hi: float, operator: "str | None", limit_value: "float | None") -> float:
    if strategy == "conservative":
        return _conservative_value(lo, hi, operator)
    if strategy == "balanced":
        return (lo + hi) / 2.0
    if strategy == "exploratory":
        # Fixed-seed Latin-hypercube-style stratified point: parameter index
        # i of n takes the (i + 0.5) / n quantile of ITS OWN domain. No RNG,
        # deterministic, spreads distinct bound parameters across their
        # domains rather than clustering every parameter at the same
        # fractional position.
        quantile = (index + 0.5) / n if n else 0.5
        return lo + quantile * (hi - lo)
    if strategy == "near-limit":
        return _near_limit_value(lo, hi, limit_value)
    raise ValueError(f"Unknown strategy {strategy!r}; must be one of {STRATEGIES}.")


def sample_tier0(bound_params: list[dict[str, Any]], limit: Any, strategy: str) -> dict[str, Any]:
    """One deterministic, guaranteed-valid assignment for `strategy`.

    Every produced numeric value is `step_align`ed and then clipped into
    `[domainMin, domainMax]`, so the returned assignment passes
    `validate_candidate` by construction -- this is Tier 0's entire
    contract. Boolean parameters are set per `_BOOLEAN_BY_STRATEGY`, never
    range/step-checked.

    `limit` is `None` (sample the domain only) or an object/dict exposing
    `.operator`/`.value` (or `["operator"]`/`["value"]`) -- see the module
    docstring for why direction is applied uniformly across every numeric
    parameter rather than per-metric.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy {strategy!r}; must be one of {STRATEGIES}.")

    operator = _limit_operator(limit)
    limit_value = _limit_value(limit)
    n = len(bound_params)

    assignment: dict[str, Any] = {}
    for index, row in enumerate(bound_params):
        parameter_id = row["reinstateParameterId"]
        state_type = row.get("stateType")

        if state_type == "Boolean":
            assignment[parameter_id] = _BOOLEAN_BY_STRATEGY.get(strategy, False)
            continue

        domain_min = row.get("domainMin")
        domain_max = row.get("domainMax")
        domain_step = row.get("domainStep")
        lo, hi = _domain_bounds(domain_min, domain_max)

        raw = _sample_numeric(strategy, index, n, lo, hi, operator, limit_value)
        aligned = step_align(raw, domain_min, domain_step)
        clipped = _clip(aligned, domain_min, domain_max)
        if state_type == "Integer":
            clipped = int(round(clipped))
        assignment[parameter_id] = clipped

    return assignment


def _perturb(assignment: dict[str, Any], bound_params: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    """Nudge every numeric value by `cycle` additional domain steps so a
    repeated strategy (candidate index >= len(STRATEGIES)) is not a
    duplicate of its first occurrence. Deterministic -- no RNG."""
    perturbed: dict[str, Any] = {}
    for row in bound_params:
        parameter_id = row["reinstateParameterId"]
        value = assignment.get(parameter_id)
        state_type = row.get("stateType")
        if state_type == "Boolean" or value is None:
            perturbed[parameter_id] = value
            continue
        domain_min = row.get("domainMin")
        domain_max = row.get("domainMax")
        domain_step = row.get("domainStep")
        if not domain_step:
            span = (domain_max - domain_min) if (domain_min is not None and domain_max is not None) else 1.0
            domain_step = span * 0.05 or 1.0
        shifted = value + cycle * domain_step
        aligned = step_align(shifted, domain_min, domain_step)
        clipped = _clip(aligned, domain_min, domain_max)
        if state_type == "Integer":
            clipped = int(round(clipped))
        perturbed[parameter_id] = clipped
    return perturbed


def sample_candidate_set(bound_params: list[dict[str, Any]], limit: Any, count: int) -> list[dict[str, Any]]:
    """`count` deterministic assignments, cycling `STRATEGIES`. Each entry is
    `{"strategy": ..., "parameters": {parameterId: value}}`. Past the fourth
    candidate, `_perturb` shifts every numeric value by one additional
    domain step per extra cycle so a fifth candidate is not a duplicate of
    the first.

    Calling this twice with identical arguments returns identical output --
    no `random`, no wall-clock read, no external state.
    """
    candidates: list[dict[str, Any]] = []
    for i in range(count):
        strategy = STRATEGIES[i % len(STRATEGIES)]
        assignment = sample_tier0(bound_params, limit, strategy)
        cycle = i // len(STRATEGIES)
        if cycle:
            assignment = _perturb(assignment, bound_params, cycle)
        candidates.append({"strategy": strategy, "parameters": assignment})
    return candidates


# ── normalized_distance() / is_near_duplicate() -- diversity (D-13, SC1-d) ──


def normalized_distance(a: "dict[str, Any] | None", b: "dict[str, Any] | None", bound_params: list[dict[str, Any]]) -> float:
    """Mean absolute difference across `bound_params`, each parameter scaled
    to its own domain (`(v - min) / (max - min)`; `0.0`/`1.0` for booleans).
    A parameter with a degenerate domain (`domainMax == domainMin`, or
    either bound missing) contributes `0.0` rather than dividing by zero.
    """
    if not bound_params:
        return 0.0
    a = a or {}
    b = b or {}
    total = 0.0
    for row in bound_params:
        parameter_id = row["reinstateParameterId"]
        va = a.get(parameter_id)
        vb = b.get(parameter_id)
        if row.get("stateType") == "Boolean":
            sa = 1.0 if va else 0.0
            sb = 1.0 if vb else 0.0
            total += abs(sa - sb)
            continue
        domain_min = row.get("domainMin")
        domain_max = row.get("domainMax")
        if domain_min is None or domain_max is None or domain_max == domain_min:
            continue
        span = domain_max - domain_min
        sa = ((va if va is not None else domain_min) - domain_min) / span
        sb = ((vb if vb is not None else domain_min) - domain_min) / span
        total += abs(sa - sb)
    return total / len(bound_params)


def is_near_duplicate(
    candidate: "dict[str, Any] | None",
    others: list["dict[str, Any]"],
    bound_params: list[dict[str, Any]],
    threshold: float = NEAR_DUPLICATE_THRESHOLD,
) -> bool:
    """True when the minimum `normalized_distance` from `candidate` to any
    member of `others` is below `threshold`. `False` when `others` is
    empty -- nothing to be a duplicate of."""
    if not others:
        return False
    return min(normalized_distance(candidate, other, bound_params) for other in others) < threshold
