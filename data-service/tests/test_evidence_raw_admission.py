"""Raw-byte HTTP and same-byte C# controls for review 1205.1 (offline I/O)."""
import json

import pytest
import app
import evidence_contract as contract
from test_evidence_versions import full_payload
from test_gh_publish_wire import wire_harness, captured_graph, refuse_network, client


def nested_raw(depth, version="2.0.0"):
    # root object = 1, sourceRepresentation object = 2; containers only count.
    raw = compact(full_payload(version))
    return raw[:-1] + ',"sourceRepresentation":{"x":' + '[' * (depth - 2) + '0' + ']' * (depth - 2) + '}}'


def install_run(graph, raw):
    run = {"runId": "raw-corrupt", "rulesJson": "[]", "speckleProjectId": "sp-wire",
           "baseModelId": "bm-wire", "baseVersionId": "bv-wire",
           "validationModelId": "vm-wire", "validationVersionId": "vv-wire",
           "baseResourceUrl": "http://speckle.invalid/base",
           "validationResourceUrl": "http://speckle.invalid/validation",
           "modelViewerUrl": "http://dg.invalid/view", "evidenceEnvelopeJson": raw}
    graph.runs[app.VALIDATION_GRAPH, "P_WIRE", run["runId"]] = run
    return run


@pytest.mark.parametrize("depth", [70, 127, 128, 129, 702])
@pytest.mark.parametrize("version", ["1", "1.0.0", "2.0.0"])
def test_depth_bound_raw_read_and_real_view(wire_harness, captured_graph, depth, version):
    raw = nested_raw(depth, version)
    payload = json.loads(raw)  # 700 nested arrays decode successfully, unlike old regression.
    expected = depth <= 128
    assert (contract.read_envelope_dict(payload) is not None) == expected
    assert (app.parse_evidence_envelope(raw) is not None) == expected
    read = json.loads(wire_harness("read", input_bytes=raw.encode()))
    assert read["envelopePresent"] == expected
    assert json.loads(wire_harness("strict", input_bytes=raw.encode())) == expected
    run = install_run(captured_graph, raw)
    view = client.get('/validation/view/P_WIRE/' + run['runId'])
    assert view.status_code == 200
    assert (view.json()['evidenceEnvelope'] is not None) == expected


@pytest.mark.parametrize("depth", [129, 702])
def test_publish_depth_denial_before_writes(wire_harness, captured_graph, depth):
    raw = compact(json.loads(wire_harness("emit", "supported")))
    raw = raw[:-1] + ',"ignored":' + '[' * (depth - 1) + '0' + ']' * (depth - 1) + '}'
    response = client.post('/validation/publish', content=raw.encode(), headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert captured_graph.all_writes == captured_graph.speckle_payloads == []


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e400", "-1e400"])
@pytest.mark.parametrize("version", ["1", "1.0.0", "2.0.0"])
def test_nonfinite_raw_and_inmemory_read_view(wire_harness, captured_graph, token, version):
    raw = compact(full_payload(version))[:-1] + ',"sourceRepresentation":{"x":' + token + '}}'
    payload = json.loads(raw)
    assert contract.read_envelope_dict(payload) is None
    with pytest.raises(ValueError):
        contract.parse_envelope_model(payload)
    assert_absent(wire_harness, raw)
    run = install_run(captured_graph, raw)
    response = client.get('/validation/view/P_WIRE/' + run['runId'])
    assert response.status_code == 200
    assert response.json()['evidenceEnvelope'] is None


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e400", "-1e400"])
def test_nonfinite_publish_raw_and_inmemory_denied_before_writes(wire_harness, captured_graph, token):
    raw = compact(json.loads(wire_harness("emit", "supported")))[:-1] + ',"ignored":{"x":' + token + '}}'
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        app.ValidationPublishRequest.model_validate(json.loads(raw))
    response = client.post('/validation/publish', content=raw.encode(), headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert captured_graph.all_writes == captured_graph.speckle_payloads == []


@pytest.mark.parametrize("token,expected", [
    ("1.0", True), ("1e0", True), ("1099511627776", True),
    ("9007199254740990", True), ("9007199254740991", True), ("9007199254740992", False),
    ("-9007199254740991", True), ("-9007199254740992", False), ("1.5", False),
])
@pytest.mark.parametrize("version", ["1", "1.0.0", "2.0.0"])
def test_integral_number_range_schema_reader_parity(wire_harness, token, expected, version):
    import jsonschema
    raw = compact(full_payload(version)).replace('"canonicalizationVersion":1', '"canonicalizationVersion":' + token)
    payload = json.loads(raw)
    assert jsonschema.Draft202012Validator(contract.load_contract_schema()).is_valid(payload) == expected
    # Historical readers intentionally do not validate unused root metadata.
    admitted = expected or version != "2.0.0"
    assert (contract.read_envelope_dict(payload) is not None) == admitted
    read = json.loads(wire_harness('read', input_bytes=raw.encode()))
    assert read['envelopePresent'] == admitted
    assert json.loads(wire_harness("strict", input_bytes=raw.encode())) == expected


@pytest.mark.parametrize("field", ["inputHash", "outputHash", "dgId", "row.inputHash", "row.outputHash"])
@pytest.mark.parametrize("mutation", ["short", "exact", "long", "newline"])
def test_hash_absolute_end_schema_reader_parity(wire_harness, field, mutation):
    import jsonschema
    payload = full_payload()
    payload['rows'] = [{'ruleId': 'R', 'objectId': 'O', 'canonicalStatus': 'unsupported'}]
    value = ('dg:' + 'A' * 16) if field == 'dgId' else 'A' * 64
    value = value[:-1] if mutation == 'short' else value + ('A' if mutation == 'long' else '\n' if mutation == 'newline' else '')
    target = payload['rows'][0] if field.startswith('row.') else payload
    target[field.split('.')[-1]] = value
    expected = mutation == 'exact'
    assert jsonschema.Draft202012Validator(contract.load_contract_schema()).is_valid(payload) == expected
    assert (app.parse_evidence_envelope(compact(payload)) is not None) == expected
    assert json.loads(wire_harness('read', input_bytes=compact(payload).encode()))['envelopePresent'] == expected


@pytest.mark.parametrize("token,expected", [("1e308", True), ("1e309", False), ("9" * 400, False), ("0.0", True)])
def test_metadata_finite_number_range(wire_harness, token, expected):
    raw = compact(full_payload())[:-1] + ',"sourceRepresentation":{"x":' + token + '}}'
    assert (app.parse_evidence_envelope(raw) is not None) == expected
    assert json.loads(wire_harness('read', input_bytes=raw.encode()))['envelopePresent'] == expected


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_nonfinite_sibling_view_fallback(captured_graph, token):
    run = install_run(captured_graph, None)
    run['shaclReportJson'] = '{"source":{"x":' + token + '}}'
    response = client.get('/validation/view/P_WIRE/' + run['runId'])
    assert response.status_code == 200
    assert response.json()['shaclReport'] is None


@pytest.mark.parametrize("status", ['"unsupported","canonicalStatus":"passed"', '"passed","canonicalStatus":"unsupported"'])
def test_duplicate_row_status_raw_member_not_array_collision(wire_harness, status):
    raw = compact(full_payload())
    raw = raw.replace('"rows":[]', '"rows":[{"ruleId":"R","objectId":"O","canonicalStatus":' + status + '}]')
    assert_absent(wire_harness, raw)


@pytest.mark.parametrize("token", [float('nan'), float('inf'), float('-inf')])
def test_v2_factory_does_not_coerce_nonfinite_metadata_to_null(token):
    with pytest.raises(ValueError):
        contract.build_envelope_with_rule_results('p', 'd', 's', '1', 'test', [], [], source_representation={'x': token})


def test_legacy_validation_checks_before_json_mode_coercion():
    envelope = contract.build_envelope('p', 'd', 's', '1', 'test', [], source_representation={'x': float('nan')})
    with pytest.raises(ValueError):
        contract.validate_envelope(envelope)


@pytest.mark.parametrize("depth", [127, 128])
def test_publish_depth_below_and_at_limit(wire_harness, captured_graph, depth):
    raw = compact(json.loads(wire_harness('emit', 'supported')))
    raw = raw[:-1] + ',"ignored":' + '[' * (depth - 1) + '0' + ']' * (depth - 1) + '}'
    response = client.post('/validation/publish', content=raw.encode(), headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert captured_graph.evidence_writes and captured_graph.speckle_payloads


def compact(value):
    return json.dumps(value, separators=(",", ":"))


def assert_absent(wire_harness, raw):
    assert app.parse_evidence_envelope(raw) is None
    projection = json.loads(wire_harness("read", input_bytes=raw.encode()))
    assert json.loads(wire_harness("strict", input_bytes=raw.encode())) is False
    assert projection["envelopePresent"] is False
    assert projection["verdicts"] == []
    assert projection["collisions"] == []


@pytest.mark.parametrize("key", ["evidenceContractVersion", "canonicalStatus", "canonicalStatuses", "R_WIRE", "entities"])
def test_duplicate_publish_raw_bytes_denied_before_writes(wire_harness, captured_graph, key):
    raw = compact(json.loads(wire_harness("emit", "supported")))
    token = '"' + key + '":'
    first = '"unsupported"' if key in ("canonicalStatus", "R_WIRE") else 'null'
    assert token in raw
    raw = raw.replace(token, token + first + ',' + token, 1)
    response = client.post("/validation/publish", content=raw.encode(), headers={"Content-Type": "application/json"})
    assert response.status_code == 422, response.text
    assert captured_graph.all_writes == []
    assert captured_graph.speckle_payloads == []


@pytest.mark.parametrize("version", ["1", "1.0.0", "2.0.0"])
@pytest.mark.parametrize("key", ["contractVersion", "canonicalStatus", "rows", "nested", "escaped"])
def test_duplicate_persisted_members_before_version_dispatch(wire_harness, version, key):
    payload = full_payload(version)
    raw = compact(payload)
    if key == "nested":
        raw = raw[:-1] + ',"sourceRepresentation":{"x":1,"x":2}}'
    elif key == "escaped":
        raw = raw.replace('"contractVersion":', '"contract\\u0056ersion":"2.0.0","contractVersion":', 1)
    else:
        token = '"' + key + '":'
        raw = raw.replace(token, token + ('"2.0.0"' if key == "contractVersion" else 'null') + ',' + token, 1)
    assert_absent(wire_harness, raw)


@pytest.mark.parametrize("version", ["1", "1.0.0"])
def test_unambiguous_old_no_rows_is_not_rewritten(wire_harness, version):
    raw = compact({"contractVersion": version, "canonicalStatus": "passed"})
    assert app.parse_evidence_envelope(raw) == json.loads(raw)
    read = json.loads(wire_harness("read", input_bytes=raw.encode()))
    assert read["envelopePresent"] and read["verdicts"] == []
