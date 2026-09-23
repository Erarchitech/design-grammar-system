"""D-19 provenance void-guard tests for the 1204 benchmark.

Harness-side only (D-23). Covers the sibling `LLM_SAMPLE_PROVENANCE_FIELDS`
tuple + `assert_llm_sample_provenance` guard landed beside — never replacing —
`REQUIRED_PROVENANCE_FIELDS` / `assert_provenance` in `corpus.py`:
a sample missing any unconditional field is void, and a provenance block
carrying credentials or api-key-shaped material is rejected before any score.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

from recognition_eval import corpus as corpus_module  # noqa: E402
from recognition_eval.corpus import (  # noqa: E402
    CONDITIONAL_LLM_SAMPLE_PROVENANCE_FIELDS,
    LLM_SAMPLE_PROVENANCE_FIELDS,
    REQUIRED_PROVENANCE_FIELDS,
    ProvenanceError,
    assert_llm_sample_provenance,
    assert_provenance,
)

# The fields a sample must always carry: the D-19 tuple minus the ones recorded
# only when the provider returned them / the provider is local.
_UNCONDITIONAL_FIELDS = [
    field
    for field in LLM_SAMPLE_PROVENANCE_FIELDS
    if field not in CONDITIONAL_LLM_SAMPLE_PROVENANCE_FIELDS
]


def _full_sample(**overrides) -> dict:
    """A fully-populated, credential-free sample for every unconditional field."""
    sample = {
        "adapter": "openai",
        "endpointHost": "api.openai.com",
        "requestedModelId": "gpt-4o-mini",
        "servedModelId": "gpt-4o-mini-2024-07-18",
        "responseId": "chatcmpl-abc123",
        "systemFingerprint": "fp_44709d6fcb",
        "ollamaWeightsDigest": None,
        "promptFilePath": "prompts/recognition_system.md",
        "promptSha256": "0" * 64,
        "promptVersion": "r1",
        "renderedRequestSha256": "1" * 64,
        "samplingParamsAsSent": {"temperature": 0.0},
        "negotiatedMode": "json_schema",
        "gatewayCommit": "deadbeef",
        "serviceCommit": "deadbeef",
        "inputSha256": "2" * 64,
        "sampleIndex": 0,
        "timestamp": "2026-01-01T00:00:00Z",
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        "finishReason": "stop",
    }
    sample.update(overrides)
    return sample


class TestD19VoidGuard:
    def test_full_sample_passes(self):
        assert assert_llm_sample_provenance(_full_sample()) is None

    def test_llm_sample_provenance_fields_is_the_d19_tuple(self):
        assert isinstance(LLM_SAMPLE_PROVENANCE_FIELDS, tuple)
        assert LLM_SAMPLE_PROVENANCE_FIELDS == (
            "adapter",
            "endpointHost",
            "requestedModelId",
            "servedModelId",
            "responseId",
            "systemFingerprint",
            "ollamaWeightsDigest",
            "promptFilePath",
            "promptSha256",
            "promptVersion",
            "renderedRequestSha256",
            "samplingParamsAsSent",
            "negotiatedMode",
            "gatewayCommit",
            "serviceCommit",
            "inputSha256",
            "sampleIndex",
            "timestamp",
            "usage",
            "finishReason",
        )

    @pytest.mark.parametrize("field", _UNCONDITIONAL_FIELDS)
    def test_removing_an_unconditional_field_is_void(self, field):
        sample = _full_sample()
        del sample[field]
        with pytest.raises(ProvenanceError):
            assert_llm_sample_provenance(sample)

    @pytest.mark.parametrize("field", _UNCONDITIONAL_FIELDS)
    def test_none_unconditional_field_is_void(self, field):
        with pytest.raises(ProvenanceError):
            assert_llm_sample_provenance(_full_sample(**{field: None}))

    def test_missing_message_names_the_field(self):
        sample = _full_sample()
        del sample["promptSha256"]
        with pytest.raises(ProvenanceError) as excinfo:
            assert_llm_sample_provenance(sample)
        assert "missing required provenance field" in str(excinfo.value)

    def test_conditional_fields_may_be_absent(self):
        sample = _full_sample()
        for field in CONDITIONAL_LLM_SAMPLE_PROVENANCE_FIELDS:
            del sample[field]
        assert assert_llm_sample_provenance(sample) is None

    def test_frozen_required_provenance_fields_unchanged(self):
        # D-19 is additive: the pre-plan tuple still has its own 8 fields and
        # `assert_provenance` still guards result rows, not LLM samples.
        assert REQUIRED_PROVENANCE_FIELDS == (
            "promptVersion",
            "provider",
            "model",
            "temperature",
            "negotiatedMode",
            "contextSha256",
            "frozenAtCommit",
            "corpusVersion",
        )

    def test_assert_provenance_reuses_provenance_error_unchanged(self):
        incomplete_row = {
            "promptVersion": "r1",
            "provider": "anthropic",
            "model": "m",
            "temperature": 0.0,
            "contextSha256": "x",
            "frozenAtCommit": "y",
            "corpusVersion": 1,
            # negotiatedMode deliberately missing.
        }
        with pytest.raises(ProvenanceError):
            assert_provenance(incomplete_row)


class TestCredentialRejection:
    def test_endpoint_with_userinfo_rejected(self):
        with pytest.raises(ProvenanceError):
            assert_llm_sample_provenance(
                _full_sample(endpointHost="https://user:pass@api.example.com")
            )

    def test_endpoint_with_query_key_rejected(self):
        with pytest.raises(ProvenanceError):
            assert_llm_sample_provenance(
                _full_sample(endpointHost="https://api.example.com/v1?key=abc123")
            )

    @pytest.mark.parametrize(
        "value",
        [
            "sk-abc123def456",
            "Bearer abc123",
            "api_key=abc123",
            "api-key=abc123",
            "apikey=abc123",
        ],
    )
    def test_api_key_shaped_value_rejected(self, value):
        with pytest.raises(ProvenanceError):
            assert_llm_sample_provenance(_full_sample(promptFilePath=value))

    def test_bare_host_without_key_material_passes(self):
        assert (
            assert_llm_sample_provenance(
                _full_sample(endpointHost="127.0.0.1:11434")
            )
            is None
        )

    def test_provenance_error_is_a_value_error(self):
        # Refusal semantics preserved: a `ValueError` catch still catches it.
        assert issubclass(corpus_module.ProvenanceError, ValueError)