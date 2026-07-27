"""Two-tier test suite for cg_structure_checks.py (Phase 37 Plan 03: SVAL-01).

Unit tier (`-k convention`): pure-Python coverage of parse_context_warnings,
convention_name_from_cg_id, _finding/_entity's normative key shapes, and
check_annotation_conventions against a minimal session double. No Neo4j, no
container -- this is the per-commit gate.

Integration tier (`-k structural`, `integration` marker): publishes the
Frame envelope and its two mutated variants (cg_fixtures.py, Phase 37 Plan
01) into live Neo4j, then proves every graph-pattern check, the SC1
exact-procedure naming, determinism, and project/definitionId scoping.
Requires the compose network -- the `neo4j` hostname only resolves there
(same constraint test_dg_context.py's Neo4j-dependent tests already
document). Run via:

    docker compose exec data-service python -m pytest tests/test_cg_structure_checks.py -k structural -q
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import app as app_module  # noqa: E402
import cg_structure_checks as checks  # noqa: E402
import computgraph_publish  # noqa: E402
from cg_fixtures import (  # noqa: E402
    FIXTURE_PROJECT,
    FRAME_DEFINITION_ID,
    FRAME_NO_FOOTER_DEFINITION_ID,
    FRAME_NO_INTERFACE_DEFINITION_ID,
    PARAM_HTOTAL_CG_ID,
    PROC_11_CG_ID,
    PROC_11_NAME,
    PROC_12_NAME,
    frame_cg_context,
    frame_with_normalization_warnings,
    frame_without_footer_procedure,
    frame_without_interface,
)

client = TestClient(app_module.app, raise_server_exceptions=False)


# ── Unit tier (no Neo4j, no container) -- select with `-k convention` ──


def test_convention_name_from_cg_id_extracts_last_segment_for_parameter():
    assert checks.convention_name_from_cg_id(PARAM_HTOTAL_CG_ID) == "11_Var_HTotal"


def test_convention_name_from_cg_id_extracts_last_segment_for_procedure():
    assert checks.convention_name_from_cg_id(PROC_11_CG_ID) == "11"


def test_convention_name_from_cg_id_empty_input_returns_empty_string():
    assert checks.convention_name_from_cg_id("") == ""


def test_convention_finding_and_entity_have_normative_key_sets():
    """Matches spec/API.md's `entities[]` item shape
    ({label, cgId, name, conventionName}) and `findings[]` item shape
    ({checkId, severity, message, entities})."""
    entity = checks._entity("Procedure", PROC_11_CG_ID, PROC_11_NAME)
    assert set(entity) == {"label", "cgId", "name", "conventionName"}
    assert entity["conventionName"] == "11"

    finding = checks._finding(
        "procedure_without_interface",
        checks.SEVERITY_VIOLATION,
        "Procedure has no Interface.",
        "Procedure cgId=cg:1:proc:11",
        "tag at least one IntF_ group and re-publish.",
        [entity],
    )
    assert set(finding) == {"checkId", "severity", "message", "entities"}
    assert finding["message"] == (
        "Procedure has no Interface. Where: Procedure cgId=cg:1:proc:11. "
        "How to fix: tag at least one IntF_ group and re-publish."
    )


def test_convention_parse_context_warnings_none_returns_empty():
    assert checks.parse_context_warnings(None) == []


def test_convention_parse_context_warnings_empty_string_returns_empty():
    assert checks.parse_context_warnings("") == []


def test_convention_parse_context_warnings_invalid_json_returns_empty():
    assert checks.parse_context_warnings("{oops") == []


def test_convention_parse_context_warnings_non_dict_json_returns_empty():
    assert checks.parse_context_warnings("[]") == []


def test_convention_parse_context_warnings_missing_key_returns_empty():
    assert checks.parse_context_warnings(json.dumps({"a": 1})) == []


def test_convention_parse_context_warnings_not_a_list_returns_empty():
    assert checks.parse_context_warnings(json.dumps({"warnings": "x"})) == []


def test_convention_parse_context_warnings_filters_non_string_members():
    payload = json.dumps({"warnings": ["a", 2, "b"]})
    assert checks.parse_context_warnings(payload) == ["a", "b"]


def test_convention_parse_context_warnings_happy_path_preserves_order():
    payload = json.dumps({"warnings": ["first warning", "second warning"]})
    assert checks.parse_context_warnings(payload) == ["first warning", "second warning"]


def _algorithm_row(envelope: dict, alg_index: int = 1, alg_name: str = "1_ALGORITHM") -> dict:
    """Build a canned Algorithm row the way computgraph_publish.py actually
    writes contextJson: the full envelope minus `untagged`, JSON-dumped."""
    storage_ctx = {k: v for k, v in envelope.items() if k != "untagged"}
    return {
        "algIndex": alg_index,
        "algorithmName": alg_name,
        "contextJson": json.dumps(storage_ctx, sort_keys=True),
    }


class _CannedAlgorithmSession:
    """Minimal session double for check_annotation_conventions. The check
    makes exactly one read call, so a small object exposing `run` and
    returning a canned row list is sufficient and honest -- not the
    write-oriented FakeGraph harness (that mirrors computgraph_publish.py's
    MERGE writes, which this check never issues)."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def run(self, query: str, params: dict) -> list[dict]:
        del query, params
        return list(self._rows)


def test_convention_check_annotation_conventions_fires_one_finding_per_warning():
    envelope = frame_with_normalization_warnings()
    session = _CannedAlgorithmSession([_algorithm_row(envelope)])

    findings = checks.check_annotation_conventions(session, FIXTURE_PROJECT, FRAME_DEFINITION_ID)

    assert len(findings) == len(envelope["warnings"])
    for finding in findings:
        assert finding["checkId"] == "annotation_convention"
        assert finding["severity"] == checks.SEVERITY_INFO
    assert [f["message"].split(" Where:")[0] for f in findings] == sorted(envelope["warnings"])


def test_convention_check_annotation_conventions_zero_findings_when_warnings_empty():
    envelope = frame_cg_context()
    assert envelope["warnings"] == []
    session = _CannedAlgorithmSession([_algorithm_row(envelope)])

    findings = checks.check_annotation_conventions(session, FIXTURE_PROJECT, FRAME_DEFINITION_ID)

    assert findings == []


# ── Structure-rule mapping unit tier (no Neo4j) -- select with `-k structure_rules` ──
#
# Named to match neither `-k convention` nor `-k rule_mapped` so these run in
# both invocations of the full suite but not inside either narrow selection.


def test_structure_rules_missing_file_yields_empty_envelope(tmp_path, monkeypatch):
    monkeypatch.setattr(checks, "STRUCTURE_RULES_FILE", tmp_path / "does-not-exist.json")
    assert checks.load_structure_rules() == {"version": 0, "mappings": []}


def test_structure_rules_invalid_json_yields_empty_envelope(tmp_path, monkeypatch):
    path = tmp_path / "structure_rules.json"
    path.write_text("{oops", encoding="utf-8")
    monkeypatch.setattr(checks, "STRUCTURE_RULES_FILE", path)
    assert checks.load_structure_rules() == {"version": 0, "mappings": []}


def test_structure_rules_top_level_list_yields_empty_envelope(tmp_path, monkeypatch):
    path = tmp_path / "structure_rules.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    monkeypatch.setattr(checks, "STRUCTURE_RULES_FILE", path)
    assert checks.load_structure_rules() == {"version": 0, "mappings": []}


def test_structure_rules_mappings_not_a_list_yields_empty_envelope(tmp_path, monkeypatch):
    path = tmp_path / "structure_rules.json"
    path.write_text(json.dumps({"version": 1, "mappings": "oops"}), encoding="utf-8")
    monkeypatch.setattr(checks, "STRUCTURE_RULES_FILE", path)
    assert checks.load_structure_rules() == {"version": 0, "mappings": []}


def test_structure_rules_real_shipped_file_has_four_valid_mappings():
    payload = checks.load_structure_rules()
    assert payload["version"] == 1
    assert len(payload["mappings"]) == 4
    assert len(checks.valid_structure_mappings(payload)) == 4


@pytest.mark.parametrize("forbidden_key", sorted(checks._FORBIDDEN_PARAM_KEYS))
def test_structure_rules_forbidden_param_key_is_rejected(forbidden_key):
    payload = {
        "version": 1,
        "mappings": [
            {
                "ruleId": "R_STRUCT_TEST_V",
                "operation": "requiresParameter",
                "params": {forbidden_key: 3},
            }
        ],
    }
    assert checks.valid_structure_mappings(payload) == []


def test_structure_rules_unknown_operation_is_rejected():
    payload = {
        "version": 1,
        "mappings": [{"ruleId": "R_STRUCT_TEST_V", "operation": "requiresMagic", "params": {}}],
    }
    assert checks.valid_structure_mappings(payload) == []


def test_structure_rules_empty_rule_id_is_rejected():
    payload = {
        "version": 1,
        "mappings": [{"ruleId": "", "operation": "requiresProcedure", "params": {}}],
    }
    assert checks.valid_structure_mappings(payload) == []


def test_structure_rules_params_as_string_is_rejected():
    payload = {
        "version": 1,
        "mappings": [{"ruleId": "R_STRUCT_TEST_V", "operation": "requiresProcedure", "params": "oops"}],
    }
    assert checks.valid_structure_mappings(payload) == []


def test_structure_rules_forbids_orphan_label_outside_allowlist_is_rejected():
    payload = {
        "version": 1,
        "mappings": [
            {"ruleId": "R_STRUCT_TEST_V", "operation": "forbidsOrphan", "params": {"label": "Rule"}}
        ],
    }
    assert checks.valid_structure_mappings(payload) == []


# ── Report contract tests (no Neo4j) -- select with `-k report_contract` ──
#
# Route-shape and error-mapping coverage for POST /computgraph/validate,
# using a canned checks.build_validation_report() result monkeypatched onto
# the shared cg_structure_checks module -- app.py calls
# `cg_structure_checks.build_validation_report(...)` by attribute lookup at
# request time, so patching the attribute here is visible through the route.


class _DummySession:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _DummyDriver:
    """Stands in for the real Neo4j driver when the route body is fully
    monkeypatched -- session open/close must succeed but nothing reads it."""

    def session(self):
        return _DummySession()


class _ExplodingDriver:
    """Raises if .session() is ever called -- proves request validation
    rejects a malformed body before any session is opened."""

    def session(self):
        raise AssertionError("session should not be opened for an invalid request body")


def _canned_finding() -> dict:
    return {
        "checkId": "procedure_without_interface",
        "severity": "violation",
        "message": (
            "Procedure '2D Truss Configuration' has no Interface. "
            "Where: Procedure cgId=cg:1:proc:11. How to fix: tag at least one "
            "IntF_ group under this Procedure and re-publish."
        ),
        "entities": [
            {"label": "Procedure", "cgId": "cg:1:proc:11", "name": "2D Truss Configuration", "conventionName": "11"}
        ],
    }


def _canned_rule_result() -> dict:
    return {
        "ruleId": "R_STRUCT_FRAME_FOOTER_V",
        "operation": "requiresProcedure",
        "passed": True,
        "ruleExists": False,
        "message": "A Procedure matching 'Footer' was found. Where: ... How to fix: no action needed.",
        "satisfyingEntities": [
            {"label": "Procedure", "cgId": "cg:1:proc:12", "name": "2D Footer Configuration", "conventionName": "12"}
        ],
        "offendingEntities": [],
    }


def _canned_report(project: str = "p1", definition_id: str = "frame.gh") -> dict:
    return {
        "project": project,
        "definitionId": definition_id,
        "publishedAt": "2026-07-08T00:00:00+00:00",
        "checkedAt": "2026-07-27T12:00:00+00:00",
        "findings": [_canned_finding()],
        "ruleResults": [_canned_rule_result()],
        "counts": {"violation": 1, "warning": 0, "info": 0},
    }


def test_report_contract_well_formed_request_returns_200_with_exact_top_level_keys(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())
    monkeypatch.setattr(checks, "build_validation_report", lambda *a, **k: _canned_report())

    response = client.post("/computgraph/validate", json={"project": "p1", "definitionId": "frame.gh"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "project",
        "definitionId",
        "publishedAt",
        "checkedAt",
        "findings",
        "ruleResults",
        "counts",
    }


def test_report_contract_findings_and_entity_key_sets_are_exact(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())
    monkeypatch.setattr(checks, "build_validation_report", lambda *a, **k: _canned_report())

    body = client.post("/computgraph/validate", json={"project": "p1"}).json()

    for finding in body["findings"]:
        assert set(finding) == {"checkId", "severity", "message", "entities"}
        for entity in finding["entities"]:
            assert set(entity) == {"label", "cgId", "name", "conventionName"}


def test_report_contract_rule_results_entry_key_set_is_exact(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())
    monkeypatch.setattr(checks, "build_validation_report", lambda *a, **k: _canned_report())

    body = client.post("/computgraph/validate", json={"project": "p1"}).json()

    for rule_result in body["ruleResults"]:
        assert set(rule_result) == {
            "ruleId",
            "operation",
            "passed",
            "ruleExists",
            "message",
            "satisfyingEntities",
            "offendingEntities",
        }


def test_report_contract_counts_always_carries_all_three_severity_keys(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())
    report = _canned_report()
    report["counts"] = {"violation": 0, "warning": 0, "info": 0}
    monkeypatch.setattr(checks, "build_validation_report", lambda *a, **k: report)

    body = client.post("/computgraph/validate", json={"project": "p1"}).json()

    assert set(body["counts"]) == {"violation", "warning", "info"}
    assert body["counts"] == {"violation": 0, "warning": 0, "info": 0}


def test_report_contract_ambiguous_definition_error_returns_422_with_hint_listing_available_ids(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())

    def _raise(*args, **kwargs):
        raise checks.DefinitionResolutionError(
            "Multiple published definitions found for project 'p1'; specify definitionId.",
            "COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION",
            ["a.gh", "b.gh", "c.gh"],
        )

    monkeypatch.setattr(checks, "build_validation_report", _raise)

    response = client.post("/computgraph/validate", json={"project": "p1"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert set(detail) == {"error", "hint", "code"}
    assert detail["code"] == "COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION"
    for definition_id in ("a.gh", "b.gh", "c.gh"):
        assert definition_id in detail["hint"]


def test_report_contract_no_definition_error_returns_422_with_documented_code(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())

    def _raise(*args, **kwargs):
        raise checks.DefinitionResolutionError(
            "No published definition found for project 'p1'.",
            "COMPUTGRAPH_VALIDATE_NO_DEFINITION",
            [],
        )

    monkeypatch.setattr(checks, "build_validation_report", _raise)

    response = client.post("/computgraph/validate", json={"project": "p1"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert set(detail) == {"error", "hint", "code"}
    assert detail["code"] == "COMPUTGRAPH_VALIDATE_NO_DEFINITION"


def test_report_contract_unexpected_exception_returns_502_with_failed_code(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _DummyDriver())

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(checks, "build_validation_report", _raise)

    response = client.post("/computgraph/validate", json={"project": "p1"})

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert set(detail) == {"error", "hint", "code"}
    assert detail["code"] == "COMPUTGRAPH_VALIDATE_FAILED"


def test_report_contract_missing_project_rejected_before_session_opened(monkeypatch):
    monkeypatch.setattr(app_module, "driver", _ExplodingDriver())

    response = client.post("/computgraph/validate", json={"definitionId": "frame.gh"})

    # 422 here is FastAPI's own request-body validation -- if the route had
    # instead opened a session, _ExplodingDriver's AssertionError would have
    # been caught by the route's `except Exception` and mapped to 502.
    assert response.status_code == 422


def test_report_contract_sc4_module_source_has_no_gateway_identifiers():
    """Same grep the phase gate uses (grep -v '^\\s*#' | grep
    'llm_gateway\\|adapter\\.generate'), pinned inside the suite so the
    guarantee survives a refactor, not only a shell command."""
    checks_path = os.path.join(os.path.dirname(__file__), "..", "cg_structure_checks.py")
    with open(checks_path, encoding="utf-8") as handle:
        non_comment_lines = [line for line in handle if not line.strip().startswith("#")]
    source = "".join(non_comment_lines)
    assert "llm_gateway" not in source
    assert "adapter.generate" not in source


# ── Integration tier (live Neo4j, compose network) -- select with `-k structural` ──


@pytest.fixture(scope="session")
def published_frame():
    """Opens a real driver session and publishes all three envelope variants
    (full Frame, interface-stripped, footer-less) under FIXTURE_PROJECT,
    idempotently -- every node scoped to FIXTURE_PROJECT is deleted first so
    reruns never accumulate stale data. Torn down the same way."""
    with app_module.driver.session() as session:
        session.run(
            "MATCH (n {project: $project, graph: 'Computgraph'}) DETACH DELETE n",
            {"project": FIXTURE_PROJECT},
        )
        computgraph_publish.publish_structure(session, FIXTURE_PROJECT, frame_cg_context())
        computgraph_publish.publish_structure(session, FIXTURE_PROJECT, frame_without_interface())
        computgraph_publish.publish_structure(session, FIXTURE_PROJECT, frame_without_footer_procedure())
        yield session
        session.run(
            "MATCH (n {project: $project, graph: 'Computgraph'}) DETACH DELETE n",
            {"project": FIXTURE_PROJECT},
        )


class TestStructuralChecksIntegration:
    """Requires the compose network (see module docstring)."""

    pytestmark = pytest.mark.integration

    def test_structural_full_frame_has_zero_violation_findings(self, published_frame):
        """The well-formed baseline -- if this doesn't hold, one of the
        checks has a false positive and every downstream assertion here is
        worthless."""
        findings = checks.run_structural_checks(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        violations = [f for f in findings if f["severity"] == checks.SEVERITY_VIOLATION]
        assert violations == []

    def test_structural_interface_stripped_variant_flags_exact_procedure(self, published_frame):
        findings = checks.run_structural_checks(
            published_frame, FIXTURE_PROJECT, FRAME_NO_INTERFACE_DEFINITION_ID
        )
        matches = [f for f in findings if f["checkId"] == "procedure_without_interface"]
        assert len(matches) == 1
        entities = matches[0]["entities"]
        assert len(entities) == 1
        # SC1: the exact procedure must be identifiable by both name and cgId.
        assert entities[0]["name"] == PROC_11_NAME
        assert entities[0]["cgId"] == PROC_11_CG_ID

    def test_structural_defensive_checks_are_wired_and_non_firing(self, published_frame):
        for definition_id in (
            FRAME_DEFINITION_ID,
            FRAME_NO_INTERFACE_DEFINITION_ID,
            FRAME_NO_FOOTER_DEFINITION_ID,
        ):
            assert checks.check_parameters_without_datatype(published_frame, FIXTURE_PROJECT, definition_id) == []
            assert checks.check_objects_without_behavior(published_frame, FIXTURE_PROJECT, definition_id) == []

    def test_structural_determinism_repeated_calls_are_byte_identical(self, published_frame):
        first = checks.run_structural_checks(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        second = checks.run_structural_checks(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        assert first == second

    def test_structural_project_isolation_returns_empty_for_unknown_project(self, published_frame):
        findings = checks.run_structural_checks(published_frame, "p37-structure-unused", FRAME_DEFINITION_ID)
        assert findings == []

    def test_structural_footer_less_publish_does_not_change_full_frame_findings(self, published_frame):
        """Proves the definitionId scope separates the two definitions
        inside one project: re-publishing the footer-less variant must not
        bleed into the full Frame's definitionId-scoped findings."""
        before = checks.run_structural_checks(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        computgraph_publish.publish_structure(
            published_frame, FIXTURE_PROJECT, frame_without_footer_procedure()
        )
        after = checks.run_structural_checks(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        assert before == after


# ── Rule-mapped checks integration tier (live Neo4j) -- select with `-k rule_mapped` ──


class TestRuleMappedChecksIntegration:
    """Requires the compose network (see module docstring). Reuses the same
    `published_frame` session fixture as the structural-checks tier."""

    pytestmark = pytest.mark.integration

    def test_rule_mapped_footer_rule_passes_on_full_frame(self, published_frame):
        results = checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        footer = next(r for r in results if r["ruleId"] == "R_STRUCT_FRAME_FOOTER_V")
        assert footer["passed"] is True
        satisfying_names = [e["name"] for e in footer["satisfyingEntities"]]
        assert PROC_12_NAME in satisfying_names

    def test_rule_mapped_footer_rule_fails_on_footer_less_copy(self, published_frame):
        results = checks.evaluate_rule_mappings(
            published_frame, FIXTURE_PROJECT, FRAME_NO_FOOTER_DEFINITION_ID
        )
        footer = next(r for r in results if r["ruleId"] == "R_STRUCT_FRAME_FOOTER_V")
        assert footer["passed"] is False
        assert footer["offendingEntities"] != []

    def test_rule_mapped_footer_pass_fail_pair_differs_only_in_passed(self, published_frame):
        full = next(
            r
            for r in checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
            if r["ruleId"] == "R_STRUCT_FRAME_FOOTER_V"
        )
        footer_less = next(
            r
            for r in checks.evaluate_rule_mappings(
                published_frame, FIXTURE_PROJECT, FRAME_NO_FOOTER_DEFINITION_ID
            )
            if r["ruleId"] == "R_STRUCT_FRAME_FOOTER_V"
        )
        assert full["ruleId"] == footer_less["ruleId"]
        assert full["operation"] == footer_less["operation"]
        assert full["passed"] is True
        assert footer_less["passed"] is False

    def test_rule_mapped_height_parameter_rule_passes_via_cg_id_suffix_match(self, published_frame):
        results = checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        height = next(r for r in results if r["ruleId"] == "R_STRUCT_FRAME_HEIGHT_VAR_V")
        assert height["passed"] is True
        matching = next(
            (e for e in height["satisfyingEntities"] if e["cgId"] == PARAM_HTOTAL_CG_ID), None
        )
        assert matching is not None
        assert matching["conventionName"].endswith("HTotal")

    def test_rule_mapped_interface_rule_fails_on_interface_stripped_and_passes_on_full_frame(
        self, published_frame
    ):
        stripped = next(
            r
            for r in checks.evaluate_rule_mappings(
                published_frame, FIXTURE_PROJECT, FRAME_NO_INTERFACE_DEFINITION_ID
            )
            if r["ruleId"] == "R_STRUCT_PROC_INTERFACE_V"
        )
        assert stripped["passed"] is False
        offending_names = [e["name"] for e in stripped["offendingEntities"]]
        assert PROC_11_NAME in offending_names

        full = next(
            r
            for r in checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
            if r["ruleId"] == "R_STRUCT_PROC_INTERFACE_V"
        )
        assert full["passed"] is True

    def test_rule_mapped_rule_exists_false_for_all_seeded_rules_with_real_verdicts(self, published_frame):
        results = checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        assert len(results) == 4
        for result in results:
            assert result["ruleExists"] is False
            assert isinstance(result["passed"], bool)

    def test_rule_mapped_determinism_repeated_calls_are_byte_identical(self, published_frame):
        first = checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        second = checks.evaluate_rule_mappings(published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID)
        assert first == second

    def test_rule_mapped_project_isolation_returns_no_fixture_entities(self, published_frame):
        results = checks.evaluate_rule_mappings(
            published_frame, "p37-structure-unused", FRAME_DEFINITION_ID
        )
        exists_style_operations = {"requiresProcedure", "requiresParameter"}
        for result in results:
            if result["operation"] in exists_style_operations:
                assert result["passed"] is False
                assert result["satisfyingEntities"] == []
            all_entities = result["satisfyingEntities"] + result["offendingEntities"]
            all_names = [e["name"] for e in all_entities]
            assert PROC_11_NAME not in all_names
            assert PROC_12_NAME not in all_names


# ── Report surface, route-level integration tier (live Neo4j) -- `-k structural` ──
#
# Reuses the same `published_frame` session fixture (FIXTURE_PROJECT carries
# three published definitions -- frame.gh / frame-no-interface.gh /
# frame-no-footer.gh -- exactly the "three published definitions" the
# omitted-definitionId ambiguous-resolution test needs).

SINGLE_DEFINITION_PROJECT = "p37-structure-single"


@pytest.fixture(scope="session")
def published_single_definition_project():
    """A second, isolated project carrying exactly one published definition
    -- the counterpart fixture the omitted-definitionId single-resolution
    test needs (FIXTURE_PROJECT always carries three)."""
    with app_module.driver.session() as session:
        session.run(
            "MATCH (n {project: $project, graph: 'Computgraph'}) DETACH DELETE n",
            {"project": SINGLE_DEFINITION_PROJECT},
        )
        computgraph_publish.publish_structure(
            session, SINGLE_DEFINITION_PROJECT, frame_cg_context(project=SINGLE_DEFINITION_PROJECT)
        )
        yield session
        session.run(
            "MATCH (n {project: $project, graph: 'Computgraph'}) DETACH DELETE n",
            {"project": SINGLE_DEFINITION_PROJECT},
        )


class TestValidateRouteIntegration:
    """Requires the compose network (see module docstring)."""

    pytestmark = pytest.mark.integration

    def test_structural_full_frame_route_returns_200_with_publishedat_and_zero_violations(
        self, published_frame
    ):
        expected_published_at = checks.fetch_published_at(
            published_frame, FIXTURE_PROJECT, FRAME_DEFINITION_ID
        )
        response = client.post(
            "/computgraph/validate", json={"project": FIXTURE_PROJECT, "definitionId": FRAME_DEFINITION_ID}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["publishedAt"] is not None
        assert body["publishedAt"] == expected_published_at
        violations = [f for f in body["findings"] if f["severity"] == checks.SEVERITY_VIOLATION]
        assert violations == []

    def test_structural_interface_stripped_route_flags_truss_procedure_by_name_and_cgid(
        self, published_frame
    ):
        response = client.post(
            "/computgraph/validate",
            json={"project": FIXTURE_PROJECT, "definitionId": FRAME_NO_INTERFACE_DEFINITION_ID},
        )
        assert response.status_code == 200
        matches = [
            f for f in response.json()["findings"] if f["checkId"] == "procedure_without_interface"
        ]
        assert len(matches) == 1
        entities = matches[0]["entities"]
        assert len(entities) == 1
        assert entities[0]["name"] == PROC_11_NAME
        assert entities[0]["cgId"] == PROC_11_CG_ID

    def test_structural_footer_less_route_rule_result_fails_while_full_frame_passes(
        self, published_frame
    ):
        full = client.post(
            "/computgraph/validate", json={"project": FIXTURE_PROJECT, "definitionId": FRAME_DEFINITION_ID}
        ).json()
        footer_less = client.post(
            "/computgraph/validate",
            json={"project": FIXTURE_PROJECT, "definitionId": FRAME_NO_FOOTER_DEFINITION_ID},
        ).json()
        full_footer = next(r for r in full["ruleResults"] if r["ruleId"] == "R_STRUCT_FRAME_FOOTER_V")
        footer_less_footer = next(
            r for r in footer_less["ruleResults"] if r["ruleId"] == "R_STRUCT_FRAME_FOOTER_V"
        )
        assert full_footer["passed"] is True
        assert footer_less_footer["passed"] is False

    def test_structural_route_determinism_two_calls_differ_only_in_checked_at(self, published_frame):
        first = client.post(
            "/computgraph/validate", json={"project": FIXTURE_PROJECT, "definitionId": FRAME_DEFINITION_ID}
        ).json()
        second = client.post(
            "/computgraph/validate", json={"project": FIXTURE_PROJECT, "definitionId": FRAME_DEFINITION_ID}
        ).json()

        for body in (first, second):
            assert "checkedAt" in body
            # Raises if not a parseable ISO 8601 timestamp.
            datetime.fromisoformat(body["checkedAt"].replace("Z", "+00:00"))

        del first["checkedAt"]
        del second["checkedAt"]
        assert first == second

    def test_structural_omit_definition_id_ambiguous_for_three_published_definitions(
        self, published_frame
    ):
        response = client.post("/computgraph/validate", json={"project": FIXTURE_PROJECT})
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["code"] == "COMPUTGRAPH_VALIDATE_AMBIGUOUS_DEFINITION"
        for definition_id in (
            FRAME_DEFINITION_ID,
            FRAME_NO_INTERFACE_DEFINITION_ID,
            FRAME_NO_FOOTER_DEFINITION_ID,
        ):
            assert definition_id in detail["hint"]

    def test_structural_omit_definition_id_resolves_for_single_published_definition(
        self, published_single_definition_project
    ):
        response = client.post("/computgraph/validate", json={"project": SINGLE_DEFINITION_PROJECT})
        assert response.status_code == 200
        assert response.json()["definitionId"] == FRAME_DEFINITION_ID
