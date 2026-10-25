"""Independent pure boundary probes. No app import, HTTP, tests or builds."""
import ast
import asyncio
import copy
import difflib
import hashlib
import json
import re
import subprocess
import sys
from collections import UserDict, deque, namedtuple
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
PHASE = ROOT / '.planning/phases/1205.1-canonical-status-gh-publish-closure'
FIX = PHASE / 'evidence/fix-iteration2'
sys.path.insert(0, str(ROOT / 'data-service'))
import evidence_contract as ec
from pydantic import BaseModel
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

records = []
def record(name, **proof):
    records.append({'name': name, **proof})

def denied(fn):
    try:
        fn()
    except ValueError:
        return True
    return False

manifest = json.loads((FIX / 'manifest.json').read_bytes())
source_hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in manifest['source_sha256']}
assert source_hashes == manifest['source_sha256']
protected_mismatches = [p for p, h in manifest['protected_files'].items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
assert not protected_mismatches
parts = []
for p in manifest['source_sha256']:
    before = FIX / 'before' / p
    parts.extend(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(True) if before.exists() else [], (ROOT / p).read_text(encoding='utf-8').splitlines(True), fromfile='before/' + p, tofile='after/' + p))
assert ''.join(parts) == (FIX / 'iteration-only.diff').read_text(encoding='utf-8')

def head(p):
    return subprocess.run(['git', 'show', 'HEAD:' + p], cwd=ROOT, capture_output=True, check=True).stdout.decode('utf-8').replace('\r\n', '\n')
p = 'data-service/tests/test_evidence_contract.py'
def historical_node(text):
    return ast.dump(next(n for n in ast.parse(text).body if getattr(n, 'name', None) == 'TestParseEvidenceEnvelope'))
assert historical_node(head(p)) == historical_node((ROOT / p).read_text(encoding='utf-8'))
p = 'DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs'
pattern = r'    private static string BuildEnvelopeJson\(.*?(?=\n    \[)'
assert re.search(pattern, head(p), re.S).group().strip() == re.search(pattern, (ROOT / p).read_text(encoding='utf-8'), re.S).group().strip()

BASE = json.loads((PHASE / 'evidence/wire/supported/persisted-evidence.json').read_bytes())
def payload(meta, version):
    p = copy.deepcopy(BASE)
    p['contractVersion'] = version
    if version != '2.0.0':
        p.pop('ruleResults', None)
    p['sourceRepresentation'] = meta
    return p

def factory(meta):
    return ec.build_envelope_with_rule_results('p', 'd', 's', '1', 'test', [], [], source_representation=meta)

class PlainRecord(BaseModel):
    x: Any
class ListSubclass(list): pass
class DictSubclass(dict): pass
class TupleSubclass(tuple): pass
@dataclass
class DataRecord:
    x: Any
class Unconsumable:
    def __iter__(self):
        raise AssertionError('Unsupported iterable consumed')

bad = [('tuple-nan', (float('nan'),)), ('tuple-plus-inf', (float('inf'),)), ('tuple-minus-inf', (float('-inf'),)), ('model-nan', PlainRecord(x=(float('nan'),))), ('tuple-huge-int', (10 ** 400,)), ('key-int', {1: 'x'}), ('key-bool', {True: 'x'}), ('key-none', {None: 'x'}), ('key-surrogate', {'\udbff': 1}), ('value-surrogate-pair-codepoints', ('\ud83d\ude00',)), ('set', {1.5}), ('frozenset', frozenset([1.5])), ('deque', deque([1.5])), ('custom-mapping', UserDict(x=1.5)), ('dataclass', DataRecord(1.5)), ('namedtuple', namedtuple('Point', 'x')(1.5)), ('list-subclass', ListSubclass([1.5])), ('dict-subclass', DictSubclass(x=1.5)), ('tuple-subclass', TupleSubclass([1.5])), ('decimal', Decimal('1.5')), ('bytes', b'abc'), ('custom-iterable', Unconsumable())]
seen = []
def generate():
    seen.append('consumed')
    yield float('nan')
gen = generate()
bad.append(('generator', gen))
it = iter([1.5])
bad.append(('iterator', it))
cycle = []; cycle.append(cycle)
bad.append(('cycle-list', cycle))
model_cycle = PlainRecord(x=None); model_cycle.x = model_cycle
bad.append(('cycle-model', model_cycle))
for name, value in bad:
    meta = {'nested': [({'value': value},)]}
    old = ec.build_envelope('p', 'd', 's', '1', 'test', [], source_representation=meta)
    # Assert rejection occurs before *any* JSON dump, not just a downstream serializer error.
    with patch.object(BaseModel, 'model_dump', side_effect=AssertionError('dump reached')):
        assert denied(lambda: ec.validate_json_resources(meta))
        assert denied(lambda: factory(meta))
        assert denied(lambda: ec.validate_envelope(old))
        for version in ['1', '1.0.0', '2.0.0']:
            p = payload(meta, version)
            assert ec.read_envelope_dict(p) is None
            assert denied(lambda: ec.parse_envelope_model(p))
    record(name, rejected_before_dump=True)
assert seen == [] and next(it) == 1.5
record('unsupported-iterables-unconsumed', generator_events=seen, iterator_first_preserved=True)

for name, value in [('tuple', (1.5, None, True, '😀', {'é': 1, 'e\u0301': 2})), ('model', PlainRecord(x=(1.5, '😀', {'\ufffd': 3}))), ('typed-record', ec.EvidenceRow(ruleId='R', objectId='O', canonicalStatus=ec.CanonicalStatus.PASSED))]:
    meta = {'x': value, 'alias': value}
    new = factory(meta)
    old = ec.build_envelope('p', 'd', 's', '1', 'test', [], source_representation=meta)
    ec.validate_envelope(old)
    dumped = old.model_dump(mode='json', exclude_none=True)['sourceRepresentation']
    assert new.sourceRepresentation == dumped and dumped['x'] == dumped['alias']
    record('finite-' + name, dump_preserved=dumped)
for depth in [127, 128, 129]:
    value = 1.5
    for _ in range(depth - 2): value = (value,)
    meta = {'x': value}
    for version in ['1', '1.0.0', '2.0.0']:
        p = payload(meta, version)
        assert (ec.read_envelope_dict(p) is p) == (depth <= 128)
    if depth <= 128:
        ec.validate_json_resources(payload(meta, '2.0.0'))
        try:
            result = factory(meta)
            assert result.sourceRepresentation is not None
            outcome = 'admitted'
        except ValueError:
            outcome = 'safe-serializer-error'
    else:
        assert denied(lambda: factory(meta)); outcome = 'rejected'
    record('tuple-depth-' + str(depth), factory=outcome, read_admitted=depth <= 128)

nodes = ast.parse((ROOT / 'data-service/app.py').read_text(encoding='utf-8'))
ns = {'evidence_contract': ec, 'Any': Any, 'Request': Request, 'HTTPException': HTTPException}
for name in ['parse_evidence_envelope', '_parse_shacl_report', 'EvidencePublishRequest']:
    node = next(n for n in nodes.body if getattr(n, 'name', None) == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual-app-nodes', 'exec'), ns)
DLL = ROOT / 'DG/tests/DG.PublishWireHarness/bin/Debug/net9.0/DG.PublishWireHarness.dll'
assert DLL.is_file()
def guard(raw):
    before = hashlib.sha256(DLL.read_bytes()).hexdigest()
    r = subprocess.run(['dotnet', str(DLL), 'public-guards'], input=raw, cwd=ROOT, capture_output=True, timeout=20)
    assert hashlib.sha256(DLL.read_bytes()).hexdigest() == before
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)

strings = [('\ud800', False), ('\udbff', False), ('\udc00', False), ('\udfff', False), ('\ud800x', False), ('\udfff\ud800', False), ('\ud800\ud800', False), ('\udc00\udc00', False), ('\U00010000', True), ('\U0010ffff', True), ('😀', True), ('\ufffd', True), ('Привет é e\u0301', True), ('\\ud800', True)]
for index, (text, accepted) in enumerate(strings):
    for where in ['key', 'value']:
        meta = {text: 1} if where == 'key' else {'x': text}
        raw = json.dumps(payload(meta, '2.0.0'), ensure_ascii=True).encode()
        read = ns['parse_evidence_envelope'](raw)
        assert (read is not None) == accepted
        if accepted: assert read['sourceRepresentation'] == meta
        JSONResponse({'evidenceEnvelope': read})
        assert guard(raw) == {'utf8': True, 'read': accepted, 'strict': accepted}
        report = ns['_parse_shacl_report'](json.dumps({'source': meta}))
        assert (report is not None) == accepted
        JSONResponse({'shaclReport': report})
        record('unicode-' + str(index) + '-' + where, admitted=accepted, response='ok', public_guards='agree')
# Escaped pairs are decoded to scalar; raw in-memory surrogate codepoints are not scalars.
raw_pair = b'{"contractVersion":"1","x":"\\ud800\\udc00"}'
assert ec.decode_evidence_json(raw_pair)['x'] == '\U00010000'
assert guard(raw_pair) == {'utf8': True, 'read': True, 'strict': False}
record('raw-pair-decodes-to-scalar', preserved=True)
for invalid in [b'\xff', b'\xed\xa0\x80', b'\xf0\x80\x80\x80']:
    raw = b'{"contractVersion":"1","x":"' + invalid + b'"}'
    assert denied(lambda: ec.decode_evidence_json(raw))
    assert guard(raw) == {'utf8': False, 'read': False, 'strict': False}
    record('invalid-utf8-' + invalid.hex(), rejected=True)

async def request_check(raw, accepted):
    calls = 0
    async def receive():
        nonlocal calls
        calls += 1
        assert calls == 1
        return {'type': 'http.request', 'body': raw, 'more_body': False}
    request = ns['EvidencePublishRequest']({'type': 'http', 'method': 'POST', 'path': '/validation/publish', 'headers': []}, receive)
    assert await request.body() == raw
    try:
        first = await request.json()
        assert first is await request.json() and accepted
    except HTTPException as exc:
        assert not accepted and exc.status_code == 422 and exc.detail == 'Invalid publish JSON'
    assert calls == 1
for index, raw in enumerate([b'{"project":"p","ignored":"\\ud800"}', b'{"project":"p","\\udfff":1}', b'{"project":"p","x":"\xff"}', b'{"project":"p","x":"\\ud83d\\ude00"}']):
    asyncio.run(request_check(raw, index == 3))
    record('raw-request-unicode-' + str(index), admitted=index == 3, receives=1)

replay = json.loads((PHASE / 'evidence/review-3-replay.json').read_bytes())
assert len(replay['cases']) == 103
assert all(not v for k, v in replay['summary'].items() if isinstance(v, list))
assert all(r['python_read'] == r['csharp_read']['admitted'] for r in replay['cases'])
assert all(r.get('full_model', False) == r['csharp_strict']['admitted'] for r in replay['cases'])
assert all(r['factory'] == r['legacy_validate'] == 'rejected' for r in replay['inmemory'])
assert all(not r['admitted'] and r['response'] == 'ok' for r in replay['shacl'])
source_after = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_hashes}
assert source_after == source_hashes
print(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'source_hashes': source_hashes, 'source_count': len(source_hashes), 'iteration_diff_exact': True, 'protected_count': len(manifest['protected_files']), 'protected_mismatches': protected_mismatches, 'historical_fixtures_unchanged': True, 'replay_count': len(replay['cases']), 'replay_summary': replay['summary'], 'replay_cross_language_parity': True, 'holdout_count': len(records), 'records': records}, ensure_ascii=True, indent=2))
