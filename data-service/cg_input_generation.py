"""Tier 1 orchestrator for AI-generated Grasshopper script inputs (Phase 38:
GHIN-01/02/03/04).

`generate_inputs()` is the single entry point `POST /computgraph/generate-
inputs` delegates to. Sequence: resolve the definition -> classify the rule
(`cg_input_bindings.classify_rule`) -> read and select its bound parameters
(`cg_input_bindings.select_parameters`) -> sample the deterministic Tier 0
floor (`cg_input_sampler.sample_candidate_set`) -> attempt Tier 1 (the LLM)
under a bounded retry loop -> post-process whichever tier's candidates ship,
computing `ruleSatisfaction` and `provenance` AFTER the fact rather than
trusting anything the model claimed about itself.

38-RESEARCH.md Section 4.1 is decisive: constrained decoding is unavailable
here twice over -- `cg_schemas.to_strict_json_schema()` strips numeric
bounds by design (D-17), and the real bounds are per-parameter and dynamic
anyway. The architecture is therefore forced to generate -> validate ->
reject/retry, exactly like `cg_recognition.recognize_structure()`. The one
structural difference from that precedent is D-12: on Tier-1 exhaustion this
function NEVER returns empty-handed or raises a domain-violation error --
Tier 0's guaranteed-valid floor always ships, tagged with a
`llm_candidates_rejected` flag. That is deliberate, not a workaround for a
missing hard-failure path: a useless model must degrade the result, not
empty it, which is the exact Phase 35 failure (0 proposals from 14
candidates) this phase exists to make structurally impossible to repeat.

**Hard constraint (D-22, GHIN-04):** this module imports only
`cg_input_bindings`, `cg_input_sampler`, `cg_schemas`, `cg_structure_checks`
and `llm_gateway`. It imports neither `gh_bridge` nor any persistence
module, and issues no graph-mutating Cypher clause -- asserted transitively
by `tests/test_cg_input_boundary.py`'s `ast`-based import-closure walk, not
by this docstring alone.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import operator as _operator
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

import cg_input_bindings
import cg_input_sampler
import cg_schemas
import cg_structure_checks
import llm_gateway
from llm_gateway import (
    GenerateRequest,
    GenerationOptions,
    get_adapter,
    load_persisted_llm_settings,
    negotiate_structured_output,
)

# Provider resolution is deliberately accessed via the qualified
# `llm_gateway.` prefix (not a bare-name import) so that call appears
# exactly once in this file's source -- at its single call site inside
# generate_inputs(), never inside the retry loop (D-16).

_LOG = logging.getLogger(__name__)

MAX_RETRIES = 2


class NoEligibleParametersError(ValueError):
    """Raised when `select_parameters()` returns zero bound parameters for
    this call. `excluded` carries every exclusion this call actually
    encountered, so the route's hint can say WHY nothing was eligible, not
    just that nothing was."""

    def __init__(self, message: str, excluded: list[dict[str, Any]]):
        super().__init__(message)
        self.excluded = excluded


class DomainViolationExhaustedError(RuntimeError):
    """Raised only when Tier 0 itself cannot produce a single candidate.

    Given `select_parameters()` already guarantees a non-empty `bound` list
    before this function ever samples (checked at step 3, raising
    `NoEligibleParametersError` otherwise) and `candidateCount` is validated
    to be >= 1, `cg_input_sampler.sample_tier0` cannot fail to produce a
    domain-valid assignment -- this exception should be unreachable in
    practice. It is kept as an explicit, named failure mode rather than an
    uncaught exception so a future change to the sampler's guarantees fails
    loudly here instead of surfacing as a 500 with no diagnosis. Do NOT
    delete this branch as "dead code" -- it is the one hard-failure path
    D-12 still allows, reserved for exactly this otherwise-impossible case.
    """


# ── System prompt loader -- mirrors cg_recognition.py's versioned-prompt-file
# convention. Duplicated rather than imported: this module's first-party
# dependency surface is deliberately limited to the five modules named in
# the module docstring (D-22/GHIN-04). ──

SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "input_generation_system.md"

_system_prompt_cache: "str | None" = None
_prompt_version_cache: "str | None" = None


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split a `---\\nkey: value\\n---\\nbody` file into `(front_matter, body)`.
    Never raises: text with no leading `---` fence returns `({}, text)`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    front_matter: dict[str, str] = {}
    body_start: "int | None" = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        if ":" in lines[i]:
            key, _, value = lines[i].partition(":")
            front_matter[key.strip()] = value.strip()
    if body_start is None:
        return {}, text
    return front_matter, "\n".join(lines[body_start:])


def _load_system_prompt() -> tuple[str, str]:
    """Load `prompts/input_generation_system.md` once, cached at module
    scope. NEVER raises on a missing or malformed file -- degrades to no
    system prompt rather than breaking generation outright."""
    global _system_prompt_cache, _prompt_version_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache, _prompt_version_cache or ""
    if not SYSTEM_PROMPT_FILE.exists():
        _LOG.warning("input_generation_system_prompt_missing path=%s", SYSTEM_PROMPT_FILE)
        _system_prompt_cache = ""
        _prompt_version_cache = ""
        return _system_prompt_cache, _prompt_version_cache
    try:
        raw = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        front_matter, body = _parse_front_matter(raw)
        _system_prompt_cache = body.strip()
        _prompt_version_cache = front_matter.get("prompt_version", "")
    except OSError:
        _LOG.warning("input_generation_system_prompt_load_failed path=%s", SYSTEM_PROMPT_FILE)
        _system_prompt_cache = ""
        _prompt_version_cache = ""
    return _system_prompt_cache, _prompt_version_cache or ""


PROMPT_VERSION: str = _load_system_prompt()[1]


# ── Prompt assembly ──


def build_generation_prompt(
    *,
    rule_id: str,
    classification: "cg_input_bindings.RuleClassification",
    bound_parameters: list[dict[str, Any]],
    candidate_count: int,
    negotiated_mode: str,
) -> str:
    """Deterministic USER prompt: the rule's determinability/limit, the
    bound parameter list (each with its EXACT parameterId -- reinstateParameterId,
    never parameterName -- and full domain), the requested strategy list, and
    the output-shape instruction. Role/task framing lives in the system
    prompt (`input_generation_system.md`), mirroring
    `cg_recognition._build_recognition_prompt`'s prompt split."""
    lines = [
        f"Rule: {rule_id}",
        f"Determinability: {classification.determinability}",
    ]
    if classification.limit is not None:
        lines.append(
            f"Rule limit: candidate metric must satisfy value {classification.limit.operator} "
            f"{classification.limit.value}"
        )
    else:
        lines.append("Rule limit: not checkable from parameters alone (do not claim satisfaction).")

    lines.append("")
    lines.append("=== BOUND PARAMETERS (use these exact parameterId values, never invent one) ===")
    for row in bound_parameters:
        lines.append(
            f"- parameterId={row['reinstateParameterId']!r}, displayName={row.get('parameterName')!r}, "
            f"type={row.get('stateType')}, domainMin={row.get('domainMin')}, "
            f"domainMax={row.get('domainMax')}, domainStep={row.get('domainStep')}"
        )

    lines.append("")
    strategies_needed = [cg_input_sampler.STRATEGIES[i % len(cg_input_sampler.STRATEGIES)] for i in range(candidate_count)]
    lines.append(
        f"Produce exactly {candidate_count} candidates, one per strategy (in order): "
        f"{', '.join(strategies_needed)}."
    )
    lines.append(
        "Every value MUST be within its stated domain and aligned to its step. Values outside "
        "the stated domain will be REJECTED and the request retried."
    )

    lines.append("")
    lines.append("=== OUTPUT INSTRUCTIONS ===")
    lines.append(
        'Output ONLY a single JSON object matching this shape: {"candidates": [{"strategy",'
        '"rationale","parameters": [{"parameterId","type","numberValue","integerValue",'
        '"booleanValue"}]}]}. No markdown fences. No commentary. No text before or after the '
        "JSON object."
    )
    if negotiated_mode == "json_object":
        lines.append(
            "Return a valid json object. Example shape: "
            '{"candidates": [{"strategy": "balanced", "rationale": "...", "parameters": '
            '[{"parameterId": "HTotal", "type": "Number", "numberValue": 6.0, '
            '"integerValue": null, "booleanValue": null}]}]}'
        )

    return "\n".join(lines)


def append_domain_feedback(prompt: str, violations: list[dict[str, Any]]) -> str:
    """Append structured violations to the ORIGINAL prompt as corrective
    feedback for the next attempt (mirrors
    `cg_recognition.append_recognition_feedback`'s What+Where+How-to-fix
    vocabulary, retargeted at domain/step/diversity violations)."""
    lines = [
        prompt,
        "",
        "--- CORRECTIVE FEEDBACK: the previous candidate set failed validation ---",
    ]
    for violation in violations:
        pid = f" [{violation['parameterId']}]" if violation.get("parameterId") else ""
        lines.append(f"- [{violation['code']}]{pid} {violation['message']}")
    lines.append(
        "Regenerate the FULL candidate set, fixing every violation listed above. Output ONLY a "
        "single JSON object -- no markdown fences, no commentary."
    )
    return "\n".join(lines)


# ── JSON extraction (mirrors cg_recognition._extract_json -- duplicated, not
# imported, per this module's limited first-party dependency surface) ──


def _extract_json(text: "str | None") -> tuple["dict | None", "str | None"]:
    if not text or not text.strip():
        return None, "LLM response was empty. Where: the LLM's raw text output."

    candidate = text.strip()

    if candidate.startswith("```") and candidate.endswith("```"):
        inner = candidate[3:-3].strip()
        for prefix in ("json", "JSON"):
            if inner.startswith(prefix):
                inner = inner[len(prefix):].strip()
                break
        candidate = inner

    if not (candidate.startswith("{") and candidate.endswith("}")):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except ValueError as exc:
        return None, (
            f"Could not parse JSON from the LLM response ({exc}). Where: the LLM's raw text "
            f"output. How to fix: output ONLY a single JSON object, no markdown fences, no "
            f"commentary."
        )

    if not isinstance(parsed, dict):
        return None, (
            'Parsed value is not a JSON object (expected {"candidates": [...]}). Where: the '
            "LLM's raw text output. How to fix: output a single top-level JSON object, not an "
            "array or scalar."
        )

    return parsed, None


def _schema_violations(exc: ValidationError) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        violations.append(
            {
                "parameterId": None,
                "code": "schema_violation",
                "message": (
                    f"Candidate set failed schema validation: {err.get('msg')}. Where: "
                    f"{loc or '(top level)'}. How to fix: conform the response to the required "
                    f"GeneratedCandidateSet shape."
                ),
            }
        )
    return violations


# ── Restricted arithmetic evaluator for a monotone-bound rule's
# metricExpression -- ast-based, never Python eval(). ──

_ALLOWED_BINOPS = {ast.Add: _operator.add, ast.Sub: _operator.sub, ast.Mult: _operator.mul, ast.Div: _operator.truediv}
_ALLOWED_UNARYOPS = {ast.USub: _operator.neg, ast.UAdd: _operator.pos}


def _safe_eval_expression(expr: "str | None", variables: dict[str, Any]) -> "float | None":
    """Evaluate a restricted arithmetic expression (+, -, *, /, parens,
    numeric literals, bare variable names) via `ast.parse`, never `eval()`.
    Returns `None` on any parse/evaluation failure or an unbound/non-numeric
    variable -- never raises, so a malformed `metricExpression` degrades a
    candidate's `ruleSatisfaction.claim` to `undeterminable` rather than
    crashing the request."""
    if not expr:
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None

    def _walk(node: ast.AST) -> "float | None":
        if isinstance(node, ast.Expression):
            return _walk(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            left = _walk(node.left)
            right = _walk(node.right)
            if left is None or right is None:
                return None
            try:
                return _ALLOWED_BINOPS[type(node.op)](left, right)
            except ZeroDivisionError:
                return None
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
            operand = _walk(node.operand)
            return None if operand is None else _ALLOWED_UNARYOPS[type(node.op)](operand)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name):
            value = variables.get(node.id)
            return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        return None

    return _walk(tree)


_SATISFACTION_EPS = 1e-9


def _compare(metric: float, operator: "str | None", value: float) -> bool:
    if operator == "<=":
        return metric <= value + _SATISFACTION_EPS
    if operator == "<":
        return metric < value - _SATISFACTION_EPS
    if operator == ">=":
        return metric >= value - _SATISFACTION_EPS
    if operator == ">":
        return metric > value + _SATISFACTION_EPS
    if operator == "==":
        return abs(metric - value) < 1e-6
    return False


def _rule_satisfaction(
    classification: "cg_input_bindings.RuleClassification",
    parameters: dict[str, Any],
    bound: list[dict[str, Any]],
) -> dict[str, str]:
    """Compute `{claim, basis}` AFTER the candidate's values are known --
    NEVER asked of the model (D-09, T-38-16). `geometry-required` always
    forces `undeterminable`, regardless of anything read from the graph."""
    if classification.determinability == "geometry-required":
        return {
            "claim": "undeterminable",
            "basis": (
                f"Rule {classification.ruleId} classifies as geometry-required (source="
                f"{classification.source}); its limit cannot be checked from parameters alone."
            ),
        }

    limit = classification.limit
    if limit is None:
        return {
            "claim": "undeterminable",
            "basis": (
                f"Rule {classification.ruleId}'s numeric limit could not be read unambiguously "
                f"from its SWRL atoms."
            ),
        }

    values_by_name = {row["parameterName"]: parameters.get(row["reinstateParameterId"]) for row in bound}

    if classification.determinability == "monotone-bound" and classification.metricExpression:
        metric = _safe_eval_expression(classification.metricExpression, values_by_name)
        metric_desc = classification.metricExpression
        basis_kind = "evaluated metricExpression against ruleLimit"
    elif len(classification.parameterNames) == 1:
        only_name = classification.parameterNames[0]
        metric = values_by_name.get(only_name)
        metric_desc = only_name
        basis_kind = "direct read against ruleLimit"
    else:
        metric = None
        metric_desc = "metric"
        basis_kind = "ambiguous parameter scope"

    if metric is None:
        return {
            "claim": "undeterminable",
            "basis": f"Could not evaluate {metric_desc!r} from the candidate's values ({basis_kind}).",
        }

    satisfied = _compare(metric, limit.operator, limit.value)
    claim = "satisfied" if satisfied else "violated"
    basis = (
        f"{metric_desc}={metric} {limit.operator} {limit.value} "
        f"({classification.determinability}, {basis_kind})"
    )
    return {"claim": claim, "basis": basis}


# ── Provenance / statePayload / response assembly ──

# GUESS: provisional confidence-by-tier constants, not derived from any
# measured acceptance data. Tier 0 is fully deterministic/mechanical (no
# ambiguity in HOW it was produced, hence 1.0); Tier 1 is a model choice
# within validated bounds (hence a middling, honestly-labeled 0.75). Mirrors
# cg_recognition.CONFIDENCE_FLOOR's "stated as a guess so nobody mistakes it
# for a measured value" convention -- re-derive once real generate-inputs
# acceptance data exists.
_CONFIDENCE_BY_TIER: dict[int, float] = {0: 1.0, 1: 0.75}

_BOUND_PARAMETER_VIEW_KEYS = (
    "cgId",
    "dgId",
    "parameterName",
    "reinstateParameterId",
    "dataType",
    "stateType",
    "domainMin",
    "domainMax",
    "domainStep",
)


def _bound_parameter_view(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in _BOUND_PARAMETER_VIEW_KEYS}


def _parameter_views(parameters: dict[str, Any], bound: list[dict[str, Any]]) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    for row in bound:
        parameter_id = row["reinstateParameterId"]
        if parameter_id not in parameters:
            continue
        value = parameters[parameter_id]
        state_type = row.get("stateType")
        views.append(
            {
                "parameterId": parameter_id,
                "displayName": row.get("parameterName"),
                "type": state_type,
                "numberValue": value if state_type == "Number" else None,
                "integerValue": value if state_type == "Integer" else None,
                "booleanValue": value if state_type == "Boolean" else None,
            }
        )
    return views


def _compute_preview_state_id(rule_id: str, strategy: str, parameters: dict[str, Any]) -> str:
    """A deterministic `DS_`-prefixed id for THIS generation-time preview
    payload -- identical candidate content always hashes to the same id.
    Distinct from (and not required to match) plan 38-05's
    `compute_param_state_id`, which derives the ACCEPTED DesignState's id at
    accept time; this is a preview id only, scoped to `statePayload`."""
    payload = json.dumps({"ruleId": rule_id, "strategy": strategy, "parameters": parameters}, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()
    return f"DS_{digest}"


def _postprocess_candidates(
    raw_candidates: list[dict[str, Any]],
    classification: "cg_input_bindings.RuleClassification",
    bound: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    definition_id: str,
    published_at: "str | None",
    provider: str,
    model: "str | None",
    rule_id: str,
    generated_at: str,
    tier: int,
) -> list[dict[str, Any]]:
    """Attach `ruleSatisfaction`, `provenance` (all ten GHIN-03 keys),
    `excludedParameters`, and a ParamState-compatible `statePayload` to every
    candidate, whichever tier produced it. Never trusts anything the model
    said about its own values."""
    confidence = _CONFIDENCE_BY_TIER.get(tier, _CONFIDENCE_BY_TIER[0])
    candidates: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates):
        parameters = raw["parameters"]
        parameter_views = _parameter_views(parameters, bound)
        satisfaction = _rule_satisfaction(classification, parameters, bound)
        provenance = {
            "source": "ai-generated",
            "sourceRuleId": rule_id,
            "provider": provider,
            "model": model,
            "confidence": confidence,
            "definitionId": definition_id,
            "publishedAt": published_at,
            "strategy": raw["strategy"],
            "determinabilityClass": classification.determinability,
            "generatedAt": generated_at,
        }
        state_id = _compute_preview_state_id(rule_id, raw["strategy"], parameters)
        candidates.append(
            {
                "candidateId": f"c{index}",
                "strategy": raw["strategy"],
                "parameters": parameter_views,
                "excludedParameters": list(excluded),
                "ruleSatisfaction": satisfaction,
                "provenance": provenance,
                "statePayload": {
                    "stateKind": "ParamState",
                    "stateId": state_id,
                    "capturedAtUtc": generated_at,
                    "paramStates": parameter_views,
                },
            }
        )
    return candidates


# ── Published-parameter read (one parameterized query, never a write) ──


def _list_published_parameters(session: Any, project: str, definition_id: str) -> list[dict[str, Any]]:
    result = session.run(
        """
        MATCH (p:Parameter {project: $project, definitionId: $definitionId})
        RETURN p.cgId AS cgId, p.dgId AS dgId, p.parameterName AS parameterName,
               p.reinstateParameterId AS reinstateParameterId, p.paramKind AS paramKind,
               p.dataType AS dataType, p.domainMin AS domainMin, p.domainMax AS domainMax,
               p.domainStep AS domainStep
        ORDER BY p.cgId
        // op=GENERATE_INPUTS_LIST_PARAMETERS
        """,
        {"project": project, "definitionId": definition_id},
    )
    return [dict(row) for row in result]


# ── Per-attempt structured logging (mirrors cg_recognition._log_attempt) ──


def _log_attempt(
    attempt_number: int,
    provider: str,
    model: "str | None",
    negotiated_mode: str,
    max_tokens: int,
    usage: dict,
    finish_reason: "str | None",
    violation_codes: list[str],
    latency_ms: float,
) -> None:
    """One structured log record per Tier-1 attempt. NEVER logs the current
    prompt, system prompt, or the API key -- only attributable run metadata,
    mirroring cg_recognition._log_attempt's LLMC-06 discipline."""
    record = {
        "attempt": attempt_number,
        "provider": provider,
        "model": model,
        "negotiated_mode": negotiated_mode,
        "prompt_version": PROMPT_VERSION,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "usage": usage,
        "finish_reason": finish_reason,
        "violation_codes": violation_codes,
        "latency_ms": round(latency_ms, 1),
    }
    _LOG.info("generate_inputs_attempt %s", json.dumps(record, sort_keys=True, default=str))


def _output_token_budget(candidate_count: int, parameter_count: int) -> int:
    """GUESS: sized like cg_topology.output_token_budget's clamp shape, for
    a much smaller payload (short strategy/rationale/parameter list per
    candidate, not a whole recognition proposal set) -- not yet measured
    against a real provider's token counts. Re-derive once real
    generate-inputs traffic exists."""
    n = max(candidate_count, 1) * max(parameter_count, 1)
    return max(512, min(256 + 40 * n, 4096))


def _assignments_from_typed(
    typed: "cg_schemas.GeneratedCandidateSet",
) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    for candidate in typed.candidates:
        parameters: dict[str, Any] = {}
        for p in candidate.parameters:
            parameters[p.parameterId] = _value_from_generated_param(p)
        assignments.append(
            {
                "strategy": candidate.strategy,
                "rationale": candidate.rationale,
                "parameters": parameters,
            }
        )
    return assignments


def _value_from_generated_param(p: "cg_schemas.GeneratedParameterValue") -> Any:
    ptype = (p.type or "").strip()
    if ptype == "Boolean":
        return p.booleanValue
    if ptype == "Integer":
        return p.integerValue
    if ptype == "Number":
        return p.numberValue
    return None


def _count_and_strategy_violations(
    candidate_assignments: list[dict[str, Any]], count: int
) -> list[dict[str, Any]]:
    """WR-01: the system prompt and `build_generation_prompt` require
    exactly `count` candidates, one per non-repeating strategy drawn from
    `cg_input_sampler.STRATEGIES`. Neither the schema
    (`GeneratedCandidate.strategy` is deliberately typed `str`, not a
    `Literal`) nor the domain/diversity checks enforce this -- without this
    check a short response, or one reusing a strategy string, passes
    straight through as a Tier-1 success with no retry."""
    violations: list[dict[str, Any]] = []
    if len(candidate_assignments) != count:
        violations.append(
            {
                "parameterId": None,
                "code": "candidate-count-mismatch",
                "message": (
                    f"Expected exactly {count} candidates but got {len(candidate_assignments)}. "
                    f"Where: candidates[] length. How to fix: produce exactly {count} candidates, "
                    f"one per strategy, never fewer, never more."
                ),
            }
        )

    seen_strategies: dict[str, int] = {}
    for index, assignment in enumerate(candidate_assignments):
        strategy = assignment.get("strategy")
        if strategy not in cg_input_sampler.STRATEGIES:
            violations.append(
                {
                    "parameterId": None,
                    "code": "invalid-strategy",
                    "message": (
                        f"candidates[{index}].strategy is {strategy!r}, which is not one of "
                        f"{cg_input_sampler.STRATEGIES}. Where: candidates[{index}].strategy. "
                        f"How to fix: use one of the listed strategy names exactly."
                    ),
                }
            )
            continue
        seen_strategies[strategy] = seen_strategies.get(strategy, 0) + 1

    duplicates = sorted(s for s, n in seen_strategies.items() if n > 1)
    if duplicates:
        violations.append(
            {
                "parameterId": None,
                "code": "duplicate-strategy",
                "message": (
                    f"Strategy value(s) repeated across candidates: {', '.join(duplicates)}. "
                    f"Where: candidates[].strategy. How to fix: use each strategy at most once "
                    f"across the whole candidate set."
                ),
            }
        )
    return violations


def _diversity_violations(candidate_assignments: list[dict[str, Any]], bound: list[dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    n = len(candidate_assignments)
    for i in range(n):
        for j in range(i + 1, n):
            a = candidate_assignments[i]["parameters"]
            b = candidate_assignments[j]["parameters"]
            if cg_input_sampler.is_near_duplicate(a, [b], bound):
                violations.append(
                    {
                        "parameterId": None,
                        "code": "near-duplicate",
                        "message": (
                            f"Candidates at index {i} and {j} are near-duplicates (normalized "
                            f"distance below {cg_input_sampler.NEAR_DUPLICATE_THRESHOLD}). "
                            f"Where: candidates[{i}] and candidates[{j}]. How to fix: choose "
                            f"more distinct values for at least one bound parameter."
                        ),
                    }
                )
    return violations


# ── generate_inputs() -- the orchestrator ──


def generate_inputs(
    session: Any,
    project: str,
    definition_id: "str | None",
    rule_id: str,
    candidate_count: "int | None" = None,
    parameter_overrides: "list[str] | None" = None,
) -> dict[str, Any]:
    """Generate candidate parameter sets for `rule_id` from the published
    Computgraph, bounded to a deterministic Tier 0 floor plus a bounded-retry
    Tier 1 (LLM) refinement.

    `candidateCount`'s 1..8 bound (default 4, `cg_input_sampler.
    DEFAULT_CANDIDATE_COUNT`/`MAX_CANDIDATE_COUNT`) is enforced HERE, not in
    the route -- checked exactly once, matching the documented "pick one
    place" convention.

    On Tier-1 exhaustion this function ALWAYS returns Tier 0's floor rather
    than raising -- see `DomainViolationExhaustedError`'s docstring and the
    module docstring's D-12 note for why that is the intended contract, not
    a workaround: the only way this function raises after `bound` is
    confirmed non-empty is `DomainViolationExhaustedError`, which should be
    unreachable given the sampler's own guarantees.

    Performs exactly one write-free Cypher read beyond what
    `cg_input_bindings`/`cg_structure_checks` already issue
    (`_list_published_parameters`); resolves the LLM provider/adapter
    exactly once, before the retry loop, and calls `adapter.generate()`
    in-process every attempt -- never re-issues the request through the
    gateway's own HTTP route on a later attempt (D-16).
    """
    resolved_definition_id = cg_structure_checks.resolve_definition_id(session, project, definition_id)

    bindings = cg_input_bindings.load_input_bindings()
    classification = cg_input_bindings.classify_rule(session, rule_id, project, bindings, parameter_overrides)

    published_parameters = _list_published_parameters(session, project, resolved_definition_id)
    bound, excluded = cg_input_bindings.select_parameters(classification, published_parameters)

    if not bound:
        reasons = sorted({row["reason"] for row in excluded if row.get("reason")})
        raise NoEligibleParametersError(
            f"No eligible parameters found for rule {rule_id!r} in definition "
            f"{resolved_definition_id!r}.",
            excluded,
        )

    count = candidate_count if candidate_count is not None else cg_input_sampler.DEFAULT_CANDIDATE_COUNT
    if not isinstance(count, int) or not (1 <= count <= cg_input_sampler.MAX_CANDIDATE_COUNT):
        raise ValueError(
            f"candidateCount must be an integer between 1 and {cg_input_sampler.MAX_CANDIDATE_COUNT}, "
            f"got {count!r}."
        )

    # D-12: the guaranteed floor, held for the whole function. If Tier 1
    # never produces a usable set, THIS is what ships -- never an empty list.
    tier0_candidates = cg_input_sampler.sample_candidate_set(bound, classification.limit, count)
    if not tier0_candidates:
        # See DomainViolationExhaustedError's docstring -- unreachable given
        # `bound` is non-empty and `count >= 1`, kept as a named failure
        # mode rather than an uncaught exception.
        raise DomainViolationExhaustedError(
            f"Tier 0 could not produce a candidate for rule {rule_id!r} despite a non-empty "
            f"bound parameter set -- this indicates a sampler defect, not a request error."
        )

    published_at = cg_structure_checks.fetch_published_at(session, project, resolved_definition_id)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    system_prompt, _ = _load_system_prompt()

    master_secret = os.getenv("LLM_MASTER_SECRET", "")
    settings = load_persisted_llm_settings()
    provider, model, api_key = llm_gateway.resolve_active_provider(settings, master_secret)
    adapter = get_adapter(provider, settings.get("baseUrl"))
    caps = negotiate_structured_output(provider, model, settings.get("baseUrl"))

    prompt = build_generation_prompt(
        rule_id=rule_id,
        classification=classification,
        bound_parameters=bound,
        candidate_count=count,
        negotiated_mode=caps.mode,
    )
    schema = caps.schema_for(cg_schemas.to_strict_json_schema(cg_schemas.GeneratedCandidateSet))
    options = GenerationOptions(
        temperature=0.0,
        max_tokens=_output_token_budget(count, len(bound)),
        output_schema=schema,
    )

    current_prompt = prompt
    flags: list[str] = []
    attempts = 0
    tier1_candidates: "list[dict[str, Any]] | None" = None

    for attempt in range(MAX_RETRIES + 1):
        attempts = attempt + 1
        start = time.monotonic()
        req = GenerateRequest(prompt=current_prompt, system=system_prompt, model=model, provider=provider)
        response = adapter.generate(req, api_key, options=options)
        latency_ms = (time.monotonic() - start) * 1000.0

        if response.truncated:
            # No retry -- an identical scope truncates identically, so a
            # retry burns the most expensive call for zero value. Fall back
            # to Tier 0 rather than failing (D-12).
            flags.append("output_truncated")
            _log_attempt(
                attempts, provider, model, caps.mode, options.max_tokens, response.usage,
                response.finish_reason, ["output_truncated"], latency_ms,
            )
            break

        parsed, parse_error = _extract_json(response.text)
        if parse_error:
            violations = [{"parameterId": None, "code": "bad_json", "message": parse_error}]
            _log_attempt(
                attempts, provider, model, caps.mode, options.max_tokens, response.usage,
                response.finish_reason, ["bad_json"], latency_ms,
            )
            current_prompt = append_domain_feedback(prompt, violations)
            continue

        try:
            typed = cg_schemas.GeneratedCandidateSet.model_validate(parsed)
        except ValidationError as exc:
            violations = _schema_violations(exc)
            _log_attempt(
                attempts, provider, model, caps.mode, options.max_tokens, response.usage,
                response.finish_reason, [v["code"] for v in violations], latency_ms,
            )
            current_prompt = append_domain_feedback(prompt, violations)
            continue

        candidate_assignments = _assignments_from_typed(typed)
        domain_violations: list[dict[str, Any]] = []
        for assignment in candidate_assignments:
            domain_violations.extend(cg_input_sampler.validate_candidate(assignment["parameters"], bound))

        if domain_violations:
            _log_attempt(
                attempts, provider, model, caps.mode, options.max_tokens, response.usage,
                response.finish_reason, sorted({v["code"] for v in domain_violations}), latency_ms,
            )
            current_prompt = append_domain_feedback(prompt, domain_violations)
            continue

        count_strategy_violations = _count_and_strategy_violations(candidate_assignments, count)
        if count_strategy_violations:
            _log_attempt(
                attempts, provider, model, caps.mode, options.max_tokens, response.usage,
                response.finish_reason, sorted({v["code"] for v in count_strategy_violations}), latency_ms,
            )
            current_prompt = append_domain_feedback(prompt, count_strategy_violations)
            continue

        diversity_violations = _diversity_violations(candidate_assignments, bound)
        if diversity_violations:
            _log_attempt(
                attempts, provider, model, caps.mode, options.max_tokens, response.usage,
                response.finish_reason, ["near-duplicate"], latency_ms,
            )
            current_prompt = append_domain_feedback(prompt, diversity_violations)
            continue

        tier1_candidates = candidate_assignments
        _log_attempt(
            attempts, provider, model, caps.mode, options.max_tokens, response.usage,
            response.finish_reason, [], latency_ms,
        )
        break

    if tier1_candidates:
        raw_candidates = tier1_candidates
        tier = 1
    else:
        if "output_truncated" not in flags:
            flags.append("llm_candidates_rejected")
        raw_candidates = tier0_candidates
        tier = 0

    candidates = _postprocess_candidates(
        raw_candidates,
        classification,
        bound,
        excluded,
        resolved_definition_id,
        published_at,
        provider,
        model,
        rule_id,
        generated_at,
        tier,
    )

    return {
        "project": project,
        "definitionId": resolved_definition_id,
        "publishedAt": published_at,
        "ruleId": rule_id,
        "determinabilityClass": classification.determinability,
        "ruleLimit": classification.limit.value if classification.limit is not None else None,
        "boundParameters": [_bound_parameter_view(row) for row in bound],
        "excludedParameters": excluded,
        "candidates": candidates,
        "tier": tier,
        "attempts": attempts,
        "provider": provider,
        "model": model,
        "flags": flags,
    }
