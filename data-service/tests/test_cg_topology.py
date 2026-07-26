"""Tests for cg_topology -- Tier 0 of the two-tier hybrid recognizer
(Phase 35 SC1 remediation, RCGN-01).

Follows the established test pattern from test_cg_recognition.py: sys.path
boilerplate header, class-per-concern shape, hand-built cg_context fixture
dicts. Where degree-bearing assertions need real wiring, this file derives a
cgContextJson v1-shaped fixture from the enriched
`DG/tests/DG.Tests/Fixtures/frame-cg-context.json` (Phase 35-05) -- same
nodes/wires/groups, reshaped from that fixture's RawCanvas group structure
into the algorithms[].procedures[] / untagged{nodeIds,groups} shape
cg_topology consumes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cg_topology  # noqa: E402


# ── Small hand-built cg_context, mirroring test_cg_recognition.py's _cg_context() ──
#
# n1: tagged (procedure 11 member), n2: tagged (procedure 11 member, wired
# from n1), n3: untagged (unrelated, fully isolated), n4: untagged (wired to
# n1, the procedure's tagged member) -- lets tests exercise
# procedure_index-scoped filtering and adjacent_tagged_procedures via wire
# adjacency without pulling in the whole Frame fixture.


def _small_ctx() -> dict:
    return {
        "nodes": [
            {"instanceId": "n1", "componentGuid": "g1", "name": "Number Slider", "nickname": "SpansCount",
             "position": [0, 0], "slider": {"min": 1, "max": 20, "step": 1}, "isIntegerSlider": True},
            {"instanceId": "n2", "componentGuid": "g2", "name": "Divide Curve", "nickname": "Divide",
             "position": [10, 0]},
            {"instanceId": "n3", "componentGuid": "g3", "name": "Panel", "nickname": "loose panel",
             "position": [500, 500]},
            {"instanceId": "n4", "componentGuid": "g4", "name": "Param", "nickname": "Relay",
             "position": [20, 0]},
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
                        "memberIds": ["n1", "n2"],
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
                {"nickname": "wired relay group", "memberIds": ["n4"]},
            ],
        },
        "wires": [
            {"fromNode": "n1", "fromParam": "p_out", "toNode": "n2", "toParam": "p_in"},
            {"fromNode": "n2", "fromParam": "p_out", "toNode": "n4", "toParam": "p_in"},
        ],
    }


def _empty_procedure_ctx() -> dict:
    """procedure_index 11 is tagged but owns zero members -- the F2 trigger."""
    ctx = _small_ctx()
    ctx["algorithms"][0]["procedures"][0]["memberIds"] = []
    return ctx


# ── scope_untagged() ──


class TestScope:
    def test_none_procedure_returns_all_untagged(self):
        scope = cg_topology.scope_untagged(_small_ctx(), None)
        assert scope.node_ids == ["n3", "n4"]
        assert scope.empty_procedure is False
        assert scope.procedure_index is None

    def test_procedure_narrows_to_wire_adjacent(self):
        scope = cg_topology.scope_untagged(_small_ctx(), 11)
        # n4 is one wire-hop from n2 (a procedure-11 member); n3 is unrelated.
        assert scope.node_ids == ["n4"]
        assert scope.empty_procedure is False
        assert scope.groups == [{"nickname": "wired relay group", "memberIds": ["n4"]}]

    def test_empty_procedure_never_widens_scope(self):
        """The F2 regression test: procedure 11 is tagged but member-less."""
        scope = cg_topology.scope_untagged(_empty_procedure_ctx(), 11)
        assert scope.empty_procedure is True
        assert scope.node_ids == []
        assert scope.groups == []

    def test_malformed_context_returns_empty_scope_without_raising(self):
        scope = cg_topology.scope_untagged({}, None)
        assert scope.node_ids == []
        assert scope.groups == []
        assert scope.empty_procedure is False

    def test_malformed_procedure_lookup_returns_empty_scope_without_raising(self):
        scope = cg_topology.scope_untagged({"algorithms": "not-a-list"}, 11)
        assert scope.empty_procedure is True
        assert scope.node_ids == []


# ── output_token_budget() ──


class TestOutputTokenBudget:
    def test_floor_at_zero_residual(self):
        assert cg_topology.output_token_budget([]) == 512

    def test_scaled_by_residual_count(self):
        assert cg_topology.output_token_budget(5) == 856

    def test_ceiling_at_large_residual(self):
        assert cg_topology.output_token_budget(1000) == 8192
