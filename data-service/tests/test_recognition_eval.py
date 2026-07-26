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

from recognition_eval import arms as arms_module  # noqa: E402
from recognition_eval import cassette as cassette_module  # noqa: E402
from recognition_eval import corpus as corpus_module  # noqa: E402


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


# ── TestArms (Task 2) ──


def _minimal_cg_context() -> dict:
    """A tiny hand-built cgContextJson v1 shape -- one tagged procedure
    member, two untagged nodes -- just enough for `run_arm` to exercise
    Tier-0-bypass + Tier-1 merge without depending on a real corpus fixture."""
    return {
        "nodes": [
            {"instanceId": "n1", "componentGuid": "g1", "name": "Param", "nickname": "ParSplitAt"},
            {"instanceId": "n3", "componentGuid": "g3", "name": "Panel", "nickname": "loose panel"},
            {"instanceId": "n4", "componentGuid": "g4", "name": "Line SDL", "nickname": "TopChord"},
        ],
        "algorithms": [
            {
                "index": 1,
                "name": "1_ALGORITHM",
                "procedures": [
                    {
                        "id": "cg:1:proc:11",
                        "index": 11,
                        "name": "2D Truss Configuration",
                        "source": "tagged",
                        "memberIds": ["n1"],
                        "patterns": [],
                        "parameters": [],
                        "interfaces": [],
                    }
                ],
            }
        ],
        "untagged": {
            "nodeIds": ["n3", "n4"],
            "groups": [
                {"nickname": "loose panel group", "memberIds": ["n3"]},
                {"nickname": "wired thing group", "memberIds": ["n4"]},
            ],
        },
        "wires": [
            {"fromNode": "n1", "fromParam": "p_out", "toNode": "n4", "toParam": "p_in"},
        ],
    }


class TestArms:
    def test_arms_registry_contains_exact_ids(self):
        assert set(arms_module.ARMS.keys()) == {"A0", "A0f", "A1", "A2", "A3", "A4", "A5"}

    def test_a0_is_the_negative_control_configuration(self):
        a0 = arms_module.ARMS["A0"]
        assert a0.few_shot_source == "as_shipped"
        assert a0.system_prompt is False
        assert a0.tier0 is False
        assert a0.model == "deepseek-chat"

    def test_a3_is_the_shipping_configuration(self):
        a3 = arms_module.ARMS["A3"]
        assert a3.few_shot_source == "counterexample"
        assert a3.system_prompt is True
        assert a3.tier0 is True

    def test_resolve_arm_artifacts_a0_uses_the_as_shipped_grammar_citing_fixture(self):
        artifacts = arms_module.resolve_arm_artifacts(arms_module.ARMS["A0"])
        serialized = json.dumps(artifacts.few_shot_examples).lower()
        assert "grammar" in serialized
        assert artifacts.few_shot_sha is not None

    def test_resolve_arm_artifacts_a3_uses_the_counterexample_fixture_no_grammar(self):
        artifacts = arms_module.resolve_arm_artifacts(arms_module.ARMS["A3"])
        serialized = json.dumps(artifacts.few_shot_examples).lower()
        assert "grammar" not in serialized

    def test_resolve_arm_artifacts_raises_when_sha_cannot_be_resolved(self, monkeypatch):
        def _boom():
            raise RuntimeError("simulated: no matching commit in history")

        monkeypatch.setattr(arms_module, "_resolve_pre_35_08_fewshot_sha", _boom)
        with pytest.raises(RuntimeError):
            arms_module.resolve_arm_artifacts(arms_module.ARMS["A0"])

    def test_run_arm_returns_provenance_corpus_assert_provenance_accepts(self):
        corpus = corpus_module.Corpus(
            name="test-fixture",
            context=_minimal_cg_context(),
            blocks=[],
            abstain_expected=[],
            tier0_evidence=True,
            ip_class="own",
            corpus_version=1,
            frozen_at_commit="deadbeef",
            context_sha256="dummy",
        )
        fake_response = GenerateResponse(
            text=json.dumps(
                {
                    "proposals": [],
                    "unrecognized": [
                        {"memberIds": ["n3", "n4"], "reason": "test stub -- not evaluated for real classification"}
                    ],
                }
            ),
            provider="deepseek",
            model="deepseek-chat",
            usage={},
        )
        adapter = cassette_module.CassetteAdapter(
            "A0",
            _FakeRealAdapter([fake_response]),
            negotiated_mode="none",
            prompt_version="test",
            ip_class=corpus.ip_class,
            mode="live",
        )

        outcome = arms_module.run_arm(arms_module.ARMS["A0"], corpus, adapter)

        corpus_module.assert_provenance(outcome["provenance"])
        assert outcome["result"]["valid"] is True

    def test_arms_module_never_forks_recognize_structure(self):
        source = Path(arms_module.__file__).read_text(encoding="utf-8")
        assert source.count("def recognize_structure") == 0
