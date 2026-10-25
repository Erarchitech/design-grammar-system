"""Independent bounded read-only probe; no app import, tests, build or network."""
import ast
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'data-service'))
import evidence_contract as ec
import jsonschema
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

PHASE = ROOT / '.planning/phases/1205.1-canonical-status-gh-publish-closure'
DLL = ROOT / 'DG/tests/DG.PublishWireHarness/bin/Debug/net9.0/DG.PublishWireHarness.dll'
BASE = json.loads((PHASE / 'evidence/wire/supported/persisted-evidence.json').read_bytes())
app_tree = ast.parse((ROOT / 'data-service/app.py').read_text(encoding='utf-8'))
ns = {'evidence_contract': ec, 'Any': Any, 'Request': Request, 'HTTPException': HTTPException}
for name in ['parse_evidence_envelope', '_parse_shacl_report', 'EvidencePublishRequest']:
    node = next(n for n in app_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual-app-nodes', 'exec'), ns)


def raw_base(version='2.0.0'):
    p = copy.deepcopy(BASE)
    p['contractVersion'] = version
    if version != '2.0.0':
        p.pop('ruleResults', None)
    return json.dumps(p, separators=(',', ':'), ensure_ascii=True)


def with_metadata(raw, extra):
    return raw[:-1] + ',"sourceRepresentation":' + extra + '}'


def cs(raw, mode):
    before = hashlib.sha256(DLL.read_bytes()).hexdigest()
    r = subprocess.run(['dotnet', str(DLL), mode], input=raw.encode('utf-8'), capture_output=True, timeout=20, cwd=ROOT)
    after = hashlib.sha256(DLL.read_bytes()).hexdigest()
    result = {'exit': r.returncode, 'binary_stable': before == after}
    if r.returncode == 0:
        body = json.loads(r.stdout)
        result['admitted'] = body if mode == 'strict' else body['envelopePresent']
        if mode == 'read':
            result['verdicts'] = body['verdicts']
            result['collisions'] = body['collisions']
    else:
        result['stderr'] = r.stderr.decode(errors='replace')[:2500]
    return result


cases = []
def check(name, raw, expected=None, check_strict=True):
    row = {'name': name, 'raw': raw, 'expected': expected}
    parsed = ns['parse_evidence_envelope'](raw)
    row['python_read'] = parsed is not None
    try:
        JSONResponse({'evidenceEnvelope': parsed})
        row['response'] = 'ok'
    except Exception as exc:
        row['response'] = type(exc).__name__
    try:
        decoded = ec.decode_evidence_json(raw)
        row['raw_decode'] = True
        row['schema'] = jsonschema.Draft202012Validator(ec.load_contract_schema()).is_valid(decoded)
        try:
            ec.parse_envelope_model(decoded)
            row['full_model'] = True
        except (ValueError, jsonschema.ValidationError):
            row['full_model'] = False
    except (ValueError, RecursionError):
        row['raw_decode'] = False
    row['csharp_read'] = cs(raw, 'read')
    if check_strict:
        row['csharp_strict'] = cs(raw, 'strict')
    cases.append(row)


for v in ['1', '1.0.0', '2.0.0']:
    raw = raw_base(v)
    check('baseline-' + v, raw, True)
    check('duplicate-version-' + v, raw.replace('"contractVersion":', '"contractVersion":"2.0.0","contractVersion":', 1), False)
    for suffix, meta in [
        ('escaped', r'{"x":1,"\u0078":2}'),
        ('unicode-pair', r'{"\ud83d\ude00":1,"\uD83D\uDE00":2}'),
        ('composed-distinct', r'{"\u00e9":1,"e\u0301":2}'),
    ]:
        check('keys-' + suffix + '-' + v, with_metadata(raw, meta), suffix == 'composed-distinct')
    for depth in [70, 127, 128, 129, 702]:
        check('depth-' + str(depth) + '-' + v, with_metadata(raw, '{"x":' + '[' * (depth - 2) + '0' + ']' * (depth - 2) + '}'), depth <= 128)
    for token in ['NaN', 'Infinity', '-Infinity', '1e400', '-1e400', '9' * 400, '1.7976931348623157e308']:
        check('finite-' + token[:24] + '-' + v, with_metadata(raw, '{"x":' + token + '}'), token == '1.7976931348623157e308')
    for token in ['1.0', '1e0', '1099511627776', '-9007199254740991', '9007199254740991', '9007199254740992', '-9007199254740992', '1.5', 'true', '1e-400', '9007199254740991.0']:
        mutated = raw.replace('"canonicalizationVersion":1', '"canonicalizationVersion":' + token, 1)
        check('integer-' + token + '-' + v, mutated)
    for where in ['key', 'value']:
        meta = r'{"\ud800":1}' if where == 'key' else r'{"x":"\ud800"}'
        check('unpaired-surrogate-' + where + '-' + v, with_metadata(raw, meta), False)
    if v != '2.0.0':
        check('old-no-rows-' + v, '{"contractVersion":"' + v + '","canonicalStatus":"passed"}', True)

for field in ['inputHash', 'outputHash', 'dgId', 'row.inputHash', 'row.outputHash']:
    for newline in [False, True]:
        p = copy.deepcopy(BASE)
        target = p['rows'][0] if field.startswith('row.') else p
        target[field.split('.')[-1]] = ('dg:' + 'A' * 16 if field == 'dgId' else 'A' * 64) + ('\n' if newline else '')
        check('hash-' + field + '-' + str(newline), json.dumps(p), not newline)

# Duplicate array identity is deliberately not a duplicate object member.
p = copy.deepcopy(BASE)
p['rows'].append(copy.deepcopy(p['rows'][0]))
check('allowed-array-collision', json.dumps(p), True)

inmemory = []
for container in [list, tuple]:
    for token_name, number in [('nan', float('nan')), ('inf', float('inf'))]:
        meta = {'x': container([number])}
        row = {'container': container.__name__, 'number': token_name}
        try:
            m = ec.build_envelope_with_rule_results('p', 'd', 's', '1', 'test', [], [], source_representation=meta)
            row['factory'] = 'admitted'
            row['factory_metadata'] = m.model_dump(mode='json')['sourceRepresentation']
        except ValueError:
            row['factory'] = 'rejected'
        old = ec.build_envelope('p', 'd', 's', '1', 'test', [], source_representation=meta)
        try:
            ec.validate_envelope(old)
            row['legacy_validate'] = 'admitted'
        except ValueError:
            row['legacy_validate'] = 'rejected'
        inmemory.append(row)

async def request_probe(raw):
    calls = 0
    async def receive():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise AssertionError('Body receive consumed twice')
        return {'type': 'http.request', 'body': raw.encode(), 'more_body': False}
    req = ns['EvidencePublishRequest']({'type': 'http', 'method': 'POST', 'path': '/validation/publish', 'headers': []}, receive)
    try:
        b = await req.body()  # FastAPI reads body before json().
        first = await req.json()
        second = await req.json()  # Auth project resolution reuses it.
        return {'result': 'admitted', 'same_cached_object': first is second, 'receive_calls': calls, 'body_preserved': b == raw.encode()}
    except HTTPException as exc:
        return {'status': exc.status_code, 'detail': exc.detail, 'receive_calls': calls}

requests = {}
for name, raw in [('valid', '{"project":"p"}'), ('duplicate', '{"project":"p","project":"q"}'), ('nested-escaped', r'{"project":"p","x":{"a":1,"\u0061":2}}'), ('nonfinite', '{"project":"p","x":NaN}'), ('overflow', '{"project":"p","x":1e400}'), ('deep', '{"project":"p","x":' + '[' * 128 + '0' + ']' * 128 + '}')]:
    requests[name] = asyncio.run(request_probe(raw))

shacl = []
for raw in [r'{"source":{"\ud800":1}}', r'{"source":{"x":"\ud800"}}', '{"source":{"x":NaN}}']:
    parsed = ns['_parse_shacl_report'](raw)
    row = {'raw': raw, 'admitted': parsed is not None}
    try:
        JSONResponse({'shaclReport': parsed})
        row['response'] = 'ok'
    except Exception as exc:
        row['response'] = type(exc).__name__
    shacl.append(row)

summary = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'case_count': len(cases),
    'expected_admission_mismatches': [r['name'] for r in cases if r['expected'] is not None and (r['python_read'] != r['expected'] or r['csharp_read'].get('admitted') != r['expected'])],
    'response_failures': [r['name'] for r in cases if r['response'] != 'ok'],
    'strict_process_failures': [r['name'] for r in cases if r.get('csharp_strict', {}).get('exit', 0) != 0],
    'binary_changed_during_probe': [r['name'] for r in cases if not r['csharp_read']['binary_stable'] or not r.get('csharp_strict', {}).get('binary_stable', True)],
}
print(json.dumps({'summary': summary, 'requests': requests, 'inmemory': inmemory, 'shacl': shacl, 'cases': cases}, ensure_ascii=True, indent=2))
