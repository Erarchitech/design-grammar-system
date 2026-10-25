"""Offline research: unchanged GH DTO/mapper/JSON -> actual AST-loaded backend.
No application startup, network, auth stores or database writes. Nonzero with --assert-canonical
is the expected RED acceptance assertion before implementation.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'data-service'))
import evidence_contract

project = Path(__file__).with_name('WireProbe.csproj')
completed = subprocess.run(['dotnet', 'run', '--project', str(project), '--verbosity', 'quiet'], cwd=ROOT, capture_output=True, text=True)
if completed.returncode:
    print(completed.stdout)
    print(completed.stderr)
    raise SystemExit(completed.returncode)
wire = json.loads(next(line for line in completed.stdout.splitlines() if line.startswith('{')))
names = {'ValidationPublishRulePayload', 'ValidationPublishRuleResultPayload', 'ValidationGeometryItemPayload', 'ValidationGeometryPayload', 'ValidationPublishEntityPayload', 'ValidationPublishRequest', '_parse_supplied_canonical_status', '_build_publish_evidence_envelope'}
tree = ast.parse((ROOT / 'data-service/app.py').read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
assert {n.name for n in nodes} == names
ns = {'BaseModel': BaseModel, 'Field': Field, 'Any': Any, 'evidence_contract': evidence_contract, 'EVIDENCE_SERVICE_VERSION': 'research-probe'}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<production app.py declarations>', 'exec'), ns)
payload = ns['ValidationPublishRequest'].model_validate(wire)
envelope = ns['_build_publish_evidence_envelope'](payload.project, 'RUN_AUDIT', [e.model_dump() for e in payload.entities])
evidence_contract.validate_envelope(envelope)
actual = envelope.rows[0].canonicalStatus.value
print(json.dumps({'production_wire': wire, 'actual_backend_status': actual, 'expected_canonical_status': 'unsupported'}, indent=2))
if '--assert-canonical' in sys.argv:
    assert actual == 'unsupported', f'Production-wire regression: expected unsupported, got {actual}'
