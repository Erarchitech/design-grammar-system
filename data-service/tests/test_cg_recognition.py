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
