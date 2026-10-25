"""Exact fixer scope/evidence manifest; existing dirty changes are not attributed to this iteration."""
import ast
import difflib
import hashlib
import json
import subprocess
from run import ROOT, OUT

files = ['data-service/app.py', 'data-service/evidence_contract.py', 'DG/src/DG.Core/Contracts/EvidenceEnvelopeReader.cs', 'DG/tests/DG.PublishWireHarness/Program.cs', 'data-service/tests/test_evidence_raw_admission.py', 'spec/evidence-contract.schema.json', 'spec/EVIDENCE-CONTRACT.md', 'spec/API.md', 'spec/DATABASE.md']
manifest = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
diffs = []
for name in files:
    old = OUT / 'before' / name
    if old.exists():
        diffs.extend(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True), (ROOT / name).read_text(encoding='utf-8').splitlines(True), fromfile='before/' + name, tofile='after/' + name))
(OUT / 'iteration-only.diff').write_text(''.join(diffs), encoding='utf-8')
for p in ['data-service/app.py', 'data-service/evidence_contract.py', 'data-service/tests/test_evidence_raw_admission.py']:
    ast.parse((ROOT / p).read_text(encoding='utf-8'))
probe = OUT.parent / 'verifier/admission_probe.py'
assert probe.read_bytes() == (OUT / 'admission_probe.py').read_bytes()
protected = json.loads((OUT / 'protected-before.json').read_text())
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p,h in protected.items())
# Original historical fixture source was not edited by the fixer; tests still exercise it.
for p in ['data-service/tests/test_evidence_contract.py','DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs']:
    text = (ROOT / p).read_text(encoding='utf-8')
    assert ('{"contractVersion": "1.0.0", "canonicalStatus": "passed"}' in text if p.endswith('.py') else 'BuildEnvelopeJson' in text)
for p in sorted(OUT.glob('*.log')):
    manifest[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
(OUT / 'manifest.json').write_text(json.dumps({'sourceAndLogsSha256': manifest, 'unchangedProtectedArtifacts': len(protected), 'probeSha256': hashlib.sha256(probe.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
print('PASS syntax, protected artifacts', len(protected), 'probe byte identity; manifest and iteration diff written')
