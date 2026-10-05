"""Versioned construction versus bounded historical projection (no live I/O)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jsonschema
import pytest
from pydantic import ValidationError
import app as app_module
import evidence_contract as contract
from test_gh_publish_wire import wire_harness, captured_graph, refuse_network, client, roundtrip
import hashlib
from pathlib import Path


@pytest.mark.parametrize("scenario", ["supported", "unsupported", "zero_rows", "diagnostics"])
def test_release_evidence_exact_bytes(wire_harness, captured_graph, monkeypatch, tmp_path, scenario):
    """Retain real bytes, never auth headers or a reconstructed persist result."""
    blobs = {}
    real_get = client.get

    def invoke(*args, input_bytes=None):
        output = wire_harness(*args, input_bytes=input_bytes)
        if args[0] == "emit":
            blobs["request.json"] = output
        elif args[0] == "read":
            blobs["reader-input.json"] = input_bytes
            blobs["reader-output.json"] = output
        return output

    def view_get(*args, **kwargs):
        response = real_get(*args, **kwargs)
        assert "readToken" not in response.json()  # D-21: no Speckle credential in the view payload
        blobs["view-response.json"] = response.content
        return response

    monkeypatch.setattr(client, "get", view_get)
    envelope, read = roundtrip(invoke, captured_graph, scenario)
    assert len(captured_graph.evidence_writes) == 1
    key, raw = captured_graph.evidence_writes[0]
    blobs["persisted-evidence.json"] = raw.encode("utf-8")
    assert captured_graph.evidence_reads == [(key, raw)]
    assert blobs["reader-input.json"] == blobs["persisted-evidence.json"]
    assert read["inputSha256"] == hashlib.sha256(blobs["persisted-evidence.json"]).hexdigest()
    assert json.loads(blobs["view-response.json"])["evidenceEnvelope"] == envelope
    # Temporary by default; explicit switch retains only payloads in phase-local evidence.
    directory = tmp_path / scenario
    if os.environ.get("DG_RETAIN_PHASE1205_1_EVIDENCE") == "1":
        directory = (Path(__file__).resolve().parents[2] / ".planning/phases/"
                     "1205.1-canonical-status-gh-publish-closure/evidence/wire" / scenario)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"scenario": scenario, "captureHits": len(captured_graph.evidence_writes),
                "readbackHits": len(captured_graph.evidence_reads), "identity": list(key),
                "readerInputSha256": read["inputSha256"], "files": {}}
    for name, raw_bytes in blobs.items():
        (directory / name).write_bytes(raw_bytes)
        manifest["files"][name] = {"bytes": len(raw_bytes), "sha256": hashlib.sha256(raw_bytes).hexdigest()}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@pytest.mark.parametrize("version", ["1.0.0", "2.0.0"])
def test_actual_csharp_factory_bytes_pass_python_root_schema_and_model(wire_harness, version):
    raw = wire_harness("envelope", version)
    payload = json.loads(raw)
    jsonschema.validate(payload, contract.load_contract_schema())
    model = contract.parse_envelope_model(payload)
    assert model.contractVersion == version
    assert payload["canonicalizationVersion"] == 1
    assert app_module.parse_evidence_envelope(raw) == payload
    assert len(payload["rows"]) == 3
    if version == "2.0.0":
        assert [r["ruleId"] for r in payload["ruleResults"]] == ["R_EMPTY_A", "R_EMPTY_B", "R_ROW"]
        assert payload["ruleResults"][0]["canonicalStatus"] == "no_population"
        assert payload["ruleResults"][1]["canonicalStatus"] == "not_evaluated"
    else:
        assert "ruleResults" not in payload
    assert payload["rows"][1]["detail"] == "duplicate failure"
    assert payload["rows"][1]["warnings"] == ["row-warning"]
    projection = json.loads(wire_harness("read", input_bytes=raw))
    assert projection["inputSha256"] == hashlib.sha256(raw).hexdigest()
    assert projection["envelopePresent"] is True
    assert projection["verdicts"] == [
        {"objectId": "OBJ", "status": "failed", "duplicate": True},
        {"objectId": "obj", "status": "passed", "duplicate": False},
    ]
    assert len(projection["collisions"]) == 1


def test_actual_python_v2_factory_bytes_enter_actual_csharp_reader(wire_harness):
    envelope = contract.build_envelope_with_rule_results(
        "p", "d", "python", "1", "test",
        [contract.EvidenceRow(ruleId="R", objectId="OBJ", canonicalStatus="passed"),
         contract.EvidenceRow(ruleId="R", objectId="OBJ", canonicalStatus="unknown", detail="unresolved", warnings=["typed"]),
         contract.EvidenceRow(ruleId="r", objectId="obj", canonicalStatus="passed")],
        [contract.EvidenceRuleResult(ruleId="Z", canonicalStatus="no_population", warnings=[]),
         contract.EvidenceRuleResult(ruleId="A", canonicalStatus="unsupported", warnings=["rule"], detail="unsupported rule")],
    )
    raw = envelope.model_dump_json(exclude_none=True).encode("utf-8")
    jsonschema.validate(json.loads(raw), contract.load_contract_schema())
    assert contract.parse_envelope_model(json.loads(raw)).contractVersion == "2.0.0"
    projection = json.loads(wire_harness("read", input_bytes=raw))
    assert projection["inputSha256"] == hashlib.sha256(raw).hexdigest()
    assert projection["envelopePresent"] is True
    assert projection["verdicts"] == [
        {"objectId": "OBJ", "status": "unknown", "duplicate": True},
        {"objectId": "obj", "status": "passed", "duplicate": False},
    ]
    assert len(projection["collisions"]) == 1


def test_source_linked_harness_core_diagnostics_are_nonempty_before_transport_mapping(wire_harness):
    package = json.loads(wire_harness("core-diagnostics"))
    rules = {r["RuleId"]: r for r in package["RuleResults"]}
    assert rules["R_DIAG"]["Detail"]
    assert rules["R_LEGACY"]["Warnings"] == ["typed_binding_outcome_unavailable"]
    assert rules["R_LEGACY"]["Detail"]
    entity = package["Entities"][0]
    assert entity["CanonicalDetails"]["R_DIAG"]
    assert entity["CanonicalDetails"]["R_LEGACY"]
    assert entity["CanonicalWarnings"]["R_LEGACY"] == ["typed_binding_outcome_unavailable"]
    assert "R_MISSING" in entity["CanonicalStatuses"]


def test_python_tracer_two_zero_row_rules_persist_and_read(monkeypatch):
    builder = getattr(contract, "build_envelope_with_rule_results", None)
    assert callable(builder), "Missing versioned rule-results builder"
    envelope = builder(
        "proj-version", "definition", "test-service", "1", "publish", [],
        [contract.EvidenceRuleResult(ruleId="R_Z", canonicalStatus="no_population", warnings=[]),
         contract.EvidenceRuleResult(ruleId="R_A", canonicalStatus="not_evaluated", warnings=["pending"], detail="not run")],
    )
    contract.validate_envelope(envelope)
    raw = envelope.model_dump_json(exclude_none=True)
    captured = []
    monkeypatch.setattr(app_module, "write_query", lambda query, parameters: captured.append((query, parameters)))
    app_module.persist_evidence_envelope("proj-version", "run-version", raw)
    assert len(captured) == 1
    query, parameters = captured[0]
    assert "$evidenceEnvelopeJson" in query
    assert parameters == {"graph": app_module.VALIDATION_GRAPH, "project": "proj-version", "runId": "run-version", "evidenceEnvelopeJson": raw}
    assert parameters["evidenceEnvelopeJson"].encode("utf-8") == raw.encode("utf-8")
    parsed = app_module.parse_evidence_envelope(parameters["evidenceEnvelopeJson"])
    assert parsed == json.loads(raw)
    assert parsed["contractVersion"] == "2.0.0"
    assert parsed["canonicalizationVersion"] == 1
    assert parsed["rows"] == []
    assert parsed["canonicalStatus"] == "not_evaluated"
    assert parsed["ruleResults"] == [
        {"ruleId": "R_A", "canonicalStatus": "not_evaluated", "warnings": ["pending"], "detail": "not run"},
        {"ruleId": "R_Z", "canonicalStatus": "no_population", "warnings": []},
    ]
    old = contract.build_envelope("p", "d", "s", "1", "stage", [])
    assert old.contractVersion == "1.0.0"
    assert old.canonicalStatus == contract.CanonicalStatus.NO_POPULATION
    assert "ruleResults" not in old.model_dump()


@pytest.mark.parametrize("version", ["1", "1.0.0"])
def test_python_tracer_new_partial_old_control_preserves_no_rows(version):
    payload = {"contractVersion": version, "canonicalStatus": "failed"}
    assert app_module.parse_evidence_envelope(json.dumps(payload)) == payload


@pytest.mark.parametrize("rows", [None, {}, "rows", [None], [{"ruleId": "R", "objectId": "O", "canonicalStatus": "bogus"}]])
def test_python_tracer_new_partial_old_control_rejects_invalid_rows(rows):
    assert app_module.parse_evidence_envelope(json.dumps({"contractVersion": "1.0.0", "rows": rows})) is None


@pytest.mark.parametrize("corrupt_fields", [
    ("evidenceEnvelopeJson",), ("shaclReportJson",), ("statePayloadJson",),
    ("evidenceEnvelopeJson", "shaclReportJson", "statePayloadJson"),
])
def test_json_decode_boundaries_persisted_record_view_fallback(captured_graph, corrupt_fields):
    # Actual persist function, captured external I/O, then actual view builder.
    run = {"runId": "run-corrupt", "rulesJson": "[]", "speckleProjectId": "sp-wire",
           "baseModelId": "bm-wire", "baseVersionId": "bv-wire",
           "validationModelId": "vm-wire", "validationVersionId": "vv-wire",
           "baseResourceUrl": "http://speckle.invalid/base",
           "validationResourceUrl": "http://speckle.invalid/validation",
           "modelViewerUrl": "http://dg.invalid/view"}
    key = app_module.VALIDATION_GRAPH, "P_WIRE", run["runId"]
    captured_graph.runs[key] = run
    for field in corrupt_fields:
        if field == "evidenceEnvelopeJson":
            app_module.persist_evidence_envelope("P_WIRE", run["runId"], "[" * 10000)
            assert captured_graph.evidence_writes == [(key, "[" * 10000)]
        else:
            run[field] = "[" * 10000
    payload = app_module.build_view_payload("P_WIRE", captured_graph.runs[key], {})
    assert payload["runId"] == "run-corrupt"
    assert payload["evidenceEnvelope"] is None
    assert payload["shaclReport"] is None
    assert payload["canonicalStateHash"] is None
    assert payload["objectSets"] == {}
    assert payload["rules"] == []
    assert app_module._project_state_summary(run.get("statePayloadJson")) is None
    assert json.loads(json.dumps(payload)) == payload


def full_payload(version="2.0.0"):
    payload = contract.build_envelope("p", "d", "s", "1", "stage", []).model_dump(mode="json", exclude_none=True)
    payload["contractVersion"] = version
    if version == "2.0.0":
        payload["ruleResults"] = [{"ruleId": "R", "canonicalStatus": "unsupported", "warnings": []}]
    return payload


@pytest.mark.parametrize("version,model_name", [("1.0.0", "EvidenceEnvelope"), ("1", "LegacyEvidenceEnvelope"), ("2.0.0", "EvidenceEnvelopeV2")])
def test_strict_full_admission_preserves_exact_version(version, model_name):
    payload = full_payload(version)
    parsed = contract.parse_envelope_model(payload)
    assert type(parsed).__name__ == model_name
    assert parsed.contractVersion == version
    assert contract.read_envelope_dict(payload) is payload


@pytest.mark.parametrize("version", [None, 1, 2, True, "", " 1", "1.0", "2", "2.0.0 ", "3.0.0", {}, []])
def test_unknown_or_nonstring_tokens_fail_strict_and_read(version):
    payload = full_payload()
    payload["contractVersion"] = version
    with pytest.raises(jsonschema.ValidationError):
        contract.parse_envelope_model(payload)
    assert app_module.parse_evidence_envelope(json.dumps(payload)) is None


@pytest.mark.parametrize("field", ["contractVersion", "canonicalizationVersion", "project", "definitionId", "serviceName", "serviceVersion", "emittedAt", "stage", "canonicalStatus", "rows", "ruleResults"])
def test_new_shape_requires_every_field(field):
    payload = full_payload()
    del payload[field]
    with pytest.raises((jsonschema.ValidationError, ValidationError)):
        contract.parse_envelope_model(payload)
    assert app_module.parse_evidence_envelope(json.dumps(payload)) is None


@pytest.mark.parametrize("target,field,value", [
    ("root", "extra", 1), ("root", "project", None),
    ("root", "canonicalizationVersion", "1"), ("root", "canonicalizationVersion", True),
    ("root", "canonicalStatus", "Passed"), ("root", "rows", None),
    ("root", "ruleResults", None), ("root", "inputHash", "invalid"),
    ("root", "sourceRepresentation", []), ("root", "warnings", [1]),
    ("rule", "extra", "no"), ("rule", "objectId", "fake"),
    ("rule", "warnings", None), ("rule", "detail", None),
    ("rule", "canonicalStatus", "invalid"), ("rule", "ruleId", 42),
    ("row", "extra", 1), ("row", "canonicalStatus", False),
    ("row", "objectId", None), ("row", "warnings", [False]),
    ("row", "inputHash", "lowercase"), ("row", "detail", None),
])
def test_new_shape_rejects_invalid_nested_fields_without_stripping(target, field, value):
    payload = full_payload()
    payload["rows"] = [{"ruleId": "R", "objectId": "O", "canonicalStatus": "passed"}]
    node = payload if target == "root" else payload["ruleResults" if target == "rule" else "rows"][0]
    node[field] = value
    with pytest.raises(jsonschema.ValidationError):
        contract.parse_envelope_model(payload)
    with pytest.raises(ValidationError):
        contract.EvidenceEnvelopeV2.model_validate(payload)
    assert app_module.parse_evidence_envelope(json.dumps(payload)) is None


@pytest.mark.parametrize("version", ["1", "1.0.0"])
def test_old_full_rejects_rule_results_and_partial_strict_construction(version):
    payload = full_payload(version)
    payload["ruleResults"] = []
    with pytest.raises(jsonschema.ValidationError):
        contract.parse_envelope_model(payload)
    assert contract.read_envelope_dict(payload) is None
    partial = {"contractVersion": version, "canonicalStatus": "passed"}
    with pytest.raises(jsonschema.ValidationError):
        contract.parse_envelope_model(partial)
    assert contract.read_envelope_dict(partial) is partial


def test_v2_identity_order_empty_union_and_row_rule_precedence():
    result = contract.EvidenceRuleResult(ruleId="R", canonicalStatus="unsupported", warnings=[])
    with pytest.raises(ValidationError, match="Duplicate"):
        contract.build_envelope_with_rule_results("p", "d", "s", "1", "stage", [], [result, result])
    payload = full_payload()
    payload["ruleResults"] *= 2
    assert contract.read_envelope_dict(payload) is None
    payload["ruleResults"][0] = {"ruleId": "Z", "canonicalStatus": "passed", "warnings": []}
    assert contract.read_envelope_dict(payload) is None
    empty = contract.build_envelope_with_rule_results("p", "d", "s", "1", "stage", [], [])
    assert empty.canonicalStatus == "not_evaluated"
    row = contract.EvidenceRow(ruleId="other", objectId="O", canonicalStatus="failed")
    combined = contract.build_envelope_with_rule_results("p", "d", "s", "1", "stage", [row], [result])
    assert combined.canonicalStatus == "failed"
    assert combined.rows == [row]
    assert result.canonicalStatus == "unsupported"


def test_old_model_rejects_crossed_version_literal():
    with pytest.raises(ValidationError):
        contract.EvidenceEnvelope.model_validate(full_payload("1"))
    with pytest.raises(ValidationError):
        contract.LegacyEvidenceEnvelope.model_validate(full_payload("1.0.0"))


@pytest.mark.parametrize("field,value", [("detail", None), ("warnings", ()), ("warnings", [b"bytes"]), ("ruleId", b"R")])
def test_rule_result_model_does_not_coerce_strict_record(field, value):
    payload = {"ruleId": "R", "canonicalStatus": "passed", "warnings": []}
    payload[field] = value
    with pytest.raises(ValidationError):
        contract.EvidenceRuleResult.model_validate(payload)


@pytest.mark.parametrize("version", ["1", "1.0.0", "2.0.0"])
@pytest.mark.parametrize("mutation", ["valid", "crossed", "missing-token", "numeric-token", "unknown-token", "invalid-status", "extra-root", "extra-row"])
def test_raw_schema_model_actual_reader_matrix(wire_harness, version, mutation):
    payload = full_payload(version)
    payload["rows"] = [{"ruleId": "R", "objectId": "O", "canonicalStatus": "passed"}]
    if mutation == "crossed":
        if version == "2.0.0":
            del payload["ruleResults"]
        else:
            payload["ruleResults"] = []
    elif mutation == "missing-token":
        del payload["contractVersion"]
    elif mutation == "numeric-token":
        payload["contractVersion"] = 1
    elif mutation == "unknown-token":
        payload["contractVersion"] = "9.0.0"
    elif mutation == "invalid-status":
        payload["rows"][0]["canonicalStatus"] = "Passed"
    elif mutation == "extra-root":
        payload["extra"] = True
    elif mutation == "extra-row":
        payload["rows"][0]["extra"] = True
    valid = mutation == "valid"
    if valid:
        jsonschema.validate(payload, contract.load_contract_schema())
        assert contract.parse_envelope_model(payload).contractVersion == version
    else:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, contract.load_contract_schema())
        with pytest.raises(jsonschema.ValidationError):
            contract.parse_envelope_model(payload)
    # Historical read tolerates root metadata; strict construction never does.
    admitted = valid or (version != "2.0.0" and mutation == "extra-root")
    raw = json.dumps(payload).encode()
    assert (app_module.parse_evidence_envelope(raw) is not None) == admitted
    projection = json.loads(wire_harness("read", input_bytes=raw))
    assert projection["envelopePresent"] == admitted
    assert len(projection["verdicts"]) == (1 if admitted else 0)


@pytest.mark.parametrize("version", ["1", "1.0.0"])
@pytest.mark.parametrize("summary", ["passed", "failed"])
@pytest.mark.parametrize("rows_kind", ["absent", "empty", "valid", "null", "object", "invalid-status", "ruleResults"])
def test_new_partial_controls_are_not_historical_full_fixtures(wire_harness, version, summary, rows_kind):
    payload = {"contractVersion": version, "canonicalStatus": summary}
    if rows_kind == "empty":
        payload["rows"] = []
    elif rows_kind == "valid":
        payload["rows"] = [{"ruleId": "R", "objectId": "O", "canonicalStatus": "unsupported"}]
    elif rows_kind == "null":
        payload["rows"] = None
    elif rows_kind == "object":
        payload["rows"] = {}
    elif rows_kind == "invalid-status":
        payload["rows"] = [{"ruleId": "R", "objectId": "O", "canonicalStatus": "invalid"}]
    elif rows_kind == "ruleResults":
        payload["ruleResults"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, contract.load_contract_schema())
    with pytest.raises(jsonschema.ValidationError):
        contract.parse_envelope_model(payload)
    admitted = rows_kind in ("absent", "empty", "valid")
    raw = json.dumps(payload).encode()
    parsed = app_module.parse_evidence_envelope(raw)
    assert parsed == (payload if admitted else None)
    if admitted:
        assert set(parsed) == set(payload)  # no synthesized rows/metadata/ruleResults
        assert contract.read_envelope_dict(payload) is payload
    projection = json.loads(wire_harness("read", input_bytes=raw))
    assert projection["envelopePresent"] == admitted
    assert projection["collisions"] == []
    assert projection["verdicts"] == ([{"objectId": "O", "status": "unsupported", "duplicate": False}] if rows_kind == "valid" else [])
