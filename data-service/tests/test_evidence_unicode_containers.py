"""Review-2 Unicode/container admission: real ASGI, offline external I/O."""
import json
from collections import deque, UserDict, namedtuple
from dataclasses import dataclass

import pytest
import app
import evidence_contract as contract
from test_evidence_versions import full_payload
from test_evidence_raw_admission import compact, install_run
from test_gh_publish_wire import wire_harness, captured_graph, refuse_network, client, roundtrip

VERSIONS = ['1', '1.0.0', '2.0.0']
BAD_TEXT = ['\ud800', '\udfff', '\ud800x', '\udfff\ud800']


def assert_metadata_rejected(meta):
    with pytest.raises(ValueError):
        contract.build_envelope_with_rule_results('p', 'd', 's', '1', 'test', [], [], source_representation=meta)
    old = contract.build_envelope('p', 'd', 's', '1', 'test', [], source_representation=meta)
    with pytest.raises(ValueError):
        contract.validate_envelope(old)
    for version in VERSIONS:
        payload = full_payload(version)
        payload['sourceRepresentation'] = meta
        assert contract.read_envelope_dict(payload) is None
        with pytest.raises(ValueError):
            contract.parse_envelope_model(payload)


@pytest.mark.parametrize('container', [list, tuple])
@pytest.mark.parametrize('bad', [float('nan'), float('inf'), float('-inf'), '\ud800', '\udfff'])
def test_container_nested_invalid_values_rejected_before_dump(container, bad):
    assert_metadata_rejected({'x': container([{'nested': (bad,)}])})


@pytest.mark.parametrize('container', [list, tuple])
def test_container_finite_values_shared_alias_and_unicode_preserved(container):
    shared = container([1.5, '😀', {'é': 2, 'e\u0301': 3}])
    meta = {'x': shared, 'y': shared}
    model = contract.build_envelope_with_rule_results('p', 'd', 's', '1', 'test', [], [], source_representation=meta)
    expected = {'x': list(shared), 'y': list(shared)}
    assert model.sourceRepresentation == expected
    old = contract.build_envelope('p', 'd', 's', '1', 'test', [], source_representation=meta)
    contract.validate_envelope(old)
    for version in VERSIONS:
        payload = full_payload(version)
        payload['sourceRepresentation'] = meta
        assert contract.read_envelope_dict(payload) is payload
        assert json.loads(json.dumps(payload))['sourceRepresentation'] == expected


@dataclass
class MetadataRecord:
    x: object


class CustomIterable:
    def __iter__(self):
        raise AssertionError('Unsupported custom iterables must not be consumed')


@pytest.mark.parametrize('container', [set, frozenset, deque, iter,
    lambda v: (x for x in v), lambda v: UserDict(x=v),
    lambda v: namedtuple('Point', 'x')(v),
    lambda v: MetadataRecord(v), lambda v: CustomIterable()])
@pytest.mark.parametrize('value', [1.5, float('nan')])
def test_container_non_json_forms_explicitly_rejected(container, value):
    assert_metadata_rejected({'x': container([value])})


@pytest.mark.parametrize('depth', [127, 128, 129])
def test_container_tuple_depth_accounting(depth):
    item = 1.5
    for _ in range(depth - 2):
        item = (item,)
    meta = {'x': item}
    if depth > 128:
        assert_metadata_rejected(meta)
    else:
        # The admission depth ceiling is not a promise to enlarge Pydantic's
        # independent serializer recursion limit for deeply nested Any tuples.
        contract.validate_json_resources({'sourceRepresentation': meta})
        for version in VERSIONS:
            payload = full_payload(version)
            payload['sourceRepresentation'] = meta
            assert contract.read_envelope_dict(payload) is payload


@pytest.mark.parametrize('kind', ['list', 'dict', 'tuple-list', 'model'])
def test_container_cycles_reject_without_dump(kind):
    if kind == 'list':
        item = []
        item.append(item)
    elif kind == 'dict':
        item = {}
        item['self'] = item
    elif kind == 'tuple-list':
        link = []
        item = (link,)
        link.append(item)
    else:
        item = contract.build_envelope('p', 'd', 's', '1', 'test', [])
        item.sourceRepresentation = {'self': item}
    assert_metadata_rejected({'x': item})


@pytest.mark.parametrize('key', [1, None, (float('nan'),)])
def test_container_non_string_nested_keys_rejected(key):
    assert_metadata_rejected({'x': {key: 'value'}})


@pytest.mark.parametrize('version', VERSIONS)
def test_unicode_equivalent_pair_keys_are_duplicates_not_normalized(wire_harness, version):
    raw = compact(full_payload(version))[:-1] + ',"sourceRepresentation":{"\\ud83d\\ude00":1,"😀":2}}'
    assert app.parse_evidence_envelope(raw) is None
    assert json.loads(wire_harness('public-guards', input_bytes=raw.encode())) == {
        'utf8': True, 'read': False, 'strict': False}


@pytest.mark.parametrize('escaped', [True, False])
def test_unicode_valid_publish_persist_view_roundtrip(wire_harness, captured_graph, escaped):
    request = json.loads(wire_harness('emit', 'supported'))
    detail = '😀 / Привет / é / e\u0301'
    request['ruleResults'][0]['detail'] = detail
    raw = json.dumps(request, ensure_ascii=escaped).encode('utf-8')
    envelope, projection = roundtrip(wire_harness, captured_graph, 'supported', request_bytes=raw)
    assert envelope['ruleResults'][0]['detail'] == detail
    assert projection['envelopePresent']


def metadata(text, where):
    return {text: 1} if where == 'key' else {'x': text}


@pytest.mark.parametrize('version', VERSIONS)
@pytest.mark.parametrize('where', ['key', 'value'])
@pytest.mark.parametrize('text', BAD_TEXT)
def test_unicode_raw_read_python_api_and_actual_view(wire_harness, captured_graph, version, where, text):
    payload = full_payload(version)
    payload['sourceRepresentation'] = metadata(text, where)
    raw = compact(payload)  # ASCII escaped surrogates, not broken transport.
    assert json.loads(wire_harness('public-guards', input_bytes=raw.encode())) == {
        'utf8': True, 'read': False, 'strict': False}
    run = install_run(captured_graph, raw)
    run['shaclReportJson'] = compact({'source': metadata(text, where)})
    response = client.get('/validation/view/P_WIRE/' + run['runId'])
    assert response.status_code == 200
    assert response.json()['evidenceEnvelope'] is None
    assert response.json()['shaclReport'] is None
    assert app.parse_evidence_envelope(raw) is None
    assert contract.read_envelope_dict(payload) is None
    with pytest.raises(ValueError):
        contract.parse_envelope_model(payload)
    with pytest.raises(ValueError):
        contract.decode_evidence_json(raw)


@pytest.mark.parametrize('where', ['key', 'value'])
@pytest.mark.parametrize('text', BAD_TEXT)
def test_unicode_publish_raw_denied_before_writes(wire_harness, captured_graph, where, text):
    request = json.loads(wire_harness('emit', 'supported'))
    request['ignored'] = metadata(text, where)
    response = client.post('/validation/publish', content=compact(request).encode(),
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json() == {'detail': 'Invalid publish JSON'}
    assert captured_graph.all_writes == captured_graph.speckle_payloads == []
    with pytest.raises(ValueError):
        app.ValidationPublishRequest.model_validate(request)


@pytest.mark.parametrize('where', ['key', 'value'])
@pytest.mark.parametrize('text', BAD_TEXT)
def test_unicode_factory_and_legacy_validator(where, text):
    meta = metadata(text, where)
    with pytest.raises(ValueError):
        contract.build_envelope_with_rule_results('p', 'd', 's', '1', 'test', [], [], source_representation=meta)
    old = contract.build_envelope('p', 'd', 's', '1', 'test', [], source_representation=meta)
    with pytest.raises(ValueError):
        contract.validate_envelope(old)


@pytest.mark.parametrize('version', VERSIONS)
@pytest.mark.parametrize('escaped', [True, False])
def test_unicode_valid_pairs_and_distinct_keys_preserved(wire_harness, captured_graph, version, escaped):
    payload = full_payload(version)
    payload['sourceRepresentation'] = {'😀': '𐀀 / Привет', 'é': 1, 'e\u0301': 2, '\ufffd': 'valid replacement scalar'}
    raw = json.dumps(payload, ensure_ascii=escaped)
    assert contract.decode_evidence_json(raw.encode('utf-8')) == payload
    assert json.loads(wire_harness('public-guards', input_bytes=raw.encode('utf-8'))) == {
        'utf8': True, 'read': True, 'strict': True}
    assert contract.read_envelope_dict(payload) is payload
    assert app.parse_evidence_envelope(raw) == payload
    assert json.loads(wire_harness('strict', input_bytes=raw.encode('utf-8'))) is True
    assert json.loads(wire_harness('read', input_bytes=raw.encode('utf-8')))['envelopePresent']
    run = install_run(captured_graph, raw)
    run['shaclReportJson'] = json.dumps({'source': payload['sourceRepresentation']}, ensure_ascii=escaped)
    response = client.get('/validation/view/P_WIRE/' + run['runId'])
    assert response.json()['evidenceEnvelope'] == payload
    assert response.json()['shaclReport']['source'] == payload['sourceRepresentation']


@pytest.mark.parametrize('invalid', [b'\xff', b'\xed\xa0\x80', b'\xf0\x80\x80\x80'])
def test_unicode_invalid_utf8_publish_and_read(wire_harness, captured_graph, invalid):
    raw = compact(json.loads(wire_harness('emit', 'supported'))).encode()[:-1] + b',"ignored":"' + invalid + b'"}'
    response = client.post('/validation/publish', content=raw, headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert captured_graph.all_writes == captured_graph.speckle_payloads == []
    assert app.parse_evidence_envelope(raw) is None
    with pytest.raises(ValueError):
        contract.decode_evidence_json(raw)
    envelope_raw = compact(full_payload()).encode()[:-1] + b',"sourceRepresentation":{"x":"' + invalid + b'"}}'
    assert json.loads(wire_harness('public-guards', input_bytes=envelope_raw)) == {
        'utf8': False, 'read': False, 'strict': False}


@pytest.mark.parametrize('version', ['1', '1.0.0'])
@pytest.mark.parametrize('where', ['key', 'value'])
def test_unicode_historical_unused_root_rejected(wire_harness, version, where):
    payload = {'contractVersion': version, **metadata('\ud800', where)}
    raw = compact(payload)
    assert app.parse_evidence_envelope(raw) is None
    assert json.loads(wire_harness('strict', input_bytes=raw.encode())) is False
    assert not json.loads(wire_harness('read', input_bytes=raw.encode()))['envelopePresent']
