"""SC1 measurement harness for AI-generated Grasshopper script inputs (Phase
38 plan 07: GHIN-01/02/03).

Turns the five SC1 acceptance thresholds `spec/API.md`'s SC1 table fixes
(plan 38-01) into pytest assertions computed over the Frame fixture, closing
38-RESEARCH.md's Nyquist note: Phase 35 shipped its recognition plumbing and
only later discovered the quality had never been measured. This module is
the mechanism that makes that failure impossible to repeat here -- every
number below is computed, not asserted by sentence.

No live Neo4j, no live LLM call. A Neo4j session is faked exactly like
`test_cg_input_generation.py`'s `_FakeGenerationSession` (routes by the
query's `// op=NAME` tag to a canned row list). The two scenarios that need
a realistic multi-candidate LLM response (SC1-a/SC1-b, over the Frame
fixture's `direct-parameter` and `monotone-bound` rules) go through
`InputGenCassetteAdapter`, a small record/replay double scoped to this
harness (see `input_gen_eval/cassettes/README.md` for the replay-by-default
/ loud-on-miss / stale-cassette policy, mirroring the Phase 35
recognition-eval precedent, plan 35-13, verbatim). SC1-c and SC1-e reuse
`test_cg_recognition.py`'s `_FakeAdapterForRetry` shape directly (a queued,
in-memory fake -- no cassette needed, since a useless/unparseable model
response is expressly what those two scenarios exercise).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

import cg_input_bindings  # noqa: E402
import cg_input_generation as gen  # noqa: E402
from cg_fixtures import (  # noqa: E402
    FIXTURE_PROJECT,
    FRAME_DEFINITION_ID,
    RULE_DIRECT_PARAM_ID,
    RULE_GEOMETRY_ID,
    RULE_MONOTONE_ID,
    direct_param_limit_rows,
    geometry_rule_limit_rows,
    published_parameter_rows,
)
from input_gen_eval import scoring  # noqa: E402
from llm_gateway import GenerateResponse, StructuredOutputCapability  # noqa: E402

_CASSETTES_DIR = Path(__file__).resolve().parent / "input_gen_eval" / "cassettes"
INPUT_GEN_EVAL_MODE = os.environ.get("INPUT_GEN_EVAL_MODE", "replay")


@pytest.fixture(autouse=True)
def _no_network_structured_output_negotiation(monkeypatch):
    """`generate_inputs` calls `negotiate_structured_output()`, which for
    the Ollama fallback provider makes a real network probe. Every test in
    this module pins the negotiated mode to "none" -- matching
    `test_cg_input_generation.py`'s identically-named fixture -- so the
    prompt text `InputGenCassetteAdapter` compares against a cassette is
    reproducible independently of whatever provider happens to be
    configured on the machine running this suite."""
    monkeypatch.setattr(
        gen,
        "negotiate_structured_output",
        lambda provider, model, base_url=None: StructuredOutputCapability(mode="none"),
    )


# ── Fake Neo4j session -- routes by the query's op tag (mirrors
# test_cg_input_generation.py's _FakeGenerationSession) ──


class _FakeResult(list):
    def single(self):
        return self[0] if self else None


class _FakeEvalSession:
    def __init__(self, rule_limit_rows, published_parameters, published_at="2026-07-27T00:00:00Z"):
        self._rule_limit_rows = rule_limit_rows
        self._published_parameters = published_parameters
        self._published_at = published_at

    def run(self, query, params=None):
        del params
        if "READ_RULE_LIMIT" in query:
            return _FakeResult(self._rule_limit_rows)
        if "GENERATE_INPUTS_LIST_PARAMETERS" in query:
            return _FakeResult(self._published_parameters)
        if "CHECK_PUBLISHED_AT" in query:
            return _FakeResult([{"publishedAt": self._published_at}])
        raise AssertionError(f"Unexpected query in _FakeEvalSession: {query[:80]!r}")


def _direct_param_session() -> _FakeEvalSession:
    return _FakeEvalSession(direct_param_limit_rows(), published_parameter_rows())


def _monotone_session() -> _FakeEvalSession:
    # RULE_MONOTONE_ID's real read_rule_limit target (?height <= 75, from
    # llm/structure_rules.json's R_URB_HEIGHT_MAX_75_V binding) is the SAME
    # graph fact geometry_rule_limit_rows() encodes -- test_cg_input_generation.py's
    # own _monotone_session() reuses this exact fixture for exactly this reason.
    return _FakeEvalSession(geometry_rule_limit_rows(), published_parameter_rows())


def _geometry_session() -> _FakeEvalSession:
    return _FakeEvalSession(geometry_rule_limit_rows(), published_parameter_rows())


# ── Fake LLM adapter for the SC1-c/SC1-e scenarios -- reuses
# test_cg_recognition.py's _FakeAdapterForRetry shape (queued responses, no
# disk cassette): a useless/unparseable model is exactly what these two
# scenarios exercise, so a plain in-memory fake is the correct double, not a
# recorded interaction. ──


class _FakeUselessAdapter:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, req, api_key, options=None):
        self.call_count += 1
        item = self._responses.pop(0)
        if isinstance(item, GenerateResponse):
            return item
        return GenerateResponse(text=item, provider="fake", model="fake-model", usage={})


# ── Cassette adapter for the SC1-a/SC1-b scenarios -- see
# input_gen_eval/cassettes/README.md for the full policy this implements. ──


class CassetteMissError(RuntimeError):
    """Raised in `replay` mode (the default) when no cassette file exists
    for this scenario. NEVER falls through to a live provider call --
    following the Phase 35 recognition-eval precedent (plan 35-13)
    verbatim."""


class StaleCassetteError(RuntimeError):
    """Raised in `replay` mode when a cassette file exists but its recorded
    `recordedPrompt`/`recordedSystem` no longer matches what the runtime
    computes today for this scenario -- the fixture data or the prompt
    template changed since the cassette was recorded. Re-record it (see
    `input_gen_eval/cassettes/README.md`); never hand-patch the stored
    response to make a stale cassette pass again."""


class InputGenCassetteAdapter:
    """Minimal record/replay double for `llm_gateway`'s `LLMAdapter`
    contract (`generate(req, api_key, options=None) -> GenerateResponse`),
    scoped to this eval harness. Keyed by a fixed, human-readable scenario
    `name` -- one file per fixture scenario under
    `input_gen_eval/cassettes/<name>.json` -- rather than a content hash;
    staleness is instead detected by comparing the FULL recorded prompt/
    system text to what `cg_input_generation.build_generation_prompt`/the
    system-prompt loader compute today, which catches a fixture or
    prompt-template change exactly, not only when a hash of it happens to
    differ.

    Mode is read from `INPUT_GEN_EVAL_MODE` (module-level default
    `"replay"`, i.e. $0/no secrets) unless overridden at construction:

    - `replay` (default): reads the cassette. A missing file raises
      `CassetteMissError`; a prompt/system mismatch raises
      `StaleCassetteError`. Neither ever falls through to a live call.
    - `record`: calls the wrapped real adapter and overwrites the cassette
      file with its response. Gated behind this explicit environment
      variable so recording can never happen by accident during a normal
      `pytest` run.
    """

    def __init__(self, name: str, wrapped: "Any | None" = None, *, mode: "str | None" = None):
        self.name = name
        self._wrapped = wrapped
        self.mode = mode if mode is not None else INPUT_GEN_EVAL_MODE
        if self.mode not in ("replay", "record"):
            raise ValueError(
                f"unknown INPUT_GEN_EVAL_MODE {self.mode!r} for scenario {name!r} -- "
                f"must be 'replay' or 'record'."
            )

    def _path(self) -> Path:
        return _CASSETTES_DIR / f"{self.name}.json"

    def generate(self, req: Any, api_key: "str | None", options: Any = None) -> GenerateResponse:
        path = self._path()

        if self.mode == "replay":
            if not path.exists():
                raise CassetteMissError(
                    f"cassette miss for scenario {self.name!r} (expected at {path}). "
                    f"INPUT_GEN_EVAL_MODE=replay never falls through to a live call. "
                    f"To record it: INPUT_GEN_EVAL_MODE=record python -m pytest "
                    f"data-service/tests/test_input_gen_eval.py -k {self.name}"
                )
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("recordedPrompt") != req.prompt or payload.get("recordedSystem") != req.system:
                raise StaleCassetteError(
                    f"cassette {self.name!r} at {path} was recorded against a different "
                    f"prompt/system than the runtime computes today for this scenario -- "
                    f"re-record it (see input_gen_eval/cassettes/README.md); never "
                    f"hand-patch the stored response."
                )
            return GenerateResponse(
                text=payload["responseText"],
                provider=payload.get("provider", "fake"),
                model=payload.get("model", "fake-model"),
                usage=payload.get("usage") or {},
                truncated=payload.get("truncated", False),
                finish_reason=payload.get("finishReason"),
            )

        if self._wrapped is None:
            raise CassetteMissError(
                f"INPUT_GEN_EVAL_MODE=record requires a real wrapped adapter for "
                f"scenario {self.name!r}, but none was supplied."
            )
        response = self._wrapped.generate(req, api_key, options)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "recordedPrompt": req.prompt,
                    "recordedSystem": req.system,
                    "responseText": response.text,
                    "provider": response.provider,
                    "model": response.model,
                    "usage": response.usage,
                    "truncated": response.truncated,
                    "finishReason": response.finish_reason,
                    "recordedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return response


# ── Task 1's own scoring-function tests (`-k "scoring"`) -- pure, no
# session/adapter machinery needed. ──


def _param_view(parameter_id: str, ptype: str, value: Any, display_name: "str | None" = None) -> dict[str, Any]:
    return {
        "parameterId": parameter_id,
        "displayName": display_name or parameter_id,
        "type": ptype,
        "numberValue": value if ptype == "Number" else None,
        "integerValue": value if ptype == "Integer" else None,
        "booleanValue": value if ptype == "Boolean" else None,
    }


def _candidate(parameters: list[dict[str, Any]], claim: "str | None" = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"parameters": parameters}
    if claim is not None:
        entry["ruleSatisfaction"] = {"claim": claim, "basis": "test fixture"}
    return entry


_HTOTAL_BOUND = [
    {
        "reinstateParameterId": "Spans",
        "parameterName": "HTotal",
        "stateType": "Number",
        "domainMin": 0.5,
        "domainMax": 12.0,
        "domainStep": 0.1,
    }
]

_MOCK_GEOMETRY_REQUIRED_CLASSIFICATION = cg_input_bindings.RuleClassification(
    ruleId=RULE_GEOMETRY_ID,
    determinability="geometry-required",
    parameterNames=(),
    metricExpression=None,
    monotoneIn=(),
    limit=None,
    source="default",
)

_MOCK_DIRECT_PARAM_CLASSIFICATION = cg_input_bindings.RuleClassification(
    ruleId=RULE_DIRECT_PARAM_ID,
    determinability="direct-parameter",
    parameterNames=("HTotal",),
    metricExpression=None,
    monotoneIn=(),
    limit=cg_input_bindings.RuleLimit(operator="<=", value=12.0, datatype="xsd:decimal", variableName="?htotal"),
    source="binding",
)


class TestScoringFunctions:
    def test_scoring_domain_compliance_all_in_domain_is_1_0(self):
        candidates = [
            _candidate([_param_view("Spans", "Number", 3.0)]),
            _candidate([_param_view("Spans", "Number", 6.0)]),
        ]
        assert scoring.score_domain_compliance(candidates, _HTOTAL_BOUND) == 1.0

    def test_scoring_domain_compliance_one_out_of_domain_lowers_the_fraction(self):
        candidates = [
            _candidate([_param_view("Spans", "Number", 3.0)]),
            _candidate([_param_view("Spans", "Number", 999.0)]),  # out-of-domain
        ]
        assert scoring.score_domain_compliance(candidates, _HTOTAL_BOUND) == 0.5

    def test_scoring_domain_compliance_empty_candidates_is_0_0_not_vacuous(self):
        assert scoring.score_domain_compliance([], _HTOTAL_BOUND) == 0.0

    def test_scoring_rule_satisfaction_returns_none_for_geometry_required(self):
        candidates = [_candidate([_param_view("Spans", "Number", 3.0)], claim="undeterminable")]
        assert scoring.score_rule_satisfaction(candidates, _MOCK_GEOMETRY_REQUIRED_CLASSIFICATION) is None

    def test_scoring_rule_satisfaction_measures_the_satisfied_fraction(self):
        candidates = [
            _candidate([_param_view("Spans", "Number", 3.0)], claim="satisfied"),
            _candidate([_param_view("Spans", "Number", 6.0)], claim="satisfied"),
            _candidate([_param_view("Spans", "Number", 9.0)], claim="satisfied"),
            _candidate([_param_view("Spans", "Number", 20.0)], claim="violated"),
        ]
        assert scoring.score_rule_satisfaction(candidates, _MOCK_DIRECT_PARAM_CLASSIFICATION) == 0.75

    def test_scoring_diversity_single_candidate_is_1_0_no_raise(self):
        candidates = [_candidate([_param_view("Spans", "Number", 3.0)])]
        assert scoring.score_diversity(candidates, _HTOTAL_BOUND) == 1.0

    def test_scoring_diversity_measures_the_minimum_pairwise_distance(self):
        # Domain [0.5, 12.0] -> span 11.5. Values 3.0/3.1/9.0: the closest
        # pair (3.0, 3.1) is |0.1| / 11.5 =~ 0.0087 -- the true minimum
        # across all three pairs, not the mean.
        candidates = [
            _candidate([_param_view("Spans", "Number", 3.0)]),
            _candidate([_param_view("Spans", "Number", 3.1)]),
            _candidate([_param_view("Spans", "Number", 9.0)]),
        ]
        distance = scoring.score_diversity(candidates, _HTOTAL_BOUND)
        assert distance == pytest.approx(0.1 / 11.5, abs=1e-6)

    def test_scoring_overclaim_counts_satisfied_claims_on_a_geometry_required_rule(self):
        candidates = [
            _candidate([_param_view("Spans", "Number", 3.0)], claim="satisfied"),
            _candidate([_param_view("Spans", "Number", 6.0)], claim="undeterminable"),
        ]
        assert scoring.score_overclaim(candidates, _MOCK_GEOMETRY_REQUIRED_CLASSIFICATION) == 1

    def test_scoring_overclaim_is_always_0_for_a_non_geometry_required_rule(self):
        candidates = [_candidate([_param_view("Spans", "Number", 3.0)], claim="satisfied")]
        assert scoring.score_overclaim(candidates, _MOCK_DIRECT_PARAM_CLASSIFICATION) == 0

    def test_scoring_candidate_set_assembles_all_four_metrics_and_the_count(self):
        candidates = [
            _candidate([_param_view("Spans", "Number", 3.0)], claim="satisfied"),
            _candidate([_param_view("Spans", "Number", 11.5)], claim="satisfied"),
        ]
        summary = scoring.score_candidate_set(candidates, _HTOTAL_BOUND, _MOCK_DIRECT_PARAM_CLASSIFICATION)
        assert summary == {
            "domainCompliance": 1.0,
            "ruleSatisfaction": 1.0,
            "diversity": pytest.approx(8.5 / 11.5),
            "overclaimCount": 0,
            "candidateCount": 2,
        }


# ── Task 2 -- the five SC1 thresholds, asserted end to end over the Frame
# fixture through generate_inputs(). ──


class TestSC1Thresholds:
    def test_sc1_a_and_sc1_b_direct_parameter_domain_compliance_and_rule_satisfaction(self, monkeypatch):
        adapter = InputGenCassetteAdapter("direct_parameter")
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: adapter)

        result = gen.generate_inputs(
            _direct_param_session(), FIXTURE_PROJECT, FRAME_DEFINITION_ID, RULE_DIRECT_PARAM_ID
        )
        classification = cg_input_bindings.classify_rule(
            _direct_param_session(),
            RULE_DIRECT_PARAM_ID,
            FIXTURE_PROJECT,
            cg_input_bindings.load_input_bindings(),
        )
        summary = scoring.score_candidate_set(result["candidates"], result["boundParameters"], classification)
        print(f"[SC1 direct-parameter] {summary}")

        domain_compliance = summary["domainCompliance"]
        if domain_compliance != 1.0:
            offenders = [
                (c["candidateId"], gen.cg_input_sampler.validate_candidate(
                    scoring._extract_values(c), result["boundParameters"]
                ))
                for c in result["candidates"]
            ]
            pytest.fail(f"SC1-a FAILED: domainCompliance={domain_compliance} (threshold 100%); offending candidates: {offenders}")
        assert domain_compliance == 1.0  # SC1-a

        rule_satisfaction = summary["ruleSatisfaction"]
        assert rule_satisfaction is not None, "direct-parameter must never be undeterminable"
        assert rule_satisfaction >= 0.75, f"SC1-b FAILED: ruleSatisfaction={rule_satisfaction} < 0.75"  # SC1-b

    def test_sc1_a_and_sc1_b_monotone_bound_domain_compliance_and_rule_satisfaction(self, monkeypatch):
        adapter = InputGenCassetteAdapter("monotone_bound")
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: adapter)

        result = gen.generate_inputs(
            _monotone_session(), FIXTURE_PROJECT, FRAME_DEFINITION_ID, RULE_MONOTONE_ID
        )
        classification = cg_input_bindings.classify_rule(
            _monotone_session(),
            RULE_MONOTONE_ID,
            FIXTURE_PROJECT,
            cg_input_bindings.load_input_bindings(),
        )
        summary = scoring.score_candidate_set(result["candidates"], result["boundParameters"], classification)
        print(f"[SC1 monotone-bound] {summary}")

        domain_compliance = summary["domainCompliance"]
        if domain_compliance != 1.0:
            offenders = [
                (c["candidateId"], gen.cg_input_sampler.validate_candidate(
                    scoring._extract_values(c), result["boundParameters"]
                ))
                for c in result["candidates"]
            ]
            pytest.fail(f"SC1-a FAILED: domainCompliance={domain_compliance} (threshold 100%); offending candidates: {offenders}")
        assert domain_compliance == 1.0  # SC1-a

        rule_satisfaction = summary["ruleSatisfaction"]
        assert rule_satisfaction is not None, "monotone-bound must never be undeterminable"
        assert rule_satisfaction >= 0.75, f"SC1-b FAILED: ruleSatisfaction={rule_satisfaction} < 0.75"  # SC1-b

    def test_sc1_c_useless_model_still_yields_a_valid_tier0_floor(self, monkeypatch):
        # An unparseable response on every attempt forces Tier-1 exhaustion
        # -> Tier 0's guaranteed floor ships (D-12). The Tier 0 floor is the
        # ONLY thing this scenario measures, so a plain in-memory fake
        # adapter is correct here, not a cassette.
        adapter = _FakeUselessAdapter(["not json"] * 3)
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: adapter)

        result = gen.generate_inputs(
            _direct_param_session(), FIXTURE_PROJECT, FRAME_DEFINITION_ID, RULE_DIRECT_PARAM_ID
        )

        assert result["tier"] == 0
        assert "llm_candidates_rejected" in result["flags"]
        assert len(result["candidates"]) >= 1, "SC1-c FAILED: expected >= 1 candidate from the Tier 0 floor"

        domain_compliance = scoring.score_domain_compliance(result["candidates"], result["boundParameters"])
        print(f"[SC1-c] candidateCount={len(result['candidates'])} domainCompliance={domain_compliance}")
        assert domain_compliance == 1.0, (
            f"SC1-c FAILED: the Tier 0 fallback candidates are themselves invalid "
            f"(domainCompliance={domain_compliance}) -- the floor is worthless if it is "
            f"not itself domain-valid"
        )

    def test_sc1_d_diversity_at_least_0_10_on_the_default_four_candidate_set(self, monkeypatch):
        adapter = InputGenCassetteAdapter("direct_parameter")
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: adapter)

        result = gen.generate_inputs(
            _direct_param_session(), FIXTURE_PROJECT, FRAME_DEFINITION_ID, RULE_DIRECT_PARAM_ID
        )
        assert len(result["candidates"]) == 4

        diversity = scoring.score_diversity(result["candidates"], result["boundParameters"])
        print(f"[SC1-d] diversity={diversity}")
        assert diversity >= 0.10, f"SC1-d FAILED: diversity={diversity} < 0.10"

    def test_sc1_e_geometry_required_rule_never_overclaims_despite_a_readable_swrl_limit(self, monkeypatch):
        # The SC1-e fixture rule (RULE_GEOMETRY_ID) has a REAL, readable SWRL
        # limit on the graph -- proving the system DECLINES to claim
        # satisfaction, not that it merely lacks data to claim with.
        session_for_limit_check = _geometry_session()
        limit = cg_input_bindings.read_rule_limit(session_for_limit_check, RULE_GEOMETRY_ID, FIXTURE_PROJECT)
        assert limit is not None, "SC1-e fixture rule must have a readable SWRL limit"

        classification = cg_input_bindings.classify_rule(
            _geometry_session(), RULE_GEOMETRY_ID, FIXTURE_PROJECT, cg_input_bindings.load_input_bindings()
        )
        assert classification.determinability == "geometry-required"
        assert classification.limit is None, (
            "classify_rule must force limit=None for geometry-required even though "
            "read_rule_limit found a real limit on the graph"
        )

        adapter = _FakeUselessAdapter(["not json"] * 3)
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: adapter)

        result = gen.generate_inputs(
            _geometry_session(), FIXTURE_PROJECT, FRAME_DEFINITION_ID, RULE_GEOMETRY_ID
        )
        assert result["determinabilityClass"] == "geometry-required"
        assert result["candidates"], "geometry-required must still produce candidates, just no satisfaction claim"

        overclaim_count = scoring.score_overclaim(result["candidates"], classification)
        print(f"[SC1-e] overclaimCount={overclaim_count}")
        assert overclaim_count == 0, f"SC1-e FAILED: overclaimCount={overclaim_count} (threshold exactly 0)"
