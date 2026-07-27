"""Tier 0 tests for cg_input_bindings.py (Phase 38 Plan 03: JOIN B).

All tests here are Tier 0 -- no Neo4j, no LLM. A Neo4j session is faked with
a small object exposing `run(query, params) -> list[dict]` that returns a
canned row list, following the existing `_CannedAlgorithmSession` pattern in
test_cg_structure_checks.py. Every read this module issues is a single call,
so one canned-row list per test is sufficient.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import cg_input_bindings as bindings_module  # noqa: E402
import cg_structure_checks  # noqa: E402
from cg_fixtures import (  # noqa: E402
    RULE_DIRECT_PARAM_ID,
    RULE_GEOMETRY_ID,
    RULE_MONOTONE_ID,
    RULE_UNKNOWN_ID,
    direct_param_binding,
    direct_param_limit_rows,
    geometry_rule_limit_rows,
    monotone_binding,
    no_builtin_limit_rows,
    published_parameter_rows,
    rule_limit_row,
    structure_rules_with_bindings,
)


class _FakeSession:
    """Minimal session double: one canned row list, returned regardless of
    the query text -- every function under test issues exactly one call."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def run(self, query: str, params: dict) -> list[dict]:
        del query, params
        return list(self._rows)


def _write_payload(payload: dict) -> str:
    path = tempfile.mktemp(suffix=".json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return path


# ── Loader and fence ──


def test_missing_file_returns_empty_dict_no_raise():
    assert bindings_module.load_input_bindings("this/path/does/not/exist.json") == {}


def test_malformed_json_returns_empty_dict_no_raise():
    path = tempfile.mktemp(suffix=".json")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{not valid json")
    assert bindings_module.load_input_bindings(path) == {}


@pytest.mark.parametrize("forbidden_key", ["min", "max", "threshold", "value", "limit", "operator"])
def test_forbidden_key_raises_with_key_and_rule_id_in_message(forbidden_key):
    payload = {
        "inputBindings": [
            {
                "ruleId": "R_BAD",
                "determinability": "direct-parameter",
                "parameters": ["A"],
                "description": "x",
                forbidden_key: 1,
            }
        ]
    }
    path = _write_payload(payload)
    with pytest.raises(bindings_module.InputBindingError) as excinfo:
        bindings_module.load_input_bindings(path)
    message = str(excinfo.value)
    assert forbidden_key in message
    assert "R_BAD" in message


def test_monotone_bound_without_metric_expression_raises():
    payload = {
        "inputBindings": [
            {
                "ruleId": "R_MONO",
                "determinability": "monotone-bound",
                "parameters": ["A"],
                "monotoneIn": ["A"],
                "description": "x",
            }
        ]
    }
    with pytest.raises(bindings_module.InputBindingError):
        bindings_module.load_input_bindings(_write_payload(payload))


def test_monotone_bound_without_monotone_in_raises():
    payload = {
        "inputBindings": [
            {
                "ruleId": "R_MONO",
                "determinability": "monotone-bound",
                "parameters": ["A"],
                "metricExpression": "A",
                "description": "x",
            }
        ]
    }
    with pytest.raises(bindings_module.InputBindingError):
        bindings_module.load_input_bindings(_write_payload(payload))


def test_monotone_in_outside_parameters_raises():
    payload = {
        "inputBindings": [
            {
                "ruleId": "R_MONO",
                "determinability": "monotone-bound",
                "parameters": ["A"],
                "metricExpression": "A + B",
                "monotoneIn": ["B"],
                "description": "x",
            }
        ]
    }
    with pytest.raises(bindings_module.InputBindingError):
        bindings_module.load_input_bindings(_write_payload(payload))


def test_duplicate_rule_id_raises():
    entry = {
        "ruleId": "R_DUP",
        "determinability": "direct-parameter",
        "parameters": ["A"],
        "description": "x",
    }
    payload = {"inputBindings": [dict(entry), dict(entry)]}
    with pytest.raises(bindings_module.InputBindingError):
        bindings_module.load_input_bindings(_write_payload(payload))


def test_unknown_determinability_raises():
    payload = {
        "inputBindings": [
            {
                "ruleId": "R_X",
                "determinability": "always-satisfied",
                "parameters": ["A"],
                "description": "x",
            }
        ]
    }
    with pytest.raises(bindings_module.InputBindingError):
        bindings_module.load_input_bindings(_write_payload(payload))


def test_binding_for_rule_returns_none_for_unmapped_rule():
    assert bindings_module.binding_for_rule({}, "R_ANYTHING") is None


# ── Phase 37 non-regression (the D-07 proof) ──


def test_load_structure_rules_unaffected_by_input_bindings_addition():
    """Calls the shipped cg_structure_checks.load_structure_rules() against
    the real, edited llm/structure_rules.json and asserts all four original
    mappings are unchanged and no exception is raised -- proving the
    inputBindings addition required zero Phase 37 changes."""
    payload = cg_structure_checks.load_structure_rules()
    rule_ids = {entry["ruleId"] for entry in payload["mappings"]}
    assert rule_ids == {
        "R_STRUCT_FRAME_FOOTER_V",
        "R_STRUCT_FRAME_HEIGHT_VAR_V",
        "R_STRUCT_NO_ORPHAN_PATTERN_V",
        "R_STRUCT_PROC_INTERFACE_V",
    }


# ── Limit extraction ──


def test_greater_than_body_yields_inverted_le_operator():
    session = _FakeSession([rule_limit_row("swrlb:greaterThan", "?v", "75", "xsd:decimal")])
    limit = bindings_module.read_rule_limit(session, "R_X", "p")
    assert limit == bindings_module.RuleLimit(
        operator="<=", value=75.0, datatype="xsd:decimal", variableName="?v"
    )


def test_less_than_body_yields_inverted_ge_operator():
    session = _FakeSession([rule_limit_row("swrlb:lessThan", "?v", "3", "xsd:decimal")])
    limit = bindings_module.read_rule_limit(session, "R_X", "p")
    assert limit.operator == ">="


def test_unknown_rule_id_raises_rule_not_found():
    session = _FakeSession([])
    with pytest.raises(bindings_module.RuleNotFoundError):
        bindings_module.read_rule_limit(session, RULE_UNKNOWN_ID, "p")


def test_rule_with_no_builtin_atom_returns_none_no_raise():
    session = _FakeSession(no_builtin_limit_rows())
    assert bindings_module.read_rule_limit(session, "R_X", "p") is None


def test_rule_with_two_comparison_atoms_returns_none_and_logs_one_warning(caplog):
    session = _FakeSession(
        [
            rule_limit_row("swrlb:greaterThan", "?v", "75", "xsd:decimal"),
            rule_limit_row("swrlb:lessThan", "?v", "10", "xsd:decimal"),
        ]
    )
    with caplog.at_level(logging.WARNING, logger=bindings_module.logger.name):
        result = bindings_module.read_rule_limit(session, "R_X", "p")
    assert result is None
    assert len(caplog.records) == 1


def test_var_arg_at_pos_two_returns_none():
    session = _FakeSession([rule_limit_row("swrlb:greaterThan", None, None, "xsd:decimal")])
    assert bindings_module.read_rule_limit(session, "R_X", "p") is None


def test_non_numeric_lex_returns_none():
    session = _FakeSession([rule_limit_row("swrlb:greaterThan", "?v", "abc", "xsd:decimal")])
    assert bindings_module.read_rule_limit(session, "R_X", "p") is None


# ── Classification ──


def test_unmapped_rule_classifies_geometry_required_with_limit_none():
    """The D-09 structural guarantee: limit is None even though the fixture
    rule has a readable swrlb:greaterThan atom."""
    session = _FakeSession(geometry_rule_limit_rows())
    classification = bindings_module.classify_rule(session, RULE_GEOMETRY_ID, "p", {})
    assert classification.determinability == "geometry-required"
    assert classification.limit is None
    assert classification.source == "default"
    assert classification.parameterNames == ()


def test_direct_parameter_binding_carries_class_and_parameters_with_limit():
    session = _FakeSession(direct_param_limit_rows())
    binding_dict = {RULE_DIRECT_PARAM_ID: direct_param_binding()}
    classification = bindings_module.classify_rule(session, RULE_DIRECT_PARAM_ID, "p", binding_dict)
    assert classification.determinability == "direct-parameter"
    assert classification.parameterNames == ("HTotal",)
    assert classification.source == "binding"
    assert classification.limit is not None


def test_override_replaces_parameters_preserves_determinability():
    session = _FakeSession(direct_param_limit_rows())
    binding_dict = {RULE_DIRECT_PARAM_ID: direct_param_binding()}
    classification = bindings_module.classify_rule(
        session, RULE_DIRECT_PARAM_ID, "p", binding_dict, parameter_overrides=["OtherParam"]
    )
    assert classification.source == "override"
    assert classification.parameterNames == ("OtherParam",)
    assert classification.determinability == "direct-parameter"


def test_monotone_bound_binding_carries_metric_expression_and_monotone_in():
    session = _FakeSession(
        [rule_limit_row("swrlb:greaterThan", "?height", "75", "xsd:decimal")]
    )
    binding_dict = {RULE_MONOTONE_ID: monotone_binding()}
    classification = bindings_module.classify_rule(session, RULE_MONOTONE_ID, "p", binding_dict)
    assert classification.determinability == "monotone-bound"
    assert classification.metricExpression == "HTotal + 0.1 * SpansCount"
    assert classification.monotoneIn == ("HTotal",)
    assert classification.limit is not None


def test_classify_rule_propagates_rule_not_found_before_binding_lookup():
    session = _FakeSession([])
    with pytest.raises(bindings_module.RuleNotFoundError):
        bindings_module.classify_rule(session, RULE_UNKNOWN_ID, "p", {})


# ── Selection and type mapping ──


@pytest.mark.parametrize(
    "param_name,expected_state_type,expected_reason",
    [
        ("HTotal", "Number", None),
        ("SpansCount", "Integer", None),
        ("IsCorner", "Boolean", None),
        ("Notes", None, "unsupported-datatype"),
        ("Shape", None, "unsupported-datatype"),
    ],
)
def test_datatype_to_state_type_and_unsupported_datatype_table(
    param_name, expected_state_type, expected_reason
):
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="geometry-required",
        parameterNames=(),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="default",
    )
    bound, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    if expected_reason is None:
        row = next(p for p in bound if p["parameterName"] == param_name)
        assert row["stateType"] == expected_state_type
    else:
        row = next(e for e in excluded if e["parameterName"] == param_name)
        assert row["reason"] == expected_reason


def test_constant_param_kind_excluded_as_non_variable_kind():
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="geometry-required",
        parameterNames=(),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="default",
    )
    _, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    label_entry = next(e for e in excluded if e["parameterName"] == "Label")
    assert label_entry["reason"] == "non-variable-kind"


def test_float_with_null_domain_max_excluded_as_missing_domain():
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="geometry-required",
        parameterNames=(),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="default",
    )
    _, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    no_domain_entry = next(e for e in excluded if e["parameterName"] == "NoDomain")
    assert no_domain_entry["reason"] == "missing-domain"


def test_boolean_with_null_domain_is_bound_not_excluded():
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="geometry-required",
        parameterNames=(),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="default",
    )
    bound, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    assert "IsCorner" in {p["parameterName"] for p in bound}
    assert "IsCorner" not in {e["parameterName"] for e in excluded}


def test_missing_reinstate_id_excluded_as_unresolved_reinstate_id():
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="geometry-required",
        parameterNames=(),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="default",
    )
    _, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    unresolved_entry = next(e for e in excluded if e["parameterName"] == "Unresolved")
    assert unresolved_entry["reason"] == "unresolved-reinstate-id"


def test_bound_and_excluded_lists_sorted_by_parameter_name():
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="geometry-required",
        parameterNames=(),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="default",
    )
    bound, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    assert [p["parameterName"] for p in bound] == sorted(p["parameterName"] for p in bound)
    assert [e["parameterName"] for e in excluded] == sorted(e["parameterName"] for e in excluded)


def test_select_parameters_restricts_to_named_parameters_when_bound():
    classification = bindings_module.RuleClassification(
        ruleId="r",
        determinability="direct-parameter",
        parameterNames=("HTotal",),
        metricExpression=None,
        monotoneIn=(),
        limit=None,
        source="binding",
    )
    bound, excluded = bindings_module.select_parameters(classification, published_parameter_rows())
    assert [p["parameterName"] for p in bound] == ["HTotal"]
    assert excluded == []
