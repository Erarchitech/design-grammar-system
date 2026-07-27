"""Tests for cg_input_generation.py -- the Tier 1 orchestrator (Phase 38
Plan 04: GHIN-01/02/03/04).

No live Neo4j, no live LLM. A Neo4j session is faked with a small object
that routes by the query's `// op=NAME` tag to a canned row list, mirroring
`test_cg_input_bindings.py`'s `_FakeSession` precedent but extended to
support the three distinct reads this module issues (`read_rule_limit`,
`_list_published_parameters`, `fetch_published_at`). An LLM adapter is faked
with a queue of responses, mirroring `test_cg_recognition.py`'s
`_FakeAdapterForRetry` precedent.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

import cg_input_bindings  # noqa: E402
import cg_input_generation as gen  # noqa: E402
from cg_fixtures import (  # noqa: E402
    RULE_DIRECT_PARAM_ID,
    RULE_GEOMETRY_ID,
    RULE_MONOTONE_ID,
    RULE_UNKNOWN_ID,
    direct_param_limit_rows,
    geometry_rule_limit_rows,
    no_builtin_limit_rows,
    published_parameter_rows,
)
from llm_gateway import GenerateResponse, StructuredOutputCapability  # noqa: E402


@pytest.fixture(autouse=True)
def _no_network_structured_output_negotiation(monkeypatch):
    """`generate_inputs` calls `negotiate_structured_output()`, which for the
    Ollama fallback provider makes a real network probe. Tests must never
    depend on that -- pin the negotiated mode to "none" everywhere unless a
    test explicitly overrides it."""
    monkeypatch.setattr(
        gen,
        "negotiate_structured_output",
        lambda provider, model, base_url=None: StructuredOutputCapability(mode="none"),
    )


# ── Fake Neo4j session -- routes by the query's op tag ──


class _FakeResult(list):
    """A plain list that also supports `.single()`, matching both call
    shapes this module's upstream helpers use (`list(result)` iteration in
    `_list_published_parameters`, `.single()` in
    `cg_structure_checks.fetch_published_at`)."""

    def single(self):
        return self[0] if self else None


class _FakeGenerationSession:
    def __init__(self, rule_limit_rows, published_parameters, published_at="2026-07-08T00:00:00Z"):
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
        raise AssertionError(f"Unexpected query in _FakeGenerationSession: {query[:80]!r}")


def _direct_param_session() -> _FakeGenerationSession:
    return _FakeGenerationSession(direct_param_limit_rows(), published_parameter_rows())


def _geometry_session() -> _FakeGenerationSession:
    return _FakeGenerationSession(geometry_rule_limit_rows(), published_parameter_rows())


def _monotone_session() -> _FakeGenerationSession:
    return _FakeGenerationSession(geometry_rule_limit_rows(), published_parameter_rows())


# ── Fake LLM adapter -- queued responses, mirrors test_cg_recognition.py's
# _FakeAdapterForRetry precedent ──


class _FakeGenerationAdapter:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.call_count = 0
        self.prompts_seen: list[str] = []

    def generate(self, req, api_key, options=None):
        self.call_count += 1
        self.prompts_seen.append(req.prompt)
        item = self._responses.pop(0)
        if isinstance(item, GenerateResponse):
            return item
        return GenerateResponse(text=item, provider="fake", model="fake-model", usage={})


def _candidate_set_text(entries: list[dict]) -> str:
    """`entries` is a list of `(strategy, [(parameterId, type, value), ...])`
    tuples' worth of raw dicts -- build the well-formed GeneratedCandidateSet
    JSON text an LLM would return."""
    candidates = []
    for strategy, params in entries:
        parameters = []
        for parameter_id, ptype, value in params:
            entry = {
                "parameterId": parameter_id,
                "type": ptype,
                "numberValue": None,
                "integerValue": None,
                "booleanValue": None,
            }
            key = {"Number": "numberValue", "Integer": "integerValue", "Boolean": "booleanValue"}[ptype]
            entry[key] = value
            parameters.append(entry)
        candidates.append({"strategy": strategy, "rationale": "test rationale", "parameters": parameters})
    return json.dumps({"candidates": candidates})


_DIRECT_PARAM_VALID_TEXT = _candidate_set_text(
    [
        ("conservative", [("Spans", "Number", 3.0)]),
        ("balanced", [("Spans", "Number", 6.0)]),
        ("exploratory", [("Spans", "Number", 9.0)]),
        ("near-limit", [("Spans", "Number", 11.5)]),
    ]
)

_DIRECT_PARAM_OUT_OF_DOMAIN_TEXT = _candidate_set_text(
    [("conservative", [("Spans", "Number", 50.0)])]
)

_DIRECT_PARAM_ONE_VALID_TEXT = _candidate_set_text(
    [("conservative", [("Spans", "Number", 3.0)])]
)

_TRUNCATED_RESPONSE = GenerateResponse(
    text="", provider="fake", model="fake-model", usage={}, truncated=True, finish_reason="length"
)


# ── Well-formed in-domain set -> those candidates are used ──


class TestTier1Success:
    def test_well_formed_in_domain_set_is_used_tier_1(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID)

        assert result["tier"] == 1
        assert result["attempts"] == 1
        assert len(result["candidates"]) == 4
        assert fake_adapter.call_count == 1

    def test_join_a_divergence_honored_parameter_id_is_reinstate_id(self, monkeypatch):
        # published_parameter_rows()'s HTotal row has reinstateParameterId
        # "Spans", deliberately divergent from parameterName "HTotal" (the
        # JOIN A fixture, plan 38-02). The response's parameterId MUST be
        # the reinstateParameterId -- that is what
        # ParameterReinstateComponent.cs actually matches on -- while
        # displayName carries the human-readable parameterName.
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID)

        candidate = result["candidates"][0]
        assert candidate["parameters"][0]["parameterId"] == "Spans"
        assert candidate["parameters"][0]["displayName"] == "HTotal"
        assert result["boundParameters"][0]["reinstateParameterId"] == "Spans"
        assert result["boundParameters"][0]["parameterName"] == "HTotal"


class TestRetryLoop:
    def test_out_of_domain_then_valid_retries_and_succeeds_at_attempt_2(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_OUT_OF_DOMAIN_TEXT, _DIRECT_PARAM_ONE_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(
            _direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID, candidate_count=1
        )

        assert result["tier"] == 1
        assert result["attempts"] == 2
        assert fake_adapter.call_count == 2
        assert "CORRECTIVE FEEDBACK" in fake_adapter.prompts_seen[1]
        assert "out-of-domain" in fake_adapter.prompts_seen[1]

    def test_never_returns_anything_usable_falls_back_to_tier_0_floor(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_OUT_OF_DOMAIN_TEXT] * 3)
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(
            _direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID
        )

        assert result["tier"] == 0
        assert result["attempts"] == 3
        assert "llm_candidates_rejected" in result["flags"]
        assert len(result["candidates"]) >= 1
        for candidate in result["candidates"]:
            assert candidate["parameters"], "Tier 0 candidate must still carry parameter values"

    def test_truncated_response_no_retry_tier_0_fallback(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_TRUNCATED_RESPONSE])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID)

        assert result["tier"] == 0
        assert result["attempts"] == 1
        assert fake_adapter.call_count == 1
        assert result["flags"] == ["output_truncated"]

    def test_diversity_violation_retries(self, monkeypatch):
        # 6.0 and 6.1 are both step-aligned (domainStep=0.1) and in-domain --
        # this must be REJECTED for insufficient diversity, not domain
        # invalidity, so the retry path exercised here is specifically the
        # near-duplicate gate (D-13), not the domain validator.
        near_duplicate_text = _candidate_set_text(
            [
                ("conservative", [("Spans", "Number", 6.0)]),
                ("balanced", [("Spans", "Number", 6.1)]),
            ]
        )
        valid_text = _candidate_set_text(
            [
                ("conservative", [("Spans", "Number", 0.5)]),
                ("balanced", [("Spans", "Number", 12.0)]),
            ]
        )
        fake_adapter = _FakeGenerationAdapter([near_duplicate_text, valid_text])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(
            _direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID, candidate_count=2
        )

        assert result["tier"] == 1
        assert result["attempts"] == 2
        assert "near-duplicate" in fake_adapter.prompts_seen[1]

    def test_provider_resolved_exactly_once_across_multi_attempt_run(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_OUT_OF_DOMAIN_TEXT, _DIRECT_PARAM_ONE_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        call_count = {"n": 0}
        real_resolve = gen.llm_gateway.resolve_active_provider

        def _counting_resolve(settings, master_secret):
            call_count["n"] += 1
            return real_resolve(settings, master_secret)

        monkeypatch.setattr(gen.llm_gateway, "resolve_active_provider", _counting_resolve)

        result = gen.generate_inputs(
            _direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID, candidate_count=1
        )

        assert result["attempts"] >= 2
        assert call_count["n"] == 1


class TestProvenanceAndSatisfaction:
    def test_provenance_completeness_all_ten_keys_non_empty_where_expected(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID)

        expected_keys = {
            "source",
            "sourceRuleId",
            "provider",
            "model",
            "confidence",
            "definitionId",
            "publishedAt",
            "strategy",
            "determinabilityClass",
            "generatedAt",
        }
        for candidate in result["candidates"]:
            provenance = candidate["provenance"]
            assert set(provenance.keys()) == expected_keys
            assert provenance["source"] == "ai-generated"
            assert provenance["sourceRuleId"]
            assert provenance["provider"]
            assert provenance["generatedAt"]

    def test_geometry_required_every_claim_is_undeterminable(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter(["not json"] * 3)
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_geometry_session(), "p37-structure", "frame.gh", RULE_GEOMETRY_ID)

        assert result["determinabilityClass"] == "geometry-required"
        assert result["candidates"]
        for candidate in result["candidates"]:
            assert candidate["ruleSatisfaction"]["claim"] == "undeterminable"

    def test_type_mapping_float_integer_boolean_only_text_geometry_excluded(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter(["not json"] * 3)
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_geometry_session(), "p37-structure", "frame.gh", RULE_GEOMETRY_ID)

        for candidate in result["candidates"]:
            types = {p["type"] for p in candidate["parameters"]}
            assert types <= {"Number", "Integer", "Boolean"}

        reasons = {row["reason"] for row in result["excludedParameters"]}
        assert "unsupported-datatype" in reasons

    def test_state_payload_has_ds_prefixed_state_id_and_iso8601_captured_at(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(_direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID)

        from datetime import datetime

        for candidate in result["candidates"]:
            state_payload = candidate["statePayload"]
            assert state_payload["stateId"].startswith("DS_")
            parsed = datetime.fromisoformat(state_payload["capturedAtUtc"].replace("Z", "+00:00"))
            assert parsed.tzinfo is not None

    def test_monotone_bound_metric_expression_evaluated(self, monkeypatch):
        monotone_text = _candidate_set_text(
            [
                (
                    "conservative",
                    [("Spans", "Number", 3.0), ("SpansCount", "Integer", 5)],
                ),
            ]
        )
        fake_adapter = _FakeGenerationAdapter([monotone_text])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = gen.generate_inputs(
            _monotone_session(), "p37-structure", "frame.gh", RULE_MONOTONE_ID, candidate_count=1
        )

        satisfaction = result["candidates"][0]["ruleSatisfaction"]
        # HTotal + 0.1 * SpansCount = 3.0 + 0.5 = 3.5 <= 75 -> satisfied.
        assert satisfaction["claim"] == "satisfied"
        assert "HTotal + 0.1 * SpansCount" in satisfaction["basis"]


class TestErrorPaths:
    def test_rule_not_found_propagates(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        session = _FakeGenerationSession([], published_parameter_rows())
        with pytest.raises(cg_input_bindings.RuleNotFoundError):
            gen.generate_inputs(session, "p37-structure", "frame.gh", RULE_UNKNOWN_ID)
        assert fake_adapter.call_count == 0

    def test_no_eligible_parameters_via_override(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        with pytest.raises(gen.NoEligibleParametersError):
            gen.generate_inputs(
                _direct_param_session(),
                "p37-structure",
                "frame.gh",
                RULE_DIRECT_PARAM_ID,
                parameter_overrides=["DoesNotExist"],
            )

    def test_candidate_count_out_of_range_raises_value_error(self, monkeypatch):
        fake_adapter = _FakeGenerationAdapter([_DIRECT_PARAM_VALID_TEXT])
        monkeypatch.setattr(gen, "get_adapter", lambda provider, base_url=None: fake_adapter)

        with pytest.raises(ValueError):
            gen.generate_inputs(
                _direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID, candidate_count=99
            )
        with pytest.raises(ValueError):
            gen.generate_inputs(
                _direct_param_session(), "p37-structure", "frame.gh", RULE_DIRECT_PARAM_ID, candidate_count=0
            )
