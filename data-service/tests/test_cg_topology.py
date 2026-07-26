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

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

import cg_recognition  # noqa: E402
import cg_schemas  # noqa: E402
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


# ── Enriched Frame fixture, reshaped from frame-cg-context.json (35-05) into
# cgContextJson v1's algorithms[].procedures[] / untagged{nodeIds,groups}
# shape. Same 34 nodes and 33 wires; 11_Proc/12_Proc own their real members;
# untagged is exactly the abstainExpected set (n-untagged-01, n-scratch-01,
# n-scratch-02). ──

_FRAME_NODES = [
    {"instanceId": "n-divide-curve", "componentGuid": "guid-divide-curve", "name": "Divide Curve", "nickname": "Divide", "position": [100, 100]},
    {"instanceId": "n-topchord", "componentGuid": "guid-line-sdl", "name": "Line SDL", "nickname": "TopChord", "position": [140, 100]},
    {"instanceId": "n-footer-bottom", "componentGuid": "guid-line", "name": "Line", "nickname": "FooterBottom", "position": [100, 400]},
    {"instanceId": "n-parsplit", "componentGuid": "guid-param", "name": "Param", "nickname": "ParSplitAt", "position": [200, 100]},
    {"instanceId": "n-trussconfig-intf", "componentGuid": "guid-param", "name": "Param", "nickname": "TrussConfig", "position": [220, 100]},
    {"instanceId": "n-mergeres", "componentGuid": "guid-param", "name": "Param", "nickname": "MergeRes", "position": [240, 100]},
    {"instanceId": "n-footerframe-intf", "componentGuid": "guid-param", "name": "Param", "nickname": "FooterFrame", "position": [220, 400]},
    {"instanceId": "n-spanscount", "componentGuid": "guid-number-slider", "name": "Number Slider", "nickname": "SpansCount",
     "position": [10, 10], "slider": {"min": 1, "max": 20, "step": 1}, "isIntegerSlider": True},
    {"instanceId": "n-lentotal", "componentGuid": "guid-number-slider", "name": "Number Slider", "nickname": "LenTotal", "position": [10, 30]},
    {"instanceId": "n-mode", "componentGuid": "guid-value-list", "name": "Value List", "nickname": "Mode", "position": [10, 50]},
    {"instanceId": "n-htotal", "componentGuid": "guid-number-slider", "name": "Number Slider", "nickname": "HTotal", "position": [10, 70]},
    {"instanceId": "n-hfooter", "componentGuid": "guid-number-slider", "name": "Number Slider", "nickname": "HFooter", "position": [10, 410]},
    {"instanceId": "n-footercount", "componentGuid": "guid-number-slider", "name": "Number Slider", "nickname": "FooterCount", "position": [10, 430]},
    {"instanceId": "n-ptzero", "componentGuid": "guid-construct-point", "name": "Construct Point", "nickname": "ptZero", "position": [30, 10]},
    {"instanceId": "n-vecy", "componentGuid": "guid-unit-y", "name": "Unit Y", "nickname": "vecY", "position": [30, 30]},
    {"instanceId": "n-splitpar", "componentGuid": "guid-panel", "name": "Panel", "nickname": "SplitPar", "position": [30, 50]},
    {"instanceId": "n-trussconfig-const11", "componentGuid": "guid-panel", "name": "Panel", "nickname": "TrussConfig", "position": [30, 70]},
    {"instanceId": "n-divider", "componentGuid": "guid-panel", "name": "Panel", "nickname": "Divider", "position": [30, 90]},
    {"instanceId": "n-indlist1", "componentGuid": "guid-panel", "name": "Panel", "nickname": "IndList_1", "position": [30, 440]},
    {"instanceId": "n-indlist2", "componentGuid": "guid-panel", "name": "Panel", "nickname": "IndList_2", "position": [30, 460]},
    {"instanceId": "n-trussconfig-const12", "componentGuid": "guid-panel", "name": "Panel", "nickname": "TrussConfig", "position": [30, 480]},
    {"instanceId": "n-divpoints", "componentGuid": "guid-panel", "name": "Panel", "nickname": "DivPoints", "position": [50, 10]},
    {"instanceId": "n-paramat", "componentGuid": "guid-evaluate-curve", "name": "Evaluate Curve", "nickname": "ParamAt", "position": [50, 30]},
    {"instanceId": "n-linesdl", "componentGuid": "guid-line-sdl", "name": "Line SDL", "nickname": "LineSDL", "position": [50, 50]},
    {"instanceId": "n-upperchord", "componentGuid": "guid-line-sdl", "name": "Line SDL", "nickname": "UpperChord", "position": [50, 70]},
    {"instanceId": "n-topframe", "componentGuid": "guid-line-sdl", "name": "Line SDL", "nickname": "TopFrame", "position": [50, 90]},
    {"instanceId": "n-vertpost", "componentGuid": "guid-line-sdl", "name": "Line SDL", "nickname": "VertPost", "position": [50, 110]},
    {"instanceId": "n-bottomln", "componentGuid": "guid-line", "name": "Line", "nickname": "BottomLn", "position": [50, 420]},
    {"instanceId": "n-topln", "componentGuid": "guid-line", "name": "Line", "nickname": "TopLn", "position": [50, 440]},
    {"instanceId": "n-footerunit", "componentGuid": "guid-panel", "name": "Panel", "nickname": "FooterUnit", "position": [50, 460]},
    {"instanceId": "n-footerframe-emg", "componentGuid": "guid-panel", "name": "Panel", "nickname": "FooterFrame", "position": [50, 480]},
    {"instanceId": "n-scratch-01", "componentGuid": "guid-panel", "name": "Panel", "nickname": "scribbled note 1", "position": [500, 500]},
    {"instanceId": "n-scratch-02", "componentGuid": "guid-panel", "name": "Panel", "nickname": "scribbled note 2", "position": [520, 500]},
    {"instanceId": "n-untagged-01", "componentGuid": "guid-panel", "name": "Panel", "nickname": "loose panel", "position": [700, 700]},
]

_FRAME_WIRES = [
    {"fromNode": "n-ptzero", "fromParam": "out0", "toNode": "n-topchord", "toParam": "in0"},
    {"fromNode": "n-vecy", "fromParam": "out0", "toNode": "n-topchord", "toParam": "in1"},
    {"fromNode": "n-lentotal", "fromParam": "out0", "toNode": "n-topchord", "toParam": "in2"},
    {"fromNode": "n-topchord", "fromParam": "out0", "toNode": "n-divide-curve", "toParam": "in0"},
    {"fromNode": "n-spanscount", "fromParam": "out0", "toNode": "n-divide-curve", "toParam": "in1"},
    {"fromNode": "n-divider", "fromParam": "out0", "toNode": "n-divide-curve", "toParam": "in2"},
    {"fromNode": "n-divide-curve", "fromParam": "out0", "toNode": "n-parsplit", "toParam": "in0"},
    {"fromNode": "n-divide-curve", "fromParam": "out1", "toNode": "n-divpoints", "toParam": "in0"},
    {"fromNode": "n-divide-curve", "fromParam": "out2", "toNode": "n-mergeres", "toParam": "in0"},
    {"fromNode": "n-parsplit", "fromParam": "out0", "toNode": "n-paramat", "toParam": "in1"},
    {"fromNode": "n-topchord", "fromParam": "out0", "toNode": "n-paramat", "toParam": "in0"},
    {"fromNode": "n-ptzero", "fromParam": "out0", "toNode": "n-linesdl", "toParam": "in0"},
    {"fromNode": "n-mergeres", "fromParam": "out0", "toNode": "n-linesdl", "toParam": "in1"},
    {"fromNode": "n-htotal", "fromParam": "out0", "toNode": "n-linesdl", "toParam": "in2"},
    {"fromNode": "n-ptzero", "fromParam": "out0", "toNode": "n-upperchord", "toParam": "in0"},
    {"fromNode": "n-splitpar", "fromParam": "out0", "toNode": "n-upperchord", "toParam": "in1"},
    {"fromNode": "n-htotal", "fromParam": "out0", "toNode": "n-upperchord", "toParam": "in2"},
    {"fromNode": "n-ptzero", "fromParam": "out0", "toNode": "n-topframe", "toParam": "in0"},
    {"fromNode": "n-trussconfig-const11", "fromParam": "out0", "toNode": "n-topframe", "toParam": "in1"},
    {"fromNode": "n-htotal", "fromParam": "out0", "toNode": "n-topframe", "toParam": "in2"},
    {"fromNode": "n-mode", "fromParam": "out0", "toNode": "n-trussconfig-intf", "toParam": "in0"},
    {"fromNode": "n-ptzero", "fromParam": "out0", "toNode": "n-vertpost", "toParam": "in0"},
    {"fromNode": "n-trussconfig-intf", "fromParam": "out0", "toNode": "n-vertpost", "toParam": "in1"},
    {"fromNode": "n-htotal", "fromParam": "out0", "toNode": "n-vertpost", "toParam": "in2"},
    {"fromNode": "n-indlist1", "fromParam": "out0", "toNode": "n-footer-bottom", "toParam": "in0"},
    {"fromNode": "n-indlist2", "fromParam": "out0", "toNode": "n-footer-bottom", "toParam": "in1"},
    {"fromNode": "n-footer-bottom", "fromParam": "out0", "toNode": "n-footerframe-intf", "toParam": "in0"},
    {"fromNode": "n-footerframe-intf", "fromParam": "out0", "toNode": "n-topln", "toParam": "in0"},
    {"fromNode": "n-trussconfig-const12", "fromParam": "out0", "toNode": "n-topln", "toParam": "in1"},
    {"fromNode": "n-footer-bottom", "fromParam": "out0", "toNode": "n-bottomln", "toParam": "in0"},
    {"fromNode": "n-indlist2", "fromParam": "out0", "toNode": "n-bottomln", "toParam": "in1"},
    {"fromNode": "n-hfooter", "fromParam": "out0", "toNode": "n-footerunit", "toParam": "in0"},
    {"fromNode": "n-footercount", "fromParam": "out0", "toNode": "n-footerframe-emg", "toParam": "in0"},
]

_PROC_11_MEMBERS = [
    "n-divide-curve", "n-topchord", "n-parsplit", "n-trussconfig-intf", "n-mergeres",
    "n-spanscount", "n-lentotal", "n-mode", "n-htotal", "n-ptzero", "n-vecy", "n-splitpar",
    "n-trussconfig-const11", "n-divider", "n-divpoints", "n-paramat", "n-linesdl",
    "n-upperchord", "n-topframe", "n-vertpost",
]

_PROC_12_MEMBERS = [
    "n-footer-bottom", "n-footerframe-intf", "n-hfooter", "n-footercount", "n-indlist1",
    "n-indlist2", "n-trussconfig-const12", "n-bottomln", "n-topln", "n-footerunit",
    "n-footerframe-emg",
]


def _frame_cg_context() -> dict:
    return {
        "nodes": _FRAME_NODES,
        "algorithms": [
            {
                "index": 1,
                "name": "1_ALGORITHM",
                "procedures": [
                    {
                        "id": "cg:1:proc:11", "index": 11, "name": "2D Truss Configuration",
                        "source": "tagged", "memberIds": list(_PROC_11_MEMBERS),
                        "patterns": [], "parameters": [], "interfaces": [],
                    },
                    {
                        "id": "cg:1:proc:12", "index": 12, "name": "2D Footer Configuration",
                        "source": "tagged", "memberIds": list(_PROC_12_MEMBERS),
                        "patterns": [], "parameters": [], "interfaces": [],
                    },
                ],
            }
        ],
        "untagged": {
            "nodeIds": ["n-scratch-01", "n-scratch-02", "n-untagged-01"],
            "groups": [
                {"nickname": "Scratch notes", "memberIds": ["n-scratch-01", "n-scratch-02"]},
            ],
        },
        "wires": _FRAME_WIRES,
    }


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


# ── widget_kind() -- C# ClassifyNodeKind parity table ──

_WIDGET_KIND_CASES = [
    ("slider present wins over any name", {"name": "Number Slider", "slider": {"min": 0, "max": 1, "step": 0.01}}, "Slider"),
    ("value list substring, case-insensitive", {"name": "123 value LIST widget"}, "ValueList"),
    ("panel substring, case-insensitive", {"name": "Big PANEL"}, "Panel"),
    ("toggle substring, case-insensitive", {"name": "toggle switch"}, "Boolean"),
    ("number exact match", {"name": "Number"}, "Number"),
    ("integer exact match", {"name": "Integer"}, "Integer"),
    ("text exact match", {"name": "Text"}, "Text"),
    ("string exact match maps to Text", {"name": "String"}, "Text"),
    ("geometry exact match", {"name": "Line"}, "Geometry"),
    ("geometry exact match, another member", {"name": "Curve"}, "Geometry"),
    ("unmatched geometry-ish name stays None", {"name": "Construct Point"}, "None"),
    ("number-slider exact-match trap: no slider field, name != 'Number'", {"name": "Number Slider"}, "None"),
    ("missing name defaults to None", {}, "None"),
]


class TestWidgetKindParity:
    @pytest.mark.parametrize("label,node,expected", _WIDGET_KIND_CASES)
    def test_parity_case(self, label, node, expected):
        assert cg_topology.widget_kind(node) == expected, label


# ── extract_features() ──


class TestExtractFeatures:
    def test_frame_spanscount_has_zero_in_degree(self):
        features = cg_topology.extract_features(_frame_cg_context(), ["n-spanscount"])
        assert features["n-spanscount"].in_degree == 0
        assert features["n-spanscount"].out_degree > 0
        assert features["n-spanscount"].widget_kind == "Slider"

    def test_frame_emg_grouped_node_has_zero_out_degree(self):
        features = cg_topology.extract_features(_frame_cg_context(), ["n-linesdl"])
        assert features["n-linesdl"].out_degree == 0
        assert features["n-linesdl"].in_degree > 0

    def test_frame_abstain_nodes_are_fully_isolated(self):
        node_ids = ["n-untagged-01", "n-scratch-01", "n-scratch-02"]
        features = cg_topology.extract_features(_frame_cg_context(), node_ids)
        for node_id in node_ids:
            assert features[node_id].in_degree == 0, node_id
            assert features[node_id].out_degree == 0, node_id

    def test_frame_scratch_nodes_share_a_group(self):
        features = cg_topology.extract_features(_frame_cg_context(), ["n-scratch-01", "n-scratch-02"])
        assert features["n-scratch-01"].group_id == "Scratch notes"
        assert features["n-scratch-01"].group_member_count == 2
        assert features["n-scratch-02"].group_member_count == 2

    def test_adjacent_tagged_procedures_via_one_hop_wire(self):
        features = cg_topology.extract_features(_small_ctx(), ["n4"])
        assert features["n4"].adjacent_tagged_procedures == [11]

    def test_isolated_untagged_node_has_no_adjacent_procedures(self):
        features = cg_topology.extract_features(_small_ctx(), ["n3"])
        assert features["n3"].adjacent_tagged_procedures == []

    def test_module_never_reads_nested_group_ids(self):
        source = open(cg_topology.__file__, "r", encoding="utf-8").read()
        assert "nestedGroupIds" not in source

    def test_malformed_context_returns_empty_features_without_raising(self):
        features = cg_topology.extract_features({}, ["missing"])
        assert features["missing"].in_degree == 0
        assert features["missing"].out_degree == 0
        assert features["missing"].widget_kind == "None"


# ── classify() -- R1-R6 rule table, one PASS and one ABSTAIN per rule ──


def _features(
    instance_id="n1",
    name="",
    nickname="n1",
    in_degree=0,
    out_degree=0,
    widget="None",
    group_id=None,
    group_member_count=0,
    adjacent=(11,),
) -> cg_topology.NodeFeatures:
    return cg_topology.NodeFeatures(
        instance_id=instance_id,
        name=name,
        nickname=nickname,
        component_guid="g",
        widget_kind=widget,
        in_degree=in_degree,
        out_degree=out_degree,
        group_id=group_id,
        group_member_count=group_member_count,
        adjacent_tagged_procedures=list(adjacent),
    )


class TestClassifyR1Var:
    def test_r1_pass_slider_with_no_upstream_decides_var(self):
        f = _features(widget="Slider", in_degree=0, nickname="SpansCount")
        result = cg_topology.classify({"n1": f})
        assert result.residual == []
        assert result.decided[0]["kind"] == "Var"
        assert result.decided[0]["confidence"] == 1.0

    def test_r1_abstain_when_widget_has_upstream(self):
        # A Slider with an upstream wire is not an architect-driven input by
        # this signal, and its degree profile also fails R2/R3/R4.
        f = _features(widget="Slider", in_degree=1, out_degree=1)
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]


class TestClassifyR2Const:
    def test_r2_pass_source_only_non_widget_decides_const(self):
        # Const is not restricted to widgets -- Construct Point/Unit Y style.
        f = _features(widget="None", in_degree=0, out_degree=2, name="Construct Point")
        result = cg_topology.classify({"n1": f})
        assert result.decided[0]["kind"] == "Const"

    def test_r2_abstain_when_widget_kind_disqualifies(self):
        # widget_kind Number is neither R1's set nor R2's {Panel, None}.
        f = _features(widget="Number", in_degree=0, out_degree=1)
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]

    def test_r2_defers_to_residual_when_shared_with_pattern_group(self):
        f = _features(widget="None", in_degree=0, out_degree=1, group_member_count=3)
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]


class TestClassifyR3Emg:
    def test_r3_pass_clean_sink_decides_emg(self):
        f = _features(widget="Geometry", in_degree=1, out_degree=0, name="Line SDL")
        result = cg_topology.classify({"n1": f})
        assert result.decided[0]["kind"] == "Emg"

    def test_r3_abstain_when_not_a_sink(self):
        f = _features(widget="Geometry", in_degree=1, out_degree=1, name="Evaluate Curve")
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]

    def test_r3_defers_to_residual_when_shared_with_pattern_group(self):
        f = _features(widget="Geometry", in_degree=1, out_degree=0, group_member_count=2)
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]


class TestClassifyR4Interface:
    def test_r4_pass_bare_param_relay_decides_intf(self):
        f = _features(widget="None", in_degree=1, out_degree=1, name="Param", nickname="ParSplitAt")
        result = cg_topology.classify({"n1": f})
        assert result.decided[0]["kind"] == "IntF"

    def test_r4_abstain_when_not_a_bare_param(self):
        # Same degree profile, but not a bare GH `Param` component -- would
        # swallow ordinary compute-chain nodes if allowed through.
        f = _features(widget="None", in_degree=1, out_degree=1, name="Divide Curve")
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]


class TestClassifyR5Isolated:
    def test_r5_pass_fully_isolated_node_abstains(self):
        f = _features(widget="None", in_degree=0, out_degree=0)
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]

    def test_r5_isolated_widget_is_owned_by_r1_not_r5(self):
        # First-match-wins: an isolated Slider still matches R1's condition
        # (in_degree == 0 and widget in {Slider, ValueList, Boolean}) before
        # R5 is ever considered.
        f = _features(widget="Slider", in_degree=0, out_degree=0)
        result = cg_topology.classify({"n1": f})
        assert result.decided[0]["kind"] == "Var"


class TestClassifyR6Everything:
    def test_r6_pass_multi_io_compute_node_abstains(self):
        f = _features(widget="None", in_degree=2, out_degree=3, name="Divide Curve")
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]

    def test_r6_abstain_boundary_not_isolated_but_no_earlier_rule_matches(self):
        f = _features(widget="Panel", in_degree=1, out_degree=1, name="Panel")
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]


class TestClassifyProcedureAttribution:
    def test_abstains_when_no_adjacent_tagged_procedure(self):
        f = _features(widget="Slider", in_degree=0, adjacent=())
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]

    def test_abstains_when_multiple_adjacent_tagged_procedures(self):
        f = _features(widget="Slider", in_degree=0, adjacent=(11, 12))
        result = cg_topology.classify({"n1": f})
        assert result.decided == []
        assert result.residual == ["n1"]


class TestClassifyShapeAndRationale:
    def test_decided_rows_validate_as_structure_proposal(self):
        f1 = _features(instance_id="n1", widget="Slider", in_degree=0, nickname="SpansCount")
        f2 = _features(instance_id="n2", widget="None", in_degree=0, out_degree=1, name="Construct Point", nickname="ptZero")
        result = cg_topology.classify({"n1": f1, "n2": f2})
        cg_schemas.ProposedStructure.model_validate({"proposals": result.decided, "unrecognized": []})

    def test_decided_rows_have_full_confidence_and_mechanical_rationale(self):
        f = _features(widget="Slider", in_degree=0)
        result = cg_topology.classify({"n1": f})
        row = result.decided[0]
        assert row["confidence"] == 1.0
        assert "in-degree" in row["rationale"] or "out-degree" in row["rationale"]
        assert "grammar" not in row["rationale"].lower()

    def test_frame_abstain_nodes_land_in_residual(self):
        node_ids = ["n-untagged-01", "n-scratch-01", "n-scratch-02"]
        features = cg_topology.extract_features(_frame_cg_context(), node_ids)
        result = cg_topology.classify(features)
        assert result.decided == []
        assert sorted(result.residual) == sorted(node_ids)


# ── merge() -- order-stable Tier-0 + Tier-1 composition (G13) ──


def _tier1_proposal(**overrides) -> dict:
    base = {
        "kind": "Pattern",
        "suggestedName": "11_Pat_Something",
        "procedureIndex": 11,
        "memberIds": ["n-b"],
        "confidence": 0.8,
        "rationale": "grouped compute chain",
    }
    base.update(overrides)
    return base


def _tier0_row(**overrides) -> dict:
    base = {
        "kind": "Var",
        "suggestedName": "11_Var_A",
        "procedureIndex": 11,
        "memberIds": ["n-a"],
        "confidence": 1.0,
        "rationale": "in-degree 0, out-degree 1, widget=Slider",
    }
    base.update(overrides)
    return base


class TestMerge:
    def test_merge_is_byte_identical_on_repeat_calls(self):
        decided = [_tier0_row()]
        parsed = {"proposals": [_tier1_proposal()], "unrecognized": []}
        first = json.dumps(cg_topology.merge(decided, parsed))
        second = json.dumps(cg_topology.merge(decided, parsed))
        assert first == second

    def test_merge_order_is_stable_under_shuffled_tier0_input(self):
        row_a = _tier0_row(memberIds=["n-a"], procedureIndex=11, kind="Var")
        row_b = _tier0_row(memberIds=["n-b"], procedureIndex=11, kind="Const", suggestedName="11_Const_B")
        row_c = _tier0_row(memberIds=["n-c"], procedureIndex=12, kind="Emg", suggestedName="12_Emg_C")
        parsed = {"proposals": [], "unrecognized": []}

        baseline = cg_topology.merge([row_a, row_b, row_c], parsed)
        shuffled = cg_topology.merge([row_c, row_a, row_b], parsed)

        assert [p["memberIds"] for p in shuffled["proposals"]] == [p["memberIds"] for p in baseline["proposals"]]

    def test_tier0_rows_precede_tier1_rows(self):
        decided = [_tier0_row()]
        parsed = {"proposals": [_tier1_proposal()], "unrecognized": []}
        merged = cg_topology.merge(decided, parsed)
        assert merged["proposals"][0]["memberIds"] == ["n-a"]
        assert merged["proposals"][1]["memberIds"] == ["n-b"]

    def test_tier1_overlap_with_tier0_survives_and_is_caught_by_validator(self):
        decided = [_tier0_row(memberIds=["n-a"])]
        overlapping = _tier1_proposal(memberIds=["n-a", "n-b"])
        parsed = {"proposals": [overlapping], "unrecognized": []}

        merged = cg_topology.merge(decided, parsed)

        # Not dropped: the overlapping Tier-1 proposal is present verbatim.
        assert any(p["memberIds"] == ["n-a", "n-b"] for p in merged["proposals"])

        cg_context = {
            "nodes": [{"instanceId": "n-a"}, {"instanceId": "n-b"}],
            "algorithms": [],
        }
        validation = cg_recognition.validate_proposed_structure(merged, cg_context)
        assert validation["valid"] is False
        assert any(v["code"] == "duplicate_member" for v in validation["violations"])

    def test_merge_passes_through_unrecognized_and_handles_malformed_parsed(self):
        merged = cg_topology.merge([], {"proposals": [], "unrecognized": [{"memberIds": ["n-z"], "reason": "isolated"}]})
        assert merged["unrecognized"] == [{"memberIds": ["n-z"], "reason": "isolated"}]

        merged_malformed = cg_topology.merge([], None)
        assert merged_malformed == {"proposals": [], "unrecognized": []}
