"""Tests for evidence_contract.py (Phase 1200 Plan 03, ALGN12-01/ALGN12-02)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jsonschema
import pytest

from evidence_contract import (
    EVIDENCE_CONTRACT_VERSION,
    CanonicalStatus,
    EvidenceEnvelope,
    EvidenceRow,
    build_envelope,
    load_contract_schema,
    to_legacy_boolean,
    validate_envelope,
)

from app import (
    _build_publish_evidence_envelope,
    parse_evidence_envelope,
    persist_evidence_envelope,
)


def _sample_rows() -> list[EvidenceRow]:
    return [
        EvidenceRow(ruleId="R_B", objectId="OBJ_2", canonicalStatus=CanonicalStatus.PASSED),
        EvidenceRow(ruleId="R_A", objectId="OBJ_1", canonicalStatus=CanonicalStatus.FAILED),
        EvidenceRow(ruleId="R_A", objectId="OBJ_2", canonicalStatus=CanonicalStatus.PASSED),
    ]


# --- Vocabulary drift guard ---


def test_canonical_status_matches_schema_enum_exactly():
    schema = load_contract_schema()
    schema_enum = set(schema["$defs"]["CanonicalStatus"]["enum"])
    python_enum = {s.value for s in CanonicalStatus}
    assert python_enum == schema_enum


def test_canonical_status_has_exactly_eight_members():
    assert len(list(CanonicalStatus)) == 8


def test_no_population_serializes_as_snake_case():
    assert CanonicalStatus.NO_POPULATION.value == "no_population"


# --- Envelope construction and ordering ---


def test_build_envelope_returns_valid_shape():
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=_sample_rows(),
    )
    assert isinstance(envelope, EvidenceEnvelope)
    assert envelope.contractVersion == EVIDENCE_CONTRACT_VERSION
    validate_envelope(envelope)  # must not raise


def test_build_envelope_sorts_rows_by_objectid_then_ruleid():
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=_sample_rows(),
    )
    keys = [(row.objectId, row.ruleId) for row in envelope.rows]
    assert keys == sorted(keys)
    assert keys == [("OBJ_1", "R_A"), ("OBJ_2", "R_A"), ("OBJ_2", "R_B")]


def test_build_envelope_rollup_precedence_error_beats_everything():
    rows = [
        EvidenceRow(ruleId="R_A", objectId="OBJ_1", canonicalStatus=CanonicalStatus.PASSED),
        EvidenceRow(ruleId="R_A", objectId="OBJ_2", canonicalStatus=CanonicalStatus.ERROR),
        EvidenceRow(ruleId="R_A", objectId="OBJ_3", canonicalStatus=CanonicalStatus.FAILED),
    ]
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=rows,
    )
    assert envelope.canonicalStatus == CanonicalStatus.ERROR


def test_build_envelope_rollup_all_passed():
    rows = [
        EvidenceRow(ruleId="R_A", objectId="OBJ_1", canonicalStatus=CanonicalStatus.PASSED),
        EvidenceRow(ruleId="R_A", objectId="OBJ_2", canonicalStatus=CanonicalStatus.PASSED),
    ]
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=rows,
    )
    assert envelope.canonicalStatus == CanonicalStatus.PASSED


def test_build_envelope_accepts_explicit_rollup_override():
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=[EvidenceRow(ruleId="R_A", objectId="OBJ_1", canonicalStatus=CanonicalStatus.PASSED)],
        roll_up=CanonicalStatus.UNKNOWN,
    )
    assert envelope.canonicalStatus == CanonicalStatus.UNKNOWN


def test_build_envelope_emitted_at_is_rfc3339_utc_z_suffix():
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=[],
    )
    assert envelope.emittedAt.endswith("Z")


# --- Schema validation enforcement ---


def test_validate_envelope_missing_required_field_raises():
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=[],
    )
    payload = envelope.model_dump(mode="json", exclude_none=True)
    del payload["contractVersion"]
    schema = load_contract_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)


def test_validate_envelope_extra_field_raises():
    envelope = build_envelope(
        project="TEST_PROJECT",
        definition_id="def-01",
        service_name="data-service",
        service_version="1.0.0",
        stage="publish",
        rows=[],
    )
    payload = envelope.model_dump(mode="json", exclude_none=True)
    payload["unexpectedExtraField"] = "should not be allowed"
    schema = load_contract_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)


def test_evidence_envelope_model_forbids_extra_fields():
    with pytest.raises(Exception):
        EvidenceEnvelope(
            contractVersion="1.0.0",
            canonicalizationVersion=1,
            project="TEST_PROJECT",
            definitionId="def-01",
            serviceName="data-service",
            serviceVersion="1.0.0",
            emittedAt="2026-09-20T00:00:00Z",
            stage="publish",
            canonicalStatus=CanonicalStatus.PASSED,
            rows=[],
            unexpectedField="nope",
        )


# --- Legacy boolean direction (D-04) ---


def test_to_legacy_boolean_only_passed_is_true():
    for status in CanonicalStatus:
        expected = status == CanonicalStatus.PASSED
        assert to_legacy_boolean(status) is expected


def test_no_boolean_to_canonical_inference_function_exists():
    """Grep-verifiable acceptance criterion: no from_legacy/from_boolean function,
    and no function with a bool argument returning CanonicalStatus."""
    import re
    from pathlib import Path

    module_path = Path(__file__).resolve().parent.parent / "evidence_contract.py"
    source = module_path.read_text(encoding="utf-8")
    pattern = re.compile(r"def .*bool.*-> CanonicalStatus|from_legacy|from_boolean")
    assert not pattern.search(source)


# --- app.py additive sidecar: persist_evidence_envelope / parse_evidence_envelope ---


class TestPersistEvidenceEnvelope:
    def test_persist_uses_parameterized_query_with_all_four_keys(self, monkeypatch):
        import app as app_module

        captured = {}

        def fake_write_query(query, parameters=None):
            captured["query"] = query
            captured["parameters"] = parameters

        monkeypatch.setattr(app_module, "write_query", fake_write_query)

        envelope_json = json.dumps({"contractVersion": "1.0.0"})
        persist_evidence_envelope("proj-a", "run-1", envelope_json)

        assert "$evidenceEnvelopeJson" in captured["query"]
        assert "$project" in captured["query"]
        assert "$runId" in captured["query"]
        assert "proj-a" not in captured["query"]  # never string-interpolated
        assert "run-1" not in captured["query"]
        assert set(captured["parameters"].keys()) == {"graph", "project", "runId", "evidenceEnvelopeJson"}
        assert captured["parameters"] == {
            "graph": app_module.VALIDATION_GRAPH,
            "project": "proj-a",
            "runId": "run-1",
            "evidenceEnvelopeJson": envelope_json,
        }

    def test_persist_touches_only_evidenceenvelopejson(self):
        """git diff / grep-verifiable acceptance criterion: the write body only sets
        evidenceEnvelopeJson -- no ValidStatus/SendStatus/statePayloadJson/shaclReportJson
        appears in this function's query text."""
        from pathlib import Path

        module_path = Path(__file__).resolve().parent.parent / "app.py"
        source = module_path.read_text(encoding="utf-8")
        # Isolate the function body between its def line and the next top-level def.
        start = source.index("def persist_evidence_envelope(")
        end = source.index("\ndef ", start + 1)
        body = source[start:end]
        assert "ValidStatus" not in body
        assert "SendStatus" not in body
        assert "statePayloadJson" not in body
        assert "shaclReportJson" not in body
        assert "SET run.evidenceEnvelopeJson = $evidenceEnvelopeJson" in body


class TestParseEvidenceEnvelope:
    def test_returns_none_for_none_empty_malformed_and_array(self):
        assert parse_evidence_envelope(None) is None
        assert parse_evidence_envelope("") is None
        assert parse_evidence_envelope("not json") is None
        assert parse_evidence_envelope("[1,2]") is None

    def test_returns_parsed_dict_for_well_formed_envelope_json(self):
        envelope_json = json.dumps({"contractVersion": "1.0.0", "canonicalStatus": "passed"})
        result = parse_evidence_envelope(envelope_json)
        assert result == {"contractVersion": "1.0.0", "canonicalStatus": "passed"}

    def test_never_raises_on_garbage_input(self):
        for garbage in ["{", "}", "{not:json}", "\x00\x01", "[" * 1000]:
            try:
                parse_evidence_envelope(garbage)
            except Exception as e:
                pytest.fail(f"parse_evidence_envelope raised on input {garbage!r}: {e}")


class TestBuildPublishEvidenceEnvelope:
    def test_failed_and_passed_rule_ids_map_to_genuine_statuses(self):
        entity_dicts = [
            {
                "dgEntityId": "OBJ_1",
                "ruleIds": ["R_A", "R_B"],
                "failedRuleIds": ["R_A"],
                "passedRuleIds": ["R_B"],
            }
        ]
        envelope = _build_publish_evidence_envelope("proj-a", "run-1", entity_dicts)
        by_rule = {row.ruleId: row for row in envelope.rows}
        assert by_rule["R_A"].canonicalStatus == CanonicalStatus.FAILED
        assert by_rule["R_B"].canonicalStatus == CanonicalStatus.PASSED
        assert by_rule["R_A"].warnings == []
        assert by_rule["R_B"].warnings == []

    def test_rule_with_no_boolean_signal_emits_unknown_with_warning(self):
        entity_dicts = [
            {
                "dgEntityId": "OBJ_1",
                "ruleIds": ["R_C"],
                "failedRuleIds": [],
                "passedRuleIds": [],
            }
        ]
        envelope = _build_publish_evidence_envelope("proj-a", "run-1", entity_dicts)
        assert len(envelope.rows) == 1
        row = envelope.rows[0]
        assert row.canonicalStatus == CanonicalStatus.UNKNOWN
        assert len(row.warnings) == 1
        assert "R_C" in row.warnings[0]

    def test_envelope_validates_against_schema(self):
        entity_dicts = [
            {
                "dgEntityId": "OBJ_1",
                "ruleIds": ["R_A"],
                "failedRuleIds": ["R_A"],
                "passedRuleIds": [],
            }
        ]
        envelope = _build_publish_evidence_envelope("proj-a", "run-1", entity_dicts)
        validate_envelope(envelope)  # must not raise
