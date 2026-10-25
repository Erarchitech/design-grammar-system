"""Independent supplemental raw-byte controls; existing temp auth + socket denial."""
import json
import pytest
import app
from test_gh_publish_wire import client, wire_harness, captured_graph, refuse_network

@pytest.mark.parametrize('legacy', [False, True])
@pytest.mark.parametrize('tail', [
    ',"ignored":{"a":0,"\\u0061":1}',
    ',"ignored":[{"ok":1},{"deep":{"x":0,"x":1}}]',
    ',"ignored":{"x":NaN}',
])
def test_raw_denial_even_without_version(wire_harness,captured_graph,legacy,tail):
    payload=json.loads(wire_harness('emit','supported'))
    if legacy:
        payload.pop('evidenceContractVersion')
    raw=json.dumps(payload,separators=(',',':'))[:-1]+tail+'}'
    response=client.post('/validation/publish',content=raw.encode(),headers={'Content-Type':'application/json'})
    assert response.status_code==422, response.text
    assert captured_graph.all_writes==captured_graph.speckle_payloads==[]

@pytest.mark.parametrize('legacy', [False, True])
def test_unambiguous_repeated_keys_in_distinct_objects_allowed(wire_harness,captured_graph,legacy):
    payload=json.loads(wire_harness('emit','supported'))
    if legacy:
        payload.pop('evidenceContractVersion')
    raw=json.dumps(payload,separators=(',',':'))[:-1]+',"ignored":[{"x":0},{"x":1}]}'
    response=client.post('/validation/publish',content=raw.encode(),headers={'Content-Type':'application/json'})
    assert response.status_code==200, response.text
    assert captured_graph.evidence_writes and captured_graph.speckle_payloads
