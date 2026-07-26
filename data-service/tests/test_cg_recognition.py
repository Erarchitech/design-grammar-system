"""Tests for the recognition backend (Phase 35: RCGN-01/RCGN-04).

Follows the existing test pattern from test_dg_context.py: sys.path.insert
boilerplate header, class-per-concern shape (TestValidator/TestExtractJson/
TestRetryLoop/TestPrompt), hand-built cg_context fixture dicts, and a
_FakeAdapterForRetry mirroring test_dg_context.py's own fake-adapter precedent
so no live LLM call is ever made.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import cg_recognition  # noqa: E402
import cg_topology  # noqa: E402
from app import app  # noqa: E402
from llm_gateway import GenerateResponse, StructuredOutputCapability  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _no_network_structured_output_negotiation(monkeypatch):
    """`recognize_structure` calls `negotiate_structured_output()`, which for
    the Ollama fallback provider makes a real network probe. Tests must never
    depend on that -- pin the negotiated mode to "none" everywhere unless a
    test explicitly overrides it."""
    monkeypatch.setattr(
        cg_recognition,
        "negotiate_structured_output",
        lambda provider, model, base_url=None: StructuredOutputCapability(mode="none"),
    )


# ── Shared cg_context fixture (small hand-built cgContextJson v1 shape) ──
#
# n1: tagged (procedure member), n2: tagged (pattern member), n3: untagged
# (unrelated), n4: untagged (wired to n1, the procedure's tagged member) --
# lets tests exercise procedure_index-scoped filtering via wire adjacency.


def _cg_context() -> dict:
    return {
        "nodes": [
            {"instanceId": "n1", "componentGuid": "g1", "name": "Param", "nickname": "ParSplitAt", "position": [0, 0]},
            {"instanceId": "n2", "componentGuid": "g2", "name": "Divide Curve", "nickname": "Divide", "position": [10, 0]},
            {"instanceId": "n3", "componentGuid": "g3", "name": "Panel", "nickname": "loose panel", "position": [500, 500]},
            {"instanceId": "n4", "componentGuid": "g4", "name": "Line SDL", "nickname": "TopChord", "position": [20, 0]},
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
                        "patterns": [
                            {
                                "id": "cg:1:pat:11_1",
                                "label": "11_Pat_1",
                                "name": None,
                                "hostPatternId": None,
                                "memberIds": ["n2"],
                                "source": "tagged",
                            }
                        ],
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


# ── validate_proposed_structure() -- mirrors validate_cypher()'s violation-list shape ──


class TestValidator:
    def _proposal(self, **overrides) -> dict:
        base = {
            "kind": "Interface",
            "suggestedName": "11_IntF_Test",
            "procedureIndex": 11,
            "memberIds": ["n3"],
            "confidence": 0.9,
            "rationale": "test rationale",
        }
        base.update(overrides)
        return base

    def test_bad_shape_when_proposals_not_a_list(self):
        result = cg_recognition.validate_proposed_structure({"proposals": "nope"}, _cg_context())
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "bad_shape" in codes

    def test_missing_field_is_caught_for_each_required_field(self):
        for field in ("kind", "suggestedName", "memberIds", "confidence", "rationale"):
            proposal = self._proposal()
            del proposal[field]
            result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
            assert result["valid"] is False
            codes = {v["code"] for v in result["violations"]}
            assert "missing_field" in codes, f"expected missing_field violation when '{field}' absent"

    def test_unknown_member_id_is_caught(self):
        proposal = self._proposal(memberIds=["n999"])
        result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "unknown_member_id" in codes

    def test_tagged_overlap_is_caught(self):
        """n2 is already owned by a tagged Pattern -- referencing it is a hard reject."""
        proposal = self._proposal(memberIds=["n2"])
        result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "tagged_overlap" in codes

    def test_too_many_proposals_is_caught(self):
        proposals = [self._proposal() for _ in range(cg_recognition.MAX_PROPOSALS + 1)]
        result = cg_recognition.validate_proposed_structure({"proposals": proposals}, _cg_context())
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "too_many_proposals" in codes

    def test_too_many_members_per_proposal_is_caught(self):
        proposal = self._proposal(memberIds=[f"m{i}" for i in range(cg_recognition.MAX_MEMBERS_PER_PROPOSAL + 1)])
        result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "too_many_members" in codes

    def test_invalid_kind_is_caught(self):
        """WR-02: a present-but-bogus 'kind' previously sailed through
        validation and only failed (or half-rendered) on the Grasshopper
        side -- it must be a validator reject so the retry loop corrects it."""
        for bad_kind in ("Widget", "7", 7, None):
            proposal = self._proposal(kind=bad_kind)
            result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
            assert result["valid"] is False, f"expected reject for kind={bad_kind!r}"
            codes = {v["code"] for v in result["violations"]}
            assert "invalid_kind" in codes, f"expected invalid_kind for kind={bad_kind!r}"

    def test_both_short_and_catalog_kind_names_are_accepted(self):
        """WR-02: the prompt teaches catalog kinds ('Interface'); the C# side
        also accepts EntityTagKind short names ('IntF') -- both must validate."""
        for good_kind in ("IntF", "Interface", "Proc", "Procedure", "Pattern", "VariableParam"):
            proposal = self._proposal(kind=good_kind)
            result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
            assert result == {"valid": True, "violations": []}, f"kind={good_kind!r}"

    def test_duplicate_member_across_proposals_is_caught(self):
        """WR-03: two proposals claiming the same node must be a hard reject --
        accepting both would create the double-ownership state tagged_overlap
        exists to prevent, one confirmation step later."""
        first = self._proposal(memberIds=["n3", "n4"])
        second = self._proposal(suggestedName="11_IntF_Other", memberIds=["n4"])
        result = cg_recognition.validate_proposed_structure({"proposals": [first, second]}, _cg_context())
        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "duplicate_member" in codes

    def test_disjoint_proposals_are_valid(self):
        first = self._proposal(memberIds=["n3"])
        second = self._proposal(suggestedName="11_IntF_Other", memberIds=["n4"])
        result = cg_recognition.validate_proposed_structure({"proposals": [first, second]}, _cg_context())
        assert result == {"valid": True, "violations": []}

    def test_unrecognized_with_hallucinated_id_is_caught(self):
        """WR-06: 'never invented' is a validator guarantee -- ids in the
        unrecognized block must exist in the submitted context."""
        parsed = {
            "proposals": [self._proposal()],
            "unrecognized": [{"memberIds": ["n999"], "reason": "unclear cluster"}],
        }
        result = cg_recognition.validate_proposed_structure(parsed, _cg_context())
        assert result["valid"] is False
        violations = [v for v in result["violations"] if v["code"] == "unknown_member_id"]
        assert violations
        assert violations[0]["path"] == "unrecognized[0].memberIds"

    def test_unrecognized_shape_and_bounds_are_validated(self):
        """WR-06: unrecognized must be a list of {memberIds, reason} objects,
        bounded like proposals."""
        ctx = _cg_context()
        base = {"proposals": [self._proposal()]}

        result = cg_recognition.validate_proposed_structure({**base, "unrecognized": "nope"}, ctx)
        assert {"bad_shape"} <= {v["code"] for v in result["violations"]}

        result = cg_recognition.validate_proposed_structure({**base, "unrecognized": ["not a dict"]}, ctx)
        assert {"bad_shape"} <= {v["code"] for v in result["violations"]}

        result = cg_recognition.validate_proposed_structure({**base, "unrecognized": [{"memberIds": ["n4"]}]}, ctx)
        assert {"missing_field"} <= {v["code"] for v in result["violations"]}

        too_many = [{"memberIds": [], "reason": "x"}] * (cg_recognition.MAX_PROPOSALS + 1)
        result = cg_recognition.validate_proposed_structure({**base, "unrecognized": too_many}, ctx)
        assert {"too_many_unrecognized"} <= {v["code"] for v in result["violations"]}

    def test_valid_unrecognized_block_passes(self):
        parsed = {
            "proposals": [self._proposal()],
            "unrecognized": [{"memberIds": ["n4"], "reason": "ambiguous wiring"}],
        }
        result = cg_recognition.validate_proposed_structure(parsed, _cg_context())
        assert result == {"valid": True, "violations": []}

    def test_well_formed_untagged_proposal_is_valid(self):
        proposal = self._proposal(memberIds=["n3", "n4"])
        result = cg_recognition.validate_proposed_structure({"proposals": [proposal]}, _cg_context())
        assert result == {"valid": True, "violations": []}

    def test_module_constants_exist(self):
        assert cg_recognition.MAX_PROPOSALS == 200
        assert cg_recognition.MAX_MEMBERS_PER_PROPOSAL == 1000


# ── _extract_json() -- new territory per Pitfall 1 (no existing precedent) ──


class TestExtractJson:
    def test_bare_json_parses(self):
        text = json.dumps({"proposals": [], "unrecognized": []})
        parsed, error = cg_recognition._extract_json(text)
        assert error is None
        assert parsed == {"proposals": [], "unrecognized": []}

    def test_fenced_json_parses(self):
        text = "```json\n" + json.dumps({"proposals": [], "unrecognized": []}) + "\n```"
        parsed, error = cg_recognition._extract_json(text)
        assert error is None
        assert parsed == {"proposals": [], "unrecognized": []}

    def test_plain_fence_without_json_tag_parses(self):
        text = "```\n" + json.dumps({"proposals": []}) + "\n```"
        parsed, error = cg_recognition._extract_json(text)
        assert error is None
        assert parsed == {"proposals": []}

    def test_prose_wrapped_json_parses(self):
        text = "Here is the result:\n" + json.dumps({"proposals": []}) + "\nHope that helps!"
        parsed, error = cg_recognition._extract_json(text)
        assert error is None
        assert parsed == {"proposals": []}

    def test_malformed_json_returns_none_and_message(self):
        parsed, error = cg_recognition._extract_json("{not valid json")
        assert parsed is None
        assert error
        assert isinstance(error, str)

    def test_non_object_json_returns_none_and_message(self):
        parsed, error = cg_recognition._extract_json("[1, 2, 3]")
        assert parsed is None
        assert error


# ── recognize_structure() -- two-tier orchestrator (Phase 35-12: mirrors
# CTXA-04's bounded Tier-1 retry loop) ──
#
# NOTE on _cg_context(): under the default (procedure_index=None) scope, Tier
# 0 DECIDES n4 on its own (R3: clean sink, group_member_count <= 1, adjacent
# to exactly one tagged procedure) -- only n3 (an isolated Panel) reaches
# Tier 1's residual. Every fake LLM response below therefore targets n3, not
# n4; a response claiming n4 is used deliberately in the duplicate_member
# test below, since n4 is EXACTLY the id Tier 0 already decided.

_VALID_PROPOSAL_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "11_IntF_LoosePanel",
                "procedureIndex": 11,
                "memberIds": ["n3"],
                "confidence": 0.88,
                "rationale": "Isolated panel adjacent to procedure 11 in this scope.",
            }
        ],
        "unrecognized": [],
    }
)

# Invalid: memberIds references an id absent from the submitted context.
_INVALID_PROPOSAL_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "Bogus",
                "procedureIndex": 11,
                "memberIds": ["n999"],
                "confidence": 0.5,
                "rationale": "hallucinated id",
            }
        ],
        "unrecognized": [],
    }
)

# Schema-invalid: 'confidence' (a required field) is missing entirely.
_SCHEMA_INVALID_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "11_IntF_Test",
                "procedureIndex": 11,
                "memberIds": ["n3"],
                "rationale": "missing the confidence field",
            }
        ],
        "unrecognized": [],
    }
)

# Claims n4 -- an id Tier 0 already decided under the default scope.
_DUPLICATE_WITH_TIER0_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "11_IntF_Dup",
                "procedureIndex": 11,
                "memberIds": ["n4"],
                "confidence": 0.7,
                "rationale": "duplicate of a tier0 decision",
            }
        ],
        "unrecognized": [{"memberIds": ["n3"], "reason": "unclear cluster"}],
    }
)

_MALFORMED_JSON_TEXT = "this is not json at all"

_TRUNCATED_RESPONSE = GenerateResponse(
    text='{"proposals": [{"kind": "Interf',
    provider="fake",
    model="fake-model",
    usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    truncated=True,
    finish_reason="length",
)

_REFUSAL_RESPONSE = GenerateResponse(
    text="",
    provider="fake",
    model="fake-model",
    usage={},
    truncated=False,
    finish_reason="refusal",
)


class _FakeAdapterForRetry:
    """Stand-in for an llm_gateway LLMAdapter -- returns queued responses in
    order and records every prompt/system it was called with (mirrors
    test_dg_context.py's own _FakeAdapterForRetry precedent, retargeted at
    cg_recognition). Queue entries may be plain text (wrapped into a default
    GenerateResponse) or a pre-built GenerateResponse (for truncated/refusal
    scenarios)."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.prompts_seen: list[str] = []
        self.systems_seen: list[str | None] = []
        self.call_count = 0

    def generate(self, req, api_key, options=None):
        self.call_count += 1
        self.prompts_seen.append(req.prompt)
        self.systems_seen.append(req.system)
        item = self._responses.pop(0)
        if isinstance(item, GenerateResponse):
            return item
        return GenerateResponse(text=item, provider="fake", model="fake-model", usage={})


class TestTierZero:
    def test_empty_procedure_scope_blocks_without_calling_the_adapter(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        # Procedure 999 does not exist in the context -> zero tagged members.
        result = cg_recognition.recognize_structure(_cg_context(), procedure_index=999)

        assert result["valid"] is False
        assert result["attempts"] == 0
        codes = {v["code"] for v in result["violations"]}
        assert "empty_procedure_scope" in codes
        assert fake_adapter.call_count == 0

    def test_tier0_decides_everything_skips_the_llm_entirely(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        # Scope this context to ONLY n4 -- R3 (clean sink, group_member_count
        # <= 1, adjacent to exactly one tagged procedure) decides it, and
        # nothing is left over for the LLM.
        ctx = _cg_context()
        ctx["untagged"] = {
            "nodeIds": ["n4"],
            "groups": [{"nickname": "wired thing group", "memberIds": ["n4"]}],
        }

        result = cg_recognition.recognize_structure(ctx)

        assert result["valid"] is True
        assert result["attempts"] == 0
        assert result["tier"] == "0"
        assert fake_adapter.call_count == 0
        assert result["proposal"]["proposals"]


class TestRetryLoop:
    def test_first_attempt_valid_returns_attempts_1_no_retry(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert result["attempts"] == 1
        assert result["tier"] == "0+1"
        # The LLM's Tier-1 proposal is preserved verbatim (merged after Tier
        # 0's own decided rows); recognize_structure adds the run's
        # provider/model on top (F6 -- see TestRecognitionProvenance).
        expected = json.loads(_VALID_PROPOSAL_TEXT)
        assert expected["proposals"][0] in result["proposal"]["proposals"]
        assert fake_adapter.call_count == 1
        # system= is set on every request (the point of the prompt split).
        assert fake_adapter.systems_seen[0]
        assert "NOT A FILTER" in fake_adapter.systems_seen[0]

    def test_malformed_json_then_valid_retries_and_succeeds_at_attempt_2(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_MALFORMED_JSON_TEXT, _VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        original_prompt = _prompt(_cg_context())
        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert result["attempts"] == 2
        assert fake_adapter.call_count == 2
        # First prompt is the ORIGINAL, unmodified prompt (not accumulated).
        assert fake_adapter.prompts_seen[0] == original_prompt
        # Second prompt carries corrective feedback appended to the ORIGINAL
        # prompt -- not the first prompt plus two feedback blocks.
        assert fake_adapter.prompts_seen[1].startswith(original_prompt)
        assert "CORRECTIVE FEEDBACK" in fake_adapter.prompts_seen[1]
        assert "bad_json" in fake_adapter.prompts_seen[1]

    def test_all_three_attempts_fail_returns_final_violations_bounded_at_3(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_INVALID_PROPOSAL_TEXT, _INVALID_PROPOSAL_TEXT, _INVALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is False
        assert result["attempts"] == 3
        assert len(result["violations"]) > 0
        assert fake_adapter.call_count == 3

    def test_schema_invalid_proposal_retries_with_dotted_path_feedback(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_SCHEMA_INVALID_TEXT, _VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert result["attempts"] == 2
        assert "schema_violation" in fake_adapter.prompts_seen[1]

    def test_all_attempts_schema_invalid_reports_dotted_path(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_SCHEMA_INVALID_TEXT] * 3)
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is False
        violations = [v for v in result["violations"] if v["code"] == "schema_violation"]
        assert violations
        assert "proposals.0.confidence" in violations[0]["path"]

    def test_output_truncated_blocks_with_no_retry(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_TRUNCATED_RESPONSE])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is False
        assert result["attempts"] == 1
        codes = {v["code"] for v in result["violations"]}
        assert "output_truncated" in codes
        assert fake_adapter.call_count == 1

    def test_provider_refusal_is_distinct_from_bad_json_with_no_retry(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_REFUSAL_RESPONSE])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is False
        assert result["attempts"] == 1
        codes = {v["code"] for v in result["violations"]}
        assert "provider_refusal" in codes
        assert fake_adapter.call_count == 1

    def test_tier1_claiming_a_tier0_decided_node_yields_duplicate_member(self, monkeypatch):
        """A Tier-1 proposal claiming n4 (Tier 0 already decided it) must
        SURVIVE the merge and be caught post-merge -- never silently dropped
        (G13/RCGN-04)."""
        fake_adapter = _FakeAdapterForRetry([_DUPLICATE_WITH_TIER0_TEXT] * 3)
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is False
        codes = {v["code"] for v in result["violations"]}
        assert "duplicate_member" in codes

    def test_retry_loop_never_calls_llm_generate_http_endpoint(self, monkeypatch):
        """The retry loop must call the adapter in-process -- never re-POST to
        /llm/generate (RESEARCH.md Anti-pattern guard)."""
        import httpx

        def fail_post(*args, **kwargs):
            raise AssertionError("recognize_structure must not re-POST to /llm/generate")

        monkeypatch.setattr(httpx, "post", fail_post)
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True


# ── LLM provenance surfaced to the caller (Phase 36 UAT F6) ──


class TestRecognitionProvenance:
    """recognize_structure() resolves the run's provider/model and must SURFACE
    them. Before F6 it resolved and dropped them, so the accept path had nothing
    to stamp onto the canvas and computgraph_publish.py -- which has always read
    provider/model/confidence -- could only ever write nulls.
    """

    def _fake_settings(self, monkeypatch, provider: str, model: str) -> None:
        monkeypatch.setattr(
            cg_recognition,
            "resolve_active_provider",
            lambda settings, master_secret: (provider, model, "sk-test"),
        )

    def test_success_returns_provider_and_model_at_top_level(self, monkeypatch):
        self._fake_settings(monkeypatch, "anthropic", "claude-opus-4-6")
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert result["provider"] == "anthropic"
        assert result["model"] == "claude-opus-4-6"

    def test_success_injects_provider_and_model_into_the_proposal(self, monkeypatch):
        """The proposal object is what a caller hands to gh_preview_structure, and
        the listener reads provider/model off ITS top level -- so the identity has
        to travel inside the proposal, not only beside it."""
        self._fake_settings(monkeypatch, "anthropic", "claude-opus-4-6")
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        proposal = cg_recognition.recognize_structure(_cg_context())["proposal"]

        assert proposal["provider"] == "anthropic"
        assert proposal["model"] == "claude-opus-4-6"
        # Injection must not disturb the validated payload -- the Tier-1
        # proposal survives the merge verbatim, alongside Tier 0's own
        # decided rows.
        assert json.loads(_VALID_PROPOSAL_TEXT)["proposals"][0] in proposal["proposals"]

    def test_failure_path_also_reports_which_model_failed(self, monkeypatch):
        self._fake_settings(monkeypatch, "openai", "gpt-5")
        fake_adapter = _FakeAdapterForRetry([_INVALID_PROPOSAL_TEXT] * 3)
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is False
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-5"

    def test_ollama_fallback_reports_provider_with_null_model(self, monkeypatch):
        """No configured cloud key -> ("ollama", None, None). Provenance is then
        partial, not absent, and the marker records exactly that."""
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)
        monkeypatch.setattr(
            cg_recognition,
            "resolve_active_provider",
            lambda settings, master_secret: ("ollama", None, None),
        )

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["provider"] == "ollama"
        assert result["model"] is None


# ── Guardrails G6/G7/G10/G11 + per-attempt logging (Phase 35-12 Task 3) ──


def _isolated_candidates_context(count: int, prefix: str) -> dict:
    """A context with `count` fully isolated Panel nodes (no wires, no
    groups) -- every one abstains at Tier 0 (none of R1-R4 match a node with
    in_degree==0 and out_degree==0), so the whole set reaches Tier 1's
    residual untouched."""
    node_ids = [f"{prefix}{i}" for i in range(count)]
    return {
        "nodes": [
            {"instanceId": nid, "componentGuid": f"g-{nid}", "name": "Panel", "nickname": nid}
            for nid in node_ids
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
                        "memberIds": [],
                        "patterns": [],
                        "parameters": [],
                        "interfaces": [],
                    }
                ],
            }
        ],
        "untagged": {"nodeIds": node_ids, "groups": []},
        "wires": [],
    }


_GRAMMAR_CITING_RATIONALE_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "11_IntF_Test",
                "procedureIndex": 11,
                "memberIds": ["n3"],
                "confidence": 0.6,
                "rationale": "does not match the Interface naming grammar",
            }
        ],
        "unrecognized": [],
    }
)

_ZERO_PROPOSALS_SIX_CANDIDATES_TEXT = json.dumps(
    {
        "proposals": [],
        "unrecognized": [
            {"memberIds": [f"m{i}" for i in range(6)], "reason": "isolated: no wires in or out"}
        ],
    }
)

_EMPTY_RESPONSE_TEXT = json.dumps({"proposals": [], "unrecognized": []})

_LOW_CONFIDENCE_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "11_IntF_Test",
                "procedureIndex": 11,
                "memberIds": ["n3"],
                "confidence": 0.4,
                "rationale": "weak signal from wiring alone",
            }
        ],
        "unrecognized": [],
    }
)

_FIVE_FLAT_CONFIDENCE_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": f"11_IntF_K{i}",
                "procedureIndex": 11,
                "memberIds": [f"k{i}"],
                "confidence": 0.9,
                "rationale": f"isolated component k{i}, no wires in or out",
            }
            for i in range(5)
        ],
        "unrecognized": [],
    }
)


class TestGuardrails:
    def test_grammar_citing_rationale_triggers_g7_retry_on_first_attempt(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_GRAMMAR_CITING_RATIONALE_TEXT, _VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert result["attempts"] == 2
        assert fake_adapter.call_count == 2
        assert "OUTPUT TARGET" in fake_adapter.prompts_seen[1]
        assert "grammar_as_filter" in fake_adapter.prompts_seen[1]

    def test_zero_proposals_for_many_candidates_triggers_g7_structural_signature(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry(
            [_ZERO_PROPOSALS_SIX_CANDIDATES_TEXT, _ZERO_PROPOSALS_SIX_CANDIDATES_TEXT]
        )
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)
        monkeypatch.setattr(
            cg_recognition,
            "resolve_active_provider",
            lambda settings, master_secret: ("openai", "gpt-5", "sk-test"),
        )

        result = cg_recognition.recognize_structure(_isolated_candidates_context(6, "m"))

        assert result["valid"] is False
        # Exactly one targeted retry, then block -- never a third call.
        assert fake_adapter.call_count == 2
        violations = [v for v in result["violations"] if v["code"] == "grammar_as_filter"]
        assert violations
        assert cg_recognition.PROMPT_VERSION in violations[0]["message"]
        assert "openai" in violations[0]["message"]

    def test_unaddressed_candidate_retries_then_autofills_on_final_attempt(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_EMPTY_RESPONSE_TEXT, _EMPTY_RESPONSE_TEXT, _EMPTY_RESPONSE_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert fake_adapter.call_count == 3
        assert "unaddressed_candidate" in fake_adapter.prompts_seen[1]
        assert result["valid"] is True
        assert "unaddressed_candidates_autofilled" in result["flags"]
        unrecognized_entries = result["proposal"]["unrecognized"]
        matching = [u for u in unrecognized_entries if "n3" in u["memberIds"]]
        assert matching
        assert matching[0]["reason"] == "not addressed by the model"

    def test_low_confidence_proposal_is_demoted_not_blocked(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_LOW_CONFIDENCE_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        proposal_member_sets = [set(p["memberIds"]) for p in result["proposal"]["proposals"]]
        assert {"n3"} not in proposal_member_sets
        unrecognized_ids = {m for u in result["proposal"]["unrecognized"] for m in u["memberIds"]}
        assert "n3" in unrecognized_ids

    def test_confidence_floor_constant_is_a_labelled_guess(self):
        assert cg_recognition.CONFIDENCE_FLOOR == 0.5
        source = inspect.getsource(cg_recognition)
        floor_region = source[source.index("CONFIDENCE_FLOOR = 0.5") : source.index("CONFIDENCE_FLOOR = 0.5") + 400]
        assert "guess" in floor_region.lower()

    def test_flat_confidence_across_five_proposals_flags_but_does_not_block(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_FIVE_FLAT_CONFIDENCE_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_isolated_candidates_context(5, "k"))

        assert result["valid"] is True
        assert "confidence_uninformative" in result["flags"]

    def test_attempt_log_record_contains_metadata_and_never_leaks_prompt_or_key(self, monkeypatch, caplog):
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)
        monkeypatch.setattr(
            cg_recognition,
            "resolve_active_provider",
            lambda settings, master_secret: ("anthropic", "claude-x", "sk-super-secret-key"),
        )

        with caplog.at_level(logging.INFO, logger="cg_recognition"):
            result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert "negotiated_mode" in caplog.text
        assert "prompt_version" in caplog.text
        assert "usage" in caplog.text
        # Never leak the prompt body or the API key.
        prompt_sent = fake_adapter.prompts_seen[0]
        assert prompt_sent not in caplog.text
        assert "sk-super-secret-key" not in caplog.text


# ── POST /computgraph/recognize route (Phase 35-12 Task 4) ──


class TestRecognizeRoute:
    def test_members_less_procedure_returns_actionable_422(self, monkeypatch):
        monkeypatch.setattr(
            cg_recognition, "get_adapter", lambda provider, base_url=None: _FakeAdapterForRetry([])
        )

        response = client.post(
            "/computgraph/recognize",
            json={"cg_context": _cg_context(), "procedure_index": 999},
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "999" in detail["error"]
        assert detail["hint"]
        assert detail["code"] == "RECOGNIZE_EMPTY_PROCEDURE_SCOPE"

    def test_tier0_only_recognition_returns_200_without_calling_the_adapter(self, monkeypatch):
        call_tracker = {"called": False}

        def _tracking_get_adapter(provider, base_url=None):
            call_tracker["called"] = True
            return _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])

        monkeypatch.setattr(cg_recognition, "get_adapter", _tracking_get_adapter)

        ctx = _cg_context()
        ctx["untagged"] = {
            "nodeIds": ["n4"],
            "groups": [{"nickname": "wired thing group", "memberIds": ["n4"]}],
        }

        response = client.post("/computgraph/recognize", json={"cg_context": ctx})

        assert response.status_code == 200
        body = response.json()
        assert body["tier"] == "0"
        assert call_tracker["called"] is False

    def test_output_truncated_returns_200_with_valid_false_not_502(self, monkeypatch):
        monkeypatch.setattr(
            cg_recognition,
            "get_adapter",
            lambda provider, base_url=None: _FakeAdapterForRetry([_TRUNCATED_RESPONSE]),
        )

        response = client.post("/computgraph/recognize", json={"cg_context": _cg_context()})

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        codes = {v["code"] for v in body["violations"]}
        assert "output_truncated" in codes

    def test_grammar_as_filter_returns_200_with_valid_false_not_502(self, monkeypatch):
        monkeypatch.setattr(
            cg_recognition,
            "get_adapter",
            lambda provider, base_url=None: _FakeAdapterForRetry(
                [_ZERO_PROPOSALS_SIX_CANDIDATES_TEXT, _ZERO_PROPOSALS_SIX_CANDIDATES_TEXT]
            ),
        )

        response = client.post(
            "/computgraph/recognize",
            json={"cg_context": _isolated_candidates_context(6, "m")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        codes = {v["code"] for v in body["violations"]}
        assert "grammar_as_filter" in codes


# ── _build_recognition_prompt() -- deterministic prompt assembly ──


def _prompt_inputs(cg_context: dict, procedure_index: "int | None" = None):
    """Build the (scope, features, tier0) triple `_build_recognition_prompt`
    now takes, the same way `recognize_structure` will -- via the real
    `cg_topology` Tier-0 pipeline, not a hand-rolled stand-in."""
    scope = cg_topology.scope_untagged(cg_context, procedure_index)
    features = cg_topology.extract_features(cg_context, scope.node_ids)
    tier0 = cg_topology.classify(features)
    return scope, features, tier0


def _prompt(cg_context: dict, procedure_index: "int | None" = None, negotiated_mode: str = "none") -> str:
    scope, features, tier0 = _prompt_inputs(cg_context, procedure_index)
    return cg_recognition._build_recognition_prompt(cg_context, scope, features, tier0, negotiated_mode)


class TestSystemPrompt:
    def test_prompt_version_matches_front_matter(self):
        assert cg_recognition.PROMPT_VERSION == "r35.4"

    def test_build_recognition_system_prompt_contains_not_a_filter(self):
        prompt = cg_recognition.build_recognition_system_prompt()
        assert "NOT A FILTER" in prompt

    def test_build_recognition_system_prompt_degrades_gracefully_when_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cg_recognition, "SYSTEM_PROMPT_FILE", tmp_path / "missing.md")
        monkeypatch.setattr(cg_recognition, "_system_prompt_cache", None)
        monkeypatch.setattr(cg_recognition, "_prompt_version_cache", None)
        result = cg_recognition.build_recognition_system_prompt()
        assert result == ""


class TestPrompt:
    _REQUIRED_MARKERS = (
        cg_recognition._CONCEPT_CATALOG_MARKER,
        cg_recognition._FEWSHOT_MARKER,
        cg_recognition._TAGGED_ANCHOR_MARKER,
        cg_recognition._UNTAGGED_MARKER,
        cg_recognition._OUTPUT_INSTRUCTION_MARKER,
    )

    def test_prompt_contains_every_required_section_marker(self):
        prompt = _prompt(_cg_context())
        for marker in self._REQUIRED_MARKERS:
            assert marker in prompt

    def test_prompt_contains_annotation_convention_grammar(self):
        prompt = _prompt(_cg_context())
        assert "IntF" in prompt or "annotation_convention" in prompt

    def test_prompt_contains_json_only_output_instruction(self):
        prompt = _prompt(_cg_context())
        assert "JSON" in prompt
        assert "no markdown fences" in prompt.lower() or "markdown" in prompt.lower()

    def test_candidate_line_carries_features_not_position(self):
        """n3 (an isolated Panel with no wires) matches none of Tier 0's
        R1-R4 rules, so it abstains into the residual, where a derived
        feature line must be rendered for it -- never a raw `position`."""
        prompt = _prompt(_cg_context())
        assert "widget=" in prompt
        assert "in=" in prompt
        assert "out=" in prompt
        assert "adj_proc=" in prompt
        assert "position=" not in prompt

    def test_tier0_decisions_block_present_when_tier0_decides_something(self):
        # n1 in _cg_context() is a bare 'Param' node with in=1/out=1 wired
        # into n4 -- wait, n1 is TAGGED (procedure member), so it never
        # reaches Tier 0 classification. Build a context with an untagged
        # bare-Param node instead, wired 1-in/1-out to a single tagged
        # procedure, to exercise R4 and populate tier0.decided.
        ctx = _cg_context()
        ctx["nodes"].append(
            {"instanceId": "n5", "componentGuid": "g5", "name": "Param", "nickname": "relay"}
        )
        ctx["untagged"]["nodeIds"].append("n5")
        ctx["wires"].append({"fromNode": "n1", "fromParam": "p_out", "toNode": "n5", "toParam": "p_in"})
        ctx["wires"].append({"fromNode": "n5", "fromParam": "p_out", "toNode": "n2", "toParam": "p_in"})

        prompt = _prompt(ctx)
        assert cg_recognition._TIER0_DECISIONS_MARKER in prompt
        assert "n5 -> IntF" in prompt

    def test_procedure_index_filters_residual_scope_to_wired_nodes(self):
        """n4 is wired to the tagged procedure-11 member n1; n3 is unrelated."""
        unfiltered = _prompt(_cg_context())
        assert "n3" in unfiltered
        assert "n4" in unfiltered

        filtered = _prompt(_cg_context(), 11)
        assert "n4" in filtered
        assert "n3" not in filtered

    def test_procedure_index_anchor_block_summarizes_other_procedures(self):
        """With procedure_index=11 set, the anchor block shows full memberIds
        for procedure 11 and a member COUNT (not the full list) for procedure
        12."""
        ctx = _cg_context()
        ctx["algorithms"][0]["procedures"].append(
            {
                "id": "cg:1:proc:12",
                "index": 12,
                "name": "2D Footer Configuration",
                "source": "tagged",
                "memberIds": ["n6", "n7"],
                "patterns": [],
                "parameters": [],
                "interfaces": [],
            }
        )
        prompt = _prompt(ctx, 11)
        assert "members: ['n1']" in prompt
        assert "member count: 2" in prompt
        assert "'n6', 'n7'" not in prompt

    def test_prompt_is_deterministic_across_identical_calls(self):
        ctx = _cg_context()
        first = _prompt(ctx)
        second = _prompt(ctx)
        assert first == second

    def test_json_object_mode_includes_lowercase_json_literal(self):
        prompt = _prompt(_cg_context(), negotiated_mode="json_object")
        assert "json" in prompt

    def test_prompt_byte_size_is_measured_and_under_locked_budget(self):
        """A4 resolution: measure the assembled prompt size and lock it as an
        assertion so future catalog growth is a deliberate, visible change."""
        prompt = _prompt(_cg_context())
        size = len(prompt.encode("utf-8"))
        assert size > 0
        # Locked budget: measured ~9.5KB at authoring time for this small
        # fixture context (catalog + fewshot dominate; catalog is bounded and
        # OWL-file-derived, not user-scaled). 20KB gives headroom for catalog
        # growth while still catching an accidental unbounded-context leak.
        assert size < 20_000

    def test_frame_fewshot_fixture_exists_and_is_valid_json(self):
        # Phase 35-08 replaced the single {input, expected} blob with a LIST of
        # heterogeneous, counterexample-shaped examples: the old fixture's two
        # Interface demonstrations both had convention-conforming input names
        # and grammar-citing rationales, which is what taught the model to read
        # the convention as a filter (UAT F3). The list shape also makes a later
        # dynamic-retrieval selector a one-line change. Phase 35-12:
        # _load_frame_fewshot() now returns the `examples` list directly.
        examples = cg_recognition._load_frame_fewshot()
        assert isinstance(examples, list) and len(examples) >= 4
        assert all("input" in e and "expected" in e for e in examples)
        assert all(isinstance(e["expected"].get("proposals"), list) for e in examples)

    def test_frame_fewshot_rationales_never_cite_the_grammar(self):
        # The regression guard for UAT F3's root cause: a demonstration that
        # justifies a proposal by the naming grammar teaches the model to
        # reject every untagged node, since untagged nodes never match it.
        examples = cg_recognition._load_frame_fewshot()
        rationales = [
            p["rationale"].lower()
            for e in examples
            for p in e["expected"]["proposals"]
        ]
        assert rationales
        for rationale in rationales:
            assert "grammar" not in rationale
            assert "convention" not in rationale
