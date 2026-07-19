"""Tests for the recognition backend (Phase 35: RCGN-01/RCGN-04).

Follows the existing test pattern from test_dg_context.py: sys.path.insert
boilerplate header, class-per-concern shape (TestValidator/TestExtractJson/
TestRetryLoop/TestPrompt), hand-built cg_context fixture dicts, and a
_FakeAdapterForRetry mirroring test_dg_context.py's own fake-adapter precedent
so no live LLM call is ever made.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import cg_recognition  # noqa: E402
from llm_gateway import GenerateResponse  # noqa: E402


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


# ── recognize_structure() -- bounded-retry loop (Phase 35-02: mirrors CTXA-04) ──

_VALID_PROPOSAL_TEXT = json.dumps(
    {
        "proposals": [
            {
                "kind": "Interface",
                "suggestedName": "11_IntF_TopChord",
                "procedureIndex": 11,
                "memberIds": ["n4"],
                "confidence": 0.88,
                "rationale": "Line SDL node wired from the tagged procedure member n1.",
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

_MALFORMED_JSON_TEXT = "this is not json at all"


class _FakeAdapterForRetry:
    """Stand-in for an llm_gateway LLMAdapter -- returns queued response texts
    in order and records every prompt it was called with (mirrors
    test_dg_context.py's own _FakeAdapterForRetry precedent, retargeted at
    cg_recognition)."""

    def __init__(self, texts: list[str]):
        self._texts = list(texts)
        self.prompts_seen: list[str] = []
        self.call_count = 0

    def generate(self, req, api_key):
        self.call_count += 1
        self.prompts_seen.append(req.prompt)
        text = self._texts.pop(0)
        return GenerateResponse(text=text, provider="fake", model="fake-model", usage={})


class TestRetryLoop:
    def test_first_attempt_valid_returns_attempts_1_no_retry(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        result = cg_recognition.recognize_structure(_cg_context())

        assert result["valid"] is True
        assert result["attempts"] == 1
        assert result["proposal"] == json.loads(_VALID_PROPOSAL_TEXT)
        assert fake_adapter.call_count == 1

    def test_malformed_json_then_valid_retries_and_succeeds_at_attempt_2(self, monkeypatch):
        fake_adapter = _FakeAdapterForRetry([_MALFORMED_JSON_TEXT, _VALID_PROPOSAL_TEXT])
        monkeypatch.setattr(cg_recognition, "get_adapter", lambda provider, base_url=None: fake_adapter)

        original_prompt = cg_recognition._build_recognition_prompt(_cg_context(), None)
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


# ── _build_recognition_prompt() -- deterministic prompt assembly ──


class TestPrompt:
    _REQUIRED_MARKERS = (
        cg_recognition._CONCEPT_CATALOG_MARKER,
        cg_recognition._FEWSHOT_MARKER,
        cg_recognition._TAGGED_ANCHOR_MARKER,
        cg_recognition._UNTAGGED_MARKER,
        cg_recognition._OUTPUT_INSTRUCTION_MARKER,
    )

    def test_prompt_contains_every_required_section_marker(self):
        prompt = cg_recognition._build_recognition_prompt(_cg_context(), None)
        for marker in self._REQUIRED_MARKERS:
            assert marker in prompt

    def test_prompt_contains_annotation_convention_grammar(self):
        prompt = cg_recognition._build_recognition_prompt(_cg_context(), None)
        assert "IntF" in prompt or "annotation_convention" in prompt

    def test_prompt_contains_json_only_output_instruction(self):
        prompt = cg_recognition._build_recognition_prompt(_cg_context(), None)
        assert "JSON" in prompt
        assert "no markdown fences" in prompt.lower() or "markdown" in prompt.lower()

    def test_procedure_index_filters_untagged_scope_to_wired_nodes(self):
        """n4 is wired to the tagged procedure-11 member n1; n3 is unrelated."""
        unfiltered = cg_recognition._build_recognition_prompt(_cg_context(), None)
        assert "n3" in unfiltered
        assert "n4" in unfiltered

        filtered = cg_recognition._build_recognition_prompt(_cg_context(), 11)
        assert "n4" in filtered
        assert "n3" not in filtered

    def test_prompt_byte_size_is_measured_and_under_locked_budget(self):
        """A4 resolution: measure the assembled prompt size and lock it as an
        assertion so future catalog growth is a deliberate, visible change."""
        prompt = cg_recognition._build_recognition_prompt(_cg_context(), None)
        size = len(prompt.encode("utf-8"))
        assert size > 0
        # Locked budget: measured ~9.5KB at authoring time for this small
        # fixture context (catalog + fewshot dominate; catalog is bounded and
        # OWL-file-derived, not user-scaled). 20KB gives headroom for catalog
        # growth while still catching an accidental unbounded-context leak.
        assert size < 20_000

    def test_frame_fewshot_fixture_exists_and_is_valid_json(self):
        fewshot = cg_recognition._load_frame_fewshot()
        assert "input" in fewshot
        assert "expected" in fewshot
        assert isinstance(fewshot["expected"].get("proposals"), list)
