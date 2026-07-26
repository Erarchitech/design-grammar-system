"""Driver tests for the recognition eval harness (Phase 35-13,
35-AI-SPEC.md 5 "Evaluation Strategy").

Extends `test_cg_recognition.py`'s sys.path/no-network boilerplate rather
than duplicating it -- see that file's own docstring for the
`_FakeAdapterForRetry` precedent this harness scales up into cassette-based
record/replay.

Built incrementally across 35-13-PLAN.md's tasks:
- `TestCassette` (Task 1): `recognition_eval.cassette`'s record/replay/miss
  behaviour.
- `TestArms` (Task 2): `recognition_eval.arms`'s A0-A5 registry and artifact
  resolution.
- The conjunctive SC1 gate, the A0 validity check, and the parametrized
  (corpus x arm) driver (Task 3).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

from llm_gateway import GenerateRequest, GenerateResponse  # noqa: E402

from recognition_eval import cassette as cassette_module  # noqa: E402


class _FakeRealAdapter:
    """Stand-in for a real llm_gateway adapter, wrapped by `CassetteAdapter`
    in 'record'/'live' mode tests. Mirrors test_cg_recognition.py's
    `_FakeAdapterForRetry` precedent, retargeted at cassette round-trip
    testing rather than the retry loop."""

    def __init__(self, responses: "list[GenerateResponse]"):
        self._responses = list(responses)
        self.call_count = 0

    def generate(self, req, api_key, options=None):
        self.call_count += 1
        return self._responses.pop(0)


# ── TestCassette (Task 1) ──


class TestCassette:
    _KEY_KWARGS = dict(
        provider="anthropic",
        model="claude-sonnet-5",
        prompt_version="r35.4",
        system="you are a recognizer",
        user_prompt="classify these nodes",
        temperature=0.0,
        negotiated_mode="none",
        max_tokens=2048,
    )

    @pytest.mark.parametrize(
        "field,new_value",
        [
            ("provider", "openai"),
            ("model", "gpt-4o"),
            ("prompt_version", "r35.5"),
            ("system", "a different system prompt"),
            ("user_prompt", "a different user prompt"),
            ("temperature", 0.5),
            ("negotiated_mode", "json_schema_strict"),
            ("max_tokens", 4096),
        ],
    )
    def test_cassette_key_changes_when_any_single_input_flips(self, field, new_value):
        base_key = cassette_module.cassette_key(**self._KEY_KWARGS)
        flipped = dict(self._KEY_KWARGS)
        flipped[field] = new_value
        flipped_key = cassette_module.cassette_key(**flipped)
        assert flipped_key != base_key, f"changing {field!r} did not change the cassette key"

    def test_replay_miss_raises_with_key_and_refresh_command(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        adapter = cassette_module.CassetteAdapter(
            "A0", None, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="replay",
        )
        req = GenerateRequest(prompt="hello", system="sys", model="m", provider="p")

        with pytest.raises(cassette_module.CassetteMissError) as excinfo:
            adapter.generate(req, "key")

        message = str(excinfo.value)
        assert "RECOGNITION_EVAL_MODE=record" in message
        expected_key = cassette_module.cassette_key(
            provider="p", model="m", prompt_version="r35.4", system="sys",
            user_prompt="hello", temperature=None, negotiated_mode="none", max_tokens=None,
        )
        assert expected_key in message

    def test_replay_miss_does_not_call_wrapped_adapter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        fake = _FakeRealAdapter([])
        adapter = cassette_module.CassetteAdapter(
            "A0", fake, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="replay",
        )
        req = GenerateRequest(prompt="hello", system="sys", model="m", provider="p")

        with pytest.raises(cassette_module.CassetteMissError):
            adapter.generate(req, "key")

        assert fake.call_count == 0

    def test_recorded_cassette_round_trips_truncated_finish_reason_usage(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        real_response = GenerateResponse(
            text='{"proposals": []}',
            provider="anthropic",
            model="claude-sonnet-5",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            truncated=True,
            finish_reason="max_tokens",
        )
        fake = _FakeRealAdapter([real_response])
        recorder = cassette_module.CassetteAdapter(
            "A0", fake, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="record",
        )
        req = GenerateRequest(prompt="hello", system="sys", model="claude-sonnet-5", provider="anthropic")

        recorded = recorder.generate(req, "key")
        assert recorded.truncated is True
        assert fake.call_count == 1

        replayer = cassette_module.CassetteAdapter(
            "A0", None, negotiated_mode="none", prompt_version="r35.4",
            ip_class="own", mode="replay",
        )
        replayed = replayer.generate(req, "key")
        assert replayed.truncated is True
        assert replayed.finish_reason == "max_tokens"
        assert replayed.usage == real_response.usage
        assert replayed.text == real_response.text

    def test_promptbody_stored_only_for_ip_class_own(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cassette_module, "_FIXTURES_ROOT", tmp_path)
        response = GenerateResponse(text="{}", provider="p", model="m", usage={})

        own_req = GenerateRequest(prompt="hello-own", system="sys", model="m", provider="p")
        own_adapter = cassette_module.CassetteAdapter(
            "A0", _FakeRealAdapter([response]), negotiated_mode="none",
            prompt_version="r1", ip_class="own", mode="record",
        )
        own_adapter.generate(own_req, "key")
        own_key = cassette_module.cassette_key(
            provider="p", model="m", prompt_version="r1", system="sys",
            user_prompt="hello-own", temperature=None, negotiated_mode="none", max_tokens=None,
        )
        own_payload = json.loads((tmp_path / "A0" / f"{own_key}.json").read_text())
        assert "promptBody" in own_payload

        other_req = GenerateRequest(prompt="hello-other", system="sys", model="m", provider="p")
        other_adapter = cassette_module.CassetteAdapter(
            "A0", _FakeRealAdapter([response]), negotiated_mode="none",
            prompt_version="r1", ip_class="third_party", mode="record",
        )
        other_adapter.generate(other_req, "key")
        other_key = cassette_module.cassette_key(
            provider="p", model="m", prompt_version="r1", system="sys",
            user_prompt="hello-other", temperature=None, negotiated_mode="none", max_tokens=None,
        )
        other_payload = json.loads((tmp_path / "A0" / f"{other_key}.json").read_text())
        assert "promptBody" not in other_payload

    def test_generate_signature_matches_llm_adapter(self):
        import inspect

        sig = inspect.signature(cassette_module.CassetteAdapter.generate)
        assert list(sig.parameters) == ["self", "req", "api_key", "options"]

    def test_unknown_mode_rejected_at_construction(self):
        with pytest.raises(ValueError):
            cassette_module.CassetteAdapter(
                "A0", None, negotiated_mode="none", prompt_version="r1",
                ip_class="own", mode="bogus",
            )
