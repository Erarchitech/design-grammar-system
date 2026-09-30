"""Bounded iteration-2 runner; logs and snapshots stay in this directory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
UV = ['uv', 'run', '--no-project', '--with-requirements', 'data-service/requirements.txt', 'python']
ENV = dict(os.environ)
ENV['DG_DE01_CONNECTOR_TOKEN'] = ''
ENV['DG_DE01_CONNECTOR_TOKEN_FILE'] = str(OUT / 'nonexistent-token')
ENV.pop('DG_RETAIN_PHASE1205_1_EVIDENCE', None)
assert not Path(ENV['DG_DE01_CONNECTOR_TOKEN_FILE']).exists()
TOUCH = ['data-service/evidence_contract.py', 'DG/src/DG.Core/Contracts/EvidenceEnvelopeReader.cs',
         'DG/tests/DG.PublishWireHarness/Program.cs', 'DG/tests/DG.Tests/EvidenceContractTests.cs',
         'spec/EVIDENCE-CONTRACT.md']

def run(name, command):
    result = subprocess.run(command, cwd=ROOT, env=ENV, capture_output=True, timeout=600)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    (OUT / (name + '.log')).write_text('command=' + json.dumps(command) + '\ntime=' + datetime.datetime.now(datetime.timezone.utc).isoformat() + '\n' + output + '\nexit=' + str(result.returncode), encoding='utf-8')
    print(name, 'exit', result.returncode)
    print(output[-4000:])
    return result.returncode

if __name__ == '__main__':
    name = sys.argv[1]
    if name == 'snapshot':
        for file in TOUCH:
            target = OUT / 'before' / file
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists()
            shutil.copyfile(ROOT / file, target)
        phase = OUT.parent.parent
        protected = [p for p in phase.rglob('*') if p.is_file() and OUT not in p.parents and '__pycache__' not in p.parts]
        protected += [ROOT / p for p in ['.planning/STATE.md', '.planning/ROADMAP.md', '.planning/REQUIREMENTS.md', 'data-service/app.py', 'data-service/tests/test_evidence_contract.py', 'data-service/tests/test_evidence_raw_admission.py', 'DG/tests/DG.Tests/Neo4jValidGraphRepositoryTests.cs', 'spec/evidence-contract.schema.json']]
        (OUT / 'protected-before.json').write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}, indent=2))
        print('snapshotted', len(TOUCH), 'protected', len(protected))
    elif name.startswith('csharp-'):
        sys.exit(run(name, ['dotnet', 'test', 'DG/tests/DG.Tests/DG.Tests.csproj', '--no-restore', '--filter', 'FullyQualifiedName~UnicodeAdmission', '-v', 'minimal']))
    else:
        sys.exit(run(name, UV + ['-m', 'pytest', 'data-service/tests/test_evidence_unicode_containers.py', '-q', '--tb=short'] + sys.argv[2:]))
